import frappe
import frappe
from frappe import _

@frappe.whitelist()
def set_remaining_actual_taxes(invoice_name):
    """
    Whitelisted method to calculate and set remaining actual taxes
    FOR SAVED DOCUMENTS ONLY
    """
    if not frappe.db.exists("Sales Invoice", invoice_name):
        frappe.throw(_("Sales Invoice {0} not found").format(invoice_name))
    
    doc = frappe.get_doc("Sales Invoice", invoice_name)
    
    if doc.docstatus == 2:  # Cancelled
        frappe.throw(_("Cannot update taxes for a cancelled invoice"))
    
    _calculate_and_set_remaining_taxes(doc)
    
    # Save and reload
    doc.save()
    frappe.db.commit()
    
    return {
        "success": True,
        "message": _("Actual taxes updated successfully")
    }


@frappe.whitelist()
def get_remaining_taxes_for_draft(sales_orders, current_invoice_name=None):
    """
    Calculate remaining taxes for DRAFT/UNSAVED documents
    Returns a dictionary of account_head: remaining_amount
    """
    if isinstance(sales_orders, str):
        import json
        sales_orders = json.loads(sales_orders)
    
    remaining_taxes = {}
    
    for so_name in sales_orders:
        # Get Sales Order taxes with charge_type = "Actual"
        so_doc = frappe.get_doc("Sales Order", so_name)
        so_actual_taxes = {}
        
        for tax in so_doc.taxes:
            if tax.charge_type == "Actual":
                key = tax.account_head
                if key not in so_actual_taxes:
                    so_actual_taxes[key] = 0
                so_actual_taxes[key] += tax.tax_amount or 0
        
        if not so_actual_taxes:
            continue
        
        # Get all existing Sales Invoices for this Sales Order (excluding cancelled and current)
        filters = {
            "sales_order": so_name,
            "docstatus": ["!=", 2]  # Exclude cancelled
        }
        
        # Exclude current invoice if it exists (saved documents)
        if current_invoice_name and frappe.db.exists("Sales Invoice", current_invoice_name):
            filters["parent"] = ["!=", current_invoice_name]
        
        existing_invoices = frappe.get_all(
            "Sales Invoice Item",
            filters=filters,
            fields=["parent"],
            distinct=True
        )
        
        # Calculate total billed actual taxes from existing invoices
        billed_taxes = {}
        for inv in existing_invoices:
            si_doc = frappe.get_doc("Sales Invoice", inv.parent)
            for tax in si_doc.taxes:
                if tax.charge_type == "Actual":
                    key = tax.account_head
                    if key not in billed_taxes:
                        billed_taxes[key] = 0
                    billed_taxes[key] += tax.tax_amount or 0
        
        # Calculate remaining for each account
        for account_head, total_amount in so_actual_taxes.items():
            billed_amount = billed_taxes.get(account_head, 0)
            remaining = max(total_amount - billed_amount, 0)
            
            # If multiple SOs, take the minimum remaining
            if account_head in remaining_taxes:
                remaining_taxes[account_head] = min(remaining_taxes[account_head], remaining)
            else:
                remaining_taxes[account_head] = remaining
    
    return remaining_taxes


# def before_save(doc, method):
#     items_to_remove = set()
#     component_info = {}

#     for row in doc.items:
#         if row.component_of:
#             items_to_remove.add(row.component_of)

#     for row in doc.items:
#         if row.item_code in items_to_remove:
#             info = f"{row.item_code} - {row.description or ''}"
#             component_info[row.item_code] = info.strip()

#     for row in doc.items:
#         if row.component_of:
#             info = component_info.get(row.component_of)
#             if info:
#                 if row.remarks:
#                     row.remarks += f"\n{info}"
#                 else:
#                     row.remarks = info

#     rows_to_keep = []
#     for row in doc.items:
#         if row.item_code in items_to_remove:
#             continue
#         rows_to_keep.append(row)

#     doc.items = rows_to_keep

#     for i, row in enumerate(doc.items, start=1):
#         row.idx = i


def after_insert(doc, method=None):
    """
    Called automatically after Sales Invoice is inserted
    """
    _calculate_and_set_remaining_taxes(doc)


