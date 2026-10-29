# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import json
import os
import re
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


def output_has_branch_column(columns):
	"""Checks whether the dataset columns include a 'branch' column."""
	if not columns:
		return False
	for col in columns:
		if isinstance(col, dict):
			fieldname = (col.get("fieldname") or "").strip().lower()
			label = (col.get("label") or "").strip().lower()
			if fieldname == "branch" or label == "branch":
				return True
		elif isinstance(col, str) and col.strip().lower() == "branch":
			return True
	return False


def page_supports_branch_filter(page_name):
	"""
	Inspects whether a custom Page explicitly accepts and filters by 'branch'.
	"""
	if not page_name:
		return False

	clean_name = page_name.strip()

	# 1. Check registered page provider
	for key in (clean_name, frappe.scrub(clean_name), clean_name.replace("_", "-"), clean_name.replace("-", "_")):
		if key in PAGE_DATA_PROVIDERS:
			provider = PAGE_DATA_PROVIDERS[key]
			if getattr(provider, "supports_branch", False):
				return True

	# 2. Check page controller python / js file
	try:
		if frappe.db.table_exists("Page") and frappe.db.exists("Page", clean_name):
			page_doc = frappe.get_doc("Page", clean_name)
			if page_doc and page_doc.module:
				scrubbed = frappe.scrub(clean_name)
				mod_path = frappe.get_module_path(page_doc.module, "page", scrubbed)
				py_file = os.path.join(mod_path, scrubbed + ".py")
				if os.path.exists(py_file):
					with open(py_file, "r", encoding="utf-8") as f:
						content = f.read()
						if (
							'filters.get("branch")' in content
							or "filters.get('branch')" in content
							or 'branch=None' in content
							or ('branch' in content and 'conditions.append' in content)
						):
							return True
				js_file = os.path.join(mod_path, scrubbed + ".js")
				if os.path.exists(js_file):
					with open(js_file, "r", encoding="utf-8") as f:
						content = f.read()
						if '"branch"' in content or "'branch'" in content:
							return True
	except Exception:
		pass

	return False


def report_supports_branch_filter(report_doc):
	"""
	Inspects report filters, query, and ref_doctype to check whether
	the report explicitly supports and applies a 'branch' filter.
	"""
	if not report_doc:
		return False

	# 1. Check if filters JSON explicitly defines branch
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

	# 2. Check query string in Query Report
	if report_doc.report_type == "Query Report" and report_doc.query:
		q_lower = report_doc.query.lower()
		if "%(branch)s" in q_lower or "branch" in q_lower:
			return True

	# 3. Check report client and server source files for branch filter definitions
	if report_doc.report_type == "Script Report" and report_doc.module:
		try:
			mod_path = frappe.get_module_path(report_doc.module, "report", frappe.scrub(report_doc.name))
			js_file = os.path.join(mod_path, frappe.scrub(report_doc.name) + ".js")
			if os.path.exists(js_file):
				with open(js_file, "r", encoding="utf-8") as f:
					content = f.read()
					if '"branch"' in content or "'branch'" in content:
						return True

			py_file = os.path.join(mod_path, frappe.scrub(report_doc.name) + ".py")
			if os.path.exists(py_file):
				with open(py_file, "r", encoding="utf-8") as f:
					content = f.read()
					if (
						'filters.get("branch")' in content
						or "filters.get('branch')" in content
						or 'filters.branch' in content
						or '%(branch)s' in content
					):
						return True
		except Exception:
			pass

	# 4. Standard Report Builder reports: check if ref_doctype has a branch field
	if report_doc.report_type == "Report Builder" and report_doc.ref_doctype and frappe.db.table_exists(report_doc.ref_doctype):
		meta = frappe.get_meta(report_doc.ref_doctype)
		if meta and meta.has_field("branch"):
			return True

	return False


def source_supports_branch_filter(source_type, source_name, report_doc=None):
	"""
	Determines whether a Report or Page explicitly supports a 'branch' filter.
	Returns True only if the source accepts and applies branch-wise filtering.
	"""
	if not source_name:
		return False

	clean_type = (source_type or "").strip()
	clean_name = (source_name or "").strip()

	if clean_type == "Report":
		if not report_doc and frappe.db.exists("Report", clean_name):
			report_doc = frappe.get_doc("Report", clean_name)
		return report_supports_branch_filter(report_doc)

	elif clean_type in ("Page", "Dashboard"):
		return page_supports_branch_filter(clean_name)

	return False


