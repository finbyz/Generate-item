# Copyright (c) 2026, FinByz Tech Pvt Ltd and contributors
# For license information, please see license.txt

"""Supplier Performance Dashboard (Frappe Page).

Data source: submitted Supplier Scorecard Period documents (one per supplier per month).

Per period:
    Order Qty             = variable "Total Ordered"
    Qty Received On Time  = variable "# of On Time Shipments"
    Qty Received          = variable "Total Received Items"
    Qty Pass              = variable "Total Accepted Items"
    Rejected Qty          = Qty Received - Qty Pass
    Delivery Rating       = score of the delivery criteria (fallback: On Time / Order Qty x 100)
    Quality Rating        = score of the quality criteria (fallback: Pass / Received x 100)
    Rejection %           = 100 - Quality Rating
    Supplier Rating       = Period Score (total_score)
    Grade                 = see GRADES
"""

import calendar
import json
from io import BytesIO

import frappe
from frappe import _
from frappe.utils import flt, getdate

# How quarter, supplier and total rows are rolled up from the monthly periods.
#   "average"  : plain average of the period ratings (average of Period Score)
#   "weighted" : ratings recalculated from the summed quantities
AGGREGATION = "average"

# Scorecard variables, matched on Variable Name (lower case) or Parameter Name.
VARIABLES = {
	"ordered": ("total ordered", "total_ordered"),
	"ontime": ("# of on time shipments", "on_time_shipment_num"),
	"received": ("total received items", "total_received_items"),
	"accepted": ("total accepted items", "total_accepted_items"),
}

# Scorecard criteria, matched when the Criteria Name contains this word.
CRITERIA = {"delivery": "deliver", "quality": "quality"}

DEFAULT_WEIGHTS = {"delivery": 60.0, "quality": 40.0}

GRADES = [
	{"grade": "A", "label": "Excellent", "min": 90, "range": "90% and above"},
	{"grade": "B", "label": "Very Good", "min": 80, "range": "80% to below 90%"},
	{"grade": "C", "label": "Good", "min": 70, "range": "70% to below 80%"},
	{"grade": "D", "label": "Need Improvements", "min": 60, "range": "60% to below 70%"},
	{"grade": "E", "label": "Need Actions", "min": None, "range": "Below 60%"},
]
GRADE_LABEL = {g["grade"]: g["label"] for g in GRADES}
QTY_FIELDS = ("ordered", "ontime", "received", "accepted")


# --------------------------------------------------------------------------- API


@frappe.whitelist()
def get_dashboard_data(filters=None):
	filters = _parse_filters(filters)
	return get_data(filters)


@frappe.whitelist()
def export_excel(filters=None):
	filters = _parse_filters(filters)
	data = get_data(filters)
	content = _build_workbook(data, filters)

	frappe.response["filename"] = "Supplier_Performance_{}_to_{}.xlsx".format(filters.from_date, filters.to_date)
	frappe.response["filecontent"] = content
	frappe.response["type"] = "binary"


# ------------------------------------------------------------------------- Data


def get_data(filters):
	periods = _get_periods(filters)
	start_month = _fy_start_month(filters)

	by_supplier = {}
	for p in periods:
		by_supplier.setdefault(p.supplier, []).append(p)

	suppliers = []
	for supplier, plist in by_supplier.items():
		row = _aggregate(plist)
		if filters.grade and row.grade != filters.grade:
			continue
		row.supplier = supplier
		row.supplier_name = plist[0].supplier_name or supplier
		row.children = _children(plist, filters.view, start_month)
		suppliers.append(row)

	suppliers.sort(key=lambda r: (-flt(r.score), r.supplier_name or ""))
	kept = [p for s in suppliers for p in by_supplier[s.supplier]]

	return {
		"cards": _cards(kept, len(suppliers)),
		"suppliers": suppliers,
		"total": _aggregate(kept) if kept else None,
		"grades": GRADES,
		"view": filters.view,
	}


