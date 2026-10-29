# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate


def execute(filters: dict | None = None):
	"""Return columns, data, message, chart, and report_summary for Job Card Report.

	This report provides an end-to-end view of Job Card operations, workstation operators,
	planned vs actual times, production quantities, and quality control (QC) status.
	"""
	filters = frappe._dict(filters or {})
	columns = get_columns()
	data = get_data(filters)
	report_summary = get_report_summary(data)
	chart = get_chart(data)

	message = None
	if not data:
		message = _("No Job Cards found matching the selected filters.")

	return columns, data, message, chart, report_summary


def get_columns() -> list[dict]:
	"""Return column definitions for the Job Card Report."""
	return [
		# A. Job Card Information
		{
			"label": _("Job Card ID"),
			"fieldname": "job_card",
			"fieldtype": "Link",
			"options": "Job Card",
			"width": 140,
		},
		{
			"label": _("Posting Date"),
			"fieldname": "posting_date",
			"fieldtype": "Date",
			"width": 105,
		},
		{
			"label": _("Job Card Status"),
			"fieldname": "status",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Work Order"),
			"fieldname": "work_order",
			"fieldtype": "Link",
			"options": "Work Order",
			"width": 130,
		},
		{
			"label": _("BOM"),
			"fieldname": "bom_no",
			"fieldtype": "Link",
			"options": "BOM",
			"width": 160,
		},
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 160,
		},
		{
			"label": _("Branch"),
			"fieldname": "branch",
			"fieldtype": "Link",
			"options": "Branch",
			"width": 110,
		},
		{
			"label": _("Production Item Code"),
			"fieldname": "production_item",
			"fieldtype": "Link",
			"options": "Item",
			"width": 140,
		},
		{
			"label": _("Production Item Name"),
			"fieldname": "item_name",
			"fieldtype": "Data",
			"width": 170,
		},
		# B. Operation and Workstation
		{
			"label": _("Operation"),
			"fieldname": "operation",
			"fieldtype": "Link",
			"options": "Operation",
			"width": 130,
		},
		{
			"label": _("Workstation"),
			"fieldname": "workstation",
			"fieldtype": "Link",
			"options": "Workstation",
			"width": 130,
		},
		{
			"label": _("Workstation Type"),
			"fieldname": "workstation_type",
			"fieldtype": "Link",
			"options": "Workstation Type",
			"width": 130,
		},
		# C. Operator Information
		{
			"label": _("Employee ID"),
			"fieldname": "employee",
			"fieldtype": "Data",
			"width": 130,
		},
		{
			"label": _("Employee Name"),
			"fieldname": "employee_name",
			"fieldtype": "Data",
			"width": 160,
		},
		# D. Time Tracking
		{
			"label": _("Planned Start Time"),
			"fieldname": "planned_start_time",
			"fieldtype": "Datetime",
			"width": 150,
		},
		{
			"label": _("Planned End Time"),
			"fieldname": "planned_end_time",
			"fieldtype": "Datetime",
			"width": 150,
		},
		{
			"label": _("Planned Time (Mins)"),
			"fieldname": "planned_time_in_mins",
			"fieldtype": "Float",
			"width": 125,
		},
		{
			"label": _("Actual Start Time"),
			"fieldname": "actual_start_time",
			"fieldtype": "Datetime",
			"width": 150,
		},
		{
			"label": _("Actual End Time"),
			"fieldname": "actual_end_time",
			"fieldtype": "Datetime",
			"width": 150,
		},
		{
			"label": _("Actual Time (Mins)"),
			"fieldname": "actual_time_in_mins",
			"fieldtype": "Float",
			"width": 125,
		},
		{
			"label": _("Time Variance (Mins)"),
			"fieldname": "time_variance_in_mins",
			"fieldtype": "Float",
			"width": 130,
		},
		# E. Production Quantities
		{
			"label": _("Planned Qty"),
			"fieldname": "planned_qty",
			"fieldtype": "Float",
			"width": 105,
		},
		{
			"label": _("Completed Qty"),
			"fieldname": "completed_qty",
			"fieldtype": "Float",
			"width": 110,
		},
		{
			"label": _("Transferred Qty"),
			"fieldname": "transferred_qty",
			"fieldtype": "Float",
			"width": 110,
		},
		{
			"label": _("Rejected Qty"),
			"fieldname": "rejected_qty",
			"fieldtype": "Float",
			"width": 105,
		},
		{
			"label": _("Pending Qty"),
			"fieldname": "pending_qty",
			"fieldtype": "Float",
			"width": 105,
		},
		{
			"label": _("Completion %"),
			"fieldname": "completion_percentage",
			"fieldtype": "Percent",
			"width": 105,
		},
		# F. Quality Control
		{
			"label": _("QC Status"),
			"fieldname": "qc_status",
			"fieldtype": "Data",
			"width": 115,
		},
		{
			"label": _("QC/Inspection Reference"),
			"fieldname": "qc_reference",
			"fieldtype": "Link",
			"options": "Quality Inspection",
			"width": 150,
		},
		{
			"label": _("Inspection Result"),
			"fieldname": "inspection_result",
			"fieldtype": "Data",
			"width": 125,
		},
		{
			"label": _("Accepted Qty"),
			"fieldname": "accepted_qty",
			"fieldtype": "Float",
			"width": 105,
		},
		{
			"label": _("QC Rejected Qty"),
			"fieldname": "qc_rejected_qty",
			"fieldtype": "Float",
			"width": 110,
		},
		{
			"label": _("QC Inspector"),
			"fieldname": "qc_inspector",
			"fieldtype": "Data",
			"width": 130,
		},
		{
			"label": _("Inspection Date"),
			"fieldname": "inspection_date",
			"fieldtype": "Date",
			"width": 110,
		},
		{
			"label": _("QC Remarks / Rejection Reason"),
			"fieldname": "qc_remarks",
			"fieldtype": "Data",
			"width": 180,
		},
	]


