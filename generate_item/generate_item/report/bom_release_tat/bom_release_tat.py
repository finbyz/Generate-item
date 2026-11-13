# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import add_days, add_months, date_diff, get_datetime, getdate, nowdate, today


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = get_columns()
	data = get_data(filters)
	return columns, data, None, None, get_report_summary(data)


def get_columns():
	return [
		{"label": _("BOM"), "fieldname": "bom", "fieldtype": "Link", "options": "BOM", "width": 180},
		{"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 150},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 200},
		{"label": _("Branch"), "fieldname": "branch", "fieldtype": "Data", "width": 110},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 120},
		{"label": _("Created By"), "fieldname": "created_by", "fieldtype": "Data", "width": 160},
		{"label": _("Created Date"), "fieldname": "created_date", "fieldtype": "Date", "width": 110},
		{"label": _("Approved Date"), "fieldname": "approved_date", "fieldtype": "Date", "width": 110},
		{"label": _("Pending Approval Days"), "fieldname": "pending_approval_days", "fieldtype": "Int", "width": 140},
		{"label": _("Approval Within Days"), "fieldname": "approval_within_days", "fieldtype": "Int", "width": 140},
		{"label": _("Approval TAT (Hrs)"), "fieldname": "approval_tat_hrs", "fieldtype": "Float", "width": 130},
		{"label": _("Modifications"), "fieldname": "modifications", "fieldtype": "Int", "width": 110},
		{"label": _("Last Modification"), "fieldname": "last_modification", "fieldtype": "Link", "options": "Bom Modification Request", "width": 180},
		{"label": _("Last Mod Date"), "fieldname": "last_mod_date", "fieldtype": "Date", "width": 110},
		{"label": _("Last Mod By"), "fieldname": "last_mod_by", "fieldtype": "Data", "width": 150},
		{"label": _("Last Mod Reason"), "fieldname": "last_mod_reason", "fieldtype": "Small Text", "width": 200},
		{"label": _("Days Since Last Mod"), "fieldname": "days_since_last_mod", "fieldtype": "Int", "width": 140},
	]


def get_data(filters):
	conditions, values = get_conditions(filters)
	rows = frappe.db.sql(
		f"""
		WITH state_history AS (
			SELECT
				parent,
				MIN(CASE WHEN workflow_state = 'Approved' THEN modification_time END) AS first_approved_at,
				MIN(CASE WHEN workflow_state = 'Draft' THEN modification_time END) AS first_draft_at
			FROM `tabState Change Items`
			WHERE parenttype = 'BOM'
				AND workflow_state IN ('Draft', 'Approved')
			GROUP BY parent
		),
		modification_counts AS (
			SELECT bom, COUNT(*) AS modification_count
			FROM `tabBom Modification Request`
			WHERE docstatus = 1
			GROUP BY bom
		),
		modification_ranked AS (
			SELECT
				m.bom,
				m.name,
				m.creation,
				m.owner,
				m.workflow_state,
				m.reason_for_change,
				ROW_NUMBER() OVER (
					PARTITION BY m.bom
					ORDER BY m.creation DESC, m.name DESC
				) AS rn
			FROM `tabBom Modification Request` m
			WHERE m.docstatus = 1
		),
		modification_summary AS (
			SELECT
				modification_ranked.*,
				modification_counts.modification_count
			FROM modification_ranked
			INNER JOIN modification_counts ON modification_counts.bom = modification_ranked.bom
			WHERE modification_ranked.rn = 1
		)
		SELECT
			b.name AS bom,
			b.item AS item_code,
			b.item_name,
			b.branch,
			b.workflow_state AS status,
			COALESCE(created_user.full_name, b.owner) AS created_by,
			DATE(b.creation) AS created_date,
			DATE(state_history.first_approved_at) AS approved_date,
			state_history.first_approved_at,
			state_history.first_draft_at,
			COALESCE(modification_summary.modification_count, 0) AS modifications,
			modification_summary.name AS last_modification,
			DATE(modification_summary.creation) AS last_mod_date,
			COALESCE(modified_user.full_name, modification_summary.owner) AS last_mod_by,
			modification_summary.workflow_state AS last_mod_state,
			modification_summary.reason_for_change AS last_mod_reason
		FROM `tabBOM` b
		LEFT JOIN state_history ON state_history.parent = b.name
		LEFT JOIN modification_summary ON modification_summary.bom = b.name
		LEFT JOIN `tabUser` created_user ON created_user.name = b.owner
		LEFT JOIN `tabUser` modified_user ON modified_user.name = modification_summary.owner
		WHERE 1 = 1
			{conditions}
		ORDER BY b.creation DESC, b.name
		""",
		values,
		as_dict=True,
	)

	if not rows:
		return []

	today_date = getdate(today())
	data = []
	for row in rows:
		created_date = getdate(row.created_date)
		approved_date = getdate(row.approved_date) if row.approved_date else None
		pending_days = 0 if approved_date else date_diff(today_date, created_date)
		approval_days = date_diff(approved_date, created_date) if approved_date else 0
		approval_tat_hrs = None
		if row.first_draft_at and row.first_approved_at:
			approval_tat_hrs = round(
				(get_datetime(row.first_approved_at) - get_datetime(row.first_draft_at)).total_seconds() / 3600,
				2,
			)

		last_mod_date = getdate(row.last_mod_date) if row.last_mod_date else None
		data.append({
			"bom": row.bom,
			"item_code": row.item_code,
			"item_name": row.item_name,
			"branch": row.branch,
			"status": row.status,
			"created_by": row.created_by,
			"created_date": created_date,
			"approved_date": approved_date,
			"pending_approval_days": pending_days,
			"approval_within_days": approval_days,
			"approval_tat_hrs": approval_tat_hrs,
			"modifications": row.modifications,
			"last_modification": row.last_modification,
			"last_mod_date": last_mod_date,
			"last_mod_by": row.last_mod_by,
			"last_mod_state": row.last_mod_state,
			"last_mod_reason": row.last_mod_reason,
			"days_since_last_mod": date_diff(today_date, last_mod_date) if last_mod_date else None,
		})

	return data


