from pydoc import doc

import frappe
from frappe import _

from generate_item.generate_item.modification_task_utils.modification_task import create_wo_po_tasks_on_gate_update


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
        frappe.db.commit()


import frappe
from erpnext.manufacturing.doctype.production_plan.production_plan import (
    get_items_for_material_requests,
)


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
    """Batch-fetch all Sales Order Item qtys in a single query instead of
    one query per po_item row (fixes N+1)."""
    so_item_names = [d.sales_order_item for d in pp.po_items if d.sales_order_item]
    if not so_item_names:
        return False

    qty_map = dict(
        frappe.get_all(
            "Sales Order Item",
            filters={"name": ["in", so_item_names]},
            fields=["name", "qty"],
            as_list=True,
        )
    )

    changed = False
    for item in pp.po_items:
        so_qty = qty_map.get(item.sales_order_item)
        if so_qty and so_qty > (item.planned_qty or 0):
            item.planned_qty = so_qty
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


@frappe.whitelist()
def get_update_for_submitted_pp(docname):
    pp = frappe.get_doc("Production Plan", docname)
    validate_work_orders_before_update(pp.name)
    was_submitted = pp.docstatus == 1

    if was_submitted:
        pp.set_status(close=True, update_bin=True)
        pp.db_set("docstatus", 0, update_modified=False)
        pp.reload()
        pp.flags.ignore_validate = True
        pp.flags.ignore_validate_update_after_submit = True
        pp.flags.ignore_permissions = True

    # All in-memory mutations happen first — nothing is written to DB yet.
    captured = _capture_original_data_if_needed(pp)
    changed = _sync_planned_qty_from_sales_orders(pp)

    # get_sub_assembly_items() reads pp.po_items in memory — no save needed first.
    pp.get_sub_assembly_items()

    # Clear both modification flags in a single UPDATE instead of two.
    pp.production_plan_updated = 1
    frappe.db.set_value(
        "Production Plan", pp.name,
        {"bom_modification": "", "sales_order_modification": ""},
        update_modified=False,
    )
    pp.bom_modification = ""
    pp.sales_order_modification = ""

    warehouses = _get_default_transfer_warehouses(pp)
    items = get_items_for_material_requests(pp.as_json(), warehouses=warehouses or None)
    pp.set("mr_items", [])
    for d in items:
        pp.append("mr_items", d)

    # Single save for everything accumulated above.
    pp.save(ignore_permissions=True)
    # flag all non-cancelled linked Work Orders for update ---
    _flag_work_orders_for_update(pp.name)

    if was_submitted:
        pp.submit()
        create_wo_po_tasks_on_gate_update(pp)
    
    pp.set_status(close=False, update_bin=True)

    frappe.db.commit()
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
#         pp.flags.ignore_validate = True
#         pp.flags.ignore_validate_update_after_submit = True
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

#     frappe.db.commit()
#     return {
#         "success": True,
#         "planned_qty_updated": changed,
#         "original_data_captured_now": captured,
#     }


def _mr_item_key(row):
    """
    Stable identity for an mr_items row that survives table rebuilds.

    Includes sales_order (not just item_code + warehouse) because the same
    item + warehouse combination can legitimately appear as separate rows
    for different sales orders within one Production Plan. Without
    sales_order in the key, rows for SO-A and SO-B on the same item could be
    cross-matched during merge, or an MR raised for SO-A could incorrectly
    make SO-B's row look "already requested".
    """
    return (row.item_code, row.get("warehouse"), row.get("sales_order"),row.get("parent"))


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


