# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import json
import os
from datetime import datetime
import frappe
from frappe import _
from frappe.utils import (
	add_months,
	cint,
	format_datetime,
	formatdate,
	get_url,
	now_datetime,
	today,
)
from generate_item.generate_item.doctype.report_email_master.report_email_master import (
	resolve_group_recipients,
)


def get_logger():
	return frappe.logger("report_email_scheduler")


def get_all_branches():
	"""
	Dynamically retrieve all active branches configured in the system.
	Does not hardcode any branch name.
	"""
	if not frappe.db.table_exists("Branch"):
		return []

	meta = frappe.get_meta("Branch")
	filters = {}
	if meta.has_field("disabled"):
		filters["disabled"] = 0
	elif meta.has_field("enabled"):
		filters["enabled"] = 1

	return frappe.get_all("Branch", filters=filters, pluck="name", order_by="name asc")


def get_report_email_master_config(source_type, name):
	"""
	Lookup the active Report Email Master configuration for a given type and name.
	Supports:
	- type='Report': matches source='Report' and report_name=name
	- type='Dashboard': matches source in ('Dashboard', 'Page') and page_name=name (or report_name=name)
	"""
	if not source_type or not name:
		return None

	target_source = "Report" if source_type == "Report" else "Dashboard"

	# Try exact match on field values
	if target_source == "Report":
		masters = frappe.get_all(
			"Report Email Master",
			filters={"type": "Master", "source": "Report", "report_name": name},
			pluck="name",
		)
	else:
		masters = frappe.get_all(
			"Report Email Master",
			filters={
				"type": "Master",
				"source": ["in", ["Dashboard", "Page"]],
				"page_name": name,
			},
			pluck="name",
		)
		if not masters:
			masters = frappe.get_all(
				"Report Email Master",
				filters={"type": "Master", "source": "Dashboard", "report_name": name},
				pluck="name",
			)

	# Fallback match by document name (e.g. "Report-Pending Advanced Material Request")
	if not masters:
		composite_name = f"{source_type}-{name}"
		if frappe.db.exists("Report Email Master", composite_name):
			doc = frappe.get_doc("Report Email Master", composite_name)
			if doc.type == "Master":
				return doc

	if masters:
		return frappe.get_doc("Report Email Master", masters[0])

	return None


def report_supports_branch_filter(report_doc):
	"""
	Inspects report filters, query, and ref_doctype to check whether
	the report supports a 'branch' filter.
	"""
	if not report_doc:
		return False

	# 1. Check if filters JSON or report fields explicitly define branch
	if report_doc.filters:
		try:
			filters_data = json.loads(report_doc.filters) if isinstance(report_doc.filters, str) else report_doc.filters
			if isinstance(filters_data, list):
				for flt in filters_data:
					if isinstance(flt, dict) and flt.get("fieldname") == "branch":
						return True
			elif isinstance(filters_data, dict) and "branch" in filters_data:
				return True
		except Exception:
			pass

	# 2. Check if ref_doctype has a branch field
	if report_doc.ref_doctype and frappe.db.table_exists(report_doc.ref_doctype):
		meta = frappe.get_meta(report_doc.ref_doctype)
		if meta and meta.has_field("branch"):
			return True

	# 3. Check query string in Query Report
	if report_doc.report_type == "Query Report" and report_doc.query:
		if "branch" in report_doc.query.lower():
			return True

	return False


def report_has_date_filters(report_doc):
	"""
	Checks whether the report defines from_date and to_date filters.
	Inspects report.filters JSON and the report's client-side .js file.
	"""
	if not report_doc:
		return False

	# 1. Check report.filters JSON
	if report_doc.filters:
		try:
			filters_data = json.loads(report_doc.filters) if isinstance(report_doc.filters, str) else report_doc.filters
			if isinstance(filters_data, list):
				for flt in filters_data:
					if isinstance(flt, dict) and flt.get("fieldname") in ("from_date", "to_date"):
						return True
		except Exception:
			pass

	# 2. Check report .js file
	try:
		mod_path = frappe.get_module_path(report_doc.module, "report", frappe.scrub(report_doc.name))
		js_file = os.path.join(mod_path, frappe.scrub(report_doc.name) + ".js")
		if os.path.exists(js_file):
			with open(js_file, "r", encoding="utf-8") as f:
				content = f.read()
				if "from_date" in content and "to_date" in content:
					return True
	except Exception:
		pass

	return False


