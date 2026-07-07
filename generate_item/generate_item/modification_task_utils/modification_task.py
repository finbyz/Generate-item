import frappe
from frappe import _
from frappe.utils import flt


# ---------------------------------------------------------------------------
# Main entry point (called after an Order Modification Request is submitted)
# ---------------------------------------------------------------------------

def create_modification_task(doc):
    """
    Creates Modification Task record(s) based on the modification request document.

    For Order Modification Requests the function walks the downstream chain
        Sales Order → Production Plan → Work Order → Purchase Order
    and creates one Modification Task per unique downstream document that is
    impacted by the changed items.

    Two separate branches:
        - Item change  → BOM task first, then PP / WO / PO tasks
        - Qty change → No BOM task, directly PP / WO / PO tasks
    """
    if doc.doctype == "Order Modification Request":
        _handle_omr(doc)


# ---------------------------------------------------------------------------
# OMR handler
# ---------------------------------------------------------------------------

def _handle_omr(doc):
    """
    1. Detect what changed — item code, qty or both.
    2. If any item code changed → create a BOM Modification Task.
    3. For ALL changes (item or qty) → walk SO → PP → WO → PO
       and create one task per unique downstream document found.
    """
    item_changes, qty_changes = _get_changed_items(doc)

    # Nothing changed at all → nothing to do
    if not item_changes and not qty_changes:
        return

    sales_order = doc.sales_order

    # -----------------------------------------------------------------------
    # BRANCH A: Item code changed → BOM task required
    # -----------------------------------------------------------------------
    if item_changes:
        _create_bom_task(doc, item_changes)
        # _create_downstream_tasks(doc, sales_order, item_changes)

    # -----------------------------------------------------------------------
    # BRANCH B: Qty changed (no item code change) → no BOM task
    # -----------------------------------------------------------------------
    if qty_changes:

        _create_downstream_tasks(doc, sales_order, qty_changes)


# ---------------------------------------------------------------------------
# Helpers – data extraction
# ---------------------------------------------------------------------------

def _get_changed_items(doc):
    """
    Splits changes into two separate dicts:

    item_changes      — rows where the item code itself changed
                        (new_item is set and differs from item)
    qty_changes  — rows where only qty  changed
                        (item code is the same)

    Each dict has the shape:
        {original_item_code: {
            "display_item": str,
            "item_changed": bool,
            "qty_changed": bool,
         
        }}
    """
    item_changes = {}
    qty_changes = {}

    if not (hasattr(doc, "original_record") and doc.original_record):
        return item_changes, qty_changes

    for row in doc.original_record:
        original_item = row.item
        new_item      = getattr(row, "new_item", None) or original_item

        old_qty  = flt(getattr(row, "qty",      0))
        new_qty  = flt(getattr(row, "rev_qty",  0))
       

        item_changed = bool(new_item and new_item != original_item)
        qty_changed  = new_qty  > 0 and new_qty  != old_qty
       

        if not (item_changed or qty_changed ):
            continue   # this row has no change worth acting on

        record = {
            "display_item": new_item,
            "old_qty":      old_qty,
            "new_qty":      new_qty  if qty_changed  else old_qty,
            "item_changed": item_changed,
            "qty_changed":  qty_changed,
            
        }

        if item_changed:
            # Item code changed → BOM branch
            item_changes[original_item] = record
        else:
            # Only qty  no BOM needed
            qty_changes[original_item] = record

    return item_changes, qty_changes


# ---------------------------------------------------------------------------
# BOM task (item-change branch only)
# ---------------------------------------------------------------------------

