# Copyright (c) 2026, Steelstrong and contributors
# For license information, please see license.txt

import datetime
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

import frappe
from frappe import _
from frappe.utils import add_days, add_months, cint, flt, getdate, nowdate
from frappe.utils.data import get_timespan_date_range


def _check_access(company: str) -> None:
	"""Validates company access and user permissions."""
	if frappe.session.user in ("Administrator", "System Manager") or not getattr(frappe, "session", None) or not getattr(frappe.session, "user", None):
		return

	if not frappe.has_permission("GL Entry", "read"):
		frappe.throw(_("Not permitted to view financial ledgers"), frappe.PermissionError)

	# Verify user has access to company
	allowed_companies = frappe.get_list(
		"Company",
		filters={"name": company},
		pluck="name",
		ignore_permissions=False,
	)
	if not allowed_companies and not frappe.has_permission("Company", "read"):
		frappe.throw(_("Not permitted to view company {0}").format(company), frappe.PermissionError)


def get_fy_dates(fiscal_year: str) -> Tuple[datetime.date, datetime.date]:
	"""Retrieves year_start_date and year_end_date for a given fiscal year."""
	res = frappe.db.get_value(
		"Fiscal Year",
		fiscal_year,
		["year_start_date", "year_end_date"],
		as_dict=True,
	)
	if not res:
		today = getdate(nowdate())
		return datetime.date(today.year, 1, 1), datetime.date(today.year, 12, 31)
	return getdate(res.year_start_date), getdate(res.year_end_date)


def get_previous_fiscal_year(fiscal_year: str) -> Optional[str]:
	"""Finds the previous fiscal year record."""
	fy_start, _ = get_fy_dates(fiscal_year)
	prev_fy = frappe.db.get_value(
		"Fiscal Year",
		{"year_end_date": ("<", fy_start), "disabled": 0},
		"name",
		order_by="year_end_date desc",
	)
	return prev_fy


def resolve_date_range(
	date_filter: Optional[str] = None,
	from_date: Optional[str] = None,
	to_date: Optional[str] = None,
	fiscal_year: Optional[str] = None,
	company: Optional[str] = None,
) -> Tuple[datetime.date, datetime.date, str]:
	"""
	Resolves user-selected date filter into concrete start and end dates.
	Supported date_filters:
	- this_month
	- last_month
	- this_quarter
	- last_quarter
	- this_year
	- last_year
	- this_fy
	- last_fy
	- custom
	"""
	today = getdate(nowdate())
	df = (date_filter or "").lower().strip().replace(" ", "_")

	if not fiscal_year:
		from erpnext.accounts.utils import get_fiscal_year
		try:
			fiscal_year = get_fiscal_year(today, company=company)[0]
		except Exception:
			fiscal_year = frappe.db.get_value("Fiscal Year", {"disabled": 0}, "name", order_by="year_start_date desc")

	current_fy = fiscal_year

	if df in ("this_month", "thismonth"):
		rng = get_timespan_date_range("this month")
		return getdate(rng[0]), getdate(rng[1]), "this_month"
	elif df in ("last_month", "lastmonth"):
		rng = get_timespan_date_range("last month")
		return getdate(rng[0]), getdate(rng[1]), "last_month"
	elif df in ("this_quarter", "thisquarter"):
		rng = get_timespan_date_range("this quarter")
		return getdate(rng[0]), getdate(rng[1]), "this_quarter"
	elif df in ("last_quarter", "lastquarter"):
		rng = get_timespan_date_range("last quarter")
		return getdate(rng[0]), getdate(rng[1]), "last_quarter"
	elif df in ("this_year", "thisyear"):
		rng = get_timespan_date_range("this year")
		return getdate(rng[0]), getdate(rng[1]), "this_year"
	elif df in ("last_year", "lastyear"):
		rng = get_timespan_date_range("last year")
		return getdate(rng[0]), getdate(rng[1]), "last_year"
	elif df in ("this_fy", "thisfy", "current_fy"):
		s, e = get_fy_dates(current_fy)
		return s, e, "this_fy"
	elif df in ("last_fy", "lastfy", "prev_fy", "previous_fy"):
		prev_fy = get_previous_fiscal_year(current_fy)
		if prev_fy:
			s, e = get_fy_dates(prev_fy)
			return s, e, "last_fy"
		s, e = get_fy_dates(current_fy)
		return add_months(s, -12), add_months(e, -12), "last_fy"
	elif df in ("today",):
		return today, today, "today"
	elif df in ("yesterday",):
		yest = add_days(today, -1)
		return yest, yest, "yesterday"
	elif df in ("last_week", "lastweek"):
		rng = get_timespan_date_range("last week")
		return getdate(rng[0]), getdate(rng[1]), "last_week"
	elif df in ("this_week", "thisweek"):
		rng = get_timespan_date_range("this week")
		return getdate(rng[0]), getdate(rng[1]), "this_week"
	elif df in ("custom", "custom_date"):
		if from_date and to_date:
			return getdate(from_date), getdate(to_date), "custom"
		elif from_date:
			return getdate(from_date), today, "custom"
		elif to_date:
			return getdate(to_date), getdate(to_date), "custom"
		s, e = get_fy_dates(current_fy)
		return s, e, "custom"
	elif from_date and to_date:
		return getdate(from_date), getdate(to_date), "custom"
	elif fiscal_year:
		s, e = get_fy_dates(fiscal_year)
		return s, e, "this_fy"
	else:
		s, e = get_fy_dates(current_fy)
		return s, e, "this_fy"


