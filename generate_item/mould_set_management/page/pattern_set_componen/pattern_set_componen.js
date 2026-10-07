// Pattern Set Component Warehouse Availability
// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt

frappe.pages['pattern-set-componen'].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Pattern Set Component Warehouse Availability'),
		single_column: true,
	});
	wrapper.page = page;

	if (frappe.breadcrumbs && frappe.breadcrumbs.add) {
		frappe.breadcrumbs.add({
			type: 'Custom',
			label: __('Mould Set Management'),
			route: '#workspace/Mould Set Management',
		});
	}

	page.set_title(__('Pattern Set Component Warehouse Availability'));
	document.title = __('Pattern Set Component Warehouse Availability') + ' - Frappe';
	wrapper.psca = new PatternSetComponentAvailability(page, wrapper);
};

frappe.pages['pattern-set-componen'].on_page_show = function (wrapper) {
	if (frappe.breadcrumbs && frappe.breadcrumbs.add) {
		frappe.breadcrumbs.add({
			type: 'Custom',
			label: __('Mould Set Management'),
			route: '#workspace/Mould Set Management',
		});
	}
	if (wrapper.page && wrapper.page.set_title) {
		wrapper.page.set_title(__('Pattern Set Component Warehouse Availability'));
	}
	document.title = __('Pattern Set Component Warehouse Availability') + ' - Frappe';
	if (wrapper.psca && wrapper.psca.initialized) {
		wrapper.psca.refresh();
	}
};

class PatternSetComponentAvailability {
	constructor(page, wrapper) {
		this.page = page;
		this.wrapper = wrapper;
		this.initialized = false;

		this.state = {
			filters: {
				pattern_set: null,
				component_item: null,
				warehouse: null,
				type_of_valve: null,
				size: null,
				class: null,
				show_zero_stock: 0,
			},
			hierarchy: [],
			summary: {
				total_pattern_sets: 0,
				total_groups: 0,
				total_components: 0,
				total_warehouses: 0,
				components_with_stock: 0,
				components_without_stock: 0,
				total_stock_qty: 0,
				common_warehouse_stock: 0,
			},
			expanded_groups: new Set(),
			loading: false,
		};

		this.api_method = 'generate_item.mould_set_management.page.pattern_set_componen.pattern_set_componen.get_pattern_set_component_availability';
		this.filter_options_method = 'generate_item.mould_set_management.page.pattern_set_componen.pattern_set_componen.get_filter_options';
		this.export_method = '/api/method/generate_item.mould_set_management.page.pattern_set_componen.pattern_set_componen.export_availability_excel';

		this.setup_page();
		this.render_shell();
		this.init_filters();
		this.load_filter_options();
		this.bind_events();
		this.fetch_data().then(() => {
			this.initialized = true;
		});
	}

	setup_page() {
		this.page.clear_actions();
		this.page.clear_inner_toolbar();
		this.page.set_title(__('Pattern Set Component Warehouse Availability'));
		this.page.set_title_sub(__('Stock Availability Analysis by Pattern Set, Warehouse & Components'));
		document.title = __('Pattern Set Component Warehouse Availability') + ' - Frappe';
	}