def _create_bom_task(doc, item_changes):
    """
    Creates a single BOM Modification Task summarising every item whose
    code has changed on the Sales Order.

    For each changed item, pulls:
      - bom_update_request  from doc.sales_order_item (matched on item + rev_item)
      - source_bom          from the BOM Modification Request document
      - batch_no    from doc.sales_order_item for reference
    """

    # Build lookup: (original_item, rev_item) → {bom_update_request, batch_no, tag_no}
    so_item_map = {}
    for si_row in (getattr(doc, "sales_order_item", None) or []):
        rev_item = getattr(si_row, "rev_item", None)
        if rev_item:
            so_item_map[(si_row.item, rev_item)] = {
                "bom_update_request": getattr(si_row, "bom_update_request", None) or None,
                "batch_no": getattr(si_row, "batch_no", None),
               
            }

    lines = []

    # ── Why this task exists ────────────────────────────────────────────────
    lines.append("## Why This Task Was Created")
    lines.append(
        f"Sales Order **{doc.sales_order}** was modified and one or more finished "
        f"item codes were changed. The associated Batch and Bill of Materials (BOM) "
        f"have been updated, and a BOM Modification Request has been created for "
        f"each affected item. Review and complete each BOM Modification Request "
        f"listed below before production planning can continue."
    )
    lines.append("")

    # ── Affected items ──────────────────────────────────────────────────────
    lines.append("## Affected Items")
    lines.append("")

    for original_item, info in item_changes.items():
        new_item = info["display_item"]

        # Resolve BOM Modification Request and source BOM from the lookup
        si_info            = so_item_map.get((original_item, new_item), {})
        bom_update_request = si_info.get("bom_update_request")
        batch_no           = si_info.get("batch_no")
       

        # Fetch the source BOM name from the BMR document
        source_bom = None
        if bom_update_request:
            source_bom = frappe.db.get_value(
                "Bom Modification Request", bom_update_request, "bom"
            )

        lines.append("### Item Change")
        lines.append(f"- **Original Item Code :** {original_item}")
        lines.append(f"- **Revised Item Code  :** {new_item}")

        if batch_no:
            lines.append(f"- **Batch Reference    :** {batch_no}")
       
        if info.get("qty_changed"):
            lines.append(
                f"- **Qty Change          :** {info['old_qty']} → {info['new_qty']}"
            )

        lines.append("")
        lines.append("**BOM References**")

        if source_bom:
            lines.append(f"- **Reference BOM            :** {source_bom}")
        

        if bom_update_request:
            lines.append(f"- **BOM Modification Request :** {bom_update_request}")
        else:
            lines.append(
                "- **BOM Modification Request :** Not yet created — "
                "raise one against the revised item before proceeding"
            )

        lines.append("")

    # ── Steps ───────────────────────────────────────────────────────────────
    lines.append("## Steps to Complete This Task")
    lines.append(
        "1. Open each **BOM Modification Request** listed above."
    )
    lines.append(
        "2. Review the finished item and verify that the copied BOM components, "
        "operations, and routing are correct for the revised item."
    )
    lines.append(
        "3. Add, remove, or modify any BOM components, quantities, or operations "
        "wherever required."
    )
    lines.append(
        "4. Save and submit the BOM Modification Request after all necessary "
        "changes have been completed."
    )
    lines.append(
        "5. Confirm that the BOM is ready for manufacturing and inform the "
        "Planning team if any production impact exists."
    )
    lines.append(
        "6. Mark this task as completed so Production Planning and Work Order "
        "creation can proceed."
    )
    lines.append("")
    lines.append(
        "**Important:** Production Planning and Work Order creation must not "
        "proceed until all BOM Modification Requests listed above have been "
        "reviewed and submitted."
    )

    _create_single_task(
        category="BOM Modification",
        reference_doctype="Sales Order",
        reference_document_name=doc.sales_order,
        subject=f"BOM modification for SO {doc.sales_order}",
        description="\n".join(lines),
        remarks=doc.reason_for_change,
        branch=doc.branch,
    )

# ---------------------------------------------------------------------------
# Downstream chain: PP → WO → PO (shared by both branches)
# ---------------------------------------------------------------------------

