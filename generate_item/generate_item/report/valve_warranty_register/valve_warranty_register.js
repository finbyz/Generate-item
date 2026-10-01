// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt

frappe.query_reports["Valve Warranty Register"] = {
	filters: [
		{
			fieldname: "branch",
			label: __("Branch"),
			fieldtype: "Link",
			options: "Branch",
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
		},
		{
			fieldname: "sales_order",
			label: __("Sales Order"),
			fieldtype: "Link",
			options: "Sales Order",
			get_query: function () {
				let customer = frappe.query_report.get_filter_value("customer");
				let branch = frappe.query_report.get_filter_value("branch");
				let filters = { docstatus: ["!=", 2] };
				if (customer) filters["customer"] = customer;
				if (branch) filters["branch"] = branch;
				return { filters: filters };
			},
		},
		{
			fieldname: "sales_invoice",
			label: __("Sales Invoice"),
			fieldtype: "Link",
			options: "Sales Invoice",
			get_query: function () {
				let customer = frappe.query_report.get_filter_value("customer");
				let branch = frappe.query_report.get_filter_value("branch");
				let filters = { docstatus: 1 };
				if (customer) filters["customer"] = customer;
				if (branch) filters["branch"] = branch;
				return { filters: filters };
			},
		},
		{
			fieldname: "batch",
			label: __("Batch"),
			fieldtype: "Link",
			options: "Batch",
		},
		{
			fieldname: "serial_number",
			label: __("Valve Serial No"),
			fieldtype: "Link",
			options: "Serial Number",
			get_query: function () {
				let batch = frappe.query_report.get_filter_value("batch");
				let branch = frappe.query_report.get_filter_value("branch");
				let filters = { docstatus: ["!=", 2] };
				if (batch) filters["batch"] = batch;
				if (branch) filters["branch"] = branch;
				return { filters: filters };
			},
		},
		{
			fieldname: "item_code",
			label: __("Item Code"),
			fieldtype: "Link",
			options: "Item",
		},
		{
			fieldname: "warranty_status",
			label: __("Warranty Status"),
			fieldtype: "Select",
			options: [
				"All",
				"Under Warranty",
				"Expiring in 30 Days",
				"Expiring in 60 Days",
				"Expired",
				"Warranty Expiry Not Set",
			],
			default: "Under Warranty"
		},
		{
			fieldname: "from_expiry_date",
			label: __("From Expiry Date"),
			fieldtype: "Date",
		},
		{
			fieldname: "to_expiry_date",
			label: __("To Expiry Date"),
			fieldtype: "Date",
		},
		{
			fieldname: "from_invoice_date",
			label: __("From Invoice Date"),
			fieldtype: "Date",
		},
		{
			fieldname: "to_invoice_date",
			label: __("To Invoice Date"),
			fieldtype: "Date",
		},
	],

	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "serial_number" && data && data.serial_number) {
			value = `<span style="font-family: var(--font-stack-monospace, monospace); font-weight: 600; color: #2563eb;">${value}</span>`;
		}

		if (column.fieldname === "warranty_expiry_date" && data && data.warranty_expiry_date) {
			value = `<span style="font-weight: 600;">${value}</span>`;
		}

		if (column.fieldname === "days_remaining" && data && data.days_remaining !== null && data.days_remaining !== undefined) {
			if (data.days_remaining < 0) {
				value = `<span style="font-weight: 600; color: #dc2626;">${Math.abs(data.days_remaining)} days overdue</span>`;
			} else if (data.days_remaining <= 30) {
				value = `<span style="font-weight: 600; color: #ea580c;">${data.days_remaining} days left</span>`;
			} else if (data.days_remaining <= 60) {
				value = `<span style="font-weight: 600; color: #d97706;">${data.days_remaining} days left</span>`;
			} else {
				value = `<span style="font-weight: 600; color: #16a34a;">${data.days_remaining} days left</span>`;
			}
		}

		if (column.fieldname === "warranty_status" && data && data.warranty_status) {
			let color_map = {
				"Under Warranty": { bg: "#dcfce7", text: "#15803d", border: "#86efac" },
				"Expiring in 30 Days": { bg: "#ffedd5", text: "#c2410c", border: "#fdba74" },
				"Expiring in 60 Days": { bg: "#fef3c7", text: "#b45309", border: "#fde047" },
				"Expired": { bg: "#fee2e2", text: "#b91c1c", border: "#fca5a5" },
				"Not Set": { bg: "#f3f4f6", text: "#4b5563", border: "#d1d5db" },
			};
			let style = color_map[data.warranty_status] || { bg: "#f3f4f6", text: "#4b5563", border: "#d1d5db" };
			value = `<span style="display: inline-block; padding: 2px 8px; font-size: 11px; font-weight: 600; border-radius: 12px; background-color: ${style.bg}; color: ${style.text}; border: 1px solid ${style.border};">${data.warranty_status}</span>`;
		}

		return value;
	},
};
