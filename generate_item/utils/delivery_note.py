# Copyright (c) 2025, Finbyz and contributors
# For license information, please see license.txt

# from erpnext.selling.doctype.sales_order.sales_order import get_company_address
import frappe
from frappe import _
import json
from frappe.utils import flt
from erpnext.stock.doctype.batch.batch import get_batch_qty

@frappe.whitelist()
def get_custom_batches_for_dn_items(items_data):
    """
    Fetch custom batch numbers from linked Sales Orders for Delivery Note items.
    items_data: list of dicts e.g.,
        [{'against_sales_order': 'SO-001', 'so_detail': 'SO-ITEM-ROW-ID', 'item_code': 'ITEM-1',
          'item_name': 'Item Name', 'dn_item_name': 'DN-ITEM-ROW-ID'}]
    Returns: dict {dn_item_name: custom_batch_no} for items where batch is available.
    """
    if isinstance(items_data, str):
        items_data = frappe.parse_json(items_data)
    elif not isinstance(items_data, list):
        frappe.throw(_("Invalid items_data format. Expected list of dicts."))

    if not items_data:
        return {}

    results = {}

    for data in items_data:
        so_name = data.get('against_sales_order')
        so_detail = data.get('so_detail')
        item_code = data.get('item_code')
        item_name = data.get('item_name')
        dn_item_name = data.get('dn_item_name')

        if not all([so_name, so_detail, item_code, dn_item_name]):
            continue

        try:
            so_item = frappe.get_all(
                "Sales Order Item",
                filters={
                    "parent": so_name,
                    "name": so_detail,
                    "item_code": item_code
                },
                fields=["item_name", "custom_batch_no"],
                limit=1
            )

            if not so_item:
                continue

            so_data = so_item[0]

            # Optional: strict match on item_name (can be skipped if same code = same item)
            if so_data.item_name != item_name:
                frappe.log_error(f"Item name mismatch for {item_code} in Sales Order Item {so_detail} (SO: {so_name})")
                continue

            if so_data.custom_batch_no:
                results[dn_item_name] = so_data.custom_batch_no

        except frappe.PermissionError:
            frappe.log_error(f"Permission denied accessing Sales Order Item {so_detail} (SO: {so_name}) for item {item_code}")
            continue
        except Exception as e:
            frappe.log_error(f"Error fetching batch for {item_code} in SO Item {so_detail} (SO: {so_name}): {str(e)}")
            continue

    return results

def before_save(doc,method):
    dn_shipping = doc.shipping_address_name

    # If Delivery Note shipping is empty, skip validation
    if not dn_shipping:
        return

    for idx, row in enumerate(doc.items, start=1):
        # Skip if row shipping_address is empty
        if not row.custom_shipping_address:
            continue

        # Compare row shipping vs DN shipping
        if row.custom_shipping_address != dn_shipping:
            frappe.throw(
                f"Row #{idx}: The shipping address '{row.custom_shipping_address}' "
                f"does not match the Delivery Note shipping address '{dn_shipping}'."
            )
            
def set_batch_from_sales_order(doc, method):
    """
    Server-side hook to set batches on save (backup for any missed client-side sets).
    Runs only for new documents.
    """
    if not doc.get("__islocal"):
        return

    # Collect items data similar to JS
    items_data = []
    for item in doc.items:
        if item.against_sales_order and item.so_detail and not item.custom_batch_no:
            items_data.append({
                'against_sales_order': item.against_sales_order,
                'so_detail': item.so_detail,
                'item_code': item.item_code,
                'item_name': item.item_name,
                'dn_item_name': item.name  # Not used here, but for consistency
            })

    if items_data:
        batches = get_custom_batches_for_dn_items(items_data)
        updated_count = 0
        for dn_item_name, batch_no in batches.items():
            # Find and set in doc
            for item in doc.items:
                if item.name == dn_item_name:
                    item.custom_batch_no = batch_no
                    updated_count += 1
                    break

        if updated_count > 0:
            frappe.msgprint(
                f"{updated_count} custom batch(es) set from Sales Orders.",
                title=__("Batches Updated"),
                indicator="green"
            )



@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_dispatchable_sales_orders(doctype, txt, searchfield, start, page_len, filters):
    """
    Custom query for Dispatchable Sales Orders link field.
    Returns Sales Orders that are:
    - Submitted and not fully delivered
    - Have all linked Work Orders completed
    """

    import json

    # Parse filters safely
    if isinstance(filters, str):
        try:
            filters = json.loads(filters)
        except Exception:
            filters = {}
    elif not isinstance(filters, dict):
        filters = {}

    customer = filters.get("customer")
    company = filters.get("company")
    project = filters.get("project")

    if not customer:
        return []

    values = {
        "customer": customer,
        "start": int(start or 0),
        "page_len": int(page_len or 20),
    }

    # Core conditions
    conditions = [
        "so.docstatus = 1",
        "so.status NOT IN ('Closed', 'On Hold', 'Completed')",
        "COALESCE(so.per_delivered, 0) < 99.99",
        "so.customer = %(customer)s",
        # Has at least one completed Work Order
        """EXISTS (
            SELECT 1 FROM `tabWork Order` wo
            WHERE wo.sales_order = so.name
            AND wo.docstatus = 1
            AND wo.status = 'Completed'
        )""",
        # No Work Orders that are not completed
        """NOT EXISTS (
            SELECT 1 FROM `tabWork Order` wo2
            WHERE wo2.sales_order = so.name
            AND wo2.docstatus = 1
            AND wo2.status != 'Completed'
        )"""
    ]

    if company:
        conditions.append("so.company = %(company)s")
        values["company"] = company
    if project:
        conditions.append("so.project = %(project)s")
        values["project"] = project
    if txt:
        conditions.append("(so.name LIKE %(txt)s OR so.customer_name LIKE %(txt)s)")
        values["txt"] = f"%{txt}%"

    where_clause = " AND ".join(conditions)

    # --- Add Batch Reference in Description ---
    query = f"""
        SELECT 
            so.name,
            CONCAT(
                so.name,
                ' - ',
                COALESCE((
                    SELECT MAX(soi.custom_batch_no)
                    FROM `tabSales Order Item` soi
                    WHERE soi.parent = so.name
                    AND COALESCE(soi.custom_batch_no, '') != ''
                ), 'No Batch'),
                ' - ',
                so.customer_name
            ) AS description
        FROM `tabSales Order` so
        WHERE {where_clause}
        ORDER BY so.modified DESC
        LIMIT %(page_len)s OFFSET %(start)s
    """

    return frappe.db.sql(query, values, as_list=True)

