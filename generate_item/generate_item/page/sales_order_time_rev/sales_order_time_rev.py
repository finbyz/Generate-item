# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, get_datetime, format_date, flt


@frappe.whitelist()
def get_dashboard_data(period=None, from_date=None, to_date=None, branch=None, sales_order=None, customer=None):
    """
    Returns Sales Order Phase Time Dashboard metrics and line items.
    Calculates elapsed duration in weeks between key manufacturing/procurement milestones:
      Duration 1: SO Creation -> SO Approval
      Duration 2: SO Approval -> Last BOM Created
      Duration 3: Last BOM Created -> Last BOM Submitted
      Duration 4: Last BOM Submitted -> Last PO Submitted
      Duration 5: Last PO Submitted -> Last PR Submitted
      Duration 6: Last PR Submitted -> Last WO Submitted
      Duration 7: SO Creation -> Last WO Submitted
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
    # 2a. Last BOM Created (valid non-cancelled BOMs, docstatus != 2)
    bom_created_map = {}
    bom_created_rows = frappe.db.sql("""
        SELECT sales_order, name, creation
        FROM `tabBOM`
        WHERE sales_order IN %(so_tuple)s
          AND docstatus != 2
        ORDER BY creation DESC
    """, {"so_tuple": so_tuple}, as_dict=True)
    for b in bom_created_rows:
        if b.sales_order not in bom_created_map:
            bom_created_map[b.sales_order] = b

    # 2b. Last BOM Submitted (docstatus = 1)
    bom_sub_map = {}
    bom_sub_rows = frappe.db.sql("""
        SELECT sales_order, name, modified, creation
        FROM `tabBOM`
        WHERE sales_order IN %(so_tuple)s
          AND docstatus = 1
        ORDER BY modified DESC, creation DESC
    """, {"so_tuple": so_tuple}, as_dict=True)
    for b in bom_sub_rows:
        if b.sales_order not in bom_sub_map:
            bom_sub_map[b.sales_order] = b

    # 2c. Last Purchase Order Submitted (docstatus = 1)
    po_sub_map = {}
    po_sub_rows = frappe.db.sql("""
        SELECT poi.sales_order, po.name, po.transaction_date, po.modified, po.creation
        FROM `tabPurchase Order Item` poi
        JOIN `tabPurchase Order` po ON po.name = poi.parent
        WHERE poi.sales_order IN %(so_tuple)s
          AND po.docstatus = 1
        ORDER BY po.transaction_date DESC, po.modified DESC
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
            pr.posting_date,
            pr.modified,
            COALESCE(TIMESTAMP(pr.posting_date, pr.posting_time), pr.modified) AS max_date
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
        SELECT sales_order, name, modified, creation
        FROM `tabWork Order`
        WHERE sales_order IN %(so_tuple)s
          AND docstatus = 1
        ORDER BY modified DESC, creation DESC
    """, {"so_tuple": so_tuple}, as_dict=True)
    for wo in wo_sub_rows:
        if wo.sales_order not in wo_sub_map:
            wo_sub_map[wo.sales_order] = wo

    # 3. Assemble rows & calculate milestone durations
    rows = []
    p1_weeks, p2_weeks, p3_weeks, p4_weeks, p5_weeks, overall_weeks = (
        [], [], [], [], [], []
    )

    for so in sales_orders:
        so_cre_dt = so.so_creation
        so_approved_dt = so.so_approved_date  # None if not approved, no fallback

        bc = bom_created_map.get(so.sales_order)
        bs = bom_sub_map.get(so.sales_order)
        po = po_sub_map.get(so.sales_order)
        pr = pr_sub_map.get(so.sales_order)
        wo = wo_sub_map.get(so.sales_order)

        bc_dt = bc.creation if bc else None
        bs_dt = bs.modified if bs else None
        po_dt = po.transaction_date or po.modified if po else None
        pr_dt = pr.posting_date or pr.max_date if pr else None
        wo_dt = wo.modified or wo.creation if wo else None

        # Calculate 7 duration columns in weeks: (End Date - Start Date).days / 7
        dur_1 = _calc_duration_weeks(so_cre_dt, so_approved_dt)
        dur_2 = _calc_duration_weeks(so_approved_dt, bc_dt)
        dur_3 = _calc_duration_weeks(bc_dt, bs_dt)
        dur_4 = _calc_duration_weeks(bs_dt, po_dt)
        dur_5 = _calc_duration_weeks(po_dt, pr_dt)
        dur_6 = _calc_duration_weeks(pr_dt, wo_dt)
        dur_7 = _calc_duration_weeks(so_cre_dt, wo_dt)

        if dur_2 is not None: p1_weeks.append(dur_2)
        if dur_3 is not None: p2_weeks.append(dur_3)
        if dur_4 is not None: p3_weeks.append(dur_4)
        if dur_5 is not None: p4_weeks.append(dur_5)
        if dur_6 is not None: p5_weeks.append(dur_6)
        if dur_7 is not None: overall_weeks.append(dur_7)

        rows.append({
            "sales_order": so.sales_order,
            "customer": so.customer,
            "customer_name": so.customer_name or so.customer or "",
            "so_date": format_date(so.so_date, "dd-MMM-yyyy") if so.so_date else "",
            "so_date_raw": str(so.so_date or ""),
            "branch": so.branch or "",
            "so_creation": format_date(so_cre_dt, "dd-MMM-yyyy") if so_cre_dt else "",
            "so_creation_raw": str(so_cre_dt or ""),

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

            # 7 Phase Durations in Weeks
            "dur_so_cre_to_so_app": dur_1,
            "dur_so_app_to_bom_cre": dur_2,
            "dur_bom_cre_to_bom_sub": dur_3,
            "dur_bom_sub_to_po_sub": dur_4,
            "dur_po_sub_to_pr_sub": dur_5,
            "dur_pr_sub_to_wo_sub": dur_6,
            "dur_so_cre_to_last_wo_sub": dur_7,

            # Backwards compatibility aliases
            "dur_so_to_bom_created": dur_2,
            "dur_bom_created_to_submitted": dur_3,
            "dur_bom_to_po_submitted": dur_4,
            "dur_po_to_pr_submitted": dur_5,
            "dur_pr_to_wo_submitted": dur_6,
            "dur_overall": dur_7,
        })

    # 4. Summary Number Cards (in weeks)
    summary = {
        "total_orders": len(sales_orders),
        "cards": [
            {
                "id": "so_to_bom_created",
                "label": _("SO Approval → Last BOM Created"),
                "avg_weeks": _compute_avg(p1_weeks),
                "avg_days": round(_compute_avg(p1_weeks) * 7.0, 1) if _compute_avg(p1_weeks) is not None else None,
                "count": len(p1_weeks),
                "total": len(sales_orders),
                "unit": _("weeks average"),
            },
            {
                "id": "bom_created_to_submitted",
                "label": _("Last BOM Created → Last BOM Submitted"),
                "avg_weeks": _compute_avg(p2_weeks),
                "avg_days": round(_compute_avg(p2_weeks) * 7.0, 1) if _compute_avg(p2_weeks) is not None else None,
                "count": len(p2_weeks),
                "total": len(sales_orders),
                "unit": _("weeks average"),
            },
            {
                "id": "bom_to_po_submitted",
                "label": _("Last BOM Submitted → Last PO Submitted"),
                "avg_weeks": _compute_avg(p3_weeks),
                "avg_days": round(_compute_avg(p3_weeks) * 7.0, 1) if _compute_avg(p3_weeks) is not None else None,
                "count": len(p3_weeks),
                "total": len(sales_orders),
                "unit": _("weeks average"),
            },
            {
                "id": "po_to_pr_submitted",
                "label": _("Last PO Submitted → Last Purchase Receipt Submitted"),
                "avg_weeks": _compute_avg(p4_weeks),
                "avg_days": round(_compute_avg(p4_weeks) * 7.0, 1) if _compute_avg(p4_weeks) is not None else None,
                "count": len(p4_weeks),
                "total": len(sales_orders),
                "unit": _("weeks average"),
            },
            {
                "id": "pr_to_wo_submitted",
                "label": _("Last Purchase Receipt → Last Work Order Submitted"),
                "avg_weeks": _compute_avg(p5_weeks),
                "avg_days": round(_compute_avg(p5_weeks) * 7.0, 1) if _compute_avg(p5_weeks) is not None else None,
                "count": len(p5_weeks),
                "total": len(sales_orders),
                "unit": _("weeks average"),
            },
            {
                "id": "overall_duration",
                "label": _("SO Creation → Last Work Order Submitted"),
                "avg_weeks": _compute_avg(overall_weeks),
                "avg_days": round(_compute_avg(overall_weeks) * 7.0, 1) if _compute_avg(overall_weeks) is not None else None,
                "count": len(overall_weeks),
                "total": len(sales_orders),
                "unit": _("weeks average"),
                "delta": _("End-to-end cycle"),
            },
        ],
    }

    return {
        "summary": summary,
        "rows": rows,
    }


def _calc_duration_weeks(start_ts, end_ts):
    """
    Calculates elapsed weeks rounded to 2 decimal places using date portions: (End Date - Start Date).days / 7.
    Returns None if either date is missing or if end_date < start_date.
    """
    if not start_ts or not end_ts:
        return None
    try:
        s_date = getdate(start_ts)
        e_date = getdate(end_ts)
        if not s_date or not e_date:
            return None
        diff_days = (e_date - s_date).days
        if diff_days < 0:
            return None
        return round(diff_days / 7.0, 2)
    except Exception:
        return None


def _compute_avg(durations):
    """Averages only non-null values rounded to 2 decimal places. Missing records are never treated as zero."""
    if not durations:
        return None
    return round(sum(durations) / len(durations), 2)


def _build_empty_response():
    cards = [
        {"id": "so_to_bom_created", "label": _("SO Approval → Last BOM Created"), "avg_weeks": None, "avg_days": None, "count": 0, "total": 0, "unit": _("weeks average")},
        {"id": "bom_created_to_submitted", "label": _("Last BOM Created → Last BOM Submitted"), "avg_weeks": None, "avg_days": None, "count": 0, "total": 0, "unit": _("weeks average")},
        {"id": "bom_to_po_submitted", "label": _("Last BOM Submitted → Last PO Submitted"), "avg_weeks": None, "avg_days": None, "count": 0, "total": 0, "unit": _("weeks average")},
        {"id": "po_to_pr_submitted", "label": _("Last PO Submitted → Last Purchase Receipt Submitted"), "avg_weeks": None, "avg_days": None, "count": 0, "total": 0, "unit": _("weeks average")},
        {"id": "pr_to_wo_submitted", "label": _("Last Purchase Receipt → Last Work Order Submitted"), "avg_weeks": None, "avg_days": None, "count": 0, "total": 0, "unit": _("weeks average")},
        {"id": "overall_duration", "label": _("SO Creation → Last Work Order Submitted"), "avg_weeks": None, "avg_days": None, "count": 0, "total": 0, "unit": _("weeks average"), "delta": _("End-to-end cycle")},
    ]
    return {
        "summary": {"total_orders": 0, "cards": cards},
        "rows": [],
    }
