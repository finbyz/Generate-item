import frappe

def before_insert(doc, method):
    """Set custom_batch_no for subcontracting order and its items from purchase order"""
    if not doc.purchase_order:
        return
    
    try:
        # Get the purchase order document
        purchase_order = frappe.get_doc("Purchase Order", doc.purchase_order)
        
        # Get custom_batch_no from purchase order
        batch_no = getattr(purchase_order, 'custom_batch_no', None)
        
        if batch_no:
            # Set custom_batch_no in parent subcontracting order
            doc.custom_batch_no = batch_no
            
            # Set custom_batch_no in child items that match purchase order items
            for sub_item in doc.items:
                # Find matching item in purchase order
                for po_item in purchase_order.items:
                    if po_item.item_code == sub_item.item_code:
                        # Set batch_no for matching item
                        sub_item.custom_batch_no = batch_no
                        break
                # If no match found but we have batch_no, set it anyway for subcontracting items
                if not sub_item.custom_batch_no:
                    sub_item.custom_batch_no = batch_no
                    
    except frappe.DoesNotExistError:
        frappe.log_error(f"Purchase Order {doc.purchase_order} not found", "Subcontracting Order Validation Error")
    except Exception as e:
        frappe.log_error(f"Error in subcontracting order validation: {str(e)}", "Subcontracting Order Validation Error")


