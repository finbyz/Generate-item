# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import get_link_to_form, now_datetime


SNAPSHOT_FIELDS_MAP = [
	("custom_drawing_no", "drawing_no"),
	("custom_drawing_rev_no", "drawing_rev_no"),
	("custom_pattern_drawing_no", "pattern_drawing_no"),
	("custom_pattern_drawing_rev_no", "pattern_drawing_rev_no"),
	("custom_purchase_specification_no", "purchase_specification_no"),
	("custom_purchase_specification_rev_no", "purchase_specification_rev_no"),
]


def normalize_val(v):
	return (v or "").strip()


def check_snapshot_mismatches(comp_rows):
	"""
	Compares snapshot fields on component rows against current Item fields.
	Returns (has_unapproved_mismatch, has_approved_mismatch, mismatch_details)
	"""
	has_unapproved = False
	has_approved = False
	details = []

	for r in comp_rows:
		item_code = r.get("item_code") or r.get("component_item")
		if not item_code or not frappe.db.exists("Item", item_code):
			continue

		item_fields = [f[0] for f in SNAPSHOT_FIELDS_MAP]
		item_vals = frappe.db.get_value("Item", item_code, item_fields, as_dict=True) or {}

		mismatch_in_row = False
		row_diffs = []
		for item_f, comp_f in SNAPSHOT_FIELDS_MAP:
			curr_val = normalize_val(item_vals.get(item_f))
			snap_val = normalize_val(r.get(comp_f))
			if curr_val != snap_val:
				mismatch_in_row = True
				row_diffs.append(f"{comp_f}: snapshot='{snap_val}' vs item='{curr_val}'")

		if mismatch_in_row:
			is_approved_as_is = bool(r.get("approved_as_is"))
			if is_approved_as_is:
				has_approved = True
			else:
				has_unapproved = True
			details.append({
				"row_name": r.name,
				"item_code": item_code,
				"approved_as_is": is_approved_as_is,
				"diffs": row_diffs,
			})

	return has_unapproved, has_approved, details


def get_pattern_set_slots_and_serials(pattern_set_name):
	"""
	Returns component rows, attached serials, warehouse, and status calculation data for a Pattern Set.
	Follows Specification v2.0:
	Dual Status Model:
	- completeness_status: Complete / Incomplete
	- engineering_status: Current / Review Pending / Rework Required / Approved As-Is / Replaced / Disabled
	"""
	doc = frappe.get_doc("Pattern Set", pattern_set_name)
	
	comp_rows = getattr(doc, "components", None) or getattr(doc, "items", None) or []
	
	rows_data = []
	attached_serials = []
	warehouses = set()
	all_required_met = True
	missing_items = []
	
	slot_summary = {}

	for r in comp_rows:
		item_code = r.get("item_code") or r.get("component_item")
		item_name = r.get("item_name") or r.get("component_name") or item_code
		serial_no = (r.get("serial_no") or "").strip()
		is_optional = 1 if r.get("is_optional") else 0
		row_warehouse = r.get("warehouse")
		paired_on = r.get("paired_on")

		# Determine row state
		if serial_no:
			state = "OK"
			attached_serials.append({
				"serial_no": serial_no,
				"item_code": item_code,
				"warehouse": row_warehouse,
				"row_name": r.name,
			})
			if row_warehouse:
				warehouses.add(row_warehouse)
		elif is_optional:
			state = "Optional empty"
		else:
			state = "MISSING"
			all_required_met = False
			missing_items.append(item_code)

		row_dict = {
			"row_name": r.name,
			"idx": r.idx,
			"item_code": item_code,
			"item_name": item_name,
			"serial_no": serial_no,
			"warehouse": row_warehouse,
			"is_optional": is_optional,
			"paired_on": paired_on,
			"remarks": r.get("remarks") or "",
			"state": state,
			"drawing_no": r.get("drawing_no") or "",
			"drawing_rev_no": r.get("drawing_rev_no") or "",
			"pattern_drawing_no": r.get("pattern_drawing_no") or "",
			"pattern_drawing_rev_no": r.get("pattern_drawing_rev_no") or "",
			"purchase_specification_no": r.get("purchase_specification_no") or "",
			"purchase_specification_rev_no": r.get("purchase_specification_rev_no") or "",
			"approved_as_is": bool(r.get("approved_as_is")),
		}
		rows_data.append(row_dict)

		# Aggregate by item for slot summary
		if item_code not in slot_summary:
			slot_summary[item_code] = {
				"item_code": item_code,
				"item_name": item_name,
				"qty": 0,
				"attached_qty": 0,
				"is_optional": is_optional,
				"attached_serials": [],
			}
		slot_summary[item_code]["qty"] += 1
		if serial_no:
			slot_summary[item_code]["attached_qty"] += 1
			slot_summary[item_code]["attached_serials"].append(serial_no)

	# Current warehouse from attached serials
	current_warehouse = list(warehouses)[0] if len(warehouses) == 1 else (None if not warehouses else list(warehouses)[0])
	current_supplier = None
	if current_warehouse:
		current_supplier = frappe.db.get_value("Warehouse", current_warehouse, "custom_supplier")

	# Completeness Status
	if all_required_met and len(comp_rows) > 0:
		completeness_status = "Complete"
	else:
		completeness_status = "Incomplete"

	# Engineering Status
	is_disabled = bool(doc.get("disabled") or doc.get("disable"))
	if is_disabled:
		engineering_status = "Disabled"
	else:
		# Check open engineering change records
		open_changes = frappe.db.sql("""
			SELECT psec.name
			FROM `tabPattern Set Engineering Change Item` pseci
			JOIN `tabPattern Set Engineering Change` psec ON psec.name = pseci.parent
			WHERE pseci.pattern_set = %s
			  AND psec.docstatus = 0
		""", (pattern_set_name,))
		
		has_unapproved, has_approved, _diffs = check_snapshot_mismatches(comp_rows)

		if open_changes or has_unapproved:
			engineering_status = "Review Pending"
		elif has_approved:
			engineering_status = "Approved As-Is"
		else:
			engineering_status = "Current"

	# Legacy/Combined Status
	if doc.docstatus == 0:
		computed_status = "Draft"
	elif doc.docstatus == 2:
		computed_status = "Cancelled"
	elif is_disabled:
		computed_status = "Disabled"
	else:
		computed_status = completeness_status

	return {
		"doc": doc,
		"rows": rows_data,
		"slots": list(slot_summary.values()),
		"attached_serials": attached_serials,
		"current_warehouse": current_warehouse or "",
		"current_supplier": current_supplier or "",
		"status": computed_status,
		"completeness_status": completeness_status,
		"engineering_status": engineering_status,
		"all_required_met": all_required_met,
		"missing_items": missing_items,
		"warehouses": list(warehouses),
	}


