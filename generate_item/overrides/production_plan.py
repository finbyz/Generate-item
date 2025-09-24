# # # from erpnext.manufacturing.doctype.production_plan.production_plan import ProductionPlan as _ProductionPlan
# # # import frappe
# # # from frappe import _
# # # from frappe.query_builder.functions import IfNull, Sum
# # # from frappe.utils import flt
# # # from pypika.terms import ExistsCriterion

# # # class ProductionPlan(_ProductionPlan):
# # # 	@frappe.whitelist()
# # # 	def make_work_order(self):
# # # 		from erpnext.manufacturing.doctype.work_order.work_order import get_default_warehouse
# # # 		doc = frappe.get_all("Work Order", filters={"production_plan": self.name}, fields=["name"])
# # # 		if doc:
# # # 			frappe.throw("Work Order already exists")
# # # 		wo_list, po_list = [], []
# # # 		subcontracted_po = {}
# # # 		default_warehouses = get_default_warehouse()

# # # 		self.make_work_order_for_finished_goods(wo_list, default_warehouses)
# # # 		self.make_work_order_for_subassembly_items(wo_list, subcontracted_po, default_warehouses)
# # # 		self.make_subcontracted_purchase_order(subcontracted_po, po_list)
# # # 		self.show_list_created_message("Work Order", wo_list)
# # # 		self.show_list_created_message("Purchase Order", po_list)

# # # 		if not wo_list:
# # # 			frappe.msgprint(_("No Work Orders were created"))

# # # 	@frappe.whitelist()
# # # 	def get_sub_assembly_items(self, manufacturing_type=None):
# # # 		"""Override to ensure sub_assembly_items inherit custom fields from po_items"""
# # # 		# Call the original method first
# # # 		super().get_sub_assembly_items(manufacturing_type)
		
# # # 		# Now populate custom fields from parent po_items
# # # 		self._populate_subassembly_items_from_po_items()

# # # 	def _populate_subassembly_items_from_po_items(self):
# # # 		"""Populate subassembly items with custom fields from their parent po_items"""
# # # 		try:
# # # 			# Build mappings to find parent po_item quickly
# # # 			po_item_by_item_code = {}
# # # 			po_item_by_rowname = {}
# # # 			for po_item in self.po_items:
# # # 				if getattr(po_item, "item_code", None):
# # # 					po_item_by_item_code[po_item.item_code] = po_item
# # # 				if getattr(po_item, "name", None):
# # # 					po_item_by_rowname[po_item.name] = po_item

# # # 			# Update each sub_assembly_item with custom fields from its parent po_item
# # # 			for sub_item in self.sub_assembly_items:
# # # 				parent_po_item = None
# # # 				# 1) Best: link via production_plan_item (should equal po_items.name)
# # # 				ppi_name = getattr(sub_item, "production_plan_item", None)
# # # 				if ppi_name and ppi_name in po_item_by_rowname:
# # # 					parent_po_item = po_item_by_rowname.get(ppi_name)
# # # 				# if ppi_name:
# # # 				# 	parent_po_item = po_item_by_rowname.get(ppi_name)
# # # 				# 2) Fallback: link via parent_item_code (finished good code)
# # # 				if not parent_po_item:
# # # 					parent_code = getattr(sub_item, "parent_item_code", None)
# # # 					if parent_code:
# # # 						parent_po_item = po_item_by_item_code.get(parent_code)
# # # 				# 3) Last resort: match by subassembly's production_item
# # # 				if not parent_po_item:
# # # 					parent_po_item = po_item_by_item_code.get(getattr(sub_item, "production_item", None))
				
# # # 				if parent_po_item:
# # # 					# Inherit batch and branch from parent po_item (common fieldnames)
# # # 					parent_batch = (
# # # 						getattr(parent_po_item, "custom_batch_no", None)
# # # 						or getattr(parent_po_item, "custom_batch_ref", None)
# # # 						or getattr(parent_po_item, "batch_no", None)
# # # 					)
# # # 					if parent_batch:
# # # 						# support fieldname typo custom_bath_no as well
# # # 						if hasattr(sub_item, "custom_batch_no"):
# # # 							sub_item.custom_batch_no = parent_batch
# # # 						if hasattr(sub_item, "custom_bath_no"):
# # # 							sub_item.custom_bath_no = parent_batch
# # # 						elif hasattr(sub_item, "custom_batch_ref"):
# # # 							sub_item.custom_batch_ref = parent_batch
# # # 						elif hasattr(sub_item, "batch_no"):
# # # 							sub_item.batch_no = parent_batch
# # # 						# When batch info is present, set manufacturing type to In House
# # # 						if hasattr(sub_item, "type_of_manufacturing"):
# # # 							sub_item.type_of_manufacturing = "In House"
# # # 					if hasattr(parent_po_item, "branch") and getattr(parent_po_item, "branch", None):
# # # 						sub_item.branch = parent_po_item.branch
# # # 						if hasattr(sub_item, "custom_branch"):
# # # 							sub_item.custom_branch = parent_po_item.branch
					
# # # 					# Also inherit sales_order and sales_order_item for traceability
# # # 					if hasattr(parent_po_item, "sales_order") and getattr(parent_po_item, "sales_order", None):
# # # 						sub_item.sales_order = parent_po_item.sales_order
# # # 					if hasattr(parent_po_item, "sales_order_item") and getattr(parent_po_item, "sales_order_item", None):
# # # 						sub_item.sales_order_item = parent_po_item.sales_order_item

# # # 		except Exception as e:
# # # 			frappe.log_error(f"Error populating subassembly items from po_items: {str(e)}", "Subassembly Item Population Error")

# # # 	def make_work_order_for_subassembly_items(self, wo_list, subcontracted_po, default_warehouses):
# # # 		"""Override to ensure sub_assembly_items get correct values from Sales Order Items"""
# # # 		for row in self.sub_assembly_items:
# # # 			# Apply custom logic to fetch values from Sales Order Items
# # # 			self._populate_subassembly_item_from_sales_order(row)
			
# # # 			if row.type_of_manufacturing == "Subcontract":
# # # 				subcontracted_po.setdefault(row.supplier, []).append(row)
# # # 				continue

# # # 			if row.type_of_manufacturing == "Material Request":
# # # 				continue

# # # 			work_order_data = {
# # # 				"wip_warehouse": default_warehouses.get("wip_warehouse"),
# # # 				"fg_warehouse": default_warehouses.get("fg_warehouse"),
# # # 				"company": self.get("company"),
# # # 			}

# # # 			if flt(row.qty) <= flt(row.ordered_qty):
# # # 				continue

# # # 			# If linked Production Plan Item was removed, avoid fetching it downstream
# # # 			try:
# # # 				if getattr(row, "production_plan_item", None):
# # # 					if not frappe.db.exists("Production Plan Item", row.production_plan_item):
# # # 						row.production_plan_item = None
# # # 						if row.get("name"):  # persist change to child row if it already exists
# # # 							frappe.db.set_value(row.doctype, row.name, "production_plan_item", None)

# # # 			except Exception:
# # # 				pass

# # # 			self.prepare_data_for_sub_assembly_items(row, work_order_data)

# # # 			# Ensure branch and batch flow into Work Order for sub-assemblies
# # # 			try:
# # # 				# Branch from sub-assembly row
# # # 				if hasattr(row, "branch") and row.branch and not work_order_data.get("branch"):
# # # 					work_order_data["branch"] = row.branch
# # # 				# Sales Order context to allow hooks to resolve batch/branch
# # # 				if hasattr(row, "sales_order") and row.sales_order and not work_order_data.get("sales_order"):
# # # 					work_order_data["sales_order"] = row.sales_order
# # # 				if hasattr(row, "sales_order_item") and row.sales_order_item and not work_order_data.get("sales_order_item"):
# # # 					work_order_data["sales_order_item"] = row.sales_order_item
# # # 				# Batch from common custom fields
# # # 				row_batch = None
# # # 				if hasattr(row, "custom_batch_no") and row.custom_batch_no:
# # # 					row_batch = row.custom_batch_no
# # # 				elif hasattr(row, "custom_batch_ref") and row.custom_batch_ref:
# # # 					row_batch = row.custom_batch_ref
# # # 				elif hasattr(row, "batch_no") and row.batch_no:
# # # 					row_batch = row.batch_no
# # # 				if row_batch and not work_order_data.get("custom_batch_no"):
# # # 					work_order_data["custom_batch_no"] = row_batch