def get_data(filters: dict) -> list[dict]:
	"""Fetch, calculate, and aggregate Job Card data ensuring exactly one row per Job Card."""
	conditions, values = build_conditions(filters)

	# Fetch primary Job Card records joined with Work Order and Workstation
	sql = f"""
		SELECT
			jc.name AS job_card,
			jc.posting_date,
			jc.creation,
			jc.status,
			jc.docstatus,
			jc.is_paused,
			jc.work_order,
			jc.bom_no,
			jc.company,
			wo.branch AS branch,
			jc.production_item,
			COALESCE(jc.item_name, item.item_name, jc.production_item) AS item_name,
			jc.operation,
			jc.workstation,
			COALESCE(jc.workstation_type, ws.workstation_type) AS workstation_type,
			jc.expected_start_date,
			jc.expected_end_date,
			jc.time_required,
			jc.actual_start_date,
			jc.actual_end_date,
			jc.total_time_in_mins,
			jc.for_quantity AS planned_qty,
			jc.total_completed_qty AS completed_qty,
			jc.transferred_qty,
			jc.process_loss_qty,
			jc.pending_qty,
			jc.quality_inspection,
			jc.quality_inspection_template
		FROM `tabJob Card` jc
		LEFT JOIN `tabWork Order` wo ON wo.name = jc.work_order
		LEFT JOIN `tabWorkstation` ws ON ws.name = jc.workstation
		LEFT JOIN `tabItem` item ON item.name = jc.production_item
		WHERE 1=1 {conditions}
		ORDER BY jc.posting_date DESC, jc.name DESC
	"""

	jc_rows = frappe.db.sql(sql, values, as_dict=True)
	if not jc_rows:
		return []

	job_card_names = [r.job_card for r in jc_rows]
	direct_qi_names = [r.quality_inspection for r in jc_rows if r.quality_inspection]

	# Aggregated Scheduled Time Logs
	scheduled_map = get_scheduled_time_map(job_card_names)

	# Aggregated Actual Time Logs
	actual_map = get_actual_time_map(job_card_names)

	# Aggregated Operators / Employees
	emp_map = get_employee_map(job_card_names)

	# Aggregated Rejections
	rejections_map = get_rejections_map(job_card_names)

	# Linked Quality Inspections
	qi_map = get_quality_inspection_map(job_card_names, direct_qi_names)

	final_data = []
	for r in jc_rows:
		jc_id = r.job_card

		# 1. Operators
		ops = emp_map.get(jc_id, [])
		emp_ids = ", ".join(dict.fromkeys(o.employee for o in ops if o.employee))
		emp_names = ", ".join(dict.fromkeys(o.employee_name or o.employee for o in ops if o.employee))

		# 2. Time Tracking
		st = scheduled_map.get(jc_id)
		planned_start = st.planned_start_time if st and st.planned_start_time else r.expected_start_date
		planned_end = st.planned_end_time if st and st.planned_end_time else r.expected_end_date
		planned_time = flt(st.planned_time_in_mins) if st and st.planned_time_in_mins is not None else flt(r.time_required)

		at = actual_map.get(jc_id)
		actual_start = at.actual_start_time if at and at.actual_start_time else (r.actual_start_date if at else None)
		actual_end = at.actual_end_time if at and at.actual_end_time else (r.actual_end_date if at else None)
		actual_time = flt(at.actual_time_in_mins) if at and at.actual_time_in_mins is not None else flt(r.total_time_in_mins)

		time_variance = round(actual_time - planned_time, 2) if actual_start and actual_end else 0

		# 3. Quality Control (QC) - Resolved first so rejections and results are available
		qi = qi_map.get(jc_id)
		if qi:
			qc_ref = qi.qc_reference
			raw_st = (qi.qc_status_raw or "").strip()
			if raw_st == "Accepted":
				qc_st = "PASS"
				insp_res = _("Accepted")
			elif raw_st in ("Rejected", "Cancelled"):
				qc_st = "FAIL"
				insp_res = _(raw_st)
			else:
				qc_st = "PENDING"
				insp_res = _("Under Inspection") if qi.docstatus == 0 else (raw_st or _("Draft"))

			qc_accepted = flt(qi.accepted_qty) if qc_st == "PASS" else 0.0
			qc_rejected = flt(qi.accepted_qty) if qc_st == "FAIL" else 0.0
			qc_inspector = qi.qc_inspector_name or qi.qc_inspector
			insp_date = qi.inspection_date
			qc_rem = qi.qc_remarks or ""
		else:
			qc_ref = None
			if r.quality_inspection_template:
				qc_st = "PENDING"
				insp_res = _("Pending Inspection")
			else:
				qc_st = "NOT REQUIRED"
				insp_res = _("Not Required")
			qc_accepted = 0.0
			qc_rejected = 0.0
			qc_inspector = None
			insp_date = None
			qc_rem = ""

		# 4. Status normalization
		display_status = r.status
		if r.docstatus == 2:
			display_status = "Cancelled"
		elif getattr(r, "is_paused", 0) and r.status != "Completed":
			display_status = "On Hold"

		# 5. Production Quantities
		planned_q = flt(r.planned_qty)
		completed_q = flt(r.completed_qty)
		transferred_q = flt(r.transferred_qty)

		# Rejections: aggregate from Job Card Rejections table, process loss, or failed QC
		rej = rejections_map.get(jc_id)
		rejected_from_log = flt(rej.rejected_qty) if rej and rej.rejected_qty is not None else 0.0
		process_loss = flt(r.process_loss_qty)
		rejected_q = max(rejected_from_log, qc_rejected, process_loss)
		if not qc_rem and rej and rej.rejection_reasons:
			qc_rem = rej.rejection_reasons

		# Pending Quantity:
		# If Job Card is Completed or Cancelled, no further production is pending.
		# For active Job Cards (Open, Work In Progress, On Hold), Pending represents
		# the remaining balance needed to reach the planned quantity (Planned - Completed).
		if display_status in ("Completed", "Cancelled") or r.docstatus == 2:
			pending_q = 0.0
		elif flt(r.get("pending_qty")) > 0:
			pending_q = flt(r.get("pending_qty"))
		else:
			pending_q = max(0.0, planned_q - completed_q)

		completion_pct = round((completed_q / planned_q) * 100, 2) if planned_q > 0 else 0.0

		# Check QC status filter post-computation
		if filters.get("qc_status") and filters.get("qc_status") != qc_st:
			continue

		row = {
			"job_card": jc_id,
			"posting_date": r.posting_date or getdate(r.creation),
			"status": display_status,
			"work_order": r.work_order,
			"bom_no": r.bom_no,
			"company": r.company,
			"branch": r.branch,
			"production_item": r.production_item,
			"item_name": r.item_name,
			"operation": r.operation,
			"workstation": r.workstation,
			"workstation_type": r.workstation_type,
			"employee": emp_ids,
			"employee_name": emp_names,
			"planned_start_time": planned_start,
			"planned_end_time": planned_end,
			"planned_time_in_mins": planned_time,
			"actual_start_time": actual_start,
			"actual_end_time": actual_end,
			"actual_time_in_mins": actual_time,
			"time_variance_in_mins": time_variance,
			"planned_qty": planned_q,
			"completed_qty": completed_q,
			"transferred_qty": transferred_q,
			"rejected_qty": rejected_q,
			"pending_qty": pending_q,
			"completion_percentage": completion_pct,
			"qc_status": qc_st,
			"qc_reference": qc_ref,
			"inspection_result": insp_res,
			"accepted_qty": qc_accepted,
			"qc_rejected_qty": qc_rejected,
			"qc_inspector": qc_inspector,
			"inspection_date": insp_date,
			"qc_remarks": qc_rem,
		}
		final_data.append(row)

	return final_data


