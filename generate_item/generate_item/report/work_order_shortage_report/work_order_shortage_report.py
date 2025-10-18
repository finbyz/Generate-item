# # Copyright (c) 2025, Finbyz and contributors
# # For license information, please see license.txt

# import frappe
# from frappe import _
# from frappe.utils import flt, getdate, date_diff, nowdate, add_days
# from datetime import datetime
# import calendar

# def execute(filters=None):
#     columns = get_columns()
#     data = get_data(filters)
#     chart = get_chart_data(data, filters)
#     summary = get_report_summary(data)
    
#     return columns, data, None, chart, summary

# def get_columns():
#     """Define all report columns"""
#     return [
#         {
#             "fieldname": "fg_code",
#             "label": _("FG CODE"),
#             "fieldtype": "Data",
#             "width": 120
#         },
#         {
#             "fieldname": "custom_batch_no",
#             "label": _("Batch No"),
#             "fieldtype": "Link",
#             "options": "Batch",
#             "width": 120
#         },
#         {
#             "fieldname": "work_order",
#             "label": _("Work Order No"),
#             "fieldtype": "Link",
#             "options": "Work Order",
#             "width": 150
#         },
#         {
#             "fieldname": "so_no",
#             "label": _("SO NO"),
#             "fieldtype": "Link",
#             "options": "Sales Order",
#             "width": 120
#         },
#         {
#             "fieldname": "input_item_code",
#             "label": _("Input Item Code (Sub Assy/ RM)"),
#             "fieldtype": "Link",
#             "options": "Item",
#             "width": 180
#         },
#         {
#             "fieldname": "input_item_description",
#             "label": _("Input Item Description"),
#             "fieldtype": "Data",
#             "width": 200
#         },
#         {
#             "fieldname": "uom",
#             "label": _("UOM"),
#             "fieldtype": "Link",
#             "options": "UOM",
#             "width": 80
#         },
#         {
#             "fieldname": "per_valve_input",
#             "label": _("Per Valve Input Material Qty"),
#             "fieldtype": "Float",
#             "width": 150
#         },
#         {
#             "fieldname": "fg_to_be_produce_qty",
#             "label": _("FG To be Produce Qty"),
#             "fieldtype": "Float",
#             "width": 140
#         },
#         {
#             "fieldname": "total_req_qty",
#             "label": _("Total Req. Qty"),
#             "fieldtype": "Float",
#             "width": 120
#         },
#         {
#             "fieldname": "issued_qty",
#             "label": _("Issued Qty"),
#             "fieldtype": "Float",
#             "width": 100
#         },
#         {
#             "fieldname": "on_hand_qty",
#             "label": _("On hand Qty"),
#             "fieldtype": "Float",
#             "width": 110
#         },
#         {
#             "fieldname": "after_29_nov",
#             "label": _("After 29-Nov"),
#             "fieldtype": "Float",
#             "width": 110
#         },
#         {
#             "fieldname": "shortage_qty",
#             "label": _("Shortage Qty"),
#             "fieldtype": "Float",
#             "width": 120
#         },
#         {
#             "fieldname": "production_plan_no",
#             "label": _("Production Plan No."),
#             "fieldtype": "Link",
#             "options": "Production Plan",
#             "width": 150
#         },
#         {
#             "fieldname": "material_request_no",
#             "label": _("No. /Material Request No."),
#             "fieldtype": "Link",
#             "options": "Material Request",
#             "width": 150
#         },
#         {
#             "fieldname": "material_transfer_no",
#             "label": _("Material Transfer No."),
#             "fieldtype": "Link",
#             "options": "Stock Entry",
#             "width": 150
#         },
#         {
#             "fieldname": "po_no",
#             "label": _("PO NO"),
#             "fieldtype": "Link",
#             "options": "Purchase Order",
#             "width": 120
#         },
#         {
#             "fieldname": "po_date",
#             "label": _("PO Date"),
#             "fieldtype": "Date",
#             "width": 100
#         },
#         {
#             "fieldname": "po_line_required_by",
#             "label": _("PO Line, Required By"),
#             "fieldtype": "Date",
#             "width": 140
#         },
#         {
#             "fieldname": "supplier_name",
#             "label": _("Supplier Name"),
#             "fieldtype": "Link",
#             "options": "Supplier",
#             "width": 150
#         }
#     ]

# def get_data(filters):
#     """Fetch work order data with all related information"""
#     conditions = get_conditions(filters)
    
