# Copyright (c) 2025, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, date_diff, nowdate, add_days
from datetime import datetime
import calendar

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart_data(data, filters)
    summary = get_report_summary(data)
    
    return columns, data, None, chart, summary

def get_columns():
    """Define all report columns"""
    return [
         {
            "fieldname": "so_no",
            "label": _("SO NO"),
            "fieldtype": "Link",
            "options": "Sales Order",
            "width": 120
        },
        {
            "fieldname": "custom_batch_no",
            "label": _("Batch No"),
            "fieldtype": "Link",
            "options": "Batch",
            "width": 120
        },
        {
            "fieldname": "fg_code",
            "label": _("FG CODE"),
            "fieldtype": "Data",
            "width": 120
        },
       
        {
            "fieldname": "work_order",
            "label": _("Work Order No"),
            "fieldtype": "Link",
            "options": "Work Order",
            "width": 150
        },
       
        {
            "fieldname": "input_item_code",
            "label": _("Input Item Code (Sub Assy/ RM)"),
            "fieldtype": "Link",
            "options": "Item",
            "width": 180
        },
        {
            "fieldname": "input_item_description",
            "label": _("Input Item Description"),
            "fieldtype": "Data",
            "width": 200
        },
        {
            "fieldname": "uom",
            "label": _("UOM"),
            "fieldtype": "Link",
            "options": "UOM",
            "width": 80
        },
         {
            "fieldname": "custom_drawing_no",
            "label": _("Drawing No (As per Bom)"),
            "fieldtype": "Data",
            "width": 80
        },
         {
            "fieldname": "custom_drawing_rev_no",
            "label": _("Drawing Rev No (As per Bom)"),
            "fieldtype": "Data",
            "width": 80
        },
        {
            "fieldname": "per_valve_input",
            "label": _("Per Valve Input Material Qty"),
            "fieldtype": "Float",
            "width": 150
        },
        {
            "fieldname": "fg_to_be_produce_qty",
            "label": _("FG To be Produce Qty"),
            "fieldtype": "Float",
            "width": 140
        },
        {
            "fieldname": "total_req_qty",
            "label": _("Total Req. Qty"),
            "fieldtype": "Float",
            "width": 120
        },
        {
            "fieldname": "issued_qty",
            "label": _("Issued Qty"),
            "fieldtype": "Float",
            "width": 100
        },
         {
            "fieldname": "allocated_qty",
            "label": _("Allocated Qty"),
            "fieldtype": "Float",
            "width": 100
        },
        {
            "fieldname": "on_hand_qty",
            "label": _("On hand Qty"),
            "fieldtype": "Float",
            "width": 110
        },
        {
            "fieldname": "shortage_qty",
            "label": _("Shortage Qty"),
            "fieldtype": "Float",
            "width": 120
        },
         {
            "fieldname": "po_qty",
            "label": _("PO Qty"),
            "fieldtype": "Float",
            "width": 120
        },
         {
            "fieldname": "po_received_qty",
            "label": _("PO Received Qty"),
            "fieldtype": "Float",
            "width": 120
        },
         {
            "fieldname": "stock_transfer_qty",
            "label": _("Stock Transfer Qty(from PP)"),
            "fieldtype": "Float",
            "width": 120
        },
        {
            "fieldname": "production_plan_no",
            "label": _("Production Plan No."),
            "fieldtype": "Link",
            "options": "Production Plan",
            "width": 150
        },
        {
            "fieldname": "material_request_no",
            "label": _("Material Request No."),
            "fieldtype": "Link",
            "options": "Material Request",
            "width": 150
        },
         {
            "fieldname": "material_transferrequest_no",
            "label": _("Material Transfer Request No.."),
            "fieldtype": "Data",
            "width": 150
        },


        {
            "fieldname": "material_transfer_no",
            "label": _("Material Transfer No."),
            "fieldtype": "Link",
            "options": "Stock Entry",
            "width": 150
        },
        {
            "fieldname": "po_no",
            "label": _("PO NO"),
            "fieldtype": "Link",
            "options": "Purchase Order",
            "width": 120
        },
        {
            "fieldname": "po_date",
            "label": _("PO Date"),
            "fieldtype": "Date",
            "width": 100
        },
        {
            "fieldname": "po_line_no",
            "label": _("PO Line No"),
            "fieldtype": "Data",
            "width": 140
        },
         {
            "fieldname": "required_by",
            "label": _("Required By"),
            "fieldtype": "Date",
            "width": 140
        },
        {
            "fieldname": "supplier_name",
            "label": _("Supplier Name"),
            "fieldtype": "Link",
            "options": "Supplier",
            "width": 150
        }
    ]

