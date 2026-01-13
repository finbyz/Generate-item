# Copyright (c) 2025, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data

def get_columns():
	columns = [
		{
			"label": _("Sales Order"),
			"fieldname": "sales_order",
			"fieldtype": "Link",
			"options": "Sales Order",
			"width": 150
		},
		{
			"label": _("Branch"),
			"fieldname": "branch",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Order Date"),
			"fieldname": "order_date",
			"fieldtype": "Date",
			"width": 100
		},
		{
			"label": _("Order Delivery Date"),
			"fieldname": "order_delivery_date",
			"fieldtype": "Date",
			"width": 120
		},
		{
			"label": _("Customer Name"),
			"fieldname": "customer_name",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"label": _("Customer PO Number"),
			"fieldname": "customer_po_number",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": _("Customer PO Date"),
			"fieldname": "customer_po_date",
			"fieldtype": "Date",
			"width": 100
		},
		{
			"label": _("Liquidate Damage"),
			"fieldname": "custom_liquidate_damage",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": _("Order Status"),
			"fieldname": "order_status",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": _("Approved Date"),
			"fieldname": "approved_on",
			"fieldtype": "Date",
			"width": 100
		},
		{
			"label": _("Approved By"),
			"fieldname": "approved_by",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": _("Payment Term"),
			"fieldname": "custom_payment_terms",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Mode Of Dispatch"),
			"fieldname": "mode_of_dispatch",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": _("Freight Charges"),
			"fieldname": "custom_freight_charges",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Price Basis"),
			"fieldname": "price_basis",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Order Currency"),
			"fieldname": "order_currency",
			"fieldtype": "Data",
			"width": 80
		},
		{
			"label": _("Exchange rate"),
			"fieldname": "exchange_rate",
			"fieldtype": "Float",
			"width": 100
		},
		{
			"label": _("Item ID"),
			"fieldname": "item_id",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Order Line Index"),
			"fieldname": "order_line_index",
			"fieldtype": "Int",
			"width": 80
		},
		{
			"label": _("Batch Number"),
			"fieldname": "batch_number",
			"fieldtype": "Link",
			"options": "Batch",
			"width": 100
		},
		{
			"label": _("Item Code"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 150
		},
		{
			"label": _("Item Name"),
			"fieldname": "item_name",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"label": _("Item Description"),
			"fieldname": "item_description",
			"fieldtype": "Text",
			"width": 200
		},
		{
			"label": _("Item Group"),
			"fieldname": "item_group",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("PO Line No."),
			"fieldname": "po_line_no",
			"fieldtype": "Data",
			"width": 80
		},
		{
			"label": _("Tag No."),
			"fieldname": "tag_no",
			"fieldtype": "Data",
			"width": 80
		},
		{
			"label": _("Line Status"),
			"fieldname": "line_status",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Infor Ref"),
			"fieldname": "infor_ref",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Order Qty"),
			"fieldname": "order_qty",
			"fieldtype": "Float",
			"width": 80
		},
		{
			"label": _("Delivered Qty"),
			"fieldname": "delivered_qty",
			"fieldtype": "Float",
			"width": 100
		},
		{
			"label": _("Pending Qty"),
			"fieldname": "pending_qty",
			"fieldtype": "Float",
			"width": 100
		},
		{
			"label": _("Currency"),
			"fieldname": "currency",
			"fieldtype": "Data",
			"width": 80
		},
		{
			"label": _("Exchange Rate"),
			"fieldname": "item_exchange_rate",
			"fieldtype": "Float",
			"width": 100
		},
		{
			"label": _("Unit Rate"),
			"fieldname": "unit_rate",
			"fieldtype": "Currency",
			"width": 100
		},
		{
			"label": _("Item Basic Amount INR"),
			"fieldname": "item_basic_amount_inr",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"label": _("Order Amount INR"),
			"fieldname": "order_amount_inr",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"label": _("Type of Product"),
			"fieldname": "type_of_product",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": _("Valve Type"),
			"fieldname": "valve_type",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": _("Construction"),
			"fieldname": "construction",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Bore"),
			"fieldname": "bore",
			"fieldtype": "Data",
			"width": 80
		},
		{
			"label": _("Size"),
			"fieldname": "size",
			"fieldtype": "Data",
			"width": 80
		},
		{
			"label": _("Rating"),
			"fieldname": "rating",
			"fieldtype": "Data",
			"width": 80
		},
		{
			"label": _("Ends"),
			"fieldname": "ends",
			"fieldtype": "Data",
			"width": 80
		},
		{
			"label": _("End Sub type"),
			"fieldname": "end_sub_type",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Shell MOC"),
			"fieldname": "shell_moc",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Ball Moc"),
			"fieldname": "ball_moc",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Ball Facing"),
			"fieldname": "ball_facing",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Seat Ring(GUIDE) MOC"),
			"fieldname": "seat_ring_guide_moc",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": _("Seat Facing/Plating"),
			"fieldname": "seat_facing_plating",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": _("SEAT INSERT + SEAT SEAL MOC"),
			"fieldname": "seat_insert_seat_seal_moc",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"label": _("Stem MOC"),
			"fieldname": "stem_moc",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("GASKET"),
			"fieldname": "gasket",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Gland Packing + O'Ring Moc"),
			"fieldname": "gland_packing_o_ring_moc",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"label": _("Fasteners"),
			"fieldname": "fasteners",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Operator"),
			"fieldname": "operator",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Accessories"),
			"fieldname": "accessories",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": _("Special Requirement for valve"),
			"fieldname": "special_requirement_for_valve",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"label": _("QUALITY Special Requirement (NDE)"),
			"fieldname": "quality_special_requirement_nde",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"label": _("Service"),
			"fieldname": "service",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Inspection"),
			"fieldname": "inspection",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Additional Charges"),
			"fieldname": "additional_charges",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"label": _("Grand Total"),
			"fieldname": "grand_total",
			"fieldtype": "Currency",
			"width": 120
		},
	]
	return columns

def get_data(filters):
	if not filters:
		filters = {}

	data = []
	so_conditions = get_so_conditions(filters)
	so_fields = [
		"name as sales_order",
		"branch",
		"transaction_date as order_date",
		"delivery_date as order_delivery_date",
		"customer_name",
		"po_no as customer_po_number",
		"po_date as customer_po_date",
		"custom_liquidate_damage",
		"status as order_status",
		# "modified as approved_on",
		# "modified_by as approved_by",
		"currency as order_currency",
		"conversion_rate as exchange_rate",
		"payment_terms_template as payment_term",
		"custom_payment_terms",
		"custom_mode_of_dispatch",
		"custom_freight_charges",
		"custom_price_basis",
		"discount_amount",
		"grand_total",
  		"total_taxes_and_charges"
	]
	sales_orders = frappe.get_all("Sales Order", filters=so_conditions, fields=so_fields)

	for so in sales_orders:
		approval_details = get_approval_details(so.sales_order)

		# Compute freight charges from Sales Taxes and Charges for this Sales Order
		freight_charges = 0
		freight_row = frappe.db.sql(
			"""
			SELECT SUM(tax_amount) as freight_total
			FROM `tabSales Taxes and Charges`
			WHERE parent = %s
			  AND parenttype = 'Sales Order'
			  AND docstatus = 1
			  AND account_head LIKE 'Freight Charges Sales%%'
			""",
			so.sales_order,
			as_dict=True,
		)
		if freight_row and freight_row[0].freight_total:
			freight_charges = freight_row[0].freight_total or 0

		so_conditions_for_items = {"parent": so.sales_order}
		if filters.get("item_code"):
			so_conditions_for_items["item_code"] = filters.item_code
		if filters.get("batch_no"):
			so_conditions_for_items["custom_batch_no"] = filters.batch_no
		item_fields = [
			"idx as item_idx",
			"parent",
			"idx as order_line_index",
			"item_code",
			"item_name",
			"description as item_description",
			"item_group",
			"qty as order_qty",
			"delivered_qty",
			"rate as unit_rate",
			"base_amount as item_basic_amount_inr",
			"amount as order_amount_inr",
			"custom_batch_no as batch_number",
			"line_status",
			"po_line_no",
			"tag_no",
			"infor_ref",
			"custom_infor_ref",
		]
		items = frappe.get_all("Sales Order Item", filters=so_conditions_for_items, fields=item_fields, order_by="parent asc, idx asc")

		for item in items:
			item_id = f"{item.parent}-{item.item_idx}"
			item_gen = get_item_generator_attributes(item.item_code)
			type_of_product = item_gen.get("attribute_1_value") or ""
			valve_type = item_gen.get("attribute_2_value") or ""
			construction = item_gen.get("attribute_3_value") or ""
			bore = item_gen.get("attribute_4_value") or ""
			size = item_gen.get("attribute_5_value") or ""
			rating = item_gen.get("attribute_6_value") or ""
			ends = item_gen.get("attribute_7_value") or ""
			end_sub_type = item_gen.get("attribute_8_value") or ""
			shell_moc = item_gen.get("attribute_9_value") or ""
			ball_moc = item_gen.get("attribute_10_value") or ""
			ball_facing = item_gen.get("attribute_11_value") or ""
			seat_ring_guide_moc = item_gen.get("attribute_12_value") or ""
			seat_facing_plating = item_gen.get("attribute_13_value") or ""
			seat_insert_seat_seal_moc = item_gen.get("attribute_14_value") or ""
			stem_moc = item_gen.get("attribute_15_value") or ""
			gasket = item_gen.get("attribute_16_value") or ""
			gland_packing_o_ring_moc = item_gen.get("attribute_17_value") or ""
			fasteners = item_gen.get("attribute_18_value") or ""
			operator = item_gen.get("attribute_19_value") or ""
			accessories = item_gen.get("attribute_20_value") or ""
			special_requirement_for_valve = item_gen.get("attribute_21_value") or ""
			quality_special_requirement_nde = item_gen.get("attribute_22_value") or ""
			service = item_gen.get("attribute_23_value") or ""
			inspection = item_gen.get("attribute_24_value") or ""
			actual_charges = 0
			actual_tax_row = frappe.db.sql(
				"""
				SELECT SUM(tax_amount) AS actual_total
				FROM `tabSales Taxes and Charges`
				WHERE parent = %s
				AND parenttype = 'Sales Order'
				AND docstatus = 1
				AND charge_type = 'Actual'
				""",
				so.sales_order,
				as_dict=True,
			)

			if actual_tax_row and actual_tax_row[0].actual_total:
				actual_charges = actual_tax_row[0].actual_total or 0

			additional_charges = actual_charges

			calculated_grand_total = (
				(so.grand_total or 0)
				- (item.order_amount_inr or 0)
				+ (additional_charges or 0) 
				+ (so.total_taxes_and_charges or 0)
			)

			row = [
				so.sales_order,
				so.branch or "",
				so.order_date,
				so.order_delivery_date,
				so.customer_name,
				so.customer_po_number or "",
				so.customer_po_date,
				so.custom_liquidate_damage,
				so.order_status,
				# so.approved_on,
				# so.approved_by or "",
				approval_details.get("approved_on"),
				approval_details.get("approved_by") or "",
				so.custom_payment_terms or "",
				so.custom_mode_of_dispatch or "",
				so.custom_freight_charges or "",
				so.custom_price_basis or "",
				so.order_currency,
				so.exchange_rate,
				# item.item_id,
				item_id,   
				item.order_line_index,
				item.batch_number or "",
				item.item_code,
				item.item_name,
				item.item_description,
				item.item_group,
				item.po_line_no or "",
				item.tag_no or "",
				item.line_status or "",
				item.infor_ref or item.custom_infor_ref or "",
				item.order_qty,
				item.delivered_qty or 0,
				(item.order_qty or 0) - (item.delivered_qty or 0),
				so.order_currency,
				so.exchange_rate,
				item.unit_rate or 0,
				item.item_basic_amount_inr or 0,
				item.order_amount_inr or 0,
				type_of_product,
				valve_type,
				construction,
				bore,
				size,
				rating,
				ends,
				end_sub_type,
				shell_moc,
				ball_moc,
				ball_facing,
				seat_ring_guide_moc,
				seat_facing_plating,
				seat_insert_seat_seal_moc,
				stem_moc,
				gasket,
				gland_packing_o_ring_moc,
				fasteners,
				operator,
				accessories,
				special_requirement_for_valve,
				quality_special_requirement_nde,
				service,
				inspection,
				additional_charges,
				calculated_grand_total,
			]
			data.append(row)

	return data

def get_so_conditions(filters):
	conditions = {
		"docstatus": ["in", [0, 1]]  # Draft + Submitted
	}



	# Date range handling
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")

	if from_date and to_date:
		conditions["transaction_date"] = ["between", [from_date, to_date]]
	elif from_date:
		conditions["transaction_date"] = [">=", from_date]
	elif to_date:
		conditions["transaction_date"] = ["<=", to_date]

	if filters.get("customer"):
		conditions["customer"] = filters.customer
	if filters.get("branch"):
		conditions["branch"] = filters.branch
	if filters.get("sales_order"):
		conditions["name"] = filters.sales_order




	# Exclude Closed & Completed
	# conditions["status"] = ["not in", ["Closed", "Completed"]]
	# if filters.get("status"):
	# 	conditions["status"] = ["in", filters.status]
	#  status logic (important)
	if filters.get("status"):
		conditions["status"] = ["in", filters.status]
	else:
		conditions["status"] = ["not in", ["Closed", "Completed"]]



	return conditions


def get_item_generator_attributes(item_code):
	if not item_code:
		return {}

	fields = [f"attribute_{i}_value" for i in range(1, 25)]
	item_gen = frappe.db.get_value(
		"Item Generator",
		{"name": item_code},
		fields,
		as_dict=True,
	)
	return item_gen or {}


def get_approval_details(sales_order):
	approval = frappe.db.sql(
		"""
		SELECT
			username AS approved_by,
			modification_time AS approved_on
		FROM `tabState Change Items`
		WHERE parent = %s
		  AND parenttype = 'Sales Order'
		  AND workflow_state = 'Approved'
		ORDER BY modification_time DESC
		LIMIT 1
		""",
		sales_order,
		as_dict=True,
	)

	if approval:
		return approval[0]

	return {"approved_by": "", "approved_on": None}
