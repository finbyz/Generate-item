import frappe
from frappe import _
from frappe.desk.search import validate_and_sanitize_search_inputs
import json


@frappe.whitelist()
def get_data(filters=None):
    """Get data for the page"""
    if isinstance(filters, str):
        filters = frappe.parse_json(filters)
    
    filters = frappe._dict(filters or {})
    
    conditions = []

    if filters.get("company"):
        conditions.append("mr.company = %(company)s")

    if filters.get("from_date"):
        conditions.append("mr.transaction_date >= %(from_date)s")

    if filters.get("to_date"):
        conditions.append("mr.transaction_date <= %(to_date)s")

    condition_sql = ""
    if conditions:
        condition_sql = " AND " + " AND ".join(conditions)

    return frappe.db.sql(
        f"""
        SELECT
            mr.name AS material_request,
            mr.transaction_date,
            mr.company,
            mri.item_code,
            mri.item_name,
            mri.qty,
            mri.warehouse,
            mri.custom_batch_no AS batch_no,
            mri.production_plan,
            mri.name AS name
        FROM
            `tabMaterial Request` mr
        INNER JOIN
            `tabMaterial Request Item` mri
            ON mri.parent = mr.name
        WHERE
            mr.docstatus = 1
            AND mr.advance_mr = 1
           
            {condition_sql}
        ORDER BY
            mr.transaction_date DESC,
            mr.name,
            mri.idx
        """,
        filters,
        as_dict=True,
    )


@frappe.whitelist()
@validate_and_sanitize_search_inputs
def production_plan_query(doctype, txt, searchfield, start, page_len, filters):
    """Link-field query for Production Plan, filtered by batch_no."""
    # Handle filters being passed as JSON string
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    batch_no = filters.get("batch_no") if isinstance(filters, dict) else None
    
    if not batch_no:
        return []

    return frappe.db.sql(
        """
        SELECT DISTINCT pp.name
        FROM `tabProduction Plan` pp
        INNER JOIN `tabProduction Plan Item` ppi
            ON ppi.parent = pp.name
        WHERE
            pp.docstatus = 1
            AND ppi.custom_batch_no = %(batch)s
            AND pp.name LIKE %(txt)s
        ORDER BY pp.creation DESC
        LIMIT %(start)s, %(page_len)s
        """,
        {
            "batch": batch_no,
            "txt": f"%{txt}%",
            "start": start,
            "page_len": page_len,
        },
    )


@frappe.whitelist()
def bulk_update_production_plan(material_request, updates):
    """
    updates: list of {"name": <Material Request Item row name>, "production_plan": <PP name>}
    """
    if isinstance(updates, str):
        updates = frappe.parse_json(updates)

    if not updates:
        frappe.throw(_("No updates provided."))

    docstatus = frappe.db.get_value("Material Request", material_request, "docstatus")
    if docstatus != 1:
        frappe.throw(_("Production Plan can only be linked to Submitted Material Requests."))

    mr_items = frappe.get_all(
        "Material Request Item",
        filters={"parent": material_request},
        fields=["name", "custom_batch_no as batch_no"],
    )
    batch_by_row = {d.name: d.batch_no for d in mr_items}

    cleaned = []
    for update in updates:
        row_name = update.get("name")
        production_plan = (update.get("production_plan") or "").strip()

        if row_name not in batch_by_row:
            frappe.throw(
                _("Row {0} does not belong to Material Request {1}.").format(row_name, material_request)
            )

        if production_plan:
            batch_no = batch_by_row[row_name]
            is_valid = frappe.db.exists(
                "Production Plan Item",
                {"parent": production_plan, "custom_batch_no": batch_no},
            )
            if not is_valid:
                frappe.throw(
                    _("Production Plan {0} is not valid for Batch {1}.").format(production_plan, batch_no)
                )

        cleaned.append({"name": row_name, "production_plan": production_plan or None})

    for update in cleaned:
        frappe.db.set_value(
            "Material Request Item",
            update["name"],
            "production_plan",
            update["production_plan"],
            update_modified=False,
        )

    linked = [u for u in cleaned if u["production_plan"]]
    skipped_count = len(cleaned) - len(linked)

    if not linked:
        message = _("No Production Plan was selected for any item.")
    elif skipped_count:
        message = _("Production Plan linked for {0} item(s). {1} item(s) skipped.").format(
            len(linked), skipped_count
        )
    else:
        message = _("Production Plan linked for {0} item(s).").format(len(linked))

    return {
        "status": "success",
        "updated": len(linked),
        "skipped": skipped_count,
        "message": message,
    }