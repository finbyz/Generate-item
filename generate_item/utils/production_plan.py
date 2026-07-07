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

#     # All in-memory mutations happen first — nothing is written to DB yet.
#     captured = _capture_original_data_if_needed(pp)
#     changed = _sync_planned_qty_from_sales_orders(pp)

#     # get_sub_assembly_items() reads pp.po_items in memory — no save needed first.
#     pp.get_sub_assembly_items()

#     # Clear both modification flags in a single UPDATE instead of two.
#     frappe.db.set_value(
#         "Production Plan", pp.name,
#         {"bom_modification": "", "sales_order_modification": ""},
#         update_modified=False,
#     )
#     pp.bom_modification = ""
#     pp.sales_order_modification = ""

#     warehouses = _get_default_transfer_warehouses(pp)
#     items = get_items_for_material_requests(pp.as_json(), warehouses=warehouses or None)
#     pp.set("mr_items", [])
#     for d in items:
#         pp.append("mr_items", d)

#     # Single save for everything accumulated above.
#     pp.save(ignore_permissions=True)
#     # flag all non-cancelled linked Work Orders for update ---
#     _flag_work_orders_for_update(pp.name)

#     if was_submitted:
#         pp.submit()
#         create_wo_po_tasks_on_gate_update(pp)
    

#     frappe.db.commit()
#     return {
#         "success": True,
#         "planned_qty_updated": changed,
#         "original_data_captured_now": captured,
#     }


@frappe.whitelist()
def get_update_for_submitted_pp(docname):
    pp = frappe.get_doc("Production Plan", docname)
    validate_work_orders_before_update(pp.name)
    was_submitted = pp.docstatus == 1

    if was_submitted:
        pp.db_set("docstatus", 0, update_modified=False)
        pp.reload()
        pp.flags.ignore_validate = True
        pp.flags.ignore_validate_update_after_submit = True
        pp.flags.ignore_permissions = True

    captured = _capture_original_data_if_needed(pp)
    changed = _sync_planned_qty_from_sales_orders(pp)

    # get_sub_assembly_items() reads pp.po_items in memory — no save needed first.
    pp.get_sub_assembly_items()

    # Clear both modification flags in a single UPDATE instead of two.
    frappe.db.set_value(
        "Production Plan", pp.name,
        {"bom_modification": "", "sales_order_modification": ""},
        update_modified=False,
    )
    pp.bom_modification = ""
    pp.sales_order_modification = ""

    # Snapshot item codes that existed BEFORE this update, so we can tell
    # which mr_items rows are genuinely new after rebuilding the table.
    existing_mr_item_codes = {d.item_code for d in (pp.mr_items or []) if d.item_code}

    warehouses = _get_default_transfer_warehouses(pp)
    items = get_items_for_material_requests(pp.as_json(), warehouses=warehouses or None)
    pp.set("mr_items", [])
    for d in items:
        pp.append("mr_items", d)

    # Single save for everything accumulated above.
    # This is also what assigns each mr_items row its real `name`.
    pp.save(ignore_permissions=True)

    # flag all non-cancelled linked Work Orders for update
    _flag_work_orders_for_update(pp.name)

    if was_submitted:
        pp.submit()
        create_wo_po_tasks_on_gate_update(pp)

    # --- Auto-create MR for newly added BOM items ---
    # IMPORTANT: build this list from pp.mr_items AFTER save(), not from the
    # raw `items` dicts collected before save. Pre-save dicts never receive
    # the `name` frappe assigns on save, so if you later feed them into
    # make_material_request(), the created MR Items lose their
    # `material_request_plan_item` back-link to this Production Plan.
    # Using the post-save rows keeps that link intact.
    newly_added_rows = [
        d for d in (pp.mr_items or [])
        if d.item_code and d.item_code not in existing_mr_item_codes
    ]

    new_items_created = []
    if newly_added_rows and was_submitted:
        try:
            original_mr_items = pp.mr_items

            # Temporarily narrow mr_items to just the new rows (already-saved
            # Document rows, so `.name` etc. are correct) and reuse the
            # existing make_material_request() flow — same one the
            # "Create > Material Request" button calls.
            pp.set("mr_items", newly_added_rows)
            pp.make_material_request()

            # Restore full mr_items in memory. No re-save needed: the DB
            # already has the complete list from pp.save() above, and we're
            # not persisting pp again after this point.
            pp.set("mr_items", original_mr_items)

            new_items_created = [row.item_code for row in newly_added_rows]
            frappe.msgprint(
                _("Material Request created for newly added BOM items: {0}").format(
                    ", ".join(new_items_created)
                )
            )
        except Exception as e:
            frappe.log_error(
                "Auto MR Creation Error",
                f"Error creating MR for new items in PP {pp.name}: {str(e)}"
            )
            frappe.msgprint(
                _("Could not auto-create Material Request for new items: {0}").format(str(e)),
                indicator="orange",
            )

    frappe.db.commit()
    return {
        "success": True,
        "planned_qty_updated": changed,
        "original_data_captured_now": captured,
        "new_items_added": bool(new_items_created),
        "new_items": new_items_created,
    }

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