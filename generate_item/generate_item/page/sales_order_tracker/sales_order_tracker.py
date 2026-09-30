# Copyright (c) 2026
# For license information, please see license.txt
#
# ---------------------------------------------------------------------------
# SALES ORDER TRACKER — backend
#
# Core concept: Driven completely by Sales Order.
# Each record represents a Sales Order and its item line breakdown.
# Linked documents (MR, PO, SCO, SCR, PR, PI, DN, SI, Payment Entry, Journal Entry)
# are resolved via direct Sales Order links (e.g. against_sales_order / sales_order)
# and fallback to linked Project (AO Number) when present.
# ---------------------------------------------------------------------------

import frappe
from frappe import _
from frappe.utils import flt, today, date_diff, getdate


DOC_ORDER = [
	"quote", "so", "bom", "pp", "mr", "po", "sco", "scr", "pr", "sr",
	"pi", "dn", "si", "pe_in", "pe_out", "je",
]

# Columns shown on the Tab 1 list grid, in this order:
# BOM -> Production Plan -> Material Request -> Purchase Order -> Purchase
# Receipt -> Purchase Invoice -> Delivery Note -> Sales Invoice.
LIST_DOC_KEYS = ["bom", "pp", "mr", "po", "pr", "pi", "dn", "si"]

DOC_CONFIG = {
	"quote": {
		"doctype": "Quotation", "label": "Quotation", "short": "QTN",
		"status_field": "status", "amount_field": "grand_total",
	},
	"so": {
		"doctype": "Sales Order", "label": "Sales Order", "short": "SO",
		"status_field": "status", "amount_field": "grand_total",
	},
	"bom": {
		"doctype": "BOM", "label": "BOM", "short": "BOM",
		"status_field": "workflow_state", "amount_field": "total_cost",
	},
	"pp": {
		"doctype": "Production Plan", "label": "Production Plan", "short": "PP",
		"status_field": "status", "amount_field": None,
	},
	"mr": {
		"doctype": "Material Request", "label": "Material Request", "short": "MR",
		"status_field": "status", "amount_field": None,
		"item_doctype": "Material Request Item", "item_so_field": "sales_order",
	},
	"po": {
		"doctype": "Purchase Order", "label": "Purchase Order", "short": "PO",
		"status_field": "status", "amount_field": "grand_total",
		"item_doctype": "Purchase Order Item", "item_so_field": "sales_order",
	},
	"sco": {
		"doctype": "Subcontracting Order", "label": "Subcontracting Order", "short": "SCO",
		"status_field": "status", "amount_field": "grand_total",
		"item_doctype": "Subcontracting Order Item", "item_so_field": "against_sales_order",
	},
	"scr": {
		"doctype": "Subcontracting Receipt", "label": "Subcontracting Receipt", "short": "SCR",
		"status_field": "status", "amount_field": "grand_total",
		"item_doctype": "Subcontracting Receipt Item", "item_so_field": "against_sales_order",
	},
	"pr": {
		"doctype": "Purchase Receipt", "label": "Purchase Receipt", "short": "PR",
		"status_field": "status", "amount_field": "grand_total",
		"item_doctype": "Purchase Receipt Item", "item_so_field": "sales_order",
	},
	"sr": {
		"doctype": "Stock Entry", "label": "Stock Requisition", "short": "SR",
		"status_field": "status", "amount_field": None,
		"extra_filters": {"purpose": "Material Transfer"},
	},
	"pi": {
		"doctype": "Purchase Invoice", "label": "Purchase Invoice", "short": "PI",
		"status_field": "status", "amount_field": "grand_total",
	},
	"dn": {
		"doctype": "Delivery Note", "label": "Delivery Note", "short": "DN",
		"status_field": "status", "amount_field": "grand_total",
		"item_doctype": "Delivery Note Item", "item_so_field": "against_sales_order",
	},
	"si": {
		"doctype": "Sales Invoice", "label": "Sales Invoice", "short": "SI",
		"status_field": "status", "amount_field": "grand_total",
		"item_doctype": "Sales Invoice Item", "item_so_field": "sales_order",
	},
	"pe_in": {
		"doctype": "Payment Entry", "label": "Payment Received", "short": "PREC",
		"status_field": "status", "amount_field": "paid_amount",
		"extra_filters": {"payment_type": "Receive"},
	},
	"pe_out": {
		"doctype": "Payment Entry", "label": "Payment Paid", "short": "PPD",
		"status_field": "status", "amount_field": "paid_amount",
		"extra_filters": {"payment_type": "Pay"},
	},
	"je": {
		"doctype": "Journal Entry", "label": "Journal Entry", "short": "JE",
		"status_field": None, "amount_field": "total_debit",
	},
}

PENDING_STATUSES = {"Draft", "Pending Approval", "To Approve", "Pending"}

_DOCTYPE_EXISTS_CACHE = {}
_FIELD_EXISTS_CACHE = {}


def doctype_installed(doctype):
	if not doctype:
		return False
	if doctype not in _DOCTYPE_EXISTS_CACHE:
		_DOCTYPE_EXISTS_CACHE[doctype] = bool(frappe.db.exists("DocType", doctype))
	return _DOCTYPE_EXISTS_CACHE[doctype]


def field_exists(doctype, fieldname):
	if not doctype or not fieldname:
		return False
	key = (doctype, fieldname)
	if key not in _FIELD_EXISTS_CACHE:
		try:
			_FIELD_EXISTS_CACHE[key] = frappe.get_meta(doctype).has_field(fieldname)
		except Exception:
			_FIELD_EXISTS_CACHE[key] = False
	return _FIELD_EXISTS_CACHE[key]


def resolve_status_field(doctype, cfg):
	candidate = cfg.get("status_field")
	if candidate and field_exists(doctype, candidate):
		return candidate
	if field_exists(doctype, "workflow_state"):
		return "workflow_state"
	if candidate != "status" and field_exists(doctype, "status"):
		return "status"
	return None


def check_detail_view_permission(throw=True):
	"""Checks if logged in user has the role configured in Selling Settings."""
	configured_role = (frappe.db.get_single_value("Selling Settings", "role_allowed_to_detail_view_sales_order_tracker") or "").strip()
	user_roles = frappe.get_roles(frappe.session.user)

	if frappe.session.user == "Administrator" or "System Manager" in user_roles:
		return True

	if configured_role and configured_role in user_roles:
		return True

	if throw:
		frappe.throw(
			_("You do not have permission to view Sales Order Tracker details. Configured role: {0}").format(
				configured_role or _("None (System Manager only)")
			),
			frappe.PermissionError,
		)
	return False


# ---------------------------------------------------------------------------
# List view (Tab 1 — Status Overview)
# Driven by Sales Order, Item, and Batch
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_sales_order_list(
	from_date=None, to_date=None, sales_order=None, customer=None,
	project=None, branch=None, company=None, batch_no=None, item_code=None,
	so_status=None, view_mode="batch", page=1, page_length=50, limit=None
):
	"""Returns line-wise item rows driven by Sales Order, with document status trail."""
	import math
	so_filters = {"docstatus": ["!=", 2]}

	from_date = (from_date or "").strip()
	to_date = (to_date or "").strip()
	sales_order = (sales_order or "").strip()
	customer = (customer or "").strip()
	project = (project or "").strip()
	branch = (branch or "").strip()
	company = (company or "").strip()
	batch_no = (batch_no or "").strip()
	item_code = (item_code or "").strip()
	so_status = (so_status or "").strip()

	# Show only open Sales Orders by default unless specified otherwise
	if not so_status or so_status.lower() in ("open", "open orders"):
		so_filters["status"] = ["not in", ["Closed", "Completed", "Cancelled"]]
	elif so_status.lower() == "all":
		pass  # keep docstatus != 2
	elif so_status in ("To Deliver and Bill"):
		so_filters["status"] = ["in", ["To Deliver and Bill"]]
	else:
		so_filters["status"] = so_status

	page = max(1, frappe.utils.cint(page or 1))
	page_length = frappe.utils.cint(limit or page_length or 50)
	if page_length < 1:
		page_length = 50
	start = (page - 1) * page_length

	date_field = "transaction_date" if field_exists("Sales Order", "transaction_date") else "creation"
	if from_date and to_date:
		if not sales_order:
			so_filters[date_field] = ["between", [from_date, to_date]]
	elif from_date:
		if not sales_order:
			so_filters[date_field] = [">=", from_date]
	elif to_date:
		if not sales_order:
			so_filters[date_field] = ["<=", to_date]

	if sales_order:
		so_filters["name"] = sales_order
	if customer and field_exists("Sales Order", "customer"):
		so_filters["customer"] = customer
	if project and field_exists("Sales Order", "project"):
		so_filters["project"] = ["like", f"%{project}%"]
	if branch and field_exists("Sales Order", "branch"):
		so_filters["branch"] = branch
	if company and field_exists("Sales Order", "company"):
		so_filters["company"] = company

	total_sos = 0  # Only consider Sales Orders that have stock items
	so_item_conds = ["soi.docstatus != 2", "item.is_stock_item = 1", "so.docstatus != 2"]
	so_item_vals = {}

	if not so_status or so_status.lower() in ("open", "open orders"):
		so_item_conds.append("so.status not in ('Closed', 'Completed', 'Cancelled')")
	elif so_status.lower() == "all":
		pass
	elif so_status in ("To Deliver and Bill"):
		so_item_conds.append("so.status in ('To Deliver and Bill')")
	else:
		so_item_conds.append("so.status = %(so_status)s")
		so_item_vals["so_status"] = so_status

	if sales_order:
		so_item_conds.append("soi.parent = %(sales_order)s")
		so_item_vals["sales_order"] = sales_order
	if batch_no:
		has_b = field_exists("Sales Order Item", "batch_no")
		has_cb = field_exists("Sales Order Item", "custom_batch_no")
		b_clauses = []
		if has_b:
			b_clauses.append("soi.batch_no like %(batch_no)s")
		if has_cb:
			b_clauses.append("soi.custom_batch_no like %(batch_no)s")
		if b_clauses:
			so_item_conds.append(f"({' or '.join(b_clauses)})")
			so_item_vals["batch_no"] = f"%{batch_no}%"
	if item_code:
		so_item_conds.append("soi.item_code like %(item_code)s")
		so_item_vals["item_code"] = f"%{item_code}%"

	matching_sos = frappe.db.sql(
		f"""
		select distinct soi.parent
		from `tabSales Order Item` soi
		join `tabSales Order` so on so.name = soi.parent
		inner join `tabItem` item on item.name = soi.item_code
		where {' and '.join(so_item_conds)}
		""",
		so_item_vals,
		pluck=True,
	)
	if not matching_sos:
		return {
			"sales_orders": [],
			"batch_items": [],
			"total_sos": 0,
			"total_batches": 0,
			"page": page,
			"page_length": page_length,
			"total_pages": 0,
			"view_mode": view_mode or "batch",
			"can_view_detail": check_detail_view_permission(throw=False),
		}
	if not sales_order:
		so_filters["name"] = ["in", matching_sos]
	total_sos = frappe.db.count("Sales Order", filters=so_filters)

	so_fields = ["name", "customer", "transaction_date", "delivery_date", "status", "grand_total", "net_total", "per_delivered"]
	if field_exists("Sales Order", "project"):
		so_fields.append("project")
	if field_exists("Sales Order", "branch"):
		so_fields.append("branch")
	if field_exists("Sales Order", "company"):
		so_fields.append("company")
	if field_exists("Sales Order", "customer_name"):
		so_fields.append("customer_name")
	if field_exists("Sales Order", "title"):
		so_fields.append("title")

	sales_orders = frappe.get_all(
		"Sales Order",
		filters=so_filters,
		fields=so_fields,
		order_by=f"{date_field} desc, creation desc",
		start=start,
		page_length=page_length,
	)

	if not sales_orders:
		return {
			"sales_orders": [],
			"batch_items": [],
			"total_sos": total_sos,
			"total_batches": 0,
			"page": page,
			"page_length": page_length,
			"total_pages": math.ceil(total_sos / page_length) if page_length and total_sos else 1,
			"view_mode": view_mode or "batch",
		}

	so_names = [s.name for s in sales_orders]

	has_batch = field_exists("Sales Order Item", "batch_no")
	has_custom_batch = field_exists("Sales Order Item", "custom_batch_no")
	batch_field = "soi.batch_no" if has_batch else ("soi.custom_batch_no as batch_no" if has_custom_batch else "NULL as batch_no")
	has_prevdoc = field_exists("Sales Order Item", "prevdoc_docname")
	prevdoc_field = "soi.prevdoc_docname" if has_prevdoc else "NULL as prevdoc_docname"

	all_so_items = frappe.db.sql(
		f"""
		select soi.name as so_item_name, soi.parent as sales_order, soi.idx as line_no, soi.item_code, soi.item_name, soi.description,
			soi.qty, soi.delivered_qty, soi.rate, soi.amount, soi.delivery_date,
			{batch_field}, {prevdoc_field}
		from `tabSales Order Item` soi
		inner join `tabItem` item on item.name = soi.item_code
		where soi.parent in %(so_names)s and soi.docstatus != 2 and item.is_stock_item = 1
		order by soi.parent, soi.idx
		""",
		{"so_names": so_names},
		as_dict=True,
	)

	# Fast bulk prefetching of all document trails for all loaded SOs and items
	so_docs_map, item_docs_map = bulk_prefetch_docs(sales_orders, all_so_items, branch=branch)

	so_items_by_so = {}
	for it in all_so_items:
		so_items_by_so.setdefault(it.sales_order, []).append(it)

	result = []
	all_batch_items = []

	for so in sales_orders:
		so_name = so.name
		so_project = so.get("project")
		so_branch = so.get("branch")
		so_customer = so.get("customer")
		so_customer_name = so.get("customer_name") or so_customer
		so_date = str(so.get("transaction_date") or getdate(so.get("creation"))) if (so.get("transaction_date") or so.get("creation")) else None

		docs = so_docs_map.get(so_name) or {
			k: None for k in LIST_DOC_KEYS
		}
		docs["so"] = {
			"name": so_name,
			"doctype": "Sales Order",
			"status": so.status,
			"count": 1,
		}

		pending_at, _stage_key = determine_pending(docs, so_doc=so)
		priority = determine_priority(so)

		so_items = so_items_by_so.get(so_name, [])

		items_list = []
		total_qty = 0.0
		total_delivered = 0.0

		if so_items:
			for item in so_items:
				item_b_no = item.get("batch_no")
				if batch_no and batch_no.lower() not in (item_b_no or "").lower():
					continue
				if item_code and item_code.lower() not in (item.item_code or "").lower():
					continue

				q = flt(item.qty)
				dq = flt(item.delivered_qty)
				total_qty += q
				total_delivered += dq

				item_docs = item_docs_map.get((so_name, item.so_item_name)) or {
					k: None for k in LIST_DOC_KEYS
				}
				item_docs["so"] = {
					"name": so_name,
					"doctype": "Sales Order",
					"status": so.status,
					"count": 1,
				}

				item_pending, _ = determine_item_pending(item_docs, item_data=item, so_status=so.status)
				item_priority = determine_item_priority(item, so_status=so.status)
				item_delivery_date = str(item.delivery_date) if item.delivery_date else (str(so.get("delivery_date")) if so.get("delivery_date") else None)

				item_record = {
					"so_item_name": item.so_item_name,
					"sales_order": so_name,
					"line_no": item.line_no,
					"item_code": item.item_code,
					"item_name": item.item_name or item.item_code,
					"batch_no": item_b_no,
					"description": item.description,
					"qty": q,
					"delivered_qty": dq,
					"pending_qty": max(0.0, q - dq),
					"rate": flt(item.rate),
					"amount": flt(item.amount or (q * flt(item.rate))),
					"delivery_date": item_delivery_date,
					"customer": so_customer,
					"customer_name": so_customer_name,
					"project": so_project,
					"branch": so_branch,
					"pending_at": item_pending,
					"priority": item_priority,
					"so_status": so.get("status"),
					"docs": {k: item_docs.get(k) for k in LIST_DOC_KEYS},
				}

				items_list.append(item_record)
				all_batch_items.append(item_record)

		if not items_list and (batch_no or item_code):
			continue

		so_delivery_date = str(so.get("delivery_date")) if so.get("delivery_date") else (items_list[0]["delivery_date"] if items_list and items_list[0].get("delivery_date") else None)

		result.append({
			"sales_order": so_name,
			"so": so_name,
			"project": so_project,
			"project_name": so_project,
			"branch": so_branch,
			"customer": so_customer,
			"customer_name": so_customer_name,
			"date": so_date,
			"delivery_date": so_delivery_date,
			"status": so.get("status"),
			"grand_total": flt(so.get("grand_total") or so.get("net_total") or sum(it["amount"] for it in items_list)),
			"total_qty": total_qty,
			"delivered_qty": total_delivered,
			"pending_at": pending_at,
			"priority": priority,
			"items_count": len(items_list),
			"items": items_list,
			"docs": {k: docs.get(k) for k in LIST_DOC_KEYS},
		})

	total_batches = 0
	if total_sos > 0:
		so_join_conds = ["so.docstatus != 2", "soi.docstatus != 2"]
		so_join_vals = {}
		if from_date and to_date:
			if not sales_order:
				so_join_conds.append(f"so.{date_field} between %(from_date)s and %(to_date)s")
				so_join_vals["from_date"] = from_date
				so_join_vals["to_date"] = to_date
		elif from_date:
			if not sales_order:
				so_join_conds.append(f"so.{date_field} >= %(from_date)s")
				so_join_vals["from_date"] = from_date
		elif to_date:
			if not sales_order:
				so_join_conds.append(f"so.{date_field} <= %(to_date)s")
				so_join_vals["to_date"] = to_date

		if sales_order:
			# so_join_conds.append("so.name like %(sales_order)s")
			# so_join_vals["sales_order"] = f"%{sales_order}%"
			so_join_conds.append("so.name = %(sales_order)s")
			so_join_vals["sales_order"] = sales_order
		if customer and field_exists("Sales Order", "customer"):
			so_join_conds.append("so.customer = %(customer)s")
			so_join_vals["customer"] = customer
		if project and field_exists("Sales Order", "project"):
			so_join_conds.append("so.project like %(project)s")
			so_join_vals["project"] = f"%{project}%"
		if branch and field_exists("Sales Order", "branch"):
			so_join_conds.append("so.branch = %(branch)s")
			so_join_vals["branch"] = branch
		if company and field_exists("Sales Order", "company"):
			so_join_conds.append("so.company = %(company)s")
			so_join_vals["company"] = company

		if batch_no:
			has_b = field_exists("Sales Order Item", "batch_no")
			has_cb = field_exists("Sales Order Item", "custom_batch_no")
			b_clauses = []
			if has_b:
				b_clauses.append("soi.batch_no like %(batch_no)s")
			if has_cb:
				b_clauses.append("soi.custom_batch_no like %(batch_no)s")
			if b_clauses:
				so_join_conds.append(f"({' or '.join(b_clauses)})")
				so_join_vals["batch_no"] = f"%{batch_no}%"

		if not so_status or so_status.lower() in ("open", "open orders"):
			so_join_conds.append("so.status not in ('Closed', 'Completed', 'Cancelled')")
		elif so_status.lower() == "all":
			pass
		elif so_status in ("To Deliver and Bill"):
			so_join_conds.append("so.status in ('To Deliver and Bill')")
		else:
			so_join_conds.append("so.status = %(so_status)s")
			so_join_vals["so_status"] = so_status

		if item_code:
			so_join_conds.append("soi.item_code like %(item_code)s")
			so_join_vals["item_code"] = f"%{item_code}%"

		batches_count_res = frappe.db.sql(
			f"""
			select count(soi.name)
			from `tabSales Order Item` soi
			join `tabSales Order` so on so.name = soi.parent
			inner join `tabItem` item on item.name = soi.item_code
			where item.is_stock_item = 1 and {' and '.join(so_join_conds)}
			""",
			so_join_vals,
			pluck=True,
		)
		total_batches = batches_count_res[0] if batches_count_res else len(all_batch_items)

	return {
		"sales_orders": result,
		"batch_items": all_batch_items,
		"total_sos": total_sos,
		"total_batches": total_batches,
		"page": page,
		"page_length": page_length,
		"total_pages": math.ceil(total_sos / page_length) if page_length and total_sos else 1,
		"view_mode": view_mode or "batch",
		"can_view_detail": check_detail_view_permission(throw=False),
	}


