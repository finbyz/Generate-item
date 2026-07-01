import frappe
from erpnext.stock.report.stock_balance.stock_balance import execute as stock_balance_execute

def execute(filters=None):
    columns, data = stock_balance_execute(filters)

    # Add Item Description column after Item Code
    columns.insert(3, {
        "label": "Item Description",
        "fieldname": "description",
        "fieldtype": "Data",
        "width": 250,
    })

    # Fetch descriptions
    descriptions = frappe._dict(
        frappe.get_all(
            "Item",
            fields=["name", "description"],
            as_list=True
        )
    )

    for row in data:
        row["description"] = descriptions.get(row.get("item_code"))

    return columns, data