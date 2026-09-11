// ---------------------------------------------------------------------------
// SALES ORDER TRACKER — frontend
//
// Driven completely by Sales Order.
// Tab 1 lists Sales Orders with line-wise item breakdowns and live document trails.
// Tab 2 drills into a Sales Order's overview KPIs, BOM raw material consumption,
// and linked document catalog.
//
// Drop at: apps/generate_item/generate_item/generate_item/page/ao_tracker/ao_tracker.js
// ---------------------------------------------------------------------------

frappe.pages['ao-tracker'].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Sales Order Tracker',
		single_column: true
	});

	page.set_title(__('Sales Order Tracker'));
	new AOTracker(page, wrapper);
};

class AOTracker {
	constructor(page, wrapper) {
		this.page = page;
		this.wrapper = wrapper;
		if (this.page && this.page.set_title) this.page.set_title(__('Sales Order Tracker'));
		document.title = __('Sales Order Tracker');
		this.method = {
			list: 'generate_item.generate_item.page.ao_tracker.ao_tracker.get_ao_list',
			detail: 'generate_item.generate_item.page.ao_tracker.ao_tracker.get_ao_detail',
			doc_summary: 'generate_item.generate_item.page.ao_tracker.ao_tracker.get_doc_summary',
			doc_list: 'generate_item.generate_item.page.ao_tracker.ao_tracker.get_doc_list'
		};

		this.state = {
			list: [],
			salesOrders: [],
			batchItems: [],
			viewMode: 'batch', // 'batch' or 'so'
			currentSo: null,
			activeTab: 1,
			selected: new Set(),
			expandedSos: new Set(),
			theme: localStorage.getItem('aot_theme') || 'light',
			period: 'monthly',
			page: 1,
			pageSize: 50,
			totalPages: 1,
			totalSos: 0,
			totalBatches: 0
		};

		this.period_options = [
			{ value: 'monthly', label: __('Monthly (Last 30 Days)') },
			{ value: 'quarterly', label: __('Quarterly (Last 3 Months)') },
			{ value: 'fy_current', label: __('This Financial Year') },
			{ value: 'fy_previous', label: __('Previous Financial Year') },
			{ value: 'weekly', label: __('Weekly (Last 7 Days)') },
			{ value: 'all', label: __('All Time') },
			{ value: 'custom', label: __('Custom Range') }
		];

		this.doc_type_colors = {
			quote: '#F59E0B', so: '#2563EB', mr: '#7C3AED', po: '#0284C7',
			sco: '#0D9488', scr: '#D97706', pr: '#E11D48', sr: '#65A30D',
			pi: '#EA580C', dn: '#059669', si: '#C026D3', pe_in: '#16A34A',
			pe_out: '#DB2777', je: '#475569'
		};

		this.doc_columns = [
			{ key: 'mr', label: 'MR', full_label: 'Material Requests', color: '#7C3AED' },
			{ key: 'po', label: 'PO', full_label: 'Purchase Orders', color: '#0284C7' },
			{ key: 'sco', label: 'Subcontracting Order', full_label: 'Subcontracting Orders', color: '#0D9488' },
			{ key: 'scr', label: 'Subcontracting Receipt', full_label: 'Subcontracting Receipts', color: '#D97706' },
			{ key: 'pr', label: 'Purchase Receipt', full_label: 'Purchase Receipts', color: '#E11D48' },
			{ key: 'pi', label: 'Purchase Invoice', full_label: 'Purchase Invoices', color: '#EA580C' },
			{ key: 'dn', label: 'Delivery Note', full_label: 'Delivery Notes', color: '#059669' },
			{ key: 'si', label: 'Sales Invoice', full_label: 'Sales Invoices', color: '#C026D3' }
		];

		this.setup_actions();
		this.render_shell();
		this.bind_events();
		this.load_list();
	}

	setup_actions() {
		$(this.wrapper).find('.page-head').hide();
	}

	render_shell() {
		this.$wrap = $(`<div class="ao-tracker-wrap">${this.markup()}</div>`);
		$(this.page.body).empty().append(this.$wrap);
		this.render_period_menu();
		this.apply_period('monthly', { silent: true });

		this._initializing = true;
		this.init_link_filters();
		this._initializing = false;

		this.apply_theme();
	}

	init_link_filters() {
		this.company_control = frappe.ui.form.make_control({
			parent: this.$wrap.find('.aot-f-company-wrap').get(0),
			df: {
				fieldtype: 'Link',
				options: 'Company',
				fieldname: 'company',
				placeholder: __('All Companies'),
				onchange: () => {
					if (!this._initializing) {
						this.state.page = 1;
						this.load_list();
					}
				}
			},
			render_input: true
		});
		this.company_control.refresh();
		const default_company = frappe.defaults.get_default('company') || frappe.sys_defaults?.company;
		if (default_company) this.company_control.set_value(default_company);

		this.so_control = frappe.ui.form.make_control({
			parent: this.$wrap.find('.aot-f-so-wrap').get(0),
			df: {
				fieldtype: 'Link',
				options: 'Sales Order',
				fieldname: 'sales_order',
				placeholder: __('Sales Order'),
				get_query: () => {
					const filters = { docstatus: ['!=', 2] };
					const comp = this.company_control ? this.company_control.get_value() : '';
					const cust = this.customer_control ? this.customer_control.get_value() : '';
					const branch = this.branch_control ? this.branch_control.get_value() : '';
					if (comp) filters.company = comp;
					if (cust) filters.customer = cust;
					if (branch) filters.branch = branch;
					return { filters };
				},
				onchange: () => {
					if (!this._initializing) {
						this.state.page = 1;
						this.load_list();
					}
				}
			},
			render_input: true
		});
		this.so_control.refresh();

		this.customer_control = frappe.ui.form.make_control({
			parent: this.$wrap.find('.aot-f-customer-wrap').get(0),
			df: {
				fieldtype: 'Link',
				options: 'Customer',
				fieldname: 'customer',
				placeholder: __('Customer'),
				get_query: () => {
					return { filters: { disabled: 0 } };
				},
				onchange: () => {
					if (!this._initializing) {
						this.state.page = 1;
						this.load_list();
					}
				}
			},
			render_input: true
		});
		this.customer_control.refresh();

		this.branch_control = frappe.ui.form.make_control({
			parent: this.$wrap.find('.aot-f-branch-wrap').get(0),
			df: {
				fieldtype: 'Link',
				options: 'Branch',
				fieldname: 'branch',
				placeholder: __('All Branches'),
				get_query: () => {
					const comp = this.company_control ? this.company_control.get_value() : '';
					const filters = {};
					if (comp && frappe.meta.has_field('Branch', 'company')) filters.company = comp;
					return { filters };
				},
				onchange: () => {
					if (!this._initializing) {
						this.state.page = 1;
						this.load_list();
					}
				}
			},
			render_input: true
		});
		this.branch_control.refresh();
		const default_branch = frappe.defaults.get_default('branch');
		if (default_branch) this.branch_control.set_value(default_branch);

		this.batch_control = frappe.ui.form.make_control({
			parent: this.$wrap.find('.aot-f-batch-wrap').get(0),
			df: {
				fieldtype: 'Link',
				options: 'Batch',
				fieldname: 'batch_no',
				placeholder: __('Batch No'),
				onchange: () => {
					if (!this._initializing) {
						this.state.page = 1;
						this.load_list();
					}
				}
			},
			render_input: true
		});
		this.batch_control.refresh();
	}

	render_period_menu() {
		const $menu = this.$wrap.find('.aot-period-menu').empty();
		this.period_options.forEach((opt) => {
			$menu.append(`<div class="aot-period-item" data-period="${opt.value}">${opt.label}</div>`);
		});
	}

	compute_period_range(period) {
		if (period === 'all') {
			return { from: '', to: '' };
		}
		const FY_START_MONTH = 4; // April
		const today = frappe.datetime.get_today();

		if (period === 'weekly') {
			return { from: frappe.datetime.add_days(today, -7), to: today };
		}
		if (period === 'monthly') {
			return { from: frappe.datetime.add_months(today, -1), to: today };
		}
		if (period === 'quarterly') {
			return { from: frappe.datetime.add_months(today, -3), to: today };
		}
		if (period === 'fy_current' || period === 'fy_previous') {
			const d = frappe.datetime.str_to_obj(today);
			let fyStartYear = d.getFullYear();
			if ((d.getMonth() + 1) < FY_START_MONTH) fyStartYear -= 1;
			if (period === 'fy_previous') fyStartYear -= 1;
			const pad = (n) => String(n).padStart(2, '0');
			const from = `${fyStartYear}-${pad(FY_START_MONTH)}-01`;
			const nextStart = `${fyStartYear + 1}-${pad(FY_START_MONTH)}-01`;
			return { from, to: frappe.datetime.add_days(nextStart, -1) };
		}
		return null;
	}

	apply_period(period, opts) {
		opts = opts || {};
		this.state.period = period;

		const chosen = this.period_options.find((o) => o.value === period);
		this.$wrap.find('.aot-period-label').text(chosen ? chosen.label : period);
		this.$wrap.find('.aot-period-item').removeClass('active');
		this.$wrap.find(`.aot-period-item[data-period="${period}"]`).addClass('active');

		const isCustom = period === 'custom';
		this.$wrap.find('.aot-f-from, .aot-f-to').prop('readonly', !isCustom).toggleClass('aot-locked', !isCustom);

		if (!isCustom) {
			const range = this.compute_period_range(period);
			if (range) {
				this.$wrap.find('.aot-f-from').val(range.from);
				this.$wrap.find('.aot-f-to').val(range.to);
			}
		}

		this.$wrap.find('.aot-period-menu').removeClass('open');
		if (!opts.silent) {
			this.state.page = 1;
			this.load_list();
		}
	}

	apply_theme() {
		this.$wrap.attr('data-theme', this.state.theme);
		const isDark = this.state.theme === 'dark';
		this.$wrap.find('.aot-theme-toggle')
			.html(this.theme_icon())
			.attr('title', isDark ? __('Switch to Light Mode') : __('Switch to Dark Mode'));
	}

	toggle_theme() {
		this.state.theme = this.state.theme === 'dark' ? 'light' : 'dark';
		localStorage.setItem('aot_theme', this.state.theme);
		this.apply_theme();
	}

	theme_icon() {
		if (this.state.theme === 'dark') {
			return `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></svg>`;
		}
		return `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>`;
	}

	refresh_icon() {
		return `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 11-9-9c2.5 0 4.7 1 6.4 2.6L21 8M21 3v5h-5"/></svg>`;
	}

	home_icon() {
		return `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 11.5 12 4l9 7.5"/><path d="M5.5 10v9a1 1 0 0 0 1 1H9a1 1 0 0 0 1-1v-4a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v4a1 1 0 0 0 1 1h2.5a1 1 0 0 0 1-1v-9"/></svg>`;
	}

	calendar_icon() {
		return `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="3.5" y="5" width="17" height="16" rx="2.2"/><path d="M8 3v4M16 3v4M3.5 10h17"/></svg>`;
	}

	chevron_icon() {
		return `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>`;
	}

	project_icon() {
		return `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7a2 2 0 0 1 2-2h4l2 2.5h8a2 2 0 0 1 2 2V17a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z"/></svg>`;
	}

	sales_order_icon() {
		return `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 2.5h9l3 3V20a1.2 1.2 0 0 1-1.2 1.2H6A1.2 1.2 0 0 1 4.8 20V3.7A1.2 1.2 0 0 1 6 2.5Z"/><path d="M9 9h6M9 13h6M9 17h3.5"/></svg>`;
	}

	user_icon() {
		return `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>`;
	}

	branch_icon() {
		return `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><line x1="6" y1="3" x2="6" y2="15"></line><circle cx="18" cy="6" r="3"></circle><circle cx="6" cy="18" r="3"></circle><path d="M18 9a9 9 0 0 1-9 9"></path></svg>`;
	}

	item_icon() {
		return `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m7.5 4.27 9 5.15"/><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/></svg>`;
	}

	batch_icon() {
		return `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2H2v10l9.29 9.29c.94.94 2.48.94 3.42 0l6.58-6.58c.94-.94.94-2.48 0-3.42L12 2Z"/><path d="M7 7h.01"/></svg>`;
	}

