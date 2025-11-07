import frappe
from generate_item.utils.bom_naming import get_custom_bom_name, get_available_bom_name

def before_insert(doc, method=None):
    """Set custom BOM name before document is inserted"""
    try:
        # Map fields from BOM Creator if this BOM was created from BOM Creator
        if hasattr(doc, 'bom_creator') and doc.bom_creator:
            _map_fields_from_bom_creator(doc)
        
        if not doc.name and doc.item:
            # Get branch abbreviation from the document
            branch_abbr = getattr(doc, 'branch_abbr', None)
            
            # Generate custom BOM name
            custom_name = get_custom_bom_name(doc.item, branch_abbr)
            if custom_name:
                # Ensure uniqueness by adding suffix when needed
                doc.name = get_available_bom_name(custom_name)
    except Exception as e:
        frappe.log_error(
            "BOM Before Insert Error",
            f"Failed to set custom name for BOM {getattr(doc, 'item', 'None')}: {str(e)}"
        )

def before_validate(doc, method=None):
    set_branch_details(doc, method)
    # Populate BOM-level drawing/spec fields from Item if missing on BOM
    try:
        if getattr(doc, "item", None):
            item_doc = frappe.get_doc("Item", doc.item)

            def set_if_empty(target, fieldname, value):
                if not getattr(target, fieldname, None) and value:
                    setattr(target, fieldname, value)

            # BOM header fields
            set_if_empty(doc, "custom_drawing_no", item_doc.get("custom_drawing_no"))
            set_if_empty(doc, "custom_pattern_drawing_no", item_doc.get("custom_pattern_drawing_no"))
            set_if_empty(doc, "custom_purchase_specification_no", item_doc.get("custom_purchase_specification_no"))
            set_if_empty(doc, "custom_drawing_rev_no", item_doc.get("custom_drawing_rev_no"))
            set_if_empty(doc, "custom_pattern_drawing_rev_no", item_doc.get("custom_pattern_drawing_rev_no"))
            set_if_empty(doc, "custom_purchase_specification_rev_no", item_doc.get("custom_purchase_specification_rev_no"))
    except Exception:
        # Do not block validation if Item fetch fails; log and continue
        frappe.log_error(f"Failed to backfill BOM custom fields from Item for {getattr(doc, 'name', '')}")

    # for item in doc.items:
    #     if item.bom_no:
    #         bom = frappe.get_doc("BOM", item.bom_no)
    #         if bom.custom_batch_no and bom.sales_order:
    #             frappe.throw(
    #                 (
    #                 f"<p>Item <strong>{item.item_code}</strong> cannot be submitted.</p>"
    #                 f"<p>The linked Bill of Materials (<strong>{item.bom_no}</strong>) is "
    #                 "configured for both a <strong>specific Sales Order</strong> and a "
    #                 "<strong>Batch Number</strong>, which is a conflict in production.</p>"
    #                 ),
    #                 ("Conflicting BOM Data")
    #             )

    # 1. Determine the Production Plan name (guarding against missing attributes)
    production_plan = getattr(doc, "production_plan", None)

    # 2. Fallback: check child rows if parent field isn’t set
    if not production_plan and doc.items:
        production_plan = next(
            (getattr(item, "production_plan", None) for item in doc.items),
            None
        )

    # 3. Exit early if no Production Plan found
    if not production_plan:
        return

    # 4. Fetch the Production Plan document safely
    try:
        pp = frappe.get_doc("Production Plan", production_plan)
    except frappe.DoesNotExistError:
        frappe.logger("generate_item").warning(
            f"Production Plan {production_plan} not found for BOM {doc.name}"
        )
        return

    # 5. Extract the custom batch number from the first PO Item (if set)
    batch_no = None
    if pp.po_items:
        batch_no = getattr(pp.po_items[0], "custom_batch_no", None)

    # 6. Apply batch number to BOM and all child items
    if batch_no:
        doc.custom_batch_no = batch_no
        for item in doc.items:
            item.custom_batch_no = batch_no

def clear_custom_fields_on_cancel(doc, method):
    doc.custom_batch_no = ""
    doc.sales_order = ""
    doc.db_update()
    
def on_submit(self,method):
    for row in self.items:
        if row.bom_no and self.sales_order and self.custom_batch_no:
            data = frappe.get_doc("BOM", row.bom_no)
            data.db_set("custom_batch_no",self.custom_batch_no)
            data.db_set("sales_order",self.sales_order) 


