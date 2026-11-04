# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import json
from collections import defaultdict
import frappe
from frappe import _
from frappe.utils import getdate, format_date, cstr, cint


TRANSACTION_CONFIG = {
	"Delivery Note": {
		"date_field": "posting_date",
		"open_statuses": {"Draft", "To Bill"},
		# "completed_statuses": {"Completed", "Closed", "Return Issued"},
		"icon": "fa fa-truck",
		"badge_class": "badge-primary",
	},
	"Sales Invoice": {
		"date_field": "posting_date",
		"open_statuses": {"Draft"},
		# "completed_statuses": {"Paid", "Return"},
		"only_draft": True,
		"icon": "fa fa-file-text-o",
		"badge_class": "badge-info",
	},
	"Payment Entry": {
		"date_field": "posting_date",
		"open_statuses": {"Draft"},
		# "completed_statuses": {"Submitted"},
		"only_draft": True,
		"icon": "fa fa-money",
		"badge_class": "badge-success",
	},
	"Work Order": {
		"date_field": "planned_start_date",
		"date_fallback": "creation",
		"open_statuses": {"Draft", "Not Started", "In Process"},
		# "completed_statuses": {"Completed", "Closed"},
		"icon": "fa fa-cogs",
		"badge_class": "badge-warning",
	},
	"Production Plan": {
		"date_field": "posting_date",
		"open_statuses": {"Draft", "Submitted", "In Process", "Material Requested"},
		# "completed_statuses": {"Completed", "Closed"},
		"icon": "fa fa-industry",
		"badge_class": "badge-secondary",
	},
	"Material Request": {
		"date_field": "transaction_date",
		"open_statuses": {"Draft", "Pending", "Ordered", "Partially Ordered", "Partially Received"},
		# "completed_statuses": {"Received", "Transferred", "Issued", "Stopped"},
		"icon": "fa fa-clipboard",
		"badge_class": "badge-warning",
	},
	"Purchase Order": {
		"date_field": "transaction_date",
		"open_statuses": {"Draft", "To Receive and Bill", "To Receive", "To Bill"},
		# "completed_statuses": {"Completed", "Closed", "Delivered"},
		"icon": "fa fa-shopping-cart",
		"badge_class": "badge-danger",
	},
	"Purchase Receipt": {
		"date_field": "posting_date",
		"open_statuses": {"Draft", "To Bill", "Partly Billed"},
		# "completed_statuses": {"Completed", "Closed", "Return", "Return Issued"},
		"icon": "fa fa-inbox",
		"badge_class": "badge-info",
	},
	"Purchase Invoice": {
		"date_field": "posting_date",
		"open_statuses": {"Draft"},
		# "completed_statuses": {"Paid", "Return"},
		"only_draft": True,
		"icon": "fa fa-credit-card",
		"badge_class": "badge-purple",
	},
	"Stock Entry": {
		"date_field": "posting_date",
		"open_statuses": {"Draft"},
		# "completed_statuses": {"Submitted"},
		"only_draft": True,
		"icon": "fa fa-exchange",
		"badge_class": "badge-secondary",
	},
	"Subcontracting Order": {
		"date_field": "transaction_date",
		"open_statuses": {"Draft", "Open", "Material Transferred", "Partial Material Transferred"},
		# "completed_statuses": {"Completed", "Closed"},
		"icon": "fa fa-wrench",
		"badge_class": "badge-dark",
	},
	"Subcontracting Receipt": {
		"date_field": "posting_date",
		"open_statuses": {"Draft"},
		# "completed_statuses": {"Completed"},
		"only_draft": True,
		"icon": "fa fa-check-circle",
		"badge_class": "badge-success",
	},
	"Pick List": {
		"date_field": "creation",
		"open_statuses": {"Draft", "Open"},
		"only_draft": True,
		"icon": "fa fa-list-ul",
		"badge_class": "badge-light",
	},
	"Order Modification Request": {
		"date_field": "date",
		"date_fallback": "creation",
		"open_statuses": {"Draft"},
		"only_draft": True,
		"icon": "fa fa-pencil-square-o",
		"badge_class": "badge-warning",
	},
	"BOM": {
		"date_field": "creation",
		"open_statuses": {"Draft"},
		"only_draft": True,
		"icon": "fa fa-sitemap",
		"badge_class": "badge-info",
	},
	"Bom Modification Request": {
		"date_field": "date",
		"date_fallback": "creation",
		"open_statuses": {"Draft"},
		"only_draft": True,
		"icon": "fa fa-wrench",
		"badge_class": "badge-primary",
	},
	"Valve Painting": {
		"date_field": "posting_date",
		"date_fallback": "creation",
		"open_statuses": {"Draft"},
		"only_draft": True,
		"icon": "fa fa-paint-brush",
		"badge_class": "badge-info",
	},
	"Valve Testing": {
		"date_field": "posting_date",
		"date_fallback": "creation",
		"open_statuses": {"Draft"},
		"only_draft": True,
		"icon": "fa fa-flask",
		"badge_class": "badge-warning",
	},
	"Valve Assembly": {
		"date_field": "posting_date",
		"date_fallback": "creation",
		"open_statuses": {"Draft"},
		"only_draft": True,
		"icon": "fa fa-cogs",
		"badge_class": "badge-secondary",
	},
	"Proforma Invoice": {
		"date_field": "transaction_date",
		"date_fallback": "creation",
		"open_statuses": {"Draft"},
		"only_draft": True,
		"icon": "fa fa-file-text-o",
		"badge_class": "badge-purple",
	},
}

