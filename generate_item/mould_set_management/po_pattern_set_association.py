# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

"""Pattern association for Purchase Order lines (view-only, TASK40942).

A casting item on a PO line matches an item of the "Patterns and Die" item group when both
    Item.custom_pattern_drawing_no      and
    Item.custom_pattern_drawing_rev_no
are equal. Values are compared after trimming spaces and ignoring case, because the item
master has values like " 12T2500101_P". Drawing no alone is not a match.

The PO's Set Target Warehouse and Supplier Warehouse are NOT used. The supplier's
warehouses are the warehouses whose Supplier field (Warehouse.custom_supplier) is the PO
supplier. For each matched row:
    complete_sets    submitted, enabled Pattern Sets with current_supplier = PO supplier and
                     current_warehouse in the supplier's warehouses, status Complete,
                     that contain a matched pattern item
    incomplete_sets  the same, status Incomplete
    warehouse_qty    Bin.actual_qty of the matched pattern item(s) in the supplier's warehouses
    company_qty      Bin.actual_qty of the matched pattern item(s) in all warehouses of the
                     PO company (whole system)

Nothing is saved to the Purchase Order.
"""

import json

import frappe
from frappe import _
from frappe.utils import cint, cstr, flt
from frappe.utils.nestedset import get_descendants_of

PATTERN_ITEM_GROUP = "Patterns and Die"
MAX_ITEMS = 2000


@frappe.whitelist()
def get_pattern_set_info(items=None, supplier=None, company=None, purchase_order=None):
	"""Return pattern association info per Purchase Order row.

	:param items: list (or JSON) of {"row": <row name>, "idx": <row no>, "item_code": <item>}
	:param supplier: Purchase Order supplier
	:param company: Purchase Order company, for the company (whole system) quantity
	:param purchase_order: saved PO name, for document-level permission
	:return: {"supplier", "company", "warehouses": [...], "rows": [...]},
	        one row per PO line whose item has a pattern drawing no
	"""
	_check_permission(purchase_order)
	warehouses = _get_supplier_warehouses(supplier)
	out = {"supplier": supplier, "company": company, "warehouses": warehouses, "rows": []}

	rows = _parse_items(items)
	if not rows:
		return out

	castings = _get_casting_items({r["item_code"] for r in rows})
	keys = {c.key for c in castings.values() if c.key}
	patterns_by_key = _get_pattern_items(keys)

	pattern_codes = {p.name for plist in patterns_by_key.values() for p in plist}
	warehouse_stock = _get_actual_qty(pattern_codes, warehouses=warehouses)
	company_stock = _get_actual_qty(pattern_codes, company=company)
	sets_by_item = _get_pattern_sets(pattern_codes, supplier, warehouses)

	result = []
	for r in rows:
		casting = castings.get(r["item_code"])
		if not casting or not casting.key:
			continue  # no pattern drawing no on the item, or the item is itself a pattern

		patterns = patterns_by_key.get(casting.key, [])
		sets = {}
		for p in patterns:
			sets.update(sets_by_item.get(p.name, {}))

		result.append(
			{
				"row": r["row"],
				"idx": r["idx"],
				"item_code": r["item_code"],
				"item_name": casting.item_name,
				"pattern_drawing_no": casting.drawing_no,
				"pattern_drawing_rev_no": casting.rev_no,
				"patterns": [{"item_code": p.name, "item_name": p.item_name} for p in patterns],
				"complete_sets": sorted(n for n, s in sets.items() if s == "Complete"),
				"incomplete_sets": sorted(n for n, s in sets.items() if s != "Complete"),
				"warehouse_qty": sum(warehouse_stock.get(p.name, 0.0) for p in patterns) if warehouses else None,
				"company_qty": sum(company_stock.get(p.name, 0.0) for p in patterns),
			}
		)

	out["rows"] = result
	return out


# ---------------------------------------------------------------------- queries


def _norm(value):
	value = cstr(value).strip()
	return value.upper() if value else None


def _pattern_groups():
	return [PATTERN_ITEM_GROUP] + (get_descendants_of("Item Group", PATTERN_ITEM_GROUP) or [])


def _get_casting_items(item_codes):
	"""Item code -> {item_name, drawing_no, rev_no, key}. Pattern items themselves get no key."""
	pattern_groups = set(_pattern_groups())
	out = {}
	for item in frappe.get_all(
		"Item",
		filters={"name": ["in", list(item_codes)]},
		fields=["name", "item_name", "item_group", "custom_pattern_drawing_no", "custom_pattern_drawing_rev_no"],
	):
		drawing_no = cstr(item.custom_pattern_drawing_no).strip()
		rev_no = cstr(item.custom_pattern_drawing_rev_no).strip()
		key = None
		if drawing_no and item.item_group not in pattern_groups:
			key = (_norm(drawing_no), _norm(rev_no))
		out[item.name] = frappe._dict(item_name=item.item_name, drawing_no=drawing_no, rev_no=rev_no, key=key)
	return out


