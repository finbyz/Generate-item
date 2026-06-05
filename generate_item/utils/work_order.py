import frappe
from frappe.utils import flt


def before_insert(doc, method=None):
    logger = frappe.logger("generate_item")
    try:
        logger.info(f"Work Order before_insert: name={getattr(doc, 'name', None)}, sales_order={getattr(doc, 'sales_order', None)}, bom_no={getattr(doc, 'bom_no', None)}")

        if getattr(doc, 'sales_order', None):
            sales_order = frappe.get_doc('Sales Order', doc.sales_order)
            logger.info(f"Fetched Sales Order {sales_order.name} with {len(sales_order.items or [])} items")

            for item in (getattr(doc, 'required_items', []) or []):
                if hasattr(item, 'sales_order'):
                    item.sales_order = doc.sales_order

            batch_no = None
            branch = None

            sales_order_item_name = getattr(doc, 'sales_order_item', None)
            if sales_order_item_name:
                soi = frappe.get_all(
                    'Sales Order Item',
                    filters={'name': sales_order_item_name, 'parent': sales_order.name},
                    fields=['name', 'item_code', 'custom_batch_no', 'bom_no', 'idx', 'branch'],
                    limit=1,
                )
                if soi:
                    batch_no = soi[0].get('custom_batch_no')
                    branch = soi[0].get('branch')
                    logger.info(f"Batch from exact Sales Order Item {sales_order_item_name}: {batch_no}")

            if not batch_no:
                production_item = getattr(doc, 'production_item', None) or getattr(doc, 'item_code', None)
                bom_no = getattr(doc, 'bom_no', None)
                if production_item:
                    soi_filters = {'parent': sales_order.name, 'item_code': production_item}
                    soi_fields = ['name', 'custom_batch_no', 'bom_no', 'idx', 'branch']
                    candidates = frappe.get_all('Sales Order Item', filters=soi_filters, fields=soi_fields, order_by='idx asc')
                    if candidates:
                        chosen = None
                        if bom_no:
                            for c in candidates:
                                if c.get('bom_no') == bom_no and c.get('custom_batch_no'):
                                    chosen = c
                                    break
                        if not chosen:
                            chosen = next((c for c in candidates if c.get('custom_batch_no')), candidates[0])
                        batch_no = chosen.get('custom_batch_no')
                        if not branch:
                            branch = chosen.get('branch')
                        logger.info(f"Batch from SO item by item_code/BOM: {batch_no}")

            if batch_no:
                doc.custom_batch_no = batch_no
                for item in (getattr(doc, 'required_items', []) or []):
                    item.custom_batch_no = batch_no
                for item in (getattr(doc, 'items', []) or []):
                    item.custom_batch_no = batch_no
            else:
                logger.info("Could not resolve custom_batch_no from Sales Order context")

            if branch:
                try:
                    for child in (getattr(doc, 'required_items', []) or []):
                        if hasattr(child, 'branch') and not getattr(child, 'branch', None):
                            child.branch = branch
                    for child in (getattr(doc, 'items', []) or []):
                        if hasattr(child, 'branch') and not getattr(child, 'branch', None):
                            child.branch = branch
                    logger.info(f"Applied branch {branch} to Work Order child rows where missing")
                except Exception as set_branch_err:
                    logger.error(f"Failed to set child branch: {set_branch_err}")

        if getattr(doc, 'bom_no', None):
            bom = frappe.get_doc("BOM", doc.bom_no)
            logger.info(f"Fetched BOM {bom.name} with {len(bom.items or [])} items")

            doc.custom_ga_drawing_no = getattr(bom, 'custom_ga_drawing_no', None)
            doc.custom_ga_drawing_rev_no = getattr(bom, 'custom_ga_drawing_rev_no', None)

            bom_items_map = {d.item_code: d for d in (bom.items or []) if getattr(d, 'item_code', None)}

            children = (getattr(doc, 'required_items', []) or []) + (getattr(doc, 'items', []) or [])
            for child in children:
                bom_item = bom_items_map.get(getattr(child, 'item_code', None))
                if not bom_item:
                    continue
                child.custom_drawing_no = getattr(bom_item, 'custom_drawing_no', None)
                child.custom_pattern_drawing_no = getattr(bom_item, 'custom_pattern_drawing_no', None)
                child.custom_purchase_specification_no = getattr(bom_item, 'custom_purchase_specification_no', None)
                child.custom_drawing_rev_no = getattr(bom_item, 'custom_drawing_rev_no', None)
                child.custom_pattern_drawing_rev_no = getattr(bom_item, 'custom_pattern_drawing_rev_no', None)
                child.custom_purchase_specification_rev_no = getattr(bom_item, 'custom_purchase_specification_rev_no', None)
                child.custom_batch_no = getattr(bom_item, 'custom_batch_no', None) or getattr(child, 'custom_batch_no', None)

    except Exception as e:
        logger.error(f"Error in work_order.before_insert: {e}")
        frappe.log_error(frappe.get_traceback(), "work_order.before_insert")


