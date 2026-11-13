# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe import _

ALLOWED_ISSUE_STATUSES = ("Open", "In Process", "Closed")
ALLOWED_COMPLAINT_STATUSES = ("Open", "Action in Progress", "In Process", "Close", "Closed")

STATUS_TO_COMPLAINT_MAP = {
	"Open": "Open",
	"In Process": "Action in Progress",
	"Closed": "Close",
}

COMPLAINT_TO_STATUS_MAP = {
	"Open": "Open",
	"Action in Progress": "In Process",
	"In Process": "In Process",
	"Close": "Closed",
	"Closed": "Closed",
}

PROGRESS_TRACKED_FIELDS = (
	"status",
	"custom_complaint_status",
	"custom_action_remarks",
	"custom_final_action_remarks",
	"custom_action_date",
	"custom_responsible_department",
	"custom_ssv_visiting_engineer",
	"custom_visit_schedule_date",
	"custom_visit_schedule_notes",
)


def validate_issue(doc, method=None):
	"""
	Validates complaint fields on Issue DocType:
	- Enforces allowed status (Open, In Process, Closed) and synchronizes with custom_complaint_status
	- Sets defaults for registration date and complaint status
	- Sets closure date and closed by on closing
	- Enforces append-only rule for progress history
	"""
	# Synchronize standard status and custom_complaint_status
	if not doc.status and not doc.custom_complaint_status:
		doc.status = "Open"
		doc.custom_complaint_status = "Open"
	elif doc.status:
		if doc.status not in ALLOWED_ISSUE_STATUSES:
			frappe.throw(
				_("Status must be one of: {0}").format(", ".join(ALLOWED_ISSUE_STATUSES)),
				frappe.ValidationError,
			)
		doc.custom_complaint_status = STATUS_TO_COMPLAINT_MAP.get(doc.status, "Open")
	elif doc.custom_complaint_status:
		doc.status = COMPLAINT_TO_STATUS_MAP.get(doc.custom_complaint_status, "Open")
		doc.custom_complaint_status = STATUS_TO_COMPLAINT_MAP.get(doc.status, doc.custom_complaint_status)

	# Set default registration date
	if not doc.custom_complaint_reg_date:
		doc.custom_complaint_reg_date = doc.opening_date or frappe.utils.today()

	# Set closure metadata when closed
	if doc.status == "Closed" or doc.custom_complaint_status in ("Close", "Closed"):
		if not doc.custom_closure_date:
			doc.custom_closure_date = frappe.utils.today()
		if not doc.custom_closure_by and frappe.session and frappe.session.user:
			doc.custom_closure_by = frappe.session.user

	# Synchronize customer name and default primary address
	sync_customer_details(doc)

	# Append-only check for existing progress history
	validate_progress_history_append_only(doc)


def sync_customer_details(doc):
	"""
	Ensures customer name and primary customer address are defaulted when customer is set on Issue.
	"""
	if not doc.customer:
		return

	if not doc.customer_name:
		doc.customer_name = frappe.db.get_value("Customer", doc.customer, "customer_name")

	if not doc.custom_customer_address:
		from frappe.contacts.doctype.address.address import get_default_address
		primary_addr = frappe.db.get_value("Customer", doc.customer, "customer_primary_address")
		if not primary_addr:
			primary_addr = get_default_address("Customer", doc.customer)
		if primary_addr:
			doc.custom_customer_address = primary_addr

	if doc.custom_customer_address and not doc.custom_address_display:
		from frappe.contacts.doctype.address.address import get_address_display
		doc.custom_address_display = get_address_display(doc.custom_customer_address)


def validate_progress_history_append_only(doc):
	"""
	Ensures historical child rows in custom_progress_history cannot be deleted or modified.
	"""
	if doc.is_new():
		return

	old_doc = doc.get_doc_before_save()
	if not old_doc:
		return

	old_rows = {row.name: row for row in (old_doc.custom_progress_history or []) if row.name}
	if not old_rows:
		return

	current_rows = {row.name: row for row in (doc.custom_progress_history or []) if row.name}

	# Check that no historical row was removed
	missing_row_ids = set(old_rows.keys()) - set(current_rows.keys())
	if missing_row_ids:
		frappe.throw(
			_("Complaint Progress History is append-only. Earlier progress entries cannot be deleted."),
			frappe.PermissionError,
		)

	# Check that historical row timestamps are not modified (allow small tolerance for serialization)
	for row_id, old_row in old_rows.items():
		curr_row = current_rows.get(row_id)
		if not curr_row:
			continue
		curr_dt = frappe.utils.get_datetime(curr_row.posting_datetime)
		old_dt = frappe.utils.get_datetime(old_row.posting_datetime)
		if curr_dt and old_dt and abs((curr_dt - old_dt).total_seconds()) > 2:
			frappe.throw(
				_("Modification of history entry timestamps is not permitted."),
				frappe.PermissionError,
			)