# # # 				# If still missing key context, try falling back to parent po_item
# # # 				if (
# # # 					(not work_order_data.get("custom_batch_no") or not work_order_data.get("branch") or not work_order_data.get("sales_order") or not work_order_data.get("sales_order_item"))
# # # 					and getattr(self, "po_items", None)
# # # 				):
# # # 					po_item_by_rowname = {getattr(d, "name", None): d for d in self.po_items if getattr(d, "name", None)}
# # # 					parent_po_item = po_item_by_rowname.get(getattr(row, "production_plan_item", None))
# # # 					if parent_po_item:
# # # 						if not work_order_data.get("custom_batch_no"):
# # # 							parent_batch = (
# # # 								getattr(parent_po_item, "custom_batch_no", None)
# # # 								or getattr(parent_po_item, "custom_batch_ref", None)
# # # 								or getattr(parent_po_item, "batch_no", None)
# # # 							)
# # # 							if parent_batch:
# # # 								work_order_data["custom_batch_no"] = parent_batch
# # # 						if not work_order_data.get("branch") and getattr(parent_po_item, "branch", None):
# # # 							work_order_data["branch"] = parent_po_item.branch
# # # 						if not work_order_data.get("sales_order") and getattr(parent_po_item, "sales_order", None):
# # # 							work_order_data["sales_order"] = parent_po_item.sales_order
# # # 						if not work_order_data.get("sales_order_item") and getattr(parent_po_item, "sales_order_item", None):
# # # 							work_order_data["sales_order_item"] = parent_po_item.sales_order_item
# # # 			except Exception:
# # # 				# Non-fatal; continue without blocking WO creation
# # # 				pass

# # # 			if work_order_data.get("qty") <= 0:
# # # 				continue

# # # 			work_order = self.create_work_order(work_order_data)
# # # 			if work_order:
# # # 				wo_list.append(work_order)


# # # 	def _populate_subassembly_item_from_sales_order(self, row):
# # # 		"""Populate subassembly item with values from Sales Order Items"""
# # # 		try:
# # # 			# Get the production plan item that this subassembly item is related to
# # # 			if hasattr(row, 'production_plan_item') and row.production_plan_item:
# # # 				try:
# # # 					if frappe.db.exists("Production Plan Item", row.production_plan_item):
# # # 						production_plan_item = frappe.get_doc("Production Plan Item", row.production_plan_item)
# # # 				except Exception:
# # # 					production_plan_item = None

# # # 			# Fallback: try to find the production plan item by item_code
# # # 			if not production_plan_item:
# # # 				pp_items = frappe.get_all(
# # # 					"Production Plan Item",
# # # 					filters={"parent": self.name, "item_code": row.production_item},
# # # 					fields=["name", "sales_order", "sales_order_item"],
# # # 					limit=1
# # # 				)
# # # 				if pp_items:
# # # 					production_plan_item = frappe.get_doc("Production Plan Item", pp_items[0].name)

# # # 			if not production_plan_item:
# # # 				return

# # # 			sales_order = getattr(production_plan_item, "sales_order", None)
# # # 			sales_order_item = getattr(production_plan_item, "sales_order_item", None)
# # # 			item_code = getattr(production_plan_item, "item_code", None)

# # # 			if not sales_order:
# # # 				return

# # # 			# Prefer exact Sales Order Item link; fallback to first matching by item_code in SO
# # # 			soi_filters = {"parent": sales_order}
# # # 			if sales_order_item:
# # # 				soi_filters["name"] = sales_order_item
# # # 			elif item_code:
# # # 				soi_filters["item_code"] = item_code

# # # 			soi = frappe.get_all(
# # # 				"Sales Order Item",
# # # 				filters=soi_filters,
# # # 				fields=["name", "custom_batch_no", "bom_no", "idx", "branch"],
# # # 				order_by="idx asc",
# # # 				limit=1,
# # # 			)

# # # 			if not soi:
# # # 				return

# # # 			soi = soi[0]

# # # 			# Set custom fields from Sales Order Item
# # # 			if hasattr(row, 'custom_batch_no'):
# # # 				row.custom_batch_no = soi.get("custom_batch_no") or None
# # # 			if hasattr(row, 'branch'):
# # # 				row.branch = soi.get("branch") or None

# # # 		except Exception as e:
# # # 			frappe.log_error(f"Error populating subassembly item from sales order: {str(e)}", "Subassembly Item Population Error")

# # # 	def get_so_items(self):
# # # 		"""Override to check previous Production Plans and calculate remaining quantities"""
# # # 		# Check for empty table or empty rows
# # # 		if not self.get("sales_orders") or not self.get_so_mr_list("sales_order", "sales_orders"):
# # # 			frappe.throw(_("Please fill the Sales Orders table"), title=_("Sales Orders Required"))

# # # 		so_list = self.get_so_mr_list("sales_order", "sales_orders")

# # # 		bom = frappe.qb.DocType("BOM")
# # # 		so_item = frappe.qb.DocType("Sales Order Item")
# # # 		pp_item = frappe.qb.DocType("Production Plan Item")

# # # 		# Get all Sales Order items with BOMs
# # # 		items_subquery = frappe.qb.from_(bom).select(bom.name).where(bom.is_active == 1)
# # # 		items_query = (
# # # 			frappe.qb.from_(so_item)
# # # 			.select(
# # # 				so_item.parent,
# # # 				so_item.item_code,
# # # 				so_item.warehouse,
# # # 				so_item.qty,
# # # 				so_item.work_order_qty,
# # # 				so_item.delivered_qty,
# # # 				so_item.conversion_factor,
# # # 				so_item.description,
# # # 				so_item.name,
# # # 				so_item.bom_no,
# # # 				so_item.custom_batch_no,
# # # 				so_item.branch,
# # # 			)
# # # 			.distinct()
# # # 			.where(
# # # 				(so_item.parent.isin(so_list))
# # # 				& (so_item.docstatus == 1)
# # # 			)
# # # 		)

# # # 		if self.item_code and frappe.db.exists("Item", self.item_code):
# # # 			items_query = items_query.where(so_item.item_code == self.item_code)
# # # 			items_subquery = items_subquery.where(
# # # 				self.get_bom_item_condition() or bom.item == so_item.item_code
# # # 			)

# # # 		items_query = items_query.where(ExistsCriterion(items_subquery))
# # # 		items = items_query.run(as_dict=True)

# # # 		# Calculate remaining quantities by checking previous Production Plans
# # # 		items_with_remaining = []
# # # 		for item in items:
# # # 			# Use original Sales Order qty directly (not affected by work_order_qty from previous plans)
# # # 			original_pending_qty = flt(item.qty)
			
# # # 			# Get total planned quantity from previous Production Plans for this specific Sales Order Item line
# # # 			# This ensures line-by-line tracking - no merging of quantities for same item code in different lines
# # # 			# Include both submitted (docstatus = 1) and draft (docstatus = 0) production plans
# # # 			previous_planned_qty = frappe.db.sql("""
# # # 				SELECT SUM(ppi.planned_qty) as total_planned
# # # 				FROM `tabProduction Plan Item` ppi
# # # 				INNER JOIN `tabProduction Plan` pp ON ppi.parent = pp.name
# # # 				INNER JOIN `tabProduction Plan Sales Order` pps ON pp.name = pps.parent
# # # 				WHERE pps.sales_order = %s
# # # 				AND ppi.item_code = %s
# # # 				AND ppi.sales_order_item = %s
# # # 				AND pp.docstatus IN (0, 1)
# # # 				AND pp.name != %s
# # # 			""", (item.parent, item.item_code, item.name, self.name or ""), as_dict=True)
			
# # # 			total_planned = flt(previous_planned_qty[0].total_planned) if previous_planned_qty else 0
			
# # # 			# Convert SO pending qty to stock UOM, then subtract previously planned (already in stock UOM)
# # # 			stock_pending_qty = original_pending_qty * flt(item.conversion_factor or 1)
# # # 			remaining_qty = stock_pending_qty - total_planned
# # # 			if remaining_qty < 0:
# # # 				remaining_qty = 0
			
# # # 			# Set pending_qty and planned_qty to remaining quantity (stock UOM)
# # # 			item.pending_qty = remaining_qty
# # # 			item.planned_qty = remaining_qty
			
# # # 			# Set BOM only if BOM matches Sales Order and custom_batch_no; accept active or default BOMs
# # # 			try:
# # # 				selected_bom = None
# # # 				if item.get("parent") and item.get("item_code") and item.get("custom_batch_no"):
# # # 					bom_candidate = frappe.get_all(
# # # 						"BOM",
# # # 						filters={
# # # 							"item": item.get("item_code"),
# # # 							"sales_order": item.get("parent"),
# # # 							"custom_batch_no": item.get("custom_batch_no"),
# # # 						},
# # # 						or_filters=[{"is_active": 1}, {"is_default": 1}],
# # # 						fields=["name"],
# # # 						order_by="modified desc",
# # # 						limit=1,
# # # 					)
# # # 					if bom_candidate:
# # # 						selected_bom = bom_candidate[0]["name"]
# # # 				if selected_bom:
# # # 					item.bom_no = selected_bom
# # # 			except Exception:
# # # 				# Non-fatal; continue without changing bom_no
# # # 				pass
			
# # # 			# Only include items with remaining quantity > 0
# # # 			if remaining_qty > 0:
# # # 				items_with_remaining.append(item)
		
# # # 		items = items_with_remaining

