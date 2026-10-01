# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import json
import math
import frappe
from frappe import _
from frappe.utils import flt, get_link_to_form
from erpnext.stock.utils import get_stock_balance


def get_mould_sets_for_items(items_list):
	"""
	Given a list of items (or dicts with item_code / fg_item),
	finds all active Mould Sets where:
	1) Mould Set item == item_code or fg_item
	2) Any component in Mould Set == item_code or fg_item
	"""
	item_codes = set()
	for row in items_list:
		if isinstance(row, dict):
			if row.get("item_code"):
				item_codes.add(row["item_code"])
			if row.get("fg_item"):
				item_codes.add(row["fg_item"])
		elif hasattr(row, "item_code"):
			if row.item_code:
				item_codes.add(row.item_code)
			if getattr(row, "fg_item", None):
				item_codes.add(row.fg_item)
		elif isinstance(row, str):
			item_codes.add(row)

	item_codes = [c for c in item_codes if c]
	if not item_codes:
		return []

	matched_mould_set_names = set()

	# 1. Direct match on Pattern Set parent item
	parent_matches = frappe.get_all(
		"Pattern Set",
		filters={
			"item": ["in", item_codes],
			"docstatus": ["!=", 2],
			"disable": 0,
		},
		pluck="name",
	)
	matched_mould_set_names.update(parent_matches)

	# 2. Match on component items
	comp_matches = frappe.get_all(
		"Pattern Set Component",
		filters={"component_item": ["in", item_codes]},
		pluck="parent",
	)
	if comp_matches:
		active_comp_parents = frappe.get_all(
			"Pattern Set",
			filters={
				"name": ["in", list(set(comp_matches))],
				"docstatus": ["!=", 2],
				"disable": 0,
			},
			pluck="name",
		)
		matched_mould_set_names.update(active_comp_parents)

	return list(matched_mould_set_names)


def get_mould_sets_with_stock_at_warehouse(warehouse):
	"""
	Fallback: If no items in PO matched, find any active Pattern Sets
	whose components have non-zero stock at the given warehouse.
	"""
	if not warehouse:
		return []

	all_active = frappe.get_all(
		"Pattern Set",
		filters={"docstatus": ["!=", 2], "disable": 0},
		pluck="name",
	)
	relevant = []
	for ms_name in all_active:
		components = frappe.get_all(
			"Pattern Set Component",
			filters={"parent": ms_name},
			pluck="component_item",
		)
		has_stock = False
		for c_item in components:
			if get_stock_balance(c_item, warehouse) > 0:
				has_stock = True
				break
		if has_stock:
			relevant.append(ms_name)

	return relevant


def calculate_mould_sets_stock(mould_set_names, warehouse):
	"""
	Calculates complete pattern sets and loose/individual components at the given warehouse.
	"""
	if not mould_set_names or not warehouse:
		return []

	results = []
	for ms_name in mould_set_names:
		ms_doc = frappe.get_doc("Pattern Set", ms_name)
		if ms_doc.docstatus == 2 or cint_disable(ms_doc):
			continue

		comp_stock_map = {}
		comp_rows = []

		for c in ms_doc.items:
			stock = max(0.0, flt(get_stock_balance(c.component_item, warehouse)))
			comp_stock_map[c.component_item] = stock
			comp_rows.append(c)

		# Calculate sets possible per component
		sets_possible = []
		for c in comp_rows:
			req = flt(c.qty)
			if req > 0:
				sets_possible.append(math.floor(comp_stock_map[c.component_item] / req))
			else:
				sets_possible.append(0)

		complete_sets = int(min(sets_possible)) if sets_possible else 0

		# Calculate loose/individual components
		loose_components_total = 0.0
		components_detail = []
		for c in comp_rows:
			actual_qty = comp_stock_map[c.component_item]
			req_qty = flt(c.qty)
			component_loose = max(0.0, actual_qty - (complete_sets * req_qty))
			loose_components_total += component_loose

			sets_for_this_comp = math.floor(actual_qty / req_qty) if req_qty > 0 else 0

			components_detail.append({
				"component_item": c.component_item,
				"component_name": c.component_name or frappe.db.get_value("Item", c.component_item, "item_name"),
				"req_qty": req_qty,
				"actual_qty": actual_qty,
				"sets_possible": int(sets_for_this_comp),
				"loose_qty": component_loose,
				"uom": c.uom,
				"drawing_no": c.drawing_no or "-",
				"drawing_rev_no": c.drawing_rev_no or "-",
			})

		results.append({
			"mould_set": ms_doc.name,
			"mould_set_name": getattr(ms_doc, "pattern_set_name", getattr(ms_doc, "mould_set_name", ms_doc.name)),
			"item": ms_doc.item,
			"item_name": ms_doc.item_name or frappe.db.get_value("Item", ms_doc.item, "item_name"),
			"complete_sets": complete_sets,
			"loose_components": loose_components_total,
			"components": components_detail,
		})

	return results


