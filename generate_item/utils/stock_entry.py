import frappe

def before_insert(doc, method):
    """Set custom_batch_no for stock entry and its items from work order when creating from work order"""
    if not doc.work_order:
        return
    
    try:
        # Get the work order document
        work_order = frappe.get_doc("Work Order", doc.work_order)
        
        # Get custom_batch_no from work order
        batch_no = getattr(work_order, 'custom_batch_no', None)
        
        if batch_no:
            # Set custom_batch_no in parent stock entry
            doc.custom_batch_no = batch_no
            
            # Set custom_batch_no in child items that match the work order's production item
            production_item = getattr(work_order, 'production_item', None)
            
            for item in doc.items:
                # Set batch_no for items that match the production item
                if production_item and item.item_code == production_item:
                    item.custom_batch_no = batch_no
                # Also set for required items (raw materials) if they exist
                elif hasattr(doc, 'required_items') and doc.required_items:
                    for req_item in doc.required_items:
                        if req_item.item_code == item.item_code:
                            item.custom_batch_no = batch_no
                            break
                # For manufacturing stock entries, set batch_no for all items
                elif doc.purpose in ['Manufacture', 'Material Transfer for Manufacture']:
                    item.custom_batch_no = batch_no
                    
    except frappe.DoesNotExistError:
        frappe.log_error(f"Work Order {doc.work_order} not found", "Stock Entry Validation Error")
    except Exception as e:
        frappe.log_error(f"Error in stock entry validation: {str(e)}", "Stock Entry Validation Error")