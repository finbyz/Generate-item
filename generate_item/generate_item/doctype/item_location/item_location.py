# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ItemLocation(Document):

    def validate(self):
        self.unique_link = (
            (self.branch or "") +
            (self.item or "") +
            (self.warehouse_1 or "") +
            (self.warehouse_2 or "")
        )
