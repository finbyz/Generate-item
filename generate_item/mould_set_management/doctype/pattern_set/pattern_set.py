# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint


class PatternSet(Document):
	def autoname(self):
		self.set_pattern_set_name()
		if self.pattern_set_name:
			self.name = self.pattern_set_name

	def validate(self):
		self.set_pattern_set_name()
		self.validate_items()
		self.validate_default_and_disable()
		self.sync_component_drawings()

	def set_pattern_set_name(self):
		valve_type = (getattr(self, "type_of_valve", None) or "").strip()
		size = (getattr(self, "size", None) or "").strip()
		class_val = (self.get("class") or getattr(self, "class", None) or "").strip()
		parts = [p for p in [valve_type, size, class_val] if p]
		if parts:
			self.pattern_set_name = " ".join(parts)


	def validate_default_and_disable(self):
		if cint(self.disable) and cint(self.is_default):
			frappe.throw(_("A Disabled Pattern Set cannot be set as Default."))

	def on_update(self):
		if cint(self.is_default) and self.item:
			self.disable_other_pattern_sets()

	def on_update_after_submit(self):
		if cint(self.is_default) and self.item:
			self.disable_other_pattern_sets()

	def on_submit(self):
		if cint(self.is_default) and self.item:
			self.disable_other_pattern_sets()

	def on_change(self):
		if cint(self.is_default) and self.item:
			self.disable_other_pattern_sets()

	def on_cancel(self):
		if cint(self.is_default):
			self.db_set("is_default", 0)

	def disable_other_pattern_sets(self):
		"""
		When this Pattern Set is set as default, disable all other Pattern Sets
		matching the same Item and unset their default flag.
		"""
		other_pattern_sets = frappe.get_all(
			"Pattern Set",
			filters={
				"item": self.item,
				"name": ["!=", self.name],
				"docstatus": ["!=", 2],
			},
			pluck="name",
		)

		if other_pattern_sets:
			frappe.db.sql(
				"""
				UPDATE `tabPattern Set`
				SET is_default = 0, disable = 1
				WHERE name IN %(names)s
				""",
				{"names": tuple(other_pattern_sets)},
			)
			for ps_name in other_pattern_sets:
				frappe.clear_document_cache("Pattern Set", ps_name)

			frappe.msgprint(
				_("Other Pattern Set(s) for Item {0} have been disabled: {1}").format(
					frappe.bold(self.item),
					", ".join(frappe.bold(name) for name in other_pattern_sets),
				),
				alert=True,
			)

	def validate_items(self):
		if not self.item:
			frappe.throw(_("Pattern Set Item is mandatory."))

		if not self.items:
			frappe.throw(_("At least one component item is required in the Pattern Set."))

		seen_components = set()
		for row in self.items:
			if not row.component_item:
				frappe.throw(_("Row #{0}: Component Item is required.").format(row.idx))

			if row.component_item == self.item:
				frappe.throw(
					_("Row #{0}: Component Item cannot be the same as Pattern Set Item ({1}).").format(
						row.idx, self.item
					)
				)

			if row.component_item in seen_components:
				frappe.throw(
					_("Row #{0}: Duplicate Component Item {1} found.").format(
						row.idx, frappe.bold(row.component_item)
					)
				)
			seen_components.add(row.component_item)

			if not row.qty or row.qty <= 0:
				frappe.throw(
					_("Row #{0}: Qty must be greater than 0 for Component {1}.").format(
						row.idx, row.component_item
					)
				)

	def sync_component_drawings(self):
		"""
		Enforce data consistency across items linked to the pattern set:
		Auto-fetches item details and drawing/pattern details from Item master.
		"""
		for row in self.items:
			item_data = frappe.db.get_value(
				"Item",
				row.component_item,
				[
					"item_name",
					"stock_uom",
					"custom_drawing_no",
					"custom_drawing_rev_no",
					"custom_pattern_drawing_no",
					"custom_pattern_drawing_rev_no",
				],
				as_dict=True,
			)
			if not item_data:
				continue

			if not row.component_name:
				row.component_name = item_data.item_name
			if not row.uom:
				row.uom = item_data.stock_uom

			# Fetch drawing details if empty or ensure consistency
			if not row.drawing_no and item_data.custom_drawing_no:
				row.drawing_no = item_data.custom_drawing_no
			if not row.drawing_rev_no and item_data.custom_drawing_rev_no:
				row.drawing_rev_no = item_data.custom_drawing_rev_no
			if not row.pattern_drawing_no and item_data.custom_pattern_drawing_no:
				row.pattern_drawing_no = item_data.custom_pattern_drawing_no
			if not row.pattern_drawing_rev_no and item_data.custom_pattern_drawing_rev_no:
				row.pattern_drawing_rev_no = item_data.custom_pattern_drawing_rev_no