def _get_pattern_items(keys):
	"""(drawing_no, rev_no) -> [enabled Patterns and Die items with the same pair]."""
	if not keys:
		return {}

	candidates = frappe.db.sql(
		"""
		select name, item_name, custom_pattern_drawing_no, custom_pattern_drawing_rev_no
		from `tabItem`
		where item_group in %(groups)s
			and disabled = 0
			and upper(trim(custom_pattern_drawing_no)) in %(drawing_nos)s
		order by name
		""",
		{"groups": tuple(_pattern_groups()), "drawing_nos": tuple({k[0] for k in keys})},
		as_dict=True,
	)

	out = {}
	for item in candidates:
		key = (_norm(item.custom_pattern_drawing_no), _norm(item.custom_pattern_drawing_rev_no))
		if key in keys:  # drawing no AND revision must both match
			out.setdefault(key, []).append(item)
	return out


def _get_supplier_warehouses(supplier):
	"""Leaf warehouses linked to the supplier through Warehouse.custom_supplier."""
	if not supplier:
		return []
	return frappe.get_all(
		"Warehouse",
		filters={"custom_supplier": supplier, "is_group": 0, "disabled": 0},
		pluck="name",
		order_by="name",
	)


def _get_actual_qty(item_codes, warehouses=None, company=None):
	"""Item -> total Bin.actual_qty, either in the given warehouses or in all warehouses of the company."""
	if not item_codes:
		return {}
	if warehouses is not None and not warehouses:
		return {}

	conditions, values = ["b.item_code in %(items)s"], {"items": tuple(item_codes)}
	if warehouses:
		conditions.append("b.warehouse in %(warehouses)s")
		values["warehouses"] = tuple(warehouses)
	if company:
		conditions.append("w.company = %(company)s")
		values["company"] = company

	return {
		row.item_code: flt(row.qty)
		for row in frappe.db.sql(
			"""
			select b.item_code, sum(b.actual_qty) as qty
			from `tabBin` b
			inner join `tabWarehouse` w on w.name = b.warehouse
			where {}
			group by b.item_code
			""".format(" and ".join(conditions)),
			values,
			as_dict=True,
		)
	}


def _get_pattern_sets(item_codes, supplier, warehouses):
	"""Pattern item -> {pattern_set: completeness_status} for sets held by the supplier
	(current_supplier) in one of the supplier's warehouses (current_warehouse)."""
	if not item_codes or not supplier or not warehouses:
		return {}

	out = {}
	for row in frappe.db.sql(
		"""
		select distinct psc.item_code, ps.name, ps.completeness_status
		from `tabPattern Set Component` psc
		inner join `tabPattern Set` ps on ps.name = psc.parent
		where psc.parenttype = 'Pattern Set'
			and psc.parentfield = 'items'
			and psc.item_code in %(items)s
			and ps.docstatus = 1
			and ifnull(ps.disabled, 0) = 0
			and ifnull(ps.disable, 0) = 0
			and ifnull(ps.status, '') not in ('Disabled', 'Cancelled')
			and ps.current_supplier = %(supplier)s
			and ps.current_warehouse in %(warehouses)s
		""",
		{"items": tuple(item_codes), "supplier": supplier, "warehouses": tuple(warehouses)},
		as_dict=True,
	):
		out.setdefault(row.item_code, {})[row.name] = row.completeness_status
	return out


# ---------------------------------------------------------------- validation


def _check_permission(purchase_order=None):
	for doctype in ("Purchase Order", "Item"):
		if not frappe.has_permission(doctype, "read"):
			frappe.throw(_("Not permitted to read {0}.").format(_(doctype)), frappe.PermissionError)

	if purchase_order and frappe.db.exists("Purchase Order", purchase_order):
		frappe.has_permission("Purchase Order", "read", doc=purchase_order, throw=True)


def _parse_items(items):
	if isinstance(items, str):
		items = json.loads(items or "[]")
	if not items:
		return []
	if not isinstance(items, list):
		frappe.throw(_("Items must be a list."))
	if len(items) > MAX_ITEMS:
		frappe.throw(_("Too many items. Maximum allowed is {0}.").format(MAX_ITEMS))

	rows = []
	for item in items:
		if isinstance(item, dict) and cstr(item.get("item_code")).strip():
			rows.append(
				{"row": cstr(item.get("row")), "idx": cint(item.get("idx")), "item_code": cstr(item["item_code"])}
			)
	return rows
