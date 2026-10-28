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

frappe.query_reports["SO Approval TAT"] = {
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
					if (period === "Custom") {
						frappe.query_report.set_filter_value("period", "");
					}
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
					if (period === "Custom") {
						frappe.query_report.set_filter_value("period", "");
					}
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
			fieldname: "sales_order",
			label: __("Sales Order"),
			fieldtype: "Link",
			options: "Sales Order",
			width: "150",
			get_query: function () {
				return { filters: { docstatus: ["!=", 2] } }; // exclude Cancelled
			},
			on_change: () => frappe.query_report.refresh(),
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
			width: "150",
			on_change: () => frappe.query_report.refresh(),
		},
		{
			fieldname: "branch",
			label: __("Branch"),
			fieldtype: "Select",
			options: ["", "Sanand", "Rabale", "Nandikoor"],
			width: "100",
			on_change: () => frappe.query_report.refresh(),
		},
		{
			fieldname: "status",
			label: __("Order Status"),
			fieldtype: "MultiSelectList",
			options: [
				"Draft",
				"To Deliver and Bill",
				"To Deliver",
				"To Bill",
				"Closed",
				"Cancelled",
				"Completed",
			],
			default: ["Draft"], // by default show Draft orders
			get_data: function (txt) {
				const status_options = [
					"Draft",
					"To Deliver and Bill",
					"To Deliver",
					"To Bill",
					"Closed",
					"Cancelled",
					"Completed",
				];
				return status_options.map((s) => ({ value: s, label: __(s), description: "" }));
			},
			on_change: () => frappe.query_report.refresh(),
		},
	],

	onload: function (report) {
		const me = frappe.query_reports["SO Approval TAT"];
		me._report = report;
		me._pending_changes = {};

		const status = report.get_filter_value("status");
		if (!status || (Array.isArray(status) && !status.length)) {
			report.set_filter_value("status", ["Draft"]);
		}

		// Save Changes toolbar button
		me._save_btn = report.page.add_inner_button(__("Save Changes"), () => {
			me._save_all_changes();
		});
		me._update_save_button();

		// Cell click → open inline editor (like Daily Review Sales Order report)
		report.$report.off("click.so_remark").on("click.so_remark", ".dt-cell", function (e) {
			if ($(e.target).closest(".inline-editor").length) return;

			const col_idx = parseInt($(this).attr("data-col-index"), 10);
			const row_idx = parseInt($(this).attr("data-row-index"), 10);

			const col = report.datatable ? report.datatable.getColumn(col_idx) : null;
			if (!col || (col.fieldname !== "remark" && col.id !== "remark")) return;

			const row_data = (report.data || [])[row_idx];
			if (!row_data || !row_data.sales_order) return;

			me._open_inline_editor($(this), row_data);
		});
	},

	_update_save_button: function () {
		const me = frappe.query_reports["SO Approval TAT"];
		if (!me._save_btn) return;

		const count = Object.keys(me._pending_changes || {}).length;
		if (count > 0) {
			me._save_btn
				.html(`<i class="fa fa-save mr-1"></i>${__("Save Changes")} (${count})`)
				.removeClass("btn-default btn-secondary")
				.addClass("btn-warning");
		} else {
			me._save_btn
				.html(__("Save Changes"))
				.removeClass("btn-warning")
				.addClass("btn-default");
		}
	},

	_stage_change: function ($cell, row_data, new_value) {
		const me = frappe.query_reports["SO Approval TAT"];
		const so = row_data.sales_order;

		me._pending_changes[so] = new_value;
		row_data.remark = new_value;

		me._paint_cell($cell, new_value, true /* pending */);
		me._update_save_button();
	},

	_open_inline_editor: function ($cell, row_data) {
		const me = frappe.query_reports["SO Approval TAT"];
		if ($cell.find(".inline-editor").length) return;

		$cell.css("position", "relative");
		$(document).trigger("close_so_remark_inline_editor");

		let closed = false;
		const so = row_data.sales_order;
		const cur_value = me._pending_changes[so] !== undefined
			? me._pending_changes[so]
			: (row_data.remark || "");

		const close = (should_stage) => {
			if (closed) return;
			closed = true;
			$(document).off("pointerdown.so_remark_inline_editor close_so_remark_inline_editor");

			if (should_stage && $editor) {
				const new_value = String($editor.val() || "").trim();
				if (new_value !== cur_value) {
					me._stage_change($cell, row_data, new_value);
				} else {
					const is_pending = me._pending_changes[so] !== undefined;
					me._paint_cell($cell, cur_value, is_pending);
				}
			} else {
				const is_pending = me._pending_changes[so] !== undefined;
				me._paint_cell($cell, cur_value, is_pending);
			}

			if ($editor) $editor.remove();
		};

		$(document).on("close_so_remark_inline_editor", () => close(true));

		const $editor = $(`
			<input type="text" class="inline-editor form-control input-sm" value="${frappe.utils.escape_html(cur_value)}" style="
				position:absolute; top:0; left:0; width:100%; height:100%;
				z-index:100; font-size:12px; border:2px solid var(--primary, var(--blue-500, #3b82f6));
				background:var(--control-bg, var(--card-bg, #ffffff)); color:var(--text-color, #1f272e); padding:2px 6px;
				border-radius:3px; outline:none; box-shadow: 0 2px 6px rgba(0,0,0,0.15);
			"/>
		`);

		$editor.on("keydown", (e) => {
			if (e.key === "Enter") {
				e.preventDefault();
				close(true);
			} else if (e.key === "Escape") {
				e.preventDefault();
				close(false);
			}
		});

		$editor.on("click pointerdown mousedown", (e) => {
			e.stopPropagation();
		});

		$cell.append($editor);
		$editor.focus();

		setTimeout(() => {
			$(document).on("pointerdown.so_remark_inline_editor", (e) => {
				if (!$(e.target).closest($cell).length) {
					close(true);
				}
			});
		}, 100);
	},

	_save_all_changes: function () {
		const me = frappe.query_reports["SO Approval TAT"];
		const changes = me._pending_changes || {};
		const count = Object.keys(changes).length;

		if (!count) {
			frappe.show_alert({ message: __("No pending changes to save."), indicator: "blue" }, 3);
			return;
		}

		me._save_btn && me._save_btn.prop("disabled", true).html(
			`<i class="fa fa-spinner fa-spin mr-1"></i>${__("Saving…")}`
		);

		frappe.call({
			method: "generate_item.generate_item.report.so_approval_tat.so_approval_tat.bulk_update_remarks",
			args: { changes: changes },
			freeze: true,
			freeze_message: __("Saving {0} remark(s)…", [count]),
			callback: function (r) {
				me._save_btn && me._save_btn.prop("disabled", false);
				if (r.message) {
					me._pending_changes = {};
					me._update_save_button();
					frappe.show_alert({
						message: __("Saved — {0} remark(s) updated.", [r.message.updated || count]),
						indicator: "green",
					}, 4);
					me._report.refresh();
				}
			},
			error: function () {
				me._save_btn && me._save_btn.prop("disabled", false);
				me._update_save_button();
			},
		});
	},

	_paint_cell: function ($cell, val, pending) {
		const display = frappe.utils.escape_html(val || "");
		const empty = `<span style="color:var(--text-muted);">${__("User Entry")}</span>`;

		const inner_html = pending
			? `<span style="
					display:block;
					background:var(--alert-bg-warning, var(--bg-yellow, #fef9c3));
					color:var(--alert-text-warning, var(--text-on-yellow, #854d0e));
					border-left:3px solid var(--yellow-500, #facc15);
					padding:2px 6px;
					border-radius:2px;
					cursor:cell;
			   " title="${__("Unsaved — click Save Changes to apply")}">
				   ${display || empty}
			   </span>`
			: `<span style="cursor:cell;" title="${__("Click to edit")}">${display || empty}</span>`;

		let $target = $cell.find(".dt-cell__content");
		if (!$target.length) {
			$target = $('<div class="dt-cell__content"></div>');
			$cell.prepend($target);
		}
		$target.html(inner_html);
	},

	formatter: function (value, row, column, data, default_formatter) {
		const me = frappe.query_reports["SO Approval TAT"];
		if (data && column.fieldname === "remark") {
			const so = data.sales_order;
			const is_pending = me && me._pending_changes && me._pending_changes[so] !== undefined;
			const val = is_pending ? me._pending_changes[so] : (data.remark || "");
			const display = frappe.utils.escape_html(val || "");
			const empty = `<span style="color:var(--text-muted);">${__("User Entry")}</span>`;

			if (is_pending) {
				return `<span style="
					display:block;
					background:var(--alert-bg-warning, var(--bg-yellow, #fef9c3));
					color:var(--alert-text-warning, var(--text-on-yellow, #854d0e));
					border-left:3px solid var(--yellow-500, #facc15);
					padding:2px 6px;
					border-radius:2px;
					cursor:cell;
				" title="${__("Unsaved — click Save Changes to apply")}">
					${display || empty}
				</span>`;
			}

			return `<span style="cursor:cell;" title="${__("Click to edit")}">${display || empty}</span>`;
		}

		value = default_formatter(value, row, column, data);
		if (data && column.fieldname === "pending_approval_days" && data.pending_approval_days > 0) {
			value = `<span style="color:var(--red-500);font-weight:600">${value}</span>`;
		}
		return value;
	},
};