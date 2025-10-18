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


