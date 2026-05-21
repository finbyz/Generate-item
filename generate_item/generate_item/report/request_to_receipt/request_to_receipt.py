# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt
#
# Report  : Request to Receipt
# Purpose : MR → PO → PR  tree view.  Submitted MRs only.  No cross-level data bleed.
#
# ── Architecture ─────────────────────────────────────────────────────────────
#
#   execute()
#     └─ get_data()
#          ├─ fetch_mr_items()           (docstatus=1, material_request_type="Purchase")
#          ├─ fetch_po_items_for_mrs()   (docstatus=1, linked via material_request_item)
#          ├─ fetch_pr_items_for_pos()   (docstatus=1, linked via purchase_order_item)
#          └─ build_tree()
#               MR row  indent=0
#                 PO row  indent=1
#                   PR row  indent=2
#                   PR row  indent=2
#                 PO row  indent=1
#                   PR row  indent=2
#
# WHY three separate queries and NOT one big JOIN:
#   A single MR→PO→PR join with multiple PRs per PO causes row-multiplication
#   (fan-out), which makes every SUM field incorrect.  Separate queries + Python
#   assembly is the only correct approach for multi-level trees.
#
# WHY link PR via `purchase_order_item` (not just `purchase_order`):
#   A PO can cover multiple MR items for the same item code.  Linking only on
#   purchase_order would attach every PR line for that PO to every MR row,
#   again causing duplicate data.
# ─────────────────────────────────────────────────────────────────────────────

import frappe
from frappe import _
from frappe.utils import date_diff, flt, cstr, cint, getdate
from collections import OrderedDict
import copy
from frappe.query_builder.functions import Coalesce, Sum
from frappe.utils import cint, date_diff, flt, getdate


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def execute(filters=None):
	if not filters:
		return [], []

	validate_filters(filters)

	columns = get_columns()
	data    = get_data(filters)


	return columns, data


# ─────────────────────────────────────────────────────────────────────────────
# Validation
# ─────────────────────────────────────────────────────────────────────────────

def validate_filters(filters):
	from_date = filters.get("from_date")
	to_date   = filters.get("to_date")

	if not from_date or not to_date:
		frappe.throw(_("From Date and To Date are required."))

	if date_diff(to_date, from_date) < 0:
		frappe.throw(_("To Date cannot be before From Date."))


# ─────────────────────────────────────────────────────────────────────────────
# Columns
# ─────────────────────────────────────────────────────────────────────────────
#
# Every fieldname listed here MUST appear as a key in every row dict returned
# by build_tree().  Missing keys raise KeyError inside Frappe's renderer.
# The _blank() helper guarantees this by pre-filling all fields with None.

