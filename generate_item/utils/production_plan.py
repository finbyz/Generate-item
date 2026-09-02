from pydoc import doc

import frappe
from frappe import _

from generate_item.generate_item.modification_task_utils.modification_task import create_wo_po_tasks_on_gate_update
from erpnext.manufacturing.doctype.production_plan.production_plan import get_exploded_items

def before_save(doc, method):
    # Handle po_items
    if hasattr(doc, "po_items") and doc.po_items:
        for row in doc.po_items:
            _populate_production_plan_item_from_sales_order(doc, row)
    
    # Handle sub_assembly_items
    if hasattr(doc, "sub_assembly_items") and doc.sub_assembly_items:
        for row in doc.sub_assembly_items:
            _populate_subassembly_item_from_sales_order(doc, row)

def _populate_production_plan_item_from_sales_order(doc, row):
    """Populate production plan item with values from Sales Order Items"""
    try:
        sales_order = getattr(row, "sales_order", None)
        sales_order_item = getattr(row, "sales_order_item", None)
        item_code = getattr(row, "item_code", None)

        # Fallback: if items were combined, SO link is in prod_plan_references
        if not sales_order and hasattr(doc, "prod_plan_references") and doc.prod_plan_references:
            for ref in doc.prod_plan_references:
                if getattr(ref, "item_reference", None) == getattr(row, "name", None):
                    sales_order = getattr(ref, "sales_order", None)
                    sales_order_item = getattr(ref, "sales_order_item", None)
                    if sales_order:
                        break
        if not sales_order:
            return

        # Prefer exact Sales Order Item link; fallback to first matching by item_code in SO
        soi_filters = {"parent": sales_order}
        if sales_order_item:
            soi_filters["name"] = sales_order_item
        elif item_code:
            soi_filters["item_code"] = item_code

        soi = frappe.get_all(
            "Sales Order Item",
            filters=soi_filters,
            fields=["name", "custom_batch_no", "bom_no", "idx", "branch"],
            order_by="idx asc",
            limit=1,
        )

        if not soi:
            return

        soi = soi[0]

        # Force-set from Sales Order Item only
        row.custom_batch_no = soi.get("custom_batch_no") or None
        # Ensure branch propagates into po_items for downstream logic
        if hasattr(row, "branch"):
            row.branch = soi.get("branch") or None

        # Set BOM only if BOM matches Sales Order and custom_batch_no; accept active or default BOMs
        selected_bom = None
        if item_code and sales_order and row.custom_batch_no:
            try:
                bom_candidate = frappe.get_all(
                    "BOM",
                    filters={
                        "item": item_code,
                        "sales_order": sales_order,
                        "custom_batch_no": row.custom_batch_no,
                    },
                    or_filters=[{"is_active": 1}, {"is_default": 1}],
                    fields=["name"],
                    order_by="modified desc",
                    limit=1,
                )
                if bom_candidate:
                    selected_bom = bom_candidate[0]["name"]
            except Exception:
                selected_bom = None

        if selected_bom:
            row.bom_no = selected_bom
        # If no matching BOM is found, keep the existing bom_no intact

    except Exception as e:
        frappe.log_error(
            message=_(
                "Failed to sync batch/BOM from Sales Order for Production Plan {0} row {1}: {2}"
            ).format(doc.name, getattr(row, "name", ""), str(e)),
            title=_("Production Plan SO Sync Error"),
        )

