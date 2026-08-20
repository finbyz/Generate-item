import frappe
import json
from erpnext.controllers.stock_controller import make_quality_inspections as original_make_qis
from frappe.utils import flt
from frappe import _
from frappe.model.mapper import get_mapped_doc


@frappe.whitelist()
def make_purchase_receipt(source_name, target_doc=None, args=None):
    """
    PO -> PR override (Create button + Get Items, same function backs both).

    WHY THE OLD CODE FAILED:
    Calling erpnext's core make_purchase_receipt() first means its own internal
    `condition` (pending_qty > 0 only) has ALREADY dropped every Service Item
    sitting at 0 pending qty before this function even sees `pr.items`. No
    post-processing afterward can restore a row that was never mapped in the
    first place. Fix: call get_mapped_doc() ourselves with a custom condition.

    RULE (per requirement):
      - Stock Items: unaffected, standard pending-qty logic.
      - Service/Non-stock Items: if Buying Settings.include_service_items_in_pending_pr
        is enabled AND any Stock Item on this PO has pending_qty_in_stock_uom > 0,
        include ALL non-stock items at qty 0, regardless of their own pending qty.
        Once every Stock Item is fully received, non-stock items are excluded.
      - Setting disabled: pure standard ERPNext behaviour, no override.
    """

    include_service_items = frappe.db.get_single_value(
        "Buying Settings", "include_service_items_in_pending_purchase_receipt"
    )
    frappe.log_error("include_service_items_in_pending_purchase_receipt pr creaation is call")

    po_doc = frappe.get_doc("Purchase Order", source_name)

    stock_item_flags = {}  # item_code -> is_stock_item, cached for this call

    def is_stock_item(item_code):
        val = stock_item_flags.get(item_code)
        if val is None:
            val = bool(frappe.db.get_value("Item", item_code, "is_stock_item"))
            stock_item_flags[item_code] = val
        return val

    def pending_qty_in_stock_uom(row):
        cf = flt(row.conversion_factor) or 1.0
        return (flt(row.qty) - flt(row.received_qty)) * cf

    # Is ANY Stock Item on this PO still pending, measured in stock UOM?
    any_stock_item_pending = False
    if include_service_items:
        for row in po_doc.items:
            if is_stock_item(row.item_code):
                if pending_qty_in_stock_uom(row) > 0:
                    any_stock_item_pending = True
                    break

    # PO Item row names included purely as a non-stock item riding along -
    # must survive the final qty>0 filter later even though qty = 0.
    service_ride_along = set()

    def condition(doc):
        # doc = Purchase Order Item row being evaluated for inclusion
        if is_stock_item(doc.item_code):
            # Stock Items: always standard behaviour, never touched.
            return pending_qty_in_stock_uom(doc) > 0

        if not include_service_items:
            return pending_qty_in_stock_uom(doc) > 0  # setting OFF -> standard
        
        if pending_qty_in_stock_uom(doc) > 0:
            return True

        # Non-stock item, setting ON: own pending qty is irrelevant.
        if any_stock_item_pending:
            service_ride_along.add(doc.name)
            return True
        return False

    def update_item(source, target, source_parent):
        pending = pending_qty_in_stock_uom(source)
        cf = flt(source.conversion_factor) or 1.0
        target.qty = (pending / cf) if pending > 0 else 0
        target.stock_qty = target.qty * cf
        target.amount = target.qty * flt(source.rate)
        target.base_amount = target.amount * flt(source_parent.conversion_rate)

    doc = get_mapped_doc(
        "Purchase Order",
        source_name,
        {
            "Purchase Order": {
                "doctype": "Purchase Receipt",
                "field_map": {
                    "party_account_currency": "party_account_currency",
                    "supplier_warehouse": "supplier_warehouse",
                },
                "validation": {"docstatus": ["=", 1]},
            },
            "Purchase Order Item": {
                "doctype": "Purchase Receipt Item",
                "field_map": {
                    "name": "purchase_order_item",
                    "parent": "purchase_order",
                    "bom": "bom",
                    "material_request": "material_request",
                    "material_request_item": "material_request_item",
                },
                "postprocess": update_item,
                "condition": condition,
            },
            "Purchase Taxes and Charges": {
                "doctype": "Purchase Taxes and Charges",
                "add_if_empty": True,
            },
        },
        target_doc,
    )

    # ---- Draft-PR-aware remaining qty + custom_batch_no carry-over ----
    items_to_keep = []
    for item in doc.items or []:
        po_item_name = getattr(item, "purchase_order_item", None)
        if not po_item_name:
            items_to_keep.append(item)
            continue

        po_item = frappe.db.get_value(
            "Purchase Order Item",
            po_item_name,
            ["qty", "received_qty", "conversion_factor", "custom_batch_no", "stock_qty"],
            as_dict=True,
        )
        if not po_item:
            items_to_keep.append(item)
            continue

        po_qty = flt(po_item.qty)
        received_qty = flt(po_item.received_qty)
        po_cf = flt(po_item.conversion_factor) or 1.0

        base_remaining_stock_qty = max(po_qty - received_qty, 0) * po_cf

        draft_pr_stock_qty = frappe.db.sql(
            """
            SELECT COALESCE(SUM(pri.stock_qty), 0)
            FROM `tabPurchase Receipt Item` pri
            INNER JOIN `tabPurchase Receipt` pr ON pri.parent = pr.name
            WHERE pr.docstatus = 0
              AND pri.purchase_order_item = %s
            """,
            (po_item_name,),
        )[0][0]

        remaining_stock_qty = max(base_remaining_stock_qty - flt(draft_pr_stock_qty), 0)

        item_cf = flt(getattr(item, "conversion_factor", None)) or 1.0
        new_qty = remaining_stock_qty / item_cf if item_cf else 0

        item.qty = new_qty
        item.stock_qty = remaining_stock_qty
        if po_item.stock_qty:
            item.qty_in_stock_uom = po_item.stock_qty

        if po_item.custom_batch_no and not getattr(item, "batch_no", None):
            item.batch_no = po_item.custom_batch_no

        # Keep the row if it has real remaining qty, OR it's a non-stock item
        # deliberately included at qty 0 because a Stock Item is still pending.
        if (new_qty and new_qty > 0) or (po_item_name in service_ride_along):
            items_to_keep.append(item)

    if doc.items is not None:
        doc.items = items_to_keep

    return doc


