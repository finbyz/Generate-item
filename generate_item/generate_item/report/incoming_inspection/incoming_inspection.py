# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
    filters = frappe._dict(filters or {})
    columns = get_columns()
    conditions = get_conditions(filters)
    data = get_data(conditions, filters)
    return columns, data


def get_columns():
    return [
        {"label": _("Branch"),                "fieldname": "branch",             "fieldtype": "Data",       "width": 100},
        {"label": _("GRN No"),              "fieldname": "pr_name",            "fieldtype": "Link",       "options": "Purchase Receipt", "width": 120},
        {"label": _("GRN Date"),            "fieldname": "pr_date",            "fieldtype": "Date",       "width": 100},
        {"label": _("PO No"),               "fieldname": "po_name",            "fieldtype": "Link",       "options": "Purchase Order",   "width": 120},
        {"label": _("PO Position"),         "fieldname": "po_line",            "fieldtype": "Data",       "width": 90},
        {"label": _("PO Date"),             "fieldname": "po_date",            "fieldtype": "Date",       "width": 100},
        {"label": _("Supplier Name"),       "fieldname": "supplier",           "fieldtype": "Data",       "width": 180},
        {"label": _("Batch no"),            "fieldname": "custom_batch_no",    "fieldtype": "Data",       "width": 120},
        {"label": _("Item Description"),    "fieldname": "description",        "fieldtype": "Small Text", "width": 200},
        {"label": _("INV- No"),             "fieldname": "bill_no",            "fieldtype": "Data",       "width": 120},
        {"label": _("Bill Date"),           "fieldname": "bill_date",          "fieldtype": "Date",       "width": 100},
        {"label": _("UOM"),                 "fieldname": "stock_uom",          "fieldtype": "Data",       "width": 80},
        {"label": _("Receipt QTY"),         "fieldname": "received_stock_qty", "fieldtype": "Float",      "width": 100},
        {"label": _("Approved QTY"),        "fieldname": "approved_qty",       "fieldtype": "Float",      "width": 100},
        {"label": _("Heat No & Batch No."), "fieldname": "heat_no",            "fieldtype": "Data",       "width": 150},
        {"label": _("MTC STATUS"),          "fieldname": "mtc_status",         "fieldtype": "Data",       "width": 130},
        {"label": _("MTC Last Updated On"), "fieldname": "mtc_last_updated",   "fieldtype": "Datetime",   "width": 150},
        {"label": _("MTC Remark"),          "fieldname": "mtc_remark",         "fieldtype": "Small Text", "width": 150},
        {"label": _("PMI STATUS"),          "fieldname": "pmi_status",         "fieldtype": "Data",       "width": 100},
        {"label": _("TOTAL NC QTY."),       "fieldname": "total_rejected_qty", "fieldtype": "Float",      "width": 100},
        {"label": _("NCR NO"),              "fieldname": "ncr_no",             "fieldtype": "Data",       "width": 120},
        {"label": _("REMARK"),              "fieldname": "qi_remarks",         "fieldtype": "Data",       "width": 150},
        {"label": _("INSPECTION BY"),       "fieldname": "inspected_by",       "fieldtype": "Data",       "width": 120},
        {"label": _("INSPECTION DATE"),     "fieldname": "inspection_date",    "fieldtype": "Date",       "width": 120},
        # hidden carrier for save, not visible but needed for JS key
        {"label": _("QI Name"),             "fieldname": "qi_name",            "fieldtype": "Data",       "width": 0, "hidden": 1},
    ]


# Whitelist maps, so column names never come from raw user input
DATE_FIELD_MAP = {
    "GRN Date":        "DATE(pr.posting_date)",
    "Creation Date":   "DATE(qi.report_date)",   # Quality Inspection posting date
    "Submission Date": "DATE(qi.modified)",      # only for submitted QIs
}

ORDER_FIELD_MAP = {
    "GRN Date":        "pr.posting_date",
    "Creation Date":   "qi.report_date",
    "Submission Date": "qi.modified",
}

BULK_UPDATE_SELECT_OPTIONS = {
    "mtc_status": {
        "RT PENDING",
        "RECEIVED IN MTC FOLDER",
        "MTC NOT RECEIVED",
        "MTC CORRCTION",
        "TRIM PART MTC PENDING IGC PENDING",
        "UPLOADED IN DMS",
    },
    "pmi_status": {"YES", "NO"},
}