def _populate_subassembly_item_from_sales_order(doc, row):
    """Populate subassembly item with values from Sales Order Items"""
    try:
        # Get the production plan item that this subassembly item is related to
        production_plan_item = None
        if hasattr(row, 'production_plan_item') and row.production_plan_item:
            production_plan_item = frappe.get_doc("Production Plan Item", row.production_plan_item)
        else:
            # Try to find the production plan item by item_code
            pp_items = frappe.get_all(
                "Production Plan Item",
                filters={"parent": doc.name, "item_code": row.production_item},
                fields=["name", "sales_order", "sales_order_item"],
                limit=1
            )
            if pp_items:
                production_plan_item = frappe.get_doc("Production Plan Item", pp_items[0].name)

        if not production_plan_item:
            return

        sales_order = getattr(production_plan_item, "sales_order", None)
        sales_order_item = getattr(production_plan_item, "sales_order_item", None)
        item_code = getattr(production_plan_item, "item_code", None)

        if not sales_order:
            return

        # Prefer exact Sales Order Item link; fallback to first matching by item_code in SO
        soi_filters = {"parent": sales_order}
        if sales_order_item:
            soi_filters["name"] = sales_order_item
        elif item_code:
            soi_filters["item_code"] = item_code

        soi = frappe.get_all(
            "Sales Order Item",
            filters=soi_filters,
            fields=["name", "custom_batch_no", "bom_no", "idx", "branch"],
            order_by="idx asc",
            limit=1,
        )

        if not soi:
            return

        soi = soi[0]

        # Set custom fields from Sales Order Item
        if hasattr(row, 'custom_batch_no'):
            row.custom_batch_no = soi.get("custom_batch_no") or None
        if hasattr(row, 'branch'):
            row.branch = soi.get("branch") or None

    except Exception as e:
        frappe.log_error(
            message=_(
                "Failed to sync batch/branch from Sales Order for Production Plan {0} subassembly item {1}: {2}"
            ).format(doc.name, getattr(row, "name", ""), str(e)),
            title=_("Production Plan Subassembly SO Sync Error"),
        )


@frappe.whitelist()
def set_actual_qty_for_child_row(cdt, cdn):
    # Fetch the planned_qty value from the child row
    planned_qty = frappe.db.get_value(cdt, cdn, 'planned_qty') or 0

    # Get the current actual_qty value
    actual_qty = frappe.db.get_value(cdt, cdn, 'actual_qty') or 0

    # Set actual_qty = planned_qty only if actual_qty is 0 or None
    if not actual_qty:
        frappe.db.set_value(cdt, cdn, 'actual_qty', planned_qty)



import frappe
from erpnext.manufacturing.doctype.production_plan.production_plan import (
    get_items_for_material_requests,
)
from collections import defaultdict
from frappe.utils import flt


def _validate_schema_match(source_doctype, target_doctype):
    """One-time set comparison — cheap, meta is cached by frappe.get_meta."""
    skip = {"name", "parent", "parentfield", "parenttype", "doctype",
            "owner", "creation", "modified", "modified_by", "idx"}

    source_fields = {df.fieldname for df in frappe.get_meta(source_doctype).fields
                      if df.fieldname not in skip}
    target_fields = {df.fieldname for df in frappe.get_meta(target_doctype).fields
                      if df.fieldname not in skip}

    missing = source_fields - target_fields
    if missing:
        frappe.throw(
            "Tracking DocType '{0}' is missing field(s) present on source '{1}': {2}."
            .format(target_doctype, source_doctype, ", ".join(sorted(missing)))
        )


def _copy_child_table(pp, source_fieldname, target_fieldname):
    source_rows = pp.get(source_fieldname) or []
    if not source_rows:
        return

    parent_meta = frappe.get_meta(pp.doctype)
    source_doctype = parent_meta.get_field(source_fieldname).options
    target_doctype = parent_meta.get_field(target_fieldname).options

    _validate_schema_match(source_doctype, target_doctype)

    system_fields = {"name", "idx", "parent", "parentfield", "parenttype",
                      "doctype", "owner", "creation", "modified", "modified_by"}

    # append() only builds in-memory objects — no DB hit per row.
    for row in source_rows:
        cleaned = {k: v for k, v in row.as_dict().items() if k not in system_fields}
        pp.append(target_fieldname, cleaned)


def _capture_original_data_if_needed(pp):
    if pp.get("original_data"):
        return False

    pp.set("tracking_assembly_items", [])
    pp.set("tracking_sub_assembly_items", [])
    pp.set("tracking_raw_materials", [])

    _copy_child_table(pp, "po_items", "tracking_assembly_items")
    _copy_child_table(pp, "sub_assembly_items", "tracking_sub_assembly_items")
    _copy_child_table(pp, "mr_items", "tracking_raw_materials")

    pp.original_data = 1
    return True


