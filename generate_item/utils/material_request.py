# import frappe

# def before_validate(doc, method=None):
#     if doc.items and len(doc.items) > 0:
#         # Get production plan from the first item that has it
#         production_plan = None
#         for item in doc.items:
#             if item.production_plan:
#                 production_plan = item.production_plan
#                 break
        
#         # Set batch number from production plan if available
#         if production_plan:
#             try:
#                 pp = frappe.get_doc('Production Plan', production_plan)
#                 if pp.po_items and len(pp.po_items) > 0 and pp.po_items[0].custom_batch_no:
#                     batch_no = pp.po_items[0].custom_batch_no
#                     doc.custom_batch_no = batch_no
#                     for item in doc.items:
#                         item.custom_batch_no = batch_no
#             except frappe.DoesNotExistError:
#                 frappe.log_error(f"Production Plan {production_plan} not found")


import frappe

def before_insert(doc, method=None):
    """Run only when creating new Material Request"""
    populate_custom_fields(doc)

def before_save(doc, method=None):
    """Run before saving (both insert and update)"""
    # Only populate if fields are empty or if specific trigger conditions are met
    if should_populate_fields(doc):
        populate_custom_fields(doc)

def should_populate_fields(doc):
    """Check if we should populate custom fields"""
    # Only populate if most custom fields are empty
    if not doc.items:
        return False
        
    for item in doc.items:
        if (not item.get('custom_drawing_no') and not item.get('custom_drawing_rev_no') and
            not item.get('custom_pattern_drawing_no') and not item.get('custom_pattern_drawing_no') and 
            not item.get('custom_purchase_specification_no') and not item.get('custom_purchase_specification_rev_no') ):
            return True
    return False

def populate_custom_fields(doc):
    """Main logic to populate custom fields"""
    if not doc.items or len(doc.items) == 0:
        return
        
    # Get production plan from the first item that has it
    production_plan = None
    for item in doc.items:
        if item.production_plan:
            production_plan = item.production_plan
            break
    
    # Set batch number from production plan if available
    if production_plan:
        try:
            pp = frappe.get_doc('Production Plan', production_plan)
            if pp.po_items and len(pp.po_items) > 0 and pp.po_items[0].custom_batch_no:
                batch_no = pp.po_items[0].custom_batch_no
                
                # Only set if different to avoid unnecessary updates
                if doc.get('custom_batch_no') != batch_no:
                    doc.custom_batch_no = batch_no
                
                for item in doc.items:
                    if item.get('custom_batch_no') != batch_no:
                        item.custom_batch_no = batch_no
        except frappe.DoesNotExistError:
            frappe.log_error(f"Production Plan {production_plan} not found")
    
    # Process each item in doc.items
    for row in doc.items:
        if row.bom_no:
            try:
                bom = frappe.get_doc("BOM", row.bom_no)
                
                # If this is a finished good item, get its BOM data
                if row.item_code == bom.item:
                    # Only update if values are different
                    update_if_different(row, 'custom_drawing_no', bom.get('custom_drawing_no'))
                    update_if_different(row, 'custom_pattern_drawing_no', bom.get('custom_pattern_drawing_no'))
                    update_if_different(row, 'custom_purchase_specification_no', bom.get('custom_purchase_specification_no'))
                    update_if_different(row, 'custom_drawing_rev_no', bom.get('custom_drawing_rev_no'))
                    update_if_different(row, 'custom_pattern_drawing_rev_no', bom.get('custom_pattern_drawing_rev_no'))
                    update_if_different(row, 'custom_purchase_specification_rev_no', bom.get('custom_purchase_specification_rev_no'))
                
                # For BOM components (raw materials), get their item-specific data
                else:
                    set_item_data(row)
                
            except frappe.DoesNotExistError:
                frappe.log_error(f"BOM {row.bom_no} not found")
                # Fallback to item data if BOM not found
                set_item_data(row)
        
        else:
            # If no BOM, get data directly from item
            set_item_data(row)