ALIAS_DOCTYPE_MAP = {
	"valve painting": "Valve Painting",
	"valve painting item": "Valve Painting",
	"valve testing": "Valve Testing",
	"valve testing item": "Valve Testing",
	"valve assembly": "Valve Assembly",
	"assembly item serial no": "Valve Assembly",
	"proforma invoice": "Proforma Invoice",
	"proforma invoice item": "Proforma Invoice",
	"bom": "BOM",
	"bom modification request": "Bom Modification Request",
	"order modification request": "Order Modification Request",
}



def doctype_is_available(doctype):
	"""Check if DocType and underlying table exist."""
	if not frappe.db.exists("DocType", doctype):
		return False
	return frappe.db.table_exists(doctype)


def classify_transaction_status(doctype, docstatus, raw_status):
	"""
	Determines the display status and whether a transaction is open or draft.
	Returns: (status_label, is_open, is_draft)
	"""
	docstatus = cint(docstatus)
	status = cstr(raw_status).strip()

	# 1. Cancelled documents are strictly excluded
	if docstatus == 2 or status == "Cancelled":
		return ("Cancelled", False, False)

	cfg = TRANSACTION_CONFIG.get(doctype, {})
	open_statuses = cfg.get("open_statuses")
	# completed_statuses = cfg.get("completed_statuses", set())

	# 2. Draft documents (docstatus = 0)
	if docstatus == 0:
		status_label = status if status in ("Open", "Draft") else "Draft"
		return (status_label, True, True)

	# 3. If doctype is only open in draft (docstatus = 0)
	if cfg.get("only_draft"):
		return (status or "Submitted", False, False)

	# 4. Submitted documents (docstatus = 1)
	final_status = status or "Submitted"
	# if final_status in completed_statuses:
	# 	return (final_status, False, False)

	if open_statuses is not None:
		if final_status in open_statuses:
			return (final_status, True, False)
		return (final_status, False, False)

	return (final_status, True, False)


def get_user_full_names(user_emails):
	"""Return a map of user email -> full_name."""
	if not user_emails:
		return {}
	users = frappe.db.sql(
		"""
		SELECT name, full_name
		FROM `tabUser`
		WHERE name IN %(emails)s
		""",
		{"emails": tuple(set(user_emails))},
		as_dict=True,
	)
	return {u.name: u.full_name or u.name for u in users}


def resolve_responsible_user(doc_dict):
	"""Extract responsible user from _assign or modified_by/owner."""
	raw_assign = doc_dict.get("_assign")
	if raw_assign:
		try:
			assigned = json.loads(raw_assign) if isinstance(raw_assign, str) else raw_assign
			if isinstance(assigned, list) and assigned:
				return assigned[0]
		except Exception:
			pass
	return doc_dict.get("modified_by") or doc_dict.get("owner") or ""