@frappe.whitelist()
def get_dispatchable_sales_orders_list(customer=None, company=None, project=None, warehouse=None, branch=None):
    """
    Returns Sales Orders that:
    1. Belong to given customer
    2. Are not fully delivered
    3. All items have sufficient stock (>= required qty)
    """
    if not customer:
        frappe.throw("Customer is required")

    values = {"customer": customer}
    conditions = [
        "so.docstatus = 1",
        "so.status NOT IN ('Closed', 'On Hold', 'Completed')",
        "COALESCE(so.per_delivered, 0) < 99.99",
        "so.customer = %(customer)s"
    ]

    if company:
        conditions.append("so.company = %(company)s")
        values["company"] = company

    if project:
        conditions.append("so.project = %(project)s")
        values["project"] = project
        
    if branch:
        conditions.append("so.branch = %(branch)s")
        values["branch"] = branch

    where_clause = " AND ".join(conditions)

    # Step 1: Fetch candidate Sales Orders that meet criteria
    sales_orders = frappe.db.sql(f"""
        SELECT so.name,so.set_warehouse
        FROM `tabSales Order` so
        WHERE {where_clause}
        ORDER BY so.modified DESC
    """, values, as_dict=True)

    dispatchable_orders = []

    # Step 2: Check stock availability for all items in each SO
    for so in sales_orders:
        items = frappe.get_all(
            "Sales Order Item",
            filters={"parent": so.name},
            fields=["name", "item_code", "qty", "warehouse"]
        )

        if not items:
            continue

        delivered_qty_map = {
            row.so_detail: row.dn_qty
            for row in frappe.db.sql(
                """
                SELECT dni.so_detail, SUM(dni.qty) AS dn_qty
                FROM `tabDelivery Note Item` dni
                INNER JOIN `tabDelivery Note` dn ON dn.name = dni.parent
                WHERE dn.docstatus != 2
                  AND dni.against_sales_order = %s
                GROUP BY dni.so_detail
                """,
                so.name,
                as_dict=True,
            )
        }

        # Skip SO if all its items are already fully covered by existing Delivery Notes (docstatus 0/1)
        all_items_delivered = all(
            delivered_qty_map.get(item.name, 0) >= flt(item.qty)
            for item in items
        )

        if all_items_delivered:
            continue

        all_items_in_stock = True
        at_least_one_in_stock = False
        
        for item in items:
            
            # item_warehouse = warehouse or item.warehouse
            # if not item_warehouse:
            #     all_items_in_stock = False
            #     break
            item_warehouse = so.set_warehouse or warehouse or item.warehouse
            if not item_warehouse:
                continue


            batches = frappe.get_all(
                "Batch",
                filters={
                    "item": item.item_code,
                    "reference_name": so.name,  
                    "reference_doctype": "Sales Order", 
                    "disabled": 0
                },
                pluck="name"
            )
            # frappe.log_error( "Batches data----",batches)

            total_batch_qty = 0

            for batch_no in batches:
                qty = get_batch_qty(
                    batch_no=batch_no,
                    warehouse=item_warehouse,
                    item_code=item.item_code
                )
                total_batch_qty += flt(qty)
            
            
            if total_batch_qty > 0:
                at_least_one_in_stock = True 
                break

        # if all_items_in_stock:
        #     dispatchable_orders.append({"name": so.name})
        if at_least_one_in_stock:
            dispatchable_orders.append({
                "name": so.name
            })
            
    return dispatchable_orders
import frappe
from frappe import _
from frappe.utils import flt


@frappe.whitelist()
def get_dispatchable_so():
    """
    Return dispatchable Sales Orders.
    Checks ALL submitted SOs that are not fully delivered and have available stock.
    """
    # ── 1. Eligible SOs ──────────────────────────────────────────────────────
    eligible_sos = frappe.db.sql(
        """
        SELECT name, set_warehouse
        FROM `tabSales Order`
        WHERE docstatus = 1
          AND status NOT IN ('Closed', 'On Hold', 'Completed')
          AND COALESCE(per_delivered, 0) < 99.99
        ORDER BY modified DESC
        """,
        as_dict=True,
    )

    if not eligible_sos:
        return []

    so_names = [so.name for so in eligible_sos]
    so_wh_map = {so.name: so.set_warehouse for so in eligible_sos}
    ph = _build_placeholders(so_names)

    # ── 2. All SO items (bulk) ───────────────────────────────────────────────
    so_items = frappe.db.sql(
        f"""
        SELECT name, parent, item_code, qty, warehouse
        FROM `tabSales Order Item`
        WHERE parent IN ({ph})
        """,
        so_names,
        as_dict=True,
    )

    if not so_items:
        return []

    # ── 3. All delivered quantities (bulk) ───────────────────────────────────
    delivered_rows = frappe.db.sql(
        f"""
        SELECT dni.so_detail, SUM(dni.qty) AS delivered_qty
        FROM `tabDelivery Note Item` dni
        INNER JOIN `tabDelivery Note` dn ON dn.name = dni.parent
        WHERE dn.docstatus != 2
          AND dni.against_sales_order IN ({ph})
        GROUP BY dni.so_detail
        """,
        so_names,
        as_dict=True,
    )
    delivered_map = {r.so_detail: flt(r.delivered_qty) for r in delivered_rows}

    # ── 4. Get all item-warehouse pairs needed ───────────────────────────────
    item_warehouse_pairs = set()
    for item in so_items:
        warehouse = so_wh_map.get(item.parent) or item.warehouse
        if warehouse and item.item_code:
            item_warehouse_pairs.add((item.item_code, warehouse))

    # ── 5. Get available stock for all items at once ─────────────────────────
    batch_avail = _get_stock_availability(item_warehouse_pairs)

    # ── 6. Python-side filtering ────────────────────────────────────────────
    items_by_so = {}
    for item in so_items:
        items_by_so.setdefault(item.parent, []).append(item)

    dispatchable = []
    for so in eligible_sos:
        items = items_by_so.get(so.name, [])
        if not items:
            continue

        for item in items:
            # Calculate pending quantity
            pending = flt(item.qty) - flt(delivered_map.get(item.name, 0))
            
            # Skip if fully delivered
            if pending <= 0:
                continue

            # Get warehouse (priority: SO set_warehouse > item warehouse)
            warehouse = so_wh_map.get(so.name) or item.warehouse
            if not warehouse:
                continue

            # Check if stock is available
            available = batch_avail.get((item.item_code, warehouse), 0)
            
            if available > 0:
                dispatchable.append({"name": so.name})
                break  # One stocked pending item is enough

    return dispatchable


