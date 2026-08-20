# -*- coding: utf-8 -*-
# Copyright (c) 2026, Steelstrong / Custom App
# License: MIT / see LICENSE
"""
Production Plan & Work Order Update Control Report
====================================================

Single-screen manufacturing control center that shows, for every Sales
Order, whether a downstream change (Order Modification Request -> BOM
Modification Request -> Production Plan -> Work Order) has been fully
propagated.

Flow:
1. OMR submitted → Production Plan sales_order_modification = "Yes"
2. BMR submitted → Production Plan bom_modification = "Yes"
3. Production Plan "Get Update" button clicked → updates applied
4. Work Orders created FROM Production Plans (PP → WO relationship)
5. Report shows only WOs linked to both SO and its PPs
"""

from __future__ import unicode_literals

import json
import io
from datetime import datetime, timedelta
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

import frappe
from frappe import _
from frappe.utils import (
	add_days,
	add_months,
	cint,
	cstr,
	flt,
	get_first_day,
	get_last_day,
	getdate,
	nowdate,
	pretty_date,
	now_datetime,
)


# --------------------------------------------------------------------------- #
# Badge / severity vocabulary
# --------------------------------------------------------------------------- #

BADGES = {
	"updated": {"key": "updated", "emoji": "", "label": "Updated", "color": "green"},
	"pending": {"key": "pending", "emoji": "", "label": "Pending", "color": "amber"},
	"critical": {"key": "critical", "emoji": "", "label": "Critical", "color": "red"},
	"not_required": {"key": "not_required", "emoji": "", "label": "Not Required", "color": "blue"},
	"waiting": {"key": "waiting", "emoji": "", "label": "Waiting", "color": "grey"},
}


SEVERITY_ORDER = ["Critical", "High", "Low"]
SEVERITY_COLOR = {
	"Critical": "red",
	"High": "amber",
	"Low": "green",
}
SEVERITY_FILL_HEX = {
	"Critical": "E86161",
	"High": "F5A623",
	"Low": "5EBB63",
}
BADGE_FILL_HEX = {
	"updated": "5EBB63",
	"pending": "F5A623",
	"critical": "E86161",
	"not_required": "4C9CE2",
	"waiting": "98A6BF",
}


STAGE_KEYS = ["so", "omr", "bmr", "pp", "wo", "completed"]
STAGE_LABEL = {
	"so": "SO",
	"omr": "OMR",
	"bmr": "BMR",
	"pp": "PP",
	"wo": "WO",
	"completed": "Completed",
}

PERIOD_OPTIONS = [
	{"value": "", "label": "All Time"},
	{"value": "today", "label": "Today"},
	{"value": "this_week", "label": "This Week"},
	{"value": "last_week", "label": "Last Week"},
	{"value": "this_month", "label": "This Month"},
	{"value": "last_month", "label": "Last Month"},
	{"value": "this_year", "label": "This Year"},
	{"value": "last_year", "label": "Last Year"},
	{"value": "custom", "label": "Custom…"},
]


def _badge(key):
	return dict(BADGES[key])


# --------------------------------------------------------------------------- #
# Public whitelisted API
# --------------------------------------------------------------------------- #


@frappe.whitelist()
def get_filter_options():
	"""Static option lists for the sticky filter bar."""
	companies = frappe.get_all("Company", pluck="name", order_by="name")
	if frappe.db.table_exists("Branch"):
		branches = frappe.get_all("Branch", pluck="name", order_by="name")
	else:
		branches = frappe.get_all(
			"Sales Order", pluck="branch", distinct=True, filters={"branch": ["is", "set"]}
		)

	return {
		"companies": companies,
		"branches": [b for b in branches if b],
		"period_options": PERIOD_OPTIONS,
		"default_from": add_days(nowdate(), -90),
		"default_to": nowdate(),
	}


@frappe.whitelist()
def get_dashboard_data(filters=None):
	"""KPI cards + overall sync ring."""
	rows = _get_computed_rows(_parse_filters(filters), limit=2000)

	pending_pp = sum(1 for r in rows if r["pp_update_required"])
	pending_wo = sum(1 for r in rows if r["wo_update_required"])
	pending_bmr = sum(1 for r in rows if r["bmr_exists"] and not r["bmr_all_approved"])
	pending_omr = sum(1 for r in rows if r["omr_exists"] and not r["omr_approved"])
	completed = sum(1 for r in rows if r["severity"] == "Low")
	critical = sum(1 for r in rows if r["severity"] == "Critical")

	trackable = sum(1 for r in rows if r["omr_exists"])
	sync_pct = round((completed / trackable) * 100, 1) if trackable else 100.0

	return {
		"pending_pp": pending_pp,
		"pending_wo": pending_wo,
		"pending_bmr": pending_bmr,
		"pending_omr": pending_omr,
		"completed": completed,
		"critical": critical,
		"total": len(rows),
		"trackable": trackable,
		"sync_pct": sync_pct,
		"all_clear": trackable > 0 and pending_pp == 0 and pending_wo == 0 and pending_bmr == 0 and critical == 0,
	}


@frappe.whitelist()
def get_grid_data(filters=None, start=0, page_length=50):
	"""Paginated grid rows."""
	start = cint(start)
	page_length = cint(page_length) or 50

	rows = _get_computed_rows(_parse_filters(filters), limit=2000)
	total = len(rows)
	page = rows[start : start + page_length]

	return {"rows": page, "total": total, "start": start, "page_length": page_length}