def _sync_planned_qty_from_sales_orders(pp):
    """Batch-fetch all Sales Order Item data in a single query instead of
    one query per po_item row (fixes N+1), and propagate FG exchanges
    (item_code change on the SO) into the Production Plan row's
    item_code/description/stock_uom. BOM is intentionally left untouched."""

    so_item_names = [d.sales_order_item for d in pp.po_items if d.sales_order_item]
    if not so_item_names:
        return False

    so_item_data = frappe.get_all(
        "Sales Order Item",
        filters={"name": ["in", so_item_names]},
        fields=["name", "qty", "item_code"],
    )
    so_map = {row.name: row for row in so_item_data}

    desc_cache = {}
    changed = False

    for item in pp.po_items:
        so_row = so_map.get(item.sales_order_item)
        if not so_row or not so_row.qty:
            continue

        # --- 1. Quantity sync (existing behavior) ---
        if item.planned_qty != so_row.qty:
            item.planned_qty = so_row.qty
            item.actual_qty = so_row.qty
            item.pending_qty = so_row.qty
            changed = True

        # --- 2. FG exchange sync: item_code changed on the SO ---
        new_item_code = so_row.item_code
        if new_item_code and new_item_code != item.item_code:
            item.item_code = new_item_code


            if new_item_code not in desc_cache:
                desc_cache[new_item_code] = frappe.db.get_value(
                    "Item", new_item_code, "description"
                )
            if desc_cache[new_item_code]:
                item.description = desc_cache[new_item_code]

            changed = True

    return changed


def _get_default_transfer_warehouses(pp):
    if not pp.branch:
        return []
    store_wh = frappe.db.get_value(
        "Warehouse",
        {"branch": pp.branch, "store_warehouse": 1, "disabled": 0, "is_group": 0},
        "name",
    )
    return [{"warehouse": store_wh}] if store_wh else []
# working method 

@frappe.whitelist()
def get_update_for_submitted_pp(docname):
    pp = frappe.get_doc("Production Plan", docname)
    validate_work_orders_before_update(pp.name)
    was_submitted = pp.docstatus == 1

    # --- Step 2 & 3: Set status Close / Docstatus 0 ---
    if was_submitted:
        pp.set_status(close=True, update_bin=True)
        pp.db_set("docstatus", 0, update_modified=False)
        pp.reload()
        pp.flags.ignore_validate = True
        pp.flags.ignore_validate_update_after_submit = True
        pp.flags.ignore_permissions = True

    # All in-memory mutations happen first — nothing is written to DB yet.
    captured = _capture_original_data_if_needed(pp)

    # --- Step 4: Fetch Assembly Update (FG qty/item_code sync from SO) ---
    changed = _sync_planned_qty_from_sales_orders(pp)

    # --- Step 5: Uncheck "Consider Projected Qty" checkboxes for
    # Sub Assembly (skip_available_sub_assembly_item) and Raw Material
    # (ignore_existing_ordered_qty), caching originals so we can restore
    # them exactly — including None, so don't coerce with `or 0` here. ---
    checkbox_cache = {
        "skip_available_sub_assembly_item": pp.get("skip_available_sub_assembly_item"),
        "ignore_existing_ordered_qty": pp.get("ignore_existing_ordered_qty"),
    }
    pp.skip_available_sub_assembly_item = 0
    pp.ignore_existing_ordered_qty = 1

    # --- Step 6: Fetch Sub Assembly updates (unfiltered by projected qty) ---
    pp.get_sub_assembly_items()

    # --- Step 7: Fetch Raw Material updates (unfiltered by existing ordered qty) ---
    warehouses = _get_default_transfer_warehouses(pp)
    items = get_items_for_material_requests(pp.as_json(), warehouses=warehouses or None)
    pp.set("mr_items", [])
    for d in items:
        pp.append("mr_items", d)

    # --- Step 8: Revert checkbox state from cache ---
    pp.skip_available_sub_assembly_item = checkbox_cache["skip_available_sub_assembly_item"]
    pp.ignore_existing_ordered_qty = checkbox_cache["ignore_existing_ordered_qty"]

    # Clear both modification flags in a single UPDATE instead of two.
    pp.production_plan_updated = 1
    pp.work_order_updated = 1
    frappe.db.set_value(
        "Production Plan", pp.name,
        {"bom_modification": "", "sales_order_modification": ""},
        update_modified=False,
    )
    pp.bom_modification = ""
    pp.sales_order_modification = ""

    # --- Step 9: Save (persists the reverted checkbox values, not the
    # temporary 0/0 used for fetching) ---
    pp.calculate_total_planned_qty()
    pp.calculate_total_produced_qty()
    pp.save(ignore_permissions=True)

    _flag_work_orders_for_update(pp.name)

    # --- Step 10: Submit ---
    if was_submitted:
        pp.submit()
        create_wo_po_tasks_on_gate_update(pp)

    # --- Step 11: Set status Re-open ---
    pp.set_status(close=False, update_bin=True)

    # frappe.db.commit()
    return {
        "success": True,
        "planned_qty_updated": changed,
        "original_data_captured_now": captured,
    }