# # # 		# Handle packed items similarly
# # # 		pi = frappe.qb.DocType("Packed Item")
# # # 		packed_items_query = (
# # # 			frappe.qb.from_(so_item)
# # # 			.from_(pi)
# # # 			.select(
# # # 				pi.parent,
# # # 				pi.item_code,
# # # 				pi.warehouse.as_("warehouse"),
# # # 				pi.qty,
# # # 				pi.parent_item,
# # # 				pi.description,
# # # 				so_item.name,
# # # 				so_item.branch,
# # # 			)
# # # 			.distinct()
# # # 			.where(
# # # 				(so_item.parent == pi.parent)
# # # 				& (so_item.docstatus == 1)
# # # 				& (pi.parent_item == so_item.item_code)
# # # 				& (so_item.parent.isin(so_list))
# # # 				& (
# # # 					ExistsCriterion(
# # # 						frappe.qb.from_(bom)
# # # 						.select(bom.name)
# # # 						.where((bom.item == pi.item_code) & (bom.is_active == 1))
# # # 					)
# # # 				)
# # # 			)
# # # 		)

# # # 		if self.item_code:
# # # 			packed_items_query = packed_items_query.where(so_item.item_code == self.item_code)

# # # 		packed_items = packed_items_query.run(as_dict=True)

# # # 		# Calculate remaining quantities for packed items
# # # 		packed_items_with_remaining = []
# # # 		for item in packed_items:
# # # 			# For packed items, the qty is already the pending quantity, convert to stock UOM
# # # 			original_pending_qty = flt(item.qty)
			
# # # 			previous_planned_qty = frappe.db.sql("""
# # # 				SELECT SUM(ppi.planned_qty) as total_planned
# # # 				FROM `tabProduction Plan Item` ppi
# # # 				INNER JOIN `tabProduction Plan` pp ON ppi.parent = pp.name
# # # 				INNER JOIN `tabProduction Plan Sales Order` pps ON pp.name = pps.parent
# # # 				WHERE pps.sales_order = %s
# # # 				AND ppi.item_code = %s
# # # 				AND ppi.sales_order_item = %s
# # # 				AND pp.docstatus IN (0, 1)
# # # 				AND pp.name != %s
# # # 			""", (item.parent, item.item_code, item.name, self.name or ""), as_dict=True)
			
# # # 			total_planned = flt(previous_planned_qty[0].total_planned) if previous_planned_qty else 0
			
# # # 			# Calculate remaining quantity in stock UOM
# # # 			stock_pending_qty = original_pending_qty
# # # 			remaining_qty = stock_pending_qty - total_planned
# # # 			if remaining_qty < 0:
# # # 				remaining_qty = 0
			
			
# # # 			# Set pending_qty and planned_qty to remaining quantity
# # # 			item.pending_qty = remaining_qty
# # # 			item.planned_qty = remaining_qty

# # # 			# Set BOM only if BOM matches Sales Order and custom_batch_no; accept active or default BOMs
# # # 			try:
# # # 				selected_bom = None
# # # 				if item.get("parent") and item.get("item_code") and item.get("custom_batch_no"):
# # # 					bom_candidate = frappe.get_all(
# # # 						"BOM",
# # # 						filters={
# # # 							"item": item.get("item_code"),
# # # 							"sales_order": item.get("parent"),
# # # 							"custom_batch_no": item.get("custom_batch_no"),
# # # 						},
# # # 						or_filters=[{"is_active": 1}],
# # # 						fields=["name"],
# # # 						order_by="modified desc",
# # # 						limit=1,
# # # 					)
# # # 					if bom_candidate:
# # # 						selected_bom = bom_candidate[0]["name"]
# # # 				if selected_bom:
# # # 					item.bom_no = selected_bom
# # # 			except Exception:
# # # 				pass

# # # 			# Only include items with remaining quantity > 0
# # # 			if remaining_qty > 0:
# # # 				packed_items_with_remaining.append(item)

# # # 		self.add_items(items + packed_items_with_remaining)

# # # 		# Explicitly propagate branch from Sales Order Item to Production Plan Item
# # # 		try:
# # # 			item_to_branch = {}
# # # 			for it in (items + packed_items_with_remaining):
# # # 				soi = getattr(it, "name", None) or it.get("name") if isinstance(it, dict) else None
# # # 				br = getattr(it, "branch", None) or (it.get("branch") if isinstance(it, dict) else None)
# # # 				if soi and br:
# # # 					item_to_branch[soi] = br
# # # 			for d in self.get("po_items", []):
# # # 				if not getattr(d, "branch", None) and getattr(d, "sales_order_item", None):
# # # 					br = item_to_branch.get(d.sales_order_item)
# # # 					if br:
# # # 						d.branch = br
# # # 		except Exception:
# # # 			pass

# # # 		self.calculate_total_planned_qty()

# # # 	@frappe.whitelist()
# # # 	def get_items(self):
# # # 		"""Override get_items method to add custom logic"""
# # # 		# Add your custom logic here before calling the original method
		
		
# # # 		# Clear the po_items table
# # # 		self.set("po_items", [])
		
# # # 		# Add any custom validation or processing here
# # # 		if self.get_items_from == "Sales Order":
# # # 			# Call your custom get_so_items method
# # # 			self.get_so_items()
# # # 		elif self.get_items_from == "Material Request":
# # # 			# Call the original get_mr_items method or create a custom one
# # # 			self.get_mr_items()










# from erpnext.manufacturing.doctype.production_plan.production_plan import ProductionPlan as _ProductionPlan
# import frappe
# from frappe import _
# from frappe.query_builder.functions import IfNull, Sum
# from frappe.utils import flt
# from pypika.terms import ExistsCriterion

# class ProductionPlan(_ProductionPlan):
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         # Run cleanup only if po_items is populated and document is saved
#         if hasattr(self, 'name') and self.name and hasattr(self, 'po_items') and self.po_items:
#             try:
#                 cleanup_all_orphaned_references(self)
#             except Exception as e:
#                 frappe.log_error(f"Cleanup error in __init__: {str(e)}", "Production Plan Init Cleanup")

#     @frappe.whitelist()
#     def make_work_order(self):
#         from erpnext.manufacturing.doctype.work_order.work_order import get_default_warehouse
#         doc = frappe.get_all("Work Order", filters={"production_plan": self.name}, fields=["name"])
#         if doc:
#             frappe.throw("Work Order already exists")
#         wo_list, po_list = [], []
#         subcontracted_po = {}
#         default_warehouses = get_default_warehouse()

#         self.make_work_order_for_finished_goods(wo_list, default_warehouses)
#         self.make_work_order_for_subassembly_items(wo_list, subcontracted_po, default_warehouses)
#         self.make_subcontracted_purchase_order(subcontracted_po, po_list)
#         self.show_list_created_message("Work Order", wo_list)
#         self.show_list_created_message("Purchase Order", po_list)

#         if not wo_list:
#             frappe.msgprint(_("No Work Orders were created"))

#     @frappe.whitelist()
#     def get_sub_assembly_items(self, manufacturing_type=None):
#         """Override to ensure sub_assembly_items inherit custom fields from po_items"""
#         # Clean up first, but only if po_items is populated
#         if hasattr(self, 'po_items') and self.po_items:
#             try:
#                 cleanup_all_orphaned_references(self)
#             except Exception as e:
#                 frappe.log_error(f"Cleanup error in get_sub_assembly_items: {str(e)}", "Subassembly Cleanup")
                
#         # Call the original method first
#         super().get_sub_assembly_items(manufacturing_type)
        
#         # Now populate custom fields from parent po_items
#         self._populate_subassembly_items_from_po_items()

#     def _populate_subassembly_items_from_po_items(self):
#         """Populate subassembly items with custom fields from their parent po_items"""
#         try:
#             # Build mappings to find parent po_item quickly
#             po_item_by_item_code = {}
#             po_item_by_rowname = {}
#             for po_item in self.po_items:
#                 if getattr(po_item, "item_code", None):
#                     po_item_by_item_code[po_item.item_code] = po_item
#                 if getattr(po_item, "name", None):
#                     po_item_by_rowname[po_item.name] = po_item

#             # Update each sub_assembly_item with custom fields from its parent po_item
#             for sub_item in self.sub_assembly_items:
#                 parent_po_item = None
#                 # 1) Best: link via production_plan_item (should equal po_items.name)
#                 ppi_name = getattr(sub_item, "production_plan_item", None)
#                 if ppi_name and ppi_name in po_item_by_rowname:
#                     parent_po_item = po_item_by_rowname.get(ppi_name)
#                 # 2) Fallback: link via parent_item_code (finished good code)
#                 if not parent_po_item:
#                     parent_code = getattr(sub_item, "parent_item_code", None)
#                     if parent_code:
#                         parent_po_item = po_item_by_item_code.get(parent_code)
#                 # 3) Last resort: match by subassembly's production_item
#                 if not parent_po_item:
#                     parent_po_item = po_item_by_item_code.get(getattr(sub_item, "production_item", None))
                