@frappe.whitelist()
def get_ao_list(*args, **kwargs):
	"""Backward compatibility wrapper for get_sales_order_list."""
	return get_sales_order_list(*args, **kwargs)


def bulk_prefetch_docs(sales_orders_list, all_so_items, branch=None):
	"""
	Prefetches and indexes all linked documents for a list of Sales Orders and their items in bulk.
	Returns:
	  so_docs_map: dict[so_name -> dict[key -> latest_doc_dict]]
	  item_docs_map: dict[(so_name, so_item_name) -> dict[key -> latest_doc_dict]]
	"""
	from collections import defaultdict
	if not sales_orders_list:
		return {}, {}

	so_names = [s.name for s in sales_orders_list]
	all_discovered_docnames = defaultdict(set)

	so_docnames_map = defaultdict(lambda: defaultdict(set))
	item_docnames_map = defaultdict(lambda: defaultdict(set))

	items_by_so = defaultdict(list)
	for it in all_so_items:
		items_by_so[it.sales_order].append(it)

	# 1. Quotations
	for it in all_so_items:
		prevdoc = it.get("prevdoc_docname")
		if prevdoc:
			so_docnames_map[it.sales_order]["quote"].add(prevdoc)
			item_docnames_map[(it.sales_order, it.so_item_name)]["quote"].add(prevdoc)
			all_discovered_docnames["Quotation"].add(prevdoc)

	for so in sales_orders_list:
		if field_exists("Sales Order", "quotation_no"):
			q_no = so.get("quotation_no")
			if q_no:
				so_docnames_map[so.name]["quote"].add(q_no)
				all_discovered_docnames["Quotation"].add(q_no)

	# 2. BOMs
	# Match ONLY Finished Good item for each SO item line.
	# Apply Batch filter if batch exists.
	if doctype_installed("BOM"):
		item_codes_set = {it.item_code for it in all_so_items if it.get("item_code")}
		bom_where = ["sales_order in %(so_names)s"]
		bom_vals = {"so_names": so_names}
		if item_codes_set:
			bom_where.append("(item in %(item_codes)s and is_default = 1 and is_active = 1 and docstatus = 1)")
			bom_vals["item_codes"] = tuple(item_codes_set)

		has_cb_field = field_exists("BOM", "custom_batch_no")
		cb_select = "custom_batch_no" if has_cb_field else "NULL as custom_batch_no"

		bom_rows = frappe.db.sql(
			f"""
			select name, item, sales_order, {cb_select}, is_default, is_active, docstatus, workflow_state, total_cost
			from `tabBOM`
			where docstatus != 2 and ({' or '.join(bom_where)})
			""",
			bom_vals,
			as_dict=True,
		)
		boms_by_item_so_batch = defaultdict(list)
		boms_by_item_so = defaultdict(list)
		default_boms_by_item = defaultdict(list)

		for b in bom_rows:
			all_discovered_docnames["BOM"].add(b.name)
			ic = b.item
			so = b.sales_order
			cb = (b.custom_batch_no or "").strip()
			if so and ic:
				if cb:
					boms_by_item_so_batch[(so, ic, cb)].append(b)
				else:
					boms_by_item_so[(so, ic)].append(b)
			if ic and b.is_default and b.is_active and b.docstatus == 1:
				default_boms_by_item[ic].append(b)

		for it in all_so_items:
			b_no = it.get("bom_no")
			if b_no:
				all_discovered_docnames["BOM"].add(b_no)

		for it in all_so_items:
			so_n = it.sales_order
			soi_n = it.so_item_name
			ic = it.item_code
			b_no = (it.get("batch_no") or "").strip()
			explicit_bom = it.get("bom_no")

			matched_bom = None
			if b_no and boms_by_item_so_batch.get((so_n, ic, b_no)):
				candidates = boms_by_item_so_batch[(so_n, ic, b_no)]
				submitted = [c for c in candidates if c.docstatus == 1]
				matched_bom = submitted[0].name if submitted else candidates[0].name
			elif explicit_bom:
				matched_bom = explicit_bom
			elif boms_by_item_so.get((so_n, ic)):
				candidates = boms_by_item_so[(so_n, ic)]
				submitted = [c for c in candidates if c.docstatus == 1]
				matched_bom = submitted[0].name if submitted else candidates[0].name
			elif default_boms_by_item.get(ic):
				matched_bom = default_boms_by_item[ic][0].name

			if matched_bom:
				item_docnames_map[(so_n, soi_n)]["bom"].add(matched_bom)
				so_docnames_map[so_n]["bom"].add(matched_bom)

	# 3. Production Plans
	pp_by_so_item = defaultdict(set)
	pp_by_so_batch = defaultdict(set)
	pp_by_so = defaultdict(set)
	all_pp_names = set()

	if doctype_installed("Production Plan"):
		if doctype_installed("Production Plan Item"):
			has_ppi_cb = field_exists("Production Plan Item", "custom_batch_no")
			ppi_cb_col = "custom_batch_no" if has_ppi_cb else "NULL as custom_batch_no"
			ppi_rows = frappe.db.sql(
				f"""
				select parent as pp_name, name as ppi_name, sales_order, sales_order_item, item_code, {ppi_cb_col}, bom_no
				from `tabProduction Plan Item`
				where docstatus != 2 and sales_order in %(so_names)s
				""",
				{"so_names": so_names},
				as_dict=True,
			)
			for ppi in ppi_rows:
				pp_name = ppi.pp_name
				so_n = ppi.sales_order
				soi_n = ppi.sales_order_item
				cb = (ppi.custom_batch_no or "").strip()
				ic = ppi.item_code
				bom = ppi.bom_no

				all_discovered_docnames["Production Plan"].add(pp_name)
				all_pp_names.add(pp_name)
				so_docnames_map[so_n]["pp"].add(pp_name)
				pp_by_so[so_n].add(pp_name)

				if soi_n:
					item_docnames_map[(so_n, soi_n)]["pp"].add(pp_name)
					pp_by_so_item[(so_n, soi_n)].add(pp_name)
				if cb:
					pp_by_so_batch[(so_n, cb)].add(pp_name)

				if bom and ic:
					for it in items_by_so[so_n]:
						if it.item_code == ic and ((not cb) or (it.get("batch_no") == cb)):
							if not item_docnames_map[(so_n, it.so_item_name)]["bom"]:
								item_docnames_map[(so_n, it.so_item_name)]["bom"].add(bom)
								so_docnames_map[so_n]["bom"].add(bom)
								all_discovered_docnames["BOM"].add(bom)

		if doctype_installed("Production Plan Sales Order"):
			ppso_rows = frappe.db.sql(
				"""
				select parent as pp_name, sales_order
				from `tabProduction Plan Sales Order`
				where docstatus != 2 and sales_order in %(so_names)s
				""",
				{"so_names": so_names},
				as_dict=True,
			)
			for ppso in ppso_rows:
				pp_name = ppso.pp_name
				so_n = ppso.sales_order
				all_discovered_docnames["Production Plan"].add(pp_name)
				all_pp_names.add(pp_name)
				so_docnames_map[so_n]["pp"].add(pp_name)
				pp_by_so[so_n].add(pp_name)

	# 4. Material Requests
	mr_names_set = set()
	mr_to_so_map = defaultdict(set)
	mr_to_soi_map = defaultdict(set)

	if doctype_installed("Material Request") and doctype_installed("Material Request Item"):
		mri_conds = []
		mri_vals = {"so_names": so_names}
		has_mri_so = field_exists("Material Request Item", "sales_order")
		has_mri_pp = field_exists("Material Request Item", "production_plan")
		has_mri_cb = field_exists("Material Request Item", "custom_batch_no")
		has_mri_soi = field_exists("Material Request Item", "sales_order_item")

		mri_so_expr = "mri.sales_order" if has_mri_so else "NULL as sales_order"
		mri_pp_expr = "mri.production_plan" if has_mri_pp else "NULL as production_plan"
		mri_cb_expr = "mri.custom_batch_no" if has_mri_cb else "NULL as custom_batch_no"
		mri_soi_expr = "mri.sales_order_item" if has_mri_soi else "NULL as sales_order_item"

		if has_mri_so:
			mri_conds.append("mri.sales_order in %(so_names)s")
		if has_mri_pp and all_pp_names:
			mri_conds.append("mri.production_plan in %(pp_names)s")
			mri_vals["pp_names"] = tuple(all_pp_names)

		mri_rows = []
		if mri_conds:
			mri_rows = frappe.db.sql(
				f"""
				select mri.parent as mr_name, {mri_so_expr}, {mri_soi_expr}, {mri_pp_expr},
					   {mri_cb_expr}, mri.item_code
				from `tabMaterial Request Item` mri
				where mri.docstatus != 2 and ({' or '.join(mri_conds)})
				""",
				mri_vals,
				as_dict=True,
			)

		ppmr_rows = []
		if all_pp_names and doctype_installed("Production Plan Material Request"):
			ppmr_rows = frappe.db.sql(
				"""
				select parent as pp_name, material_request as mr_name
				from `tabProduction Plan Material Request`
				where docstatus != 2 and parent in %(pp_names)s and material_request is not null
				""",
				{"pp_names": tuple(all_pp_names)},
				as_dict=True,
			)

		pp_to_so = defaultdict(set)
		pp_to_soi = defaultdict(set)
		pp_to_batch = defaultdict(set)
		for so_n, pps in pp_by_so.items():
			for p in pps:
				pp_to_so[p].add(so_n)
		for (so_n, soi_n), pps in pp_by_so_item.items():
			for p in pps:
				pp_to_soi[p].add((so_n, soi_n))
		for (so_n, cb), pps in pp_by_so_batch.items():
			for p in pps:
				pp_to_batch[p].add((so_n, cb))

		for mri in mri_rows:
			mr_n = mri.mr_name
			all_discovered_docnames["Material Request"].add(mr_n)
			mr_names_set.add(mr_n)
			so_n = mri.get("sales_order")
			soi_n = mri.get("sales_order_item")
			pp_n = mri.get("production_plan")
			cb = (mri.get("custom_batch_no") or "").strip()

			if so_n:
				so_docnames_map[so_n]["mr"].add(mr_n)
				mr_to_so_map[mr_n].add(so_n)
				if soi_n:
					item_docnames_map[(so_n, soi_n)]["mr"].add(mr_n)
					mr_to_soi_map[mr_n].add((so_n, soi_n))
				elif cb:
					for it in items_by_so[so_n]:
						if (it.get("batch_no") or "").strip() == cb:
							item_docnames_map[(so_n, it.so_item_name)]["mr"].add(mr_n)
							mr_to_soi_map[mr_n].add((so_n, it.so_item_name))
			elif pp_n:
				for s in pp_to_so.get(pp_n, []):
					so_docnames_map[s]["mr"].add(mr_n)
					mr_to_so_map[mr_n].add(s)
				for (s, soi) in pp_to_soi.get(pp_n, []):
					item_docnames_map[(s, soi)]["mr"].add(mr_n)
					mr_to_soi_map[mr_n].add((s, soi))
				for (s, b) in pp_to_batch.get(pp_n, []):
					if (not cb) or (cb == b):
						for it in items_by_so[s]:
							if (it.get("batch_no") or "").strip() == b:
								item_docnames_map[(s, it.so_item_name)]["mr"].add(mr_n)
								mr_to_soi_map[mr_n].add((s, it.so_item_name))

		for ppmr in ppmr_rows:
			mr_n = ppmr.mr_name
			pp_n = ppmr.pp_name
			all_discovered_docnames["Material Request"].add(mr_n)
			mr_names_set.add(mr_n)
			for s in pp_to_so.get(pp_n, []):
				so_docnames_map[s]["mr"].add(mr_n)
				mr_to_so_map[mr_n].add(s)
			for (s, soi) in pp_to_soi.get(pp_n, []):
				item_docnames_map[(s, soi)]["mr"].add(mr_n)
				mr_to_soi_map[mr_n].add((s, soi))

	# 5. Purchase Orders
	po_names_set = set()
	po_to_so_map = defaultdict(set)
	po_to_soi_map = defaultdict(set)

	if doctype_installed("Purchase Order") and doctype_installed("Purchase Order Item"):
		poi_conds = []
		poi_vals = {"so_names": so_names}
		has_poi_so = field_exists("Purchase Order Item", "sales_order")
		has_poi_mr = field_exists("Purchase Order Item", "material_request")
		has_poi_pp = field_exists("Purchase Order Item", "production_plan")
		has_poi_cb = field_exists("Purchase Order Item", "custom_batch_no")
		has_poi_soi = field_exists("Purchase Order Item", "sales_order_item")

		poi_so_expr = "poi.sales_order" if has_poi_so else "NULL as sales_order"
		poi_soi_expr = "poi.sales_order_item" if has_poi_soi else "NULL as sales_order_item"
		poi_mr_expr = "poi.material_request" if has_poi_mr else "NULL as material_request"
		poi_pp_expr = "poi.production_plan" if has_poi_pp else "NULL as production_plan"
		poi_cb_expr = "poi.custom_batch_no" if has_poi_cb else "NULL as custom_batch_no"

		if has_poi_so:
			poi_conds.append("poi.sales_order in %(so_names)s")
		if has_poi_mr and mr_names_set:
			poi_conds.append("poi.material_request in %(mr_names)s")
			poi_vals["mr_names"] = tuple(mr_names_set)
		if has_poi_pp and all_pp_names:
			poi_conds.append("poi.production_plan in %(pp_names)s")
			poi_vals["pp_names"] = tuple(all_pp_names)

		if poi_conds:
			poi_rows = frappe.db.sql(
				f"""
				select poi.parent as po_name, {poi_so_expr}, {poi_soi_expr}, {poi_mr_expr},
					   {poi_pp_expr}, {poi_cb_expr}
				from `tabPurchase Order Item` poi
				where poi.docstatus != 2 and ({' or '.join(poi_conds)})
				""",
				poi_vals,
				as_dict=True,
			)
			for poi in poi_rows:
				po_n = poi.po_name
				all_discovered_docnames["Purchase Order"].add(po_n)
				po_names_set.add(po_n)
				so_n = poi.get("sales_order")
				soi_n = poi.get("sales_order_item")
				mr_n = poi.get("material_request")
				pp_n = poi.get("production_plan")
				cb = (poi.get("custom_batch_no") or "").strip()

				if so_n:
					so_docnames_map[so_n]["po"].add(po_n)
					po_to_so_map[po_n].add(so_n)
					if soi_n:
						item_docnames_map[(so_n, soi_n)]["po"].add(po_n)
						po_to_soi_map[po_n].add((so_n, soi_n))
					elif cb:
						for it in items_by_so[so_n]:
							if (it.get("batch_no") or "").strip() == cb:
								item_docnames_map[(so_n, it.so_item_name)]["po"].add(po_n)
								po_to_soi_map[po_n].add((so_n, it.so_item_name))
				elif mr_n and mr_n in mr_to_so_map:
					for s in mr_to_so_map[mr_n]:
						so_docnames_map[s]["po"].add(po_n)
						po_to_so_map[po_n].add(s)
					for (s, soi) in mr_to_soi_map[mr_n]:
						item_docnames_map[(s, soi)]["po"].add(po_n)
						po_to_soi_map[po_n].add((s, soi))
				elif pp_n:
					for s in pp_to_so.get(pp_n, []):
						so_docnames_map[s]["po"].add(po_n)
						po_to_so_map[po_n].add(s)
					for (s, soi) in pp_to_soi.get(pp_n, []):
						item_docnames_map[(s, soi)]["po"].add(po_n)
						po_to_soi_map[po_n].add((s, soi))

	# 6. Purchase Receipts
	if doctype_installed("Purchase Receipt") and doctype_installed("Purchase Receipt Item"):
		pri_conds = []
		pri_vals = {"so_names": so_names}
		has_pri_so = field_exists("Purchase Receipt Item", "sales_order")
		has_pri_po = field_exists("Purchase Receipt Item", "purchase_order")
		has_pri_mr = field_exists("Purchase Receipt Item", "material_request")
		has_pri_cb = field_exists("Purchase Receipt Item", "custom_batch_no")
		has_pri_soi = field_exists("Purchase Receipt Item", "sales_order_item")

		pri_so_expr = "pri.sales_order" if has_pri_so else "NULL as sales_order"
		pri_soi_expr = "pri.sales_order_item" if has_pri_soi else "NULL as sales_order_item"
		pri_po_expr = "pri.purchase_order" if has_pri_po else "NULL as purchase_order"
		pri_mr_expr = "pri.material_request" if has_pri_mr else "NULL as material_request"
		pri_cb_expr = "pri.custom_batch_no" if has_pri_cb else "NULL as custom_batch_no"

		if has_pri_so:
			pri_conds.append("pri.sales_order in %(so_names)s")
		if has_pri_po and po_names_set:
			pri_conds.append("pri.purchase_order in %(po_names)s")
			pri_vals["po_names"] = tuple(po_names_set)
		if has_pri_mr and mr_names_set:
			pri_conds.append("pri.material_request in %(mr_names)s")
			pri_vals["mr_names"] = tuple(mr_names_set)

		if pri_conds:
			pri_rows = frappe.db.sql(
				f"""
				select pri.parent as pr_name, {pri_so_expr}, {pri_soi_expr}, {pri_po_expr},
					   {pri_mr_expr}, {pri_cb_expr}
				from `tabPurchase Receipt Item` pri
				where pri.docstatus != 2 and ({' or '.join(pri_conds)})
				""",
				pri_vals,
				as_dict=True,
			)
			for pri in pri_rows:
				pr_n = pri.pr_name
				all_discovered_docnames["Purchase Receipt"].add(pr_n)
				so_n = pri.get("sales_order")
				soi_n = pri.get("sales_order_item")
				po_n = pri.get("purchase_order")
				mr_n = pri.get("material_request")
				cb = (pri.get("custom_batch_no") or "").strip()

				if so_n:
					so_docnames_map[so_n]["pr"].add(pr_n)
					if soi_n:
						item_docnames_map[(so_n, soi_n)]["pr"].add(pr_n)
					elif cb:
						for it in items_by_so[so_n]:
							if (it.get("batch_no") or "").strip() == cb:
								item_docnames_map[(so_n, it.so_item_name)]["pr"].add(pr_n)
				elif po_n and po_n in po_to_so_map:
					for s in po_to_so_map[po_n]:
						so_docnames_map[s]["pr"].add(pr_n)
					for (s, soi) in po_to_soi_map[po_n]:
						item_docnames_map[(s, soi)]["pr"].add(pr_n)
				elif mr_n and mr_n in mr_to_so_map:
					for s in mr_to_so_map[mr_n]:
						so_docnames_map[s]["pr"].add(pr_n)
					for (s, soi) in mr_to_soi_map[mr_n]:
						item_docnames_map[(s, soi)]["pr"].add(pr_n)

	# 7. Purchase Invoices
	pi_names_set = set()
	pi_to_so_map = defaultdict(set)
	pi_to_soi_map = defaultdict(set)

	if doctype_installed("Purchase Invoice") and doctype_installed("Purchase Invoice Item"):
		if po_names_set:
			pii_rows = frappe.db.sql(
				"""
				select pii.parent as pi_name, pii.purchase_order
				from `tabPurchase Invoice Item` pii
				where pii.docstatus != 2 and pii.purchase_order in %(po_names)s
				""",
				{"po_names": tuple(po_names_set)},
				as_dict=True,
			)
			for pii in pii_rows:
				pi_n = pii.pi_name
				po_n = pii.purchase_order
				all_discovered_docnames["Purchase Invoice"].add(pi_n)
				pi_names_set.add(pi_n)
				for s in po_to_so_map.get(po_n, []):
					so_docnames_map[s]["pi"].add(pi_n)
					pi_to_so_map[pi_n].add(s)
				for (s, soi) in po_to_soi_map[po_n]:
					item_docnames_map[(s, soi)]["pi"].add(pi_n)
					pi_to_soi_map[pi_n].add((s, soi))

	# 8. Delivery Note
	if doctype_installed("Delivery Note") and doctype_installed("Delivery Note Item"):
		has_dni_sod = field_exists("Delivery Note Item", "so_detail")
		has_dni_cb = field_exists("Delivery Note Item", "custom_batch_no")
		has_dni_b = field_exists("Delivery Note Item", "batch_no")

		dni_sod_expr = "dni.so_detail" if has_dni_sod else "NULL as so_detail"
		dni_cb_expr = "dni.custom_batch_no" if has_dni_cb else ("dni.batch_no" if has_dni_b else "NULL as custom_batch_no")

		dni_rows = frappe.db.sql(
			f"""
			select dni.parent as dn_name, dni.against_sales_order as sales_order, {dni_sod_expr},
				   dni.item_code, {dni_cb_expr}
			from `tabDelivery Note Item` dni
			where dni.docstatus != 2 and dni.against_sales_order in %(so_names)s
			""",
			{"so_names": so_names},
			as_dict=True,
		)
		for dni in dni_rows:
			dn_n = dni.dn_name
			so_n = dni.sales_order
			sod = dni.get("so_detail")
			ic = dni.item_code
			b_no = (dni.get("custom_batch_no") or "").strip()
			all_discovered_docnames["Delivery Note"].add(dn_n)
			so_docnames_map[so_n]["dn"].add(dn_n)
			if sod:
				item_docnames_map[(so_n, sod)]["dn"].add(dn_n)
			else:
				for it in items_by_so[so_n]:
					if it.item_code == ic and ((not b_no) or ((it.get("batch_no") or "").strip() == b_no)):
						item_docnames_map[(so_n, it.so_item_name)]["dn"].add(dn_n)

	# 9. Sales Invoice
	si_names_set = set()
	si_to_so_map = defaultdict(set)
	si_to_soi_map = defaultdict(set)

	if doctype_installed("Sales Invoice") and doctype_installed("Sales Invoice Item"):
		has_sii_sod = field_exists("Sales Invoice Item", "so_detail")
		has_sii_cb = field_exists("Sales Invoice Item", "custom_batch_no")
		has_sii_b = field_exists("Sales Invoice Item", "batch_no")

		sii_sod_expr = "sii.so_detail" if has_sii_sod else "NULL as so_detail"
		sii_cb_expr = "sii.custom_batch_no" if has_sii_cb else ("sii.batch_no" if has_sii_b else "NULL as custom_batch_no")

		sii_rows = frappe.db.sql(
			f"""
			select sii.parent as si_name, sii.sales_order, {sii_sod_expr},
				   sii.item_code, {sii_cb_expr}
			from `tabSales Invoice Item` sii
			where sii.docstatus != 2 and sii.sales_order in %(so_names)s
			""",
			{"so_names": so_names},
			as_dict=True,
		)
		for sii in sii_rows:
			si_n = sii.si_name
			so_n = sii.sales_order
			sod = sii.get("so_detail")
			ic = sii.item_code
			b_no = (sii.get("custom_batch_no") or "").strip()
			all_discovered_docnames["Sales Invoice"].add(si_n)
			so_docnames_map[so_n]["si"].add(si_n)
			si_names_set.add(si_n)
			si_to_so_map[si_n].add(so_n)
			if sod:
				item_docnames_map[(so_n, sod)]["si"].add(si_n)
				si_to_soi_map[si_n].add((so_n, sod))
			else:
				for it in items_by_so[so_n]:
					if it.item_code == ic and ((not b_no) or ((it.get("batch_no") or "").strip() == b_no)):
						item_docnames_map[(so_n, it.so_item_name)]["si"].add(si_n)
						si_to_soi_map[si_n].add((so_n, it.so_item_name))

	# 10. Payment Entries (Payment Paid - pe_out & Payment Received - pe_in)
	if doctype_installed("Payment Entry") and doctype_installed("Payment Entry Reference"):
		pe_conds = []
		pe_vals = {"so_names": tuple(so_names)}
		pe_conds.append("(per.reference_doctype = 'Sales Order' and per.reference_name in %(so_names)s)")
		if pi_names_set:
			pe_conds.append("(per.reference_doctype = 'Purchase Invoice' and per.reference_name in %(pi_names)s)")
			pe_vals["pi_names"] = tuple(pi_names_set)
		if po_names_set:
			pe_conds.append("(per.reference_doctype = 'Purchase Order' and per.reference_name in %(po_names)s)")
			pe_vals["po_names"] = tuple(po_names_set)
		if si_names_set:
			pe_conds.append("(per.reference_doctype = 'Sales Invoice' and per.reference_name in %(si_names)s)")
			pe_vals["si_names"] = tuple(si_names_set)

		pe_rows = frappe.db.sql(
			f"""
			select per.parent as pe_name, per.reference_doctype, per.reference_name, pe.payment_type
			from `tabPayment Entry Reference` per
			inner join `tabPayment Entry` pe on pe.name = per.parent
			where pe.docstatus != 2 and ({' or '.join(pe_conds)})
			""",
			pe_vals,
			as_dict=True,
		)
		for per in pe_rows:
			pe_n = per.pe_name
			ref_dt = per.reference_doctype
			ref_n = per.reference_name
			ptype = per.payment_type
			all_discovered_docnames["Payment Entry"].add(pe_n)

			if ptype in ("Pay", "Internal Transfer"):
				if ref_dt == "Purchase Invoice":
					for s in pi_to_so_map.get(ref_n, []):
						so_docnames_map[s]["pe_out"].add(pe_n)
					for (s, soi) in pi_to_soi_map.get(ref_n, []):
						item_docnames_map[(s, soi)]["pe_out"].add(pe_n)
				elif ref_dt == "Purchase Order":
					for s in po_to_so_map.get(ref_n, []):
						so_docnames_map[s]["pe_out"].add(pe_n)
					for (s, soi) in po_to_soi_map.get(ref_n, []):
						item_docnames_map[(s, soi)]["pe_out"].add(pe_n)
				elif ref_dt == "Sales Order":
					so_docnames_map[ref_n]["pe_out"].add(pe_n)
					for it in items_by_so.get(ref_n, []):
						item_docnames_map[(ref_n, it.so_item_name)]["pe_out"].add(pe_n)

			if ptype in ("Receive", "Internal Transfer"):
				if ref_dt == "Sales Invoice":
					for s in si_to_so_map.get(ref_n, []):
						so_docnames_map[s]["pe_in"].add(pe_n)
					for (s, soi) in si_to_soi_map.get(ref_n, []):
						item_docnames_map[(s, soi)]["pe_in"].add(pe_n)
				elif ref_dt == "Sales Order":
					so_docnames_map[ref_n]["pe_in"].add(pe_n)
					for it in items_by_so.get(ref_n, []):
						item_docnames_map[(ref_n, it.so_item_name)]["pe_in"].add(pe_n)

	# Bulk Query Headers
	headers_cache = defaultdict(dict)
	for doctype, docnames in all_discovered_docnames.items():
		if not docnames:
			continue
		cfg = next((c for c in DOC_CONFIG.values() if c["doctype"] == doctype), {})
		status_field = resolve_status_field(doctype, cfg)
		amount_field = cfg.get("amount_field") if cfg.get("amount_field") and field_exists(doctype, cfg["amount_field"]) else None

		fields = ["name", "creation", "docstatus"]
		if status_field:
			fields.append(f"{status_field} as status")
		if amount_field:
			fields.append(f"{amount_field} as amount")

		docs = frappe.get_all(doctype, filters={"name": ["in", list(docnames)]}, fields=fields)
		for d in docs:
			doc_status = d.get("status")
			if not status_field:
				doc_status = "Submitted" if d.get("docstatus") == 1 else "Draft"
			headers_cache[doctype][d.name] = {
				"name": d.name,
				"creation": d.creation,
				"status": doc_status,
				"docstatus": d.get("docstatus"),
				"amount": flt(d.get("amount", 0)),
				"doctype": doctype,
			}

	def _resolve(doctype, docname_set):
		if not docname_set:
			return None
		valid_docs = [
			headers_cache[doctype][dn]
			for dn in docname_set
			if dn in headers_cache[doctype]
			and headers_cache[doctype][dn].get("docstatus") != 2
			and str(headers_cache[doctype][dn].get("status") or "").lower() != "cancelled"
		]
		if not valid_docs:
			return None
		valid_docs.sort(key=lambda x: str(x["creation"] or ""), reverse=True)
		latest = valid_docs[0]
		return {
			"name": latest["name"],
			"creation": str(latest["creation"]),
			"status": latest["status"],
			"docstatus": latest["docstatus"],
			"amount": latest["amount"],
			"doctype": doctype,
			"count": len(valid_docs),
		}

	so_docs_result = {}
	item_docs_result = {}

	# Resolve items
	for it in all_so_items:
		so_n = it.sales_order
		soi_n = it.so_item_name
		docs = {}
		for k in LIST_DOC_KEYS:
			dt = DOC_CONFIG[k]["doctype"]
			names = item_docnames_map[(so_n, soi_n)][k]
			resolved = _resolve(dt, names)
			if k == "bom":
				if resolved and resolved.get("docstatus") == 1:
					docs["bom"] = {
						"doctype": "BOM",
						"name": resolved["name"],
						"creation": resolved["creation"],
						"status": "Approved",
						"docstatus": 1,
						"count": 1,
					}
				else:
					docs["bom"] = {
						"doctype": "BOM",
						"name": resolved["name"] if resolved else None,
						"creation": resolved["creation"] if resolved else None,
						"status": "Pending",
						"docstatus": 0,
						"count": 0,
					}
			else:
				docs[k] = resolved

		docs["so"] = {"name": so_n, "doctype": "Sales Order", "status": next((s.status for s in sales_orders_list if s.name == so_n), None), "count": 1}
		item_docs_result[(so_n, soi_n)] = docs

	# Resolve SO header
	for so in sales_orders_list:
		so_n = so.name
		docs = {}
		for k in LIST_DOC_KEYS:
			if k == "bom":
				so_items = items_by_so[so_n]
				all_approved = bool(so_items) and all(
					(item_docs_result.get((so_n, it.so_item_name), {}).get("bom") or {}).get("status") in ("Approved", "Submitted")
					for it in so_items
				)
				bom_names = list(so_docnames_map[so_n]["bom"])
				latest_bom = _resolve("BOM", bom_names)
				docs["bom"] = {
					"doctype": "BOM",
					"name": latest_bom["name"] if latest_bom else None,
					"creation": latest_bom["creation"] if latest_bom else None,
					"status": "Approved" if all_approved else "Pending",
					"docstatus": 1 if all_approved else 0,
					"count": len(so_items),
				}
			else:
				dt = DOC_CONFIG[k]["doctype"]
				docs[k] = _resolve(dt, so_docnames_map[so_n][k])
		docs["so"] = {"name": so_n, "doctype": "Sales Order", "status": so.status, "count": 1}
		so_docs_result[so_n] = docs

	return so_docs_result, item_docs_result


