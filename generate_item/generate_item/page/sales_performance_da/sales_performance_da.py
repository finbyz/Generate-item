
import frappe
from frappe.utils import getdate, add_days, flt, nowdate, today


@frappe.whitelist()
def get_dashboard_data(from_date, to_date, branch=None):
    """Main API to fetch all dashboard metrics"""
    data = {}

    data["orders_status"] = get_orders_status(from_date, to_date, branch)
    data["orders_delay"] = get_orders_delay(from_date, to_date, branch)
    data["order_booking"] = get_order_booking_value(branch)
    data["invoicing"] = get_invoicing_value(branch)
    data["outstanding_collection"] = get_outstanding_vs_collection(branch)
    data["bom_pending"] = get_bom_release_pending(branch)
    
    # OTD Pie Charts
    data["delivery_otd"] = get_delivery_otd(from_date, to_date, branch)
    data["order_entry_otd"] = get_order_entry_otd(from_date, to_date, branch)
    data["order_approval_otd"] = get_order_approval_otd(from_date, to_date, branch)

    return data


def get_fiscal_year_dates():
    """Get current fiscal year start and end dates"""
    try:
        fy = frappe.get_cached_doc('Fiscal Year', {'disabled': 0})
        return fy.year_start_date, fy.year_end_date
    except Exception:
        # Fallback to April-March fiscal year
        current_date = getdate(today())
        if current_date.month >= 4:
            fy_start = getdate(f"{current_date.year}-04-01")
            fy_end = getdate(f"{current_date.year + 1}-03-31")
        else:
            fy_start = getdate(f"{current_date.year - 1}-04-01")
            fy_end = getdate(f"{current_date.year}-03-31")
        return fy_start, fy_end


# --------------------------------------------------
# 1. Orders Pie – Booked / Approved / Draft
# Booked = docstatus=1, status NOT IN ('Closed', 'Cancelled')
# --------------------------------------------------
def get_orders_status(from_date, to_date, branch):
    conditions = [
        "so.docstatus < 2",
        "so.status NOT IN ('Closed', 'Cancelled')"
    ]

    if from_date and to_date:
        conditions.append("so.transaction_date BETWEEN %(from_date)s AND %(to_date)s")

    if branch:
        conditions.append("so.branch = %(branch)s")

    where = " AND ".join(conditions)

    result = frappe.db.sql(f"""
        SELECT
            CASE
                WHEN so.docstatus = 0 THEN 'Draft'
                WHEN so.workflow_state = 'Approved' THEN 'Approved'
                WHEN so.docstatus = 1 THEN 'Booked'
                ELSE COALESCE(so.workflow_state, 'Draft')
            END as status_group,
            COUNT(*) AS total_orders,
            SUM(so.grand_total) AS total_value
        FROM `tabSales Order` so
        WHERE {where}
        GROUP BY status_group
    """, {
        "from_date": from_date,
        "to_date": to_date,
        "branch": branch
    }, as_dict=True)

    output = {}
    for r in result:
        key = r.status_group or "Draft"
        output[key] = {
            "count": r.total_orders,
            "value": round((r.total_value or 0) / 100000, 2)
        }
    return output


# --------------------------------------------------
# 2. Orders Pie – Delayed / Not Delayed
# Delay in Booking: transaction_date - po_date > 3 days
# Delay in Approval: docstatus=1 and (submission took > 3 days)
# --------------------------------------------------
def get_orders_delay(from_date, to_date, branch):
    conditions = [
        "so.docstatus < 2",
        "so.status NOT IN ('Closed', 'Cancelled')"
    ]

    if from_date and to_date:
        conditions.append("so.transaction_date BETWEEN %(from_date)s AND %(to_date)s")

    if branch:
        conditions.append("so.branch = %(branch)s")

    where = " AND ".join(conditions)

    rows = frappe.db.sql(f"""
        SELECT
            so.name,
            so.transaction_date,
            so.po_date,
            so.docstatus,
            so.workflow_state,
            so.grand_total,
            so.creation,
            so.modified
        FROM `tabSales Order` so
        WHERE {where}
    """, {
        "from_date": from_date,
        "to_date": to_date,
        "branch": branch
    }, as_dict=True)

    delayed = {"count": 0, "value": 0}
    not_delayed = {"count": 0, "value": 0}

    for r in rows:
        is_delayed = False

        # Delay in Booking: SO creation date - Customer PO date > 3 days
        if r.po_date:
            delay_booking = (getdate(r.transaction_date) - getdate(r.po_date)).days
            if delay_booking > 3:
                is_delayed = True

        # Delay in Approval: For submitted orders, check if approval took > 3 days
        if r.docstatus == 1 and not is_delayed:
            delay_approval = (getdate(r.modified) - getdate(r.creation)).days
            if delay_approval > 3:
                is_delayed = True

        if is_delayed:
            delayed["count"] += 1
            delayed["value"] += flt(r.grand_total)
        else:
            not_delayed["count"] += 1
            not_delayed["value"] += flt(r.grand_total)

    return {
        "Delayed": to_lakh(delayed),
        "Not Delayed": to_lakh(not_delayed)
    }


