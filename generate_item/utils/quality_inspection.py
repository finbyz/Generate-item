from posix import read
import frappe
@frappe.whitelist()
def get_reference_name(reference_name, reference_type):
    ref_data = frappe.get_value(reference_type, reference_name, "branch")
    return ref_data

def on_submit(doc,method):
    if not doc.rejected_qty:
        return
    reference_doc = frappe.get_doc("Purchase Receipt",doc.reference_name)
    if not reference_doc:
        return
    if reference_doc.branch == "Nandikoor":
        reference_doc.rejected_warehouse = "Nandikoor Stores - SVIPL"
    elif reference_doc.branch == "Sanand":
        reference_doc.rejected_warehouse = "Sanand Stores - SVIPL"
    elif reference_doc.branch == "Rabale":
        reference_doc.rejected_warehouse = "Rabale Stores - SVIPL"
        
    for item in reference_doc.items:
        if item.item_code == doc.item_code:
            item.qty -= doc.rejected_qty
            item.rejected_qty = doc.rejected_qty
        


    
    reference_doc.save()
    

def before_save(doc, method):
    if doc.branch or not (doc.reference_type and doc.reference_name):
        return

    try:
        branch = frappe.db.get_value(doc.reference_type, doc.reference_name, "branch")
        if branch:
            doc.branch = branch
    except Exception as e:
        frappe.log_error(f"Failed to fetch branch for {doc.reference_type} - {doc.reference_name}: {e}", "Quality Inspection before_save")

        

@frappe.whitelist()
def get_bom_item_custom_fields(item_code: str, batch_no_ref: str, fields: list | str | None = None):
    # Patch: decode if passed as JSON string from JS (Frappe 15+ type validation)
    if fields and isinstance(fields, str):
        import json
        fields = json.loads(fields)
    """Return selected custom fields from BOM Item for given component `item_code`
    and selected `batch_no_ref`.

    Logic:
    - Look up finished good from `Batch.item` using `batch_no_ref`
    - Resolve active, submitted BOM for that finished good (prefer default BOM)
    - Find matching `BOM Item` row where `parent` = BOM name and `item_code` = given item
    - Return only requested `fields` if provided, otherwise all custom_* fields
    """

    if not item_code or not batch_no_ref:
        return {}

    batch = frappe.db.get_value("Batch", batch_no_ref, ["item"], as_dict=True)
    if not batch or not batch.item:
        return {}

    parent_item = batch.item

    # Prefer default BOM if set and valid
    bom_name = frappe.db.get_value("Item", parent_item, "default_bom")
    if bom_name:
        # Ensure this BOM is submitted and active
        is_valid = frappe.db.exists("BOM", {"name": bom_name, "docstatus": 1, "is_active": 1})
        if not is_valid:
            bom_name = None

    # Fallback to any active submitted BOM for parent item (prefer is_default, newest)
    if not bom_name:
        bom_name = frappe.db.sql(
            """
            SELECT name
            FROM `tabBOM`
            WHERE item = %s AND docstatus = 1 AND is_active = 1
            ORDER BY is_default DESC, modified DESC
            LIMIT 1
            """,
            (parent_item,),
            as_dict=False,
        )
        bom_name = bom_name and bom_name[0][0]

    if not bom_name:
        return {}

    bom_item_row = frappe.db.get_value(
        "BOM Item",
        {"parent": bom_name, "item_code": item_code},
        "*",
        as_dict=True,
    )

    if not bom_item_row:
        return {}

    # Determine which fields to return
    if fields and isinstance(fields, (list, tuple)):
        return {f: bom_item_row.get(f) for f in fields}

    # By default, return all custom_* fields present on BOM Item
    meta = frappe.get_meta("BOM Item")
    custom_fields = [df.fieldname for df in meta.fields if df.fieldname and df.fieldname.startswith("custom_")]
    response = {f: bom_item_row.get(f) for f in custom_fields}

    # Always include a few useful identifiers
    response.update({
        "bom": bom_name,
        "parent_item": parent_item,
    })

    return response