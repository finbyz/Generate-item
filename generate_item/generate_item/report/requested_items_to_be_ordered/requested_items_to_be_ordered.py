# Copyright (c) 2025, Finbyz and contributors
# For license information, please see license.txt





from frappe import _
import frappe
from frappe.utils import flt, getdate, nowdate


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": "Material Request", "fieldname": "name", "fieldtype": "Link", "options": "Material Request", "width": 160},
		{"label": "Batch No Ref", "fieldname": "custom_batch_no", "fieldtype": "Link", "options": "Batch", "width": 160},
        {"label": "Posting Date", "fieldname": "transaction_date", "fieldtype": "Date", "width": 100},
        {"label": "Required By", "fieldname": "schedule_date", "fieldtype": "Date", "width": 100},
        {"label": "MR Type", "fieldname": "material_request_type", "width": 120},
		{"label": "Supplier", "fieldname": "party_type","fieldtype": "Link", "options": "Supplier", "width": 120},
		{"label": "Created By", "fieldname": "created_by", "fieldtype": "Link", "options": "User", "width": 140},
        {"label": "Status", "fieldname": "status", "width": 120},
        {"label": "Item Code", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 140},
        {"label": "Item Name", "fieldname": "item_name", "width": 220},
		{"label": "Description", "fieldname": "description", "width": 220},
		{"label": "Drawing Number", "fieldname": "custom_drawing_no", "width": 220},
		{"label": "Drawing Rev No", "fieldname": "custom_drawing_rev_no", "width": 220},
        {"label": "Requested Qty", "fieldname": "qty", "fieldtype": "Float", "width": 120},
        {"label": "Ordered Qty", "fieldname": "ordered_qty", "fieldtype": "Float", "width": 120},
        {"label": "Draft Ordered Qty", "fieldname": "draft_ordered_qty", "fieldtype": "Float", "width": 120},
        {"label": "Pending Qty", "fieldname": "pending_qty", "fieldtype": "Float", "width": 120},
		{"label": "Last PO No", "fieldname": "last_po_no", "fieldtype": "Link", "options": "Purchase Order", "width": 150},
		{"label": "Last PO Date", "fieldname": "last_po_date", "fieldtype": "Date", "width": 110},
		{"label": "Last PO Supplier", "fieldname": "last_po_supplier", "fieldtype": "Link", "options": "Supplier", "width": 150},
		{"label": "Last PO Qty", "fieldname": "last_po_qty", "fieldtype": "Float", "width": 110},
		{"label": "Last PO Rate", "fieldname": "last_po_rate", "fieldtype": "Currency", "width": 110},
		{"label": "Age (Days)", "fieldname": "age", "fieldtype": "Int", "width": 90},
		{"label": "0-30", "fieldname": "range_0_30", "fieldtype": "Float", "width": 100},
		{"label": "31-60", "fieldname": "range_31_60", "fieldtype": "Float", "width": 100},
		{"label": "61-90", "fieldname": "range_61_90", "fieldtype": "Float", "width": 100},
		{"label": "91-120", "fieldname": "range_91_120", "fieldtype": "Float", "width": 100},
		{"label": "121+", "fieldname": "range_121_above", "fieldtype": "Float", "width": 100},

        {"label": "Warehouse", "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 160},
        {"label": "Company", "fieldname": "company", "width": 200},
    ]


