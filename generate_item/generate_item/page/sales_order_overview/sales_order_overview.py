import frappe
from frappe import _
from frappe.utils import (
	getdate,
	nowdate,
	add_days,
	add_months,
	get_first_day,
	get_last_day,
	flt,
	cint,
)
try:
	# get_fiscal_year belongs to ERPNext (the Fiscal Year doctype is an ERPNext
	# doctype), not to frappe core — so it must be imported from there.
	from erpnext.accounts.utils import get_fiscal_year as _get_fiscal_year
except ImportError:
	_get_fiscal_year = None


# ---------------------------------------------------------------------------
# CONFIG — change these if your doctype/field names differ
# ---------------------------------------------------------------------------
SO_DOCTYPE = "Sales Order"
SO_ITEM_DOCTYPE = "Sales Order Item"
SALES_TEAM_DOCTYPE = "Sales Team"          # child table on Sales Order
OMR_DOCTYPE = "Order Modification Request"  # change-request doctype

MANAGER_ROLES = ("Sales Manager", "System Manager")

VALID_PERIODS = ("monthly", "quarterly", "half_yearly", "yearly", "all", "custom")


# ---------------------------------------------------------------------------
# Period resolution (Apr–Mar fiscal year based Quarterly / Half-Yearly / Yearly)
# ---------------------------------------------------------------------------
def _fiscal_year_bounds(on_date=None):
	"""Return (fy_name, start_date, end_date) for the fiscal year containing on_date."""
	on_date = getdate(on_date or nowdate())
	if _get_fiscal_year:
		try:
			fy_name, fy_start, fy_end = _get_fiscal_year(on_date, as_dict=False)
			return fy_name, getdate(fy_start), getdate(fy_end)
		except Exception:
			pass

	# Fallback (ERPNext not installed, or no Fiscal Year record found):
	# assume a standard Apr 1 - Mar 31 Indian fiscal year.
	if on_date.month >= 4:
		start = getdate(f"{on_date.year}-04-01")
		end = getdate(f"{on_date.year + 1}-03-31")
	else:
		start = getdate(f"{on_date.year - 1}-04-01")
		end = getdate(f"{on_date.year}-03-31")
	return f"{start.year}-{end.year}", start, end


def _quarter_bounds_within_fy(on_date, fy_start):
	"""Apr-Jun / Jul-Sep / Oct-Dec / Jan-Mar quarter containing on_date."""
	months_since_fy_start = (on_date.year - fy_start.year) * 12 + (on_date.month - fy_start.month)
	q_index = months_since_fy_start // 3  # 0..3
	q_start = add_months(fy_start, q_index * 3)
	q_end = get_last_day(add_months(q_start, 2))
	return getdate(q_start), getdate(q_end)


def _half_bounds_within_fy(on_date, fy_start):
	"""Apr-Sep / Oct-Mar half-year containing on_date."""
	months_since_fy_start = (on_date.year - fy_start.year) * 12 + (on_date.month - fy_start.month)
	h_index = months_since_fy_start // 6  # 0 or 1
	h_start = add_months(fy_start, h_index * 6)
	h_end = get_last_day(add_months(h_start, 5))
	return getdate(h_start), getdate(h_end)


def resolve_period(period, from_date=None, to_date=None, reference_date=None):
	"""
	Returns a dict with:
	  start, end               -> resolved date range for the requested period
	  prev_start, prev_end     -> equivalent prior period (for trend badge), or None
	"""
	today = getdate(reference_date or nowdate())
	period = (period or "monthly").lower()
	if period not in VALID_PERIODS:
		period = "monthly"

	if period == "custom":
		if not from_date or not to_date:
			frappe.throw(_("Please provide both From Date and To Date for a custom range."))
		start, end = getdate(from_date), getdate(to_date)
		if start > end:
			frappe.throw(_("From Date cannot be after To Date."))
		return {"start": start, "end": end, "prev_start": None, "prev_end": None}

	if period == "all":
		row = frappe.db.sql(
			"select min(transaction_date) from `tab{so}` where docstatus = 1".format(so=SO_DOCTYPE)
		)
		earliest = row[0][0] if row and row[0][0] else None
		earliest = earliest or add_years_safe(today)
		return {"start": getdate(earliest), "end": today, "prev_start": None, "prev_end": None}

	if period == "monthly":
		start, end = getdate(get_first_day(today)), getdate(get_last_day(today))
		prev_ref = add_months(today, -1)
		prev_start, prev_end = getdate(get_first_day(prev_ref)), getdate(get_last_day(prev_ref))
		return {"start": start, "end": end, "prev_start": prev_start, "prev_end": prev_end}

	# quarterly / half_yearly / yearly are fiscal-year based
	fy_name, fy_start, fy_end = _fiscal_year_bounds(today)

	if period == "yearly":
		prev_fy_name, prev_fy_start, prev_fy_end = _fiscal_year_bounds(add_months(fy_start, -1))
		return {"start": fy_start, "end": fy_end, "prev_start": prev_fy_start, "prev_end": prev_fy_end}

	if period == "quarterly":
		start, end = _quarter_bounds_within_fy(today, fy_start)
		prev_ref = add_days(start, -1)  # last day of previous quarter
		prev_fy_name, prev_fy_start, prev_fy_end = _fiscal_year_bounds(prev_ref)
		prev_start, prev_end = _quarter_bounds_within_fy(prev_ref, prev_fy_start)
		return {"start": start, "end": end, "prev_start": prev_start, "prev_end": prev_end}

	if period == "half_yearly":
		start, end = _half_bounds_within_fy(today, fy_start)
		prev_ref = add_days(start, -1)
		prev_fy_name, prev_fy_start, prev_fy_end = _fiscal_year_bounds(prev_ref)
		prev_start, prev_end = _half_bounds_within_fy(prev_ref, prev_fy_start)
		return {"start": start, "end": end, "prev_start": prev_start, "prev_end": prev_end}


