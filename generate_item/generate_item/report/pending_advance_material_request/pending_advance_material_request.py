import frappe
from frappe import _


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)

    return columns, data


def get_columns():
    return [
        {
            "label": "#",
            "fieldname": "idx",
            "fieldtype": "Int",
            "width": 50,
        },
        {
            "label": _("Material Request"),
            "fieldname": "material_request",
            "fieldtype": "Link",
            "options": "Material Request",
            "width": 180,
        },
        {
            "label": _("Date"),
            "fieldname": "transaction_date",
            "fieldtype": "Date",
            "width": 100,
        },
        {
            "label": _("Company"),
            "fieldname": "company",
            "fieldtype": "Link",
            "options": "Company",
            "width": 170,
        },
        {
            "label": _("Item"),
            "fieldname": "item_code",
            "fieldtype": "Link",
            "options": "Item",
            "width": 160,
        },
        {
            "label": _("Item Name"),
            "fieldname": "item_name",
            "fieldtype": "Data",
            "width": 250,
        },
        {
            "label": _("Qty"),
            "fieldname": "qty",
            "fieldtype": "Float",
            "precision": 2,
            "width": 90,
        },
        {
            "label": _("Warehouse"),
            "fieldname": "warehouse",
            "fieldtype": "Link",
            "options": "Warehouse",
            "width": 180,
        },
    ]
    
def get_data(filters):
    conditions = []

    if filters.get("company"):
        conditions.append("mr.company = %(company)s")

    if filters.get("from_date"):
        conditions.append("mr.transaction_date >= %(from_date)s")

    if filters.get("to_date"):
        conditions.append("mr.transaction_date <= %(to_date)s")

    condition_sql = ""
    if conditions:
        condition_sql = " AND " + " AND ".join(conditions)

    return frappe.db.sql(
        f"""
        SELECT
            mr.name AS material_request,
            mr.transaction_date,
            mr.company,
            mri.item_code,
            mri.item_name,
            mri.qty,
            mri.warehouse
        FROM
            `tabMaterial Request` mr
        INNER JOIN
            `tabMaterial Request Item` mri
            ON mri.parent = mr.name
        WHERE
            mr.docstatus = 1
            AND mr.advance_mr = 1
            AND (
                mri.production_plan IS NULL
                OR mri.production_plan = ''
            )
            {condition_sql}
        ORDER BY
            mr.transaction_date DESC,
            mr.name,
            mri.idx
        """,
        filters,
        as_dict=True,
    )