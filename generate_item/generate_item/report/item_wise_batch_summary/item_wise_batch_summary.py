from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    # data = get_data(filters)
    data = get_data2(filters)
    return columns, data

def get_columns():
    return [
        {
            "label": _("Level"),
            "fieldname": "level",
            "fieldtype": "Int",
            "width": 50,
            "hidden": 1
        },
        {
            "label": _("Parent"),
            "fieldname": "parent",
            "fieldtype": "Data",
            "width": 50,
            "hidden": 1
        },
        {
            "label": _("Is Group"),
            "fieldname": "is_group",
            "fieldtype": "Check",
            "width": 50,
            "hidden": 1
        },
        {
            "label": _("Batch No"),
            "fieldname": "batch_no",
            "fieldtype": "Link",
            "options": "Batch",
            "width": 120
        },
        {
            "label": _("Production Plan"),
            "fieldname": "production_plan",
            "fieldtype": "Link",
            "options": "Production Plan",
            "width": 120
        },
        {
            "label": _("Sales Order"),
            "fieldname": "sales_order",
            "fieldtype": "Link",
            "options": "Sales Order",
            "width": 120
        },
        {
            "label": _("Customer"),
            "fieldname": "customer",
            "fieldtype": "Link",
            "options": "Customer",
            "width": 150
        },
        {
            "label": _("Transaction Date"),
            "fieldname": "transaction_date",
            "fieldtype": "Date",
            "width": 100
        },
        {
            "label": _("PO No"),
            "fieldname": "po_no",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("Item Code"),
            "fieldname": "item_code",
            "fieldtype": "Link",
            "options": "Item",
            "width": 120
        },
        {
            "label": _("Item Description"),
            "fieldname": "description",
            "fieldtype": "Data",
            "width": 150
        },
        {
            "label": _("Quantity"),
            "fieldname": "quantity",
            "fieldtype": "Float",
            "width": 80
        },
        # {
        #     "label": _("UOM"),
        #     "fieldname": "uom",
        #     "fieldtype": "Link",
        #     "options": "UOM",
        #     "width": 80
        # },
        {
            "label": _("BOM"),
            "fieldname": "bom_no",
            "fieldtype": "Link",
            "options": "BOM",
            "width": 120
        },
        {
            "label": _("BOM Status"),
            "fieldname": "bom_status",
            "fieldtype": "Data",
            "width": 100
        },
        # {
        #     "label": _("Has BOM"),
        #     "fieldname": "has_bom",
        #     "fieldtype": "Data",
        #     "width": 80
        # },
       
       
    ]