# @frappe.whitelist()
# def get_update_for_submitted_pp(docname):
#     pp = frappe.get_doc("Production Plan", docname)
#     validate_work_orders_before_update(pp.name)
#     was_submitted = pp.docstatus == 1

#     if was_submitted:
#         pp.db_set("docstatus", 0, update_modified=False)
#         pp.reload()

#         pp.flags.ignore_permissions = True

#     captured = _capture_original_data_if_needed(pp)
#     changed = _sync_planned_qty_from_sales_orders(pp)

#     # get_sub_assembly_items() reads pp.po_items in memory — no save needed first.
#     pp.get_sub_assembly_items()

#     # Clear both modification flags in a single UPDATE instead of two.
#     pp.production_plan_updated = 1
#     frappe.db.set_value(
#         "Production Plan", pp.name,
#         {"bom_modification": "", "sales_order_modification": ""},
#         update_modified=False,
#     )
#     pp.bom_modification = ""
#     pp.sales_order_modification = ""

#     warehouses = _get_default_transfer_warehouses(pp)
#     items = get_items_for_material_requests(pp.as_json(), warehouses=warehouses or None)

#     # Merge instead of wipe-and-rebuild: existing rows keep their original
#     # `name` (and therefore stay correctly linked to any Material Request
#     # already created against them). See _merge_mr_items() for details.
#     _merge_mr_items(pp, items)

#     pp.save(ignore_permissions=True)

#     # flag all non-cancelled linked Work Orders for update
#     _flag_work_orders_for_update(pp.name)

#     if was_submitted:
#         pp.submit()
#         create_wo_po_tasks_on_gate_update(pp)

#     # Auto-creation of Material Requests has been intentionally removed from
#     # this flow. MR creation now happens ONLY via the explicit "Create
#     # Material Request" button -> create_material_request_for_pending_items().

#     return {
#         "success": True,
#         "planned_qty_updated": changed,
#         "original_data_captured_now": captured,
#     }




# Fields we never overwrite when updating an existing mr_items row in place —
# these are either system-managed or identity fields, and must be left alone.
_MR_ITEM_PROTECTED_FIELDS = {
    "name", "idx", "doctype", "parent", "parentfield", "parenttype",
    "owner", "creation", "modified", "modified_by", "docstatus",
    "material_request_plan_item",
}


