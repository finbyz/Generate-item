# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import get_link_to_form, now_datetime


def get_pattern_set_slots_and_serials(pattern_set_name):
	"""
	Returns component rows, attached serials, warehouse, and status calculation data for a Pattern Set.
	Follows Specification v2.0:
	One row = one physical piece.
	Each row carries item_code, serial_no (or blank if open), is_optional, warehouse, paired_on.
	"""
	doc = frappe.get_doc("Pattern Set", pattern_set_name)
	
	comp_rows = getattr(doc, "components", None) or getattr(doc, "items", None) or []
	
	rows_data = []
	attached_serials = []
	warehouses = set()
	all_required_met = True
	missing_items = []
	
	slot_summary = {}  # for backward-compatible slot counts if needed

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

	# Status calculation (v2.0 Section 5.4)
	# Draft, Complete, Incomplete, Disabled, Cancelled
	if doc.docstatus == 0:
		computed_status = "Draft"
	elif doc.docstatus == 2:
		computed_status = "Cancelled"
	elif doc.get("disabled") or doc.get("disable"):
		computed_status = "Disabled"
	elif all_required_met and len(comp_rows) > 0:
		computed_status = "Complete"
	else:
		computed_status = "Incomplete"

	return {
		"doc": doc,
		"rows": rows_data,
		"slots": list(slot_summary.values()),
		"attached_serials": attached_serials,
		"current_warehouse": current_warehouse or "",
		"current_supplier": current_supplier or "",
		"status": computed_status,
		"all_required_met": all_required_met,
		"missing_items": missing_items,
		"warehouses": list(warehouses),
	}


def render_set_info_html(pattern_set_name):
	"""
	Renders HTML for the Set Info panel per v2.0 Section 4.3 & 9.1:
	Columns: #, Item, Required/Optional, Serial No, Warehouse, State.
	Under the table: Status, Current Warehouse (and supplier), counts.
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

		rows_html.append(f"""
			<tr>
				<td style='text-align: center; color: #6b7280;'>{r['idx']}</td>
				<td><strong>{r['item_code']}</strong><br><small class='text-muted'>{frappe.utils.escape_html(r['item_name'] or '')}</small></td>
				<td style='text-align: center;'>{req_badge}</td>
				<td>{serial_display}</td>
				<td>{wh_display}</td>
				<td style='text-align: center;'>{state_badge}</td>
			</tr>
		""")

	status_color = "#28a745" if info["status"] == "Complete" else ("#e06666" if info["status"] == "Incomplete" else "#6c757d")
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
					<th style='width: 100px; text-align: center;'>{_("Type")}</th>
					<th style='width: 180px;'>{_("Serial No")}</th>
					<th style='width: 150px;'>{_("Warehouse")}</th>
					<th style='width: 120px; text-align: center;'>{_("State")}</th>
				</tr>
			</thead>
			<tbody>
				{''.join(rows_html) if rows_html else "<tr><td colspan='6' class='text-center text-muted'>" + _("No component rows configured") + "</td></tr>"}
			</tbody>
		</table>
		<div style='display: flex; justify-content: space-between; align-items: center; padding: 6px 8px; font-size: 13px; background: #f9fafb; border-radius: 4px;'>
			<div>
				<strong>{_("Status")}:</strong>
				<span class='badge' style='background-color: {status_color}; color: white; padding: 4px 8px; font-size: 12px; margin-right: 12px;'>
					{info['status']}
				</span>
				<strong>{_("Location")}:</strong>
				<span>{wh_display_text}{supplier_display}</span>
			</div>
			<div style='color: #4b5563;'>
				<span>{_("Total Rows")}: <strong>{total_rows}</strong></span> |
				<span>{_("Attached")}: <strong style='color: #059669;'>{attached_count}</strong></span>
				{" | <span style='color: #dc2626;'>" + _("Missing Required") + f": <strong>{missing_count}</strong></span>" if missing_count else ""}
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
	Recalculates status, current_warehouse, and current_supplier for a Pattern Set.
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
		"current_warehouse": info["current_warehouse"] or None,
		"current_supplier": info["current_supplier"] or None,
	}
	frappe.db.set_value("Pattern Set", pattern_set_name, updates, update_modified=False)
	return info