def render_set_info_html(pattern_set_name):
	"""
	Renders HTML for the Set Info panel per v2.0 Section 4.3 & 9.1:
	Columns: #, Item, Required/Optional, Serial No, Warehouse, Drawing / Spec, State.
	Under the table: Completeness Status, Engineering Status, Current Warehouse (and supplier), counts.
	"""
	if not pattern_set_name or not frappe.db.exists("Pattern Set", pattern_set_name):
		return "<div class='text-muted' style='padding: 10px;'>" + _("Select a Pattern Set to view details.") + "</div>"

	info = get_pattern_set_slots_and_serials(pattern_set_name)
	rows_data = info["rows"]

	rows_html = []
	for r in rows_data:
		req_badge = (
			"<span class='badge bg-light text-dark' style='border: 1px solid #d1d5db; padding: 3px 6px;'>" + _("Optional") + "</span>"
			if r["is_optional"]
			else "<span class='badge bg-primary text-white' style='padding: 3px 6px;'>" + _("Required") + "</span>"
		)

		if r["state"] == "OK":
			state_badge = "<span class='badge bg-success text-white' style='background-color: #28a745 !important; padding: 4px 8px;'>" + _("OK") + "</span>"
		elif r["state"] == "MISSING":
			state_badge = "<span class='badge bg-danger text-white' style='background-color: #dc3545 !important; font-weight: bold; padding: 4px 8px;'>" + _("MISSING") + "</span>"
		else:
			state_badge = "<span class='badge bg-secondary text-white' style='background-color: #6c757d !important; padding: 4px 8px;'>" + _("Optional empty") + "</span>"

		serial_display = (
			f"<a href='/app/serial-no/{r['serial_no']}' target='_blank' style='font-weight: 600;'>{r['serial_no']}</a>"
			if r["serial_no"]
			else "<span class='text-muted'>— (Open)</span>"
		)
		wh_display = r["warehouse"] or "<span class='text-muted'>—</span>"

		dwg_info = f"<small class='text-muted'>Dwg: {r['drawing_no'] or '-'} (Rev {r['drawing_rev_no'] or '0'})<br>Spec: {r['purchase_specification_no'] or '-'} (Rev {r['purchase_specification_rev_no'] or '0'})</small>"
		if r["approved_as_is"]:
			dwg_info += "<br><span class='badge bg-info text-dark' style='font-size: 10px;'>" + _("Approved As-Is") + "</span>"

		rows_html.append(f"""
			<tr>
				<td style='text-align: center; color: #6b7280;'>{r['idx']}</td>
				<td><strong>{r['item_code']}</strong><br><small class='text-muted'>{frappe.utils.escape_html(r['item_name'] or '')}</small></td>
				<td style='text-align: center;'>{req_badge}</td>
				<td>{serial_display}</td>
				<td>{wh_display}</td>
				<td>{dwg_info}</td>
				<td style='text-align: center;'>{state_badge}</td>
			</tr>
		""")

	comp_color = "#28a745" if info["completeness_status"] == "Complete" else "#e06666"
	eng_color = "#28a745" if info["engineering_status"] == "Current" else ("#17a2b8" if info["engineering_status"] == "Approved As-Is" else "#e0a96d")
	
	wh_display_text = info["current_warehouse"] or "<span class='text-muted'>" + _("None (No components attached)") + "</span>"
	supplier_display = f" <span class='badge bg-info text-white' style='margin-left: 6px;'>{info['current_supplier']}</span>" if info["current_supplier"] else ""

	total_rows = len(rows_data)
	attached_count = len(info["attached_serials"])
	missing_count = len(info["missing_items"])

	html = f"""
	<div class='pattern-set-info-panel' style='border: 1px solid #d1d5db; border-radius: 6px; padding: 12px; margin-bottom: 15px; background: #fafbfc;'>
		<table class='table table-bordered table-sm' style='margin-bottom: 10px; background: white;'>
			<thead>
				<tr style='background: #f3f4f6;'>
					<th style='width: 40px; text-align: center;'>#</th>
					<th>{_("Item")}</th>
					<th style='width: 90px; text-align: center;'>{_("Type")}</th>
					<th style='width: 160px;'>{_("Serial No")}</th>
					<th style='width: 140px;'>{_("Warehouse")}</th>
					<th>{_("Drawing / Spec Snapshot")}</th>
					<th style='width: 100px; text-align: center;'>{_("State")}</th>
				</tr>
			</thead>
			<tbody>
				{''.join(rows_html)}
			</tbody>
		</table>
		<div style='display: flex; gap: 20px; align-items: center; font-size: 13px;'>
			<div>
				<strong>{_("Completeness Status")}:</strong> 
				<span style='color: {comp_color}; font-weight: bold;'>{info['completeness_status']}</span>
			</div>
			<div>
				<strong>{_("Engineering Status")}:</strong> 
				<span style='color: {eng_color}; font-weight: bold;'>{info['engineering_status']}</span>
			</div>
			<div>
				<strong>{_("Location")}:</strong> {wh_display_text}{supplier_display}
			</div>
			<div style='margin-left: auto; color: #4b5563;'>
				{_("Components")}: <strong>{attached_count}</strong> / {total_rows} attached
				{f" (<span style='color: #dc3545;'>{missing_count} required missing</span>)" if missing_count else ""}
			</div>
		</div>
	</div>
	"""
	return html