@frappe.whitelist()
def get_transaction_integrity_data(
	from_date=None,
	to_date=None,
	branch=None,
	customer=None,
	sales_order=None,
	transaction_type=None,
	transaction_status=None,
	search_term=None,
	sort_field="transaction_date",
	sort_order="desc",
	page=1,
	page_length=25,
):
	"""
	Main backend method for Sales Order Transaction Integrity Report.
	Identifies completed Sales Orders with open linked transactions.
	"""
	# Permission check
	if not frappe.has_permission("Sales Order", "read"):
		frappe.throw(_("You do not have permission to view Sales Orders."), frappe.PermissionError)

	# 1. Build Sales Order Query Filters
	so_conditions = ["so.docstatus = 1", "so.status = 'Completed'"]
	so_values = {}

	# Branch permissions
	try:
		from frappe.core.doctype.user_permission.user_permission import get_user_permissions
		user_perms = get_user_permissions(frappe.session.user)
		if "Branch" in user_perms:
			allowed_branches = [b.get("doc") for b in user_perms["Branch"] if b.get("doc")]
			if allowed_branches:
				if branch:
					if branch not in allowed_branches:
						return _build_empty_response()
				else:
					so_conditions.append("so.branch IN %(user_allowed_branches)s")
					so_values["user_allowed_branches"] = tuple(allowed_branches)
	except Exception:
		pass

	if branch:
		so_conditions.append("so.branch = %(branch)s")
		so_values["branch"] = branch

	if customer:
		so_conditions.append("(so.customer = %(customer)s OR so.customer_name LIKE %(cust_pattern)s)")
		so_values["customer"] = customer
		so_values["cust_pattern"] = f"%{customer}%"

	if sales_order:
		so_conditions.append("so.name = %(sales_order)s")
		so_values["sales_order"] = sales_order

	if from_date:
		so_conditions.append("so.transaction_date >= %(from_date)s")
		so_values["from_date"] = from_date

	if to_date:
		so_conditions.append("so.transaction_date <= %(to_date)s")
		so_values["to_date"] = to_date

	sales_orders = frappe.db.sql(
		f"""
		SELECT
			so.name,
			so.customer,
			so.customer_name,
			so.transaction_date,
			so.branch,
			so.status,
			so.owner
		FROM `tabSales Order` so
		WHERE {' AND '.join(so_conditions)}
		ORDER BY so.transaction_date DESC, so.name DESC
		""",
		so_values,
		as_dict=True,
	)

	completed_sos_checked = len(sales_orders)
	if completed_sos_checked == 0:
		return _build_empty_response(completed_sos_checked=0)

	so_map = {s.name: s for s in sales_orders}
	so_names = list(so_map.keys())

	# Determine which transaction doctypes to query
	target_doctypes = list(TRANSACTION_CONFIG.keys())
	norm_tx_type = None
	if transaction_type:
		clean_tt = cstr(transaction_type).strip()
		norm_tx_type = ALIAS_DOCTYPE_MAP.get(clean_tt.lower(), clean_tt)
		if norm_tx_type in TRANSACTION_CONFIG:
			target_doctypes = [norm_tx_type]

	# Respect read permissions on each transaction doctype
	permitted_doctypes = [dt for dt in target_doctypes if frappe.has_permission(dt, "read")]

	# Fetch open transactions linked to these Sales Orders
	# Map: so_name -> dict of (doctype, docname) -> tx_dict (guarantees deduplication)
	so_open_transactions = defaultdict(dict)

	_query_all_linked_transactions(
		so_names=so_names,
		so_map=so_map,
		permitted_doctypes=permitted_doctypes,
		so_open_transactions=so_open_transactions,
	)

	# Apply Transaction Type and Transaction Status filters
	status_filter = cstr(transaction_status).strip()

	qualifying_sales_orders = []
	all_user_emails = set()
	total_open_tx_count = 0
	open_draft_tx_count = 0

	for s in sales_orders:
		so_name = s.name
		raw_tx_map = so_open_transactions.get(so_name, {})

		filtered_tx_list = []
		for (dt, dname), tx in raw_tx_map.items():
			# Filter by transaction type if specified (supporting aliases like child table names)
			if norm_tx_type and tx["doctype"].lower() != norm_tx_type.lower():
				continue

			# Filter by transaction status if specified
			if status_filter:
				if status_filter.lower() == "draft":
					if not tx["is_draft"]:
						continue
				else:
					if tx["status"].lower() != status_filter.lower():
						continue

			filtered_tx_list.append(tx)
			if tx.get("owner"):
				all_user_emails.add(tx["owner"])
			if tx.get("responsible_user_raw"):
				all_user_emails.add(tx["responsible_user_raw"])

		# Rule: "Display only Sales Orders having at least one open linked transaction."
		if not filtered_tx_list:
			continue

		# Sort transactions by date desc, then doctype, name
		filtered_tx_list.sort(key=lambda x: (x.get("posting_date") or "", x["doctype"], x["name"]), reverse=True)

		so_record = {
			"sales_order": s.name,
			"customer": s.customer,
			"customer_name": s.customer_name or s.customer,
			"transaction_date": s.transaction_date,
			"transaction_date_formatted": format_date(s.transaction_date),
			"branch": s.branch or "-",
			"status": s.status,
			"open_transactions_count": len(filtered_tx_list),
			"open_transactions": filtered_tx_list,
		}

		# Check search_term filter if provided
		if search_term:
			term = search_term.strip().lower()
			matches_so = (
				term in s.name.lower()
				or term in (s.customer or "").lower()
				or term in (s.customer_name or "").lower()
				or term in (s.branch or "").lower()
			)
			matches_tx = any(
				term in tx["name"].lower()
				or term in tx["doctype"].lower()
				or term in tx["status"].lower()
				or term in (tx.get("owner") or "").lower()
				for tx in filtered_tx_list
			)
			if not (matches_so or matches_tx):
				continue

		qualifying_sales_orders.append(so_record)
		total_open_tx_count += len(filtered_tx_list)
		open_draft_tx_count += sum(1 for tx in filtered_tx_list if tx["is_draft"])

	# Resolve user full names
	user_name_map = get_user_full_names(all_user_emails)
	for so in qualifying_sales_orders:
		for tx in so["open_transactions"]:
			tx["owner_name"] = user_name_map.get(tx.get("owner"), tx.get("owner") or "-")
			resp = tx.get("responsible_user_raw")
			tx["responsible_user"] = user_name_map.get(resp, resp or tx["owner_name"])

	# Sort Sales Orders
	reverse_sort = (sort_order or "desc").lower() == "desc"
	if sort_field == "open_transactions_count":
		qualifying_sales_orders.sort(key=lambda x: x["open_transactions_count"], reverse=reverse_sort)
	elif sort_field == "sales_order":
		qualifying_sales_orders.sort(key=lambda x: x["sales_order"], reverse=reverse_sort)
	elif sort_field == "customer":
		qualifying_sales_orders.sort(key=lambda x: x["customer_name"], reverse=reverse_sort)
	else:
		qualifying_sales_orders.sort(key=lambda x: (x.get("transaction_date") or "", x["sales_order"]), reverse=reverse_sort)

	# Pagination
	total_records = len(qualifying_sales_orders)
	page = max(1, cint(page or 1))
	page_len = cint(page_length or 25)

	if page_len <= 0 or page_len == 999999:
		paginated_data = qualifying_sales_orders
		total_pages = 1
	else:
		total_pages = (total_records + page_len - 1) // page_len if total_records > 0 else 1
		start_idx = (page - 1) * page_len
		end_idx = start_idx + page_len
		paginated_data = qualifying_sales_orders[start_idx:end_idx]

	return {
		"summary": {
			"completed_sos_checked": completed_sos_checked,
			"sos_with_open_tx": total_records,
			"total_open_tx": total_open_tx_count,
			"open_draft_tx": open_draft_tx_count,
		},
		"data": paginated_data,
		"pagination": {
			"page": page,
			"page_length": page_len,
			"total_records": total_records,
			"total_pages": total_pages,
		},
		"filter_meta": {
			"branches": _get_available_branches(),
			"transaction_types": [dt for dt in TRANSACTION_CONFIG.keys() if frappe.has_permission(dt, "read")],
			"transaction_statuses": [
				"Draft",
				"To Bill",
				"Partly Billed",
				"Not Started",
				"In Process",
				"Submitted",
				"Material Requested",
				"Pending",
				"Ordered",
				"Partially Ordered",
				"Partially Received",
				"To Receive and Bill",
				"To Receive",
				"Open",
				"Material Transferred",
				"Partial Material Transferred",
			],
		},
	}


