# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document

from generate_item.generate_item.modification_task_utils.modification_task_notification import send_modification_task_notification
class ModificationTask(Document):

	def on_submit(self):
		pass
		# send_modification_task_notification(self)
		