#     # Get date reference field based on filter
#     date_field = get_date_field(filters)
    
#     # Initialize age filter
#     if not filters.get("age"):
#         filters["age"] = 0
        
#     data = frappe.db.sql(f"""
#     SELECT
#         -- Production Plan Info
#         pp.name AS production_plan_no,
#         pp.posting_date AS pp_date,
#         pp.company,
#         pp.status AS pp_status,
        
#         -- Work Order Info (if exists)
#         wo.name AS work_order,
#         wo.production_item AS fg_code,
#         wo.custom_batch_no,
#         wo.sales_order AS so_no,
#         wo.qty AS fg_to_be_produce_qty,
#         wo.status AS wo_status,
#         DATE(wo.creation) AS wo_creation_date,
#         wo.planned_start_date AS wo_planned_start_date,
#         wo.planned_end_date AS wo_planned_end_date,
#         wo.actual_start_date AS wo_actual_start_date,
#         wo.actual_end_date AS wo_actual_end_date,
        
#         -- Item Details (from WO Item, MR Item, or PO Item)
#         COALESCE(woi.item_code, mri.item_code, poi.item_code) AS input_item_code,
#         COALESCE(woi.description, mri.description, poi.description) AS input_item_description,
#         COALESCE(woi.stock_uom, mri.stock_uom, poi.stock_uom) AS uom,
        
#         -- Quantities from Work Order Item
#         CASE 
#             WHEN woi.item_code IS NOT NULL AND wo.qty > 0 THEN (woi.required_qty / wo.qty)
#             ELSE 0
#         END AS per_valve_input,
#         woi.required_qty AS wo_total_req_qty,
#         woi.transferred_qty AS wo_issued_qty,
        
#         -- Quantities from Material Request Item
#         mri.qty AS mr_qty,
#         mri.ordered_qty AS mr_ordered_qty,
#         mri.received_qty AS mr_received_qty,
        
#         -- Quantities from Purchase Order Item
#         poi.qty AS po_qty,
#         poi.received_qty AS po_received_qty,
        
#         -- On Hand Quantity
#         IFNULL((
#             SELECT SUM(bin.projected_qty)
#             FROM `tabBin` bin
#             WHERE bin.item_code = COALESCE(woi.item_code, mri.item_code, poi.item_code)
#             AND bin.warehouse IN (
#                 SELECT wh.name
#                 FROM `tabWarehouse` wh
#                 WHERE wh.company = pp.company
#                 AND wh.raw_material_warehouse = 1
#                 AND wh.store_warehouse = 1
#             )
#         ), 0) AS on_hand_qty,
        
#         -- Shortage Calculation
#         GREATEST(
#             0,
#             COALESCE(woi.required_qty, mri.qty, 0)
#             - IFNULL(woi.transferred_qty, 0)
#             - IFNULL(mri.received_qty, 0)
#             - IFNULL(poi.received_qty, 0)
#             - IFNULL((
#                 SELECT SUM(bin.projected_qty)
#                 FROM `tabBin` bin
#                 WHERE bin.item_code = COALESCE(woi.item_code, mri.item_code, poi.item_code)
#                 AND bin.warehouse IN (
#                     SELECT wh.name
#                     FROM `tabWarehouse` wh
#                     WHERE wh.company = pp.company
#                     AND wh.raw_material_warehouse = 1
#                     AND wh.store_warehouse = 1
#                 )
#             ), 0)
#         ) AS shortage_qty,
        
#         -- Material Request Info
#         mr.name AS material_request_no,
#         mr.transaction_date AS mr_date,
#         mr.material_request_type,
#         mr.status AS mr_status,
#         mr.schedule_date AS mr_schedule_date,
        
#         -- Stock Entry Info (linked to WO only, MR links through Stock Entry Detail)
#         se.name AS material_transfer_no,
#         se.posting_date AS se_date,
#         se.purpose AS se_purpose,
#         se.from_warehouse,
#         se.to_warehouse,
        
#         -- Purchase Order Info
#         po.name AS po_no,
#         po.transaction_date AS po_date,
#         po.supplier_name,
#         po.status AS po_status,
#         poi.schedule_date AS po_line_required_by,
        
#         -- Additional fields
#         0 AS after_29_nov,
#         0 AS age,
        
