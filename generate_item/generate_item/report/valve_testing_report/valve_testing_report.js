// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt

function format_iso_date(d) {
	let year = d.getFullYear();
	let month = String(d.getMonth() + 1).padStart(2, "0");
	let day = String(d.getDate()).padStart(2, "0");
	return `${year}-${month}-${day}`;
}

function calculate_date_range(range_type) {
	let now = new Date();
	let year = now.getFullYear();
	let month = now.getMonth();
	let day = now.getDate();

	if (range_type === "Today") {
		let d = format_iso_date(now);
		return [d, d];
	} else if (range_type === "Yesterday") {
		let y = new Date(year, month, day - 1);
		let d = format_iso_date(y);
		return [d, d];
	} else if (range_type === "This Week") {
		let dayOfWeek = now.getDay(); // 0 is Sunday, 1 is Monday...
		let diffToMon = (dayOfWeek === 0 ? -6 : 1) - dayOfWeek;
		let monday = new Date(year, month, day + diffToMon);
		let sunday = new Date(monday.getFullYear(), monday.getMonth(), monday.getDate() + 6);
		return [format_iso_date(monday), format_iso_date(sunday)];
	} else if (range_type === "Last Week") {
		let dayOfWeek = now.getDay();
		let diffToMon = (dayOfWeek === 0 ? -6 : 1) - dayOfWeek;
		let lastMonday = new Date(year, month, day + diffToMon - 7);
		let lastSunday = new Date(lastMonday.getFullYear(), lastMonday.getMonth(), lastMonday.getDate() + 6);
		return [format_iso_date(lastMonday), format_iso_date(lastSunday)];
	} else if (range_type === "This Month") {
		let firstDay = new Date(year, month, 1);
		let lastDay = new Date(year, month + 1, 0);
		return [format_iso_date(firstDay), format_iso_date(lastDay)];
	} else if (range_type === "Last Month") {
		let firstDay = new Date(year, month - 1, 1);
		let lastDay = new Date(year, month, 0);
		return [format_iso_date(firstDay), format_iso_date(lastDay)];
	}
	return null;
}

frappe.query_reports["Valve Testing Report"] = {
	filters: [
		{
			fieldname: "date_range",
			label: __("Date Range"),
			fieldtype: "Select",
			options: [
				"Today",
				"Yesterday",
				"This Week",
				"Last Week",
				"This Month",
				"Last Month",
				"Custom",
			],
			default: "This Month",
			on_change: function (query_report) {
				let range = query_report.get_filter_value("date_range");
				if (range && range !== "Custom") {
					let dates = calculate_date_range(range);
					if (dates) {
						query_report.set_filter_value("from_date", dates[0]);
						query_report.set_filter_value("to_date", dates[1]);
					}
				}
			},
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: calculate_date_range("This Month")[0],
			reqd: 1,
			on_change: function (query_report) {
				let range = query_report.get_filter_value("date_range");
				if (range && range !== "Custom") {
					let expected = calculate_date_range(range);
					if (expected && expected[0] !== query_report.get_filter_value("from_date")) {
						query_report.set_filter_value("date_range", "Custom");
					}
				}
			},
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: calculate_date_range("This Month")[1],
			reqd: 1,
			on_change: function (query_report) {
				let range = query_report.get_filter_value("date_range");
				if (range && range !== "Custom") {
					let expected = calculate_date_range(range);
					if (expected && expected[1] !== query_report.get_filter_value("to_date")) {
						query_report.set_filter_value("date_range", "Custom");
					}
				}
			},
		},
		{
			fieldname: "test_ok",
			label: __("Test Result"),
			fieldtype: "Select",
			options: "Accepted\nNot Accepted\nBoth",
			default: "Accepted",
		},
		{
			fieldname: "testing_phase",
			label: __("Testing Phase"),
			fieldtype: "Select",
			options: "\nPre Testing\nFinal Testing\nTPI Testing",
		},
		{
			fieldname: "branch",
			label: __("Branch"),
			fieldtype: "Link",
			options: "Branch",
		},
		{
			fieldname: "leak_reason",
			label: __("Leak Reason"),
			fieldtype: "Select",
			options: "\nAir Seat Leak\nHydro Seat Leak\nBody Casting Leak\nSeatring Casting Leak\nBonnet Casting Leak\nWedge Casting Leak\nJoint Leak\nBack Seat Leak\nWelding Leak\nBore Casting Leak",
		},
		{
			fieldname: "valve_testing",
			label: __("Valve Testing"),
			fieldtype: "Link",
			options: "Valve Testing",
		},
		{
			fieldname: "sales_order",
			label: __("Sales Order"),
			fieldtype: "Link",
			options: "Sales Order",
		},
		{
			fieldname: "batch_no",
			label: __("Batch No"),
			fieldtype: "Link",
			options: "Batch",
		},
		{
			fieldname: "serial_number",
			label: __("Valve Sr No"),
			fieldtype: "Link",
			options: "Serial Number",
		},
		{
			fieldname: "item_code",
			label: __("Item Code"),
			fieldtype: "Link",
			options: "Item",
		},
		{
			fieldname: "user",
			label: __("Inspector"),
			fieldtype: "Link",
			options: "Employee",
		},
		{
			fieldname: "tested_by",
			label: __("Tested By"),
			fieldtype: "Link",
			options: "User",
			get_query: function () {
				return {
					filters: {
						enabled: 1,
						custom_is_operator: 1,
					},
				};
			},
		},
	],

	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "test_ok" && data) {
			if (data.test_ok === "Accepted") {
				value = `<span style="background: rgba(16, 185, 129, 0.14); color: #059669; border: 1px solid rgba(16, 185, 129, 0.35); font-weight: 600; padding: 3px 10px; border-radius: 12px; font-size: 11px; display: inline-flex; align-items: center; gap: 4px;">✓ ${__("Accepted")}</span>`;
			} else if (data.test_ok === "Not Accepted") {
				value = `<span style="background: rgba(239, 68, 68, 0.14); color: #dc2626; border: 1px solid rgba(239, 68, 68, 0.35); font-weight: 600; padding: 3px 10px; border-radius: 12px; font-size: 11px; display: inline-flex; align-items: center; gap: 4px;">✗ ${__("Not Accepted")}</span>`;
			}
		}

		if (column.fieldname === "leak_reason" && data) {
			if (data.test_ok === "Not Accepted" && data.leak_reason) {
				value = `<span style="background: rgba(244, 63, 94, 0.12); color: #e11d48; border: 1px solid rgba(244, 63, 94, 0.3); padding: 2px 8px; border-radius: 6px; font-weight: 600; font-size: 11px; display: inline-flex; align-items: center; gap: 4px;">⚠️ ${data.leak_reason}</span>`;
			} else if (data.test_ok === "Accepted") {
				value = "";
			}
		}

		if (column.fieldname === "serial_number" && data && data.serial_number) {
			value = `<span style="font-family: var(--font-stack-monospace, monospace); font-weight: 600; color: #2563eb;">${value}</span>`;
		}

		if (column.fieldname === "inches" && data && data.inches) {
			value = `<span style="font-weight: 600; color: #7c3aed;">${value}</span>`;
		}

		return value;
	},
};