	markup() {
		return `
		<style>${this.css()}</style>

		<div class="aot-topbar">
			<div class="aot-topbar-title">
				<div class="aot-topbar-badge">SO</div>
				<div>
					<div class="aot-topbar-heading">${__('Sales Order Tracker')}</div>
					<div class="aot-topbar-sub">${__('Sales Order & Batch')} \u2192 ${__('Procurement')} \u2192 ${__('Fulfilment')}</div>
				</div>
			</div>
			<div class="aot-topbar-actions">
				<div class="aot-toggle" role="tablist">
					<button class="aot-toggle-btn active" data-goto="1">${__('Status Overview')}</button>
					<button class="aot-toggle-btn" data-goto="2">${__('Detailed View')}</button>
				</div>
				<button class="aot-icon-btn aot-refresh-btn" title="${__('Refresh')}">${this.refresh_icon()}</button>
			</div>
		</div>

		<div class="aot-view aot-view-1 active" data-view="1">
			<div class="aot-filters">
				<div class="aot-filter-row aot-filter-row-primary">
					<div class="aot-filter-group">
						<div class="aot-pill-field aot-field-company">
							<span class="aot-pill-icon">${this.home_icon()}</span>
							<div class="aot-f-company-wrap aot-pill-input"></div>
						</div>

						<div class="aot-period-dropdown aot-pill-field">
							<button type="button" class="aot-period-btn">
								${this.calendar_icon()}
								<span class="aot-period-label">${__('Monthly')}</span>
								${this.chevron_icon()}
							</button>
							<div class="aot-period-menu"></div>
						</div>

						<div class="aot-daterange-box">
							<input type="date" class="aot-f-from aot-locked" readonly>
							<span class="aot-date-sep">${__('to')}</span>
							<input type="date" class="aot-f-to aot-locked" readonly>
						</div>
					</div>

					<div class="aot-filter-actions">
						<button class="btn btn-default btn-sm aot-reset">${__('Reset')}</button>
						<button class="aot-icon-btn aot-theme-toggle" title="${__('Switch to Dark Mode')}">${this.theme_icon()}</button>
					</div>
				</div>

				<div class="aot-filter-row aot-filter-row-secondary">
					<div class="aot-filter-group">
						<div class="aot-pill-field aot-field-so">
							<span class="aot-pill-icon">${this.sales_order_icon()}</span>
							<div class="aot-f-so-wrap aot-pill-input"></div>
						</div>
						<div class="aot-pill-field aot-field-customer">
							<span class="aot-pill-icon">${this.user_icon()}</span>
							<div class="aot-f-customer-wrap aot-pill-input"></div>
						</div>
						<div class="aot-pill-field aot-field-branch">
							<span class="aot-pill-icon">${this.branch_icon()}</span>
							<div class="aot-f-branch-wrap aot-pill-input"></div>
						</div>
						<div class="aot-pill-field aot-field-batch">
							<span class="aot-pill-icon">${this.batch_icon()}</span>
							<div class="aot-f-batch-wrap aot-pill-input"></div>
						</div>
					</div>
				</div>
			</div>

			<div class="aot-section-head">
				<div class="aot-section-title-wrap">
					<div class="aot-section-title">${__('Tracker Dashboard')}</div>
					<div class="aot-result-count"></div>
				</div>
				<div class="aot-table-actions">
					<div class="aot-view-mode-toggle">
						<button type="button" class="aot-mode-btn active" data-mode="batch" title="${__('Show each batch and item line as its own row')}">
							<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
							<span>${__('Batch Wise')}</span>
						</button>
						<button type="button" class="aot-mode-btn" data-mode="so" title="${__('Show Sales Orders with expandable item breakdowns')}">
							<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>
							<span>${__('Sales Order Wise')}</span>
						</button>
					</div>
					<button type="button" class="aot-toggle-all-btn" style="display:none;">
						<span class="aot-toggle-all-icon">▸</span>
						<span class="aot-toggle-all-text">${__('Expand All')}</span>
					</button>
				</div>
			</div>

			<div class="aot-table-scroll">
				<table class="aot-status-table">
					<thead class="aot-thead"></thead>
					<tbody class="aot-tbody"></tbody>
				</table>
			</div>

			<div class="aot-pagination-bar" style="display:none;">
				<div class="aot-page-info"></div>
				<div class="aot-page-controls">
					<button type="button" class="aot-page-btn aot-page-prev" title="${__('Previous Page')}">
						${frappe.utils.icon('left', 'xs')}
						<span>${__('Prev')}</span>
					</button>
					<div class="aot-page-status">
						<span>${__('Page')}</span>
						<input type="number" class="aot-page-input" min="1" value="1">
						<span>${__('of')} <b class="aot-page-total">1</b></span>
					</div>
					<button type="button" class="aot-page-btn aot-page-next" title="${__('Next Page')}">
						<span>${__('Next')}</span>
						${frappe.utils.icon('right', 'xs')}
					</button>
					<select class="aot-page-size-select">
						<option value="25">25 / page</option>
						<option value="50" selected>50 / page</option>
						<option value="100">100 / page</option>
						<option value="200">200 / page</option>
					</select>
				</div>
			</div>
		</div>

		<div class="aot-view aot-view-2" data-view="2">
			<button class="aot-back-link">
				${frappe.utils.icon('left', 'sm')} ${__('Back to status overview')}
			</button>

			<div class="aot-detail-header">
				<div class="aot-detail-title-block">
					<h1 class="aot-d-title"></h1>
					<div class="aot-d-sub"></div>
				</div>
				<div class="aot-mini-pill aot-d-status-pill"></div>
			</div>

			<div class="aot-panel">
				<div class="aot-panel-head aot-collapsible">
					<div class="aot-panel-head-left">
						<div class="aot-panel-title">${__('Order Overview & Profitability')}</div>
						<div class="aot-panel-desc">${__('Estimated revenue, material cost, and profitability for this Sales Order.')}</div>
					</div>
					<span class="aot-caret">${frappe.utils.icon('small-down', 'sm')}</span>
				</div>
				<div class="aot-panel-body">
					<div class="aot-stat-grid aot-overview-grid"></div>
				</div>
			</div>

			<div class="aot-panel">
				<div class="aot-panel-head aot-collapsible">
					<div class="aot-panel-head-left">
						<div class="aot-panel-title">${__('Order Items & Material Consumption')}</div>
						<div class="aot-panel-desc">${__('Every finished item and raw material / component consumed against this Sales Order.')}</div>
					</div>
					<span class="aot-caret">${frappe.utils.icon('small-down', 'sm')}</span>
				</div>
				<div class="aot-panel-body">
					<div class="aot-table-x-scroll">
						<table class="aot-flat-table aot-items-table">
							<thead>
								<tr>
									<th style="width:34px; text-align:center;"></th>
									<th style="width:45px; text-align:center;">${__('Line')}</th>
									<th style="min-width:220px;">${__('Order Item')}</th>
									<th style="min-width:130px;">${__('Batch No')}</th>
									<th class="aot-num" style="text-align:right; min-width:90px;">${__('Ordered Qty')}</th>
									<th class="aot-num" style="text-align:right; min-width:90px;">${__('Delivered Qty')}</th>
									<th class="aot-num" style="text-align:right; min-width:90px;">${__('Pending Qty')}</th>
									<th class="aot-num" style="text-align:right; min-width:110px;">${__('Selling Rate')}</th>
									<th class="aot-num" style="text-align:right; min-width:110px;">${__('Amount')}</th>
									<th style="min-width:110px;">${__('Delivery Date')}</th>
									<th style="min-width:90px;">${__('Branch')}</th>
									<th style="min-width:140px; text-align:center;">${__('Raw Materials')}</th>
								</tr>
							</thead>
							<tbody class="aot-items-tbody"></tbody>
						</table>
					</div>
				</div>
			</div>

			<div class="aot-panel">
				<div class="aot-panel-head aot-collapsible">
					<div class="aot-panel-head-left">
						<div class="aot-panel-title">${__('Linked Documents')}</div>
						<div class="aot-panel-desc">${__('Every document generated for this Sales Order. Dashed cards have not been generated yet.')}</div>
					</div>
					<span class="aot-caret">${frappe.utils.icon('small-down', 'sm')}</span>
				</div>
				<div class="aot-panel-body">
					<div class="aot-doc-catalog-grid aot-doc-grid"></div>
				</div>
			</div>
		</div>

		<div class="aot-modal-backdrop">
			<div class="aot-modal">
				<div class="aot-modal-head">
					<div>
						<div class="aot-modal-eyebrow"></div>
						<div class="aot-modal-title"></div>
					</div>
					<button class="aot-modal-close">&times;</button>
				</div>
				<div class="aot-modal-stats"></div>
				<div class="aot-modal-items-label">${__('Items in this document')}</div>
				<div class="aot-modal-items"></div>
				<div class="aot-modal-footer">
					<button class="btn btn-default btn-sm aot-modal-cancel">${__('Close')}</button>
					<button class="btn btn-primary btn-sm aot-modal-open">${__('Open full record')}</button>
				</div>
			</div>
		</div>

		<div class="aot-doclist-backdrop">
			<div class="aot-doclist-modal">
				<div class="aot-modal-head">
					<div>
						<div class="aot-modal-eyebrow aot-doclist-eyebrow"></div>
						<div class="aot-modal-title aot-doclist-title"></div>
					</div>
					<button class="aot-modal-close aot-doclist-close">&times;</button>
				</div>
				<div class="aot-doclist-hint">${__('Click any document below to preview it.')}</div>
				<div class="aot-doclist-rows"></div>
				<div class="aot-modal-footer">
					<button class="btn btn-default btn-sm aot-doclist-close">${__('Close')}</button>
				</div>
			</div>
		</div>
		`;
	}

	bind_events() {
		// View Mode Switcher: Batch Wise vs Sales Order Wise
		this.$wrap.on('click', '.aot-mode-btn', (e) => {
			const mode = $(e.currentTarget).data('mode');
			if (mode === this.state.viewMode) return;
			this.state.viewMode = mode;
			this.$wrap.find('.aot-mode-btn').removeClass('active');
			$(e.currentTarget).addClass('active');
			this.state.list = this.state.viewMode === 'batch' ? this.state.batchItems : this.state.salesOrders;
			this.render_list();
			this.render_pagination();
		});

		// Pagination controls
		this.$wrap.on('click', '.aot-page-prev', () => {
			if (this.state.page > 1) {
				this.state.page -= 1;
				this.load_list();
			}
		});

		this.$wrap.on('click', '.aot-page-next', () => {
			if (this.state.page < this.state.totalPages) {
				this.state.page += 1;
				this.load_list();
			}
		});

		this.$wrap.on('change', '.aot-page-input', (e) => {
			let p = parseInt($(e.target).val(), 10) || 1;
			if (p < 1) p = 1;
			if (p > this.state.totalPages) p = this.state.totalPages;
			this.state.page = p;
			this.load_list();
		});

		this.$wrap.on('change', '.aot-page-size-select', (e) => {
			this.state.pageSize = parseInt($(e.target).val(), 10) || 50;
			this.state.page = 1;
			this.load_list();
		});

		this.$wrap.on('click', '.aot-reset', () => {
			this._initializing = true;
			this.apply_period('monthly', { silent: true });
			const default_company = frappe.defaults.get_default('company') || frappe.sys_defaults?.company || '';
			if (this.company_control) this.company_control.set_value(default_company);
			if (this.so_control) this.so_control.set_value('');
			if (this.customer_control) this.customer_control.set_value('');
			if (this.branch_control) {
				const default_branch = frappe.defaults.get_default('branch') || '';
				this.branch_control.set_value(default_branch);
			}
			if (this.batch_control) this.batch_control.set_value('');
			this.state.selected.clear();
			this.state.page = 1;
			this._initializing = false;
			this.load_list();
		});

		this.$wrap.on('change', '.aot-f-from, .aot-f-to', () => {
			this.state.page = 1;
			this.load_list();
		});

		this.$wrap.on('click', '.aot-period-btn', (e) => {
			e.stopPropagation();
			this.$wrap.find('.aot-period-menu').toggleClass('open');
		});
		this.$wrap.on('click', '.aot-period-item', (e) => {
			this.apply_period($(e.currentTarget).data('period'));
		});
		$(document).on('click.aotPeriod', () => {
			if (this.$wrap) this.$wrap.find('.aot-period-menu').removeClass('open');
		});
		this.$wrap.on('click', '.aot-back-link', () => this.go_tab(1));
		this.$wrap.on('click', '.aot-toggle-btn', (e) => {
			const n = Number($(e.currentTarget).data('goto'));
			if (n === 2 && !this.state.currentSo) {
				frappe.show_alert({ message: __('Open a Sales Order from the list first.'), indicator: 'orange' });
				return;
			}
			if (n === 2) {
				this.open_detail(this.state.currentSo, this.state.currentBatch);
			} else {
				this.go_tab(1);
			}
		});

		this.$wrap.on('click', '.aot-theme-toggle', () => this.toggle_theme());

		this.$wrap.on('click', '.aot-refresh-btn', () => {
			if (this.state.activeTab === 2 && this.state.currentSo) {
				this.open_detail(this.state.currentSo, this.state.currentBatch);
			} else {
				this.load_list();
			}
		});

		// Navigation into detail view by clicking Sales Order or the arrow button
		this.$wrap.on('click', '.aot-so-link, .aot-view-btn', (e) => {
			const so = $(e.currentTarget).data('sales-order') || $(e.currentTarget).data('name');
			const batch = $(e.currentTarget).data('batch') || (this.batch_control ? this.batch_control.get_value() : '') || null;
			if (so) this.open_detail(so, batch);
		});

		this.$wrap.on('click', '.aot-doc-link', (e) => {
			e.stopPropagation();
			const doctype = $(e.currentTarget).data('doctype');
			const name = $(e.currentTarget).data('name');
			if (doctype && name) frappe.set_route('Form', doctype, name);
		});

		this.$wrap.on('click', '.aot-doc-multi, .aot-doc-card-multi', (e) => {
			e.stopPropagation();
			const so = $(e.currentTarget).data('sales-order');
			const project = $(e.currentTarget).data('project');
			const key = $(e.currentTarget).data('key');
			const label = $(e.currentTarget).data('label');
			const color = $(e.currentTarget).data('color');
			const so_item = $(e.currentTarget).data('so-item');
			const item_code = $(e.currentTarget).data('item-code');
			const batch = $(e.currentTarget).data('batch');
			this.open_doc_list_modal(so, project, key, label, color, so_item, item_code, batch);
		});

		this.$wrap.on('click', '.aot-doc-card:not(.empty):not(.unavailable):not(.aot-doc-card-multi)', (e) => {
			const doctype = $(e.currentTarget).data('doctype');
			const name = $(e.currentTarget).data('name');
			const batch = $(e.currentTarget).data('batch') || (this.batch_control ? this.batch_control.get_value() : '') || this.state.currentBatch || null;
			if (doctype && name) this.open_doc_modal(doctype, name, batch);
		});

		this.$wrap.on('click', '.aot-modal-close, .aot-modal-cancel, .aot-modal-backdrop', function (e) {
			if (e.target === this) $(this).closest('.ao-tracker-wrap').find('.aot-modal-backdrop').removeClass('open');
		});
		this.$wrap.on('click', '.aot-modal', (e) => e.stopPropagation());
		this.$wrap.on('click', '.aot-modal-open', () => {
			const doctype = this.$wrap.find('.aot-modal').data('doctype');
			const name = this.$wrap.find('.aot-modal').data('name');
			if (doctype && name) frappe.set_route('Form', doctype, name);
		});
		this.$wrap.on('click', '.aot-modal-item-ref, .aot-doc-link', (e) => {
			e.stopPropagation();
			e.preventDefault();
			const doctype = $(e.currentTarget).data('doctype');
			const name = $(e.currentTarget).data('name');
			if (doctype && name) frappe.set_route('Form', doctype, name);
		});

		this.$wrap.on('click', '.aot-doclist-close, .aot-doclist-backdrop', function (e) {
			if (e.target === this) $(this).closest('.ao-tracker-wrap').find('.aot-doclist-backdrop').removeClass('open');
		});
		this.$wrap.on('click', '.aot-doclist-modal', (e) => e.stopPropagation());
		this.$wrap.on('click', '.aot-doclist-row', (e) => {
			const doctype = $(e.currentTarget).data('doctype');
			const name = $(e.currentTarget).data('name');
			const batch = $(e.currentTarget).data('batch') || $(e.currentTarget).closest('.aot-doclist-modal').data('batch') || (this.batch_control ? this.batch_control.get_value() : '') || this.state.currentBatch || null;
			if (!doctype || !name) return;
			this.$wrap.find('.aot-doclist-backdrop').removeClass('open');
			this.open_doc_modal(doctype, name, batch);
		});

		this.$wrap.on('click', '.aot-collapsible', (e) => {
			$(e.currentTarget).closest('.aot-panel').toggleClass('collapsed');
		});

		// Expand / collapse single Sales Order items in SO Wise mode
		this.$wrap.on('click', '.aot-expand-btn:not(.aot-item-expand-btn), .aot-items-badge', (e) => {
			e.stopPropagation();
			const so = $(e.currentTarget).data('sales-order');
			if (so) this.toggle_so_expand(so);
		});

		// Expand / collapse single item raw materials in Tab 2
		this.$wrap.on('click', '.aot-item-expand-btn, .aot-bom-toggle-btn', (e) => {
			e.stopPropagation();
			const line = $(e.currentTarget).data('line');
			const $row = this.$wrap.find(`.aot-item-row[data-line="${line}"]`);
			const $child = this.$wrap.find(`.aot-item-child-row[data-child-of-line="${line}"]`);
			const isExp = $row.hasClass('expanded');
			$row.toggleClass('expanded', !isExp);
			$child.toggleClass('expanded', !isExp);
		});

		// Clicking row toggles expansion unless clicking interactive links/controls
		this.$wrap.on('click', '.aot-so-row', (e) => {
			if ($(e.target).closest('a, button, input, .aot-doc-multi, .aot-doc-link, .aot-view-btn, .aot-row-check').length) {
				return;
			}
			const so = $(e.currentTarget).data('so');
			if (so) this.toggle_so_expand(so);
		});

		// Toggle all expand / collapse
		this.$wrap.on('click', '.aot-toggle-all-btn', () => {
			this.toggle_all_expand();
		});

		this.$wrap.on('click', '.aot-row-check', (e) => e.stopPropagation());
		this.$wrap.on('change', '.aot-row-check', (e) => {
			const key = $(e.currentTarget).data('batch') || $(e.currentTarget).data('sales-order');
			if (e.currentTarget.checked) this.state.selected.add(key);
			else this.state.selected.delete(key);
		});
		this.$wrap.on('change', '.aot-select-all', (e) => {
			const checked = e.currentTarget.checked;
			this.$wrap.find('.aot-row-check').prop('checked', checked).each((_, el) => {
				const key = $(el).data('batch') || $(el).data('sales-order');
				if (checked) this.state.selected.add(key);
				else this.state.selected.delete(key);
			});
		});
	}

	go_tab(n) {
		this.state.activeTab = n;
		this.$wrap.find('.aot-view').removeClass('active');
		this.$wrap.find(`.aot-view[data-view="${n}"]`).addClass('active');
		this.$wrap.find('.aot-toggle-btn').removeClass('active');
		this.$wrap.find(`.aot-toggle-btn[data-goto="${n}"]`).addClass('active');
	}

	load_list() {
		const args = {
			from_date: this.$wrap.find('.aot-f-from').val(),
			to_date: this.$wrap.find('.aot-f-to').val(),
			company: this.company_control ? this.company_control.get_value() : '',
			sales_order: this.so_control ? this.so_control.get_value() : '',
			customer: this.customer_control ? this.customer_control.get_value() : '',
			branch: this.branch_control ? this.branch_control.get_value() : '',
			batch_no: this.batch_control ? this.batch_control.get_value() : '',
			view_mode: this.state.viewMode,
			page: this.state.page,
			page_length: this.state.pageSize
		};
		frappe.call({
			method: this.method.list,
			args,
			freeze: true,
			callback: (r) => {
				const msg = r.message || {};
				if (Array.isArray(msg)) {
					this.state.salesOrders = msg;
					this.state.batchItems = [];
					msg.forEach(so => {
						(so.items || []).forEach(it => {
							this.state.batchItems.push(it);
						});
					});
					this.state.totalPages = 1;
					this.state.totalSos = msg.length;
					this.state.totalBatches = this.state.batchItems.length;
				} else {
					this.state.salesOrders = msg.sales_orders || [];
					this.state.batchItems = msg.batch_items || [];
					this.state.totalPages = msg.total_pages || 1;
					this.state.totalSos = msg.total_sos || 0;
					this.state.totalBatches = msg.total_batches || 0;
					this.state.page = msg.page || 1;
				}
				this.state.list = this.state.viewMode === 'batch' ? this.state.batchItems : this.state.salesOrders;
				this.render_list();
				this.render_pagination();
			}
		});
	}