def get_data(filters):
	conditions = []
	values = {}

	if filters.get("company"):
		conditions.append("mr.company = %(company)s")
		values["company"] = filters.get("company")

	# filter by created by (multi or single)
	created_by = filters.get("created_by")
	if created_by:
		if isinstance(created_by, str):
			created_by_list = [u.strip() for u in created_by.replace(",", "\n").split("\n") if u.strip()]
		else:
			created_by_list = created_by

		if created_by_list:
			conditions.append("mr.owner IN %(created_by)s")
			values["created_by"] = tuple(created_by_list)

	if filters.get("from_date"):
		conditions.append("mr.transaction_date >= %(from_date)s")
		values["from_date"] = filters.get("from_date")

	if filters.get("to_date"):
		conditions.append("mr.transaction_date <= %(to_date)s")
		values["to_date"] = filters.get("to_date")

	if filters.get("material_request_type"):
		conditions.append("mr.material_request_type = %(material_request_type)s")
		values["material_request_type"] = filters.get("material_request_type")

	# Drawing filters
	if filters.get("drawing_no"):
		conditions.append("mri.custom_drawing_no = %(drawing_no)s")
		values["drawing_no"] = filters.get("drawing_no")

	if filters.get("drawing_rev_no"):
		conditions.append("mri.custom_drawing_rev_no = %(drawing_rev_no)s")
		values["drawing_rev_no"] = filters.get("drawing_rev_no")

	if filters.get("status"):
		conditions.append("mr.status = %(status)s")
		values["status"] = filters.get("status")

	global_filters = "Purchase"
	if global_filters:
		conditions.append("mr.material_request_type = %(global_filters)s")
		values["global_filters"] = global_filters

	where_clause = " AND ".join(conditions)
	if where_clause:
		where_clause = " AND " + where_clause

	


	query = f"""
		SELECT
			mr.name,
			mr.transaction_date,
			mr.schedule_date,
			mr.material_request_type,
			mr.owner as created_by,
			mr.status,
			mr.company,
			mr.branch,

			mri.item_code,
			mri.item_name,
			mri.description,
			mri.custom_batch_no,
			mri.qty,
			IFNULL(mri.ordered_qty, 0) AS ordered_qty,
			mri.warehouse,
			mri.supplier as party_type,
			mri.custom_drawing_no,
			mri.custom_drawing_rev_no,
			mri.name as material_request_item,
			  
			mri.custom_pattern_drawing_no,
			mri.custom_pattern_drawing_rev_no,
			mri.custom_purchase_specification_no,
			mri.custom_purchase_specification_rev_no

		FROM `tabMaterial Request` mr
		INNER JOIN `tabMaterial Request Item` mri
			ON mri.parent = mr.name

		WHERE
			mr.docstatus = 1  and mr.status !="Ordered"
			{where_clause}

		ORDER BY
    		mr.transaction_date ASC, mr.name
	"""
	rows = frappe.db.sql(query, values, as_dict=True)

	today = getdate(nowdate())
	data = []
	# Map last purchase order (single latest) per item
	item_codes = list({row.item_code for row in rows if row.get("item_code")})
	last_po_by_item = {}

	if item_codes:
		last_po_rows = frappe.db.sql(
			"""
			SELECT
				poi.item_code,
				po.name as last_po_no,
				po.transaction_date as last_po_date,
				po.supplier as last_po_supplier,
				poi.qty as last_po_qty,
				poi.rate as last_po_rate
			FROM `tabPurchase Order Item` poi
			INNER JOIN `tabPurchase Order` po ON poi.parent = po.name
			WHERE
				poi.item_code IN %(item_codes)s
				AND po.docstatus = 1
			ORDER BY
				poi.item_code,
				po.transaction_date DESC,
				po.name DESC
			""",
			{"item_codes": tuple(item_codes)},
			as_dict=True,
		)

		for r in last_po_rows:
			# keep only the latest per item_code
			if r.item_code not in last_po_by_item:
				last_po_by_item[r.item_code] = r

	# Map draft ordered qty (docstatus = 0) per Material Request Item
	mr_items = [row.material_request_item for row in rows if row.get("material_request_item")]
	draft_ordered_by_mr_item = {}

	if mr_items:
		draft_rows = frappe.db.sql(
			"""
			SELECT
				material_request_item,
				SUM(qty) as draft_ordered_qty
			FROM `tabPurchase Order Item`
			WHERE
				docstatus = 0
				AND material_request_item IN %(mr_items)s
			GROUP BY material_request_item
			""",
			{"mr_items": tuple(mr_items)},
			as_dict=True,
		)

		for r in draft_rows:
			draft_ordered_by_mr_item[r.material_request_item] = flt(r.draft_ordered_qty)

	for row in rows:
		# include draft ordered qty in ordered_qty
		
		requested_qty = flt(row.qty or 0)
		ordered_qty = flt(row.ordered_qty or 0)
		draft_ordered_qty = flt(draft_ordered_by_mr_item.get(row.material_request_item, 0))
		pending_qty = requested_qty - ordered_qty - draft_ordered_qty


				
		if pending_qty == 0:
			continue

		age = (today - getdate(row.schedule_date)).days if row.schedule_date else 0

		row.update({
			"ordered_qty": ordered_qty,
			"draft_ordered_qty": draft_ordered_qty,
			"pending_qty": pending_qty,
			"age": age,
			"range_0_30": pending_qty if age <= 30 else 0,
			"range_31_60": pending_qty if 31 <= age <= 60 else 0,
			"range_61_90": pending_qty if 61 <= age <= 90 else 0,
			"range_91_120": pending_qty if 91 <= age <= 120 else 0,
			"range_121_above": pending_qty if age > 120 else 0,
		})

		# attach last purchase info if available
		last_po = last_po_by_item.get(row.item_code)
		if last_po:
			row.update(
				{
					"last_po_no": last_po.get("last_po_no"),
					"last_po_date": last_po.get("last_po_date"),
					"last_po_supplier": last_po.get("last_po_supplier"),
					"last_po_qty": last_po.get("last_po_qty"),
					"last_po_rate": last_po.get("last_po_rate"),
				}
			)

		data.append(row)

	return data





