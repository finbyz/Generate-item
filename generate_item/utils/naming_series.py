# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe.model.naming import get_default_naming_series, revert_series_if_last
from frappe.utils import getdate


def set_naming_series_variables(doc):
	"""
	Populate naming series variables (such as fiscal and fiscal_year) on the document
	if not already present. This ensures prefix parsing resolves correctly on deletion.
	"""
	date = (
		doc.get("posting_date")
		or doc.get("transaction_date")
		or doc.get("manufacturing_date")
		or doc.get("date")
		or doc.get("creation")
		or getdate()
	)

	if not getattr(doc, "fiscal_year", None):
		try:
			from erpnext.accounts.utils import get_fiscal_year

			doc.fiscal_year = get_fiscal_year(date)[0]
		except Exception:
			pass

	if not getattr(doc, "fiscal", None):
		try:
			get_fiscal_fn = frappe.get_attr("finbyzerp.api.get_fiscal")
			doc.fiscal = get_fiscal_fn(date)
		except Exception:
			if getattr(doc, "fiscal_year", None):
				fy_parts = str(doc.fiscal_year).split("-")
				if len(fy_parts) >= 2:
					doc.fiscal = fy_parts[0][2:] + fy_parts[1][2:]


def revert_series_on_trash(doc):
	"""
	Revert naming series counter in tabSeries when a document is permanently deleted,
	provided the document being deleted was the latest sequence number in that series.
	"""
	if not doc or not getattr(doc, "name", None):
		return

	# Ensure naming variables like .fiscal. are resolved
	set_naming_series_variables(doc)

	key = getattr(doc, "naming_series", None)
	if not key and getattr(doc, "meta", None) and doc.meta.autoname:
		if doc.meta.autoname.startswith("naming_series:"):
			key = get_default_naming_series(doc.doctype)
		elif doc.meta.autoname.split(":", 1)[0] not in ("Prompt", "field", "hash", "autoincrement"):
			key = doc.meta.autoname

	if key:
		revert_series_if_last(key, doc.name, doc)