def get_data2(filters):
    conditions = get_conditions(filters)
    
    batch_selected = filters.get("so_custom_batch_no") or filters.get("batch_no")
    
    if batch_selected:
        return get_simple_batch_data(filters)
    
    query = """
        (
            -- Directly linked BOMs
            SELECT 
                soi.custom_batch_no AS batch_no,
                pp.name AS production_plan,
                so.name AS sales_order,
                so.customer AS customer,
                so.transaction_date AS transaction_date,
                so.po_no AS po_no,
                so.total_qty AS total_qty,
                soi.item_code AS so_item_code,
                soi.description AS so_description,
                soi.qty AS so_qty,
                soi.uom AS so_uom,
                soi.bom_no AS bom_no,
                'Yes' AS has_bom,
                bom.docstatus AS bom_docstatus,
                CASE
                    WHEN bom.docstatus = 0 THEN 'Draft'
                    WHEN bom.docstatus = 1 THEN 'Submitted'
                    WHEN bom.docstatus = 2 THEN 'Not Available'
                    ELSE 'Not Available'
                END AS bom_status,
                bom.item AS bom_item_code,
                bom.description AS bom_description,
                bom.quantity AS bom_quantity,
                bom.uom AS bom_uom,
                bom.name AS effective_bom_no,
                soi.bom_no AS existing_bom,  -- Use soi.bom_no directly
                bom_item.item_code AS bom_child_item_code,
                bom_item.description AS bom_child_description,
                bom_item.qty AS bom_child_qty,
                bom_item.uom AS bom_child_uom,
                bom_item.idx AS bom_item_idx
            FROM
                `tabSales Order` so
            INNER JOIN
                `tabSales Order Item` soi ON so.name = soi.parent
            LEFT JOIN
                `tabBOM` bom ON soi.bom_no = bom.name
                    AND (bom.custom_batch_no IS NULL OR bom.custom_batch_no = soi.custom_batch_no)
            LEFT JOIN
                `tabBOM Item` bom_item ON bom.name = bom_item.parent
                    AND (bom_item.custom_batch_no IS NULL OR bom_item.custom_batch_no = soi.custom_batch_no)
            LEFT JOIN
                `tabProduction Plan Sales Order` pps ON so.name = pps.sales_order
            LEFT JOIN
                `tabProduction Plan` pp ON pps.parent = pp.name
            WHERE
                so.docstatus = 1
                AND soi.custom_batch_no IS NOT NULL
                AND soi.custom_batch_no != ''
                AND soi.bom_no IS NOT NULL
                AND soi.bom_no != ''
                AND {conditions}
        )
        UNION ALL
        (
            -- Item-based BOMs (when no direct BOM link)
            SELECT 
                soi.custom_batch_no AS batch_no,
                pp.name AS production_plan,
                so.name AS sales_order,
                so.customer AS customer,
                so.transaction_date AS transaction_date,
                so.po_no AS po_no,
                so.total_qty AS total_qty,
                soi.item_code AS so_item_code,
                soi.description AS so_description,
                soi.qty AS so_qty,
                soi.uom AS so_uom,
                soi.bom_no AS bom_no,
                'No' AS has_bom,
                item_bom.docstatus AS bom_docstatus,
                CASE
                    WHEN item_bom.docstatus = 0 THEN 'Draft'
                    WHEN item_bom.docstatus = 1 THEN 'Submitted'
                    WHEN item_bom.docstatus = 2 THEN 'Not Available'
                    ELSE 'Not Available'
                END AS bom_status,
                item_bom.item AS bom_item_code,
                item_bom.description AS bom_description,
                item_bom.quantity AS bom_quantity,
                item_bom.uom AS bom_uom,
                item_bom.name AS effective_bom_no,
                soi.bom_no AS existing_bom,  -- Use soi.bom_no, even if null
                bom_item.item_code AS bom_child_item_code,
                bom_item.description AS bom_child_description,
                bom_item.qty AS bom_child_qty,
                bom_item.uom AS bom_child_uom,
                bom_item.idx AS bom_item_idx
            FROM
                `tabSales Order` so
            INNER JOIN
                `tabSales Order Item` soi ON so.name = soi.parent
            LEFT JOIN
                `tabBOM` item_bom ON soi.item_code = item_bom.item
                    AND item_bom.is_active = 1
                    AND item_bom.docstatus = 1
                    AND (item_bom.custom_batch_no IS NULL OR item_bom.custom_batch_no = soi.custom_batch_no)
            LEFT JOIN
                `tabBOM Item` bom_item ON item_bom.name = bom_item.parent
                    AND (bom_item.custom_batch_no IS NULL OR bom_item.custom_batch_no = soi.custom_batch_no)
            LEFT JOIN
                `tabProduction Plan Sales Order` pps ON so.name = pps.sales_order
            LEFT JOIN
                `tabProduction Plan` pp ON pps.parent = pp.name
            WHERE
                so.docstatus = 1
                AND soi.custom_batch_no IS NOT NULL
                AND soi.custom_batch_no != ''
                AND (soi.bom_no IS NULL OR soi.bom_no = '')
                AND {conditions}
        )
        UNION ALL
        (
            -- Items with no BOMs at all
            SELECT 
                soi.custom_batch_no AS batch_no,
                pp.name AS production_plan,
                so.name AS sales_order,
                so.customer AS customer,
                so.transaction_date AS transaction_date,
                so.po_no AS po_no,
                so.total_qty AS total_qty,
                soi.item_code AS so_item_code,
                soi.description AS so_description,
                soi.qty AS so_qty,
                soi.uom AS so_uom,
                soi.bom_no AS bom_no,
                'No' AS has_bom,
                2 AS bom_docstatus,
                'Not Available' AS bom_status,
                soi.item_code AS bom_item_code,
                soi.description AS bom_description,
                soi.qty AS bom_quantity,
                soi.uom AS bom_uom,
                NULL AS effective_bom_no,
                soi.bom_no AS existing_bom,  -- Use soi.bom_no, even if null
                NULL AS bom_child_item_code,
                NULL AS bom_child_description,
                NULL AS bom_child_qty,
                NULL AS bom_child_uom,
                NULL AS bom_item_idx
            FROM
                `tabSales Order` so
            INNER JOIN
                `tabSales Order Item` soi ON so.name = soi.parent
            LEFT JOIN
                `tabProduction Plan Sales Order` pps ON so.name = pps.sales_order
            LEFT JOIN
                `tabProduction Plan` pp ON pps.parent = pp.name
            WHERE
                so.docstatus = 1
                AND soi.custom_batch_no IS NOT NULL
                AND soi.custom_batch_no != ''
                AND (soi.bom_no IS NULL OR soi.bom_no = '')
                AND NOT EXISTS (
                    SELECT 1 FROM `tabBOM` item_bom 
                    WHERE item_bom.item = soi.item_code 
                    AND item_bom.is_active = 1 
                    AND item_bom.docstatus = 1
                    AND (item_bom.custom_batch_no IS NULL OR item_bom.custom_batch_no = soi.custom_batch_no)
                )
                AND {conditions}
        )
        ORDER BY
            batch_no,
            transaction_date DESC, 
            sales_order, 
            so_item_code, 
            effective_bom_no, 
            bom_item_idx
    """.format(conditions=conditions)

    raw_data = frappe.db.sql(query, filters, as_dict=1)
    
    return build_original_tree(raw_data)

# def get_simple_batch_data(filters):
#     """Get simple table data when batch filter is applied"""
#     conditions = get_conditions(filters)
    
#     # Simple query to get all linked data for the batch
#     query = """
#         SELECT 
#             soi.custom_batch_no AS batch_no,
#             pp.name AS production_plan,
#             so.name AS sales_order,
#             so.customer AS customer,
#             so.transaction_date AS transaction_date,
#             so.po_no AS po_no,
#             soi.item_code AS so_item_code,
#             soi.description AS so_description,
#             soi.qty AS so_qty,
#             soi.uom AS so_uom,
#             soi.bom_no AS bom_no,
#             bom.name AS effective_bom_no,
#             COALESCE(soi.bom_no, item_bom.name) AS existing_bom,
#             bom.item AS bom_item_code,
#             bom.description AS bom_description,
#             bom.quantity AS bom_quantity,
#             bom.uom AS bom_uom,
#             bom.docstatus AS bom_docstatus,
#             CASE
#                 WHEN bom.docstatus = 0 THEN 'Draft'
#                 WHEN bom.docstatus = 1 THEN 'Submitted'
#                 WHEN bom.docstatus = 2 THEN 'Not Available'
#                 ELSE 'Not Available'
#             END AS bom_status,
#             CASE
#                 WHEN soi.bom_no IS NOT NULL AND soi.bom_no != '' THEN 'Yes'
#                 ELSE 'No'
#             END AS has_bom,
#             bom_item.item_code AS bom_child_item_code,
#             bom_item.description AS bom_child_description,
#             bom_item.qty AS bom_child_qty,
#             bom_item.uom AS bom_child_uom
#         FROM
#             `tabSales Order` so
#         INNER JOIN
#             `tabSales Order Item` soi ON so.name = soi.parent
#         LEFT JOIN
#             `tabBOM` bom ON soi.bom_no = bom.name
#         LEFT JOIN
#             `tabBOM Item` bom_item ON bom.name = bom_item.parent
#         LEFT JOIN
#             `tabBOM` item_bom ON item_bom.item = soi.item_code
#                 AND item_bom.is_active = 1
#                 AND item_bom.docstatus = 1
#         LEFT JOIN
#             `tabProduction Plan Sales Order` pps ON so.name = pps.sales_order
#         LEFT JOIN
#             `tabProduction Plan` pp ON pps.parent = pp.name
#         WHERE
#             so.docstatus = 1
#             AND soi.custom_batch_no IS NOT NULL
#             AND soi.custom_batch_no != ''
#             AND {conditions}
#         ORDER BY
#             soi.custom_batch_no,
#             so.transaction_date DESC,
#             so.name,
#             soi.item_code,
#             bom_item.idx
#     """.format(conditions=conditions)
    
