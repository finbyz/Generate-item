# Copyright (c) 2025, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, date_diff, nowdate, formatdate


def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()

    if not filters.get("branch"):
        return columns, [], None, None, []

    base_data = get_base_data(filters)
    if not base_data:
        return columns, [], None, None, []

    batch_numbers = list({r["custom_batch_no"] for r in base_data if r.get("custom_batch_no")})
    pp_numbers = list({r["production_plan_no"] for r in base_data if r.get("production_plan_no")})
    item_codes = list({r["input_item_code"] for r in base_data if r.get("input_item_code")})

    mr_data_map, all_mr_item_names, mr_item_to_batch = get_material_request_data(batch_numbers, pp_numbers, item_codes)
    po_data_map, all_po_item_names, po_item_to_batch, all_po_names, po_to_batch = get_purchase_order_data(batch_numbers, all_mr_item_names, item_codes, mr_item_to_batch)
    pr_data_map = get_purchase_receipt_data(all_po_item_names, all_po_names, batch_numbers, item_codes, po_item_to_batch, po_to_batch)
    stock_map = get_stock_data(filters, item_codes)

    data = build_final_data(base_data, mr_data_map, po_data_map, pr_data_map, stock_map)

    data = apply_age_filter(data, filters)

    chart = get_chart_data(data, filters)
    summary = get_report_summary(data)

    return columns, data, None, chart, summary


def get_columns():
    """Define all report columns matching exact requested layout"""
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
            "fieldname": "production_plan_no",
            "label": _("Production Plan No."),
            "fieldtype": "Link",
            "options": "Production Plan",
            "width": 150
        },
        {
            "fieldname": "pp_status",
            "label": _("Production Plan Status"),
            "fieldtype": "Data",
            "width": 150
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
            "width": 100
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
            "width": 140
        },
        {
            "fieldname": "fg_to_be_produce_qty",
            "label": _("FG To be Produce Qty"),
            "fieldtype": "Float",
            "width": 130
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
            "fieldname": "balance_to_issue_qty",
            "label": _("Balance to Issue Qty"),
            "fieldtype": "Float",
            "width": 130
        },
        {
            "fieldname": "on_hand_qty",
            "label": _("On hand Qty"),
            "fieldtype": "Float",
            "width": 110
        },
        {
            "fieldname": "purchase_mr_qty",
            "label": _("Purchase MR Qty"),
            "fieldtype": "Float",
            "width": 130
        },
        {
            "fieldname": "purchase_mr_no",
            "label": _("Purchase MR No. "),
            "fieldtype": "Data",
            "width": 160
        },
        {
            "fieldname": "po_qty",
            "label": _("PO Qty"),
            "fieldtype": "Float",
            "width": 120
        },
        {
            "fieldname": "po_no",
            "label": _("PO No"),
            "fieldtype": "Data",
            "width": 150
        },
        {
            "fieldname": "po_date",
            "label": _("PO Date"),
            "fieldtype": "Date",
            "width": 130
        },
        {
            "fieldname": "po_line_no",
            "label": _("PO Line No"),
            "fieldtype": "Data",
            "width": 110
        },
        {
            "fieldname": "received_qty",
            "label": _("Received Qty"),
            "fieldtype": "Float",
            "width": 120
        },
        {
            "fieldname": "receipt_draft_qty",
            "label": _("Receipt Draft Qty"),
            "fieldtype": "Float",
            "width": 130
        },
        {
            "fieldname": "supplier_name",
            "label": _("Supplier Name"),
            "fieldtype": "Data",
            "width": 180
        },
        {
            "fieldname": "transfer_request_qty",
            "label": _("Transfer Request  Qty"),
            "fieldtype": "Float",
            "width": 140
        },
        {
            "fieldname": "transfer_request_no",
            "label": _("Transfer Request  no"),
            "fieldtype": "Data",
            "width": 160
        },
        {
            "fieldname": "required_by",
            "label": _("Required By"),
            "fieldtype": "Date",
            "width": 140
        }
    ]


