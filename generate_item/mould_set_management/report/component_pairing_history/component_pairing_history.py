# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{
			"label": _("Serial No"),
			"fieldname": "serial_no",
			"fieldtype": "Link",
			"options": "Serial No",
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
			"label": _("Pattern Set"),
			"fieldname": "pattern_set",
			"fieldtype": "Link",
			"options": "Pattern Set",
			"width": 180,
		},
		{
			"label": _("Paired On"),
			"fieldname": "paired_on",
			"fieldtype": "Datetime",
			"width": 150,
		},
		{
			"label": _("Unpaired On"),
			"fieldname": "unpaired_on",
			"fieldtype": "Datetime",
			"width": 150,
		},
		{
			"label": _("Pairing Status"),
			"fieldname": "pairing_status",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Reason"),
			"fieldname": "reason",
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"label": _("Source DocType"),
			"fieldname": "source_doctype",
			"fieldtype": "Link",
			"options": "DocType",
			"width": 140,
		},
		{
			"label": _("Source Document"),
			"fieldname": "source_doc",
			"fieldtype": "Dynamic Link",
			"options": "source_doctype",
			"width": 160,
		},
		{
			"label": _("Change Reference"),
			"fieldname": "change_ref",
			"fieldtype": "Link",
			"options": "Pattern Set Component Change",
			"width": 160,
		},
	]


def get_data(filters):
	conditions = {}
	if filters.get("serial_no"):
		conditions["serial_no"] = filters["serial_no"]
	if filters.get("pattern_set"):
		conditions["pattern_set"] = filters["pattern_set"]

	logs = frappe.get_all(
		"Component Pairing Log",
		filters=conditions,
		fields=[
			"serial_no",
			"item_code",
			"pattern_set",
			"paired_on",
			"unpaired_on",
			"reason",
			"source_doctype",
			"source_doc",
			"change_ref",
		],
		order_by="paired_on desc",
	)

	data = []
	for row in logs:
		is_current = not bool(row.unpaired_on)
		data.append({
			"serial_no": row.serial_no,
			"item_code": row.item_code,
			"pattern_set": row.pattern_set,
			"paired_on": row.paired_on,
			"unpaired_on": row.unpaired_on,
			"pairing_status": _("Currently Active") if is_current else _("Past Pairing"),
			"reason": row.reason,
			"source_doctype": row.source_doctype,
			"source_doc": row.source_doc,
			"change_ref": row.change_ref or row.source_doc,
		})

	return data