#     raw_data = frappe.db.sql(query, filters, as_dict=1)
    
#     # Convert to simple table format
#     table_data = []
#     for row in raw_data:
#         table_data.append({
#             'level': 0,
#             'parent': '',
#             'is_group': 0,
#             'batch_no': row.get('batch_no', ''),
#             'production_plan': row.get('production_plan', ''),
#             'sales_order': row.get('sales_order', ''),
#             'customer': row.get('customer', ''),
#             'transaction_date': row.get('transaction_date', ''),
#             'po_no': row.get('po_no', ''),
#             'item_code': row.get('so_item_code', ''),
#             'description': row.get('so_description', ''),
#             'quantity': row.get('so_qty', ''),
#             'uom': row.get('so_uom', ''),
#             'bom_no': row.get('effective_bom_no', ''),
#             'bom_status': row.get('bom_status', ''),
#             'existing_bom': row.get('existing_bom', ''),
#             'has_bom': row.get('has_bom', ''),
#             'bom_item_code': row.get('bom_item_code', ''),
#             'bom_description': row.get('bom_description', ''),
#             'bom_quantity': row.get('bom_quantity', ''),
#             'bom_uom': row.get('bom_uom', ''),
#             'bom_child_item_code': row.get('bom_child_item_code', ''),
#             'bom_child_description': row.get('bom_child_description', ''),
#             'bom_child_qty': row.get('bom_child_qty', ''),
#             'bom_child_uom': row.get('bom_child_uom', ''),
#             'type': 'Linked Data'
#         })
    
#     return table_data

def get_simple_batch_data(filters):
    conditions = get_conditions(filters)
    
    query = """
        SELECT 
            soi.custom_batch_no AS batch_no,
            pp.name AS production_plan,
            so.name AS sales_order,
            so.customer AS customer,
            so.transaction_date AS transaction_date,
            so.po_no AS po_no,
            soi.item_code AS so_item_code,
            soi.description AS so_description,
            soi.qty AS so_qty,
            soi.uom AS so_uom,
            soi.bom_no AS bom_no,
            bom.name AS effective_bom_no,
            soi.bom_no AS existing_bom,  -- Use soi.bom_no directly for existing_bom
            bom.item AS bom_item_code,
            bom.description AS bom_description,
            bom.quantity AS bom_quantity,
            bom.uom AS bom_uom,
            bom.docstatus AS bom_docstatus,
            CASE
                WHEN bom.docstatus = 0 THEN 'Draft'
                WHEN bom.docstatus = 1 THEN 'Submitted'
                WHEN bom.docstatus = 2 THEN 'Not Available'
                ELSE 'Not Available'
            END AS bom_status,
            CASE
                WHEN soi.bom_no IS NOT NULL AND soi.bom_no != '' THEN 'Yes'
                ELSE 'No'
            END AS has_bom,
            bom_item.item_code AS bom_child_item_code,
            bom_item.description AS bom_child_description,
            bom_item.qty AS bom_child_qty,
            bom_item.uom AS bom_child_uom
        FROM
            `tabSales Order` so
        INNER JOIN
            `tabSales Order Item` soi ON so.name = soi.parent
        LEFT JOIN
            `tabBOM` bom ON soi.bom_no = bom.name
        LEFT JOIN
            `tabBOM Item` bom_item ON bom.name = bom_item.parent
        LEFT JOIN
            `tabProduction Plan Sales Order` pps ON so.name = pps.sales_order
        LEFT JOIN
            `tabProduction Plan` pp ON pps.parent = pp.name
        WHERE
            so.docstatus = 1
            AND soi.custom_batch_no IS NOT NULL
            AND soi.custom_batch_no != ''
            AND {conditions}
        ORDER BY
            soi.custom_batch_no,
            so.transaction_date DESC,
            so.name,
            soi.item_code,
            bom_item.idx
    """.format(conditions=conditions)
    
    raw_data = frappe.db.sql(query, filters, as_dict=1)
    
    table_data = []
    for row in raw_data:
        table_data.append({
            'level': 0,
            'parent': '',
            'is_group': 0,
            'batch_no': row.get('batch_no', ''),
            'production_plan': row.get('production_plan', ''),
            'sales_order': row.get('sales_order', ''),
            'customer': row.get('customer', ''),
            'transaction_date': row.get('transaction_date', ''),
            'po_no': row.get('po_no', ''),
            'item_code': row.get('so_item_code', ''),
            'description': row.get('so_description', ''),
            'quantity': row.get('so_qty', ''),
            'uom': row.get('so_uom', ''),
            'bom_no': row.get('effective_bom_no', ''),
            'bom_status': row.get('bom_status', ''),
            'existing_bom': row.get('existing_bom', ''), 
            'has_bom': row.get('has_bom', ''),
            'bom_item_code': row.get('bom_item_code', ''),
            'bom_description': row.get('bom_description', ''),
            'bom_quantity': row.get('bom_quantity', ''),
            'bom_uom': row.get('bom_uom', ''),
            'bom_child_item_code': row.get('bom_child_item_code', ''),
            'bom_child_description': row.get('bom_child_description', ''),
            'bom_child_qty': row.get('bom_child_qty', ''),
            'bom_child_uom': row.get('bom_child_uom', ''),
            'type': 'Linked Data'
        })
    
    return table_data

