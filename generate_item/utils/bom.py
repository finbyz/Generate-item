import frappe
from generate_item.utils.bom_naming import get_custom_bom_name, get_available_bom_name

from frappe import _

def on_trash(doc, method):
    doc.sales_order = ""
    doc.custom_batch_no = ""
    items = frappe.get_all("Sales Order Item", filters={"bom_no": doc.name})
    for row in items:
        frappe.db.set_value("Sales Order Item", row.name, "bom_no", "")
    


def validate_bom_creation(doc, method=None):
    # If no Sales Order linked, skip validation
    if not doc.sales_order:
        return

    # Fetch Sales Order Items where line_status is NOT empty
    blocked_items = frappe.get_all(
        "Sales Order Item",
        filters={
            "parent": doc.sales_order,
            "line_status": ["is", "set"],
            "custom_batch_no" : doc.custom_batch_no   
        },
        fields=["item_code", "idx", "line_status"]
    )

    # If any line has line_status filled, block BOM creation
    if blocked_items:
        blocked_item_list = ", ".join(
            [f"Row {d.idx} ({d.item_code}) - Status: {d.line_status}" 
            for d in blocked_items]
        )

        frappe.throw(
            _("Cannot create BOM because the following Sales Order lines have a status set: {0}")
            .format(blocked_item_list)
        )

def before_insert(doc, method=None):
    """Set custom BOM name before document is inserted"""
    try:
        # Map fields from BOM Creator if this BOM was created from BOM Creator
        if hasattr(doc, 'bom_creator') and doc.bom_creator:
            _map_fields_from_bom_creator(doc)
        
        # Ensure branch_abbr is set before generating name
        # This is needed when BOM is created from Sales Order or other sources
        branch_abbr = getattr(doc, 'branch_abbr', None)
        if not branch_abbr and getattr(doc, 'branch', None):
            try:
                # Get branch_abbr from Branch master
                branch_abbr = frappe.get_cached_value("Branch", doc.branch, "abbr") or \
                             frappe.get_cached_value("Branch", doc.branch, "custom_abbr")
                if branch_abbr:
                    doc.branch_abbr = branch_abbr
                else:
                    # Fallback mapping
                    branch_abbr_map = {'Rabale': 'RA', 'Nandikoor': 'NA', 'Sanand': 'SA'}
                    branch_abbr = branch_abbr_map.get(doc.branch, None)
                    if branch_abbr:
                        doc.branch_abbr = branch_abbr
            except Exception:
                pass
        
        # Also try to get branch_abbr from sales_order if branch is not set
        if not getattr(doc, 'branch_abbr', None) and hasattr(doc, 'sales_order') and doc.sales_order:
            try:
                branch = frappe.get_cached_value("Sales Order", doc.sales_order, "branch")
                if branch:
                    doc.branch = branch
                    branch_abbr = frappe.get_cached_value("Branch", branch, "abbr") or \
                                 frappe.get_cached_value("Branch", branch, "custom_abbr")
                    if branch_abbr:
                        doc.branch_abbr = branch_abbr
                    else:
                        # Fallback mapping
                        branch_abbr_map = {'Rabale': 'RA', 'Nandikoor': 'NA', 'Sanand': 'SA'}
                        branch_abbr = branch_abbr_map.get(branch, None)
                        if branch_abbr:
                            doc.branch_abbr = branch_abbr
            except Exception:
                pass
        
        if not doc.name and doc.item:
            # Get branch abbreviation from the document (now it should be set)
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
    validate_bom_batch_reference(doc, method)
    validate_bom_creation(doc, method)
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
    # Check if BOM is used in any Production Plan (main or sub-assembly items) that is in draft state
    # 1️⃣ From Production Plan Item table
    production_plan_items = frappe.get_all(
        "Production Plan Item",
        filters={"bom_no": doc.name},
        fields=["parent"],
        limit=100
    )

    # 2️⃣ From Production Plan Sub Assembly Item table
    sub_assembly_items = frappe.get_all(
        "Production Plan Sub Assembly Item",
        filters={"bom_no": doc.name},
        fields=["parent"],
        limit=100
    )

    # 3️⃣ Collect unique Production Plan parents from both tables
    production_plan_names = list(
        set(
            [item.parent for item in production_plan_items]
            + [item.parent for item in sub_assembly_items]
        )
    )

    if production_plan_names:
        # Check which Production Plans are in draft state
        draft_production_plans = frappe.get_all(
            "Production Plan",
            filters={
                "name": ["in", production_plan_names],
                "docstatus": 0,  # Draft state
            },
            fields=["name"],
            limit=100
        )

        if draft_production_plans:
            plan_names = ", ".join([plan.name for plan in draft_production_plans])
            frappe.throw(
                f"Cannot cancel BOM <b>{doc.name}</b> because it is referenced in the following Production Plan(s) that are in draft state: <b>{plan_names}</b>. Please remove the BOM from these Production Plans or submit/cancel them first.",
                title="BOM Cannot Be Cancelled",
            )
    
    if getattr(doc, "name", None):
        clear_batch_and_so_from_child_boms(doc.name)

    doc.custom_batch_no = ""
    doc.sales_order = ""
    doc.db_update()
    
