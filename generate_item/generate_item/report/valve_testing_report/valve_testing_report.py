# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	"""Return columns, data, message, chart, and report_summary for Valve Testing Report."""
	filters = frappe._dict(filters or {})
	columns = get_columns()
	data = get_data(filters)
	report_summary = get_report_summary(data)
	chart = get_chart(data)

	message = None
	if not data:
		message = _("No records found for the selected filters.")

	return columns, data, message, chart, report_summary


def get_columns() -> list[dict]:
	"""Return column definitions strictly based on Valve Testing & Valve Testing Item schema."""
	return [
		{
			"label": _("Valve Testing"),
			"fieldname": "valve_testing",
			"fieldtype": "Link",
			"options": "Valve Testing",
			"width": 140,
		},
		{
			"label": _("Posting Date"),
			"fieldname": "posting_date",
			"fieldtype": "Date",
			"width": 100,
		},
		{
			"label": _("Test Date"),
			"fieldname": "test_date",
			"fieldtype": "Date",
			"width": 100,
		},
		{
			"label": _("Branch"),
			"fieldname": "branch",
			"fieldtype": "Link",
			"options": "Branch",
			"width": 100,
		},
		{
			"label": _("Inspector"),
			"fieldname": "user",
			"fieldtype": "Link",
			"options": "Employee",
			"width": 110,
		},
		{
			"label": _("Inspector Name"),
			"fieldname": "user_name",
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"label": _("Valve Sr No"),
			"fieldname": "serial_number",
			"fieldtype": "Link",
			"options": "Serial Number",
			"width": 130,
		},
		{
			"label": _("Item Code"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 140,
		},
		{
			"label": _("Item Name"),
			"fieldname": "item_name",
			"fieldtype": "Data",
			"width": 160,
		},
		{
			"label": _("Sales Order"),
			"fieldname": "sales_order",
			"fieldtype": "Link",
			"options": "Sales Order",
			"width": 130,
		},
		{
			"label": _("Batch No"),
			"fieldname": "batch_no",
			"fieldtype": "Link",
			"options": "Batch",
			"width": 120,
		},
		{
			"label": _("Valve Type"),
			"fieldname": "type",
			"fieldtype": "Data",
			"width": 110,
		},
		{
			"label": _("Size"),
			"fieldname": "size",
			"fieldtype": "Data",
			"width": 80,
		},
		{
			"label": _("Class/Rating"),
			"fieldname": "class",
			"fieldtype": "Data",
			"width": 90,
		},
		{
			"label": _("MOC"),
			"fieldname": "shell_moc",
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"label": _("End Connection"),
			"fieldname": "end_connection",
			"fieldtype": "Data",
			"width": 110,
		},
		{
			"label": _("Operation"),
			"fieldname": "operation",
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"label": _("Inch Factor"),
			"fieldname": "inch_factor",
			"fieldtype": "Data",
			"width": 90,
		},
		{
			"label": _("Size Value"),
			"fieldname": "value",
			"fieldtype": "Data",
			"width": 80,
		},
		{
			"label": _("Inspector Inches"),
			"fieldname": "inches",
			"fieldtype": "Float",
			"width": 110,
		},
		{
			"label": _("Test Result"),
			"fieldname": "test_ok",
			"fieldtype": "Data",
			"width": 110,
		},
		{
			"label": _("Leak Reason"),
			"fieldname": "leak_reason",
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"label": _("Remark"),
			"fieldname": "remark",
			"fieldtype": "Data",
			"width": 160,
		},
	]


def get_data(filters: dict) -> list[dict]:
	"""Fetch data by joining Valve Testing (parent) with Valve Testing Item (child), submitted only."""
	conditions, values = build_conditions(filters)

	sql = f"""
		SELECT
			vt.name AS valve_testing,
			vt.posting_date AS posting_date,
			vti.date AS test_date,
			vt.branch AS branch,
			vt.user AS user,
			emp.employee_name AS user_name,
			vt.docstatus AS docstatus,
			vti.serial_number AS serial_number,
			vti.item_code AS item_code,
			item.item_name AS item_name,
			vti.sales_order AS sales_order,
			vti.batch_no AS batch_no,
			vti.type AS type,
			vti.size AS size,
			vti.class AS class,
			vti.shell_moc AS shell_moc,
			vti.end_connection AS end_connection,
			vti.operation AS operation,
			vti.inch_factor AS inch_factor,
			vti.value AS value,
			vti.inches AS inches,
			vti.test_ok AS test_ok,
			vti.leak_reason AS leak_reason,
			vti.remark AS remark
		FROM `tabValve Testing` vt
		INNER JOIN `tabValve Testing Item` vti
			ON vti.parent = vt.name AND vti.parenttype = 'Valve Testing'
		LEFT JOIN `tabEmployee` emp
			ON emp.name = vt.user
		LEFT JOIN `tabItem` item
			ON item.name = vti.item_code
		WHERE vt.docstatus = 1
			{conditions}
		ORDER BY vt.posting_date DESC, vt.name DESC, vti.idx ASC
	"""

	data = frappe.db.sql(sql, values, as_dict=True)

	for row in data:
		if row.inches:
			row.inches = flt(row.inches)

	return data


def build_conditions(filters: dict) -> tuple[str, dict]:
	"""Construct SQL WHERE conditions securely using parameterized queries."""
	conditions = []
	values = {}

	if filters.get("from_date"):
		conditions.append("vt.posting_date >= %(from_date)s")
		values["from_date"] = filters.get("from_date")

	if filters.get("to_date"):
		conditions.append("vt.posting_date <= %(to_date)s")
		values["to_date"] = filters.get("to_date")

	if filters.get("branch"):
		conditions.append("vt.branch = %(branch)s")
		values["branch"] = filters.get("branch")

	if filters.get("valve_testing"):
		conditions.append("vt.name = %(valve_testing)s")
		values["valve_testing"] = filters.get("valve_testing")

	if filters.get("user"):
		conditions.append("vt.user = %(user)s")
		values["user"] = filters.get("user")

	if filters.get("sales_order"):
		conditions.append("vti.sales_order = %(sales_order)s")
		values["sales_order"] = filters.get("sales_order")

	if filters.get("batch_no"):
		conditions.append("vti.batch_no = %(batch_no)s")
		values["batch_no"] = filters.get("batch_no")

	if filters.get("serial_number"):
		conditions.append("vti.serial_number = %(serial_number)s")
		values["serial_number"] = filters.get("serial_number")

	if filters.get("item_code"):
		conditions.append("vti.item_code = %(item_code)s")
		values["item_code"] = filters.get("item_code")

	if filters.get("test_ok") and filters.get("test_ok") not in ("Both", "All", ""):
		conditions.append("vti.test_ok = %(test_ok)s")
		values["test_ok"] = filters.get("test_ok")

	if filters.get("leak_reason"):
		conditions.append("vti.leak_reason = %(leak_reason)s")
		values["leak_reason"] = filters.get("leak_reason")

	cond_str = ("AND " + " AND ".join(conditions)) if conditions else ""
	return cond_str, values


def get_report_summary(data: list[dict]) -> list[dict]:
	"""Generate executive KPI summary cards for Valve Testing Report."""
	if not data:
		return []

	total_tested = len(data)
	no_leak_accepted = sum(1 for r in data if r.get("test_ok") == "Accepted")
	not_accepted = sum(1 for r in data if r.get("test_ok") == "Not Accepted")
	total_inches = sum(flt(r.get("inches")) for r in data if r.get("inches"))

	acceptance_rate = (no_leak_accepted / total_tested * 100) if total_tested else 0.0

	return [
		{
			"value": total_tested,
			"label": _("Total Tested Valves"),
			"datatype": "Int",
			"indicator": "blue",
		},
		{
			"value": no_leak_accepted,
			"label": _("Accepted"),
			"datatype": "Int",
			"indicator": "green",
		},
		{
			"value": not_accepted,
			"label": _("Not Accepted"),
			"datatype": "Int",
			"indicator": "red" if not_accepted > 0 else "gray",
		},
		{
			"value": f"{acceptance_rate:.1f}%",
			"label": _("Acceptance Rate"),
			"datatype": "Data",
			"indicator": "green" if acceptance_rate >= 90 else ("orange" if acceptance_rate >= 75 else "red"),
		},
		{
			"value": total_inches,
			"label": _("Total Inspector Inches"),
			"datatype": "Float",
			"indicator": "purple",
		},
	]


def get_chart(data: list[dict]) -> dict | None:
	"""Generate a clean Bar Chart showing Not Accepted (Red) and Accepted (Green) bars."""
	if not data:
		return None

	not_accepted = sum(1 for r in data if r.get("test_ok") == "Not Accepted")
	accepted = sum(1 for r in data if r.get("test_ok") == "Accepted")

	if not_accepted == 0 and accepted == 0:
		return None

	return {
		"data": {
			"labels": [_("Valves Status")],
			"datasets": [
				{
					"name": _("Not Accepted"),
					"values": [not_accepted],
				},
				{
					"name": _("Accepted"),
					"values": [accepted],
				},
			],
		},
		"type": "bar",
		"height": 220,
		"colors": ["#ff5858", "#28a745"],
	}
