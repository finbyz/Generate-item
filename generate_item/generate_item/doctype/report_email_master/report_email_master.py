# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ReportEmailMaster(Document):
	def autoname(self):
		if self.type == "Master":
			source_val = (self.source or "").strip()
			target = (self.report_name if self.source == "Report" else self.page_name) or ""
			target = target.strip()
			if not source_val or not target:
				frappe.throw(_("Source and Report/Dashboard Name are required to generate Document Name."))
			self.name = f"{source_val}-{target}"
		elif self.type == "Group":
			if not self.group_name or not self.group_name.strip():
				frappe.throw(_("Group Name is required to generate Document Name."))
			self.name = self.group_name.strip()

	def on_trash(self):
		# Clean up any orphaned child table rows that have no parent
		frappe.db.sql(
			"""
			DELETE FROM `tabReport Email Group`
			WHERE parent IS NULL OR parent = '' OR parenttype IS NULL
			"""
		)
		if self.type == "Group":
			# Clean up references to this group from child tables so deletion is never blocked by orphaned links
			frappe.db.sql(
				"""
				DELETE FROM `tabReport Email Group`
				WHERE group_name = %s AND (parent IS NULL OR parent = '' OR parenttype IS NULL)
				""",
				(self.name,),
			)

	def validate(self):
		# Ensure orphaned rows in child table are purged on save/validate
		frappe.db.sql(
			"""
			DELETE FROM `tabReport Email Group`
			WHERE parent IS NULL OR parent = '' OR parenttype IS NULL
			"""
		)
		if self.type == "Master":
			self.validate_master_configuration()
		elif self.type == "Group":
			self.validate_group_configuration()
		else:
			frappe.throw(_("Invalid Type: {0}").format(self.type))

	def validate_master_configuration(self):
		# Clear group-specific fields
		self.group_name = None
		self.branch = None
		self.receipts = []
		self.cc = []

		# Validate source-specific fields
		if self.source == "Report":
			if not self.report_name:
				frappe.throw(_("Report Name is mandatory when Source is Report."))
			self.page_name = None
		elif self.source in ("Dashboard", "Page"):
			if not self.page_name:
				frappe.throw(_("Dashboard/Page Name is mandatory when Source is {0}.").format(self.source))
			self.report_name = None
		else:
			frappe.throw(_("Please select Source (Report or Dashboard) for Master configuration."))

		# Validate email_group child table
		if not self.email_group:
			frappe.throw(_("At least one Email Group is required for a Master configuration."))

		seen_groups = set()
		for row in self.email_group:
			if not row.group_name:
				frappe.throw(_("Row #{0}: Group Name cannot be empty.").format(row.idx))

			if row.group_name == self.name:
				frappe.throw(_("A Master document cannot reference itself as an Email Group."))

			group_doc = frappe.db.get_value(
				"Report Email Master",
				row.group_name,
				["name", "type"],
				as_dict=True
			)
			if not group_doc:
				frappe.throw(_("Row #{0}: Group '{1}' does not exist.").format(row.idx, row.group_name))

			if group_doc.type != "Group":
				frappe.throw(
					_("Row #{0}: Document '{1}' is a Master, but only Group documents can be selected in Email Group.").format(
						row.idx, row.group_name
					)
				)

			if row.group_name in seen_groups:
				frappe.throw(_("Duplicate group '{0}' in Email Group table.").format(row.group_name))
			seen_groups.add(row.group_name)

			# Calculate recipient count for the group row
			row.count = get_group_recipient_count(row.group_name)

	def validate_group_configuration(self):
		# Clear master-specific fields
		self.source = None
		self.report_name = None
		self.page_name = None
		self.email_group = []

		if not self.group_name or not self.group_name.strip():
			frappe.throw(_("Group Name is mandatory for Group configuration."))

		if self.branch and not frappe.db.exists("Branch", self.branch):
			frappe.throw(_("Branch '{0}' does not exist.").format(self.branch))

		# Validate receipts child table
		if not self.receipts:
			frappe.throw(_("At least one recipient is required in Receipts table."))

		seen_users = set()
		for row in self.receipts:
			if not row.user:
				frappe.throw(_("Row #{0}: User cannot be empty in Receipts table.").format(row.idx))

			user_info = frappe.db.get_value("User", row.user, ["enabled", "email"], as_dict=True)
			if not user_info:
				frappe.throw(_("Row #{0}: User '{1}' does not exist.").format(row.idx, row.user))
			if not user_info.enabled:
				frappe.throw(
					_("Row #{0}: User '{1}' is disabled. Only enabled users can be added.").format(
						row.idx, row.user
					)
				)

			if row.user in seen_users:
				frappe.throw(_("Duplicate user '{0}' in Receipts table.").format(row.user))
			seen_users.add(row.user)

		# Validate CC table
		seen_cc = set()
		for row in self.cc:
			if not row.cc_user:
				frappe.throw(_("Row #{0}: CC User cannot be empty in CC table.").format(row.idx))

			cc_user_info = frappe.db.get_value("User", row.cc_user, ["enabled", "email"], as_dict=True)
			if not cc_user_info:
				frappe.throw(_("Row #{0}: CC User '{1}' does not exist.").format(row.idx, row.cc_user))
			if not cc_user_info.enabled:
				frappe.throw(
					_("Row #{0}: CC User '{1}' is disabled.").format(row.idx, row.cc_user)
				)

			if row.cc_user in seen_cc:
				frappe.throw(_("Duplicate CC user '{0}' in CC table.").format(row.cc_user))
			seen_cc.add(row.cc_user)


