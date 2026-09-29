# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def setup_mould_set_management():
	"""
	Sets up custom fields and configurations required by Pattern Set / Mould Set Management.
	"""
	# 1. Custom fields for Supplier Warehouse tracking on Warehouse doctype
	custom_fields = {
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

	# 2. Ensure "Supplier" Warehouse Type exists
	if not frappe.db.exists("Warehouse Type", "Supplier"):
		try:
			doc = frappe.new_doc("Warehouse Type")
			doc.name = "Supplier"
			doc.insert(ignore_permissions=True)
		except Exception:
			pass

	# 3. Rename DocType Mould Set -> Pattern Set if Mould Set exists
	if frappe.db.exists("DocType", "Mould Set") and not frappe.db.exists("DocType", "Pattern Set"):
		try:
			frappe.rename_doc("DocType", "Mould Set", "Pattern Set", force=True)
			print("Renamed DocType 'Mould Set' to 'Pattern Set'")
		except Exception as e:
			print(f"Error renaming Mould Set: {e}")

	if frappe.db.exists("DocType", "Mould Set Component") and not frappe.db.exists("DocType", "Pattern Set Component"):
		try:
			frappe.rename_doc("DocType", "Mould Set Component", "Pattern Set Component", force=True)
			print("Renamed DocType 'Mould Set Component' to 'Pattern Set Component'")
		except Exception as e:
			print(f"Error renaming Mould Set Component: {e}")

	# If old DocType still exists alongside new, or tables need syncing:
	try:
		if frappe.db.table_exists("tabMould Set") and not frappe.db.table_exists("tabPattern Set"):
			frappe.db.sql("RENAME TABLE `tabMould Set` TO `tabPattern Set`")
			frappe.db.commit()
	except Exception:
		pass

	try:
		if frappe.db.table_exists("tabMould Set Component") and not frappe.db.table_exists("tabPattern Set Component"):
			frappe.db.sql("RENAME TABLE `tabMould Set Component` TO `tabPattern Set Component`")
			frappe.db.commit()
	except Exception:
		pass

	# Ensure pattern_set_name column is populated
	try:
		if frappe.db.table_exists("tabPattern Set"):
			if frappe.db.has_column("Pattern Set", "mould_set_name") and frappe.db.has_column("Pattern Set", "pattern_set_name"):
				frappe.db.sql(
					"""
					UPDATE `tabPattern Set`
					SET pattern_set_name = mould_set_name
					WHERE (pattern_set_name IS NULL OR pattern_set_name = '')
					AND mould_set_name IS NOT NULL
					"""
				)
				frappe.db.commit()
			elif frappe.db.has_column("Pattern Set", "module_set_name") and frappe.db.has_column("Pattern Set", "pattern_set_name"):
				frappe.db.sql(
					"""
					UPDATE `tabPattern Set`
					SET pattern_set_name = module_set_name
					WHERE (pattern_set_name IS NULL OR pattern_set_name = '')
					AND module_set_name IS NOT NULL
					"""
				)
				frappe.db.commit()
	except Exception:
		pass

	print("Pattern Set Management setup completed.")