def _create_downstream_tasks(doc, sales_order, changed_items):
    """
    Walks the chain Sales Order → Production Plan → Work Order → Purchase Order
    and creates one Modification Task per unique downstream document found.
    Documents not present in the chain are silently skipped.
    """
    pp_item_map = _get_production_plans_for_items(sales_order, list(changed_items.keys()))

    for pp_name, items_in_pp in pp_item_map.items():
        # --- Production Plan task ---
        description = _build_pp_description(pp_name, sales_order, items_in_pp, changed_items)
        branch = frappe.db.get_value("Production Plan", pp_name, "branch")
        _create_single_task(
            category="Production Plan Update",
            reference_doctype="Production Plan",
            reference_document_name=pp_name,
            subject=f"Modification for {pp_name}",
            description=description,
            remarks=doc.reason_for_change,
            branch=doc.branch or branch,
        )

        # --- Work Order tasks (per PP) ---
        wo_item_map = _get_work_orders_for_pp_items(pp_name, items_in_pp)
        for wo_name, wo_items in wo_item_map.items():
            wo_description = _build_wo_description(wo_name, pp_name, sales_order, wo_items, changed_items)
            branch = frappe.db.get_value("Work Order", wo_name, "branch")
            _create_single_task(
                category="Work Order Update",
                reference_doctype="Work Order",
                reference_document_name=wo_name,
                subject=f"Modification for {wo_name}",
                description=wo_description,
                remarks=doc.reason_for_change,
                branch=doc.branch or branch,
            )

        # --- Purchase Order tasks (per PP) ---
        po_item_map = _get_purchase_orders_for_pp_items(pp_name, items_in_pp)
        for po_name, po_items in po_item_map.items():
            po_description = _build_po_description(po_name, pp_name, sales_order, po_items, changed_items)
            branch = frappe.db.get_value("Purchase Order", po_name, "branch")
            _create_single_task(
                category="Purchase Order Modification",
                reference_doctype="Purchase Order",
                reference_document_name=po_name,
                subject=f"Modification for {po_name}",
                description=po_description,
                remarks=doc.reason_for_change,
                branch=doc.branch or branch,
            )


# ---------------------------------------------------------------------------
# Helpers – database lookups 
# ---------------------------------------------------------------------------

def _get_production_plans_for_items(sales_order, item_codes):
    if not item_codes:
        return {}

    rows = frappe.db.sql(
        """
        SELECT
            ppi.parent    AS pp_name,
            ppi.item_code AS item_code
        FROM
            `tabProduction Plan Item` ppi
        INNER JOIN
            `tabProduction Plan` pp ON pp.name = ppi.parent
        WHERE
            ppi.sales_order = %(so)s
            AND ppi.item_code IN %(items)s
            AND pp.docstatus != 2
        """,
        {"so": sales_order, "items": tuple(item_codes)},
        as_dict=True,
    )

    pp_item_map = {}
    for row in rows:
        pp_item_map.setdefault(row.pp_name, [])
        if row.item_code not in pp_item_map[row.pp_name]:
            pp_item_map[row.pp_name].append(row.item_code)

    return pp_item_map


def _get_work_orders_for_pp_items(pp_name, item_codes):
    if not item_codes:
        return {}

    rows = frappe.db.sql(
        """
        SELECT
            wo.name            AS wo_name,
            wo.production_item AS item_code
        FROM
            `tabWork Order` wo
        WHERE
            wo.production_plan = %(pp)s
            AND wo.production_item IN %(items)s
            AND wo.docstatus != 2
        """,
        {"pp": pp_name, "items": tuple(item_codes)},
        as_dict=True,
    )

    wo_item_map = {}
    for row in rows:
        wo_item_map.setdefault(row.wo_name, [])
        if row.item_code not in wo_item_map[row.wo_name]:
            wo_item_map[row.wo_name].append(row.item_code)

    return wo_item_map