def add_years_safe(d, years=-5):
	try:
		return d.replace(year=d.year + years)
	except Exception:
		return d


# ---------------------------------------------------------------------------
# Permission helpers
# ---------------------------------------------------------------------------
def _current_user_is_manager():
	roles = frappe.get_roles(frappe.session.user)
	return any(r in roles for r in MANAGER_ROLES)



def _own_sales_person():
	"""Best-effort match of the logged-in user to a Sales Person record."""
	if frappe.session.user == "Administrator":
		return None

	# Only query user_id if that field actually exists on this site's
	# Sales Person doctype — it isn't part of standard ERPNext and may
	if frappe.get_meta("Sales Person").has_field("user_id"):
		name = frappe.db.get_value("Sales Person", {"user_id": frappe.session.user}, "name")
		if name:
			return name

	# fallback: match by full name text, in case Sales Person isn't linked via user_id
	full_name = frappe.utils.get_fullname(frappe.session.user)
	return frappe.db.get_value("Sales Person", {"sales_person_name": full_name}, "name")


@frappe.whitelist()
def get_filter_options():
	"""Populates the user/salesperson dropdown and tells the client whether
	the current user is restricted to their own data."""
	is_manager = _current_user_is_manager()
	own = _own_sales_person()

	if is_manager:
		persons = frappe.get_all(
			"Sales Person",
			filters={"enabled": 1},
			fields=["name", "sales_person_name"],
			order_by="sales_person_name asc",
		)
		options = [{"value": p.name, "label": p.sales_person_name or p.name} for p in persons]
	else:
		if own:
			label = frappe.db.get_value("Sales Person", own, "sales_person_name") or own
			options = [{"value": own, "label": label}]
		else:
			options = []

	return {
		"is_manager": is_manager,
		"own_sales_person": own,
		"options": options,
	}


def _enforce_user_permission(user):
	"""Server-side guard: non-managers cannot request anyone else's data."""
	if _current_user_is_manager():
		return user
	own = _own_sales_person()
	if not own:
		frappe.throw(_("No Sales Person record is linked to your user account."), frappe.PermissionError)
	if user and user != "all" and user != own:
		frappe.throw(_("You are not permitted to view this Sales Person's data."), frappe.PermissionError)
	return own


# ---------------------------------------------------------------------------
# Core aggregation
# ---------------------------------------------------------------------------
def _get_order_names_and_values(user, start, end):
	"""Returns (order_names, rows) for submitted Sales Orders in range,
	optionally scoped to a single Sales Person via the sales_team child table."""

	filters = [
		[SO_DOCTYPE, "docstatus", "=", 1],
		[SO_DOCTYPE, "transaction_date", "between", [start, end]],
	]
	if user and user != "all":
		filters.append([SALES_TEAM_DOCTYPE, "sales_person", "=", user])

	rows = frappe.get_list(
		SO_DOCTYPE,
		filters=filters,
		fields=[
			"name",
			"status",
			"base_grand_total",
			"grand_total",
			"delivery_date",
			"per_delivered",
			"per_billed",
		],
		distinct=True,
		limit_page_length=0,
	)
	order_names = [r.name for r in rows]
	return order_names, rows


