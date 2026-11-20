# -*- coding: utf-8 -*-
# Copyright (c) 2021, Finbyz Tech. Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt,cint ,comma_or, nowdate, getdate
from frappe.model.mapper import get_mapped_doc
from generate_item.utils.sales_order import update_proforma_details,change_sales_order_status
from erpnext.controllers.status_updater import StatusUpdater
from erpnext.utilities.transaction_base import TransactionBase
# from generate_item.api import validate_sales_person


class ProformaInvoice(TransactionBase):
	# TransactionBase gives the server-side item selection (process_item_selection) that the
	# ERPNext v16 selling form calls when an item is picked.
	def calculate_taxes_and_totals(self):
		from erpnext.controllers.taxes_and_totals import calculate_taxes_and_totals

		# ERPNext's totals code reads tax.category for doctypes outside its sales list.
		# Sales tax rows have no such field, so treat every row as "Total".
		for tax in self.get("taxes") or []:
			if not tax.get("category"):
				tax.category = "Total"
			if not tax.get("add_deduct_tax"):
				tax.add_deduct_tax = "Add"

		calculate_taxes_and_totals(self)

	def apply_shipping_rule(self):
		if self.get("shipping_rule"):
			shipping_rule = frappe.get_doc("Shipping Rule", self.shipping_rule)
			shipping_rule.apply(self)
			self.calculate_taxes_and_totals()

	def is_rounded_total_disabled(self):
		if self.meta.get_field("disable_rounded_total"):
			return self.disable_rounded_total
		return frappe.db.get_single_value("Global Defaults", "disable_rounded_total")

	def is_internal_transfer(self):
		return False

	def drop_mapped_discount(self, item):
		item.mapped_additional_discount_amount = 0

	def before_insert(self):
		self.set_naming_series_by_branch()

	def set_naming_series_by_branch(self):
		series_map = {
			"Sanand": "PINS.fiscal.#####",
			"Nandikoor": "PINN.fiscal.#####",
			"Rabale": "PINR.fiscal.#####",
		}
		if self.branch and self.branch in series_map:
			self.naming_series = series_map[self.branch]

	def validate(self):
		if self.payment_percentage:
			self.payment_due_amount = flt(self.rounded_total) * self.payment_percentage / 100
		for item in self.items:
			item.payment_amount = flt(item.net_amount) * self.payment_percentage / 100
		self.validate_sales_team_allocation()
		self.validate_sales_person()
	
	def validate_sales_team_allocation(self):
		if not self.sales_team:
			return
		total = sum(flt(d.allocated_percentage) for d in self.sales_team)
		if abs(flt(total, 2) - 100) > 0.01:
			frappe.throw(
				_("Total contribution of the Sales Team must be 100%. It is currently {0}%.").format(flt(total, 2)),
				title=_("Invalid Sales Team"),
			)

	def validate_sales_person(self):
		if self.sales_team:
			self.sales_person=self.sales_team[0].sales_person

	def on_submit(self):
		if self.payment_percentage == 0:
			frappe.throw("Please Enter Payment Percentage")
		update_proforma_details(self.name,"submit")
		set_status(self)

	def on_cancel(self):
		update_proforma_details(self.name,"cancel")

	@frappe.whitelist()
	def set_status(self, status):
		self.db_set('status', status)
		set_status(self)

def set_status(self, update_modified= True):
	if self.status != "Closed":
		if flt(self.advance_paid) == flt(self.payment_due_amount) or (flt(self.advance_paid) > flt(self.payment_due_amount) and self.allow_over_billing_payment):
			self.db_set('status','Paid', update_modified= update_modified)
		elif flt(self.advance_paid) > 0:
			self.db_set('status','Partially Paid', update_modified= update_modified)
		else:
			self.db_set('status','Unpaid', update_modified= update_modified)
	# Only when the invoice is linked to a Sales Order (items added by hand have none).
	sales_orders = {d.sales_order for d in self.items if d.sales_order}
	for sales_order in sales_orders:
		change_sales_order_status(frappe.get_doc("Sales Order", sales_order), update_modified= update_modified)

@frappe.whitelist()
def create_proforma_invoice(source_name, target_doc=None):
	def set_missing_value(source, target):
		target.run_method('set_missing_values')
		target.run_method('calculate_taxes_and_totals')
		target.set_naming_series_by_branch()
		
	fields = {
		"Sales Order": {
			"doctype": "Proforma Invoice",
			"field_map": {
				"company": "company",
				"branch": "branch",
				"customer": "customer",
				"customer_name": "customer_name",
				"customer_group": "customer_group",
				"territory": "territory",			
				"taxes_and_charges": "taxes_and_charges",
				"taxes_and_charges_template": "taxes_and_charges_template",
				"po_no": "po_no",	
				"po_date": "po_date",
				"project": "project",
				"payment_terms_template": "payment_terms_template",
				"bank_account": "bank_account",
				"sales_person": "sales_person",
				"tax_id": "tax_id",
				"taxes": "taxes",
			},
			"field_no_map":{
				"naming_series",
				"skip_delivery_note",
				"amended_from",
				"scan_barcode",
				"inter_company_order_reference",
				"status",
				
				"delivery_status",
				"per_delivered",
				"per_billed",
				"billing_status",
				"auto_repeat",
				"total_qty",
				"base_total",
				"base_net_total",
				"total_net_weight",
				"total",
				"net_total"
			},
		},
		"Sales Order Item": {
			"doctype": "Proforma Invoice Item",
			"field_map": {
				"parent": "sales_order",
				"name":"sales_order_item",
    			"qty": "qty",
				"rate": "rate",	
			},
			"condition": lambda doc: (doc.proforma_percentage) < 100
		},
	}
	doclist = get_mapped_doc(
		"Sales Order",
		source_name,
		fields,
		target_doc,
		set_missing_value,
		ignore_permissions=True
	)
	return doclist


