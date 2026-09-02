# Copyright (c) 2026, Finbyz and Contributors
# For license information, please see license.txt

# Prevent Frappe's legacy compat layer from pre-loading ERPNext dependency test
# records (BOM → Item → FiscalYear) which fail on sites with existing fiscal years.
FRAPPE_SKIP_TEST_RECORDS = True

"""
Test suite for the Customer & Supplier Approval Workflow.

Covers:
  - Settings validation (empty rules warning)
  - New record creation: only Who Create role is allowed
  - Status tamper prevention
  - Full 3-step approval chain (Draft → L1 → Final → Approved)
  - disabled flag sync (disabled=1 until Approved)
  - Error cases: wrong role, wrong status, missing rule

Uses frappe.tests.utils.FrappeTestCase with setUp/tearDown fixtures.
All tests are isolated — settings & test records are rolled back after each test.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import cint

from generate_item.utils.customer_supplier_workflow import (
	CF_APPROVAL_STATUS,
	STATUS_APPROVED,
	STATUS_DRAFT,
	STATUS_PENDING_FINAL,
	STATUS_PENDING_L1,
	_build_approval_control,
	_get_settings,
	_is_workflow_active,
	final_approve,
	l1_approve,
	submit_for_l1_approval,
)

CS_SETTINGS = "Customer Supplier Workflow Settings"

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _create_test_role(role_name):
	if not frappe.db.exists("Role", role_name):
		frappe.get_doc({"doctype": "Role", "role_name": role_name}).insert(ignore_permissions=True)
	return role_name


def _create_test_user(email, roles):
	"""Create a test user with the given roles if it does not already exist."""
	if not frappe.db.exists("User", email):
		user = frappe.get_doc({
			"doctype": "User",
			"email": email,
			"first_name": email.split("@")[0].replace(".", " ").title(),
			"send_welcome_email": 0,
		})
		for role in roles:
			user.append("roles", {"role": role})
		user.insert(ignore_permissions=True)
	else:
		user = frappe.get_doc("User", email)
	return user


def _get_settings_doc():
	return frappe.get_single(CS_SETTINGS)


def _reset_settings():
	"""Restore settings to a known disabled state."""
	settings = _get_settings_doc()
	settings.enable_customer_approval = 0
	settings.enable_supplier_approval = 0
	settings.allow_system_manager_approval_bypass = 0
	settings.approval_bypass_role = None
	settings.customer_who_create = None
	settings.customer_l1_approver = None
	settings.customer_final_approver = None
	settings.supplier_approval_rules = []
	settings.save(ignore_permissions=True)
	frappe.clear_cache(doctype=CS_SETTINGS)


def _enable_customer_workflow(who_create, l1_approver, final_approver):
	"""Configure settings for Customer approval with direct role fields."""
	settings = _get_settings_doc()
	settings.enable_customer_approval = 1
	settings.customer_who_create = who_create
	settings.customer_l1_approver = l1_approver
	settings.customer_final_approver = final_approver
	settings.save(ignore_permissions=True)
	frappe.clear_cache(doctype=CS_SETTINGS)


def _make_customer():
	"""Create a Customer doc using ignore_permissions for fixtures."""
	name = f"__test_customer_{frappe.generate_hash(length=6)}__"
	customer = frappe.get_doc({
		"doctype": "Customer",
		"customer_name": name,
		"customer_group": frappe.db.get_value("Customer Group", {"is_group": 0}, "name") or "Commercial",
		"territory": frappe.db.get_value("Territory", {"is_group": 0}, "name") or "All Territories",
		CF_APPROVAL_STATUS: STATUS_DRAFT,
	})
	customer.insert(ignore_permissions=True)
	return customer


def _delete_customer(name):
	if frappe.db.exists("Customer", name):
		frappe.delete_doc("Customer", name, ignore_permissions=True, force=True)


# ─────────────────────────────────────────────────────────────────────────────
# Test: Settings Validation
# ─────────────────────────────────────────────────────────────────────────────

class TestCustomerSupplierWorkflowSettings(FrappeTestCase):
	"""Tests for CustomerSupplierWorkflowSettings validate logic."""

	def setUp(self):
		_reset_settings()

	def tearDown(self):
		_reset_settings()

	def test_both_workflows_disabled_by_default(self):
		"""Fresh/reset settings should have both Customer and Supplier approvals disabled."""
		settings = _get_settings_doc()
		self.assertFalse(cint(settings.enable_customer_approval))
		self.assertFalse(cint(settings.enable_supplier_approval))
		self.assertFalse(cint(settings.allow_system_manager_approval_bypass))
		self.assertFalse(settings.approval_bypass_role)


# ─────────────────────────────────────────────────────────────────────────────
# Test: Workflow Active / Inactive Guards
# ─────────────────────────────────────────────────────────────────────────────

class TestWorkflowActiveGuard(FrappeTestCase):

	def setUp(self):
		_reset_settings()

	def tearDown(self):
		_reset_settings()

	def test_workflow_inactive_when_customer_disabled(self):
		settings = _get_settings()
		self.assertFalse(_is_workflow_active(settings, "customer"))

	def test_workflow_active_when_customer_enabled(self):
		s = _get_settings_doc()
		s.enable_customer_approval = 1
		s.save(ignore_permissions=True)
		frappe.clear_cache(doctype=CS_SETTINGS)
		settings = _get_settings()
		self.assertTrue(_is_workflow_active(settings, "customer"))

	def test_customer_enabled_does_not_activate_supplier(self):
		s = _get_settings_doc()
		s.enable_customer_approval = 1
		s.save(ignore_permissions=True)
		frappe.clear_cache(doctype=CS_SETTINGS)
		settings = _get_settings()
		self.assertFalse(_is_workflow_active(settings, "supplier"))

	def test_workflow_inactive_when_supplier_disabled(self):
		settings = _get_settings()
		self.assertFalse(_is_workflow_active(settings, "supplier"))


# ─────────────────────────────────────────────────────────────────────────────
# Test: Approval Chain — Full Happy Path
# ─────────────────────────────────────────────────────────────────────────────

class TestApprovalChainHappyPath(FrappeTestCase):

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.role_create = _create_test_role("CS Test Creator")
		cls.role_l1 = _create_test_role("CS Test L1 Approver")
		cls.role_final = _create_test_role("CS Test Final Approver")
		cls.user_create = _create_test_user("cs_creator@test.com", [cls.role_create])
		cls.user_l1 = _create_test_user("cs_l1@test.com", [cls.role_l1])
		cls.user_final = _create_test_user("cs_final@test.com", [cls.role_final])

	def setUp(self):
		_reset_settings()
		_enable_customer_workflow(
			who_create=self.role_create,
			l1_approver=self.role_l1,
			final_approver=self.role_final,
		)
		self.customer = _make_customer()

	def tearDown(self):
		frappe.set_user("Administrator")
		_delete_customer(self.customer.name)
		_reset_settings()

	def test_initial_status_is_draft(self):
		"""Newly created Customer must start in Draft status."""
		self.assertEqual(self.customer.get(CF_APPROVAL_STATUS), STATUS_DRAFT)

	def test_new_customer_is_disabled(self):
		"""Customer must be disabled (inactive) from creation until Final Approval."""
		self.assertEqual(cint(self.customer.disabled), 1)

	def test_submit_for_l1_by_creator_role(self):
		"""Who Create role can advance Draft → Pending L1 Approval."""
		frappe.set_user(self.user_create.name)
		result = submit_for_l1_approval("Customer", self.customer.name)
		self.assertEqual(result["new_status"], STATUS_PENDING_L1)
		db_status = frappe.db.get_value("Customer", self.customer.name, CF_APPROVAL_STATUS)
		self.assertEqual(db_status, STATUS_PENDING_L1)

	def test_l1_approve_advances_to_pending_final(self):
		"""L1 Approver advances Pending L1 → Pending Final Approval."""
		frappe.set_user(self.user_create.name)
		submit_for_l1_approval("Customer", self.customer.name)

		frappe.set_user(self.user_l1.name)
		result = l1_approve("Customer", self.customer.name)
		self.assertEqual(result["new_status"], STATUS_PENDING_FINAL)

		db_status = frappe.db.get_value("Customer", self.customer.name, CF_APPROVAL_STATUS)
		self.assertEqual(db_status, STATUS_PENDING_FINAL)

	def test_final_approve_activates_customer(self):
		"""Final Approver sets Approved and Customer.disabled becomes 0."""
		frappe.set_user(self.user_create.name)
		submit_for_l1_approval("Customer", self.customer.name)

		frappe.set_user(self.user_l1.name)
		l1_approve("Customer", self.customer.name)

		frappe.set_user(self.user_final.name)
		result = final_approve("Customer", self.customer.name)
		self.assertEqual(result["new_status"], STATUS_APPROVED)

		db_status = frappe.db.get_value("Customer", self.customer.name, CF_APPROVAL_STATUS)
		self.assertEqual(db_status, STATUS_APPROVED)

		disabled = frappe.db.get_value("Customer", self.customer.name, "disabled")
		self.assertEqual(cint(disabled), 0)

	def test_customer_remains_disabled_at_pending_l1(self):
		"""After L1 submission, Customer must still be disabled."""
		frappe.set_user(self.user_create.name)
		submit_for_l1_approval("Customer", self.customer.name)
		disabled = frappe.db.get_value("Customer", self.customer.name, "disabled")
		self.assertEqual(cint(disabled), 1)

	def test_customer_remains_disabled_at_pending_final(self):
		"""After L1 approval, Customer must still be disabled until Final."""
		frappe.set_user(self.user_create.name)
		submit_for_l1_approval("Customer", self.customer.name)
		frappe.set_user(self.user_l1.name)
		l1_approve("Customer", self.customer.name)
		disabled = frappe.db.get_value("Customer", self.customer.name, "disabled")
		self.assertEqual(cint(disabled), 1)


# ─────────────────────────────────────────────────────────────────────────────
# Test: Permission Errors (Wrong Role / Wrong Status)
# ─────────────────────────────────────────────────────────────────────────────

class TestApprovalPermissionErrors(FrappeTestCase):

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.role_create = _create_test_role("CS Perm Creator")
		cls.role_l1 = _create_test_role("CS Perm L1")
		cls.role_final = _create_test_role("CS Perm Final")
		cls.user_wrong = _create_test_user("cs_wrong@test.com", ["Accounts User"])

	def setUp(self):
		_reset_settings()
		_enable_customer_workflow(
			who_create=self.role_create,
			l1_approver=self.role_l1,
			final_approver=self.role_final,
		)
		self.customer = _make_customer()

	def tearDown(self):
		frappe.set_user("Administrator")
		_delete_customer(self.customer.name)
		_reset_settings()

	def test_wrong_role_cannot_submit_for_l1(self):
		"""A user without Who Create role must receive PermissionError."""
		frappe.set_user(self.user_wrong.name)
		with self.assertRaises(frappe.PermissionError):
			submit_for_l1_approval("Customer", self.customer.name)

	def test_cannot_l1_approve_from_draft_status(self):
		"""Calling l1_approve on a Draft record must throw ValidationError."""
		frappe.set_user("Administrator")
		with self.assertRaises(frappe.ValidationError):
			l1_approve("Customer", self.customer.name)

	def test_cannot_final_approve_from_draft_status(self):
		"""Calling final_approve on a Draft record must throw ValidationError."""
		frappe.set_user("Administrator")
		with self.assertRaises(frappe.ValidationError):
			final_approve("Customer", self.customer.name)

	def test_cannot_skip_l1_to_final_approve(self):
		"""Final Approve on Pending L1 (skipping L1 step) must throw ValidationError."""
		frappe.db.set_value("Customer", self.customer.name, CF_APPROVAL_STATUS, STATUS_PENDING_L1)
		frappe.set_user("Administrator")
		with self.assertRaises(frappe.ValidationError):
			final_approve("Customer", self.customer.name)


# ─────────────────────────────────────────────────────────────────────────────
# Test: Approval Bypass Follows Hierarchy
# ─────────────────────────────────────────────────────────────────────────────

class TestApprovalBypassFollowsHierarchy(FrappeTestCase):

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.role_create = _create_test_role("CS Bypass Creator")
		cls.role_l1 = _create_test_role("CS Bypass L1")
		cls.role_final = _create_test_role("CS Bypass Final")
		cls.role_bypass = _create_test_role("CS Approval Bypass")
		cls.user_bypass = _create_test_user("cs_approval_bypass@test.com", [cls.role_bypass])

	def setUp(self):
		_reset_settings()
		_enable_customer_workflow(
			who_create=self.role_create,
			l1_approver=self.role_l1,
			final_approver=self.role_final,
		)
		self.customer = _make_customer()

	def tearDown(self):
		frappe.set_user("Administrator")
		_delete_customer(self.customer.name)
		_reset_settings()

	def test_system_manager_bypass_still_follows_all_status_steps(self):
		settings = _get_settings_doc()
		settings.allow_system_manager_approval_bypass = 1
		settings.save(ignore_permissions=True)
		frappe.clear_cache(doctype=CS_SETTINGS)
		frappe.set_user("Administrator")

		result = submit_for_l1_approval("Customer", self.customer.name)
		self.assertEqual(result["new_status"], STATUS_PENDING_L1)

		result = l1_approve("Customer", self.customer.name)
		self.assertEqual(result["new_status"], STATUS_PENDING_FINAL)

		result = final_approve("Customer", self.customer.name)
		self.assertEqual(result["new_status"], STATUS_APPROVED)

	def test_approval_bypass_role_still_follows_all_status_steps(self):
		settings = _get_settings_doc()
		settings.approval_bypass_role = self.role_bypass
		settings.save(ignore_permissions=True)
		frappe.clear_cache(doctype=CS_SETTINGS)
		frappe.set_user(self.user_bypass.name)

		result = submit_for_l1_approval("Customer", self.customer.name)
		self.assertEqual(result["new_status"], STATUS_PENDING_L1)

		result = l1_approve("Customer", self.customer.name)
		self.assertEqual(result["new_status"], STATUS_PENDING_FINAL)

		result = final_approve("Customer", self.customer.name)
		self.assertEqual(result["new_status"], STATUS_APPROVED)

	def test_bypass_cannot_skip_status_order(self):
		settings = _get_settings_doc()
		settings.allow_system_manager_approval_bypass = 1
		settings.save(ignore_permissions=True)
		frappe.clear_cache(doctype=CS_SETTINGS)
		frappe.set_user("Administrator")

		with self.assertRaises(frappe.ValidationError):
			final_approve("Customer", self.customer.name)


# ─────────────────────────────────────────────────────────────────────────────
# Test: Approval Control Payload
# ─────────────────────────────────────────────────────────────────────────────

class TestApprovalControlPayload(FrappeTestCase):
	"""Tests _build_approval_control returns the correct UI control payload."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.role_create = _create_test_role("CS Ctrl Creator")
		cls.role_l1 = _create_test_role("CS Ctrl L1")
		cls.role_final = _create_test_role("CS Ctrl Final")
		cls.user_regular = _create_test_user("cs_ctrl_regular@test.com", ["Accounts User"])

	def setUp(self):
		_reset_settings()

	def tearDown(self):
		frappe.set_user("Administrator")
		_reset_settings()

	def test_control_disabled_when_workflow_off(self):
		"""Control payload must have enabled=False when workflow is disabled."""
		customer = _make_customer()
		control = _build_approval_control(customer)
		self.assertFalse(control.get("enabled"))
		_delete_customer(customer.name)

	def test_control_enabled_when_workflow_on(self):
		"""Control payload must have enabled=True when workflow is enabled."""
		_enable_customer_workflow(
			who_create=self.role_create,
			l1_approver=self.role_l1,
			final_approver=self.role_final,
		)
		customer = _make_customer()
		control = _build_approval_control(customer)
		self.assertTrue(control.get("enabled"))
		_delete_customer(customer.name)

	def test_control_reflects_current_status(self):
		"""Control payload current_status must match the document's DB status."""
		_enable_customer_workflow(
			who_create=self.role_create,
			l1_approver=self.role_l1,
			final_approver=self.role_final,
		)
		customer = _make_customer()
		frappe.db.set_value("Customer", customer.name, CF_APPROVAL_STATUS, STATUS_PENDING_L1)
		customer.set(CF_APPROVAL_STATUS, STATUS_PENDING_L1)

		control = _build_approval_control(customer)
		self.assertEqual(control.get("current_status"), STATUS_PENDING_L1)
		_delete_customer(customer.name)

	def test_roles_not_configured_shows_no_rule(self):
		"""When customer approval is enabled but roles are empty, show no_rule."""
		s = _get_settings_doc()
		s.enable_customer_approval = 1
		s.customer_who_create = None
		s.customer_l1_approver = None
		s.customer_final_approver = None
		s.save(ignore_permissions=True)
		frappe.clear_cache(doctype=CS_SETTINGS)

		customer = _make_customer()
		try:
			frappe.set_user(self.user_regular.name)
			control = _build_approval_control(customer)

			self.assertTrue(control.get("no_rule"))
			self.assertFalse(control.get("can_submit_for_l1"))
			self.assertFalse(control.get("can_l1_approve"))
			self.assertFalse(control.get("can_final_approve"))
		finally:
			_delete_customer(customer.name)