def get_base_data(filters):
    """Fetch base Work Order and Work Order Item details matching filters"""
    conditions = get_conditions(filters)

    return frappe.db.sql(f"""
        SELECT
            pp.name AS production_plan_no,
            pp.status AS pp_status,
            pp.posting_date AS pp_date,
            pp.company,

            wo.name AS work_order,
            wo.production_item AS fg_code,
            wo.custom_batch_no,
            wo.sales_order AS so_no,
            wo.qty AS fg_to_be_produce_qty,
            wo.status,
            wo.branch,
            wo.actual_start_date,
            wo.planned_start_date,
            DATE(wo.creation) AS wo_creation_date,

            woi.name AS woi_name,
            woi.item_code AS input_item_code,
            woi.description AS input_item_description,
            woi.stock_uom AS uom,
            woi.custom_drawing_no,
            woi.custom_drawing_rev_no,
            COALESCE(woi.required_qty, 0) AS total_req_qty,
            COALESCE(woi.transferred_qty, 0) AS issued_qty,

            CASE
                WHEN woi.item_code IS NOT NULL AND wo.qty > 0
                THEN (woi.required_qty / wo.qty)
                ELSE 0
            END AS per_valve_input

        FROM `tabProduction Plan` pp
        JOIN `tabWork Order` wo
            ON wo.production_plan = pp.name
            AND wo.docstatus < 2
        JOIN `tabWork Order Item` woi
            ON woi.parent = wo.name
        WHERE
            pp.docstatus < 2
            {conditions}
        ORDER BY
            pp.posting_date DESC,
            wo.planned_start_date ASC,
            wo.name ASC,
            woi.idx ASC
    """, filters, as_dict=True)


def get_conditions(filters):
    """Build SQL conditions from filters"""
    conditions = []

    if filters.get("company"):
        conditions.append("AND pp.company = %(company)s")

    if filters.get("status"):
        conditions.append("AND (wo.status = %(status)s OR pp.status = %(status)s)")
    else:
        conditions.append("AND wo.status NOT IN ('Stopped', 'Closed', 'Completed')")
        conditions.append("AND pp.status NOT IN ('Cancelled', 'Closed', 'Completed')")

    if filters.get("production_item"):
        conditions.append("AND wo.production_item = %(production_item)s")

    if filters.get("sales_order"):
        conditions.append("AND wo.sales_order = %(sales_order)s")

    if filters.get("custom_batch_no"):
        conditions.append("AND wo.custom_batch_no = %(custom_batch_no)s")

    if filters.get("branch"):
        conditions.append("AND wo.branch = %(branch)s")

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


def get_material_request_data(batch_numbers, pp_numbers, item_codes):
    """
    Fetch Material Request Items batch-wise.
    Separates into Purchase MR vs Transfer MR.
    Uses stock_qty for quantities.
    """
    mr_map = {}
    all_mr_item_names = set()
    mr_item_to_batch = {}

    if not item_codes or (not batch_numbers and not pp_numbers):
        return mr_map, all_mr_item_names, mr_item_to_batch

    params = {"item_codes": tuple(item_codes)}
    or_clauses = []
    if batch_numbers:
        or_clauses.append("mri.custom_batch_no IN %(batch_numbers)s")
        params["batch_numbers"] = tuple(batch_numbers)
    if pp_numbers:
        or_clauses.append("mri.production_plan IN %(pp_numbers)s")
        params["pp_numbers"] = tuple(pp_numbers)

    where_clause = f"({' OR '.join(or_clauses)})"

    mr_rows = frappe.db.sql(f"""
        SELECT
            mri.name AS mri_name,
            mri.parent AS mr_name,
            mri.item_code,
            COALESCE(mri.stock_qty, mri.qty, 0) AS stock_qty,
            mri.custom_batch_no,
            mri.production_plan,
            mr.material_request_type,
            mr.transaction_date
        FROM `tabMaterial Request Item` mri
        JOIN `tabMaterial Request` mr ON mr.name = mri.parent
        WHERE
            mr.docstatus < 2
            AND mr.material_request_type IN ('Purchase', 'Material Transfer')
            AND mri.item_code IN %(item_codes)s
            AND {where_clause}
        ORDER BY mr.transaction_date ASC, mr.name ASC
    """, params, as_dict=True)

    for row in mr_rows:
        mri_name = row.mri_name
        item_code = row.item_code
        batch_no = row.custom_batch_no
        pp_no = row.production_plan
        mr_type = row.material_request_type
        mr_name = row.mr_name
        qty = flt(row.stock_qty)

        all_mr_item_names.add(mri_name)

        target_keys = []
        if batch_no:
            target_keys.append((batch_no, item_code))
            mr_item_to_batch[mri_name] = (batch_no, item_code)
        elif pp_no:
            target_keys.append((pp_no, item_code))
            mr_item_to_batch[mri_name] = (pp_no, item_code)

        for key in target_keys:
            if key not in mr_map:
                mr_map[key] = {
                    "purchase_mr_qty": 0.0,
                    "purchase_mr_nos": [],
                    "transfer_request_qty": 0.0,
                    "transfer_request_nos": [],
                    "mr_item_names": set()
                }

            entry = mr_map[key]
            entry["mr_item_names"].add(mri_name)

            if mr_type == "Purchase":
                entry["purchase_mr_qty"] += qty
                if mr_name and mr_name not in entry["purchase_mr_nos"]:
                    entry["purchase_mr_nos"].append(mr_name)
            elif mr_type == "Material Transfer":
                entry["transfer_request_qty"] += qty
                if mr_name and mr_name not in entry["transfer_request_nos"]:
                    entry["transfer_request_nos"].append(mr_name)

    return mr_map, all_mr_item_names, mr_item_to_batch