def get_data(filters):
    """Fetch production plan data with all related information"""
    if not filters.get("branch"):
        return []
    conditions = get_conditions(filters)
    
    # Initialize age filter
    if not filters.get("age"):
        filters["age"] = 0
        
    data = frappe.db.sql(f"""
    SELECT DISTINCT
        -- Production Plan Info
        pp.name AS production_plan_no,
        pp.posting_date AS pp_date,
        pp.company,
        pp.status AS pp_status,
        
        -- Work Order Info (if exists)
        wo.name AS work_order,
        wo.production_item AS fg_code,
        wo.custom_batch_no,
        wo.sales_order AS so_no,
        wo.qty AS fg_to_be_produce_qty,
        wo.status,
        DATE(wo.creation) AS wo_creation_date,
        wo.planned_start_date,
        wo.planned_end_date,
        wo.actual_start_date,
        wo.actual_end_date,
        wo.branch,
        
        -- Item Details (from WO Item, MR Item, or PO Item)
        COALESCE(woi.item_code, mri.item_code, poi.item_code) AS input_item_code,
        COALESCE(woi.description, mri.description, poi.description) AS input_item_description,
        COALESCE(woi.stock_uom, mri.stock_uom, poi.stock_uom) AS uom,
        
        -- Drawing Numbers from BOM Item
        COALESCE(woi.custom_drawing_no, mri.custom_drawing_no, poi.custom_drawing_no) AS custom_drawing_no,
        COALESCE(woi.custom_drawing_rev_no, mri.custom_drawing_rev_no, poi.custom_drawing_rev_no) AS custom_drawing_rev_no,
        
        -- Per Valve Input Material Qty - Direct fetch from BOM
        CASE 
            WHEN woi.item_code IS NOT NULL AND wo.qty > 0 THEN (woi.required_qty / wo.qty)
            ELSE 0
        END AS per_valve_input,
        
        -- Total Required Qty = Per Valve Input Material Qty x FG to be Produce Qty
        CASE 
            WHEN woi.item_code IS NOT NULL AND wo.qty > 0 THEN 
                (woi.required_qty / wo.qty) * wo.qty
            ELSE COALESCE(woi.required_qty, mri.qty, poi.qty, 0)
        END AS total_req_qty,
        
        -- Issued Qty - Against Work Order Issue Qty Store to Production
        COALESCE(woi.transferred_qty, 0) AS issued_qty,
        
        -- Allocated Qty = PO Qty + Stock Transfer Qty
        (COALESCE(poi.qty, 0) + IFNULL((
            SELECT SUM(sed.qty)
            FROM `tabStock Entry Detail` sed
            INNER JOIN `tabStock Entry` se ON se.name = sed.parent
            WHERE sed.material_request = mr.name
            AND sed.item_code = COALESCE(woi.item_code, mri.item_code, poi.item_code)
            AND se.purpose = 'Material Transfer'
            AND se.docstatus IN (0, 1)
        ), 0)) AS allocated_qty,
        
        -- PO Quantities
        COALESCE(poi.qty, 0) AS po_qty,
        COALESCE(poi.received_qty, 0) AS po_received_qty,
        
        -- Stock Transfer Qty from Production Plan (Material Transfer Stock Entries)
        IFNULL((
            SELECT SUM(sed.qty)
            FROM `tabStock Entry Detail` sed
            INNER JOIN `tabStock Entry` se ON se.name = sed.parent
            WHERE sed.material_request = mr.name
            AND sed.item_code = COALESCE(woi.item_code, mri.item_code, poi.item_code)
            AND se.purpose = 'Material Transfer'
            AND se.docstatus IN (0, 1)
        ), 0) AS stock_transfer_qty,
        
        -- Individual quantities for reference
        woi.required_qty AS wo_total_req_qty,
        woi.transferred_qty AS wo_issued_qty,
        mri.qty AS mr_qty,
        mri.ordered_qty AS mr_ordered_qty,
        mri.received_qty AS mr_received_qty,
        
        -- On Hand Quantity (Store and RM Combined Qty)
        IFNULL((
            SELECT SUM(bin.projected_qty)
            FROM `tabBin` bin
            WHERE bin.item_code = COALESCE(woi.item_code, mri.item_code, poi.item_code)
            AND bin.warehouse IN (
                SELECT wh.name
                FROM `tabWarehouse` wh
                WHERE wh.company = pp.company
                AND (wh.raw_material_warehouse = 1 OR wh.store_warehouse = 1)
            )
        ), 0) AS on_hand_qty,
        
        -- Shortage Calculation = Total Req. Qty - Allocated Qty
        GREATEST(
            0,
            CASE 
                WHEN woi.item_code IS NOT NULL AND wo.qty > 0 THEN 
                    (woi.required_qty / wo.qty) * wo.qty
                ELSE COALESCE(woi.required_qty, mri.qty, poi.qty, 0)
            END
            - (COALESCE(poi.qty, 0) + IFNULL((
                SELECT SUM(sed.qty)
                FROM `tabStock Entry Detail` sed
                INNER JOIN `tabStock Entry` se ON se.name = sed.parent
                WHERE sed.material_request = mr.name
                AND sed.item_code = COALESCE(woi.item_code, mri.item_code, poi.item_code)
                AND se.purpose = 'Material Transfer'
                AND se.docstatus IN (0, 1)
            ), 0))
        ) AS shortage_qty,
        
        -- Material Request Info
        mr.name AS material_request_no,
        mr.transaction_date AS mr_date,
        mr.material_request_type,
        mr.status AS mr_status,
        mr.schedule_date AS mr_schedule_date,
        
        -- Material Transfer Request (Material Request with type 'Material Transfer')
        CASE 
            WHEN mr.material_request_type = 'Material Transfer' THEN mr.name
            ELSE NULL
        END AS material_transferrequest_no,
        
        -- Stock Entry Info (combined from both sources)
        COALESCE(se.name, se_mr.name) AS material_transfer_no,
        COALESCE(se.posting_date, se_mr.posting_date) AS se_date,
        COALESCE(se.purpose, se_mr.purpose) AS se_purpose,
        
        -- Purchase Order Info
        po.name AS po_no,
        po.transaction_date AS po_date,
        po.supplier_name,
        po.status AS po_status,
        poi.schedule_date AS po_line_required_by,
        poi.schedule_date AS required_by,
        poi.po_line_no AS po_line_no,
        
        -- Additional fields
        0 AS after_29_nov,
        0 AS age,
        
        -- Source indicator
        CASE
            WHEN wo.name IS NOT NULL THEN 'Work Order'
            WHEN mr.name IS NOT NULL AND wo.name IS NULL THEN 'Material Request'
            WHEN po.name IS NOT NULL AND mr.name IS NULL AND wo.name IS NULL THEN 'Direct Purchase Order'
            ELSE 'Production Plan Only'
        END AS source_type,
        
        -- Unique identifier for duplicate detection
        CONCAT(
            COALESCE(pp.name, ''),
            '|',
            COALESCE(wo.name, ''),
            '|',
            COALESCE(woi.item_code, mri.item_code, poi.item_code, ''),
            '|',
            COALESCE(woi.name, mri.name, poi.name, '')
        ) AS unique_key

    FROM
        `tabProduction Plan` pp
    
    -- Link to Work Orders created from Production Plan
    LEFT JOIN
        `tabWork Order` wo ON wo.production_plan = pp.name 
        AND wo.docstatus IN (0, 1)
    
    -- Link to Work Order Items
    LEFT JOIN
        `tabWork Order Item` woi ON woi.parent = wo.name
    
    -- Link to Material Requests via Material Request Item (production_plan field)
    LEFT JOIN
        `tabMaterial Request Item` mri ON mri.production_plan = pp.name
        AND mri.docstatus IN (0, 1)
        AND (woi.item_code IS NULL OR mri.item_code = woi.item_code)
    
    LEFT JOIN
        `tabMaterial Request` mr ON mr.name = mri.parent
        AND mr.material_request_type IN ('Purchase', 'Material Transfer')
        AND mr.docstatus IN (0, 1)
    
    -- Link to Stock Entries from Work Order
    LEFT JOIN
        `tabStock Entry` se ON se.work_order = wo.name 
        AND se.purpose = 'Material Transfer for Manufacture'
        AND se.docstatus IN (0, 1)
    
    -- Link to Stock Entries from Material Request through Stock Entry Detail
    LEFT JOIN
        `tabStock Entry Detail` sed ON sed.material_request = mr.name
        AND sed.docstatus IN (0, 1)
        AND sed.item_code = mri.item_code
    
    LEFT JOIN
        `tabStock Entry` se_mr ON se_mr.name = sed.parent
        AND se_mr.purpose IN ('Material Transfer', 'Material Issue')
        AND se_mr.docstatus IN (0, 1)
        AND se.name IS NULL
    
    -- Link to Purchase Orders via Material Request Item
    LEFT JOIN
        `tabPurchase Order Item` poi ON poi.material_request_item = mri.name
        AND poi.docstatus IN (0, 1)
    
    LEFT JOIN
        `tabPurchase Order` po ON po.name = poi.parent
        AND po.docstatus IN (0, 1)
    
    WHERE
        pp.docstatus IN (0, 1)
        {conditions}
    
    GROUP BY
        pp.name, wo.name, woi.item_code, mri.item_code, poi.item_code
    
    ORDER BY
        pp.posting_date DESC, pp.name DESC, wo.planned_start_date ASC
""", filters, as_dict=1)
    
    # Remove duplicates based on unique_key
    seen_keys = set()
    unique_data = []
    
    for row in data:
        unique_key = row.get("unique_key")
        if unique_key and unique_key not in seen_keys:
            seen_keys.add(unique_key)
            unique_data.append(row)
        elif not unique_key:
            # Include rows without unique_key (shouldn't happen but safety check)
            unique_data.append(row)
    
    data = unique_data
    
    # Calculate age and apply age filter
    for row in data:
        # Calculate age based on Work Order if exists, otherwise use Production Plan
        start_date = None
        status = row.get("status") or row.get("pp_status")
        
        if row.get("work_order"):
            start_date = row.get("actual_start_date") or row.get("planned_start_date")
        elif row.get("pp_date"):
            start_date = row.get("pp_date")
        
        if start_date and status not in ["Completed", "Stopped", "Closed"]:
            row["age"] = date_diff(nowdate(), start_date)
        else:
            row["age"] = 0
    
    # Apply age filter at entity level (Work Order or Production Plan)
    if filters.get("age", 0) > 0:
        entity_ages = {}
        for row in data:
            # Use work_order as primary entity, fallback to production_plan_no
            entity = row.get("work_order") or row.get("production_plan_no")
            if entity not in entity_ages:
                entity_ages[entity] = row.get("age", 0)
            entity_ages[entity] = max(entity_ages[entity], row.get("age", 0))
        
        valid_entities = {entity for entity, age in entity_ages.items() if age >= filters["age"]}
        data = [row for row in data if (row.get("work_order") or row.get("production_plan_no")) in valid_entities]
    
    return data