def _merge_mr_items(pp, new_items):
    """
    Merge freshly recomputed mr_items into pp.mr_items WITHOUT wiping the
    table. This replaces the old "pp.set('mr_items', []) + re-append"
    approach, which destroyed and recreated every row on every call —
    handing each row a brand-new `name` and silently orphaning the link to
    any Material Request already created against it (root cause of the
    duplicate-MR bug).

    Matching key: (item_code, warehouse) — same key used by
    _get_pending_mr_rows() / _get_already_requested_keys().

    Rules:
    1. Existing row, still needed (key present in new_items)
       -> update its fields IN PLACE. Same object, same `name`, so any
          existing Material Request link stays valid.
    2. Existing row, no longer needed, NO Material Request created yet
       -> safe to drop.
    3. Existing row, no longer needed, but a Material Request WAS already
       created against it
       -> keep the row untouched. We never delete a row that a live MR
          still references, even if recompute says it's no longer required —
          that MR is a real document already in the system.
    4. Genuinely new item (key not in existing rows)
       -> appended as a new row (this is the only case where a new `name`
          is expected/correct, because there was nothing to preserve).
    """
    already_requested_keys = _get_already_requested_keys(pp)

    existing_rows = list(pp.mr_items or [])
    existing_by_key = {}
    for row in existing_rows:
        existing_by_key.setdefault(_mr_item_key(row), []).append(row)

    new_by_key = {}
    for d in new_items:
        key = (d.get("item_code"), d.get("warehouse"), d.get("sales_order"),d.get("parent"))
        new_by_key.setdefault(key, []).append(d)

    kept_rows = []
    dropped_with_live_mr = []  # for an optional heads-up message to the user

    for key, rows in existing_by_key.items():
        new_matches = new_by_key.pop(key, [])

        for i, row in enumerate(rows):
            if i < len(new_matches):
                # Rule 1: still needed -> update in place, same `name`.
                new_data = new_matches[i]
                for fieldname, value in new_data.items():
                    if fieldname not in _MR_ITEM_PROTECTED_FIELDS:
                        row.set(fieldname, value)
                kept_rows.append(row)
            elif key in already_requested_keys:
                # Rule 3: no longer needed but MR already exists -> keep as-is.
                kept_rows.append(row)
                dropped_with_live_mr.append(row.item_code)
            # else Rule 2: no longer needed, no MR yet -> drop (don't append).

    # Rule 4: anything left in new_by_key is genuinely new.
    remaining_new = [d for items_ in new_by_key.values() for d in items_]

    pp.set("mr_items", kept_rows)
    for d in remaining_new:
        pp.append("mr_items", d)

    # Renumber idx cleanly since rows may have been dropped/reordered.
    for i, row in enumerate(pp.mr_items, start=1):
        row.idx = i

    if dropped_with_live_mr:
        frappe.msgprint(
            _(
                "Note: {0} no longer appear required by the current plan, "
                "but a Material Request already exists for them, so they "
                "were kept as-is."
            ).format(", ".join(dropped_with_live_mr)),
            indicator="orange",
            alert=True,
        )

def _normalize(value):
    """
    Treat None, False, and blank identically, and strip whitespace, so key
    matching can't silently break just because one side has None and the
    other has "" for the same logical value.
    """
    return (value or "").strip()


def _mr_item_key(item_code, warehouse,sales_order):
    """
    Match key linking a Production Plan required-item row to Material
    
    """
    return (_normalize(item_code), _normalize(warehouse),_normalize(sales_order))


def _get_already_requested_qty_map(pp):
    """
    Returns a dict keyed by (item_code, warehouse) -> total qty already
    requested via non-cancelled Material Request Items linked to this
    Production Plan (plus legacy fallback rows matched the same way, for
    MR Items created before `production_plan` was stamped on them).
    """
    qty_map = defaultdict(float)

    rows = frappe.get_all(
        "Material Request Item",
        filters={
            "production_plan": pp.name,
            "docstatus": ["!=", 2],  # cancelled MRs don't count as "requested"
        },
        fields=["item_code", "warehouse", "sales_order","qty"],
    )
    for r in rows:
        key = _mr_item_key(r.item_code, r.warehouse,r.sales_order)
        qty_map[key] += flt(r.qty)

    # Fallback for legacy data where production_plan wasn't stamped on the
    # MR Item (e.g. rows created before this field/flow existed).
    sales_orders = {d.get("sales_order") for d in (pp.mr_items or []) if d.get("sales_order")}
    if sales_orders:
        legacy_rows = frappe.get_all(
            "Material Request Item",
            filters={
                "sales_order": ["in", list(sales_orders)],
                "production_plan": ["in", ["", None]],
                "docstatus": ["!=", 2],
            },
            fields=["item_code", "warehouse", "sales_order","qty"],
        )
        for r in legacy_rows:
            key = _mr_item_key(r.item_code, r.warehouse,r.sales_order)
            qty_map[key] += flt(r.qty)

    return qty_map


