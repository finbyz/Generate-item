import frappe
from frappe import _


@frappe.whitelist()
def get_bom_item_custom_fields(bom_no, item_code):
    if not bom_no or not item_code:
        return {}
    
    # Get BOM Item data for the specific item_code
    bom_item_data = frappe.db.get_value(
        "BOM Item",
        {"parent": bom_no, "item_code": item_code},
        [
            "custom_drawing_no",
            "custom_drawing_rev_no", 
            "custom_pattern_drawing_no",
            "custom_pattern_drawing_rev_no",
            "custom_purchase_specification_no",
            "custom_purchase_specification_rev_no",
            "custom_batch_no"
        ],
        as_dict=True
    )
    
    if not bom_item_data:
        frappe.log_error(
            f"BOM Item not found",
            f"BOM: {bom_no}, Item: {item_code}"
        )
        return {}
    
    # Add bom_no to the response
    bom_item_data["bom_no"] = bom_no
    
    return bom_item_data
