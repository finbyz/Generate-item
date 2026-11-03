# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from generate_item.mould_set_management.pattern_set_utils import get_pattern_set_slots_and_serials


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{
			"label": _("Pattern Set"),
			"fieldname": "pattern_set",
			"fieldtype": "Link",
			"options": "Pattern Set",
			"width": 180,
		},
		{
			"label": _("Status"),
			"fieldname": "status",
			"fieldtype": "Data",
			"width": 110,
		},
		{
			"label": _("Missing Item"),
			"fieldname": "missing_item",
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
		{
			"label": _("Missing Quantity"),
			"fieldname": "missing_qty",
			"fieldtype": "Int",
			"width": 130,
		},
		{
			"label": _("Location"),
			"fieldname": "location",
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 160,
		},
	]


def get_data(filters):
	conditions = {"docstatus": 1, "status": "Incomplete"}
	if filters.get("pattern_set"):
		conditions["name"] = filters["pattern_set"]
	if filters.get("warehouse"):
		conditions["current_warehouse"] = filters["warehouse"]

	incomplete_sets = frappe.get_all(
		"Pattern Set",
		filters=conditions,
		fields=["name", "status", "current_warehouse"],
		order_by="name asc",
	)

	data = []
	for s in incomplete_sets:
		info = get_pattern_set_slots_and_serials(s.name)
		for slot in info["slots"]:
			# Only required slots that are short
			if not slot["is_optional"] and slot["attached_qty"] < slot["qty"]:
				missing_qty = int(slot["qty"] - slot["attached_qty"])
				data.append({
					"pattern_set": s.name,
					"status": s.status,
					"missing_item": slot["item_code"],
					"item_name": slot["item_name"],
					"missing_qty": missing_qty,
					"location": s.current_warehouse or _("No Warehouse"),
				})

	return data