def build_conditions(filters: dict) -> tuple[str, dict]:
	"""Build parameterized SQL conditions based on report filters."""
	conditions = []
	values = {}

	if filters.get("company"):
		conditions.append("jc.company = %(company)s")
		values["company"] = filters.get("company")

	if filters.get("branch"):
		conditions.append("wo.branch = %(branch)s")
		values["branch"] = filters.get("branch")

	if filters.get("from_date"):
		conditions.append("COALESCE(jc.posting_date, DATE(jc.creation)) >= %(from_date)s")
		values["from_date"] = filters.get("from_date")

	if filters.get("to_date"):
		conditions.append("COALESCE(jc.posting_date, DATE(jc.creation)) <= %(to_date)s")
		values["to_date"] = filters.get("to_date")

	if filters.get("work_order"):
		conditions.append("jc.work_order = %(work_order)s")
		values["work_order"] = filters.get("work_order")

	if filters.get("job_card"):
		conditions.append("jc.name = %(job_card)s")
		values["job_card"] = filters.get("job_card")

	if filters.get("production_item"):
		conditions.append("jc.production_item = %(production_item)s")
		values["production_item"] = filters.get("production_item")

	if filters.get("operation"):
		conditions.append("jc.operation = %(operation)s")
		values["operation"] = filters.get("operation")

	if filters.get("workstation"):
		conditions.append("jc.workstation = %(workstation)s")
		values["workstation"] = filters.get("workstation")

	if filters.get("status"):
		if filters.get("status") == "Cancelled":
			conditions.append("jc.docstatus = 2")
		elif filters.get("status") == "On Hold":
			conditions.append("(jc.status = 'On Hold' OR jc.is_paused = 1)")
		else:
			conditions.append("jc.status = %(status)s AND jc.docstatus != 2")
			values["status"] = filters.get("status")

	if filters.get("operator"):
		conditions.append("""
			jc.name IN (
				SELECT DISTINCT parent
				FROM `tabJob Card Time Log`
				WHERE employee = %(operator)s
			)
		""")
		values["operator"] = filters.get("operator")

	cond_str = ("AND " + " AND ".join(conditions)) if conditions else ""
	return cond_str, values


