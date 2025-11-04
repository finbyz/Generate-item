# import frappe

# def before_insert(doc, method):
#     """Set custom_batch_no for stock entry and its items from work order when creating from work order"""
#     if not doc.work_order:
#         return
    
#     try:
#         # Get the work order document
#         work_order = frappe.get_doc("Work Order", doc.work_order)
        
#         # Get custom_batch_no from work order
#         batch_no = getattr(work_order, 'custom_batch_no', None)
        
#         if batch_no:
#             # Set custom_batch_no in parent stock entry
#             doc.custom_batch_no = batch_no
            
#             # Set custom_batch_no in child items that match the work order's production item
#             production_item = getattr(work_order, 'production_item', None)
            
#             for item in doc.items:
#                 # Set batch_no for items that match the production item
#                 if production_item and item.item_code == production_item:
#                     item.custom_batch_no = batch_no
#                 # Also set for required items (raw materials) if they exist
#                 elif hasattr(doc, 'required_items') and doc.required_items:
#                     for req_item in doc.required_items:
#                         if req_item.item_code == item.item_code:
#                             item.custom_batch_no = batch_no
#                             break
#                 # For manufacturing stock entries, set batch_no for all items
#                 elif doc.purpose in ['Manufacture', 'Material Transfer for Manufacture']:
#                     item.custom_batch_no = batch_no
                    
#     except frappe.DoesNotExistError:
#         frappe.log_error(f"Work Order {doc.work_order} not found", "Stock Entry Validation Error")
#     except Exception as e:
#         frappe.log_error(f"Error in stock entry validation: {str(e)}", "Stock Entry Validation Error")



# def handle_subcontracting_order(doc, sub_order_name=None):
#     """Fetch custom fields from Subcontracting Order Supplied Item for each stock entry item"""
#     try:
#         if not sub_order_name:
#             sub_order_name = doc.subcontracting_order
        
#         if not sub_order_name:
#             return
        
#         # Get the subcontracting order
#         subcontracting_order = frappe.get_doc("Subcontracting Order", sub_order_name)
        

#         supplied_items_dict = {}
#         for supplied_item in subcontracting_order.supplied_items:
#             if supplied_item.rm_item_code:
#                 rm_item_code = supplied_item.rm_item_code
#                 # Store only first match for each rm_item_code to avoid conflicts
#                 if rm_item_code not in supplied_items_dict:
#                     supplied_items_dict[rm_item_code] = {
#                         'custom_batch_no': getattr(supplied_item, 'custom_batch_no', None),
#                         'custom_drawing_no': getattr(supplied_item, 'custom_drawing_no', None),
#                         'custom_drawing_rev_no': getattr(supplied_item, 'custom_drawing_rev_no', None),
#                         'custom_pattern_drawing_no': getattr(supplied_item, 'custom_pattern_drawing_no', None),
#                         'custom_pattern_drawing_rev_no': getattr(supplied_item, 'custom_pattern_drawing_rev_no', None),
#                         'custom_purchase_specification_no': getattr(supplied_item, 'custom_purchase_specification_no', None),
#                         'custom_purchase_specification_rev_no': getattr(supplied_item, 'custom_purchase_specification_rev_no', None),
#                         'bom_reference': getattr(supplied_item, 'bom_reference', None),
#                         'main_item_code': getattr(supplied_item, 'main_item_code', None),
#                     }
        
#         # Apply custom fields to each stock entry item
#         for item in doc.items:
#             # Method 1: Use sco_rm_detail field to find exact match
#             supplied_item = None
            
#             if hasattr(item, 'sco_rm_detail') and item.sco_rm_detail:
#                 # Direct reference via sco_rm_detail field
#                 for si in subcontracting_order.supplied_items:
#                     if si.name == item.sco_rm_detail:
#                         supplied_item = si
#                         break
            
#             # Method 2: Fallback to matching by item_code and subcontracted_item
#             if not supplied_item:
#                 for si in subcontracting_order.supplied_items:
#                     if (si.rm_item_code == item.item_code and 
#                         hasattr(item, 'subcontracted_item') and 
#                         si.main_item_code == item.subcontracted_item):
#                         supplied_item = si
#                         break
            
#             if supplied_item:
#                 # Apply fields directly from supplied_item
#                 apply_custom_fields_from_supplied_item(item, supplied_item)
                    
