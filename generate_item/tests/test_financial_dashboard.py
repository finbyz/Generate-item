# Copyright (c) 2026, Steelstrong and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase
from generate_item.generate_item.page.financial_dashboard.financial_dashboard import (
	get_overview,
	get_unit_series,
)


class TestFinancialDashboard(IntegrationTestCase):
	def setUp(self):
		self.company = frappe.db.get_value("Company", {}, "name")
		self.fiscal_year = frappe.db.get_value("Fiscal Year", {"disabled": 0}, "name", order_by="year_start_date desc")

	def test_get_overview_structure(self):
		if not self.company:
			return

		data = get_overview(company=self.company, fiscal_year=self.fiscal_year)
		self.assertIn("meta", data)
		self.assertIn("kpis", data)
		self.assertIn("revenue_margin", data)
		self.assertIn("orders_monthly", data)
		self.assertIn("pending_orders", data)
		self.assertIn("ar_ageing", data)
		self.assertIn("ap_ageing", data)

		# Check KPI types and values
		kpis = data["kpis"]
		self.assertIsInstance(kpis["net_revenue"], (int, float))
		self.assertIsInstance(kpis["operating_margin"], (int, float))
		self.assertIsInstance(kpis["orders_booked_count"], int)
		self.assertIsInstance(kpis["pending_backlog_count"], int)

		# Check Item 1 Revenue & Margin series
		rm = data["revenue_margin"]
		self.assertEqual(len(rm["revenue_series"]), len(rm["labels"]))
		self.assertEqual(len(rm["margin_series"]), len(rm["labels"]))

	def test_get_unit_series_sales_and_purchases(self):
		if not self.company:
			return

		# Sales Quarters
		sales_data = get_unit_series(
			company=self.company,
			fiscal_year=self.fiscal_year,
			kind="sales",
			grain="quarters",
			unit_dimension="Cost Center",
		)
		self.assertEqual(sales_data["labels"], ["Q1", "Q2", "Q3", "Q4"])
		self.assertIsInstance(sales_data["datasets"], list)
		self.assertIn("grand_total", sales_data)

		# Purchases Quarters
		purchases_data = get_unit_series(
			company=self.company,
			fiscal_year=self.fiscal_year,
			kind="purchases",
			grain="quarters",
			unit_dimension="Cost Center",
		)
		self.assertEqual(purchases_data["labels"], ["Q1", "Q2", "Q3", "Q4"])
		self.assertIsInstance(purchases_data["datasets"], list)
