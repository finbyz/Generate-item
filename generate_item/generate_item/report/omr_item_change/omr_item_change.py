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
        
        # Generator Attributes
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
    data = []
    conditions = get_conditions(filters)

    omr_list = frappe.get_all(
        "Order Modification Request",
        filters=conditions,
        fields=["name", "branch", "creation", "customer_name", "workflow_state", "reason_for_change"]
    )

    for omr in omr_list:
        approval_details = get_approval_details(omr.name)
        
        items = frappe.get_all(
            "Sales Order Item For OMR",
            filters={"parent": omr.name},
            fields=["item", "rev_item", "batch_no", "qty", "rev_qty", "line_remark", "rev_line_remark"]
        )

        for itm in items:
            # CHANGE: Skip rows where Revised Item is not set
            if not itm.rev_item:
                continue


			 # IDENTIFY NEW VS MODIFIED
            # If original 'item' is empty but 'rev_item' exists, it is a new addition
            if not itm.item and itm.rev_item:
                entry_label = _("New Item Added")
            else:
                entry_label = _("Item Modified")

            # Since we are filtering for changed items, final_item is the rev_item
            final_item = itm.rev_item
            
            # Logic: If revised qty is provided (>0), use it, else keep old qty
            final_qty = itm.rev_qty if flt(itm.rev_qty) > 0 else itm.qty
            
            # Logic: If revised remark is provided, use it, else keep old remark
            final_remark = itm.rev_line_remark if itm.rev_line_remark else itm.line_remark
            
            # Fetch info for the Revised Item
            item_info = frappe.db.get_value("Item", final_item, ["item_name", "description", "item_group"], as_dict=True) or {}
            item_gen = get_item_generator_attributes(final_item)

            row = {
                "omr_no": omr.name,
                "branch": omr.branch,
                "omr_date": getdate(omr.creation),
                "customer_name": omr.customer_name,
                "omr_status": omr.workflow_state,
                "approved_on": approval_details.get("approved_on"),
                "approved_by": approval_details.get("approved_by"),
                "reason_for_change": omr.reason_for_change,
                "batch_no": itm.batch_no,
				"entry_type": entry_label,
                "item_code": final_item,
                "item_name": item_info.get("item_name"),
                "item_description": item_info.get("description"),
                "item_group": item_info.get("item_group"),
                "qty": final_qty,
                "item_remarks": final_remark,
                
                "type_of_product": item_gen.get("attribute_1_value"),
                "valve_type": item_gen.get("attribute_2_value"),
                "construction": item_gen.get("attribute_3_value"),
                "bore": item_gen.get("attribute_4_value"),
                "size": item_gen.get("attribute_5_value"),
                "rating": item_gen.get("attribute_6_value"),
                "ends": item_gen.get("attribute_7_value"),
                "end_sub_type": item_gen.get("attribute_8_value"),
                "shell_moc": item_gen.get("attribute_9_value"),
                "ball_moc": item_gen.get("attribute_10_value"),
                "ball_facing": item_gen.get("attribute_11_value"),
                "seat_ring_guide_moc": item_gen.get("attribute_12_value"),
                "seat_facing_plating": item_gen.get("attribute_13_value"),
                "seat_insert_seat_seal_moc": item_gen.get("attribute_14_value"),
                "stem_moc": item_gen.get("attribute_15_value"),
                "gasket": item_gen.get("attribute_16_value"),
                "gland_packing_o_ring_moc": item_gen.get("attribute_17_value"),
                "fasteners": item_gen.get("attribute_18_value"),
                "operator": item_gen.get("attribute_19_value"),
                "accessories": item_gen.get("attribute_20_value"),
                "special_requirement_for_valve": item_gen.get("attribute_21_value"),
                "quality_special_requirement_nde": item_gen.get("attribute_22_value"),
                "service": item_gen.get("attribute_23_value"),
                "inspection": item_gen.get("attribute_24_value"),
            }
            data.append(row)

    return data

def get_conditions(filters):
    # Base condition: Only Draft (0) and Submitted (1). Excludes Cancelled (2).
    conditions = {"docstatus": ["in", [0, 1]]} 
    
    if filters.get("from_date") and filters.get("to_date"):
        conditions["creation"] = ["between", [filters.from_date, filters.to_date]]
    
    if filters.get("omr_number"):
        conditions["name"] = filters.omr_number
    
    if filters.get("customer"):
        conditions["customer_name"] = ["like", f"%{filters.customer}%"]
        
    if filters.get("branch"):
        conditions["branch"] = filters.branch
        
    if filters.get("status"):
        conditions["workflow_state"] = ["in", filters.status]
        
    return conditions

def get_approval_details(omr_name):
    approval = frappe.db.sql("""
        SELECT username AS approved_by, modification_time AS approved_on
        FROM `tabState Change Items`
        WHERE parent = %s AND parenttype = 'Order Modification Request'
        AND workflow_state = 'Approved'
        ORDER BY modification_time DESC LIMIT 1
    """, omr_name, as_dict=True)
    
    return approval[0] if approval else {"approved_by": "", "approved_on": None}

def get_item_generator_attributes(item_code):
    if not item_code:
        return {}
    fields = [f"attribute_{i}_value" for i in range(1, 25)]
    return frappe.db.get_value("Item Generator", {"name": item_code}, fields, as_dict=True) or {}