	render_shell() {
		const html = `
			<div class="psca-container">
				<!-- Header Card -->
				<div class="psca-hero">
					<div class="psca-hero-left">
						<div class="psca-hero-icon">
							<i class="fa fa-cubes"></i>
						</div>
						<div class="psca-hero-title-group">
							<h1>
								${__('Pattern Set Component Warehouse Availability')}
								<span class="psca-hero-badge">
									<span class="psca-live-dot"></span>
									${__('Live Stock')}
								</span>
							</h1>
							<p>${__('Warehouse-wise breakdown across Pattern Sets and all constituent component items')}</p>
						</div>
					</div>
				</div>

				<!-- Summary KPI Cards -->
				<div class="psca-summary-grid">
					<div class="psca-kpi-card kpi-blue">
						<div class="psca-kpi-label">
							<span>${__('Pattern Sets')}</span>
							<i class="fa fa-cubes"></i>
						</div>
						<div class="psca-kpi-val" data-kpi="total_pattern_sets">0</div>
					</div>
					<div class="psca-kpi-card kpi-indigo">
						<div class="psca-kpi-label">
							<span>${__('Warehouse Groups')}</span>
							<i class="fa fa-building-o"></i>
						</div>
						<div class="psca-kpi-val" data-kpi="total_groups">0</div>
					</div>
					<div class="psca-kpi-card kpi-teal">
						<div class="psca-kpi-label">
							<span>${__('Components')}</span>
							<i class="fa fa-cogs"></i>
						</div>
						<div class="psca-kpi-val" data-kpi="total_components">0</div>
					</div>
					<div class="psca-kpi-card kpi-green">
						<div class="psca-kpi-label">
							<span>${__('With Stock')}</span>
							<i class="fa fa-check-circle-o"></i>
						</div>
						<div class="psca-kpi-val" data-kpi="components_with_stock">0</div>
					</div>
					<div class="psca-kpi-card kpi-amber">
						<div class="psca-kpi-label">
							<span>${__('Without Stock')}</span>
							<i class="fa fa-exclamation-circle"></i>
						</div>
						<div class="psca-kpi-val" data-kpi="components_without_stock">0</div>
					</div>
					<div class="psca-kpi-card psca-kpi-purple">
						<div class="psca-kpi-label">
							<span>${__('Common WH Stock')}</span>
							<i class="fa fa-database"></i>
						</div>
						<div class="psca-kpi-val" data-kpi="common_warehouse_stock">0</div>
					</div>
				</div>

				<!-- Filters Section: 3 by 3 Grid Layout -->
				<div class="psca-filter-panel">
					<div class="psca-filter-grid">
						<!-- Row 1: Pattern Set, Warehouse, Component Item -->
						<div class="psca-filter-item">
							<label class="psca-filter-label">${__('Pattern Set')}</label>
							<div class="psca-control-pattern-set"></div>
						</div>
						<div class="psca-filter-item">
							<label class="psca-filter-label">${__('Warehouse')}</label>
							<div class="psca-control-warehouse"></div>
						</div>
						<div class="psca-filter-item">
							<label class="psca-filter-label">${__('Component Item')}</label>
							<div class="psca-control-component-item"></div>
						</div>

						<!-- Row 2: Type of Valve, Size, Class -->
						<div class="psca-filter-item">
							<label class="psca-filter-label">${__('Type of Valve')}</label>
							<div class="psca-control-type-of-valve"></div>
						</div>
						<div class="psca-filter-item">
							<label class="psca-filter-label">${__('Size')}</label>
							<div class="psca-control-size"></div>
						</div>
						<div class="psca-filter-item">
							<label class="psca-filter-label">${__('Class')}</label>
							<div class="psca-control-class"></div>
						</div>
					</div>

					<div class="psca-filter-actions">
						<label class="psca-checkbox-wrapper">
							<input type="checkbox" class="psca-show-zero-stock-cb">
							<span>${__('Show Zero Stock Components')}</span>
						</label>

						<div class="psca-filter-btns">
							<button type="button" class="btn btn-xs btn-default psca-btn-reset-filters">
								<i class="fa fa-undo"></i> ${__('Reset Filters')}
							</button>
							<button type="button" class="btn btn-xs btn-primary psca-btn-refresh ml-2">
								<i class="fa fa-refresh"></i> ${__('Refresh')}
							</button>
						</div>
					</div>
				</div>

				<!-- Action Bar above Table -->
				<div class="psca-table-action-bar">
					<div class="psca-results-badge">
						<span class="psca-results-text">${__('Loading availability data...')}</span>
					</div>
					<div class="psca-table-btns">
						<button type="button" class="btn btn-xs btn-default psca-btn-export-excel mr-2">
							<i class="fa fa-file-excel-o text-success"></i> ${__('Export Excel')}
						</button>
						<button type="button" class="btn btn-xs btn-default psca-btn-expand-all mr-1">
							<i class="fa fa-angle-double-down"></i> ${__('Expand All')}
						</button>
						<button type="button" class="btn btn-xs btn-default psca-btn-collapse-all">
							<i class="fa fa-angle-double-up"></i> ${__('Collapse All')}
						</button>
					</div>
				</div>

				<!-- Table Container: 4 Columns (Pattern Set, Warehouse, QTY, Extra Qty) -->
				<div class="psca-table-container">
					<table class="psca-table">
						<thead>
							<tr>
								<th style="width: 44%;">${__('Pattern Set')}</th>
								<th style="width: 26%;">${__('Warehouse')}</th>
								<th style="width: 15%; text-align: right;">${__('QTY')}</th>
								<th style="width: 15%; text-align: right;">${__('Extra Qty')}</th>
							</tr>
						</thead>
						<tbody class="psca-tbody">
							<tr>
								<td colspan="4" class="psca-empty-state">
									<div class="psca-empty-icon"><i class="fa fa-spinner fa-spin"></i></div>
									<div class="psca-empty-title">${__('Loading Data...')}</div>
								</td>
							</tr>
						</tbody>
					</table>
				</div>
			</div>
		`;

		this.$container = $(html);
		$(this.page.body).empty().append(this.$container);
	}

