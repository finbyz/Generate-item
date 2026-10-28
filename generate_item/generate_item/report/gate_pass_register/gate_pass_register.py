# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt



import frappe
from frappe import _
from frappe.utils import flt, cstr


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

def execute(filters=None):
    filters = frappe._dict(filters or {})
    columns = get_columns()
    data    = get_data(filters)
    return columns, data


# ---------------------------------------------------------------------------
# COLUMNS
# ---------------------------------------------------------------------------

def get_columns():
    return [
        # ── OUTWARD INFO ──────────────────────────────────────────────────
        {
            "label"    : _("Outward #"),
            "fieldname": "outward_no",
            "fieldtype": "Link",
            "options"  : "Gate Pass Outward",
            "width"    : 140,
        },
        {
            "label"    : _("Date"),
            "fieldname": "date",
            "fieldtype": "Date",
            "width"    : 100,
        },
        {
            "label"    : _("Branch"),
            "fieldname": "branch",
            "fieldtype": "Data",
            "width"    : 100,
        },
        {
            "label"    : _("Purpose"),
            "fieldname": "purpose",
            "fieldtype": "Data",
            "width"    : 100,
        },
        {
            "label"    : _("Party Type"),
            "fieldname": "party_type",
            "fieldtype": "Data",
            "width"    : 90,
        },
        {
            "label"    : _("Party Name"),
            "fieldname": "party_name",
            "fieldtype": "Data",
            "width"    : 150,
        },
        {
            "label"    : _("Email By"),
            "fieldname": "email_by",
            "fieldtype": "Link",
            "options"  : "User",
            "width"    : 140,
        },
        {
            "label"    : _("Transporter"),
            "fieldname": "transporter_name",
            "fieldtype": "Data",
            "width"    : 130,
        },
        {
            "label"    : _("Vehicle No"),
            "fieldname": "vehicle_no",
            "fieldtype": "Data",
            "width"    : 100,
        },
        {
            "label"    : _("LR No"),
            "fieldname": "lr_no",
            "fieldtype": "Data",
            "width"    : 90,
        },
        {
            "label"    : _("Road Permit"),
            "fieldname": "road_permit_no",
            "fieldtype": "Data",
            "width"    : 100,
        },
        {
            "label"    : _("Returnable"),
            "fieldname": "returnable",
            "fieldtype": "Data",
            "width"    : 90,
        },
        {
            "label"    : _("Outward Remarks"),
            "fieldname": "outward_remarks",
            "fieldtype": "Data",
            "width"    : 180,
        },

        # ── ITEM / COMPONENT INFO ─────────────────────────────────────────
        {
            "label"    : _("Sub Component"),
            "fieldname": "sub_component",
            "fieldtype": "Data",
            "width"    : 140,
        },
        {
            "label"    : _("Description"),
            "fieldname": "description",
            "fieldtype": "Data",
            "width"    : 220,
        },
        {
            "label"    : _("Rate"),
            "fieldname": "rate",
            "fieldtype": "Currency",
            "width"    : 90,
        },
        {
            "label"    : _("Sent Qty"),
            "fieldname": "sent_qty",
            "fieldtype": "Float",
            "width"    : 80,
        },
        {
            "label"    : _("Total Sent Amount"),
            "fieldname": "total_amount",
            "fieldtype": "Currency",
            "width"    : 130,
        },

        # ── INWARD AGGREGATES ─────────────────────────────────────────────
        {
            "label"    : _("Total Received"),
            "fieldname": "total_received",
            "fieldtype": "Float",
            "width"    : 110,
        },
        {
            "label"    : _("Pending Qty"),
            "fieldname": "pending_qty",
            "fieldtype": "Float",
            "width"    : 100,
        },
        {
            "label"    : _("Last Received On"),
            "fieldname": "last_received_on",
            "fieldtype": "Date",
            "width"    : 120,
        },
        {
            "label"    : _("Inward Ref(s)"),
            "fieldname": "inward_refs",
            "fieldtype": "Data",
            "width"    : 160,
        },
        {
            "label"    : _("Received Quality"),
            "fieldname": "received_quality",
            "fieldtype": "Data",
            "width"    : 120,
        },
        {
            "label"    : _("Billing Status"),
            "fieldname": "billing_status",
            "fieldtype": "Data",
            "width"    : 120,
        },
        {
            "label"    : _("Bill Amount"),
            "fieldname": "bill_amount",
            "fieldtype": "Currency",
            "width"    : 100,
        },
        {
            "label"    : _("Inward Remarks"),
            "fieldname": "inward_remarks",
            "fieldtype": "Data",
            "width"    : 180,
        },

        # ── COMPONENT MASTER ──────────────────────────────────────────────
        {
            "label"    : _("Component Status"),
            "fieldname": "component_status",
            "fieldtype": "Data",
            "width"    : 130,
        },
        {
            "label"    : _("Installed Date"),
            "fieldname": "installed_date",
            "fieldtype": "Date",
            "width"    : 110,
        },
        {
            "label"    : _("Component Remarks"),
            "fieldname": "component_remarks",
            "fieldtype": "Data",
            "width"    : 200,
        },

        # ── STOCK ENTRY ───────────────────────────────────────────────────
        {
            "label"    : _("Outward SE Ref"),
            "fieldname": "outward_se_ref",
            "fieldtype": "Link",
            "options"  : "Stock Entry",
            "width"    : 140,
        },
        {
            "label"    : _("Outward SE Type"),
            "fieldname": "outward_se_type",
            "fieldtype": "Data",
            "width"    : 160,
        },
        {
            "label"    : _("Inward SE Ref"),
            "fieldname": "inward_se_ref",
            "fieldtype": "Link",
            "options"  : "Stock Entry",
            "width"    : 140,
        },
        {
            "label"    : _("Inward SE Type"),
            "fieldname": "inward_se_type",
            "fieldtype": "Data",
            "width"    : 160,
        },

        # ── DERIVED STATUS ────────────────────────────────────────────────
        {
            "label"    : _("GP Status"),
            "fieldname": "gp_status",
            "fieldtype": "Data",
            "width"    : 120,
        },
        {
            "label"    : _("Aging (Days)"),
            "fieldname": "aging_days",
            "fieldtype": "Int",
            "width"    : 100,
        },
    ]