def _get_stock_availability(item_warehouse_pairs):
    """
    Get available stock quantities for multiple item-warehouse combinations.
    Returns {(item_code, warehouse): total_actual_qty}
    """
    if not item_warehouse_pairs:
        return {}

    # Build OR conditions for all pairs
    conditions = []
    params = []
    for item_code, warehouse in item_warehouse_pairs:
        conditions.append("(sle.item_code = %s AND sle.warehouse = %s)")
        params.extend([item_code, warehouse])

    where_clause = " OR ".join(conditions)

    rows = frappe.db.sql(
        f"""
        SELECT 
            sle.item_code, 
            sle.warehouse, 
            SUM(sle.actual_qty) AS qty
        FROM `tabStock Ledger Entry` sle
        WHERE ({where_clause})
          AND sle.is_cancelled = 0
        GROUP BY sle.item_code, sle.warehouse
        HAVING SUM(sle.actual_qty) > 0
        """,
        params,
        as_dict=True,
    )

    return {(r.item_code, r.warehouse): flt(r.qty) for r in rows}


def _build_placeholders(lst):
    """Return a %s placeholder string for a list."""
    return ",".join(["%s"] * len(lst))


# ── Link-field query (used by frontend dialog) ──────────────────────────────
@frappe.whitelist()
def get_dispatchable_so_for_query(doctype, txt, searchfield, start, page_len, filters):
    """
    Link-field query for dispatchable SOs.
    """
    so_names = [so["name"] for so in get_dispatchable_so()]

    if not so_names:
        return []

    ph = _build_placeholders(so_names)
    params = list(so_names)

    txt_cond = ""
    if txt:
        txt_cond = " AND name LIKE %s"
        params.append(f"%{txt}%")

    params.extend([int(page_len), int(start)])

    return frappe.db.sql(
        f"""
        SELECT name
        FROM `tabSales Order`
        WHERE name IN ({ph}){txt_cond}
        ORDER BY modified DESC
        LIMIT %s OFFSET %s
        """,
        params,
    )


# ── Get items for selected SO ───────────────────────────────────────────────
@frappe.whitelist()
def get_so_items_for_selection(sales_order):
    """
    Fetch SO items with pending qty + available stock for the dialog.
    """
    if not sales_order:
        frappe.throw(_("Sales Order is required"))

    so = frappe.get_doc("Sales Order", sales_order)
    if so.docstatus != 1:
        frappe.throw(_("Selected Sales Order is not submitted."))

    # ── 1. Delivered quantities ──────────────────────────────────────────────
    delivered_rows = frappe.db.sql(
        """
        SELECT dni.so_detail, SUM(dni.qty) AS delivered_qty
        FROM `tabDelivery Note Item` dni
        INNER JOIN `tabDelivery Note` dn ON dn.name = dni.parent
        WHERE dn.docstatus != 2
          AND dni.against_sales_order = %s
        GROUP BY dni.so_detail
        """,
        sales_order,
        as_dict=True,
    )
    delivered_map = {r.so_detail: flt(r.delivered_qty) for r in delivered_rows}

    # ── 2. Get item-warehouse pairs ──────────────────────────────────────────
    item_warehouse_pairs = set()
    for item in so.items:
        warehouse = so.set_warehouse or item.warehouse
        if warehouse and item.item_code:
            item_warehouse_pairs.add((item.item_code, warehouse))

    # ── 3. Get available stock ───────────────────────────────────────────────
    batch_avail = _get_stock_availability(item_warehouse_pairs)

    # ── 4. Build result ──────────────────────────────────────────────────────
    result = []
    for item in so.items:
        ordered = flt(item.qty)
        delivered = flt(delivered_map.get(item.name, 0))
        pending = ordered - delivered

        if pending <= 0:
            continue

        warehouse = so.set_warehouse or item.warehouse
        available_qty = max(0, flt(batch_avail.get((item.item_code, warehouse), 0))) if warehouse else 0

        result.append({
            # Identity
            "name": item.name,
            "idx": item.idx,
            # Item details
            "item_code": item.item_code,
            "item_name": item.item_name,
            "description": item.description,
            "gst_hsn_code": item.gst_hsn_code,
            # Quantities
            "ordered_qty": ordered,
            "delivered_qty": delivered,
            "pending_qty": pending,
            "available_batch_qty": available_qty,
            "qty": pending,
            # UOM
            "uom": item.uom,
            "stock_uom": item.stock_uom,
            "conversion_factor": item.conversion_factor,
            # Pricing
            "rate": item.rate,
            "amount": item.amount,
            "net_rate": item.net_rate,
            "net_amount": item.net_amount,
            "base_rate": item.base_rate,
            "base_amount": item.base_amount,
            "base_net_rate": item.base_net_rate,
            "base_net_amount": item.base_net_amount,
            "price_list_rate": item.price_list_rate,
            "margin_type": item.margin_type,
            "margin_rate_or_amount": item.margin_rate_or_amount,
            "discount_percentage": item.discount_percentage,
            "discount_amount": item.discount_amount,
            # Logistics
            "warehouse": warehouse,
            "against_sales_order": so.name,
            "so_detail": item.name,
            # GST
            "igst_rate": item.igst_rate,
            "cgst_rate": item.cgst_rate,
            "sgst_rate": item.sgst_rate,
            "cess_rate": item.cess_rate,
            "igst_amount": item.igst_amount,
            "cgst_amount": item.cgst_amount,
            "sgst_amount": item.sgst_amount,
            "cess_amount": item.cess_amount,
            "taxable_value": item.taxable_value,
            # Custom fields
            "custom_batch_no": item.get("custom_batch_no"),
            "branch": item.get("branch") or so.get("branch"),
            "project": item.get("project") or so.project,
            "cost_center": item.get("cost_center"),
            "expense_account": item.get("expense_account"),
            "weight_per_unit": item.get("weight_per_unit"),
            "weight_uom": item.get("weight_uom"),
            "custom_drg_and_pur_spec": item.get("custom_drg_and_pur_spec"),
            "custom_drawing_no": item.get("custom_drawing_no"),
            "custom_drawing_rev_no": item.get("custom_drawing_rev_no"),
            "custom_pattern_drawing_no": item.get("custom_pattern_drawing_no"),
            "custom_pattern_drawing_rev_no": item.get("custom_pattern_drawing_rev_no"),
            "custom_purchase_specification_no": item.get("custom_purchase_specification_no"),
            "custom_purchase_specification_rev_no": item.get("custom_purchase_specification_rev_no"),
        })

    return result