@frappe.whitelist()
def get_row_detail(sales_order, filters=None):
	"""Everything the right-hand drawer needs for a single Sales Order."""
	if not sales_order:
		frappe.throw(_("Sales Order is required"))

	if isinstance(filters, str):
		try:
			filters = json.loads(filters)
		except Exception:
			filters = {}

	so = frappe.db.get_value(
		"Sales Order",
		sales_order,
		[
			"name", "customer", "customer_name", "branch", "company", "transaction_date",
			"delivery_date", "status", "grand_total", "currency", "owner", "modified", "modified_by",
		],
		as_dict=True,
	)
	if not so:
		frappe.throw(_("Sales Order {0} not found").format(sales_order))

	omrs = frappe.get_all(
		"Order Modification Request",
		filters={"sales_order": sales_order},
		fields=[
			"name", "workflow_state", "docstatus", "reason_for_change", "modification_type",
			"type", "creation", "owner", "modified", "modified_by",
		],
		order_by="creation desc",
	)

	omr_names = [o.name for o in omrs]
	omr_items = []
	if omr_names:
		omr_items = frappe.get_all(
			"Sales Order Item For OMR",
			filters={"parent": ["in", omr_names]},
			fields=[
				"parent", "item", "rev_item", "description", "rev_description",
				"qty", "rev_qty", "bom_update_request", "tag_no", "line_status", "rev_line_status",
			],
		)

	bmr_names = sorted({d.bom_update_request for d in omr_items if d.bom_update_request})
	bmrs = []
	if bmr_names:
		bmrs = frappe.get_all(
			"Bom Modification Request",
			filters={"name": ["in", bmr_names]},
			fields=[
				"name", "workflow_state", "docstatus", "fg_item_code", "fg_item_name",
				"item_description", "reason_for_change", "batch_no_ref", "creation",
				"modified", "modified_by",
			],
		)

	filtered_pp = filters.get("production_plan") if filters else None
	maps = _fetch_maps([sales_order], filtered_pp=filtered_pp)
	row = _compute_row(so, maps)

	chosen_pp = maps["pp"].get(sales_order)
	pps = [chosen_pp] if chosen_pp else []
	wos = row["wo_list"]

	pending_actions = []
	if row["omr_exists"] and not row["omr_approved"]:
		pending_actions.append(_("Get Order Modification Request {0} approved.").format(row["omr"]["name"]))
	if row["bmr_exists"] and not row["bmr_all_approved"]:
		pending_names = ", ".join(b["name"] for b in row["bmr_pending"])
		pending_actions.append(_("Approve BOM Modification Request(s): {0}.").format(pending_names))
	if row["pp_update_required"]:
		pending_actions.append(_("Click 'Get Update' on the Production Plan to apply the approved BOM change."))
	if row["wo_update_required"]:
		wo_names = ", ".join(w.get("name") for w in wos if w.get("modification_status") == "Yes")
		pending_actions.append(_("Re-issue / update Work Order(s): {0}.").format(wo_names))
	if not pending_actions:
		pending_actions.append(_("Nothing pending - fully synchronised. ✅"))

	history = []
	for o in omrs:
		history.append({
			"time": o.creation, "doctype": "Order Modification Request", "name": o.name,
			"event": _("Change request raised"), "state": o.workflow_state,
			"user": o.owner,
		})
	for b in bmrs:
		history.append({
			"time": b.creation, "doctype": "Bom Modification Request", "name": b.name,
			"event": _("BOM change requested"), "state": b.workflow_state,
			"user": b.modified_by,
		})
	for p in pps:
		history.append({
			"time": p.creation, "doctype": "Production Plan", "name": p.name,
			"event": _("Production Plan updated") if p.production_plan_updated else _("Production Plan linked"),
			"state": p.status, "user": p.modified_by,
		})
	for w in wos:
		history.append({
			"time": w.get("creation"), "doctype": "Work Order", "name": w.get("name"),
			"event": _("Work Order updated") if w.get("modification_status") == "No" else _("Work Order pending update"),
			"state": w.get("status"), "user": w.get("modified_by"),
		})
	history.sort(key=lambda h: str(h["time"]) if h["time"] else "", reverse=True)

	return {
		"so": so,
		"row": row,
		"omrs": omrs,
		"omr_items": omr_items,
		"bmrs": bmrs,
		"pps": pps,
		"wos": wos,
		"pending_actions": pending_actions,
		"history": history,
	}


@frappe.whitelist()
def refresh_row(sales_order, filters=None):
	"""Nothing is cached server side."""
	if isinstance(filters, str):
		try:
			filters = json.loads(filters)
		except Exception:
			filters = {}
	
	filtered_pp = filters.get("production_plan") if filters else None
	maps = _fetch_maps([sales_order], filtered_pp=filtered_pp)
	so = frappe.db.get_value(
		"Sales Order",
		sales_order,
		["name", "customer", "customer_name", "branch", "company", "transaction_date",
		 "delivery_date", "status", "grand_total", "modified", "modified_by"],
		as_dict=True,
	)
	if not so:
		frappe.throw(_("Sales Order {0} not found").format(sales_order))
	return _compute_row(so, maps)


@frappe.whitelist()
def get_charts_data(filters=None):
	rows = _get_computed_rows(_parse_filters(filters), limit=2000)

	by_branch = {}
	for r in rows:
		b = r["branch"] or _("Unassigned")
		slot = by_branch.setdefault(b, {"pending": 0, "total": 0})
		slot["total"] += 1
		if r["is_pending"]:
			slot["pending"] += 1
	branch_labels = sorted(by_branch.keys())
	branch_pending = [by_branch[b]["pending"] for b in branch_labels]
	branch_total = [by_branch[b]["total"] for b in branch_labels]

	sev_counts = {s: 0 for s in SEVERITY_ORDER}
	for r in rows:
		sev_counts[r["severity"]] += 1

	funnel = {
		"SO": len(rows),
		"OMR": sum(1 for r in rows if r["omr_exists"]),
		"BMR": sum(1 for r in rows if r["bmr_exists"]),
		"PP Updated": sum(1 for r in rows if r["pp_updated_flag"]),
		"WO Updated": sum(1 for r in rows if r["wo_synced"]),
		"Completed": sum(1 for r in rows if r["severity"] == "Low" and r["omr_exists"]),
	}

	trend = {}
	start_date = getdate(add_days(nowdate(), -29))
	d = start_date
	while d <= getdate(nowdate()):
		trend[cstr(d)] = 0
		d = add_days(d, 1)
	for r in rows:
		if not r["is_pending"] or not r["omr"]:
			continue
		created = getdate(r["omr"]["creation"]) if r["omr"].get("creation") else None
		if created and cstr(created) in trend:
			trend[cstr(created)] += 1

	branch_perf = []
	for b in branch_labels:
		total = by_branch[b]["total"]
		pending = by_branch[b]["pending"]
		synced = total - pending
		branch_perf.append({
			"branch": b, "total": total, "synced": synced, "pending": pending,
			"sync_pct": round((synced / total) * 100, 1) if total else 100.0,
		})

	return {
		"branch": {"labels": branch_labels, "pending": branch_pending, "total": branch_total},
		"status_distribution": {"labels": list(sev_counts.keys()), "values": list(sev_counts.values())},
		"funnel": funnel,
		"trend": {"labels": list(trend.keys()), "values": list(trend.values())},
		"branch_performance": branch_perf,
	}


