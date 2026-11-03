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
			"label": _("Item Name"),
			"fieldname": "item_name",
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"label": _("Warehouse"),
			"fieldname": "warehouse",
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 160,
		},
		{
			"label": _("Supplier"),
			"fieldname": "supplier",
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 140,
		},
		{
			"label": _("Status"),
			"fieldname": "status",
			"fieldtype": "Data",
			"width": 100,
		},
	]


def get_data(filters):
	conditions = {
		"status": "Active",
		"custom_pattern_set": ("is", "not set"),
	}

	if filters.get("item_code"):
		conditions["item_code"] = filters["item_code"]
	if filters.get("warehouse"):
		conditions["warehouse"] = filters["warehouse"]

	serials = frappe.get_all(
		"Serial No",
		filters=conditions,
		fields=["name", "item_code", "item_name", "warehouse", "status"],
		order_by="item_code asc, name asc",
	)

	# Fetch supplier for warehouses
	wh_suppliers = {}
	warehouses = {s.warehouse for s in serials if s.warehouse}
	if warehouses:
		wh_data = frappe.get_all(
			"Warehouse",
			filters={"name": ["in", list(warehouses)]},
			fields=["name", "custom_supplier"],
		)
		wh_suppliers = {w.name: w.custom_supplier for w in wh_data}

	data = []
	for s in serials:
		data.append({
			"serial_no": s.name,
			"item_code": s.item_code,
			"item_name": s.item_name,
			"warehouse": s.warehouse,
			"supplier": wh_suppliers.get(s.warehouse, ""),
			"status": s.status,
		})

	return data

