

import frappe
from frappe.utils import getdate, flt, today


@frappe.whitelist()
def get_dashboard_data(branch=None, from_date=None, to_date=None):
    """
    Main API for the Director Dashboard.
    from_date / to_date filter on transaction_date for MR and PO.
    Branch filter applied when provided.
    """
    data = {}
    data["pending_mr"] = get_pending_mr(branch, from_date, to_date)
    data["pending_po"] = get_pending_po(branch, from_date, to_date)


    data["pending_pr"] = get_pending_pr(branch, from_date, to_date)
    return data


# ─────────────────────────────────────────────────────────────────────────────
# HELPER: build day-age buckets from a list of rows
#
# rows     : list of dicts, each must have `date_field` and optionally `count`
# date_field: the field name to measure age from (e.g. "transaction_date")
# Buckets  : 0-7 | 8-14 | 15-21 | 22-28 | 28+
# ─────────────────────────────────────────────────────────────────────────────
def _build_buckets(rows, date_field="transaction_date"):
    buckets = {
        "0-7":   {"count": 0},
        "8-14":  {"count": 0},
        "15-21": {"count": 0},
        "22-28": {"count": 0},
       
    }

    today_date = getdate(today())

    for r in rows:
        dt = r.get(date_field)

        if not dt:
            continue

        age = (today_date - getdate(dt)).days
        if age < 0:
            age = 0  # future-dated docs treated as fresh

        if age <= 7:
            key = "0-7"
        elif age <= 14:
            key = "8-14"
        elif age <= 21:
            key = "15-21"
        elif age <= 28:
            key = "22-28"
        else:
            continue

        buckets[key]["count"] += 1

    return buckets


# ─────────────────────────────────────────────────────────────────────────────
# 1. Pending Material Requests
#

# Exclude : status IN ('Ordered', 'Cancelled')
# Age from: transaction_date
#
# from_date / to_date filter on transaction_date when provided.
# ─────────────────────────────────────────────────────────────────────────────
def get_pending_mr(branch=None, from_date=None, to_date=None):
    conditions = [
       
        "status NOT IN ('Ordered', 'Cancelled')"           # pending statuses
    ]
    params = {}

    if branch:
        conditions.append("branch = %(branch)s")
        params["branch"] = branch

    if from_date and to_date:
        conditions.append(
            "transaction_date BETWEEN %(from_date)s AND %(to_date)s"
        )
        params["from_date"] = from_date
        params["to_date"]   = to_date

    where = " AND ".join(conditions)

    rows = frappe.db.sql(f"""
        SELECT name, transaction_date, status
        FROM   `tabMaterial Request`
        WHERE  {where}
    """, params, as_dict=True)

    return _build_buckets(rows, date_field="transaction_date")


# ─────────────────────────────────────────────────────────────────────────────
# 2. Pending Purchase Orders
#

# Exclude : status IN ('To Receive and Bill', 'Cancelled')
#           – 'To Receive and Bill' = fully placed, awaiting receipt (done)
#           – 'Cancelled'           = voided
# Age from: transaction_date
#
# from_date / to_date filter on transaction_date when provided.
# ─────────────────────────────────────────────────────────────────────────────
def get_pending_po(branch=None, from_date=None, to_date=None):
    conditions = [
        "status NOT IN ('To Receive and Bill', 'Cancelled')"
    ]
    params = {}

    if branch:
        conditions.append("branch = %(branch)s")
        params["branch"] = branch

    if from_date and to_date:
        conditions.append(
            "transaction_date BETWEEN %(from_date)s AND %(to_date)s"
        )
        params["from_date"] = from_date
        params["to_date"]   = to_date

    where = " AND ".join(conditions)

    rows = frappe.db.sql(f"""
        SELECT name, transaction_date, status
        FROM   `tabPurchase Order`
        WHERE  {where}
    """, params, as_dict=True)

    return _build_buckets(rows, date_field="transaction_date")



def get_pending_pr(branch=None, from_date=None, to_date=None):
    conditions = [
        "status NOT IN ('To Bill','Completed', 'Cancelled')"
    ]
    params = {}

    if branch:
        conditions.append("branch = %(branch)s")
        params["branch"] = branch

    if from_date and to_date:
        conditions.append(
            "posting_date BETWEEN %(from_date)s AND %(to_date)s"
        )
        params["from_date"] = from_date
        params["to_date"]   = to_date

    where = " AND ".join(conditions)

    rows = frappe.db.sql(f"""
        SELECT name, posting_date, status
        FROM   `tabPurchase Receipt`
        WHERE  {where}
    """, params, as_dict=True)

    return _build_buckets(rows, date_field="posting_date")