# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, date_diff, today, now_datetime

REMARK_CHILD_DT = "SO Approval Remark History"


def execute(filters=None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{"label": _("Sales Order"), "fieldname": "sales_order", "fieldtype": "Link", "options": "Sales Order", "width": 140},
		{"label": _("Order Status"), "fieldname": "order_status", "fieldtype": "Data", "width": 130},
		{"label": _("Order Date"), "fieldname": "order_date", "fieldtype": "Date", "width": 100},
		{"label": _("Order Delivery Date"), "fieldname": "delivery_date", "fieldtype": "Date", "width": 120},
		{"label": _("Sales Person 1"), "fieldname": "sales_person_1", "fieldtype": "Data", "width": 130},
		{"label": _("Sales Person 2"), "fieldname": "sales_person_2", "fieldtype": "Data", "width": 130},
		{"label": _("Customer Name"), "fieldname": "customer_name", "fieldtype": "Data", "width": 220},
		{"label": _("Customer PO Number"), "fieldname": "po_no", "fieldtype": "Data", "width": 160},
		{"label": _("Customer PO Date"), "fieldname": "po_date", "fieldtype": "Date", "width": 110},
		{"label": _("Approved Date"), "fieldname": "approved_date", "fieldtype": "Date", "width": 110},
		{"label": _("Entry Within Days"), "fieldname": "entry_within_days", "fieldtype": "Int", "width": 120},
		{"label": _("Pending Approval Days"), "fieldname": "pending_approval_days", "fieldtype": "Int", "width": 140},
		{"label": _("Approval Within Days"), "fieldname": "approval_within_days", "fieldtype": "Int", "width": 140},
		{"label": _("Total Days"), "fieldname": "total_days", "fieldtype": "Int", "width": 100},
		# Editable from the report (see .js) - latest row of the SO Approval Remark History table
		{"label": _("Remark"), "fieldname": "remark", "fieldtype": "Small Text", "width": 280, "editable": 1},
		{"label": _("Updated On"), "fieldname": "updated_on", "fieldtype": "Date", "width": 100},
	]


def get_data(filters):
	conditions, values = get_conditions(filters)

	orders = frappe.db.sql(
		f"""
		SELECT
			so.name AS sales_order,
			so.status AS order_status,
			so.workflow_state,
			so.transaction_date AS order_date,
			so.delivery_date,
			so.customer_name,
			so.po_no,
			so.po_date,
			DATE(so.creation) AS created_on,
			(
				SELECT DATE(MAX(sc.modification_time))
				FROM `tabState Change Items` sc
				WHERE sc.parent = so.name
					AND sc.parenttype = 'Sales Order'
					AND sc.workflow_state = 'Approved'
			) AS approved_on
		FROM `tabSales Order` so
		WHERE so.docstatus < 2
		{conditions}
		ORDER BY so.transaction_date, so.name
		""",
		values,
		as_dict=True,
	)

	if not orders:
		return []

	names = [d.sales_order for d in orders]
	sales_persons = get_top_two_sales_persons(names)
	remarks = get_latest_remarks(names)
	today_date = getdate(today())
	data = []

	for d in orders:
		is_approved = d.workflow_state == "Approved" and d.approved_on
		approved_date = getdate(d.approved_on) if is_approved else None
		order_date = getdate(d.order_date) if d.order_date else None
		po_date = getdate(d.po_date) if d.po_date else None

		# Entry Within Days = Order Date - Customer PO Date
		entry_days = date_diff(order_date, po_date) if order_date and po_date else 0
		# Pending Approval Days = created date till today (0 once approved)
		pending_days = 0 if approved_date else date_diff(today_date, getdate(d.created_on))
		# Approval Within Days = Approved Date - Order Date
		approval_days = date_diff(approved_date, order_date) if approved_date and order_date else 0

		sp = sales_persons.get(d.sales_order, [])
		rem = remarks.get(d.sales_order, {})

		data.append({
			"sales_order": d.sales_order,
			"order_status": d.order_status,
			"order_date": d.order_date,
			"delivery_date": d.delivery_date,
			"sales_person_1": sp[0] if len(sp) > 0 else None,
			"sales_person_2": sp[1] if len(sp) > 1 else None,
			"customer_name": d.customer_name,
			"po_no": d.po_no,
			"po_date": d.po_date,
			"approved_date": approved_date,
			"entry_within_days": entry_days,
			"pending_approval_days": pending_days,
			"approval_within_days": approval_days,
			"total_days": entry_days + approval_days,
			"remark": rem.get("remark") or "",
			"updated_on": getdate(rem["modified_on"]) if rem.get("modified_on") else None,
		})

	return data


def get_top_two_sales_persons(order_names):
	rows = frappe.db.sql(
		"""
		SELECT parent, sales_person
		FROM `tabSales Team`
		WHERE parenttype = 'Sales Order' AND parent IN %(names)s
		ORDER BY parent, idx
		""",
		{"names": order_names},
		as_dict=True,
	)
	result = {}
	for r in rows:
		result.setdefault(r.parent, [])
		if len(result[r.parent]) < 2:
			result[r.parent].append(r.sales_person)
	return result


