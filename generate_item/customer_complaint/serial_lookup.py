# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

"""Serial lookups for the Customer Complaint (Issue) Current Order flow, TASK41458.

Source of truth is core ERPNext stock data:
    Serial No  <-  Serial and Batch Entry  <-  Serial and Batch Bundle (Delivery Note, submitted, Outward)
               ->  Delivery Note Item.against_sales_order  ->  Sales Order
A serial counts as delivered against a Sales Order when a submitted, non-return Delivery Note
for that order moved it out, and the Serial No is still in status Delivered (so returned
serials, which go back to Active, are not offered).

Fallbacks for the reverse lookup, in order: Serial No + its Batch's Sales Order, then the
custom Serial Number register (Batch -> Batch.reference_name).
"""

import frappe
from frappe import _
from frappe.utils import cint

MAX_ROWS = 1000

_DELIVERED_SQL = """
	SELECT
		e.serial_no,
		sn.item_code,
		i.item_name,
		COALESCE(NULLIF(e.batch_no, ''), sn.batch_no) AS batch_no,
		dni.against_sales_order AS sales_order,
		dn.name AS delivery_note,
		dn.posting_date,
		dn.customer
	FROM `tabSerial and Batch Entry` e
	INNER JOIN `tabSerial and Batch Bundle` sbb
		ON sbb.name = e.parent
		AND sbb.voucher_type = 'Delivery Note'
		AND sbb.docstatus = 1
		AND sbb.type_of_transaction = 'Outward'
	INNER JOIN `tabDelivery Note Item` dni ON dni.name = sbb.voucher_detail_no
	INNER JOIN `tabDelivery Note` dn ON dn.name = dni.parent AND dn.docstatus = 1 AND IFNULL(dn.is_return, 0) = 0
	INNER JOIN `tabSerial No` sn ON sn.name = e.serial_no
	LEFT JOIN `tabItem` i ON i.name = sn.item_code
	WHERE IFNULL(e.serial_no, '') != '' AND sn.status = 'Delivered' AND {conditions}
	ORDER BY dn.posting_date DESC, e.serial_no
"""


@frappe.whitelist()
def get_delivered_serials(sales_order, batch_no=None, txt=None, exclude=None):
	"""Serials delivered against a Sales Order, for the complaint serial picker.

	:param sales_order: Sales Order (required)
	:param batch_no: optional Batch filter
	:param txt: optional search text on serial no or item code
	:param exclude: optional list (or JSON list) of serials already on the complaint
	:return: {"rows": [...], "truncated": bool}
	"""
	if not sales_order:
		frappe.throw(_("Select a Sales Order first."))
	frappe.has_permission("Sales Order", "read", sales_order, throw=True)

	conditions = ["dni.against_sales_order = %(sales_order)s"]
	values = {"sales_order": sales_order}
	if batch_no:
		conditions.append("COALESCE(NULLIF(e.batch_no, ''), sn.batch_no) = %(batch_no)s")
		values["batch_no"] = batch_no
	if txt:
		conditions.append("(e.serial_no LIKE %(txt)s OR sn.item_code LIKE %(txt)s)")
		values["txt"] = f"%{txt.strip()}%"

	if isinstance(exclude, str):
		exclude = frappe.parse_json(exclude) if exclude else []
	exclude = {s for s in (exclude or []) if s}

	rows, seen = [], set()
	for r in frappe.db.sql(_DELIVERED_SQL.format(conditions=" AND ".join(conditions)), values, as_dict=True):
		if r.serial_no in seen or r.serial_no in exclude:
			continue  # one row per serial (latest delivery first)
		seen.add(r.serial_no)
		rows.append(r)

	truncated = len(rows) > MAX_ROWS
	return {"rows": rows[:MAX_ROWS], "truncated": truncated, "total": len(rows)}


@frappe.whitelist()
def get_delivered_batches(sales_order):
	"""Batches that have serials delivered against the Sales Order (for the picker's Batch filter)."""
	if not sales_order:
		return []
	frappe.has_permission("Sales Order", "read", sales_order, throw=True)
	return sorted(
		{
			r.batch_no
			for r in frappe.db.sql(
				_DELIVERED_SQL.format(conditions="dni.against_sales_order = %(so)s"), {"so": sales_order}, as_dict=True
			)
			if r.batch_no
		}
	)


@frappe.whitelist()
def get_serial_details(serial_no):
	"""Reverse lookup: Sales Order, batch, item and customer of a valve serial.

	Returns {} when the serial is not found anywhere, else a dict with item_code, batch_no,
	sales_order, customer, delivery_note (may be empty) and source.
	"""
	serial_no = (serial_no or "").strip()
	if not serial_no:
		return {}

	# 1. Delivered: the latest delivery of this serial
	delivered = frappe.db.sql(
		_DELIVERED_SQL.format(conditions="e.serial_no = %(sn)s") + " LIMIT 1", {"sn": serial_no}, as_dict=True
	)
	if delivered:
		d = delivered[0]
		return {
			"item_code": d.item_code,
			"batch_no": d.batch_no,
			"sales_order": d.sales_order,
			"customer": d.customer,
			"delivery_note": d.delivery_note,
			"source": "Delivery Note",
		}

	# 2. Core Serial No, not (or no longer) delivered
	sn = frappe.db.get_value("Serial No", serial_no, ["item_code", "batch_no", "customer"], as_dict=True)
	if sn:
		so = _batch_sales_order(sn.batch_no)
		return {
			"item_code": sn.item_code,
			"batch_no": sn.batch_no,
			"sales_order": so,
			"customer": sn.customer or _so_customer(so),
			"delivery_note": None,
			"source": "Serial No",
		}

	# 3. Custom Serial Number register
	reg = frappe.db.get_value("Serial Number", serial_no, ["batch"], as_dict=True)
	if reg and reg.batch:
		item, so = frappe.db.get_value("Batch", reg.batch, ["item", "reference_name"]) or (None, None)
		so = so if so and frappe.db.exists("Sales Order", so) else None
		return {
			"item_code": item,
			"batch_no": reg.batch,
			"sales_order": so,
			"customer": _so_customer(so),
			"delivery_note": None,
			"source": "Serial Register",
		}
	return {}


def _batch_sales_order(batch_no):
	if not batch_no:
		return None
	ref_dt, ref_name = frappe.db.get_value("Batch", batch_no, ["reference_doctype", "reference_name"]) or (None, None)
	return ref_name if ref_dt == "Sales Order" and ref_name else None


def _so_customer(sales_order):
	return frappe.db.get_value("Sales Order", sales_order, "customer") if sales_order else None
