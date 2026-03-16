# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt



import frappe
# from email.utils import formatdate
from frappe.utils import getdate
from datetime import date as date_type
from frappe import _

from frappe.utils import flt



def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

# ---------------------------------------------------------
# COLUMNS
# ---------------------------------------------------------

def get_columns():
    columns = [
        {"label": _("Sales Order"), "fieldname": "sales_order", "fieldtype": "Link", "options": "Sales Order", "width": 150},
        {"label": _("Branch"), "fieldname": "branch", "fieldtype": "Data", "width": 100},
         {
            "label": "Currency",
            "fieldname": "currency",
            "fieldtype": "Link",
            "options": "Currency",
            "width": 100
        },
        {"label": _("Order Date"), "fieldname": "order_date", "fieldtype": "Date", "width": 120},
        {"label": _("Order Delivery Date"), "fieldname": "order_delivery_date", "fieldtype": "Date", "width": 120},
        {"label": _("Customer Name"), "fieldname": "customer_name", "fieldtype": "Data", "width": 150},
        {"label": _("Customer PO Number"), "fieldname": "customer_po_number", "fieldtype": "Data", "width": 120},
        {"label": _("Customer PO Date"), "fieldname": "customer_po_date", "fieldtype": "Date", "width": 100},
        {"label": _("Liquidate Damage"), "fieldname": "custom_liquidate_damage", "fieldtype": "Data", "width": 120},
        {"label": _("Order Status"), "fieldname": "order_status", "fieldtype": "Data", "width": 120},
        {"label": _("Approved Date"), "fieldname": "approved_on", "fieldtype": "Date", "width": 100},
        {"label": _("Approved By"), "fieldname": "approved_by", "fieldtype": "Data", "width": 120},
        {"label": _("Sales Person 1"), "fieldname": "sales_person_1", "fieldtype": "Data", "width": 150},
        {"label": _("Sales Person 2"), "fieldname": "sales_person_2", "fieldtype": "Data", "width": 150},
        {"label": _("Payment Term"), "fieldname": "custom_payment_terms", "fieldtype": "Data", "width": 100},
        {"label": _("Mode Of Dispatch"), "fieldname": "mode_of_dispatch", "fieldtype": "Data", "width": 120},
        {"label": _("Freight Charges"), "fieldname": "custom_freight_charges", "fieldtype": "Data", "width": 100},
        {"label": _("Price Basis"), "fieldname": "price_basis", "fieldtype": "Data", "width": 100},
        {"label": _("Batch No Ref"), "fieldname": "custom_batch_no", "fieldtype": "Link", "options": "Batch", "width": 100},
        {"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 150},
        {"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 150},
        {"label": _("Item Description"), "fieldname": "item_description", "fieldtype": "Text", "width": 200},
        {"label": _("Item Group"), "fieldname": "item_group", "fieldtype": "Data", "width": 100},
        {"label": _("Order Qty"), "fieldname": "order_qty", "fieldtype": "Float", "width": 80},
        {"label": _("Delivered Qty"), "fieldname": "delivered_qty", "fieldtype": "Float", "width": 100},
        {"label": _("Invoiced Qty"), "fieldname": "invoiced_qty", "fieldtype": "Float", "width": 100},
        {"label": _("Pending Qty"), "fieldname": "pending_qty", "fieldtype": "Float", "width": 100},
        {"label": _("Unit Rate"), "fieldname": "unit_rate", "fieldtype": "Currency","options": "currency", "width": 100},
        {"label": _("Item Basic Amount INR"), "fieldname": "item_basic_amount_inr","options": "currency", "fieldtype": "Currency", "width": 120},
        {
			"label": _("Item ID"),
			"fieldname": "item_id",
			"fieldtype": "Data",
			"width": 100
		},
        {
			"label": _("Order Line Index"),
			"fieldname": "order_line_index",
			"fieldtype": "Int",
			"width": 80
		},
         {
			"label": _("Additional Charges"),
			"fieldname": "additional_charges",
			"fieldtype": "Currency",
            "options": "currency",
			"width": 120
		},
         {
            "label": _("Item Grand Total"),
            "fieldname": "calculated_grand_total",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 120
        },
         {
            "label": "Sales Order Total With Tax",
            "fieldname": "base_grand_total",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 150
        },


        # ---------------------------------------------------------
        #  NEW COLUMNS INSERTED HERE (AS REQUESTED)
        # ---------------------------------------------------------

        {"label": _("PO Sr. No."), "fieldname": "po_sr_no", "fieldtype": "Data", "width": 120},
        {"label": _("Tag No"), "fieldname": "tag_no", "fieldtype": "Data", "width": 100},
        {"label": _("Item Remarks"), "fieldname": "item_remarks", "fieldtype": "Data", "width": 200},
        {"label": _("Order Remarks (Terms & Conditions)"), "fieldname": "order_terms", "fieldtype": "Data", "width": 200},
        {"label": _("End User"), "fieldname": "end_user", "fieldtype": "Data", "width": 150},
        {"label": _("Project"), "fieldname": "custom_customer_project_name", "fieldtype": "Data", "width": 150},
        {"label": _("Qtn Ref. No."), "fieldname": "qtn_ref_no", "fieldtype": "Data", "width": 150},
        {"label": _("Qtn Ref Date"), "fieldname": "qtn_ref_date", "fieldtype": "Date", "width": 100},
        {"label": _("Billing Customer Name (Order Level)"), "fieldname": "billing_customer", "fieldtype": "Data", "width": 150},
        {"label": _("Shipping Customer Name (Order Level)"), "fieldname": "shipping_customer_order", "fieldtype": "Data", "width": 150},
        {"label": _("Shipping Customer Name (Item Level)"), "fieldname": "shipping_customer_item", "fieldtype": "Data", "width": 150},
        {"label": _("Billing Address (Order Level)"), "fieldname": "billing_address", "fieldtype": "Data", "width": 200},
        {"label": _("Shipping Address (Order Level)"), "fieldname": "shipping_address_order", "fieldtype": "Data", "width": 200},
        {"label": _("Shipping Address (Item Level)"), "fieldname": "shipping_address_item", "fieldtype": "Data", "width": 250},
        {"label": _("GST No (Order Level)"), "fieldname": "gst_order", "fieldtype": "Data", "width": 120,"hidden":1},
        {"label": _("GST No (Item Level)"), "fieldname": "gst_item", "fieldtype": "Data", "width": 120,"hidden":1},
        {"label": _("Taxes (Order Level)"), "fieldname": "taxes_order", "fieldtype": "Currency", "width": 120,"hidden":1},
        {"label": _("Taxes (Line Item Level)"), "fieldname": "taxes_item", "fieldtype": "Currency", "width": 120,"hidden":1},
        {"label": _("Delivery Status"), "fieldname": "delivery_status", "fieldtype": "Data", "width": 120},
        {"label": _("Delivered Qty (Actual)"), "fieldname": "delivered_qty_actual", "fieldtype": "Float", "width": 120,"hidden":1},
        # {"label": _("Delivered Date"), "fieldname": "delivered_date", "fieldtype": "Date", "width": 120},
        {"label": _("Invoice No."), "fieldname": "invoice_no", "fieldtype": "Data", "width": 150},
        {"label": _("Repeat Order Ref"), "fieldname": "custom_repeat_order_ref", "fieldtype": "Data", "width": 150},

        # ---------------------------------------------------------
        #  EXISTING GENERATOR ATTRIBUTES
        # ---------------------------------------------------------

        {"label": _("Type of Product"), "fieldname": "type_of_product", "fieldtype": "Data", "width": 120},
        {"label": _("Valve Type"), "fieldname": "valve_type", "fieldtype": "Data", "width": 120},
        {"label": _("Construction"), "fieldname": "construction", "fieldtype": "Data", "width": 100},
        {"label": _("Bore"), "fieldname": "bore", "fieldtype": "Data", "width": 80},
        {"label": _("Size"), "fieldname": "size", "fieldtype": "Data", "width": 80},
        {"label": _("Rating"), "fieldname": "rating", "fieldtype": "Data", "width": 80},
        {"label": _("Ends"), "fieldname": "ends", "fieldtype": "Data", "width": 80},
        {"label": _("End Sub type"), "fieldname": "end_sub_type", "fieldtype": "Data", "width": 100},
        {"label": _("Shell MOC"), "fieldname": "shell_moc", "fieldtype": "Data", "width": 100},
        {"label": _("Ball Moc"), "fieldname": "ball_moc", "fieldtype": "Data", "width": 100},
        {"label": _("Ball Facing"), "fieldname": "ball_facing", "fieldtype": "Data", "width": 100},
        {"label": _("Seat Ring(GUIDE) MOC"), "fieldname": "seat_ring_guide_moc", "fieldtype": "Data", "width": 120},
        {"label": _("Seat Facing/Plating"), "fieldname": "seat_facing_plating", "fieldtype": "Data", "width": 120},
        {"label": _("SEAT INSERT + SEAT SEAL MOC"), "fieldname": "seat_insert_seat_seal_moc", "fieldtype": "Data", "width": 150},
        {"label": _("Stem MOC"), "fieldname": "stem_moc", "fieldtype": "Data", "width": 100},
        {"label": _("GASKET"), "fieldname": "gasket", "fieldtype": "Data", "width": 100},
        {"label": _("Gland Packing + O'Ring Moc"), "fieldname": "gland_packing_o_ring_moc", "fieldtype": "Data", "width": 150},
        {"label": _("Fasteners"), "fieldname": "fasteners", "fieldtype": "Data", "width": 100},
        {"label": _("Operator"), "fieldname": "operator", "fieldtype": "Data", "width": 100},
        {"label": _("Accessories"), "fieldname": "accessories", "fieldtype": "Data", "width": 120},
        {"label": _("Special Requirement for valve"), "fieldname": "special_requirement_for_valve", "fieldtype": "Data", "width": 150},
        {"label": _("QUALITY Special Requirement (NDE)"), "fieldname": "quality_special_requirement_nde", "fieldtype": "Data", "width": 150},
        {"label": _("Service"), "fieldname": "service", "fieldtype": "Data", "width": 100},
        {"label": _("Inspection"), "fieldname": "inspection", "fieldtype": "Data", "width": 100},
       
    ]
    return columns

# ---------------------------------------------------------
# MAIN DATA SECTION
# ---------------------------------------------------------

def get_data(filters):
    if not filters:
        filters = {}

    data = []
    so_conditions = get_so_conditions(filters)

    so_fields = [
        "name as sales_order",
        "branch",
        "currency",
        "transaction_date as order_date",
        "delivery_date as order_delivery_date",
        "customer_name",
        "po_no as customer_po_number",
        "po_date as customer_po_date",
        "custom_liquidate_damage",
        "status as order_status",
        # "modified as approved_on",
        # "modified_by as approved_by",
        "payment_terms_template as payment_term",
        "custom_payment_terms",
        "custom_mode_of_dispatch",
        "custom_freight_charges",
        "custom_price_basis",
        "terms",
        "custom_end_user",
        "custom_qtn_ref_no",
        "custom_qtn_ref_date",
        "customer",
        "shipping_address_name",
        "address_display",
        "shipping_address",
        "billing_address_gstin",
        "total_taxes_and_charges",
        "delivery_status",
        "total_qty",
        "grand_total as grand_total_usd",
        "base_grand_total",
        "custom_customer_project_name",
        "delivery_date",
        "conversion_rate",
        "custom_repeat_order_ref"
    ]

    sales_orders = frappe.get_all("Sales Order", filters=so_conditions, fields=so_fields)

    for so in sales_orders:

        # Get Sales Team
        sales_team = frappe.get_all(
            "Sales Team",
            filters={"parent": so.sales_order},
            fields=["sales_person"],
            order_by="idx asc",
            limit_page_length=2
        )

        sales_person_1 = sales_team[0].sales_person if len(sales_team) > 0 else ""
        sales_person_2 = sales_team[1].sales_person if len(sales_team) > 1 else ""

        # Item filters
        so_item_filters = {"parent": so.sales_order}

        if filters.get("item_code"):
            so_item_filters["item_code"] = filters.item_code
        if filters.get("batch_no"):
            so_item_filters["custom_batch_no"] = filters.batch_no

        # Fetch ALL required item fields properly from SO Item child table
        item_fields = [
            "name as item_id",
            "idx as item_idx",
			"parent",
            "idx as order_line_index",
            "item_code",
            "item_name",
            "description as item_description",
            "item_group",
            "qty as order_qty",
            # "delivered_qty",
            "rate as rate_usd",
            "base_rate as unit_rate",
            "base_amount as item_basic_amount_inr",
            "amount as amount_usd",
            "custom_batch_no",
            "line_remark",        # ✔ Correct Item Remarks
            "igst_amount",
            "tag_no",             # ✔ Correct Tag No
            "po_line_no",         # ✔ Correct PO Sr No
            "custom_shipping_address"
        ]

        items = frappe.get_all("Sales Order Item", filters=so_item_filters, fields=item_fields,order_by="parent asc, idx asc")

        so.order_date = safe_date(so.order_date)
        so.order_delivery_date = safe_date(so.order_delivery_date)
        so.customer_po_date = safe_date(so.customer_po_date) 
        so.custom_qtn_ref_date = safe_date(so.custom_qtn_ref_date)  

        # Shipping Customer (order level)
        shipping_customer_order = get_address_link_name(so.shipping_address_name)
        actual_charges = 0
        actual_tax_row = frappe.db.sql(
            """
            SELECT SUM(base_tax_amount) AS actual_total,
            SUM(tax_amount) AS actual_total_usd
            FROM `tabSales Taxes and Charges`
            WHERE parent = %s
            AND parenttype = 'Sales Order'
            AND charge_type = 'Actual'
            """,
            so.sales_order,
            as_dict=True,
        )

        if actual_tax_row and so.currency == "USD" and actual_tax_row[0].actual_total_usd:
            actual_charges = actual_tax_row[0].actual_total_usd or 0

        if actual_tax_row and so.currency == "INR" and actual_tax_row[0].actual_total:
            actual_charges = actual_tax_row[0].actual_total or 0

        #  Calculate per-item additional charges here
        num_items = len(items)
        additional_charges = actual_charges / num_items if num_items else 0 

       

        for item in items:
            approval_details = get_approval_details(so.sales_order)
            # item_id = f"{item.parent}-{item.item_idx}"
            item_gen = get_item_generator_attributes(item.item_code)

            # Shipping Customer (item level)
            shipping_customer_item = get_address_link_name(item.custom_shipping_address)

            # Shipping Address (item level)
            shipping_address_item = get_address_full_display(item.custom_shipping_address)

            # GST (item level)
            gst_item = frappe.db.get_value("Address", item.custom_shipping_address, "gstin") if item.custom_shipping_address else ""

            invoice_no = get_invoice_no(so.sales_order)
            # delivered_qty = get_delivered_qty_from_invoice(so.sales_order, item.item_code)
            delivered_qty = get_delivered_qty_from_delivery_note(item.item_id)
            invoiced_qty = get_invoiced_qty_from_sales_invoice(item.item_id)

            if invoice_no:
                # Delivered Qty & Delivery Date
                delivered_qty_actual = get_delivered_qty_from_delivery_note(item.item_id)
                # delivered_date = so.delivery_date if so.order_status not in ["Draft", "Cancelled", "To Deliver and Bill"] else ""
            else:
                delivered_qty_actual = ""
                delivered_date = ""

            # Invoice No.
            # invoice_no = get_invoice_no(so.sales_order)
            

            cur       = so.currency
            conv_rate = so.conversion_rate or 1 
            is_foreign = so.currency != "INR"

            display_unit_rate         = item.rate_usd        if is_foreign else item.unit_rate
            display_item_basic_amount = item.amount_usd      if is_foreign else item.item_basic_amount_inr
            
            display_calculated_total  = flt((display_item_basic_amount or 0) + (additional_charges or 0), 2)
            display_grand_total       = so.grand_total_usd     if is_foreign else so.base_grand_total


            
            # so.order_date = getdate(so.order_date) if so.order_date else None
            # so.order_delivery_date = getdate(so.order_delivery_date) if so.order_delivery_date else None
            # so.customer_po_date = getdate(so.customer_po_date) if so.customer_po_date else None
            # so.custom_qtn_ref_date = getdate(so.custom_qtn_ref_date) if so.custom_qtn_ref_date else None
            # formatdate(so.order_date)
            # formatdate(so.order_delivery_date)
            # formatdate(so.customer_po_date)
            # formatdate(so.custom_qtn_ref_date)
            # Build row
            row = [
                so.sales_order,
                so.branch or "",
                so.currency,
                safe_date(so.order_date),
                safe_date(so.order_delivery_date),
                so.customer_name,
                so.customer_po_number or "",
                safe_date(so.customer_po_date),
                so.custom_liquidate_damage,
                so.order_status,
                # so.approved_on,
                # so.approved_by or "",
                approval_details.get("approved_on"),
				approval_details.get("approved_by") or "",
                sales_person_1,
                sales_person_2,
                so.custom_payment_terms or "",
                so.custom_mode_of_dispatch or "",
                so.custom_freight_charges or "",
                so.custom_price_basis or "",
                item.custom_batch_no or "",
                item.item_code,
                item.item_name,
                item.item_description,
                item.item_group,
                item.order_qty,
                delivered_qty or 0,
                invoiced_qty or 0,
                (item.order_qty or 0) - (delivered_qty or 0),
                display_unit_rate,
                display_item_basic_amount,
                item.item_id,
                item.order_line_index,
                additional_charges,
				display_calculated_total,
                display_grand_total  ,

                # -------------------------
                # FIXED COLUMNS BELOW ⬇⬇⬇
                # -------------------------

                           
                item.po_line_no or "",
                item.tag_no or "",             
                item.line_remark or "",        
                so.terms or "",       
                so.custom_end_user or "",
                so.custom_customer_project_name or "",
                so.custom_qtn_ref_no or "",
                safe_date(so.custom_qtn_ref_date),
                so.customer,
                shipping_customer_order,
                shipping_customer_item,
                so.address_display or "",
                so.shipping_address or "",
                shipping_address_item,
                so.billing_address_gstin or "",
                gst_item,
                so.total_taxes_and_charges or 0,
                item.igst_amount or 0,
                so.order_status or "",
                delivered_qty_actual or 0,
                
                # delivered_date,
                invoice_no,
                so.custom_repeat_order_ref or "",

                # Generator attributes
                item_gen.get("attribute_1_value"),
                item_gen.get("attribute_2_value"),
                item_gen.get("attribute_3_value"),
                item_gen.get("attribute_4_value"),
                item_gen.get("attribute_5_value"),
                item_gen.get("attribute_6_value"),
                item_gen.get("attribute_7_value"),
                item_gen.get("attribute_8_value"),
                item_gen.get("attribute_9_value"),
                item_gen.get("attribute_10_value"),
                item_gen.get("attribute_11_value"),
                item_gen.get("attribute_12_value"),
                item_gen.get("attribute_13_value"),
                item_gen.get("attribute_14_value"),
                item_gen.get("attribute_15_value"),
                item_gen.get("attribute_16_value"),
                item_gen.get("attribute_17_value"),
                item_gen.get("attribute_18_value"),
                item_gen.get("attribute_19_value"),
                item_gen.get("attribute_20_value"),
                item_gen.get("attribute_21_value"),
                item_gen.get("attribute_22_value"),
                item_gen.get("attribute_23_value"),
                item_gen.get("attribute_24_value"),
            ]

            data.append(row)

    return data


# ---------------------------------------------------------
# ADDRESS LOOKUP HELPERS
# ---------------------------------------------------------

def get_address_link_name(address_name):
    """Fetch first link_name from Address.links child table."""
    if not address_name:
        return ""
    links = frappe.get_all("Dynamic Link", filters={"parent": address_name}, fields=["link_name"], limit=1)
    return links[0].link_name if links else ""

def get_address_full_display(address_name):
    """Concatenate full address fields."""
    if not address_name:
        return ""
    addr = frappe.db.get_value(
        "Address",
        address_name,
        ["address_title", "address_line1", "address_line2", "city", "state", "country", "pincode"],
        as_dict=True
    )
    if not addr:
        return ""
    return ", ".join([str(x) for x in addr.values() if x])

# ---------------------------------------------------------
# SALES INVOICE LOOKUP
# ---------------------------------------------------------

# def get_invoice_no(sales_order):
#     inv = frappe.get_all("Sales Invoice Item", filters={"sales_order": sales_order}, fields=["parent"], limit=1)
#     return inv[0].parent if inv else ""

def get_invoice_no(sales_order):
    invoices = frappe.get_all(
        "Sales Invoice Item",
        filters={"sales_order": sales_order},
        fields=["parent"]
    )

    if not invoices:
        return ""

    invoice_set = sorted({d.parent for d in invoices})
    return ", ".join(invoice_set)

def get_delivered_qty_from_invoice(sales_order, item_code):
    """
    Fetch the total delivered quantity for a specific item from Sales Invoice Items
    linked to the given sales order.
    """
    result = frappe.db.sql(
        """
        SELECT SUM(delivered_qty) as total_delivered_qty
        FROM `tabSales Invoice Item`
        WHERE sales_order = %s
          AND item_code = %s
          AND docstatus IN (0, 1)
        """,
        (sales_order, item_code),
        as_dict=True
    )
    
    if result and result[0].total_delivered_qty:
        return result[0].total_delivered_qty
    
    return 0
# ---------------------------------------------------------
# OTHERS
# ---------------------------------------------------------

def get_so_conditions(filters):
    conditions = {
        "docstatus": ["in", [0, 1]]  
    }
    

    if filters.get("from_date") and filters.get("to_date"):
        conditions["transaction_date"] = ["between", [filters.from_date, filters.to_date]]
    elif filters.get("from_date"):
        conditions["transaction_date"] = [">=", filters.from_date]
    elif filters.get("to_date"):
        conditions["transaction_date"] = ["<=", filters.to_date]

    if filters.get("customer"):
        conditions["customer"] = filters.customer
    if filters.get("branch"):
        conditions["branch"] = filters.branch
    if filters.get("sales_order"):
        conditions["name"] = filters.sales_order
 
    # Exclude Closed & Completed
    # conditions["status"] = ["not in", ["Closed", "Completed"]]
    # if filters.get("status"):
    #     conditions["status"] = ["in", filters.status]
     
    if filters.get("status"):
        conditions["status"] = ["in", filters.status]
    else:
        conditions["status"] = ["not in", ["Closed", "Completed"]]

    return conditions

def get_item_generator_attributes(item_code):
    if not item_code:
        return {}
    fields = [f"attribute_{i}_value" for i in range(1, 25)]
    return frappe.db.get_value("Item Generator", {"name": item_code}, fields, as_dict=True) or {}



def get_approval_details(sales_order):
	approval = frappe.db.sql(
		"""
		SELECT
			username AS approved_by,
			modification_time AS approved_on
		FROM `tabState Change Items`
		WHERE parent = %s
		  AND parenttype = 'Sales Order'
		  AND workflow_state = 'Approved'
		ORDER BY modification_time DESC
		LIMIT 1
		""",
		sales_order,
		as_dict=True,
	)

	if approval:
		return approval[0]

	return {"approved_by": "", "approved_on": None}


def get_delivered_qty_from_delivery_note(so_detail):
    delivered_qty = frappe.db.sql("""
        SELECT 
            SUM(dni.qty)
        FROM 
            `tabDelivery Note Item` dni
        INNER JOIN 
            `tabDelivery Note` dn 
            ON dn.name = dni.parent
        WHERE 
            dni.so_detail = %s
            AND dn.docstatus = 1
    """, (so_detail,), as_list=1)

    return flt(delivered_qty[0][0]) if delivered_qty and delivered_qty[0][0] else 0



# def get_invoiced_qty_from_sales_invoice (so_detail):
#     delivered_qty = frappe.db.sql("""
#         SELECT 
#             SUM(dni.qty)
#         FROM 
#             `tabSales Invoice Item` sii
#         INNER JOIN 
#             `tabSales Invoice` si 
#             ON si.name = sii.parent
#         WHERE 
#             sii.so_detail = %s
#             AND si.docstatus = 1
#     """, (so_detail,), as_list=1)

#     return flt(delivered_qty[0][0]) if delivered_qty and delivered_qty[0][0] else 0

def get_invoiced_qty_from_sales_invoice(so_detail):
    invoiced_qty = frappe.db.sql("""
        SELECT 
            SUM(sii.qty)
        FROM 
            `tabSales Invoice Item` sii
        INNER JOIN 
            `tabSales Invoice` si 
            ON si.name = sii.parent
        WHERE 
            sii.so_detail = %s
            AND si.docstatus = 1
    """, (so_detail,), as_list=1)

    return flt(invoiced_qty[0][0]) if invoiced_qty and invoiced_qty[0][0] else 0


def safe_date(val):
    if not val:
        return None
    if isinstance(val, date_type):
        return val
    try:
        return getdate(str(val))
    except Exception:
        return None


