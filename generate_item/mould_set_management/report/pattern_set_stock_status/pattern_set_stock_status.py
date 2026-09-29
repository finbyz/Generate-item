# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import math
import frappe
from frappe import _
from frappe.utils import flt
from erpnext.stock.utils import get_stock_balance


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{
			"label": _("Pattern Set Item"),
			"fieldname": "mould_set_item",
			"fieldtype": "Link",
			"options": "Item",
			"width": 160,
		},
		{
			"label": _("Pattern Set"),
			"fieldname": "mould_set",
			"fieldtype": "Link",
			"options": "Pattern Set",
			"width": 140,
		},
		{
			"label": _("Warehouse"),
			"fieldname": "warehouse",
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 180,
		},
		{
			"label": _("Supplier WH?"),
			"fieldname": "is_supplier_warehouse",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Complete Sets"),
			"fieldname": "complete_sets_available",
			"fieldtype": "Float",
			"width": 130,
		},
		{
			"label": _("Component Item"),
			"fieldname": "component_item",
			"fieldtype": "Link",
			"options": "Item",
			"width": 160,
		},
		{
			"label": _("Component Name"),
			"fieldname": "component_name",
			"fieldtype": "Data",
			"width": 160,
		},
		{
			"label": _("Qty Per Set"),
			"fieldname": "required_qty",
			"fieldtype": "Float",
			"width": 110,
		},
		{
			"label": _("In-Stock Qty"),
			"fieldname": "actual_qty",
			"fieldtype": "Float",
			"width": 120,
		},
		{
			"label": _("Loose Qty"),
			"fieldname": "loose_qty",
			"fieldtype": "Float",
			"width": 120,
		},
		{
			"label": _("UOM"),
			"fieldname": "uom",
			"fieldtype": "Link",
			"options": "UOM",
			"width": 90,
		},
		{
			"label": _("Drawing No"),
			"fieldname": "drawing_no",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Drawing Rev No"),
			"fieldname": "drawing_rev_no",
			"fieldtype": "Data",
			"width": 120,
		},
	]


def get_data(filters):
	if not filters:
		filters = {}

	# Filter Pattern Sets
	pattern_set_conditions = {"docstatus": ["!=", 2]}
	if filters.get("mould_set_item"):
		pattern_set_conditions["item"] = filters.get("mould_set_item")
	if filters.get("mould_set"):
		pattern_set_conditions["name"] = filters.get("mould_set")

	pattern_sets = frappe.get_all(
		"Pattern Set",
		filters=pattern_set_conditions,
		fields=["name", "item", "pattern_set_name"],
	)

	if not pattern_sets:
		return []

	supplier_warehouses = set(
		frappe.get_all("Supplier", filters={"warehouse": ["!=", ""]}, pluck="warehouse")
	)

	# Filter Warehouses
	wh_filters = {"is_group": 0}
	if filters.get("company"):
		wh_filters["company"] = filters.get("company")
	if filters.get("warehouse"):
		wh_filters["name"] = filters.get("warehouse")
	elif filters.get("supplier"):
		supp_wh = frappe.db.get_value("Supplier", filters.get("supplier"), "warehouse")
		wh_filters["name"] = supp_wh or ""
	elif filters.get("is_supplier_warehouse"):
		wh_filters["name"] = ["in", list(supplier_warehouses) or [""]]

	warehouses = frappe.get_all(
		"Warehouse",
		filters=wh_filters,
		fields=["name"],
	)

	data = []
	for ps in pattern_sets:
		components = frappe.get_all(
			"Pattern Set Component",
			filters={"parent": ps.name},
			fields=[
				"component_item",
				"component_name",
				"qty",
				"uom",
				"drawing_no",
				"drawing_rev_no",
				"pattern_drawing_no",
				"pattern_drawing_rev_no",
			],
			order_by="idx asc",
		)

		if not components:
			continue

		for wh in warehouses:
			comp_stock_map = {}
			for c in components:
				stock = get_stock_balance(c.component_item, wh.name)
				comp_stock_map[c.component_item] = max(0.0, flt(stock))

			# Calculate complete sets
			sets_possible = []
			for c in components:
				req = flt(c.qty)
				if req > 0:
					sets_possible.append(math.floor(comp_stock_map[c.component_item] / req))
				else:
					sets_possible.append(0)

			complete_sets = min(sets_possible) if sets_possible else 0

			total_stock_at_wh = sum(comp_stock_map.values())
			if total_stock_at_wh > 0 or filters.get("warehouse"):
				for c in components:
					actual_qty = comp_stock_map[c.component_item]
					req_qty = flt(c.qty)
					loose_qty = max(0.0, actual_qty - (complete_sets * req_qty))

					is_supp = wh.name in supplier_warehouses
					data.append(
						{
							"mould_set_item": ps.item,
							"mould_set": ps.name,
							"warehouse": wh.name,
							"is_supplier_warehouse": _("Yes") if is_supp else _("No"),
							"complete_sets_available": complete_sets,
							"component_item": c.component_item,
							"component_name": c.component_name,
							"required_qty": req_qty,
							"actual_qty": actual_qty,
							"loose_qty": loose_qty,
							"uom": c.uom,
							"drawing_no": c.drawing_no,
							"drawing_rev_no": c.drawing_rev_no,
						}
					)

	return data