def get_conditions(filters):
    conditions = []

    date_based_on = filters.get("date_based_on") or "GRN Date"
    date_field = DATE_FIELD_MAP.get(date_based_on, DATE_FIELD_MAP["GRN Date"])

    if filters.get("from_date"):
        conditions.append(f"{date_field} >= %(from_date)s")
    if filters.get("to_date"):
        conditions.append(f"{date_field} <= %(to_date)s")

    # a QI that is not submitted has no submission date
    if date_based_on == "Submission Date":
        conditions.append("qi.docstatus = 1")

    if filters.get("supplier"):
        conditions.append("pr.supplier = %(supplier)s")
    if filters.get("branch"):
        conditions.append("pr.branch = %(branch)s")

    return " AND ".join(conditions) if conditions else "1=1"


def get_data(conditions, filters):
    order_field = ORDER_FIELD_MAP.get(
        filters.get("date_based_on") or "GRN Date", "pr.posting_date"
    )

    query = f"""
        SELECT
            pr.branch,
            pr.name AS pr_name,
            pr.posting_date AS pr_date,
            pri.purchase_order AS po_name,
            pri.po_line_no AS po_line,
            po.transaction_date AS po_date,
            pr.supplier,
            GROUP_CONCAT(DISTINCT hn.heat_no ORDER BY hn.idx SEPARATOR ', ') AS heat_no,
            pri.custom_batch_no,
            pri.description,
            pr.bill_no,
            pr.bill_date,
            pri.stock_uom,
            pri.received_stock_qty,
            pri.stock_qty AS approved_qty,
            qi.mtc_status AS mtc_status,
            (
                SELECT MAX(h.modified_on)
                FROM `tabMTC Status History` h
                WHERE h.parent = qi.name
                  AND h.parenttype = 'Quality Inspection'
                  AND h.parentfield = 'mtc_status_history'
            ) AS mtc_last_updated,
            qi.mtc_remark AS mtc_remark,
            qi.pmi_status AS pmi_status,
            qi.ncr_no AS ncr_no,
            qi.remarks AS qi_remarks,
            qi.name AS qi_name,
            qi.rejected_qty_in_stock_uom AS total_rejected_qty,
            qi.inspected_by,
            qi.creation AS inspection_date
        FROM
            `tabQuality Inspection` qi
        LEFT JOIN
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
        GROUP BY
            qi.name
        ORDER BY
            {order_field} DESC,
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
    Logs a row in MTC Status History when mtc_status actually changes.
    """

    # Verify document exists and read the current MTC status
    exists = frappe.db.sql(
        "SELECT name, docstatus, mtc_status FROM `tabQuality Inspection` WHERE name = %s",
        qi_name, as_dict=True
    )
    if not exists:
        frappe.throw(_("Quality Inspection {0} not found").format(qi_name))

    if not frappe.has_permission("Quality Inspection", "write", doc=qi_name):
        frappe.throw(
            _("You do not have permission to update Quality Inspection {0}.").format(qi_name),
            frappe.PermissionError,
        )

    old_status = exists[0].mtc_status or ""

    # Build SET clause dynamically (only non-None fields)
    allowed_fields = {
        "mtc_status": mtc_status,
        "mtc_remark": mtc_remark,
        "pmi_status": pmi_status,
        "ncr_no":     ncr_no,
    }

    set_parts = []
    set_values = []

    for db_field, value in allowed_fields.items():
        if value is not None:
            set_parts.append(f"`{db_field}` = %s")
            set_values.append(value)

    # MTC Received checkbox logic (only when mtc_status is being updated)
    if mtc_status is not None:
        if mtc_status == "RECEIVED IN MTC FOLDER":
            set_parts.append("`mtc_received` = %s")
            set_values.append(1)
        elif mtc_status == "MTC NOT RECEIVED":
            set_parts.append("`mtc_received` = %s")
            set_values.append(0)

    if not set_parts:
        return {"status": "nothing_to_update"}

    # Parent `modified` is intentionally NOT stamped, because the
    # "Submission Date" filter reads qi.modified.
    set_values.append(qi_name)

    frappe.db.sql(
        f"""
        UPDATE `tabQuality Inspection`
        SET    {', '.join(set_parts)}
        WHERE  name = %s
        """,
        set_values,
    )

    # Log only when MTC status really changed
    if mtc_status is not None and (mtc_status or "") != old_status:
        log_mtc_status_change(qi_name, mtc_status)

    return {"status": "ok", "updated": qi_name}