def get_data(filters):
    conditions = get_conditions(filters)
    
    # Check if batch number is selected
    batch_selected = filters.get("so_custom_batch_no") or filters.get("batch_no")
    
    # If batch is selected, use simple table format
    if batch_selected:
        return get_simple_batch_data(filters)
    
    # Get all batch data with related information - handle multiple BOMs per item
    query = """
        (
            -- Directly linked BOMs
            SELECT 
                soi.custom_batch_no AS batch_no,
                pp.name AS production_plan,
                so.name AS sales_order,
                so.customer AS customer,
                so.transaction_date AS transaction_date,
                so.po_no AS po_no,
                so.total_qty AS total_qty,
                soi.item_code AS so_item_code,
                soi.description AS so_description,
                soi.qty AS so_qty,
                soi.uom AS so_uom,
                soi.bom_no AS bom_no,
                'Yes' AS has_bom,
                bom.docstatus AS bom_docstatus,
                CASE
                    WHEN bom.docstatus = 0 THEN 'Draft'
                    WHEN bom.docstatus = 1 THEN 'Submitted'
                    WHEN bom.docstatus = 2 THEN 'Not Available'
                    ELSE 'Not Available'
                END AS bom_status,
                bom.item AS bom_item_code,
                bom.description AS bom_description,
                bom.quantity AS bom_quantity,
                bom.uom AS bom_uom,
                bom.name AS effective_bom_no,
                soi.bom_no AS existing_bom,
                bom_item.item_code AS bom_child_item_code,
                bom_item.description AS bom_child_description,
                bom_item.qty AS bom_child_qty,
                bom_item.uom AS bom_child_uom,
                bom_item.idx AS bom_item_idx
            FROM
                `tabSales Order` so
            INNER JOIN
                `tabSales Order Item` soi ON so.name = soi.parent
            LEFT JOIN
                `tabBOM` bom ON soi.bom_no = bom.name
                    AND (bom.custom_batch_no IS NULL OR bom.custom_batch_no = soi.custom_batch_no)
            LEFT JOIN
                `tabBOM Item` bom_item ON bom.name = bom_item.parent
                    AND (bom_item.custom_batch_no IS NULL OR bom_item.custom_batch_no = soi.custom_batch_no)
            -- Ensure alias exists for item_bom referenced in conditions
            LEFT JOIN
                `tabBOM` item_bom ON 1=0
            LEFT JOIN
                `tabProduction Plan Sales Order` pps ON so.name = pps.sales_order
            LEFT JOIN
                `tabProduction Plan` pp ON pps.parent = pp.name
            WHERE
                so.docstatus = 1
                AND soi.custom_batch_no IS NOT NULL
                AND soi.custom_batch_no != ''
                AND soi.bom_no IS NOT NULL
                AND soi.bom_no != ''
                AND {conditions}
        )
        UNION ALL
        (
            -- Item-based BOMs (when no direct BOM link)
            SELECT 
                soi.custom_batch_no AS batch_no,
                pp.name AS production_plan,
                so.name AS sales_order,
                so.customer AS customer,
                so.transaction_date AS transaction_date,
                so.po_no AS po_no,
                so.total_qty AS total_qty,
                soi.item_code AS so_item_code,
                soi.description AS so_description,
                soi.qty AS so_qty,
                soi.uom AS so_uom,
                soi.bom_no AS bom_no,
                'No' AS has_bom,
                item_bom.docstatus AS bom_docstatus,
                CASE
                    WHEN item_bom.docstatus = 0 THEN 'Draft'
                    WHEN item_bom.docstatus = 1 THEN 'Submitted'
                    WHEN item_bom.docstatus = 2 THEN 'Not Available'
                    ELSE 'Not Available'
                END AS bom_status,
                item_bom.item AS bom_item_code,
                item_bom.description AS bom_description,
                item_bom.quantity AS bom_quantity,
                item_bom.uom AS bom_uom,
                item_bom.name AS effective_bom_no,
                item_bom.name AS existing_bom,
                bom_item.item_code AS bom_child_item_code,
                bom_item.description AS bom_child_description,
                bom_item.qty AS bom_child_qty,
                bom_item.uom AS bom_child_uom,
                bom_item.idx AS bom_item_idx
            FROM
                `tabSales Order` so
            INNER JOIN
                `tabSales Order Item` soi ON so.name = soi.parent
            LEFT JOIN
                `tabBOM` item_bom ON soi.item_code = item_bom.item
                    AND item_bom.is_active = 1
                    AND item_bom.docstatus = 1
                    AND (item_bom.custom_batch_no IS NULL OR item_bom.custom_batch_no = soi.custom_batch_no)
            -- Ensure alias exists for bom referenced in conditions
            LEFT JOIN
                `tabBOM` bom ON 1=0
            LEFT JOIN
                `tabBOM Item` bom_item ON item_bom.name = bom_item.parent
                    AND (bom_item.custom_batch_no IS NULL OR bom_item.custom_batch_no = soi.custom_batch_no)
            LEFT JOIN
                `tabProduction Plan Sales Order` pps ON so.name = pps.sales_order
            LEFT JOIN
                `tabProduction Plan` pp ON pps.parent = pp.name
            WHERE
                so.docstatus = 1
                AND soi.custom_batch_no IS NOT NULL
                AND soi.custom_batch_no != ''
                AND (soi.bom_no IS NULL OR soi.bom_no = '')
                AND {conditions}
        )
        UNION ALL
        (
            -- Items with no BOMs at all
            SELECT 
                soi.custom_batch_no AS batch_no,
                pp.name AS production_plan,
                so.name AS sales_order,
                so.customer AS customer,
                so.transaction_date AS transaction_date,
                so.po_no AS po_no,
                so.total_qty AS total_qty,
                soi.item_code AS so_item_code,
                soi.description AS so_description,
                soi.qty AS so_qty,
                soi.uom AS so_uom,
                soi.bom_no AS bom_no,
                'No' AS has_bom,
                2 AS bom_docstatus,
                'Not Available' AS bom_status,
                soi.item_code AS bom_item_code,
                soi.description AS bom_description,
                soi.qty AS bom_quantity,
                soi.uom AS bom_uom,
                NULL AS effective_bom_no,
                NULL AS existing_bom,
                NULL AS bom_child_item_code,
                NULL AS bom_child_description,
                NULL AS bom_child_qty,
                NULL AS bom_child_uom,
                NULL AS bom_item_idx
            FROM
                `tabSales Order` so
            INNER JOIN
                `tabSales Order Item` soi ON so.name = soi.parent
            -- Ensure aliases exist for bom and item_bom referenced in conditions
            LEFT JOIN
                `tabBOM` bom ON 1=0
            LEFT JOIN
                `tabBOM` item_bom ON 1=0
            LEFT JOIN
                `tabProduction Plan Sales Order` pps ON so.name = pps.sales_order
            LEFT JOIN
                `tabProduction Plan` pp ON pps.parent = pp.name
            WHERE
                so.docstatus = 1
                AND soi.custom_batch_no IS NOT NULL
                AND soi.custom_batch_no != ''
                AND (soi.bom_no IS NULL OR soi.bom_no = '')
                AND NOT EXISTS (
                    SELECT 1 FROM `tabBOM` item_bom 
                    WHERE item_bom.item = soi.item_code 
                    AND item_bom.is_active = 1 
                    AND item_bom.docstatus = 1
                    AND (item_bom.custom_batch_no IS NULL OR item_bom.custom_batch_no = soi.custom_batch_no)
                )
                AND {conditions}
        )
        ORDER BY
            batch_no,
            transaction_date DESC, 
            sales_order, 
            so_item_code, 
            effective_bom_no, 
            bom_item_idx
    """.format(conditions=conditions)

    raw_data = frappe.db.sql(query, filters, as_dict=1)
    
    # Use original tree structure for non-batch filters
    return build_original_tree(raw_data)

