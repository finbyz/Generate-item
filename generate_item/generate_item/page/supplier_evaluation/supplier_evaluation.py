# Copyright (c) 2026, FinByz Tech Pvt Ltd
# Server-side API for the Supplier Evaluation Dashboard page.
#
# Supplier Rating = 60% Quality Rating + 40% Delivery Rating
# Quality Rating  = Qty Pass x 100 / Qty Received
# Delivery Rating = Qty Received On Time x 100 / Order Qty
#
# Order Qty, Qty Received and Qty Pass come from the submitted Supplier
# Scorecard Period (variables total_ordered, total_received_items and
# total_accepted_items). The scorecard only stores a count of on-time
# shipments, so Qty Received On Time is calculated from Purchase Receipts
# for the same period dates.

import frappe
from frappe.utils import add_days, add_months, flt, getdate

QUALITY_WEIGHT = 60
DELIVERY_WEIGHT = 40

# Grade on Supplier Rating: (minimum score, grade, performance level).
# A boundary score goes to the higher grade, e.g. exactly 90% is A.
GRADES = [
	(90, "A", "Excellent"),
	(80, "B", "Very Good"),
	(70, "C", "Good"),
	(60, "D", "Need Improvements"),
	(0, "E", "Need Actions"),
]

VARIABLE_MAP = {
	"total_ordered": "order_qty",
	"total_received_items": "received_qty",
	"total_accepted_items": "pass_qty",
}


QTY_KEYS = ("order_qty", "received_qty", "pass_qty", "on_time_qty")
QUARTERS = ("Q1", "Q2", "Q3", "Q4")


@frappe.whitelist()
def get_dashboard_data(
	supplier: str | None = None, fiscal_year: str | None = None, quarter: str | None = None
) -> dict:
	"""With a supplier: one row per Scorecard Period of that supplier.
	Without: one row per supplier, totalled over all its periods.
	With a fiscal year: only periods starting in that year, plus a
	quarter-wise (Q1 to Q4) weighted rating table.
	With a quarter (Q1 to Q4, needs a fiscal year): only periods starting
	in that quarter of the fiscal year."""
	frappe.has_permission("Supplier Scorecard Period", "read", throw=True)
	if quarter and quarter not in QUARTERS:
		frappe.throw(frappe._("Invalid Quarter {0}").format(quarter))
	if quarter and not fiscal_year:
		frappe.throw(frappe._("Please select a Fiscal Year to filter by Quarter"))

	filters = {"docstatus": 1}
	if supplier:
		filters["supplier"] = supplier

	fy_start = fy_end = None
	if fiscal_year:
		fy_start, fy_end = frappe.db.get_value(
			"Fiscal Year", fiscal_year, ["year_start_date", "year_end_date"]
		) or (None, None)
		if not fy_start:
			frappe.throw(frappe._("Fiscal Year {0} not found").format(fiscal_year))
		filters["start_date"] = ["between", [fy_start, fy_end]]
		if quarter:
			filters["start_date"] = ["between", list(quarter_range(fy_start, QUARTERS.index(quarter)))]

	periods = frappe.get_list(
		"Supplier Scorecard Period",
		filters=filters,
		fields=["name", "supplier", "start_date", "end_date"],
		order_by="start_date asc",
	)
	if not periods:
		return {"rows": [], "summary": None, "group_by": "period" if supplier else "supplier"}

	variables = frappe.get_all(
		"Supplier Scorecard Scoring Variable",
		filters={
			"parenttype": "Supplier Scorecard Period",
			"parent": ["in", [p.name for p in periods]],
			"param_name": ["in", list(VARIABLE_MAP)],
		},
		fields=["parent", "param_name", "value"],
	)
	values = {}
	for v in variables:
		values.setdefault(v.parent, {})[VARIABLE_MAP[v.param_name]] = flt(v.value)

	period_rows = []
	for p in periods:
		row = {
			"period": p.name,
			"supplier": p.supplier,
			"start_date": p.start_date,
			"end_date": p.end_date,
			"order_qty": 0.0,
			"received_qty": 0.0,
			"pass_qty": 0.0,
			**values.get(p.name, {}),
			"on_time_qty": get_on_time_received_qty(p.supplier, p.start_date, p.end_date),
		}
		period_rows.append(add_ratings(row))

	by_supplier = {}
	for r in period_rows:
		total = by_supplier.setdefault(
			r["supplier"], {"supplier": r["supplier"], "periods": 0, **dict.fromkeys(QTY_KEYS, 0.0)}
		)
		total["periods"] += 1
		for key in QTY_KEYS:
			total[key] += r[key]
	supplier_rows = [add_ratings(r) for r in by_supplier.values()]

	if supplier:
		rows = period_rows
	else:
		rows = sorted(supplier_rows, key=lambda r: r["supplier_rating"], reverse=True)

	summary = add_ratings({key: sum(r[key] for r in period_rows) for key in QTY_KEYS})

	return {
		"rows": rows,
		"summary": summary,
		"quarters": get_quarter_table(period_rows, fy_start, quarter) if fy_start else None,
		"quarter_rows": get_quarter_rows(period_rows, fy_start, quarter) if fy_start else None,
		"group_by": "period" if supplier else "supplier",
		"weights": {"quality": QUALITY_WEIGHT, "delivery": DELIVERY_WEIGHT},
		"grades": [{"min": m, "grade": g, "level": lvl} for m, g, lvl in GRADES],
	}