#                 if parent_po_item:
#                     # Inherit batch and branch from parent po_item (common fieldnames)
#                     parent_batch = (
#                         getattr(parent_po_item, "custom_batch_no", None)
#                         or getattr(parent_po_item, "custom_batch_ref", None)
#                         or getattr(parent_po_item, "batch_no", None)
#                     )
#                     if parent_batch:
#                         if hasattr(sub_item, "custom_batch_no"):
#                             sub_item.custom_batch_no = parent_batch
#                         if hasattr(sub_item, "custom_bath_no"):
#                             sub_item.custom_bath_no = parent_batch
#                         elif hasattr(sub_item, "custom_batch_ref"):
#                             sub_item.custom_batch_ref = parent_batch
#                         elif hasattr(sub_item, "batch_no"):
#                             sub_item.batch_no = parent_batch
#                         if hasattr(sub_item, "type_of_manufacturing"):
#                             sub_item.type_of_manufacturing = "In House"
#                     if hasattr(parent_po_item, "branch") and getattr(parent_po_item, "branch", None):
#                         sub_item.branch = parent_po_item.branch
#                         if hasattr(sub_item, "custom_branch"):
#                             sub_item.custom_branch = parent_po_item.branch
                    
#                     if hasattr(parent_po_item, "sales_order") and getattr(parent_po_item, "sales_order", None):
#                         sub_item.sales_order = parent_po_item.sales_order
#                     if hasattr(parent_po_item, "sales_order_item") and getattr(parent_po_item, "sales_order_item", None):
#                         sub_item.sales_order_item = parent_po_item.sales_order_item

#         except Exception as e:
#             frappe.log_error(f"Error populating subassembly items from po_items: {str(e)}", "Subassembly Item Population Error")

#     def make_work_order_for_subassembly_items(self, wo_list, subcontracted_po, default_warehouses):
#         """Override to ensure sub_assembly_items get correct values from Sales Order Items"""
#         if hasattr(self, 'po_items') and self.po_items:
#             try:
#                 cleanup_all_orphaned_references(self)
#             except Exception:
#                 pass
                
#         clean_orphaned_subassemblies(self)
#         for row in self.sub_assembly_items:
#             self._populate_subassembly_item_from_sales_order(row)
            
#             if row.type_of_manufacturing == "Subcontract":
#                 subcontracted_po.setdefault(row.supplier, []).append(row)
#                 continue

#             if row.type_of_manufacturing == "Material Request":
#                 continue

#             work_order_data = {
#                 "wip_warehouse": default_warehouses.get("wip_warehouse"),
#                 "fg_warehouse": default_warehouses.get("fg_warehouse"),
#                 "company": self.get("company"),
#             }

#             if flt(row.qty) <= flt(row.ordered_qty):
#                 continue

#             try:
#                 if getattr(row, "production_plan_item", None):
#                     if not frappe.db.exists("Production Plan Item", row.production_plan_item):
#                         frappe.log_error(
#                             f"Orphaned Production Plan Item reference found: {row.production_plan_item}. Clearing reference.",
#                             "Orphaned Production Plan Item Reference"
#                         )
#                         row.production_plan_item = None
#                         if row.get("name"):
#                             frappe.db.set_value(row.doctype, row.name, "production_plan_item", None)
#                             frappe.db.commit()
#             except Exception as e:
#                 frappe.log_error(
#                     f"Error checking Production Plan Item existence: {str(e)}",
#                     "Production Plan Item Check Error"
#                 )
#                 row.production_plan_item = None

#             self.safe_prepare_data_for_sub_assembly_items(row, work_order_data)

#             try:
#                 if hasattr(row, "branch") and row.branch and not work_order_data.get("branch"):
#                     work_order_data["branch"] = row.branch
#                 if hasattr(row, "sales_order") and row.sales_order and not work_order_data.get("sales_order"):
#                     work_order_data["sales_order"] = row.sales_order
#                 if hasattr(row, "sales_order_item") and row.sales_order_item and not work_order_data.get("sales_order_item"):
#                     work_order_data["sales_order_item"] = row.sales_order_item
#                 row_batch = None
#                 if hasattr(row, "custom_batch_no") and row.custom_batch_no:
#                     row_batch = row.custom_batch_no
#                 elif hasattr(row, "custom_batch_ref") and row.custom_batch_ref:
#                     row_batch = row.custom_batch_ref
#                 elif hasattr(row, "batch_no") and row.batch_no:
#                     row_batch = row.batch_no
#                 if row_batch and not work_order_data.get("custom_batch_no"):
#                     work_order_data["custom_batch_no"] = row_batch

#                 if (
#                     (not work_order_data.get("custom_batch_no") or not work_order_data.get("branch") or not work_order_data.get("sales_order") or not work_order_data.get("sales_order_item"))
#                     and getattr(self, "po_items", None)
#                 ):
#                     po_item_by_rowname = {getattr(d, "name", None): d for d in self.po_items if getattr(d, "name", None)}
#                     parent_po_item = po_item_by_rowname.get(getattr(row, "production_plan_item", None))
#                     if parent_po_item:
#                         if not work_order_data.get("custom_batch_no"):
#                             parent_batch = (
#                                 getattr(parent_po_item, "custom_batch_no", None)
#                                 or getattr(parent_po_item, "custom_batch_ref", None)
#                                 or getattr(parent_po_item, "batch_no", None)
#                             )
#                             if parent_batch:
#                                 work_order_data["custom_batch_no"] = parent_batch
#                         if not work_order_data.get("branch") and getattr(parent_po_item, "branch", None):
#                             work_order_data["branch"] = parent_po_item.branch
#                         if not work_order_data.get("sales_order") and getattr(parent_po_item, "sales_order", None):
#                             work_order_data["sales_order"] = parent_po_item.sales_order
#                         if not work_order_data.get("sales_order_item") and getattr(parent_po_item, "sales_order_item", None):
#                             work_order_data["sales_order_item"] = parent_po_item.sales_order_item
#             except Exception:
#                 pass

#             if work_order_data.get("qty") <= 0:
#                 continue

#             work_order = self.create_work_order(work_order_data)
#             if work_order:
#                 wo_list.append(work_order)
    
#     def prepare_data_for_sub_assembly_items(self, row, work_order_data):
#         return self.safe_prepare_data_for_sub_assembly_items(row, work_order_data)

#     def safe_prepare_data_for_sub_assembly_items(self, row, work_order_data):
#         try:
#             production_plan_item = None
#             if getattr(row, "production_plan_item", None):
#                 if frappe.db.exists("Production Plan Item", row.production_plan_item):
#                     try:
#                         production_plan_item = frappe.get_doc("Production Plan Item", row.production_plan_item)
#                     except Exception as e:
#                         frappe.log_error(
#                             f"Error fetching Production Plan Item {row.production_plan_item}: {str(e)}",
#                             "Production Plan Item Fetch Error"
#                         )
#                         production_plan_item = None
#                         row.production_plan_item = None
#                 else:
#                     frappe.log_error(
#                         f"Production Plan Item {row.production_plan_item} does not exist. Clearing reference.",
#                         "Missing Production Plan Item"
#                     )
#                     row.production_plan_item = None
#                     if row.get("name"):
#                         frappe.db.set_value(row.doctype, row.name, "production_plan_item", None)
#                         frappe.db.commit()
            
#             if not production_plan_item and hasattr(row, 'production_item'):
#                 try:
#                     for po_item in self.po_items:
#                         if getattr(po_item, 'item_code') == getattr(row, 'production_item'):
#                             production_plan_item = po_item
#                             break
#                 except Exception:
#                     pass
            
#             work_order_data.update({
#                 "production_item": getattr(row, "production_item", None),
#                 "qty": flt(row.qty) - flt(row.ordered_qty),
#                 "description": getattr(row, "description", ""),
#                 "bom_no": getattr(row, "bom_no", None),
#                 "stock_uom": getattr(row, "stock_uom", None),
#                 "production_plan": self.name,
#                 "production_plan_sub_assembly_item": getattr(row, "name", None),
#             })
            
#             if production_plan_item:
#                 work_order_data.update({
#                     "sales_order": getattr(production_plan_item, "sales_order", None),
#                     "sales_order_item": getattr(production_plan_item, "sales_order_item", None),
#                     "project": getattr(production_plan_item, "project", None),
#                     "production_plan_item": getattr(production_plan_item, "name", None),
#                 })
            
#             if not work_order_data.get("wip_warehouse"):
#                 work_order_data["wip_warehouse"] = getattr(row, "wip_warehouse", None)
#             if not work_order_data.get("fg_warehouse"):
#                 work_order_data["fg_warehouse"] = getattr(row, "fg_warehouse", None)
                
#         except Exception as e:
#             frappe.log_error(
#                 f"Error in safe_prepare_data_for_sub_assembly_items: {str(e)}",
#                 "Safe Prepare Data Error"
#             )
#             work_order_data.update({
#                 "production_item": getattr(row, "production_item", None),
#                 "qty": flt(row.qty) - flt(row.ordered_qty),
#                 "description": getattr(row, "description", ""),
#                 "bom_no": getattr(row, "bom_no", None),
#                 "stock_uom": getattr(row, "stock_uom", None),
#                 "production_plan": self.name,
#                 "production_plan_sub_assembly_item": getattr(row, "name", None),
#             })