def resolve_group_recipients(group_name, visited=None):
	"""
	Helper to resolve To and CC recipients for a Group document.
	"""
	if visited is None:
		visited = set()

	if group_name in visited:
		return {"to": [], "cc": []}
	visited.add(group_name)

	group_doc = frappe.get_doc("Report Email Master", group_name)
	if group_doc.type != "Group":
		return {"to": [], "cc": []}

	to_emails = []
	cc_emails = []

	# Resolve configured users from receipts child table
	for row in group_doc.receipts:
		if row.user:
			user_info = frappe.db.get_value("User", row.user, ["enabled", "email"], as_dict=True)
			if user_info and user_info.enabled and user_info.email and user_info.email.strip():
				to_emails.append(user_info.email.strip())

	# Resolve CC recipients from cc child table
	for row in group_doc.cc:
		if row.cc_user:
			u_info = frappe.db.get_value("User", row.cc_user, ["enabled", "email"], as_dict=True)
			if u_info and u_info.enabled and u_info.email and u_info.email.strip():
				cc_emails.append(u_info.email.strip())

	return {"to": to_emails, "cc": cc_emails}


@frappe.whitelist()
def get_group_recipient_count(group_name):
	"""
	Calculates the total unique recipients for a given Group document.
	"""
	if not group_name:
		return 0
	try:
		res = get_resolved_recipients(group_name)
		return len(res.get("to", [])) + len(res.get("cc", []))
	except Exception:
		return 0


@frappe.whitelist()
def get_resolved_recipients(report_email_master):
	"""
	Resolves and de-duplicates recipients from a Report Email Master configuration.
	- For Group: resolves receipts (To) and cc table (CC).
	- For Master: aggregates To and CC recipients from all referenced groups in email_group.
	- Deduplication rule: If an address is in both To and CC, keep it in To, remove from CC.
	- Excludes disabled users, empty or invalid email addresses.

	Returns: {"to": [...], "cc": [...]}
	"""
	if isinstance(report_email_master, str):
		master = frappe.get_doc("Report Email Master", report_email_master)
	elif hasattr(report_email_master, "type"):
		master = report_email_master
	else:
		master = frappe.get_doc("Report Email Master", report_email_master.get("name"))

	to_raw = []
	cc_raw = []

	if master.type == "Group":
		group_res = resolve_group_recipients(master.name, visited=set())
		to_raw.extend(group_res.get("to", []))
		cc_raw.extend(group_res.get("cc", []))

	elif master.type == "Master":
		visited = set()
		for row in master.email_group:
			if not row.group_name:
				continue
			group_res = resolve_group_recipients(row.group_name, visited)
			to_raw.extend(group_res.get("to", []))
			cc_raw.extend(group_res.get("cc", []))

	# Deduplicate:
	# Keep To unique.
	seen_to = set()
	unique_to = []
	for email in to_raw:
		clean = email.strip()
		key = clean.lower()
		if key not in seen_to:
			seen_to.add(key)
			unique_to.append(clean)

	# Keep CC unique and exclude any that already exist in To.
	seen_cc = set()
	unique_cc = []
	for email in cc_raw:
		clean = email.strip()
		key = clean.lower()
		if key not in seen_to and key not in seen_cc:
			seen_cc.add(key)
			unique_cc.append(clean)

	return {"to": unique_to, "cc": unique_cc}