#     except Exception as e:
#         frappe.log_error(f"Error setting custom fields from subcontracting order: {str(e)}", "Stock Entry Validation Error")





# def apply_custom_fields_from_supplied_item(item, supplied_item):
#     """Apply custom fields directly from supplied_item object to stock entry item"""
#     if getattr(supplied_item, 'custom_batch_no', None):
#         item.custom_batch_no = supplied_item.custom_batch_no
#     if getattr(supplied_item, 'custom_drawing_no', None):
#         item.custom_drawing_no = supplied_item.custom_drawing_no
#     if getattr(supplied_item, 'custom_drawing_rev_no', None):
#         item.custom_drawing_rev_no = supplied_item.custom_drawing_rev_no
#     if getattr(supplied_item, 'custom_pattern_drawing_no', None):
#         item.custom_pattern_drawing_no = supplied_item.custom_pattern_drawing_no
#     if getattr(supplied_item, 'custom_pattern_drawing_rev_no', None):
#         item.custom_pattern_drawing_rev_no = supplied_item.custom_pattern_drawing_rev_no
#     if getattr(supplied_item, 'custom_purchase_specification_no', None):
#         item.custom_purchase_specification_no = supplied_item.custom_purchase_specification_no
#     if getattr(supplied_item, 'custom_purchase_specification_rev_no', None):
#         item.custom_purchase_specification_rev_no = supplied_item.custom_purchase_specification_rev_no
#     if getattr(supplied_item, 'bom_reference', None):
#         item.bom_reference = supplied_item.bom_reference

import frappe

def before_insert(doc, method):
    """Set custom fields for stock entry and its items from work order when creating from work order"""
    if not doc.work_order:
        return
    
    try:
        # Get the work order document
        work_order = frappe.get_doc("Work Order", doc.work_order)
        
        # Set BOM on parent if available
        if getattr(work_order, 'bom_no', None):
            doc.bom_no = work_order.bom_no

        # Get custom_batch_no from work order
        batch_no = getattr(work_order, 'custom_batch_no', None)
        
        if batch_no:
            # Set custom_batch_no in parent stock entry
            doc.custom_batch_no = batch_no
        
        # Prepare a dictionary of custom fields from work order's required_items, keyed by item_code
        required_items_dict = {}
        for req_item in work_order.required_items:
            if req_item.item_code:
                required_items_dict[req_item.item_code] = {
                    'custom_batch_no': getattr(req_item, 'custom_batch_no', None),
                    'custom_drawing_no': getattr(req_item, 'custom_drawing_no', None),
                    'custom_drawing_rev_no': getattr(req_item, 'custom_drawing_rev_no', None),
                    'custom_pattern_drawing_no': getattr(req_item, 'custom_pattern_drawing_no', None),
                    'custom_pattern_drawing_rev_no': getattr(req_item, 'custom_pattern_drawing_rev_no', None),
                    'custom_purchase_specification_no': getattr(req_item, 'custom_purchase_specification_no', None),
                    'custom_purchase_specification_rev_no': getattr(req_item, 'custom_purchase_specification_rev_no', None),
                }
        
        # Get production item for reference
        production_item = getattr(work_order, 'production_item', None)
        
        # Apply custom fields to child items
        for item in doc.items:
            custom_fields = None
            
            # First, check if it's a required item (raw material)
            if item.item_code in required_items_dict:
                custom_fields = required_items_dict[item.item_code]
            
            # Fallback: if it's the production item, set batch_no (and potentially other fields from work_order if available)
            elif production_item and item.item_code == production_item:
                item.custom_batch_no = batch_no
                # Add other fields from work_order if they exist and are relevant for FG
                # e.g., item.custom_ga_drawing_no = getattr(work_order, 'custom_ga_drawing_no', None)
                # item.custom_ga_drawing_rev_no = getattr(work_order, 'custom_ga_drawing_rev_no', None)
                # Uncomment and adjust as needed based on your FG custom fields
            
            # For manufacturing stock entries, ensure batch_no is set for all if not already
            elif doc.purpose in ['Manufacture', 'Material Transfer for Manufacture']:
                if not getattr(item, 'custom_batch_no', None):
                    item.custom_batch_no = batch_no
            
            # Apply all custom fields if found
            if custom_fields:
                apply_custom_fields_to_item(item, custom_fields)
                    
    except frappe.DoesNotExistError:
        frappe.log_error(f"Work Order {doc.work_order} not found", "Stock Entry Validation Error")
    except Exception as e:
        frappe.log_error(f"Error in stock entry validation: {str(e)}", "Stock Entry Validation Error")

