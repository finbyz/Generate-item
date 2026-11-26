# Copyright (c) 2026, FinByz Tech Pvt Ltd
# Server-side API for the Procurement Dashboard page.
#
# Base document: Material Request (submitted, type "Purchase").
# One row per Material Request + Purchase Receipt pair, taken from
# Purchase Receipt Item.material_request (submitted receipts, returns excluded).
# A Material Request with no receipt yet keeps one row (its first PO, if any).
#
# Turnaround time (TAT)   = Material Request created to that Purchase Receipt.
# Full purchase cycle     = Material Request created to the receipt's Purchase Invoice.
# Broken down into six steps:
#
#   MR created ──► PO created ──► submitted for checking ──► checked ──► approved ──► receipt ──► invoice
#        1. MR → PO     2. Preparation     3. Checking       4. Approval    5. Approved → Receipt   6. Receipt → Invoice
#
# Timestamps (per row):
#   MR created       Material Request creation
#   PO               the PO the receipt was made against (Purchase Receipt
#                    Item.purchase_order); rows without a receipt use the MR's
#                    first (earliest) submitted PO
#   PO created       that PO's creation
#   Submitted        first "Checking Pending" in that PO's State Change log
#   Checked          last "Approval Pending" on or before approval (the final pass
#                    through checking; rework loops back to Draft count in Checking)
#   Approved         first "Approved" in that PO's State Change log
#   Receipt          the receipt's posting date + time
#   Invoice          posting date + time of the first submitted Purchase Invoice
#                    (not a debit note) with a line for the receipt
#                    (Purchase Invoice Item.purchase_receipt)
#   When no receipt line carries the MR link, receipts against the MR's POs
#   (Purchase Receipt Item.purchase_order) are used instead.
#
# State Change / State Change Items come from the workflow_transitions app,
# which logs every workflow state change of the Purchase Order.
# A step whose end is before its start (backdated entries) is left out of the
# averages for that step. All durations are returned in hours.

from collections import defaultdict
from statistics import median

import frappe
from frappe import _
from frappe.utils import add_months, get_datetime, getdate, now_datetime, nowdate

STEPS = [
	{"key": "mr_to_po", "label": "MR to PO", "from": "mr", "to": "created"},
	{"key": "preparation", "label": "PO Preparation", "from": "created", "to": "submitted"},
	{"key": "checking", "label": "Checking", "from": "submitted", "to": "checked"},
	{"key": "approval", "label": "Approval", "from": "checked", "to": "approved"},
	{"key": "approved_to_pr", "label": "Approved to Receipt", "from": "approved", "to": "receipt"},
	{"key": "receipt_to_invoice", "label": "Receipt to Invoice", "from": "receipt", "to": "invoice"},
]


