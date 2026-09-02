import frappe
from frappe import _
from typing import List, Dict

def update_material_request_with_production_plan():
    """
    Daily scheduler event to update Material Requests with Production Plan references
    based on batch numbers.
    """
    
    try:
        # Get all qualifying Material Request items
        qualifying_items = get_qualifying_material_request_items()
        
        if not qualifying_items:
            return
        
        # Group items by batch number
        batch_item_map = {}
        for item in qualifying_items:
            batch_no = item['batch_no']
            if batch_no not in batch_item_map:
                batch_item_map[batch_no] = []
            batch_item_map[batch_no].append(item)
        
        # Find Production Plans for all batch numbers
        batch_pp_map = find_production_plans_by_batches(list(batch_item_map.keys()))
        
        # Update Material Request items with Production Plan references
        update_count = 0
        for batch_no, items in batch_item_map.items():
            pp_data = batch_pp_map.get(batch_no)
            if pp_data:
                for item in items:
                    update_material_request_item(item['item_name'], pp_data)
                    update_count += 1
        
        if update_count:

            frappe.log_error(
                f"Material Request Update Complete: {update_count} items updated",
                "Material Request Production Plan Update"
            )
    
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(f"Error in Material Request update: {str(e)}", "Material Request Production Plan Update")
        raise


def get_qualifying_material_request_items() -> List[Dict]:
    """
    Get Material Request items where:
    - advance_mr = 1 at MR level
    - custom_batch_no has value
    - production_plan is null/empty
    - docstatus = 1
    """
    
    return frappe.db.sql("""
        SELECT 
            mri.name as item_name,
            mri.parent as mr_name,
            mri.custom_batch_no as batch_no
        FROM `tabMaterial Request Item` mri
        INNER JOIN `tabMaterial Request` mr ON mr.name = mri.parent
        WHERE mr.docstatus = 1
        AND mr.advance_mr = 1
        AND mri.custom_batch_no IS NOT NULL 
        AND mri.custom_batch_no != ''
        AND (mri.production_plan IS NULL OR mri.production_plan = '')
        ORDER BY mr.creation
    """, as_dict=True)

def find_production_plans_by_batches(batch_numbers: List[str]) -> Dict[str, Dict]:
    """
    Find Production Plans for multiple batch numbers.
    Searches in Production Plan Items
    
    Returns:
        Dict mapping batch_no to Production Plan data
    """
    
    if not batch_numbers:
        return {}
    
    placeholders = ','.join(['%s'] * len(batch_numbers))
    
    pp_data = frappe.db.sql(f"""
        SELECT 
            ppi.custom_batch_no as batch_no,
            pp.name as pp_name
        FROM `tabProduction Plan` pp
        INNER JOIN `tabProduction Plan Item` ppi ON ppi.parent = pp.name
        WHERE pp.docstatus = 1
        AND ppi.custom_batch_no IN ({placeholders})
    """, batch_numbers, as_dict=True)
    
    batch_pp_map = {}
    for pp in pp_data:
        if pp['batch_no'] not in batch_pp_map:  # First match wins
            batch_pp_map[pp['batch_no']] = {
                'name': pp['pp_name']
            }
    
    return batch_pp_map

def update_material_request_item(item_name: str, pp_data: Dict):
    """
    Update Material Request Item with Production Plan reference.
    """
    
    frappe.db.sql("""
        UPDATE `tabMaterial Request Item`
        SET 
            production_plan = %s,
            modified = NOW()
        WHERE name = %s
    """, (pp_data['name'], item_name))