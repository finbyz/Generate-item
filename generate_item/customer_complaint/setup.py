# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def get_complaint_custom_fields():
	return {
		"Issue": [
			# =========================================================================
			# SECTION 1: Complaint & Order Information
			# Unified 2-column card placed right after 'description' so user sees it upfront!
			# =========================================================================
			{
				"fieldname": "sb_complaint_details",
				"label": "Complaint and Order Details",
				"fieldtype": "Section Break",
				"insert_after": "description",
				"module": "Generate Item",
			},
			{
				"fieldname": "custom_complaint_ref_no",
				"label": "Complaint Reference No (CCR No)",
				"fieldtype": "Data",
				"bold": 1,
				"insert_after": "sb_complaint_details",
				"in_list_view": 1,
				"in_standard_filter": 1,
				"module": "Generate Item",
			},
			{
				"fieldname": "custom_complaint_status",
				"label": "Complaint Status",
				"fieldtype": "Select",
				"options": "Open\nAction in Progress\nClose",
				"default": "Open",
				"bold": 1,
				"insert_after": "custom_complaint_ref_no",
				"in_list_view": 1,
				"in_standard_filter": 1,
				"module": "Generate Item",
			},
			{
				"fieldname": "custom_complaint_reg_date",
				"label": "Complaint Registration Date",
				"fieldtype": "Date",
				"insert_after": "custom_complaint_status",
				"in_list_view": 1,
				"in_standard_filter": 1,
				"module": "Generate Item",
			},
			{
				"fieldname": "cb_complaint_details",
				"fieldtype": "Column Break",
				"insert_after": "custom_complaint_reg_date",
				"module": "Generate Item",
			},
			{
				"fieldname": "custom_sales_order",
				"label": "Sales Order",
				"fieldtype": "Link",
				"options": "Sales Order",
				"insert_after": "cb_complaint_details",
				"in_standard_filter": 1,
				"module": "Generate Item",
			},
			{
				"fieldname": "custom_fs_number",
				"label": "FS Number",
				"fieldtype": "Data",
				"insert_after": "custom_sales_order",
				"module": "Generate Item",
			},
			{
				"fieldname": "custom_project_name",
				"label": "Project",
				"fieldtype": "Data",
				"insert_after": "custom_fs_number",
				"module": "Generate Item",
			},
			{
				"fieldname": "custom_site",
				"label": "Site / Location",
				"fieldtype": "Data",
				"insert_after": "custom_project_name",
				"in_standard_filter": 1,
				"module": "Generate Item",
			},

			# =========================================================================
			# SECTION 2: Valve and Product Details
			# Left: Valve specifications (Model, Type, Size, Class, MOC, Qty)
			# Right: Serial numbers & Actuator specifications
			# =========================================================================
			{
				"fieldname": "sb_valve_product",
				"label": "Valve and Product Details",
				"fieldtype": "Section Break",
				"insert_after": "custom_site",
				"module": "Generate Item",
			},
			{
				"fieldname": "custom_valve",
				"label": "Valve",
				"fieldtype": "Data",
				"insert_after": "sb_valve_product",
				"module": "Generate Item",
			},
			{
				"fieldname": "custom_valve_type",
				"label": "Valve Type",
				"fieldtype": "Data",
				"insert_after": "custom_valve",
				"module": "Generate Item",
			},
			{
				"fieldname": "custom_valve_size",
				"label": "Valve Size",
				"fieldtype": "Data",
				"insert_after": "custom_valve_type",
				"module": "Generate Item",
			},
			{
				"fieldname": "custom_valve_class",
				"label": "Valve Class / Rating",
				"fieldtype": "Data",
				"insert_after": "custom_valve_size",
				"module": "Generate Item",
			},
			{
				"fieldname": "custom_moc",
				"label": "Material of Construction (MOC)",
				"fieldtype": "Data",
				"insert_after": "custom_valve_class",
				"module": "Generate Item",
			},
			{
				"fieldname": "custom_qty",
				"label": "Quantity",
				"fieldtype": "Data",
				"insert_after": "custom_moc",
				"module": "Generate Item",
			},
			{
				"fieldname": "cb_valve_product",
				"fieldtype": "Column Break",
				"insert_after": "custom_qty",
				"module": "Generate Item",
			},
			{
				"fieldname": "custom_valve_serial_no",
				"label": "Valve Serial Nos.",
				"fieldtype": "Small Text",
				"insert_after": "cb_valve_product",
				"module": "Generate Item",
			},
			{
				"fieldname": "custom_actuator_make",
				"label": "Actuator Make",
				"fieldtype": "Data",
				"insert_after": "custom_valve_serial_no",
				"module": "Generate Item",
			},
			{
				"fieldname": "custom_actuator_serial_no",
				"label": "Actuator Serial No",
				"fieldtype": "Data",
				"insert_after": "custom_actuator_make",
				"module": "Generate Item",
			},

			# =========================================================================
			# SECTION 3: Responsibility and Complaint Analysis
			# Left: Nature of Complaint (Defect description)
			# Right: Responsible Dept, Action Taken By, Progress Updated By
			# =========================================================================
			{
				"fieldname": "sb_resp_analysis",
				"label": "Responsibility and Complaint Analysis",
				"fieldtype": "Section Break",
				"insert_after": "custom_actuator_serial_no",
				"module": "Generate Item",
			},
			{
				"fieldname": "custom_nature_of_complaint",
				"label": "Nature of Complaint / Defect",
				"fieldtype": "Small Text",
				"insert_after": "sb_resp_analysis",
				"module": "Generate Item",
			},
			{
				"fieldname": "cb_resp_analysis",
				"fieldtype": "Column Break",
				"insert_after": "custom_nature_of_complaint",
				"module": "Generate Item",
			},
			{
				"fieldname": "custom_responsible_department",
				"label": "Responsible Department",
				"fieldtype": "Data",
				"insert_after": "cb_resp_analysis",
				"in_standard_filter": 1,
				"module": "Generate Item",
			},
			{
				"fieldname": "custom_action_taken_by",
				"label": "Action By",
				"fieldtype": "Data",
				"insert_after": "custom_responsible_department",
				"module": "Generate Item",
			},
			{
				"fieldname": "custom_progress_updated_by",
				"label": "Progress Updated By",
				"fieldtype": "Data",
				"read_only": 1,
				"insert_after": "custom_action_taken_by",
				"module": "Generate Item",
			},

			# =========================================================================
			# SECTION 4: Action Taken and Closure
			# Left: Action Date & Remarks
			# Right: Final Closure Remarks, Closure Date (conditional), Closed By (conditional)
			# =========================================================================
			{
				"fieldname": "sb_action_closure",
				"label": "Action Taken and Closure",
				"fieldtype": "Section Break",
				"insert_after": "custom_progress_updated_by",
				"module": "Generate Item",
			},
			{
				"fieldname": "custom_action_date",
				"label": "Action Date",
				"fieldtype": "Date",
				"insert_after": "sb_action_closure",
				"module": "Generate Item",
			},
			{
				"fieldname": "custom_action_remarks",
				"label": "Action Decided / Remarks",
				"fieldtype": "Small Text",
				"insert_after": "custom_action_date",
				"module": "Generate Item",
			},
			{
				"fieldname": "cb_action_closure",
				"fieldtype": "Column Break",
				"insert_after": "custom_action_remarks",
				"module": "Generate Item",
			},
			{
				"fieldname": "custom_final_action_remarks",
				"label": "Final Status / Closure Remarks",
				"fieldtype": "Small Text",
				"insert_after": "cb_action_closure",
				"module": "Generate Item",
			},
			{
				"fieldname": "custom_closure_date",
				"label": "Closure Date",
				"fieldtype": "Date",
				"read_only": 1,
				"depends_on": "eval:doc.custom_complaint_status=='Close'",
				"insert_after": "custom_final_action_remarks",
				"module": "Generate Item",
			},
			{
				"fieldname": "custom_closure_by",
				"label": "Closed By",
				"fieldtype": "Link",
				"options": "User",
				"read_only": 1,
				"depends_on": "eval:doc.custom_complaint_status=='Close'",
				"insert_after": "custom_closure_date",
				"module": "Generate Item",
			},

			# =========================================================================
			# SECTION 5: Visit Schedule and Evidence
			# Left: SSV Visiting Engineer, Schedule Date, Visit Notes
			# Right: Photo Evidence, MOM Attachment
			# =========================================================================
			{
				"fieldname": "sb_visit_schedule",
				"label": "Visit Schedule and Evidence",
				"fieldtype": "Section Break",
				"insert_after": "custom_closure_by",
				"module": "Generate Item",
			},
			{
				"fieldname": "custom_ssv_visiting_engineer",
				"label": "SSV Visiting Engineer",
				"fieldtype": "Data",
				"insert_after": "sb_visit_schedule",
				"module": "Generate Item",
			},
			{
				"fieldname": "custom_visit_schedule_date",
				"label": "SSV Visiting Schedule Date",
				"fieldtype": "Date",
				"insert_after": "custom_ssv_visiting_engineer",
				"module": "Generate Item",
			},
			{
				"fieldname": "custom_visit_schedule_notes",
				"label": "Visit Schedule / Notes",
				"fieldtype": "Small Text",
				"insert_after": "custom_visit_schedule_date",
				"module": "Generate Item",
			},
			{
				"fieldname": "cb_visit_schedule",
				"fieldtype": "Column Break",
				"insert_after": "custom_visit_schedule_notes",
				"module": "Generate Item",
			},
			{
				"fieldname": "custom_photo_evidence",
				"label": "Photo Evidence",
				"fieldtype": "Attach Image",
				"insert_after": "cb_visit_schedule",
				"module": "Generate Item",
			},
			{
				"fieldname": "custom_mom_attachment",
				"label": "MOM Attachment",
				"fieldtype": "Attach",
				"insert_after": "custom_photo_evidence",
				"module": "Generate Item",
			},

			# =========================================================================
			# SECTION 6: Complaint Progress History Child Table
			# Full-width append-only audit trail
			# =========================================================================
			{
				"fieldname": "sb_progress_history",
				"label": "Complaint Progress History",
				"fieldtype": "Section Break",
				"insert_after": "custom_mom_attachment",
				"module": "Generate Item",
			},
			{
				"fieldname": "custom_progress_history",
				"label": "Progress History",
				"fieldtype": "Table",
				"options": "Issue Progress Update",
				"insert_after": "sb_progress_history",
				"module": "Generate Item",
			},
		]
	}


