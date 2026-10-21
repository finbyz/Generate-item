import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt, getdate, nowdate, escape_html
from erpnext.stock.doctype.item.item import get_item_defaults
from generate_item.utils.scenario_workflow import validate_material_request_create
from erpnext.stock.doctype.material_request.material_request import make_stock_entry


def validate(doc,method):
    validate_duplicate_mr(doc, method)
    if doc.custom_batch_no:
        for row in doc.items:
            row.db_set("custom_batch_no", doc.custom_batch_no)

def before_insert(doc, method=None):
    # frappe.log_error("before_insert MR")
    """Run only when creating new Material Request"""
    populate_custom_fields(doc)
    validate_material_request_create(doc, method)

from collections import defaultdict
from frappe.utils import cint

def check_material_transfer_stock_availability(doc):
    """
    Check stock availability for items in a Material Transfer request.
    Returns a list of dicts for items with insufficient stock in their source warehouse:
    [
        {
            "item_code": str,
            "warehouse": str,
            "required_qty": float,
            "available_qty": float
        },
        ...
    ]
    """
    from erpnext.stock.stock_ledger import is_negative_stock_allowed
    from erpnext.stock.utils import get_stock_balance

    required_by_item_wh = defaultdict(float)
    default_from_wh = getattr(doc, "set_from_warehouse", None)

    for item in doc.items:
        source_wh = getattr(item, "from_warehouse", None) or default_from_wh
        if item.item_code and source_wh:
            qty = flt(getattr(item, "stock_qty", None) or getattr(item, "qty", 0))
            if qty > 0:
                required_by_item_wh[(item.item_code, source_wh)] += qty

    insufficient_items = []
    for (item_code, source_wh), required_qty in required_by_item_wh.items():
        is_stock_item = frappe.db.get_value("Item", item_code, "is_stock_item")
        if not is_stock_item:
            continue

        if is_negative_stock_allowed(item_code=item_code):
            continue

        available_qty = flt(get_stock_balance(item_code, source_wh))
        if available_qty < required_qty:
            insufficient_items.append({
                "item_code": item_code,
                "warehouse": source_wh,
                "required_qty": required_qty,
                "available_qty": available_qty,
            })

    return insufficient_items


def format_insufficient_stock_message(insufficient_items, se_name=None):
    """
    Format a clear, user-facing message detailing the affected item(s),
    source warehouse, required quantity, and available quantity,
    along with reference to the Stock Entry created in Draft mode.
    """
    if not insufficient_items:
        return ""

    se_link = frappe.utils.get_link_to_form("Stock Entry", se_name) if se_name else _("Stock Entry")

    if len(insufficient_items) == 1:
        item = insufficient_items[0]
        return _(
            "Stock Entry {0} was created in <b>Draft</b> mode and was not submitted for item <b>{1}</b> "
            "because of insufficient stock in warehouse <b>{2}</b>.<br><br>"
            "<b>Required Quantity:</b> {3}, <b>Available Quantity:</b> {4}.<br><br>"
            "Please arrange the required stock and submit the Stock Entry."
        ).format(
            se_link,
            item["item_code"],
            item["warehouse"],
            flt(item["required_qty"]),
            flt(item["available_qty"]),
        )

    # Multiple items
    lines = []
    for item in insufficient_items:
        lines.append(
            _(
                "• Item <b>{0}</b> in warehouse <b>{1}</b> — Required Quantity: {2}, Available Quantity: {3}"
            ).format(
                item["item_code"],
                item["warehouse"],
                flt(item["required_qty"]),
                flt(item["available_qty"]),
            )
        )
    return _(
        "Stock Entry {0} was created in <b>Draft</b> mode and was not submitted because of "
        "insufficient stock in source warehouse(s):<br><br>{1}<br><br>"
        "Please arrange the required stock and submit the Stock Entry."
    ).format(se_link, "<br>".join(lines))