	init_filters() {
		// 1. Pattern Set Link Field
		this.ps_control = frappe.ui.form.make_control({
			parent: this.$container.find('.psca-control-pattern-set').get(0),
			df: {
				fieldtype: 'Link',
				options: 'Pattern Set',
				fieldname: 'pattern_set',
				placeholder: __('Select Pattern Set...'),
				get_query: () => {
					return {
						filters: {
							docstatus: ['!=', 2],
							disable: 0,
						},
					};
				},
				change: () => {
					const val = this.ps_control.get_value();
					this.state.filters.pattern_set = val || null;
					this.fetch_data();
				},
			},
			render_input: true,
		});

		// 2. Warehouse Link Field (Supports both Group & Leaf Warehouses)
		this.wh_control = frappe.ui.form.make_control({
			parent: this.$container.find('.psca-control-warehouse').get(0),
			df: {
				fieldtype: 'Link',
				options: 'Warehouse',
				fieldname: 'warehouse',
				placeholder: __('Select Warehouse (Group or Leaf)...'),
				get_query: () => {
					return {
						filters: {
							disabled: 0,
						},
					};
				},
				change: () => {
					const val = this.wh_control.get_value();
					this.state.filters.warehouse = val || null;
					this.fetch_data();
				},
			},
			render_input: true,
		});

		// 3. Type of Valve Select Field
		this.valve_control = frappe.ui.form.make_control({
			parent: this.$container.find('.psca-control-type-of-valve').get(0),
			df: {
				fieldtype: 'Select',
				fieldname: 'type_of_valve',
				options: [''],
				placeholder: __('All Valve Types'),
				change: () => {
					const val = this.valve_control.get_value();
					this.state.filters.type_of_valve = val || null;
					this.fetch_data();
				},
			},
			render_input: true,
		});

		// 4. Size Select Field
		this.size_control = frappe.ui.form.make_control({
			parent: this.$container.find('.psca-control-size').get(0),
			df: {
				fieldtype: 'Select',
				fieldname: 'size',
				options: [''],
				placeholder: __('All Sizes'),
				change: () => {
					const val = this.size_control.get_value();
					this.state.filters.size = val || null;
					this.fetch_data();
				},
			},
			render_input: true,
		});

		// 5. Class Select Field
		this.class_control = frappe.ui.form.make_control({
			parent: this.$container.find('.psca-control-class').get(0),
			df: {
				fieldtype: 'Select',
				fieldname: 'class',
				options: [''],
				placeholder: __('All Classes'),
				change: () => {
					const val = this.class_control.get_value();
					this.state.filters.class = val || null;
					this.fetch_data();
				},
			},
			render_input: true,
		});

		// 6. Component Item Link Field
		this.item_control = frappe.ui.form.make_control({
			parent: this.$container.find('.psca-control-component-item').get(0),
			df: {
				fieldtype: 'Link',
				options: 'Item',
				fieldname: 'component_item',
				placeholder: __('Select Component Item...'),
				change: () => {
					const val = this.item_control.get_value();
					this.state.filters.component_item = val || null;
					this.fetch_data();
				},
			},
			render_input: true,
		});
	}

