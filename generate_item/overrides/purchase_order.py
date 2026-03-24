
import frappe
from frappe.utils import flt
from erpnext.buying.doctype.purchase_order.purchase_order import PurchaseOrder



class CustomPurchaseOrder(PurchaseOrder):

    def update_receiving_percentage(self):
        # Check if ANY item has stock_uom not same as uom
        
        has_mismatch = any(
            item.uom != item.stock_uom for item in self.items
        )

        if has_mismatch:
            # Custom logic: use stock UOM quantities (Nos)
            frappe.log_error("custom  update_receiving_percentage --- called")
            total_qty, received_qty = 0.0, 0.0
            for item in self.items:
                total_qty    += flt(item.stock_qty)
                received_qty += min(
                    flt(item.received_qty_in_stock_uom),
                    flt(item.stock_qty)
                )
        else:
            # Core logic: use purchase UOM quantities (Kg)
            frappe.log_error("custom but core logic  update_receiving_percentage --- called else")
            total_qty, received_qty = 0.0, 0.0
            for item in self.items:
                received_qty += min(item.received_qty, item.qty)
                total_qty    += item.qty

        if total_qty:
            self.db_set(
                "per_received",
                flt(received_qty / total_qty) * 100,
                update_modified=False
            )
        else:
            self.db_set("per_received", 0, update_modified=False)
