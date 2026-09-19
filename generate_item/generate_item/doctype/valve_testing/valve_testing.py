# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, nowdate
from frappe.model.document import Document
from generate_item.utils.inspector_inches import (
    calculate_doc_inspector_inches,
    get_serial_register_items as _get_serial_register_items,
    validate_serial_for_testing_phase,
    get_valve_testing_serial_query,
)


class ValveTesting(Document):

    def validate(self):
        self.validate_back_dated_entries()
        self.validate_testing_phase()
        self.validate_serial_numbers()

    def validate_testing_phase(self):
        if not self.testing_phase:
            frappe.throw(frappe._("Testing Phase is mandatory."))

    def validate_back_dated_entries(self):
        today_date = getdate(nowdate())
        if self.posting_date and getdate(self.posting_date) < today_date:
            frappe.throw(frappe._("Posting Date cannot be a back date."))

        for row in getattr(self, "item_serial_number", []):
            if getattr(row, "date", None) and getdate(row.date) < today_date:
                frappe.throw(
                    frappe._("Row #{0}: Date cannot be a back date.").format(row.idx)
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
        # if not self.user and frappe.session.user:
        #     self.user = frappe.session.user
        calculate_doc_inspector_inches(self)


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


