import frappe
import json
from erpnext.controllers.stock_controller import make_quality_inspections as original_make_qis
from frappe.utils import flt


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
			["qty", "received_qty", "conversion_factor", "custom_batch_no","stock_qty"],
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

        # 🔹 ADDED: map PO stock_qty → PR stock_uom_qty
		if po_item.stock_qty:
			item.qty_in_stock_uom = po_item.stock_qty

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


@frappe.whitelist()
def make_quality_inspections(doctype, docname, items):

	if isinstance(items, str):
		items = json.loads(items)

	inspection_names = original_make_qis(doctype, docname, items)

	qi_map = {
		frappe.get_value("Quality Inspection", qi, "child_row_reference"): qi
		for qi in inspection_names
	}

	for item in items:
		ref = item.get("child_row_reference")
		if not ref:
			continue

		qi_name = qi_map.get(ref)
		if not qi_name:
			continue

		qty = flt(item.get("qty"))

		frappe.db.set_value(
			"Quality Inspection",
			qi_name,
			{
				"received_qty": qty,
				"sample_size": qty
			}
		)

	return inspection_names


def update_received_qty_stock_uom(doc, method):
	for item in doc.items:
		if not item.purchase_order or not item.purchase_order_item:
			continue

			

		po_item = frappe.get_doc("Purchase Order Item", item.purchase_order_item)
		if item.received_stock_qty :
			po_item.db_set(
				"received_qty_in_stock_uom",
				item.received_stock_qty,
				update_modified=False
			)
   
		calculate_pending_qty(item)

		# if item.pending_qty_in_stock_uom :
			# po_item.db_set(
			# 	"pending_qty_in_stock_uom",
			# 	item.pending_qty_in_stock_uom,
			# 	update_modified=False
			# )


def calculate_pending_qty(item):
    if not item.purchase_order_item:
        return

    # Get Purchase Order Item stock_qty
    po_item = frappe.db.get_value(
        "Purchase Order Item",
        item.purchase_order_item,
        ["stock_qty"],
        as_dict=True
    )

    if not po_item:
        return

    po_stock_qty = flt(po_item.stock_qty)

    # Sum stock_qty from submitted Purchase Receipt Items
    received_qty = frappe.db.sql("""
        SELECT SUM(pri.stock_qty)
        FROM `tabPurchase Receipt Item` pri
        INNER JOIN `tabPurchase Receipt` pr
            ON pr.name = pri.parent
        WHERE
            pri.purchase_order_item = %s
            AND pr.docstatus = 1
    """, (item.purchase_order_item,))[0][0] or 0

    received_qty = flt(received_qty)

    # Calculate pending quantity
    pending_qty = po_stock_qty - received_qty
    if pending_qty < 0:
        pending_qty = 0

    # Update the Purchase Order Item field
    frappe.db.set_value(
        "Purchase Order Item",
        item.purchase_order_item,
        "pending_qty_in_stock_uom",
        pending_qty
    )

@frappe.whitelist()
def get_pending_qty(po_item_name):
    if not po_item_name:
        return 0

    return frappe.db.get_value(
        "Purchase Order Item",
        po_item_name,
        "pending_qty_in_stock_uom"
    )
