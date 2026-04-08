# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": _("OMR No."), "fieldname": "omr_no", "fieldtype": "Link", "options": "Order Modification Request", "width": 120},
        {"label": _("Branch"), "fieldname": "branch", "fieldtype": "Data", "width": 100},
        {"label": _("OMR Date"), "fieldname": "omr_date", "fieldtype": "Date", "width": 100},
        {"label": _("Customer Name"), "fieldname": "customer_name", "fieldtype": "Data", "width": 150},
        {"label": _("OMR Status"), "fieldname": "omr_status", "fieldtype": "Data", "width": 120},
        {"label": _("Approved Date"), "fieldname": "approved_on", "fieldtype": "Date", "width": 100},
        {"label": _("Approved By"), "fieldname": "approved_by", "fieldtype": "Data", "width": 120},
        {"label": _("Reason for Change"), "fieldname": "reason_for_change", "fieldtype": "Small Text", "width": 150},
        {"label": _("Batch No Ref"), "fieldname": "batch_no", "fieldtype": "Data", "width": 120},
        {"label": _("Entry Type"), "fieldname": "entry_type", "fieldtype": "Data", "width": 130},
        {"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 150},
        {"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 150},
        {"label": _("Item Description"), "fieldname": "item_description", "fieldtype": "Text", "width": 200},
        {"label": _("Item Group"), "fieldname": "item_group", "fieldtype": "Data", "width": 100},
        {"label": _("Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 80},
        {"label": _("Item Remarks"), "fieldname": "item_remarks", "fieldtype": "Text", "width": 200},
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

def get_data(filters):
    conditions, values = get_conditions(filters)

    # Single optimized query:
    # - JOINs OMR + Items + Item master + Item Generator in one shot
    # - Filters modified items only at DB level:
    #     itm.item IS NOT NULL AND itm.item != ''   → original item must exist (not a new addition)
    #     itm.rev_item IS NOT NULL AND itm.rev_item != ''  → revised item must exist
    raw_rows = frappe.db.sql(f"""
        SELECT
            omr.name           AS omr_no,
            omr.branch         AS branch,
            DATE(omr.creation) AS omr_date,
            omr.customer_name  AS customer_name,
            omr.workflow_state AS omr_status,
            omr.reason_for_change AS reason_for_change,

            itm.batch_no       AS batch_no,
            itm.item           AS original_item,
            itm.rev_item       AS rev_item,
            itm.qty            AS qty,
            itm.rev_qty        AS rev_qty,
            itm.line_remark    AS line_remark,
            itm.rev_line_remark AS rev_line_remark,

            i.item_name        AS item_name,
            i.description      AS item_description,
            i.item_group       AS item_group,

            ig.attribute_1_value,  ig.attribute_2_value,  ig.attribute_3_value,
            ig.attribute_4_value,  ig.attribute_5_value,  ig.attribute_6_value,
            ig.attribute_7_value,  ig.attribute_8_value,  ig.attribute_9_value,
            ig.attribute_10_value, ig.attribute_11_value, ig.attribute_12_value,
            ig.attribute_13_value, ig.attribute_14_value, ig.attribute_15_value,
            ig.attribute_16_value, ig.attribute_17_value, ig.attribute_18_value,
            ig.attribute_19_value, ig.attribute_20_value, ig.attribute_21_value,
            ig.attribute_22_value, ig.attribute_23_value, ig.attribute_24_value

        FROM `tabOrder Modification Request` omr
        INNER JOIN `tabSales Order Item For OMR` itm
            ON itm.parent = omr.name
        LEFT JOIN `tabItem` i
            ON i.name = itm.rev_item
        LEFT JOIN `tabItem Generator` ig
            ON ig.name = itm.rev_item

        WHERE omr.docstatus IN (0, 1)
            AND itm.item      IS NOT NULL AND itm.item      != ''
            AND itm.rev_item  IS NOT NULL AND itm.rev_item  != ''
            {conditions}

        ORDER BY omr.creation DESC
    """, values=values, as_dict=True)

    # Fetch all approval details in one query (avoid N+1)
    omr_names = list({r.omr_no for r in raw_rows})
    approval_map = get_approval_details_bulk(omr_names)

    data = []
    for r in raw_rows:
        approval = approval_map.get(r.omr_no, {})
        final_qty    = flt(r.rev_qty) if flt(r.rev_qty) > 0 else flt(r.qty)
        final_remark = r.rev_line_remark if r.rev_line_remark else r.line_remark

        data.append({
            "omr_no":           r.omr_no,
            "branch":           r.branch,
            "omr_date":         r.omr_date,
            "customer_name":    r.customer_name,
            "omr_status":       r.omr_status,
            "approved_on":      approval.get("approved_on"),
            "approved_by":      approval.get("approved_by"),
            "reason_for_change": r.reason_for_change,
            "batch_no":         r.batch_no,
            "entry_type":       _("Item Modified"),   # always "Modified" since new additions are excluded
            "item_code":        r.rev_item,
            "item_name":        r.item_name,
            "item_description": r.item_description,
            "item_group":       r.item_group,
            "qty":              final_qty,
            "item_remarks":     final_remark,

            "type_of_product":               r.attribute_1_value,
            "valve_type":                    r.attribute_2_value,
            "construction":                  r.attribute_3_value,
            "bore":                          r.attribute_4_value,
            "size":                          r.attribute_5_value,
            "rating":                        r.attribute_6_value,
            "ends":                          r.attribute_7_value,
            "end_sub_type":                  r.attribute_8_value,
            "shell_moc":                     r.attribute_9_value,
            "ball_moc":                      r.attribute_10_value,
            "ball_facing":                   r.attribute_11_value,
            "seat_ring_guide_moc":           r.attribute_12_value,
            "seat_facing_plating":           r.attribute_13_value,
            "seat_insert_seat_seal_moc":     r.attribute_14_value,
            "stem_moc":                      r.attribute_15_value,
            "gasket":                        r.attribute_16_value,
            "gland_packing_o_ring_moc":      r.attribute_17_value,
            "fasteners":                     r.attribute_18_value,
            "operator":                      r.attribute_19_value,
            "accessories":                   r.attribute_20_value,
            "special_requirement_for_valve": r.attribute_21_value,
            "quality_special_requirement_nde": r.attribute_22_value,
            "service":                       r.attribute_23_value,
            "inspection":                    r.attribute_24_value,
        })

    return data


def get_conditions(filters):
    conditions = ""
    values = {}

    if filters.get("from_date") and filters.get("to_date"):
        conditions += " AND DATE(omr.creation) BETWEEN %(from_date)s AND %(to_date)s"
        values["from_date"] = filters.from_date
        values["to_date"]   = filters.to_date

    if filters.get("omr_number"):
        conditions += " AND omr.name = %(omr_number)s"
        values["omr_number"] = filters.omr_number

    if filters.get("customer"):
        conditions += " AND omr.customer_name LIKE %(customer)s"
        values["customer"] = f"%{filters.customer}%"

    if filters.get("branch"):
        conditions += " AND omr.branch = %(branch)s"
        values["branch"] = filters.branch

    if filters.get("status"):
        # MultiSelectList returns a list
        placeholders = ", ".join([f"%(status_{i})s" for i in range(len(filters.status))])
        conditions += f" AND omr.workflow_state IN ({placeholders})"
        for i, s in enumerate(filters.status):
            values[f"status_{i}"] = s

    return conditions, values


def get_approval_details_bulk(omr_names):
    """Fetch approval details for all OMRs in a single query instead of one per OMR."""
    if not omr_names:
        return {}

    placeholders = ", ".join([f"%(n{i})s" for i in range(len(omr_names))])
    values = {f"n{i}": name for i, name in enumerate(omr_names)}

    rows = frappe.db.sql(f"""
        SELECT parent, username AS approved_by, modification_time AS approved_on
        FROM `tabState Change Items`
        WHERE parent IN ({placeholders})
            AND parenttype = 'Order Modification Request'
            AND workflow_state = 'Approved'
        ORDER BY modification_time DESC
    """, values=values, as_dict=True)

    # Keep only the latest approval per OMR (DESC order, first-seen wins)
    approval_map = {}
    for row in rows:
        if row.parent not in approval_map:
            approval_map[row.parent] = {
                "approved_by": row.approved_by,
                "approved_on": row.approved_on,
            }

    return approval_map