def get_columns():
	return [
		# ── level badge ──────────────────────────────────────────────────────
		{
			"fieldname": "row_type",
			"label":     _(""),
			"fieldtype": "Data",
			"width":     200,
		},
		# ── MR fields ────────────────────────────────────────────────────────
		{
			"fieldname": "material_request",
			"label":     _("Material Request"),
			"fieldtype": "Link",
			"options":   "Material Request",
			"width":     175,
		},
		{
			"fieldname": "mr_date",
			"label":     _("Date"),
			"fieldtype": "Date",
			"width":     100,
		},
		{
			"fieldname": "required_date",
			"label":     _("Required By"),
			"fieldtype": "Date",
			"width":     105,
		},
		
		{
			"fieldname": "custom_batch_no",
			"label":     _("Batch No"),
			"fieldtype": "Link",
			"options":   "Batch",
			"width":     120,
		},
		{
			"fieldname": "branch",
			"label":     _("Branch"),
			"fieldtype": "Link",
			"options":   "Branch",
			"width":     120,
		},
		
		{
			"fieldname": "mr_qty",
			"label":     _("Request Qty"),
			"fieldtype": "Float",
			"width":     90,
		},
		{
			"fieldname": "mr_uom",
			"label":     _("UOM(Request Qty)"),
			"fieldtype": "Link",
			"options":   "UOM",
			"width":     80,
		},
		{
			"fieldname": "mr_status",
			"label":     _("MR Status"),
			"fieldtype": "Data",
			"width":     145,
		},
		# ── PO fields ────────────────────────────────────────────────────────
		{
			"fieldname": "po_no",
			"label":     _("Vendor PO No"),
			"fieldtype": "Link",
			"options":   "Purchase Order",
			"width":     170,
		},
		{
			"fieldname": "po_date",
			"label":     _("Vendor PO Date"),
			"fieldtype": "Date",
			"width":     100,
		},
		{
			"fieldname": "po_required_by",
			"label":     _("PO Required By"),
			"fieldtype": "Date",
			"width":     105,
		},
		{
			"fieldname": "supplier",
			"label":     _("Vendor Name"),
			"fieldtype": "Link",
			"options":   "Supplier",
			"width":     160,
		},
		{
			"fieldname": "item_code",
			"label":     _("Item Code"),
			"fieldtype": "Link",
			"options":   "Item",
			"width":     150,
		},
		{
			"fieldname": "item_name",
			"label":     _("Item Name"),
			"fieldtype": "Data",
			"width":     200,
		},

		{
			"fieldname": "description",
			"label":     _("Description"),
			"fieldtype": "Data",
			"width":     200,
		},
		

		{
			"fieldname": "po_qty",
			"label":     _("PO Qty"),
			"fieldtype": "Float",
			"width":     90,
		},
		{
			"fieldname": "po_uom",
			"label":     _("PO UOM"),
			"fieldtype": "Link",
			"options":   "UOM",
			"width":     80,
		},
		{
			"fieldname": "po_qty_stock",
			"label":     _("PO Qty (Stock UOM)"),
			"fieldtype": "Float",
			"width":     120,
		},
		{
			"fieldname": "po_stock_uom",
			"label":     _("PO Stock UOM"),
			"fieldtype": "Link",
			"options":   "UOM",
			"width":     105,
		},
		{
			"fieldname": "balance_qty",
			"label":     _("Balance Qty"),
			"fieldtype": "Float",
			"width":     100,
		},
		# ── PR fields ────────────────────────────────────────────────────────
		{
			"fieldname": "receipt_no",
			"label":     _("Purchase Receipt"),
			"fieldtype": "Link",
			"options":   "Purchase Receipt",
			"width":     170,
		},
		{
			"fieldname": "received_date",
			"label":     _("Received Date"),
			"fieldtype": "Date",
			"width":     110,
		},
		{
			"fieldname": "received_qty",
			"label":     _("Received Qty"),
			"fieldtype": "Float",
			"width":     100,
		},
		{
			"fieldname": "received_uom",
			"label":     _("Received Qty UOM"),
			"fieldtype": "Link",
			"options":   "UOM",
			"width":     90,
		},
		{
			"fieldname": "received_qty_stock",
			"label":     _("Received Qty (Stock UOM)"),
			"fieldtype": "Float",
			"width":     150,
		},
		{
			"fieldname": "received_stock_uom",
			"label":     _("Received Qty Stock UOM"),
			"fieldtype": "Link",
			"options":   "UOM",
			"width":     120,
		},

		# {
		# 		"label": _("Qty in Stock UOM"),
		# 		"fieldname": "stock_qty",
		# 		"fieldtype": "Float",
		# 		"width": 140,
		# 		"convertible": "qty",
		# 	},
			# {
			# 	"label": _("Ordered Qty"),
			# 	"fieldname": "ordered_qty",
			# 	"fieldtype": "Float",
			# 	"width": 120,
			# 	"convertible": "qty",
			# },
			# {
			# 	"label": _("Received Qty"),
			# 	"fieldname": "received_qty",
			# 	"fieldtype": "Float",
			# 	"width": 120,
			# 	"convertible": "qty",
			# },
			{
				"label": _("Qty to Receive"),
				"fieldname": "qty_to_receive",
				"fieldtype": "Float",
				"width": 120,
				"convertible": "qty",
			},
			{
				"label": _("Qty to Order"),
				"fieldname": "qty_to_order",
				"fieldtype": "Float",
				"width": 120,
				"convertible": "qty",
			},
			
		# ── shared ───────────────────────────────────────────────────────────
		{
			"fieldname": "company",
			"label":     _("Company"),
			"fieldtype": "Link",
			"options":   "Company",
			"width":     150,
		},
	]


# ─────────────────────────────────────────────────────────────────────────────
# Blank-row template
# ─────────────────────────────────────────────────────────────────────────────
# Every row produced by build_tree() starts as _blank() so that cells
# belonging to a different hierarchy level are always None (renders as empty),
# never accidentally populated with data from another level.

