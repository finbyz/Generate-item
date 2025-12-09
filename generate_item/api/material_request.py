import frappe
from typing import List

@frappe.whitelist()
def get_batches_linked_to_partly_delivered_sales_orders(branch=None, item_code=None):
    conditions = [
        "b.reference_doctype = 'Sales Order'",
        "so.docstatus = 1",
        "so.status IN ('Partly Delivered', 'To Deliver and Bill')"
    ]
    params = {}

    if branch:
        conditions.append("so.branch = %(branch)s")
        params["branch"] = branch

    if item_code:
        conditions.append("b.item = %(item_code)s")
        params["item_code"] = item_code

    where_clause = " AND ".join(conditions)

    query = f"""
        SELECT b.name
        FROM `tabBatch` b
        INNER JOIN `tabSales Order` so
            ON so.name = b.reference_name
        WHERE {where_clause}
        ORDER BY b.modified DESC
    """

    return [r.name for r in frappe.db.sql(query, params, as_dict=True)]