def _sum_allocated_value(user, order_names):
	"""When scoped to one salesperson, use their allocated_amount from the
	Sales Team child table rather than the full order value."""
	if not order_names:
		return 0

	if not user or user == "all":
		row = frappe.db.sql(
			"""
			select sum(base_grand_total)
			from `tab{so}`
			where name in %(orders)s
			""".format(so=SO_DOCTYPE),
			{"orders": tuple(order_names)},
		)
		return flt(row[0][0]) if row and row[0][0] else 0

	val = frappe.db.sql(
		"""
		select sum(allocated_amount)
		from `tab{st}`
		where parenttype = %(so)s
		  and parent in %(orders)s
		  and sales_person = %(user)s
		""".format(st=SALES_TEAM_DOCTYPE),
		{"so": SO_DOCTYPE, "orders": tuple(order_names), "user": user},
	)
	return flt(val[0][0]) if val and val[0][0] else 0


def _count_lines(order_names):
	if not order_names:
		return 0
	return cint(
		frappe.db.count(SO_ITEM_DOCTYPE, filters={"parent": ["in", order_names]})
	)


def _count_change_requests(user, order_names, start, end):
	"""Change requests logged within the period. If order_names is empty
	(no orders matched), there can't be any linked change requests."""
	if not order_names:
		return 0

	filters = {
		"sales_order": ["in", order_names],
		"docstatus": 1,
		"creation": ["between", [start, end]],
	}
	try:
		return cint(frappe.db.count(OMR_DOCTYPE, filters=filters))
	except Exception:
		# OMR doctype not installed in this site / different name — degrade gracefully
		return 0


def _compute_bucket(user, start, end):
	order_names, rows = _get_order_names_and_values(user, start, end)

	total_count = len(order_names)
	total_value = _sum_allocated_value(user, order_names)
	total_lines = _count_lines(order_names)

	today = getdate(nowdate())
	open_count = 0
	overdue_count = 0
	for r in rows:
		fully_done = flt(r.per_delivered) >= 100 and flt(r.per_billed) >= 100
		is_closed_status = r.status in ("Closed", "Completed", "Cancelled")
		if not fully_done and not is_closed_status:
			open_count += 1
			if r.delivery_date and getdate(r.delivery_date) < today:
				overdue_count += 1

	closed_count = max(total_count - open_count, 0)
	change_count = _count_change_requests(user, order_names, start, end)

	return {
		"count": total_count,
		"lines": total_lines,
		"value": total_value,
		"open": open_count,
		"overdue": overdue_count,
		"closed": closed_count,
		"change": change_count,
		"rate": round((change_count / total_count * 100), 1) if total_count else 0,
	}


@frappe.whitelist()
def get_dashboard_data(user="all", period="monthly", from_date=None, to_date=None):
	user = _enforce_user_permission(user)
	period = (period or "monthly").lower()

	bounds = resolve_period(period, from_date, to_date)
	current = _compute_bucket(user, bounds["start"], bounds["end"])

	previous = None
	if bounds["prev_start"] and bounds["prev_end"]:
		previous = _compute_bucket(user, bounds["prev_start"], bounds["prev_end"])

	return {
		"period": period,
		"user": user,
		"start": str(bounds["start"]),
		"end": str(bounds["end"]),
		"current": current,
		"previous": previous,
	}


PREVIEW_LIMIT = 10
MAX_PAGE_LENGTH = 50


