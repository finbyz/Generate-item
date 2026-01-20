import frappe
import json

from frappe import _, msgprint
from frappe.desk.notifications import clear_doctype_notifications
from frappe.model.mapper import get_mapped_doc
from frappe.utils import cint, cstr, flt, get_link_to_form


def validate(doc, method):
    validate_duplicate_po(doc, method)
    for i in doc.items:
        i.po_line_no = i.idx
        if i.rate == 0:
            frappe.throw(f"Please enter a valid rate for item in line No. {i.idx}. The rate cannot be 0.",
                         title="Zero Rate Found")


def validate_duplicate_po(doc, method):
    """Prevent duplicate draft Purchase Orders for same supplier, item, qty, custom_batch_no, material_request, and material_request_item."""
    
    # Skip validation for cancelled or submitted docs
    if doc.docstatus != 0:
        return

    # Only proceed if custom_batch_no is set
    if not doc.custom_batch_no:
        return

    # Get potential duplicate POs first (outside item loop for efficiency)
    duplicates = frappe.db.get_all(
        "Purchase Order",
        filters={
            "supplier": doc.supplier,
            "custom_batch_no": doc.custom_batch_no,
            "docstatus": 0,  # Only Draft
            "name": ["!=", doc.name],  # Exclude current
        },
        fields=["name"]
    )

    if not duplicates:
        return

    # Now check each item against these potential duplicates
    for item in doc.items:
        for d in duplicates:
            duplicate_items = frappe.db.get_all(
                "Purchase Order Item",
                filters={
                    "parent": d.name,
                    "item_code": item.item_code,
                    "qty": item.qty,
                    "material_request": item.material_request or "",
                    "material_request_item": item.material_request_item or "",
                },
                fields=["item_code", "qty"]
            )
            if duplicate_items:
                frappe.throw(_(
                    f"Duplicate Purchase Order Found: <b>{d.name}</b><br>"
                    f"Supplier <b>{doc.supplier}</b> already has a Draft PO "
                    f"for Item <b>{item.item_code}</b> with Qty <b>{item.qty}</b>, "
                    f"Batch No <b>{doc.custom_batch_no}</b>, "
                   
                ))


def before_insert(doc, method):
    """Set custom_batch_no for purchase order and its items from linked Production Plan Item"""
    if not doc.items:
        return

    try:
        # Loop through PO items
        for po_item in doc.items:
            po_item.po_line_no = po_item.idx
            if po_item.production_plan_item:
                plan_item = frappe.get_doc("Production Plan Item", po_item.production_plan_item)

                # Get custom_batch_no from Production Plan Item
                batch_no = getattr(plan_item, "custom_batch_no", None)

                if batch_no:
                    # Set on PO parent (first found batch_no)
                    if not getattr(doc, "custom_batch_no", None):
                        doc.custom_batch_no = batch_no

                    # Set on PO child item
                    po_item.custom_batch_no = batch_no

    except frappe.DoesNotExistError:
        frappe.log_error(
            f"Linked Production Plan Item not found for PO {doc.name}",
            "Purchase Order before_insert Error"
        )
    except Exception as e:
        frappe.log_error(
            f"Error setting custom_batch_no for PO {doc.name}: {str(e)}",
            "Purchase Order before_insert Error"
        )

    
def before_save(doc, method):
    for i in doc.items:
        i.po_line_no = i.idx
#     try:
#         _enrich_subcontract_items_from_production_plan_or_bom(doc)
#     except Exception as e:
#         frappe.log_error(f"PO before_save enrichment error for {getattr(doc, 'name', 'Unsaved')}: {str(e)}", "Purchase Order before_save Enrichment")

# def _enrich_subcontract_items_from_production_plan_or_bom(doc):
#     """When an item row is subcontracted, copy custom fields from Production Plan rows
#     (po_items / sub_assembly_items / mr_items) matching the item_code. If no production_plan
#     is linked on the item row, fallback to the latest matching BOM Item.

#     Fields copied (if present on PO Item):
#       - custom_drawing_no
#       - custom_drawing_rev_no
#       - custom_purchase_specification_no
#       - custom_purchase_specification_rev_no
#       - custom_pattern_drawing_no
#       - custom_pattern_drawing_rev_no
#     """
#     if not getattr(doc, "items", None):
#         return

#     custom_fields = [
#         "custom_drawing_no",
#         "custom_drawing_rev_no",
#         "custom_purchase_specification_no",
#         "custom_purchase_specification_rev_no",
#         "custom_pattern_drawing_no",
#         "custom_pattern_drawing_rev_no",
#     ]