def get_scheduled_time_map(job_card_names: list[str]) -> dict:
	"""Fetch aggregated scheduled start, end, and duration per Job Card."""
	scheduled_map = {}
	if not job_card_names:
		return scheduled_map

	st_rows = frappe.db.sql(
		"""
		SELECT
			parent,
			MIN(from_time) AS planned_start_time,
			MAX(to_time) AS planned_end_time,
			SUM(time_in_mins) AS planned_time_in_mins
		FROM `tabJob Card Scheduled Time`
		WHERE parent IN %(job_card_names)s
		GROUP BY parent
	""",
		{"job_card_names": tuple(job_card_names)},
		as_dict=True,
	)

	for st in st_rows:
		scheduled_map[st.parent] = st
	return scheduled_map


def get_actual_time_map(job_card_names: list[str]) -> dict:
	"""Fetch aggregated actual start, end, and duration from actual work time logs."""
	actual_map = {}
	if not job_card_names:
		return actual_map

	at_rows = frappe.db.sql(
		"""
		SELECT
			parent,
			MIN(from_time) AS actual_start_time,
			MAX(to_time) AS actual_end_time,
			SUM(time_in_mins) AS actual_time_in_mins
		FROM `tabJob Card Time Log`
		WHERE parent IN %(job_card_names)s
		  AND parentfield = 'time_logs'
		GROUP BY parent
	""",
		{"job_card_names": tuple(job_card_names)},
		as_dict=True,
	)

	for at in at_rows:
		actual_map[at.parent] = at
	return actual_map


