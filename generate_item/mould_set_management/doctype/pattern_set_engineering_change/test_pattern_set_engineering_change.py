# Copyright (c) 2026, Finbyz and Contributors
# For license information, please see license.txt

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, call, patch

import frappe

from generate_item.mould_set_management.doctype.pattern_set_engineering_change.pattern_set_engineering_change import (
	PatternSetEngineeringChange,
)
from generate_item.mould_set_management.doctype.pattern_set_component_change.pattern_set_component_change import (
	PatternSetComponentChange,
)


class TestPatternSetEngineeringStatusPropagation(TestCase):
	def setUp(self):
		frappe.local.db = SimpleNamespace()
		self.impacted_sets = [SimpleNamespace(pattern_set="PS-1"), SimpleNamespace(pattern_set="PS-2")]

	def make_change(self, status="Open"):
		change = SimpleNamespace(status=status, impacted_pattern_sets=self.impacted_sets)
		change.db_set = lambda fieldname, value: setattr(change, fieldname, value)
		change.recalculate_impacted_pattern_sets = Mock()
		change.revert_legacy_component_approvals = Mock()
		change.propagate_engineering_status = (
			lambda value=None: PatternSetEngineeringChange.propagate_engineering_status(change, value)
		)
		return change

	def assert_propagated(self, sync_status, status):
		self.assertEqual(
			sync_status.call_args_list,
			[
				call(pattern_set.pattern_set, status) for pattern_set in self.impacted_sets
			],
		)

	def test_save_propagates_current_status(self):
		change = self.make_change("Rejected")
		with patch(
			"generate_item.mould_set_management.doctype.pattern_set_engineering_change.pattern_set_engineering_change.sync_pattern_set_engineering_status"
		) as sync_status:
			PatternSetEngineeringChange.on_update(change)

		self.assert_propagated(sync_status, "Rejected")

	def test_submit_sets_and_propagates_approved(self):
		change = self.make_change("Open")
		with patch(
			"generate_item.mould_set_management.doctype.pattern_set_engineering_change.pattern_set_engineering_change.sync_pattern_set_engineering_status"
		) as sync_status:
			PatternSetEngineeringChange.on_submit(change)

		self.assertEqual(change.status, "Approved")
		change.recalculate_impacted_pattern_sets.assert_called_once_with()
		self.assert_propagated(sync_status, "Approved")

	def test_update_after_submit_propagates_changed_status(self):
		change = self.make_change("Rejected")
		with patch(
			"generate_item.mould_set_management.doctype.pattern_set_engineering_change.pattern_set_engineering_change.sync_pattern_set_engineering_status"
		) as sync_status:
			PatternSetEngineeringChange.on_update_after_submit(change)

		self.assert_propagated(sync_status, "Rejected")

	def test_cancel_reopens_linked_pattern_sets(self):
		change = self.make_change("Approved")
		with patch(
			"generate_item.mould_set_management.doctype.pattern_set_engineering_change.pattern_set_engineering_change.sync_pattern_set_engineering_status"
		) as sync_status:
			PatternSetEngineeringChange.on_cancel(change)

		change.revert_legacy_component_approvals.assert_called_once_with()
		change.recalculate_impacted_pattern_sets.assert_called_once_with()
		self.assert_propagated(sync_status, "Open")


class TestPatternSetComponentChangeCancellation(TestCase):
	def setUp(self):
		frappe.local.db = SimpleNamespace()

	def test_cancel_recalculates_and_syncs_engineering_status(self):
		change = SimpleNamespace(pattern_set="PS-1", items=[])
		change.recalculate_affected_pattern_sets = (
			lambda previous_sets: PatternSetComponentChange.recalculate_affected_pattern_sets(change, previous_sets)
		)

		with (
			patch(
				"generate_item.mould_set_management.doctype.pattern_set_component_change.pattern_set_component_change.recalculate_pattern_set"
			) as recalculate,
			patch(
				"generate_item.mould_set_management.doctype.pattern_set_component_change.pattern_set_component_change.sync_pattern_set_engineering_status"
			) as sync_status,
			patch(
				"generate_item.mould_set_management.doctype.pattern_set_component_change.pattern_set_component_change.now_datetime",
				return_value="2026-01-01 00:00:00",
			),
		):
			PatternSetComponentChange.on_cancel(change)

		recalculate.assert_called_once_with("PS-1")
		sync_status.assert_called_once_with("PS-1")
