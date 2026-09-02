from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import cint, getdate, nowdate, add_days, get_first_day, get_last_day
from datetime import datetime, timedelta

OMR_DOCTYPE = "Order Modification Request"
OMR_ITEM_DOCTYPE = "Sales Order Item For OMR"
SO_DOCTYPE = "Sales Order"

REV_TEXT_FIELDS = ("rev_item", "rev_description", "rev_line_status")
REV_NUMERIC_FIELDS = ("rev_qty", "rev_rate")
# Cache all rev_* fields once
REV_FIELDS = [
    df.fieldname
    for df in frappe.get_meta(OMR_ITEM_DOCTYPE).fields
    if df.fieldname.startswith("rev_")
]




# ---------------------------------------------------------------------------
# Helper: compute from_date / to_date from a preset label (server-side safety)
# ---------------------------------------------------------------------------
def _resolve_date_range(from_date=None, to_date=None):
    """
    If both from_date and to_date are given, use them directly.
    Otherwise fall back to today.
    Returns (from_date_str, to_date_str) as YYYY-MM-DD strings.
    """
    today = nowdate()
    if from_date and to_date:
        return str(from_date), str(to_date)
    return today, today


# ---------------------------------------------------------------------------
# Helper: build the date portion of a filters dict
# ---------------------------------------------------------------------------
def _date_filters(from_date, to_date):
    """Return a dict snippet that scopes OMR creation to [from_date, to_date]."""
    if from_date and to_date:
        return {"creation": ["between", [from_date, to_date + " 23:59:59"]]}
    return {}


# ---------------------------------------------------------------------------
# Helper: is a child row actually changed?
# ---------------------------------------------------------------------------
def _row_is_changed(row):
    """Return True if any rev_* field has a meaningful value."""
    return any(
        (
            value not in (None, "", 0, 0.0)
            and (not isinstance(value, str) or value.strip())
        )
        for field in REV_FIELDS
        for value in [row.get(field)]
    )


# ---------------------------------------------------------------------------
# Main whitelisted API
# ---------------------------------------------------------------------------
@frappe.whitelist()
def get_dashboard_data(branch=None, from_date=None, to_date=None):
    """
    Single API endpoint for the KPI dashboard.
    Accepts:
        branch    – exact branch name (e.g. "Sanand"), or empty/None for All
        from_date – YYYY-MM-DD string
        to_date   – YYYY-MM-DD string
    """
    from_date, to_date = _resolve_date_range(from_date, to_date)

    # Base filters always require docstatus=1
    base_filters = {"docstatus": 1}
    if branch:
        base_filters["branch"] = branch

    # Date-scoped filters (for functions that use frappe.db.get_all with creation filter)
    date_scoped_filters = dict(base_filters)
    date_scoped_filters.update(_date_filters(from_date, to_date))

    return {
        "branch_wise":       get_branch_wise_changes(date_scoped_filters),
        "order_change":      get_order_change_buckets(date_scoped_filters),
 
        "batch_change":      get_batch_change_count(date_scoped_filters),
        
        "top_creators_high": get_top_creators(date_scoped_filters, order="desc"),
        "top_creators_low":  get_top_creators(date_scoped_filters, order="asc"),
        "top_customers":     get_top_customers(date_scoped_filters),
        "batch_buckets":     get_batch_change_buckets(date_scoped_filters),
        "revision_rates":    get_revision_rates(date_scoped_filters, from_date, to_date),
        "trends":            get_30_day_trends(base_filters, from_date, to_date),
        "generated_at":      frappe.utils.now(),
        "active_filters":    {"branch": branch or "", "from_date": from_date, "to_date": to_date},
    }


# ---------------------------------------------------------------------------
# KPI functions
# ---------------------------------------------------------------------------

def get_branch_wise_changes(filters):
    """Count of submitted OMRs per branch within the active filter scope."""
    rows = frappe.db.get_all(
        OMR_DOCTYPE,
        filters=filters,
        fields=["branch", {"COUNT": "name", "as": "count"}],
        group_by="branch",
        order_by="count desc",
    )
    return [{"branch": r.branch or _("Not Set"), "count": r.count} for r in rows]

