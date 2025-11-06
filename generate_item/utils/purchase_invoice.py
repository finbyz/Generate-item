import frappe
from frappe import _


def validate(doc, method):
    validate_duplicate_pi(doc, method)
   

def validate_duplicate_pi(doc, method):
    """Prevent duplicate draft Purchase Invoices for same supplier, item, qty, custom_batch_no, material_request, and material_request_item."""
    
    # Skip validation for cancelled or submitted docs
    if doc.docstatus != 0:
        return

    # Only proceed if custom_batch_no is set
    if not doc.custom_batch_no:
        return

    # Get potential duplicate PIs first (outside item loop for efficiency)
    duplicates = frappe.db.get_all(
        "Purchase Invoice",
        filters={
            "supplier": doc.supplier,
            "custom_batch_no": doc.custom_batch_no,
            "docstatus": 0,  # Only Draft
            "name": ["!=", doc.name],  # Exclude current
        },
        fields=["name"]
    )

    if not duplicates:
        return

    # Now check each item against these potential duplicates
    for item in doc.items:
        for d in duplicates:
            duplicate_items = frappe.db.get_all(
                "Purchase Invoice Item",
                filters={
                    "parent": d.name,
                    "item_code": item.item_code,
                    "qty": item.qty,
                    "material_request": item.material_request or "",
                    "material_request_item": item.material_request_item or "",
                },
                fields=["item_code", "qty"]
            )
            if duplicate_items:
                frappe.throw(_(
                    f"Duplicate Purchase Invoice Found: <b>{d.name}</b><br>"
                    f"Supplier <b>{doc.supplier}</b> already has a Draft PI "
                    f"for Item <b>{item.item_code}</b> with Qty <b>{item.qty}</b>, "
                    f"Batch No <b>{doc.custom_batch_no}</b>, "
                  
                ))