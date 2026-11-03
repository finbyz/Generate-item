# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def setup_mould_set_management():
	"""
	Sets up custom fields, roles, indexes, and configurations required by Pattern Set Management v1.0.
	"""
	print("Setting up Pattern Set Management v1.0...")

	# 1. Custom fields per Section 4.8
	custom_fields = {
		"Serial No": [
			{
				"fieldname": "custom_pattern_set",
				"label": "Pattern Set",
				"fieldtype": "Link",
				"options": "Pattern Set",
				"read_only": 1,
				"in_list_view": 1,
				"in_standard_filter": 1,
				"no_copy": 1,
				"insert_after": "warehouse",
				"module": "Mould Set Management",
			}
		],
		"Warehouse": [
			{
				"fieldname": "custom_supplier",
				"label": "Supplier",
				"fieldtype": "Link",
				"options": "Supplier",
				"insert_after": "warehouse_type",
				"module": "Mould Set Management",
			}
		],
		"Stock Entry": [
			{
				"fieldname": "custom_pattern_set",
				"label": "Pattern Set",
				"fieldtype": "Link",
				"options": "Pattern Set",
				"read_only": 1,
				"no_copy": 1,
				"insert_after": "to_warehouse",
				"module": "Mould Set Management",
			},
			{
				"fieldname": "custom_pattern_set_transfer",
				"label": "Pattern Set Transfer",
				"fieldtype": "Link",
				"options": "Pattern Set Transfer",
				"read_only": 1,
				"no_copy": 1,
				"insert_after": "custom_pattern_set",
				"module": "Mould Set Management",
			},
		],
		"Purchase Order": [
			{
				"fieldname": "mould_set_info",
				"label": "Pattern Sets Information",
				"fieldtype": "HTML",
				"insert_after": "supplier_warehouse",
			}
		],
	}
	create_custom_fields(custom_fields, update=True)
	print("Custom fields verified and created.")

	# 2. Roles per Section 10
	roles = ["Pattern Master", "Stores User", "Stores Manager"]
	for role_name in roles:
		if not frappe.db.exists("Role", role_name):
			try:
				r = frappe.new_doc("Role")
				r.role_name = role_name
				r.insert(ignore_permissions=True)
				print(f"Created role: {role_name}")
			except Exception as e:
				print(f"Error creating role {role_name}: {e}")

	# 3. Database Indexes per Section 13.2
	try:
		if frappe.db.table_exists("tabSerial No") and frappe.db.has_column("Serial No", "custom_pattern_set"):
			frappe.db.add_index("Serial No", ["custom_pattern_set"], "idx_serial_no_custom_pattern_set")
	except Exception:
		pass

	try:
		if frappe.db.table_exists("tabComponent Pairing Log"):
			if frappe.db.has_column("Component Pairing Log", "serial_no"):
				frappe.db.add_index("Component Pairing Log", ["serial_no"], "idx_cpl_serial_no")
			if frappe.db.has_column("Component Pairing Log", "pattern_set"):
				frappe.db.add_index("Component Pairing Log", ["pattern_set"], "idx_cpl_pattern_set")
	except Exception:
		pass

	# 4. Data Migration for existing records (Section 13.3)
	try:
		if frappe.db.table_exists("tabPattern Set Component"):
			if frappe.db.has_column("Pattern Set Component", "component_item") and frappe.db.has_column("Pattern Set Component", "item_code"):
				frappe.db.sql(
					"""
					UPDATE `tabPattern Set Component`
					SET item_code = component_item
					WHERE (item_code IS NULL OR item_code = '')
					AND component_item IS NOT NULL
					"""
				)
			if frappe.db.has_column("Pattern Set Component", "component_name") and frappe.db.has_column("Pattern Set Component", "item_name"):
				frappe.db.sql(
					"""
					UPDATE `tabPattern Set Component`
					SET item_name = component_name
					WHERE (item_name IS NULL OR item_name = '')
					AND component_name IS NOT NULL
					"""
				)

		if frappe.db.table_exists("tabPattern Set"):
			# Sync disabled flag
			if frappe.db.has_column("Pattern Set", "disable") and frappe.db.has_column("Pattern Set", "disabled"):
				frappe.db.sql(
					"""
					UPDATE `tabPattern Set`
					SET disabled = disable
					WHERE (disabled IS NULL OR disabled = 0)
					AND disable = 1
					"""
				)

			# Recalculate all pattern sets
			all_sets = frappe.get_all("Pattern Set", pluck="name")
			from generate_item.mould_set_management.pattern_set_utils import recalculate_pattern_set
			for ps_name in all_sets:
				recalculate_pattern_set(ps_name)
	except Exception as e:
		print(f"Error during data migration: {e}")

	print("Pattern Set Management setup completed successfully.")