@frappe.whitelist()
def make_delivery_note_for_so(source_name, target_doc=None, kwargs=None):
    
    from erpnext.stock.doctype.packed_item.packed_item import make_packing_list
    from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
        get_sre_details_for_voucher,
        get_sre_reserved_qty_details_for_voucher,
        get_ssb_bundle_for_voucher,
    )

    if not kwargs:
        kwargs = {
            "for_reserved_stock": frappe.flags.args and frappe.flags.args.for_reserved_stock,
            "skip_item_mapping": frappe.flags.args and frappe.flags.args.skip_item_mapping,
        }

    kwargs = frappe._dict(kwargs)

    sre_details = {}
    if kwargs.for_reserved_stock:
        sre_details = get_sre_reserved_qty_details_for_voucher("Sales Order", source_name)

    mapper = {
        "Sales Order": {"doctype": "Delivery Note", "validation": {"docstatus": ["=", 1]}},
        "Sales Taxes and Charges": {"doctype": "Sales Taxes and Charges", "reset_value": True},
        "Sales Team": {"doctype": "Sales Team", "add_if_empty": True},
    }

    # 0 qty is accepted, as the qty is uncertain for some items
    has_unit_price_items = frappe.db.get_value("Sales Order", source_name, "has_unit_price_items")

    def is_unit_price_row(source):
        return has_unit_price_items and source.qty == 0

    def select_item(d):
        filtered_items = kwargs.get("filtered_children", [])
        child_filter = d.name in filtered_items if filtered_items else True
        return child_filter

    def set_missing_values(source, target):
        if kwargs.get("ignore_pricing_rule"):
            # Skip pricing rule when the dn is creating from the pick list
            target.ignore_pricing_rule = 1

        target.run_method("set_missing_values")
        target.run_method("set_po_nos")
        target.run_method("calculate_taxes_and_totals")
        target.run_method("set_use_serial_batch_fields")

        if source.company_address:
            target.update({"company_address": source.company_address})
        else:
            # set company address
            target.update(get_company_address(target.company))

        if target.company_address:
            target.update(get_fetch_values("Delivery Note", "company_address", target.company_address))

        # if invoked in bulk creation, validations are ignored and thus this method is nerver invoked
        if frappe.flags.bulk_transaction:
            # set target items names to ensure proper linking with packed_items
            target.set_new_name()

        make_packing_list(target)

    def condition(doc):
        if doc.name in sre_details:
            del sre_details[doc.name]
            return False

        # make_mapped_doc sets js `args` into `frappe.flags.args`
        if frappe.flags.args and frappe.flags.args.delivery_dates:
            if cstr(doc.delivery_date) not in frappe.flags.args.delivery_dates:
                return False

        return (
            (abs(doc.delivered_qty) < abs(doc.qty)) or is_unit_price_row(doc)
        ) and doc.delivered_by_supplier != 1

    def update_item(source, target, source_parent):
        target.base_amount = (flt(source.qty) - flt(source.delivered_qty)) * flt(source.base_rate)
        target.amount = (flt(source.qty) - flt(source.delivered_qty)) * flt(source.rate)
        target.qty = (
            flt(source.qty) if is_unit_price_row(source) else flt(source.qty) - flt(source.delivered_qty)
        )

        item = get_item_defaults(target.item_code, source_parent.company)
        item_group = get_item_group_defaults(target.item_code, source_parent.company)

        if item:
            target.cost_center = (
                frappe.db.get_value("Project", source_parent.project, "cost_center")
                or item.get("buying_cost_center")
                or item_group.get("buying_cost_center")
            )

    if not kwargs.skip_item_mapping:
        mapper["Sales Order Item"] = {
            "doctype": "Delivery Note Item",
            "field_map": {
                "rate": "rate",
                "name": "so_detail",
                "parent": "against_sales_order",
                "component_of": "component_of",
                "custom_shipping_address":"shipping_address"
            },
            "condition": lambda d: condition(d) and select_item(d),
            "postprocess": update_item,
        }

    so = frappe.get_doc("Sales Order", source_name)
    target_doc = get_mapped_doc("Sales Order", so.name, mapper, target_doc)

    if not kwargs.skip_item_mapping and kwargs.for_reserved_stock:
        sre_list = get_sre_details_for_voucher("Sales Order", source_name)

        if sre_list:

            def update_dn_item(source, target, source_parent):
                update_item(source, target, so)

            so_items = {d.name: d for d in so.items if d.stock_reserved_qty}

            for sre in sre_list:
                if not condition(so_items[sre.voucher_detail_no]):
                    continue

                dn_item = get_mapped_doc(
                    "Sales Order Item",
                    sre.voucher_detail_no,
                    {
                        "Sales Order Item": {
                            "doctype": "Delivery Note Item",
                            "field_map": {
                                "rate": "rate",
                                "name": "so_detail",
                                "parent": "against_sales_order",
                                "component_of": "component_of",
                                "custom_shipping_address":"shipping_address"
                            },
                            "postprocess": update_dn_item,
                        }
                    },
                    ignore_permissions=True,
                )

                dn_item.qty = flt(sre.reserved_qty) / flt(dn_item.get("conversion_factor", 1))

                if sre.reservation_based_on == "Serial and Batch" and (sre.has_serial_no or sre.has_batch_no):
                    dn_item.serial_and_batch_bundle = get_ssb_bundle_for_voucher(sre)

                target_doc.append("items", dn_item)
            else:
                # Correct rows index.
                for idx, item in enumerate(target_doc.items):
                    item.idx = idx + 1

    # Should be called after mapping items.
    set_missing_values(so, target_doc)

    return target_doc