def generate_report_content(report_name, branch=None, filters=None, supports_branch=None):
	"""
	Executes the report and returns (columns, data).
	- Branch is optional. If the report supports a branch filter and branch is provided, applies filters["branch"] = branch.
	- Date filters (from_date / to_date) are automatically defaulted to the standard 1-month range (matching Desk UI)
	  if the report defines date filters and they are not explicitly supplied.
	- Deduplicates data rows while preserving order to ensure 100% data accuracy.
	"""
	if not frappe.db.exists("Report", report_name):
		frappe.throw(_("Report '{0}' does not exist.").format(report_name))

	report = frappe.get_doc("Report", report_name)
	report_filters = frappe._dict(filters or {})

	if supports_branch is None:
		supports_branch = report_supports_branch_filter(report)

	# Only apply branch filter if report actually supports it and branch is specified
	if supports_branch and branch:
		report_filters["branch"] = branch

	# Default date filters (from_date: 1 month ago, to_date: today) if the report defines date filters
	if report_has_date_filters(report):
		if "to_date" not in report_filters:
			report_filters["to_date"] = today()
		if "from_date" not in report_filters:
			report_filters["from_date"] = add_months(today(), -1)

	# Default company if report doctype uses company and not specified
	if "company" not in report_filters:
		default_company = frappe.defaults.get_global_default("company")
		if default_company and report.ref_doctype and frappe.db.table_exists(report.ref_doctype):
			meta = frappe.get_meta(report.ref_doctype)
			if meta and meta.has_field("company"):
				report_filters["company"] = default_company

	columns, data = report.get_data(
		user="Administrator",
		filters=report_filters,
		as_dict=True,
		ignore_prepared_report=True,
		are_default_filters=bool(not filters),
	)

	# Ensure data rows are unique while preserving order
	seen_keys = set()
	unique_data = []
	for row in (data or []):
		if isinstance(row, dict):
			key = tuple(sorted((k, str(v)) for k, v in row.items()))
		elif isinstance(row, (list, tuple)):
			key = tuple(str(x) for x in row)
		else:
			key = row

		if key not in seen_keys:
			seen_keys.add(key)
			unique_data.append(row)

	return columns or [], unique_data


def build_report_excel_attachment(report_name, columns, data, branch=None):
	"""
	Builds an Excel (.xlsx) file attachment from report data using Frappe's xlsxutils.
	Compatible with Frappe v15 and v16 make_xlsx(data, sheet_name).
	"""
	from frappe.utils.xlsxutils import make_xlsx

	# Extract column headers and fieldnames
	headers = []
	fieldnames = []
	for col in columns:
		if isinstance(col, dict):
			headers.append(col.get("label") or col.get("fieldname") or "")
			fieldnames.append(col.get("fieldname"))
		elif isinstance(col, str):
			headers.append(col)
			fieldnames.append(col)

	rows = [headers] if headers else []
	for row in data:
		if isinstance(row, dict):
			rows.append([row.get(fld, "") for fld in fieldnames])
		elif isinstance(row, (list, tuple)):
			rows.append(list(row))

	sheet_name = (report_name[:28] if report_name else "Report").replace("/", "-")
	xlsx_file = make_xlsx(rows, sheet_name)

	clean_name = frappe.scrub(report_name)
	branch_suffix = f"_{frappe.scrub(branch)}" if branch else ""
	date_suffix = today()
	file_name = f"{clean_name}{branch_suffix}_{date_suffix}.xlsx"

	return {
		"fname": file_name,
		"fcontent": xlsx_file.getvalue(),
	}


