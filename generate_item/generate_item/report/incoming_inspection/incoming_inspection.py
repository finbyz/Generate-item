# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    conditions = get_conditions(filters)
    data = get_data(conditions, filters)
    return columns, data

def get_columns():
    return [
        {"label": _("Site"),                  "fieldname": "branch",            "fieldtype": "Data",       "width": 100},
        {"label": _("GRN No"),                "fieldname": "pr_name",           "fieldtype": "Link",       "options": "Purchase Receipt", "width": 120},
        {"label": _("GRN Date"),              "fieldname": "pr_date",           "fieldtype": "Date",       "width": 100},
        {"label": _("PO No"),                 "fieldname": "po_name",           "fieldtype": "Link",       "options": "Purchase Order",   "width": 120},
        {"label": _("PO Position"),           "fieldname": "po_line",           "fieldtype": "Data",       "width": 90},
        {"label": _("PO Date"),               "fieldname": "po_date",           "fieldtype": "Date",       "width": 100},
        {"label": _("Supplier Name"),         "fieldname": "supplier",          "fieldtype": "Data",       "width": 180},
        {"label": _("Batch no"),              "fieldname": "custom_batch_no",   "fieldtype": "Data",       "width": 120},
        {"label": _("Item Description"),      "fieldname": "description",       "fieldtype": "Small Text", "width": 200},
        {"label": _("INV- No"),               "fieldname": "bill_no",           "fieldtype": "Data",       "width": 120},
        {"label": _("Bill Date"),             "fieldname": "bill_date",         "fieldtype": "Date",       "width": 100},
        {"label": _("UOM"),                   "fieldname": "stock_uom",         "fieldtype": "Data",       "width": 80},
        {"label": _("Receipt QTY"),           "fieldname": "received_stock_qty","fieldtype": "Float",      "width": 100},
        {"label": _("Approved QTY"),          "fieldname": "approved_qty",      "fieldtype": "Float",      "width": 100},
        {"label": _("Heat No & Batch No."),   "fieldname": "heat_no",           "fieldtype": "Data",       "width": 150},
        {"label": _("MTC STATUS"),            "fieldname": "mtc_status",        "fieldtype": "Data",       "width": 130},
        {"label": _("MTC Remark"),            "fieldname": "mtc_remark",        "fieldtype": "Small Text", "width": 150},
        {"label": _("PMI STATUS"),            "fieldname": "pmi_status",        "fieldtype": "Data",       "width": 100},
        {"label": _("TOTAL NC QTY."),         "fieldname": "total_rejected_qty","fieldtype": "Float",      "width": 100},
        {"label": _("NCR NO"),                "fieldname": "ncr_no",            "fieldtype": "Data",       "width": 120},
        {"label": _("REMARK"),                "fieldname": "qi_remarks",        "fieldtype": "Data",       "width": 150},
        {"label": _("INSPECTION BY"),         "fieldname": "inspected_by",      "fieldtype": "Data",       "width": 120},
        {"label": _("INSPECTION DATE"),       "fieldname": "inspection_date",   "fieldtype": "Date",       "width": 120},
        # hidden carrier for save — not visible but needed for JS key
        {"label": _("QI Name"),               "fieldname": "qi_name",           "fieldtype": "Data",       "width": 0, "hidden": 1},
    ]

def get_conditions(filters):
    conditions = []
    if filters.get("from_date"): conditions.append("pr.posting_date >= %(from_date)s")
    if filters.get("to_date"):   conditions.append("pr.posting_date <= %(to_date)s")
    if filters.get("supplier"):  conditions.append("pr.supplier = %(supplier)s")
    if filters.get("branch"):    conditions.append("pr.branch = %(branch)s")
    return " AND ".join(conditions) if conditions else "1=1"

def get_data(conditions, filters):

	

	query = f"""
		SELECT
			pr.branch,
			pr.name as pr_name,
			pr.posting_date as pr_date,
			pri.purchase_order as po_name,
			pri.po_line_no as po_line,
			po.transaction_date as po_date,
			pr.supplier ,
			hn.heat_no as heat_no,
			pri.custom_batch_no,
			pri.description,
			pr.bill_no,
			pr.bill_date,
			pri.stock_uom,
			pri.received_stock_qty,
			pri.stock_qty as approved_qty,
			# qi.name as qi_name,
			qi.mtc_status as mtc_status,
			qi.mtc_remark as mtc_remark,
			qi.pmi_status as pmi_status,
			qi.ncr_no as ncr_no,
			qi.remarks as qi_remarks,
			qi.name as qi_name,
			
			qi.rejected_qty_in_stock_uom as total_rejected_qty,
			
			qi.inspected_by,
			qi.creation as inspection_date
		FROM
			`tabQuality Inspection` qi
		INNER JOIN 
			`tabQuality Inspection Heat No` hn ON hn.parent = qi.name
		INNER JOIN
			`tabPurchase Receipt Item` pri ON pri.parent = qi.reference_name 
			AND pri.name = qi.child_row_reference
		INNER JOIN
			`tabPurchase Receipt` pr ON pr.name = pri.parent
		LEFT JOIN
			`tabPurchase Order` po ON po.name = pri.purchase_order
		
		WHERE
			qi.docstatus != 2
			AND pr.docstatus != 2
			AND {conditions}

		ORDER BY
			pr.posting_date DESC,
			qi.name DESC
		
	"""

	return frappe.db.sql(query, filters, as_dict=True)


@frappe.whitelist()
def update_inspection_row(qi_name, mtc_status=None, mtc_remark=None,
                          pmi_status=None, ncr_no=None):
    """
    Direct SQL UPDATE on tabQuality Inspection.
    Works even on submitted (docstatus=1) documents.
    Only updates fields that are explicitly passed (not None).
    """


    # ── Verify document exists ────────────────────────────────────────────────
    exists = frappe.db.sql(
        "SELECT name, docstatus FROM `tabQuality Inspection` WHERE name = %s",
        qi_name, as_dict=True
    )
    if not exists:
        frappe.throw(_("Quality Inspection {0} not found").format(qi_name))

    # ── Build SET clause dynamically (only non-None fields) ──────────────────
    allowed_fields = {
        "mtc_status":  mtc_status,
        "mtc_remark":  mtc_remark,
        "pmi_status":  pmi_status,
        "ncr_no":      ncr_no,
      
    }

    set_parts  = []
    set_values = []

    for db_field, value in allowed_fields.items():
        if value is not None:              # only update fields that were sent
            set_parts.append(f"`{db_field}` = %s")
            set_values.append(value)

	# ── MTC Received checkbox logic ───────────────────────────────────────────
    # Only touch the checkbox when mtc_status is being updated
    if mtc_status is not None:
        if mtc_status == "RECEIVED IN MTC FOLDER":
            set_parts.append("`mtc_received` = %s")
            set_values.append(1)                      # check
        elif mtc_status == "MTC NOT RECEIVED":
            set_parts.append("`mtc_received` = %s")
            set_values.append(0)


    if not set_parts:
        return {"status": "nothing_to_update"}

    # ── Always stamp modified / modified_by ───────────────────────────────────
    set_parts.append("`modified` = NOW()")
    set_parts.append("`modified_by` = %s")
    set_values.append(frappe.session.user)

    # ── Final values list: SET values + WHERE value ───────────────────────────
    set_values.append(qi_name)

    sql = f"""
        UPDATE `tabQuality Inspection`
        SET    {', '.join(set_parts)}
        WHERE  name = %s
    """

    frappe.db.sql(sql, set_values)
    frappe.db.commit()

    return {"status": "ok", "updated": qi_name}