def _get_pending_mr_rows(pp):
    """
    Return mr_items rows still pending, with `quantity` overridden to the
    *remaining* qty only (required_qty - already_requested_qty).

    NOTE: pp.mr_items is Material Request Plan Item, whose qty field is
    named `quantity` (not `qty` — that's the field name on the separate
    Material Request Item doctype used on the target MR).
    """
    if not pp.mr_items:
        return []

    requested_qty_map = _get_already_requested_qty_map(pp)
    pending_rows = []
    precision = 6  # tolerance for float rounding noise (e.g. 4.999999999 vs 5)

    for d in pp.mr_items:
        key = _mr_item_key(d.item_code, d.warehouse,d.sales_order)
        already_requested = requested_qty_map.get(key, 0)
        pending_qty = flt(flt(d.quantity) - flt(already_requested), precision)

        if pending_qty > 0:
            pending_row = frappe._dict(d.as_dict())
            pending_row.quantity = pending_qty
            pending_row.total_required_qty = d.quantity
            pending_row.already_requested_qty = already_requested
            pending_rows.append(pending_row)

    return pending_rows

@frappe.whitelist()
def get_pending_mr_items(docname):
    """
    Used by the client script on refresh to decide whether to show the
    'Create Material Request' button, and to show accurate pending qty
    (not just item codes) in the confirmation dialog.
    """
    pp = frappe.get_doc("Production Plan", docname)
    pending_rows = _get_pending_mr_rows(pp)

    return {
        "pending_count": len(pending_rows),
        "pending_items": [
            f"{d.item_code} ({d.quantity})" for d in pending_rows
        ],
    }

@frappe.whitelist()
def create_material_request_for_pending_items(docname):
    """
    Explicit button action: check every raw material row in mr_items,
    and create one Material Request covering only the genuinely pending
    quantity — not the full row qty.

    Qty-aware: if a row's required qty was increased by a BOM modification
    after a partial MR was already created (e.g. required qty 5 -> 10,
    MR already exists for 5), only the remaining shortfall (5) is requested
    here. `_get_pending_mr_rows()` is responsible for that qty math; this
    function just trusts the `.qty` it returns on each row and passes it
    straight through to make_material_request().

    Guarded against double-click / concurrent-request races with a
    short-lived cache lock per Production Plan.
    """
    lock_key = f"pp_mr_create_lock::{docname}"

    if frappe.cache().get_value(lock_key):
        frappe.throw(_("Material Request creation is already in progress for this Production Plan. Please wait."))

    frappe.cache().set_value(lock_key, 1, expires_in_sec=60)

    try:
        pp = frappe.get_doc("Production Plan", docname)

        # Re-fetch pending rows fresh inside the lock, not from any
        # earlier client-side snapshot, so a concurrent update to mr_items
        # (or an MR created by someone else moments ago) is reflected here.
        pending_rows = _get_pending_mr_rows(pp)
        if not pending_rows:
            return {
                "created": False,
                "items": [],
                "message": _("Material Request has already been created for all items."),
            }

        original_mr_items = pp.mr_items

        try:
            # pending_rows already has `.qty` overridden to the remaining
            # (shortfall) qty by _get_pending_mr_rows() — e.g. required 10,
            # already requested 5 -> qty here is 5, not 10. We swap mr_items
            # to just these rows and reuse the standard make_material_request()
            # flow — same one the stock "Create > Material Request" button
            # calls — so it requests exactly the shortfall qty per row.
            pp.set("mr_items", pending_rows)
            pp.make_material_request()
        except Exception as e:
            frappe.log_error(
                "Manual MR Creation Error",
                f"Error creating MR for pending items in PP {pp.name}: {str(e)}"
            )
            frappe.throw(_("Could not create Material Request: {0}").format(str(e)))
        finally:
            # Restore full mr_items in memory; nothing else needs re-saving on
            # pp itself since make_material_request() persists the new MR
            # document separately. pp itself is never saved in this flow.
            pp.set("mr_items", original_mr_items)

        # Report actual requested qty per item, not just item codes, so the
        # success message reflects the real (possibly partial) quantities.
        created_items = [
            f"{d.item_code} ({d.quantity})" for d in pending_rows if d.item_code
        ]
        frappe.db.set_value("Production Plan", pp.name, "production_plan_updated", 0, update_modified=False)



        return {
            "created": True,
            "items": created_items,
            "message": _("Material Request created for: {0}").format(", ".join(created_items)),
        }
    finally:
        frappe.cache().delete_value(lock_key)