def get_total_stock_balance(
	company: str,
	as_of_date: datetime.date,
	branch: Optional[str] = None,
) -> float:
	"""
	Card 1: Total Stock Balance as of the selected period's end date.
	Calculated from Stock Ledger Entry where posting_date <= as_of_date.
	"""
	as_of_date = getdate(as_of_date)
	join_wh = "INNER JOIN `tabWarehouse` wh ON sle.warehouse = wh.name" if branch else ""
	branch_cond = "AND wh.branch = %s" if branch else ""
	params = [company, as_of_date]
	if branch:
		params.append(branch)

	sql = f"""
		SELECT COALESCE(SUM(sle.stock_value_difference), 0.0)
		FROM `tabStock Ledger Entry` sle
		{join_wh}
		WHERE sle.company = %s
		  AND sle.is_cancelled = 0
		  AND sle.posting_date <= %s
		  {branch_cond}
	"""
	res = frappe.db.sql(sql, tuple(params))
	return flt(res[0][0]) if res and res[0][0] is not None else 0.0


def get_total_purchases_stock(
	company: str,
	start_date: datetime.date,
	end_date: datetime.date,
	branch: Optional[str] = None,
) -> float:
	"""
	Card 2: Total Purchase for the selected period, limited to stock items.
	Returns are deducted based on parent.is_return = 1.
	"""
	start_date = getdate(start_date)
	end_date = getdate(end_date)
	branch_cond = "AND parent.branch = %s" if branch else ""
	params = [company, start_date, end_date]
	if branch:
		params.append(branch)

	sql = f"""
		SELECT COALESCE(SUM(CASE WHEN parent.is_return = 1 THEN -pii.base_net_amount ELSE pii.base_net_amount END), 0.0)
		FROM `tabPurchase Invoice Item` pii
		INNER JOIN `tabPurchase Invoice` parent ON pii.parent = parent.name
		INNER JOIN `tabItem` item ON pii.item_code = item.name
		WHERE parent.company = %s
		  AND parent.docstatus = 1
		  AND item.is_stock_item = 1
		  AND parent.posting_date >= %s
		  AND parent.posting_date <= %s
		  {branch_cond}
	"""
	res = frappe.db.sql(sql, tuple(params))
	return flt(res[0][0]) if res and res[0][0] is not None else 0.0


def get_total_sales_stock(
	company: str,
	start_date: datetime.date,
	end_date: datetime.date,
	branch: Optional[str] = None,
) -> float:
	"""
	Card 3: Total Sales for the selected period, limited to stock items.
	Returns are deducted based on parent.is_return = 1.
	"""
	start_date = getdate(start_date)
	end_date = getdate(end_date)
	branch_cond = "AND parent.branch = %s" if branch else ""
	params = [company, start_date, end_date]
	if branch:
		params.append(branch)

	sql = f"""
		SELECT COALESCE(SUM(CASE WHEN parent.is_return = 1 THEN -sii.base_net_amount ELSE sii.base_net_amount END), 0.0)
		FROM `tabSales Invoice Item` sii
		INNER JOIN `tabSales Invoice` parent ON sii.parent = parent.name
		INNER JOIN `tabItem` item ON sii.item_code = item.name
		WHERE parent.company = %s
		  AND parent.docstatus = 1
		  AND item.is_stock_item = 1
		  AND parent.posting_date >= %s
		  AND parent.posting_date <= %s
		  {branch_cond}
	"""
	res = frappe.db.sql(sql, tuple(params))
	return flt(res[0][0]) if res and res[0][0] is not None else 0.0


