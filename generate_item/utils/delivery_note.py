# Copyright (c) 2025, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe import _

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_dispatchable_sales_orders(doctype, txt, searchfield, start, page_len, filters):
    """
    Custom query for Dispatchable Sales Orders link field.
    Returns Sales Orders that are:
    - Submitted and not fully delivered
    - Have all linked Work Orders completed
    """

    import json

    # Parse filters safely
    if isinstance(filters, str):
        try:
            filters = json.loads(filters)
        except Exception:
            filters = {}
    elif not isinstance(filters, dict):
        filters = {}

    customer = filters.get("customer")
    company = filters.get("company")
    project = filters.get("project")

    if not customer:
        return []

    values = {
        "customer": customer,
        "start": int(start or 0),
        "page_len": int(page_len or 20),
    }

    # Core conditions
    conditions = [
        "so.docstatus = 1",
        "so.status NOT IN ('Closed', 'On Hold', 'Completed')",
        "COALESCE(so.per_delivered, 0) < 99.99",
        "so.customer = %(customer)s",
        # Has at least one completed Work Order
        """EXISTS (
            SELECT 1 FROM `tabWork Order` wo
            WHERE wo.sales_order = so.name
            AND wo.docstatus = 1
            AND wo.status = 'Completed'
        )""",
        # No Work Orders that are not completed
        """NOT EXISTS (
            SELECT 1 FROM `tabWork Order` wo2
            WHERE wo2.sales_order = so.name
            AND wo2.docstatus = 1
            AND wo2.status != 'Completed'
        )"""
    ]

    if company:
        conditions.append("so.company = %(company)s")
        values["company"] = company
    if project:
        conditions.append("so.project = %(project)s")
        values["project"] = project
    if txt:
        conditions.append("(so.name LIKE %(txt)s OR so.customer_name LIKE %(txt)s)")
        values["txt"] = f"%{txt}%"

    where_clause = " AND ".join(conditions)

    # --- Add Batch Reference in Description ---
    query = f"""
        SELECT 
            so.name,
            CONCAT(
                so.name,
                ' - ',
                COALESCE((
                    SELECT MAX(soi.custom_batch_no)
                    FROM `tabSales Order Item` soi
                    WHERE soi.parent = so.name
                    AND COALESCE(soi.custom_batch_no, '') != ''
                ), 'No Batch'),
                ' - ',
                so.customer_name
            ) AS description
        FROM `tabSales Order` so
        WHERE {where_clause}
        ORDER BY so.modified DESC
        LIMIT %(page_len)s OFFSET %(start)s
    """

    return frappe.db.sql(query, values, as_list=True)


@frappe.whitelist()
def get_dispatchable_sales_orders_list(customer, company=None, project=None):
    """
    Used in custom Dispatchable SO button.
    Returns list of dispatchable Sales Orders with batch info.
    """

    if not customer:
        return []

    values = {"customer": customer}

    conditions = [
        "so.docstatus = 1",
        "so.status NOT IN ('Closed', 'On Hold', 'Completed')",
        "COALESCE(so.per_delivered, 0) < 99.99",
        "so.customer = %(customer)s",
        # Has at least one completed Work Order
        """EXISTS (
            SELECT 1 FROM `tabWork Order` wo
            WHERE wo.sales_order = so.name
            AND wo.docstatus = 1
            AND wo.status = 'Completed'
        )""",
        # No Work Orders that are not completed
        """NOT EXISTS (
            SELECT 1 FROM `tabWork Order` wo2
            WHERE wo2.sales_order = so.name
            AND wo2.docstatus = 1
            AND wo2.status != 'Completed'
        )"""
    ]

    if company:
        conditions.append("so.company = %(company)s")
        values["company"] = company
    if project:
        conditions.append("so.project = %(project)s")
        values["project"] = project

    where_clause = " AND ".join(conditions)

    query = f"""
        SELECT 
            so.name,
            so.customer_name,
            COALESCE((
                SELECT MAX(soi.custom_batch_no)
                FROM `tabSales Order Item` soi
                WHERE soi.parent = so.name
                AND COALESCE(soi.custom_batch_no, '') != ''
            ), '') AS batch_no
        FROM `tabSales Order` so
        WHERE {where_clause}
        ORDER BY so.modified DESC
    """

    return frappe.db.sql(query, values, as_dict=True)



