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
            "fieldname": "fg_code",
            "label": _("FG CODE"),
            "fieldtype": "Data",
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
            "fieldname": "work_order",
            "label": _("Work Order No"),
            "fieldtype": "Link",
            "options": "Work Order",
            "width": 150
        },
        {
            "fieldname": "so_no",
            "label": _("SO NO"),
            "fieldtype": "Link",
            "options": "Sales Order",
            "width": 120
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
            "fieldname": "on_hand_qty",
            "label": _("On hand Qty"),
            "fieldtype": "Float",
            "width": 110
        },
        {
            "fieldname": "after_29_nov",
            "label": _("After 29-Nov"),
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
            "fieldname": "production_plan_no",
            "label": _("Production Plan No."),
            "fieldtype": "Link",
            "options": "Production Plan",
            "width": 150
        },
        {
            "fieldname": "material_request_no",
            "label": _("No. /Material Request No."),
            "fieldtype": "Link",
            "options": "Material Request",
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
            "fieldname": "po_line_required_by",
            "label": _("PO Line, Required By"),
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
    """Fetch work order data with all related information"""
    conditions = get_conditions(filters)
    
    # Get date reference field based on filter
    date_field = get_date_field(filters)
    
    # Initialize age filter
    if not filters.get("age"):
        filters["age"] = 0
    
    data = frappe.db.sql(f"""
        SELECT
            wo.production_item as fg_code,
            wo.custom_batch_no,
            wo.name as work_order,
            wo.sales_order as so_no,
            woi.item_code as input_item_code,
            woi.description as input_item_description,
            woi.stock_uom as uom,
            (woi.required_qty / wo.qty) as per_valve_input,
            wo.qty as fg_to_be_produce_qty,
            woi.required_qty as total_req_qty,
            woi.transferred_qty as issued_qty,
            IFNULL(bin.actual_qty, 0) as on_hand_qty,
            0 as after_29_nov,
            GREATEST(0, woi.required_qty - IFNULL(woi.transferred_qty, 0) - IFNULL(bin.actual_qty, 0)) as shortage_qty,
            wo.production_plan as production_plan_no,
            NULL as material_request_no,
            se.name as material_transfer_no,
            NULL as po_no,
            NULL as po_date,
            NULL as po_line_required_by,
            NULL as supplier_name,
            wo.status,
            0 as age,
            DATE(wo.creation) as creation_date,
            wo.planned_start_date,
            wo.planned_end_date,
            wo.actual_start_date,
            wo.actual_end_date
        FROM
            `tabWork Order` wo
        LEFT JOIN
            `tabWork Order Item` woi ON woi.parent = wo.name
        LEFT JOIN
            `tabBin` bin ON bin.item_code = woi.item_code AND bin.warehouse = woi.source_warehouse
        LEFT JOIN
            `tabStock Entry` se ON se.work_order = wo.name AND se.purpose = 'Material Transfer for Manufacture' AND se.docstatus = 1
        WHERE
            wo.docstatus = 1
            {conditions}
        ORDER BY
            wo.planned_start_date ASC, wo.name DESC
    """, filters, as_dict=1)
    
    # Calculate age like standard report and apply age filter at Work Order level
    from frappe.utils import date_diff, nowdate
    
    # First, calculate age for each row
    for row in data:
        start_date = row.get("actual_start_date") or row.get("planned_start_date")
        if start_date and row.get("status") != "Completed":
            row["age"] = date_diff(nowdate(), start_date) if start_date else 0
        else:
            row["age"] = 0
    
    # Apply age filter at Work Order level (not row level)
    if filters.get("age", 0) > 0:
        # Group by work order and check if any item meets age criteria
        work_order_ages = {}
        for row in data:
            wo_name = row.get("work_order")
            if wo_name not in work_order_ages:
                work_order_ages[wo_name] = row.get("age", 0)
            # Take the maximum age for the work order
            work_order_ages[wo_name] = max(work_order_ages[wo_name], row.get("age", 0))
        
        # Filter work orders that meet age criteria
        valid_work_orders = {wo for wo, age in work_order_ages.items() if age >= filters["age"]}
        
        # Filter data to only include rows from valid work orders
        data = [row for row in data if row.get("work_order") in valid_work_orders]
    
    return data

def get_date_field(filters):
    """Get the date field based on filter selection"""
    based_on = filters.get("based_on", "Creation Date")
    
    date_field_map = {
        "Creation Date": "wo.creation",
        "Planned Date": "wo.planned_start_date",
        "Actual Date": "wo.actual_start_date"
    }
    
    return date_field_map.get(based_on, "wo.creation")

def get_conditions(filters):
    """Build SQL conditions from filters"""
    conditions = []
    
    # Company filter
    if filters.get("company"):
        conditions.append("AND wo.company = %(company)s")
    
    # Status filter
    if filters.get("status"):
        conditions.append("AND wo.status = %(status)s")
    
    # Production item filter
    if filters.get("production_item"):
        conditions.append("AND wo.production_item = %(production_item)s")
    
    # Sales order filter
    if filters.get("sales_order"):
        conditions.append("AND wo.sales_order = %(sales_order)s")
    
    # Batch filter
    if filters.get("custom_batch_no"):
        conditions.append("AND wo.custom_batch_no = %(custom_batch_no)s")
    
    # Date range filtering based on selected date reference
    based_on = filters.get("based_on", "Creation Date")
    
    if filters.get("from_date") and filters.get("to_date"):
        if based_on == "Planned Date":
            conditions.append("AND wo.planned_start_date >= %(from_date)s")
            conditions.append("AND wo.planned_end_date <= %(to_date)s")
        elif based_on == "Actual Date":
            conditions.append("AND wo.actual_start_date >= %(from_date)s")
            conditions.append("AND wo.actual_end_date <= %(to_date)s")
        else:  # Creation Date
            conditions.append("AND wo.creation >= %(from_date)s")
            conditions.append("AND wo.creation <= %(to_date)s")
    
    return " ".join(conditions)

def get_chart_data(data, filters):
    """Generate dynamic bar chart based on selected chart reference"""
    if not data:
        return None
    
    chart_reference = filters.get("charts_based_on", "Status")
    
    if chart_reference == "Status":
        return get_status_chart(data)
    elif chart_reference == "Age":
        return get_age_chart(data)
    elif chart_reference == "Quantity":
        return get_quantity_chart(data, filters)
    
    return None

def get_status_chart(data):
    """Create chart for status distribution"""
    status_data = {}
    
    for row in data:
        status = row.get("status", "Unknown")
        status_data[status] = status_data.get(status, 0) + 1
    
    return {
        "data": {
            "labels": list(status_data.keys()),
            "datasets": [
                {
                    "name": "Work Orders",
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
        "30-60 Days": 0,
        "60-90 Days": 0,
        "90 Above": 0
    }
    
    for row in data:
        age = row.get("age", 0)
        if age > 0 and age <= 30:
            age_ranges["0-30 Days"] += 1
        elif age > 30 and age <= 60:
            age_ranges["30-60 Days"] += 1
        elif age > 60 and age <= 90:
            age_ranges["60-90 Days"] += 1
        else:
            age_ranges["90 Above"] += 1
    
    return {
        "data": {
            "labels": list(age_ranges.keys()),
            "datasets": [
                {
                    "name": "Work Orders",
                    "values": list(age_ranges.values())
                }
            ]
        },
        "type": "donut",
        "colors": ["#28a745", "#5bc0de", "#ffc107", "#ff851b", "#dc3545"]
    }

def get_quantity_chart(data, filters):
    """Create chart for quantity distribution"""
    pending_qty = 0
    completed_qty = 0
    
    for row in data:
        qty = flt(row.get("fg_to_be_produce_qty", 0))
        issued_qty = flt(row.get("issued_qty", 0))
        
        pending_qty += max(0, qty - issued_qty)
        completed_qty += min(qty, issued_qty)
    
    return {
        "data": {
            "labels": ["Pending", "Completed"],
            "datasets": [
                {
                    "name": "Quantity",
                    "values": [pending_qty, completed_qty]
                }
            ]
        },
        "type": "bar",
        "colors": ["#ffc107", "#28a745"],
        "barOptions": {
            "stacked": 1
        }
    }

def get_report_summary(data):
    """Generate summary cards"""
    if not data:
        return []
    
    # Count unique work orders
    unique_work_orders = set()
    for row in data:
        unique_work_orders.add(row.get("work_order"))
    
    total_orders = len(unique_work_orders)
    total_qty = sum(flt(row.get("fg_to_be_produce_qty", 0)) for row in data)
    total_issued = sum(flt(row.get("issued_qty", 0)) for row in data)
    total_shortage = sum(flt(row.get("shortage_qty", 0)) for row in data)
    
    # Calculate average age for unique work orders
    work_order_ages = {}
    for row in data:
        wo_name = row.get("work_order")
        if wo_name not in work_order_ages:
            work_order_ages[wo_name] = row.get("age", 0)
    
    avg_age = sum(work_order_ages.values()) / total_orders if total_orders > 0 else 0
    
    return [
        {
            "value": total_orders,
            "label": _("Total Work Orders"),
            "datatype": "Int",
            "indicator": "blue"
        },
        {
            "value": total_qty,
            "label": _("Total Production Qty"),
            "datatype": "Float",
            "indicator": "green"
        },
        {
            "value": total_issued,
            "label": _("Total Issued Qty"),
            "datatype": "Float",
            "indicator": "orange"
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
            "indicator": "blue"
        }
    ]