def propagate_batch_and_so_to_child_boms(bom_name, sales_order, custom_batch_no, visited=None):
    """
    Recursively propagate sales_order and custom_batch_no to all descendant child BOMs.
    """
    if visited is None:
        visited = set()

    if not bom_name or bom_name in visited:
        return

    visited.add(bom_name)

    child_boms = frappe.get_all(
        "BOM Item",
        filters={"parent": bom_name, "bom_no": ["is", "set"]},
        pluck="bom_no"
    )

    for child_bom in set(child_boms):
        if child_bom and child_bom not in visited and frappe.db.exists("BOM", child_bom):
            frappe.db.set_value(
                "BOM",
                child_bom,
                {
                    "custom_batch_no": custom_batch_no,
                    "sales_order": sales_order
                },
                update_modified=False
            )
            propagate_batch_and_so_to_child_boms(child_bom, sales_order, custom_batch_no, visited)


def clear_batch_and_so_from_child_boms(bom_name, visited=None):
    """
    Recursively clear custom_batch_no and sales_order from all descendant child BOMs.
    """
    if visited is None:
        visited = set()

    if not bom_name or bom_name in visited:
        return

    visited.add(bom_name)

    child_boms = frappe.get_all(
        "BOM Item",
        filters={"parent": bom_name, "bom_no": ["is", "set"]},
        pluck="bom_no"
    )

    for child_bom in set(child_boms):
        if child_bom and child_bom not in visited and frappe.db.exists("BOM", child_bom):
            frappe.db.set_value(
                "BOM",
                child_bom,
                {
                    "custom_batch_no": "",
                    "sales_order": ""
                },
                update_modified=False
            )
            clear_batch_and_so_from_child_boms(child_bom, visited)


def on_submit(self, method=None):
    if self.sales_order and self.custom_batch_no and getattr(self, "name", None):
        propagate_batch_and_so_to_child_boms(self.name, self.sales_order, self.custom_batch_no)

    # Auto-create Draft Production Plan using native flow
    try:
        create_draft_production_plan_from_bom(self)
    except Exception as e:
        error_msg = f"Failed to auto-create Production Plan for BOM {getattr(self, 'name', '')}: {str(e)}"
        frappe.msgprint(
            _(error_msg) + "<br><br>" + _("Please check Error Log for the complete traceback."),
            title=_("Production Plan Creation Failed"),
            indicator="red",
        )
        frappe.log_error(
            title=f"Production Plan Auto Create Error ({getattr(self, 'name', '')})",
            message=f"{error_msg}\n\n{frappe.get_traceback()}",
        )
 


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
        
        # Propagate branch to all BOM items
        if doc.branch and doc.items:
            for item in doc.items:
                if not getattr(item, 'branch', None):
                    item.branch = doc.branch


@frappe.whitelist()
def get_available_batches(current_bom=None):
    """Return Batch names not linked to any other active BOM."""

    # 1️⃣ Batches already used in BOMs
    used_batches = frappe.get_all(
        "BOM",
        filters={
            "custom_batch_no": ["is", "set"],
            "docstatus": ["!=", 2],
            "name": ["!=", current_bom]
        },
        pluck="custom_batch_no"
    )

    # 2️⃣ All batches in system
    all_batches = frappe.get_all("Batch", pluck="name")

    # 3️⃣ Exclude used ones
    available_batches = [b for b in all_batches if b not in used_batches]

    return available_batches



