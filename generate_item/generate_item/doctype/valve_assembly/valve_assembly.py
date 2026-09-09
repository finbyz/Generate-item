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
        user = frappe.session.user
        employee = frappe.db.get_value(
            "Employee",
            {"user_id": user},
            "name"
        )

        if not employee and user:
            employee = frappe.db.get_value(
                "Employee",
                {"company_email": user},
                "name"
            ) or frappe.db.get_value(
                "Employee",
                {"personal_email": user},
                "name"
            )

        if not employee and user:
            user_info = frappe.db.get_value("User", user, ["first_name", "full_name", "username"], as_dict=True)
            if user_info:
                names_to_try = [user_info.get("first_name"), user_info.get("full_name"), user_info.get("username")]
                names_to_try = [n for n in names_to_try if n]
                if names_to_try:
                    employee = frappe.db.get_value(
                        "Employee",
                        {"employee_name": ["in", names_to_try]},
                        "name"
                    ) or frappe.db.get_value(
                        "Employee",
                        {"first_name": ["in", names_to_try]},
                        "name"
                    )

        if employee:
            self.user = employee
        elif not self.user and user:
            self.user = user

        calculate_doc_inspector_inches(self)


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