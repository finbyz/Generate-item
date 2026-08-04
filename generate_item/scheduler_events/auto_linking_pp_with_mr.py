
import frappe

from generate_item.utils.material_request import bulk_update_production_plan


def get_material_request_items():
    """
    Return MR Items eligible for auto-linking.

    Conditions:
    - Material Request is Submitted
    - advance_mr = 1
    - Item has Batch No
    - Production Plan is not already linked
    """

    return frappe.db.sql(
        """
        SELECT
            mri.name AS item_name,
            mri.parent AS mr_name,
            mri.custom_batch_no AS batch_no
        FROM `tabMaterial Request Item` mri
        INNER JOIN `tabMaterial Request` mr
            ON mr.name = mri.parent
        WHERE
            mr.docstatus = 1
            AND mr.advance_mr = 1
            AND IFNULL(mri.custom_batch_no, '') != ''
            AND IFNULL(mri.production_plan, '') = ''
        ORDER BY mr.creation
        """,
        as_dict=True,
    )


def auto_link_production_plan():
    total_updated = 0

    for item in get_material_request_items():
        try:
            production_plan = frappe.db.get_value(
                "Production Plan Item",
                {
                    "custom_batch_no": item.batch_no,
                },
                "parent",
                order_by="creation desc",
            )

            if not production_plan:
                continue

            result = bulk_update_production_plan(
                item.mr_name,
                [
                    {
                        "name": item.item_name,
                        "production_plan": production_plan,
                    }
                ],
            )

            total_updated += result.get("updated", 0)

        except Exception:
            frappe.log_error(
                title=f"Auto Link PP - {item.item_name}",
                message=frappe.get_traceback(),
            )

    frappe.log_error(
        f"Auto Link Production Plan completed. Linked {total_updated} item(s)."
    )