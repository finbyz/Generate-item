# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from generate_item.utils.inspector_inches import (
    calculate_doc_inspector_inches,
    get_serial_register_items as _get_serial_register_items,
)


class ProductTesting(Document):

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
def get_serial_register_items(sales_order=None, batch_number=None):
    """
    Get Serial Number records from Serial Number DocType for Product Testing.
    """
    return _get_serial_register_items(
        doctype="Product Testing",
        sales_order=sales_order,
        batch_number=batch_number,
    )