def report_requires_mandatory_date_filters(report_doc):
	"""
	Checks whether date filters (from_date, to_date, start_date, end_date)
	are mandatory (reqd: 1 or explicit validation) for this report.
	Returns False for reports with optional date filters to ensure all-time data is fetched.
	"""
	if not report_doc:
		return False

	# 1. Check report.filters JSON
	if report_doc.filters:
		try:
			flts = json.loads(report_doc.filters) if isinstance(report_doc.filters, str) else report_doc.filters
			if isinstance(flts, list):
				for f in flts:
					if isinstance(f, dict) and f.get("fieldname") in ("from_date", "to_date", "start_date", "end_date"):
						if f.get("reqd") in (1, "1", True):
							return True
		except Exception:
			pass

	# 2. Check Script Report JS and Python files
	if report_doc.report_type == "Script Report" and report_doc.module:
		try:
			mod_path = frappe.get_module_path(report_doc.module, "report", frappe.scrub(report_doc.name))
			js_file = os.path.join(mod_path, frappe.scrub(report_doc.name) + ".js")
			if os.path.exists(js_file):
				with open(js_file, "r", encoding="utf-8") as f:
					js_content = f.read()
					for block in re.findall(
						r"\{[^{}]*fieldname\s*:\s*[\'\"](?:from_date|to_date|start_date|end_date)[\'\"][^{}]*\}",
						js_content,
						re.DOTALL,
					):
						if re.search(r"reqd\s*:\s*1", block) or re.search(r"reqd\s*:\s*true", block):
							return True

			py_file = os.path.join(mod_path, frappe.scrub(report_doc.name) + ".py")
			if os.path.exists(py_file):
				with open(py_file, "r", encoding="utf-8") as f:
					py_content = f.read()
					if "validate_mandatory_date_range" in py_content:
						return True
					if re.search(
						r"if\s+not\s+filters\.get\([\'\"](?:from_date|to_date)[\'\"]\)\s*:\s*frappe\.throw",
						py_content,
					):
						return True
		except Exception:
			pass

	return False


def generate_report_content(report_name, branch=None, filters=None, supports_branch=None):
	"""
	Executes the report and returns (columns, data).
	- Fetches all-time data by default, subject only to legitimate default and mandatory filters.
	- Does NOT automatically inject date filters unless required by the report's mandatory logic.
	- Branch is optional. If the report supports a branch filter and branch is provided, applies filters["branch"] = branch.
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

	# All-Time Data Requirement:
	# Only pass date filters if mandatory for this report's execution.
	# If date filters are optional, omit from_date/to_date so all-time data is fetched.
	if report_requires_mandatory_date_filters(report):
		if "to_date" not in report_filters:
			report_filters["to_date"] = today()
		if "from_date" not in report_filters:
			try:
				from erpnext.accounts.utils import get_fiscal_year
				fy = get_fiscal_year(today(), company=report_filters.get("company"))
				report_filters["from_date"] = str(fy[1])
			except Exception:
				report_filters["from_date"] = "1900-01-01"

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


def resolve_recipients_for_group(group_doc_or_name):
	"""
	Resolves To and CC recipients for an individual Email Group.
	Ensures To emails are deduplicated, CC emails are deduplicated,
	and CC does not overlap with To.
	"""
	if not group_doc_or_name:
		return {"to": [], "cc": []}

	if isinstance(group_doc_or_name, str):
		try:
			group_doc = frappe.get_doc("Report Email Master", group_doc_or_name)
		except Exception:
			return {"to": [], "cc": []}
	else:
		group_doc = group_doc_or_name

	if getattr(group_doc, "type", None) != "Group":
		return {"to": [], "cc": []}

	res = resolve_group_recipients(group_doc.name)
	to_raw = res.get("to", [])
	cc_raw = res.get("cc", [])

	seen_to = set()
	unique_to = []
	for email in to_raw:
		clean = (email or "").strip()
		key = clean.lower()
		if key and key not in seen_to:
			seen_to.add(key)
			unique_to.append(clean)

	seen_cc = set()
	unique_cc = []
	for email in cc_raw:
		clean = (email or "").strip()
		key = clean.lower()
		if key and key not in seen_to and key not in seen_cc:
			seen_cc.add(key)
			unique_cc.append(clean)

	return {"to": unique_to, "cc": unique_cc}


def resolve_branch_for_group(group_doc, all_branches=None):
	"""
	Resolves the actual branch associated with an Email Group.
	1. First checks group_doc.branch (direct Link field to Branch).
	2. Fallback: checks if group name or doc name matches an active Branch.
	"""
	if not group_doc:
		return None

	branch = (getattr(group_doc, "branch", None) or "").strip()
	if branch:
		return branch

	if all_branches is None:
		all_branches = get_all_branches()

	group_name = (getattr(group_doc, "group_name", None) or getattr(group_doc, "name", None) or "").strip()
	for b in all_branches:
		if b.lower() == group_name.lower() or b.lower() in group_name.lower():
			return b

	return None


def resolve_recipients_for_branch(master, branch=None, cached_groups=None):
	"""
	Resolves To and CC recipients for a given branch from the Master's configured groups.
	Deduplicates email addresses and ensures no CC overlaps with To.
	Maintained for backwards compatibility.
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

		group_branch = resolve_branch_for_group(group_doc)
		if branch and group_branch and group_branch != branch:
			continue

		res = resolve_recipients_for_group(group_doc)
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


