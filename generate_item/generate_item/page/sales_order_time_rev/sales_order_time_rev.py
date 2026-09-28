# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, get_datetime, format_date, flt


@frappe.whitelist()
def get_dashboard_data(period=None, from_date=None, to_date=None, branch=None, sales_order=None, customer=None):
    """
    Returns Sales Order Phase Time Dashboard metrics and line items.
    Calculates elapsed days between key manufacturing/procurement milestones:
      Phase 1: SO Approval -> Last BOM Created
      Phase 2: Last BOM Created -> Last BOM Submitted
      Phase 3: Last BOM Submitted -> Last PO Submitted
      Phase 4: Last PO Submitted -> Last PR Submitted
      Phase 5: Last PR Submitted -> Last WO Submitted
      Overall: SO Approval -> Last WO Submitted
    """
    conditions = ["so.docstatus = 1"]
    values = {}

    if branch:
        conditions.append("so.branch = %(branch)s")
        values["branch"] = branch

    if sales_order:
        conditions.append("so.name = %(sales_order)s")
        values["sales_order"] = sales_order

    if customer:
        conditions.append("(so.customer = %(customer)s OR so.customer_name LIKE %(customer_pattern)s)")
        values["customer"] = customer
        values["customer_pattern"] = f"%{customer}%"

    if from_date:
        conditions.append("so.transaction_date >= %(from_date)s")
        values["from_date"] = from_date

    if to_date:
        conditions.append("so.transaction_date <= %(to_date)s")
        values["to_date"] = to_date

    where_clause = " AND ".join(conditions)

    # 1. Fetch filtered Sales Orders
    sales_orders = frappe.db.sql(f"""
        SELECT
            so.name AS sales_order,
            so.customer,
            so.customer_name,
            so.transaction_date AS so_date,
            so.branch,
            so.creation AS so_creation,
            (
                SELECT sc.modification_time
                FROM `tabState Change Items` sc
                WHERE sc.parent = so.name
                  AND sc.parenttype = 'Sales Order'
                  AND sc.workflow_state = 'Approved'
                ORDER BY sc.modification_time DESC
                LIMIT 1
            ) AS so_approved_date
        FROM `tabSales Order` so
        WHERE {where_clause}
        ORDER BY so.transaction_date DESC, so.creation DESC
    """, values, as_dict=True)

    if not sales_orders:
        return _build_empty_response()

    so_names = [so.sales_order for so in sales_orders]
    so_tuple = tuple(so_names)

    # 2. Batch fetch downstream documents for the filtered Sales Orders
    # 2a. Last BOM Created (any docstatus)
    bom_created_map = {}
    bom_created_rows = frappe.db.sql("""
        SELECT sales_order, name, creation
        FROM `tabBOM`
        WHERE sales_order IN %(so_tuple)s
        ORDER BY creation DESC
    """, {"so_tuple": so_tuple}, as_dict=True)
    for b in bom_created_rows:
        if b.sales_order not in bom_created_map:
            bom_created_map[b.sales_order] = b

    # 2b. Last BOM Submitted (docstatus = 1)
    bom_sub_map = {}
    bom_sub_rows = frappe.db.sql("""
        SELECT sales_order, name, modified
        FROM `tabBOM`
        WHERE sales_order IN %(so_tuple)s
          AND docstatus = 1
        ORDER BY modified DESC
    """, {"so_tuple": so_tuple}, as_dict=True)
    for b in bom_sub_rows:
        if b.sales_order not in bom_sub_map:
            bom_sub_map[b.sales_order] = b

    # 2c. Last Purchase Order Submitted (docstatus = 1)
    po_sub_map = {}
    po_sub_rows = frappe.db.sql("""
        SELECT poi.sales_order, po.name, po.modified, po.transaction_date
        FROM `tabPurchase Order Item` poi
        JOIN `tabPurchase Order` po ON po.name = poi.parent
        WHERE poi.sales_order IN %(so_tuple)s
          AND po.docstatus = 1
        ORDER BY po.modified DESC
    """, {"so_tuple": so_tuple}, as_dict=True)
    for p in po_sub_rows:
        if p.sales_order not in po_sub_map:
            po_sub_map[p.sales_order] = p

    # 2d. Last Purchase Receipt Submitted (docstatus = 1)
    pr_sub_map = {}
    pr_sub_rows = frappe.db.sql("""
        SELECT
            COALESCE(NULLIF(pri.sales_order, ''), poi.sales_order) AS sales_order,
            pr.name,
            COALESCE(TIMESTAMP(pr.posting_date, pr.posting_time), pr.modified) AS max_date,
            pr.posting_date
        FROM `tabPurchase Receipt Item` pri
        JOIN `tabPurchase Receipt` pr ON pr.name = pri.parent
        LEFT JOIN `tabPurchase Order Item` poi ON poi.name = pri.purchase_order_item
        WHERE (pri.sales_order IN %(so_tuple)s OR poi.sales_order IN %(so_tuple)s)
          AND pr.docstatus = 1
        ORDER BY pr.posting_date DESC, pr.posting_time DESC, pr.modified DESC
    """, {"so_tuple": so_tuple}, as_dict=True)
    for pr in pr_sub_rows:
        if pr.sales_order and pr.sales_order not in pr_sub_map:
            pr_sub_map[pr.sales_order] = pr

    # 2e. Last Work Order Submitted (docstatus = 1)
    wo_sub_map = {}
    wo_sub_rows = frappe.db.sql("""
        SELECT sales_order, name, modified
        FROM `tabWork Order`
        WHERE sales_order IN %(so_tuple)s
          AND docstatus = 1
        ORDER BY modified DESC
    """, {"so_tuple": so_tuple}, as_dict=True)
    for wo in wo_sub_rows:
        if wo.sales_order not in wo_sub_map:
            wo_sub_map[wo.sales_order] = wo

    # 3. Assemble rows & calculate phase durations
    rows = []
    p1_durations, p2_durations, p3_durations, p4_durations, p5_durations, overall_durations = (
        [], [], [], [], [], []
    )

    for so in sales_orders:
        so_approved_dt = so.so_approved_date or so.so_creation

        bc = bom_created_map.get(so.sales_order)
        bs = bom_sub_map.get(so.sales_order)
        po = po_sub_map.get(so.sales_order)
        pr = pr_sub_map.get(so.sales_order)
        wo = wo_sub_map.get(so.sales_order)

        bc_dt = bc.creation if bc else None
        bs_dt = bs.modified if bs else None
        po_dt = po.modified if po else None
        pr_dt = pr.max_date if pr else None
        wo_dt = wo.modified if wo else None

        d1 = _calc_duration_days(so_approved_dt, bc_dt)
        d2 = _calc_duration_days(bc_dt, bs_dt)
        d3 = _calc_duration_days(bs_dt, po_dt)
        d4 = _calc_duration_days(po_dt, pr_dt)
        d5 = _calc_duration_days(pr_dt, wo_dt)
        d_overall = _calc_duration_days(so_approved_dt, wo_dt)

        if d1 is not None: p1_durations.append(d1)
        if d2 is not None: p2_durations.append(d2)
        if d3 is not None: p3_durations.append(d3)
        if d4 is not None: p4_durations.append(d4)
        if d5 is not None: p5_durations.append(d5)
        if d_overall is not None: overall_durations.append(d_overall)

        rows.append({
            "sales_order": so.sales_order,
            "customer": so.customer,
            "customer_name": so.customer_name or so.customer or "",
            "so_date": format_date(so.so_date, "dd-MMM-yyyy") if so.so_date else "",
            "so_date_raw": str(so.so_date or ""),
            "branch": so.branch or "",

            # Milestones
            "so_approval_date": format_date(so_approved_dt, "dd-MMM-yyyy") if so_approved_dt else "",
            "so_approval_date_raw": str(so_approved_dt or ""),

            "last_bom_created_name": bc.name if bc else None,
            "last_bom_created_date": format_date(bc_dt, "dd-MMM-yyyy") if bc_dt else "",
            "last_bom_created_date_raw": str(bc_dt or ""),

            "last_bom_submitted_name": bs.name if bs else None,
            "last_bom_submitted_date": format_date(bs_dt, "dd-MMM-yyyy") if bs_dt else "",
            "last_bom_submitted_date_raw": str(bs_dt or ""),

            "last_po_submitted_name": po.name if po else None,
            "last_po_submitted_date": format_date(po_dt, "dd-MMM-yyyy") if po_dt else "",
            "last_po_submitted_date_raw": str(po_dt or ""),

            "last_pr_submitted_name": pr.name if pr else None,
            "last_pr_submitted_date": format_date(pr_dt, "dd-MMM-yyyy") if pr_dt else "",
            "last_pr_submitted_date_raw": str(pr_dt or ""),

            "last_wo_submitted_name": wo.name if wo else None,
            "last_wo_submitted_date": format_date(wo_dt, "dd-MMM-yyyy") if wo_dt else "",
            "last_wo_submitted_date_raw": str(wo_dt or ""),

            # Phase Durations
            "dur_so_to_bom_created": d1,
            "dur_bom_created_to_submitted": d2,
            "dur_bom_to_po_submitted": d3,
            "dur_po_to_pr_submitted": d4,
            "dur_pr_to_wo_submitted": d5,
            "dur_overall": d_overall,
        })

    # 4. Summary Number Cards
    summary = {
        "total_orders": len(sales_orders),
        "cards": [
            {
                "id": "so_to_bom_created",
                "label": _("SO Approval → Last BOM Created"),
                "avg_days": _compute_avg(p1_durations),
                "count": len(p1_durations),
                "total": len(sales_orders),
                "unit": _("days average"),
            },
            {
                "id": "bom_created_to_submitted",
                "label": _("Last BOM Created → Last BOM Submitted"),
                "avg_days": _compute_avg(p2_durations),
                "count": len(p2_durations),
                "total": len(sales_orders),
                "unit": _("days average"),
            },
            {
                "id": "bom_to_po_submitted",
                "label": _("Last BOM Submitted → Last PO Submitted"),
                "avg_days": _compute_avg(p3_durations),
                "count": len(p3_durations),
                "total": len(sales_orders),
                "unit": _("days average"),
            },
            {
                "id": "po_to_pr_submitted",
                "label": _("Last PO Submitted → Last Purchase Receipt Submitted"),
                "avg_days": _compute_avg(p4_durations),
                "count": len(p4_durations),
                "total": len(sales_orders),
                "unit": _("days average"),
            },
            {
                "id": "pr_to_wo_submitted",
                "label": _("Last Purchase Receipt → Last Work Order Submitted"),
                "avg_days": _compute_avg(p5_durations),
                "count": len(p5_durations),
                "total": len(sales_orders),
                "unit": _("days average"),
            },
            {
                "id": "overall_duration",
                "label": _("Sales Order → Last Work Order Submitted"),
                "avg_days": _compute_avg(overall_durations),
                "count": len(overall_durations),
                "total": len(sales_orders),
                "unit": _("days average"),
                "delta": _("End-to-end cycle"),
            },
        ],
    }

    return {
        "summary": summary,
        "rows": rows,
    }