# ---------------------------------------------------------------------------
# DATA
# ---------------------------------------------------------------------------

def get_data(filters):
    conditions, values = build_conditions(filters)

    # Sub Component / Item condition
    item_cond = conditions
    detail_cond = conditions
    if filters.get("sub_component"):
        item_cond += " AND gpoi.sub_component = %(sub_component)s"
        detail_cond += " AND gpod.item = %(sub_component)s"
        values["sub_component"] = filters.sub_component

    # ── 1. Gate Pass Outward items from BOTH child tables ──────────────────
    # 1A: Non-stock / Components (Gate Pass Outward Item)
    outward_item_rows = frappe.db.sql(
        f"""
        SELECT
            gpo.name           AS outward_no,
            gpo.date,
            gpo.branch,
            gpo.purpose,
            gpo.party_type,
            gpo.party_name,
            gpo.email_by,
            gpo.transporter_name,
            gpo.vehicle_no,
            gpo.lr_no,
            gpo.road_permit_no,
            gpo.returnable,
            gpo.remarks        AS outward_remarks,
            gpo.status         AS gpo_doc_status,
            gpo.docstatus      AS docstatus,
            gpo.stock_entry    AS outward_se_ref,
            gpo.is_stock_item,
            gpoi.name          AS child_row_id,
            gpoi.sub_component AS sub_component,
            gpoi.description,
            gpoi.rate,
            gpoi.qty           AS sent_qty,
            gpoi.amount        AS total_amount,
            gpoi.received_qty  AS row_received_qty,
            gpoi.pending_qty   AS row_pending_qty,
            'Item'             AS item_table_type
        FROM `tabGate Pass Outward` gpo
        INNER JOIN `tabGate Pass Outward Item` gpoi
               ON gpoi.parent = gpo.name AND gpoi.parenttype = 'Gate Pass Outward'
        WHERE gpo.docstatus = 1
          AND NOT (COALESCE(gpoi.sub_component, '') = '' AND COALESCE(gpoi.qty, 0) = 0)
          {item_cond}
        """,
        values,
        as_dict=True,
    )

    # 1B: Stock Items (Gate Pass Outward Detail)
    outward_detail_rows = frappe.db.sql(
        f"""
        SELECT
            gpo.name           AS outward_no,
            gpo.date,
            gpo.branch,
            gpo.purpose,
            gpo.party_type,
            gpo.party_name,
            gpo.email_by,
            gpo.transporter_name,
            gpo.vehicle_no,
            gpo.lr_no,
            gpo.road_permit_no,
            gpo.returnable,
            gpo.remarks        AS outward_remarks,
            gpo.status         AS gpo_doc_status,
            gpo.docstatus      AS docstatus,
            gpo.stock_entry    AS outward_se_ref,
            gpo.is_stock_item,
            gpod.name          AS child_row_id,
            gpod.item          AS sub_component,
            gpod.description,
            gpod.rate,
            gpod.qty           AS sent_qty,
            gpod.amount        AS total_amount,
            gpod.received_qty  AS row_received_qty,
            gpod.pending_qty   AS row_pending_qty,
            'Detail'           AS item_table_type
        FROM `tabGate Pass Outward` gpo
        INNER JOIN `tabGate Pass Outward Detail` gpod
               ON gpod.parent = gpo.name AND gpod.parenttype = 'Gate Pass Outward'
        WHERE gpo.docstatus = 1
          AND NOT (COALESCE(gpod.item, '') = '' AND COALESCE(gpod.qty, 0) = 0)
          {detail_cond}
        """,
        values,
        as_dict=True,
    )

    outward_rows = outward_item_rows + outward_detail_rows

    # Fallback: if an outward has no items in either table, ensure it is still included
    found_outwards = {r.outward_no for r in outward_rows}
    if not filters.get("sub_component"):
        empty_outwards = frappe.db.sql(
            f"""
            SELECT
                gpo.name           AS outward_no,
                gpo.date,
                gpo.branch,
                gpo.purpose,
                gpo.party_type,
                gpo.party_name,
                gpo.email_by,
                gpo.transporter_name,
                gpo.vehicle_no,
                gpo.lr_no,
                gpo.road_permit_no,
                gpo.returnable,
                gpo.remarks        AS outward_remarks,
                gpo.status         AS gpo_doc_status,
                gpo.docstatus      AS docstatus,
                gpo.stock_entry    AS outward_se_ref,
                gpo.is_stock_item,
                NULL               AS child_row_id,
                NULL               AS sub_component,
                NULL               AS description,
                0                  AS rate,
                0                  AS sent_qty,
                0                  AS total_amount,
                0                  AS row_received_qty,
                0                  AS row_pending_qty,
                'None'             AS item_table_type
            FROM `tabGate Pass Outward` gpo
            WHERE gpo.docstatus = 1
              {conditions}
            """,
            values,
            as_dict=True,
        )
        for eo in empty_outwards:
            if eo.outward_no not in found_outwards:
                outward_rows.append(eo)

    if not outward_rows:
        return []

    outward_rows.sort(key=lambda r: (str(r.date or ""), str(r.outward_no or "")), reverse=True)

    outward_names = list({r.outward_no for r in outward_rows if r.outward_no})

    # ── 2. Gate Pass Inward items aggregated per outward + item/component ──
    inward_by_child_id = {}
    inward_by_key = {}
    inward_bill_map = {}

    if outward_names:
        placeholders = ", ".join(["%s"] * len(outward_names))
        inward_rows = frappe.db.sql(
            f"""
            SELECT
                gpi.gate_pass_outward,
                gpii.gate_pass_outward_item                      AS outward_row_id,
                gpii.sub_component                               AS item_key,
                COALESCE(NULLIF(gpii.receiving_now, 0), gpii.sent_qty, 0) AS received_qty,
                gpi.date                                         AS inward_date,
                gpi.name                                         AS inward_no,
                gpii.quality                                     AS received_quality,
                gpi.billing_status                               AS billing_status,
                gpi.bill_amount                                  AS bill_amount,
                gpi.stock_entry                                  AS inward_se_ref,
                gpi.remarks                                      AS inward_remarks
            FROM `tabGate Pass Inward` gpi
            INNER JOIN `tabGate Pass Inward Item` gpii
                   ON gpii.parent = gpi.name AND gpii.parenttype = 'Gate Pass Inward'
            WHERE gpi.docstatus = 1
              AND gpi.gate_pass_outward IN ({placeholders})

            UNION ALL

            SELECT
                gpi.gate_pass_outward,
                gpid.gate_pass_outward_detail                    AS outward_row_id,
                gpid.item                                        AS item_key,
                COALESCE(gpid.qty, 0)                            AS received_qty,
                gpi.date                                         AS inward_date,
                gpi.name                                         AS inward_no,
                NULL                                             AS received_quality,
                gpi.billing_status                               AS billing_status,
                gpi.bill_amount                                  AS bill_amount,
                gpi.stock_entry                                  AS inward_se_ref,
                gpi.remarks                                      AS inward_remarks
            FROM `tabGate Pass Inward` gpi
            INNER JOIN `tabGate Pass Inward Detail` gpid
                   ON gpid.parent = gpi.name AND gpid.parenttype = 'Gate Pass Inward'
            WHERE gpi.docstatus = 1
              AND gpi.gate_pass_outward IN ({placeholders})
            """,
            tuple(outward_names) + tuple(outward_names),
            as_dict=True,
        )

        def accumulate(inward_dict, k, r):
            if k not in inward_dict:
                inward_dict[k] = {
                    "total_received": 0.0,
                    "inward_dates": [],
                    "inward_refs": set(),
                    "qualities": set(),
                    "billing_statuses": set(),
                    "inward_se_refs": set(),
                    "inward_remarks": set(),
                }
            agg = inward_dict[k]
            agg["total_received"] += flt(r.received_qty)
            if r.inward_date:
                agg["inward_dates"].append(str(r.inward_date))
            if r.inward_no:
                agg["inward_refs"].add(r.inward_no)
            if r.received_quality:
                agg["qualities"].add(r.received_quality)
            if r.billing_status:
                agg["billing_statuses"].add(r.billing_status)
            if r.inward_se_ref:
                agg["inward_se_refs"].add(r.inward_se_ref)
            if r.inward_remarks:
                agg["inward_remarks"].add(r.inward_remarks)

        for r in inward_rows:
            if r.inward_no and r.bill_amount:
                inward_bill_map[r.inward_no] = flt(r.bill_amount)
            if r.outward_row_id:
                accumulate(inward_by_child_id, (r.gate_pass_outward, r.outward_row_id), r)
            if r.item_key:
                accumulate(inward_by_key, (r.gate_pass_outward, r.item_key), r)

    # ── 3. Gatepass Component master data ─────────────────────────────────
    sub_component_names = list({
        r.sub_component for r in outward_rows
        if r.sub_component and r.get("item_table_type") == "Item"
    })
    component_map = {}
    if sub_component_names:
        placeholders = ", ".join(["%s"] * len(sub_component_names))
        comp_rows = frappe.db.sql(
            f"""
            SELECT
                name,
                status         AS component_status,
                installed_date,
                remarks        AS component_remarks
            FROM `tabGatepass Component`
            WHERE name IN ({placeholders})
            """,
            tuple(sub_component_names),
            as_dict=True,
        )
        component_map = {r.name: r for r in comp_rows}

    # ── 4. Stock Entry type lookup ────────────────────────────────────────
    se_refs = list({r.outward_se_ref for r in outward_rows if r.get("outward_se_ref")})
    se_type_map = {}
    if se_refs:
        placeholders = ", ".join(["%s"] * len(se_refs))
        se_rows = frappe.db.sql(
            f"""
            SELECT name, stock_entry_type
            FROM `tabStock Entry`
            WHERE name IN ({placeholders})
            """,
            tuple(se_refs),
            as_dict=True,
        )
        se_type_map = {r.name: r.stock_entry_type for r in se_rows}

    # ── 5. User lookup (bulk, avoids N+1 queries) ─────────────────────────
    user_names = list({r.email_by for r in outward_rows if r.email_by})
    user_map = {}
    if user_names:
        users = frappe.get_all(
            "User",
            filters={"name": ["in", user_names]},
            fields=["name", "full_name"],
        )
        user_map = {u.name: (u.full_name or u.name) for u in users}

    # ── 6. Merge everything ────────────────────────────────────────────────
    today = frappe.utils.today()
    result = []

    for row in outward_rows:
        # Match inward data by child_row_id first, then (outward_no, sub_component)
        inward_agg = None
        if row.child_row_id and (row.outward_no, row.child_row_id) in inward_by_child_id:
            inward_agg = inward_by_child_id[(row.outward_no, row.child_row_id)]
        elif row.sub_component and (row.outward_no, row.sub_component) in inward_by_key:
            inward_agg = inward_by_key[(row.outward_no, row.sub_component)]

        if inward_agg:
            inward_received = flt(inward_agg["total_received"])
            total_received  = inward_received if inward_received > 0 else flt(row.get("row_received_qty", 0))
            dates           = sorted(inward_agg["inward_dates"], reverse=True)
            last_received_on= dates[0] if dates else None
            inward_refs     = ", ".join(sorted(inward_agg["inward_refs"])) if inward_agg["inward_refs"] else "—"
            received_quality= ", ".join(sorted(inward_agg["qualities"])) if inward_agg["qualities"] else "—"
            billing_status  = ", ".join(sorted(inward_agg["billing_statuses"])) if inward_agg["billing_statuses"] else "—"
            bill_amount     = sum(inward_bill_map.get(ref, 0) for ref in inward_agg["inward_refs"])
            inward_se_ref   = ", ".join(sorted(inward_agg["inward_se_refs"])) if inward_agg["inward_se_refs"] else "—"
            inward_remarks  = "; ".join(sorted(inward_agg["inward_remarks"])) if inward_agg["inward_remarks"] else "—"
        else:
            total_received  = flt(row.get("row_received_qty", 0))
            last_received_on= None
            inward_refs     = "—"
            received_quality= "—"
            billing_status  = "—"
            bill_amount     = 0.0
            inward_se_ref   = "—"
            inward_remarks  = "—"

        sent_qty   = flt(row.sent_qty)
        returnable = cstr(row.returnable).strip()

        # Derived: GP Status & Pending Qty (Only Returnable items can have pending return qty)
        if returnable == "No":
            gp_status   = "Non-Returnable"
            pending_qty = 0.0
        else:
            pending_qty = max(sent_qty - total_received, 0)
            if total_received == 0:
                gp_status = "Open"
            elif pending_qty == 0:
                gp_status = "Closed"
            else:
                gp_status = "Partial"

        # Derived: Aging (days outward has been open - Returnable only)
        if returnable == "Yes":
            aging_days = frappe.utils.date_diff(today, row.date) if row.date else 0
        else:
            aging_days = 0

        # Stock entry type derivation
        outward_se_ref  = row.get("outward_se_ref") or ""
        outward_se_type = se_type_map.get(outward_se_ref, "")
        if not outward_se_type:
            if returnable == "Yes":
                outward_se_type = "Material Transfer (Outward)"
            else:
                outward_se_type = "Material Issue"

        inward_se_type = "Material Transfer (Inward Reverse)" if (inward_se_ref and inward_se_ref != "—") else "—"

        comp = component_map.get(row.sub_component, {})
        email_by = user_map.get(row.email_by) or row.email_by or "—"

        result.append(
            frappe._dict(
                # Outward
                outward_no        = row.outward_no,
                date              = row.date,
                branch            = row.branch,
                purpose           = row.purpose,
                party_type        = row.party_type,
                party_name        = row.party_name,
                email_by          = email_by,
                transporter_name  = row.transporter_name,
                vehicle_no        = row.vehicle_no,
                lr_no             = row.lr_no,
                road_permit_no    = row.road_permit_no,
                returnable        = returnable,
                outward_remarks   = row.outward_remarks,
                docstatus         = row.get("docstatus", 1),
                is_stock_item     = row.get("is_stock_item", 0),
                item_table_type   = row.get("item_table_type", ""),
                # Item
                sub_component     = row.sub_component or "—",
                description       = row.description or "—",
                rate              = flt(row.rate),
                sent_qty          = sent_qty,
                total_amount      = flt(row.total_amount),
                # Inward
                total_received    = total_received,
                pending_qty       = pending_qty,
                last_received_on  = last_received_on,
                inward_refs       = inward_refs,
                received_quality  = received_quality,
                billing_status    = billing_status,
                bill_amount       = flt(bill_amount),
                inward_remarks    = inward_remarks,
                # Component
                component_status  = comp.get("component_status") or "—",
                installed_date    = comp.get("installed_date"),
                component_remarks = comp.get("component_remarks") or "—",
                # Stock Entry
                outward_se_ref    = outward_se_ref or "—",
                outward_se_type   = outward_se_type,
                inward_se_ref     = inward_se_ref or "—",
                inward_se_type    = inward_se_type or "—",
                # Derived
                gp_status         = gp_status,
                aging_days        = aging_days,
            )
        )

    return result


