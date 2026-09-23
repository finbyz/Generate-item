# Copyright (c) 2026, Finbyz and Contributors
# See license.txt

import unittest
import frappe
from frappe.utils import cint


class TestValveTesting(unittest.TestCase):
	"""
	Integration tests for ValveTesting naming series deletion behavior.
	"""

	def setUp(self):
		frappe.set_user("Administrator")
		frappe.publish_realtime = lambda *args, **kwargs: None
		self.test_branch = "Sanand"  # series: VTES.fiscal.#####
		self.naming_series = "VTES.fiscal.#####"
		self.created_docs = []

	def tearDown(self):
		self.cleanup_records()

	def cleanup_records(self):
		for name in getattr(self, "created_docs", []):
			if frappe.db.exists("Valve Testing", name):
				docstatus = frappe.db.get_value("Valve Testing", name, "docstatus")
				if docstatus == 1:
					try:
						doc = frappe.get_doc("Valve Testing", name)
						doc.cancel()
					except Exception:
						pass
				try:
					frappe.delete_doc("Valve Testing", name, force=1, delete_permanently=True)
				except Exception:
					pass
		self.created_docs = []

	def _create_doc(self, submit=False):
		doc = frappe.new_doc("Valve Testing")
		doc.branch = self.test_branch
		doc.naming_series = self.naming_series
		doc.testing_phase = "Pre Testing"
		doc.insert()
		self.created_docs.append(doc.name)
		if submit:
			doc.submit()
		return doc

	def _get_number(self, doc_name):
		# Extracts the trailing integer from document name
		return cint("".join(filter(str.isdigit, doc_name.split("-")[0][-5:])))

	def test_1_delete_latest_reuses_number(self):
		"""
		Test 1:
		Create 001, 002, 003 -> Delete 003 -> Create new -> Expected 003
		"""
		d1 = self._create_doc()
		d2 = self._create_doc()
		d3 = self._create_doc()

		num1 = self._get_number(d1.name)
		num2 = self._get_number(d2.name)
		num3 = self._get_number(d3.name)

		self.assertEqual(num2, num1 + 1)
		self.assertEqual(num3, num2 + 1)

		d3_name = d3.name
		frappe.delete_doc("Valve Testing", d3_name)
		self.created_docs.remove(d3_name)

		d_new = self._create_doc()
		self.assertEqual(d_new.name, d3_name)
		self.assertEqual(self._get_number(d_new.name), num3)

	def test_2_delete_non_latest_does_not_reduce_counter(self):
		"""
		Test 2:
		Create 001, 002, 003 -> Delete 002 -> Create new -> Expected 004
		"""
		d1 = self._create_doc()
		d2 = self._create_doc()
		d3 = self._create_doc()

		num3 = self._get_number(d3.name)

		# Delete middle document
		frappe.delete_doc("Valve Testing", d2.name)
		self.created_docs.remove(d2.name)

		d_new = self._create_doc()
		self.assertEqual(self._get_number(d_new.name), num3 + 1)

	def test_3_cancel_does_not_release_number(self):
		"""
		Test 3:
		Create 001, 002, 003 (Submitted) -> Cancel 003 -> Create new -> Expected 004
		"""
		d1 = self._create_doc(submit=True)
		d2 = self._create_doc(submit=True)
		d3 = self._create_doc(submit=True)

		num3 = self._get_number(d3.name)

		# Cancel document 3
		d3.cancel()
		self.assertEqual(d3.docstatus, 2)

		# New document should receive 004 (NOT reuse 003)
		d_new = self._create_doc()
		self.assertEqual(self._get_number(d_new.name), num3 + 1)

	def test_4_repeated_delete_and_recreate(self):
		"""
		Test 4:
		Create 001, 002, 003 -> Delete 003 -> Create new (gets 003) -> Delete it -> Create new -> Expected 003
		"""
		d1 = self._create_doc()
		d2 = self._create_doc()
		d3 = self._create_doc()
		d3_name = d3.name
		num3 = self._get_number(d3_name)

		# Delete 003
		frappe.delete_doc("Valve Testing", d3_name)
		self.created_docs.remove(d3_name)

		# Create new -> gets 003
		d4 = self._create_doc()
		self.assertEqual(d4.name, d3_name)

		# Delete 003 again
		frappe.delete_doc("Valve Testing", d4.name)
		self.created_docs.remove(d4.name)

		# Create new -> gets 003 again
		d5 = self._create_doc()
		self.assertEqual(d5.name, d3_name)
		self.assertEqual(self._get_number(d5.name), num3)


IntegrationTestValveTesting = TestValveTesting