def before_save(doc,method):
    try:
        # Map fields from BOM Creator if this BOM was created from BOM Creator
        if hasattr(doc, 'bom_creator') and doc.bom_creator:
            _map_fields_from_bom_creator(doc)
        
        if getattr(doc, "item", None):
            item_doc = frappe.get_doc("Item", doc.item)

            def set_if_empty(target, fieldname, value):
                if not getattr(target, fieldname, None) and value:
                    setattr(target, fieldname, value)

            # BOM header fields
            set_if_empty(doc, "custom_drawing_no", item_doc.get("custom_drawing_no"))
            set_if_empty(doc, "custom_pattern_drawing_no", item_doc.get("custom_pattern_drawing_no"))
            set_if_empty(doc, "custom_purchase_specification_no", item_doc.get("custom_purchase_specification_no"))
            set_if_empty(doc, "custom_drawing_rev_no", item_doc.get("custom_drawing_rev_no"))
            set_if_empty(doc, "custom_pattern_drawing_rev_no", item_doc.get("custom_pattern_drawing_rev_no"))
            set_if_empty(doc, "custom_purchase_specification_rev_no", item_doc.get("custom_purchase_specification_rev_no"))
    except Exception:
        # Do not block validation if Item fetch fails; log and continue
        frappe.log_error(f"Failed to backfill BOM custom fields from Item for {getattr(doc, 'name', '')}")


def _map_fields_from_bom_creator(bom_doc):
    """
    Map fields from BOM Creator to BOM when BOM is created from BOM Creator.
    """
    try:
        bom_creator = frappe.get_doc("BOM Creator", bom_doc.bom_creator)
        
        # Map sales_order and custom_batch_no to parent BOM
        if hasattr(bom_creator, 'sales_order') and bom_creator.sales_order:
            if not bom_doc.sales_order:
                bom_doc.sales_order = bom_creator.sales_order
        
        if hasattr(bom_creator, 'custom_batch_no') and bom_creator.custom_batch_no:
            if not bom_doc.custom_batch_no:
                bom_doc.custom_batch_no = bom_creator.custom_batch_no
        
        # Map branch_abbr from sales order
        if bom_doc.sales_order and not getattr(bom_doc, 'branch_abbr', None):
            try:
                branch = frappe.get_cached_value("Sales Order", bom_doc.sales_order, "branch")
                if branch:
                    bom_doc.branch = branch
                    # Get branch_abbr from Branch master
                    branch_abbr = frappe.get_cached_value("Branch", branch, "abbr") or \
                                 frappe.get_cached_value("Branch", branch, "custom_abbr")
                    if branch_abbr:
                        bom_doc.branch_abbr = branch_abbr
                    else:
                        # Fallback mapping
                        branch_abbr_map = {'Rabale': 'RA', 'Nandikoor': 'NA', 'Sanand': 'SA'}
                        bom_doc.branch_abbr = branch_abbr_map.get(branch, None)
            except Exception:
                pass
        
        # Map drawing fields to BOM items
        _map_drawing_fields_from_bom_creator_items(bom_doc, bom_creator)
        
    except Exception as e:
        frappe.log_error(
            "Failed to map fields from BOM Creator",
            f"BOM: {bom_doc.name}, BOM Creator: {bom_doc.bom_creator}\n\n{frappe.get_traceback()}"
        )