def build_simplified_tree(raw_data):
    """Build simplified tree structure when batch is selected"""
    tree_data = []
    processed_groups = set()
    
    for row in raw_data:
        batch_no = row.get('batch_no')
        if not batch_no or batch_no.strip() == '':
            continue
            
        # Create a unique group key for each sales order + BOM combination
        group_key = f"{batch_no}|{row.get('sales_order')}|{row.get('production_plan', '')}|{row.get('effective_bom_no', '')}"
        
        if group_key not in processed_groups:
            processed_groups.add(group_key)
            
            # Add main group header (collapsible)
            header_text = f"SO: {row.get('sales_order')}"
            if row.get('production_plan'):
                header_text = f"PP: {row.get('production_plan')} | " + header_text
            if row.get('effective_bom_no'):
                header_text += f" | BOM: {row.get('effective_bom_no')}"
                
            tree_data.append({
                'level': 0,
                'parent': '',
                'is_group': 1,
                'batch_no': batch_no,
                'production_plan': row.get('production_plan', ''),
                'sales_order': row.get('sales_order', ''),
                'customer': row.get('customer', ''),
                'transaction_date': row.get('transaction_date', ''),
                'po_no': row.get('po_no', ''),
                'item_code': header_text,
                'description': '',
                'quantity': '',
                'uom': '',
                'bom_no': row.get('effective_bom_no', ''),
                'bom_status': row.get('bom_status', ''),
                'has_bom': row.get('has_bom', ''),
                'type': 'Sales Order'
            })
        
        # Add main item row
        if row.get('so_item_code'):
            tree_data.append({
                'level': 1,
                'parent': group_key,
                'is_group': 0,
                'batch_no': '',
                'production_plan': '',
                'sales_order': '',
                'customer': '',
                'transaction_date': '',
                'po_no': '',
                'item_code': row.get('so_item_code', ''),
                'description': row.get('so_description', ''),
                'quantity': row.get('so_qty', ''),
                'uom': row.get('so_uom', ''),
                'bom_no': '',
                'bom_status': '',
                'has_bom': '',
                'type': 'BOM'
            })
            
        # Add BOM child item row if exists
        if row.get('bom_child_item_code'):
            tree_data.append({
                'level': 1,
                'parent': group_key,
                'is_group': 0,
                'batch_no': '',
                'production_plan': '',
                'sales_order': '',
                'customer': '',
                'transaction_date': '',
                'po_no': '',
                'item_code': row.get('bom_child_item_code', ''),
                'description': row.get('bom_child_description', ''),
                'quantity': row.get('bom_child_qty', ''),
                'uom': row.get('bom_child_uom', ''),
                'bom_no': '',
                'bom_status': '',
                'has_bom': '',
                'type': 'BOM Item'
            })
    
    return tree_data

