

// Copyright (c) 2025, Finbyz and contributors
// For license information, please see license.txt

frappe.query_reports["Sales Order Register Marketing"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_days(frappe.datetime.get_today(), -7),
			"width": "100",
			"on_change": () => frappe.query_report.refresh()
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"width": "100",
			"on_change": () => frappe.query_report.refresh()
		},		
		{
			"fieldname": "sales_order",
			"label": __("Sales Order"),
			"fieldtype": "Link",
			"options": "Sales Order",
			"width": "150",
			"on_change": () => frappe.query_report.refresh()
		},
		{
			"fieldname": "customer",
			"label": __("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": "150",
			"on_change": () => frappe.query_report.refresh()
		},
		{
			"fieldname": "item_code",
			"label": __("Item Code"),
			"fieldtype": "Link",
			"options": "Item",
			"width": "150",
			"on_change": () => frappe.query_report.refresh()
		},
		{
			"fieldname": "batch_no",
			"label": __("Batch No"),
			"fieldtype": "Link",
			"options": "Batch",
			"width": "150",
			"on_change": () => frappe.query_report.refresh()
		},
		{
			"fieldname": "branch",
			"label": __("Branch"),
			"fieldtype": "Select",
			"options": ["","Sanand", "Rabale","Nandikoor"],
			"width": "100",
			"on_change": () => frappe.query_report.refresh()
		},
		// {
		// 	"fieldname": "status",
		// 	"label": __("Order Status"),
		// 	"fieldtype": "Select",
		// 	"options": ["", "To Deliver and Bill", "To Deliver", "To Bill", "Closed", "Cancelled"],
		// 	"width": "150",
		// 	"on_change": () => frappe.query_report.refresh()
		// }
		{
			fieldname: "status",
			label: __("Order Status"),
			fieldtype: "MultiSelectList",
			options: [
				"To Deliver and Bill",
				"To Deliver",
				"To Bill",
				"Closed",
				"Cancelled",
				"Completed"
			],
			on_change: () => frappe.query_report.refresh()
		}
	]
};