@frappe.whitelist()
def get_valid_batches(doctype, txt, searchfield, start, page_len, filters):
    item = filters.get("item")
    branch = filters.get("branch")
    bom_name = filters.get("bom_name") or ""

    return frappe.db.sql("""
        SELECT
            b.name
        FROM
            `tabBatch` b
        INNER JOIN
            `tabSales Order` so
                ON so.name = b.reference_name

        LEFT JOIN
            `tabSales Order Item` soi
                ON soi.parent = so.name
                AND soi.item_code = b.item
                AND soi.custom_batch_no = b.name

        
        WHERE
            b.item = %(item)s
            AND b.reference_doctype = 'Sales Order'
            AND so.branch = %(branch)s


            -- ✅ Only allow batches where line_status is empty or NULL
            AND (
                soi.line_status IS NULL
                OR soi.line_status = ''
            )

            


            -- 🚫 EXCLUDE batch already used in ANY BOM
            AND b.name NOT IN (
                SELECT custom_batch_no
                FROM `tabBOM`
                WHERE
                    custom_batch_no IS NOT NULL
                    AND custom_batch_no != ''
                    AND docstatus IN (0, 1)
                    AND name != %(bom_name)s
            )

            AND b.name LIKE %(txt)s
        ORDER BY
            b.creation DESC
        LIMIT %(start)s, %(page_len)s
    """, {
        "item": item,
        "branch": branch,
        "bom_name": bom_name,
        "txt": f"%{txt}%",
        "start": start,
        "page_len": page_len
    })
def validate_bom_batch_reference(self,method):
        for row in self.items:
            if not row.bom_no:
                continue

            custom_batch_no = frappe.db.get_value(
                "BOM",
                row.bom_no,
                "custom_batch_no"
            )

            if custom_batch_no:
                frappe.throw(
                    f"""
                    <b>Row {row.idx} (Row Name: {row.name})</b><br>
                    Batch No reference <b>{custom_batch_no}</b> is already set
                    in BOM <b>{row.bom_no}</b> for item
                    <b>{row.item_code}</b>.<br><br>
                    Please use a BOM without batch reference
                    or remove it first.
                    """,
                    title="Invalid BOM Reference"
                )
@frappe.whitelist()
def get_sub_assembly_boms(doctype, txt, searchfield, start, page_len, filters):
    item_code = filters.get("item_code")
    branch = filters.get("branch")

    return frappe.db.sql("""
        SELECT
            b.name,
            b.item,
            b.branch
        FROM
            `tabBOM` b
        WHERE
            b.item = %(item_code)s
            AND b.is_active = 1
            AND b.docstatus IN (0, 1)
            AND (b.branch = %(branch)s OR b.branch IS NULL OR b.branch = '')
            AND (b.custom_batch_no IS NULL OR b.custom_batch_no = '')
            AND b.name LIKE %(txt)s
        ORDER BY b.creation DESC
        LIMIT %(start)s, %(page_len)s
    """, {
        "item_code": item_code,
        "branch": branch,
        "txt": f"%{txt}%",
        "start": start,
        "page_len": page_len
    })                
    
    

import frappe
from frappe import _
from frappe.utils import flt, get_link_to_form, now_datetime, nowdate
from erpnext.manufacturing.doctype.production_plan.production_plan import (
    get_items_for_material_requests,
)

SAVEPOINT = "pp_from_bom"

BRANCH_CONFIG = {
    "Rabale": {
        "series": "PPOR.fiscal.####",
        "semi": "Rabale Semi Finished - SVIPL",
        "alloc": "Rabale Order Allocated - SVIPL",
    },
    "Nandikoor": {
        "series": "PPON.fiscal.####",
        "semi": "Nandikoor Semi Finished - SVIPL",
        "alloc": "Nandikoor Order Allocated - SVIPL",
    },
    "Sanand": {
        "series": "PPOS.fiscal.####",
        "semi": "Sanand Semi Finished - SVIPL",
        "alloc": "Sanand Order Allocated - SVIPL",
    },
}
DEFAULT_SERIES = "PPOS.fiscal.####"


def _branch_config(branch):
    for key, cfg in BRANCH_CONFIG.items():
        if branch and key in branch:
            return cfg
    return {}


def _notify(bom_name, title, msg, indicator="orange", log=None):
    """Show a message to the user; write an Error Log only when `log` is given."""
    frappe.msgprint(msg, title=_(title), indicator=indicator)
    if log:
        frappe.log_error(
            title=f"{title}: {bom_name}"[:140],
            message=log,
            reference_doctype="BOM",
            reference_name=bom_name,
        )


def get_default_transfer_warehouses(branch):
    if not branch:
        return []
    store_wh = frappe.db.get_value(
        "Warehouse",
        {"branch": branch, "store_warehouse": 1, "disabled": 0, "is_group": 0},
        "name",
    )
    return [{"warehouse": store_wh}] if store_wh else []

AUTO_PP_FIELD = "auto_create_production_plan_on_bom_submit"