def build_report_email_html(report_name, columns, data, branch=None):
	"""
	Prepares an HTML email body with summary cards and a formatted preview table.
	"""
	company_name = frappe.defaults.get_global_default("company") or "Company"
	total_rows = len(data)
	branch_label = f" (Branch: {branch})" if branch else ""

	# Render preview table for up to 15 rows
	preview_rows = data[:15]
	col_headers = [c.get("label") or c.get("fieldname") or "" for c in columns if isinstance(c, dict)][:8]
	col_fields = [c.get("fieldname") for c in columns if isinstance(c, dict)][:8]

	table_header_html = "".join(
		f'<th style="padding: 10px 12px; background-color: #1a5276; color: #ffffff; border: 1px solid #154360; text-align: left; font-size: 13px;">{h}</th>'
		for h in col_headers
	)

	table_rows_html = ""
	for idx, row in enumerate(preview_rows):
		bg = "#ffffff" if idx % 2 == 0 else "#f8f9fa"
		tds = ""
		for fld in col_fields:
			val = row.get(fld, "")
			if isinstance(val, (int, float)):
				val_str = f"{val:,.2f}" if isinstance(val, float) else f"{val:,}"
				align = "right"
			else:
				val_str = frappe.utils.escape_html(str(val) if val is not None else "")
				align = "left"
			tds += f'<td style="padding: 8px 12px; border: 1px solid #dee2e6; text-align: {align}; font-size: 13px;">{val_str}</td>'
		table_rows_html += f'<tr style="background-color: {bg};">{tds}</tr>'

	preview_note = ""
	if total_rows > len(preview_rows):
		preview_note = f"""
		<p style="margin-top: 10px; font-size: 13px; color: #6c757d; font-style: italic;">
			* Showing preview of first {len(preview_rows)} of {total_rows:,} records. Please open the attached Excel file for complete details.
		</p>
		"""

	return f"""
	<!DOCTYPE html>
	<html>
	<head>
		<meta charset="UTF-8">
		<style>
			body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; color: #333333; margin: 0; padding: 20px; background-color: #f4f6f9; }}
			.container {{ max-width: 900px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.06); border: 1px solid #dee2e6; }}
			.header {{ background-color: #1a5276; color: #ffffff; padding: 25px; }}
			.content {{ padding: 25px; background-color: #ffffff; }}
			.badge {{ display: inline-block; padding: 4px 10px; background-color: #eaf2f8; color: #1a5276; border-radius: 4px; font-weight: 600; font-size: 12px; }}
			.summary-box {{ background-color: #f8f9fa; border-left: 4px solid #1a5276; padding: 15px; margin: 20px 0; border-radius: 0 4px 4px 0; }}
			.footer {{ background-color: #f8f9fa; padding: 15px 25px; font-size: 12px; color: #6c757d; text-align: center; border-top: 1px solid #dee2e6; }}
		</style>
	</head>
	<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; color: #333333; margin: 0; padding: 20px; background-color: #f4f6f9;">
		<div class="container" style="max-width: 900px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; border: 1px solid #dee2e6;">
			<div class="header" style="background-color: #1a5276; color: #ffffff; padding: 25px 25px 20px 25px; text-align: left;">
				<h3 style="margin: 0 0 6px 0; font-size: 13px; text-transform: uppercase; letter-spacing: 1px; color: #d0e1fd !important; font-weight: 600;">{company_name}</h3>
				<h1 style="margin: 0 0 8px 0; font-size: 22px; color: #ffffff !important; font-weight: 700; line-height: 1.3;">Weekly Report: {report_name}</h1>
				<p style="margin: 0; font-size: 13px; color: #eaf2f8 !important; opacity: 0.95;">Generated on {format_datetime(now_datetime(), "dd-MM-yyyy HH:mm")}{branch_label}</p>
			</div>

			<div class="content" style="padding: 25px; background-color: #ffffff; color: #333333;">
				<p style="font-size: 15px; margin-top: 0;">Dear Team,</p>
				<p style="font-size: 14px; line-height: 1.6; color: #333333;">
					Please find attached the weekly report for <strong>{report_name}</strong>{branch_label}.
				</p>

				<div class="summary-box" style="background-color: #f8f9fa; border-left: 4px solid #1a5276; padding: 15px; margin: 20px 0; border-radius: 0 4px 4px 0;">
					<table style="width: 100%; border-collapse: collapse;">
						<tr>
							<td style="font-size: 14px; color: #555555;">Total Records: <strong>{total_rows:,}</strong></td>
							{"<td style='font-size: 14px; color: #555555;'>Branch: <strong>" + branch + "</strong></td>" if branch else ""}
							<td style="font-size: 14px; color: #555555; text-align: right;">Attachment: <strong>Excel (.xlsx)</strong></td>
						</tr>
					</table>
				</div>

				{"<h3 style='margin: 20px 0 10px 0; font-size: 16px; color: #1a5276;'>Preview</h3><div style='overflow-x: auto;'><table style='width: 100%; border-collapse: collapse; margin-top: 10px;'><thead><tr>" + table_header_html + "</tr></thead><tbody>" + table_rows_html + "</tbody></table></div>" + preview_note if preview_rows else "<p style='color: #6c757d;'>No records found for this period.</p>"}
			</div>

			<div class="footer" style="background-color: #f8f9fa; padding: 15px 25px; font-size: 12px; color: #6c757d; text-align: center; border-top: 1px solid #dee2e6;">
				<p style="margin: 0;">This is an automated weekly email sent by the Report Scheduler.</p>
				<p style="margin: 5px 0 0 0;">&copy; {now_datetime().year} {company_name}. All rights reserved.</p>
			</div>
		</div>
	</body>
	</html>
	"""