# -------------------------------------------------------------------------
# Dynamic Page Data Provider Registry
# -------------------------------------------------------------------------
PAGE_DATA_PROVIDERS = {}


def register_page_data_provider(page_name):
	"""
	Decorator to register a server-side data provider function for a custom Frappe Page.

	The provider function should accept (filters=None, **kwargs) and return:
	  (columns, data)
	where:
	  - columns: list of column definitions, e.g. [{"label": "Name", "fieldname": "name"}]
	  - data: list of dicts or list of lists
	"""
	def decorator(fn):
		clean = page_name.strip()
		PAGE_DATA_PROVIDERS[clean] = fn
		PAGE_DATA_PROVIDERS[frappe.scrub(clean)] = fn
		PAGE_DATA_PROVIDERS[clean.replace("_", "-")] = fn
		PAGE_DATA_PROVIDERS[clean.replace("-", "_")] = fn
		return fn
	return decorator


def get_page_data(page_name, filters=None, **kwargs):
	"""
	Resolves tabular data and columns for a custom Frappe Page using:
	1. Registered data providers (via @register_page_data_provider)
	2. The page module's server-side get_data(filters) function if present
	Returns (columns, data) or (None, None) if no tabular data provider is found.
	"""
	if not page_name:
		return None, None

	clean_name = page_name.strip()

	# 1. Check registry
	for key in (clean_name, frappe.scrub(clean_name), clean_name.replace("_", "-"), clean_name.replace("-", "_")):
		if key in PAGE_DATA_PROVIDERS:
			res = PAGE_DATA_PROVIDERS[key](filters=filters, **kwargs)
			if isinstance(res, tuple) and len(res) == 2:
				return res[0] or [], res[1] or []
			elif isinstance(res, list):
				columns = []
				if res and isinstance(res[0], dict):
					columns = [{"label": k.replace("_", " ").title(), "fieldname": k} for k in res[0].keys()]
				return columns, res

	# 2. Check if the page controller defines get_data(filters)
	try:
		if frappe.db.table_exists("Page") and frappe.db.exists("Page", clean_name):
			page_doc = frappe.get_doc("Page", clean_name)
			if page_doc and page_doc.module:
				scrubbed = frappe.scrub(clean_name)
				mod_path = f"{frappe.scrub(page_doc.module)}.page.{scrubbed}.{scrubbed}"
				pymod = frappe.get_module(mod_path)
				if hasattr(pymod, "get_data"):
					raw_data = pymod.get_data(filters=filters)
					columns = []
					if raw_data and isinstance(raw_data, list) and isinstance(raw_data[0], dict):
						columns = [{"label": k.replace("_", " ").title(), "fieldname": k} for k in raw_data[0].keys()]
					return columns, raw_data or []
	except Exception:
		pass

	return None, None


# -------------------------------------------------------------------------
# Developer-Controlled Scheduled Email Registry
# -------------------------------------------------------------------------
SCHEDULED_EMAIL_HANDLERS = {}


