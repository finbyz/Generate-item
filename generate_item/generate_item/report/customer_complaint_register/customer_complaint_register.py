# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe import _

ALLOWED_COMPLAINT_STATUSES = {"Open", "Action in Progress", "Close"}

ALLOWED_EDITABLE_FIELDS = {
	"custom_complaint_status",
	"custom_responsible_department",
	"custom_site",
	"custom_action_date",
	"custom_action_remarks",
	"custom_visit_schedule_date",
	"custom_visit_schedule_notes",
	"custom_final_action_remarks",
	"custom_ssv_visiting_engineer",
}


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = get_columns()
	conditions, query_params = get_conditions(filters)
	data = get_data(conditions, query_params)
	return columns, data


def get_columns():
	return [
		{
			"label": _("Complaint ID"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Issue",
			"width": 140,
		},
		{
			"label": _("CCR / Ref No"),
			"fieldname": "custom_complaint_ref_no",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Complaint Status ✎"),
			"fieldname": "custom_complaint_status",
			"fieldtype": "Select",
			"options": "\nOpen\nAction in Progress\nClose",
			"editable": 1,
			"width": 200,
		},
		{
			"label": _("Issue Status"),
			"fieldname": "status",
			"fieldtype": "Data",
			"width": 110,
		},
		{
			"label": _("Priority"),
			"fieldname": "priority",
			"fieldtype": "Link",
			"options": "Issue Priority",
			"width": 90,
		},
		{
			"label": _("Reg. Dt"),
			"fieldname": "custom_complaint_reg_date",
			"fieldtype": "Date",
			"width": 100,
		},
		{
			"label": _("Customer"),
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 180,
		},
		{
			"label": _("Subject"),
			"fieldname": "subject",
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"label": _("Issue Type"),
			"fieldname": "issue_type",
			"fieldtype": "Link",
			"options": "Issue Type",
			"width": 120,
		},
		{
			"label": _("Sales Order"),
			"fieldname": "custom_sales_order",
			"fieldtype": "Link",
			"options": "Sales Order",
			"width": 140,
		},
		{
			"label": _("FS Number"),
			"fieldname": "custom_fs_number",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Site ✎"),
			"fieldname": "custom_site",
			"fieldtype": "Data",
			"editable": 1,
			"width": 140,
		},
		{
			"label": _("Project"),
			"fieldname": "custom_project_name",
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"label": _("Valve"),
			"fieldname": "custom_valve",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Type"),
			"fieldname": "custom_valve_type",
			"fieldtype": "Data",
			"width": 90,
		},
		{
			"label": _("Size"),
			"fieldname": "custom_valve_size",
			"fieldtype": "Data",
			"width": 90,
		},
		{
			"label": _("Class"),
			"fieldname": "custom_valve_class",
			"fieldtype": "Data",
			"width": 90,
		},
		{
			"label": _("MOC"),
			"fieldname": "custom_moc",
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"label": _("Valve Serial Nos."),
			"fieldname": "custom_valve_serial_no",
			"fieldtype": "Data",
			"width": 160,
		},
		{
			"label": _("Qty"),
			"fieldname": "custom_qty",
			"fieldtype": "Data",
			"width": 80,
		},
		{
			"label": _("Actuator Make"),
			"fieldname": "custom_actuator_make",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Resp. Dept ✎"),
			"fieldname": "custom_responsible_department",
			"fieldtype": "Data",
			"editable": 1,
			"width": 130,
		},
		{
			"label": _("Nature of Complaint"),
			"fieldname": "custom_nature_of_complaint",
			"fieldtype": "Small Text",
			"width": 240,
		},
		{
			"label": _("Action Date ✎"),
			"fieldname": "custom_action_date",
			"fieldtype": "Date",
			"editable": 1,
			"width": 150,
		},
		{
			"label": _("Action Decided / Remarks ✎"),
			"fieldname": "custom_action_remarks",
			"fieldtype": "Small Text",
			"editable": 1,
			"width": 240,
		},
		{
			"label": _("Final Status / Remarks ✎"),
			"fieldname": "custom_final_action_remarks",
			"fieldtype": "Small Text",
			"editable": 1,
			"width": 240,
		},
		{
			"label": _("SSV Visiting Engineer ✎"),
			"fieldname": "custom_ssv_visiting_engineer",
			"fieldtype": "Data",
			"editable": 1,
			"width": 240,
		},
		{
			"label": _("Visit Schedule Date ✎"),
			"fieldname": "custom_visit_schedule_date",
			"fieldtype": "Date",
			"editable": 1,
			"width": 240,
		},
		{
			"label": _("Visit Schedule Notes ✎"),
			"fieldname": "custom_visit_schedule_notes",
			"fieldtype": "Small Text",
			"editable": 1,
			"width": 240,
		},
		{
			"label": _("Progress Updated By"),
			"fieldname": "custom_progress_updated_by",
			"fieldtype": "Data",
			"width": 130,
		},
		{
			"label": _("Action By"),
			"fieldname": "custom_action_taken_by",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Closure Date"),
			"fieldname": "custom_closure_date",
			"fieldtype": "Date",
			"width": 100,
		},
		{
			"label": _("Closed By"),
			"fieldname": "custom_closure_by",
			"fieldtype": "Link",
			"options": "User",
			"width": 120,
		},
		{
			"label": _("Raised By"),
			"fieldname": "owner",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Last Modified"),
			"fieldname": "modified",
			"fieldtype": "Datetime",
			"width": 140,
		},
		{
			"label": _("Last Updated By"),
			"fieldname": "modified_by",
			"fieldtype": "Data",
			"width": 120,
		},
	]


def get_conditions(filters):
	conditions = []
	params = {}

	# Date filtering based on complaint registration date or opening date
	if filters.get("from_date"):
		conditions.append("COALESCE(i.custom_complaint_reg_date, i.opening_date) >= %(from_date)s")
		params["from_date"] = filters.get("from_date")

	if filters.get("to_date"):
		conditions.append("COALESCE(i.custom_complaint_reg_date, i.opening_date) <= %(to_date)s")
		params["to_date"] = filters.get("to_date")

	# Exact filters
	if filters.get("customer"):
		conditions.append("i.customer = %(customer)s")
		params["customer"] = filters.get("customer")

	if filters.get("complaint_status"):
		conditions.append("i.custom_complaint_status = %(complaint_status)s")
		params["complaint_status"] = filters.get("complaint_status")

	if filters.get("status"):
		conditions.append("i.status = %(status)s")
		params["status"] = filters.get("status")

	if filters.get("priority"):
		conditions.append("i.priority = %(priority)s")
		params["priority"] = filters.get("priority")

	if filters.get("issue_type"):
		conditions.append("i.issue_type = %(issue_type)s")
		params["issue_type"] = filters.get("issue_type")

	if filters.get("sales_order"):
		conditions.append("i.custom_sales_order = %(sales_order)s")
		params["sales_order"] = filters.get("sales_order")

	# Substring / text filters
	if filters.get("responsible_department"):
		conditions.append("i.custom_responsible_department LIKE %(responsible_department)s")
		params["responsible_department"] = f"%{filters.get('responsible_department')}%"

	if filters.get("site"):
		conditions.append("i.custom_site LIKE %(site)s")
		params["site"] = f"%{filters.get('site')}%"

	if filters.get("fs_number"):
		conditions.append("i.custom_fs_number LIKE %(fs_number)s")
		params["fs_number"] = f"%{filters.get('fs_number')}%"

	if filters.get("valve"):
		conditions.append("i.custom_valve LIKE %(valve)s")
		params["valve"] = f"%{filters.get('valve')}%"

	if filters.get("valve_size"):
		conditions.append("i.custom_valve_size LIKE %(valve_size)s")
		params["valve_size"] = f"%{filters.get('valve_size')}%"

	if filters.get("valve_class"):
		conditions.append("i.custom_valve_class LIKE %(valve_class)s")
		params["valve_class"] = f"%{filters.get('valve_class')}%"

	if filters.get("actuator_make"):
		conditions.append("i.custom_actuator_make LIKE %(actuator_make)s")
		params["actuator_make"] = f"%{filters.get('actuator_make')}%"

	if filters.get("project"):
		conditions.append("(i.custom_project_name LIKE %(project)s OR i.project LIKE %(project)s)")
		params["project"] = f"%{filters.get('project')}%"

	where_clause = " AND ".join(conditions) if conditions else "1=1"
	return where_clause, params


def get_data(conditions, query_params):
	if not frappe.has_permission("Issue", "read"):
		return []

	query = f"""
		SELECT
			i.name,
			i.custom_complaint_ref_no,
			COALESCE(i.custom_complaint_status, 'Open') AS custom_complaint_status,
			i.status,
			i.priority,
			COALESCE(i.custom_complaint_reg_date, i.opening_date) AS custom_complaint_reg_date,
			i.customer,
			i.subject,
			i.issue_type,
			i.custom_sales_order,
			i.custom_fs_number,
			i.custom_site,
			COALESCE(i.custom_project_name, i.project) AS custom_project_name,
			i.custom_valve,
			i.custom_valve_type,
			i.custom_valve_size,
			i.custom_valve_class,
			i.custom_moc,
			i.custom_valve_serial_no,
			i.custom_qty,
			i.custom_actuator_make,
			i.custom_responsible_department,
			i.custom_nature_of_complaint,
			i.custom_action_date,
			i.custom_action_remarks,
			i.custom_final_action_remarks,
			i.custom_progress_updated_by,
			i.custom_action_taken_by,
			i.custom_ssv_visiting_engineer,
			i.custom_visit_schedule_date,
			i.custom_visit_schedule_notes,
			i.custom_closure_date,
			i.custom_closure_by,
			i.owner,
			i.modified,
			i.modified_by
		FROM
			`tabIssue` i
		WHERE
			{conditions}
		ORDER BY
			COALESCE(i.custom_complaint_reg_date, i.opening_date) DESC,
			i.creation DESC
	"""

	return frappe.db.sql(query, query_params, as_dict=True)


@frappe.whitelist()
def save_complaint_register_changes(changes):
	"""
	Server-side batch update method for Customer Complaint Register.
	Validates permissions, field allowlist, field types, and runs standard doc.save().
	"""
	if isinstance(changes, str):
		changes = frappe.parse_json(changes)

	if not changes:
		return {"success": True, "updated": [], "errors": [], "message": _("No changes to save.")}

	# Normalize changes into dict { issue_name: { field: val } }
	normalized = {}
	if isinstance(changes, list):
		for item in changes:
			issue_id = item.get("name") or item.get("issue_id") or item.get("qi_name")
			if not issue_id:
				continue
			field_updates = {k: v for k, v in item.items() if k not in ("name", "issue_id", "qi_name")}
			normalized[issue_id] = field_updates
	elif isinstance(changes, dict):
		normalized = changes

	updated = []
	errors = []

	for issue_id, field_values in normalized.items():
		try:
			if not frappe.db.exists("Issue", issue_id):
				errors.append({"issue_id": issue_id, "error": _("Issue {0} does not exist.").format(issue_id)})
				continue

			if not frappe.has_permission("Issue", "write", doc=issue_id):
				errors.append({
					"issue_id": issue_id,
					"error": _("You do not have write permission for Issue {0}.").format(issue_id),
				})
				continue

			doc = frappe.get_doc("Issue", issue_id)
			has_modifications = False

			for fieldname, value in field_values.items():
				if fieldname not in ALLOWED_EDITABLE_FIELDS:
					continue

				# Specific validation
				if fieldname == "custom_complaint_status":
					if value and value not in ALLOWED_COMPLAINT_STATUSES:
						raise frappe.ValidationError(
							_("Invalid Complaint Status '{0}'. Must be one of: {1}").format(
								value, ", ".join(ALLOWED_COMPLAINT_STATUSES)
							)
						)

				if fieldname in ("custom_action_date", "custom_visit_schedule_date"):
					if value == "":
						value = None
					elif value:
						value = str(value).strip()

				if doc.get(fieldname) != value:
					doc.set(fieldname, value)
					has_modifications = True

			if has_modifications:
				doc.save()
				updated.append(issue_id)

		except Exception as e:
			frappe.log_error(title=f"Error saving complaint changes for {issue_id}", message=str(e))
			errors.append({"issue_id": issue_id, "error": str(e)})

	return {
		"success": len(errors) == 0,
		"updated": updated,
		"errors": errors,
		"message": _("Updated {0} complaint(s).").format(len(updated)),
	}


@frappe.whitelist()
def update_complaint_row(issue_id, **kwargs):
	"""
	Single row update convenience method.
	"""
	return save_complaint_register_changes({issue_id: kwargs})
