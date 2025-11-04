import frappe
from frappe import _


def validate(doc, method):
    validate_duplicate_po(doc, method)
   

import frappe
from frappe import _

def validate_duplicate_purchase_invoice(doc, method):
    """
    Prevent duplicate Purchase Invoices for the same Purchase Order and item combination.
    Checks all items, not just the first one.
    """

    if not doc.supplier or not doc.items:
        return

    for item in doc.items:
        if not item.purchase_order or not item.item_code:
            continue

        # Find if any other Purchase Invoice already has this PO + Item
        duplicate_invoices = frappe.db.get_all(
            "Purchase Invoice Item",
            filters={
                "purchase_order": item.purchase_order,
                "item_code": item.item_code,
                "parent": ["!=", doc.name],
            },
            fields=["parent"]
        )

        if duplicate_invoices:
            # Get the first duplicate doc for reference
            existing_pi = duplicate_invoices[0].parent
            frappe.throw(
                _(
                    f"Duplicate Purchase Invoice found for Item <b>{item.item_code}</b> "
                    f"linked to Purchase Order <b>{item.purchase_order}</b>.<br>"
                    f"Existing Invoice: <b>{existing_pi}</b>"
                ),
                title="Duplicate Purchase Invoice Detected"
            )
