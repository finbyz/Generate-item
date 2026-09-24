# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, nowdate, date_diff
from frappe.model.document import Document
from generate_item.utils.inspector_inches import (
    calculate_doc_inspector_inches,
    get_serial_register_items as _get_serial_register_items,
    validate_serial_for_testing_phase,
    get_valve_testing_serial_query,
)
from generate_item.utils.naming_series import revert_series_on_trash


# ── DocType class ─────────────────────────────────────────────────────────────

class ValveTesting(Document):

    def validate(self):
        self.validate_line_items()
        self.validate_dates()
        self.validate_testing_phase()
        self.validate_serial_numbers()

    def validate_line_items(self):
        if not self.item_serial_number:
            frappe.throw(
                frappe._("Please add at least one item in the <b>Item Serial Number</b> table before saving.")
            )

    def validate_testing_phase(self):
        if not self.testing_phase:
            frappe.throw(
                frappe._("Please select a {0} before saving.").format(frappe.bold("Testing Phase")),
                title=frappe._("Mandatory")
            )

    def validate_dates(self):
        today = getdate(nowdate())

        if self.posting_date:
            posting = getdate(self.posting_date)
            diff = date_diff(today, posting)   # positive = past, negative = future
            if diff < 0:
                frappe.throw(
                    frappe._("{0} cannot be a future date.").format(frappe.bold("Posting Date")),
                    title=frappe._("Invalid Date")
                )
            elif diff > 0 and not self.allow_back_date:
                frappe.throw(
                    frappe._("{0} cannot be set to a past date unless {1} is enabled.").format(
                        frappe.bold("Posting Date"), frappe.bold("Allow Back Date")
                    ),
                    title=frappe._("Back-Dating Not Allowed")
                )

        for row in getattr(self, "item_serial_number", []):
            if getattr(row, "date", None):
                row_date = getdate(row.date)
                diff = date_diff(today, row_date)
                if diff < 0:
                    frappe.throw(
                        frappe._("Row #{0}: {1} cannot be a future date.").format(
                            row.idx, frappe.bold("Date")
                        ),
                        title=frappe._("Invalid Date")
                    )
                elif diff > 0 and not self.allow_back_date:
                    frappe.throw(
                        frappe._("Row #{0}: {1} cannot be set to a past date unless {2} is enabled.").format(
                            row.idx, frappe.bold("Date"), frappe.bold("Allow Back Date")
                        ),
                        title=frappe._("Back-Dating Not Allowed")
                    )

    def validate_serial_numbers(self):
        for row in getattr(self, "item_serial_number", []):
            if getattr(row, "serial_number", None):
                is_valid, err_msg = validate_serial_for_testing_phase(
                    row.serial_number, self.testing_phase
                )
                if not is_valid and err_msg:
                    frappe.throw(
                        frappe._("Row #{0}: {1}").format(row.idx, err_msg)
                    )

    def before_save(self):
        calculate_doc_inspector_inches(self)

    def on_trash(self):
        revert_series_on_trash(self)


# ── Whitelisted API ───────────────────────────────────────────────────────────

@frappe.whitelist()
def get_serial_register_items(sales_order=None, batch_number=None, serial_number=None, branch=None, testing_phase=None):
    """
    Get Serial Number records from Serial Number DocType for Valve Testing.
    """
    return _get_serial_register_items(
        doctype="Valve Testing",
        sales_order=sales_order,
        batch_number=batch_number,
        serial_number=serial_number,
        branch=branch,
        testing_phase=testing_phase,
    )


@frappe.whitelist()
def serial_number_query(doctype, txt, searchfield, start, page_len, filters):
    """
    Query handler for serial_number Link field.
    """
    return get_valve_testing_serial_query(doctype, txt, searchfield, start, page_len, filters)