def build_original_tree(raw_data):
    tree_data = []
    batch_groups = {}
    
    for row in raw_data:
        batch_no = row.get('batch_no')
        if not batch_no or batch_no.strip() == '':
            continue
            
        if batch_no not in batch_groups:
            batch_groups[batch_no] = {
                'batch_no': batch_no,
                'production_plans': {},
                'sales_orders': {},
                'boms': {}
            }
        
        prod_plan = row.get('production_plan')
        if prod_plan and prod_plan not in batch_groups[batch_no]['production_plans']:
            batch_groups[batch_no]['production_plans'][prod_plan] = {
                'production_plan': prod_plan,
                'sales_orders': {}
            }
        
        sales_order = row.get('sales_order')
        if sales_order:
            if prod_plan and sales_order not in batch_groups[batch_no]['production_plans'][prod_plan]['sales_orders']:
                batch_groups[batch_no]['production_plans'][prod_plan]['sales_orders'][sales_order] = {
                    'sales_order': sales_order,
                    'customer': row.get('customer'),
                    'transaction_date': row.get('transaction_date'),
                    'po_no': row.get('po_no'),
                    'total_qty': row.get('total_qty'),
                    'boms': {}
                }
            elif not prod_plan and sales_order not in batch_groups[batch_no]['sales_orders']:
                batch_groups[batch_no]['sales_orders'][sales_order] = {
                    'sales_order': sales_order,
                    'customer': row.get('customer'),
                    'transaction_date': row.get('transaction_date'),
                    'po_no': row.get('po_no'),
                    'total_qty': row.get('total_qty'),
                    'boms': {}
                }
        
        effective_bom_no = row.get('effective_bom_no')
        has_bom = row.get('has_bom')
        
        if prod_plan and sales_order:
            target_boms = batch_groups[batch_no]['production_plans'][prod_plan]['sales_orders'][sales_order]['boms']
        elif not prod_plan and sales_order:
            target_boms = batch_groups[batch_no]['sales_orders'][sales_order]['boms']
        else:
            target_boms = None

        if target_boms is not None:
            bom_key = effective_bom_no if effective_bom_no else f"NO_BOM_{row.get('so_item_code')}"
            
            if bom_key not in target_boms:
                target_boms[bom_key] = {
                    'bom_no': effective_bom_no if effective_bom_no else '',
                    'bom_status': row.get('bom_status'),
                    'has_bom': has_bom,
                    'item_code': row.get('so_item_code'),
                    'description': row.get('so_description'),
                    'quantity': row.get('so_qty'),
                    'uom': row.get('so_uom'),
                    'existing_bom': row.get('existing_bom'), 
                    'bom_items': []
                }

            if row.get('bom_child_item_code'):
                target_boms[bom_key]['bom_items'].append({
                    'item_code': row.get('bom_child_item_code'),
                    'description': row.get('bom_child_description'),
                    'quantity': row.get('bom_child_qty'),
                    'uom': row.get('bom_child_uom')
                })
    
    for batch_no, batch_data in batch_groups.items():
        tree_data.append({
            'level': 0,
            'parent': '',
            'is_group': 1,
            'batch_no': batch_no,
            'production_plan': '',
            'sales_order': '',
            'customer': '',
            'transaction_date': '',
            'po_no': '',
            'item_code': '',
            'description': '',
            'quantity': '',
            'uom': '',
            'bom_no': '',
            'bom_status': '',
            'existing_bom': '',
            'has_bom': '',
            'type': 'Batch'
        })
        
        for prod_plan, prod_data in batch_data['production_plans'].items():
            tree_data.append({
                'level': 1,
                'parent': batch_no,
                'is_group': 1,
                'batch_no': '',
                'production_plan': prod_plan,
                'sales_order': '',
                'customer': '',
                'transaction_date': '',
                'po_no': '',
                'item_code': '',
                'description': '',
                'quantity': '',
                'uom': '',
                'bom_no': '',
                'bom_status': '',
                'existing_bom': '',
                'has_bom': '',
                'type': 'Production Plan'
            })
            
            for sales_order, so_data in prod_data['sales_orders'].items():
                tree_data.append({
                    'level': 2,
                    'parent': prod_plan,
                    'is_group': 1,
                    'batch_no': '',
                    'production_plan': '',
                    'sales_order': sales_order,
                    'customer': so_data['customer'],
                    'transaction_date': so_data['transaction_date'],
                    'po_no': so_data['po_no'],
                    'item_code': '',
                    'description': '',
                    'quantity': '',
                    'uom': '',
                    'bom_no': '',
                    'bom_status': '',
                    'existing_bom': '',
                    'has_bom': '',
                    'type': 'Sales Order'
                })
                
                for bom_key, bom_data in so_data['boms'].items():
                    tree_data.append({
                        'level': 3,
                        'parent': sales_order,
                        'is_group': 1,
                        'batch_no': '',
                        'production_plan': '',
                        'sales_order': '',
                        'customer': '',
                        'transaction_date': '',
                        'po_no': '',
                        'item_code': bom_data['item_code'],
                        'description': bom_data['description'],
                        'quantity': bom_data['quantity'],
                        'uom': bom_data['uom'],
                        'bom_no': bom_data['bom_no'],
                        'bom_status': bom_data['bom_status'],
                        'existing_bom': bom_data['existing_bom'], 
                        'has_bom': bom_data['has_bom'],
                        'type': 'BOM'
                    })
                    
                    for bom_item in bom_data['bom_items']:
                        tree_data.append({
                            'level': 4,
                            'parent': bom_key,
                            'is_group': 0,
                            'batch_no': '',
                            'production_plan': '',
                            'sales_order': '',
                            'customer': '',
                            'transaction_date': '',
                            'po_no': '',
                            'item_code': bom_item['item_code'],
                            'description': bom_item['description'],
                            'quantity': bom_item['quantity'],
                            'uom': bom_item['uom'],
                            'bom_no': '',
                            'bom_status': '',
                            'existing_bom': '',
                            'has_bom': '',
                            'type': 'BOM Item'
                        })
        
        for sales_order, so_data in batch_data['sales_orders'].items():
            tree_data.append({
                'level': 1,
                'parent': batch_no,
                'is_group': 1,
                'batch_no': '',
                'production_plan': '',
                'sales_order': sales_order,
                'customer': so_data['customer'],
                'transaction_date': so_data['transaction_date'],
                'po_no': so_data['po_no'],
                'item_code': '',
                'description': '',
                'quantity': '',
                'uom': '',
                'bom_no': '',
                'bom_status': '',
                'existing_bom': '',
                'has_bom': '',
                'type': 'Sales Order'
            })
            
            for bom_key, bom_data in so_data['boms'].items():
                tree_data.append({
                    'level': 2,
                    'parent': sales_order,
                    'is_group': 1,
                    'batch_no': '',
                    'production_plan': '',
                    'sales_order': '',
                    'customer': '',
                    'transaction_date': '',
                    'po_no': '',
                    'item_code': bom_data['item_code'],
                    'description': bom_data['description'],
                    'quantity': bom_data['quantity'],
                    'uom': bom_data['uom'],
                    'bom_no': bom_data['bom_no'],
                    'bom_status': bom_data['bom_status'],
                    'existing_bom': bom_data['existing_bom'], 
                    'has_bom': bom_data['has_bom'],
                    'type': 'BOM'
                })
                
                for bom_item in bom_data['bom_items']:
                    tree_data.append({
                        'level': 3,
                        'parent': bom_key,
                        'is_group': 0,
                        'batch_no': '',
                        'production_plan': '',
                        'sales_order': '',
                        'customer': '',
                        'transaction_date': '',
                        'po_no': '',
                        'item_code': bom_item['item_code'],
                        'description': bom_item['description'],
                        'quantity': bom_item['quantity'],
                        'uom': bom_item['uom'],
                        'bom_no': '',
                        'bom_status': '',
                        'existing_bom': '',
                        'has_bom': '',
                        'type': 'BOM Item'
                    })

    return tree_data