# ---------------------------------------------------------------------------
def resolve_period(period):
    import datetime
    from frappe.utils import add_days, add_months, getdate, nowdate

    today = getdate(nowdate())
    if not period or period == "Custom":
        return None, None

    if period == "Today":
        return today, today
    elif period == "This Week":
        start = today - datetime.timedelta(days=today.weekday())
        return start, today
    elif period == "Last Week":
        start = today - datetime.timedelta(days=today.weekday() + 7)
        end = start + datetime.timedelta(days=6)
        return start, end
    elif period == "This Month":
        start = today.replace(day=1)
        return start, today
    elif period == "Last Month":
        last_day_prev_month = today.replace(day=1) - datetime.timedelta(days=1)
        start = last_day_prev_month.replace(day=1)
        return start, last_day_prev_month
    elif period == "This Quarter":
        start = add_months(today, -3)
        return start, today
    elif period == "Last Quarter":
        this_q_start = add_months(today, -3)
        last_q_end = add_days(this_q_start, -1)
        last_q_start = add_months(this_q_start, -3)
        return last_q_start, last_q_end
    elif period == "This Year":
        start = today.replace(month=1, day=1)
        return start, today
    elif period == "Last Year":
        start = today.replace(year=today.year - 1, month=1, day=1)
        end = today.replace(year=today.year - 1, month=12, day=31)
        return start, end
    return None, None


