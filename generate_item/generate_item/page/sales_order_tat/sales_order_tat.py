# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, format_date


@frappe.whitelist()
def get_dashboard_data(period=None, from_date=None, to_date=None, branch=None, sales_order=None, customer=None):
    """
    Returns Sales Order TAT Dashboard metrics and line items.
    Calculates elapsed duration in both weeks and days across exactly 6 stages:
      1. SO Creation → SO Approved
      2. SO Approval → Last BOM Submitted
      3. Last BOM Submitted → Last Material Request Created on
      4. Last Material Request Submitted → Last Purchase Order Created on
      5. Last PO Approved → Last PR Submitted on
      6. Sales Order Created on → Work Order Submitted
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
            so.delivery_date,
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

    # 2a. Last BOM Submitted (docstatus = 1)
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

    # 2b. Material Requests (docstatus != 2 for created, docstatus = 1 for submitted)
    mr_created_map = {}
    mr_sub_map = {}
    mr_rows = frappe.db.sql("""
        SELECT mri.sales_order, mr.name, mr.creation, mr.modified, mr.transaction_date, mr.docstatus
        FROM `tabMaterial Request Item` mri
        JOIN `tabMaterial Request` mr ON mr.name = mri.parent
        WHERE mri.sales_order IN %(so_tuple)s
          AND mr.docstatus != 2
        ORDER BY mr.creation DESC, mr.modified DESC
    """, {"so_tuple": so_tuple}, as_dict=True)
    for m in mr_rows:
        if m.sales_order not in mr_created_map:
            mr_created_map[m.sales_order] = m
        if m.docstatus == 1 and m.sales_order not in mr_sub_map:
            mr_sub_map[m.sales_order] = m

    # 2c. Purchase Orders (created, and approved via State Change Items)
    po_created_map = {}
    po_rows = frappe.db.sql("""
        SELECT 
            poi.sales_order, 
            po.name, 
            po.creation, 
            po.modified, 
            po.transaction_date, 
            po.docstatus
        FROM `tabPurchase Order Item` poi
        JOIN `tabPurchase Order` po ON po.name = poi.parent
        WHERE poi.sales_order IN %(so_tuple)s
          AND po.docstatus != 2
        ORDER BY po.creation DESC, po.modified DESC
    """, {"so_tuple": so_tuple}, as_dict=True)
    for p in po_rows:
        if p.sales_order not in po_created_map:
            po_created_map[p.sales_order] = p

    # 2c-ii. Latest PO Approved date for the Sales Orders
    po_app_map = {}
    po_app_rows = frappe.db.sql("""
        SELECT 
            poi.sales_order,
            sc.modification_time AS po_approved_date
        FROM `tabPurchase Order Item` poi
        JOIN `tabState Change Items` sc ON sc.parent = poi.parent
        WHERE poi.sales_order IN %(so_tuple)s
          AND sc.workflow_state = 'Approved'
        ORDER BY sc.modification_time DESC
    """, {"so_tuple": so_tuple}, as_dict=True)
    for p in po_app_rows:
        if p.sales_order not in po_app_map:
            po_app_map[p.sales_order] = p

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

    # 3. Assemble rows & calculate 6 stage durations in both weeks and days
    rows = []
    s1_weeks, s1_days = [], []
    s2_weeks, s2_days = [], []
    s3_weeks, s3_days = [], []
    s4_weeks, s4_days = [], []
    s5_weeks, s5_days = [], []
    s6_weeks, s6_days = [], []

    for so in sales_orders:
        so_cre_dt = so.so_creation
        so_approved_dt = so.so_approved_date
        so_delivery_dt = so.delivery_date

        bs = bom_sub_map.get(so.sales_order)
        bs_dt = bs.modified or bs.creation if bs else None

        mr_c = mr_created_map.get(so.sales_order)
        mr_c_dt = mr_c.creation if mr_c else None

        mr_s = mr_sub_map.get(so.sales_order)
        mr_s_dt = mr_s.modified or mr_s.transaction_date if mr_s else None

        po_c = po_created_map.get(so.sales_order)
        po_c_dt = po_c.creation if po_c else None

        po_a = po_app_map.get(so.sales_order)
        po_a_dt = po_a.po_approved_date if po_a else None

        pr = pr_sub_map.get(so.sales_order)
        pr_dt = pr.posting_date or pr.max_date if pr else None

        wo = wo_sub_map.get(so.sales_order)
        wo_dt = wo.modified or wo.creation if wo else None

        # Calculate 6 duration columns in weeks and days:
        # 1. SO Creation -> SO Approved
        dur_1, days_1 = _calc_durations(so_cre_dt, so_approved_dt)
        # 2. SO Approval -> Last BOM Submitted
        dur_2, days_2 = _calc_durations(so_approved_dt, bs_dt)
        # 3. Last BOM Submitted -> Last Material Request Created on
        dur_3, days_3 = _calc_durations(bs_dt, mr_c_dt)
        # 4. Last Material Request Submitted -> Last Purchase Order Created on
        dur_4, days_4 = _calc_durations(mr_s_dt, po_c_dt)
        # 5. Last PO Approved -> Last PR Submitted on
        dur_5, days_5 = _calc_durations(po_a_dt, pr_dt)
        # 6. Sales Order Created on -> Work Order Submitted
        dur_6, days_6 = _calc_durations(so_cre_dt, wo_dt)

        if dur_1 is not None:
            s1_weeks.append(dur_1)
            s1_days.append(days_1)
        if dur_2 is not None:
            s2_weeks.append(dur_2)
            s2_days.append(days_2)
        if dur_3 is not None:
            s3_weeks.append(dur_3)
            s3_days.append(days_3)
        if dur_4 is not None:
            s4_weeks.append(dur_4)
            s4_days.append(days_4)
        if dur_5 is not None:
            s5_weeks.append(dur_5)
            s5_days.append(days_5)
        if dur_6 is not None:
            s6_weeks.append(dur_6)
            s6_days.append(days_6)

        rows.append({
            "sales_order": so.sales_order,
            "customer": so.customer,
            "customer_name": so.customer_name or so.customer or "",
            "so_date": format_date(so.so_date, "dd-MMM-yyyy") if so.so_date else "",
            "so_date_raw": str(so.so_date or ""),
            "delivery_date": format_date(so_delivery_dt, "dd-MMM-yyyy") if so_delivery_dt else "",
            "delivery_date_raw": str(so_delivery_dt or ""),
            "branch": so.branch or "",
            "so_creation": format_date(so_cre_dt, "dd-MMM-yyyy") if so_cre_dt else "",
            "so_creation_raw": str(so_cre_dt or ""),

            # Milestone dates & document references
            "so_approval_date": format_date(so_approved_dt, "dd-MMM-yyyy") if so_approved_dt else "",
            "so_approval_date_raw": str(so_approved_dt or ""),

            "last_bom_submitted_name": bs.name if bs else None,
            "last_bom_submitted_date": format_date(bs_dt, "dd-MMM-yyyy") if bs_dt else "",
            "last_bom_submitted_date_raw": str(bs_dt or ""),

            "mr_created_name": mr_c.name if mr_c else None,
            "mr_created_date": format_date(mr_c_dt, "dd-MMM-yyyy") if mr_c_dt else "",
            "mr_created_date_raw": str(mr_c_dt or ""),

            "mr_submitted_name": mr_s.name if mr_s else None,
            "mr_submitted_date": format_date(mr_s_dt, "dd-MMM-yyyy") if mr_s_dt else "",
            "mr_submitted_date_raw": str(mr_s_dt or ""),

            "po_created_name": po_c.name if po_c else None,
            "po_created_date": format_date(po_c_dt, "dd-MMM-yyyy") if po_c_dt else "",
            "po_created_date_raw": str(po_c_dt or ""),

            "po_approved_date": format_date(po_a_dt, "dd-MMM-yyyy") if po_a_dt else "",
            "po_approved_date_raw": str(po_a_dt or ""),

            "last_pr_submitted_name": pr.name if pr else None,
            "last_pr_submitted_date": format_date(pr_dt, "dd-MMM-yyyy") if pr_dt else "",
            "last_pr_submitted_date_raw": str(pr_dt or ""),

            "last_wo_submitted_name": wo.name if wo else None,
            "last_wo_submitted_date": format_date(wo_dt, "dd-MMM-yyyy") if wo_dt else "",
            "last_wo_submitted_date_raw": str(wo_dt or ""),

            # Exactly 6 Phase Durations in Weeks and Days
            "dur_so_cre_to_so_app": dur_1,
            "days_so_cre_to_so_app": days_1,

            "dur_so_app_to_last_bom_sub": dur_2,
            "days_so_app_to_last_bom_sub": days_2,

            "dur_bom_sub_to_mr_cre": dur_3,
            "days_bom_sub_to_mr_cre": days_3,

            "dur_mr_sub_to_po_cre": dur_4,
            "days_mr_sub_to_po_cre": days_4,

            "dur_po_app_to_last_pur_sub": dur_5,
            "days_po_app_to_last_pur_sub": days_5,

            "dur_so_cre_to_wo_sub": dur_6,
            "days_so_cre_to_wo_sub": days_6,
        })

    # 4. Summary Number Cards (in both weeks and days)
    summary = {
        "total_orders": len(sales_orders),
        "cards": [
            {
                "id": "so_cre_to_so_app",
                "label": _("SO Creation → SO Approved"),
                "avg_weeks": _compute_avg(s1_weeks),
                "avg_days": _compute_avg(s1_days, 1),
                "count": len(s1_weeks),
                "total": len(sales_orders),
                "unit": _("Weeks avg"),
            },
            {
                "id": "so_app_to_last_bom_sub",
                "label": _("SO Approval → Last BOM Submitted"),
                "avg_weeks": _compute_avg(s2_weeks),
                "avg_days": _compute_avg(s2_days, 1),
                "count": len(s2_weeks),
                "total": len(sales_orders),
                "unit": _("Weeks avg"),
            },
            {
                "id": "bom_sub_to_mr_cre",
                "label": _("Last BOM Submitted → Last Material Request Created on"),
                "avg_weeks": _compute_avg(s3_weeks),
                "avg_days": _compute_avg(s3_days, 1),
                "count": len(s3_weeks),
                "total": len(sales_orders),
                "unit": _("Weeks avg"),
            },
            {
                "id": "mr_sub_to_po_cre",
                "label": _("Last Material Request Submitted → Last Purchase Order Created on"),
                "avg_weeks": _compute_avg(s4_weeks),
                "avg_days": _compute_avg(s4_days, 1),
                "count": len(s4_weeks),
                "total": len(sales_orders),
                "unit": _("Weeks avg"),
            },
            {
                "id": "po_app_to_last_pur_sub",
                "label": _("Last PO Approved → Last PR Submitted on"),
                "avg_weeks": _compute_avg(s5_weeks),
                "avg_days": _compute_avg(s5_days, 1),
                "count": len(s5_weeks),
                "total": len(sales_orders),
                "unit": _("Weeks avg"),
            },
            {
                "id": "so_cre_to_wo_sub",
                "label": _("Sales Order Created on → Work Order Submitted"),
                "avg_weeks": _compute_avg(s6_weeks),
                "avg_days": _compute_avg(s6_days, 1),
                "count": len(s6_weeks),
                "total": len(sales_orders),
                "unit": _("Weeks avg"),
            },
        ],
    }

    return {
        "summary": summary,
        "rows": rows,
    }


def _calc_durations(start_ts, end_ts, allow_negative=False):
    """
    Calculates elapsed weeks rounded to 2 decimal places and exact days.
    Returns (None, None) if either date is missing.
    If allow_negative is False, returns (None, None) when end_date < start_date.
    """
    if not start_ts or not end_ts:
        return None, None
    try:
        s_date = getdate(start_ts)
        e_date = getdate(end_ts)
        if not s_date or not e_date:
            return None, None
        diff_days = (e_date - s_date).days
        if not allow_negative and diff_days < 0:
            return None, None
        return round(diff_days / 7.0, 2), diff_days
    except Exception:
        return None, None


def _compute_avg(values, decimals=2):
    """Averages only non-null values rounded to specified decimals. Missing records are never treated as zero."""
    if not values:
        return None
    return round(sum(values) / len(values), decimals)


def _build_empty_response():
    cards = [
        {"id": "so_cre_to_so_app", "label": _("SO Creation → SO Approved"), "avg_weeks": None, "avg_days": None, "count": 0, "total": 0, "unit": _("Weeks avg")},
        {"id": "so_app_to_last_bom_sub", "label": _("SO Approval → Last BOM Submitted"), "avg_weeks": None, "avg_days": None, "count": 0, "total": 0, "unit": _("Weeks avg")},
        {"id": "bom_sub_to_mr_cre", "label": _("Last BOM Submitted → Last Material Request Created on"), "avg_weeks": None, "avg_days": None, "count": 0, "total": 0, "unit": _("Weeks avg")},
        {"id": "mr_sub_to_po_cre", "label": _("Last Material Request Submitted → Last Purchase Order Created on"), "avg_weeks": None, "avg_days": None, "count": 0, "total": 0, "unit": _("Weeks avg")},
        {"id": "po_app_to_last_pur_sub", "label": _("Last PO Approved → Last PR Submitted on"), "avg_weeks": None, "avg_days": None, "count": 0, "total": 0, "unit": _("Weeks avg")},
        {"id": "so_cre_to_wo_sub", "label": _("Sales Order Created on → Work Order Submitted"), "avg_weeks": None, "avg_days": None, "count": 0, "total": 0, "unit": _("Weeks avg")},
    ]
    return {
        "summary": {"total_orders": 0, "cards": cards},
        "rows": [],
    }