def determine_pending(docs, so_doc=None):
	so_status = so_doc.get("status") if so_doc else (docs.get("so") or {}).get("status")
	if so_status == "Completed":
		return "Completed", None
	if so_status in ("Draft", "Pending Approval", "To Approve", "On Hold", "Stopped", "Cancelled"):
		return "Sales Order", "so"

	# 1. BOM
	bom = docs.get("bom")
	if not bom or bom.get("status") not in ("Approved", "Submitted"):
		return "BOM", "bom"

	# 2. Production Plan
	pp = docs.get("pp")
	if not pp or pp.get("docstatus") == 0 or pp.get("status") in ("Draft", "Pending Approval", "To Approve"):
		return "Production Plan", "pp"

	# 3. Material Request & Downstream Trace
	mr = docs.get("mr")
	po = docs.get("po")
	sco = docs.get("sco")
	pr = docs.get("pr")
	scr = docs.get("scr")
	pi = docs.get("pi")
	dn = docs.get("dn")
	si = docs.get("si")

	if not mr and not po and not sco and not pr and not scr and not pi and not dn and not si:
		return "Material Request", "mr"

	if mr and (mr.get("docstatus") == 0 or mr.get("status") in ("Draft", "Pending Approval", "To Approve")) and not po and not sco and not pr and not scr and not pi and not dn and not si:
		return "Material Request", "mr"

	# 4. Purchase Order
	if not po and not sco and not pr and not scr and not pi and not dn and not si:
		return "Purchase Order", "po"

	if (po and (po.get("docstatus") == 0 or po.get("status") in ("Draft", "Pending Approval", "To Approve"))) and not pr and not scr and not pi and not dn and not si:
		return "Purchase Order", "po"
	if (sco and (sco.get("docstatus") == 0 or sco.get("status") in ("Draft", "Pending Approval", "To Approve"))) and not pr and not scr and not pi and not dn and not si:
		return "Purchase Order", "sco"

	# 5. Purchase Receipt
	if not pr and not scr and not pi and not dn and not si:
		return "Purchase Order", "po"

	if (pr and (pr.get("docstatus") == 0 or pr.get("status") in ("Draft", "Pending Approval", "To Approve"))) and not pi and not dn and not si:
		return "Purchase Receipt", "pr"
	if (scr and (scr.get("docstatus") == 0 or scr.get("status") in ("Draft", "Pending Approval", "To Approve"))) and not pi and not dn and not si:
		return "Purchase Receipt", "scr"

	# 6. Purchase Invoice
	if not pi and not dn and not si:
		return "Purchase Receipt", "pr"

	if pi and (pi.get("docstatus") == 0 or pi.get("status") in ("Draft", "Pending Approval", "To Approve")):
		if not dn and not si:
			return "Purchase Invoice", "pi"

	# 7. Delivery Note
	per_delivered = flt(so_doc.get("per_delivered") if so_doc else 0)
	if not dn or per_delivered < 100 or dn.get("docstatus") == 0 or dn.get("status") in ("Draft", "Pending Approval", "To Approve"):
		return "Delivery Note", "dn"

	# 8. Sales Invoice
	per_billed = flt(so_doc.get("per_billed") if so_doc else 0)
	if not si or per_billed < 100 or si.get("docstatus") == 0 or si.get("status") in ("Draft", "Pending Approval", "To Approve"):
		return "Sales Invoice", "si"

	return "Completed", None