def before_save_issue(doc, method=None):
	"""
	Maintains synchronization between current complaint state and progress history.
	Adds a progress history entry if progress fields changed and no new row was manually added.
	"""
	if doc.is_new():
		# Record initial progress entry on creation if remarks or non-default status present
		if doc.custom_action_remarks or doc.custom_final_action_remarks or (doc.custom_complaint_status and doc.custom_complaint_status != "Open"):
			add_progress_history_entry(doc, remarks="Initial Complaint Registration")
		return

	old_doc = doc.get_doc_before_save()
	if not old_doc:
		return

	# Check if any tracked progress field changed
	changed_fields = [
		f for f in PROGRESS_TRACKED_FIELDS
		if (doc.get(f) or "") != (old_doc.get(f) or "")
	]

	if not changed_fields:
		return

	old_history_len = len(old_doc.custom_progress_history or [])
	current_history_len = len(doc.custom_progress_history or [])

	# If a new child row was already added (manually or via API), don't duplicate it
	if current_history_len > old_history_len or any(not row.name or getattr(row, "__islocal", False) or row.is_new() for row in (doc.custom_progress_history or [])):
		for row in doc.custom_progress_history or []:
			if not row.name or getattr(row, "__islocal", False) or row.is_new():
				if not row.posting_datetime:
					row.posting_datetime = frappe.utils.now_datetime()
				if not row.updated_by and frappe.session and frappe.session.user:
					row.updated_by = frappe.session.user
				if not row.complaint_status:
					row.complaint_status = doc.custom_complaint_status
		return

	# Automatically append a new progress row reflecting the changes
	summary_remarks = doc.custom_action_remarks or doc.custom_final_action_remarks or f"Status changed to {doc.custom_complaint_status}"
	add_progress_history_entry(doc, remarks=summary_remarks)


def add_progress_history_entry(doc, remarks=None):
	"""Appends a new Issue Progress Update row to doc.custom_progress_history."""
	current_user = frappe.session.user if (frappe.session and frappe.session.user) else "Administrator"
	doc.append("custom_progress_history", {
		"posting_datetime": frappe.utils.now_datetime(),
		"complaint_status": doc.custom_complaint_status or "Open",
		"action_by": doc.custom_action_taken_by or current_user,
		"responsible_department": doc.custom_responsible_department,
		"action_remarks": doc.custom_action_remarks,
		"progress_update": remarks or doc.custom_final_action_remarks or doc.custom_action_remarks,
		"ssv_visiting_engineer": doc.custom_ssv_visiting_engineer,
		"visit_schedule_date": doc.custom_visit_schedule_date,
		"visit_schedule_notes": doc.custom_visit_schedule_notes,
		"updated_by": current_user,
	})