def log_mtc_status_change(qi_name, new_status):
    """Append a row to the mtc_status_history child table of the Quality Inspection."""
    idx = frappe.db.count(
        "MTC Status History",
        {
            "parent": qi_name,
            "parenttype": "Quality Inspection",
            "parentfield": "mtc_status_history",
        },
    ) + 1

    frappe.get_doc({
        "doctype": "MTC Status History",
        "parent": qi_name,
        "parenttype": "Quality Inspection",
        "parentfield": "mtc_status_history",
        "idx": idx,
        "mtc_status": new_status,
        "modified_by1": frappe.session.user,
        "modified_on": frappe.utils.now_datetime(),
    }).insert(ignore_permissions=True)


def _get_quality_inspections_for_receipt(purchase_receipt):
    if not isinstance(purchase_receipt, str) or not purchase_receipt:
        frappe.throw(_("Please select a valid Purchase Receipt."))
    if not frappe.db.exists("Purchase Receipt", purchase_receipt):
        frappe.throw(_("Please select a valid Purchase Receipt."))

    if not frappe.has_permission("Purchase Receipt", "read", doc=purchase_receipt):
        frappe.throw(_("You do not have permission to view Purchase Receipt {0}.").format(purchase_receipt),
                     frappe.PermissionError)
    if not frappe.has_permission("Quality Inspection", "read"):
        frappe.throw(_("You do not have permission to view Quality Inspections."), frappe.PermissionError)

    inspections = frappe.db.sql(
        """
        SELECT
            qi.name AS qi_name,
            qi.status,
            pri.purchase_order AS po_name
        FROM `tabQuality Inspection` qi
        INNER JOIN `tabPurchase Receipt Item` pri
            ON pri.parent = qi.reference_name
            AND pri.name = qi.child_row_reference
        INNER JOIN `tabPurchase Receipt` pr ON pr.name = pri.parent
        WHERE qi.reference_type = 'Purchase Receipt'
            AND qi.reference_name = %s
            AND qi.docstatus != 2
            AND pr.docstatus != 2
        ORDER BY qi.name
        """,
        purchase_receipt,
        as_dict=True,
    )
    return [
        inspection for inspection in inspections
        if frappe.has_permission("Quality Inspection", "read", doc=inspection.qi_name)
    ]


@frappe.whitelist()
def get_quality_inspections_for_receipt(purchase_receipt):
    return _get_quality_inspections_for_receipt(purchase_receipt)


@frappe.whitelist()
def bulk_update_inspection_rows(purchase_receipt, selected_qi_names, field_value_map):
    if isinstance(selected_qi_names, str):
        selected_qi_names = frappe.parse_json(selected_qi_names)
    if isinstance(field_value_map, str):
        field_value_map = frappe.parse_json(field_value_map)

    if not isinstance(selected_qi_names, list) or not selected_qi_names:
        frappe.throw(_("Select at least one Quality Inspection to update."))
    if any(not isinstance(qi_name, str) or not qi_name for qi_name in selected_qi_names):
        frappe.throw(_("Quality Inspection names must be valid document names."))
    if not isinstance(field_value_map, dict) or not field_value_map:
        frappe.throw(_("Provide at least one field value to update."))
    if any(not isinstance(fieldname, str) for fieldname in field_value_map):
        frappe.throw(_("Field names must be text."))

    allowed_fields = {"mtc_status", "mtc_remark", "pmi_status", "ncr_no"}
    invalid_fields = set(field_value_map) - allowed_fields
    if invalid_fields:
        frappe.throw(_("Unsupported fields: {0}").format(", ".join(sorted(invalid_fields))))

    for fieldname, value in field_value_map.items():
        if not isinstance(value, str):
            frappe.throw(_("The value for {0} must be text.").format(fieldname))
        if value and fieldname in BULK_UPDATE_SELECT_OPTIONS:
            if value not in BULK_UPDATE_SELECT_OPTIONS[fieldname]:
                frappe.throw(_("Invalid value for {0}.").format(fieldname))

    available_names = {
        row.qi_name for row in _get_quality_inspections_for_receipt(purchase_receipt)
    }
    selected_qi_names = list(dict.fromkeys(selected_qi_names))
    invalid_names = set(selected_qi_names) - available_names
    if invalid_names:
        frappe.throw(
            _("These Quality Inspections do not belong to Purchase Receipt {0}: {1}").format(
                purchase_receipt, ", ".join(sorted(invalid_names))
            )
        )

    for qi_name in selected_qi_names:
        update_inspection_row(qi_name, **field_value_map)

    return {"updated": len(selected_qi_names)}