_ALL_FIELDS = [
	# control
	"row_type", "indent", "bold",
	# MR
	"material_request", "mr_date", "required_date",
	"branch", "custom_batch_no",
	"item_code", "item_name","description",
	"mr_qty", "mr_uom", "mr_status","qty_to_order","qty_to_receive"
	# PO
	"po_no", "po_date", "po_required_by",
	"supplier",
	"po_qty", "po_uom", "po_qty_stock", "po_stock_uom",
	"balance_qty",
	# PR
	"receipt_no", "received_date",
	"received_qty", "received_uom",
	"received_qty_stock", "received_stock_uom",
	# shared
	"company",
]

def _blank():
	"""Return a dict with every report field pre-set to None."""
	return dict.fromkeys(_ALL_FIELDS, None)


# ─────────────────────────────────────────────────────────────────────────────
# Query 1 — MR items
# ─────────────────────────────────────────────────────────────────────────────

def fetch_mr_items(filters):
	"""
	Fetch submitted Purchase MR items that match the active filters.

	Status filter ("Received" / "Pending") is resolved post-query using
	mr.per_received because the value lives on the MR header, not the item.
	"""
	mr      = frappe.qb.DocType("Material Request")
	mr_item = frappe.qb.DocType("Material Request Item")

	q = (
		frappe.qb.from_(mr)
		.join(mr_item).on(mr_item.parent == mr.name)
		.select(
			# header
			mr.name.as_("material_request"),
			mr.transaction_date.as_("mr_date"),
			mr.per_received,
			mr.status.as_("mr_status_raw"),
			mr.company,
			# item
			mr_item.name.as_("mr_item_name"),
			mr_item.idx,
			mr_item.item_code,
			mr_item.item_name,
			mr_item.qty.as_("mr_qty"),
			mr_item.uom.as_("mr_uom"),
			mr_item.stock_qty.as_("mr_stock_qty"),
			mr_item.description,
			mr_item.ordered_qty,
			mr_item.stock_uom.as_("mr_stock_uom"),
			mr_item.schedule_date.as_("required_date"),
			mr_item.branch,
			mr_item.custom_batch_no,
		)
		# ── CRITICAL: submitted (1) only — excludes draft (0) & cancelled (2) ──
		.where(mr.docstatus == 1)
		
		.orderby(mr.transaction_date)
		.orderby(mr_item.idx)
	)

	# apply filter conditions
	if filters.get("from_date") and filters.get("to_date"):
		q = q.where(
			(mr.transaction_date >= filters["from_date"])
			& (mr.transaction_date <= filters["to_date"])
		)
	if filters.get("company"):
		q = q.where(mr.company == filters["company"])
	if filters.get("material_request"):
		q = q.where(mr.name == filters["material_request"])
	if filters.get("item_code"):
		q = q.where(mr_item.item_code == filters["item_code"])
	if filters.get("branch"):
		q = q.where(mr_item.branch == filters["branch"])
	if filters.get("batch"):
		q = q.where(mr_item.custom_batch_no == filters["batch"])

	rows = q.run(as_dict=True)

	# post-query status filter
	status = filters.get("status")
	if status == "Received":
		rows = [
		r for r in rows
		if r.get("mr_status_raw") in ("Received", "Partially Received")
	]

		
	elif status == "Pending":
		rows = [
		r for r in rows
		if r.get("mr_status_raw")  not in  ("Received", "Partially Received")
	]

	return rows


# ─────────────────────────────────────────────────────────────────────────────
# Query 2 — PO items
# ─────────────────────────────────────────────────────────────────────────────

