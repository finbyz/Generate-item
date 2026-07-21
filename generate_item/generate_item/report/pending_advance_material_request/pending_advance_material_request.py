import frappe
from frappe import _
from frappe.desk.search import validate_and_sanitize_search_inputs
import json


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {
            "label": _("Material Request"),
            "fieldname": "material_request",
            "fieldtype": "Link",
            "options": "Material Request",
            "width": 180,
        },
        {
            "label": _("Date"),
            "fieldname": "transaction_date",
            "fieldtype": "Date",
            "width": 100,
        },
        {
            "label": _("Company"),
            "fieldname": "company",
            "fieldtype": "Link",
            "options": "Company",
            "width": 170,
        },
        {
            "label": _("Item"),
            "fieldname": "item_code",
            "fieldtype": "Link",
            "options": "Item",
            "width": 160,
        },
        {
            "label": _("Item Name"),
            "fieldname": "item_name",
            "fieldtype": "Data",
            "width": 250,
        },
        {
            "label": _("Qty"),
            "fieldname": "qty",
            "fieldtype": "Float",
            "precision": 2,
            "width": 90,
        },
        {
            "label": _("Warehouse"),
            "fieldname": "warehouse",
            "fieldtype": "Link",
            "options": "Warehouse",
            "width": 180,
        },
        {
            "label": _("Batch No"),
            "fieldname": "batch_no",
            "fieldtype": "Data",
            "width": 140,
        },
        {
            "label": _("Production Plan"),
            "fieldname": "production_plan",
            "fieldtype": "Link",
            "options": "Production Plan",
            "width": 180,
        },
    ]


def get_data(filters):
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
            # AND (
            #     mri.production_plan IS NULL
            #     OR mri.production_plan = ''
            # )
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
    # FIX: Parse filters if it's a JSON string
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
def save_production_plan_changes(updates):
    """
    Save multiple Production Plan changes.
    updates: list of {"name": <MR Item row name>, "production_plan": <PP name>}
    """
    if isinstance(updates, str):
        updates = frappe.parse_json(updates)

    if not updates:
        return {"status": "error", "message": _("No updates provided.")}

    updated_count = 0
    errors = []

    for update in updates:
        row_name = update.get("name")
        production_plan = (update.get("production_plan") or "").strip()

        try:
            # Get row details
            row = frappe.db.get_value(
                "Material Request Item",
                row_name,
                ["name", "parent", "custom_batch_no as batch_no"],
                as_dict=True
            )

            if not row:
                errors.append(_("Row {0} not found.").format(row_name))
                continue

            # Check MR is submitted
            docstatus = frappe.db.get_value("Material Request", row.parent, "docstatus")
            if docstatus != 1:
                errors.append(_("Material Request {0} is not submitted.").format(row.parent))
                continue

            # Validate batch if production plan is provided
            if production_plan and row.batch_no:
                is_valid = frappe.db.exists(
                    "Production Plan Item",
                    {"parent": production_plan, "custom_batch_no": row.batch_no}
                )
                if not is_valid:
                    errors.append(
                        _("Production Plan {0} is not valid for Batch {1}.").format(
                            production_plan, row.batch_no
                        )
                    )
                    continue

            # Update the production plan
            frappe.db.set_value(
                "Material Request Item",
                row_name,
                "production_plan",
                production_plan or None,
                update_modified=True
            )
            updated_count += 1

        except Exception as e:
            errors.append(str(e))

    if errors:
        return {
            "status": "error",
            "message": _("Updated {0} item(s). Errors: {1}").format(updated_count, "; ".join(errors))
        }

    return {
        "status": "success",
        "message": _("Successfully updated {0} item(s).").format(updated_count)
    }