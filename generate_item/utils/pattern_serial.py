# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

"""Automatic serial numbers for Pattern and Die items on Purchase Receipt submit.

Hook: Purchase Receipt `before_submit`.

For every row whose Item is in the "Patterns and Die" item group (or a sub-group), the
serial numbers are written into `row.serial_no` (and `row.rejected_serial_no` for rejected
qty) as `{Pattern Drawing No}-001`, `-002`, ... ERPNext's own `on_submit`
(`make_bundle_using_old_serial_batch_fields`) then creates the Serial and Batch Bundle and the
standard Serial No records, Active in the row warehouse. Nothing is inserted here directly.

The running number is per Pattern Drawing No (Item.custom_pattern_drawing_no), across all
receipts, kept in `tabSeries` under `PATTERN-SERIAL::{DRAWING NO}-`. The counter row is locked
with SELECT ... FOR UPDATE and updated in the submit transaction, so a failed submit rolls the
counter back too. The revision is not part of the serial number.
"""

import re

import frappe
from frappe import _
from frappe.utils import cint, flt
from frappe.utils.nestedset import get_descendants_of

from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

PATTERN_ITEM_GROUP = "Patterns and Die"
SERIAL_DIGITS = 3  # -001
SERIES_KEY_PREFIX = "PATTERN-SERIAL::"


def create_pattern_serials(doc, method=None):
	if doc.get("is_return") or doc.is_internal_transfer():
		return

	pattern_groups = _pattern_groups()
	plan = {}  # counter key -> {"drawing_no": str, "parts": [(row, field, qty)]}

	for row in doc.items:
		item = frappe.get_cached_value(
			"Item",
			row.item_code,
			["item_group", "has_serial_no", "custom_pattern_drawing_no"],
			as_dict=True,
		)
		if not item or item.item_group not in pattern_groups:
			continue
		if row.get("serial_and_batch_bundle") or row.get("rejected_serial_and_batch_bundle"):
			continue  # serials already picked through a bundle (7.5)

		accepted = _whole_qty(row, flt(row.stock_qty), _("Accepted"))
		rejected = _whole_qty(row, flt(row.rejected_qty) * flt(row.conversion_factor or 1), _("Rejected"))
		if not accepted and not rejected:
			continue

		if not cint(item.has_serial_no):
			frappe.throw(
				_("Row #{0}: Item {1} is in Item Group {2} but Has Serial No is not enabled.").format(
					row.idx, frappe.bold(row.item_code), frappe.bold(item.item_group)
				),
				title=_("Pattern Serial Number"),
			)

		drawing_no = (item.custom_pattern_drawing_no or "").strip()
		_validate_drawing_no(row, drawing_no)

		for field, qty in (("serial_no", accepted), ("rejected_serial_no", rejected)):
			if not qty:
				continue
			existing = get_serial_nos(row.get(field))
			if existing:
				if len(existing) != qty:
					frappe.throw(
						_(
							"Row #{0}: {1} serial numbers entered for quantity {2}. "
							"Clear the field to generate them automatically."
						).format(row.idx, len(existing), qty),
						title=_("Pattern Serial Number"),
					)
				continue  # typed by hand or carried over from an amended receipt: keep
			key = drawing_no.upper()
			plan.setdefault(key, {"drawing_no": drawing_no, "parts": []})["parts"].append((row, field, qty))

	summary = []
	for key, entry in plan.items():
		total = sum(qty for _row, _field, qty in entry["parts"])
		start = _reserve_block(entry["drawing_no"], total)
		for row, field, qty in entry["parts"]:
			drawing_no = entry["drawing_no"]
			serials = [f"{drawing_no}-{str(n).zfill(SERIAL_DIGITS)}" for n in range(start, start + qty)]
			row.set(field, "\n".join(serials))
			row.use_serial_batch_fields = 1
			start += qty
			label = _("Rejected") if field == "rejected_serial_no" else _("Accepted")
			summary.append(
				_("Row #{0} {1} ({2}): {3}").format(
					row.idx,
					frappe.bold(row.item_code),
					label,
					serials[0] if qty == 1 else f"{serials[0]} to {serials[-1]}",
				)
			)

	if summary:
		frappe.msgprint(
			"<br>".join(summary), title=_("Pattern Serial Numbers Created"), indicator="green"
		)


# --------------------------------------------------------------------------- helpers


def _pattern_groups():
	return {PATTERN_ITEM_GROUP, *(get_descendants_of("Item Group", PATTERN_ITEM_GROUP) or [])}


def _whole_qty(row, qty, label):
	if not qty:
		return 0
	if abs(qty - round(qty)) > 1e-9:
		frappe.throw(
			_("Row #{0}: {1} quantity {2} is not a whole number. Pattern and Die items are serialised one piece at a time.").format(
				row.idx, label, qty
			),
			title=_("Pattern Serial Number"),
		)
	return int(round(qty))


def _validate_drawing_no(row, drawing_no):
	if not drawing_no:
		frappe.throw(
			_("Row #{0}: Pattern Drawing No is not set on Item {1}. It is needed to create the serial numbers.").format(
				row.idx, frappe.bold(row.item_code)
			),
			title=_("Pattern Serial Number"),
		)
	if "," in drawing_no or "\n" in drawing_no or "\r" in drawing_no:
		frappe.throw(
			_("Row #{0}: Pattern Drawing No {1} of Item {2} contains a comma or line break, which cannot be used in a serial number.").format(
				row.idx, frappe.bold(drawing_no), frappe.bold(row.item_code)
			),
			title=_("Pattern Serial Number"),
		)


def _reserve_block(drawing_no, qty):
	"""Reserve `qty` numbers for the drawing no and return the first one.

	The counter row is locked until the submit transaction ends, so concurrent receipts
	cannot get the same numbers, and a failed submit rolls the counter back.
	"""
	key = f"{SERIES_KEY_PREFIX}{drawing_no.upper()}-"
	current = frappe.db.sql("SELECT `current` FROM `tabSeries` WHERE `name`=%s FOR UPDATE", key)
	if current:
		current = cint(current[0][0])
	else:
		current = _max_existing_suffix(drawing_no)
		frappe.db.sql("INSERT INTO `tabSeries` (`name`, `current`) VALUES (%s, %s)", (key, current))
		frappe.db.sql("SELECT `current` FROM `tabSeries` WHERE `name`=%s FOR UPDATE", key)

	# never reuse a number that already exists as a Serial No (opening stock, manual entry)
	current = max(current, _max_existing_suffix(drawing_no))
	frappe.db.sql("UPDATE `tabSeries` SET `current`=%s WHERE `name`=%s", (current + qty, key))
	return current + 1


def _max_existing_suffix(drawing_no):
	"""Highest N among Serial Nos named exactly `{drawing_no}-N` (digits only), else 0."""
	like = drawing_no.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "-%"
	pattern = re.compile(re.escape(drawing_no) + r"-(\d+)", re.IGNORECASE)
	highest = 0
	for (name,) in frappe.db.sql("SELECT name FROM `tabSerial No` WHERE name LIKE %s", like):
		match = pattern.fullmatch(name)
		if match:
			highest = max(highest, cint(match.group(1)))
	return highest