@frappe.whitelist()
def make_delivery_note(source_name, target_doc=None, kwargs=None):
	"""Create Delivery Note from Sales Order while ensuring remaining qty excludes Draft DNs.

	This wraps the core method and then adjusts mapped quantities by subtracting
	any quantities already present in Draft Delivery Notes for the same Sales Order Item.
	"""
	from erpnext.selling.doctype.sales_order.sales_order import (
		make_delivery_note as core_make_delivery_note,
	)

	# Handle kwargs parameter - it might be a JSON string
	print(f"DEBUG: make_delivery_note called with kwargs type: {type(kwargs)}, value: {kwargs}")
	
	if isinstance(kwargs, str):
		try:
			import json
			kwargs = json.loads(kwargs)
			print(f"DEBUG: Parsed kwargs from string: {kwargs}")
		except Exception as e:
			print(f"DEBUG: Failed to parse kwargs: {e}")
			kwargs = {}
	elif not isinstance(kwargs, dict):
		print(f"DEBUG: kwargs is not dict, converting to empty dict")
		kwargs = {}
	
	print(f"DEBUG: Final kwargs: {kwargs}")

	# Create the Delivery Note using core logic first
	dn = core_make_delivery_note(source_name=source_name, target_doc=target_doc, kwargs=kwargs)

	# Adjust quantities to consider Draft DNs as consumed
	items_to_keep = []
	for item in dn.items or []:
		so_item_name = getattr(item, "so_detail", None)
		if not so_item_name:
			items_to_keep.append(item)
			continue

		# Fetch source SO Item values
		so_item = frappe.db.get_value(
			"Sales Order Item",
			so_item_name,
			["qty", "delivered_qty", "conversion_factor"],
			as_dict=True,
		)
		if not so_item:
			items_to_keep.append(item)
			continue

		so_qty = frappe.utils.flt(so_item.qty)
		delivered_qty = frappe.utils.flt(so_item.delivered_qty)
		so_cf = frappe.utils.flt(so_item.conversion_factor) or 1.0

		# Base remaining in stock units from Submitted DNs
		base_remaining_stock_qty = max((so_qty - delivered_qty), 0) * so_cf

		# Subtract quantities already present in Draft Delivery Notes for this SO Item
		draft_dn_stock_qty = frappe.db.sql(
			"""
			SELECT COALESCE(SUM(dni.stock_qty), 0)
			FROM `tabDelivery Note Item` dni
			INNER JOIN `tabDelivery Note` dn ON dni.parent = dn.name
			WHERE dn.docstatus = 0
			  AND dni.so_detail = %s
			""",
			(so_item_name,),
		)[0][0]

		remaining_stock_qty = max(base_remaining_stock_qty - frappe.utils.flt(draft_dn_stock_qty), 0)

		# Use target item's conversion factor to set displayed qty
		item_cf = frappe.utils.flt(getattr(item, "conversion_factor", None)) or 1.0
		new_qty = remaining_stock_qty / item_cf if item_cf else 0
		item.qty = new_qty
		item.stock_qty = remaining_stock_qty

		# Keep only rows with positive qty
		if new_qty and new_qty > 0:
			items_to_keep.append(item)

	# Replace items with filtered list to avoid zero-qty rows
	if dn.items is not None:
		dn.items = items_to_keep

	return dn



@frappe.whitelist()
def set_remaining_actual_taxes(delivery_name):
    """
    Whitelisted method to calculate and set remaining actual taxes
    FOR SAVED DOCUMENTS ONLY (Delivery Note)
    """
    if not frappe.db.exists("Delivery Note", delivery_name):
        frappe.throw(_("Delivery Note {0} not found").format(delivery_name))
    
    doc = frappe.get_doc("Delivery Note", delivery_name)
    
    if doc.docstatus == 2:
        frappe.throw(_("Cannot update taxes for a cancelled Delivery Note"))
    
    _calculate_and_set_remaining_taxes(doc)
    doc.save()
    frappe.db.commit()
    
    return {
        "success": True,
        "message": _("Actual taxes updated successfully on Delivery Note")
    }