def _get_purchase_orders_for_pp_items(pp_name, item_codes):
    if not item_codes:
        return {}

    mr_rows = frappe.db.sql(
        """
        SELECT
            mri.parent    AS mr_name,
            mri.item_code AS item_code,
            mri.name      AS mr_item_name
        FROM
            `tabMaterial Request Item` mri
        INNER JOIN
            `tabMaterial Request` mr ON mr.name = mri.parent
        WHERE
            mri.production_plan = %(pp)s
            AND mri.item_code IN %(items)s
            AND mr.docstatus != 2
        """,
        {"pp": pp_name, "items": tuple(item_codes)},
        as_dict=True,
    )

    if not mr_rows:
        return {}

    mr_names = list({r.mr_name for r in mr_rows})

    po_rows = frappe.db.sql(
        """
        SELECT
            poi.parent                AS po_name,
            poi.item_code             AS item_code,
            poi.material_request      AS mr_name,
            poi.material_request_item AS mr_item_name
        FROM
            `tabPurchase Order Item` poi
        INNER JOIN
            `tabPurchase Order` po ON po.name = poi.parent
        WHERE
            poi.material_request IN %(mrs)s
            AND poi.item_code IN %(items)s
            AND po.docstatus != 2
        """,
        {"mrs": tuple(mr_names), "items": tuple(item_codes)},
        as_dict=True,
    )

    po_item_map = {}
    for row in po_rows:
        po_item_map.setdefault(row.po_name, [])
        if row.item_code not in po_item_map[row.po_name]:
            po_item_map[row.po_name].append(row.item_code)

    return po_item_map


# ---------------------------------------------------------------------------
# Helpers – description builders 
# ---------------------------------------------------------------------------

def _build_pp_description(pp_name, so_name, item_codes, changed_items):
    lines = []
    lines.append("## Why This Task Was Created")
    lines.append(
        f"Sales Order **{so_name}** has been modified — the quantity or item of one "
        f"or more items has changed. Production Plan **{pp_name}** was created against "
        f"this Sales Order and must be updated to reflect the revised values before "
        f"production can proceed correctly."
    )
    lines.append("")

    lines.append("## What Changed on the Sales Order")
    has_changes = False
    for item in item_codes:
        info = changed_items.get(item, {})
        if info.get("item_changed"):
            has_changes = True
            lines.append(f"- Item code changed: **{item}** → **{info['display_item']}**")
        if info.get("qty_changed"):
            has_changes = True
            lines.append(
                f"- Item **{item}**: Qty changed from **{info['old_qty']}** → **{info['new_qty']}**"
            )
        
    if not has_changes:
        lines.append("- No item-level changes detected.")
    lines.append("")

    lines.append("## Steps to Complete This Task")
    lines.append(f"1. Open Production Plan **{pp_name}**.")
    lines.append(
        "2. Click **Refresh Production Plan** to pull the latest item quantities "
        "from the updated Sales Order."
    )
    lines.append(
        "3. Review the refreshed quantities and confirm they match the new values above."
    )
    lines.append("")
    lines.append(
        "**Important:** Do not proceed with Work Order creation or material planning "
        "until this Production Plan has been refreshed and saved."
    )

    return "\n".join(lines)


def _build_wo_description(wo_name, pp_name, so_name, item_codes, changed_items):
    lines = []
    lines.append("## Why This Task Was Created")
    lines.append(
        f"Sales Order **{so_name}** was modified, changing the planned quantities or "
        f"items. Production Plan **{pp_name}** has been updated. Work Order **{wo_name}** "
        f"is linked to this Production Plan and must now be updated to manufacture "
        f"the correct revised quantity."
    )
    lines.append("")

    lines.append("## What Changed on the Sales Order")
    has_changes = False
    for item in item_codes:
        info = changed_items.get(item, {})
        if info.get("item_changed"):
            has_changes = True
            lines.append(f"- Item code changed: **{item}** → **{info['display_item']}**")
        if info.get("qty_changed"):
            has_changes = True
            lines.append(
                f"- Item **{item}**: Qty changed from **{info['old_qty']}** → **{info['new_qty']}**"
            )
        
    if not has_changes:
        lines.append("- No item-level changes detected.")
    lines.append("")

    lines.append("## Before You Start")
    lines.append(
        f"Confirm that Production Plan **{pp_name}** has already been refreshed and "
        f"saved. Update this Work Order only after the PP task is marked complete."
    )
    lines.append("")

    lines.append("## Steps to Complete This Task")
    lines.append(f"1. Open Work Order **{wo_name}**.")
    lines.append(
        "2. Click **Refresh Work Order** to pull the latest production quantities "
        "from the refreshed Production Plan."
    )
    lines.append(
        "3. Verify that **Qty to Manufacture** and the raw material table have "
        "updated to reflect the new values above."
    )
    lines.append("")
    lines.append(
        "**Important:** If this Work Order is already **In Process**, coordinate "
        "with the production supervisor before making changes."
    )

    return "\n".join(lines)


