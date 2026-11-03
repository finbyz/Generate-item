# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe import _

ALLOWED_COMPLAINT_STATUSES = ("Open", "Action in Progress", "Close")

PROGRESS_TRACKED_FIELDS = (
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
	- Enforces allowed complaint status values
	- Sets defaults for registration date and complaint status
	- Sets closure date and closed by on closing
	- Enforces append-only rule for progress history
	"""
	# Set default complaint status
	if not doc.custom_complaint_status:
		doc.custom_complaint_status = "Open"

	# Validate complaint status
	if doc.custom_complaint_status not in ALLOWED_COMPLAINT_STATUSES:
		frappe.throw(
			_("Complaint Status must be one of: {0}").format(", ".join(ALLOWED_COMPLAINT_STATUSES)),
			frappe.ValidationError,
		)

	# Set default registration date
	if not doc.custom_complaint_reg_date:
		doc.custom_complaint_reg_date = doc.opening_date or frappe.utils.today()

	# Set closure metadata when closed
	if doc.custom_complaint_status == "Close":
		if not doc.custom_closure_date:
			doc.custom_closure_date = frappe.utils.today()
		if not doc.custom_closure_by and frappe.session and frappe.session.user:
			doc.custom_closure_by = frappe.session.user

	# Append-only check for existing progress history
	validate_progress_history_append_only(doc)


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

	if complaint_status:
		if complaint_status not in ALLOWED_COMPLAINT_STATUSES:
			frappe.throw(
				_("Invalid Complaint Status '{0}'. Must be one of: {1}").format(
					complaint_status, ", ".join(ALLOWED_COMPLAINT_STATUSES)
				)
			)
		doc.custom_complaint_status = complaint_status
		if complaint_status == "Close":
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