@frappe.whitelist()
def has_submitted_stock_entry(material_request):
    """Check if a submitted Stock Entry already exists for this Material Request."""
    return bool(
        frappe.db.exists(
            "Stock Entry Detail",
            {"material_request": material_request, "docstatus": 1},
        )
    )


@frappe.whitelist()
def create_stock_entry_for_material_transfer(material_request, submit=1):
    """
    Create Stock Entry for a Material Transfer request.
    If stock is sufficient, submits the Stock Entry.
    If stock is insufficient, keeps the Stock Entry in DRAFT mode, provides a clear reference link,
    creates an Error Log, and informs the user.
    """
    if isinstance(material_request, str):
        doc = frappe.get_doc("Material Request", material_request)
    else:
        doc = material_request

    if doc.material_request_type != "Material Transfer":
        return None

    # 1. Prevent duplicate Stock Entries if an appropriate submitted Stock Entry exists
    if has_submitted_stock_entry(doc.name):
        submitted_se = frappe.db.get_value(
            "Stock Entry Detail",
            {"material_request": doc.name, "docstatus": 1},
            "parent",
        )
        frappe.msgprint(
            _("Stock Entry {0} has already been submitted for Material Request {1}.").format(
                frappe.utils.get_link_to_form("Stock Entry", submitted_se),
                doc.name,
            ),
            alert=True,
        )
        return submitted_se

    savepoint_name = f"se_mt_{frappe.generate_hash(length=8)}"
    frappe.db.savepoint(savepoint_name)

    se = None
    try:
        # 2. Check if an existing draft Stock Entry is already linked to avoid duplicate drafts
        existing_draft = frappe.db.get_value(
            "Stock Entry Detail",
            {"material_request": doc.name, "docstatus": 0},
            "parent",
        )
        if existing_draft:
            se = frappe.get_doc("Stock Entry", existing_draft)
        else:
            se = make_stock_entry(doc.name)
            se.stock_entry_type = "Material Transfer"
            se.purpose = "Material Transfer"
            se.company = doc.company

            # Ensure zero-stock / missing valuation rate items allow zero valuation rate so draft can be created
            for row in se.items:
                if not flt(row.basic_rate):
                    rate = (
                        frappe.db.get_value("Item", row.item_code, "valuation_rate")
                        or frappe.db.get_value("Item", row.item_code, "standard_rate")
                        or frappe.db.get_value("Item", row.item_code, "last_purchase_rate")
                    )
                    if rate:
                        row.basic_rate = flt(rate)
                    else:
                        row.allow_zero_valuation_rate = 1

            se.insert(ignore_permissions=True)

        # 3. Check stock availability
        insufficient_items = check_material_transfer_stock_availability(doc)
        if insufficient_items:
            frappe.db.release_savepoint(savepoint_name)
            msg = format_insufficient_stock_message(insufficient_items, se_name=se.name)
            frappe.log_error(
                title=_("Insufficient Stock for Stock Entry {0}").format(se.name),
                message=msg,
            )
            frappe.msgprint(msg, title=_("Insufficient Stock (Saved as Draft)"), indicator="orange")
            return se.name

        if not cint(submit):
            frappe.db.release_savepoint(savepoint_name)
            frappe.msgprint(
                _("Stock Entry {0} created in Draft mode for Material Transfer").format(
                    frappe.utils.get_link_to_form("Stock Entry", se.name)
                ),
                alert=True,
            )
            return se.name

        # 4. Attempt submission inside a nested savepoint
        sub_savepoint = f"se_sub_{frappe.generate_hash(length=8)}"
        frappe.db.savepoint(sub_savepoint)

        try:
            se.submit()
            frappe.db.release_savepoint(sub_savepoint)
            frappe.db.release_savepoint(savepoint_name)

            frappe.msgprint(
                _("Stock Entry {0} created and submitted for Material Transfer").format(
                    frappe.utils.get_link_to_form("Stock Entry", se.name)
                ),
                alert=True,
            )
            return se.name

        except Exception as submit_err:
            # Roll back submit attempt only; release outer savepoint so draft SE stays saved
            frappe.db.rollback(save_point=sub_savepoint)
            frappe.db.release_savepoint(savepoint_name)
            raise submit_err

    except Exception as e:
        frappe.db.rollback(save_point=savepoint_name)

        stock_error_types = ()
        try:
            from erpnext.stock.stock_ledger import NegativeStockError
            stock_error_types += (NegativeStockError,)
        except ImportError:
            pass

        try:
            from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import (
                BatchNegativeStockError,
            )
            stock_error_types += (BatchNegativeStockError,)
        except ImportError:
            pass

        insufficient_after = check_material_transfer_stock_availability(doc)
        error_str = str(e).lower()
        is_stock_error = (
            (stock_error_types and isinstance(e, stock_error_types))
            or bool(insufficient_after)
            or "insufficient stock" in error_str
            or "not available" in error_str
            or "negative stock" in error_str
        )

        se_name = se.name if se and hasattr(se, "name") else None

        if is_stock_error:
            if not insufficient_after:
                insufficient_after = check_material_transfer_stock_availability(doc)

            if insufficient_after:
                msg = format_insufficient_stock_message(insufficient_after, se_name=se_name)
            else:
                se_link = frappe.utils.get_link_to_form("Stock Entry", se_name) if se_name else _("Stock Entry")
                msg = _(
                    "Stock Entry {0} was created in <b>Draft</b> mode and was not submitted because of "
                    "insufficient stock in source warehouse. Please arrange the required stock and submit the Stock Entry."
                ).format(se_link)

            frappe.log_error(
                title=_("Insufficient Stock for Stock Entry {0}").format(se_name or doc.name),
                message=f"{msg}\n\nTechnical details:\n{frappe.get_traceback() or str(e)}",
            )
            frappe.msgprint(msg, title=_("Insufficient Stock (Saved as Draft)"), indicator="orange")
        else:
            frappe.log_error(
                title=_("Stock Entry Submission Failed - {0}").format(se_name or doc.name),
                message=frappe.get_traceback() or str(e),
            )
            se_link = frappe.utils.get_link_to_form("Stock Entry", se_name) if se_name else ""
            if se_link:
                general_msg = _(
                    "Stock Entry {0} was created in <b>Draft</b> mode, but could not be submitted due to an error: {1}. "
                    "Please review the document or check the system Error Log for details."
                ).format(se_link, str(e))
            else:
                general_msg = _(
                    "Stock Entry could not be created for Material Request {0} due to an error: {1}. "
                    "Please check the system Error Log for details."
                ).format(doc.name, str(e))
            frappe.msgprint(general_msg, title=_("Submission Failed"), indicator="red")

        return se_name