@frappe.whitelist()
def make_delivery_note(source_name, target_doc=None, kwargs=None):
    """Create Delivery Note from Sales Order while ensuring remaining qty excludes Draft DNs.

    This wraps the core method and then adjusts mapped quantities by subtracting
    any quantities already present in Draft Delivery Notes for the same Sales Order Item.
    """
    from erpnext.selling.doctype.sales_order.sales_order import (
        make_delivery_note as core_make_delivery_note,
    )
    

    # Handle kwargs parameter - it might be a JSON string
    print(f"DEBUG: make_delivery_note called with kwargs type: {type(kwargs)}, value: {kwargs}")

    if isinstance(kwargs, str):
        try:
            import json
            kwargs = json.loads(kwargs)
            print(f"DEBUG: Parsed kwargs from string: {kwargs}")
        except Exception as e:
            print(f"DEBUG: Failed to parse kwargs: {e}")
            kwargs = {}
    elif not isinstance(kwargs, dict):
        print(f"DEBUG: kwargs is not dict, converting to empty dict")
        kwargs = {}

    print(f"DEBUG: Final kwargs: {kwargs}")

    # Create the Delivery Note using core logic first
    dn = core_make_delivery_note(source_name=source_name, target_doc=target_doc, kwargs=kwargs)
    



    # Adjust quantities to consider Draft DNs as consumed
    items_to_keep = []
    for item in dn.items or []:
        so_item_name = getattr(item, "so_detail", None)
        if not so_item_name:
            items_to_keep.append(item)
            continue

        # Fetch source SO Item values
        so_item = frappe.db.get_value(
            "Sales Order Item",
            so_item_name,
            ["qty", "delivered_qty", "conversion_factor"],
            as_dict=True,
        )
        if not so_item:
            items_to_keep.append(item)
            continue

        so_qty = frappe.utils.flt(so_item.qty)
        delivered_qty = frappe.utils.flt(so_item.delivered_qty)
        so_cf = frappe.utils.flt(so_item.conversion_factor) or 1.0

        # Base remaining in stock units from Submitted DNs
        base_remaining_stock_qty = max((so_qty - delivered_qty), 0) * so_cf

        # Subtract quantities already present in Draft Delivery Notes for this SO Item
        draft_dn_stock_qty = frappe.db.sql(
            """
            SELECT COALESCE(SUM(dni.stock_qty), 0)
            FROM `tabDelivery Note Item` dni
            INNER JOIN `tabDelivery Note` dn ON dni.parent = dn.name
            WHERE dn.docstatus = 0
                AND dni.so_detail = %s
            """,
            (so_item_name,),
        )[0][0]

        remaining_stock_qty = max(base_remaining_stock_qty - frappe.utils.flt(draft_dn_stock_qty), 0)

        # Use target item's conversion factor to set displayed qty
        item_cf = frappe.utils.flt(getattr(item, "conversion_factor", None)) or 1.0
        new_qty = remaining_stock_qty / item_cf if item_cf else 0
        item.qty = new_qty
        item.stock_qty = remaining_stock_qty

        # Keep only rows with positive qty
        if new_qty and new_qty > 0:
            items_to_keep.append(item)

    # Replace items with filtered list to avoid zero-qty rows
    if dn.items is not None:
        dn.items = items_to_keep

    return dn



@frappe.whitelist()
def set_remaining_actual_taxes(delivery_name):
    """
    Whitelisted method to calculate and set remaining actual taxes
    FOR SAVED DOCUMENTS ONLY (Delivery Note)
    """
    if not frappe.db.exists("Delivery Note", delivery_name):
        frappe.throw(_("Delivery Note {0} not found").format(delivery_name))
    
    doc = frappe.get_doc("Delivery Note", delivery_name)
    
    if doc.docstatus == 2:
        frappe.throw(_("Cannot update taxes for a cancelled Delivery Note"))
    
    _calculate_and_set_remaining_taxes(doc)
    doc.save()
    frappe.db.commit()
    
    return {
        "success": True,
        "message": _("Actual taxes updated successfully on Delivery Note")
    }


@frappe.whitelist()
def get_remaining_taxes_for_draft(sales_orders, current_dn_name=None):
    """
    Calculate remaining actual taxes for DRAFT/UNSAVED Delivery Note
    """
    if isinstance(sales_orders, str):
        import json
        sales_orders = json.loads(sales_orders)

    remaining_taxes = {}

    for so_name in sales_orders:
        # Get Sales Order actual taxes
        so_doc = frappe.get_doc("Sales Order", so_name)
        so_actual_taxes = {}
        for tax in so_doc.taxes:
            if tax.charge_type == "Actual":
                so_actual_taxes[tax.account_head] = so_actual_taxes.get(tax.account_head, 0) + (tax.tax_amount or 0)

        if not so_actual_taxes:
            continue

        # Get all existing Delivery Notes against the SO
        filters = {
            "against_sales_order": so_name,
            "docstatus": ["!=", 2],
        }

        if current_dn_name and frappe.db.exists("Delivery Note", current_dn_name):
            filters["parent"] = ["!=", current_dn_name]

        existing_dns = frappe.get_all(
            "Delivery Note Item",
            filters=filters,
            fields=["parent"],
            distinct=True
        )

        billed_taxes = {}
        for dn in existing_dns:
            dn_doc = frappe.get_doc("Delivery Note", dn.parent)
            for tax in dn_doc.taxes:
                if tax.charge_type == "Actual":
                    billed_taxes[tax.account_head] = billed_taxes.get(tax.account_head, 0) + (tax.tax_amount or 0)

        # Compute remaining
        for account_head, total_amount in so_actual_taxes.items():
            billed_amount = billed_taxes.get(account_head, 0)
            remaining = max(total_amount - billed_amount, 0)
            if account_head in remaining_taxes:
                remaining_taxes[account_head] = min(remaining_taxes[account_head], remaining)
            else:
                remaining_taxes[account_head] = remaining

    return remaining_taxes


