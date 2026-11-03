// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt

frappe.query_reports["Pattern Set Stock Summary"] = {
	filters: [
		{
			fieldname: "type_of_valve",
			label: __("Type of Valve"),
			fieldtype: "Data",
		},
		{
			fieldname: "size",
			label: __("Size"),
			fieldtype: "Data",
		},
		{
			fieldname: "class",
			label: __("Class"),
			fieldtype: "Data",
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nComplete\nIncomplete\nDisabled",
		},
		{
			fieldname: "warehouse",
			label: __("Warehouse"),
			fieldtype: "Link",
			options: "Warehouse",
		},
		{
			fieldname: "supplier",
			label: __("Supplier"),
			fieldtype: "Link",
			options: "Supplier",
		},
	],
};

