# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import random_string, nowdate
from generate_item.mould_set_management.pattern_set_utils import (
	get_pattern_set_slots_and_serials,
	recalculate_pattern_set,
)
from generate_item.mould_set_management.report.pairing_consistency_check.pairing_consistency_check import execute as run_consistency_check


class TestPatternSetAcceptance(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.flags.in_test = True
		cls.company = frappe.db.get_single_value("Global Defaults", "default_company") or frappe.get_all("Company", limit=1, pluck="name")[0]
		cls.cleanup_test_data()
		cls.setup_master_data()

	@classmethod
	def cleanup_test_data(cls):
		# Clean up any leftover test serials, pairing logs, and pattern sets
		test_serials = frappe.get_all("Serial No", filters={"name": ["like", "SN-TEST-COMP-%"]}, pluck="name")
		if test_serials:
			frappe.db.sql("DELETE FROM `tabSerial No` WHERE name IN %s", (tuple(test_serials),))
		# Clean up test pattern sets
		test_sets = frappe.get_all("Pattern Set", filters={"pattern_set_name": ["like", "GTV %"]}, pluck="name")
		if test_sets:
			frappe.db.sql("DELETE FROM `tabPattern Set Component` WHERE parent IN %s", (tuple(test_sets),))
			frappe.db.sql("DELETE FROM `tabPattern Set` WHERE name IN %s", (tuple(test_sets),))
		# Clean up orphaned pairing logs
		frappe.db.sql("DELETE FROM `tabComponent Pairing Log` WHERE item_code LIKE 'TEST-COMP-%'")
		# Clean up any remaining serials pointing to non-existent sets
		frappe.db.sql("""
			UPDATE `tabSerial No`
			SET custom_pattern_set = NULL
			WHERE custom_pattern_set IS NOT NULL
			  AND custom_pattern_set NOT IN (SELECT name FROM `tabPattern Set`)
		""")
		frappe.db.commit()

	@classmethod
	def setup_master_data(cls):
		# Create test suppliers
		for sup_name in ["Test Supplier A", "Test Supplier B"]:
			if not frappe.db.exists("Supplier", sup_name):
				s = frappe.new_doc("Supplier")
				s.supplier_name = sup_name
				s.supplier_group = "All Supplier Groups"
				s.insert(ignore_permissions=True)

		# Create test warehouses
		wh_data = [
			{"name": "Test Own Warehouse", "supplier": None},
			{"name": "Test Foundry A", "supplier": "Test Supplier A"},
			{"name": "Test Foundry B", "supplier": "Test Supplier B"},
		]
		cls.warehouses = {}
		for wh in wh_data:
			existing = frappe.get_all("Warehouse", filters={"warehouse_name": wh["name"], "company": cls.company}, pluck="name")
			if existing:
				w_name = existing[0]
				if wh["supplier"]:
					frappe.db.set_value("Warehouse", w_name, "custom_supplier", wh["supplier"])
			else:
				w = frappe.new_doc("Warehouse")
				w.warehouse_name = wh["name"]
				w.company = cls.company
				w.custom_supplier = wh["supplier"]
				w.insert(ignore_permissions=True)
				w_name = w.name
			cls.warehouses[wh["name"]] = w_name

		cls.own_wh = cls.warehouses["Test Own Warehouse"]
		cls.sup_a_wh = cls.warehouses["Test Foundry A"]
		cls.sup_b_wh = cls.warehouses["Test Foundry B"]

		# Ensure item codes exist
		cls.item_codes = []
		for i in range(1, 8):
			code = f"TEST-COMP-{i}"
			if not frappe.db.exists("Item", code):
				item = frappe.new_doc("Item")
				item.item_code = code
				item.item_name = f"Component Part {i}"
				item.item_group = "All Item Groups"
				item.stock_uom = "Nos"
				item.is_stock_item = 1
				item.has_serial_no = 1
				item.gst_hsn_code = "84604000"
				item.insert(ignore_permissions=True)
			cls.item_codes.append(code)

	def make_serial(self, item_code, warehouse):
		"""Helper to create and stock a serial number via Material Receipt"""
		sn_name = f"SN-{item_code}-{random_string(6).upper()}"
		se = frappe.new_doc("Stock Entry")
		se.purpose = "Material Receipt"
		se.stock_entry_type = "Material Receipt"
		se.company = self.company
		se.posting_date = nowdate()
		se.to_warehouse = warehouse
		branch = (
			frappe.db.get_value("Warehouse", warehouse, "branch")
			or "Sanand"
		)
		if frappe.db.has_column("Stock Entry", "branch"):
			se.branch = branch
		se.append("items", {
			"item_code": item_code,
			"qty": 1.0,
			"t_warehouse": warehouse,
			"serial_no": sn_name,
			"basic_rate": 100.0,
			"use_serial_batch_fields": 1,
		})
		se.insert(ignore_permissions=True)
		se.submit()
		return sn_name

	def test_01_save_set_with_serial_of_different_item_rejected(self):
		"""Test 1: Save a set with a serial of a different item in a row -> Rejected"""
		sn = self.make_serial(self.item_codes[1], self.own_wh)
		ps = frappe.new_doc("Pattern Set")
		ps.type_of_valve = "GTV"
		ps.size = '2"'
		ps.set("class", "150#")
		ps.type_of_pattern = "Aluminium"
		ps.pattern_length = "Short"
		ps.append("items", {
			"item_code": self.item_codes[0],  # Item 0
			"serial_no": sn,                  # Serial belongs to Item 1
			"is_optional": 0,
		})
		self.assertRaises(frappe.ValidationError, ps.save)

	def test_02_same_serial_in_two_rows_or_draft_sets_rejected(self):
		"""Test 2: Same serial in two rows, or in two draft sets -> Rejected"""
		sn = self.make_serial(self.item_codes[0], self.own_wh)
		# Part A: Two rows in same set
		ps = frappe.new_doc("Pattern Set")
		ps.type_of_valve = "GTV"
		ps.size = '3"'
		ps.set("class", "150#")
		ps.type_of_pattern = "Aluminium"
		ps.pattern_length = "Short"
		ps.append("items", {"item_code": self.item_codes[0], "serial_no": sn, "is_optional": 0})
		ps.append("items", {"item_code": self.item_codes[0], "serial_no": sn, "is_optional": 0})
		self.assertRaises(frappe.ValidationError, ps.save)

		# Part B: Serial in two draft sets
		ps1 = frappe.new_doc("Pattern Set")
		ps1.type_of_valve = "GTV"
		ps1.size = '3"'
		ps1.set("class", "300#")
		ps1.type_of_pattern = "Aluminium"
		ps1.pattern_length = "Short"
		ps1.append("items", {"item_code": self.item_codes[0], "serial_no": sn, "is_optional": 0})
		ps1.insert(ignore_permissions=True)

		ps2 = frappe.new_doc("Pattern Set")
		ps2.type_of_valve = "GTV"
		ps2.size = '3"'
		ps2.set("class", "600#")
		ps2.type_of_pattern = "Aluminium"
		ps2.pattern_length = "Short"
		ps2.append("items", {"item_code": self.item_codes[0], "serial_no": sn, "is_optional": 0})
		self.assertRaises(frappe.ValidationError, ps2.save)

	def test_03_submit_set_where_required_row_has_no_serial_is_incomplete(self):
		"""Test 3: Submit a set where one required row has no serial -> Submitted, status Incomplete"""
		ps = frappe.new_doc("Pattern Set")
		ps.type_of_valve = "GTV"
		ps.size = '4"'
		ps.set("class", "150#")
		ps.type_of_pattern = "Aluminium"
		ps.pattern_length = "Short"
		for i in range(5):
			ps.append("items", {
				"item_code": self.item_codes[i],
				"is_optional": 0
			})
		ps.insert(ignore_permissions=True)
		ps.submit()
		self.assertEqual(ps.docstatus, 1)
		ps.reload()
		self.assertEqual(ps.status, "Incomplete")

	def test_04_submit_set_where_only_optional_rows_lack_serial_is_complete(self):
		"""Test 4: Submit a set where only optional rows lack serial -> Status Complete"""
		serials = [self.make_serial(self.item_codes[i], self.own_wh) for i in range(5)]
		ps = frappe.new_doc("Pattern Set")
		ps.type_of_valve = "GTV"
		ps.size = '4"'
		ps.set("class", "300#")
		ps.type_of_pattern = "Aluminium"
		ps.pattern_length = "Short"
		# 5 required with serials
		for i in range(5):
			ps.append("items", {
				"item_code": self.item_codes[i],
				"serial_no": serials[i],
				"is_optional": 0,
			})
		# 2 optional without serials (open rows)
		ps.append("items", {"item_code": self.item_codes[5], "is_optional": 1})
		ps.append("items", {"item_code": self.item_codes[6], "is_optional": 1})
		ps.insert(ignore_permissions=True)
		ps.submit()
		ps.reload()
		self.assertEqual(ps.status, "Complete")
		self.assertEqual(ps.current_warehouse, self.own_wh)

	def test_05_submit_with_serials_from_two_warehouses_rejected(self):
		"""Test 5: Submit with serials from two warehouses -> Rejected, names serials and warehouses"""
		sn1 = self.make_serial(self.item_codes[0], self.own_wh)
		sn2 = self.make_serial(self.item_codes[1], self.sup_a_wh)
		ps = frappe.new_doc("Pattern Set")
		ps.type_of_valve = "GTV"
		ps.size = '5"'
		ps.set("class", "150#")
		ps.type_of_pattern = "Aluminium"
		ps.pattern_length = "Short"
		ps.append("items", {"item_code": self.item_codes[0], "serial_no": sn1, "is_optional": 0})
		ps.append("items", {"item_code": self.item_codes[1], "serial_no": sn2, "is_optional": 0})
		ps.insert(ignore_permissions=True)
		self.assertRaises(frappe.ValidationError, ps.submit)

	def test_06_after_submit_try_to_change_row_serial_rejected(self):
		"""Test 6: After submit, try to change a row's serial by hand -> Not possible"""
		sn1 = self.make_serial(self.item_codes[0], self.own_wh)
		sn2 = self.make_serial(self.item_codes[0], self.own_wh)
		ps = frappe.new_doc("Pattern Set")
		ps.type_of_valve = "GTV"
		ps.size = '6"'
		ps.set("class", "150#")
		ps.type_of_pattern = "Aluminium"
		ps.pattern_length = "Short"
		ps.append("items", {"item_code": self.item_codes[0], "serial_no": sn1, "is_optional": 0})
		ps.insert(ignore_permissions=True)
		ps.submit()

		# Try to change serial_no
		ps.items[0].serial_no = sn2
		self.assertRaises(frappe.ValidationError, ps.save)
		ps.reload()

	def test_07_after_submit_tick_is_optional_becomes_complete(self):
		"""Test 7: After submit, tick Is Optional on a blank required row -> Status becomes Complete on save"""
		ps = frappe.new_doc("Pattern Set")
		ps.type_of_valve = "GTV"
		ps.size = '7"'
		ps.set("class", "150#")
		ps.type_of_pattern = "Aluminium"
		ps.pattern_length = "Short"
		ps.append("items", {"item_code": self.item_codes[0], "is_optional": 0})
		ps.insert(ignore_permissions=True)
		ps.submit()
		ps.reload()
		self.assertEqual(ps.status, "Incomplete")

		# Change to optional
		ps.items[0].is_optional = 1
		ps.save()
		ps.reload()
		self.assertEqual(ps.status, "Complete")

	def test_08_after_submit_delete_row_rules(self):
		"""Test 8: After submit, delete a row that has a serial -> Rejected. Row with blank serial can be deleted."""
		sn = self.make_serial(self.item_codes[0], self.own_wh)
		ps = frappe.new_doc("Pattern Set")
		ps.type_of_valve = "GTV"
		ps.size = '8"'
		ps.set("class", "150#")
		ps.type_of_pattern = "Aluminium"
		ps.pattern_length = "Short"
		ps.append("items", {"item_code": self.item_codes[0], "serial_no": sn, "is_optional": 0})
		ps.append("items", {"item_code": self.item_codes[1], "is_optional": 1})  # blank open row
		ps.insert(ignore_permissions=True)
		ps.submit()
		ps.reload()

		# Try deleting row with serial
		ps_copy = frappe.get_doc("Pattern Set", ps.name)
		ps_copy.items = [r for r in ps_copy.items if not r.serial_no]
		self.assertRaises(frappe.ValidationError, ps_copy.save)

		# Deleting open row succeeds
		ps.reload()
		ps.items = [r for r in ps.items if r.serial_no]
		ps.save()
		ps.reload()
		self.assertEqual(len(ps.items), 1)

	def test_09_after_submit_add_new_row_allowed(self):
		"""Test 9: After submit, add a new row -> Allowed; row is open; serial blank"""
		ps = frappe.new_doc("Pattern Set")
		ps.type_of_valve = "GTV"
		ps.size = '9"'
		ps.set("class", "150#")
		ps.type_of_pattern = "Aluminium"
		ps.pattern_length = "Short"
		ps.append("items", {"item_code": self.item_codes[0], "is_optional": 1})
		ps.insert(ignore_permissions=True)
		ps.submit()

		# Add open row
		ps.append("items", {"item_code": self.item_codes[1], "is_optional": 1})
		ps.save()
		ps.reload()
		self.assertEqual(len(ps.items), 2)

	def test_10_attach_with_no_open_row_rejected(self):
		"""Test 10: Attach with no open row for the item -> Rejected with 'add a row first' message"""
		sn1 = self.make_serial(self.item_codes[0], self.own_wh)
		sn2 = self.make_serial(self.item_codes[0], self.own_wh)
		ps = frappe.new_doc("Pattern Set")
		ps.type_of_valve = "GTV"
		ps.size = '10"'
		ps.set("class", "150#")
		ps.type_of_pattern = "Aluminium"
		ps.pattern_length = "Short"
		ps.append("items", {"item_code": self.item_codes[0], "serial_no": sn1, "is_optional": 0})
		ps.insert(ignore_permissions=True)
		ps.submit()

		# Try to attach sn2 when there is no open row for item_codes[0]
		cc = frappe.new_doc("Pattern Set Component Change")
		cc.posting_date = nowdate()
		cc.pattern_set = ps.name
		cc.append("items", {"action": "Attach", "serial_no": sn2})
		self.assertRaises(frappe.ValidationError, cc.insert)

	def test_11_attach_serial_from_another_set(self):
		"""Test 11: Attach a serial from another set -> Previous Set auto-filled; old set row blank, old set status recalculated; new row filled."""
		sn = self.make_serial(self.item_codes[0], self.own_wh)
		# Set 1 with attached serial
		ps1 = frappe.new_doc("Pattern Set")
		ps1.type_of_valve = "GTV"
		ps1.size = '11"'
		ps1.set("class", "150#")
		ps1.type_of_pattern = "Aluminium"
		ps1.pattern_length = "Short"
		ps1.append("items", {"item_code": self.item_codes[0], "serial_no": sn, "is_optional": 0})
		ps1.insert(ignore_permissions=True)
		ps1.submit()
		ps1.reload()
		self.assertEqual(ps1.status, "Complete")

		# Set 2 with open row
		ps2 = frappe.new_doc("Pattern Set")
		ps2.type_of_valve = "GTV"
		ps2.size = '11"'
		ps2.set("class", "300#")
		ps2.type_of_pattern = "Aluminium"
		ps2.pattern_length = "Short"
		ps2.append("items", {"item_code": self.item_codes[0], "is_optional": 0})
		ps2.insert(ignore_permissions=True)
		ps2.submit()
		ps2.reload()
		self.assertEqual(ps2.status, "Incomplete")

		# Attach sn to Set 2
		cc = frappe.new_doc("Pattern Set Component Change")
		cc.posting_date = nowdate()
		cc.pattern_set = ps2.name
		cc.append("items", {"action": "Attach", "serial_no": sn})
		cc.insert(ignore_permissions=True)
		self.assertEqual(cc.items[0].previous_set, ps1.name)
		cc.submit()

		ps1.reload()
		ps2.reload()
		self.assertEqual(ps1.status, "Incomplete")
		self.assertFalse(ps1.items[0].serial_no)  # old row blanked
		self.assertEqual(ps2.status, "Complete")
		self.assertEqual(ps2.items[0].serial_no, sn)  # new row filled

	def test_12_attach_serial_from_different_warehouse_rejected(self):
		"""Test 12: Attach a serial from a different warehouse than the set -> Rejected"""
		sn1 = self.make_serial(self.item_codes[0], self.own_wh)
		sn2 = self.make_serial(self.item_codes[1], self.sup_a_wh)
		ps = frappe.new_doc("Pattern Set")
		ps.type_of_valve = "GTV"
		ps.size = '12"'
		ps.set("class", "150#")
		ps.type_of_pattern = "Aluminium"
		ps.pattern_length = "Short"
		ps.append("items", {"item_code": self.item_codes[0], "serial_no": sn1, "is_optional": 0})
		ps.append("items", {"item_code": self.item_codes[1], "is_optional": 0})  # open row
		ps.insert(ignore_permissions=True)
		ps.submit()

		cc = frappe.new_doc("Pattern Set Component Change")
		cc.posting_date = nowdate()
		cc.pattern_set = ps.name
		cc.append("items", {"action": "Attach", "serial_no": sn2})
		self.assertRaises(frappe.ValidationError, cc.insert)

	def test_13_detach_required_serial_becomes_incomplete(self):
		"""Test 13: Detach a required serial -> Serial free, row blank, set Incomplete"""
		sn = self.make_serial(self.item_codes[0], self.own_wh)
		ps = frappe.new_doc("Pattern Set")
		ps.type_of_valve = "GTV"
		ps.size = '13"'
		ps.set("class", "150#")
		ps.type_of_pattern = "Aluminium"
		ps.pattern_length = "Short"
		ps.append("items", {"item_code": self.item_codes[0], "serial_no": sn, "is_optional": 0})
		ps.insert(ignore_permissions=True)
		ps.submit()
		ps.reload()
		self.assertEqual(ps.status, "Complete")

		cc = frappe.new_doc("Pattern Set Component Change")
		cc.posting_date = nowdate()
		cc.pattern_set = ps.name
		cc.append("items", {"action": "Detach", "serial_no": sn})
		cc.insert(ignore_permissions=True)
		cc.submit()

		ps.reload()
		self.assertEqual(ps.status, "Incomplete")
		self.assertFalse(ps.items[0].serial_no)
		self.assertFalse(frappe.db.get_value("Serial No", sn, "custom_pattern_set"))

	def test_14_cancel_set_with_attached_serials_rejected(self):
		"""Test 14: Cancel a set that has attached serials -> Rejected"""
		sn = self.make_serial(self.item_codes[0], self.own_wh)
		ps = frappe.new_doc("Pattern Set")
		ps.type_of_valve = "GTV"
		ps.size = '14"'
		ps.set("class", "150#")
		ps.type_of_pattern = "Aluminium"
		ps.pattern_length = "Short"
		ps.append("items", {"item_code": self.item_codes[0], "serial_no": sn, "is_optional": 0})
		ps.insert(ignore_permissions=True)
		ps.submit()

		self.assertRaises(frappe.ValidationError, ps.cancel)

	def test_15_cancel_component_change_after_serial_moved_rejected(self):
		"""Test 15: Cancel a Component Change after the serial moved elsewhere -> Rejected, names the serial"""
		sn = self.make_serial(self.item_codes[0], self.own_wh)
		ps = frappe.new_doc("Pattern Set")
		ps.type_of_valve = "GTV"
		ps.size = '15"'
		ps.set("class", "150#")
		ps.type_of_pattern = "Aluminium"
		ps.pattern_length = "Short"
		ps.append("items", {"item_code": self.item_codes[0], "is_optional": 0})
		ps.insert(ignore_permissions=True)
		ps.submit()

		cc = frappe.new_doc("Pattern Set Component Change")
		cc.posting_date = nowdate()
		cc.pattern_set = ps.name
		cc.append("items", {"action": "Attach", "serial_no": sn})
		cc.insert(ignore_permissions=True)
		cc.submit()

		# Simulate moving the serial to another warehouse outside pattern set
		frappe.db.set_value("Serial No", sn, "warehouse", self.sup_a_wh)

		# Cancelling CC should now be rejected
		self.assertRaises(frappe.ValidationError, cc.cancel)

		# Restore
		frappe.db.set_value("Serial No", sn, "warehouse", self.own_wh)

	def test_16_transfer_set_to_supplier_warehouse(self):
		"""Test 16: Transfer set to supplier warehouse -> Stock Entry auto-created, location & supplier updated, type correct"""
		serials = [self.make_serial(self.item_codes[i], self.own_wh) for i in range(3)]
		ps = frappe.new_doc("Pattern Set")
		ps.type_of_valve = "GTV"
		ps.size = '16"'
		ps.set("class", "150#")
		ps.type_of_pattern = "Aluminium"
		ps.pattern_length = "Short"
		for i in range(3):
			ps.append("items", {"item_code": self.item_codes[i], "serial_no": serials[i], "is_optional": 0})
		ps.insert(ignore_permissions=True)
		ps.submit()

		pst = frappe.new_doc("Pattern Set Transfer")
		pst.posting_date = nowdate()
		pst.company = self.company
		pst.pattern_set = ps.name
		pst.purpose = "Job Work"
		pst.target_warehouse = self.sup_a_wh
		pst.insert(ignore_permissions=True)
		self.assertEqual(pst.transfer_type, "Company to Supplier")
		pst.submit()

		self.assertTrue(bool(pst.stock_entry))
		ps.reload()
		self.assertEqual(ps.current_warehouse, self.sup_a_wh)
		self.assertEqual(ps.current_supplier, "Test Supplier A")

	def test_17_try_untick_required_row_rejected(self):
		"""Test 17: Try to untick a required row in a transfer -> Not possible / Rejected"""
		sn = self.make_serial(self.item_codes[0], self.own_wh)
		ps = frappe.new_doc("Pattern Set")
		ps.type_of_valve = "GTV"
		ps.size = '17"'
		ps.set("class", "150#")
		ps.type_of_pattern = "Aluminium"
		ps.pattern_length = "Short"
		ps.append("items", {"item_code": self.item_codes[0], "serial_no": sn, "is_optional": 0})
		ps.insert(ignore_permissions=True)
		ps.submit()

		pst = frappe.new_doc("Pattern Set Transfer")
		pst.posting_date = nowdate()
		pst.company = self.company
		pst.pattern_set = ps.name
		pst.purpose = "Job Work"
		pst.target_warehouse = self.sup_a_wh
		pst.load_components_from_pattern_set()
		pst.items[0].include = 0
		self.assertRaises(frappe.ValidationError, pst.insert)

	def test_18_untick_optional_row_detaches_it_and_moves_others(self):
		"""Test 18: Untick one optional row and submit -> Auto Component Change; serial detached and stays at source; rows blank; others moved"""
		sn1 = self.make_serial(self.item_codes[0], self.own_wh)
		sn2 = self.make_serial(self.item_codes[1], self.own_wh)
		ps = frappe.new_doc("Pattern Set")
		ps.type_of_valve = "GTV"
		ps.size = '18"'
		ps.set("class", "150#")
		ps.type_of_pattern = "Aluminium"
		ps.pattern_length = "Short"
		ps.append("items", {"item_code": self.item_codes[0], "serial_no": sn1, "is_optional": 0})
		ps.append("items", {"item_code": self.item_codes[1], "serial_no": sn2, "is_optional": 1})
		ps.insert(ignore_permissions=True)
		ps.submit()

		pst = frappe.new_doc("Pattern Set Transfer")
		pst.posting_date = nowdate()
		pst.company = self.company
		pst.pattern_set = ps.name
		pst.purpose = "Job Work"
		pst.target_warehouse = self.sup_a_wh
		pst.load_components_from_pattern_set()
		# Untick optional row (sn2)
		for item in pst.items:
			if item.serial_no == sn2:
				item.include = 0
		pst.insert(ignore_permissions=True)
		pst.submit()

		self.assertTrue(bool(pst.component_change))
		# sn2 is now detached and still in own_wh
		self.assertFalse(frappe.db.get_value("Serial No", sn2, "custom_pattern_set"))
		self.assertEqual(frappe.db.get_value("Serial No", sn2, "warehouse"), self.own_wh)

		# sn1 moved to sup_a_wh
		self.assertEqual(frappe.db.get_value("Serial No", sn1, "warehouse"), self.sup_a_wh)
		ps.reload()
		self.assertEqual(ps.current_warehouse, self.sup_a_wh)

	def test_19_manual_stock_entry_moving_attached_serial_blocked(self):
		"""Test 19: Create a manual Stock Entry moving one attached serial -> Blocked"""
		sn = self.make_serial(self.item_codes[0], self.own_wh)
		ps = frappe.new_doc("Pattern Set")
		ps.type_of_valve = "GTV"
		ps.size = '19"'
		ps.set("class", "150#")
		ps.type_of_pattern = "Aluminium"
		ps.pattern_length = "Short"
		ps.append("items", {"item_code": self.item_codes[0], "serial_no": sn, "is_optional": 0})
		ps.insert(ignore_permissions=True)
		ps.submit()

		# Attempt manual Stock Entry
		se = frappe.new_doc("Stock Entry")
		se.purpose = "Material Transfer"
		se.stock_entry_type = "Material Transfer"
		se.company = self.company
		se.posting_date = nowdate()
		se.from_warehouse = self.own_wh
		se.to_warehouse = self.sup_a_wh
		se.append("items", {
			"item_code": self.item_codes[0],
			"qty": 1.0,
			"s_warehouse": self.own_wh,
			"t_warehouse": self.sup_a_wh,
			"serial_no": sn,
			"use_serial_batch_fields": 1,
		})
		self.assertRaises(frappe.ValidationError, se.insert)

	def test_20_manual_stock_entry_moving_free_serial_allowed(self):
		"""Test 20: Create a manual Stock Entry moving a free serial -> Allowed"""
		sn = self.make_serial(self.item_codes[0], self.own_wh)
		se = frappe.new_doc("Stock Entry")
		se.purpose = "Material Transfer"
		se.stock_entry_type = "Material Transfer"
		se.company = self.company
		se.posting_date = nowdate()
		se.from_warehouse = self.own_wh
		se.to_warehouse = self.sup_a_wh
		branch = (
			frappe.db.get_value("Warehouse", self.own_wh, "branch")
			or "Sanand"
		)
		if frappe.db.has_column("Stock Entry", "branch"):
			se.branch = branch
		se.append("items", {
			"item_code": self.item_codes[0],
			"qty": 1.0,
			"s_warehouse": self.own_wh,
			"t_warehouse": self.sup_a_wh,
			"serial_no": sn,
			"use_serial_batch_fields": 1,
		})
		se.insert(ignore_permissions=True)
		se.submit()
		self.assertEqual(se.docstatus, 1)
		self.assertEqual(frappe.db.get_value("Serial No", sn, "warehouse"), self.sup_a_wh)

	def test_21_force_stock_entry_failure_rolls_back_transfer(self):
		"""Test 21: Force a Stock Entry failure during a transfer -> Whole transfer rolled back, no Component Change left behind"""
		sn1 = self.make_serial(self.item_codes[0], self.own_wh)
		sn2 = self.make_serial(self.item_codes[1], self.own_wh)
		ps = frappe.new_doc("Pattern Set")
		ps.type_of_valve = "GTV"
		ps.size = '21"'
		ps.set("class", "150#")
		ps.type_of_pattern = "Aluminium"
		ps.pattern_length = "Short"
		ps.append("items", {"item_code": self.item_codes[0], "serial_no": sn1, "is_optional": 0})
		ps.append("items", {"item_code": self.item_codes[1], "serial_no": sn2, "is_optional": 1})
		ps.insert(ignore_permissions=True)
		ps.submit()

		pst = frappe.new_doc("Pattern Set Transfer")
		pst.posting_date = nowdate()
		pst.company = self.company
		pst.pattern_set = ps.name
		pst.purpose = "Job Work"
		pst.target_warehouse = self.sup_a_wh
		pst.load_components_from_pattern_set()
		for item in pst.items:
			if item.serial_no == sn2:
				item.include = 0
		pst.insert(ignore_permissions=True)

		# Sabotage Stock Entry insertion by temporarily making company invalid on submit
		pst.company = "NonExistentCompany"
		self.assertRaises(Exception, pst.submit)

		# Ensure optional serial was restored and is still attached
		ps.reload()
		self.assertEqual(frappe.db.get_value("Serial No", sn2, "custom_pattern_set"), ps.name)

	def test_22_cancel_older_transfer_when_newer_exists_rejected(self):
		"""Test 22: Cancel an older transfer when a newer one exists -> Rejected, names the newer one"""
		sn = self.make_serial(self.item_codes[0], self.own_wh)
		ps = frappe.new_doc("Pattern Set")
		ps.type_of_valve = "GTV"
		ps.size = '22"'
		ps.set("class", "150#")
		ps.type_of_pattern = "Aluminium"
		ps.pattern_length = "Short"
		ps.append("items", {"item_code": self.item_codes[0], "serial_no": sn, "is_optional": 0})
		ps.insert(ignore_permissions=True)
		ps.submit()

		# Transfer 1: Own -> Sup A
		pst1 = frappe.new_doc("Pattern Set Transfer")
		pst1.posting_date = nowdate()
		pst1.company = self.company
		pst1.pattern_set = ps.name
		pst1.purpose = "Job Work"
		pst1.target_warehouse = self.sup_a_wh
		pst1.insert(ignore_permissions=True)
		pst1.submit()

		# Transfer 2: Sup A -> Sup B
		pst2 = frappe.new_doc("Pattern Set Transfer")
		pst2.posting_date = nowdate()
		pst2.company = self.company
		pst2.pattern_set = ps.name
		pst2.purpose = "Job Work"
		pst2.target_warehouse = self.sup_b_wh
		pst2.insert(ignore_permissions=True)
		pst2.submit()

		# Cancelling transfer 1 should be rejected
		self.assertRaises(frappe.ValidationError, pst1.cancel)

	def test_23_cancel_latest_transfer_succeeds(self):
		"""Test 23: Cancel the latest transfer -> Stock Entry and Component Change cancelled; set at source; left-behind serials back in their rows"""
		sn1 = self.make_serial(self.item_codes[0], self.own_wh)
		sn2 = self.make_serial(self.item_codes[1], self.own_wh)
		ps = frappe.new_doc("Pattern Set")
		ps.type_of_valve = "GTV"
		ps.size = '23"'
		ps.set("class", "150#")
		ps.type_of_pattern = "Aluminium"
		ps.pattern_length = "Short"
		ps.append("items", {"item_code": self.item_codes[0], "serial_no": sn1, "is_optional": 0})
		ps.append("items", {"item_code": self.item_codes[1], "serial_no": sn2, "is_optional": 1})
		ps.insert(ignore_permissions=True)
		ps.submit()

		pst = frappe.new_doc("Pattern Set Transfer")
		pst.posting_date = nowdate()
		pst.company = self.company
		pst.pattern_set = ps.name
		pst.purpose = "Job Work"
		pst.target_warehouse = self.sup_a_wh
		pst.load_components_from_pattern_set()
		for item in pst.items:
			if item.serial_no == sn2:
				item.include = 0  # leave sn2 behind
		pst.insert(ignore_permissions=True)
		pst.submit()

		# Cancel latest transfer
		pst.cancel()

		# Verification: Stock Entry cancelled
		se = frappe.get_doc("Stock Entry", pst.stock_entry)
		self.assertEqual(se.docstatus, 2)

		# Auto Component Change cancelled
		cc = frappe.get_doc("Pattern Set Component Change", pst.component_change)
		self.assertEqual(cc.docstatus, 2)

		# Both serials back at own_wh and attached
		ps.reload()
		self.assertEqual(ps.current_warehouse, self.own_wh)
		self.assertEqual(frappe.db.get_value("Serial No", sn1, "warehouse"), self.own_wh)
		self.assertEqual(frappe.db.get_value("Serial No", sn2, "warehouse"), self.own_wh)
		self.assertEqual(frappe.db.get_value("Serial No", sn1, "custom_pattern_set"), ps.name)
		self.assertEqual(frappe.db.get_value("Serial No", sn2, "custom_pattern_set"), ps.name)

	def test_24_two_transfers_same_set_blocked(self):
		"""Test 24: Two users submit transfers for the same set together -> Only one succeeds"""
		sn = self.make_serial(self.item_codes[0], self.own_wh)
		ps = frappe.new_doc("Pattern Set")
		ps.type_of_valve = "GTV"
		ps.size = '24"'
		ps.set("class", "150#")
		ps.type_of_pattern = "Aluminium"
		ps.pattern_length = "Short"
		ps.append("items", {"item_code": self.item_codes[0], "serial_no": sn, "is_optional": 0})
		ps.insert(ignore_permissions=True)
		ps.submit()

		pst1 = frappe.new_doc("Pattern Set Transfer")
		pst1.posting_date = nowdate()
		pst1.company = self.company
		pst1.pattern_set = ps.name
		pst1.purpose = "Job Work"
		pst1.target_warehouse = self.sup_a_wh
		pst1.insert(ignore_permissions=True)

		pst2 = frappe.new_doc("Pattern Set Transfer")
		pst2.posting_date = nowdate()
		pst2.company = self.company
		pst2.pattern_set = ps.name
		pst2.purpose = "Job Work"
		pst2.target_warehouse = self.sup_b_wh
		pst2.insert(ignore_permissions=True)

		# Submit first transfer
		pst1.submit()

		# Second transfer submission must fail because source warehouse/serials have moved
		self.assertRaises(frappe.ValidationError, pst2.submit)

	def test_25_pairing_consistency_check_empty(self):
		"""Test 25: Open Consistency Check after all tests -> Empty"""
		columns, data = run_consistency_check()
		self.assertEqual(len(data), 0, f"Found inconsistencies: {data}")
