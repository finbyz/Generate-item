# Copyright (c) 2026, Steelstrong and contributors
# For license information, please see license.txt

import datetime
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

import frappe
from frappe import _
from frappe.query_builder import Criterion
from frappe.query_builder.functions import Date, Sum
from frappe.utils import add_days, add_months, cint, flt, getdate, nowdate


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


@frappe.whitelist()
def get_overview(company: Optional[str] = None, fiscal_year: Optional[str] = None, unit_dimension: Optional[str] = None) -> Dict[str, Any]:
	"""
	Main overview endpoint for Financial Dashboard:
	Returns: KPIs, Item 1 (Monthly Revenue & Operating Margin), Item 4 (Orders Booked),
	Item 5 (Pending Backlog Breakdown), Item 6 (AR Ageing), Item 7 (AP Ageing), and Meta info.
	"""
	if not company:
		company = (
			frappe.defaults.get_user_default("Company")
			or frappe.defaults.get_default("Company")
			or frappe.db.get_single_value("Global Defaults", "default_company")
			or frappe.db.get_value("Company", {}, "name")
		)

	_check_access(company)

	if not fiscal_year:
		from erpnext.accounts.utils import get_fiscal_year
		try:
			fiscal_year = get_fiscal_year(nowdate(), company=company)[0]
		except Exception:
			fiscal_year = frappe.db.get_value("Fiscal Year", {"disabled": 0}, "name", order_by="year_start_date desc")

	if not unit_dimension:
		unit_dimension = "Cost Center"

	fy_start, fy_end = get_fy_dates(fiscal_year)
	currency = frappe.get_cached_value("Company", company, "default_currency") or "INR"

	# Previous Fiscal Year for YoY comparisons
	prev_fy = get_previous_fiscal_year(fiscal_year)
	prev_fy_start, prev_fy_end = (get_fy_dates(prev_fy) if prev_fy else (None, None))

	# 1. Monthly Revenue and Operating Margin (Current FY)
	rev_margin_data = get_monthly_revenue_and_margin(company, fy_start, fy_end)

	# Previous FY for delta comparison
	prev_rev_margin = (
		get_monthly_revenue_and_margin(company, prev_fy_start, prev_fy_end)
		if prev_fy_start and prev_fy_end
		else {"total_revenue": 0.0, "total_expense": 0.0, "operating_margin": 0.0}
	)

	# 2. Orders Booked (Monthly)
	orders_data = get_monthly_orders_booked(company, fy_start, fy_end)

	# 3. Pending Orders Pipeline & SLA (bounded by selected Fiscal Year)
	pending_orders = get_pending_orders_status(company, fy_start, fy_end)

	# 4. AR Ageing
	ar_ageing = get_ar_ageing(company, fy_start, fy_end, rev_margin_data["total_revenue"])

	# 5. AP Ageing
	total_purchases = get_ytd_purchases(company, fy_start, fy_end)
	ap_ageing = get_ap_ageing(company, fy_start, fy_end, total_purchases)

	# 6. Book-to-Bill
	sales_invoice_net = get_sales_invoice_net_total(company, fy_start, fy_end)
	book_to_bill = (
		round(orders_data["total_orders_value"] / sales_invoice_net, 2)
		if sales_invoice_net > 0
		else (1.0 if orders_data["total_orders_value"] > 0 else 0.0)
	)

	# KPI Deltas
	rev_delta = 0.0
	if prev_rev_margin["total_revenue"] > 0:
		rev_delta = round(
			((rev_margin_data["total_revenue"] - prev_rev_margin["total_revenue"]) / prev_rev_margin["total_revenue"]) * 100,
			1
		)

	margin_delta = round(rev_margin_data["operating_margin"] - prev_rev_margin["operating_margin"], 1)

	orders_delta = 0.0
	if prev_fy_start and prev_fy_end:
		prev_orders_count = get_orders_count_for_period(company, prev_fy_start, prev_fy_end)
		if prev_orders_count > 0:
			orders_delta = round(((orders_data["total_orders_count"] - prev_orders_count) / prev_orders_count) * 100, 1)

	kpis = {
		"net_revenue": rev_margin_data["total_revenue"],
		"revenue_target": prev_rev_margin["total_revenue"],
		"revenue_delta": rev_delta,
		"operating_margin": rev_margin_data["operating_margin"],
		"margin_target": prev_rev_margin["operating_margin"],
		"margin_delta": margin_delta,
		"orders_booked_count": orders_data["total_orders_count"],
		"orders_booked_value": orders_data["total_orders_value"],
		"orders_delta": orders_delta,
		"book_to_bill": book_to_bill,
		"pending_backlog_count": pending_orders["total_count"],
		"pending_backlog_value": pending_orders["total_value"],
		"sla_percentage": pending_orders["sla_percentage"],
	}

	all_fys = frappe.db.get_all(
		"Fiscal Year",
		filters={"disabled": 0},
		fields=["name", "year_start_date", "year_end_date"],
		order_by="year_start_date asc",
	)

	return {
		"meta": {
			"company": company,
			"fiscal_year": fiscal_year,
			"fy_start": str(fy_start),
			"fy_end": str(fy_end),
			"currency": currency,
			"unit_dimension": unit_dimension,
			"all_fiscal_years": all_fys,
			"generated_at": frappe.utils.now_datetime().strftime("%H:%M"),
		},
		"kpis": kpis,
		"revenue_margin": rev_margin_data,
		"orders_monthly": orders_data,
		"pending_orders": pending_orders,
		"ar_ageing": ar_ageing,
		"ap_ageing": ap_ageing,
	}