@frappe.whitelist()
def get_overview(
	company: Optional[str] = None,
	from_date: Optional[str] = None,
	to_date: Optional[str] = None,
	date_filter: Optional[str] = None,
	branch: Optional[str] = None,
	fiscal_year: Optional[str] = None,
	unit_dimension: Optional[str] = "Branch",
) -> Dict[str, Any]:
	"""
	Main overview endpoint for Financial Dashboard.
	Returns:
	- Meta information (company, date_filter, from_date, to_date, branch, currency)
	- Cards:
	    1. Total Stock Balance (as of end date)
	    2. Total Purchase (stock items for period)
	    3. Total Sales (stock items for period)
	- Accounts Receivable (AR) Ageing
	- Accounts Payable (AP) Ageing
	"""
	if not company or company in ("undefined", "null", "None"):
		company = (
			frappe.defaults.get_user_default("Company")
			or frappe.db.get_single_value("Global Defaults", "default_company")
			or frappe.db.get_value("Company", {}, "name")
		)

	_check_access(company)

	start_date, end_date, resolved_filter = resolve_date_range(
		date_filter=date_filter,
		from_date=from_date,
		to_date=to_date,
		fiscal_year=fiscal_year,
		company=company,
	)

	if not fiscal_year:
		from erpnext.accounts.utils import get_fiscal_year
		try:
			fiscal_year = get_fiscal_year(end_date, company=company)[0]
		except Exception:
			fiscal_year = frappe.db.get_value("Fiscal Year", {"disabled": 0}, "name", order_by="year_start_date desc")

	if not unit_dimension:
		unit_dimension = "Branch"

	currency = "INR"

	# Determine comparison period for delta calculations
	if resolved_filter == "this_month":
		prev_start, prev_end = get_timespan_date_range("last month")
		prev_caption = _("vs last month")
	elif resolved_filter == "last_month":
		prev_start = add_months(start_date, -1)
		prev_end = add_days(start_date, -1)
		prev_caption = _("vs previous month")
	elif resolved_filter == "this_quarter":
		prev_start, prev_end = get_timespan_date_range("last quarter")
		prev_caption = _("vs last quarter")
	elif resolved_filter == "last_quarter":
		prev_start = add_months(start_date, -3)
		prev_end = add_days(start_date, -1)
		prev_caption = _("vs previous quarter")
	elif resolved_filter == "this_year":
		prev_start, prev_end = get_timespan_date_range("last year")
		prev_caption = _("vs last year")
	elif resolved_filter == "last_year":
		prev_start = add_months(start_date, -12)
		prev_end = add_days(start_date, -1)
		prev_caption = _("vs previous year")
	elif resolved_filter == "this_fy":
		prev_fy = get_previous_fiscal_year(fiscal_year)
		if prev_fy:
			prev_start, prev_end = get_fy_dates(prev_fy)
		else:
			prev_start, prev_end = add_months(start_date, -12), add_months(end_date, -12)
		prev_caption = _("YTD vs previous year")
	elif resolved_filter == "last_fy":
		prev_fy = get_previous_fiscal_year(fiscal_year)
		prev_prev_fy = get_previous_fiscal_year(prev_fy) if prev_fy else None
		if prev_prev_fy:
			prev_start, prev_end = get_fy_dates(prev_prev_fy)
		else:
			prev_start, prev_end = add_months(start_date, -12), add_months(end_date, -12)
		prev_caption = _("vs previous fiscal year")
	else:
		days = max(1, (end_date - start_date).days + 1)
		prev_end = add_days(start_date, -1)
		prev_start = add_days(prev_end, -days + 1)
		prev_caption = _("vs previous period")

	# Revenue vs Operating Margin for selected period
	revenue_margin_data = get_monthly_revenue_and_margin(company, start_date, end_date, branch=branch)

	# Previous comparison period
	prev_rev_margin = (
		get_monthly_revenue_and_margin(company, prev_start, prev_end, branch=branch)
		if prev_start and prev_end
		else {"total_revenue": 0.0, "total_expense": 0.0, "operating_margin": 0.0}
	)

	# Orders Booked for selected period
	orders_monthly_data = get_monthly_orders_booked(company, start_date, end_date, branch=branch)

	# Book-to-bill calculation
	sales_invoice_net = get_sales_invoice_net_total(company, start_date, end_date, branch=branch)
	book_to_bill = (
		round(orders_monthly_data["total_orders_value"] / sales_invoice_net, 2)
		if sales_invoice_net > 0
		else (1.0 if orders_monthly_data["total_orders_value"] > 0 else 0.0)
	)

	# KPI Deltas
	rev_delta = 0.0
	if prev_rev_margin["total_revenue"] > 0:
		rev_delta = round(
			((revenue_margin_data["total_revenue"] - prev_rev_margin["total_revenue"]) / prev_rev_margin["total_revenue"]) * 100,
			1,
		)

	margin_delta = round(revenue_margin_data["operating_margin"] - prev_rev_margin["operating_margin"], 1)

	orders_delta = 0.0
	if prev_start and prev_end:
		prev_orders_count = get_orders_count_for_period(company, prev_start, prev_end, branch=branch)
		if prev_orders_count > 0:
			orders_delta = round(
				((orders_monthly_data["total_orders_count"] - prev_orders_count) / prev_orders_count) * 100,
				1,
			)

	# Row 2: 3 New Cards
	stock_balance = get_total_stock_balance(company, end_date, branch=branch)
	total_purchases = get_total_purchases_stock(company, start_date, end_date, branch=branch)
	total_sales = get_total_sales_stock(company, start_date, end_date, branch=branch)

	# AR & AP Ageing (calculated as of period end date)
	ar_ageing = get_ar_ageing(company, start_date, end_date, total_sales, branch=branch)
	ap_ageing = get_ap_ageing(company, start_date, end_date, total_purchases, branch=branch)

	cards = {
		# Original 3 Cards
		"net_revenue": revenue_margin_data["total_revenue"],
		"revenue_delta": rev_delta,
		"revenue_caption": prev_caption,
		"operating_margin": revenue_margin_data["operating_margin"],
		"margin_delta": margin_delta,
		"orders_booked_count": orders_monthly_data["total_orders_count"],
		"orders_booked_value": orders_monthly_data["total_orders_value"],
		"orders_delta": orders_delta,
		"book_to_bill": book_to_bill,

		# 3 New Cards
		"stock_balance": round(stock_balance, 2),
		"total_purchases": round(total_purchases, 2),
		"total_sales": round(total_sales, 2),
		"as_of_date": str(end_date),
		"from_date": str(start_date),
		"to_date": str(end_date),
	}

	# Backward-compatibility kpis dictionary
	kpis = {
		"net_revenue": revenue_margin_data["total_revenue"],
		"revenue_target": prev_rev_margin["total_revenue"],
		"revenue_delta": rev_delta,
		"revenue_caption": prev_caption,
		"operating_margin": revenue_margin_data["operating_margin"],
		"margin_target": prev_rev_margin["operating_margin"],
		"margin_delta": margin_delta,
		"orders_booked_count": orders_monthly_data["total_orders_count"],
		"orders_booked_value": orders_monthly_data["total_orders_value"],
		"orders_delta": orders_delta,
		"book_to_bill": book_to_bill,
		"stock_balance": round(stock_balance, 2),
		"total_purchases": round(total_purchases, 2),
		"total_sales": round(total_sales, 2),
		"total_stock_balance": round(stock_balance, 2),
		"pending_backlog_count": 0,
	}

	all_fys = frappe.db.get_all(
		"Fiscal Year",
		filters={"disabled": 0},
		fields=["name", "year_start_date", "year_end_date"],
		order_by="year_start_date asc",
	)

	# Fetch active branches
	branches = frappe.get_all("Branch", fields=["name"], order_by="name asc")
	all_branches = [b.name for b in branches] if branches else []
	if not all_branches:
		raw_b = frappe.db.sql("SELECT DISTINCT branch FROM `tabSales Invoice` WHERE branch IS NOT NULL AND branch != '' ORDER BY branch ASC")
		all_branches = [r[0] for r in raw_b]

	return {
		"meta": {
			"company": company,
			"fiscal_year": fiscal_year,
			"branch": branch or "",
			"date_filter": resolved_filter,
			"from_date": str(start_date),
			"to_date": str(end_date),
			"currency": currency,
			"unit_dimension": unit_dimension,
			"all_fiscal_years": all_fys,
			"all_branches": all_branches,
			"generated_at": frappe.utils.now_datetime().strftime("%H:%M"),
		},
		"cards": cards,
		"kpis": kpis,
		"revenue_margin": revenue_margin_data,
		"orders_monthly": orders_monthly_data,
		"pending_orders": {"total_count": 0, "total_value": 0.0, "sla_percentage": 100.0, "stages": {}},
		"ar_ageing": ar_ageing,
		"ap_ageing": ap_ageing,
	}


