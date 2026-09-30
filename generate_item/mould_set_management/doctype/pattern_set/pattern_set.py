# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class PatternSet(Document):
	def autoname(self):
		valve_type = (getattr(self, "type_of_valve", None) or "").strip()
		size = (getattr(self, "size", None) or "").strip()
		class_val = (self.get("class") or getattr(self, "class", None) or "").strip()

		if not (valve_type and size and class_val):
			frappe.throw(_("Type of Valve, Size, and Class are required to generate Naming Series."))

		self.name = get_next_pattern_set_name(
			valve_type, size, class_val, exclude_name=self.name if not self.is_new() else None
		)
		self.naming_series = self.name
		self.pattern_set_name = f"{valve_type} {size} {class_val}"

	def validate(self):
		self.set_pattern_set_name()
		self.validate_items()
		self.sync_component_drawings()

	def set_pattern_set_name(self):
		valve_type = (getattr(self, "type_of_valve", None) or "").strip()
		size = (getattr(self, "size", None) or "").strip()
		class_val = (self.get("class") or getattr(self, "class", None) or "").strip()
		if valve_type and size and class_val:
			self.pattern_set_name = f"{valve_type} {size} {class_val}"
		if not getattr(self, "naming_series", None) and self.name:
			self.naming_series = self.name

	def validate_items(self):
		if not self.items:
			frappe.throw(_("At least one component item is required in the Pattern Set."))

		seen_components = set()
		for row in self.items:
			if not row.component_item:
				frappe.throw(_("Row #{0}: Component Item is required.").format(row.idx))

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


@frappe.whitelist()
def get_next_pattern_set_name(type_of_valve, size, class_val, exclude_name=None):
	valve_type = (type_of_valve or "").strip()
	size = (size or "").strip()
	class_val = (class_val or "").strip()

	if not (valve_type and size and class_val):
		return ""

	prefix = f"{valve_type} {size} {class_val}-"

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