def determine_item_pending(docs, item_data=None, so_status=None):
	if so_status == "Completed":
		return "Completed", None
	if so_status in ("Draft", "Pending Approval", "To Approve", "On Hold", "Stopped", "Cancelled"):
		return "Sales Order", "so"

	# 1. BOM
	bom = docs.get("bom")
	if not bom or bom.get("status") not in ("Approved", "Submitted"):
		return "BOM", "bom"

	# 2. Production Plan
	pp = docs.get("pp")
	if not pp or pp.get("docstatus") == 0 or pp.get("status") in ("Draft", "Pending Approval", "To Approve"):
		return "Production Plan", "pp"

	# 3. Material Request & Downstream Trace
	mr = docs.get("mr")
	po = docs.get("po")
	sco = docs.get("sco")
	pr = docs.get("pr")
	scr = docs.get("scr")
	pi = docs.get("pi")
	dn = docs.get("dn")
	si = docs.get("si")

	if not mr and not po and not sco and not pr and not scr and not pi and not dn and not si:
		return "Material Request", "mr"

	if mr and (mr.get("docstatus") == 0 or mr.get("status") in ("Draft", "Pending Approval", "To Approve")) and not po and not sco and not pr and not scr and not pi and not dn and not si:
		return "Material Request", "mr"

	# 4. Purchase Order
	if not po and not sco and not pr and not scr and not pi and not dn and not si:
		return "Purchase Order", "po"

	if (po and (po.get("docstatus") == 0 or po.get("status") in ("Draft", "Pending Approval", "To Approve"))) and not pr and not scr and not pi and not dn and not si:
		return "Purchase Order", "po"
	if (sco and (sco.get("docstatus") == 0 or sco.get("status") in ("Draft", "Pending Approval", "To Approve"))) and not pr and not scr and not pi and not dn and not si:
		return "Purchase Order", "sco"

	# 5. Purchase Receipt
	if not pr and not scr and not pi and not dn and not si:
		return "Purchase Order", "po"

	if (pr and (pr.get("docstatus") == 0 or pr.get("status") in ("Draft", "Pending Approval", "To Approve"))) and not pi and not dn and not si:
		return "Purchase Receipt", "pr"
	if (scr and (scr.get("docstatus") == 0 or scr.get("status") in ("Draft", "Pending Approval", "To Approve"))) and not pi and not dn and not si:
		return "Purchase Receipt", "scr"

	# 6. Purchase Invoice
	if not pi and not dn and not si:
		return "Purchase Receipt", "pr"

	if pi and (pi.get("docstatus") == 0 or pi.get("status") in ("Draft", "Pending Approval", "To Approve")):
		if not dn and not si:
			return "Purchase Invoice", "pi"

	# 7. Delivery Note
	qty = flt((item_data or {}).get("qty", 0))
	delivered_qty = flt((item_data or {}).get("delivered_qty", 0))
	if not dn or (qty > 0 and delivered_qty < qty) or dn.get("docstatus") == 0 or dn.get("status") in ("Draft", "Pending Approval", "To Approve"):
		return "Delivery Note", "dn"

	# 8. Sales Invoice
	if not si or si.get("docstatus") == 0 or si.get("status") in ("Draft", "Pending Approval", "To Approve"):
		return "Sales Invoice", "si"

	return "Completed", None



