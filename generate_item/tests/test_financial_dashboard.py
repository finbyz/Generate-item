# Copyright (c) 2026, Steelstrong and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate, nowdate
from generate_item.generate_item.page.financial_dashboard.financial_dashboard import (
	get_overview,
	get_total_purchases_stock,
	get_total_sales_stock,
	get_total_stock_balance,
	get_unit_series,
	resolve_date_range,
)


class TestFinancialDashboard(IntegrationTestCase):
	def setUp(self):
		self.company = frappe.db.get_value("Company", {}, "name")
		self.fiscal_year = frappe.db.get_value("Fiscal Year", {"disabled": 0}, "name", order_by="year_start_date desc")

	def test_get_overview_structure(self):
		if not self.company:
			return

		data = get_overview(company=self.company, fiscal_year=self.fiscal_year, date_filter="this_fy")
		self.assertIn("meta", data)
		self.assertIn("cards", data)
		self.assertIn("kpis", data)
		self.assertIn("ar_ageing", data)
		self.assertIn("ap_ageing", data)

		# Check Row 1 (Original 3 Cards)
		kpis = data["kpis"]
		self.assertIn("net_revenue", kpis)
		self.assertIn("operating_margin", kpis)
		self.assertIn("orders_booked_count", kpis)
		self.assertGreater(kpis["net_revenue"], 0.0)

		# Check Row 2 (3 New Cards)
		cards = data["cards"]
		self.assertIn("stock_balance", cards)
		self.assertIn("total_purchases", cards)
		self.assertIn("total_sales", cards)
		self.assertIsInstance(cards["stock_balance"], (int, float))
		self.assertIsInstance(cards["total_purchases"], (int, float))
		self.assertIsInstance(cards["total_sales"], (int, float))

	def test_date_filters_resolution(self):
		today = getdate(nowdate())

		# 1. This Month
		s, e, f = resolve_date_range(date_filter="this_month")
		self.assertEqual(s.day, 1)
		self.assertEqual(f, "this_month")

		# 2. Last Month
		s, e, f = resolve_date_range(date_filter="last_month")
		self.assertTrue(s < e)
		self.assertEqual(s.day, 1)
		self.assertEqual(f, "last_month")

		# 3. This Quarter
		s, e, f = resolve_date_range(date_filter="this_quarter")
		self.assertTrue(s <= today <= e)
		self.assertEqual(f, "this_quarter")

		# 4. Last Quarter
		s, e, f = resolve_date_range(date_filter="last_quarter")
		self.assertTrue(s < e)
		self.assertEqual(f, "last_quarter")

		# 5. This Year
		s, e, f = resolve_date_range(date_filter="this_year")
		self.assertEqual(s, getdate(f"{today.year}-01-01"))
		self.assertEqual(e, getdate(f"{today.year}-12-31"))

		# 6. Last Year
		s, e, f = resolve_date_range(date_filter="last_year")
		self.assertEqual(s, getdate(f"{today.year - 1}-01-01"))
		self.assertEqual(e, getdate(f"{today.year - 1}-12-31"))

		# 7. This FY
		s, e, f = resolve_date_range(date_filter="this_fy", fiscal_year=self.fiscal_year)
		self.assertTrue(s < e)
		self.assertEqual(f, "this_fy")

		# 8. Last FY
		s, e, f = resolve_date_range(date_filter="last_fy", fiscal_year=self.fiscal_year)
		self.assertTrue(s < e)
		self.assertEqual(f, "last_fy")

		# 9. Custom Date
		custom_start = getdate("2026-05-01")
		custom_end = getdate("2026-09-30")
		s, e, f = resolve_date_range(date_filter="custom", from_date="2026-05-01", to_date="2026-09-30")
		self.assertEqual(s, custom_start)
		self.assertEqual(e, custom_end)
		self.assertEqual(f, "custom")

	def test_dashboard_cards_calculations(self):
		if not self.company:
			return

		# 1. Test Stock Balance is as of end date
		end_date = getdate("2026-09-30")
		bal = get_total_stock_balance(self.company, end_date)
		self.assertIsInstance(bal, float)
		self.assertGreater(bal, 0.0)

		# 2. Test Purchases for stock items only in period
		start_date = getdate("2026-05-01")
		purchases = get_total_purchases_stock(self.company, start_date, end_date)
		self.assertIsInstance(purchases, float)

		# 3. Test Sales for stock items only in period
		sales = get_total_sales_stock(self.company, start_date, end_date)
		self.assertIsInstance(sales, float)
		self.assertGreater(sales, 0.0)

	def test_custom_date_ranges_and_longer_periods(self):
		if not self.company:
			return

		# Test 5-month period
		data_5m = get_overview(
			company=self.company,
			date_filter="custom",
			from_date="2026-05-01",
			to_date="2026-09-30",
		)
		cards = data_5m["cards"]
		self.assertEqual(cards["from_date"], "2026-05-01")
		self.assertEqual(cards["to_date"], "2026-09-30")
		self.assertGreater(cards["total_sales"], 0.0)
		self.assertGreater(cards["stock_balance"], 0.0)

		# Test branch-wise unit series for 5-month period
		us_5m = get_unit_series(
			company=self.company,
			from_date="2026-05-01",
			to_date="2026-09-30",
			grain="months",
		)
		self.assertEqual(len(us_5m["labels"]), 5)
		self.assertEqual(us_5m["labels"], ["May 26", "Jun 26", "Jul 26", "Aug 26", "Sep 26"])
		self.assertEqual(cards["total_sales"], us_5m["grand_total"])

	def test_branch_filter(self):
		if not self.company:
			return

		branches = frappe.get_all("Branch", pluck="name")
		if not branches:
			return

		branch = branches[0]
		data_branch = get_overview(
			company=self.company,
			date_filter="custom",
			from_date="2026-05-01",
			to_date="2026-09-30",
			branch=branch,
		)
		self.assertIn("cards", data_branch)
		self.assertEqual(data_branch["meta"]["branch"], branch)

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
		self.assertIsInstance(sales_data["labels"], list)
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
		self.assertIsInstance(purchases_data["labels"], list)
		self.assertIsInstance(purchases_data["datasets"], list)