def get_employee_map(job_card_names: list[str]) -> dict:
	"""Fetch distinct assigned or active operators/employees for each Job Card."""
	emp_map = {}
	if not job_card_names:
		return emp_map

	emp_rows = frappe.db.sql(
		"""
		SELECT DISTINCT
			jctl.parent,
			jctl.employee,
			emp.employee_name
		FROM `tabJob Card Time Log` jctl
		LEFT JOIN `tabEmployee` emp ON emp.name = jctl.employee
		WHERE jctl.parent IN %(job_card_names)s
		  AND jctl.employee IS NOT NULL
		  AND jctl.employee != ''
		ORDER BY jctl.parent, jctl.employee
	""",
		{"job_card_names": tuple(job_card_names)},
		as_dict=True,
	)

	for er in emp_rows:
		emp_map.setdefault(er.parent, []).append(er)
	return emp_map


def get_rejections_map(job_card_names: list[str]) -> dict:
	"""Fetch aggregated rejection quantities and reasons from Job Card Rejections table."""
	rejections_map = {}
	if not job_card_names:
		return rejections_map

	rej_rows = frappe.db.sql(
		"""
		SELECT
			parent,
			SUM(CAST(qty AS DECIMAL(18, 4))) AS rejected_qty,
			GROUP_CONCAT(DISTINCT reason SEPARATOR ', ') AS rejection_reasons
		FROM `tabJob Card Rejections`
		WHERE parent IN %(job_card_names)s
		GROUP BY parent
	""",
		{"job_card_names": tuple(job_card_names)},
		as_dict=True,
	)

	for rj in rej_rows:
		rejections_map[rj.parent] = rj
	return rejections_map


def get_quality_inspection_map(job_card_names: list[str], direct_qi_names: list[str]) -> dict:
	"""Fetch Quality Inspection records linked to Job Cards."""
	qi_map = {}
	if not job_card_names:
		return qi_map

	qi_conds = ["qi.reference_type = 'Job Card' AND qi.reference_name IN %(job_card_names)s"]
	qi_vals = {"job_card_names": tuple(job_card_names)}
	if direct_qi_names:
		qi_conds.append("qi.name IN %(direct_qi_names)s")
		qi_vals["direct_qi_names"] = tuple(direct_qi_names)

	qi_rows = frappe.db.sql(
		f"""
		SELECT
			qi.name AS qc_reference,
			qi.reference_type,
			qi.reference_name,
			qi.status AS qc_status_raw,
			qi.docstatus,
			qi.sample_size AS accepted_qty,
			qi.inspected_by AS qc_inspector,
			COALESCE(u.full_name, qi.inspected_by) AS qc_inspector_name,
			qi.report_date AS inspection_date,
			qi.remarks AS qc_remarks
		FROM `tabQuality Inspection` qi
		LEFT JOIN `tabUser` u ON u.name = qi.inspected_by
		WHERE ({' OR '.join(qi_conds)})
		ORDER BY qi.creation DESC
	""",
		qi_vals,
		as_dict=True,
	)

	for qi in qi_rows:
		if qi.reference_type == "Job Card" and qi.reference_name:
			if qi.reference_name not in qi_map:
				qi_map[qi.reference_name] = qi
		if qi.qc_reference:
			for jc_id in job_card_names:
				if jc_id not in qi_map and qi.reference_name == jc_id:
					qi_map[jc_id] = qi

	return qi_map