def create_draft_production_plan_from_bom(bom_doc):
    """Triggered on BOM submit. Never blocks the BOM submit."""
    # Automation switch in Manufacturing Settings
    if not frappe.db.get_single_value("Manufacturing Settings", AUTO_PP_FIELD):
        return  # unchecked -> do nothing (no message, no Error Log)
    frappe.db.savepoint(SAVEPOINT)
    try:
        _create_pp(bom_doc)
    except Exception as e:
        frappe.db.rollback(save_point=SAVEPOINT)
        _notify(
            bom_doc.name,
            "Production Plan Error",
            _("Production Plan was NOT created for BOM <b>{0}</b> because of an unexpected error:<br>{1}").format(
                bom_doc.name, frappe.utils.escape_html(str(e))
            ),
            indicator="red",
            log=f"BOM: {bom_doc.name}\n\n{frappe.get_traceback()}",
        )


def _create_pp(bom_doc):
    bom_name = bom_doc.name
    sales_order = getattr(bom_doc, "sales_order", None)
    batch_no = getattr(bom_doc, "custom_batch_no", None)
    item_code = getattr(bom_doc, "item", None)

    # 1. Required fields
    if not sales_order or not batch_no:
        return _notify(
            bom_name,
            "Production Plan Skipped",
            _("Production Plan was NOT created for BOM <b>{0}</b>: Sales Order or Batch No is missing.<br><br>"
              "<b>Sales Order:</b> {1}<br><b>Batch No:</b> {2}").format(
                bom_name, sales_order or _("Not Set"), batch_no or _("Not Set")
            ),
            log=f"BOM: {bom_name}\nItem: {item_code}\nSales Order: {sales_order}\nBatch No: {batch_no}",
        )

    # 2. Duplicate check (expected case: message only, no Error Log)
    existing = frappe.db.sql(
        """
        SELECT pp.name, pp.docstatus
        FROM `tabProduction Plan` pp
        INNER JOIN `tabProduction Plan Item` ppi ON ppi.parent = pp.name
        WHERE pp.docstatus IN (0, 1) AND ppi.bom_no = %s
        LIMIT 1
        """,
        (bom_name,),
        as_dict=True,
    )
    if existing:
        return _notify(
            bom_name,
            "Production Plan Already Exists",
            _("Production Plan already exists for BOM <b>{0}</b>: {1} (Status: <b>{2}</b>).<br>"
              "A duplicate will not be created.").format(
                bom_name,
                get_link_to_form("Production Plan", existing[0].name),
                _("Draft") if existing[0].docstatus == 0 else _("Submitted"),
            ),
            indicator="blue",
        )

    # 3. Sales Order
    so = frappe.db.get_value(
        "Sales Order",
        sales_order,
        ["docstatus", "company", "branch", "transaction_date", "customer", "base_grand_total"],
        as_dict=True,
    )
    if not so:
        return _notify(
            bom_name, "Sales Order Not Found",
            _("Linked Sales Order <b>{0}</b> does not exist.").format(sales_order),
            indicator="red", log=f"BOM: {bom_name}\nSales Order {sales_order} not found.",
        )
    if so.docstatus != 1:
        label = _("Draft") if so.docstatus == 0 else _("Cancelled")
        return _notify(
            bom_name, "Sales Order Not Submitted",
            _("Sales Order {0} is <b>{1}</b>. Please submit it first.").format(
                get_link_to_form("Sales Order", sales_order), label
            ),
        )

    # 4. Sales Order Item (item + batch)
    so_item = frappe.db.get_value(
        "Sales Order Item",
        {"parent": sales_order, "item_code": item_code, "custom_batch_no": batch_no, "docstatus": 1},
        ["name", "qty", "work_order_qty", "warehouse", "description", "stock_uom", "branch"],
        as_dict=True,
    )
    if not so_item:
        batches = ", ".join(
            frappe.get_all(
                "Sales Order Item",
                filters={"parent": sales_order, "item_code": item_code, "docstatus": 1},
                pluck="custom_batch_no",
            )
        ) or _("None")
        return _notify(
            bom_name, "Sales Order Line Not Found",
            _("No line in Sales Order <b>{0}</b> for Item <b>{1}</b> and Batch <b>{2}</b>.<br><br>"
              "<b>Batches present:</b> {3}").format(sales_order, item_code, batch_no, batches),
            log=f"BOM: {bom_name}\nItem: {item_code}\nBOM Batch: {batch_no}\nSO: {sales_order}\nSO Batches: {batches}",
        )

    pending_qty = flt(so_item.qty) - flt(so_item.work_order_qty)
    if pending_qty <= 0:
        return _notify(
            bom_name, "Quantity Already Planned",
            _("Item <b>{0}</b> (Batch <b>{1}</b>) is already fully planned or produced.<br><br>"
              "<b>Ordered Qty:</b> {2}<br><b>Work Order Qty:</b> {3}").format(
                item_code, batch_no, so_item.qty, so_item.work_order_qty
            ),
        )

    # 5. Branch / warehouses / naming series
    branch = bom_doc.branch or so_item.branch or so.branch
    company = bom_doc.company or so.company
    cfg = _branch_config(branch)
    for_warehouse = cfg.get("alloc")
    if not for_warehouse and branch:
        for_warehouse = frappe.db.get_value(
            "Warehouse",
            {"branch": branch, "store_warehouse": 1, "disabled": 0, "is_group": 0},
            "name",
        )

    # 6. Build Production Plan
    pp = frappe.new_doc("Production Plan")
    pp.company = company
    pp.branch = branch
    pp.naming_series = cfg.get("series", DEFAULT_SERIES)
    pp.posting_date = nowdate()
    pp.for_warehouse = for_warehouse
    pp.sub_assembly_warehouse = cfg.get("semi")
    pp.get_items_from = "Sales Order"
    pp.item_code = item_code
    pp.include_non_stock_items = 1
    pp.include_subcontracted_items = 1

   
    pp.append("sales_orders", {
        "sales_order": sales_order,
        "sales_order_date": so.transaction_date,
        "customer": so.customer,
        "grand_total": so.base_grand_total,
        "branch": branch,
    })

    warnings = []

    def _warn(step):
        warnings.append(step)
        frappe.log_error(
            title=f"PP {step} error: {bom_name}"[:140],
            message=f"BOM: {bom_name}\nStep: {step}\n\n{frappe.get_traceback()}",
            reference_doctype="BOM",
            reference_name=bom_name,
        )

    # Step 1: Finished goods
    try:
        pp.get_items()
    except Exception:
        _warn("get_items")

    matched = [r for r in (pp.po_items or []) if r.custom_batch_no == batch_no]
    if matched:
        for row in matched:
            row.bom_no = bom_name
            row.branch = row.get("branch") or branch
        pp.po_items = matched
    else:
        # Fallback: build the row straight from the verified SO line
        pp.set("po_items", [])
        pp.append("po_items", {
            "warehouse": so_item.warehouse,
            "item_code": item_code,
            "description": so_item.description or "",
            "stock_uom": so_item.stock_uom or "",
            "bom_no": bom_name,
            "planned_qty": pending_qty,
            "pending_qty": pending_qty,
            "actual_qty": pending_qty,
            "planned_start_date": now_datetime(),
            "sales_order": sales_order,
            "sales_order_item": so_item.name,
            "custom_batch_no": batch_no,
            "branch": branch,
        })

    # Steps 2 & 3 run with the projected-qty options relaxed, then restored
    saved = {
        "skip_available_sub_assembly_item": pp.get("skip_available_sub_assembly_item"),
        "ignore_existing_ordered_qty": pp.get("ignore_existing_ordered_qty"),
    }
    pp.skip_available_sub_assembly_item = 0
    pp.ignore_existing_ordered_qty = 1
    try:
        try:
            pp.get_sub_assembly_items()
        except Exception:
            _warn("sub-assembly")

        try:
            items = get_items_for_material_requests(
                pp.as_json(), warehouses=get_default_transfer_warehouses(branch) or None
            )
            pp.set("mr_items", [])
            for d in items or []:
                row = dict(d)
                row.pop("name", None)
                row.setdefault("sales_order", sales_order)
                if not row.get("batch_no"):
                    row["batch_no"] = batch_no
                pp.append("mr_items", row)
        except Exception:
            _warn("raw material")
    finally:
        pp.update(saved)

    # 7. Save as Draft
    pp.calculate_total_planned_qty()
    pp.calculate_total_produced_qty()
    pp.flags.ignore_permissions = True
    pp.insert()

    msg = _("Draft Production Plan <b>{0}</b> created for BOM <b>{1}</b> (Batch: <b>{2}</b>).").format(
        get_link_to_form("Production Plan", pp.name), bom_name, batch_no
    )
    if warnings:
        msg += "<br><br><b>{0}</b> {1}".format(
            _("Warning: these steps failed and need a manual check:"), ", ".join(warnings)
        )
    frappe.msgprint(
        msg,
        title=_("Production Plan Created"),
        indicator="orange" if warnings else "green",
    )