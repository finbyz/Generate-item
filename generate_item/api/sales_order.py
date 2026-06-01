import frappe
from frappe import _


@frappe.whitelist()
def get_previous_sales_data(customer, items):

    if isinstance(items, str):
        items = frappe.parse_json(items)

    result = {}

    for item_code in items:

        result[item_code] = {
            "same_customer_sales": [],
            "other_customer_sales": [],
            "quotation_rates": [],
            "purchase_rates": [],
            "valuation_rate": 0
        }

        # ==========================================================
        # 1. SAME CUSTOMER SALES
        # ==========================================================

        same_customer = frappe.db.sql("""
            SELECT
                sii.parent,
                si.customer,
                sii.rate,
                sii.creation
            FROM `tabSales Invoice Item` sii
            INNER JOIN `tabSales Invoice` si
                ON si.name = sii.parent
            WHERE
                sii.item_code = %(item_code)s
                AND si.customer = %(customer)s
                AND si.docstatus = 1
            ORDER BY sii.creation DESC
            LIMIT 5
        """, {
            "item_code": item_code,
            "customer": customer
        }, as_dict=True)

        result[item_code]["same_customer_sales"] = same_customer

        # ==========================================================
        # 2. OTHER CUSTOMER SALES
        # ==========================================================

        other_customer = frappe.db.sql("""
            SELECT
                sii.parent,
                si.customer,
                sii.rate,
                sii.creation
            FROM `tabSales Invoice Item` sii
            INNER JOIN `tabSales Invoice` si
                ON si.name = sii.parent
            WHERE
                sii.item_code = %(item_code)s
                AND si.customer != %(customer)s
                AND si.docstatus = 1
            ORDER BY sii.creation DESC
            LIMIT 5
        """, {
            "item_code": item_code,
            "customer": customer
        }, as_dict=True)

        result[item_code]["other_customer_sales"] = other_customer

        # ==========================================================
        # 3. QUOTATION RATES
        # ==========================================================

        quotation_rates = frappe.db.sql("""
            SELECT
                qi.parent,
                q.party_name as customer,
                qi.rate,
                qi.creation
            FROM `tabQuotation Item` qi
            INNER JOIN `tabQuotation` q
                ON q.name = qi.parent
            WHERE
                qi.item_code = %(item_code)s
                AND q.party_name = %(customer)s
                AND q.quotation_to = 'Customer'
                AND q.docstatus = 1
            ORDER BY qi.creation DESC
            LIMIT 5
        """, {
            "item_code": item_code,
            "customer": customer
        }, as_dict=True)

        result[item_code]["quotation_rates"] = quotation_rates

        # ==========================================================
        # 4. PURCHASE RATES
        # ==========================================================

        purchase_rates = frappe.db.sql("""
            SELECT
                pii.parent,
                pii.rate,
                pii.creation
            FROM `tabPurchase Invoice Item` pii
            INNER JOIN `tabPurchase Invoice` pi
                ON pi.name = pii.parent
            WHERE
                pii.item_code = %(item_code)s
                AND pi.docstatus = 1
            ORDER BY pii.creation DESC
            LIMIT 5
        """, {
            "item_code": item_code
        }, as_dict=True)

        result[item_code]["purchase_rates"] = purchase_rates

        # ==========================================================
        # 5. VALUATION RATE
        # ==========================================================

        valuation_rate = frappe.db.get_value(
            "Item",
            item_code,
            "valuation_rate"
        ) or 0

        result[item_code]["valuation_rate"] = valuation_rate

    return result