def get_report_summary(data):
	draft_rows = [row for row in data if row.get("status") == "Draft"]
	approved_days = [
		row.get("approval_within_days", 0)
		for row in data
		if row.get("approved_date")
	]
	average_approval_days = sum(approved_days) / len(approved_days) if approved_days else 0
	oldest_pending = max(
		(row.get("pending_approval_days", 0) for row in draft_rows),
		default=0,
	)

	return [
		{"value": len(draft_rows), "label": _("Draft Pending"), "datatype": "Int", "indicator": "orange"},
		{"value": round(average_approval_days, 2), "label": _("Avg Approval Days"), "datatype": "Float", "indicator": "blue"},
		{"value": oldest_pending, "label": _("Oldest Pending (days)"), "datatype": "Int", "indicator": "red" if oldest_pending else "blue"},
		{"value": sum(row.get("modifications", 0) for row in data), "label": _("Total Modifications"), "datatype": "Int", "indicator": "blue"},
	]


def resolve_period(period):
	import datetime

	today_date = getdate(nowdate())
	if not period or period == "Custom":
		return None, None

	if period == "Today":
		return today_date, today_date
	elif period == "This Week":
		start = today_date - datetime.timedelta(days=today_date.weekday())
		return start, today_date
	elif period == "Last Week":
		start = today_date - datetime.timedelta(days=today_date.weekday() + 7)
		return start, start + datetime.timedelta(days=6)
	elif period == "This Month":
		return today_date.replace(day=1), today_date
	elif period == "Last Month":
		last_day_prev_month = today_date.replace(day=1) - datetime.timedelta(days=1)
		return last_day_prev_month.replace(day=1), last_day_prev_month
	elif period == "This Quarter":
		return add_months(today_date, -3), today_date
	elif period == "Last Quarter":
		this_q_start = add_months(today_date, -3)
		last_q_end = add_days(this_q_start, -1)
		return add_months(this_q_start, -3), last_q_end
	elif period == "This Year":
		return today_date.replace(month=1, day=1), today_date
	elif period == "Last Year":
		start = today_date.replace(year=today_date.year - 1, month=1, day=1)
		return start, today_date.replace(year=today_date.year - 1, month=12, day=31)
	return None, None