def before_save(doc, method):
    for item in doc.items:
        if not item.po_qty:
            # Fetch PO qty and line number
            po_doc = frappe.get_doc("Purchase Order", item.purchase_order)
            for po_item in po_doc.items:
                if po_item.item_code == item.item_code and item.purchase_order_item == po_item.name :
                    item.po_qty = po_item.qty
                    item.po_line_no = po_item.idx
                    break

        # Get branch from item row
        branch = item.branch

        # Fetch warehouses linked to this branch and marked as raw_material_warehouse and stock_warehouse
        warehouses = frappe.get_all(
            "Warehouse",
            filters={
                "branch": branch,
                "raw_material_warehouse": 1,
                "store_warehouse": 1
            },
            pluck="name"
        )

        if warehouses:
            # Sum projected_qty from Bin for the item in these warehouses
            total_projected_qty = frappe.get_all(
                "Bin",
                filters={
                    "item_code": item.item_code,
                    "warehouse": ["in", warehouses]
                },
                fields=["sum(projected_qty) as total"]
            )
            item.on_hand_qty = total_projected_qty[0].total or 0
        else:
            item.on_hand_qty = 0


@frappe.whitelist()
def get_po_items(purchase_order):
    po_doc = frappe.get_doc("Purchase Order", purchase_order)
    return po_doc


def validate(doc, method):
    validate_duplicate_po(doc, method)
    validate_is_return(doc,method)
   



def validate_is_return(self,method):
    if self.is_return:
        for item in self.items:
            # If stock_qty is positive, make it negative
            if item.stock_qty > 0:
                item.stock_qty = -item.stock_qty
            
            # If qty_in_stock_uom is positive, make it negative
            if item.qty_in_stock_uom > 0:
                item.qty_in_stock_uom = -item.qty_in_stock_uom


