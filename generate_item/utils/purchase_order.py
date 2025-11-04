import frappe
from frappe import _



def validate(doc, method):
    validate_duplicate_po(doc, method)
    for i in doc.items:
        i.po_line_no = i.idx
        if i.rate == 0:
            frappe.throw(f"Please enter a valid rate for item in line No. {i.idx}. The rate cannot be 0.",
                         title="Zero Rate Found")

def validate_duplicate_po(doc, method):
    """Prevent duplicate draft Purchase Orders for same supplier, item, and qty."""
    
    # Skip validation for cancelled or submitted docs
    if doc.docstatus != 0:
        return

    for item in doc.items:
        duplicates = frappe.db.get_all(
            "Purchase Order",
            filters={
                "supplier": doc.supplier,
                "docstatus": 0,  # Only Draft
                "name": ["!=", doc.name],  # Exclude current
            },
            fields=["name"]
        )

        if not duplicates:
            continue

        # Check for matching item + qty in other POs
        for d in duplicates:
            duplicate_items = frappe.db.get_all(
                "Purchase Order Item",
                filters={
                    "parent": d.name,
                    "item_code": item.item_code,
                    "qty": item.qty,
                    "material_request": item.material_request,
                    "material_request_item": item.material_request_item,
                },
                fields=["item_code", "qty"]
            )
            if duplicate_items:
                frappe.throw(_(
                    f"Duplicate Purchase Order Found: <b>{d.name}</b><br>"
                    f"Supplier <b>{doc.supplier}</b> already has a Draft PO "
                    f"for Item <b>{item.item_code}</b> with Qty <b>{item.qty}</b>."
                ))


def before_insert(doc, method):
    """Set custom_batch_no for purchase order and its items from linked Production Plan Item"""
    if not doc.items:
        return

    try:
        # Loop through PO items
        for po_item in doc.items:
            po_item.po_line_no = po_item.idx
            if po_item.production_plan_item:
                plan_item = frappe.get_doc("Production Plan Item", po_item.production_plan_item)

                # Get custom_batch_no from Production Plan Item
                batch_no = getattr(plan_item, "custom_batch_no", None)

                if batch_no:
                    # Set on PO parent (first found batch_no)
                    if not getattr(doc, "custom_batch_no", None):
                        doc.custom_batch_no = batch_no

                    # Set on PO child item
                    po_item.custom_batch_no = batch_no

    except frappe.DoesNotExistError:
        frappe.log_error(
            f"Linked Production Plan Item not found for PO {doc.name}",
            "Purchase Order before_insert Error"
        )
    except Exception as e:
        frappe.log_error(
            f"Error setting custom_batch_no for PO {doc.name}: {str(e)}",
            "Purchase Order before_insert Error"
        )

    
def before_save(doc, method):
    for i in doc.items:
        i.po_line_no = i.idx
#     try:
#         _enrich_subcontract_items_from_production_plan_or_bom(doc)
#     except Exception as e:
#         frappe.log_error(f"PO before_save enrichment error for {getattr(doc, 'name', 'Unsaved')}: {str(e)}", "Purchase Order before_save Enrichment")

# def _enrich_subcontract_items_from_production_plan_or_bom(doc):
#     """When an item row is subcontracted, copy custom fields from Production Plan rows
#     (po_items / sub_assembly_items / mr_items) matching the item_code. If no production_plan
#     is linked on the item row, fallback to the latest matching BOM Item.

#     Fields copied (if present on PO Item):
#       - custom_drawing_no
#       - custom_drawing_rev_no
#       - custom_purchase_specification_no
#       - custom_purchase_specification_rev_no
#       - custom_pattern_drawing_no
#       - custom_pattern_drawing_rev_no
#     """
#     if not getattr(doc, "items", None):
#         return

#     custom_fields = [
#         "custom_drawing_no",
#         "custom_drawing_rev_no",
#         "custom_purchase_specification_no",
#         "custom_purchase_specification_rev_no",
#         "custom_pattern_drawing_no",
#         "custom_pattern_drawing_rev_no",
#     ]

