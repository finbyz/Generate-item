import frappe
from erpnext.selling.doctype.sales_order.sales_order import SalesOrder

# Sales Order status -> desired item-level line_status
STATUS_TO_LINE_STATUS = {
    "On Hold": "Hold",
    "Closed": "Closed",
}

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

            # frappe.db.commit()

        except Exception as e:
            frappe.log_error(f"Error unlinking batches before deleting Sales Order {self.name}: {e}")

        # Continue normal delete process
        super().on_trash()

    
    def on_cancel(self):
        # Run core cancel logic first (it also blocks cancelling a Closed
        # order, so if it throws, we never reach our code below).
        super().on_cancel()
        self._sync_item_line_status("Cancelled")

    def update_status(self, status):
        # Runs core logic for Hold / Resume / Close / Reopen.
        super().update_status(status)
        # self.status now reflects the real, final status after the call.
        new_line_status = STATUS_TO_LINE_STATUS.get(self.status, "")
        self._sync_item_line_status(new_line_status)

    def _sync_item_line_status(self, line_status):
        if not self.get("items"):
            return
        for item in self.items:
            # db_set works on child-table rows too (they're real Documents)
            # and writes straight to DB without re-running full save/validate.
            item.db_set("line_status", line_status, update_modified=False)


