import frappe
@frappe.whitelist()
def make_purchase_receipt(source_name, target_doc=None, args=None):
	"""Create Purchase Receipt from Purchase Order while mapping custom_batch_no → batch_no.

	This wraps the core method and then copies `custom_batch_no` from the source
	Purchase Order Item into the `batch_no` field on the target Purchase Receipt Item.
	"""
	from erpnext.buying.doctype.purchase_order.purchase_order import (
		make_purchase_receipt as core_make_purchase_receipt,
	)

	# Create the Purchase Receipt using core logic first
	# Pass through args to maintain compatibility with mapper flows
	pr = core_make_purchase_receipt(source_name=source_name, target_doc=target_doc, args=args)

	# Map custom_batch_no from PO Item to PR Item.batch_no
	for item in pr.items or []:
		po_item_name = getattr(item, "purchase_order_item", None)
		if not po_item_name:
			continue
		custom_batch_no = frappe.db.get_value(
			"Purchase Order Item", po_item_name, "custom_batch_no"
		)
		if custom_batch_no and not getattr(item, "batch_no", None):
			item.batch_no = custom_batch_no

	return pr

def before_save(doc, method):
	for i in doc.items:
		if not i.po_qty:
			po_qty = frappe.get_doc("Purchase Order", i.purchase_order)
			for item in po_qty.items:
				if item.item_code == i.item_code:
					i.po_qty = item.qty
					i.po_line_no = item.idx
					break

@frappe.whitelist()
def get_po_items(purchase_order):
	po_doc = frappe.get_doc("Purchase Order", purchase_order)
	return po_doc