#     def _populate_subassembly_item_from_sales_order(self, row):
#         try:
#             production_plan_item = None
#             if hasattr(row, 'production_plan_item') and row.production_plan_item:
#                 try:
#                     if frappe.db.exists("Production Plan Item", row.production_plan_item):
#                         production_plan_item = frappe.get_doc("Production Plan Item", row.production_plan_item)
#                     else:
#                         frappe.log_error(
#                             f"Production Plan Item {row.production_plan_item} not found for subassembly item {getattr(row, 'name', 'Unknown')}. Clearing reference.",
#                             "Missing Production Plan Item"
#                         )
#                         row.production_plan_item = None
#                         if row.get("name"):
#                             frappe.db.set_value(row.doctype, row.name, "production_plan_item", None)
#                             frappe.db.commit()
#                 except frappe.DoesNotExistError:
#                     frappe.log_error(
#                         f"Production Plan Item {row.production_plan_item} does not exist. Clearing orphaned reference.",
#                         "Orphaned Production Plan Item Reference"
#                     )
#                     row.production_plan_item = None
#                     if row.get("name"):
#                         frappe.db.set_value(row.doctype, row.name, "production_plan_item", None)
#                         frappe.db.commit()
#                 except Exception as e:
#                     frappe.log_error(
#                         f"Error fetching Production Plan Item {row.production_plan_item}: {str(e)}",
#                         "Production Plan Item Fetch Error"
#                     )
#                     production_plan_item = None

#             if not production_plan_item and hasattr(row, 'production_item') and row.production_item:
#                 try:
#                     pp_items = frappe.get_all(
#                         "Production Plan Item",
#                         filters={"parent": self.name, "item_code": row.production_item},
#                         fields=["name", "sales_order", "sales_order_item"],
#                         limit=1
#                     )
#                     if pp_items:
#                         production_plan_item = frappe.get_doc("Production Plan Item", pp_items[0].name)
#                 except Exception as e:
#                     frappe.log_error(
#                         f"Error finding Production Plan Item by item_code {row.production_item}: {str(e)}",
#                         "Production Plan Item Lookup Error"
#                     )

#             if not production_plan_item:
#                 return

#             sales_order = getattr(production_plan_item, "sales_order", None)
#             sales_order_item = getattr(production_plan_item, "sales_order_item", None)
#             item_code = getattr(production_plan_item, "item_code", None)

#             if not sales_order:
#                 return

#             soi_filters = {"parent": sales_order}
#             if sales_order_item:
#                 soi_filters["name"] = sales_order_item
#             elif item_code:
#                 soi_filters["item_code"] = item_code

#             soi = frappe.get_all(
#                 "Sales Order Item",
#                 filters=soi_filters,
#                 fields=["name", "custom_batch_no", "bom_no", "idx", "branch"],
#                 order_by="idx asc",
#                 limit=1,
#             )

#             if not soi:
#                 return

#             soi = soi[0]

#             if hasattr(row, 'custom_batch_no'):
#                 row.custom_batch_no = soi.get("custom_batch_no") or None
#             if hasattr(row, 'branch'):
#                 row.branch = soi.get("branch") or None

#         except Exception as e:
#             frappe.log_error(f"Error populating subassembly item from sales order: {str(e)}", "Subassembly Item Population Error")

#     def get_so_items(self):
#         if not self.get("sales_orders") or not self.get_so_mr_list("sales_order", "sales_orders"):
#             frappe.throw(_("Please fill the Sales Orders table"), title=_("Sales Orders Required"))

#         so_list = self.get_so_mr_list("sales_order", "sales_orders")

#         bom = frappe.qb.DocType("BOM")
#         so_item = frappe.qb.DocType("Sales Order Item")
#         pp_item = frappe.qb.DocType("Production Plan Item")

#         items_subquery = frappe.qb.from_(bom).select(bom.name).where(bom.is_active == 1)
#         items_query = (
#             frappe.qb.from_(so_item)
#             .select(
#                 so_item.parent,
#                 so_item.item_code,
#                 so_item.warehouse,
#                 so_item.qty,
#                 so_item.work_order_qty,
#                 so_item.delivered_qty,
#                 so_item.conversion_factor,
#                 so_item.description,
#                 so_item.name,
#                 so_item.bom_no,
#                 so_item.custom_batch_no,
#                 so_item.branch,
#             )
#             .distinct()
#             .where(
#                 (so_item.parent.isin(so_list))
#                 & (so_item.docstatus == 1)
#             )
#         )

#         if self.item_code and frappe.db.exists("Item", self.item_code):
#             items_query = items_query.where(so_item.item_code == self.item_code)
#             items_subquery = items_subquery.where(
#                 self.get_bom_item_condition() or bom.item == so_item.item_code
#             )

#         items_query = items_query.where(ExistsCriterion(items_subquery))
#         items = items_query.run(as_dict=True)

#         items_with_remaining = []
#         for item in items:
#             original_pending_qty = flt(item.qty)
#             previous_planned_qty = frappe.db.sql("""
#                 SELECT SUM(ppi.planned_qty) as total_planned
#                 FROM `tabProduction Plan Item` ppi
#                 INNER JOIN `tabProduction Plan` pp ON ppi.parent = pp.name
#                 INNER JOIN `tabProduction Plan Sales Order` pps ON pp.name = pps.parent
#                 WHERE pps.sales_order = %s
#                 AND ppi.item_code = %s
#                 AND ppi.sales_order_item = %s
#                 AND pp.docstatus IN (0, 1)
#                 AND pp.name != %s
#             """, (item.parent, item.item_code, item.name, self.name or ""), as_dict=True)
            
#             total_planned = flt(previous_planned_qty[0].total_planned) if previous_planned_qty else 0
#             stock_pending_qty = original_pending_qty * flt(item.conversion_factor or 1)
#             remaining_qty = stock_pending_qty - total_planned
#             if remaining_qty < 0:
#                 remaining_qty = 0
            
#             item.pending_qty = remaining_qty
#             item.planned_qty = remaining_qty
            
#             try:
#                 selected_bom = None
#                 if item.get("parent") and item.get("item_code") and item.get("custom_batch_no"):
#                     bom_candidate = frappe.get_all(
#                         "BOM",
#                         filters={
#                             "item": item.get("item_code"),
#                             "sales_order": item.get("parent"),
#                             "custom_batch_no": item.get("custom_batch_no"),
#                         },
#                         or_filters=[{"is_active": 1}, {"is_default": 1}],
#                         fields=["name"],
#                         order_by="modified desc",
#                         limit=1,
#                     )
#                     if bom_candidate:
#                         selected_bom = bom_candidate[0]["name"]
#                 if selected_bom:
#                     item.bom_no = selected_bom
#             except Exception:
#                 pass
            
#             if remaining_qty > 0:
#                 items_with_remaining.append(item)
        
#         items = items_with_remaining

#         pi = frappe.qb.DocType("Packed Item")
#         packed_items_query = (
#             frappe.qb.from_(so_item)
#             .from_(pi)
#             .select(
#                 pi.parent,
#                 pi.item_code,
#                 pi.warehouse.as_("warehouse"),
#                 pi.qty,
#                 pi.parent_item,
#                 pi.description,
#                 so_item.name,
#                 so_item.branch,
#             )
#             .distinct()
#             .where(
#                 (so_item.parent == pi.parent)
#                 & (so_item.docstatus == 1)
#                 & (pi.parent_item == so_item.item_code)
#                 & (so_item.parent.isin(so_list))
#                 & (
#                     ExistsCriterion(
#                         frappe.qb.from_(bom)
#                         .select(bom.name)
#                         .where((bom.item == pi.item_code) & (bom.is_active == 1))
#                     )
#                 )
#             )
#         )

#         if self.item_code:
#             packed_items_query = packed_items_query.where(so_item.item_code == self.item_code)

#         packed_items = packed_items_query.run(as_dict=True)

#         packed_items_with_remaining = []
#         for item in packed_items:
#             original_pending_qty = flt(item.qty)
#             previous_planned_qty = frappe.db.sql("""
#                 SELECT SUM(ppi.planned_qty) as total_planned
#                 FROM `tabProduction Plan Item` ppi
#                 INNER JOIN `tabProduction Plan` pp ON ppi.parent = pp.name
#                 INNER JOIN `tabProduction Plan Sales Order` pps ON pp.name = pps.parent
#                 WHERE pps.sales_order = %s
#                 AND ppi.item_code = %s
#                 AND ppi.sales_order_item = %s
#                 AND pp.docstatus IN (0, 1)
#                 AND pp.name != %s
#             """, (item.parent, item.item_code, item.name, self.name or ""), as_dict=True)
            
#             total_planned = flt(previous_planned_qty[0].total_planned) if previous_planned_qty else 0
#             stock_pending_qty = original_pending_qty
#             remaining_qty = stock_pending_qty - total_planned
#             if remaining_qty < 0:
#                 remaining_qty = 0
            