def fetch_po_items_for_mrs(mr_names,filters):
	"""
	Fetch submitted PO items linked to the given MR names.
	Returns:  { (mr_name, mr_item_name): [po_row, ...] }

	Linked on BOTH material_request AND material_request_item to prevent
	a PO item appearing under the wrong MR item for the same item code.
	"""
	if not mr_names:
		return {}

	po      = frappe.qb.DocType("Purchase Order")
	po_item = frappe.qb.DocType("Purchase Order Item")

	q = (
		frappe.qb.from_(po_item)
		.join(po).on(po.name == po_item.parent)
		.select(
			po_item.material_request.as_("mr_name"),
			po_item.material_request_item.as_("mr_item_name"),
			po_item.name.as_("po_item_name"),           # used to join PR
			po.name.as_("po_no"),
			po.transaction_date.as_("po_date"),
			po.schedule_date.as_("po_required_by"),
			po.supplier,
			po_item.qty.as_("po_qty"),
			po_item.uom.as_("po_uom"),
			po_item.stock_qty.as_("po_qty_stock"),
			po_item.stock_uom.as_("po_stock_uom"),
		)
		.where(po_item.material_request.isin(mr_names))
		.where(po.docstatus == 1)
	
		.orderby(po.transaction_date)
	)

	#   Only apply supplier/PO filters when provided
	if filters.get("supplier"):
		q = q.where(po.supplier == filters["supplier"])
	
	if filters.get("po_no"):
		q = q.where(po.name == filters["po_no"])
 
	rows = q.run(as_dict=True)

	result = {}
	for r in rows:
		key = (r["mr_name"], r["mr_item_name"])
		result.setdefault(key, []).append(r)

	return result


# ─────────────────────────────────────────────────────────────────────────────
# Query 3 — PR items
# ─────────────────────────────────────────────────────────────────────────────

def fetch_pr_items_for_pos(po_item_names):
	"""
	Fetch submitted PR items linked to the given PO item names.
	Returns:  { po_item_name: [pr_row, ...] }

	Linked on `purchase_order_item` (the child row name) rather than just
	`purchase_order`.  This ensures the exact PR line that received against
	a specific PO line is shown — not every PR line on the same PO.
	"""
	if not po_item_names:
		return {}

	pr      = frappe.qb.DocType("Purchase Receipt")
	pr_item = frappe.qb.DocType("Purchase Receipt Item")

	rows = (
		frappe.qb.from_(pr_item)
		.join(pr).on(pr.name == pr_item.parent)
		.select(
			pr_item.purchase_order_item.as_("po_item_name"),
			pr_item.purchase_order.as_("po_no"),
			pr.name.as_("receipt_no"),
			pr.posting_date.as_("received_date"),
			pr_item.received_qty,
			pr_item.uom.as_("received_uom"),
			pr_item.received_stock_qty,
			pr_item.stock_uom.as_("received_stock_uom"),
		)
		.where(pr_item.purchase_order_item.isin(po_item_names))
		.where(pr.docstatus == 1)
		.orderby(pr.posting_date)
	).run(as_dict=True)

	result = {}
	for r in rows:
		key = r["po_item_name"]
		result.setdefault(key, []).append(r)

	return result


# ─────────────────────────────────────────────────────────────────────────────
# Status label
# ─────────────────────────────────────────────────────────────────────────────


def _display_status(mr_status_raw):
	"""
	Custom display status based on Material Request status.

	Blank     = All
	Received  = Partially Received + Received
	Pending   = Everything except Partially Received + Received
	"""

	if mr_status_raw in ("Received", "Partially Received"):
		return "Received"

	return "Pending"
	

# ─────────────────────────────────────────────────────────────────────────────
# Tree builder
# ─────────────────────────────────────────────────────────────────────────────