def get_dashboard_title(dashboard_name):
	"""
	Resolves human-readable title for a dashboard or page.
	First checks Page.title, then Dashboard.dashboard_name, then falls back to title-cased string.
	"""
	if not dashboard_name:
		return ""

	clean_name = dashboard_name.strip()

	# Check Page title
	if frappe.db.table_exists("Page"):
		page_title = frappe.db.get_value("Page", clean_name, "title")
		if page_title and str(page_title).strip():
			return str(page_title).strip()

	# Check Dashboard name
	if frappe.db.table_exists("Dashboard"):
		dash_title = frappe.db.get_value("Dashboard", clean_name, "dashboard_name")
		if dash_title and str(dash_title).strip():
			return str(dash_title).strip()

	# Fallback: convert slug like "pending-advance-mate" -> "Pending Advance Mate"
	clean = clean_name.replace("-", " ").replace("_", " ").strip()
	return clean.title()


def build_dashboard_email_html(dashboard_name, dashboard_url, branch=None):
	"""
	Prepares an executive dashboard email with direct Desk link.
	"""
	company_name = frappe.defaults.get_global_default("company") or "Company"
	branch_label = f" (Branch: {branch})" if branch else ""
	dashboard_title = get_dashboard_title(dashboard_name)

	return f"""
	<!DOCTYPE html>
	<html>
	<head>
		<meta charset="UTF-8">
		<style>
			body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; color: #333333; margin: 0; padding: 20px; background-color: #f4f6f9; }}
			.container {{ max-width: 750px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.06); border: 1px solid #dee2e6; }}
			.header {{ background-color: #1a5276; color: #ffffff; padding: 25px; text-align: center; }}
			.content {{ padding: 30px; text-align: center; background-color: #ffffff; }}
			.card {{ background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 25px; margin: 20px 0; }}
			.btn {{ display: inline-block; padding: 12px 30px; background-color: #1a5276; color: #ffffff !important; text-decoration: none; border-radius: 4px; font-weight: bold; font-size: 15px; margin-top: 15px; }}
			.footer {{ background-color: #f8f9fa; padding: 15px 25px; font-size: 12px; color: #6c757d; text-align: center; border-top: 1px solid #dee2e6; }}
		</style>
	</head>
	<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; color: #333333; margin: 0; padding: 20px; background-color: #f4f6f9;">
		<div class="container" style="max-width: 750px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; border: 1px solid #dee2e6;">
			<div class="header" style="background-color: #1a5276; color: #ffffff; padding: 25px 25px 20px 25px; text-align: center;">
				<h3 style="margin: 0 0 6px 0; font-size: 13px; text-transform: uppercase; letter-spacing: 1px; color: #d0e1fd !important; font-weight: 600;">{company_name}</h3>
				<h1 style="margin: 0 0 8px 0; font-size: 22px; color: #ffffff !important; font-weight: 700; line-height: 1.3;">Weekly Dashboard: {dashboard_title}</h1>
				<p style="margin: 0; font-size: 13px; color: #eaf2f8 !important; opacity: 0.95;">Generated on {format_datetime(now_datetime(), "dd-MM-yyyy HH:mm")}{branch_label}</p>
			</div>

			<div class="content" style="padding: 30px; text-align: center; background-color: #ffffff;">
				<p style="font-size: 16px; margin-top: 0; color: #333333;">Dear Team,</p>
				<p style="font-size: 14px; color: #555555; line-height: 1.6;">
					Your weekly <strong>{dashboard_title}</strong> metrics and dashboard views are ready for review{branch_label}.
				</p>

				<div class="card" style="background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 25px; margin: 20px 0;">
					<div style="font-size: 40px; margin-bottom: 10px;">📊</div>
					<h2 style="margin: 0 0 10px 0; color: #1a5276; font-size: 20px; font-weight: 700;">{dashboard_title}</h2>
					{"<p style='margin: 0 0 10px 0; color: #6c757d; font-size: 14px;'>Branch: <strong>" + branch + "</strong></p>" if branch else ""}
					<a href="{dashboard_url}" class="btn" target="_blank" style="display: inline-block; padding: 12px 30px; background-color: #1a5276; color: #ffffff !important; text-decoration: none; border-radius: 4px; font-weight: bold; font-size: 15px; margin-top: 15px;">View Live Dashboard</a>
				</div>

				<p style="font-size: 13px; color: #7f8c8d; margin-top: 20px;">
					Click the button above to view live metrics, charts, and key performance indicators in the ERPNext Desk.
				</p>
			</div>

			<div class="footer" style="background-color: #f8f9fa; padding: 15px 25px; font-size: 12px; color: #6c757d; text-align: center; border-top: 1px solid #dee2e6;">
				<p style="margin: 0;">This is an automated weekly email sent by the Dashboard Scheduler.</p>
				<p style="margin: 5px 0 0 0;">&copy; {now_datetime().year} {company_name}. All rights reserved.</p>
			</div>
		</div>
	</body>
	</html>
	"""


