# Copyright (c) 2025, Finbyz and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"label": "Transaction Date", "fieldname": "transaction_date", "fieldtype": "Date", "width": 120},
		{"label": "Customer Name", "fieldname": "customer_name", "fieldtype": "Data", "width": 180},
		{"label": "BOM", "fieldname": "bom", "fieldtype": "Link", "options": "BOM", "width": 140},
		{"label": "Item Code", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 150},
		{"label": "Item Description", "fieldname": "description", "fieldtype": "Data", "width": 250},
		 {"label": "Batch No", "fieldname": "custom_batch_no", "fieldtype": "Data", "width": 140},
		{"label": "Sales Order", "fieldname": "sales_order", "fieldtype": "Link", "options": "Sales Order", "width": 150},
		{"label": "Status", "fieldname": "bom_status", "fieldtype": "Data", "width": 110},
		{"label": "Production Plan", "fieldname": "production_plan", "fieldtype": "Link", "options": "Production Plan", "width": 160},
		{"label": "Production Plan Status", "fieldname": "production_plan_status", "fieldtype": "Data", "width": 170},
		{"label": "Customer PO No", "fieldname": "po_no", "fieldtype": "Data", "width": 140},
		{"label": "Item Qty", "fieldname": "so_qty", "fieldtype": "Int", "width": 100},
	]


def get_conditions(filters):
	conditions = ["so.docstatus = 1"]
	values = {}

	if filters.get("sales_order"):
		conditions.append("so.name = %(sales_order)s")
		values["sales_order"] = filters.get("sales_order")

	if filters.get("branch"):
		conditions.append("so.branch = %(branch)s")
		values["branch"] = filters.get("branch")

	if filters.get("item_code"):
		conditions.append("soi.item_code = %(item_code)s")
		values["item_code"] = filters.get("item_code")

	if filters.get("batch"):
		conditions.append("soi.custom_batch_no = %(batch)s")
		values["batch"] = filters.get("batch")

	if filters.get("from_date"):
		conditions.append("so.transaction_date >= %(from_date)s")
		values["from_date"] = filters.get("from_date")

	if filters.get("to_date"):
		conditions.append("so.transaction_date <= %(to_date)s")
		values["to_date"] = filters.get("to_date")

	# Filter by BOM after we compute it; we will do it via having-like wrapper
	if filters.get("bom"):
		conditions.append("EXISTS (SELECT 1 FROM `tabBOM` b3 WHERE b3.name = %(bom)s AND (b3.sales_order = so.name OR b3.item = soi.item_code) LIMIT 1)")
		values["bom"] = filters.get("bom")

	return " AND ".join(conditions), values


def map_docstatus_to_status(docstatus):
	# ERPNext standard: 0 Draft, 1 Submitted, 2 Cancelled
	if docstatus is None:
		return None
	return {0: "Draft", 1: "Submitted", 2: "Cancelled"}.get(int(docstatus), str(docstatus))


def get_data(filters):
	if not filters.get("branch"):
		return []
	conditions_sql, values = get_conditions(filters)

	query = f"""
		SELECT
			so.transaction_date,
			so.customer_name,
			(
				SELECT b2.name
				FROM `tabBOM` b2
				WHERE (b2.sales_order = so.name AND b2.item = soi.item_code AND b2.custom_batch_no = soi.custom_batch_no)
				ORDER BY b2.modified DESC
				LIMIT 1
			) AS bom,
			soi.item_code,
			soi.description,
			so.name AS sales_order,
			soi.idx AS so_row,
			COALESCE(soi.custom_batch_no, soi.custom_batch_no) AS custom_batch_no,
			(
				SELECT b2.docstatus
				FROM `tabBOM` b2
				WHERE (b2.sales_order = so.name AND b2.item = soi.item_code AND b2.custom_batch_no = soi.custom_batch_no)
				ORDER BY b2.modified DESC
				LIMIT 1
			) AS bom_docstatus,
			(
				SELECT pp2.name
				FROM `tabProduction Plan Item` ppi2
				JOIN `tabProduction Plan` pp2 ON pp2.name = ppi2.parent
				WHERE 
					(
						ppi2.sales_order_item = soi.name
						OR (
							ppi2.item_code = soi.item_code
							AND COALESCE(ppi2.custom_batch_no, '') = COALESCE(soi.custom_batch_no, '')
							AND (ppi2.bom_no IS NULL OR ppi2.bom_no = soi.bom_no)
						)
					)
					AND ppi2.sales_order = so.name
				ORDER BY pp2.creation DESC
				LIMIT 1
			) AS production_plan,
			(
				SELECT pp2.docstatus
				FROM `tabProduction Plan Item` ppi2
				JOIN `tabProduction Plan` pp2 ON pp2.name = ppi2.parent
				WHERE 
					(
						ppi2.sales_order_item = soi.name
						OR (
							ppi2.item_code = soi.item_code
							AND COALESCE(ppi2.custom_batch_no, '') = COALESCE(soi.custom_batch_no, '')
							AND (ppi2.bom_no IS NULL OR ppi2.bom_no = soi.bom_no)
						)
					)
					AND ppi2.sales_order = so.name
				ORDER BY pp2.creation DESC
				LIMIT 1
			) AS production_plan_status,
			so.po_no,
			soi.qty AS so_qty
		FROM `tabSales Order` so
		JOIN `tabSales Order Item` soi ON soi.parent = so.name
		WHERE {conditions_sql}
		ORDER BY so.transaction_date DESC, so.name DESC, soi.idx ASC
	"""
	

	rows = frappe.db.sql(query, values=values, as_dict=True)

	# Map docstatus to human-readable status for BOM
	for row in rows:
		row["bom_status"] = map_docstatus_to_status(row.pop("bom_docstatus", None))
		row["production_plan_status"] = (
			map_docstatus_to_status(row.get("production_plan_status"))
			if row.get("production_plan") else "Not Created"
		)

	return rows
