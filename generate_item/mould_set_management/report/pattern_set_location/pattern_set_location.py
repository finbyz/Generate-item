# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import date_diff, nowdate
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
			"width": 160,
		},
		{
			"label": _("Valve Type"),
			"fieldname": "type_of_valve",
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"label": _("Size"),
			"fieldname": "size",
			"fieldtype": "Data",
			"width": 80,
		},
		{
			"label": _("Class"),
			"fieldname": "class",
			"fieldtype": "Data",
			"width": 80,
		},
		{
			"label": _("Status"),
			"fieldname": "status",
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"label": _("Current Warehouse"),
			"fieldname": "warehouse",
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 160,
		},
		{
			"label": _("Current Supplier"),
			"fieldname": "supplier",
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 140,
		},
		{
			"label": _("Last Transfer"),
			"fieldname": "last_transfer",
			"fieldtype": "Link",
			"options": "Pattern Set Transfer",
			"width": 140,
		},
		{
			"label": _("Days at Location"),
			"fieldname": "days_at_location",
			"fieldtype": "Int",
			"width": 130,
		},
		{
			"label": _("Attached vs Required"),
			"fieldname": "attached_vs_required",
			"fieldtype": "Data",
			"width": 160,
		},
	]


def get_data(filters):
	conditions = {"docstatus": 1}
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
			"status",
			"current_warehouse",
			"current_supplier",
		],
		order_by="name asc",
	)

	today = nowdate()
	data = []

	for s in sets:
		# Find last transfer
		last_transfer = frappe.get_all(
			"Pattern Set Transfer",
			filters={"pattern_set": s.name, "docstatus": 1},
			fields=["name", "posting_date"],
			order_by="posting_date desc, creation desc",
			limit=1,
		)

		transfer_name = last_transfer[0].name if last_transfer else ""
		transfer_date = str(last_transfer[0].posting_date) if last_transfer else ""
		days_at_loc = date_diff(today, transfer_date) if transfer_date else 0

		if filters.get("days_more_than_n") and days_at_loc <= int(filters["days_more_than_n"]):
			continue

		info = get_pattern_set_slots_and_serials(s.name)
		total_req = sum(slot["qty"] for slot in info["slots"] if not slot["is_optional"])
		total_att = sum(slot["attached_qty"] for slot in info["slots"] if not slot["is_optional"])
		att_vs_req = f"{total_att} / {int(total_req)}"

		data.append({
			"pattern_set": s.name,
			"type_of_valve": s.type_of_valve,
			"size": s.size,
			"class": s.get("class"),
			"status": s.status,
			"warehouse": s.current_warehouse,
			"supplier": s.current_supplier,
			"last_transfer": transfer_name,
			"days_at_location": days_at_loc,
			"attached_vs_required": att_vs_req,
		})

	return data

