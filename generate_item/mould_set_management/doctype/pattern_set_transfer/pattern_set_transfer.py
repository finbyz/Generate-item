# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_link_to_form
from generate_item.mould_set_management.pattern_set_utils import (
	get_pattern_set_slots_and_serials,
	recalculate_pattern_set,
)


class PatternSetTransfer(Document):
	def validate(self):
		self.validate_pattern_set()
		self.set_transfer_type_and_suppliers()
		self.validate_target_warehouse()
		self.validate_items()
		self.check_concurrent_drafts()

	def set_transfer_type_and_suppliers(self):
		if self.source_warehouse:
			self.source_supplier = frappe.db.get_value("Warehouse", self.source_warehouse, "custom_supplier") or ""
		else:
			self.source_supplier = ""

		if self.target_warehouse:
			self.target_supplier = frappe.db.get_value("Warehouse", self.target_warehouse, "custom_supplier") or ""
		else:
			self.target_supplier = ""

		if self.source_warehouse and self.target_warehouse:
			is_src_supplier = bool(self.source_supplier)
			is_tgt_supplier = bool(self.target_supplier)

			if not is_src_supplier and is_tgt_supplier:
				self.transfer_type = "Company to Supplier"
			elif is_src_supplier and is_tgt_supplier:
				self.transfer_type = "Supplier to Supplier"
			elif is_src_supplier and not is_tgt_supplier:
				self.transfer_type = "Supplier to Company"
			else:
				self.transfer_type = "Company to Company"

	def validate_pattern_set(self):
		if not self.pattern_set:
			frappe.throw(_("Pattern Set is required."))

		ps = frappe.db.get_value(
			"Pattern Set",
			self.pattern_set,
			["docstatus", "disabled", "disable", "current_warehouse"],
			as_dict=True,
		)
		if not ps:
			frappe.throw(_("Pattern Set {0} does not exist.").format(self.pattern_set))

		if ps.docstatus != 1:
			frappe.throw(_("Pattern Set {0} must be submitted.").format(self.pattern_set))

		if ps.disabled or ps.disable:
			frappe.throw(_("Pattern Set {0} is disabled and cannot be transferred.").format(self.pattern_set))

		info = get_pattern_set_slots_and_serials(self.pattern_set)
		if not info["attached_serials"]:
			frappe.throw(_("Pattern Set {0} has no attached serial numbers to transfer.").format(self.pattern_set))

		if not info["current_warehouse"]:
			frappe.throw(_("Pattern Set {0} does not have a current warehouse.").format(self.pattern_set))

		# v2.0 Section 7.2 & 7.3: If set moved since transfer draft was created, block
		if not self.is_new() and self.source_warehouse:
			if info["current_warehouse"] != self.source_warehouse:
				frappe.throw(
					_("Pattern Set {0} has moved from {1} to {2} since this transfer was created. Please reload or recreate the transfer.").format(
						frappe.bold(self.pattern_set), frappe.bold(self.source_warehouse), frappe.bold(info["current_warehouse"])
					)
				)

		self.source_warehouse = info["current_warehouse"]
		self.set_status = info["status"]
		self.completeness_status = info["completeness_status"]
		self.engineering_status = info["engineering_status"]
		self.source_supplier = info["current_supplier"]

		# v2.0 Section 5: Transfer Eligibility
		if info["completeness_status"] != "Complete":
			frappe.throw(
				_("Pattern Set {0} is Incomplete and cannot be transferred. All required components must be attached before transfer.").format(
					frappe.bold(self.pattern_set)
				)
			)

		if info["engineering_status"] not in ("Current", "Approved As-Is"):
			frappe.throw(
				_("Pattern Set {0} has Engineering Status '{1}' and cannot be transferred. Component drawing or purchase specification revisions must be reviewed and approved first.").format(
					frappe.bold(self.pattern_set), frappe.bold(info["engineering_status"])
				)
			)

		open_changes = frappe.db.sql("""
			SELECT psec.name
			FROM `tabPattern Set Engineering Change Item` pseci
			JOIN `tabPattern Set Engineering Change` psec ON psec.name = pseci.parent
			WHERE pseci.pattern_set = %s AND psec.docstatus = 0
		""", (self.pattern_set,))
		if open_changes:
			frappe.throw(
				_("Pattern Set {0} has an open Engineering Change ({1}) and cannot be transferred until disposition is approved.").format(
					frappe.bold(self.pattern_set), frappe.bold(open_changes[0][0])
				)
			)

		if not self.items:
			self.load_components_from_pattern_set()

	def load_components_from_pattern_set(self):
		comp_rows = frappe.get_all(
			"Pattern Set Component",
			filters={
				"parent": self.pattern_set,
				"serial_no": ["is", "set"],
			},
			fields=["serial_no", "item_code", "item_name", "is_optional", "warehouse", "remarks"],
			order_by="idx asc",
		)
		for r in comp_rows:
			if not r.serial_no:
				continue
			self.append("items", {
				"include": 1,
				"serial_no": r.serial_no,
				"item_code": r.item_code,
				"item_name": r.item_name or frappe.db.get_value("Item", r.item_code, "item_name"),
				"is_optional": 1 if r.is_optional else 0,
				"warehouse": r.warehouse or self.source_warehouse,
				"remarks": r.remarks or "",
			})


	def validate_target_warehouse(self):
		if not self.target_warehouse:
			frappe.throw(_("Target Warehouse is required."))

		if self.target_warehouse == self.source_warehouse:
			frappe.throw(_("Target Warehouse cannot be the same as Source Warehouse ({0}).").format(self.source_warehouse))

		tgt_wh = frappe.db.get_value("Warehouse", self.target_warehouse, ["is_group", "disabled", "company"], as_dict=True)
		if not tgt_wh:
			frappe.throw(_("Target Warehouse {0} does not exist.").format(self.target_warehouse))

		if tgt_wh.is_group:
			frappe.throw(_("Target Warehouse {0} cannot be a group warehouse.").format(self.target_warehouse))

		if tgt_wh.disabled:
			frappe.throw(_("Target Warehouse {0} is disabled.").format(self.target_warehouse))

		if self.company and tgt_wh.company and tgt_wh.company != self.company:
			frappe.throw(
				_("Target Warehouse {0} belongs to company {1}, but transfer company is {2}.").format(
					self.target_warehouse, tgt_wh.company, self.company
				)
			)

	def validate_items(self):
		if not self.items:
			frappe.throw(_("No components found in transfer table. Please select Pattern Set again."))

		moving_count = 0
		left_behind_count = 0

		for idx, row in enumerate(self.items, start=1):
			if not row.serial_no:
				frappe.throw(_("Row #{0}: Serial No is required.").format(idx))

			# v2.0 Section 7.2: Required components must have Include ticked (Acceptance Test 17)
			if not row.is_optional and not row.include:
				frappe.throw(
					_("Row #{0}: Serial No {1} is a required component and cannot be unticked.").format(
						idx, frappe.bold(row.serial_no)
					)
				)

			# Verify serial status and location
			sn_data = frappe.db.get_value(
				"Serial No",
				row.serial_no,
				["custom_pattern_set", "warehouse", "status"],
				as_dict=True,
			)
			if not sn_data:
				frappe.throw(_("Row #{0}: Serial No {1} does not exist.").format(idx, row.serial_no))

			if sn_data.custom_pattern_set != self.pattern_set:
				frappe.throw(
					_("Serial No {0} is no longer attached to Pattern Set {1}. Please reload components.").format(
						frappe.bold(row.serial_no), frappe.bold(self.pattern_set)
					)
				)

			if sn_data.status != "Active":
				frappe.throw(
					_("Serial No {0} is not Active (current status: {1}).").format(
						frappe.bold(row.serial_no), frappe.bold(sn_data.status)
					)
				)

			if sn_data.warehouse != self.source_warehouse:
				frappe.throw(
					_("Serial No {0} is in warehouse {1}, not source warehouse {2}. Please reload components.").format(
						frappe.bold(row.serial_no), frappe.bold(sn_data.warehouse), frappe.bold(self.source_warehouse)
					)
				)

			if row.include:
				moving_count += 1
			else:
				left_behind_count += 1

		if moving_count == 0:
			frappe.throw(_("At least one component must be included in the transfer."))

		self.total_moving = moving_count
		self.total_left_behind = left_behind_count

	def check_concurrent_drafts(self):
		if not self.is_new():
			drafts = frappe.get_all(
				"Pattern Set Transfer",
				filters={"pattern_set": self.pattern_set, "docstatus": 0, "name": ["!=", self.name]},
				pluck="name",
			)
		else:
			drafts = frappe.get_all(
				"Pattern Set Transfer",
				filters={"pattern_set": self.pattern_set, "docstatus": 0},
				pluck="name",
			)

		if drafts:
			frappe.msgprint(
				_("Notice: Another draft transfer ({0}) exists for Pattern Set {1}.").format(
					", ".join(drafts), frappe.bold(self.pattern_set)
				),
				indicator="orange",
				alert=True,
			)

	def on_submit(self):
		self._process_submit()

	def _process_submit(self):
		# Re-validate with DB locks on serial numbers (v2.0 Section 7.3 step 1)
		all_serials = [row.serial_no for row in self.items]
		if all_serials:
			frappe.db.sql(
				"SELECT name FROM `tabSerial No` WHERE name IN %s FOR UPDATE",
				(tuple(all_serials),),
			)

		self.validate()

		cc_doc = None
		stock_entry = None
		try:
			# Step 2: Handle left-behind optional components
			left_behind_rows = [row for row in self.items if not row.include]
			if left_behind_rows:
				cc_doc = frappe.new_doc("Pattern Set Component Change")
				cc_doc.posting_date = self.posting_date
				cc_doc.pattern_set = self.pattern_set
				cc_doc.reason = f"Left behind during set transfer {self.name}"
				cc_doc.auto_created_from = self.name
				for r in left_behind_rows:
					cc_doc.append("items", {
						"action": "Detach",
						"serial_no": r.serial_no,
						"item_code": r.item_code,
						"warehouse": r.warehouse,
						"remarks": f"Left behind on transfer {self.name}",
					})
				cc_doc.flags.ignore_permissions = True
				cc_doc.insert(ignore_permissions=True)
				cc_doc.submit()
				self.db_set("component_change", cc_doc.name)

			# Step 3: Create and submit Stock Entry of type Material Transfer
			moving_rows = [row for row in self.items if row.include]
			stock_entry = frappe.new_doc("Stock Entry")
			stock_entry.purpose = "Material Transfer"
			stock_entry.stock_entry_type = "Material Transfer"
			stock_entry.company = self.company
			stock_entry.posting_date = self.posting_date
			stock_entry.from_warehouse = self.source_warehouse
			stock_entry.to_warehouse = self.target_warehouse
			stock_entry.custom_pattern_set = self.pattern_set
			stock_entry.custom_pattern_set_transfer = self.name

			# Set branch if present on Stock Entry
			branch = (
				frappe.db.get_value("Warehouse", self.source_warehouse, "branch")
				or frappe.db.get_value("Warehouse", self.target_warehouse, "branch")
				or frappe.get_all("Branch", limit=1, pluck="name")[0]
			)
			if frappe.db.has_column("Stock Entry", "branch"):
				stock_entry.branch = branch

			stock_entry.remarks = (
				f"Material Transfer for Pattern Set {self.pattern_set} via Pattern Set Transfer {self.name}. Purpose: {self.purpose}"
			)

			for r in moving_rows:
				stock_uom = frappe.db.get_value("Item", r.item_code, "stock_uom") or "Nos"
				has_batch = frappe.db.get_value("Item", r.item_code, "has_batch_no")
				row_dict = {
					"item_code": r.item_code,
					"qty": 1.0,
					"uom": stock_uom,
					"stock_uom": stock_uom,
					"conversion_factor": 1.0,
					"s_warehouse": self.source_warehouse,
					"t_warehouse": self.target_warehouse,
					"serial_no": r.serial_no,
					"use_serial_batch_fields": 1,
					"allow_zero_valuation_rate": 1,
				}
				if has_batch:
					sn_batch = frappe.db.get_value("Serial No", r.serial_no, "batch_no")
					if sn_batch and frappe.db.get_value("Batch", sn_batch, "item") == r.item_code:
						row_dict["batch_no"] = sn_batch
				stock_entry.append("items", row_dict)

			stock_entry.set_stock_entry_type()
			stock_entry.flags.ignore_permissions = True
			stock_entry.insert(ignore_permissions=True)
			stock_entry.submit()
			self.db_set("stock_entry", stock_entry.name)

			# Step 4: Refresh warehouse on set's component rows for moving serials
			for r in moving_rows:
				frappe.db.sql(
					"""
					UPDATE `tabPattern Set Component`
					SET warehouse = %s
					WHERE parent = %s AND serial_no = %s
					""",
					(self.target_warehouse, self.pattern_set, r.serial_no),
				)

			# Step 5: Refresh set location, supplier, status
			recalculate_pattern_set(self.pattern_set)

		except Exception as e:
			frappe.db.rollback()
			# If an auto Component Change was created before Stock Entry failed, cancel it cleanly
			if cc_doc and frappe.db.exists("Pattern Set Component Change", cc_doc.name):
				try:
					cc = frappe.get_doc("Pattern Set Component Change", cc_doc.name)
					if cc.docstatus == 1:
						cc.flags.ignore_permissions = True
						cc.cancel()
					recalculate_pattern_set(self.pattern_set)
					frappe.db.commit()
				except Exception:
					pass
			raise e

		frappe.msgprint(
			_("Pattern Set Transfer completed: Stock Entry {0} submitted.").format(
				get_link_to_form("Stock Entry", stock_entry.name)
			),
			alert=True,
		)

	def on_cancel(self):
		# Step 1: Check this is the latest transfer for the Pattern Set (Section 7.4)
		newer_transfers = frappe.get_all(
			"Pattern Set Transfer",
			filters={
				"pattern_set": self.pattern_set,
				"docstatus": 1,
				"creation": [">", self.creation],
			},
			pluck="name",
		)
		if newer_transfers:
			frappe.throw(
				_("Cannot cancel {0}: A newer transfer ({1}) exists for Pattern Set {2}. Cancel newer transfers first.").format(
					self.name, ", ".join(newer_transfers), frappe.bold(self.pattern_set)
				)
			)

		# Step 2: Cancel linked Stock Entry
		if self.stock_entry and frappe.db.exists("Stock Entry", self.stock_entry):
			se = frappe.get_doc("Stock Entry", self.stock_entry)
			if se.docstatus == 1:
				se.flags.ignore_permissions = True
				se.flags.allow_pattern_set_transfer_cancel = True
				se.cancel()

		# Step 3: Update warehouse on set's component rows back to source_warehouse for moving serials
		moving_serials = [r.serial_no for r in self.items if r.include]
		for sn in moving_serials:
			frappe.db.sql(
				"""
				UPDATE `tabPattern Set Component`
				SET warehouse = %s
				WHERE parent = %s AND serial_no = %s
				""",
				(self.source_warehouse, self.pattern_set, sn),
			)

		# Step 4: Cancel linked auto-created Component Change if any
		if self.component_change and frappe.db.exists("Pattern Set Component Change", self.component_change):
			cc = frappe.get_doc("Pattern Set Component Change", self.component_change)
			if cc.docstatus == 1:
				# Verify left-behind serials are still free and in source warehouse
				for r in cc.items:
					sn = frappe.db.get_value(
						"Serial No",
						r.serial_no,
						["custom_pattern_set", "warehouse"],
						as_dict=True,
					)
					if sn and sn.custom_pattern_set:
						frappe.throw(
							_("Cannot cancel {0}: Left-behind Serial No {1} has since been attached to {2}.").format(
								self.name, frappe.bold(r.serial_no), frappe.bold(sn.custom_pattern_set)
							)
						)
				cc.flags.ignore_permissions = True
				cc.cancel()

		# Step 5: Refresh Pattern Set location and status
		recalculate_pattern_set(self.pattern_set)


