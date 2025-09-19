import frappe

def before_insert(doc, method):
    """Set custom_batch_no for purchase order and its items from linked Production Plan Item"""
    if not doc.items:
        return

    try:
        # Loop through PO items
        for po_item in doc.items:
            if po_item.production_plan_item:
                # Get Production Plan Item document
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

def validate(doc, method):
    for i in doc.items:
        if i.rate == 0:
            frappe.throw(f"Please enter a valid rate for item in line No. {i.idx}. The rate cannot be 0.",
                         title="Zero Rate Found")