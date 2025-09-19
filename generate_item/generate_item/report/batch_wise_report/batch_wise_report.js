// Copyright (c) 2025, Finbyz and contributors
// For license information, please see license.txt

frappe.query_reports["Batch Wise Report"] = {
	"filters": [
		{
			fieldname: "from_date",
			label: "From Date",
			fieldtype: "Date"
		},
		{
			fieldname: "to_date",
			label: "To Date",
			fieldtype: "Date"
		},
		{
			fieldname: "bom",
			label: "BOM",
			fieldtype: "Link",
			options: "BOM"
		},
		{
			fieldname: "batch",
			label: "Batch",
			fieldtype: "Link",
			options: "Batch"
		},
		{
			fieldname: "sales_order",
			label: "Sales Order",
			fieldtype: "Link",
			options: "Sales Order"
		},
		{
			fieldname: "item_code",
			label: "Item Code",
			fieldtype: "Link",
			options: "Item"
		}],
		"formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
		if (column.fieldname == "production_plan_status") {
            if (value == "Submitted") {
                value = `<span style="color: green; font-weight: bold;">${value}</span>`;
            } else if (value == "Draft") {
                value = `<span style="color: orange; font-weight: bold;">${value}</span>`;
            } else if (value == "Not Created") {
                value = `<span style="color: gray; font-style: italic;">${value}</span>`;
            }
        }
		return value;
    },
	
};