def register_scheduled_email_handler(source_type: str, source_name: str):
	"""
	Decorator to register an explicit developer-controlled scheduled email handler.
	Only explicitly registered handlers are executed during scheduled runs.
	Configuration in Report Email Master alone will NOT cause automatic execution.
	"""
	def decorator(fn):
		key = (source_type.strip(), source_name.strip())
		SCHEDULED_EMAIL_HANDLERS[key] = fn
		return fn
	return decorator


# -------------------------------------------------------------------------
# Dynamic Common Email Function
# -------------------------------------------------------------------------
def send_configured_email(
	source_name: str,
	source_type: str = "Report",
	filters: dict | None = None,
	data: list | tuple | None = None,
	columns: list | None = None,
	branch: str | None = None,
	**kwargs,
) -> dict:
	"""
	Generic, reusable email dispatcher for Frappe/ERPNext Reports and Pages.
	
	Processes only the specified Report or Page and sends emails according
	to the matching existing configuration in Report Email Master.
	
	Parameters:
	- source_name: Identifier of the Report or Page (e.g. 'OMR Item Change', 'pending-advance-mate')
	- source_type: 'Report', 'Page', or 'Dashboard' (defaults to 'Report')
	- filters: Optional dictionary of filters explicitly supplied by caller
	- data: Optional caller-provided dataset (list of dicts or list of rows)
	- columns: Optional column definitions for caller-provided data
	- branch: Optional branch string to restrict dispatch to groups matching this branch
	- **kwargs: Optional parameters (e.g., custom subject, email reference)
	
	Returns:
	  dict with status ('completed' or 'skipped'), sent, skipped, failed, and details.
	"""
	logger = get_logger()
	type_clean = (source_type or "").strip()
	name_clean = (source_name or "").strip()

	if type_clean not in ("Report", "Dashboard", "Page"):
		frappe.throw(_("Invalid source_type '{0}'. Must be 'Report', 'Page', or 'Dashboard'.").format(type_clean))

	if not name_clean:
		frappe.throw(_("source_name is required."))

	logger.info(f"Starting configured email send for {type_clean} '{name_clean}'.")

	# 1. Dynamic Configuration Lookup
	master = get_report_email_master_config(type_clean, name_clean)
	if not master:
		logger.warning(
			f"No active Report Email Master configuration found for {type_clean} '{name_clean}'. Skipping execution."
		)
		return {"status": "skipped", "reason": "configuration_not_found"}

	if not master.email_group:
		logger.warning(
			f"Report Email Master '{master.name}' has no Email Groups configured. Skipping execution."
		)
		return {"status": "skipped", "reason": "no_email_groups"}

	all_branches = get_all_branches()
	target_branch = branch or (filters.get("branch") if filters and isinstance(filters, dict) else None)

	supports_branch = False
	report_doc = None

	if type_clean == "Report":
		if not frappe.db.exists("Report", name_clean):
			logger.error(f"Report '{name_clean}' does not exist in the system.")
			return {"status": "error", "reason": "report_not_found"}
		report_doc = frappe.get_doc("Report", name_clean)

	supports_branch = source_supports_branch_filter(type_clean, name_clean, report_doc=report_doc)

	# Pre-load linked Group documents for performance
	cached_groups = {}
	for row in master.email_group:
		if row.group_name and row.group_name not in cached_groups:
			try:
				cached_groups[row.group_name] = frappe.get_doc("Report Email Master", row.group_name)
			except Exception as e:
				logger.error(f"Failed to load group '{row.group_name}': {str(e)}")

	groups_sent = []
	groups_skipped = []
	groups_failed = []

	# Process each configured email group independently
	for row in master.email_group:
		group_name = (row.group_name or "").strip()
		if not group_name:
			continue

		group_doc = cached_groups.get(group_name)
		if not group_doc:
			try:
				group_doc = frappe.get_doc("Report Email Master", group_name)
				cached_groups[group_name] = group_doc
			except Exception as e:
				logger.error(f"Failed to retrieve group doc '{group_name}': {str(e)}")
				groups_failed.append({"group": group_name, "error": str(e)})
				continue

		group_branch = resolve_branch_for_group(group_doc, all_branches=all_branches)

		# If caller explicitly targeted a specific branch, only process matching groups
		if target_branch and group_branch and group_branch != target_branch:
			continue

		effective_branch = target_branch if target_branch else group_branch

		try:
			# 1. Resolve recipients for this specific group
			recipients = resolve_recipients_for_group(group_doc)
			to_emails = recipients.get("to", [])
			cc_emails = recipients.get("cc", [])

			if not to_emails:
				logger.warning(
					f"No valid To recipients configured for group '{group_name}' (Branch: '{effective_branch or 'Global'}') in {type_clean} '{name_clean}'. Skipping send."
				)
				groups_skipped.append({
					"group": group_name,
					"branch": effective_branch or "Global",
					"reason": "no_recipients",
				})
				continue

			# 2. Build fresh filter object for this branch / invocation
			group_filters = dict(filters or {})
			branch_filter_applied = False
			if effective_branch and supports_branch:
				group_filters["branch"] = effective_branch
				branch_filter_applied = True

			# 3 & 4. Dynamic Data Retrieval (caller-supplied vs Report execution vs Page provider)
			group_cols, group_data = None, None
			has_tabular_data = False

			if data is not None:
				group_cols = columns or []
				group_data = data
				has_tabular_data = True
			elif type_clean == "Report":
				group_cols, group_data = generate_report_content(
					name_clean,
					branch=effective_branch if branch_filter_applied else None,
					filters=group_filters,
					supports_branch=supports_branch,
				)
				has_tabular_data = True
			elif type_clean in ("Page", "Dashboard"):
				p_cols, p_data = get_page_data(name_clean, filters=group_filters)
				if p_data is not None:
					group_cols, group_data = p_cols or [], p_data
					has_tabular_data = True

			# Conditional Branch Display:
			# Determine whether to display branch in email subject, headings, body, and summary box.
			# Only display branch if the source genuinely supports a branch filter AND a branch filter was applied,
			# or if caller explicitly supplied branch-targeted data.
			display_branch = None
			if data is not None:
				if target_branch:
					display_branch = target_branch
			else:
				if branch_filter_applied and supports_branch:
					display_branch = effective_branch

			attachments = []
			subject_branch = f" - {display_branch}" if display_branch else ""

			if has_tabular_data:
				excel_attachment = build_report_excel_attachment(
					name_clean, group_cols or [], group_data or [], branch=display_branch
				)
				attachments.append(excel_attachment)
				message_html = build_report_email_html(
					name_clean, group_cols or [], group_data or [], branch=display_branch
				)
				default_subject = f"Weekly Report: {name_clean}{subject_branch} - {today()}"
			else:
				# Non-tabular Page / Dashboard fallback to Executive Desk link
				dashboard_title = get_dashboard_title(name_clean)
				dashboard_route = frappe.scrub(name_clean).replace("_", "-")
				dashboard_url = f"{get_url()}/desk/{dashboard_route}"
				if display_branch:
					dashboard_url += f"?branch={frappe.utils.quote(display_branch)}"

				message_html = build_dashboard_email_html(name_clean, dashboard_url, branch=display_branch)
				default_subject = f"Weekly Dashboard: {dashboard_title}{subject_branch} - {today()}"

			subject = kwargs.get("subject") or default_subject

			# 5. Email Delivery
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
				f"Successfully sent email for {type_clean} '{name_clean}' to group '{group_name}' (Branch: '{effective_branch or 'Global'}') to {len(to_emails)} To, {len(cc_emails)} CC."
			)
			groups_sent.append({
				"group": group_name,
				"branch": effective_branch or "Global",
				"recipients": to_emails,
				"cc": cc_emails,
				"record_count": len(group_data) if group_data is not None else None,
			})

		except Exception as group_err:
			# 6. Failure Isolation: error in one group must not halt remaining groups
			logger.error(
				f"Failed to send email for group '{group_name}' (Branch: '{effective_branch}') for {type_clean} '{name_clean}': {str(group_err)}"
			)
			frappe.log_error(
				frappe.get_traceback(),
				f"Configured Email Failed: {type_clean} '{name_clean}' - Group: {group_name} (Branch: {effective_branch})",
			)
			groups_failed.append({
				"group": group_name,
				"branch": effective_branch or "Global",
				"error": str(group_err),
			})

	branches_sent = [g["branch"] for g in groups_sent]
	branches_skipped = [g["branch"] for g in groups_skipped]
	branches_failed = [g["branch"] for g in groups_failed]

	return {
		"status": "completed",
		"sent": branches_sent,
		"skipped": branches_skipped,
		"failed": branches_failed,
		"details": {
			"sent": groups_sent,
			"skipped": groups_skipped,
			"failed": groups_failed,
		},
	}


