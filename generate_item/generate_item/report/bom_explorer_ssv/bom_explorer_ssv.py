# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	data = []
	columns = get_columns()
	
	# Get parent BOM details for header columns
	parent_bom = frappe.get_doc("BOM", filters.bom)
	parent_data = {
		"custom_batch_no": parent_bom.get("custom_batch_no"),
		"sales_order": parent_bom.get("sales_order")
	}
	
	get_data(filters, data, parent_data)
	return columns, data


def get_data(filters, data, parent_data):
	get_exploded_items(filters.bom, data, parent_data)


def get_exploded_items(bom, data, parent_data, indent=0, qty=1):
	exploded_items = frappe.get_all(
		"BOM Item",
		filters={"parent": bom},
		fields=[
			"qty", 
			"bom_no", 
			"item_code", 
			"item_name", 
			"description", 
			"uom", 
			"idx",
			"custom_drawing_no",
			"custom_drawing_rev_no",
			"custom_pattern_drawing_no",
			"custom_pattern_drawing_rev_no",
			"custom_purchase_specification_no",
			"custom_purchase_specification_rev_no"
		],
		order_by="idx ASC",
	)

	for item in exploded_items:
		print(item.bom_no, indent)
		item["indent"] = indent
		data.append(
			{
				"item_code": item.item_code,
				"item_name": item.item_name,
				"indent": indent,
				"bom_level": indent,
				"bom": item.bom_no,
				"qty": item.qty * qty,
				"uom": item.uom,
				"description": item.description,
				"custom_batch_no": parent_data.get("custom_batch_no"),
				"sales_order": parent_data.get("sales_order"),
				"custom_drawing_no": item.get("custom_drawing_no"),
				"custom_drawing_rev_no": item.get("custom_drawing_rev_no"),
				"custom_pattern_drawing_no": item.get("custom_pattern_drawing_no"),
				"custom_pattern_drawing_rev_no": item.get("custom_pattern_drawing_rev_no"),
				"custom_purchase_specification_no": item.get("custom_purchase_specification_no"),
				"custom_purchase_specification_rev_no": item.get("custom_purchase_specification_rev_no"),
			}
		)
		if item.bom_no:
			get_exploded_items(item.bom_no, data, parent_data, indent=indent + 1, qty=item.qty)


def get_columns():
	return [
		{
			"label": _("Item Code"),
			"fieldtype": "Link",
			"fieldname": "item_code",
			"width": 300,
			"options": "Item",
		},
		{
			"label": _("Item Name"), 
			"fieldtype": "data", 
			"fieldname": "item_name", 
			"width": 100
		},
		{
			"label": _("BOM"), 
			"fieldtype": "Link", 
			"fieldname": "bom", 
			"width": 150, 
			"options": "BOM"
		},
		{
			"label": _("Qty"), 
			"fieldtype": "data", 
			"fieldname": "qty", 
			"width": 100
		},
		{
			"label": _("UOM"), 
			"fieldtype": "data", 
			"fieldname": "uom", 
			"width": 100
		},
		{
			"label": _("BOM Level"), 
			"fieldtype": "Int", 
			"fieldname": "bom_level", 
			"width": 100
		},
		{
			"label": _("Standard Description"),
			"fieldtype": "data",
			"fieldname": "description",
			"width": 150,
		},
		# New columns added below
		{
			"label": _("Batch No"),
			"fieldtype": "data",
			"fieldname": "custom_batch_no",
			"width": 150,
		},
		{
			"label": _("Sales Order"),
			"fieldtype": "Link",
			"fieldname": "sales_order",
			"width": 150,
			"options": "Sales Order",
		},
		{
			"label": _("Drawing No"),
			"fieldtype": "data",
			"fieldname": "custom_drawing_no",
			"width": 150,
		},
		{
			"label": _("Drawing Rev No"),
			"fieldtype": "data",
			"fieldname": "custom_drawing_rev_no",
			"width": 120,
		},
		{
			"label": _("Pattern Drawing No"),
			"fieldtype": "data",
			"fieldname": "custom_pattern_drawing_no",
			"width": 150,
		},
		{
			"label": _("Pattern Drawing Rev No"),
			"fieldtype": "data",
			"fieldname": "custom_pattern_drawing_rev_no",
			"width": 150,
		},
		{
			"label": _("Purchase Specification No"),
			"fieldtype": "data",
			"fieldname": "custom_purchase_specification_no",
			"width": 180,
		},
		{
			"label": _("Purchase Specification Rev. No"),
			"fieldtype": "data",
			"fieldname": "custom_purchase_specification_rev_no",
			"width": 200,
		},
	]