def after_insert(doc, method=None):
    """Run after new Delivery Note is inserted"""
    _calculate_and_set_remaining_taxes(doc)


def _calculate_and_set_remaining_taxes(doc):
    """
    Internal function to calculate remaining taxes for Delivery Note
    """
    sales_orders = list(set([item.against_sales_order for item in doc.items if item.against_sales_order]))
    if not sales_orders:
        return

    taxes_updated = False

    for so_name in sales_orders:
        so_doc = frappe.get_doc("Sales Order", so_name)
        so_actual_taxes = {}
        for tax in so_doc.taxes:
            if tax.charge_type == "Actual":
                so_actual_taxes[tax.account_head] = {
                    "amount": tax.tax_amount or 0,
                    "description": tax.description,
                    "cost_center": tax.cost_center,
                    "branch": tax.get("branch"),
                }

        if not so_actual_taxes:
            continue

        # Get existing DNs (exclude current)
        existing_dns = frappe.get_all(
            "Delivery Note Item",
            filters={"against_sales_order": so_name, "docstatus": ["!=", 2], "parent": ["!=", doc.name]},
            fields=["parent"],
            distinct=True
        )

        billed_taxes = {}
        for dn in existing_dns:
            dn_doc = frappe.get_doc("Delivery Note", dn.parent)
            for tax in dn_doc.taxes:
                if tax.charge_type == "Actual":
                    billed_taxes[tax.account_head] = billed_taxes.get(tax.account_head, 0) + (tax.tax_amount or 0)

        # Update current doc taxes
        for tax in doc.taxes:
            if tax.charge_type == "Actual" and tax.account_head in so_actual_taxes:
                so_total = so_actual_taxes[tax.account_head]["amount"]
                billed = billed_taxes.get(tax.account_head, 0)
                remaining = max(so_total - billed, 0)

                if tax.tax_amount != remaining:
                    tax.tax_amount = remaining
                    tax.base_tax_amount = remaining
                    tax.tax_amount_after_discount_amount = remaining
                    tax.base_tax_amount_after_discount_amount = remaining
                    taxes_updated = True

                    frappe.msgprint(
                        _("Updated '{0}' tax to remaining amount {1}").format(
                            tax.account_head, frappe.format_value(remaining, {"fieldtype": "Currency"})
                        ),
                        alert=True, indicator="blue"
                    )

    if taxes_updated:
        doc.calculate_taxes_and_totals()
        if doc.name and not doc.get("__islocal"):
            doc.db_update()
        frappe.msgprint(_("Actual taxes adjusted successfully"), alert=True, indicator="green")


def validate(doc, method):
    """Validate Delivery Note"""
    fetch_po_line_no_from_sales_order(doc)
    validate_duplicate_delivery_note(doc, method)
    # validate_so_line_shipping_address(doc)
    validate_free_items(doc)
    # validate_batch_from_custom_field(doc,method)
    validate_dn_line_status(doc,method)

def validate_duplicate_delivery_note(doc, method):
    """
    Prevent creating duplicate Delivery Notes (DRAFT only)
    for same batch_no + item_code + qty + customer combination.
    """
    for item in doc.items:
        if not item.custom_batch_no:
            continue

        # Look for another DRAFT Delivery Note with same details
        duplicate = frappe.db.sql(
            """
            SELECT dni.parent
            FROM `tabDelivery Note Item` dni
            INNER JOIN `tabDelivery Note` dn ON dn.name = dni.parent
            WHERE dni.custom_batch_no = %s
              AND dni.item_code = %s
              AND dni.qty = %s
              AND dn.customer = %s
              AND dn.docstatus = 0
              AND dni.parent != %s
            LIMIT 1
            """,
            (item.custom_batch_no, item.item_code, item.qty, doc.customer, doc.name),
        )

        if duplicate:
            dn_name = duplicate[0][0]
            frappe.throw(
                _(
                    f"Duplicate Draft Delivery Note found for Batch: <b>{item.custom_batch_no}</b>, "
                    f"Item: <b>{item.item_code}</b>, Qty: <b>{item.qty}</b>, "
                    f"Customer: <b>{doc.customer}</b>.<br><br>"
                    f"Existing Draft DN: <b><a href='/app/delivery-note/{dn_name}'>{dn_name}</a></b>"
                ),
                title=_("Duplicate Draft Delivery Note"),
            )


def fetch_po_line_no_from_sales_order(doc, method=None):
    """Populate po_line_no (and optionally po_no) on Delivery Note Item rows using SO linkage.

    Resolution strategy (per row):
    1) Use exact Sales Order Item row via item.so_detail -> copy po_line_no
    2) Use parent Sales Order via item.against_sales_order -> copy po_no
    """
    try:
        # Collect unique Sales Order Item row names from DN items
        so_item_names = []
        for it in (doc.items or []):
            so_detail = getattr(it, 'so_detail', None)
            if so_detail and so_detail not in so_item_names:
                so_item_names.append(so_detail)

        po_line_map = {}
        if so_item_names:
            so_items = frappe.get_all(
                'Sales Order Item',
                filters={'name': ['in', so_item_names]},
                fields=['name', 'po_line_no']
            )
            po_line_map = {row['name']: row.get('po_line_no') for row in so_items}

        # Collect unique Sales Orders from DN items
        so_names = []
        for it in (doc.items or []):
            so_name = getattr(it, 'against_sales_order', None)
            if so_name and so_name not in so_names:
                so_names.append(so_name)

        po_no_map = {}
        if so_names:
            so_rows = frappe.get_all(
                'Sales Order',
                filters={'name': ['in', so_names]},
                fields=['name', 'po_no']
            )
            po_no_map = {row['name']: row.get('po_no') for row in so_rows}

        # Set values on each DN item
        for it in (doc.items or []):
            so_detail = getattr(it, 'so_detail', None)
            so_name = getattr(it, 'against_sales_order', None)

            if hasattr(it, 'po_line_no') and so_detail and so_detail in po_line_map:
                it.po_line_no = po_line_map[so_detail]

            

    except Exception as e:
        frappe.log_error('DN Fetch PO Line No', f'Error populating po_line_no on DN {getattr(doc, "name", "Unsaved")}: {str(e)}')