	load_filter_options() {
		frappe.call({
			method: this.filter_options_method,
			callback: (r) => {
				if (r && r.message) {
					const opts = r.message;
					if (opts.types_of_valve && opts.types_of_valve.length) {
						this.set_control_options(this.valve_control, opts.types_of_valve);
					}
					if (opts.sizes && opts.sizes.length) {
						this.set_control_options(this.size_control, opts.sizes);
					}
					if (opts.classes && opts.classes.length) {
						this.set_control_options(this.class_control, opts.classes);
					}
				}
			},
		});
	}

	set_control_options(control, options_list) {
		if (!control) return;
		const options = ['', ...options_list];
		control.df.options = options;
		if (control.$input) {
			const current_val = control.get_value() || '';
			control.$input.empty();
			options.forEach((opt) => {
				control.$input.append($('<option>', {
					value: opt,
					text: opt ? opt : __('All'),
				}));
			});
			control.$input.val(current_val);
		} else if (control.set_df_property) {
			control.set_df_property('options', options);
			control.refresh();
		}
	}

	bind_events() {
		// Show Zero Stock Checkbox
		this.$container.on('change', '.psca-show-zero-stock-cb', (e) => {
			this.state.filters.show_zero_stock = $(e.currentTarget).is(':checked') ? 1 : 0;
			this.fetch_data();
		});

		// Reset Filters Button
		this.$container.on('click', '.psca-btn-reset-filters', () => {
			this.reset_filters();
		});

		// Refresh Button (after Reset Filters)
		this.$container.on('click', '.psca-btn-refresh', () => {
			this.refresh();
		});

		// Export Excel Button
		this.$container.on('click', '.psca-btn-export-excel', () => {
			this.export_excel();
		});

		// Expand All / Collapse All buttons
		this.$container.on('click', '.psca-btn-expand-all', () => {
			this.expand_all();
		});

		this.$container.on('click', '.psca-btn-collapse-all', () => {
			this.collapse_all();
		});

		// Click on Group Row (Pattern Set + Warehouse) to toggle component detail rows
		this.$container.on('click', '.psca-row-group', (e) => {
			if ($(e.target).closest('a').length) return; // allow link navigation
			const group_key = $(e.currentTarget).data('group-key');
			if (group_key) {
				this.toggle_group(group_key);
			}
		});
	}

	reset_filters() {
		this.ps_control.set_value('');
		this.wh_control.set_value('');
		this.valve_control.set_value('');
		this.size_control.set_value('');
		this.class_control.set_value('');
		this.item_control.set_value('');
		this.$container.find('.psca-show-zero-stock-cb').prop('checked', false);

		this.state.filters = {
			pattern_set: null,
			component_item: null,
			warehouse: null,
			type_of_valve: null,
			size: null,
			class: null,
			show_zero_stock: 0,
		};

		this.fetch_data();
	}

	refresh() {
		this.fetch_data();
	}