def on_submit(doc, method=None):
    if doc.material_request_type != "Material Transfer":
        return

    create_stock_entry_for_material_transfer(doc, submit=1)



def validate_duplicate_mr(doc, method):
    """Prevent duplicate draft Material Requests for same custom_batch_no, item, qty, and custom_drawing_no."""
    
    # Skip validation for cancelled or submitted docs
    if doc.docstatus != 0:
        return

    # Only proceed if custom_batch_no is set
    if not doc.custom_batch_no:
        return

    # Get potential duplicate MRs first (outside item loop for efficiency)
    duplicates = frappe.db.get_all(
        "Material Request",
        filters={
            "custom_batch_no": doc.custom_batch_no,
            "docstatus": 0,  # Only Draft
            "name": ["!=", doc.name],  # Exclude current
        },
        fields=["name"]
    )

    if not duplicates:
        return

    # Collect all violations
    violations = []
    for item in doc.items:
        drawing_no = item.custom_drawing_no or ""
        for d in duplicates:
            duplicate_items = frappe.db.get_all(
                "Material Request Item",
                filters={
                    "parent": d.name,
                    "item_code": item.item_code,
                    "qty": item.qty,
                    "custom_drawing_no": drawing_no,
                },
                fields=["item_code", "qty", "custom_drawing_no"]
            )
            if duplicate_items:
                violations.append({
                    "doc_name": d.name,
                    "item_code": item.item_code,
                    "qty": item.qty,
                    "batch_no": doc.custom_batch_no,
                    "drawing_no": drawing_no or 'N/A'
                })

    if violations:
        # Format a single error message with all issues
        error_msg = "<b>Multiple Duplicate Material Requests Found:</b><br><br>"
        seen_docs = {}  # To group by doc if multiple items per doc
        for v in violations:
            doc_key = v["doc_name"]
            if doc_key not in seen_docs:
                seen_docs[doc_key] = []
            seen_docs[doc_key].append(f"- Item <b>{v['item_code']}</b> (Qty: <b>{v['qty']}</b>)")
        
        for doc_name, items_list in seen_docs.items():
            error_msg += f"Existing Draft Material Request: <b><a href='/app/material-request/{doc_name}'>{doc_name}</a></b><br>"
            error_msg += f"<br>Batch No: <b>{violations[0]['batch_no']}</b><br><br>" 
            error_msg += "<br>".join(items_list)
            # Assuming same batch for all
        
        frappe.throw(_(error_msg))

