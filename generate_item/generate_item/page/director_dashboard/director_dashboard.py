import frappe
from frappe.utils import getdate, today


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# Verified against live documents:
#   MR  : tabMaterial Request       / tabMaterial Request Item
#   PO  : tabPurchase Order         / tabPurchase Order Item
#   PR  : tabPurchase Receipt       / tabPurchase Receipt Item
# ─────────────────────────────────────────────────────────────────────────────

BUCKET_KEYS = ("0-7", "8-14", "15-21", "22-28", "28+")

# MR  – status NOT IN (verified: "Draft","Pending","Partially Ordered" are pending)
MR_EXCLUDED_STATUSES = ("Ordered", "Received", "Stopped", "Cancelled")

# PO  – status NOT IN
PO_EXCLUDED_STATUSES = ("Completed", "Closed", "To Bill", "Cancelled")

# PR  – status NOT IN
PR_EXCLUDED_STATUSES = ("To Bill", "Completed", "Cancelled")


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_dashboard_data(branch=None, from_date=None, to_date=None):
    """Doc-wise pending counts bucketed by age."""
    return {
        "pending_mr": _get_pending_mr_doc(branch, from_date, to_date),
        "pending_po": _get_pending_po_doc(branch, from_date, to_date),
        "pending_pr": _get_pending_pr_doc(branch, from_date, to_date),
    }


@frappe.whitelist()
def get_item_wise_data(branch=None, from_date=None, to_date=None):
    """Line-wise pending counts bucketed by age (only truly outstanding lines)."""
    return {
        "pending_mr": _get_pending_mr_line(branch, from_date, to_date),
        "pending_po": _get_pending_po_line(branch, from_date, to_date),
        "pending_pr": _get_pending_pr_line(branch, from_date, to_date),
    }


# ─────────────────────────────────────────────────────────────────────────────
# BUCKET BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def _empty_buckets():
    return {k: {"count": 0} for k in BUCKET_KEYS}


def _build_buckets(rows, date_field):
    """
    Assign each row to an age bucket: (today – date_field).days
    Buckets: 0-7 | 8-14 | 15-21 | 22-28 | 28+
    """
    buckets    = _empty_buckets()
    today_date = getdate(today())

    for row in rows:
        raw = row.get(date_field)
        if not raw:
            continue

        age = max((today_date - getdate(raw)).days, 0)

        if   age <= 7:   key = "0-7"
        elif age <= 14:  key = "8-14"
        elif age <= 21:  key = "15-21"
        elif age <= 28:  key = "22-28"
        else:            key = "28+"

        buckets[key]["count"] += 1

    return buckets


# ─────────────────────────────────────────────────────────────────────────────
# SQL HELPERS  (all values passed as params – SQL-injection safe)
# ─────────────────────────────────────────────────────────────────────────────

def _in_clause(values):
    """Return (%s, %s, ...) placeholder string and a list copy."""
    return "({})".format(", ".join(["%s"] * len(values))), list(values)


def _build_where(clauses_params):
    """
    clauses_params: list of (sql_fragment_str, [param, ...])
    Empty sql_fragment strings are skipped.
    Returns (where_sql, flat_params_list).
    """
    parts, params = [], []
    for sql, p in clauses_params:
        if sql:
            parts.append(sql)
            params.extend(p)
    return " AND ".join(parts), params


def _branch_clause(col_alias, branch):
    col = f"{col_alias}.branch" if col_alias else "branch"
    return (f"{col} = %s", [branch]) if branch else ("", [])


def _date_range_clause(col_alias, col_name, from_date, to_date):
    if from_date and to_date:
        col = f"{col_alias}.{col_name}" if col_alias else col_name
        return f"{col} BETWEEN %s AND %s", [from_date, to_date]
    return "", []


# ─────────────────────────────────────────────────────────────────────────────
# MATERIAL REQUEST – DOC WISE
#
# Table  : tabMaterial Request
# Filter : material_request_type = 'Purchase'
#          status NOT IN MR_EXCLUDED_STATUSES
# Age    : transaction_date  
# ─────────────────────────────────────────────────────────────────────────────

def _get_pending_mr_doc(branch=None, from_date=None, to_date=None):
    ph, exc = _in_clause(MR_EXCLUDED_STATUSES)
    br_sql, br_p   = _branch_clause("", branch)
    dt_sql, dt_p   = _date_range_clause("", "transaction_date", from_date, to_date)

    where, params = _build_where([
        (f"status NOT IN {ph}",       exc),
        ("material_request_type = %s", ["Purchase"]),
        (br_sql,                       br_p),
        (dt_sql,                       dt_p),
    ])

    rows = frappe.db.sql(
        f"""
        SELECT transaction_date
        FROM   `tabMaterial Request`
        WHERE  {where}
        """,
        params, as_dict=True,
    )
    return _build_buckets(rows, "transaction_date")


# ─────────────────────────────────────────────────────────────────────────────
# MATERIAL REQUEST – LINE WISE
#
# Tables  : tabMaterial Request Item  (mri)
#           tabMaterial Request       (mr)
# Filter  : mr.material_request_type = 'Purchase'
#           mr.status NOT IN MR_EXCLUDED_STATUSES
#           Pending qty > 0:
#             (mri.qty - IFNULL(mri.ordered_qty, 0)) > 0
#            
# Age     : mr.transaction_date
# ─────────────────────────────────────────────────────────────────────────────

