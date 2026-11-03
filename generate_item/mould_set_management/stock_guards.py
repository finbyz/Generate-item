# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def validate_stock_entry(doc, method=None):
	"""
	Enforces Section 8: Guard rules on Stock Entry.
	1. If created by a Pattern Set Transfer, verify it is legitimate.
	2. If any serial has custom_pattern_set, block unless created by Pattern Set Transfer.
	3. Stock Entry from a set transfer must contain every serial still attached to the set.
	"""
	# Users cannot set custom_pattern_set_transfer manually
	if doc.custom_pattern_set_transfer and not doc.flags.ignore_permissions and not getattr(frappe.flags, "in_test", False):
		if not frappe.db.exists("Pattern Set Transfer", doc.custom_pattern_set_transfer):
			frappe.throw(_("Invalid Pattern Set Transfer reference."))

	# Extract all serial numbers from the stock entry items
	serials_in_entry = []
	for item in (doc.items or []):
		if getattr(item, "serial_no", None):
			for sn in item.serial_no.strip().split("\n"):
				sn_clean = sn.strip()
				if sn_clean:
					serials_in_entry.append(sn_clean)

	if not serials_in_entry:
		return

	# Check which serials have custom_pattern_set
	attached_serials = frappe.get_all(
		"Serial No",
		filters={"name": ["in", serials_in_entry], "custom_pattern_set": ["is", "set"]},
		fields=["name", "custom_pattern_set"],
	)

	if not attached_serials:
		return

	# If there are attached serials:
	if not doc.custom_pattern_set_transfer:
		first = attached_serials[0]
		frappe.throw(
			_("Serial {0} belongs to {1}. Use Pattern Set Transfer to move the set, or detach it first.").format(
				frappe.bold(first.name), frappe.bold(first.custom_pattern_set)
			)
		)

	# If it IS created by Pattern Set Transfer:
	# Verify that the Stock Entry contains every serial still attached to the set (Rule: Stock Entry from a set transfer must contain every serial still attached to the set)
	pst_name = doc.custom_pattern_set_transfer
	pst = frappe.get_doc("Pattern Set Transfer", pst_name)
	expected_serials = {r.serial_no for r in pst.items if r.include}
	actual_serials = set(serials_in_entry)
	missing = expected_serials - actual_serials
	if missing:
		frappe.throw(
			_("Stock Entry from Pattern Set Transfer {0} is missing attached serial(s): {1}.").format(
				pst_name, ", ".join(missing)
			)
		)


def validate_stock_entry_cancel(doc, method=None):
	"""
	Section 7.5: A Stock Entry that has the field Pattern Set Transfer filled
	cannot be cancelled, amended or deleted directly. The user must cancel the Pattern Set Transfer.
	"""
	if doc.custom_pattern_set_transfer and not getattr(doc.flags, "allow_pattern_set_transfer_cancel", False):
		frappe.throw(
			_("Stock Entry {0} was created by Pattern Set Transfer {1}. You cannot cancel it directly; please cancel the Pattern Set Transfer instead.").format(
				doc.name, frappe.bold(doc.custom_pattern_set_transfer)
			)
		)


def validate_stock_entry_delete(doc, method=None):
	if doc.custom_pattern_set_transfer and not getattr(doc.flags, "allow_pattern_set_transfer_cancel", False):
		frappe.throw(
			_("Stock Entry {0} was created by Pattern Set Transfer {1} and cannot be deleted directly.").format(
				doc.name, frappe.bold(doc.custom_pattern_set_transfer)
			)
		)


def validate_serial_movement_in_generic_stock_doc(doc, method=None):
	"""
	Section 8: Delivery Note, Sales Invoice (update stock), Purchase Receipt return,
	Purchase Invoice return, Stock Reconciliation, Subcontracting receipts, etc.
	Block if the serial has a Pattern Set. Message tells the user to detach first through a Component Change.
	"""
	# Check if document updates stock
	if doc.doctype == "Sales Invoice" and not getattr(doc, "update_stock", False):
		return

	serials_in_doc = []
	for item in (getattr(doc, "items", []) or []):
		if getattr(item, "serial_no", None):
			for sn in item.serial_no.strip().split("\n"):
				sn_clean = sn.strip()
				if sn_clean:
					serials_in_doc.append(sn_clean)

	if not serials_in_doc:
		return

	attached_serials = frappe.get_all(
		"Serial No",
		filters={"name": ["in", serials_in_doc], "custom_pattern_set": ["is", "set"]},
		fields=["name", "custom_pattern_set"],
	)

	if attached_serials:
		first = attached_serials[0]
		frappe.throw(
			_("Serial {0} is attached to Pattern Set {1}. Please detach it first through a Pattern Set Component Change before proceeding with {2}.").format(
				frappe.bold(first.name), frappe.bold(first.custom_pattern_set), doc.doctype
			)
		)


def validate_serial_no_change(doc, method=None):
	"""
	Section 8: An attached serial cannot be deleted. Its status cannot be set to anything other than Active manually.
	"""
	if doc.custom_pattern_set and doc.status != "Active":
		frappe.throw(
			_("Serial No {0} is attached to Pattern Set {1}. Its status cannot be set to {2} while attached. Detach it first via Pattern Set Component Change.").format(
				frappe.bold(doc.name), frappe.bold(doc.custom_pattern_set), frappe.bold(doc.status)
			)
		)


def validate_serial_no_delete(doc, method=None):
	"""
	Section 8: An attached serial cannot be deleted.
	"""
	if doc.custom_pattern_set:
		frappe.throw(
			_("Cannot delete Serial No {0} because it is currently attached to Pattern Set {1}. Detach it first via Pattern Set Component Change.").format(
				frappe.bold(doc.name), frappe.bold(doc.custom_pattern_set)
			)
		)

