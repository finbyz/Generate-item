# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CRMNotes(Document):
	def before_submit(self):
		"""Re-sync from the Sales Order so a submitted note matches it at submission time.

		before_submit runs before the row is written, so the changes are saved with the submit.
		"""
		from generate_item.utils.crm_notes import apply_sales_order_values, changes_html

		changes = apply_sales_order_values(self)
		if changes:
			frappe.msgprint(
				changes_html(self, changes),
				title=frappe._("CRM Note updated from Sales Order {0}").format(self.order_number),
				indicator="blue",
			)

import frappe
from frappe import _
from frappe.utils import get_link_to_form


def submit_draft_crm_notes(doc, method=None):
    """On Sales Order submit/approval, submit all Draft CRM Notes linked to it.

    The Sales Order is never blocked. Notes that cannot be submitted stay in
    Draft, and the user is shown a message explaining why.
    """
    notes = frappe.get_all(
        "CRM Notes",
        filters={"order_number": doc.name, "docstatus": 0},
        pluck="name",
        order_by="creation asc",
    )
    if not notes:
        return

    submitted, failed = [], []  # failed = [(note_name, reason)]

    for note_name in notes:
        savepoint = f"crm_note_{frappe.generate_hash(length=6)}"
        frappe.db.savepoint(savepoint)

        try:
            note = frappe.get_doc("CRM Notes", note_name)

            if note.docstatus != 0 or note.order_number != doc.name:
                continue

            note.submit()  # runs validate / before_submit / on_submit
            submitted.append(note_name)

        except Exception as e:
            # Undo any partial changes of this note only; the Sales Order is untouched
            frappe.db.rollback(save_point=savepoint)
            frappe.log_error(
                title=f"CRM Note auto-submit failed: {note_name} (SO: {doc.name})",
                message=frappe.get_traceback(),
            )
            failed.append((note_name, frappe.utils.strip_html_tags(str(e)) or _("Unknown error")))

    if submitted:
        frappe.msgprint(
            _("{0} CRM Note(s) submitted for {1}.").format(len(submitted), doc.name),
            alert=True,
            indicator="green",
        )

    if failed:
        frappe.msgprint(
            _("Sales Order {0} is submitted, but the following CRM Notes could not be submitted. ").format(doc.name),
            alert=True,
            indicator="orange",
        )