def get_conditions(filters):
    """Build SQL conditions from filters"""
    conditions = []
    
    # Company filter
    if filters.get("company"):
        conditions.append("AND pp.company = %(company)s")
    
    # Status filter - check both WO and PP status
    if filters.get("status"):
        conditions.append("AND (wo.status = %(status)s OR pp.status = %(status)s)")
    
    # Production item filter
    if filters.get("production_item"):
        conditions.append("AND wo.production_item = %(production_item)s")
    
    # Sales order filter
    if filters.get("sales_order"):
        conditions.append("AND wo.sales_order = %(sales_order)s")
    
    # Batch filter
    if filters.get("custom_batch_no"):
        conditions.append("AND wo.custom_batch_no = %(custom_batch_no)s")

    if filters.get("branch"):
        conditions.append("AND wo.branch = %(branch)s")
    
    # Date range filtering based on selected date reference
    based_on = filters.get("based_on", "Creation Date")
    
    if filters.get("from_date") and filters.get("to_date"):
        if based_on == "Planned Date":
            conditions.append("AND (wo.planned_start_date >= %(from_date)s OR pp.posting_date >= %(from_date)s)")
            conditions.append("AND (wo.planned_end_date <= %(to_date)s OR pp.posting_date <= %(to_date)s)")
        elif based_on == "Actual Date":
            conditions.append("AND (wo.actual_start_date >= %(from_date)s OR pp.posting_date >= %(from_date)s)")
            conditions.append("AND (wo.actual_end_date <= %(to_date)s OR pp.posting_date <= %(to_date)s)")
        else:  # Creation Date
            conditions.append("AND (DATE(wo.creation) >= %(from_date)s OR pp.posting_date >= %(from_date)s)")
            conditions.append("AND (DATE(wo.creation) <= %(to_date)s OR pp.posting_date <= %(to_date)s)")
    
    return " ".join(conditions)