def update_if_different(row, field_name, new_value):
    """Helper function to update field only if value is different"""
    current_value = row.get(field_name)
    if current_value != new_value:
        row.set(field_name, new_value)

def set_item_data(row):
    """Helper function to set item data from Item master"""
    try:
        item_doc = frappe.get_doc("Item", row.item_code)
        
        # Only update if values are different
        update_if_different(row, 'custom_drawing_no', item_doc.get("custom_drawing_no"))
        update_if_different(row, 'custom_pattern_drawing_no', item_doc.get("custom_pattern_drawing_no"))
        update_if_different(row, 'custom_purchase_specification_no', item_doc.get("custom_purchase_specification_no"))
        update_if_different(row, 'custom_drawing_rev_no', item_doc.get("custom_drawing_rev_no"))
        update_if_different(row, 'custom_pattern_drawing_rev_no', item_doc.get("custom_pattern_drawing_rev_no"))
        update_if_different(row, 'custom_purchase_specification_rev_no', item_doc.get("custom_purchase_specification_rev_no"))
        update_if_different(row, 'custom_batch_no', item_doc.get("custom_batch_no"))
        
    except frappe.DoesNotExistError:
        frappe.log_error(f"Item {row.item_code} not found")

# Alternative: If you want to use the original before_validate approach with fixes
def before_validate(doc, method=None):
    """Fixed version of original before_validate hook"""
    # Skip if this validation has already been run in this request
    if hasattr(doc, '_custom_fields_updated') and doc._custom_fields_updated:
        return
        
    if doc.items and len(doc.items) > 0:
        # Get production plan from the first item that has it
        production_plan = None
        for item in doc.items:
            if item.production_plan:
                production_plan = item.production_plan
                break
        
        # Set batch number from production plan if available
        if production_plan:
            try:
                pp = frappe.get_doc('Production Plan', production_plan)
                if pp.po_items and len(pp.po_items) > 0 and pp.po_items[0].custom_batch_no:
                    batch_no = pp.po_items[0].custom_batch_no
                    
                    # Only set if different to avoid unnecessary updates
                    if doc.get('custom_batch_no') != batch_no:
                        doc.custom_batch_no = batch_no
                    
                    for item in doc.items:
                        if item.get('custom_batch_no') != batch_no:
                            item.custom_batch_no = batch_no
            except frappe.DoesNotExistError:
                frappe.log_error(f"Production Plan {production_plan} not found")
        
        # Process each item in doc.items
        for row in doc.items:
            if row.bom_no:
                try:
                    bom = frappe.get_doc("BOM", row.bom_no)
                    
                    # If this is a finished good item, get its BOM data
                    if row.item_code == bom.item:
                        # Only update if values are different
                        update_if_different(row, 'custom_drawing_no', bom.get('custom_drawing_no'))
                        update_if_different(row, 'custom_pattern_drawing_no', bom.get('custom_pattern_drawing_no'))
                        update_if_different(row, 'custom_purchase_specification_no', bom.get('custom_purchase_specification_no'))
                        update_if_different(row, 'custom_drawing_rev_no', bom.get('custom_drawing_rev_no'))
                        update_if_different(row, 'custom_pattern_drawing_rev_no', bom.get('custom_pattern_drawing_rev_no'))
                        update_if_different(row, 'custom_purchase_specification_rev_no', bom.get('custom_purchase_specification_rev_no'))
                    
                    # For BOM components (raw materials), get their item-specific data
                    else:
                        set_item_data(row)
                    
                except frappe.DoesNotExistError:
                    frappe.log_error(f"BOM {row.bom_no} not found")
                    # Fallback to item data if BOM not found
                    set_item_data(row)
            
            else:
                # If no BOM, get data directly from item
                set_item_data(row)
    
    # Set flag to prevent repeated execution in the same request
    doc._custom_fields_updated = True