#     for row in doc.items:
#         try:
#             # Only for subcontracted lines
#             if not getattr(row, "is_subcontracted", 0):
#                 continue

#             # Prefer Production Plan linked on the row (if any)
#             pp_name = getattr(row, "production_plan", None)
#             if pp_name:
#                 try:
#                     pp_doc = frappe.get_doc("Production Plan", pp_name)
#                 except Exception:
#                     pp_doc = None

#                 if pp_doc:
#                     copied = _copy_fields_from_pp_tables(pp_doc, row, custom_fields)
#                     if copied:
#                         continue  # Done for this row

#             # Fallback: copy from BOM Item by item_code (latest modified)
#             _copy_fields_from_bom_item(row, custom_fields)
#         except Exception as row_err:
#             frappe.log_error(
#                 f"PO Item enrichment error on row {getattr(row, 'idx', '?')} in {getattr(doc, 'name', 'Unsaved')}: {str(row_err)}",
#                 "Purchase Order Item Enrichment",
#             )

# def _copy_fields_from_pp_tables(pp_doc, po_item_row, fieldnames):
#     """Find a matching row by item_code in Production Plan's po_items, sub_assembly_items, or mr_items
#     and copy the provided fieldnames onto the Purchase Order Item row (only setting values that are empty).

#     Returns True if any field was copied, else False.
#     """
#     item_code = getattr(po_item_row, "item_code", None)
#     if not item_code:
#         return False

#     sources = []
#     try:
#         if getattr(pp_doc, "po_items", None):
#             sources.extend(pp_doc.po_items)
#     except Exception:
#         pass
#     try:
#         if getattr(pp_doc, "sub_assembly_items", None):
#             sources.extend(pp_doc.sub_assembly_items)
#     except Exception:
#         pass
#     try:
#         if getattr(pp_doc, "mr_items", None):
#             sources.extend(pp_doc.mr_items)
#     except Exception:
#         pass

#     # Find first matching source row by item_code; for sub-assemblies also consider production_item/parent_item_code
#     match = None
#     for src in sources:
#         try:
#             src_codes = [
#                 getattr(src, "item_code", None),
#                 getattr(src, "production_item", None),
#                 getattr(src, "parent_item_code", None),
#             ]
#             if item_code in src_codes:
#                 match = src
#                 break
#         except Exception:
#             continue
#     if not match:
#         return False

#     copied_any = False
#     for f in fieldnames:
#         if hasattr(po_item_row, f):
#             dst_val = getattr(po_item_row, f, None)
#             src_val = getattr(match, f, None)
#             if (not dst_val) and src_val:
#                 setattr(po_item_row, f, src_val)
#                 copied_any = True
#     return copied_any

# def _copy_fields_from_bom_item(po_item_row, fieldnames):
#     """Copy custom fields from the latest BOM Item where item_code matches the PO Item's item_code.
#     Copies only into empty fields on the PO item row.
#     """
#     item_code = getattr(po_item_row, "item_code", None)
#     if not item_code:
#         return False

#     try:
#         bom_item = frappe.get_all(
#             "BOM Item",
#             filters={"item_code": item_code},
#             fields=fieldnames,
#             order_by="modified desc",
#             limit=1,
#         )
#     except Exception:
#         bom_item = []

#     if not bom_item:
#         return False

#     src = bom_item[0]
#     copied_any = False
#     for f in fieldnames:
#         if hasattr(po_item_row, f):
#             dst_val = getattr(po_item_row, f, None)
#             src_val = src.get(f)
#             if (not dst_val) and src_val:
#                 setattr(po_item_row, f, src_val)
#                 copied_any = True
#     return copied_any
        

@frappe.whitelist()
def update_po_line(po):
    if not po:
        frappe.throw("Purchase Order name is required")

    try:
        po_doc = frappe.get_doc("Purchase Order", po)
        for item in po_doc.items:
            item.po_line_no = item.idx

        po_doc.save(ignore_permissions=True)
        return "Line numbers updated successfully"

    except frappe.DoesNotExistError:
        frappe.throw(f"Purchase Order {po} not found.")
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "update_po_line error")
        frappe.throw(f"Error updating PO line numbers: {str(e)}")