def determine_priority(so_data):
	"""Priority derived from Sales Order delivery date and fulfillment status."""
	if not so_data:
		return None

	status = so_data.get("status")
	if status == "Closed":
		return "Closed"
	if flt(so_data.get("per_delivered")) >= 100 or status == "Completed":
		return "Low"

	delivery_date = so_data.get("delivery_date")
	if not delivery_date:
		return None

	diff = date_diff(delivery_date, today())
	if diff > 60:
		return "Low"
	if diff > 30:
		return "Medium"
	if diff > 15:
		return "High"
	if diff >= 1:
		return "Urgent"

	return f"Overdue ({abs(diff)}d)"


def determine_item_priority(item_data, so_status=None):
	if not item_data:
		return None
	if so_status == "Closed":
		return "Closed"
	qty = flt(item_data.get("qty"))
	delivered = flt(item_data.get("delivered_qty"))
	if qty > 0 and delivered >= qty:
		return "Low"

	delivery_date = item_data.get("delivery_date")
	if not delivery_date:
		return None

	diff = date_diff(delivery_date, today())
	if diff > 60:
		return "Low"
	if diff > 30:
		return "Medium"
	if diff > 15:
		return "High"
	if diff >= 1:
		return "Urgent"

	return f"Overdue ({abs(diff)}d)"


# ---------------------------------------------------------------------------
# Detail view (Tab 2 — Detailed View)
# Driven primarily by Sales Order and Batch
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_sales_order_detail(sales_order=None, project=None, branch=None, batch_no=None):
	"""Returns complete Sales Order details, BOM items & consumption, and linked documents."""
	check_detail_view_permission(throw=True)
	so_name = sales_order
	if not so_name and project:
		so_name = frappe.db.get_value("Sales Order", {"project": project, "docstatus": ["!=", 2]}, "name")

	if not so_name:
		frappe.throw(_("Sales Order is required."))

	batch_no = (batch_no or "").strip()
	so = frappe.get_doc("Sales Order", so_name)
	so_project = so.get("project") if so.meta.has_field("project") else None
	so_branch = so.get("branch") if so.meta.has_field("branch") else None
	active_branch = branch or so_branch

	if batch_no:
		docs = get_docs_for_so_item(so.name, batch_no=batch_no, project=so_project, branch=active_branch)
	else:
		docs = get_docs_for_sales_order(so.name, project=so_project, branch=active_branch)

	docs["so"] = {
		"name": so.name,
		"doctype": "Sales Order",
		"status": so.status,
		"count": 1,
	}

	return {
		"sales_order": so.name,
		"so": so.name,
		"batch_no": batch_no or None,
		"project": so_project,
		"project_name": so_project,
		"branch": so_branch,
		"customer": so.customer,
		"customer_name": so.get("customer_name"),
		"date": str(so.transaction_date) if so.transaction_date else str(getdate(so.creation)),
		"delivery_date": str(so.delivery_date) if so.delivery_date else None,
		"status": so.status,
		"overview": compute_overview(sales_order=so.name, project=so_project, batch_no=batch_no),
		"items": get_items_and_consumption(sales_order=so.name, project=so_project, branch=active_branch, batch_no=batch_no),
		"docs": docs,
		"doc_meta": {
			k: {
				"label": cfg["label"],
				"short": cfg["short"],
				"doctype": cfg["doctype"],
				"queryable": is_doc_type_queryable(cfg, k),
			}
			for k, cfg in DOC_CONFIG.items()
		},
		"doc_order": DOC_ORDER,
	}


@frappe.whitelist()
def get_ao_detail(*args, **kwargs):
	"""Backward compatibility wrapper for get_sales_order_detail."""
	return get_sales_order_detail(*args, **kwargs)


def is_doc_type_queryable(cfg, key=None):
	if not doctype_installed(cfg["doctype"]):
		return False
	if cfg["doctype"] == "Journal Entry":
		return doctype_installed("Journal Entry Account")
	if key == "quote":
		return doctype_installed("Quotation")
	return True


# ---------------------------------------------------------------------------
# Linked Document Queries for Sales Order & Item/Batch
# ---------------------------------------------------------------------------

def get_docs_for_sales_order(sales_order, project=None, branch=None):
	return {key: get_latest_doc_for_so(sales_order, key, cfg, project=project, branch=branch) for key, cfg in DOC_CONFIG.items()}


def get_latest_doc_for_so(sales_order, key, cfg, project=None, branch=None):
	doctype = cfg["doctype"]
	if not is_doc_type_queryable(cfg, key):
		return None

	names = get_doc_names_for_so(sales_order, key, cfg, project=project, branch=branch)
	if not names:
		return None

	status_field = resolve_status_field(doctype, cfg)
	fields = ["name", "creation", "docstatus"]
	if status_field:
		fields.append(f"{status_field} as status")
	if cfg.get("amount_field") and field_exists(doctype, cfg["amount_field"]):
		fields.append(f"{cfg['amount_field']} as amount")

	rows = frappe.get_all(doctype, filters={"name": ["in", names]}, fields=fields, order_by="creation desc", limit_page_length=1)
	if not rows:
		return None

	doc = rows[0]
	if key == "bom":
		doc["status"] = "Approved" if doc.get("docstatus") == 1 else "Pending"
	elif not status_field:
		if doctype == "Journal Entry":
			doc["status"] = "Submitted" if doc.get("docstatus") == 1 else "Draft"
		else:
			doc["status"] = None
	doc["doctype"] = doctype
	doc["count"] = len(names)
	return doc


def get_doc_names_for_so(sales_order, key, cfg, project=None, branch=None):
	doctype = cfg["doctype"]
	if not doctype_installed(doctype):
		return []

	names = set()

	if key == "quote":
		# Quotation linked via Sales Order Items (prevdoc_docname) or Sales Order.quotation_no
		if doctype_installed("Sales Order Item") and field_exists("Sales Order Item", "prevdoc_docname"):
			q_names = frappe.get_all("Sales Order Item", filters={"parent": sales_order, "prevdoc_docname": ["is", "set"]}, pluck="prevdoc_docname")
			names.update(q_names)
		if field_exists("Sales Order", "quotation_no"):
			q_no = frappe.db.get_value("Sales Order", sales_order, "quotation_no")
			if q_no:
				names.add(q_no)
		return list(names)

	if key == "so":
		return [sales_order] if frappe.db.exists("Sales Order", sales_order) else []

	if key == "bom":
		if doctype_installed("Sales Order Item") and sales_order:
			so_items = frappe.get_all("Sales Order Item", filters={"parent": sales_order, "docstatus": ["!=", 2]}, fields=["item_code", "bom_no"])
			fg_items = list(set([d.item_code for d in so_items if d.item_code]))
			if fg_items:
				if field_exists("BOM", "sales_order"):
					b_names = frappe.get_all("BOM", filters={"sales_order": sales_order, "item": ["in", fg_items], "docstatus": ["!=", 2]}, pluck="name")
					names.update(b_names)
				b_soi = [d.bom_no for d in so_items if d.bom_no]
				if b_soi:
					b_valid = frappe.get_all("BOM", filters={"name": ["in", b_soi], "item": ["in", fg_items], "docstatus": ["!=", 2]}, pluck="name")
					names.update(b_valid)
				if not names:
					b_defs = frappe.get_all("BOM", filters={"item": ["in", fg_items], "is_default": 1, "is_active": 1, "docstatus": 1}, pluck="name")
					names.update(b_defs)
		return list(names)

	if key == "pp":
		if doctype_installed("Production Plan Item") and sales_order:
			pp_names = frappe.get_all("Production Plan Item", filters={"sales_order": sales_order, "docstatus": ["!=", 2]}, pluck="parent")
			names.update(pp_names)
		if doctype_installed("Production Plan Sales Order") and sales_order:
			pp_so = frappe.get_all("Production Plan Sales Order", filters={"sales_order": sales_order, "docstatus": ["!=", 2]}, pluck="parent")
			names.update(pp_so)
		return list(names)

	if key == "mr":
		# Production Plan -> Material Request
		pp_names = get_doc_names_for_so(sales_order, "pp", DOC_CONFIG.get("pp", {"doctype": "Production Plan"}), project=project, branch=branch)
		if pp_names:
			if doctype_installed("Material Request Item") and field_exists("Material Request Item", "production_plan"):
				mr_pp = frappe.get_all("Material Request Item", filters={"production_plan": ["in", pp_names], "docstatus": ["!=", 2]}, pluck="parent")
				names.update(mr_pp)
			if doctype_installed("Production Plan Material Request"):
				ppmr = frappe.get_all("Production Plan Material Request", filters={"parent": ["in", pp_names], "material_request": ["is", "set"], "docstatus": ["!=", 2]}, pluck="material_request")
				names.update(ppmr)

	if key == "po":
		# Material Request -> Purchase Order
		mr_names = get_doc_names_for_so(sales_order, "mr", DOC_CONFIG.get("mr", {"doctype": "Material Request"}), project=project, branch=branch)
		if mr_names and doctype_installed("Purchase Order Item") and field_exists("Purchase Order Item", "material_request"):
			po_mr = frappe.get_all("Purchase Order Item", filters={"material_request": ["in", mr_names], "docstatus": ["!=", 2]}, pluck="parent")
			names.update(po_mr)

	# Direct child item link to Sales Order (e.g. against_sales_order / sales_order)
	item_doctype = cfg.get("item_doctype")
	item_so_field = cfg.get("item_so_field")
	if item_doctype and item_so_field and doctype_installed(item_doctype) and field_exists(item_doctype, item_so_field):
		child_names = frappe.get_all(
			item_doctype,
			filters={item_so_field: sales_order, "docstatus": ["!=", 2]},
			pluck="parent",
		)
		names.update(child_names)

	# Direct header link to Sales Order
	if field_exists(doctype, "sales_order"):
		header_names = frappe.get_all(
			doctype,
			filters={"sales_order": sales_order, "docstatus": ["!=", 2]},
			pluck="name",
		)
		names.update(header_names)

	# Fallback / additional query via linked Project
	if project and field_exists(doctype, "project"):
		proj_filters = {"project": project, "docstatus": ["!=", 2]}
		proj_filters.update(cfg.get("extra_filters") or {})
		proj_names = frappe.get_all(doctype, filters=proj_filters, pluck="name")
		names.update(proj_names)

	# Purchase Orders linked to this Sales Order -> Purchase Receipts / Invoices
	if doctype in ("Purchase Receipt", "Purchase Invoice") and sales_order:
		po_names = get_doc_names_for_so(sales_order, "po", DOC_CONFIG.get("po", {"doctype": "Purchase Order"}), project=project, branch=branch)
		if po_names:
			if doctype == "Purchase Receipt" and doctype_installed("Purchase Receipt Item") and field_exists("Purchase Receipt Item", "purchase_order"):
				pr_from_po = frappe.get_all(
					"Purchase Receipt Item",
					filters={"purchase_order": ["in", po_names], "docstatus": ["!=", 2]},
					pluck="parent",
				)
				names.update(pr_from_po)
			elif doctype == "Purchase Invoice" and doctype_installed("Purchase Invoice Item") and field_exists("Purchase Invoice Item", "purchase_order"):
				pi_from_po = frappe.get_all(
					"Purchase Invoice Item",
					filters={"purchase_order": ["in", po_names], "docstatus": ["!=", 2]},
					pluck="parent",
				)
				names.update(pi_from_po)

	# Journal Entry Account link
	if doctype == "Journal Entry" and doctype_installed("Journal Entry Account"):
		je_params = [sales_order]
		je_cond = "jea.reference_name = %s"
		if project:
			je_cond += " or jea.project = %s"
			je_params.append(project)

		je_rows = frappe.db.sql(
			f"""
			select distinct je.name
			from `tabJournal Entry` je
			inner join `tabJournal Entry Account` jea on jea.parent = je.name
			where ({je_cond}) and je.docstatus != 2
			""",
			tuple(je_params),
			pluck=True,
		)
		names.update(je_rows)

	# Payment Entry references
	if key == "pe_out":
		po_names = get_doc_names_for_so(sales_order, "po", DOC_CONFIG.get("po", {"doctype": "Purchase Order"}), project=project, branch=branch)
		pi_names = get_doc_names_for_so(sales_order, "pi", DOC_CONFIG.get("pi", {"doctype": "Purchase Invoice"}), project=project, branch=branch)
		pe_conds = ["pe.payment_type in ('Pay', 'Internal Transfer')", "pe.docstatus != 2"]
		pe_refs = []
		pe_vals = {}
		if pi_names:
			pe_refs.append("(per.reference_doctype = 'Purchase Invoice' and per.reference_name in %(pi_names)s)")
			pe_vals["pi_names"] = tuple(pi_names)
		if po_names:
			pe_refs.append("(per.reference_doctype = 'Purchase Order' and per.reference_name in %(po_names)s)")
			pe_vals["po_names"] = tuple(po_names)
		if sales_order:
			pe_refs.append("(per.reference_doctype = 'Sales Order' and per.reference_name = %(so)s)")
			pe_vals["so"] = sales_order
		if pe_refs:
			pe_conds.append(f"({' or '.join(pe_refs)})")
			pe_rows = frappe.db.sql(
				f"""
				select distinct per.parent
				from `tabPayment Entry Reference` per
				inner join `tabPayment Entry` pe on pe.name = per.parent
				where {' and '.join(pe_conds)}
				""",
				pe_vals,
				pluck=True,
			)
			names.update(pe_rows)
		return list(names)

	if key == "pe_in":
		si_names = get_doc_names_for_so(sales_order, "si", DOC_CONFIG.get("si", {"doctype": "Sales Invoice"}), project=project, branch=branch)
		pe_conds = ["pe.payment_type in ('Receive', 'Internal Transfer')", "pe.docstatus != 2"]
		pe_refs = []
		pe_vals = {}
		if si_names:
			pe_refs.append("(per.reference_doctype = 'Sales Invoice' and per.reference_name in %(si_names)s)")
			pe_vals["si_names"] = tuple(si_names)
		if sales_order:
			pe_refs.append("(per.reference_doctype = 'Sales Order' and per.reference_name = %(so)s)")
			pe_vals["so"] = sales_order
		if pe_refs:
			pe_conds.append(f"({' or '.join(pe_refs)})")
			pe_rows = frappe.db.sql(
				f"""
				select distinct per.parent
				from `tabPayment Entry Reference` per
				inner join `tabPayment Entry` pe on pe.name = per.parent
				where {' and '.join(pe_conds)}
				""",
				pe_vals,
				pluck=True,
			)
			names.update(pe_rows)
		return list(names)

	if doctype == "Payment Entry" and doctype_installed("Payment Entry Reference"):
		pe_rows = frappe.db.sql(
			"""
			select distinct per.parent
			from `tabPayment Entry Reference` per
			inner join `tabPayment Entry` pe on pe.name = per.parent
			where per.reference_name = %s and pe.docstatus != 2
			""",
			sales_order,
			pluck=True,
		)
		names.update(pe_rows)

	# Apply branch filtering if doc supports branch
	if branch and names and field_exists(doctype, "branch"):
		valid_names = set(frappe.get_all(doctype, filters={"name": ["in", list(names)], "branch": branch}, pluck="name"))
		names = valid_names or names

	return list(names)