def _get_periods(filters):
	conditions = ["ssp.docstatus = 1", "ssp.start_date >= %(from_date)s", "ssp.end_date <= %(to_date)s"]
	values = dict(filters)

	if filters.supplier:
		conditions.append("ssp.supplier = %(supplier)s")

	if filters.supplier_group:
		values["supplier_groups"] = tuple(_with_descendants("Supplier Group", filters.supplier_group))
		conditions.append("sup.supplier_group in %(supplier_groups)s")

	# Supplier Scorecard Period has no company field in standard ERPNext.
	# If a custom "company" field is added later, the Company filter applies automatically.
	if filters.company and frappe.get_meta("Supplier Scorecard Period").has_field("company"):
		conditions.append("ssp.company = %(company)s")

	periods = frappe.db.sql(
		"""
		select ssp.name, ssp.supplier, sup.supplier_name, ssp.start_date, ssp.end_date, ssp.total_score
		from `tabSupplier Scorecard Period` ssp
		left join `tabSupplier` sup on sup.name = ssp.supplier
		where {}
		order by ssp.supplier, ssp.start_date
		""".format(" and ".join(conditions)),
		values,
		as_dict=True,
	)
	if not periods:
		return []

	by_name = {}
	for p in periods:
		p.update({k: 0.0 for k in QTY_FIELDS})
		p.update({"delivery_score": None, "quality_score": None, "delivery_weight": 0.0, "quality_weight": 0.0})
		by_name[p.name] = p

	names = tuple(by_name)

	for v in frappe.db.sql(
		"""
		select parent, variable_label, param_name, value
		from `tabSupplier Scorecard Scoring Variable`
		where parenttype = 'Supplier Scorecard Period' and parent in %(names)s
		""",
		{"names": names},
		as_dict=True,
	):
		label = (v.variable_label or "").strip().lower()
		param = (v.param_name or "").strip().lower()
		for key, (var_label, var_param) in VARIABLES.items():
			if label == var_label or param == var_param:
				by_name[v.parent][key] = flt(v.value)

	for c in frappe.db.sql(
		"""
		select parent, criteria_name, score, weight
		from `tabSupplier Scorecard Scoring Criteria`
		where parenttype = 'Supplier Scorecard Period' and parent in %(names)s
		""",
		{"names": names},
		as_dict=True,
	):
		name = (c.criteria_name or "").lower()
		for key, word in CRITERIA.items():
			if word in name:
				by_name[c.parent][key + "_score"] = flt(c.score)
				by_name[c.parent][key + "_weight"] = flt(c.weight)

	for p in periods:
		p.periods = 1
		p.rejected = p.received - p.accepted
		p.delivery = p.delivery_score if p.delivery_score is not None else _ratio(p.ontime, p.ordered)
		p.quality = p.quality_score if p.quality_score is not None else _ratio(p.accepted, p.received)
		p.rejection = (100 - p.quality) if p.received else 0.0
		p.score = flt(p.total_score)
		p.grade = get_grade(p.score)

	return periods


def _aggregate(rows):
	n = len(rows) or 1
	t = frappe._dict(periods=len(rows))
	for key in QTY_FIELDS:
		t[key] = sum(flt(r[key]) for r in rows)
	t.rejected = t.received - t.accepted

	if len(rows) == 1:
		# a single period keeps its own criteria scores and Period Score
		t.delivery, t.quality, t.score = flt(rows[0].delivery), flt(rows[0].quality), flt(rows[0].score)
	elif AGGREGATION == "weighted":
		w_del, w_qual = _avg_weights(rows)
		t.delivery = _ratio(t.ontime, t.ordered)
		t.quality = _ratio(t.accepted, t.received)
		t.score = (t.delivery * w_del + t.quality * w_qual) / 100
	else:
		t.delivery = sum(flt(r.delivery) for r in rows) / n
		t.quality = sum(flt(r.quality) for r in rows) / n
		t.score = sum(flt(r.score) for r in rows) / n

	t.rejection = (100 - t.quality) if t.received else 0.0
	t.grade = get_grade(t.score)
	return t


def _children(plist, view, start_month):
	if view == "month":
		children = []
		for p in sorted(plist, key=lambda x: x.start_date):
			row = _aggregate([p])
			row.label = getdate(p.start_date).strftime("%b %Y")
			row.period = p.name
			children.append(row)
		return children

	quarters = {}
	for p in plist:
		key, label = _quarter_of(getdate(p.start_date), start_month)
		quarters.setdefault(key, {"label": label, "rows": []})["rows"].append(p)

	children = []
	for key in sorted(quarters):
		row = _aggregate(quarters[key]["rows"])
		row.label = quarters[key]["label"]
		children.append(row)
	return children


def _cards(periods, supplier_count):
	n = len(periods)
	w_del, w_qual = _avg_weights(periods)
	return {
		"delivery": sum(flt(p.delivery) for p in periods) / n if n else 0.0,
		"quality": sum(flt(p.quality) for p in periods) / n if n else 0.0,
		"score": sum(flt(p.score) for p in periods) / n if n else 0.0,
		"periods": n,
		"suppliers": supplier_count,
		"delivery_weight": w_del,
		"quality_weight": w_qual,
	}


