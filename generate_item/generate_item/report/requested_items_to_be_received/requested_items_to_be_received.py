# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

from frappe import _
import frappe
from frappe.utils import flt, getdate, nowdate





def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": "Purchase Order", "fieldname": "name", "fieldtype": "Link", "options": "Purchase Order", "width": 160},
        {"label": "Batch No Ref", "fieldname": "custom_batch_no", "fieldtype": "Link", "options": "Batch", "width": 160},
        {"label": "Supplier", "fieldname": "supplier", "fieldtype": "Link", "options": "Supplier", "width": 180},
        
        {"label": "Posting Date", "fieldname": "transaction_date", "fieldtype": "Date", "width": 110},
        {"label": "Schedule Date", "fieldname": "schedule_date", "fieldtype": "Date", "width": 110},
        {"label": "Status", "fieldname": "status", "width": 120},
        {"label": "Item ID", "fieldname": "item_id", "width": 220},
        {"label": "Item Code", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 140},
        {"label": "Item Name", "fieldname": "item_name", "width": 220},
        {"label": "Description", "fieldname": "description", "width": 250},
        
        {"label": "PO Qty", "fieldname": "po_qty", "fieldtype": "Float", "width": 110},
        {"label": "Received Qty", "fieldname": "received_qty", "fieldtype": "Float", "width": 120},
        {"label": "Pending Receipt Qty", "fieldname": "pending_qty", "fieldtype": "Float", "width": 140},
        
        {"label": "Drawing Number", "fieldname": "custom_drawing_no", "width": 220},
        {"label": "Drawing Rev No", "fieldname": "custom_drawing_rev_no", "width": 220},
        
        {"label": "Created By", "fieldname": "created_by", "fieldtype": "Link", "options": "User", "width": 140},
        
        
        {"label": "Pattern Drawing No", "fieldname": "custom_pattern_drawing_no", "width": 220},
		{"label": "Pattern Drawing Rev No", "fieldname": "custom_pattern_drawing_rev_no", "width": 220},
		{"label": "Purchase Specification No", "fieldname": "custom_purchase_specification_no", "width": 220},
		{"label": "Purchase Specification Rev No", "fieldname": "custom_purchase_specification_rev_no", "width": 220},
  

        {"label": "Age (Days)", "fieldname": "age", "fieldtype": "Int", "width": 90},
		{"label": "0-30", "fieldname": "range_0_30", "fieldtype": "Float", "width": 100},
		{"label": "31-60", "fieldname": "range_31_60", "fieldtype": "Float", "width": 100},
		{"label": "61-90", "fieldname": "range_61_90", "fieldtype": "Float", "width": 100},
		{"label": "91-120", "fieldname": "range_91_120", "fieldtype": "Float", "width": 100},
		{"label": "121+", "fieldname": "range_121_above", "fieldtype": "Float", "width": 100},
  
        {"label": "Warehouse", "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 160},
        {"label": "Company", "fieldname": "company", "width": 220},
    ]



def get_data(filters):
    conditions = []
    values = {}

    if filters.get("company"):
        conditions.append("po.company = %(company)s")
        values["company"] = filters["company"]

    if filters.get("supplier"):
        conditions.append("po.supplier = %(supplier)s")
        values["supplier"] = filters["supplier"]

    # filter by created by (multi or single)
    created_by = filters.get("created_by")
    if created_by:
        if isinstance(created_by, str):
            created_by_list = [u.strip() for u in created_by.replace(",", "\n").split("\n") if u.strip()]
        else:
            created_by_list = created_by

        if created_by_list:
            conditions.append("po.owner IN %(created_by)s")
            values["created_by"] = tuple(created_by_list)

    if filters.get("from_date"):
        conditions.append("po.transaction_date >= %(from_date)s")
        values["from_date"] = filters["from_date"]

    if filters.get("to_date"):
        conditions.append("po.transaction_date <= %(to_date)s")
        values["to_date"] = filters["to_date"]

    if filters.get("status"):
        conditions.append("po.status = %(status)s")
        values["status"] = filters["status"]

    where_clause = " AND ".join(conditions)
    if where_clause:
        where_clause = " AND " + where_clause

    query = f"""
        SELECT
            po.name,
            po.owner as created_by,
            po.supplier,
            po.transaction_date,
            po.schedule_date,
            po.status,
            po.company,
            po.branch,

            poi.name AS purchase_order_item,
            poi.item_code,
            poi.item_name,
            poi.description,
            poi.custom_batch_no,
            poi.custom_drawing_no,
            poi.custom_drawing_rev_no,
            poi.qty AS po_qty,
            IFNULL(poi.received_qty, 0) AS received_qty,
            poi.rate,
            poi.warehouse,
            poi.uom,
            poi.schedule_date AS item_schedule_date,

            poi.material_request,
            poi.material_request_item,
            poi.name as item_id,
			poi.custom_pattern_drawing_no,
			poi.custom_pattern_drawing_rev_no,
			poi.custom_purchase_specification_no,
			poi.custom_purchase_specification_rev_no

        FROM `tabPurchase Order` po
        INNER JOIN `tabPurchase Order Item` poi
            ON poi.parent = po.name
        WHERE
            po.docstatus = 1
            {where_clause}
        ORDER BY
            po.transaction_date ASC, po.name
    """

    rows = frappe.db.sql(query, values, as_dict=True)

    data = []
    today = getdate(nowdate())
    for row in rows:
        pending_qty = flt(row.po_qty) - flt(row.received_qty)

        if pending_qty <= 0:
            continue
        
        age = (today - getdate(row.item_schedule_date)).days if row.item_schedule_date else 0


        row.update({
            "pending_qty": pending_qty,
            "age": age,
			"range_0_30": pending_qty if age <= 30 else 0,
			"range_31_60": pending_qty if 31 <= age <= 60 else 0,
			"range_61_90": pending_qty if 61 <= age <= 90 else 0,
			"range_91_120": pending_qty if 91 <= age <= 120 else 0,
			"range_121_above": pending_qty if age > 120 else 0,
        })

        data.append(row)

    return data