#             item.pending_qty = remaining_qty
#             item.planned_qty = remaining_qty

#             try:
#                 selected_bom = None
#                 if item.get("parent") and item.get("item_code") and item.get("custom_batch_no"):
#                     bom_candidate = frappe.get_all(
#                         "BOM",
#                         filters={
#                             "item": item.get("item_code"),
#                             "sales_order": item.get("parent"),
#                             "custom_batch_no": item.get("custom_batch_no"),
#                         },
#                         or_filters=[{"is_active": 1}],
#                         fields=["name"],
#                         order_by="modified desc",
#                         limit=1,
#                     )
#                     if bom_candidate:
#                         selected_bom = bom_candidate[0]["name"]
#                 if selected_bom:
#                     item.bom_no = selected_bom
#             except Exception:
#                 pass

#             if remaining_qty > 0:
#                 packed_items_with_remaining.append(item)

#         self.add_items(items + packed_items_with_remaining)

#         try:
#             item_to_branch = {}
#             for it in (items + packed_items_with_remaining):
#                 soi = getattr(it, "name", None) or it.get("name") if isinstance(it, dict) else None
#                 br = getattr(it, "branch", None) or (it.get("branch") if isinstance(it, dict) else None)
#                 if soi and br:
#                     item_to_branch[soi] = br
#             for d in self.get("po_items", []):
#                 if not getattr(d, "branch", None) and getattr(d, "sales_order_item", None):
#                     br = item_to_branch.get(d.sales_order_item)
#                     if br:
#                         d.branch = br
#         except Exception:
#             pass

#         self.calculate_total_planned_qty()

#     @frappe.whitelist()
#     def get_items(self):
#         self.set("po_items", [])
#         if self.get_items_from == "Sales Order":
#             self.get_so_items()
#         elif self.get_items_from == "Material Request":
#             self.get_mr_items()

# def clean_orphaned_subassemblies(production_plan):
#     try:
#         if not hasattr(production_plan, 'sub_assembly_items') or not production_plan.sub_assembly_items:
#             return
            
#         valid_po_item_names = {getattr(po, 'name', None) for po in production_plan.po_items if getattr(po, 'name', None)}
        
#         for sub_item in production_plan.sub_assembly_items:
#             ppi_name = getattr(sub_item, "production_plan_item", None)
#             if ppi_name:
#                 if not frappe.db.exists("Production Plan Item", ppi_name) or ppi_name not in valid_po_item_names:
#                     frappe.log_error(
#                         f"Clearing invalid Production Plan Item reference in subassembly item: {ppi_name}",
#                         "Subassembly Reference Cleanup"
#                     )
#                     sub_item.production_plan_item = None
#                     if sub_item.get("name"):
#                         frappe.db.set_value(sub_item.doctype, sub_item.name, "production_plan_item", None)
#                         frappe.db.commit()
                        
#     except Exception as e:
#         frappe.log_error(f"Error cleaning orphaned subassemblies: {str(e)}", "Subassembly Cleanup Error")

# def safe_get_production_plan_item(production_plan_item_name, context=""):
#     try:
#         if not production_plan_item_name:
#             return None
            
#         if not frappe.db.exists("Production Plan Item", production_plan_item_name):
#             frappe.log_error(
#                 f"Production Plan Item {production_plan_item_name} not found in context: {context}",
#                 "Missing Production Plan Item"
#             )
#             return None
            
#         return frappe.get_doc("Production Plan Item", production_plan_item_name)
        
#     except frappe.DoesNotExistError:
#         frappe.log_error(
#             f"Production Plan Item {production_plan_item_name} does not exist in context: {context}",
#             "Production Plan Item Does Not Exist"
#         )
#         return None
#     except Exception as e:
#         frappe.log_error(
#             f"Error fetching Production Plan Item {production_plan_item_name} in context {context}: {str(e)}",
#             "Production Plan Item Fetch Error"
#         )
#         return None

# def cleanup_all_orphaned_references(production_plan):
#     try:
#         valid_ppi_names = set()
#         if hasattr(production_plan, 'po_items') and production_plan.po_items:
#             for po_item in production_plan.po_items:
#                 if getattr(po_item, 'name', None):
#                     valid_ppi_names.add(po_item.name)
        
#         if hasattr(production_plan, 'sub_assembly_items') and production_plan.sub_assembly_items:
#             for sub_item in production_plan.sub_assembly_items:
#                 ppi_name = getattr(sub_item, "production_plan_item", None)
#                 if ppi_name:
#                     if not frappe.db.exists("Production Plan Item", ppi_name) or ppi_name not in valid_ppi_names:
#                         frappe.log_error(
#                             f"Clearing invalid Production Plan Item reference in subassembly item: {ppi_name}",
#                             "Cleanup Mismatched Subassembly"
#                         )
#                         sub_item.production_plan_item = None
#                         if sub_item.get("name"):
#                             frappe.db.set_value(sub_item.doctype, sub_item.name, "production_plan_item", None)
#                             frappe.db.commit()
        
#         if hasattr(production_plan, 'mr_items') and production_plan.mr_items:
#             for mr_item in production_plan.mr_items:
#                 ppi_name = getattr(mr_item, "production_plan_item", None)
#                 if ppi_name and not frappe.db.exists("Production Plan Item", ppi_name):
#                     frappe.log_error(
#                         f"Clearing orphaned Production Plan Item reference in mr_items: {ppi_name}",
#                         "Cleanup Orphaned MR Item"
#                     )
#                     mr_item.production_plan_item = None
#                     if mr_item.get("name"):
#                         frappe.db.set_value(mr_item.doctype, mr_item.name, "production_plan_item", None)
#                         frappe.db.commit()
        
#         frappe.log_error("Completed comprehensive cleanup of orphaned references", "Production Plan Cleanup")
        
#     except Exception as e:
#         frappe.log_error(f"Error in comprehensive cleanup: {str(e)}", "Production Plan Cleanup Error")

from erpnext.manufacturing.doctype.production_plan.production_plan import ProductionPlan as _ProductionPlan
import frappe
from frappe import _
from frappe.utils import flt

