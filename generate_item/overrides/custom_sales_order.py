import frappe
from erpnext.selling.doctype.sales_order.sales_order import SalesOrder

class CustomSalesOrder(SalesOrder):
    def on_trash(self):
        """Before deleting Sales Order, unlink it from any Batch and Sales Order Item"""
        try:
            # 1️⃣ Unlink all Batches referencing this Sales Order
            batches = frappe.get_all(
                "Batch",
                filters={
                    "reference_doctype": "Sales Order",
                    "reference_name": self.name
                },
                pluck="name"
            )

            for batch_name in batches:
                frappe.db.set_value("Batch", batch_name, "reference_doctype", None)
                frappe.db.set_value("Batch", batch_name, "reference_name", None)

            # 2️⃣ Also clear custom_batch_no from Sales Order Items (optional but safe)
            for item in self.items:
                if item.custom_batch_no:
                    frappe.db.set_value("Sales Order Item", item.name, "custom_batch_no", None)

            frappe.db.commit()

        except Exception as e:
            frappe.log_error(f"Error unlinking batches before deleting Sales Order {self.name}: {e}")

        # Continue normal delete process
        super().on_trash()
