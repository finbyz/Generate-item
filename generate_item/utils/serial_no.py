import frappe
from frappe.utils import add_months, nowdate

def update_warranty_period(doc, method):
    # Serial No shares its `name` with the custom "Serial Number" doctype
    batch_no = frappe.db.get_value("Serial Number", doc.name, "custom_batch_no")
    if not batch_no:
        return

    warranty_period = frappe.db.get_value(
        "Sales Order Item",
        {"batch_no": batch_no},
        "warranty_period"
    )

    if warranty_period:
        doc.warranty_period = warranty_period
        
        
def update_warranty_expiry_date(doc, method):
    if doc.status != "Delivered":
        return

    if not doc.warranty_period:
        return

    base_date = doc.delivery_date or nowdate()