def resolve_recipients_for_branch(master, branch=None, cached_groups=None):
	"""
	Resolves To and CC recipients for a given branch from the Master's configured groups.
	Deduplicates email addresses and ensures no CC overlaps with To.
	"""
	cached_groups = cached_groups or {}
	to_raw = []
	cc_raw = []

	# Find groups that match this branch or are global (branch is None/empty)
	for row in master.email_group:
		group_name = row.group_name
		if not group_name:
			continue

		group_doc = cached_groups.get(group_name)
		if not group_doc:
			try:
				group_doc = frappe.get_doc("Report Email Master", group_name)
				cached_groups[group_name] = group_doc
			except Exception:
				continue

		# A group applies to this branch if:
		# 1. group_doc.branch matches the current branch, OR
		# 2. group_doc has no branch configured (company-wide group)
		group_branch = (group_doc.branch or "").strip()
		if branch and group_branch and group_branch != branch:
			continue

		res = resolve_group_recipients(group_name)
		to_raw.extend(res.get("to", []))
		cc_raw.extend(res.get("cc", []))

	# Deduplicate To
	seen_to = set()
	unique_to = []
	for email in to_raw:
		clean = (email or "").strip().lower()
		if clean and clean not in seen_to:
			seen_to.add(clean)
			unique_to.append(email.strip())

	# Deduplicate CC (excluding any that exist in To)
	seen_cc = set()
	unique_cc = []
	for email in cc_raw:
		clean = (email or "").strip().lower()
		if clean and clean not in seen_to and clean not in seen_cc:
			seen_cc.add(clean)
			unique_cc.append(email.strip())

	return {"to": unique_to, "cc": unique_cc}