def cint_disable(doc):
	return bool(getattr(doc, "disable", 0))


def render_mould_set_html(warehouse, mould_sets_data):
	"""
	Renders a modern, visually stunning HTML section for the Purchase Order form.
	"""
	if not warehouse:
		return """
		<div style="padding: 14px 18px; background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 8px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
			<div style="display: flex; align-items: center; gap: 10px; color: #64748b; font-size: 13px;">
				<span style="font-size: 18px;">ℹ️</span>
				<span>Please specify a <b>Supplier Warehouse</b> to view Pattern Set stock availability and component balance.</span>
			</div>
		</div>
		"""

	if not mould_sets_data:
		return f"""
		<div style="padding: 14px 18px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
			<div style="display: flex; justify-content: space-between; align-items: center;">
				<div style="font-size: 13px; color: #475569;">
					<span>No Pattern Sets linked to PO items or found with stock in <b>{frappe.utils.escape_html(warehouse)}</b>.</span>
				</div>
				<span style="font-size: 11px; padding: 3px 8px; background: #e2e8f0; color: #475569; border-radius: 4px; font-weight: 600;">
					WH: {frappe.utils.escape_html(warehouse)}
				</span>
			</div>
		</div>
		"""

	total_complete_sets = sum(d["complete_sets"] for d in mould_sets_data)
	total_loose_items = sum(d["loose_components"] for d in mould_sets_data)

	mould_set_cards = ""
	for ms in mould_sets_data:
		comp_rows = ""
		for c in ms["components"]:
			comp_status_badge = (
				'<span style="background: #ecfdf5; color: #047857; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: 600;">Ready</span>'
				if c["actual_qty"] >= c["req_qty"]
				else '<span style="background: #fef2f2; color: #b91c1c; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: 600;">Shortage</span>'
			)

			loose_badge = (
				f'<span style="font-weight: 600; color: #d97706;">{c["loose_qty"]:g}</span>'
				if c["loose_qty"] > 0
				else '<span style="color: #94a3b8;">0</span>'
			)

			comp_rows += f"""
			<tr style="border-bottom: 1px solid #f1f5f9; font-size: 12px;">
				<td style="padding: 8px 10px; font-weight: 500; color: #1e293b;">
					{frappe.utils.escape_html(c['component_item'])}
					<div style="font-size: 11px; color: #64748b;">{frappe.utils.escape_html(c['component_name'] or '')}</div>
				</td>
				<td style="padding: 8px 10px; text-align: center; color: #334155;">{c['req_qty']:g} {frappe.utils.escape_html(c['uom'] or '')}</td>
				<td style="padding: 8px 10px; text-align: center; font-weight: 600; color: #0f172a;">{c['actual_qty']:g}</td>
				<td style="padding: 8px 10px; text-align: center; font-weight: 600; color: #0369a1;">{c['sets_possible']}</td>
				<td style="padding: 8px 10px; text-align: center;">{loose_badge}</td>
				<td style="padding: 8px 10px; text-align: center; color: #475569; font-size: 11px;">{frappe.utils.escape_html(c['drawing_no'])} (Rev: {frappe.utils.escape_html(c['drawing_rev_no'])})</td>
				<td style="padding: 8px 10px; text-align: center;">{comp_status_badge}</td>
			</tr>
			"""

		mould_set_cards += f"""
		<div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; margin-bottom: 12px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
			<div style="background: #f8fafc; padding: 10px 14px; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center;">
				<div>
					<span style="font-size: 13px; font-weight: 700; color: #0f172a;">
						📦 Pattern Set: {frappe.utils.escape_html(ms['mould_set_name'])}
					</span>
					<span style="font-size: 12px; color: #64748b; margin-left: 8px;">
						(Item: <b>{frappe.utils.escape_html(ms['item'])}</b> - {frappe.utils.escape_html(ms['item_name'] or '')})
					</span>
				</div>
				<div style="display: flex; gap: 8px;">
					<span style="background: #ecfdf5; border: 1px solid #a7f3d0; color: #065f46; font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 20px;">
						✓ {ms['complete_sets']} Complete Sets
					</span>
					<span style="background: #fffbeb; border: 1px solid #fde68a; color: #92400e; font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 20px;">
						⚡ {ms['loose_components']:g} Loose Items
					</span>
				</div>
			</div>
			<div style="overflow-x: auto;">
				<table style="width: 100%; border-collapse: collapse; text-align: left;">
					<thead>
						<tr style="background: #f1f5f9; color: #475569; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px;">
							<th style="padding: 7px 10px;">Component</th>
							<th style="padding: 7px 10px; text-align: center;">Qty / Set</th>
							<th style="padding: 7px 10px; text-align: center;">In-Stock</th>
							<th style="padding: 7px 10px; text-align: center;">Sets Possible</th>
							<th style="padding: 7px 10px; text-align: center;">Loose Qty</th>
							<th style="padding: 7px 10px; text-align: center;">Drawing / Rev</th>
							<th style="padding: 7px 10px; text-align: center;">Status</th>
						</tr>
					</thead>
					<tbody>
						{comp_rows}
					</tbody>
				</table>
			</div>
		</div>
		"""

	html = f"""
	<div style="margin: 10px 0 16px 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
		<!-- Header & Overall Metrics -->
		<div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border-radius: 10px; padding: 14px 18px; color: #ffffff; margin-bottom: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
			<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 10px;">
				<div style="display: flex; align-items: center; gap: 8px;">
					<span style="font-size: 16px;">🧩</span>
					<span style="font-size: 14px; font-weight: 700; letter-spacing: 0.3px;">PATTERN SET STOCK INFORMATION</span>
				</div>
				<div style="font-size: 12px; background: rgba(255,255,255,0.15); padding: 3px 10px; border-radius: 6px; font-weight: 500;">
					📍 Warehouse: <b>{frappe.utils.escape_html(warehouse)}</b>
				</div>
			</div>
			
			<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
				<div style="background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.4); border-radius: 8px; padding: 10px 14px; display: flex; align-items: center; gap: 12px;">
					<div style="font-size: 28px; font-weight: 800; color: #34d399; line-height: 1;">
						{total_complete_sets}
					</div>
					<div>
						<div style="font-size: 12px; font-weight: 700; color: #6ee7b7; text-transform: uppercase;">Complete Pattern Sets</div>
						<div style="font-size: 11px; color: #a7f3d0;">Fully assembled sets available in stock</div>
					</div>
				</div>
				<div style="background: rgba(245, 158, 11, 0.15); border: 1px solid rgba(245, 158, 11, 0.4); border-radius: 8px; padding: 10px 14px; display: flex; align-items: center; gap: 12px;">
					<div style="font-size: 28px; font-weight: 800; color: #fbbf24; line-height: 1;">
						{total_loose_items:g}
					</div>
					<div>
						<div style="font-size: 12px; font-weight: 700; color: #fde68a; text-transform: uppercase;">Loose Components</div>
						<div style="font-size: 11px; color: #fef3c7;">Incomplete / individual component items</div>
					</div>
				</div>
			</div>
		</div>

		<!-- Pattern Sets Cards Detail -->
		{mould_set_cards}
	</div>
	"""
	return html