def _get_pending_mr_line(branch=None, from_date=None, to_date=None):
    ph, exc = _in_clause(MR_EXCLUDED_STATUSES)
    br_sql, br_p = _branch_clause("mr", branch)
    dt_sql, dt_p = _date_range_clause("mr", "transaction_date", from_date, to_date)

    where, params = _build_where([
        (f"mr.status NOT IN {ph}",       exc),
        ("mr.material_request_type = %s", ["Purchase"]),
        (br_sql,                          br_p),
        (dt_sql,                          dt_p),
        # Only lines with outstanding qty (qty – ordered_qty > 0)
        # Fields verified: mri.qty, mri.ordered_qty (PMRN250100 item)
        ("(mri.qty - IFNULL(mri.ordered_qty, 0)) > 0", []),
    ])

    rows = frappe.db.sql(
        f"""
        SELECT mr.transaction_date
        FROM   `tabMaterial Request Item` mri
        INNER JOIN `tabMaterial Request` mr ON mr.name = mri.parent
        WHERE  {where}
        """,
        params, as_dict=True,
    )
    return _build_buckets(rows, "transaction_date")


# ─────────────────────────────────────────────────────────────────────────────
# PURCHASE ORDER – DOC WISE
#
# Table  : tabPurchase Order
# Filter : status NOT IN PO_EXCLUDED_STATUSES
# Age    : transaction_date  (verified in SD2502406: "2026-03-18")
# ─────────────────────────────────────────────────────────────────────────────

def _get_pending_po_doc(branch=None, from_date=None, to_date=None):
    ph, exc = _in_clause(PO_EXCLUDED_STATUSES)
    br_sql, br_p = _branch_clause("", branch)
    dt_sql, dt_p = _date_range_clause("", "transaction_date", from_date, to_date)

    where, params = _build_where([
        (f"status NOT IN {ph}", exc),
        (br_sql,                br_p),
        (dt_sql,                dt_p),
    ])

    rows = frappe.db.sql(
        f"""
        SELECT transaction_date
        FROM   `tabPurchase Order`
        WHERE  {where}
        """,
        params, as_dict=True,
    )
    return _build_buckets(rows, "transaction_date")


# ─────────────────────────────────────────────────────────────────────────────
# PURCHASE ORDER – LINE WISE
#
# Tables  : tabPurchase Order Item  (poi)
#           tabPurchase Order       (po)
# Filter  : po.status NOT IN PO_EXCLUDED_STATUSES
# ─────────────────────────────────────────────────────────────────────────────

def _get_pending_po_line(branch=None, from_date=None, to_date=None):
    ph, exc = _in_clause(PO_EXCLUDED_STATUSES)
    br_sql, br_p = _branch_clause("po", branch)
    # Date filter on schedule_date (Required By) for line-wise
    dt_sql, dt_p = _date_range_clause("poi", "schedule_date", from_date, to_date)

    where, params = _build_where([
        (f"po.status NOT IN {ph}", exc),
        (br_sql,                   br_p),
        (dt_sql,                   dt_p),
        # UOM-aware pending qty check
        # poi.received_qty_in_stock_uom is the correct field on PO Item (verified)
        (
            """
            CASE
                WHEN poi.uom != poi.stock_uom
                THEN (poi.stock_qty - IFNULL(poi.received_qty_in_stock_uom, 0))
                ELSE (poi.qty       - IFNULL(poi.received_qty, 0))
            END > 0
            """,
            [],
        ),
    ])

    rows = frappe.db.sql(
        f"""
        SELECT poi.schedule_date
        FROM   `tabPurchase Order Item` poi
        INNER JOIN `tabPurchase Order` po ON po.name = poi.parent
        WHERE  {where}
        """,
        params, as_dict=True,
    )
    # Age measured from schedule_date (Required By)
    return _build_buckets(rows, "schedule_date")


# ─────────────────────────────────────────────────────────────────────────────
# PURCHASE RECEIPT – DOC WISE
#
# Table  : tabPurchase Receipt
# Filter : status NOT IN PR_EXCLUDED_STATUSES

# ─────────────────────────────────────────────────────────────────────────────

def _get_pending_pr_doc(branch=None, from_date=None, to_date=None):
    ph, exc = _in_clause(PR_EXCLUDED_STATUSES)
    br_sql, br_p = _branch_clause("", branch)
    dt_sql, dt_p = _date_range_clause("", "posting_date", from_date, to_date)

    where, params = _build_where([
        (f"status NOT IN {ph}", exc),
        (br_sql,                br_p),
        (dt_sql,                dt_p),
    ])

    rows = frappe.db.sql(
        f"""
        SELECT posting_date
        FROM   `tabPurchase Receipt`
        WHERE  {where}
        """,
        params, as_dict=True,
    )
    return _build_buckets(rows, "posting_date")


# ─────────────────────────────────────────────────────────────────────────────
# PURCHASE RECEIPT – LINE WISE
#
# Tables  : tabPurchase Receipt Item  (pri)
#           tabPurchase Receipt       (pr)
# Filter  : pr.status NOT IN PR_EXCLUDED_STATUSES

def _get_pending_pr_line(branch=None, from_date=None, to_date=None):
    ph, exc = _in_clause(PR_EXCLUDED_STATUSES)
    br_sql, br_p = _branch_clause("pr", branch)
    dt_sql, dt_p = _date_range_clause("pr", "posting_date", from_date, to_date)

    where, params = _build_where([
        (f"pr.status NOT IN {ph}", exc),
        (br_sql,                   br_p),
        (dt_sql,                   dt_p),
    ])

    rows = frappe.db.sql(
        f"""
        SELECT pr.posting_date
        FROM   `tabPurchase Receipt Item` pri
        INNER JOIN `tabPurchase Receipt` pr ON pr.name = pri.parent
        WHERE  {where}
        """,
        params, as_dict=True,
    )
    return _build_buckets(rows, "posting_date")