# ---------------------------------------------------------------------------
# Item & Batch specific Document Resolution
# ---------------------------------------------------------------------------

def get_docs_for_so_item(sales_order, so_item_name=None, item_code=None, batch_no=None, project=None, branch=None):
	return {
		key: get_latest_doc_for_so_item(
			sales_order, key, cfg,
			so_item_name=so_item_name,
			item_code=item_code,
			batch_no=batch_no,
			project=project,
			branch=branch,
		)
		for key, cfg in DOC_CONFIG.items()
	}


def get_latest_doc_for_so_item(sales_order, key, cfg, so_item_name=None, item_code=None, batch_no=None, project=None, branch=None):
	doctype = cfg["doctype"]
	if not is_doc_type_queryable(cfg, key):
		return None

	names = get_doc_names_for_so_item(
		sales_order, key, cfg,
		so_item_name=so_item_name,
		item_code=item_code,
		batch_no=batch_no,
		project=project,
		branch=branch,
	)
	if not names:
		return None

	status_field = resolve_status_field(doctype, cfg)
	fields = ["name", "creation", "docstatus"]
	if status_field:
		fields.append(f"{status_field} as status")
	if cfg.get("amount_field") and field_exists(doctype, cfg["amount_field"]):
		fields.append(f"{cfg['amount_field']} as amount")

	rows = frappe.get_all(doctype, filters={"name": ["in", names]}, fields=fields, order_by="creation desc", limit_page_length=1)
	if not rows:
		return None

	doc = rows[0]
	if key == "bom":
		doc["status"] = "Approved" if doc.get("docstatus") == 1 else "Pending"
	elif not status_field:
		if doctype == "Journal Entry":
			doc["status"] = "Submitted" if doc.get("docstatus") == 1 else "Draft"
		else:
			doc["status"] = None
	doc["doctype"] = doctype
	doc["count"] = len(names)
	return doc


def get_doc_names_for_so_item(sales_order, key, cfg, so_item_name=None, item_code=None, batch_no=None, project=None, branch=None):
	doctype = cfg["doctype"]
	if not doctype_installed(doctype):
		return []

	names = set()
	batch_no = (batch_no or "").strip()

	# Resolve matching Sales Order Item row names when batch_no is provided
	matching_soi_names = []
	if sales_order and (batch_no or so_item_name):
		if so_item_name:
			matching_soi_names = [so_item_name]
		elif batch_no:
			has_b = field_exists("Sales Order Item", "batch_no")
			has_cb = field_exists("Sales Order Item", "custom_batch_no")
			soi_b_clauses = []
			if has_b:
				soi_b_clauses.append("soi.batch_no like %(batch_no)s")
			if has_cb:
				soi_b_clauses.append("soi.custom_batch_no like %(batch_no)s")
			if soi_b_clauses:
				matching_soi_names = frappe.db.sql(
					f"""
					select soi.name
					from `tabSales Order Item` soi
					where soi.parent = %(so)s and soi.docstatus != 2 and ({' or '.join(soi_b_clauses)})
					""",
					{"so": sales_order, "batch_no": f"%{batch_no}%"},
					pluck=True,
				)

	if key == "quote":
		if doctype_installed("Sales Order Item") and field_exists("Sales Order Item", "prevdoc_docname"):
			if matching_soi_names:
				q_names = frappe.get_all("Sales Order Item", filters={"name": ["in", matching_soi_names], "prevdoc_docname": ["is", "set"]}, pluck="prevdoc_docname")
				names.update(q_names)
			elif so_item_name:
				q_name = frappe.db.get_value("Sales Order Item", so_item_name, "prevdoc_docname")
				if q_name:
					names.add(q_name)
		if not names and field_exists("Sales Order", "quotation_no") and sales_order and not batch_no:
			q_no = frappe.db.get_value("Sales Order", sales_order, "quotation_no")
			if q_no:
				names.add(q_no)
		return list(names)

	if key == "so":
		return [sales_order] if sales_order and frappe.db.exists("Sales Order", sales_order) else []

	if key == "bom":
		target_items = []
		if item_code:
			target_items = [item_code]
		elif so_item_name:
			ic = frappe.db.get_value("Sales Order Item", so_item_name, "item_code")
			if ic:
				target_items = [ic]
		elif matching_soi_names:
			target_items = frappe.get_all("Sales Order Item", filters={"name": ["in", matching_soi_names], "docstatus": ["!=", 2]}, pluck="item_code")
		elif sales_order:
			target_items = frappe.get_all("Sales Order Item", filters={"parent": sales_order, "docstatus": ["!=", 2]}, pluck="item_code")

		target_items = list(set([t for t in target_items if t]))

		if sales_order and target_items:
			if batch_no and field_exists("BOM", "custom_batch_no") and field_exists("BOM", "sales_order"):
				b_names = frappe.get_all("BOM", filters={"sales_order": sales_order, "item": ["in", target_items], "custom_batch_no": ["like", f"%{batch_no}%"], "docstatus": ["!=", 2]}, pluck="name")
				names.update(b_names)
			if so_item_name and not names:
				b_no = frappe.db.get_value("Sales Order Item", so_item_name, "bom_no")
				if b_no:
					b_item = frappe.db.get_value("BOM", b_no, "item")
					if b_item in target_items:
						names.add(b_no)
			if matching_soi_names and not names:
				b_sois = frappe.get_all("Sales Order Item", filters={"name": ["in", matching_soi_names], "bom_no": ["is", "set"], "docstatus": ["!=", 2]}, pluck="bom_no")
				if b_sois:
					b_valid = frappe.get_all("BOM", filters={"name": ["in", b_sois], "item": ["in", target_items], "docstatus": ["!=", 2]}, pluck="name")
					names.update(b_valid)
			if not names and field_exists("BOM", "sales_order"):
				b_so = frappe.get_all("BOM", filters={"sales_order": sales_order, "item": ["in", target_items], "docstatus": ["!=", 2]}, pluck="name")
				names.update(b_so)
			if not names:
				b_defs = frappe.get_all("BOM", filters={"item": ["in", target_items], "is_default": 1, "docstatus": 1, "is_active": 1}, pluck="name")
				names.update(b_defs)
		elif target_items and not names:
			b_defs = frappe.get_all("BOM", filters={"item": ["in", target_items], "is_default": 1, "docstatus": 1, "is_active": 1}, pluck="name")
			names.update(b_defs)
		return list(names)

	if key == "pp":
		pp_conds = ["docstatus != 2"]
		pp_vals = {}
		if sales_order:
			pp_conds.append("sales_order = %(so)s")
			pp_vals["so"] = sales_order
		if batch_no:
			pp_conds.append("custom_batch_no like %(batch_no)s")
			pp_vals["batch_no"] = f"%{batch_no}%"
		elif so_item_name:
			pp_conds.append("sales_order_item = %(soi)s")
			pp_vals["soi"] = so_item_name
		elif matching_soi_names:
			pp_conds.append("sales_order_item in %(matching_soi_names)s")
			pp_vals["matching_soi_names"] = tuple(matching_soi_names)
		if item_code:
			pp_conds.append("item_code = %(ic)s")
			pp_vals["ic"] = item_code
		pp_parents = frappe.db.sql(
			f"select distinct parent from `tabProduction Plan Item` where {' and '.join(pp_conds)}",
			pp_vals,
			pluck=True,
		)
		names.update(pp_parents)
		return list(names)

	if key == "mr":
		# Production Plan -> Material Request
		pp_names = get_doc_names_for_so_item(
			sales_order, "pp", DOC_CONFIG.get("pp", {"doctype": "Production Plan"}),
			so_item_name=so_item_name, item_code=item_code, batch_no=batch_no,
			project=project, branch=branch
		)
		if pp_names:
			if doctype_installed("Material Request Item") and field_exists("Material Request Item", "production_plan"):
				mr_pp = frappe.get_all("Material Request Item", filters={"production_plan": ["in", pp_names], "docstatus": ["!=", 2]}, pluck="parent")
				names.update(mr_pp)
			if doctype_installed("Production Plan Material Request"):
				ppmr = frappe.get_all("Production Plan Material Request", filters={"parent": ["in", pp_names], "material_request": ["is", "set"], "docstatus": ["!=", 2]}, pluck="material_request")
				names.update(ppmr)

	if key == "po":
		# Material Request -> Purchase Order
		mr_names = get_doc_names_for_so_item(
			sales_order, "mr", DOC_CONFIG.get("mr", {"doctype": "Material Request"}),
			so_item_name=so_item_name, item_code=item_code, batch_no=batch_no,
			project=project, branch=branch
		)
		if mr_names and doctype_installed("Purchase Order Item") and field_exists("Purchase Order Item", "material_request"):
			po_mr = frappe.get_all("Purchase Order Item", filters={"material_request": ["in", mr_names], "docstatus": ["!=", 2]}, pluck="parent")
			names.update(po_mr)

	if key == "pe_out":
		po_names = get_doc_names_for_so_item(
			sales_order, "po", DOC_CONFIG.get("po", {"doctype": "Purchase Order"}),
			so_item_name=so_item_name, item_code=item_code, batch_no=batch_no,
			project=project, branch=branch
		)
		pi_names = get_doc_names_for_so_item(
			sales_order, "pi", DOC_CONFIG.get("pi", {"doctype": "Purchase Invoice"}),
			so_item_name=so_item_name, item_code=item_code, batch_no=batch_no,
			project=project, branch=branch
		)
		pe_conds = ["pe.payment_type in ('Pay', 'Internal Transfer')", "pe.docstatus != 2"]
		pe_refs = []
		pe_vals = {}
		if pi_names:
			pe_refs.append("(per.reference_doctype = 'Purchase Invoice' and per.reference_name in %(pi_names)s)")
			pe_vals["pi_names"] = tuple(pi_names)
		if po_names:
			pe_refs.append("(per.reference_doctype = 'Purchase Order' and per.reference_name in %(po_names)s)")
			pe_vals["po_names"] = tuple(po_names)
		if pe_refs:
			pe_conds.append(f"({' or '.join(pe_refs)})")
			pe_rows = frappe.db.sql(
				f"""
				select distinct per.parent
				from `tabPayment Entry Reference` per
				inner join `tabPayment Entry` pe on pe.name = per.parent
				where {' and '.join(pe_conds)}
				""",
				pe_vals,
				pluck=True,
			)
			names.update(pe_rows)
		return list(names)

	if key == "pe_in":
		si_names = get_doc_names_for_so_item(
			sales_order, "si", DOC_CONFIG.get("si", {"doctype": "Sales Invoice"}),
			so_item_name=so_item_name, item_code=item_code, batch_no=batch_no,
			project=project, branch=branch
		)
		pe_conds = ["pe.payment_type in ('Receive', 'Internal Transfer')", "pe.docstatus != 2"]
		pe_refs = []
		pe_vals = {}
		if si_names:
			pe_refs.append("(per.reference_doctype = 'Sales Invoice' and per.reference_name in %(si_names)s)")
			pe_vals["si_names"] = tuple(si_names)
		if sales_order:
			pe_refs.append("(per.reference_doctype = 'Sales Order' and per.reference_name = %(so)s)")
			pe_vals["so"] = sales_order
		if pe_refs:
			pe_conds.append(f"({' or '.join(pe_refs)})")
			pe_rows = frappe.db.sql(
				f"""
				select distinct per.parent
				from `tabPayment Entry Reference` per
				inner join `tabPayment Entry` pe on pe.name = per.parent
				where {' and '.join(pe_conds)}
				""",
				pe_vals,
				pluck=True,
			)
			names.update(pe_rows)
		return list(names)

	item_doctype = cfg.get("item_doctype")
	item_so_field = cfg.get("item_so_field")

	if item_doctype and doctype_installed(item_doctype):
		conditions = []
		values = {"so": sales_order}

		if item_so_field and field_exists(item_doctype, item_so_field) and sales_order:
			# Match via linked Sales Order Item IDs (sales_order_item or so_detail)
			soi_link_fields = [f for f in ["sales_order_item", "so_detail"] if field_exists(item_doctype, f)]
			if matching_soi_names and soi_link_fields:
				or_soi = " or ".join([f"cdt.{f} in %(matching_soi_names)s" for f in soi_link_fields])
				conditions.append(f"(cdt.{item_so_field} = %(so)s and ({or_soi}))")
				values["matching_soi_names"] = tuple(matching_soi_names)

			# Direct Batch match on child doc
			batch_fields = [f for f in ["batch_no", "custom_batch_no"] if field_exists(item_doctype, f)]
			if batch_no and batch_fields:
				or_b = " or ".join([f"cdt.{f} like %(batch_no)s" for f in batch_fields])
				conditions.append(f"(cdt.{item_so_field} = %(so)s and ({or_b}))")
				values["batch_no"] = f"%{batch_no}%"

			# Direct Item Code match under this Sales Order (for direct FG sales docs DN / SI)
			if item_code and field_exists(item_doctype, "item_code") and doctype in ("Delivery Note", "Sales Invoice", "Sales Order"):
				conditions.append(f"(cdt.{item_so_field} = %(so)s and cdt.item_code = %(item_code)s)")
				values["item_code"] = item_code

		if conditions:
			where_sql = " or ".join(conditions)
			found_parents = frappe.db.sql(
				f"""
				select distinct cdt.parent
				from `tab{item_doctype}` cdt
				where ({where_sql}) and cdt.docstatus != 2
				""",
				values,
				pluck=True,
			)
			names.update(found_parents)

	# Direct Stock Entry batch link
	if doctype == "Stock Entry" and doctype_installed("Stock Entry Detail") and batch_no:
		se_b_fields = [f for f in ["batch_no", "custom_batch_no"] if field_exists("Stock Entry Detail", f)]
		if se_b_fields:
			se_or_b = " or ".join([f"sed.{f} like %(batch_no)s" for f in se_b_fields])
			se_parents = frappe.db.sql(
				f"""
				select distinct sed.parent
				from `tabStock Entry Detail` sed
				inner join `tabStock Entry` se on se.name = sed.parent
				where ({se_or_b}) and se.docstatus != 2
				""",
				{"batch_no": f"%{batch_no}%"},
				pluck=True,
			)
			names.update(se_parents)

	# Linked PR / PI via Purchase Order for this item / batch
	if doctype in ("Purchase Receipt", "Purchase Invoice") and sales_order:
		po_names = get_doc_names_for_so_item(
			sales_order, "po", DOC_CONFIG.get("po", {"doctype": "Purchase Order"}),
			so_item_name=so_item_name, item_code=item_code, batch_no=batch_no,
			project=project, branch=branch
		)
		if po_names:
			if doctype == "Purchase Receipt" and doctype_installed("Purchase Receipt Item") and field_exists("Purchase Receipt Item", "purchase_order"):
				pr_rows = frappe.get_all(
					"Purchase Receipt Item",
					filters={"purchase_order": ["in", po_names], "docstatus": ["!=", 2]},
					pluck="parent"
				)
				names.update(pr_rows)
			elif doctype == "Purchase Invoice" and doctype_installed("Purchase Invoice Item") and field_exists("Purchase Invoice Item", "purchase_order"):
				pi_rows = frappe.get_all(
					"Purchase Invoice Item",
					filters={"purchase_order": ["in", po_names], "docstatus": ["!=", 2]},
					pluck="parent"
				)
				names.update(pi_rows)

	# If branch filtering applies
	if branch and names and field_exists(doctype, "branch"):
		valid_names = set(frappe.get_all(doctype, filters={"name": ["in", list(names)], "branch": branch}, pluck="name"))
		names = valid_names or names

	return list(names)