def validate_duplicate_po(doc, method):
    """Prevent duplicate draft Purchase Orders for same supplier, item, and qty."""

    for item in doc.items:
        if not item.custom_batch_no:
            continue

        # Look for another DRAFT Delivery Note with same details
        duplicate = frappe.db.sql(
            """
            SELECT dni.parent
            FROM `tabPurchase Receipt Item` dni
            INNER JOIN `tabPurchase Receipt` dn ON dn.name = dni.parent
            WHERE dni.custom_batch_no = %s
              AND dni.item_code = %s
              AND dni.qty = %s
              AND dn.supplier = %s
              AND dn.docstatus = 0
              AND dni.parent != %s
            LIMIT 1
            """,
            (item.custom_batch_no, item.item_code, item.qty, doc.supplier, doc.name),
        )

        if duplicate:
            dn_name = duplicate[0][0]
            frappe.throw(
                (
                    f"Duplicate Draft Purchase Receipt found for Batch: <b>{item.custom_batch_no}</b>, "
                    f"Item: <b>{item.item_code}</b>, Qty: <b>{item.qty}</b>, "
                    f"Supplier: <b>{doc.supplier}</b>.<br><br>"
                    f"Existing Draft Purchase Receipt: <b><a href='/app/purchase-receipt/{dn_name}'>{dn_name}</a></b>"
                ),
                title=("Duplicate Draft Purchase Receipt Detected")
            )

def make_qc(doctype, docname, items):
    if isinstance(items, str):
        items = json.loads(items)


    SERIES_MAP = {
        "Sanand":    "MQIS.fiscal.#####",
        "Rabale":    "MQIR.fiscal.#####",
        "Nandikoor": "MQIN.fiscal.#####",
    }
    branch = frappe.db.get_value(doctype, docname, "branch")


    inspections = []
    for item in items:
        if flt(item.get("sample_size")) > flt(item.get("qty")):
            frappe.throw(
                _(
                    "{item_name}'s Sample Size ({sample_size}) cannot be greater than the Accepted Quantity ({accepted_quantity})"
                ).format(
                    item_name=item.get("item_name"),
                    sample_size=item.get("sample_size"),
                    accepted_quantity=item.get("qty"),
                )
            )
        quality_inspection = frappe.get_doc(
            {
                "doctype": "Quality Inspection",
                "inspection_type": "Incoming",
                "inspected_by": frappe.session.user,
                "reference_type": doctype,
                "reference_name": docname,
                "branch":branch,
                "naming_series": SERIES_MAP.get(branch),
                "item_code": item.get("item_code"),
                "description": item.get("description"),
                "sample_size": flt(item.get("sample_size")),
                "item_serial_no": item.get("serial_no").split("\n")[0] if item.get("serial_no") else None,
                "batch_no": item.get("batch_no"),
                "child_row_reference": item.get("child_row_reference"),
            }
        )
        quality_inspection.save()
        inspections.append(quality_inspection.name)

    return inspections
            
@frappe.whitelist()
def make_quality_inspections(doctype, docname, items):

    if isinstance(items, str):
        items = json.loads(items)

    existing_qis = []
    items_to_process = []
    existing_items_map = {}  # Map to store QI name -> item code
    for item in items:
        existing_qi = frappe.db.exists(
            "Quality Inspection",
            {
                "reference_type": doctype,
                    "reference_name": docname,
                    "item_code": item.get("item_code"),
                    "docstatus": ["in", [0, 1]]
                }
            )
        
        if existing_qi:
            existing_qis.append(existing_qi)
            existing_items_map[existing_qi] = item.get("item_code")  # Store mapping
        else:
            items_to_process.append(item)

    if existing_qis:
        for qi in existing_qis:
            item_code = existing_items_map.get(qi)
            frappe.msgprint(
                (f"Quality Inspection <b>{qi}</b> already exist for this <b>{item_code}</b>.")
            )
            continue
        

   

    # inspection_names = original_make_qis(doctype, docname, items)
    inspection_names = make_qc(doctype, docname, items_to_process)
    

    qi_map = {
        frappe.db.get_value("Quality Inspection", qi, "child_row_reference"): qi
        for qi in inspection_names
    }

    for item in items:
        ref = item.get("child_row_reference")
        if not ref:
            continue

        qi_name = qi_map.get(ref)
        if not qi_name:
            continue

        is_subcontracting = doctype == "Subcontracting Receipt"
        # Fetch data from Purchase Receipt Item
        if is_subcontracting:
            row = frappe.db.get_value(
                doctype + " Item",
                ref,
                ["qty", "stock_uom"],
                as_dict=True
            )
        else:
            row = frappe.db.get_value(
                doctype + " Item",
                ref,
                [
                "qty",
                "uom",
                "stock_uom",
                "stock_qty",
                "custom_batch_no",
                "custom_drawing_no",
                "custom_drawing_rev_no",
                "custom_pattern_drawing_no",
                "custom_pattern_drawing_rev_no",
                "custom_purchase_specification_no",
                "custom_purchase_specification_rev_no",
        ],
                as_dict=True
            )
        if not row:
            continue


        qty = flt(row.qty)
        uom = row.uom
        stock_uom = row.stock_uom

        if is_subcontracting:
            update_values = {
                "received_qty": qty,
                "sample_size": qty,
                "stock_uom": stock_uom,
            }
        else:
            received_qty_in_stock_uom = flt(row.stock_qty)
            update_values = {
                "received_qty": qty,
                "sample_size": qty,
                "uom": uom,
                "stock_uom": stock_uom,
                "received_qty_in_stock_uom": received_qty_in_stock_uom,
                "sample_size_in_stock_uom": received_qty_in_stock_uom,
                "batch_no_ref":row.custom_batch_no,
                "custom_drawing_no": row.custom_drawing_no,
                "custom_drawing_rev_no": row.custom_drawing_rev_no,
                "custom_pattern_drawing_no": row.custom_pattern_drawing_no,
                "custom_pattern_drawing_rev_no": row.custom_pattern_drawing_rev_no,
                "custom_purchase_specification_no": row.custom_purchase_specification_no,
                "custom_purchase_specification_rev_no": row.custom_purchase_specification_rev_no,
            }
            
            

        frappe.db.set_value(
            "Quality Inspection",
            qi_name,
            update_values
        )

    return inspection_names