def get_order_change_buckets(filters):
    """
    Order Change buckets with branch-wise breakdown.
    Now includes total approved SO count for context.
    """
    # Get approved SOs first for the context count
    # Use BOTH docstatus AND workflow_state for proper approved filtering
    so_filters = {
        "docstatus": 1,
        "workflow_state": "Approved"  # Add workflow state filter
    }
    if filters.get("branch"):
        so_filters["branch"] = filters.get("branch")
    
    # Build SO filters properly for SQL query
    so_conditions = "so.docstatus = 1 AND so.workflow_state = 'Approved'"
    
    date_condition = ""
    so_params = []
    if "creation" in filters:
        from_date, to_date = filters["creation"][1]
        date_condition = "AND so.transaction_date BETWEEN %s AND %s"
        so_params = [from_date, to_date.split(" ")[0]]
    
    branch_condition = "AND so.branch = %s" if filters.get("branch") else ""
    params = []
    if filters.get("branch"):
        params.append(filters.get("branch"))
    
    approved_so_query = f"""
        SELECT COUNT(DISTINCT so.name) as count
        FROM `tabSales Order` so
        WHERE {so_conditions}
        {branch_condition}
        {date_condition}
    """
    
    all_params = params + so_params
    approved_so_count = frappe.db.sql(approved_so_query, all_params, as_dict=True)
    approved_so_count = approved_so_count[0].count if approved_so_count else 0

    # Also update the main filters to include workflow_state
    main_filters = filters.copy()
    main_filters["workflow_state"] = "Approved"  # Only count approved OMRs
    
    rows = frappe.db.get_all(
        OMR_DOCTYPE,
        filters=main_filters,  # Use updated filters
        fields=[
            "sales_order",
            "branch",
            {"COUNT": "name", "as": "count"},
        ],
        group_by="sales_order, branch",
    )

    buckets = {
        "1": {"total": 0, "branches": defaultdict(int)},
        "2": {"total": 0, "branches": defaultdict(int)},
        "3": {"total": 0, "branches": defaultdict(int)},
        "3+": {"total": 0, "branches": defaultdict(int)},
    }

    drill = {"1": [], "2": [], "3": [], "3+": []}

    for row in rows:
        cnt = cint(row.count)

        if cnt == 1:
            key = "1"
        elif cnt == 2:
            key = "2"
        elif cnt == 3:
            key = "3"
        else:
            key = "3+"

        buckets[key]["total"] += 1
        buckets[key]["branches"][row.branch or "Not Set"] += 1
        drill[key].append(row.sales_order)

    for key in buckets:
        buckets[key]["branches"] = dict(buckets[key]["branches"])

    buckets["_drill"] = drill
    buckets["approved_so_count"] = approved_so_count
    
    return buckets


def get_batch_change_buckets(filters):
    """
    Batch Change buckets with branch-wise breakdown.
    Now includes total line item count from approved SOs for context.
    """
    # Get approved SOs and their line items for the context count
    # Include workflow_state filter for proper approved status
    so_conditions = "so.docstatus = 1 AND so.workflow_state = 'Approved'"
    
    date_condition = ""
    so_params = []
    if "creation" in filters:
        from_date, to_date = filters["creation"][1]
        date_condition = "AND so.transaction_date BETWEEN %s AND %s"
        so_params = [from_date, to_date.split(" ")[0]]
    
    branch_condition = "AND so.branch = %s" if filters.get("branch") else ""
    params = []
    if filters.get("branch"):
        params.append(filters.get("branch"))
    
    # Get total line items from approved SOs
    line_item_query = f"""
        SELECT COUNT(soi.name) as count
        FROM `tabSales Order Item` soi
        JOIN `tabSales Order` so ON soi.parent = so.name
        WHERE {so_conditions}
        {branch_condition}
        {date_condition}
    """
    
    all_params = params + so_params
    total_line_items = frappe.db.sql(line_item_query, all_params, as_dict=True)
    total_line_items = total_line_items[0].count if total_line_items else 0

    # Add workflow_state filter for OMR documents
    main_filters = filters.copy()
    main_filters["workflow_state"] = "Approved"  # Only approved changes
    
    submitted = frappe.db.get_all(
        OMR_DOCTYPE,
        filters=main_filters,  # Use updated filters
        fields=["name", "branch"]
    )

    if not submitted:
        return {
            "1": {"total": 0, "branches": {}},
            "2": {"total": 0, "branches": {}},
            "3": {"total": 0, "branches": {}},
            "3+": {"total": 0, "branches": {}},
            "_drill": {"1": [], "2": [], "3": [], "3+": []},
            "total_line_items": total_line_items
        }

    branch_map = {
        d.name: d.branch or "Not Set"
        for d in submitted
    }

    item_rows = frappe.db.get_all(
        OMR_ITEM_DOCTYPE,
        filters={
            "parent": ["in", list(branch_map.keys())]
        },
        fields=["parent", "item", "batch_no"] + REV_FIELDS
    )

    batch_map = defaultdict(set)

    for row in item_rows:
        if row.batch_no and _row_is_changed(row):
            batch_map[(row.item, row.batch_no)].add(row.parent)

    buckets = {
        "1": {"total": 0, "branches": defaultdict(int)},
        "2": {"total": 0, "branches": defaultdict(int)},
        "3": {"total": 0, "branches": defaultdict(int)},
        "3+": {"total": 0, "branches": defaultdict(int)},
    }

    drill = {"1": [], "2": [], "3": [], "3+": []}

    for _, omrs in batch_map.items():
        count = len(omrs)

        if count == 1:
            key = "1"
        elif count == 2:
            key = "2"
        elif count == 3:
            key = "3"
        else:
            key = "3+"

        buckets[key]["total"] += 1
        first = list(omrs)[0]
        branch = branch_map.get(first, "Not Set")
        buckets[key]["branches"][branch] += 1
        drill[key].extend(list(omrs))

    for key in buckets:
        buckets[key]["branches"] = dict(buckets[key]["branches"])

    buckets["_drill"] = drill
    buckets["total_line_items"] = total_line_items
    
    return buckets

