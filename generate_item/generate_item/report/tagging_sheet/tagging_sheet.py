# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{
			"label": _("PO No"),
			"fieldname": "po_no",
			"fieldtype": "Link",
			"options": "Purchase Order",
			"width": 160,
		},
		{
			"label": _("Branch"),
			"fieldname": "branch",
			"fieldtype": "Link",
			"options": "Branch",
			"width": 80,
		},
		{
			"label": _("PO Line"),
			"fieldname": "po_line_no",
			"fieldtype": "Int",
			"width": 80,
		},
		{
			"label": _("Batch No"),
			"fieldname": "batch_no",
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"label": _("Item Code"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 190,
		},
		{
			"label": _("Description"),
			"fieldname": "description",
			"fieldtype": "Data",
			"width": 240,
		},
		{
			"label": _("PO Qty"),
			"fieldname": "qty",
			"fieldtype": "Float",
			"width": 90,
		},
		{
			"label": _("UOM"),
			"fieldname": "uom",
			"fieldtype": "Link",
			"options": "UOM",
			"width": 80,
		},
		{
			"label": _("PO Qty (Stock UOM)"),
			"fieldname": "stock_qty",
			"fieldtype": "Float",
			"width": 140,
		},
		{
			"label": _("Stock UOM"),
			"fieldname": "stock_uom",
			"fieldtype": "Link",
			"options": "UOM",
			"width": 100,
		},
		# ---------- Item Location ----------
		{
			"label": _("Item Location"),
			"fieldname": "location",
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"label": _("Balance Qty"),
			"fieldname": "actual_qty",
			"fieldtype": "Float",
			"width": 160,
		},
	]


def get_conditions(filters):
	"""Build WHERE clause; returns (condition_str, values_dict)."""
	conditions = ["po.docstatus < 2"]
	values = {}

	if filters.get("from_date"):
		conditions.append("po.transaction_date >= %(from_date)s")
		values["from_date"] = filters.from_date

	if filters.get("to_date"):
		conditions.append("po.transaction_date <= %(to_date)s")
		values["to_date"] = filters.to_date

	if filters.get("purchase_order"):
		conditions.append("po.name = %(purchase_order)s")
		values["purchase_order"] = filters.purchase_order


	if filters.get("branch"):
		conditions.append("po.branch = %(branch)s")
		values["branch"] = filters.branch

	if filters.get("item_code"):
		conditions.append("poi.item_code = %(item_code)s")
		values["item_code"] = filters.item_code

	if filters.get("batch_no"):
		conditions.append("poi.custom_batch_no = %(batch_no)s")
		values["batch_no"] = filters.batch_no

	return " AND ".join(conditions), values


def get_data(filters):
	conditions, values = get_conditions(filters)

	query = """
		SELECT
			po.name                          AS po_no,
			po.branch,
			poi.po_line_no,
			poi.custom_batch_no              AS batch_no,
			poi.item_code,
			poi.description,
			poi.qty,
			poi.uom,
			poi.stock_qty,
			poi.stock_uom,

			/*
			  Location: only populate when at least one of warehouse_1 or
			  warehouse_2 has store_warehouse OR raw_material_warehouse = 1.
			  If BOTH warehouses have all checkboxes OFF -> NULL.
			*/
			CASE
				WHEN (
					wh1.store_warehouse           = 1
					OR wh1.raw_material_warehouse = 1
					OR wh2.store_warehouse        = 1
					OR wh2.raw_material_warehouse = 1
				) THEN il.location
				ELSE NULL
			END                              AS location,

			/*
			  Balance Qty: total actual_qty across BOTH warehouses from Item
			  Location (warehouse_1 + warehouse_2) for this item.
			  IFNULL ensures a mis	sing Bin row contributes 0, not NULL.
			*/
			IFNULL(bin_wh1.actual_qty, 0)
				+ IFNULL(bin_wh2.actual_qty, 0) AS actual_qty

		FROM `tabPurchase Order` po
		INNER JOIN `tabPurchase Order Item` poi
			ON poi.parent = po.name

		/*
		  Item Location: match on item_code + branch.
		  LEFT JOIN so PO rows still appear even without an Item Location record
		  (location and actual_qty will be NULL / 0 in that case).
		*/
		LEFT JOIN `tabItem Location` il
			ON  il.item   = poi.item_code
			AND il.branch = po.branch

		/* Warehouse master for warehouse_1 — read store/raw_material checkboxes */
		LEFT JOIN `tabWarehouse` wh1
			ON  wh1.name     = il.warehouse_1
			AND wh1.disabled = 0

		/* Warehouse master for warehouse_2 — read store/raw_material checkboxes */
		LEFT JOIN `tabWarehouse` wh2
			ON  wh2.name     = il.warehouse_2
			AND wh2.disabled = 0

		/* Live Bin balance for warehouse_1 */
		LEFT JOIN `tabBin` bin_wh1
			ON  bin_wh1.item_code = poi.item_code
			AND bin_wh1.warehouse = il.warehouse_1

		/* Live Bin balance for warehouse_2 */
		LEFT JOIN `tabBin` bin_wh2
			ON  bin_wh2.item_code = poi.item_code
			AND bin_wh2.warehouse = il.warehouse_2

		WHERE {conditions}
		ORDER BY po.transaction_date DESC, po.name
	""".format(conditions=conditions)

	return frappe.db.sql(query, values, as_dict=True)