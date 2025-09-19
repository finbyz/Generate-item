import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt, getdate, nowdate, escape_html
from erpnext.stock.doctype.item.item import get_item_defaults

def validate(doc,method):
    if doc.custom_batch_no:
        for row in doc.items:
            row.db_set("custom_batch_no", doc.custom_batch_no)

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


# Override: Include Draft and Submitted Purchase Orders when creating PO from MR
@frappe.whitelist()
def make_purchase_order(source_name, target_doc=None, args=None):
    import json
    if args is None:
        args = {}
    if isinstance(args, str):
        args = json.loads(args)

    from erpnext.stock.doctype.material_request.material_request import set_missing_values as erp_set_missing_values

    def set_missing_values(source, target_doc):
        if target_doc.doctype == "Purchase Order" and getdate(target_doc.schedule_date) < getdate(nowdate()):
            target_doc.schedule_date = None
        target_doc.run_method("set_missing_values")
        target_doc.run_method("calculate_taxes_and_totals")

    def update_item(obj, target, source_parent):
        # Use both submitted and draft PO qty in pending calculation
        # Base pending = stock_qty - (ordered_qty or received_qty)
        base_consumed = flt(obj.ordered_qty or obj.received_qty)

        # Add qty from Draft Purchase Orders mapped from this MR Item
        draft_po_qty = frappe.db.sql(
            """
            SELECT COALESCE(SUM(poi.stock_qty), 0)
            FROM `tabPurchase Order Item` poi
            INNER JOIN `tabPurchase Order` po ON poi.parent = po.name
            WHERE poi.material_request = %s
              AND poi.material_request_item = %s
              AND po.docstatus = 0
            """,
            (obj.parent, obj.name),
        )[0][0]

        total_consumed = base_consumed + flt(draft_po_qty)

        target.conversion_factor = obj.conversion_factor
        pending_stock_qty = max(flt(obj.stock_qty) - total_consumed, 0)
        target.qty = pending_stock_qty / target.conversion_factor if target.conversion_factor else 0
        target.stock_qty = target.qty * target.conversion_factor
        if getdate(target.schedule_date) < getdate(nowdate()):
            target.schedule_date = None

    def select_item(d):
        filtered_items = args.get("filtered_children", [])
        child_filter = d.name in filtered_items if filtered_items else True

        # Compute consumed including draft POs
        base_consumed = flt(d.ordered_qty or d.received_qty)
        draft_po_qty = frappe.db.sql(
            """
            SELECT COALESCE(SUM(poi.stock_qty), 0)
            FROM `tabPurchase Order Item` poi
            INNER JOIN `tabPurchase Order` po ON poi.parent = po.name
            WHERE poi.material_request = %s
              AND poi.material_request_item = %s
              AND po.docstatus = 0
            """,
            (d.parent, d.name),
        )[0][0]

        consumed = base_consumed + flt(draft_po_qty)
        return (consumed < d.stock_qty) and child_filter

    # Guard: If nothing is pending (considering Draft + Submitted POs), raise a helpful error
    mr_doc = frappe.get_doc("Material Request", source_name)
    filtered_children = args.get("filtered_children", []) if isinstance(args, dict) else []

    def is_item_considered(item_row_name: str) -> bool:
        return (item_row_name in filtered_children) if filtered_children else True

    any_pending = False
    for d in mr_doc.items:
        if not is_item_considered(d.name):
            continue
        base_consumed = flt(d.ordered_qty or d.received_qty)
        draft_po_qty = frappe.db.sql(
            """
            SELECT COALESCE(SUM(poi.stock_qty), 0)
            FROM `tabPurchase Order Item` poi
            INNER JOIN `tabPurchase Order` po ON poi.parent = po.name
            WHERE poi.material_request = %s
              AND poi.material_request_item = %s
              AND po.docstatus = 0
            """,
            (d.parent, d.name),
        )[0][0]
        if (base_consumed + flt(draft_po_qty)) < flt(d.stock_qty):
            any_pending = True
            break

    if not any_pending:
        # Build a summary of POs linked to this MR (Draft + Submitted)
        filters_clause = ""
        params = [source_name]
        if filtered_children:
            placeholders = ",".join(["%s"] * len(filtered_children))
            filters_clause = f" AND poi.material_request_item IN ({placeholders})"
            params.extend(filtered_children)

        rows = frappe.db.sql(
            f"""
            SELECT po.name, po.docstatus, COALESCE(SUM(poi.stock_qty), 0) AS total_stock_qty
            FROM `tabPurchase Order Item` poi
            INNER JOIN `tabPurchase Order` po ON poi.parent = po.name
            WHERE poi.material_request = %s
              AND po.docstatus IN (0,1)
              {filters_clause}
            GROUP BY po.name, po.docstatus
            ORDER BY po.creation DESC
            """,
            tuple(params),
            as_dict=True,
        )

        if rows:
            lines = []
            total_pos = len(rows)
            for r in rows:
                status = "Draft" if r.docstatus == 0 else "Submitted"
                po_name = escape_html(r.name)
                link = f"<a href=\"/app/purchase-order/{po_name}\">{po_name}</a>"
                lines.append(f"- {link}: {status}, Qty: {flt(r.total_stock_qty)}")
            details = "<br>".join(lines)
            message = f"All requested quantities are already covered by Purchase Orders ({total_pos}).<br>{details}"
            frappe.throw(_(message), title=_("Nothing to Order – Already in Purchase Orders"))
        else:
            frappe.throw(_( "All requested quantities are already covered by Purchase Orders." ), title=_("Nothing to Order – Already in Purchase Orders"))

    doclist = get_mapped_doc(
        "Material Request",
        source_name,
        {
            "Material Request": {
                "doctype": "Purchase Order",
                "validation": {"docstatus": ["=", 1], "material_request_type": ["=", "Purchase"]},
            },
            "Material Request Item": {
                "doctype": "Purchase Order Item",
                "field_map": [
                    ["name", "material_request_item"],
                    ["parent", "material_request"],
                    ["uom", "stock_uom"],
                    ["uom", "uom"],
                    ["sales_order", "sales_order"],
                    ["sales_order_item", "sales_order_item"],
                    ["wip_composite_asset", "wip_composite_asset"],
                ],
                "postprocess": update_item,
                "condition": select_item,
            },
        },
        target_doc,
        set_missing_values,
    )

    doclist.set_onload("load_after_mapping", False)
    return doclist