def update_received_qty_stock_uom(doc, method):
    po_names = set()
    for item in doc.items:
        if not item.purchase_order or not item.purchase_order_item:
            continue

        po_item = frappe.get_doc("Purchase Order Item", item.purchase_order_item)
        if item.received_stock_qty :
            update_po_item_received_stock_qty(item.purchase_order_item)
            
   
        calculate_pending_qty(item)
        po_names.add(item.purchase_order)

    # After all items are processed, update per_received on each linked PO
    for po_name in po_names:
        try:
            po = frappe.get_doc("Purchase Order", po_name)

            po.update_receiving_percentage()
            po.set_status(update=True)

        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                f"update_receiving_percentage failed for PO {po_name}"
            )   



def update_po_item_received_stock_qty(purchase_order_item):
    if not purchase_order_item:
        return

    # Get total received stock qty from submitted Purchase Receipt Items
    result = frappe.db.get_all(
        "Purchase Receipt Item",
        filters={
            "purchase_order_item": purchase_order_item,
            "docstatus": 1,
        },
        fields=[{"SUM": "stock_qty", "as": "total_received"}],
    )

    total_received = (
        flt(result[0].get("total_received"))
        if result
        else 0.0
    )

    # Update Purchase Order Item
    frappe.db.set_value(
        "Purchase Order Item",
        purchase_order_item,
        "received_qty_in_stock_uom",
        total_received,
        update_modified=False,
    )

def calculate_pending_qty(item):
    if not item.purchase_order_item:
        return

    # Get Purchase Order Item stock_qty
    po_item = frappe.db.get_value(
        "Purchase Order Item",
        item.purchase_order_item,
        ["stock_qty"],
        as_dict=True
    )

    if not po_item:
        return

    po_stock_qty = flt(po_item.stock_qty)

    # Sum stock_qty from submitted Purchase Receipt Items
    received_qty = frappe.db.sql("""
        SELECT SUM(pri.stock_qty)
        FROM `tabPurchase Receipt Item` pri
        INNER JOIN `tabPurchase Receipt` pr
            ON pr.name = pri.parent
        WHERE
            pri.purchase_order_item = %s
            AND pr.docstatus = 1
    """, (item.purchase_order_item,))[0][0] or 0

    received_qty = flt(received_qty)

    # Calculate pending quantity
    pending_qty = po_stock_qty - received_qty
    if pending_qty < 0:
        pending_qty = 0

    # Update the Purchase Order Item field
    frappe.db.set_value(
        "Purchase Order Item",
        item.purchase_order_item,
        "pending_qty_in_stock_uom",
        pending_qty
    )

@frappe.whitelist()
def get_pending_qty(po_item_name):
    if not po_item_name:
        return 0

    return frappe.db.get_value(
        "Purchase Order Item",
        po_item_name,
        "pending_qty_in_stock_uom"
    )