def get_purchase_order_data(batch_numbers, all_mr_item_names, item_codes, mr_item_to_batch):
    """
    Fetch Purchase Order Items batch-wise.
    Uses stock_qty for PO quantities.
    Aggregates PO No, PO Date, PO Line No, Supplier Name, PO Qty, Required By.
    """
    po_map = {}
    all_po_item_names = set()
    po_item_to_batch = {}
    po_to_batch = {}
    all_po_names = set()

    if not item_codes or (not batch_numbers and not all_mr_item_names):
        return po_map, all_po_item_names, po_item_to_batch, all_po_names, po_to_batch

    params = {"item_codes": tuple(item_codes)}
    or_clauses = []
    if batch_numbers:
        or_clauses.append("poi.custom_batch_no IN %(batch_numbers)s")
        params["batch_numbers"] = tuple(batch_numbers)
    if all_mr_item_names:
        or_clauses.append("poi.material_request_item IN %(mr_item_names)s")
        params["mr_item_names"] = tuple(all_mr_item_names)

    where_clause = f"({' OR '.join(or_clauses)})"

    po_rows = frappe.db.sql(f"""
        SELECT
            poi.name AS poi_name,
            poi.parent AS po_no,
            poi.item_code,
            COALESCE(poi.stock_qty, poi.qty, 0) AS stock_qty,
            COALESCE(poi.received_qty_in_stock_uom, poi.received_qty, 0) AS po_received_qty,
            poi.custom_batch_no,
            poi.material_request_item,
            COALESCE(poi.po_line_no, poi.idx) AS po_line_no,
            poi.schedule_date AS required_by,
            po.transaction_date,
            po.supplier_name
        FROM `tabPurchase Order Item` poi
        JOIN `tabPurchase Order` po ON po.name = poi.parent
        WHERE
            po.docstatus < 2
            AND poi.item_code IN %(item_codes)s
            AND {where_clause}
        ORDER BY po.transaction_date ASC, po.name ASC, poi.idx ASC
    """, params, as_dict=True)

    for row in po_rows:
        poi_name = row.poi_name
        po_no = row.po_no
        item_code = row.item_code
        batch_no = row.custom_batch_no
        mr_item = row.material_request_item
        po_date = formatdate(row.transaction_date, "dd-MM-yyyy") if row.transaction_date else ""
        po_line_no = str(row.po_line_no) if row.po_line_no is not None else ""
        supplier = row.supplier_name or ""
        qty = flt(row.stock_qty)
        rec_qty = flt(row.po_received_qty)
        required_by = row.required_by

        all_po_item_names.add(poi_name)
        if po_no:
            all_po_names.add(po_no)

        target_keys = []
        if batch_no:
            target_keys.append((batch_no, item_code))
            po_item_to_batch[poi_name] = (batch_no, item_code)
            if po_no:
                po_to_batch[po_no] = (batch_no, item_code)
        elif mr_item and mr_item in mr_item_to_batch:
            matched_key = mr_item_to_batch[mr_item]
            target_keys.append(matched_key)
            po_item_to_batch[poi_name] = matched_key
            if po_no:
                po_to_batch[po_no] = matched_key

        for key in target_keys:
            if key not in po_map:
                po_map[key] = {
                    "po_qty": 0.0,
                    "po_received_qty": 0.0,
                    "po_nos": [],
                    "po_dates": [],
                    "po_line_nos": [],
                    "suppliers": [],
                    "po_item_names": set(),
                    "required_by": None
                }

            entry = po_map[key]
            entry["po_qty"] += qty
            entry["po_received_qty"] += rec_qty
            entry["po_item_names"].add(poi_name)

            if po_no and po_no not in entry["po_nos"]:
                entry["po_nos"].append(po_no)
            if po_date and po_date not in entry["po_dates"]:
                entry["po_dates"].append(po_date)
            if po_line_no and po_line_no not in entry["po_line_nos"]:
                entry["po_line_nos"].append(po_line_no)
            if supplier and supplier not in entry["suppliers"]:
                entry["suppliers"].append(supplier)
            if required_by:
                if not entry["required_by"] or required_by < entry["required_by"]:
                    entry["required_by"] = required_by

    return po_map, all_po_item_names, po_item_to_batch, all_po_names, po_to_batch