@frappe.whitelist()
def get_dashboard_data(
	from_date: str | None = None,
	to_date: str | None = None,
	branch: str | None = None,
	supplier: str | None = None,
) -> dict:
	frappe.has_permission("Material Request", "read", throw=True)

	to_date = getdate(to_date or nowdate())
	from_date = getdate(from_date or add_months(to_date, -6))
	if from_date > to_date:
		frappe.throw(_("From Date cannot be after To Date"))

	filters = {
		"docstatus": 1,
		"material_request_type": "Purchase",
		"transaction_date": ["between", [from_date, to_date]],
	}
	if branch:
		filters["branch"] = branch
	if supplier:
		filters["name"] = ["in", get_mrs_for_supplier(supplier, from_date, to_date) or [""]]

	# get_list applies the user's permissions (e.g. branch restrictions)
	mrs = frappe.get_list(
		"Material Request",
		filters=filters,
		fields=["name", "branch", "transaction_date", "creation", "status", "per_ordered", "per_received"],
		order_by="transaction_date asc, creation asc",
		limit_page_length=0,
	)
	if not mrs:
		return {"steps": STEPS, "summary": None, "months": [], "rows": []}

	names = [m.name for m in mrs]
	po_links = get_po_links(names)  # mr -> [po dicts, earliest first]
	pairs = get_receipt_pairs("material_request", names)  # mr -> [receipt dicts]
	# MRs whose receipt lines carry no MR link: fall back to receipts of their POs
	missing = [n for n in names if not pairs.get(n) and po_links.get(n)]
	if missing:
		by_po = get_receipt_pairs("purchase_order", sorted({p["name"] for n in missing for p in po_links[n]}))
		for n in missing:
			found = {}
			for p in po_links[n]:
				for r in by_po.get(p["name"], []):
					found.setdefault(r["receipt"], {**r, "po": p["name"]})
			if found:
				pairs[n] = sorted(found.values(), key=lambda r: (r["time"], r["receipt"]))

	po_info = get_po_info(
		{p["name"] for links in po_links.values() for p in links}
		| {r["po"] for receipts in pairs.values() for r in receipts if r["po"]}
	)
	trails = get_state_trails(sorted(po_info))
	invoices = get_invoices(sorted({r["receipt"] for receipts in pairs.values() for r in receipts}))
	now = now_datetime()

	rows = []
	for m in mrs:
		links = po_links.get(m.name, [])
		receipts = pairs.get(m.name, [])
		common = {
			"name": m.name,
			"branch": m.branch,
			"transaction_date": m.transaction_date,
			"mr_status": m.status,
			"po_count": len(links),
			"receipt_count": len(receipts),
		}
		if receipts:
			for i, r in enumerate(receipts, start=1):
				rows.append(make_row(m, common, r["po"] or (links[0]["name"] if links else None),
					po_info, trails, r, i, now, invoices.get(r["receipt"])))
		else:
			rows.append(make_row(m, common, links[0]["name"] if links else None, po_info, trails, None, 0, now, None))

	if supplier:
		rows = [r for r in rows if r["supplier"] == supplier]

	summary = summarise(rows)

	return {
		"steps": STEPS,
		"summary": summary,
		"months": monthly_trend(rows),
		"rows": rows,
		"from_date": from_date,
		"to_date": to_date,
	}


def make_row(m, common, po_name, po_info, trails, receipt, receipt_no, now, invoice):
	po = po_info.get(po_name) if po_name else None
	trail = trails.get(po_name, []) if po_name else []
	approved = first_state(trail, "Approved")
	receipt_time = receipt["time"] if receipt else None

	times = {
		"mr": get_datetime(m.creation),
		"created": po["creation"] if po else None,
		"submitted": first_state(trail, "Checking Pending"),
		"checked": last_state(trail, "Approval Pending", before=approved),
		"approved": approved,
		"receipt": receipt_time,
		"invoice": invoice["time"] if invoice else None,
	}
	durations = {s["key"]: hours_between(times[s["from"]], times[s["to"]]) for s in STEPS}
	durations["turnaround"] = hours_between(times["mr"], times["receipt"])
	durations["po_cycle"] = hours_between(times["created"], times["approved"])
	durations["full_cycle"] = hours_between(times["mr"], times["invoice"])

	if invoice:
		stage = "Invoiced"
	elif receipt:
		stage = "Awaiting Invoice"
	elif approved:
		stage = "Awaiting Receipt"
	elif po:
		stage = "PO in Approval"
	elif m.status == "Stopped":
		stage = "Stopped"
	else:
		stage = "Awaiting PO"

	return {
		**common,
		"key": f"{m.name}|{receipt['receipt'] if receipt else ''}",
		"stage": stage,
		# age of an MR without a receipt: hours since it was created
		"age": None if receipt or stage == "Stopped" else hours_between(times["mr"], now),
		"purchase_order": po_name,
		"supplier": (receipt and receipt.get("supplier")) or (po and po["supplier"]),
		"purchase_receipt": receipt["receipt"] if receipt else None,
		"receipt_date": receipt_time.date() if receipt_time else None,
		"receipt_no": receipt_no,
		"purchase_invoice": invoice["name"] if invoice else None,
		"invoice_date": invoice["time"].date() if invoice else None,
		"invoice_count": invoice["count"] if invoice else 0,
		"rework": max(0, sum(1 for t in trail if t[0] == "Checking Pending") - 1),
		**durations,
	}


