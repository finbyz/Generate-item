import frappe

def before_insert(doc, method=None):
    logger = frappe.logger("generate_item")
    try:
        logger.info(f"Work Order before_insert: name={getattr(doc, 'name', None)}, sales_order={getattr(doc, 'sales_order', None)}, bom_no={getattr(doc, 'bom_no', None)}")

        if getattr(doc, 'sales_order', None):
            sales_order = frappe.get_doc('Sales Order', doc.sales_order)
            logger.info(f"Fetched Sales Order {sales_order.name} with {len(sales_order.items or [])} items")

            batch_no = None
            branch = None

            # Prefer exact Sales Order Item when provided on Work Order
            sales_order_item_name = getattr(doc, 'sales_order_item', None)
            if sales_order_item_name:
                soi = frappe.get_all(
                    'Sales Order Item',
                    filters={'name': sales_order_item_name, 'parent': sales_order.name},
                    fields=['name', 'item_code', 'custom_batch_no', 'bom_no', 'idx','branch'],
                    limit=1,
                )
                if soi:
                    batch_no = soi[0].get('custom_batch_no')
                    branch = soi[0].get('branch')
                    logger.info(f"Batch from exact Sales Order Item {sales_order_item_name}: {batch_no}")

            # Fallback: resolve by item_code (production_item) and, if present, BOM
            if not batch_no:
                production_item = getattr(doc, 'production_item', None) or getattr(doc, 'item_code', None)
                bom_no = getattr(doc, 'bom_no', None)
                if production_item:
                    soi_filters = {'parent': sales_order.name, 'item_code': production_item}
                    soi_fields = ['name', 'custom_batch_no', 'bom_no', 'idx', 'branch']
                    candidates = frappe.get_all('Sales Order Item', filters=soi_filters, fields=soi_fields, order_by='idx asc')
                    if candidates:
                        # Try to pick matching BOM first
                        chosen = None
                        if bom_no:
                            for c in candidates:
                                if c.get('bom_no') == bom_no and c.get('custom_batch_no'):
                                    chosen = c
                                    break
                        if not chosen:
                            # Otherwise pick the first that has a batch
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

            # Set child-level branch from resolved SO Item branch if available
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