def on_trash(doc, method=None):
    logger = frappe.logger("generate_item")
    try:
        logger.info(f"Work Order on_trash: name={doc.name}, production_plan={getattr(doc, 'production_plan', None)}")

        production_plan_name = getattr(doc, 'production_plan', None)

        # Fallback 1: search via Production Plan Item
        if not production_plan_name:
            linked = frappe.get_all(
                'Production Plan Item',
                filters={'work_order': doc.name},
                fields=['name', 'parent'],
                limit=1
            )
            if linked:
                production_plan_name = linked[0].get('parent')

        # Fallback 2: search via Sub Assembly Item
        if not production_plan_name:
            linked_sa = frappe.get_all(
                'Production Plan Sub Assembly Item',
                filters={'work_order': doc.name},
                fields=['name', 'parent'],
                limit=1
            )
            if linked_sa:
                production_plan_name = linked_sa[0].get('parent')

        if not production_plan_name:
            logger.info(f"No Production Plan linked to Work Order {doc.name}, skipping reset")
            return

        logger.info(f"Resetting Production Plan {production_plan_name} for deleted WO {doc.name}")

        # ── Reset Assembly Items (po_items) ──────────────────────────────
        po_items = frappe.get_all(
            'Production Plan Item',
            filters={
                'parent': production_plan_name,
                'work_order': doc.name
            },
            fields=['name', 'ordered_qty', 'planned_qty', 'produced_qty']
        )

        for item in po_items:
            # Subtract only this WO's qty; never go below 0
            new_ordered_qty = max(0, flt(item.ordered_qty) - flt(doc.qty))
            frappe.db.set_value(
                'Production Plan Item',
                item.name,
                {
                    'work_order': None,
                    'ordered_qty': new_ordered_qty
                }
            )
            logger.info(
                f"Reset po_item {item.name}: work_order cleared, "
                f"ordered_qty {item.ordered_qty} -> {new_ordered_qty}"
            )

        # ── Reset Sub Assembly Items ──────────────────────────────────────
        sa_items = frappe.get_all(
            'Production Plan Sub Assembly Item',
            filters={
                'parent': production_plan_name,
                'work_order': doc.name
            },
            fields=['name', 'qty']
        )

        for sa_item in sa_items:
            update_values = {'work_order': None}

            # Check if wo_created field exists before setting it
            meta = frappe.get_meta('Production Plan Sub Assembly Item')
            field_names = [f.fieldname for f in meta.fields]
            if 'wo_created' in field_names:
                update_values['wo_created'] = 0

            frappe.db.set_value(
                'Production Plan Sub Assembly Item',
                sa_item.name,
                update_values
            )
            logger.info(f"Reset sub_assembly_item {sa_item.name}: {update_values}")

        # ── Recalculate and fix Production Plan status ────────────────────
        _reset_production_plan_status(production_plan_name, logger)

    except Exception as e:
        logger.error(f"Error in work_order.on_trash: {e}")
        frappe.log_error(frappe.get_traceback(), "work_order.on_trash")


def _reset_production_plan_status(production_plan_name, logger=None):
    if not logger:
        logger = frappe.logger("generate_item")

    try:
        pp = frappe.db.get_value(
            'Production Plan',
            production_plan_name,
            ['status', 'docstatus'],
            as_dict=True
        )

        if not pp or pp.docstatus != 1:
            return

        # Check if ANY work order still exists for this production plan
        existing_wo_count = frappe.db.count(
            'Work Order',
            filters={'production_plan': production_plan_name}
        )

        # If no WOs remain, OR fewer WOs than po_items+sub_assembly_items, show button
        po_item_count = frappe.db.count(
            'Production Plan Item',
            filters={'parent': production_plan_name}
        )
        sub_item_count = frappe.db.count(
            'Production Plan Sub Assembly Item',
            filters={'parent': production_plan_name}
        )

        total_needed = po_item_count + sub_item_count
        has_pending = existing_wo_count < total_needed

        logger.info(
            f"PP {production_plan_name}: existing_wo={existing_wo_count}, "
            f"needed={total_needed}, has_pending={has_pending}"
        )

        if has_pending:
            frappe.db.set_value(
                'Production Plan',
                production_plan_name,
                'status',
                'Material Requested'
            )
            frappe.db.commit()
            logger.info(f"Production Plan {production_plan_name} status -> 'Material Requested'")

    except Exception as e:
        logger.error(f"Error in _reset_production_plan_status: {e}")
        frappe.log_error(frappe.get_traceback(), "_reset_production_plan_status")