def _get_already_requested_keys(pp):
    """
    Single query: fetch every non-cancelled Material Request Item already
    raised for this Production Plan, keyed the same way as mr_items rows.

    Matching is done on (item_code, warehouse) rather than on
    material_request_plan_item -> mr_items.name, because
    get_update_for_submitted_pp() fully rebuilds mr_items (delete + re-append)
    on every run, which assigns each row a brand-new `name`. Matching by name
    breaks the moment the plan is updated again — the old MR's back-link
    points to a row that no longer exists, so an already-fulfilled item looks
    "pending" and gets requested a second time.

    Primary match: production_plan == pp.name (set by make_material_request()
    on every row it creates).
    Fallback match: sales_order == pp's linked sales orders, for any legacy
    Material Request Item rows created before production_plan existed / was
    populated on this table.
    """
    rows = frappe.get_all(
        "Material Request Item",
        filters={
            "production_plan": pp.name,
            "docstatus": ["!=", 2],  # cancelled MRs don't count as "created"
        },
        fields=["item_code", "warehouse", "sales_order","production_plan"],
    )
    keys = {(r.item_code, r.warehouse, r.sales_order,r.production_plan) for r in rows}

    # Fallback for legacy data where production_plan wasn't stamped on the MR
    # Item (e.g. rows created before this field/flow existed).
    sales_orders = {d.get("sales_order") for d in (pp.mr_items or []) if d.get("sales_order")}
    if sales_orders:
        legacy_rows = frappe.get_all(
            "Material Request Item",
            filters={
                "sales_order": ["in", list(sales_orders)],
                "production_plan": ["in", ["", None]],
                "docstatus": ["!=", 2],
            },
            fields=["item_code", "warehouse", "sales_order","production_plan"],
        )
        keys |= {(r.item_code, r.warehouse, r.sales_order,r.production_plan) for r in legacy_rows}

    return keys


def _get_pending_mr_rows(pp):
    """Return the mr_items rows that don't yet have a live Material Request."""
    if not pp.mr_items:
        return []

    already_requested_keys = _get_already_requested_keys(pp)
    return [d for d in pp.mr_items if _mr_item_key(d) not in already_requested_keys]


@frappe.whitelist()
def get_pending_mr_items(docname):
    """
    Used by the client script on refresh to decide whether to show the
    'Create Material Request' button.
    """
    pp = frappe.get_doc("Production Plan", docname)
    pending_rows = _get_pending_mr_rows(pp)
    return {
        "pending_count": len(pending_rows),
        "pending_items": [d.item_code for d in pending_rows],
    }


@frappe.whitelist()
def create_material_request_for_pending_items(docname):
    """
    Explicit button action: check every raw material row in mr_items,
    skip the ones that already have a live Material Request, and create
    one MR covering only the genuinely pending rows.

    Guarded against double-click / concurrent-request races with a short-lived
    cache lock per Production Plan.
    """
    lock_key = f"pp_mr_create_lock::{docname}"

    if frappe.cache().get_value(lock_key):
        frappe.throw(_("Material Request creation is already in progress for this Production Plan. Please wait."))

    frappe.cache().set_value(lock_key, 1, expires_in_sec=60)

    try:
        pp = frappe.get_doc("Production Plan", docname)

        pending_rows = _get_pending_mr_rows(pp)
        if not pending_rows:
            return {
                "created": False,
                "items": [],
                "message": _("Material Request has already been created for all items."),
            }

        original_mr_items = pp.mr_items

        try:
            # Narrow mr_items to just the pending rows and reuse the standard
            # make_material_request() flow — same one the stock "Create >
            # Material Request" button calls.
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
            # document separately.
            pp.set("mr_items", original_mr_items)

        created_items = [d.item_code for d in pending_rows if d.item_code]
        frappe.db.set_value("Production Plan", pp.name, "production_plan_updated", 0, update_modified=False)
        
        frappe.db.commit()

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
    Prevent updating a Production Plan if any linked Work Order
    has already entered execution.

    Allowed:
        - Draft
        - Not Started

    Blocked:
        - Started
        - In Process
        - Completed
    """

    blocked_statuses = ("Started", "In Process", "Completed")

    work_order = frappe.db.get_value(
        "Work Order",
        {
            "production_plan": production_plan,
            "docstatus": ("!=", 2),
            "status": ("in", blocked_statuses),
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