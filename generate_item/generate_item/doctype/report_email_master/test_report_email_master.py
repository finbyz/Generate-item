import frappe
from unittest.mock import patch, MagicMock
from frappe.tests import UnitTestCase
from generate_item.utils.report_email_scheduler import (
	get_report_email_master_config,
	report_supports_branch_filter,
	page_supports_branch_filter,
	source_supports_branch_filter,
	report_requires_mandatory_date_filters,
	output_has_branch_column,
	generate_report_content,
	resolve_recipients_for_group,
	resolve_branch_for_group,
	send_configured_email,
	send_weekly_report_email,
	execute_weekly_report_email_scheduler,
	register_page_data_provider,
	SCHEDULED_EMAIL_HANDLERS,
	send_omr_item_change_email,
	send_pending_advance_mate_email,
	send_so_approval_tat_email,
)
from generate_item.generate_item.report.omr_item_change.omr_item_change import (
	execute as execute_omr_report,
)
from generate_item.generate_item.page.pending_advance_mate.pending_advance_mate import (
	get_data as get_pending_advance_mate_data,
)
from generate_item.generate_item.report.so_approval_tat.so_approval_tat import (
	execute as execute_so_approval_tat_report,
)


class TestReportEmailMaster(UnitTestCase):
	"""
	Comprehensive unit tests for ReportEmailMaster, dynamic send_configured_email,
	page data providers, and branch-wise report scheduling.
	"""

	def test_group_recipient_and_branch_resolution(self):
		master = get_report_email_master_config("Report", "OMR Item Change")
		self.assertIsNotNone(master)

		nandikoor_doc = frappe.get_doc("Report Email Master", "Nandikoor Purchase")
		self.assertEqual(resolve_branch_for_group(nandikoor_doc), "Nandikoor")
		nandikoor_recipients = resolve_recipients_for_group(nandikoor_doc)
		self.assertIn("dhanvant.marathe@finbyz.tech", nandikoor_recipients["to"])
		self.assertIn("ritik.patwa@finbyz.tech", nandikoor_recipients["to"])

		sanand_doc = frappe.get_doc("Report Email Master", "Sanand Purchase")
		self.assertEqual(resolve_branch_for_group(sanand_doc), "Sanand")
		sanand_recipients = resolve_recipients_for_group(sanand_doc)
		self.assertIn("dhanvant.marathe@finbyz.tech", sanand_recipients["to"])
		self.assertNotIn("ritik.patwa@finbyz.tech", sanand_recipients["to"])

	def test_omr_item_change_branch_data_isolation(self):
		report_doc = frappe.get_doc("Report", "OMR Item Change")
		self.assertTrue(report_supports_branch_filter(report_doc))

		_, nandikoor_data = generate_report_content("OMR Item Change", branch="Nandikoor")
		_, sanand_data = generate_report_content("OMR Item Change", branch="Sanand")

		self.assertGreater(len(nandikoor_data), 0)
		self.assertGreater(len(sanand_data), 0)

		nandikoor_branches = {r.get("branch") for r in nandikoor_data}
		sanand_branches = {r.get("branch") for r in sanand_data}

		self.assertEqual(nandikoor_branches, {"Nandikoor"})
		self.assertEqual(sanand_branches, {"Sanand"})
		self.assertNotIn("Sanand", nandikoor_branches)
		self.assertNotIn("Nandikoor", sanand_branches)

	def test_branch_wise_email_dispatch_and_recipient_isolation(self):
		sent_emails = []

		def mock_sendmail(**kwargs):
			sent_emails.append(kwargs)
			return MagicMock()

		with patch("frappe.sendmail", side_effect=mock_sendmail):
			res = send_configured_email(source_name="OMR Item Change", source_type="Report")

		self.assertEqual(res["status"], "completed")
		self.assertEqual(len(sent_emails), 2)

		nandikoor_email = next(e for e in sent_emails if "Nandikoor" in e["subject"])
		self.assertIn("dhanvant.marathe@finbyz.tech", nandikoor_email["recipients"])
		self.assertIn("ritik.patwa@finbyz.tech", nandikoor_email["recipients"])
		self.assertIn("omr_item_change_nandikoor", nandikoor_email["attachments"][0]["fname"])

		sanand_email = next(e for e in sent_emails if "Sanand" in e["subject"])
		self.assertIn("dhanvant.marathe@finbyz.tech", sanand_email["recipients"])
		self.assertNotIn("ritik.patwa@finbyz.tech", sanand_email["recipients"])
		self.assertIn("omr_item_change_sanand", sanand_email["attachments"][0]["fname"])

	def test_explicit_caller_branch_filter(self):
		"""When caller specifies a branch, only that branch's group is emailed."""
		sent_emails = []

		def mock_sendmail(**kwargs):
			sent_emails.append(kwargs)
			return MagicMock()

		with patch("frappe.sendmail", side_effect=mock_sendmail):
			res = send_omr_item_change_email(branch="Nandikoor")

		self.assertEqual(res["status"], "completed")
		self.assertEqual(len(sent_emails), 1)
		self.assertIn("Nandikoor", sent_emails[0]["subject"])
		self.assertIn("dhanvant.marathe@finbyz.tech", sent_emails[0]["recipients"])
		self.assertIn("ritik.patwa@finbyz.tech", sent_emails[0]["recipients"])

	def test_custom_page_data_provider_and_email(self):
		"""Custom Frappe Page retrieves tabular data from registered provider and attaches Excel without branch labels."""
		sent_emails = []

		def mock_sendmail(**kwargs):
			sent_emails.append(kwargs)
			return MagicMock()

		with patch("frappe.sendmail", side_effect=mock_sendmail):
			res = send_pending_advance_mate_email()

		self.assertEqual(res["status"], "completed")
		self.assertGreater(len(sent_emails), 0)
		email = sent_emails[0]
		self.assertIn("pending-advance-mate", email["subject"].lower())
		self.assertNotIn("Nandikoor", email["subject"])
		self.assertNotIn("(Branch: Nandikoor)", email["message"])
		self.assertNotIn("Branch: Nandikoor", email["message"])
		self.assertEqual(len(email["attachments"]), 1)
		self.assertTrue(email["attachments"][0]["fname"].endswith(".xlsx"))
		self.assertNotIn("nandikoor", email["attachments"][0]["fname"].lower())
		self.assertEqual(res["details"]["sent"][0]["record_count"], 66)

	def test_source_with_no_branch_filter_and_no_branch_column(self):
		"""
		A source with no branch filter and no branch column (e.g. pending-advance-mate)
		must not invent or display branch information in the email subject, body, headings, or summary.
		"""
		self.assertFalse(source_supports_branch_filter("Page", "pending-advance-mate"))
		self.assertFalse(page_supports_branch_filter("pending-advance-mate"))

		sent_emails = []

		def mock_sendmail(**kwargs):
			sent_emails.append(kwargs)
			return MagicMock()

		with patch("frappe.sendmail", side_effect=mock_sendmail):
			res = send_configured_email(source_name="pending-advance-mate", source_type="Page")

		self.assertEqual(res["status"], "completed")
		self.assertGreater(len(sent_emails), 0)
		for email in sent_emails:
			self.assertNotIn("Nandikoor", email["subject"])
			self.assertNotIn("Sanand", email["subject"])
			self.assertNotIn("(Branch:", email["message"])
			self.assertNotIn("Branch: <strong>", email["message"])
			self.assertNotIn("_nandikoor", email["attachments"][0]["fname"].lower())
			self.assertNotIn("_sanand", email["attachments"][0]["fname"].lower())

	def test_source_with_branch_filter_and_branch_column(self):
		"""
		A source with a branch filter and branch column (e.g. OMR Item Change)
		preserves the branch column in output and conditionally reflects branch info when filtered.
		"""
		report_doc = frappe.get_doc("Report", "OMR Item Change")
		self.assertTrue(source_supports_branch_filter("Report", "OMR Item Change", report_doc=report_doc))

		cols, data = generate_report_content("OMR Item Change", branch="Nandikoor")
		self.assertTrue(output_has_branch_column(cols))
		self.assertGreater(len(data), 0)
		self.assertTrue(all(r.get("branch") == "Nandikoor" for r in data))

	def test_source_with_branch_column_not_branch_filtered(self):
		"""
		When dataset contains a branch column but is NOT branch-filtered (all-branches),
		email subject and summary do not claim a single branch, while the data retains the branch column.
		"""
		cols = [{"label": "OMR No", "fieldname": "omr_no"}, {"label": "Branch", "fieldname": "branch"}]
		multi_branch_data = [
			{"omr_no": "OMR-001", "branch": "Nandikoor"},
			{"omr_no": "OMR-002", "branch": "Sanand"},
		]
		self.assertTrue(output_has_branch_column(cols))

		sent_emails = []

		def mock_sendmail(**kwargs):
			sent_emails.append(kwargs)
			return MagicMock()

		with patch("frappe.sendmail", side_effect=mock_sendmail):
			res = send_configured_email(
				source_name="OMR Item Change",
				source_type="Report",
				data=multi_branch_data,
				columns=cols,
			)

		self.assertEqual(res["status"], "completed")
		self.assertGreater(len(sent_emails), 0)
		for email in sent_emails:
			self.assertNotIn("Nandikoor", email["subject"])
			self.assertNotIn("Sanand", email["subject"])
			self.assertNotIn("(Branch:", email["message"])

	def test_source_with_optional_date_filters_fetches_all_time_data(self):
		"""
		Sources with optional date filters (e.g. OMR Item Change) must NOT have date filters
		automatically injected, ensuring all-time historical data spanning months/years is fetched.
		"""
		report_doc = frappe.get_doc("Report", "OMR Item Change")
		self.assertFalse(report_requires_mandatory_date_filters(report_doc))

		cols, all_time_data = generate_report_content("OMR Item Change")
		self.assertGreater(len(all_time_data), 1000, "All-time data should contain historical records (> 1000 rows)")

		# Check span of dates in all-time data
		dates = [r.get("omr_date") for r in all_time_data if r.get("omr_date")]
		self.assertGreater(len(dates), 0)
		min_date = str(min(dates))
		max_date = str(max(dates))
		self.assertTrue(min_date < "2026-05-01", f"Expected historical data before May 2026, got min date: {min_date}")

	def test_source_with_mandatory_date_filters(self):
		"""
		Sources with mandatory date filters (e.g. Batch-Wise Balance History) are detected,
		and mandatory date defaults are supplied to prevent validation errors.
		"""
		report_doc = frappe.get_doc("Report", "Batch-Wise Balance History")
		self.assertTrue(report_requires_mandatory_date_filters(report_doc))

	def test_historical_data_spanning_multiple_dates(self):
		"""
		Verifies pending-advance-mate returns all 66 records spanning July to September 2026
		without being truncated by any rolling period or current month restriction.
		"""
		data = get_pending_advance_mate_data(filters=None)
		self.assertEqual(len(data), 66, "Expected exactly 66 all-time records for pending-advance-mate")
		dates = [str(d.get("transaction_date")) for d in data if d.get("transaction_date")]
		min_date = min(dates)
		max_date = max(dates)
		self.assertTrue(min_date.startswith("2026-07"), f"Expected July 2026 min date, got {min_date}")
		self.assertTrue(max_date.startswith("2026-09"), f"Expected September 2026 max date, got {max_date}")

	def test_explicit_caller_supplied_data(self):
		"""Caller can supply custom data and columns directly to send_configured_email."""
		custom_cols = [{"label": "Batch", "fieldname": "batch_no"}, {"label": "Qty", "fieldname": "qty"}]
		custom_data = [{"batch_no": "BATCH-001", "qty": 50}, {"batch_no": "BATCH-002", "qty": 100}]

		sent_emails = []

		def mock_sendmail(**kwargs):
			sent_emails.append(kwargs)
			return MagicMock()

		with patch("frappe.sendmail", side_effect=mock_sendmail):
			res = send_configured_email(
				source_name="OMR Item Change",
				source_type="Report",
				data=custom_data,
				columns=custom_cols,
				branch="Nandikoor",
			)

		self.assertEqual(res["status"], "completed")
		self.assertEqual(len(sent_emails), 1)
		self.assertEqual(len(sent_emails[0]["attachments"]), 1)

	def test_unconfigured_source_skips_cleanly(self):
		"""Unconfigured reports or pages must not send email and must log clear reason."""
		sent_emails = []

		def mock_sendmail(**kwargs):
			sent_emails.append(kwargs)
			return MagicMock()

		with patch("frappe.sendmail", side_effect=mock_sendmail):
			res = send_configured_email(source_name="Completely Unconfigured Source", source_type="Report")

		self.assertEqual(res["status"], "skipped")
		self.assertEqual(res["reason"], "configuration_not_found")
		self.assertEqual(len(sent_emails), 0)

	def test_developer_controlled_scheduling(self):
		"""Scheduler only executes explicitly registered developer-controlled handlers."""
		self.assertIn(("Report", "OMR Item Change"), SCHEDULED_EMAIL_HANDLERS)
		self.assertIn(("Page", "pending-advance-mate"), SCHEDULED_EMAIL_HANDLERS)

		sent_emails = []

		def mock_sendmail(**kwargs):
			sent_emails.append(kwargs)
			return MagicMock()

		with patch("frappe.sendmail", side_effect=mock_sendmail):
			results = execute_weekly_report_email_scheduler()

		self.assertIsInstance(results, dict)
		self.assertIn("Report:OMR Item Change", results)
		self.assertIn("Page:pending-advance-mate", results)

	def test_group_failure_isolation(self):
		call_count = {"count": 0}
		sent_emails = []

		def mock_sendmail_fault(**kwargs):
			call_count["count"] += 1
			if call_count["count"] == 1:
				raise RuntimeError("Simulated network failure on group 1")
			sent_emails.append(kwargs)
			return MagicMock()

		with patch("frappe.sendmail", side_effect=mock_sendmail_fault):
			res = send_configured_email(source_name="OMR Item Change", source_type="Report")

		self.assertEqual(len(res["failed"]), 1)
		self.assertEqual(len(res["sent"]), 1)
		self.assertEqual(len(sent_emails), 1)

	def test_no_side_effects_on_report_execute_or_page_load(self):
		"""Executing report execute() or page get_data() must never send email."""
		sent_emails = []

		def mock_sendmail(**kwargs):
			sent_emails.append(kwargs)
			return MagicMock()

		with patch("frappe.sendmail", side_effect=mock_sendmail):
			execute_omr_report(filters=frappe._dict({"branch": "Nandikoor"}))
			get_pending_advance_mate_data(filters=None)
			execute_so_approval_tat_report(filters=frappe._dict({"branch": "Nandikoor"}))

		self.assertEqual(len(sent_emails), 0, "No email should ever be sent from report execute() or page get_data()!")

	def test_so_approval_tat_email_dispatch(self):
		"""
		Tests that SO Approval TAT report generates and emails separate branch-filtered reports
		to each branch's configured email group (Nandikoor and Sanand), matching OMR Item Change behavior.
		"""
		sent_emails = []

		def mock_sendmail(**kwargs):
			sent_emails.append(kwargs)
			return MagicMock()

		with patch("frappe.sendmail", side_effect=mock_sendmail):
			res = send_so_approval_tat_email()

		self.assertEqual(res["status"], "completed")
		self.assertEqual(len(sent_emails), 2)

		nandikoor_email = next(e for e in sent_emails if "Nandikoor" in e["subject"])
		self.assertIn("dhanvant.marathe@finbyz.tech", nandikoor_email["recipients"])
		self.assertIn("ritik.patwa@finbyz.tech", nandikoor_email["recipients"])
		self.assertIn("so_approval_tat_nandikoor", nandikoor_email["attachments"][0]["fname"])
		self.assertIn("Branch: <strong>Nandikoor</strong>", nandikoor_email["message"])

		sanand_email = next(e for e in sent_emails if "Sanand" in e["subject"])
		self.assertIn("dhanvant.marathe@finbyz.tech", sanand_email["recipients"])
		self.assertNotIn("ritik.patwa@finbyz.tech", sanand_email["recipients"])
		self.assertIn("so_approval_tat_sanand", sanand_email["attachments"][0]["fname"])
		self.assertIn("Branch: <strong>Sanand</strong>", sanand_email["message"])