def get_report_summary(data: list[dict]) -> list[dict]:
	"""Generate top KPI dashboard summary cards from the filtered dataset."""
	if not data:
		return []

	total_jc = len(data)
	total_planned_qty = sum(flt(r.get("planned_qty")) for r in data)
	total_completed_qty = sum(flt(r.get("completed_qty")) for r in data)
	total_pending_qty = sum(flt(r.get("pending_qty")) for r in data)
	total_rejected_qty = sum(flt(r.get("rejected_qty")) for r in data)

	total_planned_time = sum(flt(r.get("planned_time_in_mins")) for r in data)
	total_actual_time = sum(flt(r.get("actual_time_in_mins")) for r in data)

	qc_pass_count = sum(1 for r in data if r.get("qc_status") == "PASS")
	qc_fail_count = sum(1 for r in data if r.get("qc_status") == "FAIL")
	qc_pending_count = sum(1 for r in data if r.get("qc_status") == "PENDING")

	return [
		{
			"value": total_jc,
			"label": _("Total Job Cards"),
			"datatype": "Int",
			"indicator": "blue",
		},
		{
			"value": total_planned_qty,
			"label": _("Total Planned Qty"),
			"datatype": "Float",
			"indicator": "blue",
		},
		{
			"value": total_completed_qty,
			"label": _("Total Completed Qty"),
			"datatype": "Float",
			"indicator": "green",
		},
		{
			"value": total_pending_qty,
			"label": _("Total Pending Qty"),
			"datatype": "Float",
			"indicator": "orange" if total_pending_qty > 0 else "gray",
		},
		{
			"value": total_rejected_qty,
			"label": _("Total Rejected Qty"),
			"datatype": "Float",
			"indicator": "red" if total_rejected_qty > 0 else "gray",
		},
		{
			"value": total_planned_time,
			"label": _("Total Planned Time (Mins)"),
			"datatype": "Float",
			"indicator": "purple",
		},
		{
			"value": total_actual_time,
			"label": _("Total Actual Time (Mins)"),
			"datatype": "Float",
			"indicator": "orange" if total_actual_time > total_planned_time else "green",
		},
		{
			"value": qc_pass_count,
			"label": _("QC Pass Count"),
			"datatype": "Int",
			"indicator": "green",
		},
		{
			"value": qc_fail_count,
			"label": _("QC Fail Count"),
			"datatype": "Int",
			"indicator": "red" if qc_fail_count > 0 else "gray",
		},
		{
			"value": qc_pending_count,
			"label": _("QC Pending Count"),
			"datatype": "Int",
			"indicator": "orange" if qc_pending_count > 0 else "gray",
		},
	]


def get_chart(data: list[dict]) -> dict | None:
	"""Generate a clean visual bar chart showing Planned, Completed, and Pending quantities."""
	if not data:
		return None

	total_planned_qty = sum(flt(r.get("planned_qty")) for r in data)
	total_completed_qty = sum(flt(r.get("completed_qty")) for r in data)
	total_pending_qty = sum(flt(r.get("pending_qty")) for r in data)
	total_rejected_qty = sum(flt(r.get("rejected_qty")) for r in data)

	if total_planned_qty == 0 and total_completed_qty == 0 and total_pending_qty == 0:
		return None

	return {
		"data": {
			"labels": [_("Quantities Breakdown")],
			"datasets": [
				{
					"name": _("Planned"),
					"values": [total_planned_qty],
				},
				{
					"name": _("Completed"),
					"values": [total_completed_qty],
				},
				{
					"name": _("Pending"),
					"values": [total_pending_qty],
				},
				{
					"name": _("Rejected"),
					"values": [total_rejected_qty],
				},
			],
		},
		"type": "bar",
		"height": 240,
		"colors": ["#3b82f6", "#10b981", "#f59e0b", "#ef4444"],
	}
