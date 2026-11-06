# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate, get_datetime


class PatternSetEngineeringChange(Document):
	def validate(self):
		self.validate_approvals()

	def validate_approvals(self):
		if self.status == "Approved":
			if not self.engineering_approver:
				self.engineering_approver = frappe.session.user
			if not self.approval_date:
				self.approval_date = nowdate()

	def on_submit(self):
		self.process_dispositions()

	def on_cancel(self):
		self.revert_dispositions()

	def process_dispositions(self):
		from generate_item.mould_set_management.pattern_set_utils import recalculate_pattern_set

		for row in self.impacted_pattern_sets:
			ps_doc = frappe.get_doc("Pattern Set", row.pattern_set)
			updated_component = False

			# Find matching component row by component_row name or item_code
			for comp in ps_doc.items:
				if (row.component_row and comp.name == row.component_row) or (comp.item_code == self.item_code):
					if row.disposition == "Accept As-Is":
						comp.approved_as_is = 1
						comp.engineering_change_ref = self.name
						row.disposition_status = "Approved As-Is"
						row.closure_date = nowdate()
						updated_component = True
					elif row.disposition == "Supplier Rework":
						# Update snapshot values to new Item revision
						comp.drawing_no = self.new_drawing_no
						comp.drawing_rev_no = self.new_drawing_rev_no
						comp.pattern_drawing_no = self.new_pattern_drawing_no
						comp.pattern_drawing_rev_no = self.new_pattern_drawing_rev_no
						comp.purchase_specification_no = self.new_purchase_specification_no
						comp.purchase_specification_rev_no = self.new_purchase_specification_rev_no
						comp.snapshot_timestamp = get_datetime()
						comp.approved_as_is = 0
						comp.engineering_change_ref = self.name
						row.disposition_status = "Rework Completed"
						row.closure_date = nowdate()
						updated_component = True
					elif row.disposition == "Return to Company":
						row.disposition_status = "Pending"
					elif row.disposition == "Replace Component":
						row.disposition_status = "Pending"

			if updated_component:
				ps_doc.flags.ignore_validate_update_after_submit = True
				ps_doc.save(ignore_permissions=True)

			# Recalculate set status
			recalculate_pattern_set(row.pattern_set)

		self.status = "Approved"

	def revert_dispositions(self):
		from generate_item.mould_set_management.pattern_set_utils import recalculate_pattern_set

		for row in self.impacted_pattern_sets:
			ps_doc = frappe.get_doc("Pattern Set", row.pattern_set)
			for comp in ps_doc.items:
				if comp.engineering_change_ref == self.name:
					comp.approved_as_is = 0
					comp.engineering_change_ref = None

			ps_doc.flags.ignore_validate_update_after_submit = True
			ps_doc.save(ignore_permissions=True)
			recalculate_pattern_set(row.pattern_set)

		self.status = "Cancelled"

