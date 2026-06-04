import frappe

def before_insert(doc, method):
    """Set custom fields for stock entry and its items from work order when creating from work order"""
    if not doc.work_order:
        return
    
    try:
        work_order = frappe.get_doc("Work Order", doc.work_order)
        
        if getattr(work_order, 'bom_no', None):
            doc.bom_no = work_order.bom_no

        batch_no = getattr(work_order, 'custom_batch_no', None)
        
        if batch_no:
            doc.custom_batch_no = batch_no
        
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
        
        production_item = getattr(work_order, 'production_item', None)
        
        for item in doc.items:
            custom_fields = None
            
            if item.item_code in required_items_dict:
                custom_fields = required_items_dict[item.item_code]
            
            elif production_item and item.item_code == production_item:
                item.custom_batch_no = batch_no
            
            elif doc.purpose in ['Manufacture', 'Material Transfer for Manufacture']:
                if not getattr(item, 'custom_batch_no', None):
                    item.custom_batch_no = batch_no
            
            if custom_fields:
                apply_custom_fields_to_item(item, custom_fields)
                    
    except frappe.DoesNotExistError:
        frappe.log_error(f"Work Order {doc.work_order} not found", "Stock Entry Validation Error")
    except Exception as e:
        frappe.log_error(f"Error in stock entry validation: {str(e)}", "Stock Entry Validation Error")


def apply_custom_fields_to_item(item, custom_fields):
    """Helper: Apply custom fields from dict to item row"""
    for key, val in custom_fields.items():
        if val:
            setattr(item, key, val)


def handle_subcontracting_order(doc, sub_order_name=None):
    """Fetch custom fields from Subcontracting Order Supplied Item for each stock entry item"""
    try:
        if not sub_order_name:
            sub_order_name = doc.subcontracting_order
        
        if not sub_order_name:
            return
        
        subcontracting_order = frappe.get_doc("Subcontracting Order", sub_order_name)
        
        supplied_items_dict = {}
        for supplied_item in subcontracting_order.supplied_items:
            if supplied_item.rm_item_code:
                rm_item_code = supplied_item.rm_item_code
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
        
        for item in doc.items:
            supplied_item = None
            
            if hasattr(item, 'sco_rm_detail') and item.sco_rm_detail:
                for si in subcontracting_order.supplied_items:
                    if si.name == item.sco_rm_detail:
                        supplied_item = si
                        break
            
            if not supplied_item:
                for si in subcontracting_order.supplied_items:
                    if (si.rm_item_code == item.item_code and 
                        hasattr(item, 'subcontracted_item') and 
                        si.main_item_code == item.subcontracted_item):
                        supplied_item = si
                        break
            
            if supplied_item:
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


@frappe.whitelist()
def apply_work_order_custom_fields(stock_entry_name, work_order_name):
    """Fetch custom fields from Work Order and apply them to an existing Stock Entry"""
    if not stock_entry_name or not work_order_name:
        frappe.throw("Both Stock Entry and Work Order are required.")

    try:
        doc = frappe.get_doc("Stock Entry", stock_entry_name)
        work_order = frappe.get_doc("Work Order", work_order_name)

        if getattr(work_order, 'bom_no', None):
            doc.bom_no = work_order.bom_no

        batch_no = getattr(work_order, 'custom_batch_no', None)
        if batch_no:
            doc.custom_batch_no = batch_no

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
            
            if custom_fields:
                apply_custom_fields_to_item(item, custom_fields)
            elif production_item and item.item_code == production_item:
                item.custom_batch_no = batch_no
                item.custom_ga_drawing_no = getattr(work_order, 'custom_ga_drawing_no', None)
                item.custom_ga_drawing_rev_no = getattr(work_order, 'custom_ga_drawing_rev_no', None)
            elif doc.purpose in ['Manufacture', 'Material Transfer for Manufacture']:
                if not getattr(item, 'custom_batch_no', None):
                    item.custom_batch_no = batch_no

        doc.save(ignore_permissions=True)
        frappe.db.commit()
        return {"status": "success", "message": "Custom fields applied successfully."}

    except Exception as e:
        frappe.log_error(f"Error applying Work Order fields: {str(e)}", "Stock Entry Custom Fields")
        frappe.throw(f"Failed to apply custom fields: {str(e)}")



def on_submit(doc, method=None):
    
    # if doc.stock_entry_type != "Manufacture":
    #     return

    
    serial_nos = []
    for row in (doc.items or []):
   
        if row.get("serial_no"):
            
            parsed = [
                s.strip()
                for s in (row.serial_no or "").splitlines()
                if s.strip()
            ]
            serial_nos.extend(parsed)

    if not serial_nos:
        return

    
    serial_nos = list(dict.fromkeys(serial_nos))

    
    placeholders = ", ".join(["%s"] * len(serial_nos))
    frappe.db.sql(
        f"""
        UPDATE `tabSerial Number`
        SET    stock_entry  = %s,
               modified     = NOW(),
               modified_by  = %s
        WHERE  name IN ({placeholders})
        """,
        [doc.name, frappe.session.user, *serial_nos],
    )
    frappe.db.commit()

    
    frappe.msgprint(
        f"{len(serial_nos)} Serial Number(s) linked to Stock Entry <b>{doc.name}</b>.",
        title="Serial Numbers Linked",
        indicator="green",
    )




def before_cancel_stock_entry(doc, method=None):
    
    # if doc.stock_entry_type != "Manufacture":
    #     return

    
    serial_nos = []
    for row in (doc.items or []):
        if row.get("serial_no"):
            parsed = [
                s.strip()
                for s in (row.serial_no or "").splitlines()
                if s.strip()
            ]
            serial_nos.extend(parsed)

    
    serial_nos = list(dict.fromkeys(serial_nos))

    if not serial_nos:
        return

    # Bulk clear stock_entry only for serials that belong to this stock entry
    placeholders = ", ".join(["%s"] * len(serial_nos))
    frappe.db.sql(
        f"""
        UPDATE `tabSerial Number`
        SET    stock_entry = ''
        WHERE  name        IN ({placeholders})
          AND  stock_entry = %s
        """,
        [*serial_nos, doc.name],
        auto_commit=False,
    )

    # Show message to user
    frappe.msgprint(
        f"{len(serial_nos)} Serial Number(s) unlinked from Stock Entry <b>{doc.name}</b>.",
        title="Serial Numbers Unlinked",
        indicator="orange",
    )