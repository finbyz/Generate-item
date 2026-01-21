# Copyright (c) 2013, Finbyz Tech Pvt Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt
from collections import defaultdict

def execute(filters=None):
	columns, data = [], []
	columns = get_columns(filters)
	data  = get_data(filters)

	return columns, data

def get_data(filters):
	conditions = get_condition(filters)
	final_dict = defaultdict(list)
	# data = frappe.db.sql("""
	# 	select
	# 		i.image, i.name as item, i.unit_buying_price,i.unit_selling_price,su.supplier,su.supplier_part_no as vendor_item_number,i.sort_ord as sort, i.item_group, i.description, bin.actual_qty as in_stock, i.master_case_qty as master_case, i.case_qty,i.disabled, i.shelf_location as location, ir.warehouse_reorder_level as re_order_point, ir.warehouse_reorder_qty as re_order_quantity
	# 	from
	# 		`tabItem` as i
	# 		LEFT JOIN `tabItem Supplier` as su ON su.parent = i.name
	# 		LEFT JOIN `tabItem Reorder` as ir ON ir.parent = i.name
	# 		LEFT JOIN `tabBin` as bin ON bin.item_code = i.name
	# 	where
	# 		i.disabled = 0{}
	# """.format(conditions), as_dict =1) i.unit_buying_price,i.unit_selling_price,
	data = frappe.db.sql("""
		select
			i.image, i.name as item,su.supplier,su.supplier_part_no as vendor_item_number, i.item_group, i.description, bin.actual_qty as in_stock,i.disabled, ir.warehouse_reorder_level as re_order_point, ir.warehouse_reorder_qty as re_order_quantity
		from
			`tabItem` as i
			LEFT JOIN `tabItem Supplier` as su ON su.parent = i.name
			LEFT JOIN `tabItem Reorder` as ir ON ir.parent = i.name
			LEFT JOIN `tabBin` as bin ON bin.item_code = i.name
		where
			i.disabled = 0{}
	""".format(conditions), as_dict =1)
	for d in data:
		if d['image']:
			d['image'] = "<div><img src='{}';></div>".format(d['image'])
		else:
			d['image'] = "<p>No Image</p>"
		# if d['item']:
		# 	buy = frappe.db.get_value("Item Price",{"item_code":d['item'],"buying":1},"price_list_rate")
		# 	sell = frappe.db.get_value("Item Price",{"item_code":d['item'],"selling":1},"price_list_rate")
		# if buy:
		# 	d['buying_unit_price'] = buy
		# 	d['buying_case_price'] = ('%.2f'%flt(d['case_qty'] * buy))
		# if sell:
		# 	d['selling_unit_price'] = sell
		# 	d['selling_case_price'] = ('%.2f'%flt(d['case_qty'] * sell))
		if d.disabled:
			d['status'] = "Disabled"
		else:
			d['status'] = "Enabled"

	# for d in data:
	# 	if d.buying_unit_price:
	# 		final_dict[d.item].append({'buying_unit_price':d.buying_unit_price})
	# 	if d.selling_unit_price:
	# 		final_dict[d.item].append({'selling_unit_price':d.selling_unit_price})
	# 	final_dict[d.item].append({'image': d.image})
	# 	final_dict[d.item].append({'supplier': d.supplier})
	# 	final_dict[d.item].append({'description': d.description})
	# 	final_dict[d.item].append({'in_stock': d.in_stock})
	# 	final_dict[d.item].append({'master_case': d.master_case})
	# 	final_dict[d.item].append({'case_qty': d.case_qty})

		#<div><img src="/files/foam_cones.jpg" style="width:200px";>.format(d['image'])
	# frappe.msgprint(str(data))
	# temp = defaultdict(list)
	# for elem in data:
	# 	temp[elem['item']].extend(elem['buying_unit_price']) 
	# for elem in final_dict: 
	# 	temp[elem['item']].extend(elem['buying_unit_price']) 
	
	# Output = [{"buying_unit_price":y, "item":x} for x, y in temp.items()] 
	# frappe.msgprint(str(Output))

	return data

def get_condition(filters):
	conditions = ""
	if filters.get("supplier"):
		conditions += " and su.supplier= '%s'" % filters["supplier"]
	if filters.get("item_code"):
		conditions += " and i.name='%s'" % filters["item_code"]
	return conditions

def get_columns(filters):

	columns = [
		{
			"label": _("Image"),
			"fieldname": "image",
			"fieldtype": "html",
			"width": 100,
		},
		{
			"label": _("Sort"),
			"fieldname": "sort",
			"fieldtype": "Int",
			"width": 70
		},
		{
			"label": _("Item"),
			"fieldname": "item",
			"fieldtype": "Link",
			"options": "Item",
			"width": 100
		},
		{
			"label": _("Vendor"),
			"fieldname": "supplier",
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 100
		},
		{
			"label": _("Category"),
			"fieldname": "item_group",
			"fieldtype": "Link",
			"options": "Item Group",
			"width": 100
		},
		{
			"label": _("Vendor Item Number"),
			"fieldname": "vendor_item_number",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Description"),
			"fieldname": "description",
			"fieldtype": "Small Text",
			"width": 120,
			"editable": True
		},
		{
			"label": _("Status"),
			"fieldname": "status",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("In Stock"),
			"fieldname": "in_stock",
			"fieldtype": "Int",
			"width": 100
		},
		{
			"label": _("Case"),
			"fieldname": "case_qty",
			"fieldtype": "Int",
			"width": 100
		},
		{
			"label": _("Master Case"),
			"fieldname": "master_case",
			"fieldtype": "Int",
			"width": 100
		},
		{
			"label": _("Buying Unit Price"),
			"fieldname": "unit_buying_price",
			"fieldtype": "Currency",
			"width": 100
		},
		# {
		# 	"label": _("Buying Case Price"),
		# 	"fieldname": "buying_case_price",
		# 	"fieldtype": "Currency",
		# 	"width": 100
		# },
		{
			"label": _("Selling Unit Price"),
			"fieldname": "unit_selling_price",
			"fieldtype": "Currency",
			"width": 100
		},
		{
			"label": _("Re-Order Point"),
			"fieldname": "re_order_point",
			"fieldtype": "Int",
			"width": 100
		},
		{
			"label": _("Re-Order Quantity"),
			"fieldname": "re_order_quantity",
			"fieldtype": "Int",
			"width": 100
		},
		{
			"label": _("Location"),
			"fieldname": "location",
			"fieldtype": "Data",
			"width": 100
		},
		# {
		# 	"label": _("Selling Case Price"),
		# 	"fieldname": "selling_case_price",
		# 	"fieldtype": "Currency",
		# 	"width": 100
		# },
	]

	return columns