def get_latest_remarks(order_names):
	"""Latest row (highest idx) of the remark history child table, per Sales Order."""
	rows = frappe.db.sql(
		f"""
		SELECT parent, remark, modified_on
		FROM `tab{REMARK_CHILD_DT}`
		WHERE parenttype = 'Sales Order' AND parent IN %(names)s
		ORDER BY parent, idx
		""",
		{"names": order_names},
		as_dict=True,
	)
	result = {}
	for r in rows:  # later rows overwrite earlier ones -> latest wins
		result[r.parent] = r
	return result


def get_conditions(filters):
	conditions, values = [], {}

	if filters.get("from_date"):
		conditions.append("AND so.transaction_date >= %(from_date)s")
		values["from_date"] = filters.from_date
	if filters.get("to_date"):
		conditions.append("AND so.transaction_date <= %(to_date)s")
		values["to_date"] = filters.to_date
	if filters.get("sales_order"):
		conditions.append("AND so.name = %(sales_order)s")
		values["sales_order"] = filters.sales_order
	if filters.get("customer"):
		conditions.append("AND so.customer = %(customer)s")
		values["customer"] = filters.customer
	if filters.get("branch"):
		conditions.append("AND so.branch = %(branch)s")
		values["branch"] = filters.branch

	# Same behaviour as Sales Order Register: status filter, else hide Closed/Completed
	status = filters.get("status")
	if isinstance(status, str):
		status = frappe.parse_json(status) if status.startswith("[") else [s.strip() for s in status.split(",") if s.strip()]
	if status:
		conditions.append("AND so.status IN %(status)s")
		values["status"] = tuple(status)
	else:
		conditions.append("AND so.status NOT IN ('Closed', 'Completed')")

	return " " + " ".join(conditions), values


# ---------------------------------------------------------
# EDIT REMARK FROM REPORT
# ---------------------------------------------------------

def get_remark_parentfield():
	"""Find the Table field on Sales Order that points to SO Approval Remark History."""
	fields = frappe.get_meta("Sales Order").get("fields", {"fieldtype": "Table", "options": REMARK_CHILD_DT})
	if not fields:
		frappe.throw(_("Sales Order has no table field linked to {0}").format(REMARK_CHILD_DT))
	return fields[0].fieldname


@frappe.whitelist()
def bulk_update_remarks(changes):
	"""Save multiple remarks at once from the report's Save Changes button.
	changes: JSON string or dict of {sales_order: new_remark}"""
	if isinstance(changes, str):
		try:
			changes = frappe.parse_json(changes)
		except Exception:
			import ast
			try:
				changes = ast.literal_eval(changes)
			except Exception:
				changes = {}
	if not changes or not isinstance(changes, dict):
		return {"updated": 0}

	updated = 0
	parentfield = get_remark_parentfield()
	now = now_datetime()
	user = frappe.session.user

	for so, remark in changes.items():
		remark = (remark or "").strip()
		if not remark:
			continue
		if not frappe.has_permission("Sales Order", "write", so):
			continue

		last = frappe.db.sql(
			f"""
			SELECT remark, idx FROM `tab{REMARK_CHILD_DT}`
			WHERE parent = %s AND parenttype = 'Sales Order' AND parentfield = %s
			ORDER BY idx DESC LIMIT 1
			""",
			(so, parentfield),
			as_dict=True,
		)
		if last and (last[0].remark or "").strip() == remark:
			continue

		row = frappe.get_doc({
			"doctype": REMARK_CHILD_DT,
			"parent": so,
			"parenttype": "Sales Order",
			"parentfield": parentfield,
			"idx": (last[0].idx if last else 0) + 1,
			"modified_by1": user,
			"modified_on": now,
			"remark": remark,
		})
		row.insert(ignore_permissions=True)
		frappe.clear_document_cache("Sales Order", so)
		updated += 1

	return {"updated": updated}


@frappe.whitelist()
def update_remark(sales_order, remark):
	"""Append a new row to the Sales Order's remark history (works on submitted orders too)."""
	remark = (remark or "").strip()
	if not remark:
		frappe.throw(_("Remark cannot be empty"))

	if not frappe.has_permission("Sales Order", "write", sales_order):
		frappe.throw(_("You do not have permission to update Sales Order {0}").format(sales_order), frappe.PermissionError)

	parentfield = get_remark_parentfield()

	last = frappe.db.sql(
		f"""
		SELECT remark, idx FROM `tab{REMARK_CHILD_DT}`
		WHERE parent = %s AND parenttype = 'Sales Order' AND parentfield = %s
		ORDER BY idx DESC LIMIT 1
		""",
		(sales_order, parentfield),
		as_dict=True,
	)
	if last and (last[0].remark or "").strip() == remark:
		return {"changed": False, "remark": remark}

	row = frappe.get_doc({
		"doctype": REMARK_CHILD_DT,
		"parent": sales_order,
		"parenttype": "Sales Order",
		"parentfield": parentfield,
		"idx": (last[0].idx if last else 0) + 1,
		"modified_by1": frappe.session.user,
		"modified_on": now_datetime(),
		"remark": remark,
	})
	# Insert the child row directly: the parent may be submitted, so no parent save/validation
	row.insert(ignore_permissions=True)
	frappe.clear_document_cache("Sales Order", sales_order)

	return {"changed": True, "remark": remark}