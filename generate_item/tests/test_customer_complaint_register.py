# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate
from generate_item.customer_complaint.issue import add_complaint_progress_update
from generate_item.generate_item.report.customer_complaint_register.customer_complaint_register import (
	execute,
	save_complaint_register_changes,
	update_complaint_row,
)
from generate_item.generate_item.report.incoming_inspection.incoming_inspection import (
	execute as incoming_inspection_execute,
)


class TestCustomerComplaintRegister(IntegrationTestCase):
	def setUp(self):
		self.test_issues = []
		# Ensure a test customer exists
		if not frappe.db.exists("Customer", "_Test Complaint Customer"):
			c = frappe.new_doc("Customer")
			c.customer_name = "_Test Complaint Customer"
			c.customer_group = frappe.db.get_value("Customer Group", {}, "name") or "All Customer Groups"
			c.territory = frappe.db.get_value("Territory", {}, "name") or "All Territories"
			c.insert(ignore_permissions=True)

	def tearDown(self):
		frappe.set_user("Administrator")
		for issue_name in self.test_issues:
			if frappe.db.exists("Issue", issue_name):
				frappe.delete_doc("Issue", issue_name, force=True, ignore_permissions=True)

	def create_test_issue(self, **kwargs):
		doc = frappe.new_doc("Issue")
		doc.subject = kwargs.get("subject", "Test Valve Leakage Complaint")
		doc.customer = kwargs.get("customer", "_Test Complaint Customer")
		doc.status = kwargs.get("status", "Open")
		if "priority" in kwargs:
			doc.priority = kwargs["priority"]
		doc.custom_complaint_status = kwargs.get("custom_complaint_status", "Open")
		doc.custom_complaint_reg_date = kwargs.get("custom_complaint_reg_date", nowdate())
		doc.custom_complaint_ref_no = kwargs.get("custom_complaint_ref_no", "CCR-TEST-01")
		doc.custom_site = kwargs.get("custom_site", "Barmer HRRL")
		doc.custom_responsible_department = kwargs.get("custom_responsible_department", "Quality")
		doc.custom_valve = kwargs.get("custom_valve", "Gate")
		doc.custom_valve_size = kwargs.get("custom_valve_size", "4\"")
		doc.custom_valve_class = kwargs.get("custom_valve_class", "300#")
		doc.custom_action_remarks = kwargs.get("custom_action_remarks", "Sent replacement valve")
		for k, v in kwargs.items():
			doc.set(k, v)
		doc.insert(ignore_permissions=True)
		self.test_issues.append(doc.name)
		return doc

	def test_schema_installed(self):
		"""Verify custom fields and child doctype are installed."""
		self.assertTrue(frappe.db.exists("DocType", "Issue Progress Update"))
		meta = frappe.get_meta("Issue")
		self.assertTrue(meta.has_field("custom_complaint_status"))
		self.assertTrue(meta.has_field("custom_complaint_reg_date"))
		self.assertTrue(meta.has_field("custom_progress_history"))
		self.assertTrue(meta.has_field("custom_valve"))
		self.assertTrue(meta.has_field("custom_responsible_department"))

	def test_report_execution_variations(self):
		"""Verify execute handles None, empty, and partial filters without KeyError."""
		# 1. filters=None
		cols, data = execute(None)
		self.assertIsInstance(cols, list)
		self.assertIsInstance(data, list)

		# 2. empty dict
		cols, data = execute({})
		self.assertIsInstance(cols, list)

		# 3. single filter
		cols, data = execute({"complaint_status": "Open"})
		self.assertIsInstance(data, list)

		# 4. missing date filters handled safely
		cols, data = execute({"customer": "_Test Complaint Customer"})
		self.assertIsInstance(data, list)

	def test_complaint_creation_and_defaults(self):
		"""Test default values on new Issue."""
		issue = self.create_test_issue(custom_complaint_status=None, custom_complaint_reg_date=None)
		self.assertEqual(issue.custom_complaint_status, "Open")
		self.assertIsNotNone(issue.custom_complaint_reg_date)
		# Initial remarks should populate progress history
		self.assertGreaterEqual(len(issue.custom_progress_history or []), 1)

	def test_complaint_status_filtering_independent(self):
		"""Ensure custom_complaint_status is strictly separate from standard status."""
		# Issue 1: custom_complaint_status="Open", standard status="Closed"
		i1 = self.create_test_issue(
			subject="Issue 1 Test",
			custom_complaint_status="Open",
			status="Closed"
		)
		# Issue 2: custom_complaint_status="Close", standard status="Open"
		i2 = self.create_test_issue(
			subject="Issue 2 Test",
			custom_complaint_status="Close",
			status="Open"
		)

		# Filter by custom_complaint_status = "Open"
		cols, data = execute({"complaint_status": "Open", "customer": "_Test Complaint Customer"})
		names = [row["name"] for row in data]
		self.assertIn(i1.name, names)
		self.assertNotIn(i2.name, names)

		# Filter by standard status = "Closed"
		cols, data = execute({"status": "Closed", "customer": "_Test Complaint Customer"})
		names = [row["name"] for row in data]
		self.assertIn(i1.name, names)
		self.assertNotIn(i2.name, names)

	def test_priority_filter_and_column(self):
		"""Verify priority column and filter link to Issue Priority."""
		cols, _ = execute({})
		priority_col = next((c for c in cols if c["fieldname"] == "priority"), None)
		self.assertIsNotNone(priority_col)
		self.assertEqual(priority_col.get("options"), "Issue Priority")

		i = self.create_test_issue(priority="High")
		_, data = execute({"priority": "High", "customer": "_Test Complaint Customer"})
		names = [row["name"] for row in data]
		self.assertIn(i.name, names)

	def test_date_filtering_inclusive(self):
		"""Test inclusive date filtering."""
		target_date = add_days(nowdate(), -5)
		issue = self.create_test_issue(custom_complaint_reg_date=target_date)

		# Inclusive bounds matching exact date
		cols, data = execute({
			"from_date": target_date,
			"to_date": target_date,
			"customer": "_Test Complaint Customer"
		})
		names = [row["name"] for row in data]
		self.assertIn(issue.name, names)

		# Out of range
		cols, data = execute({
			"from_date": add_days(target_date, 1),
			"to_date": add_days(target_date, 2),
			"customer": "_Test Complaint Customer"
		})
		names = [row["name"] for row in data]
		self.assertNotIn(issue.name, names)

	def test_progress_history_append_only(self):
		"""Test that history rows cannot be deleted or timestamp modified."""
		issue = self.create_test_issue(custom_action_remarks="Action 1")
		initial_count = len(issue.custom_progress_history)
		self.assertGreaterEqual(initial_count, 1)

		# Attempting to delete history row
		issue.custom_progress_history = []
		with self.assertRaises(frappe.PermissionError):
			issue.save(ignore_permissions=False)

	def test_progress_history_no_unrelated_duplicates(self):
		"""Updating unrelated fields (e.g. subject) must not create duplicate history rows."""
		issue = self.create_test_issue(custom_action_remarks="Action Initial")
		initial_history_len = len(issue.custom_progress_history)

		issue.subject = "Modified Subject Only"
		issue.save()
		issue.reload()

		self.assertEqual(len(issue.custom_progress_history), initial_history_len)

	def test_progress_history_auto_sync_on_progress_change(self):
		"""Updating progress remarks or status automatically appends a new progress row."""
		issue = self.create_test_issue(custom_action_remarks="Initial")
		initial_len = len(issue.custom_progress_history)

		issue.custom_complaint_status = "Action in Progress"
		issue.custom_action_remarks = "Follow up with site engineer"
		issue.save()
		issue.reload()

		self.assertEqual(len(issue.custom_progress_history), initial_len + 1)
		last_entry = issue.custom_progress_history[-1]
		self.assertEqual(last_entry.complaint_status, "Action in Progress")
		self.assertEqual(last_entry.action_remarks, "Follow up with site engineer")

	def test_closure_logic(self):
		"""Setting custom_complaint_status='Close' auto-populates closure date."""
		issue = self.create_test_issue(custom_complaint_status="Open")
		self.assertIsNone(issue.custom_closure_date)

		issue.custom_complaint_status = "Close"
		issue.save()
		issue.reload()

		self.assertIsNotNone(issue.custom_closure_date)
		self.assertEqual(issue.custom_closure_by, "Administrator")

	def test_save_complaint_register_changes_allowed(self):
		"""Test server-side save API with allowed fields."""
		issue = self.create_test_issue(custom_complaint_status="Open", custom_site="Site A")

		res = save_complaint_register_changes({
			issue.name: {
				"custom_complaint_status": "Action in Progress",
				"custom_site": "Site B Updated",
				"custom_action_remarks": "Engineer dispatched",
			}
		})
		self.assertTrue(res.get("success"))
		self.assertIn(issue.name, res.get("updated"))

		issue.reload()
		self.assertEqual(issue.custom_complaint_status, "Action in Progress")
		self.assertEqual(issue.custom_site, "Site B Updated")

	def test_save_complaint_register_changes_disallowed_and_invalid(self):
		"""Disallowed fields must be ignored and invalid status rejected."""
		issue = self.create_test_issue(custom_complaint_status="Open")

		# 1. Invalid status value
		res = save_complaint_register_changes({
			issue.name: {
				"custom_complaint_status": "InvalidStatusXYZ"
			}
		})
		self.assertFalse(res.get("success"))
		self.assertGreater(len(res.get("errors")), 0)

		# 2. Disallowed fields ignored
		res = save_complaint_register_changes({
			issue.name: {
				"customer": "Hacker Customer",
				"owner": "test@example.com",
				"custom_site": "Authorized Site Update",
			}
		})
		issue.reload()
		self.assertEqual(issue.customer, "_Test Complaint Customer")  # Untouched
		self.assertEqual(issue.custom_site, "Authorized Site Update")

	def test_save_permissions(self):
		"""A user without write permission must fail to save."""
		issue = self.create_test_issue()

		frappe.set_user("Guest")
		res = save_complaint_register_changes({
			issue.name: {
				"custom_site": "Illegal Site"
			}
		})
		self.assertFalse(res.get("success"))
		self.assertGreater(len(res.get("errors")), 0)
		frappe.set_user("Administrator")

	def test_incoming_inspection_report_unchanged(self):
		"""Verify existing Incoming Inspection report continues to execute without error."""
		cols, data = incoming_inspection_execute({})
		self.assertIsInstance(cols, list)
		self.assertIsInstance(data, list)

	def test_add_complaint_progress_update_atomic_api(self):
		"""Verify atomic server-side progress update method avoids TimestampMismatchError."""
		issue = self.create_test_issue(custom_complaint_status="Open")
		initial_history_len = len(issue.custom_progress_history or [])

		# Simulate an external background save (updating modified timestamp in DB)
		frappe.db.set_value("Issue", issue.name, "subject", "Background Updated Subject")

		# Call add_complaint_progress_update API
		res = add_complaint_progress_update(
			issue_id=issue.name,
			complaint_status="Action in Progress",
			action_remarks="Team dispatched to Barmer site",
			responsible_department="Production",
			action_by="Vijay Kumar",
			ssv_visiting_engineer="Vijay Kumar",
			visit_schedule_date=nowdate(),
			visit_schedule_notes="Meeting customer site engineer",
		)
		self.assertTrue(res.get("success"))

		issue.reload()
		self.assertEqual(issue.custom_complaint_status, "Action in Progress")
		self.assertEqual(issue.custom_action_remarks, "Team dispatched to Barmer site")
		self.assertEqual(len(issue.custom_progress_history), initial_history_len + 1)
		latest_row = issue.custom_progress_history[-1]
		self.assertEqual(latest_row.complaint_status, "Action in Progress")
		self.assertEqual(latest_row.action_remarks, "Team dispatched to Barmer site")
		self.assertEqual(latest_row.ssv_visiting_engineer, "Vijay Kumar")

	def test_single_sales_order_field_and_no_so_number_duplicate(self):
		"""Verify only custom_sales_order Link exists in report and no duplicate custom_so_number."""
		cols, _ = execute({})
		fieldnames = [c["fieldname"] for c in cols]
		self.assertIn("custom_sales_order", fieldnames)
		self.assertNotIn("custom_so_number", fieldnames)

		so_col = next(c for c in cols if c["fieldname"] == "custom_sales_order")
		self.assertEqual(so_col.get("fieldtype"), "Link")
		self.assertEqual(so_col.get("options"), "Sales Order")

	def test_editable_columns_metadata(self):
		"""Verify all expected editable columns have editable: 1 in get_columns()."""
		cols, _ = execute({})
		editable_cols = {c["fieldname"]: c for c in cols if c.get("editable") == 1}
		expected_editable = [
			"custom_complaint_status",
			"custom_site",
			"custom_responsible_department",
			"custom_action_date",
			"custom_action_remarks",
			"custom_final_action_remarks",
			"custom_ssv_visiting_engineer",
			"custom_visit_schedule_date",
			"custom_visit_schedule_notes",
		]
		for field in expected_editable:
			self.assertIn(field, editable_cols, f"Field {field} should be marked editable")
			# Check label contains pencil indicator ✎
			self.assertIn("✎", editable_cols[field].get("label", ""))

	def test_project_text_filtering(self):
		"""Verify project filter searches custom_project_name cleanly."""
		issue = self.create_test_issue(custom_project_name="GAIL Gas Barmer Pipeline")
		cols, data = execute({"project": "GAIL Gas", "customer": "_Test Complaint Customer"})
		names = [row["name"] for row in data]
		self.assertIn(issue.name, names)

	def test_save_complaint_register_changes_visit_notes(self):
		"""Verify custom_visit_schedule_notes can be saved via save_complaint_register_changes."""
		issue = self.create_test_issue(custom_complaint_status="Open")
		res = save_complaint_register_changes({
			issue.name: {
				"custom_visit_schedule_notes": "Carried special gaskets for replacement"
			}
		})
		self.assertTrue(res.get("success"))
		issue.reload()
		self.assertEqual(issue.custom_visit_schedule_notes, "Carried special gaskets for replacement")

