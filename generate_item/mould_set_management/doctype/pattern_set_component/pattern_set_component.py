# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class PatternSetComponent(Document):
	def validate(self):
		if not self.item_code and self.component_item:
			self.item_code = self.component_item
		if not self.component_item and self.item_code:
			self.component_item = self.item_code
		if not self.item_name and self.component_name:
			self.item_name = self.component_name
		if not self.component_name and self.item_name:
			self.component_name = self.item_name