def _calc_duration_days(start_ts, end_ts):
    """Calculates elapsed days rounded to 1 decimal place. Returns None if either is missing."""
    if not start_ts or not end_ts:
        return None
    try:
        s = get_datetime(start_ts)
        e = get_datetime(end_ts)
        if not s or not e:
            return None
        diff_days = (e - s).total_seconds() / 86400.0
        return round(max(0.0, diff_days), 1)
    except Exception:
        return None


def _compute_avg(durations):
    """Averages only non-null values. Missing records are never treated as zero."""
    if not durations:
        return None
    return round(sum(durations) / len(durations), 1)


def _build_empty_response():
    cards = [
        {"id": "so_to_bom_created", "label": _("SO Approval → Last BOM Created"), "avg_days": None, "count": 0, "total": 0, "unit": _("days average")},
        {"id": "bom_created_to_submitted", "label": _("Last BOM Created → Last BOM Submitted"), "avg_days": None, "count": 0, "total": 0, "unit": _("days average")},
        {"id": "bom_to_po_submitted", "label": _("Last BOM Submitted → Last PO Submitted"), "avg_days": None, "count": 0, "total": 0, "unit": _("days average")},
        {"id": "po_to_pr_submitted", "label": _("Last PO Submitted → Last Purchase Receipt Submitted"), "avg_days": None, "count": 0, "total": 0, "unit": _("days average")},
        {"id": "pr_to_wo_submitted", "label": _("Last Purchase Receipt → Last Work Order Submitted"), "avg_days": None, "count": 0, "total": 0, "unit": _("days average")},
        {"id": "overall_duration", "label": _("Sales Order → Last Work Order Submitted"), "avg_days": None, "count": 0, "total": 0, "unit": _("days average"), "delta": _("End-to-end cycle")},
    ]
    return {
        "summary": {"total_orders": 0, "cards": cards},
        "rows": [],
    }
