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
    # Summary rows (totals) appended at the bottom
    summary = get_summary(data)
    # Chart data returned as 4th return value (Frappe supports it)
    chart   = get_chart(data)
    return columns, data, None, chart


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
            "fieldtype": "Link",
            "options"  : "Gatepass Component",
            "width"    : 130,
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

    # ── 1. Gate Pass Outward items ─────────────────────────────────────────
    outward_rows = frappe.db.sql(
        """
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
            -- stock entry linked on outward (custom field se_ref; if not present, will be NULL)
            gpo.stock_entry         AS outward_se_ref,
            gpoi.sub_component,
            gpoi.description,
            gpoi.rate,
            gpoi.qty           AS sent_qty,
            gpoi.amount        AS total_amount
        FROM `tabGate Pass Outward` gpo
        INNER JOIN `tabGate Pass Outward Item` gpoi
               ON gpoi.parent = gpo.name
        WHERE gpo.docstatus = 1
          {conditions}
        ORDER BY gpo.date DESC, gpo.name
        """.format(conditions=conditions),
        values,
        as_dict=True,
    )

    if not outward_rows:
        return []

    outward_names = list({r.outward_no for r in outward_rows})

    # ── 2. Gate Pass Inward items aggregated per outward + sub_component ───
    inward_map = {}
    if outward_names:
        inward_rows = frappe.db.sql(
            """
            SELECT
                gpi.gate_pass_outward,
                gpii.sub_component,
                SUM(gpii.receiving_now)                          AS total_received,
                MAX(gpi.date)                                    AS last_received_on,
                GROUP_CONCAT(DISTINCT gpi.name ORDER BY gpi.date SEPARATOR ', ')
                                                                 AS inward_refs,
                GROUP_CONCAT(DISTINCT gpii.quality SEPARATOR ', ')
                                                                 AS received_quality,
                MAX(gpi.billing_status)                          AS billing_status,
                SUM(gpi.bill_amount)                             AS bill_amount,
                -- stock entry on inward (custom field se_ref)
                GROUP_CONCAT(DISTINCT gpi.stock_entry SEPARATOR ', ') AS inward_se_ref
            FROM `tabGate Pass Inward` gpi
            INNER JOIN `tabGate Pass Inward Item` gpii
                   ON gpii.parent = gpi.name
            WHERE gpi.docstatus = 1
              AND gpi.gate_pass_outward IN ({placeholders})
            GROUP BY gpi.gate_pass_outward, gpii.sub_component
            """.format(placeholders=", ".join(["%s"] * len(outward_names))),
            tuple(outward_names),
            as_dict=True,
        )
        for row in inward_rows:
            key = (row.gate_pass_outward, row.sub_component)
            inward_map[key] = row

    # ── 3. Gatepass Component master data ─────────────────────────────────
    sub_component_names = list({r.sub_component for r in outward_rows if r.sub_component})
    component_map = {}
    if sub_component_names:
        comp_rows = frappe.db.sql(
            """
            SELECT
                name,
                status         AS component_status,
                installed_date,
                remarks        AS component_remarks
            FROM `tabGatepass Component`
            WHERE name IN ({placeholders})
            """.format(placeholders=", ".join(["%s"] * len(sub_component_names))),
            tuple(sub_component_names),
            as_dict=True,
        )
        component_map = {r.name: r for r in comp_rows}

    # ── 4. Stock Entry type lookup (outward SE refs) ───────────────────────
    se_refs = list(
        {r.outward_se_ref for r in outward_rows if r.get("outward_se_ref")}
    )
    se_type_map = {}
    if se_refs:
        se_rows = frappe.db.sql(
            """
            SELECT name, stock_entry_type
            FROM `tabStock Entry`
            WHERE name IN ({placeholders})
            """.format(placeholders=", ".join(["%s"] * len(se_refs))),
            tuple(se_refs),
            as_dict=True,
        )
        se_type_map = {r.name: r.stock_entry_type for r in se_rows}

    # ── 5. Merge everything ────────────────────────────────────────────────
    today = frappe.utils.today()
    result = []

    for row in outward_rows:
        key      = (row.outward_no, row.sub_component)
        inward   = inward_map.get(key, frappe._dict())
        comp     = component_map.get(row.sub_component, frappe._dict())

        sent_qty       = flt(row.sent_qty)
        total_received = flt(inward.get("total_received", 0))
        pending_qty    = max(sent_qty - total_received, 0)

        # ── Derived: GP Status
        returnable = cstr(row.returnable).strip()
        if returnable == "No":
            gp_status = "Non-Returnable"
        elif total_received == 0:
            gp_status = "Open"
        elif pending_qty == 0:
            gp_status = "Closed"
        else:
            gp_status = "Partial"

        # ── Derived: Aging (days outward has been open)
        aging_days = frappe.utils.date_diff(today, row.date) if row.date else 0

        # ── Stock entry type derivation (fallback when se_ref not stored)
        outward_se_ref  = row.get("outward_se_ref") or ""
        outward_se_type = se_type_map.get(outward_se_ref, "")
        if not outward_se_type:
            if returnable == "Yes":
                outward_se_type = "Material Transfer (Outward)"
            else:
                outward_se_type = "Material Issue"

        # Inward SE refs (could be multiple inward docs each with an SE)
        inward_se_ref  = inward.get("inward_se_ref") or ""
        inward_se_type = ""
        if inward_se_ref:
            inward_se_type = "Material Transfer (Inward Reverse)"
        
        email_by = frappe.db.get_value("User", row.email_by, "full_name") or row.email_by

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
                # Item
                sub_component     = row.sub_component,
                description       = row.description,
                rate              = flt(row.rate),
                sent_qty          = sent_qty,
                total_amount      = flt(row.total_amount),
                # Inward
                total_received    = total_received,
                pending_qty       = pending_qty,
                last_received_on  = inward.get("last_received_on"),
                inward_refs       = inward.get("inward_refs") or "—",
                received_quality  = inward.get("received_quality") or "—",
                billing_status    = inward.get("billing_status") or "—",
                bill_amount       = flt(inward.get("bill_amount", 0)),
                inward_remarks    = inward.get("inward_remarks") or "—",
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
# FILTERS  (SQL conditions builder)
# ---------------------------------------------------------------------------