#         -- Source indicator
#         CASE
#             WHEN wo.name IS NOT NULL THEN 'Work Order'
#             WHEN mr.name IS NOT NULL AND wo.name IS NULL THEN 'Material Request'
#             WHEN po.name IS NOT NULL AND mr.name IS NULL AND wo.name IS NULL THEN 'Direct Purchase Order'
#             ELSE 'Production Plan Only'
#         END AS source_type

#     FROM
#         `tabProduction Plan` pp
    
#     -- Link to Work Orders created from Production Plan
#     LEFT JOIN
#         `tabWork Order` wo ON wo.production_plan = pp.name 
#         AND wo.docstatus IN (0, 1)
    
#     -- Link to Work Order Items
#     LEFT JOIN
#         `tabWork Order Item` woi ON woi.parent = wo.name
    
#     -- Link to Material Requests via Material Request Item (production_plan field)
#     LEFT JOIN
#         `tabMaterial Request Item` mri ON mri.production_plan = pp.name
#         AND mri.docstatus IN (0, 1)
#         AND (mri.item_code = woi.item_code OR woi.item_code IS NULL)
    
#     LEFT JOIN
#         `tabMaterial Request` mr ON mr.name = mri.parent
#         AND mr.material_request_type IN ('Purchase', 'Material Transfer')
#         AND mr.docstatus IN (0, 1)
    
#     -- Link to Stock Entries (only from Work Order, as Stock Entry doesn't have direct material_request field)
#     LEFT JOIN
#         `tabStock Entry` se ON se.work_order = wo.name 
#         AND se.purpose = 'Material Transfer for Manufacture'
#         AND se.docstatus IN (0, 1)
    
#     -- For Material Request to Stock Entry, need to join through Stock Entry Detail
#     LEFT JOIN
#         `tabStock Entry Detail` sed ON sed.material_request = mr.name
#         AND sed.docstatus IN (0, 1)
#         AND sed.item_code = mri.item_code
    
#     LEFT JOIN
#         `tabStock Entry` se_mr ON se_mr.name = sed.parent
#         AND se_mr.purpose IN ('Material Transfer', 'Material Issue')
#         AND se_mr.docstatus IN (0, 1)
#         AND se.name IS NULL
    
#     -- Link to Purchase Orders via Material Request Item
#     LEFT JOIN
#         `tabPurchase Order Item` poi ON poi.material_request_item = mri.name
#         AND poi.docstatus IN (0, 1)
    
#     LEFT JOIN
#         `tabPurchase Order` po ON po.name = poi.parent
#         AND po.docstatus IN (0, 1)
    
#     WHERE
#         pp.docstatus IN (0, 1)
#         {conditions}
    
#     ORDER BY
#         pp.posting_date DESC, pp.name DESC, wo.planned_start_date ASC
# """, filters, as_dict=1)
    
# #     data = frappe.db.sql(f"""
# #     SELECT
# #         wo.production_item AS fg_code,
# #         wo.custom_batch_no,
# #         wo.name AS work_order,
# #         wo.sales_order AS so_no,
# #         woi.item_code AS input_item_code,
# #         woi.description AS input_item_description,
# #         woi.stock_uom AS uom,
# #         (woi.required_qty / wo.qty) AS per_valve_input,
# #         wo.qty AS fg_to_be_produce_qty,
# #         woi.required_qty AS total_req_qty,
# #         woi.transferred_qty AS issued_qty,
# #         IFNULL((
# #             SELECT SUM(bin.projected_qty)
# #             FROM `tabBin` bin
# #             WHERE bin.item_code = woi.item_code
# #             AND bin.warehouse IN (
# #                 SELECT wh.name
# #                 FROM `tabWarehouse` wh
# #                 WHERE wh.branch = woi.branch
# #                 AND wh.raw_material_warehouse = 1
# #                 AND wh.store_warehouse = 1
# #             )
# #         ), 0) AS on_hand_qty,
# #         0 AS after_29_nov,
# #         GREATEST(
# #             0,
# #             woi.required_qty
# #             - IFNULL(woi.transferred_qty, 0)
# #             - IFNULL((
# #                 SELECT SUM(bin.projected_qty)
# #                 FROM `tabBin` bin
# #                 WHERE bin.item_code = woi.item_code
# #                 AND bin.warehouse IN (
# #                     SELECT wh.name
# #                     FROM `tabWarehouse` wh
# #                     WHERE wh.branch = woi.branch
# #                     AND wh.raw_material_warehouse = 1
# #                     AND wh.store_warehouse = 1
# #                 )
# #             ), 0)
# #         ) AS shortage_qty,
# #         wo.production_plan AS production_plan_no,
# #         mr.name AS material_request_no,
# #         se.name AS material_transfer_no,
# #         po.name AS po_no,
# #         po.transaction_date AS po_date,
# #         poi.schedule_date AS po_line_required_by,
# #         po.supplier_name AS supplier_name,
# #         wo.status,
# #         0 AS age,
# #         DATE(wo.creation) AS creation_date,
# #         wo.planned_start_date,
# #         wo.planned_end_date,
# #         wo.actual_start_date,
# #         wo.actual_end_date

