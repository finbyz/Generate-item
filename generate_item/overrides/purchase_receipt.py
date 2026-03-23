from erpnext.stock.doctype.purchase_receipt.purchase_receipt import PurchaseReceipt
import frappe
from frappe import _, throw
from frappe.utils import cint, flt, get_datetime, getdate, nowdate
from erpnext.stock.get_item_details import get_conversion_factor
from frappe.utils import flt
from erpnext.controllers.buying_controller import BuyingController

# class PurchaseReceipt(_PurchaseReceipt):

# 	def validate(self):
# 		"""Allow UOM different from Purchase Order by auto-setting conversion_factor/stock_qty."""
# 		super().validate()
# 		for row in self.items or []:
# 			try:
# 				# Get conversion factor for selected UOM against the item's stock UOM
# 				if row.uom and row.item_code:
# 					cf_resp = get_conversion_factor(item_code=row.item_code, uom=row.uom)
# 					cf = flt(cf_resp.get("conversion_factor")) if isinstance(cf_resp, dict) else flt(cf_resp)
# 					if cf:
# 						row.conversion_factor = cf
# 						# Ensure stock_qty stays in sync
# 						row.stock_qty = flt(row.qty) * cf
# 			except Exception:
# 				# Do not block save/submit just because conversion lookup failed
# 				pass

# 	def validate_with_previous_doc(self):
# 		"""Run core previous doc validation but neutralize UOM equality by temporarily aligning UOMs."""
# 		# Save original UOMs and replace with PO Item UOMs (if any) to bypass strict UOM compare
# 		original_uoms = {}
# 		try:
# 			for row in self.items or []:
# 				original_uoms[row.name] = row.uom
# 				if getattr(row, "purchase_order_item", None):
# 					po_uom = frappe.db.get_value("Purchase Order Item", row.purchase_order_item, "uom")
# 					if po_uom:
# 						row.uom = po_uom
# 			# Call core validation which will now pass UOM equality
# 			super().validate_with_previous_doc()
# 		finally:
# 			# Restore original UOMs
# 			for row in self.items or []:
# 				if row.name in original_uoms:
# 					row.uom = original_uoms[row.name]

# 	def validate_rate_with_reference_doc(self, args=None):
# 		"""Override to skip strict rate equality with reference documents.

# 		This avoids errors like 'Rate must be same as Purchase Order' when UOM differs
# 		or negotiated rates change. All other validations remain intact.
# 		"""
# 		return

# 		if (
# 			cint(frappe.db.get_single_value("Buying Settings", "maintain_same_rate"))
# 			and not self.is_return
# 			and not self.is_internal_supplier
# 		):
# 			self.validate_rate_with_reference_doc(
# 				[["Purchase Order", "purchase_order", "purchase_order_item"]]
# 			)


class CustomBuyingController(BuyingController):

    def set_qty_as_per_stock_uom(self):
        # frappe.log_error("custom called-- set_qty_as_per_stock_uom")
        if self.doctype == "Purchase Receipt":
            return
        allow_to_edit_stock_qty = frappe.db.get_single_value(
            "Stock Settings", "allow_to_edit_stock_uom_qty_for_purchase"
        )

        for d in self.get("items"):
            if d.meta.get_field("stock_qty"):
                # Check if item code is present
                # Conversion factor should not be mandatory for non itemized items
                if not d.conversion_factor and d.item_code:
                    frappe.throw(
                        _("Row {0}: Conversion Factor is mandatory").format(d.idx)
                    )
                d.stock_qty = flt(d.qty) * flt(d.conversion_factor)

                if self.doctype == "Purchase Receipt" and d.meta.get_field(
                    "received_stock_qty"
                ):
                    # Set Received Qty in Stock UOM
                    d.received_stock_qty = flt(d.received_qty) * flt(
                        d.conversion_factor, d.precision("conversion_factor")
                    )

                if allow_to_edit_stock_qty:
                    d.stock_qty = flt(d.stock_qty, d.precision("stock_qty"))
                    if d.get("received_stock_qty") and d.meta.get_field(
                        "received_stock_qty"
                    ):
                        d.received_stock_qty = flt(
                            d.received_stock_qty, d.precision("received_stock_qty")
                        )


class CustomPurchaseReceipt(CustomBuyingController, PurchaseReceipt):
    def validate(self):
        # frappe.log_error("custom called-- CustomPurchaseReceipt validate")
        # frappe.throw(_("Custom validation logic executed"), alert=True)  # Debug message
        self.validate_posting_time()
        super(PurchaseReceipt, self).validate()

        if self._action != "submit":
            self.set_status()

        self.po_required()
        self.validate_items_quality_inspection()
        self.validate_with_previous_doc()
        # self.validate_uom_is_integer()
        self.validate_cwip_accounts()
        self.validate_provisional_expense_account()

        self.check_on_hold_or_closed_status()

        if getdate(self.posting_date) > getdate(nowdate()):
            throw(_("Posting Date cannot be future date"))

        self.get_current_stock()
        self.reset_default_field_value("set_warehouse", "items", "warehouse")
        self.reset_default_field_value(
            "rejected_warehouse", "items", "rejected_warehouse"
        )
        self.reset_default_field_value("set_from_warehouse", "items", "from_warehouse")
        if self.is_new():
            update_stock_uom_qty(self)
        # update_accepted_qty(self)

    # def on_submit(self):
    #     super().on_submit()

    #     # Check for Approving Authority
    #     frappe.get_doc("Authorization Control").validate_approving_authority(
    #         self.doctype, self.company, self.base_grand_total
    #     )

    #     self.update_prevdoc_status()
    #     if flt(self.per_billed) < 100:
    #         self.update_billing_status()
    #     else:
    #         self.db_set("status", "Completed")

    #     self.make_bundle_for_sales_purchase_return()
    #     self.make_bundle_using_old_serial_batch_fields()
    #     # Updating stock ledger should always be called after updating prevdoc status,
    #     # because updating ordered qty, reserved_qty_for_subcontract in bin
    #     # depends upon updated ordered qty in PO
    #     self.update_stock_ledger()
    #     self.make_gl_entries()
    #     self.repost_future_sle_and_gle()
    #     self.set_consumed_qty_in_subcontract_order()
    #     self.reserve_stock_for_sales_order()
    #     self.validate_uom_is_integer()


def update_stock_uom_qty(self):

    for item in self.items:

        if not item.purchase_order_item:
            continue

        if item.stock_qty:
            continue

        # 1️⃣ Get total received stock_qty from Purchase Receipt Item
        total_received = frappe.db.sql(
            """
            SELECT SUM(stock_qty)
            FROM `tabPurchase Receipt Item`
            WHERE purchase_order_item = %s
              AND docstatus < 2
              AND parent != %s
        """,
            (item.purchase_order_item, self.name),
        )

        total_received = (
            flt(total_received[0][0]) if total_received and total_received[0][0] else 0
        )

        # 2️⃣ Get stock_qty from Purchase Order Item
        po_stock_qty = (
            frappe.db.get_value(
                "Purchase Order Item", item.purchase_order_item, "stock_qty"
            )
            or 0
        )

        po_stock_qty = flt(po_stock_qty)

        # 3️⃣ Calculate remaining qty
        remaining_qty = po_stock_qty - total_received

        # 4️⃣ Update current row stock_qty
        item.db_set("stock_qty", remaining_qty)


# def update_accepted_qty(self):
#     for item in self.items:
#         item.stock_qty = item.received_stock_qty - item.rejected_stock_qty
