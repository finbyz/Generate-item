import frappe
from frappe import _

def before_save(doc, method):
    if not hasattr(doc, "po_items") or not doc.po_items:
        return

    for row in doc.po_items:
        try:
            sales_order = getattr(row, "sales_order", None)
            sales_order_item = getattr(row, "sales_order_item", None)
            item_code = getattr(row, "item_code", None)

            if not sales_order:
                continue

            # Prefer exact Sales Order Item link; fallback to first matching by item_code in SO
            soi_filters = {"parent": sales_order}
            if sales_order_item:
                soi_filters["name"] = sales_order_item
            elif item_code:
                soi_filters["item_code"] = item_code

            soi = frappe.get_all(
                "Sales Order Item",
                filters=soi_filters,
                fields=["name", "custom_batch_no", "bom_no", "idx"],
                order_by="idx asc",
                limit=1,
            )

            if not soi:
                continue

            soi = soi[0]

            # Force-set from Sales Order Item only
            row.custom_batch_no = soi.get("custom_batch_no") or None

            # Set BOM only if BOM matches Sales Order and custom_batch_no; accept active or default BOMs
            selected_bom = None
            if item_code and sales_order and row.custom_batch_no:
                try:
                    bom_candidate = frappe.get_all(
                        "BOM",
                        filters={
                            "item": item_code,
                            "sales_order": sales_order,
                            "custom_batch_no": row.custom_batch_no,
                        },
                        or_filters=[{"is_active": 1}, {"is_default": 1}],
                        fields=["name"],
                        order_by="modified desc",
                        limit=1,
                    )
                    if bom_candidate:
                        selected_bom = bom_candidate[0]["name"]
                except Exception:
                    selected_bom = None

            if selected_bom:
                row.bom_no = selected_bom
            # If no matching BOM is found, keep the existing bom_no intact

        except Exception as e:
            frappe.log_error(
                message=_(
                    "Failed to sync batch/BOM from Sales Order for Production Plan {0} row {1}: {2}"
                ).format(doc.name, getattr(row, "name", ""), str(e)),
                title=_("Production Plan SO Sync Error"),
            )