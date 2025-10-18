# your_custom_app/your_custom_app/overrides/work_order.py

import frappe
from frappe import _
from erpnext.manufacturing.doctype.work_order.work_order import WorkOrder

class WorkOrder(WorkOrder):
    def validate_sales_order(self):
        """
        Custom validation for Sales Order in Work Order
        Allows sub-assembly work orders to pass validation
        """
        if self.sales_order:
            # Basic check - SO exists and is submitted
            if not frappe.db.exists("Sales Order", {"name": self.sales_order, "docstatus": 1}):
                frappe.throw(_("Sales Order {0} is not valid").format(self.sales_order))
            
            # For sub-assembly work orders, skip production item validation
            if self.sales_order_item:
                # Validate specific SO item exists
                if not frappe.db.exists("Sales Order Item", {
                    "name": self.sales_order_item, 
                    "parent": self.sales_order
                }):
                    frappe.throw(_("Sales Order Item {0} is not valid for Sales Order {1}").format(
                        self.sales_order_item, self.sales_order))
            else:
                # Skip production item validation for sub-assemblies
                # Check if this is a sub-assembly by item group or other indicator
                item_group = frappe.db.get_value("Item", self.production_item, "item_group") if self.production_item else None
                
                # Define which item groups are considered sub-assemblies
                sub_assembly_groups = ["Sub Assembly", "Components", "Raw Material"]
                
                if item_group in sub_assembly_groups:
                    # Allow sub-assembly work orders without matching SO item
                    frappe.msgprint(
                        _("Sub-assembly Work Order created for Sales Order {0}").format(self.sales_order),
                        alert=True,
                        indicator="blue"
                    )
                    return  # Skip the original validation
                
                # Original validation logic for finished goods
                so_items = frappe.get_all("Sales Order Item",
                    filters={"parent": self.sales_order, "item_code": self.production_item},
                    fields=["name"]
                )
                if not so_items:
                    frappe.throw(_("Item {0} not found in Sales Order {1}").format(
                        self.production_item, self.sales_order))