def send_weekly_report_email(type, name, filters=None, **kwargs):
	"""
	Backward-compatible wrapper routing to send_configured_email.
	"""
	return send_configured_email(
		source_name=name,
		source_type=type,
		filters=filters,
		**kwargs,
	)


# -------------------------------------------------------------------------
# Explicit Developer-Controlled Scheduled Handlers
# Self-contained in scheduler; reports/pages remain clean and independent.
# -------------------------------------------------------------------------
@register_scheduled_email_handler("Report", "OMR Item Change")
def send_omr_item_change_email(branch=None, filters=None, **kwargs):
	"""
	Developer-controlled email handler for OMR Item Change report.
	Directly triggers send_configured_email without depending on any email code in report files.
	"""
	flt = dict(filters or {})
	if branch:
		flt["branch"] = branch

	return send_configured_email(
		source_name="OMR Item Change",
		source_type="Report",
		filters=flt,
		**kwargs,
	)


@register_scheduled_email_handler("Report", "SO Approval TAT")
def send_so_approval_tat_email(branch=None, filters=None, **kwargs):
	"""
	Developer-controlled email handler for SO Approval TAT report.
	Directly triggers send_configured_email without depending on any email code in report files.
	"""
	flt = dict(filters or {})
	if branch:
		flt["branch"] = branch

	return send_configured_email(
		source_name="SO Approval TAT",
		source_type="Report",
		filters=flt,
		**kwargs,
	)