class ProductionPlan(_ProductionPlan):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Run cleanup only for saved documents with po_items
        if self.name and self.docstatus < 2 and hasattr(self, 'po_items') and self.po_items:
            try:
                cleanup_all_orphaned_references(self)
            except Exception as e:
                frappe.log_error(f"Cleanup error in __init__: {str(e)}", "Production Plan Init Cleanup")

    def validate(self):
        """Override validate to ensure no invalid production_plan_item references"""
        super().validate()
        if hasattr(self, 'sub_assembly_items') and self.sub_assembly_items:
            try:
                invalid_references = []
                valid_ppi_names = {po_item.name for po_item in self.po_items if getattr(po_item, "name", None)}
                for sub_item in self.sub_assembly_items:
                    ppi_name = getattr(sub_item, "production_plan_item", None)
                    if ppi_name and (not frappe.db.exists("Production Plan Item", ppi_name) or ppi_name not in valid_ppi_names):
                        invalid_references.append(ppi_name)
                if invalid_references:
                    frappe.throw(
                        _("Invalid Production Plan Item references found in sub_assembly_items: {0}").format(", ".join(invalid_references)),
                        title=_("Invalid References")
                    )
                cleanup_all_orphaned_references(self)
            except Exception as e:
                frappe.log_error(f"Validation error in Production Plan: {str(e)}", "Production Plan Validation")
                frappe.throw(_("Error validating Production Plan due to invalid references: {0}").format(str(e)))

    @frappe.whitelist()
    def make_work_order(self):
        from erpnext.manufacturing.doctype.work_order.work_order import get_default_warehouse
        doc = frappe.get_all("Work Order", filters={"production_plan": self.name}, fields=["name"])
        if doc:
            frappe.throw("Work Order already exists")
        wo_list, po_list = [], []
        subcontracted_po = {}
        default_warehouses = get_default_warehouse()

        # Run cleanup before creating work orders
        if hasattr(self, 'po_items') and self.po_items:
            try:
                cleanup_all_orphaned_references(self)
            except Exception as e:
                frappe.log_error(f"Cleanup error in make_work_order: {str(e)}", "Work Order Cleanup")

        self.make_work_order_for_finished_goods(wo_list, default_warehouses)
        self.make_work_order_for_subassembly_items(wo_list, subcontracted_po, default_warehouses)
        self.make_subcontracted_purchase_order(subcontracted_po, po_list)
        self.show_list_created_message("Work Order", wo_list)
        self.show_list_created_message("Purchase Order", po_list)

        if not wo_list:
            frappe.msgprint(_("No Work Orders were created"))

    @frappe.whitelist()
    def get_sub_assembly_items(self, manufacturing_type=None):
        """Override to ensure sub_assembly_items inherit custom fields from po_items"""
        super().get_sub_assembly_items(manufacturing_type)
        self._populate_subassembly_items_from_po_items()
        if self.name and self.docstatus < 2 and hasattr(self, 'po_items') and self.po_items:
            try:
                cleanup_all_orphaned_references(self)
            except Exception as e:
                frappe.log_error(f"Cleanup error in get_sub_assembly_items: {str(e)}", "Subassembly Cleanup")

    @frappe.whitelist()
    def get_items(self):
        """Populate branch on po_items immediately after fetching items so it shows in grid"""
        super().get_items()
        try:
            if not getattr(self, "po_items", None):
                return
            soi_names = [d.sales_order_item for d in self.po_items if getattr(d, "sales_order_item", None)]
            if not soi_names:
                return
            soi_rows = frappe.get_all(
                "Sales Order Item",
                filters={"name": ("in", soi_names)},
                fields=["name", "branch"],
            )
            soi_branch_map = {row["name"]: row.get("branch") for row in soi_rows}
            for d in self.po_items:
                if hasattr(d, "branch") and getattr(d, "sales_order_item", None):
                    if not getattr(d, "branch", None):
                        d.branch = soi_branch_map.get(d.sales_order_item)
        except Exception as e:
            frappe.log_error(f"Error populating branch on po_items: {str(e)}", "Production Plan Branch Populate Error")

    def _populate_subassembly_items_from_po_items(self):
        """Populate subassembly items with custom fields from their parent po_items"""
        try:
            po_item_by_item_code = {po_item.item_code: po_item for po_item in self.po_items if getattr(po_item, "item_code", None)}
            po_item_by_rowname = {po_item.name: po_item for po_item in self.po_items if getattr(po_item, "name", None)}

            for sub_item in self.sub_assembly_items:
                parent_po_item = None
                ppi_name = getattr(sub_item, "production_plan_item", None)
                sub_item_name = getattr(sub_item, "name", "Unknown")

                # Log the reference being checked
                frappe.log_error(
                    f"Checking sub_assembly_item {sub_item_name} with production_plan_item: {ppi_name}",
                    "Subassembly Reference Check"
                )

                if ppi_name and ppi_name in po_item_by_rowname:
                    parent_po_item = po_item_by_rowname.get(ppi_name)
                if not parent_po_item:
                    parent_code = getattr(sub_item, "parent_item_code", None) or getattr(sub_item, "production_item", None)
                    if parent_code:
                        parent_po_item = po_item_by_item_code.get(parent_code)
                
                if parent_po_item:
                    parent_batch = (
                        getattr(parent_po_item, "custom_batch_no", None)
                        or getattr(parent_po_item, "custom_batch_ref", None)
                        or getattr(parent_po_item, "batch_no", None)
                    )
                    if parent_batch:
                        for field in ["custom_batch_no", "custom_bath_no", "custom_batch_ref", "batch_no"]:
                            if hasattr(sub_item, field):
                                setattr(sub_item, field, parent_batch)
                        if hasattr(sub_item, "type_of_manufacturing"):
                            sub_item.type_of_manufacturing = "In House"
                    if hasattr(parent_po_item, "branch") and getattr(parent_po_item, "branch", None):
                        sub_item.branch = parent_po_item.branch
                        if hasattr(sub_item, "branch"):
                            sub_item.branch = parent_po_item.branch
                    for field in ["sales_order", "sales_order_item"]:
                        if hasattr(parent_po_item, field) and getattr(parent_po_item, field, None):
                            setattr(sub_item, field, getattr(parent_po_item, field))
                else:
                    frappe.log_error(
                        f"No parent po_item found for sub_assembly_item {sub_item_name} with production_plan_item: {ppi_name}",
                        "Subassembly Parent Not Found"
                    )
        except Exception as e:
            frappe.log_error(f"Error populating subassembly items from po_items: {str(e)}", "Subassembly Item Population Error")

    def make_work_order_for_subassembly_items(self, wo_list, subcontracted_po, default_warehouses):
        """Override to ensure sub_assembly_items get correct values from Sales Order Items"""
        for row in self.sub_assembly_items:
            sub_item_name = getattr(row, "name", "Unknown")
            self._populate_subassembly_item_from_sales_order(row)
            
            if row.type_of_manufacturing == "Subcontract":
                subcontracted_po.setdefault(row.supplier, []).append(row)
                continue

            if row.type_of_manufacturing == "Material Request":
                continue

            work_order_data = {
                "wip_warehouse": default_warehouses.get("wip_warehouse"),
                "fg_warehouse": default_warehouses.get("fg_warehouse"),
                "company": self.get("company"),
            }

            if flt(row.qty) <= flt(row.ordered_qty):
                continue

            # Populate work_order_data with custom fields from sub_assembly_item
            row_batch = (
                getattr(row, "custom_batch_no", None) or
                getattr(row, "custom_batch_ref", None) or
                getattr(row, "batch_no", None)
            )
            if row_batch:
                work_order_data["custom_batch_no"] = row_batch
            if hasattr(row, "branch") and row.branch:
                work_order_data["branch"] = row.branch
            if hasattr(row, "sales_order") and row.sales_order:
                work_order_data["sales_order"] = row.sales_order
            if hasattr(row, "sales_order_item") and row.sales_order_item:
                work_order_data["sales_order_item"] = row.sales_order_item

            # Fallback to parent po_item if any fields are missing
            if (
                not all(work_order_data.get(field) for field in ["custom_batch_no", "branch"])
                and hasattr(self, "po_items") and self.po_items
            ):
                po_item_by_rowname = {getattr(d, "name", None): d for d in self.po_items if getattr(d, "name", None)}
                po_item_by_item_code = {getattr(d, "item_code", None): d for d in self.po_items if getattr(d, "item_code", None)}
                parent_po_item = None
                ppi_name = getattr(row, "production_plan_item", None)
                if ppi_name and ppi_name in po_item_by_rowname:
                    parent_po_item = po_item_by_rowname.get(ppi_name)
                if not parent_po_item:
                    parent_code = getattr(row, "parent_item_code", None) or getattr(row, "production_item", None)
                    if parent_code:
                        parent_po_item = po_item_by_item_code.get(parent_code)
                
                if parent_po_item:
                    if not work_order_data.get("custom_batch_no"):
                        parent_batch = (
                            getattr(parent_po_item, "custom_batch_no", None)
                            or getattr(parent_po_item, "custom_batch_ref", None)
                            or getattr(parent_po_item, "batch_no", None)
                        )
                        if parent_batch:
                            work_order_data["custom_batch_no"] = parent_batch
                    for field in ["branch", "sales_order", "sales_order_item"]:
                        if not work_order_data.get(field) and hasattr(parent_po_item, field) and getattr(parent_po_item, field, None):
                            work_order_data[field] = getattr(parent_po_item, field)
                else:
                    frappe.log_error(
                        f"No parent po_item found for sub_assembly_item {sub_item_name} with production_plan_item: {ppi_name}, "
                        f"production_item: {getattr(row, 'production_item', None)}, parent_item_code: {getattr(row, 'parent_item_code', None)}",
                        "Work Order Parent Not Found"
                    )

            # Log if critical fields are still missing
            if not work_order_data.get("custom_batch_no") or not work_order_data.get("branch"):
                frappe.log_error(
                    f"Missing fields in work_order_data for sub_assembly_item {sub_item_name}: "
                    f"custom_batch_no={work_order_data.get('custom_batch_no')}, branch={work_order_data.get('branch')}",
                    "Work Order Data Missing Fields"
                )

            # Clear invalid production_plan_item reference
            try:
                if getattr(row, "production_plan_item", None):
                    if not frappe.db.exists("Production Plan Item", row.production_plan_item):
                        frappe.log_error(
                            f"Orphaned Production Plan Item reference found in sub_assembly_item {sub_item_name}: {row.production_plan_item}. Clearing reference.",
                            "Orphaned Production Plan Item Reference"
                        )
                        row.production_plan_item = None
                        if row.get("name"):
                            frappe.db.set_value(row.doctype, row.name, "production_plan_item", None)
                            frappe.db.commit()
            except Exception as e:
                frappe.log_error(f"Error checking Production Plan Item existence for {sub_item_name}: {str(e)}", "Production Plan Item Check Error")
                row.production_plan_item = None

            self.safe_prepare_data_for_sub_assembly_items(row, work_order_data)

            if work_order_data.get("qty") <= 0:
                continue

            work_order = self.create_work_order(work_order_data)
            if work_order:
                # Ensure custom fields are actually set on the created Work Order
                try:
                    wo_doc = frappe.get_doc("Work Order", work_order)
                    updates = {}
                    # Branch
                    if work_order_data.get("branch") and hasattr(wo_doc, "branch") and not getattr(wo_doc, "branch", None):
                        updates["branch"] = work_order_data.get("branch")
                    # Batch: prefer custom_batch_no; fallback to batch_no field if present
                    custom_batch = work_order_data.get("custom_batch_no")
                    if custom_batch:
                        if hasattr(wo_doc, "custom_batch_no") and not getattr(wo_doc, "custom_batch_no", None):
                            updates["custom_batch_no"] = custom_batch
                        elif hasattr(wo_doc, "batch_no") and not getattr(wo_doc, "batch_no", None):
                            updates["batch_no"] = custom_batch
                    if updates:
                        wo_doc.db_set(updates, update_modified=False)

                    # Also backfill required_items child rows, if custom fields exist
                    try:
                        branch_value = work_order_data.get("branch")
                        for req in getattr(wo_doc, "required_items", []) or []:
                            child_updates = {}
                            if branch_value and hasattr(req, "branch") and not getattr(req, "branch", None):
                                child_updates["branch"] = branch_value
                            if custom_batch:
                                if hasattr(req, "custom_batch_no") and not getattr(req, "custom_batch_no", None):
                                    child_updates["custom_batch_no"] = custom_batch
                                elif hasattr(req, "batch_no") and not getattr(req, "batch_no", None):
                                    child_updates["batch_no"] = custom_batch
                            if child_updates:
                                req.db_set(child_updates, update_modified=False)
                    except Exception as ce:
                        frappe.log_error(
                            f"Unable to backfill required_items for Work Order {work_order}: {str(ce)}",
                            "Work Order Required Items Backfill Error"
                        )
                except Exception as e:
                    frappe.log_error(f"Unable to backfill branch/batch on Work Order {work_order}: {str(e)}", "Work Order Backfill Error")
                wo_list.append(work_order)

    def safe_prepare_data_for_sub_assembly_items(self, row, work_order_data):
        try:
            sub_item_name = getattr(row, "name", "Unknown")
            production_plan_item = None
            if getattr(row, "production_plan_item", None):
                production_plan_item = safe_get_production_plan_item(row.production_plan_item, context=f"safe_prepare_data_for_sub_assembly_items ({sub_item_name})")
                if not production_plan_item:
                    row.production_plan_item = None
                    if row.get("name"):
                        frappe.db.set_value(row.doctype, row.name, "production_plan_item", None)
                        frappe.db.commit()
            
            if not production_plan_item and hasattr(row, 'production_item'):
                for po_item in self.po_items:
                    if getattr(po_item, 'item_code') == getattr(row, 'production_item'):
                        production_plan_item = po_item
                        break
            
            work_order_data.update({
                "production_item": getattr(row, "production_item", None),
                "qty": flt(row.qty) - flt(row.ordered_qty),
                "description": getattr(row, "description", ""),
                "bom_no": getattr(row, "bom_no", None),
                "stock_uom": getattr(row, "stock_uom", None),
                "production_plan": self.name,
                "production_plan_sub_assembly_item": getattr(row, "name", None),
            })
            
            if production_plan_item:
                work_order_data.update({
                    "sales_order": getattr(production_plan_item, "sales_order", None),
                    "sales_order_item": getattr(production_plan_item, "sales_order_item", None),
                    "project": getattr(production_plan_item, "project", None),
                    "production_plan_item": getattr(production_plan_item, "name", None),
                })
            
            if not work_order_data.get("wip_warehouse"):
                work_order_data["wip_warehouse"] = getattr(row, "wip_warehouse", None)
            if not work_order_data.get("fg_warehouse"):
                work_order_data["fg_warehouse"] = getattr(row, "fg_warehouse", None)
                
        except Exception as e:
            frappe.log_error(f"Error in safe_prepare_data_for_sub_assembly_items for {sub_item_name}: {str(e)}", "Safe Prepare Data Error")
            work_order_data.update({
                "production_item": getattr(row, "production_item", None),
                "qty": flt(row.qty) - flt(row.ordered_qty),
                "description": getattr(row, "description", ""),
                "bom_no": getattr(row, "bom_no", None),
                "stock_uom": getattr(row, "stock_uom", None),
                "production_plan": self.name,
                "production_plan_sub_assembly_item": getattr(row, "name", None),
            })

    def _populate_subassembly_item_from_sales_order(self, row):
        try:
            sub_item_name = getattr(row, "name", "Unknown")
            production_plan_item = None
            ppi_name = getattr(row, "production_plan_item", None)
            if ppi_name:
                production_plan_item = safe_get_production_plan_item(ppi_name, context=f"populate_subassembly_item_from_sales_order ({sub_item_name})")
                if not production_plan_item:
                    frappe.log_error(
                        f"Production Plan Item {ppi_name} not found for sub_assembly_item {sub_item_name}. Clearing reference.",
                        "Missing Production Plan Item"
                    )
                    row.production_plan_item = None
                    if row.get("name"):
                        frappe.db.set_value(row.doctype, row.name, "production_plan_item", None)
                        frappe.db.commit()

            if not production_plan_item and hasattr(row, 'production_item') and row.production_item:
                pp_items = frappe.get_all(
                    "Production Plan Item",
                    filters={"parent": self.name, "item_code": row.production_item},
                    fields=["name", "sales_order", "sales_order_item"],
                    limit=1
                )
                if pp_items:
                    production_plan_item = frappe.get_doc("Production Plan Item", pp_items[0].name)

            if not production_plan_item:
                frappe.log_error(
                    f"No Production Plan Item found for sub_assembly_item {sub_item_name} with production_item: {getattr(row, 'production_item', None)}",
                    "Production Plan Item Not Found"
                )
                return

            sales_order = getattr(production_plan_item, "sales_order", None)
            sales_order_item = getattr(production_plan_item, "sales_order_item", None)
            item_code = getattr(production_plan_item, "item_code", None)

            if not sales_order:
                return

            soi_filters = {"parent": sales_order}
            if sales_order_item:
                soi_filters["name"] = sales_order_item
            elif item_code:
                soi_filters["item_code"] = item_code

            soi = frappe.get_all(
                "Sales Order Item",
                filters=soi_filters,
                fields=["name", "custom_batch_no", "bom_no", "idx", "branch"],
                order_by="idx asc",
                limit=1,
            )

            if not soi:
                return

            soi = soi[0]

            if hasattr(row, 'custom_batch_no'):
                row.custom_batch_no = soi.get("custom_batch_no") or None
            if hasattr(row, 'branch'):
                row.branch = soi.get("branch") or None

        except Exception as e:
            frappe.log_error(f"Error populating subassembly item {sub_item_name} from sales order: {str(e)}", "Subassembly Item Population Error")