def validate_free_items(doc):
    """
    Ensure that if SO has free items (component_of),
    those free items must be present in Delivery Note.
    """

    # Collect all linked Sales Orders from DN items
    so_names = set(
        d.against_sales_order
        for d in doc.items
        if d.against_sales_order
    )

    if not so_names:
        return

    # DN item codes for quick lookup
    dn_item_codes = {d.item_code for d in doc.items}

    missing_items = []

    for so_name in so_names:
        so = frappe.get_doc("Sales Order", so_name)

        # Find free items in SO
        free_items = [
            so_item
            for so_item in so.items
            if so_item.is_free_item and so_item.component_of
        ]

        for free_item in free_items:
            # If free item not present in DN
            if free_item.item_code not in dn_item_codes:
                missing_items.append({
                    "free_item": free_item.item_code,
                    "parent_item": free_item.component_of,
                    "so": so_name
                })

    if missing_items:
        message = "<b>Missing Free Items in Delivery Note</b><br><br>"
        for m in missing_items:
            message += (
                f"• Free Item <b>{m['free_item']}</b> "
                f"linked with <b>{m['parent_item']}</b> "
                f"in Sales Order <b>{m['so']}</b><br>"
            )

        frappe.throw(_(message), title=_("Free Item Validation Failed"))


@frappe.whitelist()
def get_stock_items_and_batch_qty(items, posting_date=None, posting_time=None):
    """
    Check if items are stock items and get batch-wise stock quantities.
    
    Args:
        items: List of dicts with item_code, warehouse, batch_no, qty, name, item_name
        posting_date: Optional posting date for stock calculation
        posting_time: Optional posting time for stock calculation
    
    Returns:
        dict with items_data containing is_stock_item, batch_no, available_qty for each item
    """
    from erpnext.stock.doctype.batch.batch import get_batch_qty
    
    if isinstance(items, str):
        items = frappe.parse_json(items)
    
    if not items:
        return {"items_data": {}}
    
    # Get all unique item codes
    item_codes = list(set([item.get('item_code') for item in items if item.get('item_code')]))
    
    # Fetch is_stock_item for all items in one query
    item_stock_map = {}
    if item_codes:
        item_data = frappe.db.sql("""
            SELECT name, is_stock_item
            FROM `tabItem`
            WHERE name IN %s
        """, (item_codes,), as_dict=True)
        
        item_stock_map = {row.name: row.is_stock_item for row in item_data}
    
    items_data = {}
    
    for item in items:
        item_code = item.get('item_code')
        warehouse = item.get('warehouse')
        batch_no = item.get('batch_no')
        item_name = item.get('name')  # DN item name (can be temporary name for new rows)
        
        if not item_code:
            continue
        
        # Use a unique key - if item_name doesn't exist, create one based on index
        if not item_name:
            item_name = f"item_{len(items_data)}"
        
        is_stock_item = item_stock_map.get(item_code, 0)
        available_qty = None
        batch_no_used = None
        
        # Only check stock for stock items with warehouse
        if is_stock_item and warehouse:
            batch_no_used = batch_no
            
            try:
                if batch_no:
                    # Get batch-wise stock quantity
                    available_qty = get_batch_qty(
                        batch_no=batch_no,
                        warehouse=warehouse,
                        item_code=item_code,
                        posting_date=posting_date,
                        posting_time=posting_time
                    )
                    # get_batch_qty returns a float when batch_no and warehouse are provided
                    if available_qty is None:
                        available_qty = 0
                    available_qty = flt(available_qty)
                else:
                    # Get general stock quantity from Bin
                    available_qty = flt(frappe.db.get_value(
                        "Bin",
                        {"item_code": item_code, "warehouse": warehouse},
                        "actual_qty"
                    ) or 0)
            except Exception as e:
                frappe.log_error(
                    f"Error getting stock for item {item_code}, batch {batch_no}, warehouse {warehouse}: {str(e)}",
                    "get_stock_items_and_batch_qty"
                )
                available_qty = 0
        
        items_data[item_name] = {
            "is_stock_item": is_stock_item,
            "batch_no": batch_no_used,
            "available_qty": available_qty
        }
    
    return {"items_data": items_data}


def validate_batch_from_custom_field(doc, method):
    for item in doc.items:
        # Check both custom_batch_no and batch_no
        batch_to_validate = item.batch_no or item.custom_batch_no
        
        if not batch_to_validate:
            continue  # Skip if no batch
            
       
        
        # 1️⃣ Check Batch Exists
        batch_doc = frappe.db.get_value(
            "Batch",
            batch_to_validate,
            ["name", "item", "disabled"],
            as_dict=True
        )

        if not batch_doc:
            frappe.throw(
                _("Row {0}: Batch {1} does not exist.")
                .format(item.idx, batch_to_validate)
            )

        # 2️⃣ Check Item Match (Filter 1: Item Code)
        if batch_doc.item != item.item_code:
            frappe.throw(
                _("Row {0}: Batch {1} does not belong to Item {2}. Cannot use this batch.")
                .format(item.idx, batch_to_validate, item.item_code)
            )

        # 3️⃣ Check Disabled
        if batch_doc.disabled:
            frappe.throw(
                _("Row {0}: Batch {1} is disabled and cannot be used.")
                .format(item.idx, batch_to_validate)
            )

        # 4️⃣ CRITICAL: Check Stock Availability (Filter 2: Warehouse + Posting Date)
        # This is what enforces the dropdown filter logic
        batch_qty = get_batch_qty(
            batch_no=batch_to_validate,
            warehouse=item.warehouse,
            posting_date=doc.posting_date,
            posting_time=doc.posting_time
        )

        # If batch_qty is 0 or negative, batch is NOT in dropdown
        if batch_qty <= 0:
            frappe.throw(
                _("Row {0}: Batch {1} is not available in Warehouse {2} on {3}. "
                  "This batch is not allowed for this transaction.")
                .format(
                    item.idx, 
                    batch_to_validate, 
                    item.warehouse,
                    frappe.format(doc.posting_date, {'fieldtype': 'Date'})
                )
            )

        # 5️⃣ Check Sufficient Quantity
        if batch_qty < item.qty:
            frappe.throw(
                _("Row {0}: Batch {1} has insufficient stock. "
                  "Available: {2}, Required: {3}")
                .format(item.idx, batch_to_validate, batch_qty, item.qty)
            )


