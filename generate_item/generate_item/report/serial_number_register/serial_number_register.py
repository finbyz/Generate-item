# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
import json

@frappe.whitelist()
def get_serial_number_options():
    meta = frappe.get_meta("Serial Number")

    def get_options(fieldname):
        df = meta.get_field(fieldname)
        return df.options.split("\n") if df and df.options else []

    return {
        "mfg_type": get_options("mfg_type"),
        "api_monogram_req": get_options("api_monogram_req")
    }


def execute(filters=None):

    
    
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    
    return [

		{"label": "Batch No", "fieldname": "batch", "fieldtype": "Link", "options": "Batch", "width": 150},
		{"label": "Branch", "fieldname": "branch", "fieldtype": "Link", "options": "Branch", "width": 150},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 120},
      
        # {"label": "Sales Order", "fieldname": "sales_order", "fieldtype": "Link", "options": "Sales Order", "width": 150},
        {"label": "Customer Name", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 180},
        {"label": "Item Code", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 200},
        {"label": "Item Description", "fieldname": "description", "fieldtype": "Data", "width": 250},

        {"label": "Valve Type", "fieldname": "valve_type", "fieldtype": "Data", "width": 150},
        {"label": "Size Inch", "fieldname": "size", "fieldtype": "Data", "width": 120},
        {"label": "Class", "fieldname": "valve_class", "fieldtype": "Data", "width": 120},
        {"label": "Valve End", "fieldname": "valve_end", "fieldtype": "Data", "width": 150},
        {"label": "Operation", "fieldname": "operation", "fieldtype": "Data", "width": 180},
        {"label": "Material (Shell)", "fieldname": "shell_moc", "fieldtype": "Data", "width": 180},
		{"label": "Valve Serial No", "fieldname": "serial_no", "fieldtype": "Link", "options": "Serial Number", "width": 150},
        {
            "label": "MFG Type",
            "fieldname": "mfg_type",
            "fieldtype": "Data",
            "width": 140
        },
        {
            "label": "API Monogram",
            "fieldname": "api_monogram_req",
            "fieldtype": "Data",
            "width": 140
        },

        
    ]


def get_data(filters):
    conditions = ""
    values = {}

    if filters.get("sales_order"):
        conditions += " AND so.name = %(sales_order)s"
        values["sales_order"] = filters.get("sales_order")

    if filters.get("customer"):
        conditions += " AND so.customer = %(customer)s"
        values["customer"] = filters.get("customer")

    if filters.get("branch"):
        conditions += " AND so.branch = %(branch)s"
        values["branch"] = filters.get("branch")

    if filters.get("batch"):
        # frappe.log_error("filters---",filters)
        conditions += " AND soi.custom_batch_no = %(batch)s"
        values["batch"] = filters.get("batch")

    

    query = f"""
        SELECT
            sn.batch,

            so.branch,
            so.status,
            # so.name AS sales_order,
            so.customer,

            soi.item_code,
            ig.description,

            ig.attribute_2_value AS valve_type,
            ig.attribute_5_value AS size,
            ig.attribute_6_value AS valve_class,
            ig.attribute_7_value AS valve_end,
            ig.attribute_19_value AS operation,
            ig.attribute_9_value AS shell_moc,

            sn.serial_number AS serial_no,
            sn.mfg_type,
            sn.api_monogram_req

        FROM `tabSerial Number` sn

        INNER JOIN `tabSales Order Item` soi
            ON soi.custom_batch_no = sn.batch

        INNER JOIN `tabSales Order` so
            ON so.name = soi.parent

        LEFT JOIN `tabItem Generator` ig
            ON ig.created_item = soi.item_code

        WHERE 1=1
        {conditions}

        ORDER BY sn.creation DESC
    """

    return frappe.db.sql(query, values, as_dict=1)


@frappe.whitelist()
def update_serial_numbers(updates):
    #  
    if isinstance(updates, str):
        updates = json.loads(updates)
    for row in updates:
        
        if not row.get("serial_number"):
            continue

        frappe.db.set_value(
            "Serial Number",
            row["serial_number"],
            {
                "mfg_type": row.get("mfg_type"),
                "api_monogram_req": row.get("api_monogram_req")
            }
        )

    frappe.db.commit()