@frappe.whitelist()
def get_remaining_taxes_for_draft(sales_orders, current_dn_name=None):
    """
    Calculate remaining actual taxes for DRAFT/UNSAVED Delivery Note
    """
    if isinstance(sales_orders, str):
        import json
        sales_orders = json.loads(sales_orders)

    remaining_taxes = {}

    for so_name in sales_orders:
        # Get Sales Order actual taxes
        so_doc = frappe.get_doc("Sales Order", so_name)
        so_actual_taxes = {}
        for tax in so_doc.taxes:
            if tax.charge_type == "Actual":
                so_actual_taxes[tax.account_head] = so_actual_taxes.get(tax.account_head, 0) + (tax.tax_amount or 0)

        if not so_actual_taxes:
            continue

        # Get all existing Delivery Notes against the SO
        filters = {
            "against_sales_order": so_name,
            "docstatus": ["!=", 2],
        }

        if current_dn_name and frappe.db.exists("Delivery Note", current_dn_name):
            filters["parent"] = ["!=", current_dn_name]

        existing_dns = frappe.get_all(
            "Delivery Note Item",
            filters=filters,
            fields=["parent"],
            distinct=True
        )

        billed_taxes = {}
        for dn in existing_dns:
            dn_doc = frappe.get_doc("Delivery Note", dn.parent)
            for tax in dn_doc.taxes:
                if tax.charge_type == "Actual":
                    billed_taxes[tax.account_head] = billed_taxes.get(tax.account_head, 0) + (tax.tax_amount or 0)

        # Compute remaining
        for account_head, total_amount in so_actual_taxes.items():
            billed_amount = billed_taxes.get(account_head, 0)
            remaining = max(total_amount - billed_amount, 0)
            if account_head in remaining_taxes:
                remaining_taxes[account_head] = min(remaining_taxes[account_head], remaining)
            else:
                remaining_taxes[account_head] = remaining

    return remaining_taxes


def after_insert(doc, method=None):
    """Run after new Delivery Note is inserted"""
    _calculate_and_set_remaining_taxes(doc)


def _calculate_and_set_remaining_taxes(doc):
    """
    Internal function to calculate remaining taxes for Delivery Note
    """
    sales_orders = list(set([item.against_sales_order for item in doc.items if item.against_sales_order]))
    if not sales_orders:
        return

    taxes_updated = False

    for so_name in sales_orders:
        so_doc = frappe.get_doc("Sales Order", so_name)
        so_actual_taxes = {}
        for tax in so_doc.taxes:
            if tax.charge_type == "Actual":
                so_actual_taxes[tax.account_head] = {
                    "amount": tax.tax_amount or 0,
                    "description": tax.description,
                    "cost_center": tax.cost_center,
                    "branch": tax.get("branch"),
                }

        if not so_actual_taxes:
            continue

        # Get existing DNs (exclude current)
        existing_dns = frappe.get_all(
            "Delivery Note Item",
            filters={"against_sales_order": so_name, "docstatus": ["!=", 2], "parent": ["!=", doc.name]},
            fields=["parent"],
            distinct=True
        )

        billed_taxes = {}
        for dn in existing_dns:
            dn_doc = frappe.get_doc("Delivery Note", dn.parent)
            for tax in dn_doc.taxes:
                if tax.charge_type == "Actual":
                    billed_taxes[tax.account_head] = billed_taxes.get(tax.account_head, 0) + (tax.tax_amount or 0)

        # Update current doc taxes
        for tax in doc.taxes:
            if tax.charge_type == "Actual" and tax.account_head in so_actual_taxes:
                so_total = so_actual_taxes[tax.account_head]["amount"]
                billed = billed_taxes.get(tax.account_head, 0)
                remaining = max(so_total - billed, 0)

                if tax.tax_amount != remaining:
                    tax.tax_amount = remaining
                    tax.base_tax_amount = remaining
                    tax.tax_amount_after_discount_amount = remaining
                    tax.base_tax_amount_after_discount_amount = remaining
                    taxes_updated = True

                    frappe.msgprint(
                        _("Updated '{0}' tax to remaining amount {1}").format(
                            tax.account_head, frappe.format_value(remaining, {"fieldtype": "Currency"})
                        ),
                        alert=True, indicator="blue"
                    )

    if taxes_updated:
        doc.calculate_taxes_and_totals()
        if doc.name and not doc.get("__islocal"):
            doc.db_update()
        frappe.msgprint(_("Actual taxes adjusted successfully"), alert=True, indicator="green")
