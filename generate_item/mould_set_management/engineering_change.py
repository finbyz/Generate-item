# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import now_datetime
from generate_item.mould_set_management.pattern_set_utils import (
	recalculate_pattern_set,
	SNAPSHOT_FIELDS_MAP,
	normalize_val,
)


def on_item_update(doc, method=None):
	"""
	Triggered when an Item is updated.
	Per v2.0 Section 2 & 4:
	If any of the 6 drawing/specification fields on Item change:
	1. Find all Pattern Set Component rows referencing this Item (including open rows).
	2. Create an auditable Pattern Set Engineering Change document.
	3. Update the Pattern Set engineering_status to 'Review Pending' without changing physical warehouse.
	"""
	if doc.is_new():
		return

	before_save = doc.get_doc_before_save()
	if not before_save:
		return

	# Check if any of the 6 fields changed
	has_change = False
	for item_f, comp_f in SNAPSHOT_FIELDS_MAP:
		old_val = normalize_val(before_save.get(item_f))
		new_val = normalize_val(doc.get(item_f))
		if old_val != new_val:
			has_change = True
			break

	if not has_change:
		return

	# Find all submitted Pattern Sets referencing this Item
	comp_rows = frappe.db.sql("""
		SELECT c.name as comp_name, c.parent as ps_name, c.serial_no,
		       ps.current_warehouse, ps.current_supplier
		FROM `tabPattern Set Component` c
		JOIN `tabPattern Set` ps ON ps.name = c.parent
		WHERE (c.item_code = %s OR c.component_item = %s)
		  AND ps.docstatus = 1
	""", (doc.name, doc.name), as_dict=True)

	if not comp_rows:
		return

	# Create Pattern Set Engineering Change document
	ec = frappe.new_doc("Pattern Set Engineering Change")
	ec.item_code = doc.name
	ec.change_date = now_datetime()
	ec.status = "Open"

	ec.old_drawing_no = before_save.get("custom_drawing_no") or ""
	ec.old_drawing_rev_no = before_save.get("custom_drawing_rev_no") or ""
	ec.old_pattern_drawing_no = before_save.get("custom_pattern_drawing_no") or ""
	ec.old_pattern_drawing_rev_no = before_save.get("custom_pattern_drawing_rev_no") or ""
	ec.old_purchase_specification_no = before_save.get("custom_purchase_specification_no") or ""
	ec.old_purchase_specification_rev_no = before_save.get("custom_purchase_specification_rev_no") or ""

	ec.new_drawing_no = doc.get("custom_drawing_no") or ""
	ec.new_drawing_rev_no = doc.get("custom_drawing_rev_no") or ""
	ec.new_pattern_drawing_no = doc.get("custom_pattern_drawing_no") or ""
	ec.new_pattern_drawing_rev_no = doc.get("custom_pattern_drawing_rev_no") or ""
	ec.new_purchase_specification_no = doc.get("custom_purchase_specification_no") or ""
	ec.new_purchase_specification_rev_no = doc.get("custom_purchase_specification_rev_no") or ""

	seen_pairs = set()
	for r in comp_rows:
		pair_key = (r.ps_name, r.comp_name)
		if pair_key in seen_pairs:
			continue
		seen_pairs.add(pair_key)

		ec.append("impacted_pattern_sets", {
			"pattern_set": r.ps_name,
			"component_row": r.comp_name,
			"serial_no": r.serial_no or "",
			"current_warehouse": r.current_warehouse or "",
			"current_supplier": r.current_supplier or "",
			"disposition": "Accept As-Is",
			"disposition_status": "Pending",
		})

	ec.flags.ignore_permissions = True
	ec.insert()

	# Recalculate each impacted Pattern Set to update engineering_status to 'Review Pending'
	affected_sets = {r.ps_name for r in comp_rows}
	for ps_name in affected_sets:
		recalculate_pattern_set(ps_name)