def get_purchase_receipt_data(all_po_item_names, all_po_names, batch_numbers, item_codes, po_item_to_batch, po_to_batch):
    """
    Fetch Purchase Receipt Items batch-wise.
    Splits into:
    - Submitted receipts (docstatus = 1) -> received_qty (uses received_stock_qty)
    - Draft receipts (docstatus = 0) -> receipt_draft_qty (uses stock_qty)
    """
    pr_map = {}

    if not item_codes or (not all_po_item_names and not all_po_names):
        return pr_map

    params = {"item_codes": tuple(item_codes)}
    or_clauses = []
    if all_po_item_names:
        or_clauses.append("pri.purchase_order_item IN %(po_item_names)s")
        params["po_item_names"] = tuple(all_po_item_names)
    if all_po_names:
        or_clauses.append("pri.purchase_order IN %(po_names)s")
        params["po_names"] = tuple(all_po_names)

    where_clause = f"({' OR '.join(or_clauses)})"

    pr_rows = frappe.db.sql(f"""
        SELECT
            pri.name AS pri_name,
            pri.parent AS pr_name,
            pri.item_code,
            pri.purchase_order,
            pri.purchase_order_item,
            COALESCE(pri.received_stock_qty, 0) AS received_stock_qty,
            COALESCE(pri.stock_qty,  0) AS stock_qty,
            pr.docstatus
        FROM `tabPurchase Receipt Item` pri
        JOIN `tabPurchase Receipt` pr ON pr.name = pri.parent
        WHERE
            pr.docstatus IN (0, 1)
            AND pri.item_code IN %(item_codes)s
            AND {where_clause}
    """, params, as_dict=True)

    seen_pri = set()
    for row in pr_rows:
        if row.pri_name in seen_pri:
            continue
        seen_pri.add(row.pri_name)

        poi_name = row.purchase_order_item
        po_name = row.purchase_order
        docstatus = row.docstatus

        target_key = po_item_to_batch.get(poi_name) or po_to_batch.get(po_name)
        if not target_key:
            continue

        if target_key not in pr_map:
            pr_map[target_key] = {
                "received_qty": 0.0,
                "receipt_draft_qty": 0.0
            }

        if docstatus == 1:
            pr_map[target_key]["received_qty"] += flt(row.stock_qty)
        elif docstatus == 0:
            pr_map[target_key]["receipt_draft_qty"] += flt(row.stock_qty)

    return pr_map


def get_stock_data(filters, item_codes):
    """Fetch on-hand warehouse stock for RM and Store warehouses"""
    if not item_codes or not filters.get("branch") or not filters.get("company"):
        return {}

    data = frappe.db.sql("""
        SELECT
            bin.item_code,
            SUM(bin.actual_qty) AS qty
        FROM `tabBin` bin
        JOIN `tabWarehouse` wh
            ON wh.name = bin.warehouse
        WHERE
            (wh.raw_material_warehouse = 1 OR wh.store_warehouse = 1)
            AND wh.branch = %(branch)s
            AND wh.company = %(company)s
            AND bin.item_code IN %(item_codes)s
        GROUP BY
            bin.item_code
    """, {
        "branch": filters.get("branch"),
        "company": filters.get("company"),
        "item_codes": tuple(item_codes)
    }, as_dict=True)

    return {d.item_code: flt(d.qty) for d in data}