@frappe.whitelist()
def get_doc_list(project=None, sales_order=None, key=None, branch=None, so_item_name=None, item_code=None, batch_no=None):
	"""Returns all documents of type `key` linked to the Sales Order / Item / Batch / Project."""
	if not key:
		return []

	cfg = DOC_CONFIG.get(key)
	if not cfg:
		return []

	doctype = cfg["doctype"]
	if not doctype_installed(doctype):
		return []

	so_name = sales_order
	if not so_name and project:
		so_name = frappe.db.get_value("Sales Order", {"project": project, "docstatus": ["!=", 2]}, "name")

	if so_item_name or batch_no or (item_code and so_name):
		names = get_doc_names_for_so_item(
			so_name, key, cfg,
			so_item_name=so_item_name,
			item_code=item_code,
			batch_no=batch_no,
			project=project,
			branch=branch
		)
	else:
		names = get_doc_names_for_so(so_name, key, cfg, project=project, branch=branch)

	if not names:
		return []

	fields = ["name", "docstatus"]
	if cfg.get("status_field") and field_exists(doctype, cfg["status_field"]):
		fields.append(cfg["status_field"])
	if cfg.get("amount_field") and field_exists(doctype, cfg["amount_field"]):
		fields.append(cfg["amount_field"])
	for extra in ("posting_date", "transaction_date", "creation", "supplier", "customer"):
		if field_exists(doctype, extra):
			fields.append(extra)

	filters = {"name": ["in", names], "docstatus": ["!=", 2]}
	if branch and field_exists(doctype, "branch"):
		filters["branch"] = branch

	rows = frappe.get_all(doctype, filters=filters, fields=list(set(fields)), order_by="creation desc")
	status_field = cfg.get("status_field")
	for r in rows:
		r["doctype"] = doctype
		if status_field and r.get(status_field):
			r["status"] = r[status_field]
		elif "docstatus" in r:
			r["status"] = "Submitted" if r["docstatus"] == 1 else "Draft"
		else:
			r["status"] = None
	return rows


# ---------------------------------------------------------------------------
# Overview KPI Calculations (Sales Order Centric)
# ---------------------------------------------------------------------------

def compute_overview(sales_order=None, project=None, batch_no=None):
	if not sales_order and project:
		sales_order = frappe.db.get_value("Sales Order", {"project": project, "docstatus": ["!=", 2]}, "name")

	revenue = 0.0
	batch_no = (batch_no or "").strip()

	matching_soi_names = []
	if sales_order and batch_no:
		has_b = field_exists("Sales Order Item", "batch_no")
		has_cb = field_exists("Sales Order Item", "custom_batch_no")
		soi_b_clauses = []
		if has_b:
			soi_b_clauses.append("soi.batch_no like %(batch_no)s")
		if has_cb:
			soi_b_clauses.append("soi.custom_batch_no like %(batch_no)s")
		if soi_b_clauses:
			matching_soi_names = frappe.db.sql(
				f"""
				select soi.name
				from `tabSales Order Item` soi
				where soi.parent = %(so)s and soi.docstatus != 2 and ({' or '.join(soi_b_clauses)})
				""",
				{"so": sales_order, "batch_no": f"%{batch_no}%"},
				pluck=True,
			)

	if sales_order:
		if batch_no:
			has_b = field_exists("Sales Invoice Item", "batch_no")
			has_cb = field_exists("Sales Invoice Item", "custom_batch_no")
			has_sod = field_exists("Sales Invoice Item", "so_detail")
			si_b_clauses = []
			si_vals = {"sales_order": sales_order, "batch_no": f"%{batch_no}%"}
			if has_b:
				si_b_clauses.append("sii.batch_no like %(batch_no)s")
			if has_cb:
				si_b_clauses.append("sii.custom_batch_no like %(batch_no)s")
			if has_sod and matching_soi_names:
				si_b_clauses.append("sii.so_detail in %(matching_soi_names)s")
				si_vals["matching_soi_names"] = tuple(matching_soi_names)

			invoiced_rev = 0.0
			if si_b_clauses:
				invoiced_rev = flt(frappe.db.sql(
					f"""
					select sum(sii.net_amount)
					from `tabSales Invoice Item` sii
					inner join `tabSales Invoice` si on si.name = sii.parent
					where sii.sales_order = %(sales_order)s and si.docstatus = 1
						and ({' or '.join(si_b_clauses)})
					""",
					si_vals,
				)[0][0] or 0)

			if invoiced_rev > 0:
				revenue = invoiced_rev
			else:
				has_sob = field_exists("Sales Order Item", "batch_no")
				has_socb = field_exists("Sales Order Item", "custom_batch_no")
				so_b_clauses = []
				if has_sob:
					so_b_clauses.append("soi.batch_no like %(batch_no)s")
				if has_socb:
					so_b_clauses.append("soi.custom_batch_no like %(batch_no)s")

				if so_b_clauses:
					revenue = flt(frappe.db.sql(
						f"""
						select sum(soi.amount)
						from `tabSales Order Item` soi
						where soi.parent = %(sales_order)s and soi.docstatus != 2
							and ({' or '.join(so_b_clauses)})
						""",
						{"sales_order": sales_order, "batch_no": f"%{batch_no}%"},
					)[0][0] or 0)
		else:
			# Invoiced net amount, or Sales Order net_total if no invoice yet
			invoiced_rev = flt(frappe.db.sql(
				"""
				select sum(sii.net_amount)
				from `tabSales Invoice Item` sii
				inner join `tabSales Invoice` si on si.name = sii.parent
				where sii.sales_order = %s and si.docstatus = 1
				""",
				sales_order,
			)[0][0] or 0)

			if invoiced_rev > 0:
				revenue = invoiced_rev
			else:
				revenue = flt(frappe.db.get_value("Sales Order", sales_order, "net_total") or 0)

	# RM Cost: GL Entries for Delivery Notes fulfilling this Sales Order / Batch
	rm_cost = 0.0
	if sales_order:
		dn_conds = ["dni.against_sales_order = %(sales_order)s", "dn.docstatus = 1"]
		dn_vals = {"sales_order": sales_order}

		if batch_no:
			has_dnb = field_exists("Delivery Note Item", "batch_no")
			has_dncb = field_exists("Delivery Note Item", "custom_batch_no")
			has_dnsod = field_exists("Delivery Note Item", "so_detail")
			dn_b_clauses = []
			if has_dnb:
				dn_b_clauses.append("dni.batch_no like %(batch_no)s")
			if has_dncb:
				dn_b_clauses.append("dni.custom_batch_no like %(batch_no)s")
			if has_dnsod and matching_soi_names:
				dn_b_clauses.append("dni.so_detail in %(matching_soi_names)s")
				dn_vals["matching_soi_names"] = tuple(matching_soi_names)
			if dn_b_clauses:
				dn_conds.append(f"({' or '.join(dn_b_clauses)})")
				dn_vals["batch_no"] = f"%{batch_no}%"

		dn_names = frappe.db.sql(
			f"""
			select distinct dni.parent
			from `tabDelivery Note Item` dni
			inner join `tabDelivery Note` dn on dn.name = dni.parent
			where {' and '.join(dn_conds)}
			""",
			dn_vals,
			pluck=True,
		)
		if dn_names:
			rm_cost = flt(frappe.db.sql(
				"""
				select sum(debit_in_account_currency)
				from `tabGL Entry`
				where voucher_type = 'Delivery Note'
					and voucher_no in %s
				""",
				(dn_names,),
			)[0][0] or 0)

	# Indirect Expense: Non-stock Purchase Invoices linked to this Sales Order or Project
	indirect = 0.0
	if batch_no:
		pi_names = get_doc_names_for_so_item(sales_order, "pi", DOC_CONFIG.get("pi", {"doctype": "Purchase Invoice"}), batch_no=batch_no, project=project)
	else:
		pi_names = get_doc_names_for_so(sales_order, "pi", DOC_CONFIG.get("pi", {"doctype": "Purchase Invoice"}), project=project)

	if pi_names and doctype_installed("Purchase Invoice Item"):
		has_is_subcontracted = field_exists("Purchase Invoice", "is_subcontracted")
		subcontract_clause = "and pi.is_subcontracted = 0" if has_is_subcontracted else ""
		indirect = flt(frappe.db.sql(
			f"""
			select sum(pii.net_amount)
			from `tabPurchase Invoice Item` pii
			inner join `tabPurchase Invoice` pi on pi.name = pii.parent
			inner join `tabItem` it on it.name = pii.item_code
			where pii.parent in %s and pi.docstatus = 1
				and it.is_stock_item = 0
				{subcontract_clause}
			""",
			(tuple(pi_names),),
		)[0][0] or 0)

	profit = revenue - rm_cost - indirect
	profit_pct = (profit / revenue * 100) if revenue else 0

	return {
		"revenue": revenue,
		"rm_cost": rm_cost,
		"indirect": indirect,
		"profit": profit,
		"profit_pct": profit_pct,
	}