# def before_save(doc, method=None):
#     """Run before saving (both insert and update)"""
#     # Only populate if fields are empty or if specific trigger conditions are met
#     if should_populate_fields(doc):
#         populate_custom_fields(doc)

# def should_populate_fields(doc):
#     """Check if we should populate custom fields"""
#     # Only populate if most custom fields are empty
#     if not doc.items:
#         return False
        
#     for item in doc.items:
#         if (not item.get('custom_drawing_no') and not item.get('custom_drawing_rev_no') and
#             not item.get('custom_pattern_drawing_no') and not item.get('custom_pattern_drawing_no') and 
#             not item.get('custom_purchase_specification_no') and not item.get('custom_purchase_specification_rev_no') and not item.get('bom_no') ):
#             return True
#     return False

def populate_custom_fields(doc):
    """Main logic to populate custom fields"""
    if not doc.items or len(doc.items) == 0:
        return
        
    # Get production plan from the first item that has it
    production_plan = None
    for item in doc.items:
        if item.production_plan:
            production_plan = item.production_plan
            break
    
    # Set batch number from production plan if available
    if production_plan:
        try:
            pp = frappe.get_doc('Production Plan', production_plan)
            if pp.po_items and len(pp.po_items) > 0 and pp.po_items[0].custom_batch_no:
                batch_no = pp.po_items[0].custom_batch_no
                branch = pp.po_items[0].branch
                
                # Only set if different to avoid unnecessary updates
                if doc.get('custom_batch_no') != batch_no:
                    doc.custom_batch_no = batch_no
                
                for item in doc.items:
                    if item.get('custom_batch_no') != batch_no:
                        item.custom_batch_no = batch_no
                        item.branch = branch
        except frappe.DoesNotExistError:
            frappe.log_error(f"Production Plan {production_plan} not found")
    
    # # Process each item in doc.items
    # for row in doc.items:
    #     if row.bom_no:
    #         try:
    #             bom = frappe.get_doc("BOM", row.bom_no)
                
    #             # If this is a finished good item, get its BOM data
    #             if row.item_code == bom.item:
    #                 # Only update if values are different
    #                 update_if_different(row, 'custom_drawing_no', bom.get('custom_drawing_no'))
    #                 update_if_different(row, 'custom_pattern_drawing_no', bom.get('custom_pattern_drawing_no'))
    #                 update_if_different(row, 'custom_purchase_specification_no', bom.get('custom_purchase_specification_no'))
    #                 update_if_different(row, 'custom_drawing_rev_no', bom.get('custom_drawing_rev_no'))
    #                 update_if_different(row, 'custom_pattern_drawing_rev_no', bom.get('custom_pattern_drawing_rev_no'))
    #                 update_if_different(row, 'custom_purchase_specification_rev_no', bom.get('custom_purchase_specification_rev_no'))
                
    #             # For BOM components (raw materials), get their item-specific data
    #             else:
    #                 set_item_data(row)
                
    #         except frappe.DoesNotExistError:
    #             frappe.log_error(f"BOM {row.bom_no} not found")
    #             # Fallback to item data if BOM not found
    #             set_item_data(row)
        
    #     else:
    #         # If no BOM, get data directly from item
    #         set_item_data(row)