	fetch_data() {
		this.state.loading = true;
		this.$container.find('.psca-results-text').html(`<i class="fa fa-spinner fa-spin"></i> ${__('Updating availability...')}`);

		return frappe.call({
			method: this.api_method,
			args: {
				pattern_set: this.state.filters.pattern_set,
				component_item: this.state.filters.component_item,
				warehouse: this.state.filters.warehouse,
				type_of_valve: this.state.filters.type_of_valve,
				size: this.state.filters.size,
				class_val: this.state.filters.class,
				show_zero_stock: this.state.filters.show_zero_stock,
			},
			callback: (r) => {
				this.state.loading = false;
				if (r && r.message) {
					this.state.hierarchy = r.message.hierarchy || [];
					this.state.summary = r.message.summary || {};
					// Expand all groups by default
					this.state.expanded_groups.clear();
					(this.state.hierarchy || []).forEach((ps, ps_idx) => {
						(ps.warehouse_groups || []).forEach((wg, wg_idx) => {
							this.state.expanded_groups.add(`${ps_idx}_${wg_idx}`);
						});
					});
					this.update_summary_cards();
					this.render_table();
				}
			},
			error: () => {
				this.state.loading = false;
				this.$container.find('.psca-tbody').html(`
					<tr>
						<td colspan="4" class="psca-empty-state">
							<div class="psca-empty-icon text-danger"><i class="fa fa-exclamation-triangle"></i></div>
							<div class="psca-empty-title">${__('Error Loading Data')}</div>
							<div class="psca-empty-desc">${__('Unable to retrieve stock availability. Please check server logs.')}</div>
						</td>
					</tr>
				`);
			},
		});
	}

	update_summary_cards() {
		const s = this.state.summary;
		this.$container.find('[data-kpi="total_pattern_sets"]').text(this.format_qty(s.total_pattern_sets || 0));
		this.$container.find('[data-kpi="total_groups"]').text(this.format_qty(s.total_groups || 0));
		this.$container.find('[data-kpi="total_components"]').text(this.format_qty(s.total_components || 0));
		this.$container.find('[data-kpi="components_with_stock"]').text(this.format_qty(s.components_with_stock || 0));
		this.$container.find('[data-kpi="components_without_stock"]').text(this.format_qty(s.components_without_stock || 0));
		this.$container.find('[data-kpi="common_warehouse_stock"]').text(this.format_qty(s.common_warehouse_stock || 0));

		const count = (this.state.hierarchy || []).length;
		const group_count = s.total_groups || 0;
		const text = count === 1
			? __('Showing 1 Pattern Set ({0} Warehouse Groups)', [group_count])
			: __('Showing {0} Pattern Sets ({1} Warehouse Groups)', [count, group_count]);
		this.$container.find('.psca-results-text').text(text);
	}

