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
)
from generate_item.mould_set_management.doctype.component_pairing_log.component_pairing_log import (
	close_pairing,
	log_pairing,
)


class PatternSetComponentChange(Document):
	def validate(self):
		self.validate_pattern_set()
		self.validate_rows()
		self.set_info = render_set_info_html(self.pattern_set)

	def validate_pattern_set(self):
		if not self.pattern_set:
			frappe.throw(_("Pattern Set is required."))

		ps_data = frappe.db.get_value(
			"Pattern Set",
			self.pattern_set,
			["docstatus", "disabled", "disable"],
			as_dict=True,
		)
		if not ps_data:
			frappe.throw(_("Pattern Set {0} does not exist.").format(self.pattern_set))

		if ps_data.docstatus != 1:
			frappe.throw(_("Pattern Set {0} must be submitted before changing components.").format(self.pattern_set))

		if ps_data.disabled or ps_data.disable:
			frappe.throw(_("Pattern Set {0} is disabled and cannot be modified.").format(self.pattern_set))

	def validate_rows(self):
		if not self.items:
			frappe.throw(_("At least one component change row is required."))

		info = get_pattern_set_slots_and_serials(self.pattern_set)
		current_wh = info["current_warehouse"]

		# Count available open rows in this pattern set by item_code
		open_rows = frappe.get_all(
			"Pattern Set Component",
			filters={
				"parent": self.pattern_set,
				"serial_no": ["in", ["", None]],
			},
			fields=["name", "item_code", "is_optional"],
			order_by="is_optional asc, idx asc",
		)
		open_count_by_item = {}
		for r in open_rows:
			open_count_by_item[r.item_code] = open_count_by_item.get(r.item_code, 0) + 1

		# Also get list of all items that exist in the set
		all_set_items = {r["item_code"] for r in info["rows"]}

		seen_serials = set()
		decided_wh = current_wh
		needed_open_by_item = {}

		for idx, row in enumerate(self.items, start=1):
			if not row.serial_no:
				frappe.throw(_("Row #{0}: Serial No is required.").format(idx))

			if row.serial_no in seen_serials:
				frappe.throw(_("Serial No {0} appears more than once in this document.").format(frappe.bold(row.serial_no)))
			seen_serials.add(row.serial_no)

			sn_data = frappe.db.get_value(
				"Serial No",
				row.serial_no,
				["item_code", "warehouse", "status", "custom_pattern_set"],
				as_dict=True,
			)

			if not sn_data:
				frappe.throw(_("Row #{0}: Serial No {1} does not exist.").format(idx, row.serial_no))

			row.item_code = sn_data.item_code
			row.warehouse = sn_data.warehouse
			row.previous_set = sn_data.custom_pattern_set or ""

			if row.action == "Attach":
				# Acceptance Test 3: Item must be in the set
				if sn_data.item_code not in all_set_items:
					frappe.throw(
						_("Row #{0}: Item {1} of Serial No {2} is not a valid component in Pattern Set {3}.").format(
							idx, frappe.bold(sn_data.item_code), frappe.bold(row.serial_no), frappe.bold(self.pattern_set)
						)
					)

				# Acceptance Test 10: Set must have an open row for that item
				needed_open_by_item[sn_data.item_code] = needed_open_by_item.get(sn_data.item_code, 0) + 1
				available_open = open_count_by_item.get(sn_data.item_code, 0)
				if needed_open_by_item[sn_data.item_code] > available_open:
					frappe.throw(
						_("Pattern Set {0} does not have an open row for Item {1}. Add a row for this item in the set first (rows can be added after submit).").format(
							frappe.bold(self.pattern_set), frappe.bold(sn_data.item_code)
						)
					)

				if sn_data.status != "Active":
					frappe.throw(
						_("Row #{0}: Serial No {1} cannot be attached because its status is {2} (must be Active).").format(
							idx, frappe.bold(row.serial_no), frappe.bold(sn_data.status)
						)
					)

				if sn_data.custom_pattern_set == self.pattern_set:
					frappe.throw(
						_("Row #{0}: Serial No {1} is already attached to Pattern Set {2}.").format(
							idx, frappe.bold(row.serial_no), frappe.bold(self.pattern_set)
						)
					)

				if not decided_wh:
					decided_wh = sn_data.warehouse

				# Acceptance Test 5 & 12: Warehouse mismatch
				if decided_wh and sn_data.warehouse != decided_wh:
					frappe.throw(
						_("Serial {0} is in warehouse {1}, but Pattern Set {2} is at {3}. Move the component to the set's warehouse first, or use a Pattern Set Transfer.").format(
							frappe.bold(row.serial_no),
							frappe.bold(sn_data.warehouse),
							frappe.bold(self.pattern_set),
							frappe.bold(decided_wh),
						)
					)

			elif row.action == "Detach":
				# Serial must be currently in this set
				attached_in_set = frappe.db.get_value(
					"Pattern Set Component",
					{"parent": self.pattern_set, "serial_no": row.serial_no},
					"name",
				)
				if not attached_in_set and sn_data.custom_pattern_set != self.pattern_set:
					frappe.throw(
						_("Row #{0}: Serial No {1} is not attached to Pattern Set {2} and cannot be detached.").format(
							idx, frappe.bold(row.serial_no), frappe.bold(self.pattern_set)
						)
					)

	def on_submit(self):
		"""
		v2.0 Section 6.3:
		1. Attach, serial in another set: in previous set find row holding serial, blank it, close pairing log.
		2. Attach: in this set pick an open row (required first, then optional), fill serial, warehouse, paired_on.
		3. Detach: blank the row in this set, clear Serial No, close pairing log.
		4. Recalculate status and location.
		"""
		previous_sets_to_refresh = set()
		now = now_datetime()

		# Fetch all currently open rows in this pattern set ordered required first
		available_open_rows = frappe.get_all(
			"Pattern Set Component",
			filters={
				"parent": self.pattern_set,
				"serial_no": ["in", ["", None]],
			},
			fields=["name", "item_code", "is_optional"],
			order_by="is_optional asc, idx asc",
		)

		for row in self.items:
			if row.action == "Attach":
				# Step 1: If serial was in another set, free it from that set's row
				if row.previous_set:
					previous_sets_to_refresh.add(row.previous_set)
					prev_comp_row = frappe.db.get_value(
						"Pattern Set Component",
						{"parent": row.previous_set, "serial_no": row.serial_no},
						"name",
					)
					if prev_comp_row:
						row.previous_row = prev_comp_row
						frappe.db.set_value(
							"Pattern Set Component",
							prev_comp_row,
							{"serial_no": None, "warehouse": None, "paired_on": None},
							update_modified=False,
						)

					close_pairing(
						serial_no=row.serial_no,
						pattern_set=row.previous_set,
						change_ref=self.name,
						reason=f"Moved to {self.pattern_set} via {self.name}",
						source_doctype="Pattern Set Component Change",
						source_doc=self.name,
					)

				# Step 2: Fill an open row in this set (required rows first, then optional)
				target_open_row = None
				for cand in available_open_rows:
					if cand.item_code == row.item_code:
						target_open_row = cand
						available_open_rows.remove(cand)
						break

				if not target_open_row:
					frappe.throw(
						_("No open row available for Item {0} in Pattern Set {1}.").format(
							row.item_code, self.pattern_set
						)
					)

				row.set_row = target_open_row.name
				frappe.db.set_value(
					"Pattern Set Component",
					target_open_row.name,
					{"serial_no": row.serial_no, "warehouse": row.warehouse, "paired_on": now},
					update_modified=False,
				)

				# Update Serial No
				frappe.db.set_value("Serial No", row.serial_no, "custom_pattern_set", self.pattern_set)

				# Log pairing
				log_pairing(
					serial_no=row.serial_no,
					item_code=row.item_code,
					pattern_set=self.pattern_set,
					change_ref=self.name,
					reason=self.reason or row.remarks or f"Attached via {self.name}",
					source_doctype="Pattern Set Component Change",
					source_doc=self.name,
				)

				# Store set_row and previous_row on child item row
				frappe.db.set_value(
					row.doctype,
					row.name,
					{"set_row": row.set_row, "previous_row": row.previous_row},
					update_modified=False,
				)

			elif row.action == "Detach":
				# Step 3: Blank the row holding the serial in this set
				comp_row = frappe.db.get_value(
					"Pattern Set Component",
					{"parent": self.pattern_set, "serial_no": row.serial_no},
					"name",
				)
				if comp_row:
					row.set_row = comp_row
					frappe.db.set_value(
						"Pattern Set Component",
						comp_row,
						{"serial_no": None, "warehouse": None, "paired_on": None},
						update_modified=False,
					)
					frappe.db.set_value(row.doctype, row.name, "set_row", comp_row, update_modified=False)

				# Clear Serial No
				frappe.db.set_value("Serial No", row.serial_no, "custom_pattern_set", None)

				# Close pairing stay
				close_pairing(
					serial_no=row.serial_no,
					pattern_set=self.pattern_set,
					change_ref=self.name,
					reason=self.reason or row.remarks or f"Detached via {self.name}",
					source_doctype="Pattern Set Component Change",
					source_doc=self.name,
				)

		# Recalculate status and location for this set and all previous sets touched
		recalculate_pattern_set(self.pattern_set)
		for ps in previous_sets_to_refresh:
			if ps != self.pattern_set:
				recalculate_pattern_set(ps)

	def on_cancel(self):
		"""
		v2.0 Section 6.4:
		Reverses every row using Set Row and Previous Row. Before reversing, check that each serial
		is still where this document left it, and that the row is still open or still holds the serial;
		otherwise block with a message naming the serial and where it is now.
		"""
		# Validation phase before reversing
		for row in self.items:
			current_ps = frappe.db.get_value("Serial No", row.serial_no, "custom_pattern_set")
			current_wh = frappe.db.get_value("Serial No", row.serial_no, "warehouse")

			if row.action == "Attach":
				if current_ps != self.pattern_set:
					frappe.throw(
						_("Cannot cancel: Serial No {0} is currently in Pattern Set {1} (expected {2}).").format(
							frappe.bold(row.serial_no), frappe.bold(current_ps or "Free"), frappe.bold(self.pattern_set)
						)
					)
				if current_wh != row.warehouse:
					frappe.throw(
						_("Cannot cancel: Serial No {0} has moved from warehouse {1} to {2}.").format(
							frappe.bold(row.serial_no), frappe.bold(row.warehouse), frappe.bold(current_wh)
						)
					)

			elif row.action == "Detach":
				if current_ps:
					frappe.throw(
						_("Cannot cancel: Serial No {0} has since been attached to Pattern Set {1}.").format(
							frappe.bold(row.serial_no), frappe.bold(current_ps)
						)
					)
				if current_wh != row.warehouse:
					frappe.throw(
						_("Cannot cancel: Serial No {0} has moved from warehouse {1} to {2}.").format(
							frappe.bold(row.serial_no), frappe.bold(row.warehouse), frappe.bold(current_wh)
						)
					)

		# Execution phase: reverse rows
		now = now_datetime()
		previous_sets_to_refresh = set()

		for row in self.items:
			if row.action == "Attach":
				# Blank the row in this pattern set
				if row.set_row and frappe.db.exists("Pattern Set Component", row.set_row):
					frappe.db.set_value(
						"Pattern Set Component",
						row.set_row,
						{"serial_no": None, "warehouse": None, "paired_on": None},
						update_modified=False,
					)
				else:
					cur_r = frappe.db.get_value(
						"Pattern Set Component",
						{"parent": self.pattern_set, "serial_no": row.serial_no},
						"name",
					)
					if cur_r:
						frappe.db.set_value(
							"Pattern Set Component",
							cur_r,
							{"serial_no": None, "warehouse": None, "paired_on": None},
							update_modified=False,
						)

				close_pairing(
					serial_no=row.serial_no,
					pattern_set=self.pattern_set,
					change_ref=self.name,
					reason=f"Cancelled: Detached from {self.pattern_set}",
					source_doctype="Pattern Set Component Change",
					source_doc=self.name,
				)

				# Return serial to previous set if it had one, or free it
				if row.previous_set:
					previous_sets_to_refresh.add(row.previous_set)
					prev_target_row = None
					if row.previous_row and frappe.db.exists("Pattern Set Component", row.previous_row):
						if not frappe.db.get_value("Pattern Set Component", row.previous_row, "serial_no"):
							prev_target_row = row.previous_row

					if not prev_target_row:
						open_cand = frappe.db.get_value(
							"Pattern Set Component",
							{"parent": row.previous_set, "item_code": row.item_code, "serial_no": ["in", ["", None]]},
							"name",
						)
						if open_cand:
							prev_target_row = open_cand
						else:
							# Previous row was deleted in meantime, add new row to previous set
							prev_doc = frappe.get_doc("Pattern Set", row.previous_set)
							new_child = prev_doc.append("items", {
								"item_code": row.item_code,
								"item_name": frappe.db.get_value("Item", row.item_code, "item_name"),
								"is_optional": 0,
							})
							new_child.db_insert()
							prev_target_row = new_child.name

					frappe.db.set_value(
						"Pattern Set Component",
						prev_target_row,
						{"serial_no": row.serial_no, "warehouse": row.warehouse, "paired_on": now},
						update_modified=False,
					)
					frappe.db.set_value("Serial No", row.serial_no, "custom_pattern_set", row.previous_set)
					log_pairing(
						serial_no=row.serial_no,
						item_code=row.item_code,
						pattern_set=row.previous_set,
						change_ref=self.name,
						reason=f"Cancelled: Re-attached to {row.previous_set}",
						source_doctype="Pattern Set Component Change",
						source_doc=self.name,
					)
				else:
					frappe.db.set_value("Serial No", row.serial_no, "custom_pattern_set", None)

			elif row.action == "Detach":
				# Re-attach back to self.pattern_set
				target_set_row = None
				if row.set_row and frappe.db.exists("Pattern Set Component", row.set_row):
					if not frappe.db.get_value("Pattern Set Component", row.set_row, "serial_no"):
						target_set_row = row.set_row

				if not target_set_row:
					open_cand = frappe.db.get_value(
						"Pattern Set Component",
						{"parent": self.pattern_set, "item_code": row.item_code, "serial_no": ["in", ["", None]]},
						"name",
					)
					if open_cand:
						target_set_row = open_cand
					else:
						# Re-add row if deleted
						ps_doc = frappe.get_doc("Pattern Set", self.pattern_set)
						new_child = ps_doc.append("items", {
							"item_code": row.item_code,
							"item_name": frappe.db.get_value("Item", row.item_code, "item_name"),
							"is_optional": 0,
						})
						new_child.db_insert()
						target_set_row = new_child.name

				frappe.db.set_value(
					"Pattern Set Component",
					target_set_row,
					{"serial_no": row.serial_no, "warehouse": row.warehouse, "paired_on": now},
					update_modified=False,
				)
				frappe.db.set_value("Serial No", row.serial_no, "custom_pattern_set", self.pattern_set)
				log_pairing(
					serial_no=row.serial_no,
					item_code=row.item_code,
					pattern_set=self.pattern_set,
					change_ref=self.name,
					reason=f"Cancelled: Re-attached to {self.pattern_set}",
					source_doctype="Pattern Set Component Change",
					source_doc=self.name,
				)

		# Recalculate
		recalculate_pattern_set(self.pattern_set)
		for ps in previous_sets_to_refresh:
			if ps != self.pattern_set:
				recalculate_pattern_set(ps)


@frappe.whitelist()
def get_serial_details(serial_no, pattern_set=None):
	if not serial_no or not frappe.db.exists("Serial No", serial_no):
		return {}
	data = frappe.db.get_value(
		"Serial No",
		serial_no,
		["item_code", "warehouse", "status", "custom_pattern_set"],
		as_dict=True,
	)
	return {
		"item_code": data.item_code,
		"warehouse": data.warehouse,
		"status": data.status,
		"previous_set": data.custom_pattern_set or "",
	}