def setup_customer_complaint():
	"""
	Sets up custom fields and configurations required for Customer Complaint Management.
	Cleans up obsolete fields, organizes sections, and enforces is_system_generated = 0.
	"""
	# Clean up removed/obsolete fields
	obsolete_fields = [
		"Issue-custom_so_number",
		"Issue-sb_order_site",
		"Issue-cb_order_site",
	]
	for field in obsolete_fields:
		if frappe.db.exists("Custom Field", field):
			frappe.db.delete("Custom Field", {"name": field})

	# Hide standard ERPNext core 'project' Link field to prevent duplicate project fields
	if not frappe.db.exists("Property Setter", "Issue-project-hidden"):
		frappe.get_doc({
			"doctype": "Property Setter",
			"doc_type": "Issue",
			"doctype_or_field": "DocField",
			"field_name": "project",
			"property": "hidden",
			"value": "1",
			"property_type": "Check",
			"module": "Generate Item",
			"is_system_generated": 0,
		}).insert(ignore_permissions=True)

	# Disable quick_entry on Issue DocType so it always opens full form directly
	if not frappe.db.exists("Property Setter", "Issue-main-quick_entry"):
		frappe.get_doc({
			"doctype": "Property Setter",
			"doc_type": "Issue",
			"doctype_or_field": "DocType",
			"property": "quick_entry",
			"value": "0",
			"property_type": "Check",
			"module": "Generate Item",
			"is_system_generated": 0,
		}).insert(ignore_permissions=True)

	custom_fields = get_complaint_custom_fields()
	create_custom_fields(custom_fields, update=True)

	frappe.db.sql(
		"""
		UPDATE `tabCustom Field`
		SET is_system_generated = 0
		WHERE dt = 'Issue' AND module = 'Generate Item'
		"""
	)
	frappe.clear_cache(doctype="Issue")
