# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class IssueProgressUpdate(Document):
	def validate(self):
		if not self.posting_datetime:
			self.posting_datetime = frappe.utils.now_datetime()
		if not self.updated_by and frappe.session and frappe.session.user:
			self.updated_by = frappe.session.user