# ---------------------------------------------------------------------- Helpers


def get_grade(score):
	score = flt(score, 2)
	for g in GRADES:
		if g["min"] is None or score >= g["min"]:
			return g["grade"]


def _ratio(part, whole):
	return flt(part) / flt(whole) * 100 if flt(whole) else 0.0


def _avg_weights(rows):
	with_weights = [r for r in rows if flt(r.get("delivery_weight")) or flt(r.get("quality_weight"))]
	if not with_weights:
		return DEFAULT_WEIGHTS["delivery"], DEFAULT_WEIGHTS["quality"]
	n = len(with_weights)
	return (
		sum(flt(r.delivery_weight) for r in with_weights) / n,
		sum(flt(r.quality_weight) for r in with_weights) / n,
	)


def _with_descendants(doctype, name):
	from frappe.utils.nestedset import get_descendants_of

	return [name] + (get_descendants_of(doctype, name) or [])


def _quarter_of(date, start_month):
	"""Return (sort_key, label) of the fiscal quarter, e.g. ("2026-1", "Q1 (Apr-Jun) FY 26-27")."""
	offset = (date.month - start_month) % 12
	q = offset // 3 + 1
	fy_year = date.year if date.month >= start_month else date.year - 1
	first = calendar.month_abbr[(start_month - 1 + (q - 1) * 3) % 12 + 1]
	last = calendar.month_abbr[(start_month - 1 + (q - 1) * 3 + 2) % 12 + 1]
	fy = "FY {}".format(fy_year) if start_month == 1 else "FY {}-{}".format(str(fy_year)[2:], str(fy_year + 1)[2:])
	return "{}-{}".format(fy_year, q), "Q{} ({}-{}) {}".format(q, first, last, fy)


def _fy_start_month(filters):
	if filters.fiscal_year:
		start = frappe.db.get_value("Fiscal Year", filters.fiscal_year, "year_start_date")
		if start:
			return getdate(start).month
	try:
		from erpnext.accounts.utils import get_fiscal_year

		return getdate(get_fiscal_year(filters.from_date, company=filters.company)[1]).month
	except Exception:
		return 4


def _parse_filters(filters):
	if not frappe.has_permission("Supplier Scorecard Period", "read"):
		frappe.throw(_("Not permitted to read Supplier Scorecard Period"), frappe.PermissionError)

	if isinstance(filters, str):
		filters = json.loads(filters or "{}")
	filters = frappe._dict(filters or {})

	if not filters.from_date or not filters.to_date:
		frappe.throw(_("From Date and To Date are mandatory"))
	filters.from_date = getdate(filters.from_date)
	filters.to_date = getdate(filters.to_date)
	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date cannot be after To Date"))

	filters.view = "month" if filters.view == "month" else "quarter"
	return filters


# ------------------------------------------------------------------------ Excel


