# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

"""CRM Notes <-> Sales Order sync.

One field map drives all three paths:
  1. auto create a Draft CRM Note when a Sales Order is inserted (after_insert hook)
  2. "Get Update" button on a Draft CRM Note
  3. CRM Notes before_submit re-sync
"""

import frappe
from frappe import _
from frappe.utils import cstr, escape_html, flt, getdate

# CRM Notes field -> Sales Order field
CRM_NOTE_SO_FIELD_MAP = {
	"order_date": "transaction_date",
	"branch": "branch",
	"delivery_date": "delivery_date",
	"customer": "customer",
	"customers_purchase_order": "po_no",
	"customers_purchase_order_date": "po_date",
	"order_amount": "grand_total",
}

DATE_FIELDS = {"order_date", "delivery_date", "customers_purchase_order_date"}
AMOUNT_FIELDS = {"order_amount"}


def _normalise(crm_note, field, value):
	if value in (None, ""):
		return None
	if field in DATE_FIELDS:
		return getdate(value)
	if field in AMOUNT_FIELDS:
		return flt(value, crm_note.precision(field))
	return cstr(value)


def get_sales_order(crm_note):
	"""Return the linked Sales Order; throw if missing, deleted or cancelled."""
	so_name = crm_note.order_number
	if not so_name:
		frappe.throw(_("Order Number is not set on this CRM Note."))
	if not frappe.db.exists("Sales Order", so_name):
		frappe.throw(_("Sales Order {0} no longer exists.").format(so_name))

	so = frappe.get_doc("Sales Order", so_name)
	if so.docstatus == 2:
		frappe.throw(_("Sales Order {0} is cancelled. CRM Note cannot be updated from it.").format(so_name))
	return so


def apply_sales_order_values(crm_note, so=None):
	"""Copy mapped Sales Order values onto crm_note in memory. Does not save.

	Returns a list of {field, label, old, new} for the values that changed.
	The rich-text CRM notes, meeting date and naming series are never touched.
	"""
	so = so or get_sales_order(crm_note)
	changes = []
	for field, so_field in CRM_NOTE_SO_FIELD_MAP.items():
		old, new = crm_note.get(field), so.get(so_field)
		if _normalise(crm_note, field, old) == _normalise(crm_note, field, new):
			continue
		crm_note.set(field, new)
		changes.append({"field": field, "label": crm_note.meta.get_label(field), "old": old, "new": new})
	return changes


def changes_html(crm_note, changes):
	def fmt(field, value):
		if value in (None, ""):
			return "-"
		return escape_html(cstr(frappe.format_value(value, crm_note.meta.get_field(field), doc=crm_note)))

	rows = "".join(
		"<tr><td>{}</td><td>{}</td><td>{}</td></tr>".format(
			escape_html(_(c["label"])), fmt(c["field"], c["old"]), fmt(c["field"], c["new"])
		)
		for c in changes
	)
	return (
		'<table class="table table-bordered table-sm">'
		"<thead><tr><td><b>{}</b></td><td><b>{}</b></td><td><b>{}</b></td></tr></thead><tbody>{}</tbody></table>"
	).format(_("Field"), _("Old Value"), _("New Value"), rows)


# ---------------------------------------------------------------- 1. auto create


def create_crm_note_for_sales_order(so):
	"""Return (crm_note_name, created). Reuses a Draft or submitted note if one exists."""
	existing = frappe.db.get_value(
		"CRM Notes", {"order_number": so.name, "docstatus": ["<", 2]}, "name", order_by="creation desc"
	)
	if existing:
		return existing, False

	# CRM Notes are named after the Sales Order, so a cancelled note blocks a new one with the same name
	if frappe.db.exists("CRM Notes", so.name):
		frappe.throw(
			_("CRM Note {0} is cancelled. Amend it instead of creating a new one.").format(
				frappe.utils.get_link_to_form("CRM Notes", so.name)
			)
		)

	crm_note = frappe.new_doc("CRM Notes")
	crm_note.order_number = so.name
	apply_sales_order_values(crm_note, so)
	# CRM Meeting Date is mandatory, but only needed when the note is submitted
	crm_note.insert(ignore_permissions=True, ignore_mandatory=True)
	return crm_note.name, True


def on_sales_order_insert(doc, method=None):
	"""Sales Order after_insert: create a Draft CRM Note. Never blocks the Sales Order."""
	savepoint = "crm_note_auto_create"
	frappe.db.savepoint(savepoint)
	try:
		create_crm_note_for_sales_order(doc)
	except Exception:
		frappe.db.rollback(save_point=savepoint)
		frappe.clear_last_message()
		frappe.log_error(
			title=_("CRM Note auto create failed for Sales Order {0}").format(doc.name),
			message=frappe.get_traceback(),
			reference_doctype="Sales Order",
			reference_name=doc.name,
		)


# ---------------------------------------------------------------- 2. Get Update


@frappe.whitelist()
def get_update_from_sales_order(crm_note):
	note = frappe.get_doc("CRM Notes", crm_note)
	note.check_permission("write")
	if note.docstatus != 0:
		frappe.throw(_("Only a Draft CRM Note can be updated from its Sales Order."))

	changes = apply_sales_order_values(note)
	if changes:
		note.flags.ignore_mandatory = True
		note.save()

	return {
		"changes": [{"field": c["field"], "label": c["label"]} for c in changes],
		"message_html": changes_html(note, changes) if changes else "",
	}