def build_tree(mr_items, po_map, pr_map):
	"""
	Produce a flat list of row dicts.  The "indent" field drives the visual
	indentation rendered by the JS formatter.

	    indent 0  →  MR row  (bold, blue bg in formatter)
	    indent 1  →  PO row  (yellow bg)
	    indent 2  →  PR row  (green bg)

	Each row starts from _blank() so only the fields relevant to that level
	are populated.  All other fields remain None → render as empty cells.
	This is the definitive fix for "PO data showing up in MR row" and vice versa.
	"""
	output = []

	# De-duplicate: one canonical MR-item row per (mr_name, item_code).
	# OrderedDict preserves the sort order from fetch_mr_items().
	mr_items_deduped = OrderedDict()
	for row in mr_items:
		key = (row["material_request"], row["item_code"])
		if key not in mr_items_deduped:
			mr_items_deduped[key] = row

	for (mr_name, item_code), mr_row in mr_items_deduped.items():

		# ── MR row ───────────────────────────────────────────────────────────
		mr_out = _blank()
		mr_out.update({
			"row_type":         "MR",
			"indent":           0,
			"bold":             1,
			"material_request": mr_name,
			"mr_date":          mr_row["mr_date"],
			"required_date":    mr_row.get("required_date"),
			"branch":           mr_row.get("branch"),
			"custom_batch_no":  mr_row.get("custom_batch_no"),
			"item_code":        item_code,
			"item_name":        mr_row.get("item_name"),
			"description":      mr_row.get("description"),
			"mr_qty":           flt(mr_row.get("mr_qty")),
			"mr_uom":           mr_row.get("mr_uom"),
			"mr_status":        _display_status(
									mr_row.get("mr_status_raw")
								),
			"company":          mr_row.get("company"),
		})
		output.append(mr_out)

		# ── PO rows ───────────────────────────────────────────────────────────
		po_rows = po_map.get((mr_name, mr_row["mr_item_name"]), [])

		if not po_rows:
			no_po = _blank()
			# no_po.update({
			# 	"row_type": "PO",
			# 	"indent":   1,
			# 	"po_no":    "— No PO Created —",
			# 	"company":  mr_row.get("company"),
			# })
			# output.append(no_po)
			continue

		

		# running PO qty tracker
		cumulative_po_qty = 0

		for po_row in po_rows:
			po_item_name = po_row["po_item_name"]
			pr_rows = pr_map.get(po_item_name, [])

			po_qty = flt(po_row.get("po_qty_stock"))

			# accumulate PO qty
			cumulative_po_qty += po_qty

			# qty still remaining to order
			qty_to_order = flt(mr_row.get("mr_stock_qty")) - cumulative_po_qty

			# prevent negative
			qty_to_order = max(qty_to_order, 0)

			# ── PR balance logic ─────────────────────────────
			total_received = sum(
				flt(p.get("received_stock_qty"))
				for p in pr_rows
			)

			balance = po_qty - total_received

			po_out = _blank()
			po_out.update({
				"row_type":       "PO",
				"indent":         1,
				"po_no":          po_row["po_no"],
				"po_date":        po_row.get("po_date"),
				"po_required_by": po_row.get("po_required_by"),
				"supplier":       po_row.get("supplier"),

				"po_qty":         flt(po_row.get("po_qty")),
				"po_uom":         po_row.get("po_uom"),

				"po_qty_stock":   po_qty,
				"po_stock_uom":   po_row.get("po_stock_uom"),

				"balance_qty":    balance,

			
				"qty_to_order":   qty_to_order,

				"company":        mr_row.get("company"),
			})

			output.append(po_out)

			# ── PR rows ───────────────────────────────────────────────────────
			if not pr_rows:
				no_pr = _blank()
				# no_pr.update({
				# 	"row_type":   "PR",
				# 	"indent":     2,
				# 	"receipt_no": "— No Receipt —",
				# 	"company":    mr_row.get("company"),
				# })
				# output.append(no_pr)
				continue

			
			cumulative_received_qty = 0

			for pr_row in pr_rows:
				current_received_qty = flt(pr_row.get("received_qty"))

				# running total
				cumulative_received_qty += current_received_qty

				# remaining qty after this receipt
				qty_to_receive = flt(po_row.get("po_qty")) - cumulative_received_qty

				# prevent negative
				qty_to_receive = max(qty_to_receive, 0)

				pr_out = _blank()
				pr_out.update({
					"row_type":           "PR",
					"indent":             2,
					"receipt_no":         pr_row["receipt_no"],
					"received_date":      pr_row.get("received_date"),

					"received_qty":       current_received_qty,
					"received_uom":       pr_row.get("received_uom"),

					"received_qty_stock": flt(pr_row.get("received_stock_qty")),
					"received_stock_uom": pr_row.get("received_stock_uom"),

				
					"qty_to_receive":     qty_to_receive,

					"company":            mr_row.get("company"),
				})

				output.append(pr_out)
	return output


# ─────────────────────────────────────────────────────────────────────────────
# Orchestrator
# ─────────────────────────────────────────────────────────────────────────────