def _calculate_and_set_remaining_taxes(doc):
    """
    Internal function to calculate and set remaining actual taxes from Sales Order
    after deducting taxes from existing Sales Invoices
    """
    # Get all unique sales orders from items
    sales_orders = list(set([item.sales_order for item in doc.items if item.sales_order]))
    
    if not sales_orders:
        return
    
    # Track if any changes were made
    taxes_updated = False
    
    # Process each sales order
    for so_name in sales_orders:
        # Get Sales Order taxes with charge_type = "Actual"
        so_doc = frappe.get_doc("Sales Order", so_name)
        so_actual_taxes = {}
        
        for tax in so_doc.taxes:
            if tax.charge_type == "Actual":
                key = tax.account_head
                if key not in so_actual_taxes:
                    so_actual_taxes[key] = {
                        'total_amount': 0,
                        'account_head': tax.account_head,
                        'description': tax.description,
                        'cost_center': tax.cost_center,
                        'branch': tax.branch,
                        'po_line_no': tax.get('po_line_no'),
                        'idx': tax.idx
                    }
                so_actual_taxes[key]['total_amount'] += tax.tax_amount or 0
        
        if not so_actual_taxes:
            continue
        
        # Get all existing Sales Invoices for this Sales Order (excluding current and cancelled)
        existing_invoices = frappe.get_all(
            "Sales Invoice Item",
            filters={
                "sales_order": so_name,
                "docstatus": ["!=", 2],  # Exclude cancelled
                "parent": ["!=", doc.name]  # Exclude current invoice
            },
            fields=["parent"],
            distinct=True
        )
        
        # Calculate total billed actual taxes from existing invoices
        billed_taxes = {}
        for inv in existing_invoices:
            si_doc = frappe.get_doc("Sales Invoice", inv.parent)
            for tax in si_doc.taxes:
                if tax.charge_type == "Actual":
                    key = tax.account_head
                    if key not in billed_taxes:
                        billed_taxes[key] = 0
                    billed_taxes[key] += tax.tax_amount or 0
        
        # Calculate remaining taxes and update current invoice
        for account_head, so_tax_data in so_actual_taxes.items():
            billed_amount = billed_taxes.get(account_head, 0)
            remaining_amount = so_tax_data['total_amount'] - billed_amount
            
            # Ensure remaining amount is not negative
            remaining_amount = max(remaining_amount, 0)
            
            # Find matching tax row in current invoice and update
            for tax in doc.taxes:
                if tax.charge_type == "Actual" and tax.account_head == account_head:
                    old_amount = tax.tax_amount or 0
                    
                    if old_amount != remaining_amount:
                        # Update to remaining amount
                        tax.tax_amount = remaining_amount
                        tax.base_tax_amount = remaining_amount
                        tax.tax_amount_after_discount_amount = remaining_amount
                        tax.base_tax_amount_after_discount_amount = remaining_amount
                        
                        taxes_updated = True
                        
                        if remaining_amount > 0:
                            frappe.msgprint(
                                _("Tax '{0}' updated to remaining amount: {1}<br>"
                                  "<small>Sales Order Total: {2} | Already Billed: {3}</small>").format(
                                    account_head,
                                    frappe.format_value(remaining_amount, {'fieldtype': 'Currency'}),
                                    frappe.format_value(so_tax_data['total_amount'], {'fieldtype': 'Currency'}),
                                    frappe.format_value(billed_amount, {'fieldtype': 'Currency'})
                                ),
                                alert=True,
                                indicator='blue'
                            )
                        else:
                            frappe.msgprint(
                                _("Tax '{0}' set to 0 (Full amount already billed from Sales Order {1})").format(
                                    account_head, so_name
                                ),
                                alert=True,
                                indicator='orange'
                            )
                    break
        
        # Recalculate totals if taxes were updated
        if taxes_updated:
            doc.calculate_taxes_and_totals()
            
            # Update database if document is already saved
            if doc.name and not doc.get("__islocal"):
                doc.db_update()
            
            frappe.msgprint(
                _("Actual taxes adjusted based on Sales Order {0}").format(so_name),
                alert=True,
                indicator='green'
            )