	render_table() {
		const hierarchy = this.state.hierarchy;
		const $tbody = this.$container.find('.psca-tbody').empty();

		if (!hierarchy || !hierarchy.length) {
			let emptyMsg = __('No Pattern Sets found matching the selected filters.');
			if (
				this.state.filters.pattern_set ||
				this.state.filters.component_item ||
				this.state.filters.warehouse ||
				this.state.filters.type_of_valve ||
				this.state.filters.size ||
				this.state.filters.class
			) {
				emptyMsg = __('No records found for the selected filters.');
			}
			$tbody.html(`
				<tr>
					<td colspan="4" class="psca-empty-state">
						<div class="psca-empty-icon"><i class="fa fa-cubes"></i></div>
						<div class="psca-empty-title">${emptyMsg}</div>
						<div class="psca-empty-desc">${__('Try clearing filters or checking zero stock visibility.')}</div>
					</td>
				</tr>
			`);
			return;
		}

		let html = '';

		hierarchy.forEach((ps, ps_idx) => {
			(ps.warehouse_groups || []).forEach((wg, wg_idx) => {
				const group_key = `${ps_idx}_${wg_idx}`;
				const is_expanded = this.state.expanded_groups.has(group_key);
				const caret_class = is_expanded ? 'expanded' : '';
				const child_hidden = is_expanded ? '' : 'psca-hidden';

				const valve_badge = ps.type_of_valve ? `<span class="psca-badge psca-badge-ps">${frappe.utils.escape_html(ps.type_of_valve)}</span>` : '';
				const size_badge = ps.size ? `<span class="psca-badge psca-badge-ps">${frappe.utils.escape_html(ps.size)}</span>` : '';
				const class_badge = ps.class ? `<span class="psca-badge psca-badge-ps">${frappe.utils.escape_html(ps.class)}</span>` : '';
				const pattern_badge = ps.type_of_pattern ? `<span class="psca-badge psca-badge-component">${frappe.utils.escape_html(ps.type_of_pattern)}</span>` : '';

				let wh_badge = '';
				if (wg.is_common) {
					wh_badge = `<span class="psca-badge psca-badge-common-wh ml-1"><i class="fa fa-database"></i> ${__('Common')}</span>`;
				} else if (wg.branch) {
					wh_badge = `<span class="psca-badge psca-badge-branch-wh ml-1"><i class="fa fa-map-marker"></i> ${frappe.utils.escape_html(wg.branch)}</span>`;
				}

				// -------------------------------------------------------------
				// Group Row: Pattern Set + Warehouse (Pattern Set Qty, Extra Qty is blank)
				// -------------------------------------------------------------
				html += `
					<tr class="psca-row-group" data-group-key="${group_key}">
						<td>
							<div class="psca-group-header-cell">
								<span class="psca-caret ${caret_class}"><i class="fa fa-play"></i></span>
								<a href="/app/pattern-set/${encodeURIComponent(ps.pattern_set)}" class="psca-ps-link" onclick="event.stopPropagation();">
									${frappe.utils.escape_html(ps.pattern_set_name || ps.pattern_set)}
								</a>
								<span class="psca-ps-id">(${frappe.utils.escape_html(ps.pattern_set)})</span>
								<div class="psca-tags-inline ml-2">
									${valve_badge} ${size_badge} ${class_badge} ${pattern_badge}
								</div>
							</div>
						</td>
						<td>
							<div class="psca-wh-cell font-weight-bold">
								<i class="fa fa-building-o text-muted mr-1"></i>
								<a href="/app/warehouse/${encodeURIComponent(wg.warehouse)}" class="text-dark" onclick="event.stopPropagation();">
									${frappe.utils.escape_html(wg.warehouse_name || wg.warehouse)}
								</a>
								${wh_badge}
							</div>
						</td>
						<td class="psca-qty-cell psca-group-qty-cell">
							<span class="psca-group-qty-val" title="${__('Pattern Set Quantity (Minimum complete sets possible)')}">
								${this.format_qty(wg.pattern_set_qty !== undefined ? wg.pattern_set_qty : 0)}
							</span>
						</td>
						<td class="psca-qty-cell psca-group-qty-cell">
							<!-- Blank Extra Qty for group row -->
						</td>
					</tr>
				`;

				// -------------------------------------------------------------
				// Component Detail Rows under this Pattern Set + Warehouse group
				// -------------------------------------------------------------
				(wg.components || []).forEach((comp) => {
					const has_stock = comp.has_stock;
					const qty_formatted = this.format_qty(comp.actual_qty);
					const extra_qty_val = comp.extra_qty !== undefined ? comp.extra_qty : 0;
					const extra_qty_formatted = this.format_qty(extra_qty_val);
					const uom_str = comp.uom ? `<span class="psca-uom">${frappe.utils.escape_html(comp.uom)}</span>` : '';

					const drawing_badges = [];
					if (comp.drawing_no) {
						drawing_badges.push(`<span class="psca-drawing-tag" title="${__('Drawing No')}">Drg: ${frappe.utils.escape_html(comp.drawing_no)}${comp.drawing_rev_no ? ' Rev: ' + frappe.utils.escape_html(comp.drawing_rev_no) : ''}</span>`);
					}
					if (comp.pattern_drawing_no) {
						drawing_badges.push(`<span class="psca-drawing-tag" title="${__('Pattern Drawing No')}">Pat: ${frappe.utils.escape_html(comp.pattern_drawing_no)}${comp.pattern_drawing_rev_no ? ' Rev: ' + frappe.utils.escape_html(comp.pattern_drawing_rev_no) : ''}</span>`);
					}

					let qty_display = '';
					if (has_stock) {
						qty_display = `<span class="psca-qty-positive">${qty_formatted} ${uom_str}</span>`;
					} else {
						qty_display = `<span class="psca-qty-zero">0 ${uom_str}</span>`;
					}

					let extra_qty_display = '';
					if (extra_qty_val > 0) {
						extra_qty_display = `<span class="psca-qty-extra-positive">${extra_qty_formatted} ${uom_str}</span>`;
					} else {
						extra_qty_display = `<span class="psca-qty-zero">0 ${uom_str}</span>`;
					}

					html += `
						<tr class="psca-row-component ${child_hidden}" data-group-key="${group_key}">
							<td class="psca-indent-col">
								<div class="psca-component-cell">
									<i class="fa fa-angle-right psca-sub-icon"></i>
									<a href="/app/item/${encodeURIComponent(comp.component_item)}" class="psca-comp-link" onclick="event.stopPropagation();">
										${frappe.utils.escape_html(comp.component_item)}
									</a>
									${comp.component_name && comp.component_name !== comp.component_item ? `<span class="psca-comp-name">${frappe.utils.escape_html(comp.component_name)}</span>` : ''}
									<span class="psca-req-badge">${comp.required_qty} ${frappe.utils.escape_html(comp.uom || '')} / set</span>
									${drawing_badges.join(' ')}
								</div>
							</td>
							<td>
								<div class="psca-wh-cell text-muted">
									${frappe.utils.escape_html(wg.warehouse_name || wg.warehouse)}
								</div>
							</td>
							<td class="psca-qty-cell">
								${qty_display}
							</td>
							<td class="psca-qty-cell">
								${extra_qty_display}
							</td>
						</tr>
					`;
				});
			});
		});

		$tbody.html(html);
	}

