import frappe
from erpnext.stock.report.stock_balance import stock_balance as stock_balance_module
from erpnext.stock.report.stock_balance.stock_balance import execute as stock_balance_execute
from frappe.desk.query_report import normalize_result

STOCK_BALANCE_REPORT = "Stock Balance"


def _get_item_descriptions(item_codes):
    if not item_codes:
        return {}
    items = frappe.get_all(
        "Item",
        filters={"name": ["in", item_codes]},
        fields=["name", "description"],
        as_list=True,
    )
    return frappe._dict(items)


def _add_description_column(columns):
    if not columns:
        return columns
    if any(column.get("fieldname") == "description" for column in columns):
        return columns

    insert_at = None
    for index, column in enumerate(columns):
        if column.get("fieldname") == "item_code":
            insert_at = index + 1  # right after Item Code, not +3
            break
    if insert_at is None:
        insert_at = len(columns)

    columns.insert(
        insert_at,
        {
            "label": "Item Description",
            "fieldname": "description",
            "fieldtype": "Data",
            "width": 250,
        },
    )
    return columns


def _enrich_stock_balance(columns, data):
    columns = list(columns or [])
    data = list(data or [])

    data = normalize_result(data, columns)
    columns = _add_description_column(columns)

    descriptions = _get_item_descriptions(
        [row.get("item_code") for row in data if isinstance(row, dict) and row.get("item_code")]
    )
    for row in data:
        if isinstance(row, dict):
            row["description"] = descriptions.get(row.get("item_code"))

    return columns, data


def custom_execute(filters=None):
    try:
        columns, data = stock_balance_execute(filters) or ([], [])
        columns, data = _enrich_stock_balance(columns, data)
        return columns, data
    except Exception:
        # Writes to Error Log doctype — visible on FC via Desk, unlike file logging
        frappe.log_error(
            title="Custom Stock Balance execute failed",
            message=frappe.get_traceback(),
        )
        raise