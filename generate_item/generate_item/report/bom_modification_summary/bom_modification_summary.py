# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{
			"label": "Batch No Ref",
			"fieldname": "batch_no_ref",
			"fieldtype": "Link",
			"options": "Batch",
			"width": 150,
		},
		{
			"label": "BOM ID",
			"fieldname": "bom",
			"fieldtype": "Link",
			"options": "BOM",
			"width": 220,
		},
		{
			"label": "Submitted On",
			"fieldname": "submitted_on",
			"fieldtype": "Datetime",
			"width": 160,
		},
		{
			"label": "Number of Modifications",
			"fieldname": "modification_count",
			"fieldtype": "Int",
			"width": 170,
		},
		{
			"label": "Last Modification ID",
			"fieldname": "last_modification_id",
			"fieldtype": "Link",
			"options": "Bom Modification Request",
			"width": 220,
		},
		{
			"label": "Last Modification Date",
			"fieldname": "last_modification_date",
			"fieldtype": "Datetime",
			"width": 170,
		},
		{
			"label": "Last Modification Approved On",
			"fieldname": "last_modification_approved_on",
			"fieldtype": "Datetime",
			"width": 190,
		},
	]


def get_data(filters):
	conditions = get_conditions(filters)

	data = frappe.db.sql(
		f"""
		SELECT
			bmr.batch_no_ref            AS batch_no_ref,
			bmr.bom                     AS bom,
			agg.submitted_on            AS submitted_on,
			agg.modification_count      AS modification_count,
			bmr.name                    AS last_modification_id,
			bmr.creation                AS last_modification_date,
			sci.approved_on             AS last_modification_approved_on
		FROM `tabBom Modification Request` bmr
		INNER JOIN (
			SELECT
				bom,
				MIN(creation) AS submitted_on,
				COUNT(name)   AS modification_count,
				MAX(creation) AS max_creation
			FROM `tabBom Modification Request`
			WHERE docstatus = 1
			GROUP BY bom
		) agg ON agg.bom = bmr.bom AND agg.max_creation = bmr.creation
		LEFT JOIN (
			SELECT
				parent,
				MAX(modification_time) AS approved_on
			FROM `tabState Change Items`
			WHERE workflow_state = 'Approved'
			GROUP BY parent
		) sci ON sci.parent = bmr.name
		WHERE bmr.docstatus = 1 {conditions}
		ORDER BY bmr.creation DESC
		""",
		filters,
		as_dict=1,
	)

	return data


def get_conditions(filters):
	conditions = ""

	if filters.get("bom"):
		conditions += " AND bmr.bom = %(bom)s"

	if filters.get("batch_no_ref"):
		conditions += " AND bmr.batch_no_ref = %(batch_no_ref)s"

	if filters.get("from_date"):
		conditions += " AND bmr.creation >= %(from_date)s"

	if filters.get("to_date"):
		conditions += " AND bmr.creation <= %(to_date)s"

	return conditions