# ---------------------------------------------------------------------------
# FILTERS  (SQL conditions builder)
# ---------------------------------------------------------------------------

def build_conditions(filters):
    conditions = []
    values = {}

    if filters.get("period") and filters.get("period") != "Custom":
        p_from, p_to = resolve_period(filters.get("period"))
        if p_from and not filters.get("from_date"):
            filters["from_date"] = p_from
        if p_to and not filters.get("to_date"):
            filters["to_date"] = p_to

    if filters.get("branch"):
        conditions.append("gpo.branch = %(branch)s")
        values["branch"] = filters.branch

    if filters.get("from_date"):
        conditions.append("gpo.date >= %(from_date)s")
        values["from_date"] = filters.from_date

    if filters.get("to_date"):
        conditions.append("gpo.date <= %(to_date)s")
        values["to_date"] = filters.to_date

    if filters.get("party_type"):
        conditions.append("gpo.party_type = %(party_type)s")
        values["party_type"] = filters.party_type

    if filters.get("party_name"):
        conditions.append("gpo.party_name = %(party_name)s")
        values["party_name"] = filters.party_name

    if filters.get("gate_pass_outward"):
        conditions.append("gpo.name = %(gate_pass_outward)s")
        values["gate_pass_outward"] = filters.gate_pass_outward

    if filters.get("returnable"):
        conditions.append("gpo.returnable = %(returnable)s")
        values["returnable"] = filters.returnable

    cond_str = ("AND " + " AND ".join(conditions)) if conditions else ""
    return cond_str, values

