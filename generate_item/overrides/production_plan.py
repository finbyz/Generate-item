from erpnext.manufacturing.doctype.production_plan.production_plan import ProductionPlan as _ProductionPlan
import frappe
from frappe import _
from frappe.query_builder.functions import IfNull, Sum
from frappe.utils import flt
from pypika.terms import ExistsCriterion

class ProductionPlan(_ProductionPlan):
	@frappe.whitelist()
	def make_work_order(self):
		from erpnext.manufacturing.doctype.work_order.work_order import get_default_warehouse
		doc = frappe.get_all("Work Order", filters={"production_plan": self.name}, fields=["name"])
		if doc:
			frappe.throw("Work Order already exists")
		wo_list, po_list = [], []
		subcontracted_po = {}
		default_warehouses = get_default_warehouse()

		self.make_work_order_for_finished_goods(wo_list, default_warehouses)
		self.make_work_order_for_subassembly_items(wo_list, subcontracted_po, default_warehouses)
		self.make_subcontracted_purchase_order(subcontracted_po, po_list)
		self.show_list_created_message("Work Order", wo_list)
		self.show_list_created_message("Purchase Order", po_list)

		if not wo_list:
			frappe.msgprint(_("No Work Orders were created"))

	def get_so_items(self):
		"""Override to check previous Production Plans and calculate remaining quantities"""
		# Check for empty table or empty rows
		if not self.get("sales_orders") or not self.get_so_mr_list("sales_order", "sales_orders"):
			frappe.throw(_("Please fill the Sales Orders table"), title=_("Sales Orders Required"))

		so_list = self.get_so_mr_list("sales_order", "sales_orders")

		bom = frappe.qb.DocType("BOM")
		so_item = frappe.qb.DocType("Sales Order Item")
		pp_item = frappe.qb.DocType("Production Plan Item")

		# Get all Sales Order items with BOMs
		items_subquery = frappe.qb.from_(bom).select(bom.name).where(bom.is_active == 1)
		items_query = (
			frappe.qb.from_(so_item)
			.select(
				so_item.parent,
				so_item.item_code,
				so_item.warehouse,
				so_item.qty,
				so_item.work_order_qty,
				so_item.delivered_qty,
				so_item.conversion_factor,
				so_item.description,
				so_item.name,
				so_item.bom_no,
				so_item.custom_batch_no,
			)
			.distinct()
			.where(
				(so_item.parent.isin(so_list))
				& (so_item.docstatus == 1)
			)
		)

		if self.item_code and frappe.db.exists("Item", self.item_code):
			items_query = items_query.where(so_item.item_code == self.item_code)
			items_subquery = items_subquery.where(
				self.get_bom_item_condition() or bom.item == so_item.item_code
			)

		items_query = items_query.where(ExistsCriterion(items_subquery))
		items = items_query.run(as_dict=True)

		# Calculate remaining quantities by checking previous Production Plans
		items_with_remaining = []
		for item in items:
			# Calculate the actual pending quantity from Sales Order
			# pending_qty = qty - work_order_qty - delivered_qty
			original_pending_qty = flt(item.qty) - flt(item.work_order_qty or 0) - flt(item.delivered_qty or 0)
			
			# Get total planned quantity from previous Production Plans for this specific Sales Order Item line
			# This ensures line-by-line tracking - no merging of quantities for same item code in different lines
			# Include both submitted (docstatus = 1) and draft (docstatus = 0) production plans
			previous_planned_qty = frappe.db.sql("""
				SELECT SUM(ppi.planned_qty) as total_planned
				FROM `tabProduction Plan Item` ppi
				INNER JOIN `tabProduction Plan` pp ON ppi.parent = pp.name
				INNER JOIN `tabProduction Plan Sales Order` pps ON pp.name = pps.parent
				WHERE pps.sales_order = %s
				AND ppi.item_code = %s
				AND ppi.sales_order_item = %s
				AND pp.docstatus IN (0, 1)
				AND pp.name != %s
			""", (item.parent, item.item_code, item.name, self.name or ""), as_dict=True)
			
			total_planned = flt(previous_planned_qty[0].total_planned) if previous_planned_qty else 0
			
			# Calculate remaining quantity: new_doc pending_qty = new pending_qty - existing planning_qty
			remaining_qty = original_pending_qty - total_planned
			
			# Debug information (can be removed in production)
			if remaining_qty != original_pending_qty:
				pass
				# frappe.msgprint(f"Item: {item.item_code}, SO: {item.parent}, Original Pending: {original_pending_qty}, Previously Planned: {total_planned}, Remaining: {remaining_qty}", alert=True)
			
			# Set pending_qty and planned_qty to remaining quantity
			item.pending_qty = remaining_qty
			item.planned_qty = remaining_qty
			
			# Set BOM only if BOM matches Sales Order and custom_batch_no; accept active or default BOMs
			try:
				selected_bom = None
				if item.get("parent") and item.get("item_code") and item.get("custom_batch_no"):
					bom_candidate = frappe.get_all(
						"BOM",
						filters={
							"item": item.get("item_code"),
							"sales_order": item.get("parent"),
							"custom_batch_no": item.get("custom_batch_no"),
						},
						or_filters=[{"is_active": 1}, {"is_default": 1}],
						fields=["name"],
						order_by="modified desc",
						limit=1,
					)
					if bom_candidate:
						selected_bom = bom_candidate[0]["name"]
				if selected_bom:
					item.bom_no = selected_bom
			except Exception:
				# Non-fatal; continue without changing bom_no
				pass
			
			# Only include items with remaining quantity > 0
			if remaining_qty > 0:
				items_with_remaining.append(item)
		
		items = items_with_remaining

		# Handle packed items similarly
		pi = frappe.qb.DocType("Packed Item")
		packed_items_query = (
			frappe.qb.from_(so_item)
			.from_(pi)
			.select(
				pi.parent,
				pi.item_code,
				pi.warehouse.as_("warehouse"),
				pi.qty,
				pi.parent_item,
				pi.description,
				so_item.name,
			)
			.distinct()
			.where(
				(so_item.parent == pi.parent)
				& (so_item.docstatus == 1)
				& (pi.parent_item == so_item.item_code)
				& (so_item.parent.isin(so_list))
				& (
					ExistsCriterion(
						frappe.qb.from_(bom)
						.select(bom.name)
						.where((bom.item == pi.item_code) & (bom.is_active == 1))
					)
				)
			)
		)

		if self.item_code:
			packed_items_query = packed_items_query.where(so_item.item_code == self.item_code)

		packed_items = packed_items_query.run(as_dict=True)

		# Calculate remaining quantities for packed items
		packed_items_with_remaining = []
		for item in packed_items:
			# For packed items, the qty is already the pending quantity
			original_pending_qty = flt(item.qty)
			
			previous_planned_qty = frappe.db.sql("""
				SELECT SUM(ppi.planned_qty) as total_planned
				FROM `tabProduction Plan Item` ppi
				INNER JOIN `tabProduction Plan` pp ON ppi.parent = pp.name
				INNER JOIN `tabProduction Plan Sales Order` pps ON pp.name = pps.parent
				WHERE pps.sales_order = %s
				AND ppi.item_code = %s
				AND ppi.sales_order_item = %s
				AND pp.docstatus IN (0, 1)
				AND pp.name != %s
			""", (item.parent, item.item_code, item.name, self.name or ""), as_dict=True)
			
			total_planned = flt(previous_planned_qty[0].total_planned) if previous_planned_qty else 0
			
			# Calculate remaining quantity: new_doc pending_qty = new pending_qty - existing planning_qty
			remaining_qty = original_pending_qty - total_planned
			
			# Debug information (can be removed in production)
			if remaining_qty != original_pending_qty:
				frappe.msgprint(f"Packed Item: {item.item_code}, SO: {item.parent}, Line: {item.name}, Original Pending: {original_pending_qty}, Previously Planned: {total_planned}, Remaining: {remaining_qty}", alert=True)
			
			# Set pending_qty and planned_qty to remaining quantity
			item.pending_qty = remaining_qty
			item.planned_qty = remaining_qty

			# Set BOM only if BOM matches Sales Order and custom_batch_no; accept active or default BOMs
			try:
				selected_bom = None
				if item.get("parent") and item.get("item_code") and item.get("custom_batch_no"):
					bom_candidate = frappe.get_all(
						"BOM",
						filters={
							"item": item.get("item_code"),
							"sales_order": item.get("parent"),
							"custom_batch_no": item.get("custom_batch_no"),
						},
						or_filters=[{"is_active": 1}],
						fields=["name"],
						order_by="modified desc",
						limit=1,
					)
					if bom_candidate:
						selected_bom = bom_candidate[0]["name"]
				if selected_bom:
					item.bom_no = selected_bom
			except Exception:
				pass

			# Only include items with remaining quantity > 0
			if remaining_qty > 0:
				packed_items_with_remaining.append(item)

		self.add_items(items + packed_items_with_remaining)
		self.calculate_total_planned_qty()

	@frappe.whitelist()
	def get_items(self):
		"""Override get_items method to add custom logic"""
		# Add your custom logic here before calling the original method
		
		
		# Clear the po_items table
		self.set("po_items", [])
		
		# Add any custom validation or processing here
		if self.get_items_from == "Sales Order":
			# Call your custom get_so_items method
			self.get_so_items()
		elif self.get_items_from == "Material Request":
			# Call the original get_mr_items method or create a custom one
			self.get_mr_items()
