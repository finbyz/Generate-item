# Copyright (c) 2026, Finbyz and Contributors
# For license information, please see license.txt

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

import frappe

from generate_item.mould_set_management.doctype.pattern_set_transfer.pattern_set_transfer import (
	PatternSetTransfer,
)


class TestPatternSetTransferPurposeValidation(TestCase):
	def setUp(self):
		frappe.local.db = SimpleNamespace(get_value=None, sql=None)

	def validate_pattern_set(self, purpose, status, completeness_status, engineering_status):
		transfer = SimpleNamespace(
			purpose=purpose,
			pattern_set="PS-TEST",
			source_warehouse="",
			items=[object()],
			is_new=lambda: True,
			load_components_from_pattern_set=lambda: None,
		)
		pattern_set = frappe._dict({
			"docstatus": 1,
			"disabled": 0,
			"disable": 0,
			"status": status,
			"completeness_status": completeness_status,
			"engineering_status": engineering_status,
		})
		info = {
			"attached_serials": ["SN-TEST"],
			"current_warehouse": "WH-TEST",
			"current_supplier": "",
			"status": status,
			"completeness_status": completeness_status,
			"engineering_status": engineering_status,
		}

		with (
			patch.object(frappe.db, "get_value", return_value=pattern_set),
			patch.object(frappe.db, "sql", return_value=[]),
			patch(
				"generate_item.mould_set_management.doctype.pattern_set_transfer.pattern_set_transfer.get_pattern_set_slots_and_serials",
				return_value=info,
			),
		):
			PatternSetTransfer.validate_pattern_set(transfer)

	def validate_target_warehouse(self, purpose, supplier):
		transfer = SimpleNamespace(
			purpose=purpose,
			target_warehouse="WH-TARGET",
			source_warehouse="WH-SOURCE",
			company="TEST-COMPANY",
		)
		warehouse = frappe._dict({
			"is_group": 0,
			"disabled": 0,
			"company": "TEST-COMPANY",
			"custom_supplier": supplier,
		})

		with patch.object(frappe.db, "get_value", return_value=warehouse):
			PatternSetTransfer.validate_target_warehouse(transfer)

	def test_transfer_accepts_complete_pattern_set(self):
		self.validate_pattern_set("Transfer", "Complete", "Complete", "Approved")

	def test_transfer_rejects_non_approved_pattern_set(self):
		with patch.object(frappe, "throw", side_effect=ValueError):
			for status in ("Open", "Rejected"):
				with self.subTest(engineering_status=status), self.assertRaises(ValueError):
					self.validate_pattern_set("Transfer", "Complete", "Complete", status)

	def test_return_accepts_complete_pattern_sets_with_any_engineering_status(self):
		for status in ("Open", "Approved", "Rejected"):
			with self.subTest(engineering_status=status):
				self.validate_pattern_set("Return", "Complete", "Complete", status)

	def test_return_rejects_incomplete_pattern_set(self):
		with patch.object(frappe, "throw", side_effect=ValueError):
			with self.assertRaises(ValueError):
				self.validate_pattern_set("Return", "Incomplete", "Incomplete", "Open")

	def test_return_rejects_supplier_linked_target_warehouse(self):
		with patch.object(frappe, "throw", side_effect=ValueError):
			with self.assertRaises(ValueError):
				self.validate_target_warehouse("Return", "SUPPLIER-TEST")

	def test_return_accepts_unlinked_target_and_transfer_keeps_supplier_target(self):
		self.validate_target_warehouse("Return", "")
		self.validate_target_warehouse("Transfer", "SUPPLIER-TEST")