def send_weekly_report_email(type, name):
	"""
	Global reusable Python function to generate a report or dashboard,
	prepare an email draft, retrieve recipients from Report Email Master,
	and send branch-wise emails.

	Parameters:
	- type: 'Report' or 'Dashboard'
	- name: the name of the Report or Dashboard
	"""
	logger = get_logger()
	type_clean = (type or "").strip()
	name_clean = (name or "").strip()

	if type_clean not in ("Report", "Dashboard", "Page"):
		frappe.throw(_("Invalid type '{0}'. Type must be 'Report' or 'Dashboard'.").format(type_clean))

	if not name_clean:
		frappe.throw(_("Report/Dashboard name is required."))

	logger.info(f"Starting weekly email process for {type_clean} '{name_clean}'.")

	# 1. Retrieve Report Email Master configuration
	master = get_report_email_master_config(type_clean, name_clean)
	if not master:
		logger.warning(
			f"No Report Email Master configuration found for {type_clean} '{name_clean}'. Skipping execution."
		)
		return {"status": "skipped", "reason": "configuration_not_found"}

	if not master.email_group:
		logger.warning(
			f"Report Email Master '{master.name}' has no Email Groups configured. Skipping execution."
		)
		return {"status": "skipped", "reason": "no_email_groups"}

	# Pre-load all linked Group documents once for performance
	cached_groups = {}
	configured_group_branches = set()
	has_global_groups = False

	for row in master.email_group:
		if row.group_name and row.group_name not in cached_groups:
			try:
				gdoc = frappe.get_doc("Report Email Master", row.group_name)
				cached_groups[row.group_name] = gdoc
				if gdoc.branch and gdoc.branch.strip():
					configured_group_branches.add(gdoc.branch.strip())
				else:
					has_global_groups = True
			except Exception as e:
				logger.error(f"Failed to load group '{row.group_name}': {str(e)}")

	# 2. Get All Branches dynamically
	all_branches = get_all_branches()

	# Determine branch-wise execution mode:
	# If branches are configured in groups or in system, we process branch-wise.
	supports_branch = False
	report_doc = None

	if type_clean == "Report":
		if not frappe.db.exists("Report", name_clean):
			logger.error(f"Report '{name_clean}' does not exist in the system.")
			return {"status": "error", "reason": "report_not_found"}
		report_doc = frappe.get_doc("Report", name_clean)
		supports_branch = report_supports_branch_filter(report_doc)

	# Decide which branches to process:
	# If email groups explicitly define branches, process those configured branches.
	# If no group has a branch configured, process once globally with branch=None (no branch filter).
	if configured_group_branches:
		branches_to_process = list(configured_group_branches)
	else:
		branches_to_process = [None]

	# Branch optimization: If report does NOT support branch filtering,
	# generate the content ONCE and reuse it across all branches.
	cached_report_content = None
	if type_clean == "Report" and not supports_branch:
		try:
			cached_report_content = generate_report_content(name_clean, branch=None, supports_branch=False)
		except Exception as e:
			logger.error(f"Failed to generate report '{name_clean}': {str(e)}")
			frappe.log_error(frappe.get_traceback(), f"Weekly Report Generation Failed: {name_clean}")
			return {"status": "error", "reason": "generation_failed"}

	branches_sent = []
	branches_skipped = []
	branches_failed = []

	# 3. Branch-wise processing loop
	for branch in branches_to_process:
		try:
			# Resolve recipients for this branch
			recipients = resolve_recipients_for_branch(master, branch=branch, cached_groups=cached_groups)
			to_emails = recipients.get("to", [])
			cc_emails = recipients.get("cc", [])

			if not to_emails:
				logger.warning(
					f"No valid To recipients configured for {type_clean} '{name_clean}' (Branch: '{branch or 'All'}'). Skipping send."
				)
				branches_skipped.append(branch or "Global")
				continue

			# Generate branch-specific content and draft
			attachments = None

			if type_clean == "Report":
				if supports_branch:
					columns, data = generate_report_content(name_clean, branch=branch, supports_branch=True)
				else:
					columns, data = cached_report_content

				# Build Excel attachment and HTML preview
				excel_attachment = build_report_excel_attachment(name_clean, columns, data, branch=branch)
				attachments = [excel_attachment]
				message_html = build_report_email_html(name_clean, columns, data, branch=branch)
				subject_branch = f" - {branch}" if branch else ""
				subject = f"Weekly Report: {name_clean}{subject_branch} - {today()}"

			else:
				# Dashboard handling
				dashboard_title = get_dashboard_title(name_clean)
				dashboard_route = frappe.scrub(name_clean).replace("_", "-")
				dashboard_url = f"{get_url()}/desk/{dashboard_route}"
				if branch:
					dashboard_url += f"?branch={frappe.utils.quote(branch)}"

				message_html = build_dashboard_email_html(name_clean, dashboard_url, branch=branch)
				subject_branch = f" - {branch}" if branch else ""
				subject = f"Weekly Dashboard: {dashboard_title}{subject_branch} - {today()}"

			# Send Email
			frappe.sendmail(
				recipients=to_emails,
				cc=cc_emails,
				subject=subject,
				message=message_html,
				attachments=attachments,
				reference_doctype="Report Email Master",
				reference_name=master.name,
				delayed=False,
			)

			logger.info(
				f"Successfully sent weekly email for {type_clean} '{name_clean}' (Branch: '{branch or 'Global'}') to {len(to_emails)} To, {len(cc_emails)} CC."
			)
			branches_sent.append(branch or "Global")

		except Exception as branch_err:
			# A failure for one branch must not prevent processing the remaining branches
			logger.error(
				f"Failed to send weekly email for {type_clean} '{name_clean}' (Branch: '{branch}'): {str(branch_err)}"
			)
			frappe.log_error(
				frappe.get_traceback(),
				f"Weekly Email Failed: {type_clean} '{name_clean}' - Branch: {branch}",
			)
			branches_failed.append(branch or "Global")

	return {
		"status": "completed",
		"sent": branches_sent,
		"skipped": branches_skipped,
		"failed": branches_failed,
	}