def get_ar_ageing(
	company: str,
	start_date: datetime.date,
	end_date: datetime.date,
	period_revenue: float,
	branch: Optional[str] = None,
) -> Dict[str, Any]:
	"""Executes ERPNext Accounts Receivable report and builds bucket summary and DSO as of end_date."""
	from erpnext.accounts.report.accounts_receivable.accounts_receivable import execute as ar_execute

	start_date = getdate(start_date)
	end_date = getdate(end_date)
	report_date = str(end_date)
	filters = {
		"company": company,
		"report_date": report_date,
		"ageing_based_on": "Due Date",
		"range1": 30,
		"range2": 60,
		"range3": 90,
		"range4": 120,
	}
	if branch:
		filters["branch"] = branch

	try:
		columns, data, _, _, report_summary, _ = ar_execute(filters)
	except Exception:
		try:
			res = ar_execute(filters)
			data = res[1] if len(res) > 1 else []
		except Exception:
			data = []

	b1, b2, b3, b4 = 0.0, 0.0, 0.0, 0.0
	total_outstanding = 0.0

	for row in data:
		if isinstance(row, dict):
			# Skip bold/total subtotal rows to avoid double counting
			if row.get("bold") or row.get("party") == "Total":
				continue
			if branch and row.get("branch") and row.get("branch") != branch:
				continue
			r1 = flt(row.get("range1"))
			r2 = flt(row.get("range2"))
			r3 = flt(row.get("range3"))
			r4 = flt(row.get("range4")) + flt(row.get("range5"))
			out = flt(row.get("outstanding"))
			b1 += r1
			b2 += r2
			b3 += r3
			b4 += r4
			total_outstanding += out

	calculated_sum = b1 + b2 + b3 + b4
	if total_outstanding == 0.0 and calculated_sum > 0:
		total_outstanding = calculated_sum

	# DSO: (AR Outstanding / Period Net Revenue) * Days in period
	days_in_period = max(1, (end_date - start_date).days + 1)
	dso = round((total_outstanding / period_revenue) * days_in_period, 0) if period_revenue > 0 else 0

	p1 = round((b1 / total_outstanding * 100), 1) if total_outstanding > 0 else 0.0
	p2 = round((b2 / total_outstanding * 100), 1) if total_outstanding > 0 else 0.0
	p3 = round((b3 / total_outstanding * 100), 1) if total_outstanding > 0 else 0.0
	p4 = round((b4 / total_outstanding * 100), 1) if total_outstanding > 0 else 0.0

	buckets = [
		{"bucket": "< 30 Days (Current)", "amount": round(b1, 2), "share": p1, "risk": "Normal", "risk_class": "risk-normal"},
		{"bucket": "31 - 60 Days", "amount": round(b2, 2), "share": p2, "risk": "Low", "risk_class": "risk-low"},
		{"bucket": "61 - 90 Days", "amount": round(b3, 2), "share": p3, "risk": "Medium", "risk_class": "risk-medium"},
		{"bucket": "> 90 Days (Overdue)", "amount": round(b4, 2), "share": p4, "risk": "High Alert", "risk_class": "risk-high"},
	]

	return {
		"total_outstanding": round(total_outstanding, 2),
		"dso_days": int(dso),
		"current_share": p1,
		"buckets": buckets,
		"chart_data": [round(b1, 2), round(b2, 2), round(b3, 2), round(b4, 2)],
	}


