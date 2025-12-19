import frappe
from typing import List
import json

@frappe.whitelist()
def get_batches_linked_to_partly_delivered_sales_orders(doctype, txt, searchfield, start, page_len, filters):

    # filters may be a JSON string → convert it safely
    if isinstance(filters, str):
        try:
            filters = json.loads(filters)
        except:
            filters = {}

    branch = filters.get("branch")
    item_code = filters.get("item_code")

    conditions = [
        "b.reference_doctype = 'Sales Order'",
        "so.docstatus = 1",
        "so.status NOT IN ('Completed', 'Cancelled')"
    ]
    params = {}

    if branch:
        conditions.append("so.branch = %(branch)s")
        params["branch"] = branch

    if item_code:
        conditions.append("b.item = %(item_code)s")
        params["item_code"] = item_code

    if txt:
        conditions.append("b.name LIKE %(txt)s")
        params["txt"] = f"%{txt}%"

    where_clause = " AND ".join(conditions)

    query = f"""
        SELECT b.name
        FROM `tabBatch` b
        INNER JOIN `tabSales Order` so
            ON so.name = b.reference_name
        WHERE {where_clause}
        ORDER BY b.modified DESC
        LIMIT {start}, {page_len}
    """

    rows = frappe.db.sql(query, params, as_dict=True)

    # Must return list of tuples → NOT list of dicts
    return [(r.name, r.name) for r in rows]