#     for row in doc.items:
#         try:
#             # Only for subcontracted lines
#             if not getattr(row, "is_subcontracted", 0):
#                 continue

#             # Prefer Production Plan linked on the row (if any)
#             pp_name = getattr(row, "production_plan", None)
#             if pp_name:
#                 try:
#                     pp_doc = frappe.get_doc("Production Plan", pp_name)
#                 except Exception:
#                     pp_doc = None

#                 if pp_doc:
#                     copied = _copy_fields_from_pp_tables(pp_doc, row, custom_fields)
#                     if copied:
#                         continue  # Done for this row

#             # Fallback: copy from BOM Item by item_code (latest modified)
#             _copy_fields_from_bom_item(row, custom_fields)
#         except Exception as row_err:
#             frappe.log_error(
#                 f"PO Item enrichment error on row {getattr(row, 'idx', '?')} in {getattr(doc, 'name', 'Unsaved')}: {str(row_err)}",
#                 "Purchase Order Item Enrichment",
#             )

# def _copy_fields_from_pp_tables(pp_doc, po_item_row, fieldnames):
#     """Find a matching row by item_code in Production Plan's po_items, sub_assembly_items, or mr_items
#     and copy the provided fieldnames onto the Purchase Order Item row (only setting values that are empty).

#     Returns True if any field was copied, else False.
#     """
#     item_code = getattr(po_item_row, "item_code", None)
#     if not item_code:
#         return False

#     sources = []
#     try:
#         if getattr(pp_doc, "po_items", None):
#             sources.extend(pp_doc.po_items)
#     except Exception:
#         pass
#     try:
#         if getattr(pp_doc, "sub_assembly_items", None):
#             sources.extend(pp_doc.sub_assembly_items)
#     except Exception:
#         pass
#     try:
#         if getattr(pp_doc, "mr_items", None):
#             sources.extend(pp_doc.mr_items)
#     except Exception:
#         pass

#     # Find first matching source row by item_code; for sub-assemblies also consider production_item/parent_item_code
#     match = None
#     for src in sources:
#         try:
#             src_codes = [
#                 getattr(src, "item_code", None),
#                 getattr(src, "production_item", None),
#                 getattr(src, "parent_item_code", None),
#             ]
#             if item_code in src_codes:
#                 match = src
#                 break
#         except Exception:
#             continue
#     if not match:
#         return False

#     copied_any = False
#     for f in fieldnames:
#         if hasattr(po_item_row, f):
#             dst_val = getattr(po_item_row, f, None)
#             src_val = getattr(match, f, None)
#             if (not dst_val) and src_val:
#                 setattr(po_item_row, f, src_val)
#                 copied_any = True
#     return copied_any

# def _copy_fields_from_bom_item(po_item_row, fieldnames):
#     """Copy custom fields from the latest BOM Item where item_code matches the PO Item's item_code.
#     Copies only into empty fields on the PO item row.
#     """
#     item_code = getattr(po_item_row, "item_code", None)
#     if not item_code:
#         return False

#     try:
#         bom_item = frappe.get_all(
#             "BOM Item",
#             filters={"item_code": item_code},
#             fields=fieldnames,
#             order_by="modified desc",
#             limit=1,
#         )
#     except Exception:
#         bom_item = []

#     if not bom_item:
#         return False

#     src = bom_item[0]
#     copied_any = False
#     for f in fieldnames:
#         if hasattr(po_item_row, f):
#             dst_val = getattr(po_item_row, f, None)
#             src_val = src.get(f)
#             if (not dst_val) and src_val:
#                 setattr(po_item_row, f, src_val)
#                 copied_any = True
#     return copied_any
        

@frappe.whitelist()
def update_po_line(po):
    if not po:
        frappe.throw("Purchase Order name is required")

    try:
        po_doc = frappe.get_doc("Purchase Order", po)
        for item in po_doc.items:
            item.po_line_no = item.idx

        po_doc.save(ignore_permissions=True)
        return "Line numbers updated successfully"

    except frappe.DoesNotExistError:
        frappe.throw(f"Purchase Order {po} not found.")
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "update_po_line error")
        frappe.throw(f"Error updating PO line numbers: {str(e)}")