@frappe.whitelist()
def get_drilldown_data(kind, user="all", period="monthly", from_date=None, to_date=None, page=0, page_length=PREVIEW_LIMIT):
	"""Returns a page of the actual records behind a card, plus the
	filters needed to open the full List View for that same slice of data."""
	user = _enforce_user_permission(user)
	period = (period or "monthly").lower()
	bounds = resolve_period(period, from_date, to_date)
	start, end = bounds["start"], bounds["end"]
	today = getdate(nowdate())

	page = cint(page) or 0
	page_length = min(cint(page_length) or PREVIEW_LIMIT, MAX_PAGE_LENGTH)
	offset = page * page_length

	order_names, rows = _get_order_names_and_values(user, start, end)

	base_so_filters = {"transaction_date": ["between", [str(start), str(end)]], "docstatus": 1}
	if user and user != "all":
		base_so_filters["Sales Team.sales_person"] = user

	if kind in ("orders_all", "orders_open", "orders_overdue", "orders_closed"):
		matched = []
		for r in rows:
			fully_done = flt(r.per_delivered) >= 100 and flt(r.per_billed) >= 100
			is_closed_status = r.status in ("Closed", "Completed", "Cancelled")
			is_open = (not fully_done) and (not is_closed_status)
			is_overdue = is_open and r.delivery_date and getdate(r.delivery_date) < today
			is_closed = not is_open

			if kind == "orders_open" and not is_open:
				continue
			if kind == "orders_overdue" and not is_overdue:
				continue
			if kind == "orders_closed" and not is_closed:
				continue
			matched.append(r)

		total = len(matched)
		page_rows = matched[offset : offset + page_length]

		customers = {}
		names = [p.name for p in page_rows]
		if names:
			for d in frappe.get_all(
				SO_DOCTYPE, filters={"name": ["in", names]}, fields=["name", "customer_name"]
			):
				customers[d.name] = d.customer_name

		result_rows = [
			{
				"name": r.name,
				"customer": customers.get(r.name, ""),
				"status": r.status,
				"amount": r.base_grand_total,
				"delivery_date": str(r.delivery_date) if r.delivery_date else "",
			}
			for r in page_rows
		]

		list_filters = dict(base_so_filters)
		if kind == "orders_open":
			list_filters["per_delivered"] = ["<", 100]
		elif kind == "orders_overdue":
			list_filters["per_delivered"] = ["<", 100]
			list_filters["delivery_date"] = ["<", str(today)]
		elif kind == "orders_closed":
			list_filters["per_delivered"] = 100
			list_filters["per_billed"] = 100

		return {
			"list_doctype": SO_DOCTYPE,
			"columns": [
				{"label": _("Sales Order"), "key": "name"},
				{"label": _("Customer"), "key": "customer"},
				{"label": _("Status"), "key": "status"},
				{"label": _("Amount"), "key": "amount", "type": "currency"},
				{"label": _("Delivery Date"), "key": "delivery_date"},
			],
			"rows": result_rows,
			"total": total,
			"page": page,
			"page_length": page_length,
			"list_filters": list_filters,
		}

	if kind == "lines":
		if not order_names:
			return {
				"list_doctype": SO_DOCTYPE,
				"columns": [],
				"rows": [],
				"total": 0,
				"page": page,
				"page_length": page_length,
				"list_filters": base_so_filters,
			}

		items = frappe.get_all(
			SO_ITEM_DOCTYPE,
			filters={"parent": ["in", order_names]},
			fields=["parent", "item_code", "item_name", "qty", "rate", "amount"],
			limit_start=offset,
			limit_page_length=page_length,
			order_by="creation desc",
		)
		total_lines = cint(frappe.db.count(SO_ITEM_DOCTYPE, filters={"parent": ["in", order_names]}))

		result_rows = [
			{
				"name": it.parent,
				"item": it.item_name or it.item_code,
				"qty": it.qty,
				"rate": it.rate,
				"amount": it.amount,
			}
			for it in items
		]

		return {
			"list_doctype": SO_DOCTYPE,
			"columns": [
				{"label": _("Sales Order"), "key": "name"},
				{"label": _("Item"), "key": "item"},
				{"label": _("Qty"), "key": "qty"},
				{"label": _("Rate"), "key": "rate", "type": "currency"},
				{"label": _("Amount"), "key": "amount", "type": "currency"},
			],
			"rows": result_rows,
			"total": total_lines,
			"page": page,
			"page_length": page_length,
			"list_filters": base_so_filters,
			"note": _("The list view opens the parent Sales Orders, not individual line items."),
		}

	if kind == "changes":
		list_filters = {"creation": ["between", [str(start), str(end)]], "docstatus": 1}
		if not order_names:
			return {
				"list_doctype": OMR_DOCTYPE,
				"columns": [],
				"rows": [],
				"total": 0,
				"page": page,
				"page_length": page_length,
				"list_filters": list_filters,
			}

		list_filters["sales_order"] = ["in", order_names]

		try:
			omrs = frappe.get_all(
				OMR_DOCTYPE,
				filters=list_filters,
				fields=["name", "sales_order", "customer_name", "modification_type", "workflow_state", "creation"],
				limit_start=offset,
				limit_page_length=page_length,
				order_by="creation desc",
			)
			total = cint(frappe.db.count(OMR_DOCTYPE, filters=list_filters))
		except Exception:
			omrs, total = [], 0

		result_rows = [
			{
				"name": o.name,
				"sales_order": o.sales_order,
				"customer": o.customer_name,
				"type": o.modification_type,
				"status": o.workflow_state,
				"date": str(o.creation)[:10] if o.creation else "",
			}
			for o in omrs
		]

		return {
			"list_doctype": OMR_DOCTYPE,
			"columns": [
				{"label": _("Change Request"), "key": "name"},
				{"label": _("Sales Order"), "key": "sales_order"},
				{"label": _("Customer"), "key": "customer"},
				{"label": _("Type"), "key": "type"},
				{"label": _("Status"), "key": "status"},
				{"label": _("Date"), "key": "date"},
			],
			"rows": result_rows,
			"total": total,
			"page": page,
			"page_length": page_length,
			"list_filters": list_filters,
		}

	frappe.throw(_("Unknown drilldown kind: {0}").format(kind))