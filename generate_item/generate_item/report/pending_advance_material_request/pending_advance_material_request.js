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

	_pending_changes: {},
	_save_btn: null,

	onload: function(report) {
		const me = frappe.query_reports["Pending Advance Material Request"];
		me._report = report;
		me._pending_changes = {};

		me._save_btn = report.page.add_inner_button(__("Save Changes"), function() {
			me._save_all_changes();
		});
		me._update_save_button();

		// Find the Production Plan column index first
		setTimeout(function() {
			me._detect_pp_column();
			me._setup_click_handler();
		}, 800);

		// Re-attach on table refresh
		me._observer = new MutationObserver(function() {
			setTimeout(function() {
				me._detect_pp_column();
				me._setup_click_handler();
			}, 300);
		});
		
		const main = report.page.main[0];
		if (main) {
			me._observer.observe(main, { childList: true, subtree: true });
		}
	},

	_detect_pp_column: function() {
		const me = frappe.query_reports["Pending Advance Material Request"];
		const headers = document.querySelectorAll('.dt-header .dt-cell__content');
		
		// Reset
		me._pp_col_index = null;
		
		headers.forEach(function(header, i) {
			const text = header.textContent.trim();
			// Match exactly "Production Plan"
			if (text === 'Production Plan') {
				me._pp_col_index = i;
			}
		});

		// If still not found, try finding the parent dt-cell index
		if (me._pp_col_index === null || me._pp_col_index === undefined) {
			const headerCells = document.querySelectorAll('.dt-header .dt-cell');
			headerCells.forEach(function(cell, i) {
				const text = cell.textContent.trim();
				if (text === 'Production Plan') {
					me._pp_col_index = parseInt(cell.getAttribute('data-col-index'));
				}
			});
		}

		// Last resort: hardcode based on your column order (9th column = index 8)
		if (me._pp_col_index === null || me._pp_col_index === undefined) {
			me._pp_col_index = 8;
		}

		console.log('PP Column Index:', me._pp_col_index);
	},

	_setup_click_handler: function() {
		const me = frappe.query_reports["Pending Advance Material Request"];
		
		if (me._pp_col_index === null || me._pp_col_index === undefined) return;

		// Remove old handlers
		$(me._report.page.main).off('click.pphandler');

		// Attach new handler using jQuery delegation
		$(me._report.page.main).on('click.pphandler', '.dt-cell', function(e) {
			const $cell = $(this);
			const colIdx = parseInt($cell.attr('data-col-index'));

			// STRICT check: only trigger for Production Plan column
			if (colIdx !== me._pp_col_index) return;

			const $row = $cell.closest('.dt-row');
			const rowIdx = parseInt($row.attr('data-row-index'));
			if (isNaN(rowIdx)) return;

			const rowData = me._report.data && me._report.data[rowIdx];
			if (!rowData || !rowData.name) return;

			if (!rowData.batch_no) {
				frappe.show_alert({
					message: __("Batch No is required to link Production Plan."),
					indicator: "red"
				}, 5);
				return;
			}

			const pendingKey = `${rowData.name}::production_plan`;
			const currentValue = me._pending_changes[pendingKey]
				? me._pending_changes[pendingKey].new_value
				: (rowData.production_plan || "");

			// Open dialog
			const dialog = new frappe.ui.Dialog({
				title: __('Select Production Plan'),
				fields: [
					{
						fieldname: 'production_plan',
						label: __('Production Plan'),
						fieldtype: 'Link',
						options: 'Production Plan',
						default: currentValue,
						get_query: function() {
							return {
								query: "generate_item.generate_item.report.pending_advance_material_request.pending_advance_material_request.production_plan_query",
								filters: { batch_no: rowData.batch_no }
							};
						}
					},
					{
						fieldname: 'info',
						fieldtype: 'HTML',
						options: `
							<div style="background:#f0f9ff;border-left:3px solid #3b82f6;padding:10px 14px;border-radius:4px;margin-top:8px;font-size:13px;">
								<div><strong>${__('Item')}:</strong> ${frappe.utils.escape_html(rowData.item_code || '')}</div>
								<div><strong>${__('Batch')}:</strong> ${frappe.utils.escape_html(rowData.batch_no || '')}</div>
								<div><strong>${__('Qty')}:</strong> ${rowData.qty || ''}</div>
							</div>
						`
					}
				],
				primary_action_label: __('Update'),
				primary_action: function(values) {
					const newValue = values.production_plan || "";
					const key = `${rowData.name}::production_plan`;
					const original = rowData.production_plan || "";

					if (newValue && newValue !== original) {
						me._pending_changes[key] = {
							row_name: rowData.name,
							material_request: rowData.material_request,
							new_value: newValue
						};
					} else {
						delete me._pending_changes[key];
					}

					rowData.production_plan = newValue;
					me._update_save_button();
					dialog.hide();
					me._report.refresh();
				}
			});

			dialog.show();
		});
	},

	_update_save_button: function() {
		const me = frappe.query_reports["Pending Advance Material Request"];
		if (!me._save_btn) return;

		const count = Object.keys(me._pending_changes).length;
		if (count > 0) {
			me._save_btn.html(`<i class="fa fa-save mr-1"></i>${__("Save Changes")} (${count})`)
				.removeClass("btn-default").addClass("btn-warning");
		} else {
			me._save_btn.html(__("Save Changes")).removeClass("btn-warning").addClass("btn-default");
		}
	},

	_save_all_changes: function() {
		const me = frappe.query_reports["Pending Advance Material Request"];
		const keys = Object.keys(me._pending_changes);
		if (!keys.length) {
			frappe.show_alert({ message: __("No pending changes to save."), indicator: "blue" }, 3);
			return;
		}

		const updates = Object.values(me._pending_changes).map(function(c) {
			return { name: c.row_name, production_plan: c.new_value };
		});

		frappe.call({
			method: "generate_item.generate_item.report.pending_advance_material_request.pending_advance_material_request.save_production_plan_changes",
			args: { updates: updates },
			callback: function(r) {
				if (r.message && r.message.status === "success") {
					me._pending_changes = {};
					me._update_save_button();
					frappe.show_alert({ message: __(r.message.message), indicator: "green" }, 5);
					me._report.refresh();
				}
			}
		});
	},

	formatter: function(value, row, column, data, default_formatter) {
		const me = frappe.query_reports["Pending Advance Material Request"];
		value = default_formatter(value, row, column, data);

		if (data && data.name && me._pending_changes) {
			const pending_key = `${data.name}::${column.fieldname}`;
			if (me._pending_changes[pending_key]) {
				const display = frappe.utils.escape_html(me._pending_changes[pending_key].new_value || "");
				return `<span style="display:block;background:#fef9c3;border-left:3px solid #facc15;padding:2px 6px;border-radius:2px;">${display || '—'}</span>`;
			}
		}

		if (column.fieldname === "material_request") {
			value = `<span style="font-weight:600;color:#2563eb;">${value}</span>`;
		}
		if (column.fieldname === "qty") {
			value = `<span style="font-weight:bold;color:#dc2626;">${value}</span>`;
		}
		if (column.fieldname === "batch_no" && data && data.batch_no) {
			value = `<span style="font-weight:500;color:#059669;">${value}</span>`;
		}
		if (column.fieldname === "production_plan") {
			if (data && data.production_plan) {
				value = `<span style="font-weight:500;color:#7c3aed;cursor:pointer;">${value}</span>`;
			} else {
				value = `<span style="color:#94a3b8;cursor:pointer;">${__('Click to add')}</span>`;
			}
		}

		return value;
	}
};