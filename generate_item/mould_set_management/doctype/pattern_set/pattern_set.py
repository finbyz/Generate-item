# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime
from generate_item.mould_set_management.pattern_set_utils import (
	get_pattern_set_slots_and_serials,
	recalculate_pattern_set,
	render_set_info_html,
	render_transfer_history_html,
)
from generate_item.mould_set_management.doctype.component_pairing_log.component_pairing_log import (
	log_pairing,
)


class PatternSet(Document):
	@property
	def components(self):
		return self.items

	def autoname(self):
		valve_type = (getattr(self, "type_of_valve", None) or "").strip()
		size = (getattr(self, "size", None) or "").strip()
		class_val = (self.get("class") or getattr(self, "class", None) or "").strip()
		bore = (getattr(self, "bore", None) or "").strip()
		if bore == "-":
			bore = ""

		if not (valve_type and size and class_val):
			frappe.throw(_("Type of Valve, Size, and Class are required to generate Naming Series."))

		self.name = get_next_pattern_set_name(
			valve_type, size, class_val, bore=bore, exclude_name=self.name if not self.is_new() else None
		)
		self.naming_series = self.name
		parts = [valve_type, size, class_val]
		if bore:
			parts.append(bore)
		self.pattern_set_name = " ".join(parts)

	def validate(self):
		self.sync_disabled_flags()
		self.set_pattern_set_name()
		self.validate_items()
		self.validate_post_submit_changes()
		self.sync_component_drawings()
		if self.name and not self.is_new():
			self.set_info = render_set_info_html(self.name)
			self.transfer_history = render_transfer_history_html(self.name)

	def sync_disabled_flags(self):
		if self.disabled and not self.disable:
			self.disable = self.disabled
		elif self.disable and not self.disabled:
			self.disabled = self.disable

	def set_pattern_set_name(self):
		valve_type = (getattr(self, "type_of_valve", None) or "").strip()
		size = (getattr(self, "size", None) or "").strip()
		class_val = (self.get("class") or getattr(self, "class", None) or "").strip()
		bore = (getattr(self, "bore", None) or "").strip()
		if bore == "-":
			bore = ""

		if valve_type and size and class_val:
			parts = [valve_type, size, class_val]
			if bore:
				parts.append(bore)
			self.pattern_set_name = " ".join(parts)
		if not getattr(self, "naming_series", None) and self.name:
			self.naming_series = self.name

	def validate_items(self):
		"""
		v2.0 Section 5.1:
		- At least one component row required.
		- For each row: select item, optionally serial (blank = open row).
		- Serial must be Active, belong to row's item, and be free.
		- The same item can appear in many rows (one row = one piece).
		- If rows hold serials from different warehouses, warning on save.
		"""
		if not self.items:
			frappe.throw(_("At least one component row is required in the Pattern Set."))

		seen_serials = set()
		warehouses = set()
		serial_warehouse_map = {}

		for row in self.items:
			item_code = row.item_code or row.component_item
			if not item_code:
				frappe.throw(_("Row #{0}: Item Code is required.").format(row.idx))

			# Section 5.1: Item must have Has Serial No ticked
			has_serial_no = frappe.db.get_value("Item", item_code, "has_serial_no")
			if not has_serial_no:
				frappe.throw(
					_("Row #{0}: Item {1} must have 'Has Serial No' enabled.").format(row.idx, frappe.bold(item_code))
				)

			# Sync legacy field
			row.item_code = item_code
			row.component_item = item_code

			serial_no = (row.serial_no or "").strip()
			if serial_no:
				if serial_no in seen_serials:
					frappe.throw(
						_("Row #{0}: Serial No {1} appears more than once in this Pattern Set.").format(
							row.idx, frappe.bold(serial_no)
						)
					)
				seen_serials.add(serial_no)

				sn_data = frappe.db.get_value(
					"Serial No",
					serial_no,
					["item_code", "warehouse", "status", "custom_pattern_set"],
					as_dict=True,
				)

				if not sn_data:
					frappe.throw(_("Row #{0}: Serial No {1} does not exist.").format(row.idx, frappe.bold(serial_no)))

				# Item match check (Acceptance Test 1)
				if sn_data.item_code != item_code:
					frappe.throw(
						_("Row #{0}: Serial No {1} belongs to Item {2}, not {3}.").format(
							row.idx, frappe.bold(serial_no), frappe.bold(sn_data.item_code), frappe.bold(item_code)
						)
					)

				# Status check
				if sn_data.status != "Active":
					frappe.throw(
						_("Row #{0}: Serial No {1} is not Active (status: {2}).").format(
							row.idx, frappe.bold(serial_no), frappe.bold(sn_data.status)
						)
					)

				# Free check (Acceptance Test 2, 4)
				if sn_data.custom_pattern_set and sn_data.custom_pattern_set != self.name:
					ps_docstatus = frappe.db.get_value("Pattern Set", sn_data.custom_pattern_set, "docstatus")
					if ps_docstatus == 1:
						frappe.throw(
							_("Serial No {0} is currently in submitted Pattern Set {1}. Use Pattern Set Component Change on this set after submitting, or detach it first.").format(
								frappe.bold(serial_no), frappe.bold(sn_data.custom_pattern_set)
							)
						)
					elif ps_docstatus == 0:
						frappe.throw(
							_("Serial No {0} is already used in Draft Pattern Set {1}.").format(
								frappe.bold(serial_no), frappe.bold(sn_data.custom_pattern_set)
							)
						)

				# Check other draft sets where serial might be listed in component rows
				other_draft = frappe.db.sql(
					"""
					SELECT parent FROM `tabPattern Set Component`
					WHERE serial_no = %s AND parent != %s AND parent IN (
						SELECT name FROM `tabPattern Set` WHERE docstatus = 0
					)
					LIMIT 1
					""",
					(serial_no, self.name or ""),
				)
				if other_draft:
					frappe.throw(
						_("Serial No {0} is already in another Draft Pattern Set {1}.").format(
							frappe.bold(serial_no), frappe.bold(other_draft[0][0])
						)
					)

				# Fetch and set warehouse
				row.warehouse = sn_data.warehouse
				if sn_data.warehouse:
					warehouses.add(sn_data.warehouse)
					serial_warehouse_map[serial_no] = sn_data.warehouse

		# Warning on save if multiple warehouses
		if len(warehouses) > 1 and self.docstatus == 0:
			wh_details = ", ".join(f"{sn} ({wh})" for sn, wh in serial_warehouse_map.items())
			frappe.msgprint(
				_("Warning: Components are in different warehouses: {0}. All components must be in one warehouse before submitting.").format(
					wh_details
				),
				indicator="orange",
				alert=True,
			)

	def validate_post_submit_changes(self):
		"""
		v2.0 Section 5.3: What can be edited after submit
		- Serial No of a row: No. Locked. Changed only through Pattern Set Component Change.
		- Item Code of a row that has a serial: No.
		- Item Code of an open row: Yes.
		- Is Optional on any row: Yes. Status is recalculated on save.
		- Remarks: Yes.
		- Disabled: Yes. Status becomes Disabled.
		- Add a new row: Yes, as an open row (blank serial).
		- Delete a row: Only if its serial is blank. A row holding a serial must be detached first.
		"""
		if self.docstatus == 1 and not self.is_new():
			db_rows = frappe.get_all(
				"Pattern Set Component",
				filters={"parent": self.name},
				fields=["name", "item_code", "serial_no", "is_optional"],
			)
			old_rows_by_name = {r.name: r for r in db_rows}
			new_rows_by_name = {r.name: r for r in (self.items or []) if getattr(r, "name", None)}

			# Check deleted rows
			deleted_names = set(old_rows_by_name.keys()) - set(new_rows_by_name.keys())
			for d_name in deleted_names:
				old_r = old_rows_by_name[d_name]
				if old_r.serial_no:
					frappe.throw(
						_("Row with Serial No {0} cannot be deleted. A row holding a serial must be detached first through Pattern Set Component Change.").format(
							frappe.bold(old_r.serial_no)
						)
					)

			# Check added rows
			for r in (self.items or []):
				r_name = getattr(r, "name", None)
				if not r_name or r_name not in old_rows_by_name:
					if getattr(r, "serial_no", None):
						frappe.throw(
							_("Cannot add a row with a Serial No on a submitted Pattern Set. New rows must be open rows (blank serial). Use Pattern Set Component Change to attach serials.")
						)

			# Check existing rows
			for name, old_r in old_rows_by_name.items():
				if name in new_rows_by_name:
					new_r = new_rows_by_name[name]
					new_serial = (getattr(new_r, "serial_no", None) or "").strip()
					old_serial = (old_r.serial_no or "").strip()
					new_item = getattr(new_r, "item_code", None) or getattr(new_r, "component_item", None)
					old_item = old_r.item_code

					if old_serial:
						if new_serial != old_serial:
							frappe.throw(
								_("Cannot change Serial No of a row after submit. Serial No is locked and can only be changed via Pattern Set Component Change.")
							)
						if new_item != old_item:
							frappe.throw(
								_("Cannot change Item Code of a row that has an attached serial after submit.")
							)
					else:
						# Row was open
						if new_serial:
							frappe.throw(
								_("Cannot attach Serial No directly to an open row on a submitted Pattern Set. Use Pattern Set Component Change to attach components.")
							)

	def before_submit(self):
		"""
		v2.0 Section 5.2:
		1. All serials in the table must be in one warehouse. Otherwise block, naming serials and warehouses.
		"""
		warehouses = set()
		serial_wh_map = {}
		for row in self.items:
			if row.serial_no:
				wh = frappe.db.get_value("Serial No", row.serial_no, "warehouse")
				row.warehouse = wh
				if wh:
					warehouses.add(wh)
					serial_wh_map[row.serial_no] = wh

		# Rule 1: All serials must be in one warehouse (Acceptance Test 5)
		if len(warehouses) > 1:
			details = ", ".join(f"{sn} in {wh}" for sn, wh in serial_wh_map.items())
			frappe.throw(
				_("All serials in the table must be in one warehouse before submitting. The following serials are in different warehouses: {0}").format(
					details
				)
			)

	def sync_component_drawings(self):
		for row in self.items:
			item_code = row.item_code or row.component_item
			item_data = frappe.db.get_value(
				"Item",
				item_code,
				[
					"item_name",
					"stock_uom",
					"custom_drawing_no",
					"custom_drawing_rev_no",
					"custom_pattern_drawing_no",
					"custom_pattern_drawing_rev_no",
					"custom_purchase_specification_no",
					"custom_purchase_specification_rev_no",
				],
				as_dict=True,
			)
			if not item_data:
				continue

			if not row.item_name:
				row.item_name = item_data.item_name
			if not row.component_name:
				row.component_name = item_data.item_name
			if not row.uom:
				row.uom = item_data.stock_uom

			if not row.drawing_no and item_data.custom_drawing_no:
				row.drawing_no = item_data.custom_drawing_no
			if not row.drawing_rev_no and item_data.custom_drawing_rev_no:
				row.drawing_rev_no = item_data.custom_drawing_rev_no
			if not row.pattern_drawing_no and item_data.custom_pattern_drawing_no:
				row.pattern_drawing_no = item_data.custom_pattern_drawing_no
			if not row.pattern_drawing_rev_no and item_data.custom_pattern_drawing_rev_no:
				row.pattern_drawing_rev_no = item_data.custom_pattern_drawing_rev_no
			if not row.purchase_specification_no and item_data.custom_purchase_specification_no:
				row.purchase_specification_no = item_data.custom_purchase_specification_no
			if not row.purchase_specification_rev_no and item_data.custom_purchase_specification_rev_no:
				row.purchase_specification_rev_no = item_data.custom_purchase_specification_rev_no
			if not getattr(row, "snapshot_timestamp", None):
				row.snapshot_timestamp = now_datetime()

	def on_submit(self):
		"""
		v2.0 Section 5.2:
		1. All serials in the table must be in one warehouse. (Validated in before_submit)
		2. For each row with a serial: write set name to Serial No field custom_pattern_set, set row's Paired On, create Pairing Log row.
		3. Calculate status, current warehouse and current supplier.
		4. A submitted set with required rows still blank becomes Incomplete.
		"""
		now = now_datetime()

		# Rule 2: Update Serial No and Pairing Log
		for row in self.items:
			if row.serial_no:
				wh = frappe.db.get_value("Serial No", row.serial_no, "warehouse")
				row.warehouse = wh
				row.paired_on = now
				frappe.db.set_value("Serial No", row.serial_no, "custom_pattern_set", self.name)
				log_pairing(
					serial_no=row.serial_no,
					item_code=row.item_code,
					pattern_set=self.name,
					reason="Initial Setup",
					source_doctype="Pattern Set",
					source_doc=self.name,
				)
				# Update child row fields in DB
				frappe.db.set_value(
					row.doctype,
					row.name,
					{"paired_on": now, "warehouse": row.warehouse},
					update_modified=False,
				)

		# Rule 3 & 4: Calculate status, warehouse, supplier
		info = recalculate_pattern_set(self.name)
		if info:
			self.status = info["status"]
			self.completeness_status = info["completeness_status"]
			self.engineering_status = info["engineering_status"]
			self.current_warehouse = info["current_warehouse"]
			self.current_supplier = info["current_supplier"]

	def before_update_after_submit(self):
		self.sync_disabled_flags()
		self.validate_post_submit_changes()
		self.sync_component_drawings()

	def on_update_after_submit(self):
		self.sync_disabled_flags()
		info = recalculate_pattern_set(self.name)
		if info:
			self.status = info["status"]
			self.completeness_status = info["completeness_status"]
			self.engineering_status = info["engineering_status"]
			self.current_warehouse = info["current_warehouse"]
			self.current_supplier = info["current_supplier"]

	def on_cancel(self):
		"""
		v2.0 Section 5.5:
		Blocked while any serial is attached. The message tells the user to detach all components first through a Component Change.
		"""
		attached = [r.serial_no for r in self.items if r.serial_no]
		if not attached:
			# Also check DB Serial No table directly
			attached = frappe.get_all(
				"Serial No",
				filters={"custom_pattern_set": self.name},
				pluck="name",
			)

		if attached:
			frappe.throw(
				_("Cannot cancel Pattern Set {0} because serial numbers ({1}) are currently attached. Detach all components first through a Component Change.").format(
					self.name, ", ".join(attached)
				)
			)
		self.db_set("status", "Cancelled")


@frappe.whitelist()
def get_set_info_html(pattern_set):
	return render_set_info_html(pattern_set)


@frappe.whitelist()
def get_next_pattern_set_name(type_of_valve, size, class_val, bore=None, exclude_name=None):
	valve_type = (type_of_valve or "").strip()
	size = (size or "").strip()
	class_val = (class_val or "").strip()
	bore_val = (bore or "").strip()
	if bore_val == "-":
		bore_val = ""

	if not (valve_type and size and class_val):
		return ""

	parts = [valve_type, size, class_val]
	if bore_val:
		parts.append(bore_val)

	prefix = f"{' '.join(parts)}-"

	existing_names = frappe.get_all(
		"Pattern Set",
		filters={"name": ["like", f"{prefix}%"]},
		pluck="name",
	)

	max_num = 0
	for n in existing_names:
		if exclude_name and n == exclude_name:
			continue
		suffix = n[len(prefix):]
		if suffix.isdigit():
			max_num = max(max_num, int(suffix))

	next_num = max_num + 1
	return f"{prefix}{next_num:04d}"