# def build_original_tree(raw_data):
#     """Build original hierarchical tree structure when no batch is selected"""
#     tree_data = []
#     batch_groups = {}
    
#     for row in raw_data:
#         batch_no = row.get('batch_no')
#         # Only process rows that have a valid batch number (not null or empty)
#         if not batch_no or batch_no.strip() == '':
#             continue
            
#         # Group by batch
#         if batch_no not in batch_groups:
#             batch_groups[batch_no] = {
#                 'batch_no': batch_no,
#                 'production_plans': {},
#                 'sales_orders': {},
#                 'boms': {}
#             }
        
#         # Add production plan
#         prod_plan = row.get('production_plan')
#         if prod_plan and prod_plan not in batch_groups[batch_no]['production_plans']:
#             batch_groups[batch_no]['production_plans'][prod_plan] = {
#                 'production_plan': prod_plan,
#                 'sales_orders': {}
#             }
        
#         # Add sales order
#         sales_order = row.get('sales_order')
#         if sales_order:
#             if prod_plan and sales_order not in batch_groups[batch_no]['production_plans'][prod_plan]['sales_orders']:
#                 batch_groups[batch_no]['production_plans'][prod_plan]['sales_orders'][sales_order] = {
#                     'sales_order': sales_order,
#                     'customer': row.get('customer'),
#                     'transaction_date': row.get('transaction_date'),
#                     'po_no': row.get('po_no'),
#                     'total_qty': row.get('total_qty'),
#                     'boms': {}
#                 }
#             elif not prod_plan and sales_order not in batch_groups[batch_no]['sales_orders']:
#                 batch_groups[batch_no]['sales_orders'][sales_order] = {
#                     'sales_order': sales_order,
#                     'customer': row.get('customer'),
#                     'transaction_date': row.get('transaction_date'),
#                     'po_no': row.get('po_no'),
#                     'total_qty': row.get('total_qty'),
#                     'boms': {}
#                 }
        
#         # Add BOM details - use effective BOM (either linked or found by item)
#         effective_bom_no = row.get('effective_bom_no')
#         has_bom = row.get('has_bom')
        
#         # Pick target map depending on production plan presence
#         if prod_plan and sales_order:
#             target_boms = batch_groups[batch_no]['production_plans'][prod_plan]['sales_orders'][sales_order]['boms']
#         elif not prod_plan and sales_order:
#             target_boms = batch_groups[batch_no]['sales_orders'][sales_order]['boms']
#         else:
#             target_boms = None

#         if target_boms is not None:
#             # Use effective BOM or create a key for items without BOM
#             bom_key = effective_bom_no if effective_bom_no else f"NO_BOM_{row.get('so_item_code')}"
            
#             # Initialize or fetch existing BOM aggregate for this sales order + batch
#             if bom_key not in target_boms:
#                 target_boms[bom_key] = {
#                     'bom_no': effective_bom_no if effective_bom_no else '',
#                     'bom_status': row.get('bom_status'),
#                     'has_bom': has_bom,
#                     'item_code': row.get('so_item_code'),
#                     'description': row.get('so_description'),
#                     'quantity': row.get('so_qty'),
#                     'uom': row.get('so_uom'),
#                     'bom_items': []
#                 }

#             # Append child item if present
#             if row.get('bom_child_item_code'):
#                 target_boms[bom_key]['bom_items'].append({
#                     'item_code': row.get('bom_child_item_code'),
#                     'description': row.get('bom_child_description'),
#                     'quantity': row.get('bom_child_qty'),
#                     'uom': row.get('bom_child_uom')
#                 })
    
#     # Convert to tree structure
#     for batch_no, batch_data in batch_groups.items():
#         # Add batch header
#         tree_data.append({
#             'level': 0,
#             'parent': '',
#             'is_group': 1,
#             'batch_no': batch_no,
#             'production_plan': '',
#             'sales_order': '',
#             'customer': '',
#             'transaction_date': '',
#             'po_no': '',
#             'item_code': '',
#             'description': '',
#             'quantity': '',
#             'uom': '',
#             'bom_no': '',
#             'bom_status': '',
#             'existing_bom': '',
#             'has_bom': '',
#             'type': 'Batch'
#         })
        
#         # Add production plans
#         for prod_plan, prod_data in batch_data['production_plans'].items():
#             tree_data.append({
#                 'level': 1,
#                 'parent': batch_no,
#                 'is_group': 1,
#                 'batch_no': '',
#                 'production_plan': prod_plan,
#                 'sales_order': '',
#                 'customer': '',
#                 'transaction_date': '',
#                 'po_no': '',
#                 'item_code': '',
#                 'description': '',
#                 'quantity': '',
#                 'uom': '',
#                 'bom_no': '',
#                 'bom_status': '',
#                 'existing_bom': '',
#                 'has_bom': '',
#                 'type': 'Production Plan'
#             })
            
#             # Add sales orders under production plan
#             for sales_order, so_data in prod_data['sales_orders'].items():
#                 tree_data.append({
#                     'level': 2,
#                     'parent': prod_plan,
#                     'is_group': 1,
#                     'batch_no': '',
#                     'production_plan': '',
#                     'sales_order': sales_order,
#                     'customer': so_data['customer'],
#                     'transaction_date': so_data['transaction_date'],
#                     'po_no': so_data['po_no'],
#                     'item_code': '',
#                     'description': '',
#                     'quantity': '',
#                     'uom': '',
#                     'bom_no': '',
#                     'bom_status': '',
#                     'existing_bom': '',
#                     'has_bom': '',
#                     'type': 'Sales Order'
#                 })
                