# ---------------------------------------------------------------------------
# Order Items & Material Consumption
# ---------------------------------------------------------------------------

def get_items_and_consumption(sales_order=None, project=None, branch=None, batch_no=None):
	if not sales_order and project:
		sales_order = frappe.db.get_value("Sales Order", {"project": project, "docstatus": ["!=", 2]}, "name")

	if not sales_order:
		return {"order_items": [], "rows": [], "material_consumption": []}

	batch_no = (batch_no or "").strip()
	has_batch = field_exists("Sales Order Item", "batch_no")
	has_custom_batch = field_exists("Sales Order Item", "custom_batch_no")
	if has_batch and has_custom_batch:
		batch_field = "coalesce(soi.custom_batch_no, soi.batch_no) as batch_no"
	elif has_custom_batch:
		batch_field = "soi.custom_batch_no as batch_no"
	elif has_batch:
		batch_field = "soi.batch_no as batch_no"
	else:
		batch_field = "NULL as batch_no"

	so_branch_col = "so.branch as branch," if field_exists("Sales Order", "branch") else ""

	order_items = frappe.db.sql(
		f"""
		select soi.name as so_item_name, soi.idx as line_no, soi.item_code, soi.item_name, soi.qty, soi.delivered_qty,
			soi.rate, soi.amount, soi.delivery_date, {batch_field}, {so_branch_col} soi.parent as sales_order
		from `tabSales Order Item` soi
		inner join `tabSales Order` so on so.name = soi.parent
		inner join `tabItem` item on item.name = soi.item_code
		where so.name = %(sales_order)s and so.docstatus != 2 and item.is_stock_item = 1
		order by soi.idx
		""",
		{"sales_order": sales_order},
		as_dict=True,
	)

	if batch_no and order_items:
		order_items = [it for it in order_items if batch_no.lower() in (it.get("batch_no") or "").lower()]

	# Consumed RM from Stock Entry Details linked to this Sales Order or Project
	se_cond = "se.sales_order = %(sales_order)s" if field_exists("Stock Entry", "sales_order") else ""
	if project and field_exists("Stock Entry", "project"):
		se_cond = f"({se_cond} or se.project = %(project)s)" if se_cond else "se.project = %(project)s"

	consumption_map = {}
	if se_cond:
		consumption_map = {
			r.item_code: r
			for r in frappe.db.sql(
				f"""
				select sed.item_code, sum(sed.qty) as qty_consumed, avg(sed.valuation_rate) as valuation_rate
				from `tabStock Entry Detail` sed
				inner join `tabStock Entry` se on se.name = sed.parent
				where {se_cond} and se.docstatus = 1
					and se.purpose in ('Material Issue', 'Manufacture', 'Material Transfer for Manufacture')
				group by sed.item_code
				""",
				{"sales_order": sales_order, "project": project},
				as_dict=True,
			)
		}

	# Purchase Order items ordered against this Sales Order or Project
	ordered_map = {}
	if doctype_installed("Purchase Order") and doctype_installed("Purchase Order Item"):
		po_cond = "poi.sales_order = %(sales_order)s" if field_exists("Purchase Order Item", "sales_order") else ""
		if project and field_exists("Purchase Order", "project"):
			po_cond = f"({po_cond} or po.project = %(project)s)" if po_cond else "po.project = %(project)s"

		if po_cond:
			ordered_map = {
				r.item_code: r.total_ordered
				for r in frappe.db.sql(
					f"""
					select poi.item_code, sum(poi.qty) as total_ordered
					from `tabPurchase Order Item` poi
					inner join `tabPurchase Order` po on po.name = poi.parent
					where {po_cond} and po.docstatus != 2
					group by poi.item_code
					""",
					{"sales_order": sales_order, "project": project},
					as_dict=True,
				)
			}

	bom_available = doctype_installed("BOM") and doctype_installed("BOM Item")

	rows = []
	flat_consumption = []

	for it in order_items:
		it_components = []
		it["pending_qty"] = max(0.0, flt(it.qty) - flt(it.delivered_qty))
		it["amount"] = flt(it.get("amount") or (flt(it.qty) * flt(it.rate)))

		if bom_available:
			bom_name = None
			if it.get("batch_no") and field_exists("BOM", "custom_batch_no") and field_exists("BOM", "sales_order") and sales_order:
				bom_name = frappe.db.get_value("BOM", {"item": it.item_code, "sales_order": sales_order, "custom_batch_no": it.get("batch_no"), "docstatus": 1}, "name")
			if not bom_name and it.get("bom_no"):
				b_item = frappe.db.get_value("BOM", it.get("bom_no"), "item")
				if b_item == it.item_code:
					bom_name = it.get("bom_no")
			if not bom_name and field_exists("BOM", "sales_order") and sales_order:
				bom_name = frappe.db.get_value("BOM", {"item": it.item_code, "sales_order": sales_order, "docstatus": 1}, "name")
			if not bom_name:
				bom_name = frappe.db.get_value("BOM", {"item": it.item_code, "is_default": 1, "docstatus": 1, "is_active": 1}, "name")
			if bom_name:
				bom_rows = frappe.db.sql(
					"""
					select bi.item_code, bi.item_name, bi.qty as qty_per_unit
					from `tabBOM Item` bi
					where bi.parent = %s
					order by bi.idx
					""",
					bom_name,
					as_dict=True,
				)
				for comp in bom_rows:
					cons = consumption_map.get(comp.item_code)
					valuation_rate = (cons.valuation_rate if cons else None)
					if valuation_rate is None:
						valuation_rate = frappe.db.get_value("Item", comp.item_code, "valuation_rate")

					comp_dict = {
						"component_name": comp.item_name or comp.item_code,
						"component_code": comp.item_code,
						"qty_needed": flt(comp.qty_per_unit) * flt(it.qty),
						"total_ordered": ordered_map.get(comp.item_code),
						"consumed": cons.qty_consumed if cons else 0,
						"valuation_rate": valuation_rate,
					}
					it_components.append(comp_dict)
					flat_consumption.append({
						"item_code": comp.item_code,
						"item_name": comp.item_name,
						"qty_consumed": cons.qty_consumed if cons else 0,
						"valuation_rate": cons.valuation_rate if cons else 0,
					})

		it["components"] = it_components
		item_branch = it.get("branch")

		if not it_components:
			rows.append({
				"line_no": it.line_no,
				"order_item": it.item_name or it.item_code,
				"item_code": it.item_code,
				"batch_no": it.get("batch_no"),
				"branch": item_branch,
				"delivery_date": str(it.delivery_date) if it.delivery_date else None,
				"type": "FG",
				"component_name": None,
				"component_code": None,
				"qty_needed": it.qty,
				"total_ordered": None,
				"consumed": None,
				"fg_delivered": it.delivered_qty,
				"selling_price": it.rate,
				"valuation_rate": None,
				"group_start": True,
			})
		else:
			for i, comp in enumerate(it_components):
				rows.append({
					"line_no": it.line_no if i == 0 else None,
					"order_item": (it.item_name or it.item_code) if i == 0 else None,
					"item_code": it.item_code if i == 0 else None,
					"batch_no": it.get("batch_no") if i == 0 else None,
					"branch": item_branch if i == 0 else None,
					"delivery_date": (str(it.delivery_date) if it.delivery_date else None) if i == 0 else None,
					"type": "FG" if i == 0 else "RM",
					"component_name": comp["component_name"],
					"component_code": comp["component_code"],
					"qty_needed": comp["qty_needed"],
					"total_ordered": comp["total_ordered"],
					"consumed": comp["consumed"],
					"fg_delivered": it.delivered_qty if i == 0 else None,
					"selling_price": it.rate if i == 0 else None,
					"valuation_rate": comp["valuation_rate"],
					"group_start": i == 0,
				})

	return {
		"order_items": order_items,
		"rows": rows,
		"material_consumption": flat_consumption,
	}


# ---------------------------------------------------------------------------
# Document Preview Popup
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_doc_summary(doctype=None, name=None, batch_no=None):
	if not doctype or not name or not frappe.db.exists(doctype, name):
		return None

	batch_no = (batch_no or "").strip()
	doc = frappe.get_doc(doctype, name)

	sales_order = doc.get("sales_order") if doc.meta.has_field("sales_order") else None
	project = doc.get("project") if doc.meta.has_field("project") else None

	child_fieldname = None
	for df in doc.meta.get_table_fields():
		if df.fieldname in ("items", "po_items", "required_items", "supplied_items"):
			child_fieldname = df.fieldname
			break

	# If batch_no is provided, find corresponding Sales Order Item IDs if doc is linked to SO
	matching_soi_names = set()
	if batch_no:
		so_for_batch = sales_order if sales_order else (name if doctype == "Sales Order" else None)
		if so_for_batch:
			has_b = field_exists("Sales Order Item", "batch_no")
			has_cb = field_exists("Sales Order Item", "custom_batch_no")
			soi_b_clauses = []
			if has_b:
				soi_b_clauses.append("soi.batch_no like %(batch_no)s")
			if has_cb:
				soi_b_clauses.append("soi.custom_batch_no like %(batch_no)s")
			if soi_b_clauses:
				soi_res = frappe.db.sql(
					f"""
					select soi.name
					from `tabSales Order Item` soi
					where soi.parent = %(so)s and soi.docstatus != 2 and ({' or '.join(soi_b_clauses)})
					""",
					{"so": so_for_batch, "batch_no": f"%{batch_no}%"},
					pluck=True,
				)
				matching_soi_names.update(soi_res)

	# Doctypes whose child rows do NOT have batch_no / SO-item link fields.
	# Always show all their child items without batch filtering.
	SKIP_BATCH_FILTER_DOCTYPES = {"BOM", "Production Plan", "Stock Entry", "Journal Entry", "Quotation"}
	skip_batch_filter = doctype in SKIP_BATCH_FILTER_DOCTYPES

	items = []
	if child_fieldname:
		for row in doc.get(child_fieldname):
			reference = None
			for ref_field, ref_doctype in (
				("against_sales_order", "Sales Order"),
				("sales_order", "Sales Order"),
				("purchase_order", "Purchase Order"),
				("material_request", "Material Request"),
				("purchase_receipt", "Purchase Receipt"),
				("delivery_note", "Delivery Note"),
			):
				if row.get(ref_field):
					reference = {"doctype": ref_doctype, "name": row.get(ref_field)}
					if not sales_order and ref_doctype == "Sales Order":
						sales_order = row.get(ref_field)
					break

			row_batch = (row.get("custom_batch_no") or row.get("batch_no") or "").strip()
			row_soi = row.get("sales_order_item") or row.get("so_detail") or (row.name if doctype == "Sales Order" else None)

			# If doc is Sales Order, only include stock items
			if doctype == "Sales Order" and row.get("item_code"):
				is_stock = frappe.db.get_value("Item", row.get("item_code"), "is_stock_item")
				if is_stock == 0:
					continue

			# For doctypes like BOM/Production Plan, skip batch filtering — always show all child items
			if not skip_batch_filter and batch_no:
				batch_match = (batch_no.lower() in row_batch.lower()) if row_batch else False
				soi_match = (row_soi in matching_soi_names) if row_soi and matching_soi_names else False
				if not batch_match and not soi_match:
					continue

			# Determine qty across different child table schemas
			row_qty = flt(
				row.get("qty")
				or row.get("planned_qty")
				or row.get("required_qty")
				or row.get("stock_qty")
				or row.get("transfer_qty")
				or 0
			)
			# Rate across schemas: BOM Item may have rate_with_margin or valuation_rate
			row_rate = row.get("rate") or row.get("rate_with_margin") or row.get("valuation_rate")
			row_amount = row.get("amount") or row.get("base_amount")

			items.append({
				"item_code": row.get("item_code") or row.get("production_item") or row.get("rm_item_code"),
				"item_name": row.get("item_name") or row.get("item_code") or row.get("production_item"),
				"description": row.get("description"),
				"batch_no": row_batch or None,
				"qty": row_qty,
				"uom": row.get("uom") or row.get("stock_uom"),
				"rate": flt(row_rate) if row_rate is not None else None,
				"amount": flt(row_amount) if row_amount is not None else None,
				"warehouse": row.get("warehouse") or row.get("t_warehouse") or row.get("source_warehouse") or row.get("from_warehouse") or row.get("set_warehouse"),
				"delivery_date": str(row.get("delivery_date") or row.get("schedule_date") or row.get("required_by") or row.get("planned_start_date") or "") or None,
				"reference": reference,
			})

	status_field = None
	if doc.meta.has_field("status"):
		status_field = "status"
	elif doc.meta.has_field("workflow_state"):
		status_field = "workflow_state"

	party_label = "Supplier" if doc.meta.has_field("supplier") else ("Customer" if doc.meta.has_field("customer") else None)
	party_name = doc.get("supplier_name") or doc.get("supplier") if party_label == "Supplier" else (doc.get("customer_name") or doc.get("customer") if party_label == "Customer" else None)

	total_qty = sum(i["qty"] for i in items) if items else flt(doc.get("total_qty") or doc.get("total_planned_qty") or doc.get("qty") or doc.get("quantity") or 0)
	grand_total = sum(i["amount"] for i in items if i.get("amount") is not None) if (batch_no and items and any(i.get("amount") is not None for i in items)) else flt(doc.get("grand_total") or doc.get("total_cost") or doc.get("total") or doc.get("paid_amount") or 0)

	doc_status = doc.get(status_field) if status_field else None
	if not doc_status:
		doc_status = "Submitted" if doc.docstatus == 1 else ("Cancelled" if doc.docstatus == 2 else "Draft")

	return {
		"doctype": doctype,
		"name": doc.name,
		"batch_no": batch_no or None,
		"status": doc_status,
		"sales_order": sales_order,
		"project": project,
		"date": str(doc.get("transaction_date") or doc.get("posting_date") or doc.get("creation") or "")[:10] or None,
		"grand_total": grand_total,
		"party_label": party_label,
		"party_name": party_name,
		"items": items,
		"total_qty": total_qty,
	}