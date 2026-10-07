# Copyright (c) 2026, Steelstrong and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import flt
from generate_item.mould_set_management.page.pattern_set_componen.pattern_set_componen import (
	get_pattern_set_component_availability,
	export_availability_excel,
	is_common_warehouse,
)


class TestPatternSetComponentAvailability(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.cleanup_records = []

	def tearDown(self):
		for doctype, name in reversed(self.cleanup_records):
			if frappe.db.exists(doctype, name):
				try:
					doc = frappe.get_doc(doctype, name)
					if doc.docstatus == 1:
						doc.cancel()
					doc.delete(ignore_permissions=True)
				except Exception:
					pass
		frappe.db.commit()

	def test_is_common_warehouse(self):
		# Test naming convention
		self.assertTrue(is_common_warehouse({"name": "Common Warehouse - SVIPL", "warehouse_name": "Common Warehouse"}))
		self.assertTrue(is_common_warehouse({"name": "Common Stores - SVIPL", "warehouse_name": "Common Stores"}))
		self.assertTrue(is_common_warehouse({"name": "Stores Central - SVIPL", "warehouse_type": "Central"}))
		self.assertFalse(is_common_warehouse({"name": "Sanand Finished Goods - SVIPL", "warehouse_name": "Sanand Finished Goods", "warehouse_type": "Finished Goods"}))

	def test_availability_structure_and_filters(self):
		# Call with no filters
		res = get_pattern_set_component_availability(show_zero_stock=1)
		self.assertIn("hierarchy", res)
		self.assertIn("summary", res)

		summary = res["summary"]
		self.assertIn("total_pattern_sets", summary)
		self.assertIn("total_components", summary)
		self.assertIn("total_warehouses", summary)
		self.assertIn("components_with_stock", summary)
		self.assertIn("components_without_stock", summary)
		self.assertIn("common_warehouse_stock", summary)

		if res["hierarchy"]:
			first_ps = res["hierarchy"][0]
			self.assertIn("pattern_set", first_ps)
			self.assertIn("components", first_ps)

			# Test pattern_set filter
			ps_res = get_pattern_set_component_availability(pattern_set=first_ps["pattern_set"])
			self.assertEqual(len(ps_res["hierarchy"]), 1)
			self.assertEqual(ps_res["hierarchy"][0]["pattern_set"], first_ps["pattern_set"])

			if first_ps["components"]:
				first_comp = first_ps["components"][0]
				self.assertIn("component_item", first_comp)
				self.assertIn("total_qty", first_comp)
				self.assertIn("warehouses", first_comp)

				# Test component_item filter
				comp_res = get_pattern_set_component_availability(component_item=first_comp["component_item"])
				self.assertTrue(len(comp_res["hierarchy"]) >= 1)

	def test_zero_stock_toggle(self):
		# Test show_zero_stock=0 vs show_zero_stock=1
		res_zero_included = get_pattern_set_component_availability(show_zero_stock=1)
		res_zero_excluded = get_pattern_set_component_availability(show_zero_stock=0)

		# When zero stock components are excluded, every component in hierarchy must have total_qty > 0
		for ps in res_zero_excluded["hierarchy"]:
			for c in ps["components"]:
				self.assertGreater(c["total_qty"], 0)

	def test_scenarios_comprehensive(self):
		company = frappe.db.get_single_value("Global Defaults", "default_company") or frappe.get_all("Company", limit=1, pluck="name")[0]
		items = frappe.get_all("Item", filters={"is_stock_item": 1, "has_variants": 0, "disabled": 0}, limit=3, pluck="name")
		if len(items) < 2:
			return

		comp_item_1 = items[0]
		comp_item_2 = items[1]

		# Fetch or create two warehouses: one common, one branch
		whs = frappe.get_all("Warehouse", filters={"is_group": 0, "company": company}, limit=2, pluck="name")
		wh1 = whs[0]
		wh2 = whs[1] if len(whs) > 1 else wh1

		# Create Test Pattern Set 1
		ps1 = frappe.new_doc("Pattern Set")
		ps1.type_of_valve = "Ball"
		ps1.size = "2\""
		ps1.set("class", "150#")
		ps1.type_of_pattern = "Aluminium"
		ps1.pattern_set_name = f"TEST-PS-AVAIL-1-{frappe.generate_hash(length=4)}"
		ps1.append("items", {
			"component_item": comp_item_1,
			"qty": 2.0,
		})
		ps1.append("items", {
			"component_item": comp_item_2,
			"qty": 1.0,
		})
		ps1.insert(ignore_permissions=True)
		ps1.submit()
		self.cleanup_records.append(("Pattern Set", ps1.name))

		# Create Test Pattern Set 2 sharing comp_item_1
		ps2 = frappe.new_doc("Pattern Set")
		ps2.type_of_valve = "Gate"
		ps2.size = "3\""
		ps2.set("class", "300#")
		ps2.type_of_pattern = "Mix"
		ps2.pattern_set_name = f"TEST-PS-AVAIL-2-{frappe.generate_hash(length=4)}"
		ps2.append("items", {
			"component_item": comp_item_1,
			"qty": 4.0,
		})
		ps2.insert(ignore_permissions=True)
		ps2.submit()
		self.cleanup_records.append(("Pattern Set", ps2.name))

		# Test 8: Pattern Set filter
		res_ps1 = get_pattern_set_component_availability(pattern_set=ps1.name)
		self.assertEqual(len(res_ps1["hierarchy"]), 1)
		self.assertEqual(res_ps1["hierarchy"][0]["pattern_set"], ps1.name)

		# Test 9: Component filter (shared comp_item_1 should match both ps1 and ps2)
		res_comp1 = get_pattern_set_component_availability(component_item=comp_item_1)
		matched_parents = [p["pattern_set"] for p in res_comp1["hierarchy"]]
		self.assertIn(ps1.name, matched_parents)
		self.assertIn(ps2.name, matched_parents)

		# Test 5: Duplicate Prevention
		# Verify that no component has duplicate warehouse rows
		for ps in res_comp1["hierarchy"]:
			for c in ps["components"]:
				wh_names = [w["warehouse"] for w in c["warehouses"]]
				self.assertEqual(len(wh_names), len(set(wh_names)), f"Duplicate warehouse found for {c['component_item']}")

		# Test 6: Zero Stock handling
		# When show_zero_stock=1, components with 0 stock exist and have has_stock = False
		has_zero_stock_comp = any(
			not c["has_stock"]
			for ps in res_ps1["hierarchy"]
			for c in ps["components"]
		)
		# Either has stock or reports 0 properly
		for c in res_ps1["hierarchy"][0]["components"]:
			if not c["has_stock"]:
				self.assertEqual(c["total_qty"], 0.0)

		# Test 7: Warehouse filter
		res_wh1 = get_pattern_set_component_availability(pattern_set=ps1.name, warehouse=wh1)
		for ps in res_wh1["hierarchy"]:
			for c in ps["components"]:
				for w in c["warehouses"]:
					self.assertEqual(w["warehouse"], wh1)

	def test_export_excel(self):
		export_availability_excel()
		self.assertIn("filecontent", frappe.response)
		self.assertEqual(frappe.response.get("type"), "binary")
		self.assertEqual(frappe.response.get("filename"), "Pattern_Set_Component_Warehouse_Availability.xlsx")
		self.assertGreater(len(frappe.response["filecontent"]), 0)
