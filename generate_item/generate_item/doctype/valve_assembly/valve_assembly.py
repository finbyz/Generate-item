# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, nowdate, date_diff
from frappe.model.document import Document
from generate_item.utils.inspector_inches import (
    calculate_doc_inspector_inches,
    get_serial_register_items as _get_serial_register_items,
)
from generate_item.utils.naming_series import revert_series_on_trash


# ── DocType class ─────────────────────────────────────────────────────────────

class ValveAssembly(Document):

    def validate(self):
        self.validate_line_items()
        self.validate_dates()

    def validate_line_items(self):
        if not self.item_serial_number:
            frappe.throw(
                frappe._("Please add at least one item in the <b>Item Serial Number</b> table before saving.")
            )

    def validate_dates(self):
        today = getdate(nowdate())

        if self.posting_date:
            posting = getdate(self.posting_date)
            diff = date_diff(today, posting)
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

    def before_save(self):
        calculate_doc_inspector_inches(self)

    def on_trash(self):
        revert_series_on_trash(self)


# ── Whitelisted API ───────────────────────────────────────────────────────────

@frappe.whitelist()
def get_serial_register_items(sales_order=None, batch_number=None, serial_number=None, branch=None):
    """
    Get Serial Number records from Serial Number DocType for Valve Assembly.
    """
    return _get_serial_register_items(
        doctype="Valve Assembly",
        sales_order=sales_order,
        batch_number=batch_number,
        serial_number=serial_number,
        branch=branch,
    )