def _build_po_description(po_name, pp_name, so_name, item_codes, changed_items):
    lines = []
    lines.append("## Why This Task Was Created")
    lines.append(
        f"Sales Order **{so_name}** was modified with revised item quantities or codes. "
        f"This change cascaded through the production chain — Production Plan **{pp_name}** "
        f"was refreshed and related Work Orders were updated. As a result, the raw material "
        f"requirements for Purchase Order **{po_name}** have changed."
    )
    lines.append("")

    lines.append("## Quantities to Update in the PO Modification Request")
    has_changes = False
    for item in item_codes:
        info = changed_items.get(item, {})
        if info.get("item_changed") or info.get("qty_changed"):
            has_changes = True
            lines.append(f"### Item: {item}")
            if info.get("item_changed"):
                lines.append(f"- **New item code:** {info['display_item']}")
            if info.get("qty_changed"):
                lines.append(f"- **Current Qty on PO:** {info['old_qty']}")
                lines.append(f"- **Revised Qty to set:** {info['new_qty']}")
            
            lines.append("")

    if not has_changes:
        lines.append("- No item-level changes detected.")
        lines.append("")

    lines.append("## Before You Start")
    lines.append(
        f"Confirm these upstream tasks are complete before raising the PO Modification Request:"
    )
    lines.append(f"- Production Plan **{pp_name}** — refreshed and saved")
    lines.append(f"- Work Orders linked to **{pp_name}** — updated and saved")
    lines.append("")

    lines.append("## Steps to Complete This Task")
    lines.append(
        f"1. Go to **Purchase Order Modification Request** and create a new request "
        f"against Purchase Order **{po_name}**."
    )
    lines.append(
        "2. Enter the revised qty for each item as listed above."
    )
    lines.append(
        f"3. Enter the reason for change — reference Sales Order **{so_name}** modification."
    )
    lines.append(
        "4. Contact the supplier to inform them of the change before or immediately after submitting."
    )
    lines.append("5. Submit the Purchase Order Modification Request.")
    lines.append(
        "6. Confirm with the supplier that they have acknowledged the updated quantities."
    )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Generic task creator
# ---------------------------------------------------------------------------

def _create_single_task(category, reference_doctype, reference_document_name,
                        subject, description, remarks, branch=None):
    """Inserts and submits one Modification Task. Returns the task name."""
    task = frappe.get_doc({
        "doctype": "Modification Task",
        "category": category,
        "subject": subject,
        "description": description,
        "remarks": remarks,
        "reference_doctype": reference_doctype,
        "reference_document_name": reference_document_name,
        "status": "Pending",
        "branch": branch,
    })
    task.insert(ignore_permissions=True)
    task.submit()
    return task.name




# =============================================================================
# STAGE 1 — Order Modification Request submitted → BOM Modification Task
# =============================================================================

def create_bom_task_on_omr_submit(doc):
    """
    Hook into OMR.on_submit (after BMRs are created and
    update_child_rows_with_omr has already linked bom_update_request).

    Creates ONE consolidated BOM Modification Task per OMR, listing every
    item-changed row. Qty-only rows are skipped here — they have no BOM step.
    """
    if doc.doctype != "Order Modification Request" or not doc.sales_order_item:
        return

    # Item-change rows only: rev_item set and different from item,
    # AND already linked to a BMR
    item_rows = [
        row for row in doc.sales_order_item
        if getattr(row, "rev_item", None)
        and row.rev_item != row.item
        and getattr(row, "bom_update_request", None)
    ]
    if not item_rows:
        return

    # Fetch source BOM for every linked BMR in a single query
    bmr_names = list({row.bom_update_request for row in item_rows})
    bom_map = dict(
        frappe.get_all(
            "Bom Modification Request",
            filters={"name": ["in", bmr_names]},
            fields=["name", "bom"],
            as_list=True,
        )
    )

    lines = _build_bom_task_description(doc, item_rows, bom_map)

    _create_single_task(
        category="BOM Modification",
        reference_doctype="Sales Order",
        reference_document_name=doc.sales_order,
        subject=f"BOM modification for SO {doc.sales_order}",
        description=lines,
        remarks=doc.reason_for_change,
        branch=doc.branch,
    )


