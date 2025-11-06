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

	# Adjust quantities to consider Draft PRs as consumed, and map custom_batch_no
	items_to_keep = []
	for item in pr.items or []:
		po_item_name = getattr(item, "purchase_order_item", None)
		if not po_item_name:
			items_to_keep.append(item)
			continue

		# Fetch source PO Item values needed for accurate remaining computation
		po_item = frappe.db.get_value(
			"Purchase Order Item",
			po_item_name,
			["qty", "received_qty", "conversion_factor", "custom_batch_no"],
			as_dict=True,
		)

		# Default to current mapped qty if lookup fails for any reason
		if not po_item:
			items_to_keep.append(item)
			continue

		po_qty = frappe.utils.flt(po_item.qty)
		received_qty = frappe.utils.flt(po_item.received_qty)
		po_cf = frappe.utils.flt(po_item.conversion_factor) or 1.0

		# Base remaining in stock units from Submitted PRs
		base_remaining_stock_qty = max((po_qty - received_qty), 0) * po_cf

		# Add quantities already present in Draft PRs for the same PO Item (in stock units)
		draft_pr_stock_qty = frappe.db.sql(
			"""
			SELECT COALESCE(SUM(pri.stock_qty), 0)
			FROM `tabPurchase Receipt Item` pri
			INNER JOIN `tabPurchase Receipt` pr ON pri.parent = pr.name
			WHERE pr.docstatus = 0
			  AND pri.purchase_order_item = %s
			""",
			(po_item_name,),
		)[0][0]

		remaining_stock_qty = max(base_remaining_stock_qty - frappe.utils.flt(draft_pr_stock_qty), 0)

		# Use target item's conversion factor to set displayed qty
		item_cf = frappe.utils.flt(getattr(item, "conversion_factor", None)) or 1.0
		new_qty = remaining_stock_qty / item_cf if item_cf else 0
		item.qty = new_qty
		item.stock_qty = remaining_stock_qty

		# Map custom_batch_no from PO Item to PR Item.batch_no if empty
		if po_item.custom_batch_no and not getattr(item, "batch_no", None):
			item.batch_no = po_item.custom_batch_no

		# Keep only rows with positive qty
		if new_qty and new_qty > 0:
			items_to_keep.append(item)

	# Replace items with filtered list to avoid zero-qty rows
	if pr.items is not None:
		pr.items = items_to_keep

	return pr


def before_save(doc, method):
    for item in doc.items:
        if not item.po_qty:
            # Fetch PO qty and line number
            po_doc = frappe.get_doc("Purchase Order", item.purchase_order)
            for po_item in po_doc.items:
                if po_item.item_code == item.item_code and item.purchase_order_item == po_item.name :
                    item.po_qty = po_item.qty
                    item.po_line_no = po_item.idx
                    break

        # Get branch from item row
        branch = item.branch

        # Fetch warehouses linked to this branch and marked as raw_material_warehouse and stock_warehouse
        warehouses = frappe.get_all(
            "Warehouse",
            filters={
                "branch": branch,
                "raw_material_warehouse": 1,
                "store_warehouse": 1
            },
            pluck="name"
        )

        if warehouses:
            # Sum projected_qty from Bin for the item in these warehouses
            total_projected_qty = frappe.get_all(
                "Bin",
                filters={
                    "item_code": item.item_code,
                    "warehouse": ["in", warehouses]
                },
                fields=["sum(projected_qty) as total"]
            )
            item.on_hand_qty = total_projected_qty[0].total or 0
        else:
            item.on_hand_qty = 0


@frappe.whitelist()
def get_po_items(purchase_order):
	po_doc = frappe.get_doc("Purchase Order", purchase_order)
	return po_doc


def validate(doc, method):
    validate_duplicate_po(doc, method)
   

def validate_duplicate_po(doc, method):
    """Prevent duplicate draft Purchase Orders for same supplier, item, and qty."""

    for item in doc.items:
        if not item.custom_batch_no:
            continue

        # Look for another DRAFT Delivery Note with same details
        duplicate = frappe.db.sql(
            """
            SELECT dni.parent
            FROM `tabPurchase Receipt Item` dni
            INNER JOIN `tabPurchase Receipt` dn ON dn.name = dni.parent
            WHERE dni.custom_batch_no = %s
              AND dni.item_code = %s
              AND dni.qty = %s
              AND dn.supplier = %s
              AND dn.docstatus = 0
              AND dni.parent != %s
            LIMIT 1
            """,
            (item.custom_batch_no, item.item_code, item.qty, doc.supplier, doc.name),
        )

        if duplicate:
            dn_name = duplicate[0][0]
            frappe.throw(
                (
                    f"Duplicate Draft Purchase Receipt found for Batch: <b>{item.custom_batch_no}</b>, "
                    f"Item: <b>{item.item_code}</b>, Qty: <b>{item.qty}</b>, "
                    f"Supplier: <b>{doc.supplier}</b>.<br><br>"
                    f"Existing Draft Purchase Receipt: <b><a href='/app/purchase-receipt/{dn_name}'>{dn_name}</a></b>"
                ),
                title=("Duplicate Draft Purchase Receipt Detected")
            )