# --------------------------------------------------
# 3. Order Booking Value (FY & Current Month)
# --------------------------------------------------
def get_order_booking_value(branch):
    conditions = [
        "docstatus = 1",
        "status NOT IN ('Closed', 'Cancelled')"
    ]

    if branch:
        conditions.append("branch = %(branch)s")

    where = " AND ".join(conditions)
    fy_start, fy_end = get_fiscal_year_dates()

    # FY value using date range
    fy_value = frappe.db.sql(f"""
        SELECT SUM(grand_total)
        FROM `tabSales Order`
        WHERE transaction_date BETWEEN %(fy_start)s AND %(fy_end)s
        AND {where}
    """, {"branch": branch, "fy_start": fy_start, "fy_end": fy_end})[0][0] or 0

    # Current month value
    month_value = frappe.db.sql(f"""
        SELECT SUM(grand_total)
        FROM `tabSales Order`
        WHERE MONTH(transaction_date) = MONTH(CURDATE())
        AND YEAR(transaction_date) = YEAR(CURDATE())
        AND {where}
    """, {"branch": branch})[0][0] or 0

    return {
        "FY": round(fy_value / 100000, 2),
        "Current Month": round(month_value / 100000, 2)
    }


# --------------------------------------------------
# 4. Invoicing – FY & Current Month
# --------------------------------------------------
def get_invoicing_value(branch):
    conditions = ["docstatus = 1"]

    if branch:
        conditions.append("branch = %(branch)s")

    where = " AND ".join(conditions)
    fy_start, fy_end = get_fiscal_year_dates()

    # FY value using date range
    fy = frappe.db.sql(f"""
        SELECT SUM(grand_total)
        FROM `tabSales Invoice`
        WHERE posting_date BETWEEN %(fy_start)s AND %(fy_end)s
        AND {where}
    """, {"branch": branch, "fy_start": fy_start, "fy_end": fy_end})[0][0] or 0

    # Current month
    month = frappe.db.sql(f"""
        SELECT SUM(grand_total)
        FROM `tabSales Invoice`
        WHERE MONTH(posting_date) = MONTH(CURDATE())
        AND YEAR(posting_date) = YEAR(CURDATE())
        AND {where}
    """, {"branch": branch})[0][0] or 0

    return {
        "FY": round(fy / 100000, 2),
        "Current Month": round(month / 100000, 2)
    }


# --------------------------------------------------
# 5. Outstanding Vs Collection (Current Month)
# --------------------------------------------------
def get_outstanding_vs_collection(branch):
    # Outstanding from Sales Invoices this month
    si_conditions = ["docstatus = 1"]
    if branch:
        si_conditions.append("branch = %(branch)s")
    si_where = " AND ".join(si_conditions)

    outstanding = frappe.db.sql(f"""
        SELECT SUM(outstanding_amount)
        FROM `tabSales Invoice`
        WHERE MONTH(posting_date) = MONTH(CURDATE())
        AND YEAR(posting_date) = YEAR(CURDATE())
        AND {si_where}
    """, {"branch": branch})[0][0] or 0

    # Collections from Payment Entries this month (with branch filter)
    pe_conditions = ["docstatus = 1", "payment_type = 'Receive'"]
    if branch:
        pe_conditions.append("branch = %(branch)s")
    pe_where = " AND ".join(pe_conditions)

    collected = frappe.db.sql(f"""
        SELECT SUM(paid_amount)
        FROM `tabPayment Entry`
        WHERE MONTH(posting_date) = MONTH(CURDATE())
        AND YEAR(posting_date) = YEAR(CURDATE())
        AND {pe_where}
    """, {"branch": branch})[0][0] or 0

    return {
        "Outstanding": round(outstanding / 100000, 2),
        "Collected": round(collected / 100000, 2)
    }


