// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt



frappe.query_reports["Bom Explorer SSV"] = {
	filters: [
		{
			fieldname: "bom",
			label: __("BOM"),
			fieldtype: "Link",
			options: "BOM",
			reqd: 1,
		},
	],
};
