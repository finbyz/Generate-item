// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt

frappe.query_reports["Customer Complaint Register"] = {

	// ─── EDITABLE FIELDS CONFIG ───────────────────────────────────────────────
	EDITABLE_FIELDS: {
		"custom_complaint_status": {
			type: "select",
			options: ["Open", "Action in Progress", "Close"],
			label: "Complaint Status",
			empty_label: "Select Status",
		},
		"custom_responsible_department": {
			type: "text",
			label: "Responsible Department",
			empty_label: "Enter Dept",
		},
		"custom_site": {
			type: "text",
			label: "Site",
			empty_label: "Enter Site",
		},
		"custom_action_date": {
			type: "date",
			label: "Action Date",
			empty_label: "Set Date",
		},
		"custom_action_remarks": {
			type: "text",
			label: "Action Decided / Remarks",
			empty_label: "Enter Action",
		},
		"custom_final_action_remarks": {
			type: "text",
			label: "Final Status / Remark",
			empty_label: "Enter Final Status",
		},
		"custom_ssv_visiting_engineer": {
			type: "text",
			label: "SSV Visiting Engineer",
			empty_label: "Enter Engineer",
		},
		"custom_visit_schedule_date": {
			type: "date",
			label: "Visit Schedule Date",
			empty_label: "Set Date",
		},
		"custom_visit_schedule_notes": {
			type: "text",
			label: "Visit Schedule Notes",
			empty_label: "Enter Notes",
		},
	},

	// ─── FILTERS ─────────────────────────────────────────────────────────────
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -12),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
		},
		{
			fieldname: "complaint_status",
			label: __("Complaint Status"),
			fieldtype: "Select",
			options: ["", "Open", "Action in Progress", "Close"].join("\n"),
		},
		{
			fieldname: "status",
			label: __("Standard Issue Status"),
			fieldtype: "Select",
			options: ["", "Open", "Replied", "On Hold", "Resolved", "Closed"].join("\n"),
		},
		{
			fieldname: "priority",
			label: __("Priority"),
			fieldtype: "Link",
			options: "Issue Priority",
		},
		{
			fieldname: "issue_type",
			label: __("Issue Type"),
			fieldtype: "Link",
			options: "Issue Type",
		},
		{
			fieldname: "sales_order",
			label: __("Sales Order"),
			fieldtype: "Link",
			options: "Sales Order",
		},
		{
			fieldname: "responsible_department",
			label: __("Responsible Department"),
			fieldtype: "Data",
		},
		{
			fieldname: "site",
			label: __("Site"),
			fieldtype: "Data",
		},
		{
			fieldname: "fs_number",
			label: __("FS Number"),
			fieldtype: "Data",
		},
		{
			fieldname: "valve",
			label: __("Valve"),
			fieldtype: "Data",
		},
		{
			fieldname: "valve_size",
			label: __("Valve Size"),
			fieldtype: "Data",
		},
		{
			fieldname: "valve_class",
			label: __("Valve Class"),
			fieldtype: "Data",
		},
		{
			fieldname: "actuator_make",
			label: __("Actuator Make"),
			fieldtype: "Data",
		},
		{
			fieldname: "project",
			label: __("Project"),
			fieldtype: "Data",
		},
	],

	// ─── STATE ────────────────────────────────────────────────────────────────
	_report: null,
	_pending_changes: {},    // { [issue_id]: { [fieldname]: new_value } }
	_original_values: {},    // { [`${issue_id}::${fieldname}`]: original_value }
	_save_btn: null,
	_discard_btn: null,

	// ─── LIFECYCLE ────────────────────────────────────────────────────────────
	onload(report) {
		const me = frappe.query_reports["Customer Complaint Register"];
		me._report = report;
		me._pending_changes = {};
		me._original_values = {};

		// Inject custom styles for editable cells, hover states, and staged indicators
		if (!document.getElementById("ccr-custom-styles")) {
			$(`
				<style id="ccr-custom-styles">
					.dt-cell--editable-col {
						cursor: pointer !important;
						transition: background-color 0.15s ease;
					}
					.dt-cell--editable-col:hover {
						background-color: var(--hover-accent-bg, rgba(59, 130, 246, 0.08)) !important;
						box-shadow: inset 0 0 0 1px var(--primary, #3b82f6);
					}
					.ccr-staged-cell {
						display: block;
						background: var(--alert-bg-warning, #fef9c3) !important;
						color: var(--alert-text-warning, #854d0e) !important;
						border-left: 3px solid var(--yellow-500, #facc15) !important;
						padding: 2px 6px;
						border-radius: 2px;
						cursor: pointer;
						font-weight: 500;
					}
					.ccr-editable-cell {
						cursor: pointer;
						display: inline-flex;
						align-items: center;
						width: 100%;
					}
					.ccr-editable-cell .ccr-pencil-icon {
						font-size: 10px;
						opacity: 0.35;
						margin-left: 5px;
					}
					.dt-cell:hover .ccr-editable-cell .ccr-pencil-icon {
						opacity: 0.9;
						color: var(--primary, #1b66c9);
					}
					.ccr-empty-placeholder {
						color: var(--text-muted, #8d99a6);
						font-style: italic;
						font-size: 11px;
						cursor: pointer;
						display: inline-flex;
						align-items: center;
					}
					.ccr-empty-placeholder .ccr-pencil-icon {
						font-size: 10px;
						opacity: 0.5;
						margin-right: 4px;
					}
					.inline-editor[type="date"]::-webkit-calendar-picker-indicator {
						cursor: pointer;
						opacity: 0.9;
						padding: 2px;
					}
					[data-theme="dark"] .ccr-staged-cell {
						background: #3b3211 !important;
						color: #fef08a !important;
						border-left-color: #eab308 !important;
					}
				</style>
			`).appendTo("head");
		}

		// Helper indicator banner in the report header
		report.page.set_indicator(
			__("Columns marked with ✎ can be clicked to edit inline"),
			"blue"
		);

		// ── Toolbar Buttons ───────────────────────────────────────────────────
		// 1. New Complaint button (directly redirect to full Issue form without quick-entry popup)
		report.page.add_inner_button(__("New Complaint"), () => {
			const default_customer = report.get_filter_value("customer");
			const default_so = report.get_filter_value("sales_order");
			const prefill = {};
			if (default_customer) prefill.customer = default_customer;
			if (default_so) prefill.custom_sales_order = default_so;

			frappe.route_options = prefill;
			frappe.model.with_doctype("Issue", () => {
				const doc = frappe.model.get_new_doc("Issue");
				if (prefill.customer) doc.customer = prefill.customer;
				if (prefill.custom_sales_order) doc.custom_sales_order = prefill.custom_sales_order;
				frappe.set_route("Form", "Issue", doc.name);
			});
		});

		// 2. Discard Changes button (hidden when clean)
		me._discard_btn = report.page.add_inner_button(__("Discard Changes"), () => {
			me._discard_all_changes();
		});

		// 3. Save Changes button
		me._save_btn = report.page.add_inner_button(__("Save Changes"), () => {
			me._save_all_changes();
		});

		me._update_action_buttons();

		// ── Cell Click Listener ───────────────────────────────────────────────
		report.$report.off("click.ccr_edit").on("click.ccr_edit", ".dt-cell", function (e) {
			if ($(e.target).closest(".inline-editor, .ccr-editor, select, input").length) {
				return;
			}
			me._on_cell_click(e, $(this));
		});
	},

	// ─── CELL CLICK HANDLER ───────────────────────────────────────────────────
	_on_cell_click(e, $cell) {
		const me = frappe.query_reports["Customer Complaint Register"];
		if (!me._report || !me._report.datatable) return;

		const col_idx = parseInt($cell.attr("data-col-index"), 10);
		const row_idx = parseInt($cell.attr("data-row-index"), 10);
		if (isNaN(col_idx) || isNaN(row_idx)) return;

		const col = me._report.datatable.getColumn(col_idx);
		if (!col) return;

		const fieldname = col.fieldname || col.id;
		const field_conf = me.EDITABLE_FIELDS[fieldname];
		if (!field_conf && !col.editable) return;

		const row_data = me._report.data[row_idx];
		if (!row_data || !row_data.name) return;

		const issue_id = row_data.name;
		const config = field_conf || { type: "text", label: col.name || fieldname };

		// Track original value if not already tracked
		const original_key = `${issue_id}::${fieldname}`;
		if (!(original_key in me._original_values)) {
			me._original_values[original_key] = row_data[fieldname] ?? "";
		}

		// Current value (prefer staged change if present)
		const cur_value = (me._pending_changes[issue_id] && me._pending_changes[issue_id][fieldname] !== undefined)
			? me._pending_changes[issue_id][fieldname]
			: (row_data[fieldname] ?? "");

		me._render_editor($cell, issue_id, fieldname, config, cur_value, (new_val) => {
			me._stage_change($cell, row_data, issue_id, fieldname, new_val);
		});
	},

	// ─── EDITOR RENDERER ──────────────────────────────────────────────────────
	_render_editor($cell, issue_id, fieldname, config, cur_value, on_save) {
		$cell.css("position", "relative");

		// Close any other open editors
		$(document).trigger("close_ccr_inline_editor");

		let closed = false;
		const close_editor = (should_commit, custom_val) => {
			if (closed) return;
			closed = true;
			$(document).off("pointerdown.ccr_inline_editor close_ccr_inline_editor");
			if (should_commit && $editor) {
				const val = custom_val !== undefined ? custom_val : $editor.val();
				const trimmed = (val !== null && val !== undefined) ? String(val).trim() : "";
				if (trimmed !== String(cur_value ?? "").trim()) {
					on_save(trimmed);
				}
			}
			if ($editor) $editor.remove();
		};

		$(document).on("close_ccr_inline_editor", () => close_editor(true));

		let $editor;

		if (config.type === "select") {
			// Dropdown Select Editor
			const opts = (config.options || []).map(opt =>
				`<option value="${frappe.utils.escape_html(opt)}" ${opt === cur_value ? "selected" : ""}>${frappe.utils.escape_html(opt || __("-- Select --"))}</option>`
			).join("");

			$editor = $(`
				<select class="ccr-editor inline-editor form-control input-sm" style="
					position:absolute; top:0; left:0; width:100%; height:100%;
					z-index:100; font-size:12px; border:2px solid var(--primary, #3b82f6);
					background:var(--control-bg, #ffffff); color:var(--text-color, #1f272e); padding:2px;
					border-radius:3px; outline:none; cursor:pointer;
					box-shadow: 0 2px 6px rgba(0,0,0,0.15);
				">${opts}</select>
			`);

			$editor.on("change", function () {
				close_editor(true, $(this).val());
			});
			$editor.on("keydown", function (e) {
				if (e.key === "Enter") { e.preventDefault(); close_editor(true, $(this).val()); }
				if (e.key === "Escape") { e.preventDefault(); close_editor(false); }
			});

		} else if (config.type === "date") {
			// Date Picker Editor
			const is_dark = document.documentElement.getAttribute("data-theme") === "dark"
				|| frappe.ui.color_mode === "dark";
			const color_scheme = is_dark ? "dark" : "light";

			$editor = $(`
				<input type="date" class="ccr-editor inline-editor form-control input-sm" value="${cur_value || ""}" style="
					position:absolute; top:0; left:0; width:100%; height:100%;
					z-index:100; font-size:12px; border:2px solid var(--primary, #3b82f6);
					background:var(--control-bg, #ffffff); color:var(--text-color, #1f272e);
					color-scheme:${color_scheme} !important; padding:2px 4px;
					border-radius:3px; outline:none; cursor:pointer;
					box-shadow: 0 2px 6px rgba(0,0,0,0.15);
				"/>
			`);

			$editor.on("change", function () {
				close_editor(true, $(this).val());
			});
			$editor.on("keydown", (e) => {
				if (e.key === "Enter") { e.preventDefault(); close_editor(true, $editor.val()); }
				if (e.key === "Escape") { e.preventDefault(); close_editor(false); }
			});

			$editor.on("click", function () {
				try {
					if (typeof this.showPicker === "function") this.showPicker();
				} catch (err) {}
			});

		} else {
			// Text / Small Text Editor
			$editor = $(`
				<input type="text" class="ccr-editor inline-editor form-control input-sm" value="${frappe.utils.escape_html(cur_value)}" style="
					position:absolute; top:0; left:0; width:100%; height:100%;
					z-index:100; font-size:12px; border:2px solid var(--primary, #3b82f6);
					background:var(--control-bg, #ffffff); color:var(--text-color, #1f272e); padding:2px 6px;
					border-radius:3px; outline:none;
					box-shadow: 0 2px 6px rgba(0,0,0,0.15);
				"/>
			`);

			$editor.on("keydown", (e) => {
				if (e.key === "Enter") { e.preventDefault(); close_editor(true, $editor.val()); }
				if (e.key === "Escape") { e.preventDefault(); close_editor(false); }
			});
		}

		// Prevent events from bubbling to .dt-cell
		$editor.on("click pointerdown mousedown", (e) => e.stopPropagation());

		$cell.append($editor);
		$editor.focus();
		if (config.type === "text") $editor.select();

		if (config.type === "date") {
			try {
				if (typeof $editor[0].showPicker === "function") $editor[0].showPicker();
			} catch (err) {}
		}

		// Close when clicking anywhere outside
		setTimeout(() => {
			$(document).on("pointerdown.ccr_inline_editor", (e) => {
				if (!$(e.target).closest($cell).length) {
					close_editor(true, $editor.val());
				}
			});
		}, 100);
	},

	// ─── STAGE CHANGE ─────────────────────────────────────────────────────────
	_stage_change($cell, row_data, issue_id, fieldname, new_val) {
		const me = frappe.query_reports["Customer Complaint Register"];
		const original_key = `${issue_id}::${fieldname}`;
		const original_val = me._original_values[original_key] ?? "";

		if (new_val === original_val) {
			// Reverted back to original
			if (me._pending_changes[issue_id]) {
				delete me._pending_changes[issue_id][fieldname];
				if (!Object.keys(me._pending_changes[issue_id]).length) {
					delete me._pending_changes[issue_id];
				}
			}
			row_data[fieldname] = original_val;
			me._paint_cell($cell, fieldname, original_val, false /* is_pending */);
		} else {
			// Changed
			if (!me._pending_changes[issue_id]) me._pending_changes[issue_id] = {};
			me._pending_changes[issue_id][fieldname] = new_val;
			row_data[fieldname] = new_val;
			me._paint_cell($cell, fieldname, new_val, true /* is_pending */);
		}

		me._update_action_buttons();
	},

	_paint_cell($cell, fieldname, value, is_pending) {
		const me = frappe.query_reports["Customer Complaint Register"];
		const field_conf = me.EDITABLE_FIELDS[fieldname] || {};
		const empty_label = field_conf.empty_label || __("Edit");
		const val_str = value !== null && value !== undefined ? String(value).trim() : "";
		const display = frappe.utils.escape_html(val_str);

		let inner_html = "";
		if (is_pending) {
			inner_html = `
				<span class="ccr-staged-cell" title="${__('Unsaved — click Save Changes to apply')}">
					${display || `<span class="text-muted">—</span>`}
					<span class="badge badge-warning" style="font-size:9px; vertical-align:middle; margin-left:4px;">${__('Unsaved')}</span>
				</span>
			`;
		} else if (!val_str) {
			inner_html = `
				<span class="ccr-empty-placeholder" title="${__('Click to edit')}">
					<i class="fa fa-pencil ccr-pencil-icon"></i>${empty_label}
				</span>
			`;
		} else {
			inner_html = `
				<span class="ccr-editable-cell" title="${__('Click to edit')}">
					${display} <i class="fa fa-pencil ccr-pencil-icon"></i>
				</span>
			`;
		}

		let $target = $cell.find(".dt-cell__content");
		if (!$target.length) {
			$target = $('<div class="dt-cell__content"></div>');
			$cell.prepend($target);
		}
		$target.html(inner_html);
	},

	// ─── ACTION BUTTONS STATE ─────────────────────────────────────────────────
	_count_pending_changes() {
		const me = frappe.query_reports["Customer Complaint Register"];
		let count = 0;
		for (const issue_id in me._pending_changes) {
			count += Object.keys(me._pending_changes[issue_id]).length;
		}
		return count;
	},

	_update_action_buttons() {
		const me = frappe.query_reports["Customer Complaint Register"];
		const count = me._count_pending_changes();

		if (me._save_btn) {
			if (count > 0) {
				me._save_btn
					.html(`<i class="fa fa-save mr-1"></i>${__("Save Changes")} (${count})`)
					.removeClass("btn-default")
					.addClass("btn-warning")
					.prop("disabled", false);
			} else {
				me._save_btn
					.html(__("Save Changes"))
					.removeClass("btn-warning")
					.addClass("btn-default")
					.prop("disabled", true);
			}
		}

		if (me._discard_btn) {
			if (count > 0) {
				me._discard_btn.show();
			} else {
				me._discard_btn.hide();
			}
		}
	},

	// ─── DISCARD CHANGES ──────────────────────────────────────────────────────
	_discard_all_changes() {
		const me = frappe.query_reports["Customer Complaint Register"];
		if (!me._count_pending_changes()) return;

		frappe.confirm(
			__("Are you sure you want to discard all unsaved changes?"),
			() => {
				me._pending_changes = {};
				me._original_values = {};
				me._update_action_buttons();
				me._report.refresh();
				frappe.show_alert({
					message: __("Unsaved changes discarded."),
					indicator: "blue",
				});
			}
		);
	},

	// ─── SAVE ALL CHANGES ─────────────────────────────────────────────────────
	async _save_all_changes() {
		const me = frappe.query_reports["Customer Complaint Register"];
		const count = me._count_pending_changes();

		if (!count) {
			frappe.show_alert({ message: __("No changes to save."), indicator: "orange" }, 3);
			return;
		}

		if (me._save_btn) {
			me._save_btn.prop("disabled", true).html(
				`<i class="fa fa-spinner fa-spin mr-1"></i>${__("Saving…")}`
			);
		}

		frappe.dom.freeze(__("Saving complaint changes..."));

		try {
			const res = await frappe.call({
				method: "generate_item.generate_item.report.customer_complaint_register.customer_complaint_register.save_complaint_register_changes",
				args: { changes: me._pending_changes },
			});

			frappe.dom.unfreeze();
			if (me._save_btn) me._save_btn.prop("disabled", false);

			const message = res.message || {};
			if (message.success) {
				const updatedCount = (message.updated || []).length;
				me._pending_changes = {};
				me._original_values = {};
				me._update_action_buttons();
				frappe.show_alert({
					message: __("Successfully saved {0} complaint(s).", [updatedCount]),
					indicator: "green",
				}, 4);
				me._report.refresh();
			} else {
				const errors = message.errors || [];
				const errMsg = errors.length ? errors[0].error : __("An unexpected error occurred.");
				frappe.msgprint({
					title: __("Save Failed"),
					message: __("Could not save complaint changes:<br><br><strong>{0}</strong>", [errMsg]),
					indicator: "red",
				});
				me._update_action_buttons();
				me._report.refresh();
			}
		} catch (err) {
			frappe.dom.unfreeze();
			if (me._save_btn) me._save_btn.prop("disabled", false);
			me._update_action_buttons();
			console.error("Save complaint changes failed:", err);
			frappe.msgprint({
				title: __("Server Error"),
				message: err.message || __("A server error occurred while saving complaint changes."),
				indicator: "red",
			});
		}
	},

	// ─── FORMATTER ────────────────────────────────────────────────────────────
	formatter(value, row, column, data, default_formatter) {
		const me = frappe.query_reports["Customer Complaint Register"];
		let formatted = default_formatter(value, row, column, data);
		if (!data || !data.name) return formatted;

		const issue_id = data.name;
		const fieldname = column.fieldname || column.id;

		// 1. Pending / Unsaved change takes highest display priority
		if (me._pending_changes && me._pending_changes[issue_id] && me._pending_changes[issue_id][fieldname] !== undefined) {
			const pending_val = me._pending_changes[issue_id][fieldname];
			const display = frappe.utils.escape_html(pending_val || "");
			return `
				<span class="ccr-staged-cell" title="${__('Unsaved — click Save Changes to apply')}">
					${display || `<span class="text-muted">—</span>`}
					<span class="badge badge-warning" style="font-size:9px; vertical-align:middle; margin-left:4px;">${__('Unsaved')}</span>
				</span>
			`;
		}

		// 2. Complaint Status Pill styling
		if (fieldname === "custom_complaint_status" && value) {
			let pill_color = "red";
			if (value === "Action in Progress") pill_color = "orange";
			if (value === "Close") pill_color = "green";
			return `
				<span class="ccr-editable-cell" title="${__('Click to edit')}">
					<span class="indicator-pill ${pill_color}">${value}</span>
					<i class="fa fa-pencil ccr-pencil-icon"></i>
				</span>
			`;
		}

		// 3. Any editable column
		const field_conf = me.EDITABLE_FIELDS[fieldname];
		if (column.editable || field_conf) {
			const empty_label = field_conf ? field_conf.empty_label : __("Edit");
			const val_str = value !== null && value !== undefined ? String(value).trim() : "";
			if (!val_str) {
				return `
					<span class="ccr-empty-placeholder" title="${__('Click to edit')}">
						<i class="fa fa-pencil ccr-pencil-icon"></i>${empty_label}
					</span>
				`;
			}
			return `
				<span class="ccr-editable-cell" title="${__('Click to edit')}">
					${formatted} <i class="fa fa-pencil ccr-pencil-icon"></i>
				</span>
			`;
		}

		return formatted;
	},
};