@frappe.whitelist()
def create_purchase_receipt_by_supplier(grouped_items, company, pr_series=None, branch=None):
    """
    Create Purchase Receipt grouped by supplier from Purchase Orders
    """
    import json

    if isinstance(grouped_items, str):
        grouped_items = json.loads(grouped_items)

    created_receipts = []

    try:
        for supplier, items in grouped_items.items():
            if not items:
                continue

            pr = frappe.new_doc("Purchase Receipt")
            pr.supplier = supplier
            pr.company = company
            pr.branch = branch or items[0].get("branch")

            if pr_series:
                pr.naming_series = pr_series

            pr.posting_date = nowdate()
            pr.set_posting_time = 1

            for item in items:
                pr.append("items", {
                    "item_code": item.get("item_code"),
                    "item_name": item.get("item_name"),
                    "description": item.get("description"),
                    "qty": item.get("pending_qty"),
                    "uom": item.get("uom"),
                    "rate": item.get("rate"),
                    "warehouse": item.get("warehouse"),

                    # REQUIRED LINKS
                    "purchase_order": item.get("name"),
                    "purchase_order_item": item.get("purchase_order_item"),
                    "material_request": item.get("material_request"),
                    "material_request_item": item.get("material_request_item"),

                    # CUSTOM FIELDS
                    "custom_batch_no": item.get("custom_batch_no"),
                    "custom_drawing_no": item.get("custom_drawing_no"),
                    "custom_drawing_rev_no": item.get("custom_drawing_rev_no"),
                    "custom_pattern_drawing_no":item.get("custom_pattern_drawing_no"),
                    "custom_pattern_drawing_rev_no":item.get("custom_pattern_drawing_rev_no"),
                    "custom_purchase_specification_no":item.get("custom_purchase_specification_no"),
                    "custom_purchase_specification_rev_no":item.get("custom_purchase_specification_rev_no")
                    
                    
                })

            pr.flags.ignore_permissions = True
            pr.flags.ignore_mandatory = True
            pr.save(ignore_permissions=True)

            created_receipts.append({
                "purchase_receipt": pr.name,
                "supplier": supplier,
                "items": len(items),
                "status": "Success"
            })

            frappe.db.commit()

        if created_receipts:
            frappe.msgprint(_("Successfully created {0} Purchase Receipt(s)").format(len(created_receipts)))

        return created_receipts

    except Exception:
        frappe.log_error(frappe.get_traceback(), _("Purchase Receipt Creation Error"))
        frappe.throw(_("Failed to create Purchase Receipt"))
        
@frappe.whitelist()
def get_pr_naming_series():
    meta = frappe.get_meta("Purchase Receipt")
    field = meta.get_field("naming_series")

    if not field or not field.options:
        return []

    return [opt for opt in field.options.split("\n") if opt]


@frappe.whitelist()
def get_last_purchase_history(item_codes):
    import json

    if isinstance(item_codes, str):
        item_codes = json.loads(item_codes)

    if not item_codes:
        return []

    query = """
        SELECT
            poi.item_code,
            po.name AS po_no,
            po.posting_date AS po_date,
            po.supplier,
            poi.qty,
            poi.rate
        FROM `tabPurchase Receipt Item` poi
        INNER JOIN `tabPurchase Receipt` po
            ON po.name = poi.parent
        WHERE
            poi.item_code IN %(item_codes)s
            AND po.docstatus = 1
            AND po.status NOT IN ('Closed')
        ORDER BY
            po.posting_date DESC
    """

    rows = frappe.db.sql(
        query,
        {"item_codes": tuple(item_codes)},
        as_dict=True
    )

    # Pick last (latest) purchase per item
    seen = set()
    result = []
	

    for row in rows:
        if row.item_code not in seen:
            result.append(row)
            seen.add(row.item_code)

    return result