def get_ap_ageing(
	company: str,
	start_date: datetime.date,
	end_date: datetime.date,
	period_purchases: float,
	branch: Optional[str] = None,
) -> Dict[str, Any]:
	"""Executes ERPNext Accounts Payable report and builds bucket summary and DPO as of end_date."""
	from erpnext.accounts.report.accounts_payable.accounts_payable import execute as ap_execute

	start_date = getdate(start_date)
	end_date = getdate(end_date)
	report_date = str(end_date)
	filters = {
		"company": company,
		"report_date": report_date,
		"ageing_based_on": "Due Date",
		"range1": 30,
		"range2": 60,
		"range3": 90,
		"range4": 120,
	}
	if branch:
		filters["branch"] = branch

	try:
		columns, data, _, _, report_summary, _ = ap_execute(filters)
	except Exception:
		try:
			res = ap_execute(filters)
			data = res[1] if len(res) > 1 else []
		except Exception:
			data = []

	b1, b2, b3, b4 = 0.0, 0.0, 0.0, 0.0
	total_outstanding = 0.0

	for row in data:
		if isinstance(row, dict):
			if row.get("bold") or row.get("party") == "Total":
				continue
			if branch and row.get("branch") and row.get("branch") != branch:
				continue
			r1 = flt(row.get("range1"))
			r2 = flt(row.get("range2"))
			r3 = flt(row.get("range3"))
			r4 = flt(row.get("range4")) + flt(row.get("range5"))
			out = flt(row.get("outstanding"))
			b1 += r1
			b2 += r2
			b3 += r3
			b4 += r4
			total_outstanding += out

	calculated_sum = b1 + b2 + b3 + b4
	if total_outstanding == 0.0 and calculated_sum > 0:
		total_outstanding = calculated_sum

	days_in_period = max(1, (end_date - start_date).days + 1)
	dpo = round((total_outstanding / period_purchases) * days_in_period, 0) if period_purchases > 0 else 0

	p1 = round((b1 / total_outstanding * 100), 1) if total_outstanding > 0 else 0.0
	p2 = round((b2 / total_outstanding * 100), 1) if total_outstanding > 0 else 0.0
	p3 = round((b3 / total_outstanding * 100), 1) if total_outstanding > 0 else 0.0
	p4 = round((b4 / total_outstanding * 100), 1) if total_outstanding > 0 else 0.0

	buckets = [
		{"bucket": "< 30 Days (Current)", "amount": round(b1, 2), "share": p1, "action": "Scheduled batch next week"},
		{"bucket": "31 - 60 Days", "amount": round(b2, 2), "share": p2, "action": "Under invoice 3-way match"},
		{"bucket": "61 - 90 Days", "amount": round(b3, 2), "share": p3, "action": "Vendor terms extension"},
		{"bucket": "> 90 Days (Critical)", "amount": round(b4, 2), "share": p4, "action": "Audit Dispute / Escalated"},
	]

	return {
		"total_outstanding": round(total_outstanding, 2),
		"dpo_days": int(dpo),
		"due_soon_share": p2,
		"buckets": buckets,
		"chart_data": [round(b1, 2), round(b2, 2), round(b3, 2), round(b4, 2)],
	}


