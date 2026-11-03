# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	columns = [
		{"label": _("Serial No"), "fieldname": "serial_no", "fieldtype": "Link", "options": "Serial No", "width": 160},
		{"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 140},
		{"label": _("Pattern Set in Components Table"), "fieldname": "components_pattern_set", "fieldtype": "Link", "options": "Pattern Set", "width": 220},
		{"label": _("Pattern Set on Serial No"), "fieldname": "serial_pattern_set", "fieldtype": "Link", "options": "Pattern Set", "width": 220},
		{"label": _("Serial Status"), "fieldname": "status", "fieldtype": "Data", "width": 110},
		{"label": _("Serial Warehouse"), "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 140},
		{"label": _("Issue / Discrepancy"), "fieldname": "issue", "fieldtype": "Data", "width": 320},
	]

	data = []

	# 1. Component rows in submitted sets pointing to a serial, but Serial No doesn't point to that Pattern Set
	mismatches_from_comp = frappe.db.sql(
		"""
		SELECT 
			c.serial_no,
			c.item_code,
			c.parent as components_pattern_set,
			s.custom_pattern_set as serial_pattern_set,
			s.status,
			s.warehouse
		FROM `tabPattern Set Component` c
		INNER JOIN `tabPattern Set` ps ON ps.name = c.parent
		LEFT JOIN `tabSerial No` s ON s.name = c.serial_no
		WHERE ps.docstatus = 1
		  AND c.serial_no IS NOT NULL 
		  AND c.serial_no != ''
		  AND (s.custom_pattern_set IS NULL OR s.custom_pattern_set != c.parent)
		""",
		as_dict=True,
	)

	for row in mismatches_from_comp:
		if not row.serial_pattern_set:
			row["issue"] = _("Attached in Pattern Set components table, but Serial No field is blank")
		else:
			row["issue"] = _("Attached in Pattern Set {0}, but Serial No points to {1}").format(
				row.components_pattern_set, row.serial_pattern_set
			)
		data.append(row)

	# 2. Serial No points to a submitted Pattern Set, but is not in that Pattern Set's components table
	mismatches_from_sn = frappe.db.sql(
		"""
		SELECT 
			s.name as serial_no,
			s.item_code,
			NULL as components_pattern_set,
			s.custom_pattern_set as serial_pattern_set,
			s.status,
			s.warehouse
		FROM `tabSerial No` s
		INNER JOIN `tabPattern Set` ps ON ps.name = s.custom_pattern_set
		LEFT JOIN `tabPattern Set Component` c ON (c.parent = s.custom_pattern_set AND c.serial_no = s.name)
		WHERE ps.docstatus = 1
		  AND s.custom_pattern_set IS NOT NULL 
		  AND s.custom_pattern_set != ''
		  AND c.name IS NULL
		""",
		as_dict=True,
	)

	for row in mismatches_from_sn:
		row["issue"] = _("Serial No points to {0}, but is missing from its components table").format(
			row.serial_pattern_set
		)
		data.append(row)

	# 3. Duplicate attached serials across component rows of submitted sets
	duplicate_rows = frappe.db.sql(
		"""
		SELECT 
			c.serial_no,
			c.item_code,
			GROUP_CONCAT(DISTINCT c.parent) as components_pattern_set,
			s.custom_pattern_set as serial_pattern_set,
			s.status,
			s.warehouse,
			COUNT(c.name) as row_count
		FROM `tabPattern Set Component` c
		INNER JOIN `tabPattern Set` ps ON ps.name = c.parent
		LEFT JOIN `tabSerial No` s ON s.name = c.serial_no
		WHERE ps.docstatus = 1
		  AND c.serial_no IS NOT NULL 
		  AND c.serial_no != ''
		GROUP BY c.serial_no
		HAVING COUNT(c.name) > 1
		""",
		as_dict=True,
	)

	for row in duplicate_rows:
		row["issue"] = _("Serial No appears in {0} different component rows across sets: {1}").format(
			row.row_count, row.components_pattern_set
		)
		data.append(row)

	return columns, data
