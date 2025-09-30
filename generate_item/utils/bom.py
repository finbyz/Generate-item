import frappe

def before_validate(doc, method=None):
    for item in doc.items:
        if item.bom_no:
            bom = frappe.get_doc("BOM", item.bom_no)
            if bom.custom_batch_no and bom.sales_order:
                frappe.throw(
                    (
                    f"<p>Item <strong>{item.item_code}</strong> cannot be submitted.</p>"
                    f"<p>The linked Bill of Materials (<strong>{item.bom_no}</strong>) is "
                    "configured for both a <strong>specific Sales Order</strong> and a "
                    "<strong>Batch Number</strong>, which is a conflict in production.</p>"
                    ),
                    ("Conflicting BOM Data")
                )

    # 1. Determine the Production Plan name (guarding against missing attributes)
    production_plan = getattr(doc, "production_plan", None)

    # 2. Fallback: check child rows if parent field isn’t set
    if not production_plan and doc.items:
        production_plan = next(
            (getattr(item, "production_plan", None) for item in doc.items),
            None
        )

    # 3. Exit early if no Production Plan found
    if not production_plan:
        return

    # 4. Fetch the Production Plan document safely
    try:
        pp = frappe.get_doc("Production Plan", production_plan)
    except frappe.DoesNotExistError:
        frappe.logger("generate_item").warning(
            f"Production Plan {production_plan} not found for BOM {doc.name}"
        )
        return

    # 5. Extract the custom batch number from the first PO Item (if set)
    batch_no = None
    if pp.po_items:
        batch_no = getattr(pp.po_items[0], "custom_batch_no", None)

    # 6. Apply batch number to BOM and all child items
    if batch_no:
        doc.custom_batch_no = batch_no
        for item in doc.items:
            item.custom_batch_no = batch_no

def clear_custom_fields_on_cancel(doc, method):
    doc.custom_batch_no = ""
    doc.sales_order = ""
    doc.db_update()
    
def on_submit(self,method):
    for row in self.items:
        if row.bom_no and self.sales_order and self.custom_batch_no:
            data = frappe.get_doc("BOM", row.bom_no)
            data.db_set("custom_batch_no",self.custom_batch_no)
            data.db_set("sales_order",self.sales_order) 
