# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import add_days, cint, getdate, nowdate


def execute(filters=None):
	"""Return columns, data, message, chart, and report_summary for Valve Warranty Register."""
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
	"""Return column definitions for Valve Warranty Register ordered respectively:

	Sales Invoice, Sales Order, Batch No, Valve Serial No, Warranty Status,
	Days Remaining, Item Code, followed by related details.
	"""
	return [
		{
			"label": _("Sales Invoice"),
			"fieldname": "sales_invoice",
			"fieldtype": "Link",
			"options": "Sales Invoice",
			"width": 140,
		},
		{
			"label": _("Invoice Date"),
			"fieldname": "invoice_date",
			"fieldtype": "Date",
			"width": 100,
		},
		{
			"label": _("Sales Order"),
			"fieldname": "sales_order",
			"fieldtype": "Link",
			"options": "Sales Order",
			"width": 140,
		},
		{
			"label": _("Branch"),
			"fieldname": "branch",
			"fieldtype": "Link",
			"options": "Branch",
			"width": 110,
		},
		{
			"label": _("Customer"),
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 180,
		},
		{
			"label": _("Batch No"),
			"fieldname": "batch",
			"fieldtype": "Link",
			"options": "Batch",
			"width": 140,
		},
		{
			"label": _("Valve Serial No"),
			"fieldname": "serial_number",
			"fieldtype": "Link",
			"options": "Serial Number",
			"width": 140,
		},
		{
			"label": _("Stock Entry"),
			"fieldname": "stock_entry",
			"fieldtype": "Link",
			"options": "Stock Entry",
			"width": 130,
		},
		{
			"label": _("Warranty Status"),
			"fieldname": "warranty_status",
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"label": _("Days Remaining"),
			"fieldname": "days_remaining",
			"fieldtype": "Int",
			"width": 130,
		},
		{
			"label": _("Warranty Expiry Date"),
			"fieldname": "warranty_expiry_date",
			"fieldtype": "Date",
			"width": 140,
		},
		{
			"label": _("Warranty Period (Days)"),
			"fieldname": "warranty_period",
			"fieldtype": "Int",
			"width": 140,
		},
		{
			"label": _("Item Code"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 160,
		},
		{
			"label": _("Item Name"),
			"fieldname": "item_name",
			"fieldtype": "Data",
			"width": 180,
		},
		
		
		
		# {
		# 	"label": _("SO Date"),
		# 	"fieldname": "so_date",
		# 	"fieldtype": "Date",
		# 	"width": 100,
		# },
		{
			"label": _("Delivery Note"),
			"fieldname": "delivery_note",
			"fieldtype": "Link",
			"options": "Delivery Note",
			"width": 140,
		},
		{
			"label": _("Customer PO"),
			"fieldname": "po_no",
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"label": _("Tag No"),
			"fieldname": "tag_no",
			"fieldtype": "Data",
			"width": 130,
		},
		{
			"label": _("Valve Type"),
			"fieldname": "valve_type",
			"fieldtype": "Data",
			"width": 130,
		},
		{
			"label": _("Size"),
			"fieldname": "size",
			"fieldtype": "Data",
			"width": 90,
		},
		{
			"label": _("Class/Rating"),
			"fieldname": "valve_class",
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"label": _("Valve End"),
			"fieldname": "valve_end",
			"fieldtype": "Data",
			"width": 110,
		},
		{
			"label": _("Shell MOC"),
			"fieldname": "shell_moc",
			"fieldtype": "Data",
			"width": 130,
		},
		{
			"label": _("Operation"),
			"fieldname": "operation",
			"fieldtype": "Data",
			"width": 130,
		},
		
	]


def get_data(filters: dict) -> list[dict]:
	"""Fetch data by joining Serial Number with Sales Order, Sales Invoice, and Item Generator."""
	conditions, values = build_conditions(filters)
	today = getdate(nowdate())

	sql = f"""
		SELECT
			sn.name AS serial_number,
			sn.batch AS batch,
			sn.branch AS branch,
			sn.stock_entry AS stock_entry,
			sn.warranty_expiry_date AS warranty_expiry_date,
			MAX(so.name) AS sales_order,
			MAX(so.customer) AS customer,
			MAX(so.po_no) AS po_no,

			MAX(COALESCE(si_so.name, si_b.name)) AS sales_invoice,
			MAX(COALESCE(si_so.posting_date, si_b.posting_date)) AS invoice_date,
			MAX(COALESCE(sii_so.delivery_note, sii_b.delivery_note)) AS delivery_note,
			MAX(COALESCE(soi.item_code, sii_so.item_code, sii_b.item_code)) AS item_code,
			MAX(COALESCE(soi.item_name, sii_so.item_name, sii_b.item_name, item.item_name)) AS item_name,
			MAX(soi.tag_no) AS tag_no,
			MAX(COALESCE(soi.warranty_period, sii_so.warranty_period, sii_b.warranty_period, so.warranty_period, 0)) AS warranty_period,
			MAX(ig.attribute_2_value) AS valve_type,
			MAX(ig.attribute_5_value) AS size,
			MAX(ig.attribute_6_value) AS valve_class,
			MAX(ig.attribute_7_value) AS valve_end,
			MAX(ig.attribute_9_value) AS shell_moc,
			MAX(ig.attribute_19_value) AS operation
		FROM `tabSerial Number` sn
		LEFT JOIN `tabSales Order Item` soi
			ON soi.custom_batch_no = sn.batch AND soi.docstatus != 2
		LEFT JOIN `tabSales Order` so
			ON so.name = soi.parent AND so.docstatus != 2
		LEFT JOIN `tabSales Invoice Item` sii_so
			ON sii_so.so_detail = soi.name AND sii_so.docstatus = 1
		LEFT JOIN `tabSales Invoice Item` sii_b
			ON soi.name IS NULL AND sii_b.batch_no_ref = sn.batch AND sii_b.docstatus = 1
		LEFT JOIN `tabSales Invoice` si_so
			ON si_so.name = sii_so.parent AND si_so.docstatus = 1
		LEFT JOIN `tabSales Invoice` si_b
			ON si_b.name = sii_b.parent AND si_b.docstatus = 1
		LEFT JOIN `tabItem` item
			ON item.name = COALESCE(soi.item_code, sii_so.item_code, sii_b.item_code)
		LEFT JOIN `tabItem Generator` ig
			ON ig.created_item = COALESCE(soi.item_code, sii_so.item_code, sii_b.item_code)
		WHERE sn.docstatus != 2
			AND sn.warranty_expiry_date IS NOT NULL
			{conditions}
		GROUP BY sn.name
		ORDER BY
			CASE WHEN sn.warranty_expiry_date IS NULL THEN 1 ELSE 0 END,
			sn.warranty_expiry_date ASC,
			sn.name DESC
	"""

	data = frappe.db.sql(sql, values, as_dict=True)

	for row in data:
		row.warranty_period = cint(row.warranty_period)
		if row.warranty_expiry_date:
			exp_date = getdate(row.warranty_expiry_date)
			diff_days = (exp_date - today).days
			row.days_remaining = diff_days

			if diff_days < 0:
				row.warranty_status = _("Expired")
			elif diff_days <= 30:
				row.warranty_status = _("Expiring in 30 Days")
			elif diff_days <= 60:
				row.warranty_status = _("Expiring in 60 Days")
			else:
				row.warranty_status = _("Under Warranty")
		else:
			row.days_remaining = None
			row.warranty_status = _("Not Set")

	return data


def build_conditions(filters: dict) -> tuple[str, dict]:
	"""Construct SQL WHERE conditions securely using parameterized queries."""
	conditions = []
	values = {}
	today_str = nowdate()

	if filters.get("sales_order"):
		conditions.append("so.name = %(sales_order)s")
		values["sales_order"] = filters.get("sales_order")

	if filters.get("sales_invoice"):
		conditions.append("(si_so.name = %(sales_invoice)s OR si_b.name = %(sales_invoice)s)")
		values["sales_invoice"] = filters.get("sales_invoice")

	if filters.get("batch"):
		conditions.append("sn.batch = %(batch)s")
		values["batch"] = filters.get("batch")

	if filters.get("serial_number"):
		conditions.append("sn.name = %(serial_number)s")
		values["serial_number"] = filters.get("serial_number")

	if filters.get("branch"):
		conditions.append("(sn.branch = %(branch)s OR so.branch = %(branch)s OR si_so.branch = %(branch)s OR si_b.branch = %(branch)s)")
		values["branch"] = filters.get("branch")

	if filters.get("customer"):
		conditions.append("(so.customer = %(customer)s OR si_so.customer = %(customer)s OR si_b.customer = %(customer)s)")
		values["customer"] = filters.get("customer")

	if filters.get("item_code"):
		conditions.append("(soi.item_code = %(item_code)s OR sii_so.item_code = %(item_code)s OR sii_b.item_code = %(item_code)s)")
		values["item_code"] = filters.get("item_code")

	if filters.get("from_expiry_date"):
		conditions.append("sn.warranty_expiry_date >= %(from_expiry_date)s")
		values["from_expiry_date"] = filters.get("from_expiry_date")

	if filters.get("to_expiry_date"):
		conditions.append("sn.warranty_expiry_date <= %(to_expiry_date)s")
		values["to_expiry_date"] = filters.get("to_expiry_date")

	if filters.get("from_invoice_date"):
		conditions.append("COALESCE(si_so.posting_date, si_b.posting_date) >= %(from_invoice_date)s")
		values["from_invoice_date"] = filters.get("from_invoice_date")

	if filters.get("to_invoice_date"):
		conditions.append("COALESCE(si_so.posting_date, si_b.posting_date) <= %(to_invoice_date)s")
		values["to_invoice_date"] = filters.get("to_invoice_date")

	# Warranty Status filter
	warranty_status = filters.get("warranty_status")
	if warranty_status == "Under Warranty":
		conditions.append("sn.warranty_expiry_date >= %(today)s")
		values["today"] = today_str
	elif warranty_status == "Expiring in 30 Days":
		conditions.append("sn.warranty_expiry_date >= %(today)s AND sn.warranty_expiry_date <= %(in_30_days)s")
		values["today"] = today_str
		values["in_30_days"] = add_days(today_str, 30)
	elif warranty_status == "Expiring in 60 Days":
		conditions.append("sn.warranty_expiry_date >= %(today)s AND sn.warranty_expiry_date <= %(in_60_days)s")
		values["today"] = today_str
		values["in_60_days"] = add_days(today_str, 60)
	elif warranty_status == "Expired":
		conditions.append("sn.warranty_expiry_date < %(today)s")
		values["today"] = today_str
	elif warranty_status == "Warranty Expiry Not Set":
		conditions.append("sn.warranty_expiry_date IS NULL")

	cond_str = ("AND " + " AND ".join(conditions)) if conditions else ""
	return cond_str, values


def get_report_summary(data: list[dict]) -> list[dict]:
	"""Generate executive KPI summary cards for Valve Warranty Register."""
	if not data:
		return []

	total_valves = len(data)
	under_warranty = sum(1 for r in data if r.get("warranty_status") == _("Under Warranty"))
	expiring_30 = sum(1 for r in data if r.get("warranty_status") == _("Expiring in 30 Days"))
	expiring_60 = sum(1 for r in data if r.get("warranty_status") == _("Expiring in 60 Days"))
	expired = sum(1 for r in data if r.get("warranty_status") == _("Expired"))
	not_set = sum(1 for r in data if r.get("warranty_status") == _("Not Set"))

	return [
		{
			"value": total_valves,
			"label": _("Total Valves"),
			"datatype": "Int",
			"indicator": "blue",
		},
		{
			"value": under_warranty,
			"label": _("Under Warranty"),
			"datatype": "Int",
			"indicator": "green",
		},
		{
			"value": expiring_30 + expiring_60,
			"label": _("Expiring Soon (<= 60 Days)"),
			"datatype": "Int",
			"indicator": "orange",
		},
		{
			"value": expired,
			"label": _("Expired Warranty"),
			"datatype": "Int",
			"indicator": "red",
		},
		{
			"value": not_set,
			"label": _("Expiry Date Not Set"),
			"datatype": "Int",
			"indicator": "gray",
		},
	]


def get_chart(data: list[dict]) -> dict | None:
	"""Return chart configuration for warranty status breakdown."""
	if not data:
		return None

	status_counts = {
		_("Under Warranty"): 0,
		_("Expiring Soon"): 0,
		_("Expired"): 0,
		_("Not Set"): 0,
	}

	for r in data:
		status = r.get("warranty_status")
		if status == _("Under Warranty"):
			status_counts[_("Under Warranty")] += 1
		elif status in (_("Expiring in 30 Days"), _("Expiring in 60 Days")):
			status_counts[_("Expiring Soon")] += 1
		elif status == _("Expired"):
			status_counts[_("Expired")] += 1
		else:
			status_counts[_("Not Set")] += 1

	labels = list(status_counts.keys())
	values = [status_counts[label] for label in labels]

	if not any(values):
		return None

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{
					"name": _("Warranty Status"),
					"values": values,
				}
			],
		},
		"type": "donut",
		"colors": ["#22c55e", "#f59e0b", "#ef4444", "#9ca3af"],
	}