# --------------------------------------------------
# 6. BOM Release Pending > 2 weeks (Order Batch wise)
# Orders where BOM is not submitted within 2 weeks of SO creation
# --------------------------------------------------
def get_bom_release_pending(branch):
    conditions = [
        "so.docstatus = 1",
        "so.status NOT IN ('Closed', 'Cancelled')",
        "DATE(so.creation) <= DATE_SUB(CURDATE(), INTERVAL 14 DAY)"
    ]

    if branch:
        conditions.append("so.branch = %(branch)s")

    where = " AND ".join(conditions)

    # Find SO items where BOM is NULL or BOM is not submitted (docstatus != 1)
    rows = frappe.db.sql(f"""
        SELECT
            so.name AS sales_order,
            so.grand_total,
            so.creation,
            soi.custom_batch_no,
            soi.item_code,
            soi.amount,
            soi.bom_no,
            CASE
                WHEN soi.bom_no IS NULL OR soi.bom_no = '' THEN 'No BOM'
                WHEN bom.docstatus != 1 THEN 'BOM Not Submitted'
                ELSE 'BOM Ready'
            END as bom_status
        FROM `tabSales Order` so
        INNER JOIN `tabSales Order Item` soi ON soi.parent = so.name
        LEFT JOIN `tabBOM` bom ON bom.name = soi.bom_no
        WHERE {where}
        AND (soi.bom_no IS NULL OR soi.bom_no = '' OR bom.docstatus != 1)
    """, {"branch": branch}, as_dict=True)

    # Aggregate by batch
    batch_summary = {}
    total_count = 0
    total_value = 0

    for r in rows:
        batch = r.custom_batch_no or "No Batch"
        if batch not in batch_summary:
            batch_summary[batch] = {
                "sales_order": r.sales_order,
                "count": 0,
                "value": 0,
                "items": []
            }
        batch_summary[batch]["count"] += 1
        batch_summary[batch]["value"] += flt(r.amount)
        batch_summary[batch]["items"].append({
            "item_code": r.item_code,
            "bom_status": r.bom_status
        })
        total_count += 1
        total_value += flt(r.amount)

    return {
        "total": {
            "count": total_count,
            "value": round(total_value / 100000, 2)
        },
        "batches": [
            {
                "batch": batch,
                "sales_order": data["sales_order"],
                "count": data["count"],
                "value": round(data["value"] / 100000, 2)
            }
            for batch, data in batch_summary.items()
        ][:20]  # Limit to 20 batches
    }


# --------------------------------------------------
# 7. Delivery OTD - On Time vs Delayed Delivery
# Compares actual delivery date with scheduled delivery date
# On Time: Actual delivery date <= Scheduled delivery date
# Delayed: Actual delivery date > Scheduled delivery date
# --------------------------------------------------
def get_delivery_otd(from_date, to_date, branch):
    """
    Delivery OTD calculation:
    - If actual delivery date (DN posting_date) <= expected delivery date (SO delivery_date): On Time
    - If actual delivery date > expected delivery date: Delayed
    """
    conditions = [
        "dn.docstatus = 1",
        "dn.status NOT IN ('Cancelled', 'Closed')"
    ]
    
    if from_date and to_date:
        conditions.append("dn.posting_date BETWEEN %(from_date)s AND %(to_date)s")
    
    if branch:
        conditions.append("dn.branch = %(branch)s")
    
    where = " AND ".join(conditions)
    
    rows = frappe.db.sql(f"""
        SELECT
            dn.name,
            dn.posting_date as actual_delivery_date,
            dni.against_sales_order,
            so.delivery_date as scheduled_delivery_date,
            dni.amount
        FROM `tabDelivery Note` dn
        INNER JOIN `tabDelivery Note Item` dni ON dni.parent = dn.name
        LEFT JOIN `tabSales Order` so ON so.name = dni.against_sales_order
        WHERE {where}
        AND dni.against_sales_order IS NOT NULL
        AND so.delivery_date IS NOT NULL
    """, {
        "from_date": from_date,
        "to_date": to_date,
        "branch": branch
    }, as_dict=True)
    
    on_time = {"count": 0, "value": 0}
    delayed = {"count": 0, "value": 0}
    
    for r in rows:
        if r.actual_delivery_date and r.scheduled_delivery_date:
            if getdate(r.actual_delivery_date) <= getdate(r.scheduled_delivery_date):
                on_time["count"] += 1
                on_time["value"] += flt(r.amount)
            else:
                delayed["count"] += 1
                delayed["value"] += flt(r.amount)
    
    return {
        "On Time": to_lakh(on_time),
        "Delayed": to_lakh(delayed)
    }


