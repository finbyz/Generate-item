// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt

frappe.query_reports["Pending Advance Material Request"] = {
	tree: false,
	initial_depth: 1,
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company"
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date"
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date"
		}
	],

	formatter: function (value, row, column, data, default_formatter) {

		value = default_formatter(value, row, column, data);

		if (column.fieldname === "material_request") {
			value = `<span style="font-weight:600;color:#2563eb;">${value}</span>`;
		}

		if (column.fieldname === "qty") {
			value = `<span style="font-weight:bold;color:#dc2626;">${value}</span>`;
		}

		return value;
	}
};