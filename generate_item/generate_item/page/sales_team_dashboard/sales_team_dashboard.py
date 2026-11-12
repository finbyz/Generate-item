# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import date_diff, getdate, nowdate

# Documents shown in "My work to do".
# date: document date field; party: "For" column; ref: extra reference shown under "For".
WORK_DOCTYPES = [
	{"doctype": "Sales Order", "short": "SO", "date": "transaction_date", "party": "customer_name", "ref": None},
	{"doctype": "Order Modification Request", "short": "OMR", "date": "date", "party": "customer_name", "ref": "sales_order"},
	{"doctype": "Bom Modification Request", "short": "BMR", "date": "date", "party": "fg_item_name", "ref": "bom"},
	{"doctype": "Material Request", "short": "MR", "date": "transaction_date", "party": "customer", "ref": "material_request_type"},
	{"doctype": "Delivery Note", "short": "DN", "date": "posting_date", "party": "customer_name", "ref": None},
]

OVERDUE_DAYS = 3


@frappe.whitelist()
def get_my_work_to_do():
	"""Draft documents (docstatus = 0) created by the logged-in user."""
	user = frappe.session.user
	today = getdate(nowdate())
	rows = []

	for cfg in WORK_DOCTYPES:
		doctype = cfg["doctype"]
		if not frappe.db.exists("DocType", doctype) or not frappe.has_permission(doctype, "read"):
			continue

		meta = frappe.get_meta(doctype)
		fields = ["name", "creation"]
		for f in ("status", "workflow_state"):
			if meta.has_field(f):
				fields.append(f)
		for key in ("date", "party", "ref"):
			if cfg[key] and meta.has_field(cfg[key]):
				fields.append(f"{cfg[key]} as {key}")
		if meta.has_field("branch"):
			fields.append("branch")

		docs = frappe.get_all(
			doctype,
			filters={"docstatus": 0, "owner": user},
			fields=fields,
			order_by="creation asc",
		)

		for d in docs:
			age = date_diff(today, getdate(d.creation))
			rows.append(
				{
					"doctype": doctype,
					"short": cfg["short"],
					"name": d.name,
					"status": d.get("workflow_state") or d.get("status") or "Draft",
					"date": d.get("date") or getdate(d.creation),
					"party": d.get("party"),
					"ref": d.get("ref"),
					"branch": d.get("branch"),
					"age": age,
					"overdue": age >= OVERDUE_DAYS,
				}
			)

	rows.sort(key=lambda r: r["age"], reverse=True)

	return {
		"rows": rows,
		"doctypes": [{"doctype": c["doctype"], "short": c["short"]} for c in WORK_DOCTYPES],
		"overdue_days": OVERDUE_DAYS,
	}


# ---------------- 2. My performance (Sales Order only) ----------------

def _period_range(period, today, offset=0):
	"""Return (from_date, to_date) for period shifted back by `offset` periods."""
	from frappe.utils import add_days

	if period == "day":
		d = add_days(today, -offset)
		return d, d
	# week (Mon-Sun)
	start = add_days(today, -today.weekday() - 7 * offset)
	return start, add_days(start, 6)


# Sales Orders (not cancelled) created by the user in the date range
SO_CONDITION = """
	so.docstatus < 2
	and so.owner = %(user)s
	and so.transaction_date between %(from)s and %(to)s
"""


def _so_stats(user, from_date, to_date):
	args = {"user": user, "from": from_date, "to": to_date}
	row = frappe.db.sql(
		f"""
		select
			count(*) as created,
			sum(case when so.docstatus = 1 then 1 else 0 end) as completed,
			coalesce(sum(so.base_net_total), 0) as value
		from `tabSales Order` so
		where {SO_CONDITION}
		""",
		args,
		as_dict=True,
	)[0]
	lines = frappe.db.sql(
		f"""
		select count(soi.name)
		from `tabSales Order Item` soi
		join `tabSales Order` so on so.name = soi.parent
		where soi.parenttype = 'Sales Order' and {SO_CONDITION}
		""",
		args,
	)[0][0]
	return {
		"created": row.created or 0,
		"completed": int(row.completed or 0),
		"lines": lines or 0,
		"value": float(row.value or 0),
	}


@frappe.whitelist()
def get_my_performance(period="week"):
	"""Sales Orders created by the logged-in user for the period vs the previous period."""
	from frappe.utils import add_days

	if period not in ("day", "week"):
		period = "week"

	today = getdate(nowdate())
	cur_from, cur_to = _period_range(period, today)
	prev_from, prev_to = _period_range(period, today, offset=1)

	user = frappe.session.user

	daily = []
	if period != "day":
		counts = dict(
			frappe.db.sql(
				f"""
				select so.transaction_date, count(*)
				from `tabSales Order` so
				where {SO_CONDITION}
				group by so.transaction_date
				""",
				{"user": user, "from": cur_from, "to": cur_to},
			)
		)
		d = cur_from
		while d <= cur_to:
			daily.append({"date": d, "count": counts.get(d, 0), "future": d > today})
			d = add_days(d, 1)

	return {
		"period": period,
		"from_date": cur_from,
		"to_date": cur_to,
		"current": _so_stats(user, cur_from, cur_to),
		"previous": _so_stats(user, prev_from, prev_to),
		"daily": daily,
		"currency": frappe.defaults.get_global_default("currency") or "INR",
	}


