# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

"""Pattern Set Association Details for Purchase Order (view-only).

A Pattern Set is associated with a Purchase Order when any Purchase Order Item
matches a component of a submitted, non-disabled Pattern Set on all seven fields
below, using exact (case-sensitive) equality. Nothing is saved to the PO.
"""

import json

import frappe
from frappe import _
from frappe.query_builder.functions import IfNull

# (Purchase Order Item field, Pattern Set Component field)
MATCH_FIELDS = (
	("item_code", "item_code"),
	("custom_drawing_no", "drawing_no"),
	("custom_drawing_rev_no", "drawing_rev_no"),
	("custom_pattern_drawing_no", "pattern_drawing_no"),
	("custom_pattern_drawing_rev_no", "pattern_drawing_rev_no"),
	("custom_purchase_specification_no", "purchase_specification_no"),
	("custom_purchase_specification_rev_no", "purchase_specification_rev_no"),
)

# Guard against abusive payloads. A real PO is far below this.
MAX_ITEMS = 2000


@frappe.whitelist()
def get_pattern_set_associations(items=None, purchase_order=None):
	"""Return unique Pattern Sets whose components match PO items on all 7 fields.

	:param items: list (or JSON string) of dicts with the 7 Purchase Order Item fields.
	:param purchase_order: name of the saved Purchase Order, if any (for doc-level permission).
	:return: list of dicts: pattern_set_id, supplier (Pattern Set current_supplier),
	        current_warehouse, completeness_status
	"""
	_check_permission(purchase_order)

	keys = _get_item_keys(items)
	if not keys:
		return []

	ps = frappe.qb.DocType("Pattern Set")
	psc = frappe.qb.DocType("Pattern Set Component")

	query = (
		frappe.qb.from_(psc)
		.inner_join(ps)
		.on(psc.parent == ps.name)
		.select(
			ps.name,
			ps.current_supplier,
			ps.current_warehouse,
			ps.completeness_status,
			*[psc[component_field] for _po_field, component_field in MATCH_FIELDS],
		)
		.where(psc.parenttype == "Pattern Set")
		.where(psc.parentfield == "items")
		.where(ps.docstatus == 1)
		# Exclude disabled Pattern Sets (current flag, legacy flag and status).
		.where(IfNull(ps.disabled, 0) == 0)
		.where(IfNull(ps.disable, 0) == 0)
		.where(IfNull(ps.status, "") != "Disabled")
		.orderby(ps.name)
	)

	# Narrow the scan in SQL: each component field must be one of the requested values.
	# This is a pre-filter only, the exact 7-field tuple match is done below.
	for index, (_po_field, component_field) in enumerate(MATCH_FIELDS):
		query = query.where(psc[component_field].isin(sorted({key[index] for key in keys})))

	rows = query.run(as_dict=True)

	# Exact, case-sensitive tuple match. SQL comparison uses the table collation
	# (case and trailing-space insensitive), so it cannot be trusted on its own.
	result = {}
	for row in rows:
		if row.name in result:
			continue
		component_key = tuple(row.get(component_field) for _po_field, component_field in MATCH_FIELDS)
		if component_key in keys:
			result[row.name] = {
				"pattern_set_id": row.name,
				"supplier": row.current_supplier,
				"current_warehouse": row.current_warehouse,
				"completeness_status": row.completeness_status,
			}

	return list(result.values())


def _check_permission(purchase_order=None):
	"""Allow only users who can read Purchase Orders (and this PO, if it is saved)."""
	if not frappe.has_permission("Purchase Order", "read"):
		frappe.throw(_("Not permitted to view Purchase Orders."), frappe.PermissionError)

	if purchase_order and frappe.db.exists("Purchase Order", purchase_order):
		if not frappe.has_permission("Purchase Order", "read", doc=purchase_order):
			frappe.throw(
				_("Not permitted to view Purchase Order {0}.").format(purchase_order),
				frappe.PermissionError,
			)


def _get_item_keys(items):
	"""Build the set of complete 7-field tuples. Items with any blank field are ignored.

	Values are not trimmed or case-folded, so matching stays exact.
	"""
	if isinstance(items, str):
		items = json.loads(items) if items else []

	if not items:
		return set()

	if not isinstance(items, list):
		frappe.throw(_("Items must be a list."))

	if len(items) > MAX_ITEMS:
		frappe.throw(_("Too many items. Maximum allowed is {0}.").format(MAX_ITEMS))

	keys = set()
	for item in items:
		if not isinstance(item, dict):
			continue

		key = tuple(_as_text(item.get(po_field)) for po_field, _component_field in MATCH_FIELDS)
		if all(value is not None for value in key):
			keys.add(key)

	return keys


def _as_text(value):
	"""Return the value as a string, or None if it is blank or not a scalar."""
	if value is None or isinstance(value, bool | dict | list):
		return None
	if not isinstance(value, str):
		value = str(value)
	return value if value.strip() else None
