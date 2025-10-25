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


def before_save(doc, method=None):
    for i in doc.items:
        if i.rate == 0:
            frappe.msgprint(
                (f"Please enter a valid rate for item in line No. {i.idx}. The rate cannot be 0."),
                title=("Invalid Value"),
                raise_exception=True
                )
        if i.is_free_item:
            if i.qty == 0:
                frappe.throw("Quantity cannot be 0 for free items.")