	render_pagination() {
		const isBatch = this.state.viewMode === 'batch';
		const total = isBatch ? (this.state.totalBatches || this.state.batchItems.length) : (this.state.totalSos || this.state.salesOrders.length);
		const listLen = (isBatch ? this.state.batchItems : this.state.salesOrders).length;

		const start = total > 0 ? (this.state.page - 1) * this.state.pageSize + 1 : 0;
		const end = Math.min(start + listLen - 1, total);

		const itemLabel = isBatch ? __('Batches / Items') : __('Sales Orders');
		let infoText = '';
		if (total > 0) {
			infoText = __('Showing {0}–{1} of {2} {3}', [start, Math.max(start, end), total, itemLabel]);
		} else {
			infoText = __('No {0} found', [itemLabel]);
		}

		this.$wrap.find('.aot-page-info').text(infoText);
		this.$wrap.find('.aot-page-input').val(this.state.page).attr('max', this.state.totalPages);
		this.$wrap.find('.aot-page-total').text(this.state.totalPages);
		this.$wrap.find('.aot-page-prev').prop('disabled', this.state.page <= 1);
		this.$wrap.find('.aot-page-next').prop('disabled', this.state.page >= this.state.totalPages);
		this.$wrap.find('.aot-page-size-select').val(this.state.pageSize);

		if (total <= 0) {
			this.$wrap.find('.aot-pagination-bar').hide();
		} else {
			this.$wrap.find('.aot-pagination-bar').show();
		}
	}

	toggle_so_expand(so_name) {
		if (!so_name) return;
		const isExpanded = this.state.expandedSos.has(so_name);
		if (isExpanded) {
			this.state.expandedSos.delete(so_name);
		} else {
			this.state.expandedSos.add(so_name);
		}
		const $row = this.$wrap.find(`.aot-so-row[data-so="${so_name}"]`);
		const $child = this.$wrap.find(`.aot-child-row[data-child-of="${so_name}"]`);
		$row.toggleClass('expanded', !isExpanded);
		$child.toggleClass('expanded', !isExpanded);
	}

	toggle_all_expand() {
		const allSos = (this.state.salesOrders || []).map(ao => ao.sales_order).filter(Boolean);
		const areAllExpanded = allSos.length > 0 && allSos.every(so => this.state.expandedSos.has(so));
		if (areAllExpanded) {
			this.state.expandedSos.clear();
			this.$wrap.find('.aot-so-row, .aot-child-row').removeClass('expanded');
			this.$wrap.find('.aot-toggle-all-text').text(__('Expand All'));
			this.$wrap.find('.aot-toggle-all-icon').removeClass('rotated');
		} else {
			allSos.forEach(so => this.state.expandedSos.add(so));
			this.$wrap.find('.aot-so-row, .aot-child-row').addClass('expanded');
			this.$wrap.find('.aot-toggle-all-text').text(__('Collapse All'));
			this.$wrap.find('.aot-toggle-all-icon').addClass('rotated');
		}
	}

	render_list() {
		const isBatch = this.state.viewMode === 'batch';
		const list = isBatch ? this.state.batchItems : this.state.salesOrders;
		this.state.list = list;

		if (isBatch) {
			this.$wrap.find('.aot-result-count').text(
				this.state.totalBatches ? __('{0} Total Batches / Items', [this.state.totalBatches]) : (list.length === 1 ? __('1 Batch / Item') : __('{0} Batches / Items', [list.length]))
			);
			this.$wrap.find('.aot-toggle-all-btn').hide();
		} else {
			this.$wrap.find('.aot-result-count').text(
				this.state.totalSos ? __('{0} Total Sales Orders', [this.state.totalSos]) : (list.length === 1 ? __('1 Sales Order') : __('{0} Sales Orders', [list.length]))
			);
			const allSos = list.map(ao => ao.sales_order).filter(Boolean);
			const areAllExpanded = allSos.length > 0 && allSos.every(so => this.state.expandedSos.has(so));
			this.$wrap.find('.aot-toggle-all-btn').show();
			this.$wrap.find('.aot-toggle-all-text').text(areAllExpanded ? __('Collapse All') : __('Expand All'));
			this.$wrap.find('.aot-toggle-all-icon').toggleClass('rotated', areAllExpanded);
		}

		this.render_table_header(isBatch);

		const $tbody = this.$wrap.find('.aot-tbody').empty();
		this.$wrap.find('.aot-select-all').prop('checked', false);
		const colspan = (isBatch ? 11 : 12) + (this.doc_columns.length * 2);

		if (!list.length) {
			const emptyMsg = isBatch ? __('No Batch / Item records match these filters.') : __('No Sales Orders match these filters.');
			$tbody.html(`<tr><td colspan="${colspan}" class="aot-empty-row">${emptyMsg}</td></tr>`);
			return;
		}

		if (isBatch) {
			list.forEach((it) => {
				$tbody.append(this.render_batch_row(it, colspan));
			});
		} else {
			list.forEach((ao) => {
				$tbody.append(this.render_list_row(ao, colspan));
			});
		}
	}

	render_table_header(isBatch) {
		const $thead = this.$wrap.find('.aot-thead').empty();
		const $table = this.$wrap.find('table.aot-status-table');
		if (isBatch) {
			$table.removeClass('aot-table-so').addClass('aot-table-batch');
			$thead.html(`
				<tr>
					<th style="width:36px; text-align:center;"><input type="checkbox" class="aot-select-all"></th>
					<th class="aot-batch-col" style="min-width:140px;">${__('Batch No')}</th>
					<th class="aot-item-col" style="min-width:180px;">${__('Item Code & Name')}</th>
					<th class="aot-so-col" style="min-width:140px;">${__('Sales Order')}</th>
					<th class="aot-customer-col" style="min-width:160px;">${__('Customer')}</th>
					<th class="aot-num aot-qty-col" style="text-align:right; min-width:95px;">${__('Total Qty')}</th>
					<th class="aot-num aot-amount-col" style="text-align:right; min-width:115px;">${__('Amount')}</th>
					<th class="aot-date-col" style="min-width:110px;">${__('Delivery Date')}</th>
					<th class="aot-branch-col" style="min-width:90px;">${__('Branch')}</th>
					<th class="aot-pending-col" style="min-width:160px;">${__('Pending At')}</th>
					${this.doc_columns.map(c => `
						<th class="aot-grp-start" style="border-top:3px solid ${c.color};">${__(c.label)}</th>
						<th>${__(c.label)} ${__('Status')}</th>
					`).join('')}
					<th class="aot-grp-start aot-priority-col">${__('Priority')}</th>
					<th style="width:40px;"></th>
				</tr>
			`);
		} else {
			$table.removeClass('aot-table-batch').addClass('aot-table-so');
			$thead.html(`
				<tr>
					<th style="width:34px; text-align:center;"></th>
					<th style="width:36px; text-align:center;"><input type="checkbox" class="aot-select-all"></th>
					<th class="aot-so-col" style="min-width:160px;">${__('Sales Order')}</th>
					<th class="aot-customer-col" style="min-width:160px;">${__('Customer')}</th>
					<th class="aot-items-col" style="width:90px; text-align:center;">${__('Items')}</th>
					<th class="aot-num aot-qty-col" style="text-align:right; min-width:95px;">${__('Total Qty')}</th>
					<th class="aot-num aot-amount-col" style="text-align:right; min-width:120px;">${__('Grand Total')}</th>
					<th class="aot-date-col" style="min-width:110px;">${__('Delivery Date')}</th>
					<th class="aot-branch-col" style="min-width:90px;">${__('Branch')}</th>
					<th class="aot-pending-col" style="min-width:160px;">${__('Pending At')}</th>
					${this.doc_columns.map(c => `
						<th class="aot-grp-start" style="border-top:3px solid ${c.color};">${__(c.label)}</th>
						<th>${__(c.label)} ${__('Status')}</th>
					`).join('')}
					<th class="aot-grp-start aot-priority-col">${__('Priority')}</th>
					<th style="width:40px;"></th>
				</tr>
			`);
		}
	}

	render_batch_row(it, colspan) {
		const docPair = (col) => {
			const d = (it.docs || {})[col.key];
			if (!d) {
				return `<td class="aot-grp-start"></td><td></td>`;
			}

			if (d.count && d.count > 1) {
				const plural = col.full_label || (col.label + 's');
				return `
					<td class="aot-grp-start" colspan="2">
						<span class="aot-doc-multi"
							style="color:${col.color};border-color:${col.color};"
							data-sales-order="${frappe.utils.escape_html(it.sales_order || '')}"
							data-project="${frappe.utils.escape_html(it.project || '')}"
							data-so-item="${frappe.utils.escape_html(it.so_item_name || '')}"
							data-item-code="${frappe.utils.escape_html(it.item_code || '')}"
							data-batch="${frappe.utils.escape_html(it.batch_no || '')}"
							data-key="${frappe.utils.escape_html(col.key)}"
							data-label="${frappe.utils.escape_html(plural)}"
							data-color="${frappe.utils.escape_html(col.color)}">
							${d.count} ${frappe.utils.escape_html(plural)}
						</span>
					</td>
				`;
			}

			const [bg, ink] = this.tone(d.status);
			return `
				<td class="aot-grp-start">
					<span class="aot-doc-link" style="color:${col.color};" data-doctype="${frappe.utils.escape_html(d.doctype || '')}" data-name="${frappe.utils.escape_html(d.name)}">${frappe.utils.escape_html(d.name)}</span>
				</td>
				<td><span class="aot-mini-pill" style="background:${bg};color:${ink};">${frappe.utils.escape_html(d.status || '')}</span></td>
			`;
		};

		const priorityClass = this.priority_class(it.priority);
		const rowKey = it.batch_no || it.so_item_name || it.sales_order;
		const checked = this.state.selected.has(rowKey) ? 'checked' : '';
		const showItemSubtitle = it.item_name && it.item_code && it.item_name.trim().toLowerCase() !== it.item_code.trim().toLowerCase();

		return `
		<tr class="aot-batch-row" data-batch="${frappe.utils.escape_html(it.batch_no || '')}" data-so="${frappe.utils.escape_html(it.sales_order || '')}">
			<td style="text-align:center;"><input type="checkbox" class="aot-row-check" data-sales-order="${frappe.utils.escape_html(it.sales_order || '')}" data-batch="${frappe.utils.escape_html(it.batch_no || '')}" ${checked}></td>
			<td class="aot-batch-cell">
				${it.batch_no ? `<span class="aot-batch-badge aot-batch-main">${frappe.utils.escape_html(it.batch_no)}</span>` : '<span class="aot-muted">—</span>'}
			</td>
			<td class="aot-item-cell" title="${frappe.utils.escape_html(it.description || it.item_name || '')}">
				<div class="aot-item-code aot-doc-link" data-doctype="Item" data-name="${frappe.utils.escape_html(it.item_code || '')}">${frappe.utils.escape_html(it.item_code || '—')}</div>
				${showItemSubtitle ? `<div class="aot-item-name">${frappe.utils.escape_html(it.item_name)}</div>` : ''}
			</td>
			<td class="aot-so-col">
				<a class="aot-so-link" data-sales-order="${frappe.utils.escape_html(it.sales_order || '')}" data-batch="${frappe.utils.escape_html(it.batch_no || '')}">${frappe.utils.escape_html(it.sales_order || '')}</a>
			</td>
			<td class="aot-customer-cell" title="${frappe.utils.escape_html(it.customer_name || it.customer || '')}">
				${it.customer ? `<span class="aot-doc-link aot-customer-link" data-doctype="Customer" data-name="${frappe.utils.escape_html(it.customer)}">${frappe.utils.escape_html(it.customer_name || it.customer)}</span>` : '<span class="aot-muted">—</span>'}
			</td>
			<td class="aot-num-cell">
				${it.qty != null ? `<span>${frappe.format(it.qty, { fieldtype: 'Float' })}</span>${it.delivered_qty ? `<div class="aot-muted" style="font-size:10.5px;">Del: ${frappe.format(it.delivered_qty, { fieldtype: 'Float' })}</div>` : ''}` : '<span class="aot-muted">—</span>'}
			</td>
			<td class="aot-num-cell">${it.amount != null ? format_currency(it.amount) : '<span class="aot-muted">—</span>'}</td>
			<td class="aot-date-cell">${it.delivery_date ? frappe.datetime.str_to_user(it.delivery_date) : '<span class="aot-muted">—</span>'}</td>
			<td class="aot-branch-cell">${it.branch ? `<span class="aot-branch-badge">${frappe.utils.escape_html(it.branch)}</span>` : '<span class="aot-muted">—</span>'}</td>
			<td class="aot-pending-cell">${it.pending_at ? `<span class="aot-pending-chip" title="${frappe.utils.escape_html(it.pending_at)}">${frappe.utils.escape_html(this.format_pending_at(it.pending_at))}</span>` : ''}</td>
			${this.doc_columns.map(col => docPair(col)).join('')}
			<td class="aot-grp-start aot-priority-col">${it.priority ? `<span class="aot-pri-badge ${priorityClass}">${frappe.utils.escape_html(it.priority)}</span>` : ''}</td>
			<td><button class="aot-view-btn" data-sales-order="${frappe.utils.escape_html(it.sales_order || '')}" data-batch="${frappe.utils.escape_html(it.batch_no || '')}" title="${__('Detailed view')}">${frappe.utils.icon('right', 'sm')}</button></td>
		</tr>
		`;
	}

