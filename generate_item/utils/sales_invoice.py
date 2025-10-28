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


