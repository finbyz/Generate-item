import frappe
from erpnext.stock.report.stock_balance.stock_balance import execute as original_execute

def _get_item_descriptions(item_codes):
    if not item_codes:
        return {}
    items = frappe.get_all("Item", filters={"name": ["in", item_codes]}, fields=["name", "description"])
    return {d.name: d.description for d in items}

def _add_description_column(columns):
    if any(col.get("fieldname") == "description" for col in columns if isinstance(col, dict)):
        return columns
    # Insert after "item_code" (or at position 5)
    insert_at = 5
    for i, col in enumerate(columns):
        if isinstance(col, dict) and col.get("fieldname") == "item_code":
            insert_at = i + 3
            break
    columns.insert(insert_at, {
        "label": "Item Description",
        "fieldname": "description",
        "fieldtype": "Data",
        "width": 250
    })
    return columns

def execute(filters=None):
    columns, data = original_execute(filters) or ([], [])
    # Ensure columns and data are lists
    columns = list(columns)
    data = list(data)
    frappe.error_log(f"Columns: {columns}", "Stock Balance Override")
    # Add description column if missing
    columns = _add_description_column(columns)

    # Fetch descriptions for all item codes
    item_codes = [row.get("item_code") for row in data if isinstance(row, dict) and row.get("item_code")]
    descriptions = _get_item_descriptions(item_codes)

    # Enrich rows
    for row in data:
        if isinstance(row, dict):
            row["description"] = descriptions.get(row.get("item_code"))

    return columns, data