	render_list_row(ao, colspan) {
		const docPair = (col) => {
			const d = ao.docs[col.key];
			if (!d) {
				return `<td class="aot-grp-start"></td><td></td>`;
			}

			if (d.count && d.count > 1) {
				const plural = col.full_label || (col.label + 's');
				return `
					<td class="aot-grp-start" colspan="2">
						<span class="aot-doc-multi"
							style="color:${col.color};border-color:${col.color};"
							data-sales-order="${frappe.utils.escape_html(ao.sales_order || '')}"
							data-project="${frappe.utils.escape_html(ao.project || '')}"
							data-key="${frappe.utils.escape_html(col.key)}"
							data-label="${frappe.utils.escape_html(plural)}"
							data-color="${frappe.utils.escape_html(col.color)}">
							${d.count} ${frappe.utils.escape_html(plural)}
						</span>
					</td>
				`;
			}

			const [bg, ink] = this.tone(d.status);
			return `
				<td class="aot-grp-start">
					<span class="aot-doc-link" style="color:${col.color};" data-doctype="${frappe.utils.escape_html(d.doctype || '')}" data-name="${frappe.utils.escape_html(d.name)}">${frappe.utils.escape_html(d.name)}</span>
				</td>
				<td><span class="aot-mini-pill" style="background:${bg};color:${ink};">${frappe.utils.escape_html(d.status || '')}</span></td>
			`;
		};

		const priorityClass = this.priority_class(ao.priority);
		const checked = this.state.selected.has(ao.sales_order) ? 'checked' : '';
		const isExpanded = this.state.expandedSos.has(ao.sales_order);
		const items = ao.items || [];
		const itemsCount = ao.items_count || items.length;

		const parentRowHtml = `
		<tr class="aot-so-row ${isExpanded ? 'expanded' : ''}" data-so="${frappe.utils.escape_html(ao.sales_order || '')}">
			<td style="text-align:center;">
				<button type="button" class="aot-expand-btn" data-sales-order="${frappe.utils.escape_html(ao.sales_order || '')}" title="${__('Toggle items')}">
					<svg class="aot-chevron-svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>
				</button>
			</td>
			<td><input type="checkbox" class="aot-row-check" data-sales-order="${frappe.utils.escape_html(ao.sales_order || '')}" ${checked}></td>
			<td class="aot-so-col">
				<a class="aot-so-link" data-sales-order="${frappe.utils.escape_html(ao.sales_order || '')}">${frappe.utils.escape_html(ao.sales_order || '')}</a>
			</td>
			<td class="aot-customer-cell" title="${frappe.utils.escape_html(ao.customer_name || ao.customer || '')}">
				${ao.customer ? `<span class="aot-doc-link aot-customer-link" data-doctype="Customer" data-name="${frappe.utils.escape_html(ao.customer)}">${frappe.utils.escape_html(ao.customer_name || ao.customer)}</span>` : '<span class="aot-muted">—</span>'}
			</td>
			<td class="aot-items-cell" style="text-align:center;">
				<span class="aot-items-badge" data-sales-order="${frappe.utils.escape_html(ao.sales_order || '')}" title="${__('Click to toggle items')}">
					${itemsCount} ${itemsCount === 1 ? __('Item') : __('Items')}
				</span>
			</td>
			<td class="aot-num-cell">
				${ao.total_qty != null ? `<span>${frappe.format(ao.total_qty, { fieldtype: 'Float' })}</span>${ao.delivered_qty ? `<div class="aot-muted" style="font-size:10.5px;">Del: ${frappe.format(ao.delivered_qty, { fieldtype: 'Float' })}</div>` : ''}` : '<span class="aot-muted">—</span>'}
			</td>
			<td class="aot-num-cell">${ao.grand_total != null ? format_currency(ao.grand_total) : '<span class="aot-muted">—</span>'}</td>
			<td class="aot-date-cell">${ao.delivery_date ? frappe.datetime.str_to_user(ao.delivery_date) : '<span class="aot-muted">—</span>'}</td>
			<td class="aot-branch-cell">${ao.branch ? `<span class="aot-branch-badge">${frappe.utils.escape_html(ao.branch)}</span>` : '<span class="aot-muted">—</span>'}</td>
			<td class="aot-pending-cell">${ao.pending_at ? `<span class="aot-pending-chip" title="${frappe.utils.escape_html(ao.pending_at)}">${frappe.utils.escape_html(this.format_pending_at(ao.pending_at))}</span>` : ''}</td>
			${this.doc_columns.map(col => docPair(col)).join('')}
			<td class="aot-grp-start aot-priority-col">${ao.priority ? `<span class="aot-pri-badge ${priorityClass}">${frappe.utils.escape_html(ao.priority)}</span>` : ''}</td>
			<td><button class="aot-view-btn" data-sales-order="${frappe.utils.escape_html(ao.sales_order || '')}" title="${__('Detailed view')}">${frappe.utils.icon('right', 'sm')}</button></td>
		</tr>
		`;

		const childRowHtml = `
		<tr class="aot-child-row ${isExpanded ? 'expanded' : ''}" data-child-of="${frappe.utils.escape_html(ao.sales_order || '')}">
			<td colspan="${colspan}" class="aot-child-cell">
				<div class="aot-nested-wrapper">
					<div class="aot-nested-header">
						<div class="aot-nested-title">
							<span class="aot-nested-tag">${__('Line Items & Batches')}</span>
							<span class="aot-nested-so-ref">${frappe.utils.escape_html(ao.sales_order || '')}</span>
						</div>
						<div class="aot-nested-meta">
							<span class="aot-meta-item">${items.length} ${items.length === 1 ? __('Batch / Item') : __('Batches / Items')}</span>
							${ao.total_qty != null ? `<span class="aot-meta-item"><span class="aot-meta-dot">&bull;</span> ${__('Total Qty')}: <b>${frappe.format(ao.total_qty, { fieldtype: 'Float' })}</b></span>` : ''}
							${ao.grand_total != null ? `<span class="aot-meta-item"><span class="aot-meta-dot">&bull;</span> ${__('Grand Total')}: <b>${format_currency(ao.grand_total)}</b></span>` : ''}
						</div>
					</div>
					<div class="aot-nested-table-wrap">
						<table class="aot-nested-table">
							<thead>
								<tr>
									<th style="width:44px; text-align:center;">${__('Line')}</th>
									<th class="aot-nested-item-col" style="min-width:180px; max-width:240px;">${__('Item Code & Name')}</th>
									<th class="aot-nested-batch-col" style="min-width:120px; max-width:160px;">${__('Batch No')}</th>
									<th style="text-align:right; width:85px;">${__('Ordered')}</th>
									<th style="text-align:right; width:80px;">${__('Delivered')}</th>
									<th style="text-align:right; width:80px;">${__('Pending')}</th>
									<th style="text-align:right; width:95px;">${__('Amount')}</th>
									<th style="width:95px;">${__('Delivery Date')}</th>
									<th class="aot-nested-docs-col" style="min-width:280px;">${__('Document Trail')}</th>
									<th style="min-width:120px;">${__('Stage')}</th>
								</tr>
							</thead>
							<tbody>
								${items.length ? items.map(it => {
									const showItemSubtitle = it.item_name && it.item_code && it.item_name.trim().toLowerCase() !== it.item_code.trim().toLowerCase();
									const docTrailPills = this.doc_columns.map(col => {
										const d = (it.docs || {})[col.key];
										if (!d) return '';
										const [bg, ink] = this.tone(d.status);
										if (d.count > 1) {
											return `
												<span class="aot-nested-doc-pill aot-doc-multi"
													style="color:${col.color};border-color:${col.color};"
													data-sales-order="${frappe.utils.escape_html(ao.sales_order || '')}"
													data-so-item="${frappe.utils.escape_html(it.so_item_name || '')}"
													data-item-code="${frappe.utils.escape_html(it.item_code || '')}"
													data-batch="${frappe.utils.escape_html(it.batch_no || '')}"
													data-key="${col.key}"
													data-label="${col.full_label || col.label}"
													data-color="${col.color}"
													title="${col.label}: ${d.count} docs">
													${col.label} (${d.count})
												</span>
											`;
										}
										return `
											<span class="aot-nested-doc-pill aot-doc-link"
												style="color:${col.color};"
												data-doctype="${frappe.utils.escape_html(d.doctype || '')}"
												data-name="${frappe.utils.escape_html(d.name)}"
												title="${col.label}: ${frappe.utils.escape_html(d.name)} (${d.status || ''})">
												${col.label}: ${frappe.utils.escape_html(d.name)}
												<span class="aot-nested-mini-pill" style="background:${bg};color:${ink};">${frappe.utils.escape_html(d.status || '')}</span>
											</span>
										`;
									}).filter(Boolean).join(' ');

									return `
									<tr>
										<td style="text-align:center;"><span class="aot-line-badge">#${it.line_no || '1'}</span></td>
										<td title="${frappe.utils.escape_html(it.description || it.item_name || '')}">
											<div class="aot-item-code aot-doc-link" data-doctype="Item" data-name="${frappe.utils.escape_html(it.item_code || '')}">${frappe.utils.escape_html(it.item_code || '—')}</div>
											${showItemSubtitle ? `<div class="aot-item-name">${frappe.utils.escape_html(it.item_name)}</div>` : ''}
										</td>
										<td>
											${it.batch_no ? `<span class="aot-batch-badge aot-batch-main">${frappe.utils.escape_html(it.batch_no)}</span>` : '<span class="aot-muted">—</span>'}
										</td>
										<td style="text-align:right; font-weight:600;">${it.qty != null ? frappe.format(it.qty, { fieldtype: 'Float' }) : '—'}</td>
										<td style="text-align:right;">${it.delivered_qty != null ? frappe.format(it.delivered_qty, { fieldtype: 'Float' }) : '0'}</td>
										<td style="text-align:right; font-weight:600; color:${(it.pending_qty || 0) > 0 ? 'var(--aot-amber-ink)' : 'inherit'};">
											${it.pending_qty != null ? frappe.format(it.pending_qty, { fieldtype: 'Float' }) : '0'}
										</td>
										<td style="text-align:right; font-weight:600;">${it.amount != null ? format_currency(it.amount) : '—'}</td>
										<td>${it.delivery_date ? frappe.datetime.str_to_user(it.delivery_date) : '<span class="aot-muted">—</span>'}</td>
										<td>
											<div class="aot-nested-docs-wrap">${docTrailPills || '<span class="aot-muted">—</span>'}</div>
										</td>
										<td>
											${it.pending_at ? `<span class="aot-pending-chip" style="font-size:11px;padding:2px 8px;" title="${frappe.utils.escape_html(it.pending_at)}">${frappe.utils.escape_html(this.format_pending_at(it.pending_at))}</span>` : ''}
										</td>
									</tr>
									`;
								}).join('') : `<tr><td colspan="10" class="aot-empty-row" style="padding:16px;">${__('No item lines found on this Sales Order.')}</td></tr>`}
							</tbody>
						</table>
					</div>
				</div>
			</td>
		</tr>
		`;

		return parentRowHtml + childRowHtml;
	}

	priority_class(priority) {
		if (!priority) return '';
		if (priority.startsWith('Overdue')) return 'aot-pri-overdue';
		const MAP = {
			Low: 'aot-pri-low',
			Medium: 'aot-pri-medium',
			High: 'aot-pri-high',
			Urgent: 'aot-pri-urgent'
		};
		return MAP[priority] || 'aot-pri-low';
	}

	format_pending_at(text) {
		if (!text) return text;
		return text.split(/\s*\/\s*/)[0];
	}

	tone(status) {
		const TONE = {
			'Partially Ordered': 'amber', Submitted: 'amber', Expired: 'red', 'To Receive and Bill': 'amber',
			Received: 'green', Unpaid: 'amber', Draft: 'gray', Approved: 'green', Completed: 'green',
			'Pending Approval': 'amber', Passed: 'green', Failed: 'red', Open: 'amber', Closed: 'green',
			Booked: 'green', Confirmed: 'green', Converted: 'green', Posted: 'green', Paid: 'green'
		};
		const MAP = {
			amber: ['var(--aot-amber-bg)', 'var(--aot-amber-ink)'],
			red: ['var(--aot-red-bg)', 'var(--aot-red-ink)'],
			green: ['var(--aot-green-bg)', 'var(--aot-green-ink)'],
			gray: ['var(--aot-gray-bg)', 'var(--aot-gray-ink)']
		};
		return MAP[TONE[status] || 'gray'];
	}

	// ---------------------------------------------------------------- tab 2
	open_detail(sales_order, batch_no) {
		this.state.currentSo = sales_order;
		if (batch_no !== undefined) {
			this.state.currentBatch = batch_no || null;
		} else if (!this.state.currentBatch && this.batch_control) {
			this.state.currentBatch = this.batch_control.get_value() || null;
		}
		const branch = this.branch_control ? this.branch_control.get_value() : '';
		frappe.call({
			method: this.method.detail,
			args: { sales_order, branch, batch_no: this.state.currentBatch },
			freeze: true,
			callback: (r) => {
				if (!r.message) return;
				this.render_detail(r.message);
				this.go_tab(2);
			}
		});
	}

	render_detail(so) {
		const headerTitle = so.batch_no ? `${so.sales_order} \u00b7 ${so.batch_no}` : (so.title && so.title !== so.sales_order ? `${so.sales_order} \u00b7 ${so.title}` : so.sales_order);
		this.$wrap.find('.aot-d-title').text(headerTitle);
		const dateFmt = so.date ? frappe.datetime.str_to_user(so.date) : '';
		const branchTxt = so.branch ? ` \u00b7 ${__('Branch')}: ${so.branch}` : '';
		const custTxt = so.customer_name || so.customer ? (so.customer_name && so.customer && so.customer_name !== so.customer ? `${so.customer_name} (${so.customer})` : (so.customer_name || so.customer)) : '';
		const batchTxt = so.batch_no ? ` \u00b7 ${__('Batch')}: <span class="aot-batch-badge aot-batch-main" style="margin-left:4px;vertical-align:middle;">${frappe.utils.escape_html(so.batch_no)}</span>` : '';
		this.$wrap.find('.aot-d-sub').html(
			`${custTxt}${branchTxt}${dateFmt ? ' \u00b7 ' + __('Date') + ': ' + dateFmt : ''}${batchTxt}`
		);
		const [bg, ink] = this.tone(so.status);
		this.$wrap.find('.aot-d-status-pill').css({ background: bg, color: ink }).text(so.status || '');

		this.render_overview(so.overview);
		this.render_items_table(so.items);
		this.render_doc_catalog(so);
	}

	render_overview(o) {
		const inr = (n) => format_currency(n || 0);
		const cards = [
			[__('Est. Revenue'), inr(o.revenue), __('From Sales Invoice, or Sales Order if none yet'), undefined, '#0284C7'],
			[__('Total RM Cost'), inr(o.rm_cost), __('Valuation rate \u00d7 qty consumed'), undefined, '#D97706'],
			[__('Total Indirect Expense'), inr(o.indirect), __('Overheads allocated to this order'), undefined, '#E11D48'],
			[__('Profitability %'), (o.profit_pct || 0).toFixed(1) + '%', __('Profit \u00f7 estimated revenue'), o.profit_pct >= 0, '#7C3AED'],
			[__('Profit'), inr(o.profit), __('Revenue \u2212 RM cost \u2212 indirect expense'), o.profit >= 0, '#059669']
		];
		this.$wrap.find('.aot-overview-grid').html(cards.map(([label, value, sub, positive, color]) => `
			<div class="aot-stat-card" style="border-top:3px solid ${color};">
				<div class="aot-stat-label" style="color:${color};">${label}</div>
				<div class="aot-stat-value ${positive === true ? 'aot-positive' : (positive === false ? 'aot-negative' : '')}">${value}</div>
				<div class="aot-stat-sub">${sub}</div>
			</div>
		`).join(''));
	}

	render_items_table(items_data) {
		const tbody = this.$wrap.find('.aot-items-tbody').empty();
		const items = (items_data && items_data.order_items) ? items_data.order_items : (Array.isArray(items_data) ? items_data : []);
		if (!items || !items.length) {
			tbody.html(`<tr><td colspan="12" class="aot-empty-row">${__('No items found for this Sales Order / Batch.')}</td></tr>`);
			return;
		}

		items.forEach((it) => {
			const comps = it.components || [];
			const compsCount = comps.length;
			const hasComps = compsCount > 0;
			const branchBadge = it.branch ? `<span class="aot-branch-badge">${frappe.utils.escape_html(it.branch)}</span>` : '<span class="aot-muted">—</span>';
			const batchBadge = it.batch_no ? `<span class="aot-batch-badge aot-batch-main">${frappe.utils.escape_html(it.batch_no)}</span>` : '<span class="aot-muted">—</span>';
			const showItemSubtitle = it.item_name && it.item_code && it.item_name.trim().toLowerCase() !== it.item_code.trim().toLowerCase();

			const mainRow = `
				<tr class="aot-item-row" data-line="${it.line_no}">
					<td style="text-align:center;">
						${hasComps ? `
							<button type="button" class="aot-expand-btn aot-item-expand-btn" data-line="${it.line_no}" title="${__('Toggle Raw Materials')}">
								<svg class="aot-chevron-svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>
							</button>
						` : ''}
					</td>
					<td class="aot-line-cell" style="text-align:center;">
						<span class="aot-line-badge">#${it.line_no || '1'}</span>
					</td>
					<td title="${frappe.utils.escape_html(it.description || it.item_name || '')}">
						<div class="aot-item-code aot-doc-link" data-doctype="Item" data-name="${frappe.utils.escape_html(it.item_code || '')}">${frappe.utils.escape_html(it.item_code || '—')}</div>
						${showItemSubtitle ? `<div class="aot-item-name">${frappe.utils.escape_html(it.item_name)}</div>` : ''}
					</td>
					<td>${batchBadge}</td>
					<td class="aot-num" style="text-align:right; font-weight:600;">${it.qty != null ? frappe.format(it.qty, { fieldtype: 'Float' }) : '—'}</td>
					<td class="aot-num" style="text-align:right;">${it.delivered_qty != null ? frappe.format(it.delivered_qty, { fieldtype: 'Float' }) : '0'}</td>
					<td class="aot-num" style="text-align:right; font-weight:600; color:${(it.pending_qty || 0) > 0 ? 'var(--aot-amber-ink)' : 'inherit'};">
						${it.pending_qty != null ? frappe.format(it.pending_qty, { fieldtype: 'Float' }) : '0'}
					</td>
					<td class="aot-num" style="text-align:right;">${it.rate != null ? format_currency(it.rate) : '—'}</td>
					<td class="aot-num" style="text-align:right; font-weight:600;">${it.amount != null ? format_currency(it.amount) : '—'}</td>
					<td>${it.delivery_date ? frappe.datetime.str_to_user(it.delivery_date) : '<span class="aot-muted">—</span>'}</td>
					<td>${branchBadge}</td>
					<td style="text-align:center;">
						${hasComps ? `
							<button type="button" class="aot-bom-toggle-btn aot-mini-pill" data-line="${it.line_no}" style="background:var(--aot-accent-soft);color:var(--aot-accent);cursor:pointer;font-weight:600;border:none;">
								${compsCount} ${compsCount === 1 ? __('Raw Material') : __('Raw Materials')}
							</button>
						` : '<span class="aot-muted">—</span>'}
					</td>
				</tr>
			`;

			const compsRow = hasComps ? `
				<tr class="aot-item-child-row" data-child-of-line="${it.line_no}">
					<td colspan="12" style="padding:0 0 16px 40px; background:var(--aot-panel-subtle);">
						<div style="border:1px solid var(--aot-line); border-radius:8px; overflow:hidden; margin:8px 16px 8px 0; background:var(--aot-panel);">
							<div style="padding:8px 14px; background:var(--aot-bg); font-weight:600; font-size:12px; color:var(--aot-ink-soft); border-bottom:1px solid var(--aot-line); display:flex; justify-content:space-between;">
								<span>${__('Raw Materials / BOM Components for Line #{0}', [it.line_no])} &middot; ${frappe.utils.escape_html(it.item_name || it.item_code)}</span>
								<span>${compsCount} ${compsCount === 1 ? __('Item') : __('Items')}</span>
							</div>
							<table class="aot-flat-table" style="margin:0; font-size:12px;">
								<thead>
									<tr style="background:var(--aot-panel-subtle);">
										<th style="min-width:180px;">${__('Component Code & Name')}</th>
										<th class="aot-num" style="text-align:right; width:110px;">${__('Qty Needed')}</th>
										<th class="aot-num" style="text-align:right; width:110px;">${__('Total Ordered')}</th>
										<th class="aot-num" style="text-align:right; width:110px;">${__('Consumed')}</th>
										<th class="aot-num" style="text-align:right; width:120px;">${__('Valuation Rate')}</th>
									</tr>
								</thead>
								<tbody>
									${comps.map(c => `
										<tr>
											<td>
												<div class="aot-item-code aot-doc-link" data-doctype="Item" data-name="${frappe.utils.escape_html(c.component_code || '')}">${frappe.utils.escape_html(c.component_code || '—')}</div>
												${c.component_name && c.component_name !== c.component_code ? `<div class="aot-item-name" style="font-size:11px;">${frappe.utils.escape_html(c.component_name)}</div>` : ''}
											</td>
											<td class="aot-num" style="text-align:right; font-weight:600;">${c.qty_needed != null ? frappe.format(c.qty_needed, { fieldtype: 'Float' }) : '—'}</td>
											<td class="aot-num" style="text-align:right;">${c.total_ordered != null ? frappe.format(c.total_ordered, { fieldtype: 'Float' }) : '—'}</td>
											<td class="aot-num" style="text-align:right; font-weight:600; color:var(--aot-green-ink);">${c.consumed != null ? frappe.format(c.consumed, { fieldtype: 'Float' }) : '0'}</td>
											<td class="aot-num" style="text-align:right;">${c.valuation_rate != null ? format_currency(c.valuation_rate) : '—'}</td>
										</tr>
									`).join('')}
								</tbody>
							</table>
						</div>
					</td>
				</tr>
			` : '';

			tbody.append(mainRow + compsRow);
		});
	}