from frappe.model.mapper import get_mapped_doc

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_material_requests_with_pending_qty(doctype, txt, searchfield, start, page_len, filters):
	"""
	Show only those Material Requests that still have pending qty to order.
	Hide all MRs whose total item qty is fully covered by existing POs (Draft + Submitted).
	"""

	sql_query = """
		SELECT
			mr.name,
			mr.transaction_date,
			mr.schedule_date,
			mr.status
		FROM `tabMaterial Request` mr
		WHERE
			mr.docstatus = 1
			AND mr.material_request_type = %(material_request_type)s
			AND mr.company = %(company)s
			AND mr.status IN ('Pending', 'Partially Ordered', 'Partially Received')
			AND (
				mr.name LIKE %(txt)s
				OR mr.transaction_date LIKE %(txt)s
				OR mr.schedule_date LIKE %(txt)s
			)
			AND (
				-- Only include MRs where total MR qty > total ordered qty (non-cancelled)
				(
					SELECT IFNULL(SUM(mri.qty), 0)
					FROM `tabMaterial Request Item` mri
					WHERE mri.parent = mr.name
				)
				>
				IFNULL((
					SELECT SUM(poi.qty)
					FROM `tabPurchase Order Item` poi
					INNER JOIN `tabPurchase Order` po ON po.name = poi.parent
					WHERE poi.material_request = mr.name
					AND po.docstatus IN (0, 1)
				), 0)
			)
		ORDER BY
			CASE WHEN mr.name LIKE %(txt)s THEN 0 ELSE 1 END,
			mr.schedule_date DESC,
			mr.transaction_date DESC,
			mr.name DESC
		LIMIT %(page_len)s OFFSET %(start)s
	"""

	params = {
		'material_request_type': filters.get('material_request_type', 'Purchase'),
		'company': filters.get('company'),
		'txt': f"%{txt}%",
		'start': start,
		'page_len': page_len
	}

	return frappe.db.sql(sql_query, params, as_dict=False)



@frappe.whitelist()
def make_purchase_order_from_mr(source_name, target_doc=None, args=None):
	"""
	Create Purchase Order from Material Request with accurate pending quantities.
	This ensures only the remaining qty (not already in Draft/Submitted POs) is added.
	"""
	
	def update_item(source, target, parent):
		"""Calculate and set the pending quantity for each item"""
		
		# Get total quantity already ordered in Draft/Submitted POs (excluding Cancelled)
		ordered_qty = frappe.db.sql("""
			SELECT COALESCE(SUM(poi.qty), 0)
			FROM `tabPurchase Order Item` poi
			INNER JOIN `tabPurchase Order` po ON po.name = poi.parent
			WHERE poi.material_request = %s
				AND poi.material_request_item = %s
				AND po.docstatus IN (0, 1)
		""", (source.parent, source.name))[0][0] or 0
		
		# Calculate pending quantity
		pending_qty = source.qty - ordered_qty
		
		if pending_qty > 0:
			target.qty = pending_qty
			target.stock_qty = pending_qty * (source.conversion_factor or 1)
		else:
			# If no pending qty, set to 0 (will be filtered out)
			target.qty = 0
			target.stock_qty = 0
	
	def set_missing_values(source, target):
		"""Set default values and validate"""
		target.run_method("set_missing_values")
		target.run_method("calculate_taxes_and_totals")
	
	# Map Material Request to Purchase Order
	doclist = get_mapped_doc(
		"Material Request",
		source_name,
		{
			"Material Request": {
				"doctype": "Purchase Order",
				"validation": {
					"docstatus": ["=", 1],
					"material_request_type": ["=", "Purchase"]
				}
			},
			"Material Request Item": {
				"doctype": "Purchase Order Item",
				"field_map": {
					"name": "material_request_item",
					"parent": "material_request",
					"uom": "stock_uom",
					"sales_order": "sales_order"
				},
				"postprocess": update_item,
				"condition": lambda doc: doc.ordered_qty < doc.stock_qty
			}
		},
		target_doc,
		set_missing_values
	)
	
	# Remove items with 0 quantity (fully ordered)
	doclist.items = [item for item in doclist.items if item.qty > 0]
	
	return doclist