def _query_all_linked_transactions(so_names, so_map, permitted_doctypes, so_open_transactions):
	"""
	Batch queries all permitted transaction doctypes for the provided Sales Orders,
	handling both direct and indirect references without N+1 queries.
	"""
	if not so_names or not permitted_doctypes:
		return

	# Helper to record a transaction if open
	def record_transaction(so_name, doctype, docname, date_val, docstatus, status_val, owner, raw_assign):
		if not so_name or so_name not in so_map:
			return
		status_label, is_open, is_draft = classify_transaction_status(doctype, docstatus, status_val)
		if not is_open:
			return

		key = (doctype, docname)
		cfg = TRANSACTION_CONFIG.get(doctype, {})
		responsible_raw = resolve_responsible_user({"_assign": raw_assign, "owner": owner})

		so_open_transactions[so_name][key] = {
			"doctype": doctype,
			"name": docname,
			"posting_date": date_val,
			"posting_date_formatted": format_date(date_val) if date_val else "-",
			"status": status_label,
			"docstatus": cint(docstatus),
			"is_draft": is_draft,
			"owner": owner or "-",
			"responsible_user_raw": responsible_raw,
			"icon": cfg.get("icon", "fa fa-file-o"),
			"badge_class": cfg.get("badge_class", "badge-default"),
		}

	# 1. Delivery Note (Direct: Delivery Note Item -> against_sales_order)
	if "Delivery Note" in permitted_doctypes and doctype_is_available("Delivery Note") and doctype_is_available("Delivery Note Item"):
		dn_rows = frappe.db.sql(
			"""
			SELECT
				dni.against_sales_order AS so_name,
				dn.name,
				dn.posting_date,
				dn.status,
				dn.docstatus,
				dn.owner,
				dn._assign
			FROM `tabDelivery Note Item` dni
			JOIN `tabDelivery Note` dn ON dn.name = dni.parent
			WHERE dni.against_sales_order IN %(sos)s
			  AND dn.docstatus != 2
			""",
			{"sos": so_names},
			as_dict=True,
		)
		for r in dn_rows:
			record_transaction(r.so_name, "Delivery Note", r.name, r.posting_date, r.docstatus, r.status, r.owner, r._assign)

	# 2. Sales Invoice (Direct: Sales Invoice Item -> sales_order)
	si_to_so = defaultdict(set)
	if ("Sales Invoice" in permitted_doctypes or "Payment Entry" in permitted_doctypes) and doctype_is_available("Sales Invoice") and doctype_is_available("Sales Invoice Item"):
		si_rows = frappe.db.sql(
			"""
			SELECT
				sii.sales_order AS so_name,
				si.name,
				si.posting_date,
				si.status,
				si.docstatus,
				si.owner,
				si._assign
			FROM `tabSales Invoice Item` sii
			JOIN `tabSales Invoice` si ON si.name = sii.parent
			WHERE sii.sales_order IN %(sos)s
			  AND si.docstatus != 2
			""",
			{"sos": so_names},
			as_dict=True,
		)
		for r in si_rows:
			si_to_so[r.name].add(r.so_name)
			if "Sales Invoice" in permitted_doctypes:
				record_transaction(r.so_name, "Sales Invoice", r.name, r.posting_date, r.docstatus, r.status, r.owner, r._assign)

	# 3. Work Order (Direct: sales_order)
	wo_to_so = defaultdict(set)
	if ("Work Order" in permitted_doctypes or "Stock Entry" in permitted_doctypes) and doctype_is_available("Work Order"):
		wo_rows = frappe.db.sql(
			"""
			SELECT
				wo.sales_order AS so_name,
				wo.name,
				DATE(wo.creation) AS posting_date,
				wo.status,
				wo.docstatus,
				wo.owner,
				wo._assign
			FROM `tabWork Order` wo
			WHERE wo.sales_order IN %(sos)s
			  AND wo.docstatus != 2
			""",
			{"sos": so_names},
			as_dict=True,
		)
		for r in wo_rows:
			wo_to_so[r.name].add(r.so_name)
			if "Work Order" in permitted_doctypes:
				record_transaction(r.so_name, "Work Order", r.name, r.posting_date, r.docstatus, r.status, r.owner, r._assign)

	# 4. Production Plan (Direct: Production Plan Sales Order / Production Plan Item)
	pp_to_so = defaultdict(set)
	if doctype_is_available("Production Plan"):
		if doctype_is_available("Production Plan Sales Order"):
			ppso_rows = frappe.db.sql(
				"""
				SELECT
					ppso.sales_order AS so_name,
					pp.name,
					pp.posting_date,
					pp.status,
					pp.docstatus,
					pp.owner,
					pp._assign
				FROM `tabProduction Plan Sales Order` ppso
				JOIN `tabProduction Plan` pp ON pp.name = ppso.parent
				WHERE ppso.sales_order IN %(sos)s
				  AND pp.docstatus != 2
				""",
				{"sos": so_names},
				as_dict=True,
			)
			for r in ppso_rows:
				pp_to_so[r.name].add(r.so_name)
				if "Production Plan" in permitted_doctypes:
					record_transaction(r.so_name, "Production Plan", r.name, r.posting_date, r.docstatus, r.status, r.owner, r._assign)

		if doctype_is_available("Production Plan Item"):
			ppi_rows = frappe.db.sql(
				"""
				SELECT
					ppi.sales_order AS so_name,
					pp.name,
					pp.posting_date,
					pp.status,
					pp.docstatus,
					pp.owner,
					pp._assign
				FROM `tabProduction Plan Item` ppi
				JOIN `tabProduction Plan` pp ON pp.name = ppi.parent
				WHERE ppi.sales_order IN %(sos)s
				  AND pp.docstatus != 2
				""",
				{"sos": so_names},
				as_dict=True,
			)
			for r in ppi_rows:
				pp_to_so[r.name].add(r.so_name)
				if "Production Plan" in permitted_doctypes:
					record_transaction(r.so_name, "Production Plan", r.name, r.posting_date, r.docstatus, r.status, r.owner, r._assign)

		# Indirect link: Work Orders linked via Production Plan
		if pp_to_so and ("Work Order" in permitted_doctypes or "Stock Entry" in permitted_doctypes) and doctype_is_available("Work Order"):
			pp_wo_rows = frappe.db.sql(
				"""
				SELECT
					wo.production_plan,
					wo.name,
					DATE(wo.creation) AS posting_date,
					wo.status,
					wo.docstatus,
					wo.owner,
					wo._assign
				FROM `tabWork Order` wo
				WHERE wo.production_plan IN %(pps)s
				  AND wo.docstatus != 2
				""",
				{"pps": tuple(pp_to_so.keys())},
				as_dict=True,
			)
			for r in pp_wo_rows:
				for s in pp_to_so.get(r.production_plan, []):
					wo_to_so[r.name].add(s)
					if "Work Order" in permitted_doctypes:
						record_transaction(s, "Work Order", r.name, r.posting_date, r.docstatus, r.status, r.owner, r._assign)

	# 5. Material Request (Direct: sales_order; Indirect: via Production Plan)
	mr_to_so = defaultdict(set)
	if ("Material Request" in permitted_doctypes or "Purchase Order" in permitted_doctypes) and doctype_is_available("Material Request") and doctype_is_available("Material Request Item"):
		mr_conds = ["mri.sales_order IN %(sos)s"]
		mr_vals = {"sos": so_names}
		if pp_to_so:
			mr_conds.append("(mri.production_plan IS NOT NULL AND mri.production_plan IN %(pps)s)")
			mr_vals["pps"] = tuple(pp_to_so.keys())

		mr_rows = frappe.db.sql(
			f"""
			SELECT
				mri.sales_order AS so_name,
				mri.production_plan,
				mr.name,
				mr.transaction_date AS posting_date,
				mr.status,
				mr.docstatus,
				mr.owner,
				mr._assign
			FROM `tabMaterial Request Item` mri
			JOIN `tabMaterial Request` mr ON mr.name = mri.parent
			WHERE ({' OR '.join(mr_conds)})
			  AND mr.docstatus != 2
			""",
			mr_vals,
			as_dict=True,
		)
		for r in mr_rows:
			target_sos = set()
			if r.so_name and r.so_name in so_map:
				target_sos.add(r.so_name)
			if r.production_plan and r.production_plan in pp_to_so:
				target_sos.update(pp_to_so[r.production_plan])
			for s in target_sos:
				mr_to_so[r.name].add(s)
				if "Material Request" in permitted_doctypes:
					record_transaction(s, "Material Request", r.name, r.posting_date, r.docstatus, r.status, r.owner, r._assign)

	# 6. Purchase Order (Direct: sales_order; Indirect: via Material Request or Production Plan)
	po_to_so = defaultdict(set)
	if ("Purchase Order" in permitted_doctypes or "Purchase Receipt" in permitted_doctypes or "Purchase Invoice" in permitted_doctypes or "Subcontracting Order" in permitted_doctypes) and doctype_is_available("Purchase Order") and doctype_is_available("Purchase Order Item"):
		po_conds = ["poi.sales_order IN %(sos)s"]
		po_vals = {"sos": so_names}
		if mr_to_so:
			po_conds.append("(poi.material_request IS NOT NULL AND poi.material_request IN %(mrs)s)")
			po_vals["mrs"] = tuple(mr_to_so.keys())
		if pp_to_so:
			po_conds.append("(poi.production_plan IS NOT NULL AND poi.production_plan IN %(pps)s)")
			po_vals["pps"] = tuple(pp_to_so.keys())

		po_rows = frappe.db.sql(
			f"""
			SELECT
				poi.sales_order AS so_name,
				poi.material_request,
				poi.production_plan,
				po.name,
				po.transaction_date AS posting_date,
				po.status,
				po.docstatus,
				po.owner,
				po._assign
			FROM `tabPurchase Order Item` poi
			JOIN `tabPurchase Order` po ON po.name = poi.parent
			WHERE ({' OR '.join(po_conds)})
			  AND po.docstatus != 2
			""",
			po_vals,
			as_dict=True,
		)
		for r in po_rows:
			target_sos = set()
			if r.so_name and r.so_name in so_map:
				target_sos.add(r.so_name)
			if r.material_request and r.material_request in mr_to_so:
				target_sos.update(mr_to_so[r.material_request])
			if r.production_plan and r.production_plan in pp_to_so:
				target_sos.update(pp_to_so[r.production_plan])
			for s in target_sos:
				po_to_so[r.name].add(s)
				if "Purchase Order" in permitted_doctypes:
					record_transaction(s, "Purchase Order", r.name, r.posting_date, r.docstatus, r.status, r.owner, r._assign)

	# 7. Purchase Receipt (Direct: sales_order; Indirect: via Purchase Order)
	if "Purchase Receipt" in permitted_doctypes and doctype_is_available("Purchase Receipt") and doctype_is_available("Purchase Receipt Item"):
		pr_conds = ["pri.sales_order IN %(sos)s"]
		pr_vals = {"sos": so_names}
		if po_to_so:
			pr_conds.append("(pri.purchase_order IS NOT NULL AND pri.purchase_order IN %(pos)s)")
			pr_vals["pos"] = tuple(po_to_so.keys())

		pr_rows = frappe.db.sql(
			f"""
			SELECT
				pri.sales_order AS so_name,
				pri.purchase_order,
				pr.name,
				pr.posting_date,
				pr.status,
				pr.docstatus,
				pr.owner,
				pr._assign
			FROM `tabPurchase Receipt Item` pri
			JOIN `tabPurchase Receipt` pr ON pr.name = pri.parent
			WHERE ({' OR '.join(pr_conds)})
			  AND pr.docstatus != 2
			""",
			pr_vals,
			as_dict=True,
		)
		for r in pr_rows:
			target_sos = set()
			if r.so_name and r.so_name in so_map:
				target_sos.add(r.so_name)
			if r.purchase_order and r.purchase_order in po_to_so:
				target_sos.update(po_to_so[r.purchase_order])
			for s in target_sos:
				record_transaction(s, "Purchase Receipt", r.name, r.posting_date, r.docstatus, r.status, r.owner, r._assign)

	# 8. Purchase Invoice (Indirect: via Purchase Order)
	if po_to_so and "Purchase Invoice" in permitted_doctypes and doctype_is_available("Purchase Invoice") and doctype_is_available("Purchase Invoice Item"):
		pi_rows = frappe.db.sql(
			"""
			SELECT
				pii.purchase_order,
				pi.name,
				pi.posting_date,
				pi.status,
				pi.docstatus,
				pi.owner,
				pi._assign
			FROM `tabPurchase Invoice Item` pii
			JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
			WHERE pii.purchase_order IN %(pos)s
			  AND pi.docstatus != 2
			""",
			{"pos": tuple(po_to_so.keys())},
			as_dict=True,
		)
		for r in pi_rows:
			for s in po_to_so.get(r.purchase_order, []):
				record_transaction(s, "Purchase Invoice", r.name, r.posting_date, r.docstatus, r.status, r.owner, r._assign)

	# 9. Stock Entry (Indirect: via Work Order)
	if wo_to_so and "Stock Entry" in permitted_doctypes and doctype_is_available("Stock Entry"):
		se_rows = frappe.db.sql(
			"""
			SELECT
				se.work_order,
				se.name,
				se.posting_date,
				se.docstatus,
				se.owner,
				se._assign
			FROM `tabStock Entry` se
			WHERE se.work_order IN %(wos)s
			  AND se.docstatus != 2
			""",
			{"wos": tuple(wo_to_so.keys())},
			as_dict=True,
		)
		for r in se_rows:
			for s in wo_to_so.get(r.work_order, []):
				record_transaction(s, "Stock Entry", r.name, r.posting_date, r.docstatus, "Draft" if r.docstatus == 0 else "Submitted", r.owner, r._assign)

	# 10. Payment Entry (Direct: Sales Order; Indirect: Sales Invoice)
	if "Payment Entry" in permitted_doctypes and doctype_is_available("Payment Entry") and doctype_is_available("Payment Entry Reference"):
		pe_conds = ["(per.reference_doctype = 'Sales Order' AND per.reference_name IN %(sos)s)"]
		pe_vals = {"sos": so_names}
		if si_to_so:
			pe_conds.append("(per.reference_doctype = 'Sales Invoice' AND per.reference_name IN %(sis)s)")
			pe_vals["sis"] = tuple(si_to_so.keys())

		pe_rows = frappe.db.sql(
			f"""
			SELECT
				per.reference_doctype,
				per.reference_name,
				pe.name,
				pe.posting_date,
				pe.status,
				pe.docstatus,
				pe.owner,
				pe._assign
			FROM `tabPayment Entry Reference` per
			JOIN `tabPayment Entry` pe ON pe.name = per.parent
			WHERE pe.docstatus != 2
			  AND ({' OR '.join(pe_conds)})
			""",
			pe_vals,
			as_dict=True,
		)
		for r in pe_rows:
			target_sos = set()
			if r.reference_doctype == "Sales Order" and r.reference_name in so_map:
				target_sos.add(r.reference_name)
			elif r.reference_doctype == "Sales Invoice" and r.reference_name in si_to_so:
				target_sos.update(si_to_so[r.reference_name])
			for s in target_sos:
				record_transaction(s, "Payment Entry", r.name, r.posting_date, r.docstatus, r.status or ("Draft" if r.docstatus == 0 else "Submitted"), r.owner, r._assign)

	# 11. Subcontracting Order (Indirect: via Purchase Order or Production Plan)
	sco_to_so = defaultdict(set)
	if ("Subcontracting Order" in permitted_doctypes or "Subcontracting Receipt" in permitted_doctypes) and doctype_is_available("Subcontracting Order"):
		sco_conds = []
		sco_vals = {}
		if po_to_so:
			sco_conds.append("sco.purchase_order IN %(pos)s")
			sco_vals["pos"] = tuple(po_to_so.keys())
		if pp_to_so:
			sco_conds.append("sco.production_plan IN %(pps)s")
			sco_vals["pps"] = tuple(pp_to_so.keys())

		if sco_conds:
			sco_rows = frappe.db.sql(
				f"""
				SELECT
					sco.purchase_order,
					sco.production_plan,
					sco.name,
					sco.transaction_date AS posting_date,
					sco.status,
					sco.docstatus,
					sco.owner,
					sco._assign
				FROM `tabSubcontracting Order` sco
				WHERE ({' OR '.join(sco_conds)})
				  AND sco.docstatus != 2
				""",
				sco_vals,
				as_dict=True,
			)
			for r in sco_rows:
				target_sos = set()
				if r.purchase_order and r.purchase_order in po_to_so:
					target_sos.update(po_to_so[r.purchase_order])
				if r.production_plan and r.production_plan in pp_to_so:
					target_sos.update(pp_to_so[r.production_plan])
				for s in target_sos:
					sco_to_so[r.name].add(s)
					if "Subcontracting Order" in permitted_doctypes:
						record_transaction(s, "Subcontracting Order", r.name, r.posting_date, r.docstatus, r.status, r.owner, r._assign)

	# 12. Subcontracting Receipt (Indirect: via Subcontracting Order)
	if sco_to_so and "Subcontracting Receipt" in permitted_doctypes and doctype_is_available("Subcontracting Receipt"):
		scr_rows = frappe.db.sql(
			"""
			SELECT
				scr.subcontracting_order,
				scr.name,
				scr.posting_date,
				scr.status,
				scr.docstatus,
				scr.owner,
				scr._assign
			FROM `tabSubcontracting Receipt` scr
			WHERE scr.subcontracting_order IN %(scos)s
			  AND scr.docstatus != 2
			""",
			{"scos": tuple(sco_to_so.keys())},
			as_dict=True,
		)
		for r in scr_rows:
			for s in sco_to_so.get(r.subcontracting_order, []):
				record_transaction(s, "Subcontracting Receipt", r.name, r.posting_date, r.docstatus, r.status or ("Draft" if r.docstatus == 0 else "Completed"), r.owner, r._assign)

	# 13. Pick List (Direct: Pick List Item -> sales_order)
	if "Pick List" in permitted_doctypes and doctype_is_available("Pick List") and doctype_is_available("Pick List Item"):
		pl_rows = frappe.db.sql(
			"""
			SELECT
				pli.sales_order AS so_name,
				pl.name,
				DATE(pl.creation) AS posting_date,
				pl.status,
				pl.docstatus,
				pl.owner,
				pl._assign
			FROM `tabPick List Item` pli
			JOIN `tabPick List` pl ON pl.name = pli.parent
			WHERE pli.sales_order IN %(sos)s
			  AND pl.docstatus != 2
			""",
			{"sos": so_names},
			as_dict=True,
		)
		for r in pl_rows:
			record_transaction(r.so_name, "Pick List", r.name, r.posting_date, r.docstatus, r.status, r.owner, r._assign)

	# 14. Order Modification Request (Direct: sales_order)
	if "Order Modification Request" in permitted_doctypes and doctype_is_available("Order Modification Request"):
		omr_rows = frappe.db.sql(
			"""
			SELECT
				omr.sales_order AS so_name,
				omr.name,
				COALESCE(omr.date, DATE(omr.creation)) AS posting_date,
				omr.workflow_state,
				omr.docstatus,
				omr.owner,
				omr._assign
			FROM `tabOrder Modification Request` omr
			WHERE omr.sales_order IN %(sos)s
			  AND omr.docstatus != 2
			""",
			{"sos": so_names},
			as_dict=True,
		)
		for r in omr_rows:
			record_transaction(r.so_name, "Order Modification Request", r.name, r.posting_date, r.docstatus, r.workflow_state or ("Draft" if r.docstatus == 0 else "Approved"), r.owner, r._assign)

	# 15. BOM (Direct: sales_order; Indirect: via Sales Order Item)
	bom_to_so = defaultdict(set)
	if ("BOM" in permitted_doctypes or "Bom Modification Request" in permitted_doctypes) and doctype_is_available("BOM"):
		bom_rows = frappe.db.sql(
			"""
			SELECT
				COALESCE(b.sales_order, soi.parent) AS so_name,
				b.name,
				DATE(b.creation) AS posting_date,
				b.docstatus,
				b.owner,
				b._assign
			FROM `tabBOM` b
			LEFT JOIN `tabSales Order Item` soi ON soi.bom_no = b.name
			WHERE (b.sales_order IN %(sos)s OR soi.parent IN %(sos)s)
			  AND b.docstatus != 2
			""",
			{"sos": so_names},
			as_dict=True,
		)
		for r in bom_rows:
			if r.so_name:
				bom_to_so[r.name].add(r.so_name)
				if "BOM" in permitted_doctypes:
					record_transaction(r.so_name, "BOM", r.name, r.posting_date, r.docstatus, "Draft" if r.docstatus == 0 else "Submitted", r.owner, r._assign)

	# 16. Bom Modification Request (Indirect: via BOM)
	if bom_to_so and "Bom Modification Request" in permitted_doctypes and doctype_is_available("Bom Modification Request"):
		bmr_rows = frappe.db.sql(
			"""
			SELECT
				bmr.name,
				bmr.bom,
				COALESCE(bmr.date, DATE(bmr.creation)) AS posting_date,
				bmr.workflow_state,
				bmr.docstatus,
				bmr.owner,
				bmr._assign
			FROM `tabBom Modification Request` bmr
			WHERE bmr.bom IN %(boms)s
			  AND bmr.docstatus != 2
			""",
			{"boms": tuple(bom_to_so.keys())},
			as_dict=True,
		)
		for r in bmr_rows:
			for s in bom_to_so.get(r.bom, []):
				record_transaction(s, "Bom Modification Request", r.name, r.posting_date, r.docstatus, r.workflow_state or ("Draft" if r.docstatus == 0 else "Approved"), r.owner, r._assign)

	# 17. Valve Painting (Direct: tabValve Painting Item -> sales_order)
	if "Valve Painting" in permitted_doctypes and doctype_is_available("Valve Painting") and doctype_is_available("Valve Painting Item"):
		vp_rows = frappe.db.sql(
			"""
			SELECT
				vpi.sales_order AS so_name,
				vp.name,
				COALESCE(vp.posting_date, vpi.date, DATE(vp.creation)) AS posting_date,
				vp.docstatus,
				vp.owner,
				vp._assign
			FROM `tabValve Painting Item` vpi
			JOIN `tabValve Painting` vp ON vp.name = vpi.parent
			WHERE vpi.sales_order IN %(sos)s
			  AND vp.docstatus != 2
			""",
			{"sos": so_names},
			as_dict=True,
		)
		for r in vp_rows:
			record_transaction(r.so_name, "Valve Painting", r.name, r.posting_date, r.docstatus, "Draft" if r.docstatus == 0 else "Submitted", r.owner, r._assign)

	# 18. Valve Testing (Direct: tabValve Testing Item -> sales_order)
	if "Valve Testing" in permitted_doctypes and doctype_is_available("Valve Testing") and doctype_is_available("Valve Testing Item"):
		vt_rows = frappe.db.sql(
			"""
			SELECT
				vti.sales_order AS so_name,
				vt.name,
				COALESCE(vt.posting_date, vti.date, DATE(vt.creation)) AS posting_date,
				vt.docstatus,
				vt.owner,
				vt._assign
			FROM `tabValve Testing Item` vti
			JOIN `tabValve Testing` vt ON vt.name = vti.parent
			WHERE vti.sales_order IN %(sos)s
			  AND vt.docstatus != 2
			""",
			{"sos": so_names},
			as_dict=True,
		)
		for r in vt_rows:
			record_transaction(r.so_name, "Valve Testing", r.name, r.posting_date, r.docstatus, "Draft" if r.docstatus == 0 else "Submitted", r.owner, r._assign)

	# 19. Valve Assembly (Direct: tabAssembly Item Serial No -> sales_order)
	if "Valve Assembly" in permitted_doctypes and doctype_is_available("Valve Assembly") and doctype_is_available("Assembly Item Serial No"):
		va_rows = frappe.db.sql(
			"""
			SELECT
				aisn.sales_order AS so_name,
				va.name,
				COALESCE(va.posting_date, aisn.date, DATE(va.creation)) AS posting_date,
				va.docstatus,
				va.owner,
				va._assign
			FROM `tabAssembly Item Serial No` aisn
			JOIN `tabValve Assembly` va ON va.name = aisn.parent
			WHERE aisn.sales_order IN %(sos)s
			  AND va.docstatus != 2
			""",
			{"sos": so_names},
			as_dict=True,
		)
		for r in va_rows:
			record_transaction(r.so_name, "Valve Assembly", r.name, r.posting_date, r.docstatus, "Draft" if r.docstatus == 0 else "Submitted", r.owner, r._assign)

	# 20. Proforma Invoice (Direct: tabProforma Invoice Item -> sales_order)
	if "Proforma Invoice" in permitted_doctypes and doctype_is_available("Proforma Invoice") and doctype_is_available("Proforma Invoice Item"):
		pi_rows = frappe.db.sql(
			"""
			SELECT
				pii.sales_order AS so_name,
				pi.name,
				COALESCE(pi.transaction_date, DATE(pi.creation)) AS posting_date,
				pi.status,
				pi.docstatus,
				pi.owner,
				pi._assign
			FROM `tabProforma Invoice Item` pii
			JOIN `tabProforma Invoice` pi ON pi.name = pii.parent
			WHERE pii.sales_order IN %(sos)s
			  AND pi.docstatus != 2
			""",
			{"sos": so_names},
			as_dict=True,
		)
		for r in pi_rows:
			record_transaction(r.so_name, "Proforma Invoice", r.name, r.posting_date, r.docstatus, r.status or ("Draft" if r.docstatus == 0 else "Submitted"), r.owner, r._assign)