def build_final_data(base_data, mr_data_map, po_data_map, pr_data_map, stock_map):
    """Assemble final rows with batch-wise aggregations and calculations"""
    result = []

    for row in base_data:
        item_code = row.get("input_item_code")
        batch_no = row.get("custom_batch_no")
        pp_no = row.get("production_plan_no")

        # Calculation (N-O): Balance to Issue Qty = Total Req. Qty - Issued Qty
        total_req = flt(row.get("total_req_qty", 0))
        issued = flt(row.get("issued_qty", 0))
        balance_to_issue = total_req - issued

        row["balance_to_issue_qty"] = balance_to_issue
        row["on_hand_qty"] = flt(stock_map.get(item_code, 0))

        # Batch-wise Material Request lookup
        mr_info = None
        if batch_no and (batch_no, item_code) in mr_data_map:
            mr_info = mr_data_map[(batch_no, item_code)]
        elif pp_no and (pp_no, item_code) in mr_data_map:
            mr_info = mr_data_map[(pp_no, item_code)]

        if mr_info:
            row["purchase_mr_qty"] = flt(mr_info.get("purchase_mr_qty", 0))
            row["purchase_mr_no"] = ", ".join(mr_info.get("purchase_mr_nos", []))
            row["transfer_request_qty"] = flt(mr_info.get("transfer_request_qty", 0))
            row["transfer_request_no"] = ", ".join(mr_info.get("transfer_request_nos", []))
        else:
            row["purchase_mr_qty"] = 0.0
            row["purchase_mr_no"] = ""
            row["transfer_request_qty"] = 0.0
            row["transfer_request_no"] = ""

        # Batch-wise Purchase Order lookup
        po_info = None
        if batch_no and (batch_no, item_code) in po_data_map:
            po_info = po_data_map[(batch_no, item_code)]
        elif pp_no and (pp_no, item_code) in po_data_map:
            po_info = po_data_map[(pp_no, item_code)]

        if po_info:
            row["po_qty"] = flt(po_info.get("po_qty", 0))
            row["po_no"] = ", ".join(po_info.get("po_nos", []))
            row["po_date"] = ", ".join(po_info.get("po_dates", []))
            row["po_line_no"] = ", ".join(po_info.get("po_line_nos", []))
            row["supplier_name"] = ", ".join(po_info.get("suppliers", []))
            required_by = po_info.get("required_by")
            row["required_by"] = formatdate(required_by, "dd-MM-yyyy") if required_by else ""
        else:
            row["po_qty"] = 0.0
            row["po_no"] = ""
            row["po_date"] = ""
            row["po_line_no"] = ""
            row["supplier_name"] = ""
            row["required_by"] = None

        # Batch-wise Purchase Receipt lookup
        pr_info = None
        if batch_no and (batch_no, item_code) in pr_data_map:
            pr_info = pr_data_map[(batch_no, item_code)]
        elif pp_no and (pp_no, item_code) in pr_data_map:
            pr_info = pr_data_map[(pp_no, item_code)]

        if pr_info:
            pr_received = flt(pr_info.get("received_qty", 0))
            po_received = flt(po_info.get("po_received_qty", 0)) if po_info else 0.0
            row["received_qty"] = max(pr_received, po_received)
            row["receipt_draft_qty"] = flt(pr_info.get("receipt_draft_qty", 0))
        else:
            po_received = flt(po_info.get("po_received_qty", 0)) if po_info else 0.0
            row["received_qty"] = po_received
            row["receipt_draft_qty"] = 0.0

        result.append(row)

    return result


def apply_age_filter(data, filters):
    """Calculate entity age and filter by minimum age if specified"""
    today = nowdate()
    entity_ages = {}

    for row in data:
        work_order = row.get("work_order")
        production_plan = row.get("production_plan_no")
        status = row.get("status") or row.get("pp_status")

        if work_order:
            start_date = row.get("actual_start_date") or row.get("planned_start_date") or row.get("wo_creation_date")
        else:
            start_date = row.get("pp_date")

        if start_date and status not in ("Completed", "Stopped", "Closed"):
            age = date_diff(today, start_date)
        else:
            age = 0

        row["age"] = age

        entity = work_order or production_plan
        if entity:
            entity_ages[entity] = max(entity_ages.get(entity, 0), age)

    min_age = flt(filters.get("age") or 0)
    if min_age > 0:
        valid_entities = {e for e, age in entity_ages.items() if age >= min_age}
        data = [
            row for row in data
            if (row.get("work_order") or row.get("production_plan_no")) in valid_entities
        ]

    return data


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
    balance_to_issue_qty = 0
    po_qty = 0
    received_qty = 0

    for row in data:
        total_qty += flt(row.get("total_req_qty", 0))
        issued_qty += flt(row.get("issued_qty", 0))
        balance_to_issue_qty += flt(row.get("balance_to_issue_qty", 0))
        po_qty += flt(row.get("po_qty", 0))
        received_qty += flt(row.get("received_qty", 0))

    return {
        "data": {
            "labels": ["Total Required", "Issued", "Balance to Issue", "PO Qty", "Received Qty"],
            "datasets": [
                {
                    "name": "Quantity",
                    "values": [total_qty, issued_qty, balance_to_issue_qty, po_qty, received_qty]
                }
            ]
        },
        "type": "bar",
        "colors": ["#17a2b8", "#28a745", "#dc3545", "#ffc107", "#20c997"]
    }


def get_report_summary(data):
    """Generate summary cards"""
    if not data:
        return []

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
    total_balance_to_issue = sum(flt(row.get("balance_to_issue_qty", 0)) for row in data)

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
            "datatype": "Float",
            "indicator": "green"
        },
        {
            "value": total_balance_to_issue,
            "label": _("Total Balance to Issue Qty"),
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