def get_supplier_warehouse(supplier=None, po_warehouse=None, branch=None):
	"""
	Determines the warehouse configured on the PO (supplier_warehouse or set_warehouse).
	"""
	return po_warehouse or None


@frappe.whitelist()
def get_po_mould_set_info(po_name=None, supplier_warehouse=None, supplier=None, items=None):
	"""
	Whitelisted API to fetch mould set stock info for a Purchase Order.
	Can be called client-side on form refresh or field change.
	"""
	items_list = []
	if items:
		if isinstance(items, str):
			try:
				items_list = json.loads(items)
			except Exception:
				items_list = []
		elif isinstance(items, list):
			items_list = items

	branch = None
	if po_name:
		po = frappe.get_doc("Purchase Order", po_name)
		if not supplier_warehouse:
			supplier_warehouse = po.supplier_warehouse or getattr(po, "set_warehouse", None)
		branch = getattr(po, "branch", None)
		if not items_list:
			items_list = [{"item_code": i.item_code, "fg_item": getattr(i, "fg_item", None)} for i in po.items]

	wh = get_supplier_warehouse(supplier=supplier, po_warehouse=supplier_warehouse, branch=branch)

	mould_set_names = get_mould_sets_for_items(items_list)
	if not mould_set_names and wh:
		mould_set_names = get_mould_sets_with_stock_at_warehouse(wh)

	mould_sets_data = calculate_mould_sets_stock(mould_set_names, wh)

	total_complete = sum(d["complete_sets"] for d in mould_sets_data)
	total_loose = sum(d["loose_components"] for d in mould_sets_data)

	html = render_mould_set_html(wh, mould_sets_data)

	return {
		"warehouse": wh,
		"total_complete_sets": total_complete,
		"total_loose_components": total_loose,
		"mould_sets": mould_sets_data,
		"html": html,
	}


