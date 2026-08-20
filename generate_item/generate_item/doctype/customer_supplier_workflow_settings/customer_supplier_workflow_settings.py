# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint


class CustomerSupplierWorkflowSettings(Document):

	def validate(self):
		self._validate_unique_active_branch_rules()
		self._validate_approval_rules_completeness()
		self._ensure_enabled_custom_fields()

	def _validate_unique_active_branch_rules(self):
		"""Only one active rule per Branch is allowed for each workflow."""
		self._validate_unique_active_branch_rule_rows(
			self.customer_approval_rules, "Customer Approval Rules"
		)
		self._validate_unique_active_branch_rule_rows(
			self.supplier_approval_rules, "Supplier Approval Rules"
		)

	def _validate_unique_active_branch_rule_rows(self, rows, label):
		seen = set()
		for row in rows or []:
			if cint(row.disabled) or not row.branch:
				continue
			if row.branch in seen:
				frappe.throw(
					_("Duplicate active rule for Branch {0} in {1}.").format(
						frappe.bold(row.branch), frappe.bold(label)
					),
					frappe.ValidationError,
				)
			seen.add(row.branch)

	def _ensure_enabled_custom_fields(self):
		"""Create or remove workflow fields based on enabled settings."""
		from generate_item.utils.customer_supplier_workflow import (
			_cleanup_workflow_for_disabled_doctype,
			_enable_workflow_for_doctype,
		)

		if cint(self.enable_customer_approval):
			_enable_workflow_for_doctype("Customer", self, "customer")
		else:
			_cleanup_workflow_for_disabled_doctype("Customer")

		if cint(self.enable_supplier_approval):
			_enable_workflow_for_doctype("Supplier", self, "supplier")
		else:
			_cleanup_workflow_for_disabled_doctype("Supplier")

	def _validate_approval_rules_completeness(self):
		"""
		Warn if approval is enabled but no rules have been configured.
		Non-blocking — just a helpful alert, not a hard error.
		"""
		if cint(self.enable_customer_approval) and not self.customer_approval_rules:
			frappe.msgprint(
				_("Customer Approval is enabled but no Customer Approval Rules are configured. "
				  "Please add at least one branch rule."),
				indicator="orange",
				alert=True,
			)

		if cint(self.enable_supplier_approval) and not self.supplier_approval_rules:
			frappe.msgprint(
				_("Supplier Approval is enabled but no Supplier Approval Rules are configured. "
				  "Please add at least one branch rule."),
				indicator="orange",
				alert=True,
			)