	toggle_group(group_key) {
		const is_expanded = this.state.expanded_groups.has(group_key);
		const $group_row = this.$container.find(`.psca-row-group[data-group-key="${group_key}"]`);
		const $caret = $group_row.find('.psca-caret');
		const $child_rows = this.$container.find(`.psca-row-component[data-group-key="${group_key}"]`);

		if (is_expanded) {
			this.state.expanded_groups.delete(group_key);
			$caret.removeClass('expanded');
			$child_rows.addClass('psca-hidden');
		} else {
			this.state.expanded_groups.add(group_key);
			$caret.addClass('expanded');
			$child_rows.removeClass('psca-hidden');
		}
	}

	expand_all() {
		(this.state.hierarchy || []).forEach((ps, ps_idx) => {
			(ps.warehouse_groups || []).forEach((wg, wg_idx) => {
				this.state.expanded_groups.add(`${ps_idx}_${wg_idx}`);
			});
		});

		this.$container.find('.psca-caret').addClass('expanded');
		this.$container.find('.psca-row-component').removeClass('psca-hidden');
	}

	collapse_all() {
		this.state.expanded_groups.clear();
		this.$container.find('.psca-caret').removeClass('expanded');
		this.$container.find('.psca-row-component').addClass('psca-hidden');
	}

	export_excel() {
		const params = {
			pattern_set: this.state.filters.pattern_set || '',
			component_item: this.state.filters.component_item || '',
			warehouse: this.state.filters.warehouse || '',
			type_of_valve: this.state.filters.type_of_valve || '',
			size: this.state.filters.size || '',
			class_val: this.state.filters.class || '',
			show_zero_stock: this.state.filters.show_zero_stock,
		};

		frappe.show_alert({
			message: __('Generating Excel export...'),
			indicator: 'blue',
		});

		if (typeof open_url_post === 'function') {
			open_url_post(this.export_method, params);
		} else if (frappe.utils && typeof frappe.utils.open_url_post === 'function') {
			frappe.utils.open_url_post(this.export_method, params);
		} else {
			const query_string = $.param(params);
			window.open(`${this.export_method}?${query_string}`, '_blank');
		}
	}

	format_qty(val) {
		const num = flt(val);
		if (isNaN(num)) return '0';
		return num.toLocaleString(undefined, {
			minimumFractionDigits: 0,
			maximumFractionDigits: 2,
		});
	}
}