# ---------------------------------------------------------------- data
def get_mrs_for_supplier(supplier, from_date, to_date):
	"""Material Requests that have a submitted PO for this supplier."""
	return frappe.db.sql_list(
		"""
		SELECT DISTINCT poi.material_request
		FROM `tabPurchase Order Item` poi
		JOIN `tabPurchase Order` po ON po.name = poi.parent
		JOIN `tabMaterial Request` mr ON mr.name = poi.material_request
		WHERE po.docstatus = 1 AND po.supplier = %(supplier)s
			AND mr.transaction_date BETWEEN %(from_date)s AND %(to_date)s
		""",
		{"supplier": supplier, "from_date": from_date, "to_date": to_date},
	)


def get_po_links(mr_names):
	"""Submitted POs made from each MR, earliest created first."""
	data = frappe.db.sql(
		"""
		SELECT DISTINCT poi.material_request, po.name, po.creation, po.supplier
		FROM `tabPurchase Order Item` poi
		JOIN `tabPurchase Order` po ON po.name = poi.parent
		WHERE poi.material_request IN %(names)s AND po.docstatus = 1
		ORDER BY poi.material_request, po.creation
		""",
		{"names": tuple(mr_names)},
		as_dict=True,
	)
	links = defaultdict(list)
	for d in data:
		links[d.material_request].append(
			{"name": d.name, "creation": get_datetime(d.creation), "supplier": d.supplier}
		)
	return links


def get_state_trails(po_names):
	"""Workflow state changes per PO, oldest first: [(state, datetime), ...]."""
	if not po_names:
		return {}
	data = frappe.db.sql(
		"""
		SELECT sc.document_name, sci.workflow_state, sci.modification_time
		FROM `tabState Change` sc
		JOIN `tabState Change Items` sci ON sci.parent = sc.name
		WHERE sc.doctype_name = 'Purchase Order' AND sc.document_name IN %(names)s
			AND sci.workflow_state IS NOT NULL AND sci.modification_time IS NOT NULL
		ORDER BY sc.document_name, sci.modification_time, sci.idx
		""",
		{"names": tuple(po_names)},
	)
	trails = defaultdict(list)
	for po, state, time in data:
		trails[po].append((state, get_datetime(time)))
	return trails


def get_receipt_pairs(field, values):
	"""Submitted, non-return Purchase Receipts per MR or PO (field is the receipt
	line's link field), earliest posting first:
	{value: [{"receipt", "time", "po", "supplier"}, ...]}."""
	if not values:
		return {}
	data = frappe.db.sql(
		f"""
		SELECT pri.{field} AS link, pr.name AS receipt, pr.supplier,
			TIMESTAMP(pr.posting_date, pr.posting_time) AS ts,
			MIN(pri.purchase_order) AS po
		FROM `tabPurchase Receipt Item` pri
		JOIN `tabPurchase Receipt` pr ON pr.name = pri.parent
		WHERE pri.{field} IN %(values)s AND pr.docstatus = 1 AND pr.is_return = 0
		GROUP BY pri.{field}, pr.name, pr.supplier, pr.posting_date, pr.posting_time
		ORDER BY pri.{field}, ts, pr.name
		""",
		{"values": tuple(values)},
		as_dict=True,
	)
	result = defaultdict(list)
	for d in data:
		result[d.link].append(
			{"receipt": d.receipt, "time": get_datetime(d.ts), "po": d.po, "supplier": d.supplier}
		)
	return result