def _flag_work_orders_for_update(production_plan):
    """Mark linked Work Orders as needing a sync, in a single bulk UPDATE."""
    work_orders = frappe.get_all(
        "Work Order",
        filters={"production_plan": production_plan, "docstatus": ["!=", 2]},
        pluck="name",
    )
    if not work_orders:
        return

    frappe.db.set_value(
        "Work Order",
        {"name": ["in", work_orders]},
        "modification_status",
        "Yes",
        update_modified=False,
    )
def validate_work_orders_before_update(production_plan):
    """
    Allow updating a Production Plan (via Get Items/Update) only if every
    linked Work Order is still in Draft or Not Started status.

    Allowed:
        - Draft
        - Not Started

    Blocked:
        - Any other status (Started, In Process, Completed, Stopped, Closed, etc.)
    """

    allowed_statuses = ("Draft", "Not Started")

    work_order = frappe.db.get_value(
        "Work Order",
        {
            "production_plan": production_plan,
            "docstatus": ("!=", 2),
            "status": ("not in", allowed_statuses),
        },
        ["name", "status"],
        as_dict=True,
    )

    if work_order:
        frappe.throw(
            _(
                "Production Plan cannot be updated because Work Order <b>{0}</b> is in <b>{1}</b> status."
            ).format(work_order.name, work_order.status),
            title=_("Update Not Allowed"),
        )
# =============================================================================
# Control Tower Dashboard — Modification Status Summary
# =============================================================================

@frappe.whitelist()
def get_modification_status_summary(branch=None, status=None, limit=200):
    """
    Returns one row per non-cancelled Production Plan with its overall
    modification status plus rollup counts for linked Work Orders and MRs.

    Supports branch filter (respects Branch User Permission) and status
    filter matching one of the five overall_status values.
    """
    user = frappe.session.user

    # --- Branch Permission ---
    from generate_item.generate_item.modification_task_utils.modification_task_permission import get_user_branches
    user_branches = get_user_branches(user)

    pp_filters = {"docstatus": ["!=", 2]}  # not cancelled

    if branch:
        pp_filters["branch"] = branch
    elif user_branches:
        pp_filters["branch"] = ["in", user_branches]

    pp_fields = [
        "name", "branch", "sales_order_modification", "bom_modification",
        "production_plan_updated", "original_data", "modified",
    ]

    # Pull all Production Plans in one query
    pp_list = frappe.get_all(
        "Production Plan",
        filters=pp_filters,
        fields=pp_fields,
        limit=limit,
        order_by="modified desc",
    )

    if not pp_list:
        return []

    pp_names = [p.name for p in pp_list]

    # --- Find the primary Sales Order for each PP ---
    pp_so_map = _get_pp_primary_sales_order(pp_names)

    # --- Pull Work Order counts in one grouped query ---
    wo_raw = frappe.db.get_all(
        "Work Order",
        filters={
            "production_plan": ["in", pp_names],
            "docstatus": ["!=", 2],
        },
        fields=["production_plan", "modification_status", "name"],
    )

    # Aggregate WO counts per PP
    wo_counts = {}  # {pp_name: {"total": N, "pending": N}}
    for w in wo_raw:
        pp_name = w.production_plan
        if pp_name not in wo_counts:
            wo_counts[pp_name] = {"total": 0, "pending": 0}
        wo_counts[pp_name]["total"] += 1
        if w.modification_status == "Yes":
            wo_counts[pp_name]["pending"] += 1

    # --- Build rows ---
    result = []
    status_counts = {}  # for summary strip on client side if needed

    for pp in pp_list:
        pp_name = pp.name
        wo = wo_counts.get(pp_name, {"total": 0, "pending": 0})
        wo_total = wo["total"]
        wo_pending = wo["pending"]
        wo_synced = wo_total - wo_pending

        # Compute overall_status per priority rules
        overall_status = _compute_overall_status(pp, wo_pending)

        # If no higher-priority flags, compute MR pending count
        pending_mr_count = 0
        if overall_status in ("Up To Date", "WO Sync Pending"):
            try:
                mr_pending = get_pending_mr_items(pp_name)
                pending_mr_count = mr_pending.get("pending_count", 0) if mr_pending else 0
                if pending_mr_count > 0 and overall_status == "Up To Date":
                    overall_status = "MR Pending"
            except Exception:
                pending_mr_count = 0

        row = {
            "production_plan": pp_name,
            "sales_order": pp_so_map.get(pp_name, ""),
            "branch": pp.branch or "",
            "sales_order_modification": pp.sales_order_modification or "",
            "bom_modification": pp.bom_modification or "",
            "production_plan_updated": pp.production_plan_updated or 0,
            "overall_status": overall_status,
            "wo_total": wo_total,
            "wo_pending": wo_pending,
            "wo_synced": wo_synced,
            "pending_mr_count": pending_mr_count,
            "modified": str(pp.modified) if pp.modified else "",
        }
        result.append(row)

        # Track status counts
        status_counts[overall_status] = status_counts.get(overall_status, 0) + 1

    # --- Server-side status filter ---
    if status and status != "All":
        result = [r for r in result if r["overall_status"] == status]

    return result


