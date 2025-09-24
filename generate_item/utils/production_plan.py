import frappe
from frappe import _

def before_save(doc, method):
    # Handle po_items
    if hasattr(doc, "po_items") and doc.po_items:
        for row in doc.po_items:
            _populate_production_plan_item_from_sales_order(doc, row)
    
    # Handle sub_assembly_items
    if hasattr(doc, "sub_assembly_items") and doc.sub_assembly_items:
        for row in doc.sub_assembly_items:
            _populate_subassembly_item_from_sales_order(doc, row)

def _populate_production_plan_item_from_sales_order(doc, row):
    """Populate production plan item with values from Sales Order Items"""
    try:
        sales_order = getattr(row, "sales_order", None)
        sales_order_item = getattr(row, "sales_order_item", None)
        item_code = getattr(row, "item_code", None)

        # Fallback: if items were combined, SO link is in prod_plan_references
        if not sales_order and hasattr(doc, "prod_plan_references") and doc.prod_plan_references:
            for ref in doc.prod_plan_references:
                if getattr(ref, "item_reference", None) == getattr(row, "name", None):
                    sales_order = getattr(ref, "sales_order", None)
                    sales_order_item = getattr(ref, "sales_order_item", None)
                    if sales_order:
                        break
        if not sales_order:
            return

        # Prefer exact Sales Order Item link; fallback to first matching by item_code in SO
        soi_filters = {"parent": sales_order}
        if sales_order_item:
            soi_filters["name"] = sales_order_item
        elif item_code:
            soi_filters["item_code"] = item_code

        soi = frappe.get_all(
            "Sales Order Item",
            filters=soi_filters,
            fields=["name", "custom_batch_no", "bom_no", "idx", "branch"],
            order_by="idx asc",
            limit=1,
        )

        if not soi:
            return

        soi = soi[0]

        # Force-set from Sales Order Item only
        row.custom_batch_no = soi.get("custom_batch_no") or None
        # Ensure branch propagates into po_items for downstream logic
        if hasattr(row, "branch"):
            row.branch = soi.get("branch") or None

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

def _populate_subassembly_item_from_sales_order(doc, row):
    """Populate subassembly item with values from Sales Order Items"""
    try:
        # Get the production plan item that this subassembly item is related to
        production_plan_item = None
        if hasattr(row, 'production_plan_item') and row.production_plan_item:
            production_plan_item = frappe.get_doc("Production Plan Item", row.production_plan_item)
        else:
            # Try to find the production plan item by item_code
            pp_items = frappe.get_all(
                "Production Plan Item",
                filters={"parent": doc.name, "item_code": row.production_item},
                fields=["name", "sales_order", "sales_order_item"],
                limit=1
            )
            if pp_items:
                production_plan_item = frappe.get_doc("Production Plan Item", pp_items[0].name)

        if not production_plan_item:
            return

        sales_order = getattr(production_plan_item, "sales_order", None)
        sales_order_item = getattr(production_plan_item, "sales_order_item", None)
        item_code = getattr(production_plan_item, "item_code", None)

        if not sales_order:
            return

        # Prefer exact Sales Order Item link; fallback to first matching by item_code in SO
        soi_filters = {"parent": sales_order}
        if sales_order_item:
            soi_filters["name"] = sales_order_item
        elif item_code:
            soi_filters["item_code"] = item_code

        soi = frappe.get_all(
            "Sales Order Item",
            filters=soi_filters,
            fields=["name", "custom_batch_no", "bom_no", "idx", "branch"],
            order_by="idx asc",
            limit=1,
        )

        if not soi:
            return

        soi = soi[0]

        # Set custom fields from Sales Order Item
        if hasattr(row, 'custom_batch_no'):
            row.custom_batch_no = soi.get("custom_batch_no") or None
        if hasattr(row, 'branch'):
            row.branch = soi.get("branch") or None

    except Exception as e:
        frappe.log_error(
            message=_(
                "Failed to sync batch/branch from Sales Order for Production Plan {0} subassembly item {1}: {2}"
            ).format(doc.name, getattr(row, "name", ""), str(e)),
            title=_("Production Plan Subassembly SO Sync Error"),
        )