def get_chart_data(data, filters):
    """Generate dynamic chart based on selected chart reference"""
    if not data:
        return None
    
    chart_reference = filters.get("charts_based_on", "Status")
    
    if chart_reference == "Status":
        return get_status_chart(data)
    elif chart_reference == "Age":
        return get_age_chart(data)
    elif chart_reference == "Quantity":
        return get_quantity_chart(data)
    
    return None

def get_status_chart(data):
    """Create chart for status distribution"""
    status_data = {}
    unique_entities = set()
    
    for row in data:
        entity = row.get("work_order") or row.get("production_plan_no")
        if entity in unique_entities:
            continue
        unique_entities.add(entity)
        
        status = row.get("status") or row.get("pp_status", "Unknown")
        status_data[status] = status_data.get(status, 0) + 1
    
    return {
        "data": {
            "labels": list(status_data.keys()),
            "datasets": [
                {
                    "name": "Orders",
                    "values": list(status_data.values())
                }
            ]
        },
        "type": "donut",
        "colors": ["#28a745", "#ffc107", "#17a2b8", "#dc3545", "#6c757d"]
    }

def get_age_chart(data):
    """Create chart for age distribution"""
    age_ranges = {
        "0-30 Days": 0,
        "31-60 Days": 0,
        "61-90 Days": 0,
        "90+ Days": 0
    }
    
    unique_entities = {}
    
    for row in data:
        entity = row.get("work_order") or row.get("production_plan_no")
        if entity not in unique_entities:
            unique_entities[entity] = row.get("age", 0)
    
    for age in unique_entities.values():
        if 0 <= age <= 30:
            age_ranges["0-30 Days"] += 1
        elif 31 <= age <= 60:
            age_ranges["31-60 Days"] += 1
        elif 61 <= age <= 90:
            age_ranges["61-90 Days"] += 1
        else:
            age_ranges["90+ Days"] += 1
    
    return {
        "data": {
            "labels": list(age_ranges.keys()),
            "datasets": [
                {
                    "name": "Orders",
                    "values": list(age_ranges.values())
                }
            ]
        },
        "type": "bar",
        "colors": ["#28a745", "#5bc0de", "#ffc107", "#dc3545"]
    }

