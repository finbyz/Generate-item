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
			"label": _("Type of Valve"),
			"fieldname": "type_of_valve",
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"label": _("Size"),
			"fieldname": "size",
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"label": _("Class"),
			"fieldname": "class",
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"label": _("Type of Pattern"),
			"fieldname": "type_of_pattern",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Total Sets"),
			"fieldname": "total_count",
			"fieldtype": "Int",
			"width": 100,
		},
		{
			"label": _("Complete Count"),
			"fieldname": "complete_count",
			"fieldtype": "Int",
			"width": 120,
		},
		{
			"label": _("Incomplete Count"),
			"fieldname": "incomplete_count",
			"fieldtype": "Int",
			"width": 130,
		},
		{
			"label": _("Disabled Count"),
			"fieldname": "disabled_count",
			"fieldtype": "Int",
			"width": 120,
		},
		{
			"label": _("In Own Warehouses"),
			"fieldname": "own_wh_count",
			"fieldtype": "Int",
			"width": 140,
		},
		{
			"label": _("With Suppliers"),
			"fieldname": "supplier_count",
			"fieldtype": "Int",
			"width": 130,
		},
	]


def get_data(filters):
	conditions = {"docstatus": 1}
	if filters.get("type_of_valve"):
		conditions["type_of_valve"] = filters["type_of_valve"]
	if filters.get("size"):
		conditions["size"] = filters["size"]
	if filters.get("class"):
		conditions["class"] = filters["class"]
	if filters.get("status"):
		conditions["status"] = filters["status"]
	if filters.get("warehouse"):
		conditions["current_warehouse"] = filters["warehouse"]
	if filters.get("supplier"):
		conditions["current_supplier"] = filters["supplier"]

	sets = frappe.get_all(
		"Pattern Set",
		filters=conditions,
		fields=[
			"name",
			"type_of_valve",
			"size",
			"class",
			"type_of_pattern",
			"status",
			"current_warehouse",
			"current_supplier",
		],
	)

	# Aggregate by (type_of_valve, size, class, type_of_pattern)
	grouped = {}
	for s in sets:
		key = (
			s.type_of_valve or "",
			s.size or "",
			s.get("class") or "",
			s.type_of_pattern or "",
		)
		if key not in grouped:
			grouped[key] = {
				"type_of_valve": key[0],
				"size": key[1],
				"class": key[2],
				"type_of_pattern": key[3],
				"total_count": 0,
				"complete_count": 0,
				"incomplete_count": 0,
				"disabled_count": 0,
				"own_wh_count": 0,
				"supplier_count": 0,
			}

		row = grouped[key]
		row["total_count"] += 1

		if s.status == "Complete":
			row["complete_count"] += 1
		elif s.status == "Incomplete":
			row["incomplete_count"] += 1
		elif s.status == "Disabled":
			row["disabled_count"] += 1

		if s.current_supplier:
			row["supplier_count"] += 1
		elif s.current_warehouse:
			row["own_wh_count"] += 1

	return list(grouped.values())

