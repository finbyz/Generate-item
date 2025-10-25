import frappe


def before_insert(doc, method):
    """Set custom_batch_no for subcontracting order and its items from purchase order"""
    if not doc.purchase_order:
        return
    
    try:
        # Get the purchase order document
        purchase_order = frappe.get_doc("Purchase Order", doc.purchase_order)
        for i in purchase_order.items:
            if i.production_plan:
                for j in doc.items:
                    j.production_plan = i.production_plan
                    break 

        
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





def validate(doc, method):
    """Set production_plan in Subcontracting Order Items from Purchase Order or Material Request"""
    if not doc.purchase_order:
        return
    po = frappe.get_doc("Purchase Order", doc.purchase_order)

    for so_item in doc.items:
        # Find corresponding PO Item
        po_item = next((item for item in po.items if item.item_code == so_item.item_code), None)
        if not po_item:
            continue

        # Case 1: PO Item already has production_plan
        if po_item.production_plan:
            so_item.production_plan = po_item.production_plan
            continue

        # Case 2: Fallback to Material Request Item
        if po_item.material_request and po_item.material_request_item:
            mr_item = frappe.db.get_value(
                "Material Request Item",
                po_item.material_request_item,
                "production_plan"
            )
            if mr_item:
                so_item.production_plan = mr_item



import frappe, json

@frappe.whitelist()
def update_supplied_items_in_db(parent, data):
    data = json.loads(data)
    for row in data:
        if not row.get("name"):
            continue

        # Corrected table name for ERPNext v15
        frappe.db.set_value(
            "Subcontracting Order Supplied Item",  # corrected name
            row["name"],
            {
                "custom_drawing_no": row.get("custom_drawing_no", ""),
                "custom_pattern_drawing_no": row.get("custom_pattern_drawing_no", ""),
                "custom_purchase_specification_no": row.get("custom_purchase_specification_no", ""),
                "custom_drawing_rev_no": row.get("custom_drawing_rev_no", ""),
                "custom_pattern_drawing_rev_no": row.get("custom_pattern_drawing_rev_no", ""),
                "custom_purchase_specification_rev_no": row.get("custom_purchase_specification_rev_no", ""),
                "custom_batch_no": row.get("custom_batch_no", ""),
                "bom_reference": row.get("bom_reference", "")
            }
        )
    frappe.db.commit()
    return "Supplied items updated successfully in DB."



def before_save(doc, method):
    """Set custom_batch_no from BOM in items and supplied_items"""
    
    # Update custom_batch_no in items table
    for item in doc.items:
        if not item.custom_batch_no and item.bom:
            batch_no = frappe.get_value("BOM", item.bom, "custom_batch_no")
            if batch_no:
                item.custom_batch_no = batch_no
    
def before_submit(doc, method):
    for supplied_item in doc.supplied_items:
        if not supplied_item.custom_batch_no and supplied_item.bom_reference:
            batch_no = frappe.get_value("BOM", supplied_item.bom_reference, "custom_batch_no")
            if batch_no:
                supplied_item.custom_batch_no = batch_no
