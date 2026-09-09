# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, nowdate
from frappe.model.document import Document
from generate_item.utils.inspector_inches import (
    calculate_doc_inspector_inches,
    get_serial_register_items as _get_serial_register_items,
)


class ValveAssembly(Document):

    def validate(self):
        self.validate_back_dated_entries()

    def validate_back_dated_entries(self):
        today_date = getdate(nowdate())
        if self.posting_date and getdate(self.posting_date) < today_date:
            frappe.throw(frappe._("Posting Date cannot be a back date."))

        for row in getattr(self, "item_serial_number", []):
            if getattr(row, "date", None) and getdate(row.date) < today_date:
                frappe.throw(
                    frappe._("Row #{0}: Date cannot be a back date.").format(row.idx)
                )

    def before_save(self):
        employee = frappe.db.get_value(
            "Employee",
            {"user_id": frappe.session.user},
            "name"
        )

        if employee:
            self.user = employee

        calculate_doc_inspector_inches(self)


@frappe.whitelist()
def get_serial_register_items(sales_order=None, batch_number=None, branch=None):
    """
    Get Serial Number records from Serial Number DocType for Valve Assembly.
    """
    return _get_serial_register_items(
        doctype="Valve Assembly",
        sales_order=sales_order,
        batch_number=batch_number,
        branch=branch,
    )