def get_batch_change_count(filters):
    submitted_omrs = frappe.db.get_all(
        OMR_DOCTYPE,
        filters=filters,
        pluck="name",
    )

    if not submitted_omrs:
        return {"total": 0}

    fields = ["parent", "item", "batch_no"] + REV_FIELDS

    item_rows = frappe.db.get_all(
        OMR_ITEM_DOCTYPE,
        filters={"parent": ["in", submitted_omrs]},
        fields=fields,
    )

    changed_batches = {
        (row.item, row.batch_no)
        for row in item_rows
        if row.batch_no and _row_is_changed(row)
    }

    return {"total": len(changed_batches)}



def get_top_creators(filters, order="desc", limit=10):
    """OMR count per creator (owner), sorted asc or desc."""
    rows = frappe.db.get_all(
        OMR_DOCTYPE,
        filters=filters,
        fields=["owner", {"COUNT": "name", "as": "count"}],
        group_by="owner",
        order_by="count {0}".format(order),
        limit_page_length=limit,
    )

    owners = [r.owner for r in rows]
    user_info = {}
    if owners:
        for u in frappe.db.get_all(
            "User",
            filters={"name": ["in", owners]},
            fields=["name", "full_name"],
        ):
            user_info[u.name] = u.full_name

    result = []
    for r in rows:
        full_name = user_info.get(r.owner) or r.owner
        result.append({"owner": r.owner, "full_name": full_name, "count": r.count})
    return result


def get_top_customers(filters, limit=10):
    branch_clause = ""
    params = []
    if filters.get("branch"):
        branch_clause = "AND omr.branch = %s"
        params.append(filters.get("branch"))
        
    date_clause = ""
    if "creation" in filters:
        date_clause = "AND omr.creation BETWEEN %s AND %s"
        params.extend(filters["creation"][1])
        
    query = f"""
        SELECT 
            so.customer,
            so.customer_name,
            COUNT(omr.name) as count
        FROM `tabOrder Modification Request` omr
        JOIN `tabSales Order` so ON omr.sales_order = so.name
        WHERE omr.docstatus = 1
        {branch_clause}
        {date_clause}
        GROUP BY so.customer
        ORDER BY count DESC
        LIMIT {limit}
    """
    
    rows = frappe.db.sql(query, params, as_dict=True)
    return rows