@frappe.whitelist()
def create_purchase_order_by_supplier(grouped_items, company, po_series=None, branch=None):
	"""
	Create Purchase order grouped by supplier

	Args:
		grouped_items: Dictionary with supplier as key and list of items as value
		company: Company name

	Returns:
		List of created purchase order documents
	"""
	import json

	# Parse grouped_items if it's a string
	if isinstance(grouped_items, str):
		grouped_items = json.loads(grouped_items)

	created_orders = []

	try:
		for supplier, items in grouped_items.items():
			if not items:
				continue
			
			# Create Purchase Order
			purchase_order = frappe.new_doc("Purchase Order")
			purchase_order.supplier = supplier
			# PO series (naming_series)
			if po_series:
				purchase_order.naming_series = po_series

			# Branch: from filter if provided, else from first item
			purchase_order.branch = branch or items[0].get("branch")
			# purchase_order.transaction_date = items[0].get("transaction_date") 


			purchase_order.transaction_date = nowdate()
			purchase_order.schedule_date = nowdate()
			# purchase_order.schedule_date = items[0].get("schedule_date") 

			
			
			
			
			# Add items to the Purchase order
			for item in items:
				
				purchase_order.append("items", {
				"item_code": item.get("item_code"),
				"item_name": item.get("item_name"),
				"description": item.get("description") or item.get("item_name"),
				"qty": item.get("pending_qty") or item.get("qty") or 1,
				"uom": item.get("uom") or frappe.db.get_value("Item", item.get("item_code"), "stock_uom"),
				"rate": item.get("rate") or 1,  #  IMPORTANT
				"warehouse": item.get("warehouse"),
				"branch":item.get("branch"),
				"schedule_date": item.get("schedule_date") ,
				# IMPORTANT LINKS
				"material_request": item.get("name"),
				"material_request_item": item.get("material_request_item"),
				# ✅ CUSTOM FIELD MAPPING (THIS WAS MISSING)
				"custom_batch_no": item.get("custom_batch_no"),
				"custom_drawing_no": item.get("custom_drawing_no"),
				"custom_drawing_rev_no": item.get("custom_drawing_rev_no"),
				"custom_pattern_drawing_no": item.get("custom_pattern_drawing_no"),
				"custom_pattern_drawing_rev_no": item.get("custom_pattern_drawing_rev_no"),
				"custom_purchase_specification_no": item.get("custom_purchase_specification_no"),
				"custom_purchase_specification_rev_no": item.get("custom_purchase_specification_rev_no"),
})

			
			# Set flags to ignore mandatory fields and validations
			purchase_order.flags.ignore_mandatory = True
			purchase_order.flags.ignore_validate = False  
			purchase_order.flags.ignore_permissions = True
			
			# Save as draft
			purchase_order.save(ignore_permissions=True)
			
			created_orders.append({
				"name": purchase_order.name,
				"supplier": supplier,
				"total_items": len(items),
				"status": "Success"
			})
			
			frappe.db.commit()
		
		if created_orders:
			frappe.msgprint(_("Successfully created {0} Purchase Order(s)").format(len(created_orders)))
		
		return created_orders

	except Exception as e:
		frappe.log_error(title=_("Purchase Order Creation Error"),message=frappe.get_traceback() )
		frappe.throw(_("Error creating purchase order: {0}").format(str(e)))


@frappe.whitelist()
def get_last_purchase_history(item_codes):
    import json

    if isinstance(item_codes, str):
        item_codes = json.loads(item_codes)

    if not item_codes:
        return []

    query = """
        SELECT
            poi.item_code,
            po.name AS po_no,
            po.transaction_date AS po_date,
            po.supplier,
            poi.qty,
            poi.rate
        FROM `tabPurchase Order Item` poi
        INNER JOIN `tabPurchase Order` po
            ON po.name = poi.parent
        WHERE
            poi.item_code IN %(item_codes)s
            AND po.docstatus = 1
            AND po.status NOT IN ('Cancelled', 'Closed')
        ORDER BY
            po.transaction_date DESC
    """

    rows = frappe.db.sql(
        query,
        {"item_codes": tuple(item_codes)},
        as_dict=True
    )

    # Pick last (latest) purchase per item
    seen = set()
    result = []
	

    for row in rows:
        if row.item_code not in seen:
            result.append(row)
            seen.add(row.item_code)

    return result



@frappe.whitelist()
def get_po_naming_series():
    meta = frappe.get_meta("Purchase Order")
    field = meta.get_field("naming_series")

    if not field or not field.options:
        return []

    return [opt for opt in field.options.split("\n") if opt]