# def update_if_different(row, field_name, new_value):
#     """Helper function to update field only if value is different"""
#     current_value = row.get(field_name)
#     if current_value != new_value:
#         row.set(field_name, new_value)

# def set_item_data(row):
#     """Helper function to set item data from Item master"""
#     try:
#         item_doc = frappe.get_doc("Item", row.item_code)
        
#         # Only update if values are different
#         update_if_different(row, 'custom_drawing_no', item_doc.get("custom_drawing_no"))
#         update_if_different(row, 'custom_pattern_drawing_no', item_doc.get("custom_pattern_drawing_no"))
#         update_if_different(row, 'custom_purchase_specification_no', item_doc.get("custom_purchase_specification_no"))
#         update_if_different(row, 'custom_drawing_rev_no', item_doc.get("custom_drawing_rev_no"))
#         update_if_different(row, 'custom_pattern_drawing_rev_no', item_doc.get("custom_pattern_drawing_rev_no"))
#         update_if_different(row, 'custom_purchase_specification_rev_no', item_doc.get("custom_purchase_specification_rev_no"))
#         update_if_different(row, 'custom_batch_no', item_doc.get("custom_batch_no"))
        
#     except frappe.DoesNotExistError:
#         frappe.log_error(f"Item {row.item_code} not found")

# Alternative: If you want to use the original before_validate approach with fixes
# def before_validate(doc, method=None):
#     """Fixed version of original before_validate hook"""
#     # Skip if this validation has already been run in this request
#     if hasattr(doc, '_custom_fields_updated') and doc._custom_fields_updated:
#         return
        
#     if doc.items and len(doc.items) > 0:
#         # Get production plan from the first item that has it
#         production_plan = None
#         for item in doc.items:
#             if item.production_plan:
#                 production_plan = item.production_plan
#                 break
        
#         # Set batch number from production plan if available
#         if production_plan:
#             try:
#                 pp = frappe.get_doc('Production Plan', production_plan)
#                 if pp.po_items and len(pp.po_items) > 0 and pp.po_items[0].custom_batch_no:
#                     batch_no = pp.po_items[0].custom_batch_no
                    
#                     # Only set if different to avoid unnecessary updates
#                     if doc.get('custom_batch_no') != batch_no:
#                         doc.custom_batch_no = batch_no
                    
#                     for item in doc.items:
#                         if item.get('custom_batch_no') != batch_no:
#                             item.custom_batch_no = batch_no
#             except frappe.DoesNotExistError:
#                 frappe.log_error(f"Production Plan {production_plan} not found")
        
#         # Process each item in doc.items
#         for row in doc.items:
#             if row.bom_no:
#                 try:
#                     bom = frappe.get_doc("BOM", row.bom_no)
                    
#                     # If this is a finished good item, get its BOM data
#                     if row.item_code == bom.item:
#                         # Only update if values are different
#                         update_if_different(row, 'custom_drawing_no', bom.get('custom_drawing_no'))
#                         update_if_different(row, 'custom_pattern_drawing_no', bom.get('custom_pattern_drawing_no'))
#                         update_if_different(row, 'custom_purchase_specification_no', bom.get('custom_purchase_specification_no'))
#                         update_if_different(row, 'custom_drawing_rev_no', bom.get('custom_drawing_rev_no'))
#                         update_if_different(row, 'custom_pattern_drawing_rev_no', bom.get('custom_pattern_drawing_rev_no'))
#                         update_if_different(row, 'custom_purchase_specification_rev_no', bom.get('custom_purchase_specification_rev_no'))
                    