def _map_drawing_fields_from_bom_creator_items(bom_doc, bom_creator):
    """
    Map drawing fields from BOM Creator items to BOM items.
    Handles both direct item_code matching and parent-child relationships.
    """
    try:
        # Build multiple maps for flexible matching
        # 1. Map by item_code
        bom_creator_item_map = {}
        # 2. Map by name (for parent-child relationships)
        bom_creator_item_by_name = {}
        # 3. Map by fg_reference_id (links child items to parent)
        bom_creator_item_by_fg_ref = {}
        # 4. Map by idx (row index)
        bom_creator_item_by_idx = {}
        
        for item in bom_creator.items:
            if item.item_code:
                bom_creator_item_map[item.item_code] = item
            if item.name:
                bom_creator_item_by_name[item.name] = item
            if hasattr(item, 'fg_reference_id') and item.fg_reference_id:
                if item.fg_reference_id not in bom_creator_item_by_fg_ref:
                    bom_creator_item_by_fg_ref[item.fg_reference_id] = []
                bom_creator_item_by_fg_ref[item.fg_reference_id].append(item)
            if hasattr(item, 'idx') and item.idx:
                bom_creator_item_by_idx[item.idx] = item
        
        # Process each BOM item
        for bom_item in bom_doc.items:
            item_code = bom_item.item_code
            bom_creator_item = None
            
            # Strategy 1: Direct item_code match
            bom_creator_item = bom_creator_item_map.get(item_code)
            
            # Strategy 2: If not found and bom_item has fg_reference_id, try to find by fg_reference_id
            if not bom_creator_item and hasattr(bom_item, 'fg_reference_id') and bom_item.fg_reference_id:
                fg_ref_items = bom_creator_item_by_fg_ref.get(bom_item.fg_reference_id, [])
                # Try to find exact match by item_code in fg_ref items
                for fg_item in fg_ref_items:
                    if fg_item.item_code == item_code:
                        bom_creator_item = fg_item
                        break
                # If still not found, use first item with matching fg_reference_id
                if not bom_creator_item and fg_ref_items:
                    bom_creator_item = fg_ref_items[0]
            
            # Strategy 3: If bom_item has parent_row_no, find parent and use its fields
            if not bom_creator_item and hasattr(bom_item, 'parent_row_no') and bom_item.parent_row_no:
                try:
                    parent_idx = int(bom_item.parent_row_no)
                    parent_item = bom_creator_item_by_idx.get(parent_idx)
                    if parent_item:
                        # For child items, we might want to use parent's fields or find child-specific item
                        # First try to find child item by matching item_code in items with same fg_reference_id
                        if hasattr(parent_item, 'fg_reference_id') and parent_item.fg_reference_id:
                            fg_ref_items = bom_creator_item_by_fg_ref.get(parent_item.fg_reference_id, [])
                            for fg_item in fg_ref_items:
                                if fg_item.item_code == item_code:
                                    bom_creator_item = fg_item
                                    break
                        # If still not found, use parent item (child inherits from parent)
                        if not bom_creator_item:
                            bom_creator_item = parent_item
                except (ValueError, TypeError):
                    pass
            
            if bom_creator_item:
                # Map all custom drawing fields
                custom_fields_to_map = [
                    'custom_drawing_no',
                    'custom_drawing_rev_no',
                    'custom_pattern_drawing_no',
                    'custom_pattern_drawing_rev_no',
                    'custom_purchase_specification_no',
                    'custom_purchase_specification_rev_no',
                ]
                
                for field_name in custom_fields_to_map:
                    if hasattr(bom_creator_item, field_name) and getattr(bom_creator_item, field_name):
                        if not getattr(bom_item, field_name, None):
                            setattr(bom_item, field_name, getattr(bom_creator_item, field_name))
                
                # Check if this item is expandable (is_expandable marked)
                is_expandable = getattr(bom_creator_item, 'is_expandable', False)
                
                if is_expandable:
                    # Map custom_drawing and custom_drawing_rev_no to custom_ga_drawing_no and custom_ga_drawing_rev_no
                    if hasattr(bom_creator_item, 'custom_drawing') and bom_creator_item.custom_drawing:
                        if not getattr(bom_item, 'custom_ga_drawing_no', None):
                            bom_item.custom_ga_drawing_no = bom_creator_item.custom_drawing
                    
                    if hasattr(bom_creator_item, 'custom_drawing_rev_no') and bom_creator_item.custom_drawing_rev_no:
                        if not getattr(bom_item, 'custom_ga_drawing_rev_no', None):
                            bom_item.custom_ga_drawing_rev_no = bom_creator_item.custom_drawing_rev_no
    
    except Exception as e:
        frappe.log_error(
            "Failed to map drawing fields from BOM Creator items",
            f"BOM: {bom_doc.name}\n\n{frappe.get_traceback()}"
        )
    



def set_branch_details(doc, method):
        """Set branch abbreviation and propagate branch to child items"""
        # Branch abbreviation mapping
        branch_abbr_map = {
            'Rabale': 'RA',
            'Nandikoor': 'NA',
            'Sanand': 'SA'
        }
        
        # Set branch abbreviation
        doc.branch_abbr = branch_abbr_map.get(doc.branch, '') if doc.branch else ''


@frappe.whitelist()
def get_available_batches(item, branch, current_bom=None):
    """Return list of Batch names not linked to any other BOM."""
    if not item or not branch:
        return []

    # 1️⃣ Get all batches already linked to other BOMs
    used_batches = frappe.get_all(
        "BOM",
        filters={
            "custom_batch_no": ["is", "set"],
            "docstatus": ["!=", 2],
            "name": ["!=", current_bom]
        },
        pluck="custom_batch_no"
    )

    # 2️⃣ Get all batches for this item + branch + Sales Order ref
    filters = {
        "item": item,
        "branch": branch,
        "reference_doctype": "Sales Order"
    }
    all_batches = frappe.get_all("Batch", filters=filters, pluck="name")

    # 3️⃣ Exclude those already used
    available_batches = [b for b in all_batches if b not in used_batches]

    return available_batches