@frappe.whitelist()
def export_transaction_integrity_data(
	from_date=None,
	to_date=None,
	branch=None,
	customer=None,
	sales_order=None,
	transaction_type=None,
	transaction_status=None,
	search_term=None,
):
	"""
	Returns all open transactions flattened for CSV/Excel export.
	"""
	res = get_transaction_integrity_data(
		from_date=from_date,
		to_date=to_date,
		branch=branch,
		customer=customer,
		sales_order=sales_order,
		transaction_type=transaction_type,
		transaction_status=transaction_status,
		search_term=search_term,
		page=1,
		page_length=999999,
	)

	flat_rows = []
	for so in res.get("data", []):
		for tx in so.get("open_transactions", []):
			flat_rows.append({
				"sales_order": so["sales_order"],
				"customer": so["customer"],
				"customer_name": so["customer_name"],
				"so_date": format_date(so["transaction_date"]) if so.get("transaction_date") else "-",
				"branch": so["branch"],
				"so_status": so["status"],
				"transaction_doctype": tx["doctype"],
				"transaction_id": tx["name"],
				"transaction_date": tx.get("posting_date_formatted") or "-",
				"transaction_status": tx["status"],
				"owner": tx.get("owner_name") or tx.get("owner") or "-",
				"responsible_user": tx.get("responsible_user") or "-",
			})

	return flat_rows