def on_po_validate_or_save(doc, method=None):
	"""
	Called from Purchase Order validate / before_save hooks.
	Displays the Pattern Sets information section showing:
	- Number of complete Pattern Sets
	- Number of individual Components (incomplete/loose items)
	"""
	wh = getattr(doc, "supplier_warehouse", None) or getattr(doc, "set_warehouse", None)

	if not wh:
		return

	items_list = [
		{"item_code": i.item_code, "fg_item": getattr(i, "fg_item", None)}
		for i in (doc.items or [])
	]

	mould_set_names = get_mould_sets_for_items(items_list)
	if not mould_set_names:
		mould_set_names = get_mould_sets_with_stock_at_warehouse(wh)

	if not mould_set_names:
		return

	mould_sets_data = calculate_mould_sets_stock(mould_set_names, wh)
	if not mould_sets_data:
		return

	total_complete = sum(d["complete_sets"] for d in mould_sets_data)
	total_loose = sum(d["loose_components"] for d in mould_sets_data)

	# 1. Update HTML on the document field if field exists
	if hasattr(doc, "mould_set_info"):
		doc.mould_set_info = render_mould_set_html(wh, mould_sets_data)

	# 2. Display info section to user on save
	ms_summary_rows = ""
	for ms in mould_sets_data:
		ms_summary_rows += f"""
		<li style="margin-top: 4px;">
			<b>{frappe.utils.escape_html(ms['mould_set_name'])}</b> (Item: {frappe.utils.escape_html(ms['item'])}):
			<span style="color: #2b8a3e; font-weight: bold;">{ms['complete_sets']} Complete Set(s)</span>,
			<span style="color: #d97706; font-weight: bold;">{ms['loose_components']:g} Loose Item(s)</span>
		</li>
		"""

	msg_html = f"""
	<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 13px;">
		<div style="display: flex; gap: 10px; margin-bottom: 12px;">
			<div style="flex: 1; background: #ebfbee; border: 1px solid #b2f2bb; border-radius: 6px; padding: 8px 12px; text-align: center;">
				<div style="font-size: 11px; font-weight: bold; color: #2b8a3e; text-transform: uppercase;">Complete Pattern Sets</div>
				<div style="font-size: 22px; font-weight: bold; color: #2b8a3e;">{total_complete}</div>
			</div>
			<div style="flex: 1; background: #fff9db; border: 1px solid #ffe066; border-radius: 6px; padding: 8px 12px; text-align: center;">
				<div style="font-size: 11px; font-weight: bold; color: #d97706; text-transform: uppercase;">Individual / Loose Components</div>
				<div style="font-size: 22px; font-weight: bold; color: #d97706;">{total_loose:g}</div>
			</div>
		</div>
		<div style="color: #495057; font-size: 12px;">
			<b>Pattern Sets at Warehouse ({frappe.utils.escape_html(wh)}):</b>
			<ul style="margin: 6px 0 0 16px; padding: 0;">
				{ms_summary_rows}
			</ul>
		</div>
	</div>
	"""

	frappe.msgprint(
		msg=msg_html,
		title=_("Pattern Set Information ({0})").format(wh),
		indicator="blue",
		alert=True,
	)