def execute_weekly_report_email_scheduler():
	"""
	Central scheduler entry point registered under scheduler_events['weekly'].
	Dynamically processes all configured Master records in Report Email Master.
	Does not hardcode report or dashboard names.
	"""
	logger = get_logger()
	logger.info("Executing weekly report email scheduler...")

	try:
		# Retrieve all configured Master records
		masters = frappe.get_all(
			"Report Email Master",
			filters={"type": "Master"},
			fields=["name", "source", "report_name", "page_name"],
		)

		if not masters:
			logger.info("No active Master configurations found in Report Email Master.")
			return

		processed_targets = set()

		for master_rec in masters:
			source = master_rec.get("source")
			report_name = master_rec.get("report_name")
			page_name = master_rec.get("page_name")

			if source == "Report" and report_name:
				target_type = "Report"
				target_name = report_name.strip()
			elif source in ("Dashboard", "Page") and page_name:
				target_type = "Dashboard"
				target_name = page_name.strip()
			elif report_name:
				target_type = "Report"
				target_name = report_name.strip()
			elif page_name:
				target_type = "Dashboard"
				target_name = page_name.strip()
			else:
				continue

			# Avoid processing the exact same (type, name) more than once per execution
			key = (target_type, target_name)
			if key in processed_targets:
				continue
			processed_targets.add(key)

			try:
				send_weekly_report_email(type=target_type, name=target_name)
			except Exception as master_err:
				logger.error(f"Error processing {target_type} '{target_name}': {str(master_err)}")
				frappe.log_error(
					frappe.get_traceback(),
					f"Weekly Scheduler Failed: {target_type} {target_name}",
				)

		logger.info(f"Weekly report email scheduler finished. Processed {len(processed_targets)} configurations.")

	except Exception as e:
		logger.error(f"Fatal error in execute_weekly_report_email_scheduler: {str(e)}")
		frappe.log_error(frappe.get_traceback(), "Weekly Report Email Scheduler Fatal Error")
