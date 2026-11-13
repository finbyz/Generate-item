// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt

function resolve_period_dates(preset) {
	const today = frappe.datetime.get_today();
	const todayDate = frappe.datetime.str_to_obj(today);

	const fmt = (d) => frappe.datetime.obj_to_str(d);
	const add = (d, n) => { const x = new Date(d); x.setDate(x.getDate() + n); return x; };
	const subMonths = (d, n) => { const x = new Date(d); x.setMonth(x.getMonth() - n); return x; };
	const dow = todayDate.getDay();
	const daysToMon = (dow === 0 ? -6 : 1 - dow);

	switch (preset) {
		case "Today":
			return { from_date: today, to_date: today };
		case "This Week": {
			const mon = add(todayDate, daysToMon);
			return { from_date: fmt(mon), to_date: today };
		}
		case "Last Week": {
			const lastMon = add(todayDate, daysToMon - 7);
			const lastSun = add(lastMon, 6);
			return { from_date: fmt(lastMon), to_date: fmt(lastSun) };
		}
		case "This Month": {
			const first = new Date(todayDate.getFullYear(), todayDate.getMonth(), 1);
			return { from_date: fmt(first), to_date: today };
		}
		case "Last Month": {
			const first = new Date(todayDate.getFullYear(), todayDate.getMonth() - 1, 1);
			const last = new Date(todayDate.getFullYear(), todayDate.getMonth(), 0);
			return { from_date: fmt(first), to_date: fmt(last) };
		}
		case "This Quarter": {
			const start = subMonths(todayDate, 3);
			return { from_date: fmt(start), to_date: today };
		}
		case "Last Quarter": {
			const thisQStart = subMonths(todayDate, 3);
			const lastQEnd = add(thisQStart, -1);
			const lastQStart = subMonths(thisQStart, 3);
			return { from_date: fmt(lastQStart), to_date: fmt(lastQEnd) };
		}
		case "This Year": {
			const first = new Date(todayDate.getFullYear(), 0, 1);
			return { from_date: fmt(first), to_date: today };
		}
		case "Last Year": {
			const first = new Date(todayDate.getFullYear() - 1, 0, 1);
			const last = new Date(todayDate.getFullYear() - 1, 11, 31);
			return { from_date: fmt(first), to_date: fmt(last) };
		}
		default:
			return null;
	}
}

