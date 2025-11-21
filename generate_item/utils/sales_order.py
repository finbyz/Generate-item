from multiprocessing import parent_process

import frappe
from frappe.utils import nowdate
from frappe import _

@frappe.whitelist()
def create_item_generator_doc(item_code: str | None = None, is_create_with_sales_order: int = 1):
    """Create an Item Generator and return the generated Item code.

    Args:
        item_code: Optional seed/entered code to put on Item Generator.
        is_create_with_sales_order: Marker flag set by SO flow.

    Returns:
        dict: { "item_code": <created_item_code>, "item_generator": <ig_name> }
    """

    # Prepare doc payload
    ig_doc = {
        "doctype": "Item Generator",
        "is_create_with_sales_order": is_create_with_sales_order,
    }
    if item_code:
        # Only set if field exists to avoid schema errors in case of customization
        try:
            if frappe.get_meta("Item Generator").has_field("item_code"):
                ig_doc["item_code"] = item_code
        except Exception:
            # Meta lookup issues should not block creation
            pass

    ig = frappe.get_doc(ig_doc).insert(ignore_permissions=True)

    # Expect Item Generator's own logic to populate created_item_code
    ig.reload()
    created_item_code = getattr(ig, "created_item_code", None)
    if not created_item_code:
        frappe.throw("Item Generator did not generate an Item Code yet.")

    return {
        "item_code": created_item_code,
        "item_generator": ig.name,
    }


# def before_save(doc, method=None):
#     for i in doc.items:
#         if i.rate == 0:
#             frappe.msgprint(
#                 (f"Please enter a valid rate for item in line No. {i.idx}. The rate cannot be 0."),
#                 title=("Invalid Value"),
#                 raise_exception=True
#                 )
#         if i.is_free_item:
#             i.rate = 0;
#             if i.qty == 0:
#                 frappe.throw("Quantity cannot be 0 for free items.")

def validate(doc, method):
    for i in doc.items:
        if i.bom_no:
            i.bom_no = ""
    # validate_duplicate_so(doc, method)

def before_save(doc, method=None):
    for i in doc.items:
        if i.is_free_item:
            i.rate = 0

            if not i.qty or i.qty == 0:
                frappe.throw(f"Quantity cannot be 0 for free item in line No. {i.idx}")

            if i.bom_no:
                i.bom_no = ""

            # Validate that component_of is specified
            # if not i.component_of:
            #     frappe.throw(f"'Component Of' must be set for free item in line No. {i.idx}")
        else:
            # For non-free items, rate must be > 0
            if i.rate == 0:
                frappe.throw(
                    f"Please enter a valid rate for item in line No. {i.idx}. The rate cannot be 0.",
                    title="Invalid Value"
                )


def validate_duplicate_so(doc, method):
    """Prevent duplicate draft Sales Orders for same customer, branch, item, qty, rate, order_type, and taxes_and_charges."""
    
    # Skip validation for cancelled or submitted docs
    if doc.docstatus != 0:
        return

    # Get potential duplicate SOs first (outside item loop for efficiency)
    duplicates = frappe.db.get_all(
        "Sales Order",
        filters={
            "customer": doc.customer,
            "branch": doc.branch or "",
            "order_type": doc.order_type,
            "taxes_and_charges": doc.taxes_and_charges or "",
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
        for d in duplicates:
            duplicate_items = frappe.db.get_all(
                "Sales Order Item",
                filters={
                    "parent": d.name,
                    "item_code": item.item_code,
                    # Removed qty check to restrict even on qty differences
                    "rate": item.rate,
                },
                fields=["item_code", "qty", "rate"]
            )
            if duplicate_items:
                violations.append({
                    "doc_name": d.name,
                    "item_code": item.item_code,
                    "qty": item.qty,
                    "rate": item.rate,
                    "existing_qty": duplicate_items[0].qty if duplicate_items else 'N/A'  # For message
                })

    if violations:
        # Format a single error message with all issues
        error_msg = "<b>Multiple Duplicate Sales Orders Found:</b><br><br>"
        seen_docs = {}  # To group by doc if multiple items per doc
        for v in violations:
            doc_key = v["doc_name"]
            if doc_key not in seen_docs:
                seen_docs[doc_key] = []
            seen_docs[doc_key].append(f"- Item <b>{v['item_code']}</b> (Your Qty: <b>{v['qty']}</b>, Existing Qty: <b>{v['existing_qty']}</b>, Rate: <b>{v['rate']}</b>)")
        
        for doc_name, items_list in seen_docs.items():
            error_msg += f"Existing Draft Sales Order: <b><a href='/app/sales-order/{doc_name}'>{doc_name}</a></b><br>"
            error_msg += f"(Customer: <b>{doc.customer}</b>, Branch: <b>{doc.branch or 'N/A'}</b>, Order Type: <b>{doc.order_type}</b>, Commercial TC: <b>{doc.taxes_and_charges or 'N/A'}</b>)<br><br>"
            error_msg += "<br>".join(items_list)
            error_msg += "<br><br>"
        
        frappe.throw(_(error_msg))


@frappe.whitelist()
def update_sales_order_child_custom_fields(parent: str, items: list | str, child_table: str | None = None):
    """Persist custom fields edited via Update Items dialog for Sales Order rows."""
    if not parent or not items:
        return

    if isinstance(items, str):
        items = frappe.parse_json(items)

    if not isinstance(items, (list, tuple)):
        return

    allowed_fields = {"po_line_no", "tag_no", "line_remark", "description", "custom_shipping_address"}

    for row in items:
        if not isinstance(row, dict):
            continue
        docname = row.get("docname") or row.get("name")
        if not docname:
            continue
        if not frappe.db.exists("Sales Order Item", {"name": docname, "parent": parent}):
            continue

        updates = {}
        for field in allowed_fields:
            if field in row:
                updates[field] = row.get(field)

        if updates:
            frappe.db.set_value("Sales Order Item", docname, updates)