# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	"""Return columns, data, message, chart, and report_summary for Valve Assembly Report."""
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
	"""Return column definitions strictly based on Valve Assembly & Assembly Item Serial No schema."""
	return [
		{
			"label": _("Valve Assembly"),
			"fieldname": "valve_assembly",
			"fieldtype": "Link",
			"options": "Valve Assembly",
			"width": 140,
		},
		{
			"label": _("Posting Date"),
			"fieldname": "posting_date",
			"fieldtype": "Date",
			"width": 100,
		},
		{
			"label": _("Assembly Date"),
			"fieldname": "assembly_date",
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
			"label": _("Assembler"),
			"fieldname": "user",
			"fieldtype": "Link",
			"options": "Employee",
			"width": 110,
		},
		{
			"label": _("Assembler Name"),
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
			"label": _("Shell MOC"),
			"fieldname": "shell_moc",
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"label": _("Operation"),
			"fieldname": "operation",
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"label": _("Facing"),
			"fieldname": "facing",
			"fieldtype": "Data",
			"width": 90,
		},
		{
			"label": _("Stem MOC"),
			"fieldname": "stem_moc",
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"label": _("Gland Packing + O'Ring MOC"),
			"fieldname": "gland_packing__oring_moc",
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"label": _("End Connection"),
			"fieldname": "end_connection",
			"fieldtype": "Data",
			"width": 110,
		},
		{
			"label": _("Wedge / Plug / Ball / Disc MOC"),
			"fieldname": "wedge_plug_ball_disc_moc",
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"label": _("Seat Ring (GUIDE) MOC"),
			"fieldname": "seat_ringguide_moc",
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"label": _("Gasket"),
			"fieldname": "gasket",
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"label": _("Fasteners"),
			"fieldname": "fasteners",
			"fieldtype": "Data",
			"width": 140,
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
			"label": _("Remark"),
			"fieldname": "remark",
			"fieldtype": "Data",
			"width": 160,
		},
	]


def get_data(filters: dict) -> list[dict]:
	"""Fetch data by joining Valve Assembly (parent) with Assembly Item Serial No (child), submitted only."""
	conditions, values = build_conditions(filters)

	sql = f"""
		SELECT
			va.name AS valve_assembly,
			va.posting_date AS posting_date,
			aisn.date AS assembly_date,
			va.branch AS branch,
			va.user AS user,
			COALESCE(emp.employee_name, va.user) AS user_name,
			va.docstatus AS docstatus,
			aisn.serial_number AS serial_number,
			aisn.item_code AS item_code,
			item.item_name AS item_name,
			aisn.sales_order AS sales_order,
			aisn.batch_no AS batch_no,
			aisn.size AS size,
			aisn.class AS class,
			aisn.shell_moc AS shell_moc,
			aisn.operation AS operation,
			aisn.facing AS facing,
			aisn.stem_moc AS stem_moc,
			aisn.gland_packing__oring_moc AS gland_packing__oring_moc,
			aisn.end_connection AS end_connection,
			aisn.wedge_plug_ball_disc_moc AS wedge_plug_ball_disc_moc,
			aisn.seat_ringguide_moc AS seat_ringguide_moc,
			aisn.gasket AS gasket,
			aisn.fasteners AS fasteners,
			aisn.inch_factor AS inch_factor,
			aisn.value AS value,
			aisn.inches AS inches,
			aisn.remark AS remark
		FROM `tabValve Assembly` va
		INNER JOIN `tabAssembly Item Serial No` aisn
			ON aisn.parent = va.name AND aisn.parenttype = 'Valve Assembly'
		LEFT JOIN `tabEmployee` emp
			ON emp.name = va.user OR emp.user_id = va.user
		LEFT JOIN `tabItem` item
			ON item.name = aisn.item_code
		WHERE va.docstatus = 1
			{conditions}
		ORDER BY va.posting_date DESC, va.name DESC, aisn.idx ASC
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
		conditions.append("va.posting_date >= %(from_date)s")
		values["from_date"] = filters.get("from_date")

	if filters.get("to_date"):
		conditions.append("va.posting_date <= %(to_date)s")
		values["to_date"] = filters.get("to_date")

	if filters.get("branch"):
		conditions.append("va.branch = %(branch)s")
		values["branch"] = filters.get("branch")

	if filters.get("valve_assembly"):
		conditions.append("va.name = %(valve_assembly)s")
		values["valve_assembly"] = filters.get("valve_assembly")

	if filters.get("user"):
		conditions.append("(va.user = %(user)s OR emp.name = %(user)s OR emp.user_id = %(user)s)")
		values["user"] = filters.get("user")

	if filters.get("sales_order"):
		conditions.append("aisn.sales_order = %(sales_order)s")
		values["sales_order"] = filters.get("sales_order")

	if filters.get("batch_no"):
		conditions.append("aisn.batch_no = %(batch_no)s")
		values["batch_no"] = filters.get("batch_no")

	if filters.get("serial_number"):
		conditions.append("aisn.serial_number = %(serial_number)s")
		values["serial_number"] = filters.get("serial_number")

	if filters.get("item_code"):
		conditions.append("aisn.item_code = %(item_code)s")
		values["item_code"] = filters.get("item_code")

	cond_str = ("AND " + " AND ".join(conditions)) if conditions else ""
	return cond_str, values


def get_report_summary(data: list[dict]) -> list[dict]:
	"""Generate executive KPI summary cards for Valve Assembly Report."""
	if not data:
		return []

	total_valves = len(data)
	total_inches = sum(flt(r.get("inches")) for r in data if r.get("inches"))

	return [
		{
			"value": total_valves,
			"label": _("Total Assembled Valves"),
			"datatype": "Int",
			"indicator": "blue",
		},
		{
			"value": total_inches,
			"label": _("Total Inspector Inches"),
			"datatype": "Float",
			"indicator": "purple",
		},
	]


def get_chart(data: list[dict]) -> dict | None:
	"""Return chart configuration if applicable."""
	return None