# ---------------- 3. Ranking ----------------

# sign: +1 -> more is better, -1 -> fewer is better
RANK_DOCTYPES = {
	"SO": {"doctype": "Sales Order", "child": "Sales Order Item", "date": "d.transaction_date", "value": "d.base_net_total", "sign": 1},
	"MR": {"doctype": "Material Request", "child": "Material Request Item", "date": "d.transaction_date", "value": None, "sign": 1},
	"DN": {"doctype": "Delivery Note", "child": "Delivery Note Item", "date": "d.posting_date", "value": "d.base_net_total", "sign": 1},
	"OMR": {"doctype": "Order Modification Request", "child": "Order Modification Request Detail", "date": "date(d.creation)", "value": None, "sign": -1},
	"BMR": {"doctype": "Bom Modification Request", "child": "Order Modification Request Detail", "date": "date(d.creation)", "value": None, "sign": -1},
}
RANK_ROLE = "Sales User"


def _sales_users():
	return frappe.db.sql(
		"""
		select u.name, u.full_name
		from `tabUser` u
		where u.enabled = 1 and u.name != 'Guest'
			and (
				u.name = 'Administrator'
				or (
					u.user_type = 'System User'
					and exists (
						select 1 from `tabHas Role` hr
						where hr.parent = u.name and hr.parenttype = 'User' and hr.role = %s
					)
				)
			)
		""",
		RANK_ROLE,
		as_dict=True,
	)


def _doc_stats(key, users, from_date, to_date):
	"""{user: {docs, lines, value}} for one doctype."""
	cfg = RANK_DOCTYPES[key]
	args = {"users": tuple(users), "from": from_date, "to": to_date, "pt": cfg["doctype"]}
	cond = f"d.docstatus < 2 and d.owner in %(users)s and {cfg['date']} between %(from)s and %(to)s"
	value = f"coalesce(sum({cfg['value']}), 0)" if cfg["value"] else "0"

	out = {}
	for r in frappe.db.sql(
		f"select d.owner, count(*) as docs, {value} as value from `tab{cfg['doctype']}` d where {cond} group by d.owner",
		args,
		as_dict=True,
	):
		out[r.owner] = {"docs": r.docs, "lines": 0, "value": float(r.value or 0)}

	for owner, lines in frappe.db.sql(
		f"""
		select d.owner, count(c.name)
		from `tab{cfg['doctype']}` d
		join `tab{cfg['child']}` c on c.parent = d.name and c.parenttype = %(pt)s
		where {cond}
		group by d.owner
		""",
		args,
	):
		out.setdefault(owner, {"docs": 0, "lines": 0, "value": 0.0})["lines"] = lines
	return out


@frappe.whitelist()
def get_ranking(week="cur", doc="ALL", metric="docs"):
	from frappe.utils import add_days

	if week not in ("cur", "prev"):
		week = "cur"
	if doc != "ALL" and doc not in RANK_DOCTYPES:
		doc = "ALL"
	if metric not in ("docs", "lines", "value"):
		metric = "docs"

	today = getdate(nowdate())
	from_date, to_date = _period_range("week", today, offset=1 if week == "prev" else 0)

	base = {
		"week": week, "doc": doc, "metric": metric,
		"from_date": from_date, "to_date": to_date,
		"me": frappe.session.user, "role": RANK_ROLE,
		"currency": frappe.defaults.get_global_default("currency") or "INR",
	}

	# Value exists only for SO and DN; for "All", value = Sales Order net value
	if metric == "value" and doc != "ALL" and not RANK_DOCTYPES[doc]["value"]:
		return {**base, "not_applicable": True}

	users = _sales_users()
	if not users:
		return {**base, "rows": []}
	user_ids = [u.name for u in users]
	keys = list(RANK_DOCTYPES) if doc == "ALL" else [doc]
	stats = {k: _doc_stats(k, user_ids, from_date, to_date) for k in set(keys) | {"SO"}}

	def val(k, u):
		return stats[k].get(u, {}).get(metric, 0)

	rows = []
	for u in users:
		row = {"user": u.name, "full_name": u.full_name or u.name}
		if doc == "ALL":
			row["breakdown"] = {k: val(k, u.name) for k in keys}
			if metric == "value":
				row["score"] = val("SO", u.name)
			else:
				row["score"] = sum(RANK_DOCTYPES[k]["sign"] * row["breakdown"][k] for k in keys)
		else:
			# fewer-is-better docs: rank only users who booked at least one Sales Order that week
			if RANK_DOCTYPES[doc]["sign"] < 0 and not stats["SO"].get(u.name, {}).get("docs"):
				continue
			row["score"] = val(doc, u.name)
		rows.append(row)

	higher_better = doc == "ALL" or RANK_DOCTYPES[doc]["sign"] > 0
	rows.sort(key=lambda r: ((-r["score"] if higher_better else r["score"]), r["full_name"].lower()))
	for i, r in enumerate(rows):
		r["rank"] = rows[i - 1]["rank"] if i and r["score"] == rows[i - 1]["score"] else i + 1

	return {
		**base,
		"rows": rows,
		"higher_better": higher_better,
		"keys": keys,
		"signs": {k: RANK_DOCTYPES[k]["sign"] for k in keys},
	}