def get_invoices(receipt_names):
	"""First submitted Purchase Invoice (not a debit note) per receipt:
	{receipt: {"name", "time", "count"}}, first = earliest posting."""
	if not receipt_names:
		return {}
	data = frappe.db.sql(
		"""
		SELECT pii.purchase_receipt AS receipt, pi.name,
			TIMESTAMP(pi.posting_date, COALESCE(pi.posting_time, '00:00:00')) AS ts
		FROM `tabPurchase Invoice Item` pii
		JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
		WHERE pii.purchase_receipt IN %(names)s AND pi.docstatus = 1 AND pi.is_return = 0
		GROUP BY pii.purchase_receipt, pi.name, pi.posting_date, pi.posting_time
		ORDER BY pii.purchase_receipt, ts, pi.name
		""",
		{"names": tuple(receipt_names)},
		as_dict=True,
	)
	result = {}
	for d in data:
		entry = result.setdefault(d.receipt, {"name": d.name, "time": get_datetime(d.ts), "count": 0, "names": []})
		entry["count"] += 1
		entry["names"].append(d.name)
	return result


def get_po_info(po_names):
	if not po_names:
		return {}
	data = frappe.get_all(
		"Purchase Order",
		filters={"name": ["in", list(po_names)]},
		fields=["name", "creation", "supplier"],
	)
	return {d.name: {"creation": get_datetime(d.creation), "supplier": d.supplier} for d in data}


def first_state(trail, state):
	return next((t for s, t in trail if s == state), None)


def last_state(trail, state, before=None):
	hits = [t for s, t in trail if s == state and (before is None or t <= before)]
	return hits[-1] if hits else None


def hours_between(start, end):
	"""Hours from start to end; None when missing or negative (backdated)."""
	if not start or not end:
		return None
	hours = (end - start).total_seconds() / 3600
	return round(hours, 2) if hours >= 0 else None


# ---------------------------------------------------------------- aggregates
DURATION_KEYS = [s["key"] for s in STEPS] + ["turnaround", "po_cycle", "full_cycle"]


def stats(values):
	values = [v for v in values if v is not None]
	if not values:
		return {"count": 0, "avg": None, "median": None, "max": None}
	return {
		"count": len(values),
		"avg": round(sum(values) / len(values), 2),
		"median": round(median(values), 2),
		"max": round(max(values), 2),
	}


def summarise(rows):
	# stage per Material Request: "Awaiting Invoice" if any of its receipts is not
	# invoiced yet, "Invoiced" when all are; MRs without receipts have one row
	row_stages = defaultdict(set)
	for r in rows:
		row_stages[r["name"]].add(r["stage"])
	mr_stage = {}
	for mr, found in row_stages.items():
		if "Awaiting Invoice" in found:
			mr_stage[mr] = "Awaiting Invoice"
		elif "Invoiced" in found:
			mr_stage[mr] = "Invoiced"
		else:
			mr_stage[mr] = next(iter(found))
	stages = defaultdict(int)
	for stage in mr_stage.values():
		stages[stage] += 1
	return {
		"mr_count": len(mr_stage),
		"row_count": len(rows),
		"receipt_rows": sum(1 for r in rows if r["purchase_receipt"]),
		"invoice_rows": sum(1 for r in rows if r["purchase_invoice"]),
		"with_receipt": stages["Invoiced"] + stages["Awaiting Invoice"],
		"stages": dict(stages),
		"reworked": sum(1 for r in rows if r["rework"]),
		"open_age": stats([r["age"] for r in rows]),
		**{key: stats([r[key] for r in rows]) for key in DURATION_KEYS},
	}


def monthly_trend(rows):
	"""Average hours per step by MR month (transaction date)."""
	by_month = defaultdict(list)
	for r in rows:
		by_month[getdate(r["transaction_date"]).strftime("%Y-%m")].append(r)
	months = []
	for month in sorted(by_month):
		month_rows = by_month[month]
		months.append(
			{
				"month": month,
				"label": getdate(month + "-01").strftime("%b %Y"),
				"mr_count": len({r["name"] for r in month_rows}),
				"received": sum(1 for r in month_rows if r["purchase_receipt"]),
				**{key: stats([r[key] for r in month_rows])["avg"] for key in DURATION_KEYS},
			}
		)
	return months
