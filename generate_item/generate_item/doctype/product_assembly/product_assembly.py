# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ProductAssembly(Document):

    def before_save(self):
        employee = frappe.db.get_value(
            "Employee",
            {"user_id": frappe.session.user},
            "name"
        )

        if employee:
            self.user = employee

@frappe.whitelist()
def get_serial_register_items(sales_order=None, batch_number=None):
    """
    Get Serial Number records from Serial Number custom DocType.

    Logic:
    - Batch selected:
        Get serial numbers for that batch.
    - Sales Order selected without batch:
        Get all batches for the Sales Order,
        then get serial numbers for those batches.
    - Neither selected:
        Return all serial numbers.

    Serial numbers already used in a *submitted* Product Assembly are excluded,
    so the same serial can't be added twice.
    """

    filters = {}
    batch_info_map = {}

    # Case 1: Batch is selected
    if batch_number:
        filters["batch"] = batch_number

    # Case 2: Sales Order selected but Batch is not selected
    elif sales_order:
        batches = frappe.get_all(
            "Batch",
            filters={"reference_name": sales_order},
            fields=["name", "item", "reference_name"],
        )

        if not batches:
            return []

        batch_info_map = {
            b.name: {"item": b.item, "sales_order": b.reference_name}
            for b in batches
        }
        filters["batch"] = ["in", list(batch_info_map.keys())]

    # Exclude serial numbers already used in a submitted Product Assembly
    used_serials = frappe.get_all(
        "Assembly Item Serial No",
        filters={
            "docstatus": 1,
            "parenttype": "Product Assembly",
        },
        pluck="serial_number",
    )

    if used_serials:
        filters["name"] = ["not in", list(set(used_serials))]

    # Get Serial Number records
    serial_numbers = frappe.get_all(
        "Serial Number",
        filters=filters,
        fields=[
            "batch",
            "name as serial_number",
        ],
        order_by="creation asc",
    )

    # Attach item_code and sales_order from Batch
    if not batch_info_map:
        involved_batches = list({s.batch for s in serial_numbers if s.batch})
        if involved_batches:
            batch_info_map = {
                b.name: {"item": b.item, "reference_name": b.reference_name}
                for b in frappe.get_all(
                    "Batch",
                    filters={"name": ["in", involved_batches]},
                    fields=["name", "item", "reference_name"],
                )
            }

    for s in serial_numbers:
        info = batch_info_map.get(s.batch, {})
        s["item_code"] = info.get("item")
        s["sales_order"] = info.get("sales_order") if "sales_order" in info else info.get("reference_name")

    return serial_numbers