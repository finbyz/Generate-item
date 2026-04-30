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
        {"label": _("OMR Line No"), "fieldname": "omr_line_no", "fieldtype": "Data", "width": 100},
        
        # PO Line No
        {"label": _("PO Line No"), "fieldname": "original_po_line_no", "fieldtype": "Data", "width": 100},
        {"label": _("Revised PO Line No"), "fieldname": "revised_po_line_no", "fieldtype": "Data", "width": 100},
        
        # Tag No
        {"label": _("Tag No"), "fieldname": "original_tag_no", "fieldtype": "Data", "width": 120},
        {"label": _("Revised Tag No"), "fieldname": "revised_tag_no", "fieldtype": "Data", "width": 120},
        
        # Delivery Date
        {"label": _("Delivery Date"), "fieldname": "original_delivery_date", "fieldtype": "Date", "width": 100},
        {"label": _("Revised Delivery Date"), "fieldname": "revised_delivery_date", "fieldtype": "Date", "width": 100},
        
        # Line Remark
        {"label": _("Line Remark"), "fieldname": "original_line_remark", "fieldtype": "Text", "width": 200},
        {"label": _("Revised Line Remark"), "fieldname": "revised_line_remark", "fieldtype": "Text", "width": 200},
        
        # Component Of
        {"label": _("Component Of"), "fieldname": "original_component_of", "fieldtype": "Data", "width": 120},
        {"label": _("Revised Component Of"), "fieldname": "revised_component_of", "fieldtype": "Data", "width": 120},
        
        # Shipping Address
        {"label": _("Shipping Address"), "fieldname": "original_shipping_address", "fieldtype": "Data", "width": 150},
        {"label": _("Revised Shipping Address"), "fieldname": "revised_shipping_address", "fieldtype": "Data", "width": 150},
        
        # Line Status
        {"label": _("Line Status"), "fieldname": "original_line_status", "fieldtype": "Data", "width": 100},
        {"label": _("Revised Line Status"), "fieldname": "revised_line_status", "fieldtype": "Data", "width": 100},
        
        # Is Free Item
        {"label": _("Is Free Item"), "fieldname": "original_is_free_item", "fieldtype": "Check", "width": 80},
        {"label": _("Revised Is Free Item"), "fieldname": "revised_is_free_item", "fieldtype": "Check", "width": 80},
        
        # Qty
        {"label": _("Qty"), "fieldname": "original_qty", "fieldtype": "Float", "width": 80},
        {"label": _("Revised Qty"), "fieldname": "revised_qty", "fieldtype": "Float", "width": 80},
        
        # Rate
        {"label": _("Rate"), "fieldname": "original_rate", "fieldtype": "Currency", "width": 100},
        {"label": _("Revised Rate"), "fieldname": "revised_rate", "fieldtype": "Currency", "width": 100},
        
        # Item Code (Original & Revised)
        {"label": _("Item Code"), "fieldname": "original_item_code", "fieldtype": "Link", "options": "Item", "width": 150},
        {"label": _("Revised Item Code"), "fieldname": "revised_item_code", "fieldtype": "Link", "options": "Item", "width": 150},
        
        # Item Name
        {"label": _("Item Name"), "fieldname": "original_item_name", "fieldtype": "Data", "width": 150},
        {"label": _("Revised Item Name"), "fieldname": "revised_item_name", "fieldtype": "Data", "width": 150},
        
        # Item Description
        {"label": _("Item Description"), "fieldname": "original_item_description", "fieldtype": "Text", "width": 200},
        {"label": _("Revised Item Description"), "fieldname": "revised_item_description", "fieldtype": "Text", "width": 200},
        
        # Item Group
        {"label": _("Item Group"), "fieldname": "original_item_group", "fieldtype": "Data", "width": 100},
        {"label": _("Revised Item Group"), "fieldname": "revised_item_group", "fieldtype": "Data", "width": 100},
        
        # Type of Product
        {"label": _("Type of Product"), "fieldname": "original_type_of_product", "fieldtype": "Data", "width": 120},
        {"label": _("Revised Type of Product"), "fieldname": "revised_type_of_product", "fieldtype": "Data", "width": 120},
        
        # Valve Type
        {"label": _("Valve Type"), "fieldname": "original_valve_type", "fieldtype": "Data", "width": 120},
        {"label": _("Revised Valve Type"), "fieldname": "revised_valve_type", "fieldtype": "Data", "width": 120},
        
        # Construction
        {"label": _("Construction"), "fieldname": "original_construction", "fieldtype": "Data", "width": 100},
        {"label": _("Revised Construction"), "fieldname": "revised_construction", "fieldtype": "Data", "width": 100},
        
        # Bore
        {"label": _("Bore"), "fieldname": "original_bore", "fieldtype": "Data", "width": 80},
        {"label": _("Revised Bore"), "fieldname": "revised_bore", "fieldtype": "Data", "width": 80},
        
        # Size
        {"label": _("Size"), "fieldname": "original_size", "fieldtype": "Data", "width": 80},
        {"label": _("Revised Size"), "fieldname": "revised_size", "fieldtype": "Data", "width": 80},
        
        # Rating
        {"label": _("Rating"), "fieldname": "original_rating", "fieldtype": "Data", "width": 80},
        {"label": _("Revised Rating"), "fieldname": "revised_rating", "fieldtype": "Data", "width": 80},
        
        # Ends
        {"label": _("Ends"), "fieldname": "original_ends", "fieldtype": "Data", "width": 80},
        {"label": _("Revised Ends"), "fieldname": "revised_ends", "fieldtype": "Data", "width": 80},
        
        # End Sub type
        {"label": _("End Sub type"), "fieldname": "original_end_sub_type", "fieldtype": "Data", "width": 100},
        {"label": _("Revised End Sub type"), "fieldname": "revised_end_sub_type", "fieldtype": "Data", "width": 100},
        
        # Shell MOC
        {"label": _("Shell MOC"), "fieldname": "original_shell_moc", "fieldtype": "Data", "width": 100},
        {"label": _("Revised Shell MOC"), "fieldname": "revised_shell_moc", "fieldtype": "Data", "width": 100},
        
        # Ball Moc
        {"label": _("Ball Moc"), "fieldname": "original_ball_moc", "fieldtype": "Data", "width": 100},
        {"label": _("Revised Ball Moc"), "fieldname": "revised_ball_moc", "fieldtype": "Data", "width": 100},
        
        # Ball Facing
        {"label": _("Ball Facing"), "fieldname": "original_ball_facing", "fieldtype": "Data", "width": 100},
        {"label": _("Revised Ball Facing"), "fieldname": "revised_ball_facing", "fieldtype": "Data", "width": 100},
        
        # Seat Ring(GUIDE) MOC
        {"label": _("Seat Ring(GUIDE) MOC"), "fieldname": "original_seat_ring_guide_moc", "fieldtype": "Data", "width": 120},
        {"label": _("Revised Seat Ring(GUIDE) MOC"), "fieldname": "revised_seat_ring_guide_moc", "fieldtype": "Data", "width": 120},
        
        # Seat Facing/Plating
        {"label": _("Seat Facing/Plating"), "fieldname": "original_seat_facing_plating", "fieldtype": "Data", "width": 120},
        {"label": _("Revised Seat Facing/Plating"), "fieldname": "revised_seat_facing_plating", "fieldtype": "Data", "width": 120},
        
        # SEAT INSERT + SEAT SEAL MOC
        {"label": _("SEAT INSERT + SEAT SEAL MOC"), "fieldname": "original_seat_insert_seat_seal_moc", "fieldtype": "Data", "width": 150},
        {"label": _("Revised SEAT INSERT + SEAT SEAL MOC"), "fieldname": "revised_seat_insert_seat_seal_moc", "fieldtype": "Data", "width": 150},
        
        # Stem MOC
        {"label": _("Stem MOC"), "fieldname": "original_stem_moc", "fieldtype": "Data", "width": 100},
        {"label": _("Revised Stem MOC"), "fieldname": "revised_stem_moc", "fieldtype": "Data", "width": 100},
        
        # GASKET
        {"label": _("GASKET"), "fieldname": "original_gasket", "fieldtype": "Data", "width": 100},
        {"label": _("Revised GASKET"), "fieldname": "revised_gasket", "fieldtype": "Data", "width": 100},
        
        # Gland Packing + O'Ring Moc
        {"label": _("Gland Packing + O'Ring Moc"), "fieldname": "original_gland_packing_o_ring_moc", "fieldtype": "Data", "width": 150},
        {"label": _("Revised Gland Packing + O'Ring Moc"), "fieldname": "revised_gland_packing_o_ring_moc", "fieldtype": "Data", "width": 150},
        
        # Fasteners
        {"label": _("Fasteners"), "fieldname": "original_fasteners", "fieldtype": "Data", "width": 100},
        {"label": _("Revised Fasteners"), "fieldname": "revised_fasteners", "fieldtype": "Data", "width": 100},
        
        # Operator
        {"label": _("Operator"), "fieldname": "original_operator", "fieldtype": "Data", "width": 100},
        {"label": _("Revised Operator"), "fieldname": "revised_operator", "fieldtype": "Data", "width": 100},
        
        # Accessories
        {"label": _("Accessories"), "fieldname": "original_accessories", "fieldtype": "Data", "width": 120},
        {"label": _("Revised Accessories"), "fieldname": "revised_accessories", "fieldtype": "Data", "width": 120},
        
        # Special Requirement for valve
        {"label": _("Special Requirement for valve"), "fieldname": "original_special_requirement_for_valve", "fieldtype": "Data", "width": 150},
        {"label": _("Revised Special Requirement for valve"), "fieldname": "revised_special_requirement_for_valve", "fieldtype": "Data", "width": 150},
        
        # QUALITY Special Requirement (NDE)
        {"label": _("QUALITY Special Requirement (NDE)"), "fieldname": "original_quality_special_requirement_nde", "fieldtype": "Data", "width": 150},
        {"label": _("Revised QUALITY Special Requirement (NDE)"), "fieldname": "revised_quality_special_requirement_nde", "fieldtype": "Data", "width": 150},
        
        # Service
        {"label": _("Service"), "fieldname": "original_service", "fieldtype": "Data", "width": 100},
        {"label": _("Revised Service"), "fieldname": "revised_service", "fieldtype": "Data", "width": 100},
        
        # Inspection
        {"label": _("Inspection"), "fieldname": "original_inspection", "fieldtype": "Data", "width": 100},
        {"label": _("Revised Inspection"), "fieldname": "revised_inspection", "fieldtype": "Data", "width": 100},
    ]