#                     # For BOM components (raw materials), get their item-specific data
#                     else:
#                         set_item_data(row)
                    
#                 except frappe.DoesNotExistError:
#                     frappe.log_error(f"BOM {row.bom_no} not found")
#                     # Fallback to item data if BOM not found
#                     set_item_data(row)
            
#             else:
#                 # If no BOM, get data directly from item
#                 set_item_data(row)
    
#     # Set flag to prevent repeated execution in the same request
#     doc._custom_fields_updated = True


# Override: Include Draft and Submitted Purchase Orders when creating PO from MR
@frappe.whitelist()
def make_purchase_order(source_name, target_doc=None, args=None):
    import json
    if args is None:
        args = {}
    if isinstance(args, str):
        args = json.loads(args)

    from erpnext.stock.doctype.material_request.material_request import set_missing_values as erp_set_missing_values

    def set_missing_values(source, target_doc):
        if target_doc.doctype == "Purchase Order" and getdate(target_doc.schedule_date) < getdate(nowdate()):
            target_doc.schedule_date = None
        target_doc.run_method("set_missing_values")
        target_doc.run_method("calculate_taxes_and_totals")

    def update_item(obj, target, source_parent):
        # Use both submitted and draft PO qty in pending calculation
        # Base pending = stock_qty - (ordered_qty or received_qty)
        base_consumed = flt(obj.ordered_qty or obj.received_qty)

        # Add qty from Draft Purchase Orders mapped from this MR Item
        draft_po_qty = frappe.db.sql(
            """
            SELECT COALESCE(SUM(poi.stock_qty), 0)
            FROM `tabPurchase Order Item` poi
            INNER JOIN `tabPurchase Order` po ON poi.parent = po.name
            WHERE poi.material_request = %s
              AND poi.material_request_item = %s
              AND po.docstatus = 0
            """,
            (obj.parent, obj.name),
        )[0][0]

        total_consumed = base_consumed + flt(draft_po_qty)

        target.conversion_factor = obj.conversion_factor
        pending_stock_qty = max(flt(obj.stock_qty) - total_consumed, 0)
        target.qty = pending_stock_qty / target.conversion_factor if target.conversion_factor else 0
        target.stock_qty = target.qty * target.conversion_factor
        if getdate(target.schedule_date) < getdate(nowdate()):
            target.schedule_date = None

    def select_item(d):
        filtered_items = args.get("filtered_children", [])
        child_filter = d.name in filtered_items if filtered_items else True

        # Compute consumed including draft POs
        base_consumed = flt(d.ordered_qty or d.received_qty)
        draft_po_qty = frappe.db.sql(
            """
            SELECT COALESCE(SUM(poi.stock_qty), 0)
            FROM `tabPurchase Order Item` poi
            INNER JOIN `tabPurchase Order` po ON poi.parent = po.name
            WHERE poi.material_request = %s
              AND poi.material_request_item = %s
              AND po.docstatus = 0
            """,
            (d.parent, d.name),
        )[0][0]

        consumed = base_consumed + flt(draft_po_qty)
        return (consumed < d.stock_qty) and child_filter

    # Guard: If nothing is pending (considering Draft + Submitted POs), raise a helpful error
    mr_doc = frappe.get_doc("Material Request", source_name)
    filtered_children = args.get("filtered_children", []) if isinstance(args, dict) else []

    def is_item_considered(item_row_name: str) -> bool:
        return (item_row_name in filtered_children) if filtered_children else True

    any_pending = False
    for d in mr_doc.items:
        if not is_item_considered(d.name):
            continue
        base_consumed = flt(d.ordered_qty or d.received_qty)
        draft_po_qty = frappe.db.sql(
            """
            SELECT COALESCE(SUM(poi.stock_qty), 0)
            FROM `tabPurchase Order Item` poi
            INNER JOIN `tabPurchase Order` po ON poi.parent = po.name
            WHERE poi.material_request = %s
              AND poi.material_request_item = %s
              AND po.docstatus = 0
            """,
            (d.parent, d.name),
        )[0][0]
        if (base_consumed + flt(draft_po_qty)) < flt(d.stock_qty):
            any_pending = True
            break

    if not any_pending:
        # Build a summary of POs linked to this MR (Draft + Submitted)
        filters_clause = ""
        params = [source_name]
        if filtered_children:
            placeholders = ",".join(["%s"] * len(filtered_children))
            filters_clause = f" AND poi.material_request_item IN ({placeholders})"
            params.extend(filtered_children)

        rows = frappe.db.sql(
            f"""
            SELECT po.name, po.docstatus, COALESCE(SUM(poi.stock_qty), 0) AS total_stock_qty
            FROM `tabPurchase Order Item` poi
            INNER JOIN `tabPurchase Order` po ON poi.parent = po.name
            WHERE poi.material_request = %s
              AND po.docstatus IN (0,1)
              {filters_clause}
            GROUP BY po.name, po.docstatus
            ORDER BY po.creation DESC
            """,
            tuple(params),
            as_dict=True,
        )

        if rows:
            lines = []
            total_pos = len(rows)
            for r in rows:
                status = "Draft" if r.docstatus == 0 else "Submitted"
                po_name = escape_html(r.name)
                link = f"<a href=\"/app/purchase-order/{po_name}\">{po_name}</a>"
                lines.append(f"- {link}: {status}, Qty: {flt(r.total_stock_qty)}")
            details = "<br>".join(lines)
            message = f"All requested quantities are already covered by Purchase Orders ({total_pos}).<br>{details}"
            frappe.throw(_(message), title=_("Nothing to Order – Already in Purchase Orders"))
        else:
            frappe.throw(_( "All requested quantities are already covered by Purchase Orders." ), title=_("Nothing to Order – Already in Purchase Orders"))

    doclist = get_mapped_doc(
        "Material Request",
        source_name,
        {
            "Material Request": {
                "doctype": "Purchase Order",
                "validation": {"docstatus": ["=", 1], "material_request_type": ["=", "Purchase"]},
            },
            "Material Request Item": {
                "doctype": "Purchase Order Item",
                "field_map": [
                    ["name", "material_request_item"],
                    ["parent", "material_request"],
                    ["uom", "stock_uom"],
                    ["uom", "uom"],
                    ["sales_order", "sales_order"],
                    ["sales_order_item", "sales_order_item"],
                    ["wip_composite_asset", "wip_composite_asset"],
                ],
                "postprocess": update_item,
                "condition": select_item,
            },
        },
        target_doc,
        set_missing_values,
    )

    doclist.set_onload("load_after_mapping", False)
    return doclist