@frappe.whitelist()
def get_pattern_set_transfer_data(pattern_set):
	"""
	Loads initial transfer data: source warehouse, supplier, status, and attached serials into items table.
	In v2.0: Loaded directly from Pattern Set Component rows that have a serial_no!
	"""
	if not pattern_set or not frappe.db.exists("Pattern Set", pattern_set):
		return {}

	info = get_pattern_set_slots_and_serials(pattern_set)
	items = []

	comp_rows = frappe.get_all(
		"Pattern Set Component",
		filters={
			"parent": pattern_set,
			"serial_no": ["is", "set"],
		},
		fields=["serial_no", "item_code", "item_name", "is_optional", "warehouse", "remarks"],
		order_by="idx asc",
	)

	for r in comp_rows:
		if not r.serial_no:
			continue
		items.append({
			"include": 1,
			"serial_no": r.serial_no,
			"item_code": r.item_code,
			"item_name": r.item_name or frappe.db.get_value("Item", r.item_code, "item_name"),
			"is_optional": 1 if r.is_optional else 0,
			"warehouse": r.warehouse or info["current_warehouse"],
			"remarks": r.remarks or "",
		})

	return {
		"source_warehouse": info["current_warehouse"],
		"source_supplier": info["current_supplier"],
		"set_status": info["status"],
		"completeness_status": info["completeness_status"],
		"engineering_status": info["engineering_status"],
		"missing_items": info["missing_items"],
		"items": items,
	}