#                 # Add BOM details under sales order
#                 for bom_key, bom_data in so_data['boms'].items():
#                     tree_data.append({
#                         'level': 3,
#                         'parent': sales_order,
#                         'is_group': 1,
#                         'batch_no': '',
#                         'production_plan': '',
#                         'sales_order': '',
#                         'customer': '',
#                         'transaction_date': '',
#                         'po_no': '',
#                         'item_code': bom_data['item_code'],
#                         'description': bom_data['description'],
#                         'quantity': bom_data['quantity'],
#                         'uom': bom_data['uom'],
#                         'bom_no': bom_data['bom_no'],
#                         'bom_status': bom_data['bom_status'],
#                         'existing_bom': bom_data['bom_no'],
#                         'has_bom': bom_data['has_bom'],
#                         'type': 'BOM'
#                     })
                    
#                     # Add BOM child items
#                     for bom_item in bom_data['bom_items']:
#                         tree_data.append({
#                             'level': 4,
#                             'parent': bom_key,
#                             'is_group': 0,
#                             'batch_no': '',
#                             'production_plan': '',
#                             'sales_order': '',
#                             'customer': '',
#                             'transaction_date': '',
#                             'po_no': '',
#                             'item_code': bom_item['item_code'],
#                             'description': bom_item['description'],
#                             'quantity': bom_item['quantity'],
#                             'uom': bom_item['uom'],
#                             'bom_no': '',
#                             'bom_status': '',
#                             'existing_bom': '',
#                             'has_bom': '',
#                             'type': 'BOM Item'
#                         })
        
#         # Add sales orders without production plan
#         for sales_order, so_data in batch_data['sales_orders'].items():
#             tree_data.append({
#                 'level': 1,
#                 'parent': batch_no,
#                 'is_group': 1,
#                 'batch_no': '',
#                 'production_plan': '',
#                 'sales_order': sales_order,
#                 'customer': so_data['customer'],
#                 'transaction_date': so_data['transaction_date'],
#                 'po_no': so_data['po_no'],
#                 'item_code': '',
#                 'description': '',
#                 'quantity': '',
#                 'uom': '',
#                 'bom_no': '',
#                 'bom_status': '',
#                 'existing_bom': '',
#                 'has_bom': '',
#                 'type': 'Sales Order'
#             })
            
#             # Add BOM details under sales order
#             for bom_key, bom_data in so_data['boms'].items():
#                 tree_data.append({
#                     'level': 2,
#                     'parent': sales_order,
#                     'is_group': 1,
#                     'batch_no': '',
#                     'production_plan': '',
#                     'sales_order': '',
#                     'customer': '',
#                     'transaction_date': '',
#                     'po_no': '',
#                     'item_code': bom_data['item_code'],
#                     'description': bom_data['description'],
#                     'quantity': bom_data['quantity'],
#                     'uom': bom_data['uom'],
#                     'bom_no': bom_data['bom_no'],
#                     'bom_status': bom_data['bom_status'],
#                     'existing_bom': bom_data['bom_no'],
#                     'has_bom': bom_data['has_bom'],
#                     'type': 'BOM'
#                 })
                
#                 # Add BOM child items
#                 for bom_item in bom_data['bom_items']:
#                     tree_data.append({
#                         'level': 3,
#                         'parent': bom_key,
#                         'is_group': 0,
#                         'batch_no': '',
#                         'production_plan': '',
#                         'sales_order': '',
#                         'customer': '',
#                         'transaction_date': '',
#                         'po_no': '',
#                         'item_code': bom_item['item_code'],
#                         'description': bom_item['description'],
#                         'quantity': bom_item['quantity'],
#                         'uom': bom_item['uom'],
#                         'bom_no': '',
#                         'bom_status': '',
#                         'existing_bom': '',
#                         'has_bom': '',
#                         'type': 'BOM Item'
#                     })

#     return tree_data

def get_conditions(filters):
    conditions = []

    if filters.get("sales_order"):
        conditions.append("so.name = %(sales_order)s")
    
    if filters.get("production_plan"):
        conditions.append("pp.name = %(production_plan)s")
    
    if filters.get("customer"):
        conditions.append("so.customer = %(customer)s")
    
    if filters.get("from_date") and filters.get("to_date"):
        conditions.append("so.transaction_date BETWEEN %(from_date)s AND %(to_date)s")
    
    if filters.get("so_item_code"):
        conditions.append("soi.item_code = %(so_item_code)s")
    
    if filters.get("so_description"):
        conditions.append("soi.description LIKE %(so_description)s")
    
    if filters.get("bom_custom_batch_no"):
        conditions.append("COALESCE(bom.custom_batch_no, item_bom.custom_batch_no) = %(bom_custom_batch_no)s")
        
    if filters.get("so_custom_batch_no"):
        conditions.append("soi.custom_batch_no = %(so_custom_batch_no)s")
        
    if filters.get("batch_no"):
        conditions.append("soi.custom_batch_no = %(batch_no)s")
    
    if filters.get("bom_no"):
        conditions.append("(soi.bom_no = %(bom_no)s OR item_bom.name = %(bom_no)s)")
    
    if filters.get("bom_status"):
        status_conditions = []
        status_map = {"Draft": 0, "Submitted": 1, "Not Available": 2}
        for status in filters.get("bom_status"):
            if status == "Not Available":
                status_conditions.append("(COALESCE(bom.docstatus, item_bom.docstatus, 2) = 2)")
            else:
                if status in status_map:
                    status_conditions.append("COALESCE(bom.docstatus, item_bom.docstatus, 2) = {}".format(status_map[status]))
        if status_conditions:
            conditions.append("({})".format(" OR ".join(status_conditions)))

    return " AND ".join(conditions) if conditions else "1=1"