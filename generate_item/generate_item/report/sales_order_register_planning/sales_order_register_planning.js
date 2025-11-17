// Copyright (c) 2025, Finbyz and contributors
// For license information, please see license.txt

frappe.query_reports["Sales Order Register Planning"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_days(frappe.datetime.get_today(), -7),
			"reqd": 1,
			"width": "100"
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1,
			"width": "100"
		},		
		{
			"fieldname": "sales_order",
			"label": __("Sales Order"),
			"fieldtype": "Link",
			"options": "Sales Order",
			"width": "150"
		},
		{
			"fieldname": "customer",
			"label": __("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": "150"
		},
		{
			"fieldname": "branch",
			"label": __("Branch"),
			"fieldtype": "Select",
			"options": ["","Sanand", "Rabale","Nandikoor"],
			"width": "100",
			"reqd": 1,
		},
		{
			"fieldname": "status",
			"label": __("Order Status"),
			"fieldtype": "Select",
			"options": ["", "To Deliver and Bill", "To Deliver", "To Bill", "Closed", "Cancelled"],
			"width": "150"
		}
	]
};