@frappe.whitelist()
def get_single_pp_status(docname):
    """
    Lightweight single-row variant for re-fetching one PP's row after
    an action button update. Returns the same shape as one element of
    get_modification_status_summary's list.
    """
    pp = frappe.get_doc("Production Plan", docname)
    if pp.docstatus == 2:
        frappe.throw(_("Cannot fetch status for a cancelled Production Plan."))

    wo_total = frappe.db.count("Work Order", {
        "production_plan": docname,
        "docstatus": ["!=", 2],
    })
    wo_pending = frappe.db.count("Work Order", {
        "production_plan": docname,
        "docstatus": ["!=", 2],
        "modification_status": "Yes",
    })
    wo_synced = wo_total - wo_pending

    overall_status = _compute_overall_status(pp, wo_pending)

    pending_mr_count = 0
    if overall_status in ("Up To Date", "WO Sync Pending"):
        try:
            mr_pending = get_pending_mr_items(docname)
            pending_mr_count = mr_pending.get("pending_count", 0) if mr_pending else 0
            if pending_mr_count > 0 and overall_status == "Up To Date":
                overall_status = "MR Pending"
        except Exception:
            pending_mr_count = 0

    pp_so_map = _get_pp_primary_sales_order([docname])

    return {
        "production_plan": docname,
        "sales_order": pp_so_map.get(docname, ""),
        "branch": pp.branch or "",
        "sales_order_modification": pp.sales_order_modification or "",
        "bom_modification": pp.bom_modification or "",
        "production_plan_updated": pp.production_plan_updated or 0,
        "overall_status": overall_status,
        "wo_total": wo_total,
        "wo_pending": wo_pending,
        "wo_synced": wo_synced,
        "pending_mr_count": pending_mr_count,
        "modified": str(pp.modified) if pp.modified else "",
    }


def _compute_overall_status(pp, wo_pending):
    """Priority-ordered status computation (section 2 of build spec)."""
    if pp.sales_order_modification == "YES":
        return "Update Required — Sales Order"
    if pp.bom_modification == "YES":
        return "Update Required — BOM"
    if wo_pending > 0:
        return "WO Sync Pending"
    return "Up To Date"  # MR Pending may override this in caller


def _get_pp_primary_sales_order(pp_names):
    """
    Resolve the primary Sales Order for each Production Plan by looking
    at po_items. Returns a dict {pp_name: sales_order}.
    """
    if not pp_names:
        return {}

    ppi = frappe.get_all(
        "Production Plan Item",
        filters={"parent": ["in", pp_names]},
        fields=["parent", "sales_order"],
        order_by="idx asc",
    )

    so_map = {}
    for row in ppi:
        if row.sales_order and row.parent not in so_map:
            so_map[row.parent] = row.sales_order

    return so_map

