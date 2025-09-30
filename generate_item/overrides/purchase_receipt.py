from erpnext.stock.doctype.purchase_receipt.purchase_receipt import PurchaseReceipt as _PurchaseReceipt
import frappe
from frappe.utils import cint, flt
from erpnext.stock.get_item_details import get_conversion_factor

class PurchaseReceipt(_PurchaseReceipt):

	# def validate(self):
	# 	"""Allow UOM different from Purchase Order by auto-setting conversion_factor/stock_qty."""
	# 	super().validate()
	# 	for row in self.items or []:
	# 		try:
	# 			# Get conversion factor for selected UOM against the item's stock UOM
	# 			if row.uom and row.item_code:
	# 				cf_resp = get_conversion_factor(item_code=row.item_code, uom=row.uom)
	# 				cf = flt(cf_resp.get("conversion_factor")) if isinstance(cf_resp, dict) else flt(cf_resp)
	# 				if cf:
	# 					row.conversion_factor = cf
	# 					# Ensure stock_qty stays in sync
	# 					row.stock_qty = flt(row.qty) * cf
	# 		except Exception:
	# 			# Do not block save/submit just because conversion lookup failed
	# 			pass

	# def validate_with_previous_doc(self):
	# 	"""Run core previous doc validation but neutralize UOM equality by temporarily aligning UOMs."""
	# 	# Save original UOMs and replace with PO Item UOMs (if any) to bypass strict UOM compare
	# 	original_uoms = {}
	# 	try:
	# 		for row in self.items or []:
	# 			original_uoms[row.name] = row.uom
	# 			if getattr(row, "purchase_order_item", None):
	# 				po_uom = frappe.db.get_value("Purchase Order Item", row.purchase_order_item, "uom")
	# 				if po_uom:
	# 					row.uom = po_uom
	# 		# Call core validation which will now pass UOM equality
	# 		super().validate_with_previous_doc()
	# 	finally:
	# 		# Restore original UOMs
	# 		for row in self.items or []:
	# 			if row.name in original_uoms:
	# 				row.uom = original_uoms[row.name]
stock_qty
	def validate_rate_with_reference_doc(self, args=None):
		"""Override to skip strict rate equality with reference documents.

		This avoids errors like 'Rate must be same as Purchase Order' when UOM differs
		or negotiated rates change. All other validations remain intact.
		"""
		return

		if (
			cint(frappe.db.get_single_value("Buying Settings", "maintain_same_rate"))
			and not self.is_return
			and not self.is_internal_supplier
		):
			self.validate_rate_with_reference_doc(
				[["Purchase Order", "purchase_order", "purchase_order_item"]]
			)
