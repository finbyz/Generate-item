import frappe


@frappe.whitelist()
def make_sales_invoice(source_name, target_doc=None, args=None):
	"""Create Sales Invoice from Delivery Note while excluding Draft SIs from remaining qty.

	Wraps core method and adjusts each mapped item's qty to subtract any quantities
	already present in Draft Sales Invoices for the same Delivery Note Item (`dn_detail`).
	"""
	from erpnext.stock.doctype.delivery_note.delivery_note import (
		make_sales_invoice as core_make_sales_invoice,
	)

	# Create Sales Invoice using core logic first (which considers submitted SIs and returns)
	si = core_make_sales_invoice(source_name=source_name, target_doc=target_doc, args=args)

	# Recompute remaining per DN Item: DN.qty - SUM(SI.qty where dn_detail matches AND docstatus IN (0,1))
	items_to_keep = []
	for item in si.items or []:
		dn_detail = getattr(item, "dn_detail", None)
		if not dn_detail:
			items_to_keep.append(item)
			continue

		# Source DN item qty
		dn_item_qty = frappe.db.get_value("Delivery Note Item", dn_detail, "qty")
		if dn_item_qty is None:
			items_to_keep.append(item)
			continue

		# Total already invoiced in Draft or Submitted (exclude Cancelled)
		total_invoiced_qty = frappe.db.sql(
			"""
			SELECT COALESCE(SUM(sii.qty), 0)
			FROM `tabSales Invoice Item` sii
			INNER JOIN `tabSales Invoice` si ON sii.parent = si.name
			WHERE sii.dn_detail = %s
			  AND si.docstatus IN (0,1)
			""",
			(dn_detail,),
		)[0][0]

		remaining_qty = max(frappe.utils.flt(dn_item_qty) - frappe.utils.flt(total_invoiced_qty), 0)
		item.qty = remaining_qty

		if remaining_qty and remaining_qty > 0:
			items_to_keep.append(item)

	# Replace items to drop zero-qty rows
	if si.items is not None:
		si.items = items_to_keep

	return si