# --------------------------------------------------
# 8. Order Entry OTD - On Time vs Delayed Entry
# Compares Party PO Date with SO Date
# On Time: SO Date - PO Date <= 3 days
# Delayed: SO Date - PO Date > 3 days
# --------------------------------------------------
def get_order_entry_otd(from_date, to_date, branch):
    """
    Order Entry OTD calculation:
    - If gap between SO transaction_date and PO date <= 3 days: On Time
    - If gap > 3 days: Order Entry Delayed
    """
    conditions = [
        "so.docstatus = 1",
        "so.status NOT IN ('Closed', 'Cancelled')",
        "so.po_date IS NOT NULL"
    ]
    
    if from_date and to_date:
        conditions.append("so.transaction_date BETWEEN %(from_date)s AND %(to_date)s")
    
    if branch:
        conditions.append("so.branch = %(branch)s")
    
    where = " AND ".join(conditions)
    
    rows = frappe.db.sql(f"""
        SELECT
            so.name,
            so.transaction_date,
            so.po_date,
            so.grand_total
        FROM `tabSales Order` so
        WHERE {where}
    """, {
        "from_date": from_date,
        "to_date": to_date,
        "branch": branch
    }, as_dict=True)
    
    on_time = {"count": 0, "value": 0}
    delayed = {"count": 0, "value": 0}
    
    for r in rows:
        if r.transaction_date and r.po_date:
            gap_days = (getdate(r.transaction_date) - getdate(r.po_date)).days
            if gap_days <= 3:
                on_time["count"] += 1
                on_time["value"] += flt(r.grand_total)
            else:
                delayed["count"] += 1
                delayed["value"] += flt(r.grand_total)
    
    return {
        "On Time": to_lakh(on_time),
        "Delayed": to_lakh(delayed)
    }


# --------------------------------------------------
# 9. Order Approval OTD - On Time vs Delayed Approval
# Compares SO Date with Approval Date
# On Time: Approval Date - SO Date <= 5 days
# Delayed: Approval Date - SO Date > 5 days
# --------------------------------------------------
def get_order_approval_otd(from_date, to_date, branch):
    """
    Order Approval OTD calculation:
    - If gap between approval date (modified date for approved/submitted) and SO date <= 5 days: On Time
    - If gap > 5 days: Approval Delayed
    """
    conditions = [
        "so.docstatus = 1",
        "so.status NOT IN ('Closed', 'Cancelled')"
    ]
    
    if from_date and to_date:
        conditions.append("so.transaction_date BETWEEN %(from_date)s AND %(to_date)s")
    
    if branch:
        conditions.append("so.branch = %(branch)s")
    
    where = " AND ".join(conditions)
    
    rows = frappe.db.sql(f"""
        SELECT
            so.name,
            so.transaction_date,
            so.modified as approval_date,
            so.grand_total,
            so.workflow_state
        FROM `tabSales Order` so
        WHERE {where}
    """, {
        "from_date": from_date,
        "to_date": to_date,
        "branch": branch
    }, as_dict=True)
    
    on_time = {"count": 0, "value": 0}
    delayed = {"count": 0, "value": 0}
    
    for r in rows:
        if r.transaction_date and r.approval_date:
            gap_days = (getdate(r.approval_date) - getdate(r.transaction_date)).days
            if gap_days <= 5:
                on_time["count"] += 1
                on_time["value"] += flt(r.grand_total)
            else:
                delayed["count"] += 1
                delayed["value"] += flt(r.grand_total)
    
    return {
        "On Time": to_lakh(on_time),
        "Delayed": to_lakh(delayed)
    }


# ---------------- HELPERS ----------------
def to_lakh(obj):
    return {
        "count": obj["count"],
        "value": round(obj["value"] / 100000, 2)
    }