def get_data(filters):
	# 1. Fetch MR items (docstatus=1, type=Purchase, all active filters)
	mr_items = fetch_mr_items(filters)
	if not mr_items:
		return []

	mr_names = list({r["material_request"] for r in mr_items})

	# 2. Fetch PO items for those MR names (bulk — one query)
	po_map = fetch_po_items_for_mrs(mr_names,filters)

	# Apply supplier / po_no filters on the PO map.
	# Doing this post-fetch keeps MR rows visible even when they have no PO,
	# so "No PO Created" placeholder still appears.
	supplier_f = filters.get("supplier")
	po_no_f    = filters.get("po_no")
	if supplier_f or po_no_f:
		filtered_po_map = {}
		for key, rows in po_map.items():
			kept = [
				p for p in rows
				if (not supplier_f or p["supplier"] == supplier_f)
				and (not po_no_f   or p["po_no"]    == po_no_f)
			]
			if kept:
				filtered_po_map[key] = kept
		po_map = filtered_po_map

		# ── FIX: Filter MR items to show only those associated with matching POs ──
		# When PO or supplier filter is applied, keep only MR items that have
		# at least one matching PO in the filtered po_map
		mr_items_with_pos = set()
		for (mr_name, mr_item_name) in po_map.keys():
			mr_items_with_pos.add((mr_name, mr_item_name))
		
		mr_items = [
			item for item in mr_items
			if (item["material_request"], item["mr_item_name"]) in mr_items_with_pos
		]
		
		if not mr_items:
			return []

	# 3. Fetch PR items for all PO item names (bulk — one query)
	all_po_item_names = [
		p["po_item_name"]
		for rows in po_map.values()
		for p in rows
	]
	pr_map = fetch_pr_items_for_pos(all_po_item_names)

	# 4. Assemble tree
	return build_tree(mr_items, po_map, pr_map)

def update_qty_columns(row_to_update, data_row):
	fields = ["qty", "stock_qty", "ordered_qty", "received_qty", "qty_to_receive", "qty_to_order"]
	for field in fields:
		row_to_update[field] += flt(data_row[field])


def prepare_data(data, filters):
	"""Prepare consolidated Report data and Chart data"""
	material_request_map, item_qty_map = {}, {}
	precision = cint(frappe.db.get_default("float_precision")) or 2

	for row in data:
		# item wise map for charts
		if row["item_code"] not in item_qty_map:
			item_qty_map[row["item_code"]] = {
				"qty": flt(row["stock_qty"], precision),
				"stock_qty": flt(row["stock_qty"], precision),
				"stock_uom": row["stock_uom"],
				"uom": row["uom"],
				"ordered_qty": flt(row["ordered_qty"], precision),
				"received_qty": flt(row["received_qty"], precision),
				"qty_to_receive": flt(row["qty_to_receive"], precision),
				"qty_to_order": flt(row["qty_to_order"], precision),
			}
		else:
			item_entry = item_qty_map[row["item_code"]]
			update_qty_columns(item_entry, row)

		if filters.get("group_by_mr"):
			# consolidated material request map for group by filter
			if row["material_request"] not in material_request_map:
				# create an entry with mr as key
				row_copy = copy.deepcopy(row)
				material_request_map[row["material_request"]] = row_copy
			else:
				mr_row = material_request_map[row["material_request"]]
				mr_row["required_date"] = min(getdate(mr_row["required_date"]), getdate(row["required_date"]))

				# sum numeric columns
				update_qty_columns(mr_row, row)

	chart_data = prepare_chart_data(item_qty_map)

	if filters.get("group_by_mr"):
		data = []
		for mr in material_request_map:
			data.append(material_request_map[mr])
		return data, chart_data

	return data, chart_data


def prepare_chart_data(item_data):
	labels, qty_to_order, ordered_qty, received_qty, qty_to_receive = [], [], [], [], []

	if len(item_data) > 30:
		item_data = dict(list(item_data.items())[:30])

	for row in item_data:
		mr_row = item_data[row]
		labels.append(row)
		qty_to_order.append(mr_row["qty_to_order"])
		ordered_qty.append(mr_row["ordered_qty"])
		received_qty.append(mr_row["received_qty"])
		qty_to_receive.append(mr_row["qty_to_receive"])

	chart_data = {
		"data": {
			"labels": labels,
			"datasets": [
				{"name": _("Qty to Order"), "values": qty_to_order},
				{"name": _("Ordered Qty"), "values": ordered_qty},
				{"name": _("Received Qty"), "values": received_qty},
				{"name": _("Qty to Receive"), "values": qty_to_receive},
			],
		},
		"type": "bar",
		"barOptions": {"stacked": 1},
	}

	return chart_data