def get_data(filters):
    conditions, values = get_conditions(filters)

    # Main query using Sales Order Item For OMR table for comparison
    raw_rows = frappe.db.sql(f"""
        SELECT
            omr.name           AS omr_no,
            omr.branch         AS branch,
            DATE(omr.creation) AS omr_date,
            omr.customer_name  AS customer_name,
            omr.workflow_state AS omr_status,
            omr.reason_for_change AS reason_for_change,

            itm.batch_no        AS batch_no,
            itm.idx             AS omr_line_no,
            itm.item            AS original_item,
            itm.rev_item        AS rev_item,
            
            -- Original values from Sales Order Item For OMR
            itm.qty             AS original_qty,
            itm.rate            AS original_rate,
            itm.po_line_no      AS original_po_line_no,
            itm.tag_no           AS original_tag_no,
            itm.delivery_date   AS original_delivery_date,
            itm.line_remark     AS original_line_remark,
            itm.line_status     AS original_line_status,
            itm.is_free_item    AS original_is_free_item,
            
            -- Revised values from Sales Order Item For OMR
            itm.rev_qty         AS revised_qty,
            itm.rev_rate        AS revised_rate,
            itm.rev_po_line_no      AS revised_po_line_no,
            itm.rev_tag_no           AS revised_tag_no,
            itm.rev_line_status AS revised_line_status,
            itm.rev_is_free_item AS revised_is_free_item,
            itm.rev_delivery_date   AS revised_delivery_date,
            itm.rev_line_remark     AS revised_line_remark,
            
           
            
            -- Original Item details
            orig_i.item_name        AS original_item_name,
            orig_i.description      AS original_item_description,
            orig_i.item_group       AS original_item_group,

            -- Original Item Generator attributes
            orig_ig.attribute_1_value  AS orig_attr_1,  
            orig_ig.attribute_2_value  AS orig_attr_2,  
            orig_ig.attribute_3_value  AS orig_attr_3,
            orig_ig.attribute_4_value  AS orig_attr_4,  
            orig_ig.attribute_5_value  AS orig_attr_5,  
            orig_ig.attribute_6_value  AS orig_attr_6,
            orig_ig.attribute_7_value  AS orig_attr_7,  
            orig_ig.attribute_8_value  AS orig_attr_8,  
            orig_ig.attribute_9_value  AS orig_attr_9,
            orig_ig.attribute_10_value AS orig_attr_10, 
            orig_ig.attribute_11_value AS orig_attr_11, 
            orig_ig.attribute_12_value AS orig_attr_12,
            orig_ig.attribute_13_value AS orig_attr_13, 
            orig_ig.attribute_14_value AS orig_attr_14, 
            orig_ig.attribute_15_value AS orig_attr_15,
            orig_ig.attribute_16_value AS orig_attr_16, 
            orig_ig.attribute_17_value AS orig_attr_17, 
            orig_ig.attribute_18_value AS orig_attr_18,
            orig_ig.attribute_19_value AS orig_attr_19, 
            orig_ig.attribute_20_value AS orig_attr_20, 
            orig_ig.attribute_21_value AS orig_attr_21,
            orig_ig.attribute_22_value AS orig_attr_22, 
            orig_ig.attribute_23_value AS orig_attr_23, 
            orig_ig.attribute_24_value AS orig_attr_24,

            -- Revised Item details (only if rev_item is different from item)
            rev_i.item_name        AS revised_item_name,
            rev_i.description      AS revised_item_description,
            rev_i.item_group       AS revised_item_group,

            -- Revised Item Generator attributes (only if rev_item is different from item)
            rev_ig.attribute_1_value  AS rev_attr_1,  
            rev_ig.attribute_2_value  AS rev_attr_2,  
            rev_ig.attribute_3_value  AS rev_attr_3,
            rev_ig.attribute_4_value  AS rev_attr_4,  
            rev_ig.attribute_5_value  AS rev_attr_5,  
            rev_ig.attribute_6_value  AS rev_attr_6,
            rev_ig.attribute_7_value  AS rev_attr_7,  
            rev_ig.attribute_8_value  AS rev_attr_8,  
            rev_ig.attribute_9_value  AS rev_attr_9,
            rev_ig.attribute_10_value AS rev_attr_10, 
            rev_ig.attribute_11_value AS rev_attr_11, 
            rev_ig.attribute_12_value AS rev_attr_12,
            rev_ig.attribute_13_value AS rev_attr_13, 
            rev_ig.attribute_14_value AS rev_attr_14, 
            rev_ig.attribute_15_value AS rev_attr_15,
            rev_ig.attribute_16_value AS rev_attr_16, 
            rev_ig.attribute_17_value AS rev_attr_17, 
            rev_ig.attribute_18_value AS rev_attr_18,
            rev_ig.attribute_19_value AS rev_attr_19, 
            rev_ig.attribute_20_value AS rev_attr_20, 
            rev_ig.attribute_21_value AS rev_attr_21,
            rev_ig.attribute_22_value AS rev_attr_22, 
            rev_ig.attribute_23_value AS rev_attr_23, 
            rev_ig.attribute_24_value AS rev_attr_24

        FROM `tabOrder Modification Request` omr
        INNER JOIN `tabSales Order Item For OMR` itm
            ON itm.parent = omr.name

        -- Join Original Item master
        LEFT JOIN `tabItem` orig_i
            ON orig_i.name = itm.item

        -- Join Original Item Generator
        LEFT JOIN `tabItem Generator` orig_ig
            ON orig_ig.name = itm.item

        -- Join Revised Item master (only if rev_item exists and is different from item)
        LEFT JOIN `tabItem` rev_i
            ON rev_i.name = itm.rev_item
            AND itm.rev_item IS NOT NULL 
            AND itm.rev_item != ''
            AND itm.rev_item != itm.item

        -- Join Revised Item Generator (only if rev_item exists and is different from item)
        LEFT JOIN `tabItem Generator` rev_ig
            ON rev_ig.name = itm.rev_item
            AND itm.rev_item IS NOT NULL 
            AND itm.rev_item != ''
            AND itm.rev_item != itm.item

        WHERE omr.docstatus IN (0, 1)
            {conditions}

        ORDER BY omr.creation DESC, itm.idx ASC
    """, values=values, as_dict=True)

    # Fetch all approval details in one query (avoid N+1)
    omr_names = list({r.omr_no for r in raw_rows})
    approval_map = get_approval_details_bulk(omr_names)

    # Attribute field mapping
    attr_fields = [
        "type_of_product", "valve_type", "construction", "bore", "size", "rating",
        "ends", "end_sub_type", "shell_moc", "ball_moc", "ball_facing",
        "seat_ring_guide_moc", "seat_facing_plating", "seat_insert_seat_seal_moc",
        "stem_moc", "gasket", "gland_packing_o_ring_moc", "fasteners", "operator",
        "accessories", "special_requirement_for_valve", "quality_special_requirement_nde",
        "service", "inspection"
    ]

    data = []
    for r in raw_rows:
        original_item = r.get("original_item")
        rev_item = r.get("rev_item")

        # Determine if item was changed
        item_changed = False
        if rev_item and rev_item != original_item:
            item_changed = True

        # Determine entry type
        entry_type = ""
        if item_changed:
            entry_type = _("Item Modified")
        elif rev_item and not original_item:
            entry_type = _("New Item Added")
        

        approval = approval_map.get(r.omr_no, {})

        # Build the row with original and revised values
        row = {
            "omr_no": r.omr_no,
            "branch": r.branch,
            "omr_date": r.omr_date,
            "customer_name": r.customer_name,
            "omr_status": r.omr_status,
            "approved_on": approval.get("approved_on"),
            "approved_by": approval.get("approved_by"),
            "reason_for_change": r.reason_for_change,
            "batch_no": r.batch_no,
            "entry_type": entry_type,
            "omr_line_no": r.omr_line_no,
            
            # PO Line No
            "original_po_line_no": r.original_po_line_no,
            "revised_po_line_no": r.revised_po_line_no, 
            
            # Tag No
            "original_tag_no": r.original_tag_no,
            "revised_tag_no": r.revised_tag_no,  
            
            # Delivery Date
            "original_delivery_date": r.original_delivery_date,
            "revised_delivery_date": r.revised_delivery_date,  
            
            # Line Remark
            "original_line_remark": r.original_line_remark,
            "revised_line_remark": r.revised_line_remark,  
            
            # Component Of
            "original_component_of": r.original_component_of,
            "revised_component_of": r.revised_component_of,
            
            # Shipping Address
            "original_shipping_address": r.original_shipping_address,
            "revised_shipping_address": r.revised_shipping_address,
            
            # Line Status
            "original_line_status": r.original_line_status,
            "revised_line_status": r.revised_line_status ,
            # Is Free Item
            "original_is_free_item": r.original_is_free_item,
            "revised_is_free_item": r.revised_is_free_item ,
            
            # Qty - use rev_qty if > 0, else original_qty
            "original_qty": flt(r.original_qty),
            "revised_qty": flt(r.revised_qty) ,
            
            # Rate - use rev_rate if > 0, else original_rate
            "original_rate": flt(r.original_rate),
            "revised_rate": flt(r.revised_rate),
            
            # Item Code - Show revised only if item was changed
            "original_item_code": original_item,
            "revised_item_code": rev_item if item_changed else None,
            
            # Item Name - Show revised only if item was changed
            "original_item_name": r.original_item_name,
            "revised_item_name": r.revised_item_name if item_changed else None,
            
            # Item Description - Show revised only if item was changed
            "original_item_description": r.original_item_description,
            "revised_item_description": r.revised_item_description if item_changed else None,
            
            # Item Group - Show revised only if item was changed
            "original_item_group": r.original_item_group,
            "revised_item_group": r.revised_item_group if item_changed else None,
        }

        # Add all attributes with original and revised values
        # Revised attributes only shown if item was changed
        for i, field in enumerate(attr_fields, 1):
            orig_value = r.get(f"orig_attr_{i}")
            rev_value = r.get(f"rev_attr_{i}")
            
            row[f"original_{field}"] = orig_value
            # Only show revised attribute if item was changed
            row[f"revised_{field}"] = rev_value if item_changed else None

        data.append(row)

    return data


def get_conditions(filters):
    conditions = ""
    values = {}

    if filters.get("from_date") and filters.get("to_date"):
        conditions += " AND DATE(omr.creation) BETWEEN %(from_date)s AND %(to_date)s"
        values["from_date"] = filters.from_date
        values["to_date"] = filters.to_date

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

    # Keep only the latest approval per OMR
    approval_map = {}
    for row in rows:
        if row.parent not in approval_map:
            approval_map[row.parent] = {
                "approved_by": row.approved_by,
                "approved_on": row.approved_on,
            }

    return approval_map