def validate_dn_line_status(doc, method=None):
    for item in doc.items:
        # If item not linked with Sales Order Item, skip
        if not item.so_detail:
            continue

        # Fetch line_status from Sales Order Item
        line_status = frappe.db.get_value(
            "Sales Order Item",
            item.so_detail,
            "line_status"
        )

        # If line_status has any value, block
        if line_status:
            frappe.throw(
                f"Row {item.idx}: Item {item.item_code} cannot be delivered "
                f"because Sales Order line has status '{line_status}'."
            )

def handle_free_issue_item(doc,method=None):
    mismatch_rows = []

    # ── Step 1: Loop through all DN items ────────────────────────
    for item in doc.items:

        # Only check free items that have a linked SO child row
        if not item.is_free_item:
            continue

        if not item.so_detail:
            continue

        # ── Step 2: Fetch the linked Sales Order Item row ────────
        so_item = frappe.db.get_value(
            "Sales Order Item",
            item.so_detail,
            ["name", "parent", "qty", "delivered_qty", "item_code"],
            as_dict=True
        )

        if not so_item:
            # SO row not found — treat as mismatch (safe-fail)
            mismatch_rows.append({
                "so_id"         : item.against_sales_order or "—",
                "item_code"     : item.item_code or item.item_code,
                "so_qty"        : "—",
                "so_del_qty"    : "—",
                "so_remaining"  : "—",
                "dn_qty"        : flt(item.qty),
                "error"         : True
            })
            continue

        so_qty        = flt(so_item.qty)
        so_del_qty    = flt(so_item.delivered_qty)
        so_remaining  = so_qty - so_del_qty
        dn_qty        = flt(item.qty)

        # ── Step 3: Compare remaining SO qty with DN qty ─────────
        if so_remaining != dn_qty:
            mismatch_rows.append({
                "so_id"         : item.against_sales_order or so_item.parent,
                "item_code"     : item.item_code or so_item.item_code,
                "so_qty"        : so_qty,
                "so_del_qty"    : so_del_qty,
                "so_remaining"  : so_remaining,
                "dn_qty"        : dn_qty,
                "error"         : False
            })


    # ── Step 4: If mismatches found — build table and block submit ──
    if mismatch_rows:

        # --- Build table rows ---
        th = "padding:8px 12px; border:1px solid #d1d8dd; background:#f5f7fa; font-weight:600; color:#3d4349;"
        td = "padding:8px 12px; border:1px solid #d1d8dd;"
        td_center = td + " text-align:center;"

        header_html = f"""
            <tr>
                <th style="{th}">Sales Order</th>
                <th style="{th}">Item Code</th>
                <th style="{th} text-align:center;">SO Qty</th>
                <th style="{th} text-align:center;">SO Delivered Qty</th>
                <th style="{th} text-align:center;">Remaining<br><small>(SO Qty − Delivered)</small></th>
                <th style="{th} text-align:center;">DN Qty</th>
                
            </tr>
        """

        rows_html = ""
        for row in mismatch_rows:
            rows_html += f"""
                <tr>
                    <td style="{td}">{row["so_id"]}</td>
                    <td style="{td}">{row["item_code"]}</td>
                    <td style="{td_center}">{row["so_qty"]}</td>
                    <td style="{td_center}">{row["so_del_qty"]}</td>
                    <td style="{td_center} font-weight:700; color:#e2401c;">{row["so_remaining"]}</td>
                    <td style="{td_center}">{row["dn_qty"]}</td>
                    
                </tr>
            """

        # --- Assemble full message ---

        message = f"""
            <style>
                .msgprint-dialog .modal-dialog {{
                    max-width : 90vw  !important;
                    width     : 90vw  !important;
                    margin    : 30px auto !important;
                }}
                .msgprint-dialog .modal-body {{
                    max-height : 65vh !important;
                    overflow-y : auto !important;
                    padding    : 20px !important;
                }}
            </style>

            <p style="color:#e2401c; font-weight:600; font-size:15px; margin-bottom:16px;">
                Submission Blocked — {len(mismatch_rows)} free item(s) have a quantity mismatch.
            </p>

            <div style="overflow-x:auto; width:100%;">
                <table style="
                    table-layout    : fixed;
                    width           : 100%;
                    border-collapse : collapse;
                    font-size       : 13px;
                    font-family     : Arial, sans-serif;
                    word-wrap       : break-word;
                ">
                    <colgroup>
                        <col style="width:20%;">  
                        <col style="width:30%;">  
                        <col style="width:10%;">  
                        <col style="width:15%;">  
                        <col style="width:15%;">  
                        <col style="width:10%;">  
                    </colgroup>
                    <thead>{header_html}</thead>
                    <tbody>{rows_html}</tbody>
                </table>
            </div>

            <p style="
                margin-top:16px; background:#fff8e1;
                border-left:4px solid #f0ad4e;
                padding:10px 16px; font-size:13px;
                border-radius:4px; text-align:center;
            ">
                <strong>Rule:</strong> For every free item,
                <code>SO Qty &minus; SO Delivered Qty</code> must equal
                <code>DN Qty</code> before submission.
            </p>
        """

        # ── Step 5: Throw error — blocks submit, shows popup ─────
        frappe.throw(
            title = "Free Item Quantity Mismatch — Submit Blocked",
            msg   = message,
          
        )
