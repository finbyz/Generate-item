import frappe
from frappe import _, msgprint
from frappe.desk.notifications import clear_doctype_notifications
from frappe.model.mapper import get_mapped_doc
from frappe.utils import cint, cstr, flt, get_link_to_form

def before_insert(doc, method):
    """Set custom_batch_no for subcontracting order and its items from purchase order"""
    if not doc.purchase_order:
        return
    
    try:
        # Get the purchase order document
        purchase_order = frappe.get_doc("Purchase Order", doc.purchase_order)
        for i in purchase_order.items:
            if i.production_plan:
                for j in doc.items:
                    j.production_plan = i.production_plan
                    break 

        
        # Get custom_batch_no from purchase order
        batch_no = getattr(purchase_order, 'custom_batch_no', None)
        
        if batch_no:
            # Set custom_batch_no in parent subcontracting order
            doc.custom_batch_no = batch_no
            
            # Set custom_batch_no in child items that match purchase order items
            for sub_item in doc.items:
                # Find matching item in purchase order
                for po_item in purchase_order.items:
                    if po_item.item_code == sub_item.item_code:
                        # Set batch_no for matching item
                        sub_item.custom_batch_no = batch_no
                        break
                # If no match found but we have batch_no, set it anyway for subcontracting items
                if not sub_item.custom_batch_no:
                    sub_item.custom_batch_no = batch_no
                    
    except frappe.DoesNotExistError:
        frappe.log_error(f"Purchase Order {doc.purchase_order} not found", "Subcontracting Order Validation Error")
    except Exception as e:
        frappe.log_error(f"Error in subcontracting order validation: {str(e)}", "Subcontracting Order Validation Error")




def before_validate(doc, method):
    if not doc.items:
        return

    for row in doc.items:
        if not row.custom_batch_no or not row.item_code:
            continue

        bom_name = frappe.db.get_value(
            "BOM",
            {
                "custom_batch_no": row.custom_batch_no,
                "is_active": 1,
                "docstatus": 1,
                "item":row.item_code
            },
            "name"
        )

        if bom_name:
            row.bom = bom_name




def validate(doc, method):
    """Set production_plan in Subcontracting Order Items from Purchase Order or Material Request"""
    if not doc.purchase_order:
        return
    po = frappe.get_doc("Purchase Order", doc.purchase_order)

    for so_item in doc.items:
        # Find corresponding PO Item
        po_item = next((item for item in po.items if item.item_code == so_item.item_code), None)
        if not po_item:
            continue

        # Case 1: PO Item already has production_plan
        if po_item.production_plan:
            so_item.production_plan = po_item.production_plan
            continue

        # Case 2: Fallback to Material Request Item
        if po_item.material_request and po_item.material_request_item:
            mr_item = frappe.db.get_value(
                "Material Request Item",
                po_item.material_request_item,
                "production_plan"
            )
            if mr_item:
                so_item.production_plan = mr_item

        



import frappe, json

@frappe.whitelist()
def update_supplied_items_in_db(parent, data):
    data = json.loads(data)
    for row in data:
        if not row.get("name"):
            continue

        # Corrected table name for ERPNext v15
        frappe.db.set_value(
            "Subcontracting Order Supplied Item",  # corrected name
            row["name"],
            {
                "custom_drawing_no": row.get("custom_drawing_no", ""),
                "custom_pattern_drawing_no": row.get("custom_pattern_drawing_no", ""),
                "custom_purchase_specification_no": row.get("custom_purchase_specification_no", ""),
                "custom_drawing_rev_no": row.get("custom_drawing_rev_no", ""),
                "custom_pattern_drawing_rev_no": row.get("custom_pattern_drawing_rev_no", ""),
                "custom_purchase_specification_rev_no": row.get("custom_purchase_specification_rev_no", ""),
                "custom_batch_no": row.get("custom_batch_no", ""),
                "bom_reference": row.get("bom_reference", "")
            }
        )
    frappe.db.commit()
    return "Supplied items updated successfully in DB."



def before_save(doc, method):
    """Set custom_batch_no from BOM in items and supplied_items"""
    
    # Update custom_batch_no in items table
    for item in doc.items:
        if not item.custom_batch_no and item.bom:
            batch_no = frappe.get_value("BOM", item.bom, "custom_batch_no")
            if batch_no:
                item.custom_batch_no = batch_no
     # NEW: Set main_description from Item master based on main_item_code
    for supplied_item in doc.supplied_items:
        if supplied_item.rm_item_code and not supplied_item.main_description:
            description = frappe.get_value("Item", supplied_item.rm_item_code, "description")
            if description:
                supplied_item.main_description = description
    
def before_submit(doc, method):
    for supplied_item in doc.supplied_items:
        if not supplied_item.custom_batch_no and supplied_item.bom_reference:
            batch_no = frappe.get_value("BOM", supplied_item.bom_reference, "custom_batch_no")
            if batch_no:
                supplied_item.custom_batch_no = batch_no



@frappe.whitelist()
def custom_make_subcontracting_receipt(source_name, target_doc=None):
	return get_mapped_subcontracting_receipt(source_name, target_doc)