@frappe.whitelist()
def get_bom_name(sales_order: str, linked_batch: str, item_code: str):
    bom_name = None

    if linked_batch:
        bom_name = frappe.db.get_value(
            "BOM",
            {"custom_batch_no": linked_batch, "sales_order": sales_order, "item": item_code},
            "name",
        )

    if not bom_name:
        return {}
    
    return bom_name


import frappe
from frappe import _
from frappe.desk.search import validate_and_sanitize_search_inputs


@frappe.whitelist()
@validate_and_sanitize_search_inputs
def production_plan_query(doctype, txt, searchfield, start, page_len, filters):
    """Link-field query for Production Plan, filtered to a single row's batch_no."""

    batch_no = filters.get("batch_no")

    return frappe.db.sql(
        """
        SELECT DISTINCT pp.name
        FROM `tabProduction Plan` pp
        INNER JOIN `tabProduction Plan Item` ppi
            ON ppi.parent = pp.name
        WHERE
            pp.docstatus = 1
            AND ppi.custom_batch_no = %(batch)s
            AND pp.name LIKE %(txt)s
        ORDER BY pp.creation DESC
        LIMIT %(start)s, %(page_len)s
        """,
        {
            "batch": batch_no,
            "txt": f"%{txt}%",
            "start": start,
            "page_len": page_len,
        },
    )


