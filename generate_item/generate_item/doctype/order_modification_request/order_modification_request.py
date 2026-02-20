import frappe, json
from frappe.model.document import Document
from erpnext.controllers.accounts_controller import update_child_qty_rate
from frappe.desk.form.linked_with import (
	get_linked_doctypes,
	get_linked_docs,
)
from frappe import _

from frappe.utils import get_url_to_form

class OrderModificationRequest(Document):

	def validate(self):
		self.validate_sales_order()
		self.validate_qty_and_rev_qty()
		

	def on_submit(self):
		if self.type == "BOM" and self.bom:
			self.update_bom_items_using_db_set()

		# if self.type == "Sales Order" and self.sales_order:
		# 	self.update_sales_order_items_using_db_set()
   
		if self.type == "Sales Order" and self.sales_order:
			self.update_sales_order_values()

	def update_sales_order_items_using_db_set(self):
		if not self.sales_order:
			return

		#  Collect OMR item codes and line numbers for tracking
		omr_items = {(row.item, row.po_line_no) for row in self.items if row.item}

		# Get the current maximum index for new items
		current_max_idx = frappe.db.get_value("Sales Order Item", {"parent": self.sales_order}, "max(idx)") or 0

		#  Update or Insert items
		for row in self.items:
			# Construct update_data only with fields that have values
			update_data = {}
			
			# Always include qty if it's part of the revision
			if row.rev_qty:
				update_data["qty"] = row.rev_qty
				
			
			
			# Check if item exists in Sales Order using both item_code and po_line_no
			filters = {
				"parent": self.sales_order, 
				"parenttype": "Sales Order", 
				"item_code": row.item
			}
			
			# Add po_line_no to filters if it exists
			if row.po_line_no:
				filters["po_line_no"] = row.po_line_no
			
			so_item_name = frappe.db.get_value("Sales Order Item", filters, "name")

			if so_item_name:
				# Update existing record in submitted Sales Order
				frappe.db.set_value("Sales Order Item", so_item_name, update_data, update_modified=True)
			
			elif frappe.utils.flt(row.rev_qty) > 0:
				# Insert new record at the end
				current_max_idx += 1
				
				# Combine basic info with the revision data
				new_item_dict = {
					"doctype": "Sales Order Item",
					"parent": self.sales_order,
					"parenttype": "Sales Order",
					"parentfield": "items",
					"item_code": row.item,
					"idx": current_max_idx
				}
				
				# Add po_line_no if it exists
				if row.po_line_no:
					new_item_dict["po_line_no"] = row.po_line_no
				
				new_item_dict.update(update_data)
				
				new_so_item = frappe.get_doc(new_item_dict)
				# new_so_item.db_insert()
				new_so_item.save()	

		#  Delete Sales Order items not present in OMR
		so_items = frappe.db.get_all(
			"Sales Order Item",
			filters={"parent": self.sales_order, "parenttype": "Sales Order"},
			fields=["name", "item_code", "po_line_no"]
		)

		for so_row in so_items:
			# Check if the combination of item_code and po_line_no exists in OMR
			if (so_row.item_code, so_row.get("po_line_no")) not in omr_items:
				frappe.db.delete("Sales Order Item", so_row.name)

		# Finalize
		# Recalculate totals for the submitted Sales Order and update the header
		so_doc = frappe.get_doc("Sales Order", self.sales_order)
		so_doc.calculate_taxes_and_totals()
		so_doc.save()	
		# so_doc.db_update()

		

	


	def update_bom_items_using_db_set(self):
		if not self.bom:
			return

		#  Collect OMR item codes
		omr_items = {row.item for row in self.items if row.item}

		# Get the current maximum index for new items
		current_max_idx = frappe.db.get_value("BOM Item", {"parent": self.bom}, "max(idx)") or 0

		#  Update or Insert items
		for row in self.items:
			# Construct update_data only with fields that have values
			update_data = {}
			
			# Always include qty if it's part of the revision
			if row.rev_qty:
				update_data["qty"] = row.rev_qty
				
			# Use if-blocks for the custom fields to prevent overwriting with None/Empty
			if row.rev_drawing_no:
				update_data["custom_drawing_no"] = row.rev_drawing_no
			if row.rev_drawing_rev_no:
				update_data["custom_drawing_rev_no"] = row.rev_drawing_rev_no
			if row.rev_pattern_drawing_no:
				update_data["custom_pattern_drawing_no"] = row.rev_pattern_drawing_no
			if row.rev_pattern_drawing_rev_no:
				update_data["custom_pattern_drawing_rev_no"] = row.rev_pattern_drawing_rev_no
			if row.rev_purchase_specification_no:
				update_data["custom_purchase_specification_no"] = row.rev_purchase_specification_no
			if row.rev_purchase_specification_rev_no:
				update_data["custom_purchase_specification_rev_no"] = row.rev_purchase_specification_rev_no
			# Check if item exists in BOM
			bom_item_name = frappe.db.get_value(
				"BOM Item",
				{"parent": self.bom, "parenttype": "BOM", "item_code": row.item},
				"name"
			)

			
			

			if bom_item_name:
				# Update existing record in submitted BOM
				frappe.db.set_value("BOM Item", bom_item_name, update_data, update_modified=True)
			
			elif frappe.utils.flt(row.rev_qty) > 0:
				# Insert new record at the end
				current_max_idx += 1
				
				# Combine basic info with the revision data
				new_item_dict = {
					"doctype": "BOM Item",
					"parent": self.bom,
					"parenttype": "BOM",
					"parentfield": "items",
					"item_code": row.item,
					"idx": current_max_idx
				}
				new_item_dict.update(update_data)
				
				new_bom_item = frappe.get_doc(new_item_dict)
				new_bom_item.db_insert()

		#  Delete BOM items not present in OMR
		bom_items = frappe.db.get_all(
			"BOM Item",
			filters={"parent": self.bom, "parenttype": "BOM"},
			fields=["name", "item_code"]
		)

		for bom_row in bom_items:
			if bom_row.item_code not in omr_items:
				frappe.db.delete("BOM Item", bom_row.name)

		#  Finalize
		# Recalculate cost for the submitted BOM and update the header
		bom_doc = frappe.get_doc("BOM", self.bom)
		bom_doc.calculate_cost()
		bom_doc.db_update()

		



	def validate_qty_and_rev_qty(self):
		for row in self.items:
			qty = frappe.utils.flt(row.qty)
			rev_qty = frappe.utils.flt(row.rev_qty)

			if qty == 0 and rev_qty == 0:
				frappe.throw(
					f"Row {row.idx}: Rev Qty cannot be 0 when Qty is 0",
					title="Invalid Quantity"
				)


	def validate_sales_order(self):
		if not self.sales_order:
			return

		so = frappe.get_doc("Sales Order", self.sales_order)

		
		
		#  Check using status 
		if so.status == "Cancelled":
			frappe.throw(
				_("Sales Order {0} is cancelled. You cannot use a cancelled Sales Order.")
				.format(so.name)
			)
		# Completed Sales Order (business rule stop)
		elif so.status == "Completed":
			frappe.throw(
				_("Sales Order {0} is already completed. You cannot proceed with a completed Sales Order.")
				.format(so.name)
			)

	def update_sales_order_values(self):
		so = frappe.get_doc("Sales Order", self.sales_order)

		trans_items = []

		for row in self.items:
			qty = row.rev_qty if (row.rev_qty and row.rev_qty > 0) else row.qty
			rate = row.rev_rate if (row.rev_rate and row.rev_rate > 0) else row.rate

			# existing row → update
			if row.sales_order_item_name:
				trans_items.append({
					"docname": row.sales_order_item_name,
					"item_code": row.item,
					"qty": qty,
					"rate": rate,
				})
			else:
				trans_items.append({
					"__islocal": True,
					"item_code": row.item,
					"qty": qty,
					"rate": rate,
				})

		# save new rows
		so.save(ignore_permissions=True)

		# update existing rows
		if trans_items:
			update_child_qty_rate(
				self.type,
				json.dumps(trans_items),
				self.sales_order,
			)




