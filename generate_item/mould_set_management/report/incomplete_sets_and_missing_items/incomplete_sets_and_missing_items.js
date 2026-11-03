// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt

frappe.query_reports["Incomplete Sets and Missing Items"] = {
	filters: [
		{
			fieldname: "pattern_set",
			label: __("Pattern Set"),
			fieldtype: "Link",
			options: "Pattern Set",
		},
		{
			fieldname: "warehouse",
			label: __("Warehouse"),
			fieldtype: "Link",
			options: "Warehouse",
		},
	],
};