def get_conditions(filters):
	filters = frappe._dict(filters or {})
	conditions, values = [], {}

	period = filters.get("period")
	if period and period != "Custom":
		p_from, p_to = resolve_period(period)
		if p_from and not filters.get("from_date"):
			filters["from_date"] = p_from
		if p_to and not filters.get("to_date"):
			filters["to_date"] = p_to

	if filters.get("from_date"):
		conditions.append("AND b.creation >= %(from_date)s")
		values["from_date"] = filters.from_date
	if filters.get("to_date"):
		conditions.append("AND b.creation < DATE_ADD(%(to_date)s, INTERVAL 1 DAY)")
		values["to_date"] = filters.to_date
	if filters.get("bom"):
		conditions.append("AND b.name = %(bom)s")
		values["bom"] = filters.bom
	if filters.get("item"):
		conditions.append("AND (b.item = %(item)s OR b.item_name LIKE %(item_like)s)")
		values["item"] = filters.item
		values["item_like"] = f"%{filters.item}%"
	if filters.get("branch"):
		conditions.append("AND b.branch = %(branch)s")
		values["branch"] = filters.branch
	if filters.get("owner"):
		conditions.append("AND b.owner = %(owner)s")
		values["owner"] = filters.owner

	status = filters.get("status")
	if isinstance(status, str):
		status = frappe.parse_json(status) if status.strip().startswith("[") else status.split(",")
	if isinstance(status, str):
		status = [status]
	if status:
		status = [value.strip() for value in status if value and value.strip()]
		if status:
			conditions.append("AND b.workflow_state IN %(status)s")
			values["status"] = tuple(status)

	conditions.extend([
		"AND LEFT(b.name, 5) != 'TEST-'",
		"AND COALESCE(LEFT(b.item, 5), '') != 'TEST-'",
		"AND COALESCE(LEFT(b.item_name, 5), '') != 'TEST-'",
		"AND b.owner != 'Administrator'",
		"AND LOWER(RIGHT(b.owner, LENGTH('@finbyz.tech'))) != '@finbyz.tech'",
	])

	return " " + " ".join(conditions), values


@frappe.whitelist()
def get_bom_timeline(bom: str):
	if not frappe.has_permission("BOM", "read", bom):
		frappe.throw(_("You do not have permission to view BOM {0}").format(bom), frappe.PermissionError)

	return frappe.db.sql(
		"""
		WITH first_approved AS (
			SELECT parent, MIN(modification_time) AS approved_at
			FROM `tabState Change Items`
			WHERE parenttype = 'BOM' AND workflow_state = 'Approved' AND parent = %(bom)s
			GROUP BY parent
		)
		SELECT
			timeline.event_type,
			timeline.event_date,
			COALESCE(user.full_name, timeline.user_id) AS user_name,
			timeline.state,
			timeline.reason,
			timeline.reference_name
		FROM (
			SELECT
				'Created' AS event_type,
				b.creation AS event_date,
				b.owner AS user_id,
				'Created' AS state,
				NULL AS reason,
				b.name AS reference_name
			FROM `tabBOM` b
			WHERE b.name = %(bom)s
			UNION ALL
			SELECT
				'Approved',
				sc.modification_time,
				sc.username,
				sc.workflow_state,
				NULL,
				sc.parent
			FROM `tabState Change Items` sc
			INNER JOIN first_approved ON first_approved.parent = sc.parent
				AND first_approved.approved_at = sc.modification_time
			WHERE sc.parent = %(bom)s
				AND sc.parenttype = 'BOM'
				AND sc.workflow_state = 'Approved'
			UNION ALL
			SELECT
				'Modification Request',
				m.creation,
				m.owner,
				m.workflow_state,
				m.reason_for_change,
				m.name
			FROM `tabBom Modification Request` m
			WHERE m.bom = %(bom)s AND m.docstatus = 1
		) timeline
		LEFT JOIN `tabUser` user ON user.name = timeline.user_id
		ORDER BY timeline.event_date, timeline.event_type, timeline.reference_name
		""",
		{"bom": bom},
		as_dict=True,
	)