def _build_workbook(data, filters):
	from openpyxl import Workbook
	from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

	wb = Workbook()
	ws = wb.active
	ws.title = "Supplier Performance"

	bold = Font(bold=True)
	head_fill = PatternFill("solid", fgColor="F3F4F6")
	sup_fill = PatternFill("solid", fgColor="FFFFFF")
	total_fill = PatternFill("solid", fgColor="E5E7EB")
	thin = Side(style="thin", color="D1D5DB")
	border = Border(top=thin, bottom=thin, left=thin, right=thin)
	grade_fill = {
		"A": PatternFill("solid", fgColor="D1FAE5"),
		"B": PatternFill("solid", fgColor="DBEAFE"),
		"C": PatternFill("solid", fgColor="FEF3C7"),
		"D": PatternFill("solid", fgColor="FFEDD5"),
		"E": PatternFill("solid", fgColor="FEE2E2"),
	}
	pct_fmt = '0.00"%"'

	def qty_fmt(v):
		return "#,##0" if flt(v) == int(flt(v)) else "#,##0.00"

	# Line 1: the three average labels, line 2: their values below them
	cards = data["cards"]
	line1 = [
		("Avg Delivery Rating", cards["delivery"]),
		("Avg Quality Rating", cards["quality"]),
		("Avg Period Score", cards["score"]),
	]
	for col, (label, value) in enumerate(line1, 1):
		c = ws.cell(row=1, column=col, value=label)
		c.font = Font(bold=True, color="6B7280")
		c.border = border
		c.fill = head_fill
		c = ws.cell(row=2, column=col, value=round(flt(value), 2))
		c.number_format = pct_fmt
		c.font = Font(bold=True, size=14)
		c.border = border
		c.alignment = Alignment(horizontal="left")
	ws.cell(
		row=3,
		column=1,
		value="Across {} scorecard periods, {} suppliers. Period {} to {}. {} view.".format(
			cards["periods"],
			cards["suppliers"],
			filters.from_date.strftime("%d-%m-%Y"),
			filters.to_date.strftime("%d-%m-%Y"),
			"Month wise" if filters.view == "month" else "Quarter wise",
		),
	).font = Font(italic=True, color="6B7280")

	# Table
	month_view = filters.view == "month"
	headers = ["Supplier / Month" if month_view else "Supplier / Quarter"]
	if month_view:
		headers.append("Scorecard Period")
	headers += [
		"Periods",
		"Order Qty",
		"Qty Received On Time",
		"Delivery Rating",
		"Qty Received",
		"Qty Pass",
		"Rejected Qty",
		"Rejection %",
		"Quality Rating",
		"Supplier Rating",
		"Grade",
	]
	qty_cols = {"Order Qty", "Qty Received On Time", "Qty Received", "Qty Pass", "Rejected Qty"}
	pct_cols = {"Delivery Rating", "Rejection %", "Quality Rating", "Supplier Rating"}

	title_row = 5
	ws.cell(row=title_row, column=1, value="Delivery and Quality Rating").font = Font(bold=True, size=12)
	head_row = title_row + 1
	for i, h in enumerate(headers, 1):
		c = ws.cell(row=head_row, column=i, value=h)
		c.font = bold
		c.fill = head_fill
		c.border = border
		c.alignment = Alignment(horizontal="left" if i == 1 else "center", vertical="center", wrap_text=True)

	def write_row(r, label, period_id, t, level):
		values = [label]
		if month_view:
			values.append(period_id or "")
		values += [
			t.periods,
			t.ordered,
			t.ontime,
			round(flt(t.delivery), 2),
			t.received,
			t.accepted,
			t.rejected,
			round(flt(t.rejection), 2),
			round(flt(t.quality), 2),
			round(flt(t.score), 2),
			t.grade,
		]
		for i, (h, v) in enumerate(zip(headers, values), 1):
			c = ws.cell(row=r, column=i, value=v)
			c.border = border
			if h in qty_cols:
				c.number_format = qty_fmt(v)
			elif h in pct_cols:
				c.number_format = pct_fmt
			if h == "Grade":
				c.alignment = Alignment(horizontal="center")
				c.fill = grade_fill.get(v, sup_fill)
			if level == 0:
				c.font = bold
			if i == 1 and level:
				c.alignment = Alignment(indent=2)
		if level:
			ws.row_dimensions[r].outlineLevel = 1

	r = head_row + 1
	for s in data["suppliers"]:
		write_row(r, s.supplier_name, None, s, 0)
		r += 1
		for ch in s.children:
			write_row(r, ch.label, ch.get("period"), ch, 1)
			r += 1

	if data["total"]:
		write_row(r, "Total ({} suppliers)".format(len(data["suppliers"])), None, data["total"], 0)
		for i in range(1, len(headers) + 1):
			if headers[i - 1] != "Grade":
				ws.cell(row=r, column=i).fill = total_fill
		r += 1
	elif not data["suppliers"]:
		ws.cell(row=r, column=1, value="No Supplier Scorecard Period found for the selected filters")
		r += 1

	# Grade legend
	r += 1
	ws.cell(row=r, column=1, value="Supplier Grade").font = bold
	ws.cell(row=r, column=2, value="Meaning").font = bold
	ws.cell(row=r, column=3, value="Supplier Rating").font = bold
	for g in GRADES:
		r += 1
		c = ws.cell(row=r, column=1, value=g["grade"])
		c.fill = grade_fill[g["grade"]]
		c.alignment = Alignment(horizontal="center")
		ws.cell(row=r, column=2, value=g["label"])
		ws.cell(row=r, column=3, value=g["range"])

	# Layout
	ws.column_dimensions["A"].width = 34
	for i in range(2, len(headers) + 1):
		ws.column_dimensions[ws.cell(row=head_row, column=i).column_letter].width = 18
	ws.row_dimensions[head_row].height = 30
	ws.freeze_panes = ws.cell(row=head_row + 1, column=2)
	ws.sheet_properties.outlinePr.summaryBelow = False

	out = BytesIO()
	wb.save(out)
	return out.getvalue()