@register_scheduled_email_handler("Page", "pending-advance-mate")
def send_pending_advance_mate_email(filters=None, **kwargs):
	"""
	Developer-controlled email handler for pending-advance-mate page.
	Directly triggers send_configured_email without depending on any email code in page files.
	"""
	return send_configured_email(
		source_name="pending-advance-mate",
		source_type="Page",
		filters=filters,
		**kwargs,
	)


@register_page_data_provider("pending-advance-mate")
def provide_pending_advance_mate_data(filters=None, **kwargs):
	"""
	Server-side data provider adapter for pending-advance-mate page.
	"""
	try:
		from generate_item.generate_item.page.pending_advance_mate.pending_advance_mate import get_data
		raw_data = get_data(filters=filters)
		columns = [
			{"label": "Material Request", "fieldname": "material_request"},
			{"label": "Transaction Date", "fieldname": "transaction_date"},
			{"label": "Company", "fieldname": "company"},
			{"label": "Item Code", "fieldname": "item_code"},
			{"label": "Item Name", "fieldname": "item_name"},
			{"label": "Qty", "fieldname": "qty"},
			{"label": "Warehouse", "fieldname": "warehouse"},
			{"label": "Batch No", "fieldname": "batch_no"},
			{"label": "Production Plan", "fieldname": "production_plan"},
		]
		return columns, raw_data or []
	except Exception as e:
		get_logger().error(f"Error fetching data for pending-advance-mate: {str(e)}")
		return None, None


# -------------------------------------------------------------------------
# Central Weekly Scheduler Hook
# -------------------------------------------------------------------------
def execute_weekly_report_email_scheduler():
	"""
	Central scheduler entry point registered under scheduler_events['weekly'].
	Only executes explicitly registered developer-controlled email handlers in
	SCHEDULED_EMAIL_HANDLERS. Configuration in Report Email Master alone will NOT
	cause automatic execution.
	"""
	logger = get_logger()
	logger.info(f"Executing weekly report email scheduler. {len(SCHEDULED_EMAIL_HANDLERS)} handlers registered.")

	results = {}
	for (source_type, source_name), handler in SCHEDULED_EMAIL_HANDLERS.items():
		try:
			logger.info(f"Executing scheduled email handler for {source_type} '{source_name}'...")
			res = handler()
			results[f"{source_type}:{source_name}"] = res
		except Exception as err:
			logger.error(f"Error in scheduled handler for {source_type} '{source_name}': {str(err)}")
			frappe.log_error(
				frappe.get_traceback(),
				f"Weekly Scheduled Handler Failed: {source_type} '{source_name}'",
			)
			results[f"{source_type}:{source_name}"] = {"status": "error", "error": str(err)}

	logger.info(f"Weekly report email scheduler finished. Processed {len(results)} registered handlers.")
	return results