def apply_custom_fields_to_item(item, custom_fields):
    """Apply custom fields from dict to stock entry item"""
    if custom_fields.get('custom_batch_no'):
        item.custom_batch_no = custom_fields['custom_batch_no']
    if custom_fields.get('custom_drawing_no'):
        item.custom_drawing_no = custom_fields['custom_drawing_no']
    if custom_fields.get('custom_drawing_rev_no'):
        item.custom_drawing_rev_no = custom_fields['custom_drawing_rev_no']
    if custom_fields.get('custom_pattern_drawing_no'):
        item.custom_pattern_drawing_no = custom_fields['custom_pattern_drawing_no']
    if custom_fields.get('custom_pattern_drawing_rev_no'):
        item.custom_pattern_drawing_rev_no = custom_fields['custom_pattern_drawing_rev_no']
    if custom_fields.get('custom_purchase_specification_no'):
        item.custom_purchase_specification_no = custom_fields['custom_purchase_specification_no']
    if custom_fields.get('custom_purchase_specification_rev_no'):
        item.custom_purchase_specification_rev_no = custom_fields['custom_purchase_specification_rev_no']

# The subcontracting functions remain unchanged, as the issue is with Work Order
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



import frappe

@frappe.whitelist()
def apply_work_order_custom_fields(stock_entry_name, work_order_name):
    """Fetch custom fields from Work Order and apply them to an existing Stock Entry"""
    if not stock_entry_name or not work_order_name:
        frappe.throw("Both Stock Entry and Work Order are required.")

    try:
        doc = frappe.get_doc("Stock Entry", stock_entry_name)
        work_order = frappe.get_doc("Work Order", work_order_name)

        # Set BOM on parent if available
        if getattr(work_order, 'bom_no', None):
            doc.bom_no = work_order.bom_no

        batch_no = getattr(work_order, 'custom_batch_no', None)
        if batch_no:
            doc.custom_batch_no = batch_no

        # Prepare dictionary of custom fields from required_items
        required_items_dict = {
            req.item_code: {
                "custom_batch_no": getattr(req, "custom_batch_no", None),
                "custom_drawing_no": getattr(req, "custom_drawing_no", None),
                "custom_drawing_rev_no": getattr(req, "custom_drawing_rev_no", None),
                "custom_pattern_drawing_no": getattr(req, "custom_pattern_drawing_no", None),
                "custom_pattern_drawing_rev_no": getattr(req, "custom_pattern_drawing_rev_no", None),
                "custom_purchase_specification_no": getattr(req, "custom_purchase_specification_no", None),
                "custom_purchase_specification_rev_no": getattr(req, "custom_purchase_specification_rev_no", None),
            }
            for req in work_order.required_items if req.item_code
        }

        production_item = getattr(work_order, 'production_item', None)

        for item in doc.items:
            custom_fields = required_items_dict.get(item.item_code)
            
            # Raw materials
            if custom_fields:
                apply_custom_fields_to_item(item, custom_fields)
            # Finished goods
            elif production_item and item.item_code == production_item:
                item.custom_batch_no = batch_no
                item.custom_ga_drawing_no = getattr(work_order, 'custom_ga_drawing_no', None)
                item.custom_ga_drawing_rev_no = getattr(work_order, 'custom_ga_drawing_rev_no', None)
            # Manufacturing transfer fallback
            elif doc.purpose in ['Manufacture', 'Material Transfer for Manufacture']:
                if not getattr(item, 'custom_batch_no', None):
                    item.custom_batch_no = batch_no

        doc.save(ignore_permissions=True)
        frappe.db.commit()
        return {"status": "success", "message": "Custom fields applied successfully."}

    except Exception as e:
        frappe.log_error(f"Error applying Work Order fields: {str(e)}", "Stock Entry Custom Fields")
        frappe.throw(f"Failed to apply custom fields: {str(e)}")


def apply_custom_fields_to_item(item, custom_fields):
    """Helper: Apply custom fields from dict to item row"""
    for key, val in custom_fields.items():
        if val:
            setattr(item, key, val)
