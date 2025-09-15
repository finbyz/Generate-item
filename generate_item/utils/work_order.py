import frappe

def before_insert(doc, method=None):
    logger = frappe.logger("generate_item")
    try:
        logger.info(f"Work Order before_insert: name={getattr(doc, 'name', None)}, sales_order={getattr(doc, 'sales_order', None)}, bom_no={getattr(doc, 'bom_no', None)}")

        if getattr(doc, 'sales_order', None):
            sales_order = frappe.get_doc('Sales Order', doc.sales_order)
            logger.info(f"Fetched Sales Order {sales_order.name} with {len(sales_order.items or [])} items")

            if sales_order.items and len(sales_order.items) > 0 and getattr(sales_order.items[0], 'custom_batch_no', None):
                batch_no = sales_order.items[0].custom_batch_no
                doc.custom_batch_no = batch_no
                logger.info(f"Set Work Order custom_batch_no from SO: {batch_no}")

                for item in (getattr(doc, 'required_items', []) or []):
                    item.custom_batch_no = batch_no
                for item in (getattr(doc, 'items', []) or []):
                    item.custom_batch_no = batch_no
            else:
                logger.info("No custom_batch_no found on first Sales Order item")

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