frappe.query_reports["BOM Release TAT"] = {
	filters: [
		{
			fieldname: "period",
			label: __("Period"),
			fieldtype: "Select",
			options: [
				"",
				"Today",
				"This Week",
				"Last Week",
				"This Month",
				"Last Month",
				"This Quarter",
				"Last Quarter",
				"This Year",
				"Last Year",
				"Custom",
			],
			default: "",
			on_change: function () {
				let period = frappe.query_report.get_filter_value("period");
				if (period && period !== "Custom") {
					let dates = resolve_period_dates(period);
					if (dates) {
						frappe.query_report.set_filter_value("from_date", dates.from_date);
						frappe.query_report.set_filter_value("to_date", dates.to_date);
					}
				} else if (!period) {
					frappe.query_report.set_filter_value("from_date", "");
					frappe.query_report.set_filter_value("to_date", "");
				}
				frappe.query_report.refresh();
			},
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			width: "100",
			on_change: function () {
				let period = frappe.query_report.get_filter_value("period");
				let from_date = frappe.query_report.get_filter_value("from_date");
				let to_date = frappe.query_report.get_filter_value("to_date");
				if (!from_date && !to_date) {
					if (period === "Custom") frappe.query_report.set_filter_value("period", "");
				} else if (period && period !== "Custom") {
					let expected = resolve_period_dates(period);
					if (expected && expected.from_date !== from_date) {
						frappe.query_report.set_filter_value("period", "Custom");
					}
				} else if (!period && (from_date || to_date)) {
					frappe.query_report.set_filter_value("period", "Custom");
				}
				frappe.query_report.refresh();
			},
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			width: "100",
			on_change: function () {
				let period = frappe.query_report.get_filter_value("period");
				let from_date = frappe.query_report.get_filter_value("from_date");
				let to_date = frappe.query_report.get_filter_value("to_date");
				if (!from_date && !to_date) {
					if (period === "Custom") frappe.query_report.set_filter_value("period", "");
				} else if (period && period !== "Custom") {
					let expected = resolve_period_dates(period);
					if (expected && expected.to_date !== to_date) {
						frappe.query_report.set_filter_value("period", "Custom");
					}
				} else if (!period && (from_date || to_date)) {
					frappe.query_report.set_filter_value("period", "Custom");
				}
				frappe.query_report.refresh();
			},
		},
		{
			fieldname: "bom",
			label: __("BOM"),
			fieldtype: "Link",
			options: "BOM",
			width: "150",
			on_change: () => frappe.query_report.refresh(),
		},
		{
			fieldname: "item",
			label: __("Item"),
			fieldtype: "Link",
			options: "Item",
			width: "150",
			on_change: () => frappe.query_report.refresh(),
		},
		{
			fieldname: "branch",
			label: __("Branch"),
			fieldtype: "Select",
			options: ["", "Sanand", "Rabale", "Nandikoor"],
			width: "120",
			on_change: () => frappe.query_report.refresh(),
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "MultiSelectList",
			options: ["Draft", "Approved"],
			default: ["Draft"],
			get_data: function () {
				return ["Draft", "Approved"].map((status) => ({
					value: status,
					label: __(status),
					description: "",
				}));
			},
			on_change: () => frappe.query_report.refresh(),
		},
	],

	onload: function (report) {
		const me = frappe.query_reports["BOM Release TAT"];

		let status = report.get_filter_value("status");
		if (typeof status === "string") {
			try {
				status = JSON.parse(status);
			} catch (error) {
				status = [status];
			}
			report.set_filter_value("status", Array.isArray(status) ? status : [status]);
		} else if (!status || !status.length) {
			report.set_filter_value("status", ["Draft"]);
		}

		report.$report.off("click.bom_release_tat").on("click.bom_release_tat", ".dt-cell", function (e) {
			const col_idx = parseInt($(this).attr("data-col-index"), 10);
			const row_idx = parseInt($(this).attr("data-row-index"), 10);
			const col = report.datatable ? report.datatable.getColumn(col_idx) : null;
			const row_data = (report.data || [])[row_idx];
			if (col && col.fieldname === "modifications" && row_data && row_data.bom) {
				me._open_timeline(row_data.bom);
			}
		});
	},

	_open_timeline: function (bom) {
		const dialog = new frappe.ui.Dialog({
			title: __("BOM Timeline: {0}", [bom]),
			fields: [{ fieldname: "timeline", fieldtype: "HTML" }],
		});
		dialog.fields_dict.timeline.$wrapper.html(`<div class="text-muted">${__("Loading timeline…")}</div>`);
		dialog.show();
		frappe.call({
			method: "generate_item.generate_item.report.bom_release_tat.bom_release_tat.get_bom_timeline",
			args: { bom },
			callback: function (r) {
				const rows = r.message || [];
				if (!rows.length) {
					dialog.fields_dict.timeline.$wrapper.html(`<div class="text-muted">${__("No timeline entries found.")}</div>`);
					return;
				}
				const body = rows.map((row) => `
					<tr>
						<td>${frappe.utils.escape_html(row.event_type || "")}</td>
						<td>${frappe.utils.escape_html(frappe.datetime.str_to_user(row.event_date) || "")}</td>
						<td>${frappe.utils.escape_html(row.user_name || "")}</td>
						<td>${frappe.utils.escape_html(row.state || "")}</td>
						<td>${frappe.utils.escape_html(row.reason || "")}</td>
					</tr>
				`).join("");
				dialog.fields_dict.timeline.$wrapper.html(`
					<div class="table-responsive">
						<table class="table table-bordered">
							<thead><tr>
								<th>${__("Event")}</th><th>${__("Date")}</th><th>${__("User")}</th>
								<th>${__("State")}</th><th>${__("Reason")}</th>
							</tr></thead>
							<tbody>${body}</tbody>
						</table>
					</div>
				`);
			},
			error: function () {
				dialog.fields_dict.timeline.$wrapper.html(`<div class="text-danger">${__("Could not load BOM timeline.")}</div>`);
			},
		});
	},

	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (data && column.fieldname === "pending_approval_days" && data.pending_approval_days > 0) {
			value = `<span style="color:var(--red-500);font-weight:600">${value}</span>`;
		}
		return value;
	},
};
