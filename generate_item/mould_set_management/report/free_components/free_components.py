# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

"""Free Components: pattern pieces that are not part of any Pattern Set.

* Serial-numbered items: each Active serial with no Pattern Set (Serial No.custom_pattern_set
  empty) is one row, qty 1.
* Items without serial numbers cannot be put in a Pattern Set, so all their stock is free.
  They are shown warehouse-wise from Bin.actual_qty, without a Serial No.

Location is the Serial No's Location when set, otherwise the warehouse's Branch.
"""

import frappe
from frappe import _
from frappe.utils import flt
from frappe.utils.nestedset import get_descendants_of


def execute(filters=None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{"label": _("Serial No"), "fieldname": "serial_no", "fieldtype": "Link", "options": "Serial No", "width": 170},
		{"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 180},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 220},
		{"label": _("Item Group"), "fieldname": "item_group", "fieldtype": "Link", "options": "Item Group", "width": 130},
		{"label": _("Warehouse"), "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 190},
		{"label": _("Location"), "fieldname": "location", "fieldtype": "Data", "width": 120},
		{"label": _("Supplier"), "fieldname": "supplier", "fieldtype": "Link", "options": "Supplier", "width": 150},
		{"label": _("Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 80},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 90},
	]


def get_data(filters):
	items = _get_items(filters)
	if not items:
		return []

	warehouses = _get_warehouses(filters.warehouse) if filters.warehouse else None
	if warehouses is not None and not warehouses:
		return []

	serial_items = [code for code, item in items.items() if item.has_serial_no]
	plain_items = [code for code, item in items.items() if not item.has_serial_no]

	rows = []

	# 1. Free serials
	if serial_items:
		conditions = {
			"item_code": ["in", serial_items],
			"status": "Active",
			"custom_pattern_set": ("is", "not set"),
			"warehouse": ["in", warehouses] if warehouses else ("is", "set"),
		}
		for s in frappe.get_all(
			"Serial No",
			filters=conditions,
			fields=["name", "item_code", "warehouse", "location", "status"],
			order_by="item_code asc, name asc",
		):
			rows.append(
				frappe._dict(
					serial_no=s.name,
					item_code=s.item_code,
					warehouse=s.warehouse,
					location=s.location,
					qty=1.0,
					status=s.status,
				)
			)

	# 2. Items without serial numbers: all stock is free
	if plain_items:
		bin_filters = {"item_code": ["in", plain_items], "actual_qty": [">", 0]}
		if warehouses:
			bin_filters["warehouse"] = ["in", warehouses]
		for b in frappe.get_all(
			"Bin",
			filters=bin_filters,
			fields=["item_code", "warehouse", "actual_qty"],
			order_by="item_code asc, warehouse asc",
		):
			rows.append(
				frappe._dict(
					serial_no=None,
					item_code=b.item_code,
					warehouse=b.warehouse,
					location=None,
					qty=flt(b.actual_qty),
					status=None,
				)
			)

	# Warehouse supplier and branch
	wh_info = {}
	used = list({r.warehouse for r in rows if r.warehouse})
	if used:
		fields = ["name", "custom_supplier"]
		if frappe.db.has_column("Warehouse", "branch"):
			fields.append("branch")
		wh_info = {w.name: w for w in frappe.get_all("Warehouse", filters={"name": ["in", used]}, fields=fields)}

	for r in rows:
		item = items[r.item_code]
		wh = wh_info.get(r.warehouse) or frappe._dict()
		r.item_name = item.item_name
		r.item_group = item.item_group
		r.supplier = wh.get("custom_supplier") or ""
		r.location = r.location or wh.get("branch") or ""

	rows.sort(key=lambda r: (r.item_code, r.warehouse or "", r.serial_no or ""))
	return rows


def _get_items(filters):
	conditions = {"disabled": 0, "is_stock_item": 1}
	if filters.item_group:
		conditions["item_group"] = ["in", [filters.item_group] + (get_descendants_of("Item Group", filters.item_group) or [])]
	if filters.item_code:
		conditions["name"] = filters.item_code
	return {
		i.name: i
		for i in frappe.get_all(
			"Item", filters=conditions, fields=["name", "item_name", "item_group", "has_serial_no"]
		)
	}


def _get_warehouses(warehouse):
	"""A leaf warehouse, or all leaf warehouses under a group warehouse."""
	is_group = frappe.db.get_value("Warehouse", warehouse, "is_group")
	if not is_group:
		return [warehouse]
	return frappe.get_all(
		"Warehouse", filters={"is_group": 0, "name": ["in", get_descendants_of("Warehouse", warehouse) or []]}, pluck="name"
	)