def render_transfer_history_html(pattern_set_name):
	"""
	Renders HTML for the Transfer History panel:
	Shows all submitted Pattern Set Transfers of this set: date, from, to, document link.
	"""
	if not pattern_set_name:
		return ""

	transfers = frappe.get_all(
		"Pattern Set Transfer",
		filters={"pattern_set": pattern_set_name, "docstatus": 1},
		fields=["name", "posting_date", "source_warehouse", "target_warehouse", "purpose", "transfer_type", "owner"],
		order_by="posting_date desc, creation desc",
	)

	if not transfers:
		return "<div class='text-muted' style='padding: 8px;'>" + _("No transfers recorded yet.") + "</div>"

	rows = []
	for t in transfers:
		link = get_link_to_form("Pattern Set Transfer", t.name)
		rows.append(f"""
			<tr>
				<td>{link}</td>
				<td>{t.posting_date}</td>
				<td>{t.source_warehouse or '-'}</td>
				<td>{t.target_warehouse or '-'}</td>
				<td>{t.transfer_type or '-'}</td>
				<td>{t.purpose or '-'}</td>
				<td>{t.owner or '-'}</td>
			</tr>
		""")

	return f"""
	<table class='table table-bordered table-sm' style='background: white;'>
		<thead>
			<tr style='background: #f3f4f6;'>
				<th>{_("Transfer ID")}</th>
				<th>{_("Posting Date")}</th>
				<th>{_("From Warehouse")}</th>
				<th>{_("To Warehouse")}</th>
				<th>{_("Type")}</th>
				<th>{_("Purpose")}</th>
				<th>{_("User")}</th>
			</tr>
		</thead>
		<tbody>
			{''.join(rows)}
		</tbody>
	</table>
	"""


def recalculate_pattern_set(pattern_set_name):
	"""
	Recalculates status, completeness_status, engineering_status,
	current_warehouse, and current_supplier for a Pattern Set.
	Updates Pattern Set in the database.
	"""
	if not pattern_set_name or not frappe.db.exists("Pattern Set", pattern_set_name):
		return None

	info = get_pattern_set_slots_and_serials(pattern_set_name)
	doc = info["doc"]
	
	comp_rows = getattr(doc, "components", None) or getattr(doc, "items", None) or []

	# Sync attached_qty for backward compatibility if field exists
	for r in comp_rows:
		if hasattr(r, "attached_qty"):
			att = 1 if r.get("serial_no") else 0
			frappe.db.set_value(r.doctype, r.name, "attached_qty", att, update_modified=False)

	# Update fields on parent Pattern Set
	updates = {
		"status": info["status"],
		"completeness_status": info["completeness_status"],
		"engineering_status": info["engineering_status"],
		"current_warehouse": info["current_warehouse"] or None,
		"current_supplier": info["current_supplier"] or None,
	}
	frappe.db.set_value("Pattern Set", pattern_set_name, updates, update_modified=False)
	return info
