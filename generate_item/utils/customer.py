import frappe

def validate(self, method=None):
    if not self.gstin:
        return

    # Find any customer with same GSTIN except current
    existing = frappe.db.exists(
        "Customer",
        {
            "gstin": self.gstin,
            "name": ["!=", self.name]
        }
    )

    if existing:
        frappe.throw(
            f"GSTIN <b>{self.gstin}</b> already exists for customer <b>{existing}</b>. "
            "Duplicate GSTIN is not allowed."
        )



def supplier_validate(self, method=None):
    if not self.gstin:
        return

    # Find any Supplier with same GSTIN except current
    existing = frappe.db.exists(
        "Supplier",
        {
            "gstin": self.gstin,
            "name": ["!=", self.name]
        }
    )

    if existing:
        frappe.throw(
            f"GSTIN <b>{self.gstin}</b> already exists for supplier <b>{existing}</b>. "
            "Duplicate GSTIN is not allowed."
        )