def get_on_time_received_qty(supplier, start_date, end_date) -> float:
	"""Received qty on submitted Purchase Receipts posted in the period, on or
	before the schedule date of the linked Purchase Order item."""
	pr = frappe.qb.DocType("Purchase Receipt")
	pr_item = frappe.qb.DocType("Purchase Receipt Item")
	po_item = frappe.qb.DocType("Purchase Order Item")

	result = (
		frappe.qb.from_(pr_item)
		.join(pr)
		.on(pr_item.parent == pr.name)
		.join(po_item)
		.on(pr_item.purchase_order_item == po_item.name)
		.select(frappe.query_builder.functions.Sum(pr_item.received_qty))
		.where(
			(pr.supplier == supplier)
			& (pr.docstatus == 1)
			& (pr.posting_date[start_date:end_date])
			& (pr.posting_date <= po_item.schedule_date)
		)
	).run()

	return flt(result[0][0]) if result else 0.0


def add_ratings(row: dict) -> dict:
	row["quality_rating"] = flt(row["pass_qty"] * 100 / row["received_qty"], 2) if row["received_qty"] else 0.0
	row["delivery_rating"] = flt(row["on_time_qty"] * 100 / row["order_qty"], 2) if row["order_qty"] else 0.0
	row["supplier_rating"] = flt(
		(row["quality_rating"] * QUALITY_WEIGHT + row["delivery_rating"] * DELIVERY_WEIGHT) / 100, 2
	)
	row["grade"], row["performance_level"] = get_grade(row["supplier_rating"])
	return row


def quarter_range(fy_start, index: int) -> tuple:
	"""Start and end date of quarter number index (0 = Q1) of a fiscal year."""
	q_start = add_months(getdate(fy_start), index * 3)
	return q_start, add_days(add_months(q_start, 3), -1)


def get_quarter_rows(period_rows: list[dict], fy_start, quarter: str | None = None) -> dict:
	"""Per supplier, quantities and ratings for each fiscal-year quarter
	(only the selected quarter when one is chosen). A period belongs to the
	quarter its start date falls in."""
	result = {}
	for supplier in sorted({r["supplier"] for r in period_rows}):
		supplier_rows = [r for r in period_rows if r["supplier"] == supplier]
		cols = []
		for q in range(4):
			if quarter and QUARTERS[q] != quarter:
				continue
			q_start, q_end = quarter_range(fy_start, q)
			q_rows = [r for r in supplier_rows if q_start <= getdate(r["start_date"]) <= q_end]
			col = {
				"label": QUARTERS[q],
				"months": f"{q_start.strftime('%b')} - {q_end.strftime('%b')}",
				"has_data": bool(q_rows),
				"periods": len(q_rows),
			}
			if q_rows:
				col.update(add_ratings({key: sum(r[key] for r in q_rows) for key in QTY_KEYS}))
			cols.append(col)
		result[supplier] = cols
	return result


def get_quarter_table(period_rows: list[dict], fy_start, quarter: str | None = None) -> dict:
	"""Weighted ratings per fiscal-year quarter. A period belongs to the
	quarter its start date falls in. Each quarter's ratings come from the
	quarter's total quantities. Avg is the simple average of the quarters
	that have data, and the grade is taken from that average. With a
	quarter selected, only that quarter is returned and there is no Avg."""
	quarters = []
	for q in range(4):
		if quarter and QUARTERS[q] != quarter:
			continue
		q_start, q_end = quarter_range(fy_start, q)
		q_rows = [r for r in period_rows if q_start <= getdate(r["start_date"]) <= q_end]
		col = {
			"label": QUARTERS[q],
			"months": f"{q_start.strftime('%b')} - {q_end.strftime('%b')}",
			"has_data": bool(q_rows),
		}
		if q_rows:
			totals = add_ratings({key: sum(r[key] for r in q_rows) for key in QTY_KEYS})
			col.update(weighted_values(totals["delivery_rating"], totals["quality_rating"]))
		quarters.append(col)

	if quarter:
		return {"quarters": quarters, "avg": None}

	with_data = [q for q in quarters if q["has_data"]]
	avg = {"has_data": bool(with_data)}
	if with_data:
		avg.update(
			weighted_values(
				sum(q["delivery_rating"] for q in with_data) / len(with_data),
				sum(q["quality_rating"] for q in with_data) / len(with_data),
			)
		)
	return {"quarters": quarters, "avg": avg}


def weighted_values(delivery_rating: float, quality_rating: float) -> dict:
	delivery = flt(delivery_rating * DELIVERY_WEIGHT / 100, 2)
	quality = flt(quality_rating * QUALITY_WEIGHT / 100, 2)
	rating = flt(delivery + quality, 2)
	grade, level = get_grade(rating)
	return {
		"delivery_rating": flt(delivery_rating, 2),
		"quality_rating": flt(quality_rating, 2),
		"delivery_weighted": delivery,
		"quality_weighted": quality,
		"supplier_rating": rating,
		"grade": grade,
		"performance_level": level,
	}


def get_grade(score: float) -> tuple[str, str]:
	for minimum, grade, level in GRADES:
		if score >= minimum:
			return grade, level
	return GRADES[-1][1], GRADES[-1][2]