@frappe.whitelist()
def bulk_assign(sales_orders, assign_to, description=None):
	"""Minimal bulk 'Assign' action."""
	names = sales_orders
	if isinstance(names, str):
		names = json.loads(names)

	created = 0
	for so in names:
		if not frappe.db.exists("Sales Order", so):
			continue
		frappe.get_doc({
			"doctype": "ToDo",
			"allocated_to": assign_to,
			"reference_type": "Sales Order",
			"reference_name": so,
			"description": description or _("Please review pending update propagation for {0}").format(so),
		}).insert(ignore_permissions=True)
		created += 1

	return {"created": created}


@frappe.whitelist()
def export_excel(filters=None, sales_orders=None):
	"""Server-side export as a colour-coded .xlsx, matching dashboard badges."""
	if sales_orders:
		if isinstance(sales_orders, str):
			sales_orders = json.loads(sales_orders)
		so_dicts = frappe.get_all(
			"Sales Order",
			filters={"name": ["in", sales_orders]},
			fields=["name", "customer", "customer_name", "branch", "company",
					"transaction_date", "delivery_date", "status", "grand_total",
					"currency", "owner", "modified", "modified_by"],
		)
		maps = _fetch_maps([s.name for s in so_dicts])
		rows = [_compute_row(s, maps) for s in so_dicts]
	else:
		rows = _get_computed_rows(_parse_filters(filters), limit=5000)

	# Updated columns for export
	columns = [
		"Sales Order", "Customer", "Pending At", "OMR", "OMR Status",
		"BMR", "BMR Status", "Production Plan", "PP Status",
		"Work Order", "WO Status", "Severity", "Remarks",
		"Updated By", "Updated Time",
	]

	wb = Workbook()
	ws = wb.active
	ws.title = "PP & WO Control Report"

	thin = Side(style="thin", color="D9E2EC")
	border = Border(left=thin, right=thin, top=thin, bottom=thin)
	header_fill = PatternFill(start_color="2490EF", end_color="2490EF", fill_type="solid")
	header_font = Font(color="FFFFFF", bold=True, size=11)

	for col_idx, title in enumerate(columns, start=1):
		cell = ws.cell(row=1, column=col_idx, value=title)
		cell.fill = header_fill
		cell.font = header_font
		cell.alignment = Alignment(horizontal="center", vertical="center")
		cell.border = border

	ws.freeze_panes = "A2"
	ws.auto_filter.ref = "A1:{0}1".format(get_column_letter(len(columns)))

	BADGE_COL_MAP = {5: "omr_badge", 7: "bmr_badge", 9: "pp_status_badge", 11: "wo_status_badge"}
	SEVERITY_COL = 12

	row_idx = 2
	for r in rows:
		bmr_list = [b["name"] for b in r.get("bmr_list", [])]
		wo_list = [w["name"] for w in r.get("wo_list", [])]
		remark = r.get("remarks", "")

		values = [
			_clean(r.get("sales_order")),
			_clean(r.get("customer_name")),
			_clean(r.get("pending_at")),
			_clean(r["omr"]["name"] if r.get("omr") else ""),
			_clean(r["omr_badge"]["label"] if r.get("omr_badge") else ""),
			_clean(_format_doc_list(bmr_list)),
			_clean(r["bmr_badge"]["label"] if r.get("bmr_badge") else ""),
			_clean(r["pp"]["name"] if r.get("pp") else ""),
			_clean(r["pp_status_badge"]["label"] if r.get("pp_status_badge") else ""),
			_clean(_format_doc_list(wo_list)),
			_clean(r["wo_status_badge"]["label"] if r.get("wo_status_badge") else ""),
			_clean(r.get("severity")),
			_clean(remark),
			_clean(r.get("modified_by")),
			_clean(pretty_date(r.get("modified")) if r.get("modified") else ""),
		]

		for col_idx, val in enumerate(values, start=1):
			cell = ws.cell(row=row_idx, column=col_idx, value=val)
			cell.border = border
			cell.alignment = Alignment(vertical="center")

		colored_cols = set()

		for col_idx, badge_key in BADGE_COL_MAP.items():
			badge = r.get(badge_key)
			if not badge:
				continue
			key = badge.get("key")
			if key not in ("pending", "critical"):
				continue

			hexcode = BADGE_FILL_HEX[key]
			cell = ws.cell(row=row_idx, column=col_idx)
			cell.fill = PatternFill(start_color=hexcode, end_color=hexcode, fill_type="solid")
			cell.font = Font(color="FFFFFF", bold=True)
			cell.alignment = Alignment(horizontal="center", vertical="center")
			colored_cols.add(col_idx)

		sev = r.get("severity")
		if sev == "Critical":
			hexcode = SEVERITY_FILL_HEX[sev]
			cell = ws.cell(row=row_idx, column=SEVERITY_COL)
			cell.fill = PatternFill(start_color=hexcode, end_color=hexcode, fill_type="solid")
			cell.font = Font(color="FFFFFF", bold=True)
			cell.alignment = Alignment(horizontal="center", vertical="center")
			colored_cols.add(SEVERITY_COL)

		if sev == "Critical":
			tint = PatternFill(start_color="FDEDED", end_color="FDEDED", fill_type="solid")
			for col_idx in range(1, len(columns) + 1):
				if col_idx not in colored_cols:
					ws.cell(row=row_idx, column=col_idx).fill = tint

		row_idx += 1

	widths = [16, 22, 22, 16, 14, 34, 14, 16, 14, 34, 14, 12, 30, 14, 14]
	for i, w in enumerate(widths, start=1):
		ws.column_dimensions[get_column_letter(i)].width = w

	buf = io.BytesIO()
	wb.save(buf)
	buf.seek(0)

	frappe.response["filename"] = "production_plan_wo_control_report.xlsx"
	frappe.response["filecontent"] = buf.getvalue()
	frappe.response["content_type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
	frappe.response["type"] = "download"


def _clean(value):
	"""Normalise 'empty' placeholder values."""
	if value is None:
		return ""
	value = cstr(value).strip()
	if value in ("—", "-", "--", "N/A", "n/a", "None"):
		return ""
	return value


def _format_doc_list(names):
	"""Format a list of linked document names for display."""
	if not names:
		return ""
	return "|".join(names)


# --------------------------------------------------------------------------- #
# Internal helpers
# --------------------------------------------------------------------------- #


def _parse_filters(filters):
	if not filters:
		return {}
	if isinstance(filters, str):
		try:
			return json.loads(filters)
		except Exception:
			return {}
	return filters


def _resolve_period_range(filters):
	"""Turn the client's named `period` into an actual (from_date, to_date) pair."""
	period = (filters.get("period") or "").strip().lower()
	if not period or period in ("all", "any", "all_time"):
		return None

	today = getdate(nowdate())

	if period == "today":
		return today, today
	if period == "this_week":
		start = add_days(today, -today.weekday())
		return start, add_days(start, 6)
	if period == "last_week":
		this_week_start = add_days(today, -today.weekday())
		start = add_days(this_week_start, -7)
		return start, add_days(start, 6)
	if period == "this_month":
		return get_first_day(today), get_last_day(today)
	if period == "last_month":
		prev = add_months(today, -1)
		return get_first_day(prev), get_last_day(prev)
	if period == "this_year":
		return getdate(f"{today.year}-01-01"), getdate(f"{today.year}-12-31")
	if period == "last_year":
		y = today.year - 1
		return getdate(f"{y}-01-01"), getdate(f"{y}-12-31")
	if period == "custom":
		f = filters.get("from_date")
		t = filters.get("to_date")
		if f and t:
			return getdate(f), getdate(t)
		return None

	return None


def _resolve_link_filters(filters):
	"""Turn link filters into a restricted set of Sales Order names."""
	restrict = None

	def _intersect(names):
		nonlocal restrict
		names = set(names)
		restrict = names if restrict is None else (restrict & names)

	if filters.get("omr"):
		so = frappe.db.get_value("Order Modification Request", filters["omr"], "sales_order")
		_intersect([so] if so else [])

	if filters.get("bmr"):
		parents = frappe.get_all(
			"Sales Order Item For OMR",
			filters={"bom_update_request": filters["bmr"]},
			pluck="parent",
		)
		sos = []
		if parents:
			sos = frappe.get_all(
				"Order Modification Request", 
				filters={"name": ["in", parents]},
				pluck="sales_order"
			)
		_intersect(sos)

	if filters.get("production_plan"):
		sos = frappe.get_all(
			"Production Plan Sales Order", 
			filters={"parent": filters["production_plan"]},
			pluck="sales_order"
		)
		_intersect(sos)

	if filters.get("work_order"):
		pp = frappe.db.get_value("Work Order", filters["work_order"], "production_plan")
		if pp:
			sos = frappe.get_all(
				"Production Plan Sales Order",
				filters={"parent": pp},
				pluck="sales_order"
			)
			_intersect(sos)
		else:
			so = frappe.db.get_value("Work Order", filters["work_order"], "sales_order")
			if so:
				_intersect([so])
			else:
				_intersect([])

	return restrict


def _get_filtered_sales_orders(filters):
	"""Build the base Sales Order query with all filters."""
	so = frappe.qb.DocType("Sales Order")
	query = (
		frappe.qb.from_(so)
		.select(
			so.name, so.customer, so.customer_name, so.branch, so.company,
			so.transaction_date, so.delivery_date, so.status, so.grand_total,
			so.modified, so.modified_by,
		)
		.where(so.docstatus == 1)
	)

	if filters.get("company"):
		query = query.where(so.company == filters["company"])
	if filters.get("branch"):
		query = query.where(so.branch == filters["branch"])
	if filters.get("customer"):
		query = query.where(so.customer == filters["customer"])
	if filters.get("sales_order"):
		query = query.where(so.name == filters["sales_order"])

	period_range = _resolve_period_range(filters)
	if period_range:
		query = query.where(so.transaction_date[cstr(period_range[0]):cstr(period_range[1])])

	restrict = _resolve_link_filters(filters)
	if restrict is not None:
		if not restrict:
			return []
		query = query.where(so.name.isin(list(restrict)))

	query = query.orderby(so.modified, order=frappe.qb.desc).limit(2000)
	return query.run(as_dict=True)



def _fetch_maps(so_names, filtered_pp=None):
	"""Batch-fetch every related doctype for the given Sales Orders."""
	maps = {
		"omr": {},
		"omr_all": {},
		"omr_bmr": {},
		"omr_items": {},  # Store OMR items for change type detection
		"bmr": {},
		"pp": {},
		"wo": {},
	}
	if not so_names:
		return maps

	# Fetch OMRs with additional fields
	omrs = frappe.get_all(
		"Order Modification Request",
		filters={"sales_order": ["in", so_names]},
		fields=[
			"name", "sales_order", "workflow_state", "docstatus", 
			"modification_type", "type", "creation", "modified", "modified_by"
		],
		order_by="creation desc",
	)
	for o in omrs:
		maps["omr_all"].setdefault(o.sales_order, []).append(o)
		if o.sales_order not in maps["omr"]:
			maps["omr"][o.sales_order] = o

	omr_names = [o.name for o in omrs]
	if omr_names:
		# Fetch all OMR items (not just those with BMR requests)
		items = frappe.get_all(
			"Sales Order Item For OMR",
			filters={"parent": ["in", omr_names]},
			fields=[
				"parent", "item", "rev_item", "description", "rev_description",
				"qty", "rev_qty", "bom_update_request", "tag_no", 
				"line_status", "rev_line_status", "parenttype", "parentfield"
			],
		)
		
		# Store items by OMR name
		for item in items:
			maps["omr_items"].setdefault(item.parent, []).append(item)
			
			# Also build the BMR mapping for items that have BMR requests
			if item.get("bom_update_request"):
				maps["omr_bmr"].setdefault(item.parent, [])
				if item.bom_update_request not in maps["omr_bmr"][item.parent]:
					maps["omr_bmr"][item.parent].append(item.bom_update_request)

		# Fetch BMRs if they exist
		bmr_names = sorted({n for names in maps["omr_bmr"].values() for n in names})
		if bmr_names:
			bmrs = frappe.get_all(
				"Bom Modification Request",
				filters={"name": ["in", bmr_names]},
				fields=[
					"name", "workflow_state", "docstatus", "fg_item_code", 
					"fg_item_name", "item_description", "reason_for_change",
					"batch_no_ref", "creation", "modified", "modified_by"
				],
			)
			for b in bmrs:
				maps["bmr"][b.name] = b

	# Fetch Production Plan links
	pp_link_filters = {"sales_order": ["in", so_names]}
	if filtered_pp:
		pp_link_filters["parent"] = filtered_pp

	pp_links = frappe.get_all(
		"Production Plan Sales Order",
		filters=pp_link_filters,
		fields=["parent", "sales_order", "creation"],
		order_by="creation desc",
	)

	pp_names_all = sorted({p.parent for p in pp_links})
	pps_by_name = {}
	if pp_names_all:
		pps = frappe.get_all(
			"Production Plan",
			filters={"name": ["in", pp_names_all]},
			fields=[
				"name", "status", "sales_order_modification", "production_plan_updated",
				"work_order_updated", "bom_modification", "branch", "modified",
				"modified_by", "creation", "docstatus"
			],
		)
		pps_by_name = {p.name: p for p in pps}

	for link in pp_links:
		if link.sales_order not in maps["pp"] and link.parent in pps_by_name:
			maps["pp"][link.sales_order] = pps_by_name[link.parent]

	# Fetch Work Orders linked to chosen PPs
	so_by_chosen_pp = {pp["name"]: so for so, pp in maps["pp"].items()}
	chosen_pp_names = list(so_by_chosen_pp.keys())

	if chosen_pp_names:
		wos = frappe.get_all(
			"Work Order",
			filters={
				"production_plan": ["in", chosen_pp_names],
				"docstatus": ["!=", 2],
			},
			fields=[
				"name", "sales_order", "production_plan", "status", 
				"modification_status",
				"qty", "produced_qty", "production_item", "item_name", "bom_no",
				"docstatus", "creation", "modified", "modified_by", "planned_start_date"
			],
		)

		for w in wos:
			target_so = so_by_chosen_pp.get(w.production_plan)
			if not target_so or target_so not in so_names:
				continue
			wo_so = w.sales_order or target_so
			if wo_so == target_so:
				maps["wo"].setdefault(target_so, []).append(w)

	return maps


def _compute_row(so, maps):
	"""Compute all derived status fields for a single Sales Order with time-based stage logic."""
	so_name = so["name"] if isinstance(so, dict) else so.name
	get = so.get if isinstance(so, dict) else (lambda k, d=None: getattr(so, k, d))

	omr = maps["omr"].get(so_name)
	omr_exists = bool(omr)
	omr_approved = bool(omr and omr.get("workflow_state") == "Approved") if isinstance(omr, dict) else bool(
		omr and omr.workflow_state == "Approved"
	)
	omr_dict = dict(omr) if omr else None

	# Determine OMR change type based on actual data
	omr_change_type = None
	if omr_dict:
		# Check for modification_type field
		omr_change_type = omr_dict.get("modification_type") or omr_dict.get("type")
		
		# Check if any items have rev_qty different from qty (indicating quantity change)
		has_qty_change = False
		has_item_replacement = False
		
		omr_items = maps.get("omr_items", {}).get(omr_dict.get("name"), [])
		for item in omr_items:
			# Check for quantity change (rev_qty differs from qty)
			if item.get("rev_qty") is not None and flt(item.get("rev_qty")) != flt(item.get("qty")):
				has_qty_change = True
			# Check for BOM update request (item replacement)
			if item.get("bom_update_request"):
				has_item_replacement = True
			# Check for item replacement (rev_item differs from item)
			if item.get("rev_item") and item.get("rev_item") != item.get("item"):
				has_item_replacement = True
		
		# Determine change type based on actual data
		if has_item_replacement:
			omr_change_type = "Item Replacement"
		elif has_qty_change:
			omr_change_type = "Quantity Change"
		else:
			# Fallback to modification_type if available
			if "Quantity" in str(omr_change_type or ""):
				omr_change_type = "Quantity Change"
			elif "Replacement" in str(omr_change_type or ""):
				omr_change_type = "Item Replacement"
			else:
				# Default to Item Replacement for safety
				omr_change_type = "Item Replacement"
	else:
		# No OMR exists
		omr_change_type = "No Change"

	bmr_names = maps["omr_bmr"].get(omr["name"] if omr_dict else None, []) if omr_dict else []
	bmr_list = [dict(maps["bmr"][n]) for n in bmr_names if n in maps["bmr"]]
	bmr_exists = len(bmr_list) > 0
	
	# Enhanced BMR state detection
	bmr_draft_list = []
	bmr_submitted_list = []
	bmr_approved_list = []
	bmr_rejected_list = []
	
	for b in bmr_list:
		docstatus = cint(b.get("docstatus", 0))
		workflow_state = b.get("workflow_state", "")
		
		if docstatus == 0:
			bmr_draft_list.append(b)
		elif docstatus == 1:
			if workflow_state == "Approved":
				bmr_approved_list.append(b)
			elif workflow_state in ("Rejected", "Cancelled"):
				bmr_rejected_list.append(b)
			else:
				bmr_submitted_list.append(b)
		elif docstatus == 2:
			bmr_rejected_list.append(b)
	
	bmr_any_approved = len(bmr_approved_list) > 0
	bmr_all_approved = bmr_exists and len(bmr_approved_list) == len(bmr_list)
	bmr_any_draft = len(bmr_draft_list) > 0
	bmr_any_submitted = len(bmr_submitted_list) > 0
	bmr_any_rejected = len(bmr_rejected_list) > 0
	bmr_pending_list = bmr_draft_list + bmr_submitted_list

	pp = maps["pp"].get(so_name)
	pp_dict = dict(pp) if pp else None
	pp_exists = bool(pp_dict)

	# Check PP modification and update flags - SAFE ACCESS
	pp_is_old = False
	pp_has_modification = False
	pp_updated_flag = False
	pp_wo_updated_flag = False
	pp_is_updated = False

	if pp_dict:
		# SAFELY get sales_order_modification (dict or object access)
		sales_order_mod = (
			pp_dict.get("sales_order_modification")
			if isinstance(pp_dict, dict)
			else getattr(pp_dict, "sales_order_modification", None)
		)

		# Normalize to a clean uppercase string regardless of source type
		# (handles None, "", "  ", bool True/False, int 0/1, "Yes"/"no", etc.)
		if sales_order_mod is None:
			sales_order_mod_str = ""
		elif isinstance(sales_order_mod, bool):
			# Guard against bool being stringified as "True"/"False" instead of "1"/"0"
			sales_order_mod_str = "1" if sales_order_mod else "0"
		else:
			sales_order_mod_str = cstr(sales_order_mod).strip()

		sales_order_mod_upper = sales_order_mod_str.upper()

		if sales_order_mod_upper == "":
			# OLD PP - no modification tracking on this record at all
			pp_is_old = True
			pp_has_modification = False
		elif sales_order_mod_upper in ("YES", "1", "TRUE"):
			pp_has_modification = True
		elif sales_order_mod_upper in ("NO", "0", "FALSE"):
			pp_has_modification = False
		else:
			# Unrecognized value - treat as old/untracked PP rather than erroring
			pp_is_old = True
			pp_has_modification = False

		# SAFELY get production_plan_updated
		prod_plan_updated = (
			pp_dict.get("production_plan_updated")
			if isinstance(pp_dict, dict)
			else getattr(pp_dict, "production_plan_updated", 0)
		)
		pp_updated_flag = bool(cint(prod_plan_updated or 0))

		# SAFELY get work_order_updated
		wo_updated = (
			pp_dict.get("work_order_updated")
			if isinstance(pp_dict, dict)
			else getattr(pp_dict, "work_order_updated", 0)
		)
		pp_wo_updated_flag = bool(cint(wo_updated or 0))

		# ---- Final PP status decision (matches required table exactly) ----
		if pp_updated_flag:
			# Get Update was clicked (production_plan_updated = 1)
			pp_is_updated = True
		elif pp_is_old:
			# Old PP, no modification tracking -> treat as Updated
			pp_is_updated = True
		elif not pp_has_modification:
			# sales_order_modification resolves to "NO" -> Get Update cleared it
			pp_is_updated = True
		else:
			# sales_order_modification is "YES" and Get Update not clicked yet
			pp_is_updated = False
	else:
		# No PP exists at all
		pp_is_updated = False
		pp_wo_updated_flag = False

	wo_list = [dict(w) for w in maps["wo"].get(so_name, [])]
	wo_exists = len(wo_list) > 0
	
	# Determine WO sync status
	wo_synced = False
	if wo_exists:
		if pp_wo_updated_flag:
			# PP indicates WO has been updated
			wo_synced = True
		else:
			# Check individual WO modification_status
			wo_pending = []
			for w in wo_list:
				# SAFELY get modification_status
				mod_status = w.get("modification_status") if isinstance(w, dict) else getattr(w, "modification_status", None)
				
				if mod_status is not None:
					mod_status_str = cstr(mod_status).strip()
					if mod_status_str.upper() == "YES":
						wo_pending.append(w)
				# If modification_status is None or empty, WO is considered synced
			wo_synced = len(wo_pending) == 0

	# ---------------- PRECISE STATUS CALCULATION LOGIC ----------------------
	# Initialize statuses based on the state machine
	bmr_status = None
	pp_status = None
	work_order_status = None

	if not omr_exists:
		# No OMR exists - regular Sales Order
		bmr_status = "Not Created"
		
		if not pp_exists:
			pp_status = "Not Created"
			work_order_status = "Not Created"
		elif pp_is_updated:
			pp_status = "Updated"
			if not wo_exists:
				work_order_status = "Not Created"
			elif wo_synced:
				work_order_status = "Updated"
			else:
				work_order_status = "Pending"
		else:
			pp_status = "Pending"
			work_order_status = "Not Created" if not wo_exists else "Not Started"
		
	elif omr_change_type == "Quantity Change":
		# Quantity Change: BMR not required
		bmr_status = "Not Created"
		
		if not pp_exists:
			pp_status = "Not Created"
			work_order_status = "Not Created"
		elif pp_is_updated:
			pp_status = "Updated"
			if not wo_exists:
				work_order_status = "Not Created"
			elif wo_synced:
				work_order_status = "Updated"
			else:
				work_order_status = "Pending"
		else:
			pp_status = "Pending"
			work_order_status = "Not Created" if not wo_exists else "Not Started"
			
	elif omr_change_type == "Item Replacement":
		# Item Replacement flow
		
		if not bmr_exists:
			bmr_status = "Not Created"
			pp_status = "Not Required"
			work_order_status = "Not Created" if not wo_exists else "Not Started"
			
		elif bmr_any_draft:
			bmr_status = "Draft"
			pp_status = "Not Required"
			work_order_status = "Not Created" if not wo_exists else "Not Started"
			
		elif bmr_any_submitted:
			bmr_status = "Pending"
			pp_status = "Not Required"
			work_order_status = "Not Created" if not wo_exists else "Not Started"
			
		elif bmr_any_rejected and not bmr_any_approved:
			bmr_status = "Rejected"
			pp_status = "Not Required"
			work_order_status = "Not Created" if not wo_exists else "Not Started"
			
		elif bmr_all_approved:
			bmr_status = "Updated"
			
			if not pp_exists:
				pp_status = "Not Created"
				work_order_status = "Not Created"
			elif not pp_is_updated:
				pp_status = "Pending"
				work_order_status = "Not Created" if not wo_exists else "Not Started"
			else:
				pp_status = "Updated"
				if not wo_exists:
					work_order_status = "Not Created"
				elif wo_synced:
					work_order_status = "Updated"
				else:
					work_order_status = "Pending"
		else:
			bmr_status = "Pending"
			pp_status = "Not Required"
			work_order_status = "Not Created" if not wo_exists else "Not Started"
			
	else:
		# Unknown change type
		if not bmr_exists:
			bmr_status = "Not Created"
		elif bmr_any_draft:
			bmr_status = "Draft"
		elif bmr_any_submitted:
			bmr_status = "Pending"
		elif bmr_all_approved:
			bmr_status = "Updated"
		else:
			bmr_status = "Pending"
		
		pp_status = "Not Created" if not pp_exists else ("Pending" if not pp_is_updated else "Updated")
		work_order_status = "Not Created" if not wo_exists else ("Pending" if not wo_synced else "Updated")

	# ---------------- SEVERITY LOGIC (WEEK-BASED) -------------------
	from datetime import datetime as dt
	from datetime import date as date_type
	
	now = now_datetime()
	
	start_time = None
	
	if omr_dict and omr_dict.get("creation"):
		start_time = omr_dict.get("creation")
	else:
		start_time = get("creation") or get("transaction_date") or get("modified")
	
	if start_time:
		if isinstance(start_time, str):
			for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d"]:
				try:
					start_time = dt.strptime(start_time, fmt)
					break
				except (ValueError, TypeError):
					continue
		elif isinstance(start_time, date_type) and not isinstance(start_time, dt):
			start_time = dt.combine(start_time, dt.min.time())
	
	if start_time and isinstance(start_time, dt):
		time_elapsed = now - start_time
		days_elapsed = time_elapsed.total_seconds() / 86400
		weeks_elapsed = days_elapsed / 7
		hours_elapsed = time_elapsed.total_seconds() / 3600
	else:
		days_elapsed = 0
		weeks_elapsed = 0
		hours_elapsed = 0
	
	# Determine if pending
	is_pending = False
	if work_order_status in ("Pending", "Not Started", "Not Created"):
		is_pending = True
	elif pp_status in ("Pending", "Not Created"):
		is_pending = True
	elif bmr_status in ("Draft", "Pending", "Rejected", "Not Created"):
		is_pending = True
	
	# For no OMR case
	if not omr_exists:
		if pp_status == "Updated" and work_order_status == "Updated":
			is_pending = False
		elif pp_status == "Not Created" or work_order_status == "Not Created":
			is_pending = True
	
	# Week-based severity
	if is_pending:
		if weeks_elapsed >= 4:
			severity = "Critical"
		elif weeks_elapsed >= 2:
			severity = "High"
		else:
			severity = "Low"
	else:
		severity = "Low"

	# ---------------- BADGES -------------------
	if not omr_exists:
		omr_badge = _badge("not_required")
	elif omr_approved:
		omr_badge = _badge("updated")
	else:
		omr_badge = _badge("pending")

	if bmr_status == "Not Created":
		bmr_badge = _badge("not_required")
	elif bmr_status == "Draft":
		bmr_badge = _badge("pending")
	elif bmr_status == "Pending":
		bmr_badge = _badge("pending")
	elif bmr_status == "Rejected":
		bmr_badge = _badge("critical")
	elif bmr_status == "Updated":
		bmr_badge = _badge("updated")
	else:
		bmr_badge = _badge("not_required")

	if pp_status == "Not Created":
		pp_status_badge = _badge("not_required")
	elif pp_status == "Not Required":
		pp_status_badge = _badge("not_required")
	elif pp_status == "Pending":
		pp_status_badge = _badge("pending")
	elif pp_status == "Updated":
		pp_status_badge = _badge("updated")
	else:
		pp_status_badge = _badge("not_required")

	if work_order_status == "Not Created":
		wo_status_badge = _badge("not_required")
	elif work_order_status == "Not Started":
		wo_status_badge = _badge("not_required")
	elif work_order_status == "Pending":
		wo_status_badge = _badge("pending")
	elif work_order_status == "Updated":
		wo_status_badge = _badge("updated")
	else:
		wo_status_badge = _badge("not_required")

	# ---------------- STAGE TIMELINE -------------------
	stages = []
	stages.append({"key": "so", "label": "SO", "state": "completed"})

	if not omr_exists:
		omr_state = "not_required"
	elif omr_approved:
		omr_state = "completed"
	else:
		omr_state = "pending"
	stages.append({"key": "omr", "label": "OMR", "state": omr_state})

	if bmr_status in ("Not Created", "Not Required"):
		bmr_state = "not_required"
	elif bmr_status == "Draft":
		bmr_state = "pending"
	elif bmr_status == "Pending":
		bmr_state = "pending"
	elif bmr_status == "Rejected":
		bmr_state = "blocked"
	elif bmr_status == "Updated":
		bmr_state = "completed"
	else:
		bmr_state = "not_required"
	stages.append({"key": "bmr", "label": "BMR", "state": bmr_state})

	if pp_status in ("Not Created", "Not Required"):
		pp_state = "not_required"
	elif pp_status == "Pending":
		pp_state = "blocked"
	elif pp_status == "Updated":
		pp_state = "completed"
	else:
		pp_state = "not_required"
	stages.append({"key": "pp", "label": "PP", "state": pp_state})

	if work_order_status in ("Not Created", "Not Started"):
		wo_state = "not_required"
	elif work_order_status == "Pending":
		wo_state = "blocked"
	elif work_order_status == "Updated":
		wo_state = "completed"
	else:
		wo_state = "not_required"
	stages.append({"key": "wo", "label": "WO", "state": wo_state})

	completed_state = "completed" if severity == "Low" and not is_pending else "pending"
	stages.append({"key": "completed", "label": "Completed", "state": completed_state})

	# ---------------- PENDING-AT / REMARKS -------------------
	pending_at = "—"
	current_stage = "Completed"
	remarks = ""
	
	if bmr_status == "Draft":
		pending_at = _("BMR Draft Submission")
		current_stage = "BMR"
	elif bmr_status == "Pending":
		pending_at = _("BMR Approval")
		current_stage = "BMR"
	elif bmr_status == "Rejected":
		pending_at = _("BMR Rejection Resolution")
		current_stage = "BMR"
	elif bmr_status == "Not Created" and omr_change_type == "Item Replacement":
		# pending_at = _("BMR Creation")
		current_stage = "BMR"
	elif pp_status == "Not Created":
		pending_at = _("Production Plan Creation")
		current_stage = "PP"
	elif pp_status == "Pending":
		pending_at = _("Production Plan Update (Get Update)")
		current_stage = "PP"
	elif work_order_status == "Not Created":
		pending_at = _("Work Order Creation")
		current_stage = "WO"
	elif work_order_status == "Pending":
		pending_at = _("Work Order Update")
		current_stage = "WO"

	if is_pending:
		elapsed_str = _format_elapsed_time_weeks(weeks_elapsed)
		remarks = _("Pending for {0} at {1}").format(elapsed_str, pending_at)
	else:
		remarks = _("Completed")

	return {
		"sales_order": so_name,
		"customer": get("customer"),
		"customer_name": get("customer_name"),
		"branch": get("branch"),
		"company": get("company"),
		"transaction_date": get("transaction_date"),
		"delivery_date": get("delivery_date"),
		"so_status": get("status"),
		"grand_total": flt(get("grand_total")),
		"modified": get("modified"),
		"modified_by": get("modified_by"),

		"omr": omr_dict,
		"omr_exists": omr_exists,
		"omr_approved": omr_approved,
		"omr_badge": omr_badge,
		"omr_change_type": omr_change_type,

		# Three calculated statuses
		"bmr_status": bmr_status,
		"pp_status": pp_status,
		"work_order_status": work_order_status,

		"bmr_list": bmr_list,
		"bmr_pending": bmr_pending_list,
		"bmr_draft": bmr_draft_list,
		"bmr_submitted": bmr_submitted_list,
		"bmr_approved": bmr_approved_list,
		"bmr_rejected": bmr_rejected_list,
		"bmr_exists": bmr_exists,
		"bmr_all_approved": bmr_all_approved,
		"bmr_any_approved": bmr_any_approved,
		"bmr_badge": bmr_badge,

		"pp": pp_dict,
		"pp_exists": pp_exists,
		"pp_updated_flag": pp_updated_flag,
		"pp_is_updated": pp_is_updated,
		"pp_is_old": pp_is_old,
		"pp_has_modification": pp_has_modification,
		"pp_update_required": pp_status in ("Pending", "Not Created"),
		"pp_status_badge": pp_status_badge,

		"wo_list": wo_list,
		"wo_exists": wo_exists,
		"wo_synced": wo_synced,
		"wo_update_required": work_order_status in ("Pending", "Not Created"),
		"wo_status_badge": wo_status_badge,

		"severity": severity,
		"severity_color": SEVERITY_COLOR[severity],
		"is_pending": is_pending,
		"stages": stages,
		"pending_at": pending_at,
		"current_stage": current_stage,
		"remarks": remarks,
		"hours_elapsed": round(hours_elapsed, 1),
		"days_elapsed": round(days_elapsed, 1),
		"weeks_elapsed": round(weeks_elapsed, 1),
	}

def _format_elapsed_time_weeks(weeks):
	"""Format elapsed time in weeks for display."""
	if weeks < 0.14:  # Less than 1 day
		return _("less than 1 day")
	elif weeks < 1:  # Less than 1 week
		days = int(weeks * 7)
		if days == 1:
			return _("1 day")
		else:
			return _("{0} days").format(days)
	elif weeks < 2:  # 1-2 weeks
		return _("1 week")
	elif weeks < 3:  # 2-3 weeks
		return _("2 weeks")
	elif weeks < 4:  # 3-4 weeks
		return _("3 weeks")
	else:  # 4+ weeks
		return _("{0} weeks").format(int(weeks))
def _format_elapsed_time(hours):
	"""Format elapsed time in a human-readable format."""
	if hours < 1:
		return _("less than 1 hour")
	elif hours < 24:
		return _("{0} hours").format(int(hours))
	else:
		days = int(hours / 24)
		remaining_hours = int(hours % 24)
		if remaining_hours > 0:
			return _("{0} days {1} hours").format(days, remaining_hours)
		else:
			return _("{0} days").format(days)


def _get_computed_rows(filters, limit=2000):
	"""Get all rows with computed status, then apply post-filters.
	IMPORTANT: Only include rows where OMR exists."""
	sos = _get_filtered_sales_orders(filters)
	if not sos:
		return []

	so_names = [s.name for s in sos]
	filtered_pp = filters.get("production_plan")
	maps = _fetch_maps(so_names, filtered_pp=filtered_pp)
	rows = [_compute_row(s, maps) for s in sos]
	
	# FILTER: Only include rows with OMR
	rows = [r for r in rows if r["omr_exists"]]

	if cint(filters.get("pending_only")):
		rows = [r for r in rows if r["is_pending"]]

	if cint(filters.get("critical_only")):
		rows = [r for r in rows if r["severity"] == "Critical"]

	status_filter = filters.get("status")
	if status_filter and status_filter != "Any":
		if status_filter == "Fully Synced":
			rows = [r for r in rows if r["severity"] == "Low"]
		elif status_filter == "Pending Update":
			rows = [r for r in rows if r["is_pending"]]
		elif status_filter == "Waiting on Approval":
			rows = [r for r in rows if r["severity"] == "Waiting"]

	priority_filter = filters.get("priority")
	if priority_filter and priority_filter != "Any":
		rows = [r for r in rows if r["severity"] == priority_filter]

	return rows[:limit]