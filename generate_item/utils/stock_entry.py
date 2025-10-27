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



def handle_subcontracting_order(doc, sub_order_name=None):
    """Fetch custom fields from Subcontracting Order Supplied Item for each stock entry item"""
    try:
        if not sub_order_name:
            sub_order_name = doc.subcontracting_order
        
        if not sub_order_name:
            return
        
        # Get the subcontracting order
        subcontracting_order = frappe.get_doc("Subcontracting Order", sub_order_name)
        

        supplied_items_dict = {}
        for supplied_item in subcontracting_order.supplied_items:
            if supplied_item.rm_item_code:
                rm_item_code = supplied_item.rm_item_code
                # Store only first match for each rm_item_code to avoid conflicts
                if rm_item_code not in supplied_items_dict:
                    supplied_items_dict[rm_item_code] = {
                        'custom_batch_no': getattr(supplied_item, 'custom_batch_no', None),
                        'custom_drawing_no': getattr(supplied_item, 'custom_drawing_no', None),
                        'custom_drawing_rev_no': getattr(supplied_item, 'custom_drawing_rev_no', None),
                        'custom_pattern_drawing_no': getattr(supplied_item, 'custom_pattern_drawing_no', None),
                        'custom_pattern_drawing_rev_no': getattr(supplied_item, 'custom_pattern_drawing_rev_no', None),
                        'custom_purchase_specification_no': getattr(supplied_item, 'custom_purchase_specification_no', None),
                        'custom_purchase_specification_rev_no': getattr(supplied_item, 'custom_purchase_specification_rev_no', None),
                        'bom_reference': getattr(supplied_item, 'bom_reference', None),
                        'main_item_code': getattr(supplied_item, 'main_item_code', None),
                    }
        
        # Apply custom fields to each stock entry item
        for item in doc.items:
            # Method 1: Use sco_rm_detail field to find exact match
            supplied_item = None
            
            if hasattr(item, 'sco_rm_detail') and item.sco_rm_detail:
                # Direct reference via sco_rm_detail field
                for si in subcontracting_order.supplied_items:
                    if si.name == item.sco_rm_detail:
                        supplied_item = si
                        break
            
            # Method 2: Fallback to matching by item_code and subcontracted_item
            if not supplied_item:
                for si in subcontracting_order.supplied_items:
                    if (si.rm_item_code == item.item_code and 
                        hasattr(item, 'subcontracted_item') and 
                        si.main_item_code == item.subcontracted_item):
                        supplied_item = si
                        break
            
            if supplied_item:
                # Apply fields directly from supplied_item
                apply_custom_fields_from_supplied_item(item, supplied_item)
                    
    except Exception as e:
        frappe.log_error(f"Error setting custom fields from subcontracting order: {str(e)}", "Stock Entry Validation Error")





def apply_custom_fields_from_supplied_item(item, supplied_item):
    """Apply custom fields directly from supplied_item object to stock entry item"""
    if getattr(supplied_item, 'custom_batch_no', None):
        item.custom_batch_no = supplied_item.custom_batch_no
    if getattr(supplied_item, 'custom_drawing_no', None):
        item.custom_drawing_no = supplied_item.custom_drawing_no
    if getattr(supplied_item, 'custom_drawing_rev_no', None):
        item.custom_drawing_rev_no = supplied_item.custom_drawing_rev_no
    if getattr(supplied_item, 'custom_pattern_drawing_no', None):
        item.custom_pattern_drawing_no = supplied_item.custom_pattern_drawing_no
    if getattr(supplied_item, 'custom_pattern_drawing_rev_no', None):
        item.custom_pattern_drawing_rev_no = supplied_item.custom_pattern_drawing_rev_no
    if getattr(supplied_item, 'custom_purchase_specification_no', None):
        item.custom_purchase_specification_no = supplied_item.custom_purchase_specification_no
    if getattr(supplied_item, 'custom_purchase_specification_rev_no', None):
        item.custom_purchase_specification_rev_no = supplied_item.custom_purchase_specification_rev_no
    if getattr(supplied_item, 'bom_reference', None):
        item.bom_reference = supplied_item.bom_reference