def validate(doc, method=None):
    """
    Optional: Validate before save to show warning if taxes exceed Sales Order
    This prevents over-billing
    """
    remove_free_items(doc)
    fetch_po_line_no_from_sales_order(doc)
    validate_duplicate_si(doc, method)
    sales_orders = list(set([item.sales_order for item in doc.items if item.sales_order]))
    
    for so_name in sales_orders:
        so_doc = frappe.get_doc("Sales Order", so_name)
        so_actual_taxes = {}
        
        for tax in so_doc.taxes:
            if tax.charge_type == "Actual":
                key = tax.account_head
                if key not in so_actual_taxes:
                    so_actual_taxes[key] = 0
                so_actual_taxes[key] += tax.tax_amount or 0
        
        if not so_actual_taxes:
            continue
        
        # Get existing invoices total
        existing_invoices = frappe.get_all(
            "Sales Invoice Item",
            filters={
                "sales_order": so_name,
                "docstatus": ["!=", 2],
                "parent": ["!=", doc.name]
            },
            fields=["parent"],
            distinct=True
        )
        
        billed_taxes = {}
        for inv in existing_invoices:
            si_doc = frappe.get_doc("Sales Invoice", inv.parent)
            for tax in si_doc.taxes:
                if tax.charge_type == "Actual":
                    key = tax.account_head
                    if key not in billed_taxes:
                        billed_taxes[key] = 0
                    billed_taxes[key] += tax.tax_amount or 0
        
        # Check current invoice taxes
        for tax in doc.taxes:
            if tax.charge_type == "Actual":
                account_head = tax.account_head
                so_total = so_actual_taxes.get(account_head, 0)
                billed = billed_taxes.get(account_head, 0)
                current = tax.tax_amount or 0
                
                if (billed + current) > so_total:
                    frappe.throw(
                        _("Row #{0}: Tax '{1}' amount {2} exceeds remaining amount.<br><br>"
                          "<b>Sales Order {3}:</b><br>"
                          "• Total: {4}<br>"
                          "• Already Billed: {5}<br>"
                          "• Remaining: {6}<br>"
                          "• Current Invoice: {7}").format(
                            tax.idx,
                            account_head,
                            frappe.format_value(current, {'fieldtype': 'Currency'}),
                            so_name,
                            frappe.format_value(so_total, {'fieldtype': 'Currency'}),
                            frappe.format_value(billed, {'fieldtype': 'Currency'}),
                            frappe.format_value(so_total - billed, {'fieldtype': 'Currency'}),
                            frappe.format_value(current, {'fieldtype': 'Currency'})
                        ),
                        title=_("Tax Amount Exceeded")
                    )


def fetch_po_line_no_from_sales_order(doc,method=None):
    so_item_names = []
    for item in doc.items:
        so_item = item.get('so_detail') or item.get('sales_order_item')
        if so_item and so_item not in so_item_names:
            so_item_names.append(so_item)

    # Fetch po_line_no from Sales Order Items
    if so_item_names:
        so_items_data = frappe.get_all(
            'Sales Order Item',
            filters={"name": ["in", so_item_names]},
            fields=["name", "po_line_no"]
        )
        
        po_line_map = {item["name"]: item.get("po_line_no") for item in so_items_data}
    else:
        po_line_map = {}

    # Fetch Sales Orders to get their po_no
    so_names = []
    for item in doc.items:
        so_name = item.get('sales_order')
        if so_name and so_name not in so_names:
            so_names.append(so_name)

    if so_names:
        so_data = frappe.get_all(
            'Sales Order',
            filters={"name": ["in", so_names]},
            fields=["name", "po_no"]
        )
        
        so_po_map = {so["name"]: so.get("po_no") for so in so_data}
    else:
        so_po_map = {}

    # Set PO Line No in Sales Invoice items
    for item in doc.items:
        so_item = item.get('so_detail') or item.get('sales_order_item')
        so_name = item.get('sales_order')
        
        if so_item and so_item in po_line_map:
            item.po_line_no = po_line_map[so_item]
        
        # Also set po_no if needed
        if so_name and so_name in so_po_map:
            item.po_no = so_po_map[so_name]