# def build_conditions(filters):
#     conditions = []
#     values     = {}

#     if filters.get("branch"):
#         conditions.append("gpo.branch = %(branch)s")
#         values["branch"] = filters.branch

#     if filters.get("from_date"):
#         conditions.append("gpo.date >= %(from_date)s")
#         values["from_date"] = filters.from_date

#     if filters.get("to_date"):
#         conditions.append("gpo.date <= %(to_date)s")
#         values["to_date"] = filters.to_date

#     if filters.get("party_name"):
#         conditions.append("gpo.party_name = %(party_name)s")
#         values["party_name"] = filters.party_name

#     if filters.get("returnable"):
#         conditions.append("gpo.returnable = %(returnable)s")
#         values["returnable"] = filters.returnable

#     if filters.get("purpose"):
#         conditions.append("gpo.purpose = %(purpose)s")
#         values["purpose"] = filters.purpose

#     if filters.get("sub_component"):
#         conditions.append("gpoi.sub_component = %(sub_component)s")
#         values["sub_component"] = filters.sub_component

#     if filters.get("gp_status"):
#         # This is a derived column; we filter in Python after fetching
#         pass

#     cond_str = ("AND " + " AND ".join(conditions)) if conditions else ""
#     return cond_str, values

# In build_conditions function:

def build_conditions(filters):
    conditions = []
    values = {}

    if filters.get("branch"):
        conditions.append("gpo.branch = %(branch)s")
        values["branch"] = filters.branch

    if filters.get("from_date"):
        conditions.append("gpo.date >= %(from_date)s")
        values["from_date"] = filters.from_date

    if filters.get("to_date"):
        conditions.append("gpo.date <= %(to_date)s")
        values["to_date"] = filters.to_date

    # Updated: Party Type filter
    if filters.get("party_type"):
        conditions.append("gpo.party_type = %(party_type)s")
        values["party_type"] = filters.party_type

    # Updated: Party Name filter (works with Dynamic Link)
    if filters.get("party_name"):
        conditions.append("gpo.party_name = %(party_name)s")
        values["party_name"] = filters.party_name

    # New: Gate Pass Outward filter
    if filters.get("gate_pass_outward"):
        conditions.append("gpo.name = %(gate_pass_outward)s")
        values["gate_pass_outward"] = filters.gate_pass_outward

    if filters.get("returnable"):
        conditions.append("gpo.returnable = %(returnable)s")
        values["returnable"] = filters.returnable

    if filters.get("sub_component"):
        conditions.append("gpoi.sub_component = %(sub_component)s")
        values["sub_component"] = filters.sub_component

    # New: Status filter from doctype
    if filters.get("status"):
        conditions.append("gpo.status = %(status)s")
        values["status"] = filters.status


    cond_str = ("AND " + " AND ".join(conditions)) if conditions else ""
    return cond_str, values

# ---------------------------------------------------------------------------
# SUMMARY  (bottom totals row)
# ---------------------------------------------------------------------------

def get_summary(data):
    if not data:
        return []

    total_sent     = sum(flt(r.sent_qty)       for r in data)
    total_received = sum(flt(r.total_received) for r in data)
    total_pending  = sum(flt(r.pending_qty)    for r in data)
    total_amount   = sum(flt(r.total_amount)   for r in data)

    open_count     = sum(1 for r in data if r.gp_status == "Open")
    partial_count  = sum(1 for r in data if r.gp_status == "Partial")
    closed_count   = sum(1 for r in data if r.gp_status == "Closed")
    nr_count       = sum(1 for r in data if r.gp_status == "Non-Returnable")

    return [
        {"value": total_sent,     "label": _("Total Sent Qty"),     "datatype": "Float",    "color": "blue"},
        {"value": total_received, "label": _("Total Received Qty"),  "datatype": "Float",    "color": "green"},
        {"value": total_pending,  "label": _("Total Pending Qty"),   "datatype": "Float",    "color": "orange"},
        {"value": total_amount,   "label": _("Total Sent Amount"),   "datatype": "Currency", "color": "blue"},
        {"value": open_count,     "label": _("Open"),                "datatype": "Int",      "color": "orange"},
        {"value": partial_count,  "label": _("Partial"),             "datatype": "Int",      "color": "yellow"},
        {"value": closed_count,   "label": _("Closed"),              "datatype": "Int",      "color": "green"},
        {"value": nr_count,       "label": _("Non-Returnable"),      "datatype": "Int",      "color": "red"},
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