# Copyright (c) 2025, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class CustomItemAttribute(Document):
	def validate(self):
		# Convert to int safely
		try:
			code_length = int(self.code_length)
		except Exception:
			frappe.throw("Code Length must be a number")

		if code_length <= 0:
			frappe.throw("Please set a valid Code Length (greater than 0)")

		# Row-level validation
		for idx, row in enumerate(self.logic_table, start=1):
			if not row.code:
				frappe.throw(f"Row #{idx}: Code is mandatory")

			if len(row.code) != code_length:
				frappe.throw(
					f"Row #{idx}: Code '{row.code}' must be exactly {code_length} characters long"
				)
		self.validate_duplicate_fields()

	def validate_duplicate_fields(self):
		fields_to_check = {
			"code": "Code",
			"item_short_description": "Item Short Description",
			"item_long_description": "Item Long Description",
			"parent_iitem": "Parent Item",   # <-- FIXED: use parent_iitem (double 'ii')
		}

		for fieldname, label in fields_to_check.items():
			seen = {}
			for idx, row in enumerate(self.logic_table or [], start=1):
				value = (getattr(row, fieldname) or "").strip().lower()
				if not value:   # ignore blanks
					continue

				if value in seen:
					frappe.throw(
						f"Row #{idx}: {label} '{getattr(row, fieldname)}' "
						f"is already used in Row #{seen[value]}"
					)

				seen[value] = idx