# #     FROM
# #         `tabWork Order` wo
# #     LEFT JOIN
# #         `tabWork Order Item` woi ON woi.parent = wo.name
# #     LEFT JOIN
# #         `tabStock Entry` se ON se.work_order = wo.name AND se.purpose = 'Material Transfer for Manufacture' AND se.docstatus IN (0, 1)
# #     LEFT JOIN
# #         `tabMaterial Request` mr ON mr.work_order = wo.name AND mr.material_request_type = 'Purchase' AND mr.docstatus IN (0, 1)
# #     LEFT JOIN
# #         `tabMaterial Request Item` mri ON mri.parent = mr.name AND mri.item_code = woi.item_code AND mri.docstatus IN (0, 1)
# #     LEFT JOIN
# #         `tabPurchase Order Item` poi ON poi.material_request_item = mri.name AND poi.docstatus IN (0, 1)
# #     LEFT JOIN
# #         `tabPurchase Order` po ON po.name = poi.parent AND po.docstatus IN (0, 1)
# #     WHERE
# #         wo.docstatus IN (0, 1)
# #         {conditions}
# #     ORDER BY
# #         wo.planned_start_date ASC, wo.name DESC
# # """, filters, as_dict=1)





    
#     # Calculate age like standard report and apply age filter at Work Order level
#     from frappe.utils import date_diff, nowdate
    
#     # First, calculate age for each row
#     for row in data:
#         start_date = row.get("actual_start_date") or row.get("planned_start_date")
#         if start_date and row.get("status") != "Completed":
#             row["age"] = date_diff(nowdate(), start_date) if start_date else 0
#         else:
#             row["age"] = 0
    
#     # Apply age filter at Work Order level (not row level)
#     if filters.get("age", 0) > 0:
#         # Group by work order and check if any item meets age criteria
#         work_order_ages = {}
#         for row in data:
#             wo_name = row.get("work_order")
#             if wo_name not in work_order_ages:
#                 work_order_ages[wo_name] = row.get("age", 0)
#             # Take the maximum age for the work order
#             work_order_ages[wo_name] = max(work_order_ages[wo_name], row.get("age", 0))
        
#         # Filter work orders that meet age criteria
#         valid_work_orders = {wo for wo, age in work_order_ages.items() if age >= filters["age"]}
        
#         # Filter data to only include rows from valid work orders
#         data = [row for row in data if row.get("work_order") in valid_work_orders]
    
#     return data

# def get_date_field(filters):
#     """Get the date field based on filter selection"""
#     based_on = filters.get("based_on", "Creation Date")
    
#     date_field_map = {
#         "Creation Date": "wo.creation",
#         "Planned Date": "wo.planned_start_date",
#         "Actual Date": "wo.actual_start_date"
#     }
    
#     return date_field_map.get(based_on, "wo.creation")

# def get_conditions(filters):
#     """Build SQL conditions from filters"""
#     conditions = []
    
#     # Company filter
#     if filters.get("company"):
#         conditions.append("AND wo.company = %(company)s")
    
#     # Status filter
#     if filters.get("status"):
#         conditions.append("AND wo.status = %(status)s")
    
#     # Production item filter
#     if filters.get("production_item"):
#         conditions.append("AND wo.production_item = %(production_item)s")
    
#     # Sales order filter
#     if filters.get("sales_order"):
#         conditions.append("AND wo.sales_order = %(sales_order)s")
    
#     # Batch filter
#     if filters.get("custom_batch_no"):
#         conditions.append("AND wo.custom_batch_no = %(custom_batch_no)s")
    
#     # Date range filtering based on selected date reference
#     based_on = filters.get("based_on", "Creation Date")
    