@frappe.whitelist()
def get_linkable_items(material_request, mode):
    """
    Returns Material Request Item rows for the grid dialog.

    mode = "link"    -> rows where production_plan is NOT set
    mode = "relink"  -> rows where production_plan IS already set

    Rows without a batch_no are excluded either way since a Production Plan
    can't be resolved for them.
    """

    if mode not in ("link", "relink"):
        frappe.throw(_("Invalid mode."))

    docstatus = frappe.db.get_value("Material Request", material_request, "docstatus")
    if docstatus is None:
        frappe.throw(_("Material Request {0} not found.").format(material_request))
    if docstatus != 1:
        frappe.throw(_("Items can only be linked/re-linked for Submitted Material Requests."))

    all_rows = frappe.get_all(
        "Material Request Item",
        filters={"parent": material_request},
        fields=["name", "item_code", "qty", "custom_batch_no as batch_no", "production_plan"],
        order_by="idx asc",
    )

    want_linked = mode == "relink"
    return [row for row in all_rows if row.batch_no and bool(row.production_plan) == want_linked]


@frappe.whitelist()
def bulk_update_production_plan(material_request, updates):
    """
    updates: list of {"name": <Material Request Item row name>, "production_plan": <PP name or "">}

    Validates every row (ownership + batch<->production plan match) before
    writing anything, so a bad row in the payload can't leave a partial update.
    """

    if isinstance(updates, str):
        updates = frappe.parse_json(updates)

    if not updates:
        frappe.throw(_("No updates provided."))

    docstatus = frappe.db.get_value("Material Request", material_request, "docstatus")
    if docstatus != 1:
        frappe.throw(_("Production Plan can only be linked to Submitted Material Requests."))

    mr_items = frappe.get_all(
        "Material Request Item",
        filters={"parent": material_request},
        fields=["name", "custom_batch_no as batch_no"],
    )
    batch_by_row = {d.name: d.batch_no for d in mr_items}

    cleaned = []
    for update in updates:
        row_name = update.get("name")
        production_plan = (update.get("production_plan") or "").strip()

        if row_name not in batch_by_row:
            frappe.throw(
                _("Row {0} does not belong to Material Request {1}.").format(row_name, material_request)
            )

        if production_plan:
            batch_no = batch_by_row[row_name]
            is_valid = frappe.db.exists(
                "Production Plan Item",
                {"parent": production_plan, "custom_batch_no": batch_no},
            )
            if not is_valid:
                frappe.throw(
                    _("Production Plan {0} is not valid for Batch {1}.").format(production_plan, batch_no)
                )

        cleaned.append({"name": row_name, "production_plan": production_plan or None})

    for update in cleaned:
        frappe.db.set_value(
            "Material Request Item",
            update["name"],
            "production_plan",
            update["production_plan"],
            update_modified=False,
        )

   

    # Count only rows that actually received a Production Plan — a row left
    # blank in the dialog was submitted but not really "updated".
    linked = [u for u in cleaned if u["production_plan"]]
    skipped_count = len(cleaned) - len(linked)

    if not linked:
        message = _("No Production Plan was selected for any item.")
    elif skipped_count:
        message = _("Production Plan linked for {0} item(s). {1} item(s) skipped (no Production Plan selected).").format(
            len(linked), skipped_count
        )
    else:
        message = _("Production Plan linked for {0} item(s).").format(len(linked))

    return {
        "status": "success",
        "updated": len(linked),
        "skipped": skipped_count,
        "message": message,
    }
    
    
    
    
