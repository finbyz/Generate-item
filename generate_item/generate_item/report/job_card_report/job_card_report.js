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
		let dayOfWeek = now.getDay();
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
	} else if (range_type === "All") {
		return ["", ""];
	}
	return null;
}

frappe.query_reports["Job Card Report"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "date_range",
			label: __("Date Range"),
			fieldtype: "Select",
			options: [
				"This Month",
				"Last Month",
				"Today",
				"Yesterday",
				"This Week",
				"Last Week",
				"All",
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
			on_change: function (query_report) {
				let range = query_report.get_filter_value("date_range");
				if (range && range !== "Custom") {
					let expected = calculate_date_range(range);
					if (expected && expected[0] !== (query_report.get_filter_value("from_date") || "")) {
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
			on_change: function (query_report) {
				let range = query_report.get_filter_value("date_range");
				if (range && range !== "Custom") {
					let expected = calculate_date_range(range);
					if (expected && expected[1] !== (query_report.get_filter_value("to_date") || "")) {
						query_report.set_filter_value("date_range", "Custom");
					}
				}
			},
		},
		
		{
			fieldname: "branch",
			label: __("Branch"),
			fieldtype: "Link",
			options: "Branch",
		},
		{
			fieldname: "work_order",
			label: __("Work Order"),
			fieldtype: "Link",
			options: "Work Order",
		},
		{
			fieldname: "job_card",
			label: __("Job Card"),
			fieldtype: "Link",
			options: "Job Card",
		},
		{
			fieldname: "production_item",
			label: __("Production Item"),
			fieldtype: "Link",
			options: "Item",
		},
		{
			fieldname: "operation",
			label: __("Operation"),
			fieldtype: "Link",
			options: "Operation",
		},
		{
			fieldname: "workstation",
			label: __("Workstation"),
			fieldtype: "Link",
			options: "Workstation",
		},
		{
			fieldname: "operator",
			label: __("Operator"),
			fieldtype: "Link",
			options: "Employee",
		},
		{
			fieldname: "status",
			label: __("Job Card Status"),
			fieldtype: "Select",
			options: [
				"",
				"Open",
				"Work In Progress",
				"Partially Transferred",
				"Material Transferred",
				"On Hold",
				"Submitted",
				"Cancelled",
				"Completed",
			],
		},
		{
			fieldname: "qc_status",
			label: __("QC Status"),
			fieldtype: "Select",
			options: [
				"",
				"PASS",
				"FAIL",
				"PENDING",
				"NOT REQUIRED",
				"NOT AVAILABLE",
			],
		},
	],

	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (!data) return value;

		// 1. Status formatting
		if (column.fieldname === "status") {
			let st = data.status;
			if (st === "Completed" || st === "Submitted") {
				value = `<span style="background: rgba(16, 185, 129, 0.12); color: #059669; border: 1px solid rgba(16, 185, 129, 0.3); font-weight: 600; padding: 2px 8px; border-radius: 12px; font-size: 11px;">✓ ${st}</span>`;
			} else if (st === "Work In Progress") {
				value = `<span style="background: rgba(59, 130, 246, 0.12); color: #2563eb; border: 1px solid rgba(59, 130, 246, 0.3); font-weight: 600; padding: 2px 8px; border-radius: 12px; font-size: 11px;">⚙ ${st}</span>`;
			} else if (st === "Open") {
				value = `<span style="background: rgba(100, 116, 139, 0.12); color: #475569; border: 1px solid rgba(100, 116, 139, 0.3); font-weight: 500; padding: 2px 8px; border-radius: 12px; font-size: 11px;">${st}</span>`;
			} else if (st === "On Hold") {
				value = `<span style="background: rgba(245, 158, 11, 0.12); color: #d97706; border: 1px solid rgba(245, 158, 11, 0.3); font-weight: 600; padding: 2px 8px; border-radius: 12px; font-size: 11px;">⏸ ${st}</span>`;
			} else if (st === "Cancelled") {
				value = `<span style="background: rgba(239, 68, 68, 0.12); color: #dc2626; border: 1px solid rgba(239, 68, 68, 0.3); font-weight: 600; padding: 2px 8px; border-radius: 12px; font-size: 11px;">✗ ${st}</span>`;
			} else if (st.includes("Transferred")) {
				value = `<span style="background: rgba(139, 92, 246, 0.12); color: #7c3aed; border: 1px solid rgba(139, 92, 246, 0.3); font-weight: 600; padding: 2px 8px; border-radius: 12px; font-size: 11px;">${st}</span>`;
			}
		}

		// 2. QC Status formatting
		if (column.fieldname === "qc_status") {
			let qc = data.qc_status;
			if (qc === "PASS") {
				value = `<span style="background: rgba(16, 185, 129, 0.14); color: #059669; border: 1px solid rgba(16, 185, 129, 0.35); font-weight: 700; padding: 3px 10px; border-radius: 12px; font-size: 11px; display: inline-flex; align-items: center; gap: 4px;">✓ PASS</span>`;
			} else if (qc === "FAIL") {
				value = `<span style="background: rgba(239, 68, 68, 0.14); color: #dc2626; border: 1px solid rgba(239, 68, 68, 0.35); font-weight: 700; padding: 3px 10px; border-radius: 12px; font-size: 11px; display: inline-flex; align-items: center; gap: 4px;">✗ FAIL</span>`;
			} else if (qc === "PENDING") {
				value = `<span style="background: rgba(245, 158, 11, 0.14); color: #d97706; border: 1px solid rgba(245, 158, 11, 0.35); font-weight: 600; padding: 3px 10px; border-radius: 12px; font-size: 11px; display: inline-flex; align-items: center; gap: 4px;">⏳ PENDING</span>`;
			} else if (qc === "NOT REQUIRED") {
				value = `<span style="color: #64748b; font-size: 11px;">NOT REQUIRED</span>`;
			} else if (qc === "NOT AVAILABLE") {
				value = `<span style="color: #94a3b8; font-size: 11px;">NOT AVAILABLE</span>`;
			}
		}

		// 3. Time Variance highlighting
		if (column.fieldname === "time_variance_in_mins") {
			let variance = flt(data.time_variance_in_mins);
			let actual = flt(data.actual_time_in_mins);
			if (actual > 0 && variance > 0) {
				value = `<span style="background: rgba(239, 68, 68, 0.1); color: #dc2626; font-weight: 600; padding: 2px 6px; border-radius: 4px;">+${variance} min ⚠️</span>`;
			} else if (actual > 0 && variance <= 0) {
				value = `<span style="background: rgba(16, 185, 129, 0.1); color: #059669; font-weight: 600; padding: 2px 6px; border-radius: 4px;">${variance} min</span>`;
			} else {
				value = `<span style="color: #94a3b8;">${variance} min</span>`;
			}
		}

		// 4. Completion Percentage styling
		if (column.fieldname === "completion_percentage") {
			let pct = flt(data.completion_percentage);
			let color = pct >= 100 ? "#059669" : (pct > 0 ? "#2563eb" : "#94a3b8");
			value = `<span style="font-weight: 700; color: ${color};">${pct.toFixed(1)}%</span>`;
		}

		// 5. Quantities styling
		if (column.fieldname === "rejected_qty" && flt(data.rejected_qty) > 0) {
			value = `<span style="color: #dc2626; font-weight: 700;">${value}</span>`;
		}

		return value;
	},
};
