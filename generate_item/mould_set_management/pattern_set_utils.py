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


def get_pattern_set_slots_and_serials(pattern_set_name):
	"""
	Returns component rows, attached serials, warehouse, and status calculation data for a Pattern Set.
	Follows Specification v2.0:
	Dual Status Model:
	- completeness_status: Complete / Incomplete
	- engineering_status: Open / Approved / Rejected
	"""
	doc = frappe.get_doc("Pattern Set", pattern_set_name)
	
	comp_rows = getattr(doc, "components", None) or getattr(doc, "items", None) or []
	
	rows_data = []
	attached_serials = []
	warehouses = set()
	all_required_met = True
	missing_items = []
	
	slot_summary = {}

	# TASK41455: a serial counts only for the Pattern Set that owns it, never for two sets
	owners = get_serial_owner_map([r.get("serial_no") for r in comp_rows])

	for r in comp_rows:
		item_code = r.get("item_code") or r.get("component_item")
		item_name = r.get("item_name") or r.get("component_name") or item_code
		serial_no = (r.get("serial_no") or "").strip()
		is_optional = 1 if r.get("is_optional") else 0
		row_warehouse = r.get("warehouse")
		paired_on = r.get("paired_on")

		owner = owners.get(serial_no) if serial_no else None

		# Determine row state
		if serial_no and owner and owner != doc.name:
			# The serial belongs to another Pattern Set: this row does not hold a piece
			state = "Linked to {0}".format(owner)
			if not is_optional:
				all_required_met = False
				missing_items.append(item_code)
		elif serial_no:
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

	engineering_status = doc.get("engineering_status") or "Open"

	# Legacy/Combined Status
	is_disabled = bool(doc.get("disabled") or doc.get("disable"))
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
	eng_colors = {
		"Open": "#e0a96d",
		"Approved": "#28a745",
		"Rejected": "#dc3545",
	}
	eng_color = eng_colors.get(info["engineering_status"], "#6c757d")
	
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
	Recalculates status, completeness_status, current_warehouse, and current_supplier
	for a Pattern Set. Engineering Status is managed by Engineering Change records.
	Updates Pattern Set in the database.
	"""
	if not pattern_set_name or not frappe.db.exists("Pattern Set", pattern_set_name):
		return None

	info = get_pattern_set_slots_and_serials(pattern_set_name)
	doc = info["doc"]
	
	comp_rows = getattr(doc, "components", None) or getattr(doc, "items", None) or []

	# Sync attached_qty for backward compatibility if field exists
	owned_rows = {s["row_name"] for s in info["attached_serials"]}
	for r in comp_rows:
		if hasattr(r, "attached_qty"):
			att = 1 if r.name in owned_rows else 0
			frappe.db.set_value(r.doctype, r.name, "attached_qty", att, update_modified=False)

	# Update fields on parent Pattern Set
	updates = {
		"status": info["status"],
		"completeness_status": info["completeness_status"],
		"current_warehouse": info["current_warehouse"] or None,
		"current_supplier": info["current_supplier"] or None,
	}
	frappe.db.set_value("Pattern Set", pattern_set_name, updates, update_modified=False)
	return info


def sync_pattern_set_engineering_status(pattern_set_name, status=None):
	if not pattern_set_name or not frappe.db.exists("Pattern Set", pattern_set_name):
		return None

	if status is None:
		active_changes = frappe.db.sql(
			"""
			SELECT psec.status
			FROM `tabPattern Set Engineering Change Item` pseci
			JOIN `tabPattern Set Engineering Change` psec ON psec.name = pseci.parent
			WHERE pseci.pattern_set = %s
			  AND psec.docstatus IN (0, 1)
			ORDER BY CASE WHEN psec.docstatus = 0 THEN 0 ELSE 1 END,
			         psec.modified DESC,
			         psec.name DESC
			LIMIT 1
			""",
			(pattern_set_name,),
		)
		status = active_changes[0][0] if active_changes else "Open"

	if status not in ("Open", "Approved", "Rejected"):
		frappe.throw(_("Invalid Engineering Status: {0}").format(status))

	frappe.db.set_value(
		"Pattern Set",
		pattern_set_name,
		"engineering_status",
		status,
		update_modified=False,
	)
	return status


def get_serials_linked_to_pattern_sets(exclude_set=None):
	"""Serial Nos already used by a Pattern Set (TASK41454).

	A serial counts as linked when it is on a component row of a Draft or Submitted
	Pattern Set, or when its Serial No.custom_pattern_set is filled. Cancelled sets do
	not count. Serials linked only to `exclude_set` are left out of the result.
	"""
	conditions = ["psc.parenttype = 'Pattern Set'", "IFNULL(psc.serial_no, '') != ''", "ps.docstatus < 2"]
	values = {}
	if exclude_set:
		conditions.append("ps.name != %(exclude_set)s")
		values["exclude_set"] = exclude_set

	linked = set(
		frappe.db.sql_list(
			"""
			SELECT DISTINCT psc.serial_no
			FROM `tabPattern Set Component` psc
			INNER JOIN `tabPattern Set` ps ON ps.name = psc.parent
			WHERE {}
			""".format(" AND ".join(conditions)),
			values,
		)
	)

	sn_filters = {"custom_pattern_set": ["is", "set"]}
	if exclude_set:
		sn_filters["custom_pattern_set"] = ["not in", ["", exclude_set]]
	linked.update(frappe.get_all("Serial No", filters=sn_filters, pluck="name"))
	return linked


def _serial_links(serials):
	"""serial -> {"link": Serial No.custom_pattern_set, "sets": {set_name: (docstatus, creation)}}.

	Only Draft and Submitted Pattern Sets are considered.
	"""
	serials = sorted({(s or "").strip() for s in serials if s and (s or "").strip()})
	if not serials:
		return {}

	out = {s: {"link": None, "sets": {}} for s in serials}
	for row in frappe.db.sql(
		"""
		SELECT psc.serial_no, ps.name, ps.docstatus, ps.creation
		FROM `tabPattern Set Component` psc
		INNER JOIN `tabPattern Set` ps ON ps.name = psc.parent
		WHERE psc.parenttype = 'Pattern Set' AND ps.docstatus < 2 AND psc.serial_no IN %(serials)s
		""",
		{"serials": tuple(serials)},
		as_dict=True,
	):
		out[row.serial_no]["sets"][row.name] = (row.docstatus, row.creation)

	links = frappe.get_all(
		"Serial No", filters={"name": ["in", serials]}, fields=["name", "custom_pattern_set"]
	)
	link_sets = {l.custom_pattern_set for l in links if l.custom_pattern_set}
	live_links = {
		p.name: (p.docstatus, p.creation)
		for p in frappe.get_all(
			"Pattern Set",
			filters={"name": ["in", list(link_sets)], "docstatus": ["<", 2]},
			fields=["name", "docstatus", "creation"],
		)
	} if link_sets else {}
	for l in links:
		if l.custom_pattern_set in live_links:
			out[l.name]["link"] = l.custom_pattern_set
			out[l.name]["sets"].setdefault(l.custom_pattern_set, live_links[l.custom_pattern_set])
	return out


def get_serial_owner_map(serials):
	"""serial -> the one Pattern Set that owns it (TASK41455).

	Owner = the set in Serial No.custom_pattern_set when that set is not cancelled.
	Otherwise the oldest Submitted set listing the serial, else the oldest Draft set.
	Serials not in any live set are left out.
	"""
	owners = {}
	for serial, info in _serial_links(serials).items():
		if info["link"]:
			owners[serial] = info["link"]
		elif info["sets"]:
			owners[serial] = sorted(info["sets"].items(), key=lambda kv: (kv[1][0] != 1, kv[1][1]))[0][0]
	return owners


def get_other_pattern_sets_for_serial(serial_no, current_set=None):
	"""Live Pattern Sets other than `current_set` that hold this serial, as [(name, docstatus)]."""
	info = _serial_links([serial_no]).get((serial_no or "").strip())
	if not info:
		return []
	return sorted(
		((name, ds) for name, (ds, _creation) in info["sets"].items() if name != current_set),
		key=lambda x: (x[1] != 1, x[0]),
	)


def find_duplicate_serial_links(apply=False):
	"""Find serials held by more than one live Pattern Set (TASK41455 data cleanup).

	With apply=True, the serial is kept in its owner set (see get_serial_owner_map) and
	cleared from the component rows of every other set, which are then recalculated.
	Returns a list of {serial_no, owner, removed_from}.
	"""
	candidates = frappe.db.sql_list(
		"""
		SELECT psc.serial_no
		FROM `tabPattern Set Component` psc
		INNER JOIN `tabPattern Set` ps ON ps.name = psc.parent
		LEFT JOIN `tabSerial No` sn ON sn.name = psc.serial_no
		WHERE psc.parenttype = 'Pattern Set' AND ps.docstatus < 2 AND IFNULL(psc.serial_no, '') != ''
		GROUP BY psc.serial_no
		HAVING COUNT(DISTINCT ps.name) > 1
			OR SUM(IFNULL(sn.custom_pattern_set, '') NOT IN ('', ps.name)) > 0
		"""
	)
	owners = get_serial_owner_map(candidates)
	report, touched = [], set()
	for serial in candidates:
		owner = owners.get(serial)
		others = [name for name, _ds in get_other_pattern_sets_for_serial(serial, owner)]
		if not others:
			continue
		report.append({"serial_no": serial, "owner": owner, "removed_from": others})
		if apply:
			for row in frappe.get_all(
				"Pattern Set Component",
				filters={"parenttype": "Pattern Set", "parent": ["in", others], "serial_no": serial},
				fields=["name", "parent"],
			):
				frappe.db.set_value(
					"Pattern Set Component",
					row.name,
					{"serial_no": None, "warehouse": None, "paired_on": None},
					update_modified=False,
				)
				touched.add(row.parent)
	for pattern_set in touched:
		recalculate_pattern_set(pattern_set)
	return report
