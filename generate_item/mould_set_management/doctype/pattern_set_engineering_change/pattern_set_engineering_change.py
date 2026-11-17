# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from generate_item.mould_set_management.pattern_set_utils import (
	recalculate_pattern_set,
	sync_pattern_set_engineering_status,
)


class PatternSetEngineeringChange(Document):
	def on_update(self):
		self.propagate_engineering_status()

	def on_submit(self):
		self.db_set("status", "Approved")
		self.recalculate_impacted_pattern_sets()
		self.propagate_engineering_status()

	def on_update_after_submit(self):
		self.propagate_engineering_status()

	def on_cancel(self):
		self.revert_legacy_component_approvals()
		self.recalculate_impacted_pattern_sets()
		self.propagate_engineering_status("Open")

	def propagate_engineering_status(self, status=None):
		status = status or self.status
		for row in self.impacted_pattern_sets:
			sync_pattern_set_engineering_status(row.pattern_set, status)

	def recalculate_impacted_pattern_sets(self):
		for row in self.impacted_pattern_sets:
			recalculate_pattern_set(row.pattern_set)

	def revert_legacy_component_approvals(self):
		for row in self.impacted_pattern_sets:
			ps_doc = frappe.get_doc("Pattern Set", row.pattern_set)
			updated_component = False
			for comp in ps_doc.items:
				if comp.engineering_change_ref == self.name:
					comp.approved_as_is = 0
					comp.engineering_change_ref = None
					updated_component = True

			if updated_component:
				ps_doc.flags.ignore_validate_update_after_submit = True
				ps_doc.save(ignore_permissions=True)