def _build_bom_task_description(doc, item_rows, bom_map):
    lines = []
    lines.append("## Why This Task Was Created")
    lines.append(
        f"Sales Order **{doc.sales_order}** was modified and one or more finished "
        f"item codes were changed. A BOM Modification Request has been created for "
        f"each affected item. Review and complete each one below before production "
        f"planning can continue."
    )
    lines.append("")
    lines.append("## Affected Items")
    lines.append("")

    for row in item_rows:
        lines.append("### Item Change")
        lines.append(f"- **Original Item Code :** {row.item}")
        lines.append(f"- **Revised Item Code  :** {row.rev_item}")
        if getattr(row, "batch_no", None):
            lines.append(f"- **Batch Reference    :** {row.batch_no}")
        if flt(getattr(row, "rev_qty", 0)) and flt(row.rev_qty) != flt(row.qty):
            lines.append(f"- **Qty Change          :** {row.qty} → {row.rev_qty}")
        lines.append("")
        lines.append("**BOM References**")
        source_bom = bom_map.get(row.bom_update_request)
        if source_bom:
            lines.append(f"- **Reference BOM            :** {source_bom}")
        lines.append(f"- **BOM Modification Request :** {row.bom_update_request}")
        lines.append("")

    lines.append("## Steps to Complete This Task")
    lines.append("1. Open each **BOM Modification Request** listed above.")
    lines.append("2. Review and correct the copied BOM components, operations, and routing.")
    lines.append("3. Add/remove/modify components, quantities, or operations as required.")
    lines.append("4. Save and submit each BOM Modification Request once complete.")
    lines.append("5. Inform the Planning team once BOMs are ready for manufacturing.")
    lines.append("6. Mark this task complete so Production Planning can proceed.")
    lines.append("")
    lines.append(
        "**Important:** Production Planning must not proceed until all BOM "
        "Modification Requests listed above are reviewed and submitted."
    )
    return "\n".join(lines)


# =============================================================================
# STAGE 2 — BOM Modification Request submitted → Production Plan Task
# =============================================================================

def create_pp_task_on_bmr_submit(doc):
    """
    Hook into Bom Modification Request.on_submit.

    Finds the OMR row(s) that link to THIS BMR via bom_update_request,
    then creates Production Plan Modification Task(s) for the downstream
    Production Plans tied to that Sales Order + item.
    """
    if doc.doctype != "Bom Modification Request":
        return

    # Single query: find every OMR child row pointing at this BMR
    linked_rows = frappe.get_all(
        "Sales Order Item For OMR",
        filters={"bom_update_request": doc.name},
        fields=["parent", "item", "rev_item", "qty", "rev_qty", "batch_no"],
    )
    if not linked_rows:
        frappe.log_error(
            title="Modification Task: BMR has no linked OMR row",
            message=f"BMR {doc.name} — bom_update_request not found on any OMR row",
        )
        return

    omr_names = list({r.parent for r in linked_rows})
    sales_orders = dict(
        frappe.get_all(
            "Order Modification Request",
            filters={"name": ["in", omr_names]},
            fields=["name", "sales_order", "reason_for_change", "branch"],
            as_list=False,
        )
        and [(o.name, o) for o in frappe.get_all(
            "Order Modification Request",
            filters={"name": ["in", omr_names]},
            fields=["name", "sales_order", "reason_for_change", "branch"],
        )]
    )

    changed_items = {
        row.item: {
            "display_item": row.rev_item,
            "old_qty": flt(row.qty),
            "new_qty": flt(row.rev_qty) if flt(row.rev_qty) else flt(row.qty),
            "item_changed": True,
            "qty_changed": bool(flt(row.rev_qty) and flt(row.rev_qty) != flt(row.qty)),
        }
        for row in linked_rows
    }

    # All linked rows should share the same sales_order in practice;
    # group defensively in case they don't.
    for omr_name, omr_info in sales_orders.items():
        items_for_this_omr = {
            r.item: changed_items[r.item] for r in linked_rows if r.parent == omr_name
        }
        if not items_for_this_omr:
            continue
        _create_pp_tasks_for_items(
            sales_order=omr_info.sales_order,
            changed_items=items_for_this_omr,
            reason=omr_info.reason_for_change,
        )


