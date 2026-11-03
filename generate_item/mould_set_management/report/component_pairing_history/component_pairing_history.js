// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt

frappe.query_reports["Component Pairing History"] = {
	filters: [
		{
			fieldname: "serial_no",
			label: __("Serial No"),
			fieldtype: "Link",
			options: "Serial No",
		},
		{
			fieldname: "pattern_set",
			label: __("Pattern Set"),
			fieldtype: "Link",
			options: "Pattern Set",
		},
	],
};

