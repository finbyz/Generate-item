# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

# import frappe



import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns()
	data    = get_data(filters)



	return columns, data


# ── Columns ───────────────────────────────────────────────────────────────────

def get_columns():
    return [
       
        {
            "label": _("Entry Date"),
            "fieldname": "entry_date",
            "fieldtype": "Date",
            "width": 110,
        },
		 {
            "label": _("Supplier Invoice No"),
            "fieldname": "supplier_invoice_no",
            "fieldtype": "Data",
            "width": 155,
        },
        {
            "label": _("Supplier Invoice Date"),
            "fieldname": "supplier_invoice_date",
            "fieldtype": "Date",
            "width": 145,
        },
        {
            "label": _("Size"),
            "fieldname": "size",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": _("Class"),
            "fieldname": "class_rating",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": _("Type"),
            "fieldname": "valve_type",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("Material"),
            "fieldname": "material",
            "fieldtype": "Data",
            "width": 160,
        },
        {
            "label": _("Part"),
            "fieldname": "part",
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "label": _("Heat No"),
            "fieldname": "heat_no",
            "fieldtype": "Data",
            "width": 130,
        },
        {
            "label": _("RT No"),
            "fieldname": "rt_no",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("Vendor Name"),
            "fieldname": "vendor_name",
            "fieldtype": "Link",
            "options": "Supplier",
            "width": 190,
        },
       
        {
            "label": _("Used"),
            "fieldname": "used",
            "fieldtype": "Data",
            
            "width": 200,
			#  "editable": 1 
        },
        {
            "label": _("Sale Order"),
            "fieldname": "sale_order",
            "fieldtype": "Link",
            "options": "Sales Order",
            "width": 150,
        },
        {
            "label": _("Remarks"),
            "fieldname": "remarks",
            "fieldtype": "Data",
            "width": 200,
        },
    ]


# ── Data query ────────────────────────────────────────────────────────────────

def get_data(filters):
    conditions = get_conditions(filters)

    data = frappe.db.sql(
        """
        SELECT
		    qi.name AS name,
		    hn.name AS heat_no_name,
            /* ENTRY DATE */
            qi.creation                     AS entry_date,

            /* SIZE / CLASS / TYPE / MATERIAL – Item Generator attributes */
            ig.attribute_5_value                AS size,
            ig.attribute_6_value                AS class_rating,
            ig.attribute_2_value                AS valve_type,
            ig.attribute_9_value                AS material,
			ig.attribute_3_value                   AS part,


            /* HEAT NO – one row per child record in tabheat_no */
            hn.heat_no                          AS heat_no,

         
            hn.rt_no                     AS rt_no,

            /* VENDOR NAME */
            pr.supplier                         AS vendor_name,

            /* SUPPLIER INVOICE NO / DATE – standard PR bill fields */
            pr.bill_no                          AS supplier_invoice_no,
            pr.bill_date                        AS supplier_invoice_date,

            /* USED – custom field on Quality Inspection */
            hn.used                      AS used,

            /* SALE ORDER – from Batch linked to a Sales Order */
            # b.reference_name                    AS sale_order,
			COALESCE(
					b1.reference_name,
					b2.reference_name
				) AS sale_order,

            /* REMARKS – custom field on Quality Inspection */
            qi.remarks                   AS remarks

        FROM `tabQuality Inspection` qi

        /* Heat No child table – INNER JOIN so only QIs with heat nos appear */
        INNER JOIN `tabQuality Inspection Heat No` hn
            ON  hn.parent     = qi.name
            AND hn.parenttype = 'Quality Inspection'

        /* PR line */
        INNER JOIN `tabPurchase Receipt Item` pri
            ON  pri.parent    = qi.reference_name
            AND pri.item_code = qi.item_code
          
        /* PR header */
        INNER JOIN `tabPurchase Receipt` pr
            ON  pr.name      = pri.parent
         

        /* Item Generator – SIZE / CLASS / TYPE / MATERIAL / PART */
        LEFT JOIN `tabItem Generator` ig
            ON ig.item_code = qi.item_code

        /* Batch linked to a Sales Order */
       /* 1️⃣ Batch directly from QC */
		LEFT JOIN `tabBatch` b1
			ON b1.name = qi.batch_no_ref

		/* 2️⃣ PR Item using child_row_reference */
		LEFT JOIN `tabPurchase Receipt Item` pri2
			ON pri2.name = qi.child_row_reference

		/* 3️⃣ Batch from PR Item */
		LEFT JOIN `tabBatch` b2
			ON b2.name = pri2.custom_batch_no

		

		

        WHERE
            qi.docstatus      != 2

            {conditions}

    
            
        """.format(conditions=conditions),
        filters,
        as_dict=True,
    )

    return data


# ── Filter conditions ─────────────────────────────────────────────────────────

def get_conditions(filters):
	conditions = []

	if not filters:
		return ""

	if filters.get("company"):
		conditions.append("AND pr.company = %(company)s")

	if filters.get("branch"):
		conditions.append("AND pr.branch = %(branch)s")

	if filters.get("supplier"):
		conditions.append("AND pr.supplier = %(supplier)s")

	if filters.get("from_date"):
		conditions.append("AND pr.posting_date >= %(from_date)s")

	if filters.get("to_date"):
		conditions.append("AND pr.posting_date <= %(to_date)s")

	if filters.get("purchase_receipt"):
		conditions.append("AND pr.name = %(purchase_receipt)s")

	if filters.get("purchase_order"):
		conditions.append("AND pri.purchase_order = %(purchase_order)s")

	if filters.get("item_code"):
		conditions.append("AND qi.item_code = %(item_code)s")

	if filters.get("sales_order"):
		conditions.append("""
			AND (
				b1.reference_name = %(sales_order)s OR
				b2.reference_name = %(sales_order)s
			)
		""")
		


	return " ".join(conditions)


@frappe.whitelist()
def update_heat_no(name, used):
    """
    Direct SQL UPDATE on tabQuality Inspection Heat No child table.
    Works even on submitted parent documents.
    """

    # ── Verify row exists ─────────────────────────────────────────────────────
    exists = frappe.db.sql(
        "SELECT name FROM `tabQuality Inspection Heat No` WHERE name = %s",
        name, as_dict=True
    )
    if not exists:
        frappe.throw(_("Heat No record {0} not found").format(name))

 

    # ── Update + stamp modified ───────────────────────────────────────────────
    frappe.db.sql("""
        UPDATE `tabQuality Inspection Heat No`
        SET    used        = %s,
               modified    = NOW(),
               modified_by = %s
        WHERE  name = %s
    """, (used, frappe.session.user, name))

    frappe.db.commit()

    return {"status": "ok", "updated": name}