def _create_pp_tasks_for_items(sales_order, changed_items, reason):
    pp_item_map = _get_production_plans_for_items(sales_order, list(changed_items.keys()))
    for pp_name, items_in_pp in pp_item_map.items():
        description = _build_pp_description(pp_name, sales_order, items_in_pp, changed_items)
        branch = frappe.db.get_value("Production Plan", pp_name, "branch")
        _create_single_task(
            category="Production Plan Update",
            reference_doctype="Production Plan",
            reference_document_name=pp_name,
            subject=f"Modification for {pp_name}",
            description=description,
            remarks=reason,
            branch=branch,
        )


# =============================================================================
# STAGE 3 — "Gate Update" clicked on Production Plan → WO + PO Tasks
# =============================================================================

def create_wo_po_tasks_on_gate_update(pp_doc):
    """
    Hook into the Production Plan Gate Update whitelisted method,
    AFTER the actual refresh logic has run.
    """
    pp_name = pp_doc.name

    item_codes = frappe.get_all(
        "Production Plan Item",
        filters={"parent": pp_name},
        pluck="item_code",
    )
    if not item_codes:
        return

    sales_order = frappe.db.get_value(
        "Production Plan Item", {"parent": pp_name}, "sales_order"
    )

    # Pull changed-item context (qty/item change) straight from OMR rows
    # tied to this sales_order + item set — single query, no doc loads.
    omr_rows = frappe.get_all(
        "Sales Order Item For OMR",
        filters={
            "item": ["in", item_codes],
            "docstatus": 1,
        },
        fields=["parent", "item", "rev_item", "qty", "rev_qty"],
    )
    if not omr_rows:
        return

    changed_items = {
        row.item: {
            "display_item": row.rev_item or row.item,
            "old_qty": flt(row.qty),
            "new_qty": flt(row.rev_qty) if flt(row.rev_qty) else flt(row.qty),
            "item_changed": bool(row.rev_item and row.rev_item != row.item),
            "qty_changed": bool(flt(row.rev_qty) and flt(row.rev_qty) != flt(row.qty)),
        }
        for row in omr_rows
    }

    wo_item_map = _get_work_orders_for_pp_items(pp_name, list(changed_items.keys()))
    for wo_name, wo_items in wo_item_map.items():
        wo_description = _build_wo_description(wo_name, pp_name, sales_order, wo_items, changed_items)
        branch = frappe.db.get_value("Work Order", wo_name, "branch")
        _create_single_task(
            category="Work Order Update",
            reference_doctype="Work Order",
            reference_document_name=wo_name,
            subject=f"Modification for {wo_name}",
            description=wo_description,
            remarks="Triggered via Production Plan Gate Update",
            branch=branch,
        )

    po_item_map = _get_purchase_orders_for_pp_items(pp_name, list(changed_items.keys()))
    for po_name, po_items in po_item_map.items():
        po_description = _build_po_description(po_name, pp_name, sales_order, po_items, changed_items)
        branch = frappe.db.get_value("Purchase Order", po_name, "branch")
        _create_single_task(
            category="Purchase Order Modification",
            reference_doctype="Purchase Order",
            reference_document_name=po_name,
            subject=f"Modification for {po_name}",
            description=po_description,
            remarks="Triggered via Production Plan Gate Update",
            branch=branch,
        )