def get_monthly_revenue_and_margin(company: str, start_date: datetime.date, end_date: datetime.date) -> Dict[str, Any]:
	"""
	Calculates monthly revenue and operating margin by aggregating GL Entries joined to Account.
	Income: root_type = 'Income' -> SUM(credit - debit)
	Expense: root_type = 'Expense' -> SUM(debit - credit)
	Operating Margin % = (Income - Expense) / Income * 100
	"""
	# Generate all months between start_date and end_date
	months = []
	cur = datetime.date(start_date.year, start_date.month, 1)
	end = datetime.date(end_date.year, end_date.month, 1)
	while cur <= end:
		months.append(cur.strftime("%b %y"))
		cur = add_months(cur, 1)

	gl_entries = frappe.db.sql(
		"""
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
			AND acc.root_type IN ('Income', 'Expense')
		GROUP BY month_key, month_label, acc.root_type
		ORDER BY month_key ASC
		""",
		(company, start_date, end_date),
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

	# Calculate summary insight tiles
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
	company: str, start_date: datetime.date, end_date: datetime.date, target_count: float = 0.0
) -> Dict[str, Any]:
	"""Fetches count and value of Sales Orders booked grouped by month."""
	months = []
	cur = datetime.date(start_date.year, start_date.month, 1)
	end = datetime.date(end_date.year, end_date.month, 1)
	while cur <= end:
		months.append(cur.strftime("%b %y"))
		cur = add_months(cur, 1)

	so_data = frappe.db.sql(
		"""
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
		GROUP BY month_key, month_label
		ORDER BY month_key ASC
		""",
		(company, start_date, end_date),
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


def get_orders_count_for_period(company: str, start_date: datetime.date, end_date: datetime.date) -> int:
	"""Returns total count of Sales Orders in a period."""
	res = frappe.db.sql(
		"""
		SELECT COUNT(name)
		FROM `tabSales Order`
		WHERE company = %s
			AND docstatus = 1
			AND status != 'Cancelled'
			AND transaction_date >= %s
			AND transaction_date <= %s
		""",
		(company, start_date, end_date),
	)
	return cint(res[0][0]) if res else 0


def get_sales_invoice_net_total(company: str, start_date: datetime.date, end_date: datetime.date) -> float:
	"""Computes net sales invoice total for book-to-bill calculation."""
	res = frappe.db.sql(
		"""
		SELECT SUM(CASE WHEN is_return = 1 THEN -base_net_total ELSE base_net_total END)
		FROM `tabSales Invoice`
		WHERE company = %s
			AND docstatus = 1
			AND posting_date >= %s
			AND posting_date <= %s
		""",
		(company, start_date, end_date),
	)
	return flt(res[0][0]) if res and res[0][0] else 0.0


def get_ytd_purchases(company: str, start_date: datetime.date, end_date: datetime.date) -> float:
	"""Computes net purchase invoice total for DPO calculation."""
	res = frappe.db.sql(
		"""
		SELECT SUM(CASE WHEN is_return = 1 THEN -base_net_total ELSE base_net_total END)
		FROM `tabPurchase Invoice`
		WHERE company = %s
			AND docstatus = 1
			AND posting_date >= %s
			AND posting_date <= %s
		""",
		(company, start_date, end_date),
	)
	return flt(res[0][0]) if res and res[0][0] else 0.0


def get_pending_orders_status(
	company: str, start_date: datetime.date, end_date: datetime.date, grace_days: int = 0
) -> Dict[str, Any]:
	"""
	Classifies active pending Sales Orders within the selected Fiscal Year:
	- Payment Hold: status = 'On Hold' or open Payment Request
	- In Transit: linked submitted Delivery Note with delivery in progress
	- QA Inspection: linked open Quality Inspection or pending inspection
	- Production: linked open Work Order (Not Started / In Process)
	- Open / Unscheduled: remaining pending SOs
	"""
	pending_sos = frappe.db.sql(
		"""
		SELECT
			name, status, delivery_date, base_grand_total, per_delivered, per_billed
		FROM `tabSales Order`
		WHERE company = %s
			AND docstatus = 1
			AND status IN ('To Deliver and Bill', 'To Deliver', 'To Bill', 'On Hold')
			AND transaction_date >= %s
			AND transaction_date <= %s
		""",
		(company, start_date, end_date),
		as_dict=True,
	)

	if not pending_sos:
		return {
			"total_count": 0,
			"total_value": 0.0,
			"sla_percentage": 100.0,
			"stages": {
				"Production": {"count": 0, "value": 0.0, "color": "#f59e0b"},
				"QA Inspection": {"count": 0, "value": 0.0, "color": "#0284c7"},
				"In Transit": {"count": 0, "value": 0.0, "color": "#6366f1"},
				"Payment Hold": {"count": 0, "value": 0.0, "color": "#ef4444"},
				"Open": {"count": 0, "value": 0.0, "color": "#10b981"},
			},
		}

	so_names = [so.name for so in pending_sos]

	# Fetch Work Orders linked to these Sales Orders
	work_orders = set(
		frappe.db.get_all(
			"Work Order",
			filters={"sales_order": ("in", so_names), "docstatus": 1, "status": ("in", ["Not Started", "In Process"])},
			pluck="sales_order",
		)
	)

	# Fetch linked open Quality Inspection
	qa_sos = set()
	if frappe.db.table_exists("Quality Inspection"):
		qa_records = frappe.db.sql(
			"""
			SELECT DISTINCT reference_name
			FROM `tabQuality Inspection`
			WHERE docstatus = 0 AND reference_type = 'Sales Order' AND reference_name IN %s
			""",
			(tuple(so_names),),
		)
		qa_sos = {r[0] for r in qa_records}

	# Fetch linked Delivery Notes
	transit_sos = set()
	if frappe.db.table_exists("Delivery Note Item"):
		dn_records = frappe.db.sql(
			"""
			SELECT DISTINCT dni.against_sales_order
			FROM `tabDelivery Note Item` dni
			INNER JOIN `tabDelivery Note` dn ON dni.parent = dn.name
			WHERE dn.docstatus = 1 AND dn.status NOT IN ('Cancelled', 'Closed')
				AND dni.against_sales_order IN %s
			""",
			(tuple(so_names),),
		)
		transit_sos = {r[0] for r in dn_records if r[0]}

	today = getdate(nowdate())
	cutoff_date = add_days(today, -grace_days) if grace_days else today

	stages = {
		"Production": {"count": 0, "value": 0.0, "color": "#f59e0b"},
		"QA Inspection": {"count": 0, "value": 0.0, "color": "#0284c7"},
		"In Transit": {"count": 0, "value": 0.0, "color": "#6366f1"},
		"Payment Hold": {"count": 0, "value": 0.0, "color": "#ef4444"},
		"Open": {"count": 0, "value": 0.0, "color": "#10b981"},
	}

	total_count = len(pending_sos)
	total_val = 0.0
	on_sla_count = 0

	for so in pending_sos:
		pending_pct = max(0.0, 100.0 - flt(so.per_delivered))
		val = flt(so.base_grand_total) * (pending_pct / 100.0)
		total_val += val

		if so.delivery_date and getdate(so.delivery_date) >= cutoff_date:
			on_sla_count += 1

		# Classify stage
		if so.status == "On Hold":
			stage = "Payment Hold"
		elif so.name in transit_sos:
			stage = "In Transit"
		elif so.name in qa_sos:
			stage = "QA Inspection"
		elif so.name in work_orders:
			stage = "Production"
		else:
			stage = "Open"

		stages[stage]["count"] += 1
		stages[stage]["value"] += round(val, 2)

	sla_pct = round((on_sla_count / total_count) * 100, 1) if total_count > 0 else 100.0

	return {
		"total_count": total_count,
		"total_value": round(total_val, 2),
		"sla_percentage": sla_pct,
		"stages": stages,
	}


def get_ar_ageing(company: str, start_date: datetime.date, end_date: datetime.date, ytd_revenue: float) -> Dict[str, Any]:
	"""Executes ERPNext Accounts Receivable report and builds bucket summary and DSO."""
	from erpnext.accounts.report.accounts_receivable.accounts_receivable import execute as ar_execute

	report_date = nowdate() if getdate(nowdate()) <= end_date else str(end_date)
	filters = {
		"company": company,
		"report_date": report_date,
		"ageing_based_on": "Due Date",
		"range1": 30,
		"range2": 60,
		"range3": 90,
		"range4": 120,
	}

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

	# DSO: (AR Outstanding / YTD Net Revenue) * Days in period
	days_in_period = max(1, (getdate(report_date) - start_date).days + 1)
	dso = round((total_outstanding / ytd_revenue) * days_in_period, 0) if ytd_revenue > 0 else 0

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


def get_ap_ageing(company: str, start_date: datetime.date, end_date: datetime.date, ytd_purchases: float) -> Dict[str, Any]:
	"""Executes ERPNext Accounts Payable report and builds bucket summary and DPO."""
	from erpnext.accounts.report.accounts_payable.accounts_payable import execute as ap_execute

	report_date = nowdate() if getdate(nowdate()) <= end_date else str(end_date)
	filters = {
		"company": company,
		"report_date": report_date,
		"ageing_based_on": "Due Date",
		"range1": 30,
		"range2": 60,
		"range3": 90,
		"range4": 120,
	}

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

	days_in_period = max(1, (getdate(report_date) - start_date).days + 1)
	dpo = round((total_outstanding / ytd_purchases) * days_in_period, 0) if ytd_purchases > 0 else 0

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
	fiscal_year: Optional[str] = None,
	kind: str = "sales",
	grain: str = "quarters",
	unit_dimension: str = "Cost Center",
) -> Dict[str, Any]:
	"""
	Returns multi-unit time-series data for Sales (Item 2) or Purchases (Item 3).
	kind: "sales" | "purchases"
	grain: "years" | "quarters" | "months"
	unit_dimension: "Cost Center" | "Branch" | "Company"
	"""
	if not company:
		company = (
			frappe.defaults.get_user_default("Company")
			or frappe.defaults.get_default("Company")
			or frappe.db.get_single_value("Global Defaults", "default_company")
			or frappe.db.get_value("Company", {}, "name")
		)

	_check_access(company)

	fy_start, fy_end = get_fy_dates(fiscal_year)

	# Determine time intervals and labels
	labels = []
	periods = []

	if grain == "years":
		# Selected FY + 2 preceding FYs
		fys = frappe.db.get_all(
			"Fiscal Year",
			filters={"year_end_date": ("<=", fy_end), "disabled": 0},
			fields=["name", "year_start_date", "year_end_date"],
			order_by="year_start_date desc",
			limit=3,
		)
		fys.reverse()
		for fy in fys:
			labels.append(fy.name)
			periods.append((getdate(fy.year_start_date), getdate(fy.year_end_date)))
	elif grain == "quarters":
		# Q1 to Q4 from fy_start
		for q in range(4):
			q_start = add_months(fy_start, q * 3)
			q_end = add_days(add_months(q_start, 3), -1)
			if q_end > fy_end:
				q_end = fy_end
			labels.append(f"Q{q + 1}")
			periods.append((q_start, q_end))
	else:  # "months"
		cur = datetime.date(fy_start.year, fy_start.month, 1)
		end = datetime.date(fy_end.year, fy_end.month, 1)
		while cur <= end:
			m_start = cur
			m_end = add_days(add_months(m_start, 1), -1)
			if m_end > fy_end:
				m_end = fy_end
			labels.append(cur.strftime("%b %y"))
			periods.append((m_start, m_end))
			cur = add_months(cur, 1)

	# Build Table & Query
	parent_dt = "Sales Invoice" if kind == "sales" else "Purchase Invoice"
	item_dt = "Sales Invoice Item" if kind == "sales" else "Purchase Invoice Item"

	# Dimension selection field
	if unit_dimension == "Branch":
		dim_expr = "COALESCE(parent.branch, 'Unassigned')"
	elif unit_dimension == "Company":
		dim_expr = "COALESCE(parent.company, 'Unassigned')"
	else:  # Cost Center
		dim_expr = "COALESCE(item.cost_center, parent.cost_center, 'Main')"

	# Aggregate across the entire range
	overall_start = periods[0][0] if periods else fy_start
	overall_end = periods[-1][1] if periods else fy_end

	query = f"""
		SELECT
			{dim_expr} AS unit_name,
			parent.posting_date AS posting_date,
			SUM(CASE WHEN parent.is_return = 1 THEN -item.base_net_amount ELSE item.base_net_amount END) AS net_amount
		FROM `tab{item_dt}` item
		INNER JOIN `tab{parent_dt}` parent ON item.parent = parent.name
		WHERE parent.company = %s
			AND parent.docstatus = 1
			AND parent.posting_date >= %s
			AND parent.posting_date <= %s
		GROUP BY unit_name, parent.posting_date
	"""
	records = frappe.db.sql(query, (company, overall_start, overall_end), as_dict=True)

	# Group data by unit and period
	unit_totals = defaultdict(float)
	unit_period_matrix = defaultdict(lambda: [0.0] * len(periods))

	for r in records:
		u = r.unit_name or "General"
		# Strip company suffix if present (e.g. "Main - ST" -> "Main")
		u_clean = u.split(" - ")[0] if " - " in u else u
		amt = flt(r.net_amount)
		p_date = getdate(r.posting_date)

		for idx, (p_start, p_end) in enumerate(periods):
			if p_start <= p_date <= p_end:
				unit_period_matrix[u_clean][idx] += amt
				unit_totals[u_clean] += amt
				break

	# Pick top 4 units + group others
	sorted_units = sorted(unit_totals.keys(), key=lambda k: unit_totals[k], reverse=True)
	top_units = sorted_units[:4]
	other_units = sorted_units[4:]

	palette = (
		["#0284c7", "#10b981", "#f59e0b", "#8b5cf6"]
		if kind == "sales"
		else ["#3b82f6", "#ec4899", "#f97316", "#6366f1"]
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
			"label": "Other Units",
			"data": [round(max(0.0, val), 2) for val in other_points],
			"backgroundColor": "#94a3b8",
			"borderColor": "#94a3b8",
			"borderRadius": 4,
			"total": round(other_total, 2),
		})

	# If no datasets found, add an empty placeholder dataset
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
	}