# ---------------------------------------------------------------------------
# SUMMARY  (bottom totals row)
# ---------------------------------------------------------------------------

def get_summary(data):
    if not data:
        return []

    unique_gps = {r.outward_no for r in data if r.get("outward_no")}
    total_gate_pass = len(unique_gps)
    returnable_gps = {r.outward_no for r in data if r.get("outward_no") and r.get("returnable") == "Yes"}
    open_gps = {r.outward_no for r in data if r.get("outward_no") and r.get("gp_status") == "Open"}
    closed_gps = {r.outward_no for r in data if r.get("outward_no") and r.get("gp_status") == "Closed"}

    return [
        {"value": total_gate_pass,     "label": _("Total Gate Pass"), "datatype": "Int", "color": "blue"},
        {"value": len(returnable_gps), "label": _("Total Returnable"),"datatype": "Int", "color": "blue"},
        {"value": len(open_gps),       "label": _("Open"),            "datatype": "Int", "color": "orange"},
        {"value": len(closed_gps),     "label": _("Closed"),          "datatype": "Int", "color": "green"},
    ]


# ---------------------------------------------------------------------------
# CHART  (bar chart — sent vs received by party)
# ---------------------------------------------------------------------------

def get_chart(data):
    if not data:
        return None

    # Group by party
    party_data = {}
    for row in data:
        p = row.party_name or "Unknown"
        if p not in party_data:
            party_data[p] = {"sent": 0, "received": 0}
        party_data[p]["sent"]     += flt(row.sent_qty)
        party_data[p]["received"] += flt(row.total_received)

    labels   = list(party_data.keys())
    sent_val = [party_data[p]["sent"]     for p in labels]
    recv_val = [party_data[p]["received"] for p in labels]

    return {
        "data": {
            "labels"  : labels,
            "datasets": [
                {"name": _("Sent Qty"),     "values": sent_val},
                {"name": _("Received Qty"), "values": recv_val},
            ],
        },
        "type"   : "bar",
        "colors" : ["#5e64ff", "#2ecc71"],
        "barOptions": {"stacked": False},
    }