def validate_duplicate_si(doc, method):
    """Prevent duplicate draft Sales Invoices for same customer, branch, item, rate, and taxes_and_charges."""
    
    # Skip validation for cancelled or submitted docs
    if doc.docstatus != 0:
        return

    # Get potential duplicate SIs first (outside item loop for efficiency)
    # Removed sales_order filter to catch duplicates even if SO is not linked
    duplicates = frappe.db.get_all(
        "Sales Invoice",
        filters={
            "customer": doc.customer,
            "branch": doc.branch or "",
            "taxes_and_charges": doc.taxes_and_charges or "",
            "docstatus": 0,  # Only Draft
            "name": ["!=", doc.name],  # Exclude current
        },
        fields=["name"]
    )

    if not duplicates:
        return

    # Collect all violations
    violations = []
    for item in doc.items:
        for d in duplicates:
            duplicate_items = frappe.db.get_all(
                "Sales Invoice Item",
                filters={
                    "parent": d.name,
                    "item_code": item.item_code,
                    # Removed qty check to restrict even on qty differences
                    "rate": item.rate,
                },
                fields=["item_code", "qty", "rate"]
            )
            if duplicate_items:
                violations.append({
                    "doc_name": d.name,
                    "item_code": item.item_code,
                    "qty": item.qty,
                    "rate": item.rate,
                    "existing_qty": duplicate_items[0].qty if duplicate_items else 'N/A'  # For message
                })

    if violations:
        # Format a single error message with all issues
        error_msg = "<b>Multiple Duplicate Sales Invoices Found:</b><br><br>"
        seen_docs = {}  # To group by doc if multiple items per doc
        for v in violations:
            doc_key = v["doc_name"]
            if doc_key not in seen_docs:
                seen_docs[doc_key] = []
            seen_docs[doc_key].append(f"- Item <b>{v['item_code']}</b> (Your Qty: <b>{v['qty']}</b>, Existing Qty: <b>{v['existing_qty']}</b>, Rate: <b>{v['rate']}</b>)")
        
        for doc_name, items_list in seen_docs.items():
            error_msg += f"Existing Draft Sales Invoice: <b><a href='/app/sales-invoice/{doc_name}'>{doc_name}</a></b><br>"
            error_msg += f"(Customer: <b>{doc.customer}</b>, Branch: <b>{doc.branch or 'N/A'}</b>, Sales Order: <b>N/A</b>, Commercial TC: <b>{doc.taxes_and_charges or 'N/A'}</b>)<br><br>"
            error_msg += "<br>".join(items_list)
            error_msg += "<br><br>"
        
        frappe.throw(_(error_msg))

def remove_free_items(doc):
	"""
	Remove free items from Sales Invoice during validate.
	Before removing, add remarks about free issue items to their associated parent items.
	"""
	if not doc.items:
		return

	# Step 1: Collect free item info grouped by parent item (component_of)
	free_items_by_parent = {}
	for row in doc.items:
		if row.is_free_item and row.component_of:
			parent_item = row.component_of
			if parent_item not in free_items_by_parent:
				free_items_by_parent[parent_item] = []
			
			# Collect free item details
			free_items_by_parent[parent_item].append({
				"item_code": row.item_code,
				"qty": row.qty,
				"uom": row.uom or "",
				"description": row.description or row.item_name or ""
			})

	# Step 2: Add remarks to parent items about their linked free issue items
	for row in doc.items:
		if not row.is_free_item and row.item_code in free_items_by_parent:
			free_items = free_items_by_parent[row.item_code]
			
			# Build the remark text for free issue items
			remark_lines = ["Free Issue Items:"]
			for fi in free_items:
				remark_lines.append(
					f"  • {fi['item_code']} - Qty: {fi['qty']} {fi['uom']}"
				)
			
			free_item_remark = "\n".join(remark_lines)
			
			# Append to existing remarks or set new
			if row.remarks:
				row.remarks = f"{row.remarks}\n{free_item_remark}"
			else:
				row.remarks = free_item_remark

	# Step 3: Keep only non-free items
	items_to_keep = []
	for row in doc.items:
		if not row.is_free_item:
			items_to_keep.append(row)

	# Reset child table safely
	doc.set("items", items_to_keep)



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