def get_quantity_chart(data):
    """Create chart for quantity distribution"""
    total_qty = 0
    issued_qty = 0
    shortage_qty = 0
    
    for row in data:
        total_qty += flt(row.get("total_req_qty", 0))
        issued_qty += flt(row.get("issued_qty", 0))
        shortage_qty += flt(row.get("shortage_qty", 0))
    
    pending_qty = total_qty - issued_qty
    
    return {
        "data": {
            "labels": ["Total Required", "Issued", "Pending", "Shortage"],
            "datasets": [
                {
                    "name": "Quantity",
                    "values": [total_qty, issued_qty, pending_qty, shortage_qty]
                }
            ]
        },
        "type": "bar",
        "colors": ["#17a2b8", "#28a745", "#ffc107", "#dc3545"]
    }

def get_report_summary(data):
    """Generate summary cards"""
    if not data:
        return []
    
    # Count unique entities (Work Orders or Production Plans)
    unique_entities = set()
    entity_ages = {}
    
    for row in data:
        entity = row.get("work_order") or row.get("production_plan_no")
        unique_entities.add(entity)
        if entity not in entity_ages:
            entity_ages[entity] = row.get("age", 0)
    
    total_entities = len(unique_entities)
    total_req_qty = sum(flt(row.get("total_req_qty", 0)) for row in data)
    total_issued = sum(flt(row.get("issued_qty", 0)) for row in data)
    total_shortage = sum(flt(row.get("shortage_qty", 0)) for row in data)
    
    avg_age = sum(entity_ages.values()) / total_entities if total_entities > 0 else 0
    
    return [
        {
            "value": total_entities,
            "label": _("Total Orders"),
            "datatype": "Int",
            "indicator": "blue"
        },
        {
            "value": total_req_qty,
            "label": _("Total Required Qty"),
            "datatype": "Float",
            "indicator": "blue"
        },
        {
            "value": total_issued,
            "label": _("Total Issued Qty"),
            "fieldtype": "Float",
            "indicator": "green"
        },
        {
            "value": total_shortage,
            "label": _("Total Shortage Qty"),
            "datatype": "Float",
            "indicator": "red"
        },
        {
            "value": round(avg_age),
            "label": _("Average Age (Days)"),
            "datatype": "Int",
            "indicator": "orange"
        }
    ]