#     if filters.get("from_date") and filters.get("to_date"):
#         if based_on == "Planned Date":
#             conditions.append("AND wo.planned_start_date >= %(from_date)s")
#             conditions.append("AND wo.planned_end_date <= %(to_date)s")
#         elif based_on == "Actual Date":
#             conditions.append("AND wo.actual_start_date >= %(from_date)s")
#             conditions.append("AND wo.actual_end_date <= %(to_date)s")
#         else:  # Creation Date
#             conditions.append("AND wo.creation >= %(from_date)s")
#             conditions.append("AND wo.creation <= %(to_date)s")
    
#     return " ".join(conditions)

# def get_chart_data(data, filters):
#     """Generate dynamic bar chart based on selected chart reference"""
#     if not data:
#         return None
    
#     chart_reference = filters.get("charts_based_on", "Status")
    
#     if chart_reference == "Status":
#         return get_status_chart(data)
#     elif chart_reference == "Age":
#         return get_age_chart(data)
#     elif chart_reference == "Quantity":
#         return get_quantity_chart(data, filters)
    
#     return None

# def get_status_chart(data):
#     """Create chart for status distribution"""
#     status_data = {}
    
#     for row in data:
#         status = row.get("status", "Unknown")
#         status_data[status] = status_data.get(status, 0) + 1
    
#     return {
#         "data": {
#             "labels": list(status_data.keys()),
#             "datasets": [
#                 {
#                     "name": "Work Orders",
#                     "values": list(status_data.values())
#                 }
#             ]
#         },
#         "type": "donut",
#         "colors": ["#28a745", "#ffc107", "#17a2b8", "#dc3545", "#6c757d"]
#     }

# def get_age_chart(data):
#     """Create chart for age distribution"""
#     age_ranges = {
#         "0-30 Days": 0,
#         "30-60 Days": 0,
#         "60-90 Days": 0,
#         "90 Above": 0
#     }
    
#     for row in data:
#         age = row.get("age", 0)
#         if age > 0 and age <= 30:
#             age_ranges["0-30 Days"] += 1
#         elif age > 30 and age <= 60:
#             age_ranges["30-60 Days"] += 1
#         elif age > 60 and age <= 90:
#             age_ranges["60-90 Days"] += 1
#         else:
#             age_ranges["90 Above"] += 1
    
#     return {
#         "data": {
#             "labels": list(age_ranges.keys()),
#             "datasets": [
#                 {
#                     "name": "Work Orders",
#                     "values": list(age_ranges.values())
#                 }
#             ]
#         },
#         "type": "donut",
#         "colors": ["#28a745", "#5bc0de", "#ffc107", "#ff851b", "#dc3545"]
#     }

# def get_quantity_chart(data, filters):
#     """Create chart for quantity distribution"""
#     pending_qty = 0
#     completed_qty = 0
    
#     for row in data:
#         qty = flt(row.get("fg_to_be_produce_qty", 0))
#         issued_qty = flt(row.get("issued_qty", 0))
        
#         pending_qty += max(0, qty - issued_qty)
#         completed_qty += min(qty, issued_qty)
    
#     return {
#         "data": {
#             "labels": ["Pending", "Completed"],
#             "datasets": [
#                 {
#                     "name": "Quantity",
#                     "values": [pending_qty, completed_qty]
#                 }
#             ]
#         },
#         "type": "bar",
#         "colors": ["#ffc107", "#28a745"],
#         "barOptions": {
#             "stacked": 1
#         }
#     }

# def get_report_summary(data):
#     """Generate summary cards"""
#     if not data:
#         return []
    
#     # Count unique work orders
#     unique_work_orders = set()
#     for row in data:
#         unique_work_orders.add(row.get("work_order"))
    
#     total_orders = len(unique_work_orders)
#     total_qty = sum(flt(row.get("fg_to_be_produce_qty", 0)) for row in data)
#     total_issued = sum(flt(row.get("issued_qty", 0)) for row in data)
#     total_shortage = sum(flt(row.get("shortage_qty", 0)) for row in data)
    
#     # Calculate average age for unique work orders
#     work_order_ages = {}
#     for row in data:
#         wo_name = row.get("work_order")
#         if wo_name not in work_order_ages:
#             work_order_ages[wo_name] = row.get("age", 0)
    
#     avg_age = sum(work_order_ages.values()) / total_orders if total_orders > 0 else 0
    