@frappe.whitelist()
def get_pending_qty_for_mr_item(material_request, material_request_item):
	"""
	Utility function to get pending quantity for a specific MR item.
	Returns the quantity not yet ordered in any Draft/Submitted PO.
	"""
	
	# Get original MR item qty
	mr_item = frappe.db.get_value(
		'Material Request Item',
		material_request_item,
		['qty', 'stock_qty', 'conversion_factor'],
		as_dict=True
	)
	
	if not mr_item:
		return 0
	
	# Get total ordered in Draft/Submitted POs
	ordered_qty = frappe.db.sql("""
		SELECT COALESCE(SUM(poi.qty), 0)
		FROM `tabPurchase Order Item` poi
		INNER JOIN `tabPurchase Order` po ON po.name = poi.parent
		WHERE poi.material_request = %s
			AND poi.material_request_item = %s
			AND po.docstatus IN (0, 1)
	""", (material_request, material_request_item))[0][0] or 0
	
	pending_qty = mr_item.qty - ordered_qty
	
	return {
		'original_qty': mr_item.qty,
		'ordered_qty': ordered_qty,
		'pending_qty': max(0, pending_qty)
	}



def is_po_fully_subcontracted(po_name):
	table = frappe.qb.DocType("Purchase Order Item")
	query = (
		frappe.qb.from_(table)
		.select(table.name)
		.where((table.parent == po_name) & (table.qty != table.subcontracted_quantity))
	)
	return not query.run(as_dict=True)

def get_mapped_subcontracting_order(source_name, target_doc=None):
	def post_process(source_doc, target_doc):
		target_doc.populate_items_table()

		
		if getattr(target_doc, "items", None):
			target_doc.items = [d for d in target_doc.items if getattr(d, "bom", None)]

		
		# Map custom_batch_no from PO -> Subcontracting Order Items.
		
		po_parent_batch_no = getattr(source_doc, "custom_batch_no", None)
		if po_parent_batch_no:
			target_doc.custom_batch_no = po_parent_batch_no

		if getattr(target_doc, "items", None):
			for d in target_doc.items:
				po_item_name = getattr(d, "purchase_order_item", None)
				po_item_batch_no = None
				if po_item_name:
					po_item_batch_no = frappe.db.get_value("Purchase Order Item", po_item_name, "custom_batch_no")

				batch_to_set = po_item_batch_no or po_parent_batch_no
				if batch_to_set and hasattr(d, "custom_batch_no") and not getattr(d, "custom_batch_no", None):
					d.custom_batch_no = batch_to_set

		if target_doc.set_warehouse:
			for item in target_doc.items:
				item.warehouse = target_doc.set_warehouse
		else:
			if source_doc.set_warehouse:
				for item in target_doc.items:
					item.warehouse = source_doc.set_warehouse
			else:
				for idx, item in enumerate(target_doc.items):
					item.warehouse = source_doc.items[idx].warehouse

	if target_doc and isinstance(target_doc, str):
		target_doc = json.loads(target_doc)
		for key in ["service_items", "items", "supplied_items"]:
			if key in target_doc:
				del target_doc[key]
		target_doc = json.dumps(target_doc)

	target_doc = get_mapped_doc(
		"Purchase Order",
		source_name,
		{
			"Purchase Order": {
				"doctype": "Subcontracting Order",
				"field_map": {},
				"field_no_map": ["total_qty", "total", "net_total"],
				"validation": {
					"docstatus": ["=", 1],
				},
			},
			"Purchase Order Item": {
				"doctype": "Subcontracting Order Service Item",
				"field_map": {
					"name": "purchase_order_item",
					
					"material_request": "material_request",
					"material_request_item": "material_request_item",
				},
				"field_no_map": ["qty", "fg_item_qty", "amount"],
				"condition": lambda item: item.qty != item.subcontracted_quantity,
			},
		},
		target_doc,
		post_process,
	)
	return target_doc


@frappe.whitelist()
def custom_make_subcontracting_order(source_name, target_doc=None, save=False, submit=False, notify=False):
	# frappe.log_error("custom_make_subcontracting_order overide is working")
	if not is_po_fully_subcontracted(source_name):
		target_doc = get_mapped_subcontracting_order(source_name, target_doc)

		if (save or submit) and frappe.has_permission(target_doc.doctype, "create"):
			target_doc.save()

			if submit and frappe.has_permission(target_doc.doctype, "submit", target_doc):
				try:
					target_doc.submit()
				except Exception as e:
					target_doc.add_comment("Comment", _("Submit Action Failed") + "<br><br>" + str(e))

			if notify:
				frappe.msgprint(
					_("Subcontracting Order {0} created.").format(
						get_link_to_form(target_doc.doctype, target_doc.name)
					),
					indicator="green",
					alert=True,
				)

		return target_doc
	else:
		frappe.throw(_("This PO has been fully subcontracted."))