def get_mapped_subcontracting_receipt(source_name, target_doc=None):
   
    def update_item(source, target, source_parent):

        target.purchase_order = source_parent.purchase_order
        # frappe.log_error("source name",source_parent.purchase_order,)
        target.purchase_order_item = source.purchase_order_item
        target.qty = flt(source.qty) - flt(source.received_qty)
        target.amount = (flt(source.qty) - flt(source.received_qty)) * flt(source.rate)
        
   
    target_doc = get_mapped_doc(
        "Subcontracting Order",
        source_name,
        {
            "Subcontracting Order": {
                "doctype": "Subcontracting Receipt",
                "field_map": {
                    "supplier_warehouse": "supplier_warehouse",
                    "set_warehouse": "set_warehouse",
                },
                "validation": {
                    "docstatus": ["=", 1],
                },
            },
            "Subcontracting Order Item": {
                "doctype": "Subcontracting Receipt Item",
                "field_map": {
                    "name": "subcontracting_order_item",
                    "parent": "subcontracting_order",
                    "bom": "bom",
                    "custom_batch_no":"custom_batch_no",
                   
                },
                "postprocess": update_item,
                "condition": lambda doc: abs(doc.received_qty) < abs(doc.qty),
            },
        },
        target_doc,
    )

    return target_doc

def get_item_details(items):
	item = frappe.qb.DocType("Item")
	item_list = (
		frappe.qb.from_(item)
		.select(item.item_code, item.item_name, item.description, item.allow_alternative_item)
		.where(item.name.isin(items))
		.run(as_dict=True)
	)

	item_details = {}
	for item in item_list:
		item_details[item.item_code] = item

	return item_details


@frappe.whitelist()
def custom_make_rm_stock_entry(
	subcontract_order, rm_items=None, order_doctype="Subcontracting Order", target_doc=None
):
    if subcontract_order:
        subcontract_order = frappe.get_doc(order_doctype, subcontract_order)

        if not rm_items:
            if not subcontract_order.supplied_items:
                frappe.throw(_("No item available for transfer."))

            rm_items = subcontract_order.supplied_items

        fg_item_code_list = list(
            set(item.get("main_item_code") or item.get("item_code") for item in rm_items)
        )

        if fg_item_code_list:
            rm_item_code_list = tuple(set(item.get("rm_item_code") for item in rm_items))
            item_wh = get_item_details(rm_item_code_list)

            field_no_map, rm_detail_field = "purchase_order", "sco_rm_detail"
            if order_doctype == "Purchase Order":
                field_no_map, rm_detail_field = "subcontracting_order", "po_detail"

            if target_doc and target_doc.get("items"):
                target_doc.items = []

            stock_entry = get_mapped_doc(
                order_doctype,
                subcontract_order.name,
                {
                    order_doctype: {
                        "doctype": "Stock Entry",
                        "field_map": {
                            "supplier": "supplier",
                            "supplier_name": "supplier_name",
                            "supplier_address": "supplier_address",
                            "to_warehouse": "supplier_warehouse",
                        },
                        "field_no_map": [field_no_map],
                        "validation": {
                            "docstatus": ["=", 1],
                        },
                    },
                },
                target_doc,
                ignore_child_tables=True,
            )
            # EXPLICIT PARENT → PARENT MAPPING
            stock_entry.po_number = subcontract_order.purchase_order

            stock_entry.purpose = "Send to Subcontractor"

            if order_doctype == "Purchase Order":
                stock_entry.purchase_order = subcontract_order.name
            else:
                stock_entry.subcontracting_order = subcontract_order.name

            stock_entry.set_stock_entry_type()

            for fg_item_code in fg_item_code_list:
                for rm_item in rm_items:
                    if (
                        rm_item.get("main_item_code") == fg_item_code
                        or rm_item.get("item_code") == fg_item_code
                    ):
                        rm_item_code = rm_item.get("rm_item_code")
                        items_dict = {
                            rm_item_code: {
                                rm_detail_field: rm_item.get("name"),
                                "item_name": rm_item.get("item_name")
                                or item_wh.get(rm_item_code, {}).get("item_name", ""),
                                "description": item_wh.get(rm_item_code, {}).get("description", ""),
                                "qty": rm_item.get("qty")
                                or max(rm_item.get("required_qty") - rm_item.get("total_supplied_qty"), 0),
                                "from_warehouse": rm_item.get("warehouse")
                                or rm_item.get("reserve_warehouse"),
                                "to_warehouse": subcontract_order.supplier_warehouse,
                                "stock_uom": rm_item.get("stock_uom"),
                                "serial_and_batch_bundle": rm_item.get("serial_and_batch_bundle"),
                                "main_item_code": fg_item_code,
                                "allow_alternative_item": item_wh.get(rm_item_code, {}).get(
                                    "allow_alternative_item"
                                ),
                                "use_serial_batch_fields": rm_item.get("use_serial_batch_fields"),
                                "serial_no": rm_item.get("serial_no")
                                if rm_item.get("use_serial_batch_fields")
                                else None,
                                "batch_no": rm_item.get("batch_no")
                                if rm_item.get("use_serial_batch_fields")
                                else None,
                            }
                        }

                        stock_entry.add_to_stock_entry_detail(items_dict)

            if target_doc:
                return stock_entry
            else:
                return stock_entry.as_dict()
        else:
            frappe.throw(_("No Items selected for transfer."))