def safe_get_production_plan_item(production_plan_item_name, context=""):
    try:
        if not production_plan_item_name:
            return None
        if not frappe.db.exists("Production Plan Item", production_plan_item_name):
            frappe.log_error(
                f"Production Plan Item {production_plan_item_name} not found in context: {context}",
                "Missing Production Plan Item"
            )
            return None
        return frappe.get_doc("Production Plan Item", production_plan_item_name)
    except frappe.DoesNotExistError:
        frappe.log_error(
            f"Production Plan Item {production_plan_item_name} does not exist in context: {context}",
            "Production Plan Item Does Not Exist"
        )
        return None
    except Exception as e:
        frappe.log_error(
            f"Error fetching Production Plan Item {production_plan_item_name} in context {context}: {str(e)}",
            "Production Plan Item Fetch Error"
        )
        return None

def cleanup_all_orphaned_references(production_plan):
    try:
        valid_ppi_names = {getattr(po, 'name', None) for po in production_plan.po_items if getattr(po, 'name', None)}
        
        if hasattr(production_plan, 'sub_assembly_items') and production_plan.sub_assembly_items:
            for sub_item in production_plan.sub_assembly_items:
                sub_item_name = getattr(sub_item, "name", "Unknown")
                ppi_name = getattr(sub_item, "production_plan_item", None)
                if ppi_name and (not frappe.db.exists("Production Plan Item", ppi_name) or ppi_name not in valid_ppi_names):
                    frappe.log_error(
                        f"Clearing invalid Production Plan Item reference {ppi_name} in sub_assembly_item {sub_item_name}",
                        "Cleanup Mismatched Subassembly"
                    )
                    sub_item.production_plan_item = None
                    if sub_item.get("name"):
                        frappe.db.set_value(sub_item.doctype, sub_item.name, "production_plan_item", None)
                        frappe.db.commit()
        
        if hasattr(production_plan, 'mr_items') and production_plan.mr_items:
            for mr_item in production_plan.mr_items:
                mr_item_name = getattr(mr_item, "name", "Unknown")
                ppi_name = getattr(mr_item, "production_plan_item", None)
                if ppi_name and not frappe.db.exists("Production Plan Item", ppi_name):
                    frappe.log_error(
                        f"Clearing orphaned Production Plan Item reference {ppi_name} in mr_item {mr_item_name}",
                        "Cleanup Orphaned MR Item"
                    )
                    mr_item.production_plan_item = None
                    if mr_item.get("name"):
                        frappe.db.set_value(mr_item.doctype, mr_item.name, "production_plan_item", None)
                        frappe.db.commit()
        
        frappe.log_error("Completed comprehensive cleanup of orphaned references", "Production Plan Cleanup")
        
    except Exception as e:
        frappe.log_error(f"Error in comprehensive cleanup: {str(e)}", "Production Plan Cleanup Error")