@frappe.whitelist()
def get_linked_documents(items):
	"""
	items → frm.doc.items (list of dicts)
	"""
	if isinstance(items, str):
		items = frappe.parse_json(items)

	EXCLUDED_DOCTYPES = {"Bin", "Order Modification Request"}

	result = []

	for row in items:
		if not row.get("item"):
			continue

		linked_docs = get_all_linked_documents("Item", row.get("item"))

		for d in linked_docs:
			#  Exclude unwanted doctypes
			if d.get("ref_doctype") in EXCLUDED_DOCTYPES:
				continue

			result.append({
				"ref_doctype": d.get("ref_doctype"),
				"document_no": d.get("document_no"),
				"line_item": row.get("idx"),
			})

	return result






def get_all_linked_documents(source_doctype, source_name):
	"""
	Wrapper around ERPNext core Linked-With logic.
	Returns linked documents for a given document.
	"""

	
	frappe.has_permission(source_doctype, doc=source_name, throw=True)

	
	linkinfo = get_linked_doctypes(source_doctype)

	if not linkinfo:
		return []

	
	linked_docs = get_linked_docs(
		doctype=source_doctype,
		name=source_name,
		linkinfo=linkinfo
	)

	
	result = []

	for ref_doctype, docs in linked_docs.items():
		for doc in docs:
			# Ignore cancelled documents
			if doc.get("docstatus") == 2:
				continue

			result.append({
				"ref_doctype": ref_doctype,
				"document_no": doc.get("name"),
				
			})

	return result