@frappe.whitelist()
def get_unit_series(
	company: Optional[str] = None,
	from_date: Optional[str] = None,
	to_date: Optional[str] = None,
	date_filter: Optional[str] = None,
	kind: str = "sales",
	grain: str = "auto",
	unit_dimension: str = "Branch",
	branch: Optional[str] = None,
	fiscal_year: Optional[str] = None,
) -> Dict[str, Any]:
	"""
	Returns multi-unit time-series data for Sales (Branch Wise Sales), limited to stock items.
	Supports dynamic periods based on the date filter and time grain.
	kind: "sales" | "purchases"
	grain: "auto" | "days" | "weeks" | "months" | "quarters" | "years"
	unit_dimension: "Branch" | "Cost Center" | "Company"
	"""
	if not company or company in ("undefined", "null", "None"):
		company = (
			frappe.defaults.get_user_default("Company")
			or frappe.db.get_single_value("Global Defaults", "default_company")
			or frappe.db.get_value("Company", {}, "name")
		)

	_check_access(company)

	if not unit_dimension:
		unit_dimension = "Branch"

	start_date, end_date, _ = resolve_date_range(
		date_filter=date_filter,
		from_date=from_date,
		to_date=to_date,
		fiscal_year=fiscal_year,
		company=company,
	)

	num_days = (end_date - start_date).days + 1

	# Determine grain and available grains based on period length
	if num_days <= 14:
		available_grains = ["days"]
		selected_grain = "days" if grain in ("auto", "days", "quarters", "months", "years") else grain
	elif num_days <= 65:
		available_grains = ["days", "weeks"]
		selected_grain = "weeks" if grain in ("auto", "months", "quarters", "years") else grain
	elif num_days <= 300:
		available_grains = ["weeks", "months", "quarters"]
		selected_grain = "months" if grain in ("auto", "years") else grain
	else:
		available_grains = ["months", "quarters", "years"]
		selected_grain = "months" if grain in ("auto", "days", "weeks") else grain

	# If caller explicitly asked for a specific grain (e.g. quarters or years)
	if grain in ("quarters", "years", "months", "weeks", "days"):
		selected_grain = grain
		if selected_grain not in available_grains:
			available_grains.append(selected_grain)

	labels = []
	periods = []

	if selected_grain == "days":
		cur = start_date
		while cur <= end_date:
			labels.append(cur.strftime("%d %b"))
			periods.append((cur, cur))
			cur = add_days(cur, 1)

	elif selected_grain == "weeks":
		w_start = start_date
		idx = 1
		while w_start <= end_date:
			w_end = min(end_date, add_days(w_start, 6))
			labels.append(f"W{idx} ({w_start.strftime('%d %b')} - {w_end.strftime('%d %b')})")
			periods.append((w_start, w_end))
			w_start = add_days(w_end, 1)
			idx += 1

	elif selected_grain == "quarters":
		cur = start_date
		idx = 1
		while cur <= end_date:
			q_end = min(end_date, add_days(add_months(cur, 3), -1))
			labels.append(f"Q{idx}")
			periods.append((cur, q_end))
			cur = add_days(q_end, 1)
			idx += 1

	elif selected_grain == "years":
		fys = frappe.db.get_all(
			"Fiscal Year",
			filters={"year_end_date": ("<=", end_date), "disabled": 0},
			fields=["name", "year_start_date", "year_end_date"],
			order_by="year_start_date desc",
			limit=3,
		)
		fys.reverse()
		for fy in fys:
			labels.append(fy.name)
			periods.append((getdate(fy.year_start_date), getdate(fy.year_end_date)))
		if not periods:
			labels.append(str(start_date.year))
			periods.append((start_date, end_date))

	else:  # "months"
		cur = datetime.date(start_date.year, start_date.month, 1)
		end = datetime.date(end_date.year, end_date.month, 1)
		while cur <= end:
			m_start = max(start_date, cur)
			next_m = add_months(datetime.date(cur.year, cur.month, 1), 1)
			m_end = min(end_date, add_days(next_m, -1))
			labels.append(cur.strftime("%b %y"))
			periods.append((m_start, m_end))
			cur = next_m

	parent_dt = "Sales Invoice" if kind == "sales" else "Purchase Invoice"
	item_dt = "Sales Invoice Item" if kind == "sales" else "Purchase Invoice Item"

	if unit_dimension == "Branch":
		dim_expr = "COALESCE(NULLIF(parent.branch, ''), 'Unassigned')"
	elif unit_dimension == "Company":
		dim_expr = "COALESCE(parent.company, 'Unassigned')"
	else:
		dim_expr = "COALESCE(item.cost_center, parent.cost_center, 'Main')"

	branch_filter = ""
	params = [company]
	if branch:
		branch_filter = "AND parent.branch = %s"
		params.append(branch)

	query_start = periods[0][0] if periods else start_date
	query_end = periods[-1][1] if periods else end_date
	params.extend([query_start, query_end])

	query = f"""
		SELECT
			{dim_expr} AS unit_name,
			parent.posting_date AS posting_date,
			SUM(CASE WHEN parent.is_return = 1 THEN -item.base_net_amount ELSE item.base_net_amount END) AS net_amount
		FROM `tab{item_dt}` item
		INNER JOIN `tab{parent_dt}` parent ON item.parent = parent.name
		INNER JOIN `tabItem` i ON item.item_code = i.name
		WHERE parent.company = %s
			AND parent.docstatus = 1
			AND i.is_stock_item = 1
			{branch_filter}
			AND parent.posting_date >= %s
			AND parent.posting_date <= %s
		GROUP BY unit_name, parent.posting_date
	"""
	records = frappe.db.sql(query, tuple(params), as_dict=True)

	unit_totals = defaultdict(float)
	unit_period_matrix = defaultdict(lambda: [0.0] * len(periods))

	for r in records:
		u = r.unit_name or "Unassigned"
		u_clean = u.split(" - ")[0] if " - " in u else u
		amt = flt(r.net_amount)
		p_date = getdate(r.posting_date)

		for idx, (p_start, p_end) in enumerate(periods):
			if p_start <= p_date <= p_end:
				unit_period_matrix[u_clean][idx] += amt
				unit_totals[u_clean] += amt
				break

	sorted_units = sorted(unit_totals.keys(), key=lambda k: unit_totals[k], reverse=True)
	top_units = sorted_units[:5]
	other_units = sorted_units[5:]

	palette = (
		["#2563eb", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899"]
		if kind == "sales"
		else ["#3b82f6", "#ec4899", "#f97316", "#6366f1", "#14b8a6"]
	)

	datasets = []
	grand_total = sum(unit_totals.values())

	for i, u_name in enumerate(top_units):
		color = palette[i % len(palette)]
		data_points = [round(max(0.0, val), 2) for val in unit_period_matrix[u_name]]
		datasets.append({
			"label": u_name,
			"data": data_points,
			"backgroundColor": color,
			"borderColor": color,
			"borderRadius": 4,
			"total": round(unit_totals[u_name], 2),
		})

	if other_units:
		other_points = [0.0] * len(periods)
		other_total = 0.0
		for u_name in other_units:
			other_total += unit_totals[u_name]
			for idx in range(len(periods)):
				other_points[idx] += unit_period_matrix[u_name][idx]
		datasets.append({
			"label": "Other Branches",
			"data": [round(max(0.0, val), 2) for val in other_points],
			"backgroundColor": "#94a3b8",
			"borderColor": "#94a3b8",
			"borderRadius": 4,
			"total": round(other_total, 2),
		})

	if not datasets:
		datasets.append({
			"label": "No Data",
			"data": [0.0] * len(periods),
			"backgroundColor": palette[0],
			"borderColor": palette[0],
			"borderRadius": 4,
			"total": 0.0,
		})

	top_unit_label = top_units[0] if top_units else "N/A"
	top_unit_share = (
		round((unit_totals[top_units[0]] / grand_total) * 100, 1)
		if (top_units and grand_total > 0)
		else 0.0
	)

	return {
		"labels": labels,
		"datasets": datasets,
		"grand_total": round(grand_total, 2),
		"top_unit": top_unit_label,
		"top_unit_share": top_unit_share,
		"unit_dimension": unit_dimension,
		"grain": selected_grain,
		"available_grains": available_grains,
		"from_date": str(start_date),
		"to_date": str(end_date),
	}


def get_monthly_revenue_and_margin(
	company: str,
	start_date: datetime.date,
	end_date: datetime.date,
	branch: Optional[str] = None,
) -> Dict[str, Any]:
	"""
	Calculates monthly revenue and operating margin by aggregating GL Entries joined to Account.
	Income: root_type = 'Income' -> SUM(credit - debit)
	Expense: root_type = 'Expense' -> SUM(debit - credit)
	Operating Margin % = (Income - Expense) / Income * 100
	"""
	start_date = getdate(start_date)
	end_date = getdate(end_date)

	months = []
	cur = datetime.date(start_date.year, start_date.month, 1)
	end = datetime.date(end_date.year, end_date.month, 1)
	while cur <= end:
		months.append(cur.strftime("%b %y"))
		cur = add_months(cur, 1)

	branch_cond = ""
	params = [company, start_date, end_date]
	if branch:
		branch_cond = "AND gle.branch = %s"
		params.append(branch)

	gl_entries = frappe.db.sql(
		f"""
		SELECT
			DATE_FORMAT(gle.posting_date, '%%b %%y') AS month_label,
			DATE_FORMAT(gle.posting_date, '%%Y-%%m') AS month_key,
			acc.root_type AS root_type,
			SUM(gle.credit - gle.debit) AS income_val,
			SUM(gle.debit - gle.credit) AS expense_val
		FROM `tabGL Entry` gle
		INNER JOIN `tabAccount` acc ON gle.account = acc.name
		WHERE gle.company = %s
			AND gle.is_cancelled = 0
			AND gle.posting_date >= %s
			AND gle.posting_date <= %s
			{branch_cond}
			AND acc.root_type IN ('Income', 'Expense')
		GROUP BY month_key, month_label, acc.root_type
		ORDER BY month_key ASC
		""",
		tuple(params),
		as_dict=True,
	)

	income_by_month = defaultdict(float)
	expense_by_month = defaultdict(float)

	for row in gl_entries:
		label = row.month_label
		if row.root_type == "Income":
			income_by_month[label] += flt(row.income_val)
		elif row.root_type == "Expense":
			expense_by_month[label] += flt(row.expense_val)

	labels = months if months else list(income_by_month.keys())
	revenue_series = []
	expense_series = []
	margin_series = []

	total_rev = 0.0
	total_exp = 0.0

	for m in labels:
		rev = max(0.0, flt(income_by_month.get(m, 0.0)))
		exp = max(0.0, flt(expense_by_month.get(m, 0.0)))
		margin = round(((rev - exp) / rev * 100), 1) if rev > 0 else 0.0

		revenue_series.append(round(rev, 2))
		expense_series.append(round(exp, 2))
		margin_series.append(margin)

		total_rev += rev
		total_exp += exp

	overall_margin = round(((total_rev - total_exp) / total_rev * 100), 1) if total_rev > 0 else 0.0

	peak_rev_val = 0.0
	peak_rev_month = "N/A"
	best_margin_val = -999.0
	best_margin_month = "N/A"

	for idx, m in enumerate(labels):
		r = revenue_series[idx]
		mg = margin_series[idx]
		if r > peak_rev_val:
			peak_rev_val = r
			peak_rev_month = m
		if r > 0 and mg > best_margin_val:
			best_margin_val = mg
			best_margin_month = m

	if best_margin_val == -999.0:
		best_margin_val = 0.0

	margin_values_with_rev = [margin_series[i] for i in range(len(labels)) if revenue_series[i] > 0]
	margin_spread = (
		round(max(margin_values_with_rev) - min(margin_values_with_rev), 1)
		if margin_values_with_rev
		else 0.0
	)
	avg_run_rate = round(total_rev / len(labels), 2) if labels else 0.0

	return {
		"labels": labels,
		"revenue_series": revenue_series,
		"expense_series": expense_series,
		"margin_series": margin_series,
		"total_revenue": round(total_rev, 2),
		"total_expense": round(total_exp, 2),
		"operating_margin": overall_margin,
		"insights": {
			"peak_revenue_month": peak_rev_month,
			"peak_revenue_value": peak_rev_val,
			"best_margin_month": best_margin_month,
			"best_margin_value": best_margin_val,
			"avg_monthly_run_rate": avg_run_rate,
			"margin_spread": margin_spread,
		},
	}


def get_monthly_orders_booked(
	company: str,
	start_date: datetime.date,
	end_date: datetime.date,
	branch: Optional[str] = None,
	target_count: float = 0.0,
) -> Dict[str, Any]:
	"""Fetches count and value of Sales Orders booked grouped by month."""
	start_date = getdate(start_date)
	end_date = getdate(end_date)

	months = []
	cur = datetime.date(start_date.year, start_date.month, 1)
	end = datetime.date(end_date.year, end_date.month, 1)
	while cur <= end:
		months.append(cur.strftime("%b %y"))
		cur = add_months(cur, 1)

	branch_cond = ""
	params = [company, start_date, end_date]
	if branch:
		branch_cond = "AND branch = %s"
		params.append(branch)

	so_data = frappe.db.sql(
		f"""
		SELECT
			DATE_FORMAT(transaction_date, '%%b %%y') AS month_label,
			DATE_FORMAT(transaction_date, '%%Y-%%m') AS month_key,
			COUNT(name) AS order_count,
			SUM(base_net_total) AS order_value
		FROM `tabSales Order`
		WHERE company = %s
			AND docstatus = 1
			AND status != 'Cancelled'
			AND transaction_date >= %s
			AND transaction_date <= %s
			{branch_cond}
		GROUP BY month_key, month_label
		ORDER BY month_key ASC
		""",
		tuple(params),
		as_dict=True,
	)

	orders_by_month = {row.month_label: row for row in so_data}

	labels = months if months else list(orders_by_month.keys())
	count_series = []
	value_series = []

	total_count = 0
	total_val = 0.0

	for m in labels:
		row = orders_by_month.get(m)
		cnt = cint(row.order_count) if row else 0
		val = flt(row.order_value) if row else 0.0
		count_series.append(cnt)
		value_series.append(round(val, 2))
		total_count += cnt
		total_val += val

	monthly_mean = round(total_count / len(labels), 1) if labels else 0.0
	benchmark_target = target_count if target_count > 0 else monthly_mean
	target_series = [benchmark_target] * len(labels)
	target_total = benchmark_target * len(labels)
	attainment = round((total_count / target_total) * 100, 1) if target_total > 0 else 100.0

	return {
		"labels": labels,
		"count_series": count_series,
		"value_series": value_series,
		"target_series": target_series,
		"total_orders_count": total_count,
		"total_orders_value": round(total_val, 2),
		"monthly_mean": monthly_mean,
		"target_attainment": attainment,
	}


def get_orders_count_for_period(
	company: str,
	start_date: datetime.date,
	end_date: datetime.date,
	branch: Optional[str] = None,
) -> int:
	"""Returns total count of Sales Orders in a period."""
	start_date = getdate(start_date)
	end_date = getdate(end_date)

	branch_cond = ""
	params = [company, start_date, end_date]
	if branch:
		branch_cond = "AND branch = %s"
		params.append(branch)

	res = frappe.db.sql(
		f"""
		SELECT COUNT(name)
		FROM `tabSales Order`
		WHERE company = %s
			AND docstatus = 1
			AND status != 'Cancelled'
			AND transaction_date >= %s
			AND transaction_date <= %s
			{branch_cond}
		""",
		tuple(params),
	)
	return cint(res[0][0]) if res else 0


def get_sales_invoice_net_total(
	company: str,
	start_date: datetime.date,
	end_date: datetime.date,
	branch: Optional[str] = None,
) -> float:
	"""Computes net sales invoice total for book-to-bill calculation."""
	start_date = getdate(start_date)
	end_date = getdate(end_date)

	branch_cond = ""
	params = [company, start_date, end_date]
	if branch:
		branch_cond = "AND branch = %s"
		params.append(branch)

	res = frappe.db.sql(
		f"""
		SELECT SUM(CASE WHEN is_return = 1 THEN -base_net_total ELSE base_net_total END)
		FROM `tabSales Invoice`
		WHERE company = %s
			AND docstatus = 1
			AND posting_date >= %s
			AND posting_date <= %s
			{branch_cond}
		""",
		tuple(params),
	)
	return flt(res[0][0]) if res and res[0] else 0.0


def get_ytd_purchases(
	company: str,
	start_date: datetime.date,
	end_date: datetime.date,
	branch: Optional[str] = None,
) -> float:
	"""Computes net purchase invoice total for DPO calculation."""
	start_date = getdate(start_date)
	end_date = getdate(end_date)

	branch_cond = ""
	params = [company, start_date, end_date]
	if branch:
		branch_cond = "AND branch = %s"
		params.append(branch)

	res = frappe.db.sql(
		f"""
		SELECT SUM(CASE WHEN is_return = 1 THEN -base_net_total ELSE base_net_total END)
		FROM `tabPurchase Invoice`
		WHERE company = %s
			AND docstatus = 1
			AND posting_date >= %s
			AND posting_date <= %s
			{branch_cond}
		""",
		tuple(params),
	)
	return flt(res[0][0]) if res and res[0] else 0.0


def get_pending_orders_status(
	company: str,
	start_date: datetime.date,
	end_date: datetime.date,
	branch: Optional[str] = None,
	grace_days: int = 0,
) -> Dict[str, Any]:
	return {
		"total_count": 0,
		"total_value": 0.0,
		"sla_percentage": 100.0,
		"stages": {},
	}
