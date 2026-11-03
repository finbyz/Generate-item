# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class ComponentPairingLog(Document):
	def validate(self):
		if not frappe.flags.ignore_permissions and not getattr(frappe.flags, "in_test", False):
			if self.is_new() and not getattr(self, "_allow_create", False):
				frappe.throw(_("Component Pairing Log entries cannot be created manually."))
			elif not self.is_new() and not getattr(self, "_allow_update", False):
				frappe.throw(_("Component Pairing Log entries cannot be edited manually."))

	def on_trash(self):
		if not frappe.flags.ignore_permissions and not getattr(frappe.flags, "in_test", False):
			frappe.throw(_("Component Pairing Log entries are immutable and cannot be deleted."))


def log_pairing(serial_no, item_code, pattern_set, change_ref=None, reason=None, source_doctype=None, source_doc=None):
	"""
	Logs the pairing (attach) of a serial number to a Pattern Set.
	"""
	doc = frappe.new_doc("Component Pairing Log")
	doc.serial_no = serial_no
	doc.item_code = item_code or frappe.db.get_value("Serial No", serial_no, "item_code")
	doc.pattern_set = pattern_set
	doc.paired_on = now_datetime()
	doc.reason = reason
	doc.change_ref = change_ref
	if source_doctype and source_doc:
		doc.source_doctype = source_doctype
		doc.source_doc = source_doc
	elif change_ref:
		doc.source_doctype = "Pattern Set Component Change"
		doc.source_doc = change_ref
	doc._allow_create = True
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	return doc


def close_pairing(serial_no, pattern_set=None, change_ref=None, reason=None, source_doctype=None, source_doc=None):
	"""
	Closes the currently active pairing of a serial number.
	"""
	filters = {"serial_no": serial_no, "unpaired_on": ("is", "not set")}
	if pattern_set:
		filters["pattern_set"] = pattern_set

	open_logs = frappe.get_all(
		"Component Pairing Log",
		filters=filters,
		fields=["name", "reason"],
		order_by="paired_on desc",
		limit=1,
	)

	if open_logs:
		log_doc = frappe.get_doc("Component Pairing Log", open_logs[0].name)
		log_doc.unpaired_on = now_datetime()
		if reason:
			log_doc.reason = f"{log_doc.reason}\n{reason}".strip() if log_doc.reason else reason
		if source_doctype and source_doc:
			log_doc.source_doctype = source_doctype
			log_doc.source_doc = source_doc
		elif change_ref:
			log_doc.change_ref = change_ref
		log_doc._allow_update = True
		log_doc.flags.ignore_permissions = True
		log_doc.save(ignore_permissions=True)
		return log_doc
	return None