@frappe.whitelist()
def add_complaint_progress_update(
	issue_id,
	complaint_status=None,
	status=None,
	action_remarks=None,
	responsible_department=None,
	action_by=None,
	ssv_visiting_engineer=None,
	visit_schedule_date=None,
	visit_schedule_notes=None,
):
	"""
	Server-side atomic progress update method.
	Loads the latest document fresh from DB, applies the progress update,
	appends to history, and saves with full lifecycle and permission checks.
	Avoids browser TimestampMismatchError.
	"""
	if not frappe.db.exists("Issue", issue_id):
		frappe.throw(_("Issue {0} does not exist.").format(issue_id), frappe.DoesNotExistError)

	if not frappe.has_permission("Issue", "write", doc=issue_id):
		frappe.throw(
			_("You do not have write permission for Issue {0}.").format(issue_id),
			frappe.PermissionError,
		)

	doc = frappe.get_doc("Issue", issue_id)

	target_status = status or complaint_status
	if target_status:
		if target_status in COMPLAINT_TO_STATUS_MAP:
			doc.status = COMPLAINT_TO_STATUS_MAP[target_status]
			doc.custom_complaint_status = STATUS_TO_COMPLAINT_MAP.get(doc.status, target_status)
		elif target_status in ALLOWED_ISSUE_STATUSES:
			doc.status = target_status
			doc.custom_complaint_status = STATUS_TO_COMPLAINT_MAP.get(target_status, "Open")
		elif target_status in ALLOWED_COMPLAINT_STATUSES:
			doc.custom_complaint_status = target_status
			doc.status = COMPLAINT_TO_STATUS_MAP.get(target_status, "Open")
		else:
			frappe.throw(
				_("Invalid Status '{0}'. Must be one of: {1}").format(
					target_status, ", ".join(ALLOWED_ISSUE_STATUSES)
				)
			)

		if doc.status == "Closed" or doc.custom_complaint_status in ("Close", "Closed"):
			if not doc.custom_closure_date:
				doc.custom_closure_date = frappe.utils.today()
			if not doc.custom_closure_by and frappe.session and frappe.session.user:
				doc.custom_closure_by = frappe.session.user

	if responsible_department is not None:
		doc.custom_responsible_department = responsible_department

	if action_by is not None:
		doc.custom_action_taken_by = action_by

	if action_remarks is not None:
		doc.custom_action_remarks = action_remarks

	if ssv_visiting_engineer is not None:
		doc.custom_ssv_visiting_engineer = ssv_visiting_engineer

	if visit_schedule_date:
		doc.custom_visit_schedule_date = visit_schedule_date

	if visit_schedule_notes is not None:
		doc.custom_visit_schedule_notes = visit_schedule_notes

	current_user = frappe.session.user if (frappe.session and frappe.session.user) else "Administrator"

	# Append the new child row
	doc.append("custom_progress_history", {
		"posting_datetime": frappe.utils.now_datetime(),
		"complaint_status": doc.custom_complaint_status or "Open",
		"action_by": action_by or doc.custom_action_taken_by or current_user,
		"responsible_department": doc.custom_responsible_department,
		"action_remarks": action_remarks or doc.custom_action_remarks,
		"progress_update": action_remarks or doc.custom_final_action_remarks or doc.custom_action_remarks or f"Status updated to {doc.custom_complaint_status}",
		"ssv_visiting_engineer": doc.custom_ssv_visiting_engineer,
		"visit_schedule_date": doc.custom_visit_schedule_date,
		"visit_schedule_notes": doc.custom_visit_schedule_notes,
		"updated_by": current_user,
	})

	doc.save()

	return {
		"success": True,
		"issue_id": doc.name,
		"message": _("Progress update added successfully."),
	}


@frappe.whitelist()
def get_valve_attribute_options(template_name=None):
	"""
	Returns dropdown options for Multiple Valves child table matching Item Generator logic.
	Reads active values from Custom Item Attribute Value child records for the selected template.
	"""
	mapping = {
		"valve_type": [],
		"size": [],
		"rating": [],
		"shell_moc": [],
		"operator": [],
	}

	if template_name and frappe.db.exists("Item Generator Template", template_name):
		t_doc = frappe.get_doc("Item Generator Template", template_name)
		for v in (t_doc.custom_variants or []):
			lh = (v.logic_heading or "").strip()
			if not lh:
				continue
			heading = lh.split("-", 1)[1].strip().upper() if "-" in lh else lh.upper()
			if heading in ("VALVE TYPE", "TYPE OF VALVE"):
				mapping["valve_type"].append(lh)
			elif heading == "SIZE":
				mapping["size"].append(lh)
			elif heading in ("RATING", "CLASS"):
				mapping["rating"].append(lh)
			elif "MOC" in heading:
				mapping["shell_moc"].append(lh)
			elif heading == "OPERATOR":
				mapping["operator"].append(lh)

	# If no template or a field has no mapped variant in the template, provide canonical fallbacks
	default_mapping = {
		"valve_type": [
			"BLV-Valve Type",
			"BFV-Valve Type",
			"GGC-Valve Type",
			"PLV-Valve Type",
			"Type Of Valve",
			"Valve Type",
		],
		"size": ["FG-Size", "Size", "WIP-Size"],
		"rating": ["FG-Rating", "Rating", "Class", "WIP-Class"],
		"shell_moc": [
			"BLV-Shell MOC",
			"BFV-Shell MOC",
			"GGC-Shell MOC",
			"PLV-Shell MOC",
			"ACTUATOR-MOC",
			"BAR-MOC",
			"STANDARD COMPONENT-MOC",
			"WIP-MOC",
			"MOC",
			"Shell MOC",
		],
		"operator": [
			"BLV-Operator",
			"BFV-Operator",
			"GGC-Operator",
			"PLV-Operator",
			"Operator",
		],
	}

	result = {}
	for fieldname in ("valve_type", "size", "rating", "shell_moc", "operator"):
		parents = mapping.get(fieldname)
		if not parents:
			parents = default_mapping[fieldname]

		rows = frappe.get_all(
			"Custom Item Attribute Value",
			filters={"parent": ["in", parents], "disabled": 0},
			fields=["item_long_description"],
			order_by="item_long_description asc",
		)
		opts = set()
		for r in rows:
			desc = (r.get("item_long_description") or "").strip()
			if desc and desc != "-":
				opts.add(desc)
		result[fieldname] = [""] + sorted(list(opts))

	return result