#     return [
#         {
#             "value": total_orders,
#             "label": _("Total Work Orders"),
#             "datatype": "Int",
#             "indicator": "blue"
#         },
#         {
#             "value": total_qty,
#             "label": _("Total Production Qty"),
#             "datatype": "Float",
#             "indicator": "green"
#         },
#         {
#             "value": total_issued,
#             "label": _("Total Issued Qty"),
#             "datatype": "Float",
#             "indicator": "orange"
#         },
#         {
#             "value": total_shortage,
#             "label": _("Total Shortage Qty"),
#             "datatype": "Float",
#             "indicator": "red"
#         },
#         {
#             "value": round(avg_age),
#             "label": _("Average Age (Days)"),
#             "datatype": "Int",
#             "indicator": "blue"
#         }
#     ]


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
            "label": _("Material Request No."),
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
    """Fetch production plan data with all related information"""
    conditions = get_conditions(filters)
    
    # Initialize age filter
    if not filters.get("age"):
        filters["age"] = 0
        
    data = frappe.db.sql(f"""
    SELECT
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
        
        -- Item Details (from WO Item, MR Item, or PO Item)
        COALESCE(woi.item_code, mri.item_code, poi.item_code) AS input_item_code,
        COALESCE(woi.description, mri.description, poi.description) AS input_item_description,
        COALESCE(woi.stock_uom, mri.stock_uom, poi.stock_uom) AS uom,
        
        -- Quantities from Work Order Item
        CASE 
            WHEN woi.item_code IS NOT NULL AND wo.qty > 0 THEN (woi.required_qty / wo.qty)
            ELSE 0
        END AS per_valve_input,
        
        -- Total Required Qty (prioritize WO, then MR, then PO)
        COALESCE(woi.required_qty, mri.qty, poi.qty, 0) AS total_req_qty,
        
        -- Issued Qty (WO transferred + MR received + PO received)
        COALESCE(woi.transferred_qty, 0) + COALESCE(mri.received_qty, 0) + COALESCE(poi.received_qty, 0) AS issued_qty,
        
        -- Individual quantities for reference
        woi.required_qty AS wo_total_req_qty,
        woi.transferred_qty AS wo_issued_qty,
        mri.qty AS mr_qty,
        mri.ordered_qty AS mr_ordered_qty,
        mri.received_qty AS mr_received_qty,
        poi.qty AS po_qty,
        poi.received_qty AS po_received_qty,
        
        -- On Hand Quantity
        IFNULL((
            SELECT SUM(bin.projected_qty)
            FROM `tabBin` bin
            WHERE bin.item_code = COALESCE(woi.item_code, mri.item_code, poi.item_code)
            AND bin.warehouse IN (
                SELECT wh.name
                FROM `tabWarehouse` wh
                WHERE wh.company = pp.company
                AND wh.raw_material_warehouse = 1
                AND wh.store_warehouse = 1
            )
        ), 0) AS on_hand_qty,
        
        -- Shortage Calculation
        GREATEST(
            0,
            COALESCE(woi.required_qty, mri.qty, poi.qty, 0)
            - IFNULL(woi.transferred_qty, 0)
            - IFNULL(mri.received_qty, 0)
            - IFNULL(poi.received_qty, 0)
            - IFNULL((
                SELECT SUM(bin.projected_qty)
                FROM `tabBin` bin
                WHERE bin.item_code = COALESCE(woi.item_code, mri.item_code, poi.item_code)
                AND bin.warehouse IN (
                    SELECT wh.name
                    FROM `tabWarehouse` wh
                    WHERE wh.company = pp.company
                    AND wh.raw_material_warehouse = 1
                    AND wh.store_warehouse = 1
                )
            ), 0)
        ) AS shortage_qty,
        
        -- Material Request Info
        mr.name AS material_request_no,
        mr.transaction_date AS mr_date,
        mr.material_request_type,
        mr.status AS mr_status,
        mr.schedule_date AS mr_schedule_date,
        
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
        
        -- Additional fields
        0 AS after_29_nov,
        0 AS age,
        
        -- Source indicator
        CASE
            WHEN wo.name IS NOT NULL THEN 'Work Order'
            WHEN mr.name IS NOT NULL AND wo.name IS NULL THEN 'Material Request'
            WHEN po.name IS NOT NULL AND mr.name IS NULL AND wo.name IS NULL THEN 'Direct Purchase Order'
            ELSE 'Production Plan Only'
        END AS source_type

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
        AND (mri.item_code = woi.item_code OR woi.item_code IS NULL)
    
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
    
    ORDER BY
        pp.posting_date DESC, pp.name DESC, wo.planned_start_date ASC
""", filters, as_dict=1)
    
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