	render_doc_catalog(so) {
		const grid = this.$wrap.find('.aot-doc-catalog-grid').empty();
		const docOrder = so.doc_order || [];
		const docMeta = so.doc_meta || {};
		const docs = so.docs || {};

		docOrder.forEach((key) => {
			const meta = docMeta[key];
			if (!meta) return;
			const d = docs[key];
			const accent = this.doc_type_colors[key] || 'var(--aot-accent)';

			if (!meta.queryable) {
				grid.append(`
					<div class="aot-doc-card empty unavailable" style="border-top:3px solid ${accent};opacity:.6;">
						<div class="aot-doc-count-badge aot-count-zero">0</div>
						<div class="aot-doc-type-label">${meta.short} \u00b7 ${meta.label}</div>
						<div class="aot-doc-code empty">${__('Not applicable')}</div>
					</div>
				`);
				return;
			}

			if (!d) {
				grid.append(`
					<div class="aot-doc-card empty" style="border-top:3px solid ${accent};">
						<div class="aot-doc-count-badge aot-count-zero">0</div>
						<div class="aot-doc-type-label">${meta.short} \u00b7 ${meta.label}</div>
						<div class="aot-doc-code empty">${__('Not generated')}</div>
					</div>
				`);
				return;
			}

			const [bg, ink] = this.tone(d.status);

			if (d.count && d.count > 1) {
				grid.append(`
					<div class="aot-doc-card aot-doc-card-multi" style="border-top:3px solid ${accent};"
						data-sales-order="${frappe.utils.escape_html(so.sales_order || '')}"
						data-project="${frappe.utils.escape_html(so.project || '')}"
						data-batch="${frappe.utils.escape_html(so.batch_no || '')}"
						data-key="${frappe.utils.escape_html(key)}"
						data-label="${frappe.utils.escape_html(meta.label + 's')}"
						data-color="${frappe.utils.escape_html(accent)}">
						<div class="aot-doc-count-badge aot-count-pos">${d.count}</div>
						<div class="aot-doc-type-label">${meta.short} \u00b7 ${meta.label}</div>
						<div class="aot-doc-code" style="color:${accent};">${d.count} ${meta.label}s \u2192</div>
						<div class="aot-doc-multi-hint">${__('Click to browse all {0}', [d.count])}</div>
					</div>
				`);
				return;
			}

			grid.append(`
				<div class="aot-doc-card" style="border-top:3px solid ${accent};"
					data-doctype="${frappe.utils.escape_html(d.doctype || meta.doctype)}"
					data-name="${frappe.utils.escape_html(d.name)}"
					data-batch="${frappe.utils.escape_html(so.batch_no || '')}">
					<div class="aot-doc-count-badge ${d.count > 0 ? 'aot-count-pos' : 'aot-count-zero'}">${d.count || 1}</div>
					<div class="aot-doc-type-label">${meta.short} \u00b7 ${meta.label}</div>
					<div class="aot-doc-code" style="color:${accent};">${frappe.utils.escape_html(d.name)}</div>
					<div class="aot-mini-pill" style="background:${bg};color:${ink};">${frappe.utils.escape_html(d.status || '')}</div>
				</div>
			`);
		});
	}

	open_doc_modal(doctype, name, batch_no) {
		if (!doctype || !name) return;
		batch_no = batch_no || (this.batch_control ? this.batch_control.get_value() : '') || this.state.currentBatch || null;
		frappe.call({
			method: this.method.doc_summary,
			args: { doctype, name, batch_no },
			freeze: true,
			callback: (r) => {
				const d = r.message;
				if (!d) return;
				const $m = this.$wrap.find('.aot-modal').data('doctype', d.doctype).data('name', d.name);
				const eyebrowText = d.batch_no ? `${d.doctype} \u00b7 Batch: ${d.batch_no}` : d.doctype;
				$m.find('.aot-modal-eyebrow').text(eyebrowText);
				$m.find('.aot-modal-title').html(`<span>${frappe.utils.escape_html(d.name)}</span> <button class="btn btn-xs btn-default aot-doc-link" data-doctype="${frappe.utils.escape_html(d.doctype)}" data-name="${frappe.utils.escape_html(d.name)}" title="${__('Open Form')}"><i class="fa fa-external-link"></i> ${__('Open')}</button>`);

				const [bg, ink] = this.tone(d.status);
				const statusPill = d.status ? `<span class="aot-mini-pill" style="background:${bg};color:${ink};">${frappe.utils.escape_html(d.status)}</span>` : '';

				const stats = [];
				if (d.status) stats.push(`<div><div class="aot-modal-stat-k">${__('Status')}</div><div class="aot-modal-stat-v">${statusPill}</div></div>`);
				if (d.sales_order) {
					stats.push(`<div><div class="aot-modal-stat-k">${__('Sales Order')}</div><div class="aot-modal-stat-v"><a href="javascript:void(0)" class="aot-doc-link" data-doctype="Sales Order" data-name="${frappe.utils.escape_html(d.sales_order)}">${frappe.utils.escape_html(d.sales_order)}</a></div></div>`);
				}
				if (d.party_name) {
					stats.push(`<div><div class="aot-modal-stat-k">${frappe.utils.escape_html(d.party_label || __('Party'))}</div><div class="aot-modal-stat-v text-truncate" title="${frappe.utils.escape_html(d.party_name)}">${frappe.utils.escape_html(d.party_name)}</div></div>`);
				}
				if (d.date) {
					stats.push(`<div><div class="aot-modal-stat-k">${__('Date')}</div><div class="aot-modal-stat-v">${frappe.datetime.str_to_user(d.date)}</div></div>`);
				}
				if (d.total_qty) {
					stats.push(`<div><div class="aot-modal-stat-k">${__('Total Quantity')}</div><div class="aot-modal-stat-v">${format_number(d.total_qty)}</div></div>`);
				}
				if (d.grand_total) {
					stats.push(`<div><div class="aot-modal-stat-k">${__('Grand Total')}</div><div class="aot-modal-stat-v">${format_currency(d.grand_total)}</div></div>`);
				}

				$m.find('.aot-modal-stats').html(stats.join(''));

				const $items = $m.find('.aot-modal-items').empty();
				if (!d.items || !d.items.length) {
					$items.html(`<div class="aot-empty-row" style="padding:24px;text-align:center;color:var(--aot-ink-faint);">${__('No item rows on this document.')}</div>`);
				} else {
					d.items.forEach((it, idx) => {
						const refPill = it.reference && it.reference.name ? `
							<a href="javascript:void(0)" class="aot-modal-pill-tag aot-doc-link" data-doctype="${frappe.utils.escape_html(it.reference.doctype)}" data-name="${frappe.utils.escape_html(it.reference.name)}" title="${__('Open Reference')}">
								\u2192 ${frappe.utils.escape_html(it.reference.doctype)}: <strong>${frappe.utils.escape_html(it.reference.name)}</strong>
							</a>` : '';

						const batchBadge = it.batch_no ? `<span class="aot-modal-pill-badge"><i class="fa fa-tag"></i> Batch: ${frappe.utils.escape_html(it.batch_no)}</span>` : '';
						const whBadge = it.warehouse ? `<span class="aot-modal-pill-badge"><i class="fa fa-building-o"></i> ${frappe.utils.escape_html(it.warehouse)}</span>` : '';
						const dateBadge = it.delivery_date ? `<span class="aot-modal-pill-badge"><i class="fa fa-calendar"></i> ${frappe.datetime.str_to_user(it.delivery_date)}</span>` : '';

						const rateAmount = [];
						if (it.rate !== null && it.rate !== undefined && it.rate > 0) {
							rateAmount.push(`<span>Rate: <strong>${format_currency(it.rate)}</strong></span>`);
						}
						if (it.amount !== null && it.amount !== undefined && it.amount > 0) {
							rateAmount.push(`<span>Amount: <strong>${format_currency(it.amount)}</strong></span>`);
						}
						const priceInfo = rateAmount.length ? `<div class="aot-modal-item-price">${rateAmount.join(' &middot; ')}</div>` : '';

						const descHtml = it.description && it.description !== it.item_name && it.description !== it.item_code ? `
							<div class="aot-modal-item-desc">${frappe.utils.escape_html(it.description)}</div>` : '';

						$items.append(`
							<div class="aot-modal-item-card">
								<div class="aot-modal-item-top">
									<div class="aot-modal-item-left">
										<span class="aot-modal-item-idx">#${idx + 1}</span>
										<a href="javascript:void(0)" class="aot-modal-item-code aot-doc-link" data-doctype="Item" data-name="${frappe.utils.escape_html(it.item_code)}" title="${__('Click to open Item master')}">
											${frappe.utils.escape_html(it.item_code)} <i class="fa fa-external-link" style="font-size:10px;margin-left:3px;opacity:0.7;"></i>
										</a>
										<span class="aot-modal-item-title">${frappe.utils.escape_html(it.item_name || it.item_code)}</span>
									</div>
									<div class="aot-modal-item-qty">
										<span class="aot-modal-qty-num">${format_number(it.qty)}</span>
										<span class="aot-modal-qty-uom">${frappe.utils.escape_html(it.uom || '')}</span>
									</div>
								</div>
								${descHtml}
								<div class="aot-modal-item-bottom">
									<div class="aot-modal-item-meta">
										${batchBadge}
										${whBadge}
										${dateBadge}
										${refPill}
									</div>
									${priceInfo}
								</div>
							</div>
						`);
					});
				}

				this.$wrap.find('.aot-modal-backdrop').addClass('open');
			}
		});
	}

	open_doc_list_modal(sales_order, project, key, label, color, so_item_name, item_code, batch_no) {
		const branch = this.branch_control ? this.branch_control.get_value() : '';
		const keyDoctypeMap = {
			quote: 'Quotation',
			so: 'Sales Order',
			mr: 'Material Request',
			po: 'Purchase Order',
			sco: 'Subcontracting Order',
			scr: 'Subcontracting Receipt',
			pr: 'Purchase Receipt',
			pi: 'Purchase Invoice',
			dn: 'Delivery Note',
			si: 'Sales Invoice',
			pe_in: 'Payment Entry',
			pe_out: 'Payment Entry',
			je: 'Journal Entry'
		};
		const defaultDoctype = keyDoctypeMap[key] || '';

		frappe.call({
			method: this.method.doc_list,
			args: { sales_order, project, key, branch, so_item_name, item_code, batch_no },
			freeze: true,
			callback: (r) => {
				const rows = r.message || [];
				const $m = this.$wrap.find('.aot-doclist-modal').data('batch', batch_no || '');
				const suffix = batch_no ? ` \u00b7 Batch: ${batch_no}` : (sales_order ? ` \u00b7 ${sales_order}` : (project ? ` \u00b7 ${project}` : ''));
				$m.find('.aot-doclist-eyebrow').text(`${label}${suffix}`);
				$m.find('.aot-doclist-title').text(__('{0} linked to this record ({1})', [label, rows.length]));

				const $list = $m.find('.aot-doclist-rows').empty();
				if (!rows.length) {
					$list.html(`<div class="aot-empty-row">${__('No documents found.')}</div>`);
				} else {
					rows.forEach((d) => {
						const [bg, ink] = this.tone(d.status);
						const docType = d.doctype || defaultDoctype;
						const dateStr = d.creation ? frappe.datetime.str_to_user(d.creation.split(' ')[0]) : '';
						const amt = d.amount ? format_currency(d.amount) : '';
						$list.append(`
							<div class="aot-doclist-row" data-doctype="${frappe.utils.escape_html(docType)}" data-name="${frappe.utils.escape_html(d.name)}" data-batch="${frappe.utils.escape_html(batch_no || '')}">
								<div class="aot-doclist-row-main">
									<div class="aot-doclist-name" style="color:${color};">${frappe.utils.escape_html(d.name)}</div>
									<div class="aot-doclist-sub">${dateStr ? __('Created') + ' ' + dateStr : ''} ${amt ? '\u00b7 ' + amt : ''}</div>
								</div>
								<div class="aot-doclist-row-right">
									${d.status ? `<span class="aot-mini-pill" style="background:${bg};color:${ink};">${frappe.utils.escape_html(d.status)}</span>` : ''}
									<span class="aot-doclist-arrow">${frappe.utils.icon('right', 'sm')}</span>
								</div>
							</div>
						`);
					});
				}

				this.$wrap.find('.aot-doclist-backdrop').addClass('open');
			}
		});
	}