def get_revision_rates(filters, from_date, to_date):
    omrs = frappe.db.get_all(OMR_DOCTYPE, filters=filters, fields=["name", "sales_order"])
    
    so_names = list(set(o.sales_order for o in omrs if o.sales_order))
    omr_names = [o.name for o in omrs]
    
    date_clause = ""
    if from_date and to_date:
        date_clause = f"so.transaction_date BETWEEN '{from_date}' AND '{to_date}'"
        
    so_condition = "1=1"
    if date_clause:
        if so_names:
            so_names_str = ", ".join(frappe.db.escape(name) for name in so_names)
            so_condition = f"({date_clause} OR so.name IN ({so_names_str}))"
        else:
            so_condition = date_clause
            
    total_sos = frappe.db.sql(f"""
        SELECT COUNT(so.name)
        FROM `tabSales Order` so
        WHERE so.docstatus = 1 AND {so_condition}
    """)[0][0]
    
    total_items = frappe.db.sql(f"""
        SELECT COUNT(soi.name) 
        FROM `tabSales Order Item` soi
        JOIN `tabSales Order` so ON soi.parent = so.name
        WHERE so.docstatus = 1 AND {so_condition}
    """)[0][0]

    if not omrs:
        return {
            "order_rate": 0, "total_sos": total_sos, "revised_sos": 0,
            "item_rate": 0, "total_items": total_items, "changed_items": 0
        }
        
    # Item wise
    item_rows = frappe.db.get_all(
        OMR_ITEM_DOCTYPE,
        filters={"parent": ["in", omr_names]},
        fields=REV_FIELDS
    )
    changed_items = sum(1 for row in item_rows if _row_is_changed(row))
    item_rate = (changed_items / total_items * 100) if total_items > 0 else 0
    
    # Order wise
    revised_sos = len(so_names)
    
    order_rate = (revised_sos / total_sos * 100) if total_sos > 0 else 0
    
    return {
        "order_rate": round(order_rate, 1),
        "total_sos": total_sos,
        "revised_sos": revised_sos,
        "item_rate": round(item_rate, 1),
        "total_items": total_items,
        "changed_items": changed_items
    }


def get_30_day_trends(base_filters, from_date=None, to_date=None):
    """
    Daily OMR counts for the active date window.
    If from_date == to_date (e.g., Today filter), show the 30-day window
    ending today so the sparkline is always meaningful.
    """
    end_dt   = frappe.utils.now_datetime()
    start_dt = end_dt - timedelta(days=30)

    # Use the provided date range if it spans more than 1 day
    if from_date and to_date and from_date != to_date:
        from datetime import datetime as dt
        start_dt = dt.strptime(from_date, "%Y-%m-%d")
        end_dt   = dt.strptime(to_date,   "%Y-%m-%d") + timedelta(hours=23, minutes=59, seconds=59)

    branch_clause = ""
    params = [start_dt, end_dt]
    branch_val = base_filters.get("branch")
    if branch_val:
        branch_clause = "AND branch = %s"
        params.append(branch_val)

    daily_counts = frappe.db.sql("""
        SELECT
            DATE(creation) AS date,
            COUNT(*) AS count
        FROM `tabOrder Modification Request`
        WHERE docstatus = 1
            AND creation BETWEEN %s AND %s
            {branch_clause}
        GROUP BY DATE(creation)
        ORDER BY date ASC
    """.format(branch_clause=branch_clause), params, as_dict=True)

    date_map = {d.date.strftime("%Y-%m-%d"): d.count for d in daily_counts}
    trends = []

    current = start_dt
    while current.date() <= end_dt.date():
        date_str = current.strftime("%Y-%m-%d")
        trends.append({
            "date":  date_str,
            "count": date_map.get(date_str, 0),
            "label": current.strftime("%d %b"),
        })
        current += timedelta(days=1)

    # Trend direction
    if len(trends) >= 2:
        mid = len(trends) // 2
        first_half  = sum(t["count"] for t in trends[:mid])
        second_half = sum(t["count"] for t in trends[mid:])
        if first_half > 0:
            change_pct = ((second_half - first_half) / first_half) * 100
        else:
            change_pct = 0 if second_half == 0 else 100

        if change_pct < -10:
            trend_direction, trend_emoji = "down", "📉"
        elif change_pct > 10:
            trend_direction, trend_emoji = "up", "📈"
        else:
            trend_direction, trend_emoji = "stable", "📊"
    else:
        change_pct, trend_direction, trend_emoji = 0, "stable", "📊"

    return {
        "daily_data":        trends,
        "trend_direction":   trend_direction,
        "trend_emoji":       trend_emoji,
        "change_percentage": round(change_pct, 1),
        "total_this_month":  sum(t["count"] for t in trends),
    }