def _get_available_branches():
	"""Fetch distinct branches present in Sales Orders."""
	if not frappe.db.has_column("Sales Order", "branch"):
		return []
	rows = frappe.db.sql(
		"""
		SELECT DISTINCT branch
		FROM `tabSales Order`
		WHERE branch IS NOT NULL AND branch != ''
		ORDER BY branch
		""",
		as_dict=True,
	)
	return [r.branch for r in rows]


def _build_empty_response(completed_sos_checked=0):
	return {
		"summary": {
			"completed_sos_checked": completed_sos_checked,
			"sos_with_open_tx": 0,
			"total_open_tx": 0,
			"open_draft_tx": 0,
		},
		"data": [],
		"pagination": {
			"page": 1,
			"page_length": 25,
			"total_records": 0,
			"total_pages": 1,
		},
		"filter_meta": {
			"branches": _get_available_branches(),
			"transaction_types": [dt for dt in TRANSACTION_CONFIG.keys() if frappe.has_permission(dt, "read")],
			"transaction_statuses": [
				"Draft",
				"To Bill",
				"Partly Billed",
				"Not Started",
				"In Process",
				"Submitted",
				"Material Requested",
				"Pending",
				"Ordered",
				"Partially Ordered",
				"Partially Received",
				"To Receive and Bill",
				"To Receive",
				"Open",
				"Material Transferred",
				"Partial Material Transferred",
			],
		},
	}