	css() {
		return `
		.ao-tracker-wrap{
			--aot-bg:#F8FAFC; --aot-panel:#FFFFFF; --aot-panel-subtle:#F8FAFD;
			--aot-line:#E2E8F0; --aot-line-soft:#EDF2F7;
			--aot-ink:#0F172A; --aot-ink-soft:#475569; --aot-ink-faint:#94A3B8;
			--aot-accent:#2563EB; --aot-accent-soft:#EFF6FF;
			--aot-green-bg:#DCFCE7; --aot-green-ink:#15803D;
			--aot-amber-bg:#FEF3C7; --aot-amber-ink:#B45309;
			--aot-orange-bg:#FFEDD5; --aot-orange-ink:#C2410C;
			--aot-red-bg:#FEE2E2; --aot-red-ink:#B91C1C;
			--aot-overdue-bg:#7F1D1D; --aot-overdue-ink:#FEE2E2;
			--aot-purple-bg:#F3E8FF; --aot-purple-ink:#7E22CE;
			--aot-gray-bg:#F1F5F9; --aot-gray-ink:#475569;
			--aot-radius:12px; --aot-shadow:0 1px 3px rgba(15,23,42,0.06);
			background:var(--aot-bg); color:var(--aot-ink); min-height:100vh;
			font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
			padding:24px 32px;
		}

		.ao-tracker-wrap[data-theme="dark"]{
			--aot-bg:#0B0E14; --aot-panel:#121620; --aot-panel-subtle:#181D2A;
			--aot-line:#232A3B; --aot-line-soft:#1B2130;
			--aot-ink:#F1F5F9; --aot-ink-soft:#94A3B8; --aot-ink-faint:#64748B;
			--aot-accent:#3B82F6; --aot-accent-soft:#1E293B;
			--aot-green-bg:#064E3B; --aot-green-ink:#6EE7B7;
			--aot-amber-bg:#78350F; --aot-amber-ink:#FDE68A;
			--aot-orange-bg:#7C2D12; --aot-orange-ink:#FFEDD5;
			--aot-red-bg:#7F1D1D; --aot-red-ink:#FCA5A5;
			--aot-overdue-bg:#450A0A; --aot-overdue-ink:#FECACA;
			--aot-purple-bg:#581C87; --aot-purple-ink:#E9D5FF;
			--aot-gray-bg:#1E293B; --aot-gray-ink:#CBD5E1;
			--aot-shadow:0 2px 6px rgba(0,0,0,0.4);
		}

		.ao-tracker-wrap[data-theme="dark"] .aot-status-table thead th{
			background:linear-gradient(180deg,#141923 0%,#181E2B 100%);
		}
		.ao-tracker-wrap[data-theme="dark"] .aot-status-table tbody tr:nth-child(even){ background:#191c26; }
		.ao-tracker-wrap[data-theme="dark"] .aot-stat-card{ background:#151A26; }
		.ao-tracker-wrap[data-theme="dark"] .aot-doc-card.empty{ background:#151A26; }

		.ao-tracker-wrap .aot-topbar{display:flex; align-items:center; justify-content:space-between; margin-bottom:20px; gap:16px; flex-wrap:wrap;}
		.ao-tracker-wrap .aot-topbar-title{display:flex; align-items:center; gap:12px;}
		.ao-tracker-wrap .aot-topbar-badge{width:36px; height:36px; border-radius:10px; background:linear-gradient(135deg,#2563EB,#4F46E5); color:#fff; font-weight:800; font-size:13px; display:flex; align-items:center; justify-content:center; letter-spacing:-.02em; box-shadow:0 4px 10px rgba(37,99,235,.28);}
		.ao-tracker-wrap .aot-topbar-heading{font-size:17px; font-weight:700; letter-spacing:-.01em; margin:0;}
		.ao-tracker-wrap .aot-topbar-sub{font-size:12px; color:var(--aot-ink-faint); margin-top:2px;}
		.ao-tracker-wrap .aot-topbar-actions{display:flex; align-items:center; gap:10px;}
		.ao-tracker-wrap .aot-toggle{display:inline-flex; background:var(--aot-panel); border:1px solid var(--aot-line); border-radius:9px; padding:3px;}
		.ao-tracker-wrap .aot-toggle-btn{border:none; background:transparent; padding:6px 14px; font-size:12.5px; font-weight:600; color:var(--aot-ink-soft); border-radius:6px; cursor:pointer; transition:.15s;}
		.ao-tracker-wrap .aot-toggle-btn.active{background:var(--aot-accent); color:#fff; box-shadow:0 2px 6px rgba(37,99,235,.28);}
		.ao-tracker-wrap .aot-icon-btn{border:1px solid var(--aot-line); background:var(--aot-panel); color:var(--aot-ink-soft); width:32px; height:32px; border-radius:8px; display:inline-flex; align-items:center; justify-content:center; cursor:pointer; transition:.15s;}
		.ao-tracker-wrap .aot-icon-btn:hover{color:var(--aot-accent); border-color:var(--aot-accent);}

		.ao-tracker-wrap .aot-view{display:none;}
		.ao-tracker-wrap .aot-view.active{display:block;}

		.ao-tracker-wrap .aot-filters{
			display:flex; flex-direction:column; gap:10px; margin-bottom:18px;
			background:var(--aot-panel); border:1px solid var(--aot-line); border-radius:var(--aot-radius);
			padding:12px 14px; box-shadow:var(--aot-shadow);
		}
		.ao-tracker-wrap .aot-filter-row{
			display:flex; align-items:center; gap:10px; flex-wrap:wrap;
		}
		.ao-tracker-wrap .aot-filter-row-primary{
			justify-content:space-between;
		}
		.ao-tracker-wrap .aot-filter-group{
			display:flex; align-items:center; gap:10px; flex-wrap:wrap; flex:1;
		}
		.ao-tracker-wrap .aot-pill-field{
			display:inline-flex; align-items:center; gap:7px;
			background:var(--aot-bg); border:1px solid var(--aot-line); border-radius:8px;
			padding:0 10px; height:36px; box-sizing:border-box; transition:border-color .15s, box-shadow .15s;
		}
		.ao-tracker-wrap .aot-pill-field:focus-within{
			border-color:var(--aot-accent); box-shadow:0 0 0 2px var(--aot-accent-soft);
		}
		.ao-tracker-wrap .aot-pill-icon{
			display:inline-flex; align-items:center; justify-content:center;
			color:var(--aot-ink-faint); flex-shrink:0;
		}
		.ao-tracker-wrap .aot-pill-input{
			display:block; flex:1; min-width:140px; height:100%; position:relative;
		}
		.ao-tracker-wrap .aot-pill-input .frappe-control{
			margin:0 !important; padding:0 !important; width:100% !important; max-width:100% !important; height:100% !important; position:relative !important;
		}
		.ao-tracker-wrap .aot-pill-input .form-group{
			margin:0 !important; padding:0 !important; width:100% !important; height:100% !important; position:relative !important;
		}
		.ao-tracker-wrap .aot-pill-input .clearfix,
		.ao-tracker-wrap .aot-pill-input .control-label,
		.ao-tracker-wrap .aot-pill-input .help,
		.ao-tracker-wrap .aot-pill-input .help-box,
		.ao-tracker-wrap .aot-pill-input .tooltip-content{
			display:none !important;
		}
		.ao-tracker-wrap .aot-pill-input .control-input-wrapper{
			margin:0 !important; padding:0 !important; width:100% !important; height:100% !important; position:relative !important;
		}
		.ao-tracker-wrap .aot-pill-input .control-input{
			width:100% !important; height:100% !important; position:relative !important;
		}
		.ao-tracker-wrap .aot-pill-input .link-field{
			width:100% !important; height:100% !important; position:relative !important;
		}
		.ao-tracker-wrap .aot-pill-input .awesomplete{
			width:100% !important; height:100% !important; display:block !important; position:relative !important;
		}
		.ao-tracker-wrap .aot-pill-input .link-btn{
			display:none !important;
		}
		.ao-tracker-wrap .aot-pill-input .input-with-feedback,
		.ao-tracker-wrap .aot-pill-input input{
			border:none !important; background:transparent !important; box-shadow:none !important;
			padding:0 4px !important; height:34px !important; line-height:34px !important; font-size:12.5px !important; font-weight:600 !important;
			color:var(--aot-ink) !important; text-overflow:ellipsis !important; width:100% !important; margin:0 !important;
			display:block !important; outline:none !important;
		}
		.ao-tracker-wrap .aot-pill-input input::placeholder{
			color:var(--aot-ink-faint) !important; font-weight:500 !important;
		}
		.ao-tracker-wrap .aot-pill-input .awesomplete > ul{
			position:absolute !important;
			top:calc(100% + 4px) !important;
			left:0 !important;
			min-width:240px !important;
			max-width:380px !important;
			max-height:260px !important;
			overflow-y:auto !important;
			background:var(--aot-panel, #ffffff) !important;
			border:1px solid var(--aot-line, #e2e8f0) !important;
			border-radius:9px !important;
			box-shadow:0 10px 25px rgba(15,23,42,0.18) !important;
			z-index:1100 !important;
			padding:4px !important;
			margin:0 !important;
			list-style:none !important;
		}
		.ao-tracker-wrap .aot-pill-input .awesomplete > ul:empty{
			display:none !important;
		}
		.ao-tracker-wrap .aot-pill-input .awesomplete > ul > li{
			padding:8px 12px !important;
			font-size:12.5px !important;
			font-weight:600 !important;
			color:var(--aot-ink, #0f172a) !important;
			border-radius:6px !important;
			cursor:pointer !important;
			transition:background .1s ease !important;
			display:block !important;
			margin-bottom:2px !important;
			white-space:nowrap !important;
			overflow:hidden !important;
			text-overflow:ellipsis !important;
		}
		.ao-tracker-wrap .aot-pill-input .awesomplete > ul > li:hover,
		.ao-tracker-wrap .aot-pill-input .awesomplete > ul > li[aria-selected="true"]{
			background:var(--aot-accent-soft, #eff6ff) !important;
			color:var(--aot-accent, #2563eb) !important;
		}
		.ao-tracker-wrap .aot-pill-input .awesomplete > ul > li p{
			margin:0 !important;
			font-size:11px !important;
			color:var(--aot-ink-faint, #94a3b8) !important;
			font-weight:normal !important;
		}
		.ao-tracker-wrap[data-theme="dark"] .aot-pill-input .awesomplete > ul{
			background:#1e293b !important;
			border-color:#334155 !important;
			box-shadow:0 10px 25px rgba(0,0,0,0.4) !important;
		}
		.ao-tracker-wrap[data-theme="dark"] .aot-pill-input .awesomplete > ul > li{
			color:#f1f5f9 !important;
		}
		.ao-tracker-wrap[data-theme="dark"] .aot-pill-input .awesomplete > ul > li:hover,
		.ao-tracker-wrap[data-theme="dark"] .aot-pill-input .awesomplete > ul > li[aria-selected="true"]{
			background:#334155 !important;
			color:#60a5fa !important;
		}
		.ao-tracker-wrap .aot-field-company{
			min-width:240px; max-width:320px;
		}
		.ao-tracker-wrap .aot-field-so{
			min-width:200px; flex:1;
		}
		.ao-tracker-wrap .aot-field-customer{
			min-width:220px; flex:1.2;
		}
		.ao-tracker-wrap .aot-field-branch{
			min-width:180px; flex:0.8;
		}
		.ao-tracker-wrap .aot-field-batch{
			min-width:200px; flex:1;
		}

		.ao-tracker-wrap .aot-view-mode-toggle{
			display:inline-flex; align-items:center; background:var(--aot-bg);
			border:1px solid var(--aot-line); border-radius:8px; padding:2px;
		}
		.ao-tracker-wrap .aot-mode-btn{
			display:inline-flex; align-items:center; gap:6px; border:none;
			background:transparent; padding:5px 12px; font-size:12px; font-weight:700;
			color:var(--aot-ink-soft); border-radius:6px; cursor:pointer; transition:all .15s ease;
		}
		.ao-tracker-wrap .aot-mode-btn:hover{ color:var(--aot-accent); }
		.ao-tracker-wrap .aot-mode-btn.active{
			background:var(--aot-accent); color:#fff; box-shadow:0 2px 6px rgba(37,99,235,.28);
		}
		.ao-tracker-wrap .aot-batch-main{
			font-weight:700; color:var(--aot-ink); font-size:12.5px; word-break:break-all;
		}
		.ao-tracker-wrap .aot-nested-docs-wrap{
			display:inline-flex; align-items:center; gap:4px; flex-wrap:wrap;
		}
		.ao-tracker-wrap .aot-nested-doc-pill{
			display:inline-flex; align-items:center; gap:4px; padding:2px 7px;
			border-radius:4px; font-size:11px; font-weight:700; cursor:pointer;
			text-decoration:none; transition:filter .15s ease, transform .15s ease;
		}
		.ao-tracker-wrap .aot-nested-doc-pill:hover{ filter:brightness(0.92); transform:translateY(-1px); }
		.ao-tracker-wrap .aot-nested-mini-pill{
			display:inline-flex; align-items:center; gap:3px; padding:2px 6px;
			border-radius:999px; font-size:10.5px; font-weight:700; white-space:nowrap;
		}

		.ao-tracker-wrap .aot-period-dropdown{ position:relative; padding:0; cursor:pointer; }
		.ao-tracker-wrap .aot-period-btn{
			display:inline-flex; align-items:center; gap:7px;
			border:none; background:transparent; font-size:12.5px; font-weight:600;
			color:var(--aot-ink); cursor:pointer; padding:0 10px; height:100%;
		}
		.ao-tracker-wrap .aot-period-menu{
			display:none; position:absolute; top:calc(100% + 4px); left:0; z-index:100;
			background:var(--aot-panel); border:1px solid var(--aot-line); border-radius:9px;
			box-shadow:0 6px 18px rgba(15,23,42,0.12); min-width:210px; padding:4px;
		}
		.ao-tracker-wrap .aot-period-menu.open{ display:block; }
		.ao-tracker-wrap .aot-period-item{
			padding:7px 11px; font-size:12px; font-weight:600; color:var(--aot-ink-soft);
			border-radius:6px; cursor:pointer; transition:.12s;
		}
		.ao-tracker-wrap .aot-period-item:hover{ background:var(--aot-accent-soft); color:var(--aot-accent); }
		.ao-tracker-wrap .aot-period-item.active{ background:var(--aot-accent); color:#fff; }

		.ao-tracker-wrap .aot-daterange-box{
			display:inline-flex; align-items:center; gap:6px;
			background:var(--aot-bg); border:1px solid var(--aot-line); border-radius:8px;
			padding:0 10px; height:36px; box-sizing:border-box;
		}
		.ao-tracker-wrap .aot-daterange-box input[type="date"]{
			border:none; background:transparent; font-size:12px; font-weight:600;
			color:var(--aot-ink); outline:none; height:100%; padding:0; cursor:pointer;
		}
		.ao-tracker-wrap .aot-daterange-box input.aot-locked{ cursor:default; }
		.ao-tracker-wrap .aot-date-sep{ font-size:12px; color:var(--aot-ink-faint); font-weight:600; padding:0 2px; }

		.ao-tracker-wrap .aot-filter-actions{
			display:inline-flex; align-items:center; gap:8px;
		}
		.ao-tracker-wrap .aot-reset{
			height:36px; padding:0 14px; font-size:12.5px; font-weight:600; border-radius:8px;
			border:1px solid var(--aot-line); background:var(--aot-bg); color:var(--aot-ink-soft);
			cursor:pointer; transition:.15s; display:inline-flex; align-items:center;
		}
		.ao-tracker-wrap .aot-reset:hover{
			background:var(--aot-panel); color:var(--aot-ink); border-color:var(--aot-ink-faint);
		}
		.ao-tracker-wrap .aot-theme-toggle{
			width:36px; height:36px; border-radius:8px;
		}

		.ao-tracker-wrap .aot-section-head{display:flex; align-items:center; justify-content:space-between; margin-bottom:12px;}
		.ao-tracker-wrap .aot-section-title-wrap{display:flex; align-items:baseline; gap:10px;}
		.ao-tracker-wrap .aot-section-title{font-size:13px; font-weight:700; color:var(--aot-ink-faint); text-transform:uppercase; letter-spacing:.05em;}
		.ao-tracker-wrap .aot-result-count{font-size:12.5px; color:var(--aot-ink-faint);}
		.ao-tracker-wrap .aot-table-actions{display:flex; align-items:center; gap:8px;}
		.ao-tracker-wrap .aot-toggle-all-btn{
			display:inline-flex; align-items:center; gap:6px; padding:4px 10px; font-size:12px; font-weight:600;
			border-radius:6px; border:1px solid var(--aot-line); background:var(--aot-bg); color:var(--aot-ink-soft);
			cursor:pointer; transition:.15s;
		}
		.ao-tracker-wrap .aot-toggle-all-btn:hover{background:var(--aot-panel); color:var(--aot-accent); border-color:var(--aot-accent);}
		.ao-tracker-wrap .aot-toggle-all-icon{display:inline-block; transition:transform .2s ease; font-size:11px;}
		.ao-tracker-wrap .aot-toggle-all-icon.rotated{transform:rotate(90deg);}

		.ao-tracker-wrap .aot-table-scroll{
			background:var(--aot-panel); border:1px solid var(--aot-line); border-radius:var(--aot-radius);
			box-shadow:var(--aot-shadow); overflow:auto; max-height:calc(100vh - 230px); position:relative;
		}
		.ao-tracker-wrap table.aot-status-table{
			width:100%; border-collapse:separate; border-spacing:0; font-size:13px; min-width:2400px;
		}
		.ao-tracker-wrap .aot-status-table thead th{
			text-align:left; font-size:10.5px; font-weight:700; color:var(--aot-ink-soft); text-transform:uppercase;
			letter-spacing:.03em; padding:12px; border-bottom:1px solid var(--aot-line); white-space:nowrap;
			background:#F3F5FC; position:sticky; top:0; z-index:20;
		}
		.ao-tracker-wrap[data-theme="dark"] .aot-status-table thead th{ background:#181D2A; }
		.ao-tracker-wrap .aot-so-col{ min-width:160px; }
		.ao-tracker-wrap .aot-items-col{ width:90px; text-align:center; }
		.ao-tracker-wrap .aot-status-table tbody td{padding:12px; border-bottom:1px solid var(--aot-line-soft); vertical-align:middle;}
		.ao-tracker-wrap .aot-so-row{cursor:pointer; transition:background .15s;}
		.ao-tracker-wrap .aot-so-row:nth-child(4n-3){background:#FBFCFE;}
		.ao-tracker-wrap .aot-so-row:hover{background:var(--aot-accent-soft);}
		.ao-tracker-wrap .aot-so-row.expanded{background:#EFF6FF !important; border-left:3px solid var(--aot-accent);}
		.ao-tracker-wrap[data-theme="dark"] .aot-so-row.expanded{background:#131E33 !important; border-left:3px solid var(--aot-accent);}

		/* Sticky columns for Batch-wise mode (Checkbox + Batch No) */
		.ao-tracker-wrap .aot-status-table.aot-table-batch thead th:nth-child(1){
			position:sticky; left:0; z-index:35; background:#F3F5FC;
		}
		.ao-tracker-wrap .aot-status-table.aot-table-batch thead th:nth-child(2){
			position:sticky; left:36px; z-index:35; background:#F3F5FC;
			box-shadow:3px 0 6px rgba(0,0,0,0.06); border-right:1px solid var(--aot-line);
		}
		.ao-tracker-wrap .aot-status-table.aot-table-batch tbody td:nth-child(1){
			position:sticky; left:0; z-index:15; background:var(--aot-panel);
		}
		.ao-tracker-wrap .aot-status-table.aot-table-batch tbody td:nth-child(2){
			position:sticky; left:36px; z-index:15; background:var(--aot-panel);
			box-shadow:3px 0 6px rgba(0,0,0,0.06); border-right:1px solid var(--aot-line);
		}
		.ao-tracker-wrap .aot-status-table.aot-table-batch tbody tr:nth-child(even) td:nth-child(1),
		.ao-tracker-wrap .aot-status-table.aot-table-batch tbody tr:nth-child(even) td:nth-child(2){
			background:#FBFCFE;
		}
		.ao-tracker-wrap .aot-status-table.aot-table-batch tbody tr:hover td:nth-child(1),
		.ao-tracker-wrap .aot-status-table.aot-table-batch tbody tr:hover td:nth-child(2){
			background:var(--aot-accent-soft) !important;
		}

		/* Sticky columns for Sales Order-wise mode (Expand + Checkbox + Sales Order) */
		.ao-tracker-wrap .aot-status-table.aot-table-so thead th:nth-child(1){
			position:sticky; left:0; z-index:35; background:#F3F5FC;
		}
		.ao-tracker-wrap .aot-status-table.aot-table-so thead th:nth-child(2){
			position:sticky; left:34px; z-index:35; background:#F3F5FC;
		}
		.ao-tracker-wrap .aot-status-table.aot-table-so thead th:nth-child(3){
			position:sticky; left:70px; z-index:35; background:#F3F5FC;
			box-shadow:3px 0 6px rgba(0,0,0,0.06); border-right:1px solid var(--aot-line);
		}
		.ao-tracker-wrap .aot-status-table.aot-table-so tbody td:nth-child(1){
			position:sticky; left:0; z-index:15; background:var(--aot-panel);
		}
		.ao-tracker-wrap .aot-status-table.aot-table-so tbody td:nth-child(2){
			position:sticky; left:34px; z-index:15; background:var(--aot-panel);
		}
		.ao-tracker-wrap .aot-status-table.aot-table-so tbody td:nth-child(3){
			position:sticky; left:70px; z-index:15; background:var(--aot-panel);
			box-shadow:3px 0 6px rgba(0,0,0,0.06); border-right:1px solid var(--aot-line);
		}
		.ao-tracker-wrap .aot-status-table.aot-table-so tbody tr.aot-so-row:nth-child(4n-3) td:nth-child(1),
		.ao-tracker-wrap .aot-status-table.aot-table-so tbody tr.aot-so-row:nth-child(4n-3) td:nth-child(2),
		.ao-tracker-wrap .aot-status-table.aot-table-so tbody tr.aot-so-row:nth-child(4n-3) td:nth-child(3){
			background:#FBFCFE;
		}
		.ao-tracker-wrap .aot-status-table.aot-table-so tbody tr.aot-so-row:hover td:nth-child(1),
		.ao-tracker-wrap .aot-status-table.aot-table-so tbody tr.aot-so-row:hover td:nth-child(2),
		.ao-tracker-wrap .aot-status-table.aot-table-so tbody tr.aot-so-row:hover td:nth-child(3){
			background:var(--aot-accent-soft) !important;
		}
		.ao-tracker-wrap .aot-status-table.aot-table-so tbody tr.aot-so-row.expanded td:nth-child(1),
		.ao-tracker-wrap .aot-status-table.aot-table-so tbody tr.aot-so-row.expanded td:nth-child(2),
		.ao-tracker-wrap .aot-status-table.aot-table-so tbody tr.aot-so-row.expanded td:nth-child(3){
			background:#EFF6FF !important;
		}

		/* Dark mode sticky styling */
		.ao-tracker-wrap[data-theme="dark"] .aot-status-table.aot-table-batch thead th:nth-child(1),
		.ao-tracker-wrap[data-theme="dark"] .aot-status-table.aot-table-batch thead th:nth-child(2),
		.ao-tracker-wrap[data-theme="dark"] .aot-status-table.aot-table-so thead th:nth-child(1),
		.ao-tracker-wrap[data-theme="dark"] .aot-status-table.aot-table-so thead th:nth-child(2),
		.ao-tracker-wrap[data-theme="dark"] .aot-status-table.aot-table-so thead th:nth-child(3){
			background:#181D2A;
		}
		.ao-tracker-wrap[data-theme="dark"] .aot-status-table.aot-table-batch tbody td:nth-child(1),
		.ao-tracker-wrap[data-theme="dark"] .aot-status-table.aot-table-batch tbody td:nth-child(2),
		.ao-tracker-wrap[data-theme="dark"] .aot-status-table.aot-table-so tbody td:nth-child(1),
		.ao-tracker-wrap[data-theme="dark"] .aot-status-table.aot-table-so tbody td:nth-child(2),
		.ao-tracker-wrap[data-theme="dark"] .aot-status-table.aot-table-so tbody td:nth-child(3){
			background:var(--aot-panel);
		}
		.ao-tracker-wrap[data-theme="dark"] .aot-status-table.aot-table-so tbody tr.aot-so-row:nth-child(4n-3) td:nth-child(1),
		.ao-tracker-wrap[data-theme="dark"] .aot-status-table.aot-table-so tbody tr.aot-so-row:nth-child(4n-3) td:nth-child(2),
		.ao-tracker-wrap[data-theme="dark"] .aot-status-table.aot-table-so tbody tr.aot-so-row:nth-child(4n-3) td:nth-child(3),
		.ao-tracker-wrap[data-theme="dark"] .aot-status-table.aot-table-batch tbody tr:nth-child(even) td:nth-child(1),
		.ao-tracker-wrap[data-theme="dark"] .aot-status-table.aot-table-batch tbody tr:nth-child(even) td:nth-child(2){
			background:#151A26;
		}
		.ao-tracker-wrap[data-theme="dark"] .aot-status-table.aot-table-so tbody tr.aot-so-row.expanded td:nth-child(1),
		.ao-tracker-wrap[data-theme="dark"] .aot-status-table.aot-table-so tbody tr.aot-so-row.expanded td:nth-child(2),
		.ao-tracker-wrap[data-theme="dark"] .aot-status-table.aot-table-so tbody tr.aot-so-row.expanded td:nth-child(3){
			background:#131E33 !important;
		}

		.ao-tracker-wrap .aot-expand-btn{
			border:none; background:transparent; color:var(--aot-ink-faint); width:26px; height:26px;
			border-radius:6px; display:inline-flex; align-items:center; justify-content:center; cursor:pointer;
			transition:transform .2s ease, color .15s, background .15s; padding:0;
		}
		.ao-tracker-wrap .aot-expand-btn:hover{background:var(--aot-accent-soft); color:var(--aot-accent);}
		.ao-tracker-wrap .aot-so-row.expanded .aot-expand-btn{transform:rotate(90deg); color:var(--aot-accent); background:rgba(37,99,235,0.12);}

		.ao-tracker-wrap .aot-items-badge{
			display:inline-flex; align-items:center; gap:4px; padding:3px 9px; border-radius:12px;
			background:var(--aot-accent-soft); color:var(--aot-accent); font-weight:700; font-size:11.5px;
			cursor:pointer; border:1px solid rgba(37,99,235,0.18); transition:transform .1s, filter .15s;
		}
		.ao-tracker-wrap .aot-items-badge:hover{filter:brightness(0.95); transform:scale(1.03);}

		/* Collapsible child row */
		.ao-tracker-wrap .aot-child-row{display:none;}
		.ao-tracker-wrap .aot-child-row.expanded{display:table-row;}
		.ao-tracker-wrap .aot-child-cell{
			padding:6px 16px 14px 44px !important; background:var(--aot-bg) !important;
			border-bottom:2px solid var(--aot-line) !important;
		}
		.ao-tracker-wrap .aot-nested-wrapper{
			background:var(--aot-panel); border:1px solid var(--aot-line); border-radius:10px;
			padding:12px 16px; box-shadow:var(--aot-shadow);
		}
		.ao-tracker-wrap .aot-nested-header{
			display:flex; align-items:center; justify-content:space-between; padding-bottom:10px;
			margin-bottom:10px; border-bottom:1px solid var(--aot-line-soft); gap:12px; flex-wrap:wrap;
		}
		.ao-tracker-wrap .aot-nested-title{display:flex; align-items:center; gap:8px;}
		.ao-tracker-wrap .aot-nested-tag{
			font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.04em;
			background:var(--aot-gray-bg); color:var(--aot-gray-ink); padding:2px 7px; border-radius:6px;
		}
		.ao-tracker-wrap .aot-nested-so-ref{font-size:12.5px; font-weight:700; color:var(--aot-ink);}
		.ao-tracker-wrap .aot-nested-meta{
			display:inline-flex; align-items:center; gap:12px; font-size:12px; color:var(--aot-ink-faint);
			white-space:nowrap; flex-shrink:0;
		}
		.ao-tracker-wrap .aot-nested-meta .aot-meta-item{
			display:inline-flex; align-items:center; gap:4px; white-space:nowrap;
		}
		.ao-tracker-wrap .aot-nested-meta .aot-meta-dot{
			color:var(--aot-ink-faint); font-size:13px; line-height:1;
		}
		.ao-tracker-wrap .aot-nested-meta b{color:var(--aot-ink); margin-left:3px; font-weight:700;}
		.ao-tracker-wrap .aot-nested-table-wrap{overflow-x:auto;}
		.ao-tracker-wrap .aot-nested-table{width:100%; border-collapse:collapse; font-size:12.5px; min-width:880px;}
		.ao-tracker-wrap .aot-nested-item-col{max-width:240px; word-break:break-all; overflow-wrap:anywhere;}
		.ao-tracker-wrap .aot-nested-batch-col{max-width:140px; word-break:break-all; overflow-wrap:anywhere;}
		.ao-tracker-wrap .aot-nested-table th{
			background:var(--aot-bg); padding:7px 10px; font-size:10px; font-weight:700; text-transform:uppercase;
			color:var(--aot-ink-soft); letter-spacing:.03em; border-bottom:1px solid var(--aot-line); white-space:nowrap;
		}
		.ao-tracker-wrap .aot-nested-table td{padding:8px 10px; border-bottom:1px solid var(--aot-line-soft); vertical-align:middle;}
		.ao-tracker-wrap .aot-nested-table tr:last-child td{border-bottom:none;}

		.ao-tracker-wrap .aot-so-link{color:var(--aot-accent); font-weight:700; cursor:pointer; text-decoration:none; font-size:13px;}
		.ao-tracker-wrap .aot-so-link:hover{text-decoration:underline;}
		.ao-tracker-wrap .aot-branch-cell{font-size:12px; white-space:nowrap;}
		.ao-tracker-wrap .aot-branch-badge{display:inline-flex; align-items:center; padding:3px 9px; border-radius:999px; font-size:11px; font-weight:700; background:#EEF2FF; color:#4338CA; border:1px solid #C7D2FE;}
		.ao-tracker-wrap .aot-line-cell{font-size:12px; text-align:center;}
		.ao-tracker-wrap .aot-line-badge{display:inline-flex; align-items:center; justify-content:center; min-width:26px; padding:2px 6px; border-radius:6px; font-size:11px; font-weight:700; background:var(--aot-panel); border:1px solid var(--aot-line); color:var(--aot-ink-soft);}
		.ao-tracker-wrap .aot-item-cell{min-width:260px; max-width:320px; line-height:1.4; word-break:break-all; overflow-wrap:anywhere;}
		.ao-tracker-wrap .aot-item-code{font-weight:700; color:var(--aot-ink); font-size:12px; word-break:break-all; overflow-wrap:anywhere; display:inline-block; max-width:100%;}
		.ao-tracker-wrap .aot-item-name{font-size:11px; color:var(--aot-ink-faint); word-break:break-word; overflow-wrap:anywhere; margin-top:2px;}
		.ao-tracker-wrap .aot-batch-cell{min-width:120px; max-width:160px; word-break:break-all; overflow-wrap:anywhere; font-size:12px;}
		.ao-tracker-wrap .aot-batch-badge{display:inline-flex; align-items:center; padding:2px 7px; border-radius:4px; font-size:11px; font-weight:600; background:var(--aot-gray-bg); color:var(--aot-gray-ink); border:1px solid var(--aot-line); word-break:break-all;}
		.ao-tracker-wrap .aot-desc-cell{max-width:320px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:var(--aot-ink-soft); font-size:12px;}
		.ao-tracker-wrap .aot-num-cell{text-align:right; font-variant-numeric:tabular-nums; font-weight:600; font-size:12px; white-space:nowrap; min-width:85px;}
		.ao-tracker-wrap .aot-date-cell{font-size:12px; white-space:nowrap; color:var(--aot-ink-soft); min-width:105px;}
		.ao-tracker-wrap .aot-muted{color:var(--aot-ink-faint); font-weight:400;}
		.ao-tracker-wrap .aot-customer-cell{font-weight:500; color:var(--aot-ink-soft); max-width:180px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;}
		.ao-tracker-wrap .aot-pending-cell{color:var(--aot-ink-soft); font-size:12.5px; max-width:200px;}
		.ao-tracker-wrap .aot-pending-chip{display:inline-block; max-width:190px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; vertical-align:middle; background:var(--aot-amber-bg); color:var(--aot-amber-ink); padding:4px 10px; border-radius:999px; font-size:11.5px; font-weight:700;}
		.ao-tracker-wrap .aot-doc-link{font-weight:700; font-size:12px; cursor:pointer;}
		.ao-tracker-wrap .aot-doc-link:hover{text-decoration:underline;}
		.ao-tracker-wrap .aot-doc-multi{
			display:inline-flex; align-items:center; gap:5px; font-weight:700; font-size:12px;
			padding:5px 11px; border:1.5px solid; border-radius:999px; cursor:pointer;
			background:var(--aot-panel); transition:filter .15s ease, transform .15s ease;
		}
		.ao-tracker-wrap .aot-doc-multi:hover{ filter:brightness(0.95); transform:translateY(-1px); }
		.ao-tracker-wrap .aot-mini-pill{display:inline-flex; align-items:center; gap:5px; padding:4px 10px; border-radius:999px; font-size:11.5px; font-weight:700; white-space:nowrap;}
		.ao-tracker-wrap .aot-pri-closed{background:var(--aot-gray-bg); color:var(--aot-gray-ink);}
		.ao-tracker-wrap .aot-priority-col{ min-width:110px; }
		.ao-tracker-wrap .aot-pri-badge{display:inline-flex; align-items:center; padding:4px 12px; border-radius:999px; font-size:11.5px; font-weight:800; text-transform:uppercase; white-space:nowrap;}
		.ao-tracker-wrap .aot-pri-low{background:var(--aot-green-bg); color:var(--aot-green-ink);}
		.ao-tracker-wrap .aot-pri-medium{background:var(--aot-amber-bg); color:var(--aot-amber-ink);}
		.ao-tracker-wrap .aot-pri-high{background:var(--aot-orange-bg); color:var(--aot-orange-ink);}
		.ao-tracker-wrap .aot-pri-urgent{background:var(--aot-red-bg); color:var(--aot-red-ink);}
		.ao-tracker-wrap .aot-pri-overdue{background:var(--aot-overdue-bg); color:var(--aot-overdue-ink);}

		.ao-tracker-wrap .aot-view-btn{border:1px solid var(--aot-line); background:var(--aot-panel); color:var(--aot-ink-soft); width:28px; height:28px; border-radius:8px; cursor:pointer;}
		.ao-tracker-wrap .aot-view-btn:hover{background:var(--aot-accent-soft); border-color:var(--aot-accent); color:var(--aot-accent);}
		.ao-tracker-wrap .aot-empty-row{text-align:center; padding:40px 20px; color:var(--aot-ink-faint); font-size:13.5px;}

		.ao-tracker-wrap .aot-back-link{display:inline-flex; align-items:center; gap:6px; font-size:13px; font-weight:600; color:var(--aot-ink-soft); cursor:pointer; border:none; background:none; padding:0; margin-bottom:14px;}
		.ao-tracker-wrap .aot-back-link:hover{color:var(--aot-accent);}
		.ao-tracker-wrap .aot-detail-header{display:flex; align-items:center; justify-content:space-between; margin-bottom:18px; gap:16px; flex-wrap:wrap;}
		.ao-tracker-wrap .aot-detail-title-block h1{font-size:19px; margin:0 0 4px;}
		.ao-tracker-wrap .aot-detail-title-block .aot-d-sub{font-size:13px; color:var(--aot-ink-faint);}
		.ao-tracker-wrap .aot-d-status-pill{font-size:13px; padding:6px 14px;}
		.ao-tracker-wrap .aot-panel{background:var(--aot-panel); border:1px solid var(--aot-line); border-radius:var(--aot-radius); box-shadow:var(--aot-shadow); margin-bottom:18px; overflow:hidden;}
		.ao-tracker-wrap .aot-panel-head{padding:14px 16px; border-bottom:1px solid var(--aot-line-soft); display:flex; align-items:center; justify-content:space-between; cursor:pointer;}
		.ao-tracker-wrap .aot-panel.collapsed .aot-panel-head{border-bottom:none;}
		.ao-tracker-wrap .aot-panel.collapsed .aot-panel-body{display:none;}
		.ao-tracker-wrap .aot-caret{color:var(--aot-ink-faint); transition:transform .15s;}
		.ao-tracker-wrap .aot-panel.collapsed .aot-caret{transform:rotate(-90deg);}
		.ao-tracker-wrap .aot-panel-title{font-size:14px; font-weight:700;}
		.ao-tracker-wrap .aot-panel-desc{font-size:12px; color:var(--aot-ink-faint); margin-top:2px;}
		.ao-tracker-wrap .aot-panel-body{padding:16px;}
		.ao-tracker-wrap .aot-stat-grid{display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:14px;}
		.ao-tracker-wrap .aot-stat-card{background:#FBFBFD; border:1px solid var(--aot-line); border-radius:11px; padding:14px 15px;}
		.ao-tracker-wrap .aot-stat-card.aot-highlight{background:var(--aot-accent-soft); border-color:#C9D3F5;}
		.ao-tracker-wrap .aot-stat-label{font-size:10.5px; font-weight:700; color:var(--aot-ink-faint); text-transform:uppercase; margin-bottom:6px;}
		.ao-tracker-wrap .aot-stat-value{font-size:20px; font-weight:800;}
		.ao-tracker-wrap .aot-stat-value.aot-positive{color:var(--aot-green-ink);}
		.ao-tracker-wrap .aot-stat-value.aot-negative{color:var(--aot-red-ink);}
		.ao-tracker-wrap .aot-stat-sub{font-size:11px; color:var(--aot-ink-faint); margin-top:4px;}
		.ao-tracker-wrap .aot-table-x-scroll{overflow-x:auto;}
		.ao-tracker-wrap table.aot-flat-table{width:100%; border-collapse:collapse; font-size:13px; min-width:760px;}
		.ao-tracker-wrap .aot-flat-table thead th{text-align:left; font-size:10.5px; font-weight:700; color:var(--aot-ink-faint); text-transform:uppercase; padding:9px 10px; border-bottom:1px solid var(--aot-line);}
		.ao-tracker-wrap .aot-flat-table thead th.aot-num, .ao-tracker-wrap .aot-flat-table td.aot-num{text-align:right;}
		.ao-tracker-wrap .aot-flat-table tbody td{padding:9px 10px; border-bottom:1px solid var(--aot-line-soft);}
		.ao-tracker-wrap .aot-items-tbody tr.aot-group-start td{border-top:1px solid var(--aot-line-soft);}
		.ao-tracker-wrap .aot-type-badge{display:inline-flex; padding:3px 9px; border-radius:999px; font-size:10.5px; font-weight:800;}
		.ao-tracker-wrap .aot-type-fg{background:var(--aot-accent-soft); color:var(--aot-accent);}
		.ao-tracker-wrap .aot-type-rm{background:var(--aot-purple-bg); color:var(--aot-purple-ink);}
		.ao-tracker-wrap .aot-fg-name{font-weight:600; font-size:13px; word-break:break-word; overflow-wrap:anywhere;}
		.ao-tracker-wrap .aot-fg-code{font-size:11px; color:var(--aot-ink-faint); margin-top:1px; word-break:break-all; overflow-wrap:anywhere;}
		.ao-tracker-wrap .aot-doc-catalog-grid{display:grid; grid-template-columns:repeat(auto-fill,minmax(180px,1fr)); gap:14px;}
		.ao-tracker-wrap .aot-doc-card{position:relative; background:var(--aot-panel); border:1.5px solid var(--aot-line); border-radius:11px; padding:14px; cursor:pointer; transition:.15s;}
		.ao-tracker-wrap .aot-doc-card:hover{transform:translateY(-2px); box-shadow:var(--aot-shadow);}
		.ao-tracker-wrap .aot-doc-card.empty{cursor:default; border-style:dashed; background:#FBFBFD;}
		.ao-tracker-wrap .aot-doc-card.empty:hover{transform:none; box-shadow:none;}
		.ao-tracker-wrap .aot-doc-count-badge{position:absolute; top:-8px; right:-8px; min-width:20px; height:20px; padding:0 5px; border-radius:999px; font-size:10.5px; font-weight:800; display:flex; align-items:center; justify-content:center;}
		.ao-tracker-wrap .aot-count-zero{background:var(--aot-gray-bg); color:var(--aot-ink-faint);}
		.ao-tracker-wrap .aot-count-pos{background:var(--aot-red-bg); color:var(--aot-red-ink);}
		.ao-tracker-wrap .aot-doc-type-label{font-size:11px; font-weight:700; color:var(--aot-ink-faint); text-transform:uppercase; margin-bottom:4px;}
		.ao-tracker-wrap .aot-doc-code{font-weight:700; font-size:13px; margin-bottom:9px; word-break:break-word;}
		.ao-tracker-wrap .aot-doc-code.empty{color:var(--aot-ink-faint); font-weight:600;}
		.ao-tracker-wrap .aot-doc-multi-hint{font-size:11px; color:var(--aot-ink-faint); font-weight:600; margin-top:2px;}

		.ao-tracker-wrap .aot-modal-backdrop, .ao-tracker-wrap .aot-doclist-backdrop{
			display:none; position:fixed; inset:0; background:rgba(15,23,42,0.5); z-index:1050;
			align-items:center; justify-content:center; backdrop-filter:blur(2px);
		}
		.ao-tracker-wrap .aot-modal-backdrop.open, .ao-tracker-wrap .aot-doclist-backdrop.open{display:flex;}
		.ao-tracker-wrap .aot-modal, .ao-tracker-wrap .aot-doclist-modal{
			background:var(--aot-panel); border-radius:14px; box-shadow:0 20px 40px rgba(0,0,0,.2);
			width:92%; max-width:680px; max-height:85vh; display:flex; flex-direction:column; overflow:hidden;
			color:var(--aot-ink);
		}
		.ao-tracker-wrap .aot-doclist-modal{ max-width:620px; }
		.ao-tracker-wrap .aot-modal-head{padding:16px 20px; border-bottom:1px solid var(--aot-line-soft); display:flex; align-items:flex-start; justify-content:space-between;}
		.ao-tracker-wrap .aot-modal-eyebrow, .ao-tracker-wrap .aot-doclist-eyebrow{font-size:11px; font-weight:700; color:var(--aot-ink-faint); text-transform:uppercase; margin-bottom:2px;}
		.ao-tracker-wrap .aot-modal-title, .ao-tracker-wrap .aot-doclist-title{font-size:17px; font-weight:800; display:flex; align-items:center; gap:8px;}
		.ao-tracker-wrap .aot-modal-close{border:none; background:transparent; font-size:22px; line-height:1; cursor:pointer; color:var(--aot-ink-faint); padding:0 4px;}
		.ao-tracker-wrap .aot-modal-close:hover{color:var(--aot-ink);}
		.ao-tracker-wrap .aot-modal-stats{padding:12px 20px; background:var(--aot-panel-subtle); border-bottom:1px solid var(--aot-line-soft); display:grid; grid-template-columns:repeat(auto-fit,minmax(120px,1fr)); gap:12px;}
		.ao-tracker-wrap .aot-modal-stat-k{font-size:10.5px; font-weight:700; color:var(--aot-ink-faint); text-transform:uppercase;}
		.ao-tracker-wrap .aot-modal-stat-v{font-size:13px; font-weight:700; margin-top:2px;}
		.ao-tracker-wrap .aot-modal-items-label{font-size:11px; font-weight:700; color:var(--aot-ink-faint); text-transform:uppercase; padding:12px 20px 6px;}
		.ao-tracker-wrap .aot-modal-items{padding:8px 20px 16px; overflow-y:auto; flex:1; display:flex; flex-direction:column; gap:10px;}
		.ao-tracker-wrap .aot-modal-item-card{
			background:var(--aot-panel); border:1px solid var(--aot-line-soft); border-radius:10px;
			padding:12px 14px; transition:border-color .15s ease;
		}
		.ao-tracker-wrap .aot-modal-item-card:hover{ border-color:var(--aot-accent); }
		.ao-tracker-wrap .aot-modal-item-top{ display:flex; align-items:flex-start; justify-content:space-between; gap:12px; }
		.ao-tracker-wrap .aot-modal-item-left{ display:flex; align-items:center; flex-wrap:wrap; gap:8px; }
		.ao-tracker-wrap .aot-modal-item-idx{ font-size:11px; font-weight:700; color:var(--aot-ink-faint); background:var(--aot-panel-subtle); padding:2px 6px; border-radius:4px; }
		.ao-tracker-wrap .aot-modal-item-code{ font-weight:700; font-size:13px; color:var(--aot-accent); text-decoration:none; display:inline-flex; align-items:center; cursor:pointer; }
		.ao-tracker-wrap .aot-modal-item-code:hover{ text-decoration:underline; }
		.ao-tracker-wrap .aot-modal-item-title{ font-size:13px; font-weight:600; color:var(--aot-ink); }
		.ao-tracker-wrap .aot-modal-item-qty{ text-align:right; white-space:nowrap; }
		.ao-tracker-wrap .aot-modal-qty-num{ font-size:14px; font-weight:800; font-variant-numeric:tabular-nums; color:var(--aot-ink); }
		.ao-tracker-wrap .aot-modal-qty-uom{ font-size:11.5px; font-weight:600; color:var(--aot-ink-faint); margin-left:3px; }
		.ao-tracker-wrap .aot-modal-item-desc{ font-size:12px; color:var(--aot-ink-sub); margin-top:6px; line-height:1.4; white-space:pre-wrap; background:var(--aot-panel-subtle); padding:6px 10px; border-radius:6px; }
		.ao-tracker-wrap .aot-modal-item-bottom{ display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px; margin-top:8px; padding-top:8px; border-top:1px dashed var(--aot-line-soft); }
		.ao-tracker-wrap .aot-modal-item-meta{ display:flex; align-items:center; flex-wrap:wrap; gap:6px; }
		.ao-tracker-wrap .aot-modal-pill-badge{ font-size:11px; font-weight:600; color:var(--aot-ink-sub); background:var(--aot-panel-subtle); padding:2px 8px; border-radius:12px; border:1px solid var(--aot-line-soft); display:inline-flex; align-items:center; gap:4px; }
		.ao-tracker-wrap .aot-modal-pill-tag{ font-size:11px; font-weight:600; color:var(--aot-accent); background:var(--aot-accent-soft); padding:2px 8px; border-radius:12px; text-decoration:none; display:inline-flex; align-items:center; gap:4px; cursor:pointer; }
		.ao-tracker-wrap .aot-modal-pill-tag:hover{ text-decoration:underline; }
		.ao-tracker-wrap .aot-modal-item-price{ font-size:11.5px; color:var(--aot-ink-sub); font-variant-numeric:tabular-nums; }
		.ao-tracker-wrap a.aot-doc-link{ color:var(--aot-accent); text-decoration:none; font-weight:600; cursor:pointer; }
		.ao-tracker-wrap a.aot-doc-link:hover{ text-decoration:underline; }
		.ao-tracker-wrap .aot-modal-footer{padding:12px 20px; border-top:1px solid var(--aot-line-soft); display:flex; justify-content:flex-end; gap:8px;}

		.ao-tracker-wrap .aot-doclist-hint{ padding:10px 20px 4px; font-size:12px; color:var(--aot-ink-faint); }
		.ao-tracker-wrap .aot-doclist-rows{ padding:8px 20px 16px; overflow-y:auto; flex:1; }
		.ao-tracker-wrap .aot-doclist-row{
			display:flex; align-items:center; justify-content:space-between;
			padding:10px 12px; border:1px solid var(--aot-line-soft); border-radius:9px;
			margin-bottom:8px; cursor:pointer; transition:.12s ease;
			background:var(--aot-panel);
		}
		.ao-tracker-wrap .aot-doclist-row:hover{
			border-color:var(--aot-accent); background:var(--aot-accent-soft);
			transform:translateX(2px);
		}
		.ao-tracker-wrap .aot-doclist-name{ font-size:13.5px; font-weight:700; }
		.ao-tracker-wrap .aot-doclist-sub{ font-size:11.5px; color:var(--aot-ink-faint); margin-top:2px; }
		.ao-tracker-wrap .aot-doclist-row-right{ display:flex; align-items:center; gap:10px; }
		.ao-tracker-wrap .aot-doclist-arrow{ color:var(--aot-ink-faint); }

		/* Pagination Bar */
		.ao-tracker-wrap .aot-pagination-bar{
			display:flex; align-items:center; justify-content:space-between;
			padding:10px 14px; margin-top:12px;
			background:var(--aot-panel); border:1px solid var(--aot-line);
			border-radius:var(--aot-radius); box-shadow:var(--aot-shadow);
			gap:12px; flex-wrap:wrap; font-size:12.5px;
		}
		.ao-tracker-wrap .aot-page-info{
			font-size:12.5px; color:var(--aot-ink-soft); font-weight:600;
		}
		.ao-tracker-wrap .aot-page-controls{
			display:inline-flex; align-items:center; gap:8px;
		}
		.ao-tracker-wrap .aot-page-btn{
			display:inline-flex; align-items:center; gap:4px;
			padding:5px 11px; border-radius:6px; font-size:12px; font-weight:600;
			border:1px solid var(--aot-line); background:var(--aot-bg); color:var(--aot-ink-soft);
			cursor:pointer; transition:.15s ease;
		}
		.ao-tracker-wrap .aot-page-btn:hover:not(:disabled){
			background:var(--aot-panel); color:var(--aot-accent); border-color:var(--aot-accent);
		}
		.ao-tracker-wrap .aot-page-btn:disabled{
			opacity:0.45; cursor:not-allowed;
		}
		.ao-tracker-wrap .aot-page-status{
			display:inline-flex; align-items:center; gap:5px; font-weight:600; color:var(--aot-ink-soft);
		}
		.ao-tracker-wrap .aot-page-input{
			width:42px; height:28px; text-align:center; font-size:12px; font-weight:700;
			border:1px solid var(--aot-line); border-radius:5px; background:var(--aot-bg);
			color:var(--aot-ink); padding:0; outline:none;
		}
		.ao-tracker-wrap .aot-page-input:focus{
			border-color:var(--aot-accent); box-shadow:0 0 0 2px var(--aot-accent-soft);
		}
		.ao-tracker-wrap .aot-page-size-select{
			height:28px; padding:0 8px; font-size:12px; font-weight:600;
			border:1px solid var(--aot-line); border-radius:6px; background:var(--aot-bg);
			color:var(--aot-ink); cursor:pointer; outline:none;
		}

		/* Tab 2 Item Raw Materials Accordion */
		.ao-tracker-wrap .aot-item-child-row{ display:none; }
		.ao-tracker-wrap .aot-item-child-row.expanded{ display:table-row; }
		.ao-tracker-wrap .aot-item-row.expanded .aot-item-expand-btn .aot-chevron-svg{ transform:rotate(90deg); }
		`;
	}
}