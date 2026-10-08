// Financial Dashboard Page Controller - Frappe v16 + ERPNext v16
// Copyright (c) 2026, Steelstrong and contributors

frappe.pages['financial-dashboard'].on_page_load = function (wrapper) {
	wrapper.fd = new FinancialDashboard(wrapper);
};

frappe.pages['financial-dashboard'].on_page_show = function (wrapper) {
	document.title = __('Financial Dashboard');
	if (wrapper.fd && wrapper.fd.page && wrapper.fd.page.head) {
		wrapper.fd.page.head.hide();
	}
	if (wrapper.fd && wrapper.fd.initialized) {
		wrapper.fd.refresh(true);
	}
};

class FinancialDashboard {
	constructor(wrapper) {
		this.wrapper = $(wrapper);
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __('Financial Dashboard'),
			single_column: true,
		});
		document.title = __('Financial Dashboard');
		if (this.page.head) {
			this.page.head.hide();
		}

		// Single source of truth for filters
		this.company = frappe.defaults.get_user_default('Company') || frappe.defaults.get_default('Company');
		this.fiscal_year = null;
		this.branch = '';
		this.fy_start = null;
		this.fy_end = null;
		this.unit_dimension = 'Branch';

		this.salesGrain = 'quarters';
		this.purchasesGrain = 'quarters';
		this.isDarkMode = localStorage.getItem('fd_theme') === 'dark';
		this.salesStacked = true;
		this.purchasesStacked = true;
		this.item1Filter = 'all';

		this.charts = {};
		this.data = null;
		this.unitCache = {};
		this.availableFYs = [];
		this.availableBranches = [];
		this.initialized = false;

		this.init();
	}

	async init() {
		await this.load_vendor_assets();
		this.render_layout();
		await this.refresh();
		this.initialized = true;
	}

	async load_vendor_assets() {
		if (window.Chart) return;
		try {
			await frappe.require('/assets/generate_item/js/vendor/chart.umd.min.js');
		} catch (e) {
			console.warn('Vendored chart.umd.min.js load fallback:', e);
		}
	}

	get_active_filters(type = 'default') {
		const f = {
			company: this.company,
			fiscal_year: this.fiscal_year,
			fy_start: this.fy_start,
			fy_end: this.fy_end,
			unit_dimension: this.unit_dimension,
		};
		if (this.branch) {
			f.branch = this.branch;
		}

		const today = frappe.datetime.get_today();
		const reportDate = (f.fy_end && f.fy_end < today) ? f.fy_end : today;

		const baseFilters = { company: f.company };
		if (this.branch) baseFilters.branch = this.branch;

		switch (type) {
			case 'pnl':
			case 'revenue':
			case 'margin':
				return Object.assign({}, baseFilters, {
					filter_based_on: 'Fiscal Year',
					from_fiscal_year: f.fiscal_year,
					to_fiscal_year: f.fiscal_year,
					period_start_date: f.fy_start,
					period_end_date: f.fy_end,
					periodicity: 'Monthly',
				});
			case 'orders':
			case 'order_book':
				return Object.assign({}, baseFilters, {
					transaction_date: ['between', [f.fy_start, f.fy_end]],
					docstatus: 1,
				});
			case 'backlog':
			case 'pending_orders':
				return Object.assign({}, baseFilters, {
					transaction_date: ['between', [f.fy_start, f.fy_end]],
					status: ['in', ['To Deliver and Bill', 'To Deliver', 'To Bill', 'On Hold']],
					docstatus: 1,
				});
			case 'sales_invoices':
			case 'sales':
				return Object.assign({}, baseFilters, {
					posting_date: ['between', [f.fy_start, f.fy_end]],
					docstatus: 1,
				});
			case 'purchase_invoices':
			case 'purchases':
				return Object.assign({}, baseFilters, {
					posting_date: ['between', [f.fy_start, f.fy_end]],
					docstatus: 1,
				});
			case 'ar':
				return Object.assign({}, baseFilters, {
					report_date: reportDate,
					ageing_based_on: 'Due Date',
					range1: 30,
					range2: 60,
					range3: 90,
					range4: 120,
				});
			case 'ap':
				return Object.assign({}, baseFilters, {
					report_date: reportDate,
					ageing_based_on: 'Due Date',
					range1: 30,
					range2: 60,
					range3: 90,
					range4: 120,
				});
			default:
				return f;
		}
	}

	get_drilldown_filters(type = 'default') {
		return this.get_active_filters(type);
	}

	drilldown(routeType, routeTarget, filterType, extraFilters = {}) {
		const filters = Object.assign({}, this.get_active_filters(filterType), extraFilters);
		frappe.route_options = filters;
		frappe.set_route(routeType, routeTarget);
	}

	format_inr(num, compact = true) {
		const val = flt(num);
		if (isNaN(val)) return '₹0';
		if (!compact) {
			return '₹' + val.toLocaleString('en-IN', { maximumFractionDigits: 2 });
		}
		const absVal = Math.abs(val);
		const sign = val < 0 ? '-' : '';
		if (absVal >= 10000000) { // 1 Crore = 10,000,000
			return `${sign}₹${(absVal / 10000000).toFixed(2)} Cr`;
		} else if (absVal >= 100000) { // 1 Lakh = 100,000
			return `${sign}₹${(absVal / 100000).toFixed(2)} L`;
		} else if (absVal >= 1000) {
			return `${sign}₹${(absVal / 1000).toFixed(1)} K`;
		}
		return `${sign}₹${absVal.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
	}

	format_compact(num) {
		return this.format_inr(num, true);
	}

	render_layout() {
		const html = `
			<div class="fd-root ${this.isDarkMode ? 'wireframe-mode' : ''}" id="fd-root-container">
				<!-- Header Bar -->
				<header class="fd-header">
					<div class="fd-container fd-header-row">
						<!-- Brand Section -->
						<div class="fd-brand-section">
							<div class="fd-brand-icon-box">
								<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
								</svg>
							</div>
							<div>
								<div style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
									<h1 class="fd-brand-title">${__('Financial Dashboard')}</h1>
									<span class="fd-status-badge">
										<span class="fd-pulse-dot"></span> Live Sync
									</span>
									<span class="fd-currency-badge">₹ INR</span>
									<span class="fd-wf-metric-pill">BRANCH READY</span>
								</div>
								<p class="fd-brand-subtitle">${__('Executive financial performance, branch operations & working capital in INR')}</p>
							</div>
						</div>

						<!-- Controls Group -->
						<div class="fd-controls-group">
							<!-- FY Selector Dropdown (Current year selected by default) -->
							<div class="fd-select-control" id="fd-fy-control" title="${__('Select Fiscal Year')}">
								<span style="display: inline-flex; align-items: center; gap: 0.25rem; font-weight: 600; font-size: 0.72rem; color: var(--text-secondary);">
									<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width: 13px; height: 13px;">
										<rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
										<line x1="16" y1="2" x2="16" y2="6"></line>
										<line x1="8" y1="2" x2="8" y2="6"></line>
										<line x1="3" y1="10" x2="21" y2="10"></line>
									</svg>
									FY:
								</span>
								<select id="fd-fy-select" class="fd-form-select">
									<!-- Dynamically populated -->
								</select>
							</div>

							<!-- Branch Filter Dropdown -->
							<div class="fd-select-control" id="fd-branch-control" title="${__('Filter by Branch')}">
								<span style="display: inline-flex; align-items: center; gap: 0.25rem; font-weight: 600; font-size: 0.72rem; color: var(--text-secondary);">
									<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width: 13px; height: 13px;">
										<path stroke-linecap="round" stroke-linejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
									</svg>
									Branch:
								</span>
								<select id="fd-branch-select" class="fd-form-select">
									<option value="">${__('All Branches')}</option>
									<!-- Dynamically populated -->
								</select>
							</div>

							<!-- Day / Night Theme Toggle Button -->
							<button type="button" class="fd-theme-toggle" id="fd-btn-theme" title="${__('Toggle Day / Night mode')}" aria-label="${__('Toggle Day / Night mode')}">
								<span class="fd-theme-track">
									<span class="fd-theme-thumb">
										<span class="fd-theme-icon" aria-hidden="true">${this.isDarkMode ? '☾' : '☀'}</span>
									</span>
								</span>
								<span class="fd-theme-text" id="fd-theme-label">${this.isDarkMode ? __('Night Mode') : __('Day Mode')}</span>
							</button>

							<!-- Refresh Button -->
							<button type="button" class="fd-btn-action" id="fd-btn-refresh" title="${__('Refresh dataset')}" style="padding: 0.4rem 0.5rem;">
								<svg id="fd-refresh-icon" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
								</svg>
							</button>
						</div>
					</div>
				</header>

				<!-- Main Dashboard Body -->
				<main class="fd-main-body">

					<!-- KPI Metric Cards Grid -->
					<div class="fd-kpi-grid">
						<!-- Card 1: Revenue -->
						<div class="fd-kpi-card" id="fd-kpi-rev" title="${__('Click to open Profit & Loss Statement for this Fiscal Year')}">
							<div class="fd-kpi-header">
								<span class="fd-kpi-label">${__('Total Net Revenue (INR)')}</span>
								<div class="fd-kpi-icon-pill" style="background: #e0f2fe; color: #0284c7;">
									<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
								</div>
							</div>
							<div class="fd-kpi-value-row">
								<div class="fd-kpi-value" id="kpi-revenue">-</div>
								<span class="fd-kpi-trend" id="kpi-revenue-trend">
									<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M5 10l7-7m0 0l7 7m-7-7v18"/></svg>+0.0%
								</span>
							</div>
							<div class="fd-kpi-caption" id="kpi-revenue-cap">${__('YTD vs previous year')}</div>
							<span class="fd-wf-metric-pill" style="position: absolute; bottom: 6px; right: 8px;">[KPI:REV]</span>
						</div>

						<!-- Card 2: Operating Margin -->
						<div class="fd-kpi-card" id="fd-kpi-margin" title="${__('Click to open Profit & Loss Statement for this Fiscal Year')}">
							<div class="fd-kpi-header">
								<span class="fd-kpi-label">${__('Operating Margin')}</span>
								<div class="fd-kpi-icon-pill" style="background: #ede9fe; color: #7c3aed;">
									<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/></svg>
								</div>
							</div>
							<div class="fd-kpi-value-row">
								<div class="fd-kpi-value" id="kpi-margin">-</div>
								<span class="fd-kpi-trend" id="kpi-margin-trend">
									<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M5 10l7-7m0 0l7 7m-7-7v18"/></svg>+0.0 pts
								</span>
							</div>
							<div class="fd-kpi-caption" id="kpi-margin-cap">${__('Avg monthly margin')}</div>
							<span class="fd-wf-metric-pill" style="position: absolute; bottom: 6px; right: 8px;">[KPI:MARGIN]</span>
						</div>

						<!-- Card 3: Orders Booked -->
						<div class="fd-kpi-card" id="fd-kpi-orders" title="${__('Click to view Sales Orders for this Fiscal Year')}">
							<div class="fd-kpi-header">
								<span class="fd-kpi-label">${__('Orders Booked')}</span>
								<div class="fd-kpi-icon-pill" style="background: #dcfce7; color: #16a34a;">
									<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/></svg>
								</div>
							</div>
							<div class="fd-kpi-value-row">
								<div class="fd-kpi-value" id="kpi-orders">-</div>
								<span class="fd-kpi-trend" id="kpi-orders-trend">
									<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M5 10l7-7m0 0l7 7m-7-7v18"/></svg>+0.0%
								</span>
							</div>
							<div class="fd-kpi-caption" id="kpi-orders-cap">${__('Book-to-bill ratio: 1.0')}</div>
							<span class="fd-wf-metric-pill" style="position: absolute; bottom: 6px; right: 8px;">[KPI:ORDERS]</span>
						</div>

						<!-- Card 4: Pending Backlog -->
						<div class="fd-kpi-card" id="fd-kpi-pending" title="${__('Click to view Pending Orders for this Fiscal Year')}">
							<div class="fd-kpi-header">
								<span class="fd-kpi-label">${__('Pending Backlog')}</span>
								<div class="fd-kpi-icon-pill" style="background: #fef3c7; color: #d97706;">
									<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
								</div>
							</div>
							<div class="fd-kpi-value-row">
								<div class="fd-kpi-value" id="kpi-pending" style="color: #d97706;">-</div>
								<span style="font-size: 0.72rem; font-weight: 700; color: #b45309; background: #fef3c7; padding: 0.15rem 0.4rem; border-radius: 4px;" id="kpi-pending-value">-</span>
							</div>
							<div class="fd-kpi-caption" id="kpi-pending-cap">${__('SLA delivery timeline')}</div>
							<span class="fd-wf-metric-pill" style="position: absolute; bottom: 6px; right: 8px;">[KPI:BACKLOG]</span>
						</div>
					</div>

					<!-- ITEM 1: Revenue vs Operating Margin (Monthly View) -->
					<div class="fd-dash-card" id="fd-card-item1">
						<div class="fd-dash-card-header">
							<div>
								<div class="fd-card-title-wrap">
									<span class="fd-item-tag fd-tag-blue">ITEM 1</span>
									<h2 class="fd-card-title" style="cursor: pointer;" id="title-item1" title="${__('Click to open Profit & Loss Statement')}">${__('Revenue vs Operating Margin')}</h2>
									<span class="fd-wf-metric-pill">[Dual-Axis Combo | Monthly View in ₹ INR]</span>
								</div>
								<p class="fd-card-subtitle">${__('Monthly View • Revenue in ₹ Crores (Left Bar) vs Operating Margin % (Right Line)')}</p>
							</div>

							<div style="display: flex; align-items: center; gap: 0.75rem;">
								<div style="display: flex; align-items: center; gap: 0.75rem; font-size: 0.72rem; font-weight: 600;">
									<span style="display: inline-flex; align-items: center; gap: 0.35rem;">
										<span style="width: 10px; height: 10px; border-radius: 2px; background: #0284c7;"></span> ${__('Revenue (₹ Cr)')}
									</span>
									<span style="display: inline-flex; align-items: center; gap: 0.35rem;">
										<span style="width: 12px; height: 3px; background: #f59e0b; border-radius: 1px;"></span> ${__('Op. Margin (%)')}
									</span>
								</div>
								<select id="revMarginMetricFilter" style="font-size: 0.72rem; padding: 0.25rem 0.5rem; border-radius: 6px; border: 1px solid #cbd5e1; background: #f8fafc; color: #334155;">
									<option value="all">${__('Full Year (12 Months)')}</option>
									<option value="h1">${__('H1 (First 6 Months)')}</option>
									<option value="h2">${__('H2 (Last 6 Months)')}</option>
								</select>
							</div>
						</div>

						<div class="fd-dash-card-body">
							<div class="fd-chart-container-lg">
								<canvas id="revenueMarginChart" aria-label="${__('Revenue vs Operating Margin Chart')}"></canvas>
							</div>
							<!-- Summary Insights strip -->
							<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 0.75rem; margin-top: 1rem; padding-top: 0.75rem; border-top: 1px solid #f1f5f9; text-align: center; font-size: 0.72rem;">
								<div style="background: #f8fafc; padding: 0.5rem; border-radius: 8px;">
									<span style="color: #64748b;">${__('Peak Revenue')}</span>
									<p style="font-weight: 700; color: #0f172a; font-size: 0.85rem; margin-top: 2px;" id="rev-peak">-</p>
								</div>
								<div style="background: #f8fafc; padding: 0.5rem; border-radius: 8px;">
									<span style="color: #64748b;">${__('Best Margin')}</span>
									<p style="font-weight: 700; color: #10b981; font-size: 0.85rem; margin-top: 2px;" id="margin-peak">-</p>
								</div>
								<div style="background: #f8fafc; padding: 0.5rem; border-radius: 8px;">
									<span style="color: #64748b;">${__('Avg Monthly Run-rate')}</span>
									<p style="font-weight: 700; color: #0f172a; font-size: 0.85rem; margin-top: 2px;" id="rev-run-rate">-</p>
								</div>
								<div style="background: #f8fafc; padding: 0.5rem; border-radius: 8px;">
									<span style="color: #64748b;">${__('Margin Variance')}</span>
									<p style="font-weight: 700; color: #0f172a; font-size: 0.85rem; margin-top: 2px;" id="margin-spread">-</p>
								</div>
							</div>
						</div>
					</div>

					<!-- ITEM 2 & ITEM 3: Sales & Purchases from Each Unit (Branch Wise) -->
					<div class="fd-two-col-grid">

						<!-- Item 2: Sales from Each Unit (Branch Wise Sales) -->
						<div class="fd-dash-card" id="fd-card-item2">
							<div class="fd-dash-card-header">
								<div>
									<div class="fd-card-title-wrap">
										<span class="fd-item-tag fd-tag-green">ITEM 2</span>
										<h2 class="fd-card-title" style="cursor: pointer;" id="title-item2" title="${__('Click to view Sales Invoices')}">${__('Sales from Each Unit (Branch Wise Sales)')}</h2>
									</div>
									<p class="fd-card-subtitle">${__('Branch Wise Sales Breakdown • Years / Year-Quarters / Year-Months in ₹ INR')}</p>
								</div>

								<!-- Grain Switcher: Years / Year-Quarters / Year-Months -->
								<div class="fd-btn-toggle-group" id="btn-sales-grains">
									<button type="button" data-grain="years" id="btn-sales-years">${__('Years')}</button>
									<button type="button" data-grain="quarters" id="btn-sales-quarters" class="active">${__('Year-Quarters')}</button>
									<button type="button" data-grain="months" id="btn-sales-months">${__('Year-Months')}</button>
								</div>
							</div>

							<div class="fd-dash-card-body">
								<div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem; font-size: 0.72rem;">
									<span style="color: #64748b;">${__('Resolution')}: <strong id="salesGrainLabel" style="color: #0f172a;">${__('Year-Quarters (Q1 - Q4)')}</strong></span>
									<div class="fd-btn-toggle-group" id="btn-sales-layout-toggle" style="font-size: 0.7rem;">
										<button type="button" data-layout="stacked" class="active">${__('Stacked')}</button>
										<button type="button" data-layout="grouped">${__('Grouped')}</button>
									</div>
								</div>
								<div class="fd-chart-container-md">
									<canvas id="salesChart" aria-label="${__('Branch Wise Sales Chart')}"></canvas>
								</div>
								<div style="margin-top: 0.75rem; padding: 0.4rem 0.65rem; background: #f8fafc; border-radius: 6px; display: flex; justify-content: space-between; font-size: 0.7rem; cursor: pointer;" id="strip-sales-footer" title="${__('Click to view Sales Invoices')}">
									<span style="color: #64748b;">${__('Top Branch')}: <strong id="salesTopUnit">-</strong></span>
									<span style="font-weight: 700; color: #10b981;" id="salesTopShare">-</span>
								</div>
							</div>
						</div>

						<!-- Item 3: Purchases from Each Unit (Branch Wise Purchase) -->
						<div class="fd-dash-card" id="fd-card-item3">
							<div class="fd-dash-card-header">
								<div>
									<div class="fd-card-title-wrap">
										<span class="fd-item-tag fd-tag-amber">ITEM 3</span>
										<h2 class="fd-card-title" style="cursor: pointer;" id="title-item3" title="${__('Click to view Purchase Invoices')}">${__('Purchases from Each Unit (Branch Wise Purchase)')}</h2>
									</div>
									<p class="fd-card-subtitle">${__('Branch Wise Purchase Breakdown • Years / Year-Quarters / Year-Months in ₹ INR')}</p>
								</div>

								<!-- Grain Switcher: Years / Year-Quarters / Year-Months -->
								<div class="fd-btn-toggle-group" id="btn-purchases-grains">
									<button type="button" data-grain="years" id="btn-purchases-years">${__('Years')}</button>
									<button type="button" data-grain="quarters" id="btn-purchases-quarters" class="active">${__('Year-Quarters')}</button>
									<button type="button" data-grain="months" id="btn-purchases-months">${__('Year-Months')}</button>
								</div>
							</div>

							<div class="fd-dash-card-body">
								<div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem; font-size: 0.72rem;">
									<span style="color: #64748b;">${__('Resolution')}: <strong id="purchasesGrainLabel" style="color: #0f172a;">${__('Year-Quarters (Q1 - Q4)')}</strong></span>
									<div class="fd-btn-toggle-group" id="btn-purchases-layout-toggle" style="font-size: 0.7rem;">
										<button type="button" data-layout="stacked" class="active">${__('Stacked')}</button>
										<button type="button" data-layout="grouped">${__('Grouped')}</button>
									</div>
								</div>
								<div class="fd-chart-container-md">
									<canvas id="purchasesChart" aria-label="${__('Branch Wise Purchase Chart')}"></canvas>
								</div>
								<div style="margin-top: 0.75rem; padding: 0.4rem 0.65rem; background: #f8fafc; border-radius: 6px; display: flex; justify-content: space-between; font-size: 0.7rem; cursor: pointer;" id="strip-purchases-footer" title="${__('Click to view Purchase Invoices')}">
									<span style="color: #64748b;">${__('Major Branch Outflow')}: <strong id="purchasesTopUnit">-</strong></span>
									<span style="font-weight: 700; color: #f43f5e;" id="purchasesTopCost">-</span>
								</div>
							</div>
						</div>

					</div>

					<!-- ITEM 4: No. of orders booked (Monthly View) -->
					<div class="fd-dash-card" id="fd-card-item4">
						<div class="fd-dash-card-header">
							<div>
								<div class="fd-card-title-wrap">
									<span class="fd-item-tag fd-tag-purple">ITEM 4</span>
									<h2 class="fd-card-title" style="cursor: pointer;" id="title-item4" title="${__('Click to view Sales Orders')}">${__('No. of Orders Booked')}</h2>
								</div>
								<p class="fd-card-subtitle">${__('Monthly View • Booked volume and fulfillment run-rate')}</p>
							</div>

							<div style="display: flex; align-items: center; gap: 0.75rem; font-size: 0.72rem; font-weight: 600;">
								<span style="display: inline-flex; align-items: center; gap: 0.35rem;">
									<span style="width: 10px; height: 10px; border-radius: 2px; background: #8b5cf6;"></span> ${__('Orders Booked')}
								</span>
							</div>
						</div>

						<div class="fd-dash-card-body">
							<div class="fd-chart-container-md">
								<canvas id="ordersBookedChart" aria-label="${__('No. of Orders Booked Chart')}"></canvas>
							</div>
							<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.5rem; text-align: center; margin-top: 0.75rem; border-top: 1px solid #f1f5f9; padding-top: 0.75rem; font-size: 0.72rem; cursor: pointer;" id="strip-orders-footer" title="${__('Click to view Sales Orders')}">
								<div>
									<span style="color: #64748b;">${__('Total Booked')}</span>
									<p style="font-weight: 700; color: #0f172a; font-size: 0.85rem;" id="orders-total-booked">-</p>
								</div>
								<div>
									<span style="color: #64748b;">${__('Total Value')}</span>
									<p style="font-weight: 700; color: #7c3aed; font-size: 0.85rem;" id="orders-total-value">-</p>
								</div>
								<div>
									<span style="color: #64748b;">${__('Monthly Mean')}</span>
									<p style="font-weight: 700; color: #0f172a; font-size: 0.85rem;" id="orders-monthly-mean">-</p>
								</div>
							</div>
						</div>
					</div>

					<!-- ITEM 6: Accounts Receivable Ageing -->
					<div class="fd-dash-card" id="fd-card-item6" style="margin-bottom: 1.25rem;">
						<div class="fd-dash-card-header">
							<div>
								<div class="fd-card-title-wrap">
									<span class="fd-item-tag fd-tag-teal">ITEM 6</span>
									<h2 class="fd-card-title" style="cursor: pointer;" id="title-item6" title="${__('Click to open Accounts Receivable report')}">${__('Accounts Receivable (AR) Ageing')}</h2>
								</div>
								<p class="fd-card-subtitle" id="arSubtitle">${__('Total Receivables: - • DSO: -')}</p>
							</div>
							<span style="font-size: 0.72rem; font-weight: 600; color: #0f766e; background: #ccfbf1; padding: 0.2rem 0.5rem; border-radius: 4px; cursor: pointer;" id="arCurrentBadge" title="${__('Click to open Accounts Receivable report')}">-</span>
						</div>

						<div class="fd-dash-card-body">
							<div class="fd-chart-container-md" style="cursor: pointer;" id="chart-container-ar" title="${__('Click to open Accounts Receivable report')}">
								<canvas id="arAgeingChart" aria-label="${__('Accounts Receivable Ageing Bar Chart')}"></canvas>
							</div>
							<div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.5rem; text-align: center; margin-top: 0.75rem; border-top: 1px solid #f1f5f9; padding-top: 0.75rem; font-size: 0.72rem; cursor: pointer;" id="strip-ar-footer" title="${__('Click to open Accounts Receivable report')}">
								<div>
									<span style="color: #64748b;">${__('Total Receivables')}</span>
									<p style="font-weight: 700; color: #0f172a; font-size: 0.85rem;" id="ar-footer-total">-</p>
								</div>
								<div>
									<span style="color: #64748b;">${__('DSO')}</span>
									<p style="font-weight: 700; color: #0284c7; font-size: 0.85rem;" id="ar-footer-dso">-</p>
								</div>
								<div>
									<span style="color: #64748b;">${__('Current (< 30d)')}</span>
									<p style="font-weight: 700; color: #10b981; font-size: 0.85rem;" id="ar-footer-current">-</p>
								</div>
								<div>
									<span style="color: #64748b;">${__('Overdue (> 90d)')}</span>
									<p style="font-weight: 700; color: #ef4444; font-size: 0.85rem;" id="ar-footer-overdue">-</p>
								</div>
							</div>
						</div>
					</div>

					<!-- ITEM 7: Accounts Payable Ageing -->
					<div class="fd-dash-card" id="fd-card-item7" style="margin-bottom: 1.25rem;">
						<div class="fd-dash-card-header">
							<div>
								<div class="fd-card-title-wrap">
									<span class="fd-item-tag fd-tag-purple">ITEM 7</span>
									<h2 class="fd-card-title" style="cursor: pointer;" id="title-item7" title="${__('Click to open Accounts Payable report')}">${__('Accounts Payable (AP) Ageing')}</h2>
								</div>
								<p class="fd-card-subtitle" id="apSubtitle">${__('Total Payables: - • DPO: -')}</p>
							</div>
							<span style="font-size: 0.72rem; font-weight: 600; color: #6d28d9; background: #ede9fe; padding: 0.2rem 0.5rem; border-radius: 4px; cursor: pointer;" id="apDueBadge" title="${__('Click to open Accounts Payable report')}">-</span>
						</div>

						<div class="fd-dash-card-body">
							<div class="fd-chart-container-md" style="cursor: pointer;" id="chart-container-ap" title="${__('Click to open Accounts Payable report')}">
								<canvas id="apAgeingChart" aria-label="${__('Accounts Payable Ageing Bar Chart')}"></canvas>
							</div>
							<div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.5rem; text-align: center; margin-top: 0.75rem; border-top: 1px solid #f1f5f9; padding-top: 0.75rem; font-size: 0.72rem; cursor: pointer;" id="strip-ap-footer" title="${__('Click to open Accounts Payable report')}">
								<div>
									<span style="color: #64748b;">${__('Total Payables')}</span>
									<p style="font-weight: 700; color: #0f172a; font-size: 0.85rem;" id="ap-footer-total">-</p>
								</div>
								<div>
									<span style="color: #64748b;">${__('DPO')}</span>
									<p style="font-weight: 700; color: #6d28d9; font-size: 0.85rem;" id="ap-footer-dpo">-</p>
								</div>
								<div>
									<span style="color: #64748b;">${__('Current (< 30d)')}</span>
									<p style="font-weight: 700; color: #10b981; font-size: 0.85rem;" id="ap-footer-current">-</p>
								</div>
								<div>
									<span style="color: #64748b;">${__('Critical (> 90d)')}</span>
									<p style="font-weight: 700; color: #ef4444; font-size: 0.85rem;" id="ap-footer-critical">-</p>
								</div>
							</div>
						</div>
					</div>

				</main>

				<!-- Toast Notification -->
				<div id="dashToast" class="fd-dash-toast">
					<svg fill="none" stroke="#34d399" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>
					<span id="toastMessage">${__('State updated successfully')}</span>
				</div>
			</div>
		`;

		this.page.main.empty().append(html);
		this.bind_events();
	}

	showToast(msg) {
		const toast = this.wrapper.find('#dashToast');
		this.wrapper.find('#toastMessage').text(msg);
		toast.addClass('show');
		setTimeout(() => toast.removeClass('show'), 2600);
	}

	toggleThemeMode() {
		this.isDarkMode = !this.isDarkMode;
		this.wrapper.find('#fd-root-container').toggleClass('wireframe-mode', this.isDarkMode);
		this.wrapper.find('.fd-theme-icon').text(this.isDarkMode ? '☾' : '☀');
		this.wrapper.find('#fd-theme-label').text(this.isDarkMode ? __('Night Mode') : __('Day Mode'));
		localStorage.setItem('fd_theme', this.isDarkMode ? 'dark' : 'light');
		this.showToast(this.isDarkMode ? __('Night mode activated') : __('Day mode activated'));
	}

	bind_events() {
		const me = this;

		// Day / Night Theme Button
		this.wrapper.find('#fd-btn-theme').on('click', () => me.toggleThemeMode());

		// Refresh Button Action
		this.wrapper.find('#fd-btn-refresh').on('click', () => {
			const icon = me.wrapper.find('#fd-refresh-icon');
			icon.css({ transition: 'transform 0.5s ease', transform: 'rotate(360deg)' });
			setTimeout(() => icon.css({ transform: 'rotate(0deg)' }), 500);
			me.unitCache = {};
			me.refresh();
			me.showToast(__('Data re-synchronized with ERP ledger'));
		});

		// FY Selector Dropdown Change
		this.wrapper.find('#fd-fy-select').on('change', function () {
			const selectedFY = $(this).val();
			if (selectedFY && selectedFY !== me.fiscal_year) {
				me.fiscal_year = selectedFY;
				const fyObj = (me.availableFYs || []).find(f => f.name === selectedFY);
				if (fyObj) {
					me.fy_start = fyObj.year_start_date;
					me.fy_end = fyObj.year_end_date;
				}
				me.unitCache = {};
				me.refresh();
				me.showToast(__('Fiscal Year switched to {0}', [selectedFY]));
			}
		});

		// Branch Filter Dropdown Change
		this.wrapper.find('#fd-branch-select').on('change', function () {
			me.branch = $(this).val() || '';
			me.unitCache = {};
			me.refresh();
			me.showToast(me.branch ? __('Filtered by Branch: {0}', [me.branch]) : __('Showing all branches'));
		});

		// Item 1 Filter (Full Year / H1 / H2)
		this.wrapper.find('#revMarginMetricFilter').on('change', function () {
			me.item1Filter = $(this).val();
			me.render_item1_chart();
			me.showToast(__('Updated Revenue View to {0}', [me.item1Filter.toUpperCase()]));
		});

		// Sales Grain Switcher
		this.wrapper.find('#btn-sales-grains button').on('click', function () {
			const grain = $(this).data('grain');
			me.wrapper.find('#btn-sales-grains button').removeClass('active');
			$(this).addClass('active');
			me.salesGrain = grain;
			me.wrapper.find('#salesGrainLabel').text(
				grain === 'years' ? __('Years') : (grain === 'quarters' ? __('Year-Quarters (Q1 - Q4)') : __('Year-Months (Jan - Dec)'))
			);
			me.load_unit_series('sales', grain);
			me.showToast(__('Sales view set to {0}', [grain.toUpperCase()]));
		});

		// Purchases Grain Switcher
		this.wrapper.find('#btn-purchases-grains button').on('click', function () {
			const grain = $(this).data('grain');
			me.wrapper.find('#btn-purchases-grains button').removeClass('active');
			$(this).addClass('active');
			me.purchasesGrain = grain;
			me.wrapper.find('#purchasesGrainLabel').text(
				grain === 'years' ? __('Years') : (grain === 'quarters' ? __('Year-Quarters (Q1 - Q4)') : __('Year-Months (Jan - Dec)'))
			);
			me.load_unit_series('purchases', grain);
			me.showToast(__('Purchases view set to {0}', [grain.toUpperCase()]));
		});

		// Sales Layout Switcher (Stacked / Grouped)
		this.wrapper.find('#btn-sales-layout-toggle button').on('click', function () {
			const layout = $(this).data('layout');
			me.set_sales_layout(layout === 'stacked');
		});

		// Purchases Layout Switcher (Stacked / Grouped)
		this.wrapper.find('#btn-purchases-layout-toggle button').on('click', function () {
			const layout = $(this).data('layout');
			me.set_purchases_layout(layout === 'stacked');
		});

		// =========================================================================
		// Click-through Drilldown Handlers with Full Fiscal Year Filter Context
		// =========================================================================

		// 1. Total Net Revenue & Operating Margin KPIs
		this.wrapper.find('#fd-kpi-rev, #title-item1').on('click', () => {
			me.drilldown('query-report', 'Profit and Loss Statement', 'revenue');
		});

		this.wrapper.find('#fd-kpi-margin').on('click', () => {
			me.drilldown('query-report', 'Profit and Loss Statement', 'margin');
		});

		// 2. Orders Booked KPI & Item 4 Title / Footer
		this.wrapper.find('#fd-kpi-orders, #title-item4, #strip-orders-footer').on('click', () => {
			me.drilldown('List', 'Sales Order', 'orders');
		});

		// 3. Pending Backlog KPI Card
		this.wrapper.find('#fd-kpi-pending').on('click', () => {
			me.drilldown('List', 'Sales Order', 'backlog');
		});

		// 4. Item 2: Sales from Each Unit
		this.wrapper.find('#title-item2, #strip-sales-footer').on('click', () => {
			me.drilldown('List', 'Sales Invoice', 'sales');
		});

		// 5. Item 3: Purchases from Each Unit
		this.wrapper.find('#title-item3, #strip-purchases-footer').on('click', () => {
			me.drilldown('List', 'Purchase Invoice', 'purchases');
		});

		// 6. Item 6: Accounts Receivable Ageing
		this.wrapper.find('#title-item6, #arCurrentBadge, #chart-container-ar, #strip-ar-footer').on('click', () => {
			me.drilldown('query-report', 'Accounts Receivable', 'ar');
		});

		// 7. Item 7: Accounts Payable Ageing
		this.wrapper.find('#title-item7, #apDueBadge, #chart-container-ap, #strip-ap-footer').on('click', () => {
			me.drilldown('query-report', 'Accounts Payable', 'ap');
		});
	}

	populate_filter_dropdowns() {
		const me = this;

		// 1. Populate FY Select Dropdown
		const fySelect = this.wrapper.find('#fd-fy-select').empty();
		if (this.availableFYs && this.availableFYs.length > 0) {
			this.availableFYs.forEach(fy => {
				const isSelected = fy.name === me.fiscal_year ? 'selected' : '';
				fySelect.append(`<option value="${fy.name}" ${isSelected}>${fy.name}</option>`);
			});
		} else if (this.fiscal_year) {
			fySelect.append(`<option value="${this.fiscal_year}" selected>${this.fiscal_year}</option>`);
		}

		// 2. Populate Branch Select Dropdown
		const branchSelect = this.wrapper.find('#fd-branch-select');
		const currentVal = this.branch || '';
		branchSelect.empty().append(`<option value="" ${currentVal === '' ? 'selected' : ''}>${__('All Branches')}</option>`);
		
		if (this.availableBranches && this.availableBranches.length > 0) {
			this.availableBranches.forEach(b => {
				const isSelected = b === currentVal ? 'selected' : '';
				branchSelect.append(`<option value="${b}" ${isSelected}>${b}</option>`);
			});
		}
	}

	async refresh(silent = false) {
		try {
			if (!silent) frappe.show_progress(__('Loading Financial Dashboard'), 40, 100);
			const r = await frappe.call({
				method: 'generate_item.generate_item.page.financial_dashboard.financial_dashboard.get_overview',
				args: {
					company: this.company,
					fiscal_year: this.fiscal_year,
					branch: this.branch || null,
					unit_dimension: this.unit_dimension,
				},
			});

			if (!silent) frappe.show_progress(__('Loading Financial Dashboard'), 80, 100);

			if (r && r.message) {
				this.data = r.message;
				this.update_meta();
				this.render_kpis();
				this.render_item1_chart();
				this.render_orders_chart();
				this.render_ar_ageing();
				this.render_ap_ageing();

				// Load multi-unit series for Items 2 & 3 with the selected fiscal year and branch
				await this.load_unit_series('sales', this.salesGrain);
				await this.load_unit_series('purchases', this.purchasesGrain);
			}
		} catch (err) {
			console.error('Dashboard refresh failed:', err);
		} finally {
			if (!silent) frappe.hide_progress();
		}
	}

	update_meta() {
		const meta = this.data.meta;
		this.currency = 'INR';
		this.fiscal_year = meta.fiscal_year;
		this.fy_start = meta.fy_start;
		this.fy_end = meta.fy_end;

		if (meta.all_fiscal_years && meta.all_fiscal_years.length > 0) {
			this.availableFYs = meta.all_fiscal_years;
		}

		if (meta.all_branches && meta.all_branches.length > 0) {
			this.availableBranches = meta.all_branches;
		}

		// Dynamically render dropdowns
		this.populate_filter_dropdowns();
	}

	render_kpis() {
		const kpi = this.data.kpis;

		// Card 1: Revenue
		this.wrapper.find('#kpi-revenue').text(this.format_inr(kpi.net_revenue));
		const revTrend = this.wrapper.find('#kpi-revenue-trend');
		revTrend.html(`
			<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="${kpi.revenue_delta >= 0 ? 'M5 10l7-7m0 0l7 7m-7-7v18' : 'M19 14l-7 7m0 0l-7-7m7 7V3'}"/></svg>
			${kpi.revenue_delta >= 0 ? '+' : ''}${kpi.revenue_delta}%
		`);
		revTrend.toggleClass('negative', kpi.revenue_delta < 0);
		this.wrapper.find('#kpi-revenue-cap').text(__('YTD vs previous year'));

		// Card 2: Operating Margin
		this.wrapper.find('#kpi-margin').text(`${kpi.operating_margin}%`);
		const marginTrend = this.wrapper.find('#kpi-margin-trend');
		marginTrend.html(`
			<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="${kpi.margin_delta >= 0 ? 'M5 10l7-7m0 0l7 7m-7-7v18' : 'M19 14l-7 7m0 0l-7-7m7 7V3'}"/></svg>
			${kpi.margin_delta >= 0 ? '+' : ''}${kpi.margin_delta} pts
		`);
		marginTrend.toggleClass('negative', kpi.margin_delta < 0);
		this.wrapper.find('#kpi-margin-cap').text(__('Avg monthly margin'));

		// Card 3: Orders Booked
		this.wrapper.find('#kpi-orders').text(kpi.orders_booked_count.toLocaleString('en-IN'));
		const ordersTrend = this.wrapper.find('#kpi-orders-trend');
		ordersTrend.html(`
			<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="${kpi.orders_delta >= 0 ? 'M5 10l7-7m0 0l7 7m-7-7v18' : 'M19 14l-7 7m0 0l-7-7m7 7V3'}"/></svg>
			${kpi.orders_delta >= 0 ? '+' : ''}${kpi.orders_delta}%
		`);
		ordersTrend.toggleClass('negative', kpi.orders_delta < 0);
		this.wrapper.find('#kpi-orders-cap').text(`Book-to-bill ratio: ${kpi.book_to_bill} (${this.format_inr(kpi.orders_booked_value)})`);

		// Card 4: Pending Backlog
		this.wrapper.find('#kpi-pending').text(`${kpi.pending_backlog_count} Units`);
		this.wrapper.find('#kpi-pending-value').text(`${this.format_inr(kpi.pending_backlog_value)} Value`);
		this.wrapper.find('#kpi-pending-cap').text(`${kpi.sla_percentage}% on SLA delivery timeline`);
	}

	render_item1_chart() {
		const rm = this.data.revenue_margin;
		let labels = rm.labels || [];
		let rev = rm.revenue_series || [];
		let margin = rm.margin_series || [];

		// Normalize to ₹ Crores (10 Million = 1 Crore) for INR display
		let revCrores = rev.map(v => flt((v / 10000000).toFixed(2)));

		if (this.item1Filter === 'h1') {
			labels = labels.slice(0, 6);
			revCrores = revCrores.slice(0, 6);
			margin = margin.slice(0, 6);
		} else if (this.item1Filter === 'h2') {
			labels = labels.slice(6, 12);
			revCrores = revCrores.slice(6, 12);
			margin = margin.slice(6, 12);
		}

		// Insights tiles
		const ins = rm.insights || {};
		this.wrapper.find('#rev-peak').text(`${ins.peak_revenue_month} (${this.format_inr(ins.peak_revenue_value)})`);
		this.wrapper.find('#margin-peak').text(`${ins.best_margin_month} (${ins.best_margin_value}%)`);
		this.wrapper.find('#rev-run-rate').text(`${this.format_inr(ins.avg_monthly_run_rate)} / Mo`);
		this.wrapper.find('#margin-spread').text(`${ins.margin_spread}% Spread`);

		const ctx = document.getElementById('revenueMarginChart');
		if (!ctx || !window.Chart) return;

		if (this.charts.revMargin) {
			this.charts.revMargin.data.labels = labels;
			this.charts.revMargin.data.datasets[0].data = revCrores;
			this.charts.revMargin.data.datasets[1].data = margin;
			this.charts.revMargin.update();
			return;
		}

		this.charts.revMargin = new Chart(ctx, {
			type: 'bar',
			data: {
				labels: labels,
				datasets: [
					{
						label: 'Revenue (₹ Cr)',
						data: revCrores,
						backgroundColor: 'rgba(2, 132, 199, 0.75)',
						borderColor: '#0284c7',
						borderWidth: 1,
						borderRadius: 5,
						yAxisID: 'yRevenue',
						order: 2,
					},
					{
						type: 'line',
						label: 'Operating Margin (%)',
						data: margin,
						borderColor: '#f59e0b',
						backgroundColor: '#f59e0b',
						borderWidth: 3,
						tension: 0.3,
						pointRadius: 4,
						pointHoverRadius: 6,
						pointBackgroundColor: '#ffffff',
						pointBorderColor: '#f59e0b',
						pointBorderWidth: 2,
						yAxisID: 'yMargin',
						order: 1,
					},
				],
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				plugins: {
					legend: { display: false },
					tooltip: {
						callbacks: {
							label: (c) => c.dataset.yAxisID === 'yRevenue' ? `Revenue: ₹${c.raw} Cr` : `Op. Margin: ${c.raw}%`,
						},
					},
				},
				scales: {
					x: { grid: { display: false } },
					yRevenue: {
						type: 'linear',
						position: 'left',
						title: { display: true, text: 'Revenue (₹ in Crores)', font: { size: 10 } },
						min: 0,
						grid: { color: 'rgba(226, 232, 240, 0.6)' },
					},
					yMargin: {
						type: 'linear',
						position: 'right',
						title: { display: true, text: 'Margin (%)', font: { size: 10 } },
						grid: { display: false },
					},
				},
			},
		});
	}

	async load_unit_series(kind, grain) {
		const cacheKey = `${kind}_${grain}_${this.fiscal_year}_${this.branch}_${this.unit_dimension}`;
		let resData = this.unitCache[cacheKey];

		if (!resData) {
			try {
				const r = await frappe.call({
					method: 'generate_item.generate_item.page.financial_dashboard.financial_dashboard.get_unit_series',
					args: {
						company: this.company,
						fiscal_year: this.fiscal_year,
						branch: this.branch || null,
						kind: kind,
						grain: grain,
						unit_dimension: this.unit_dimension,
					},
				});
				if (r && r.message) {
					resData = r.message;
					this.unitCache[cacheKey] = resData;
				}
			} catch (e) {
				console.error(`Unit series ${kind} load failed:`, e);
				return;
			}
		}

		if (!resData) return;

		// Normalize numbers to ₹ Crores for charting
		const formattedDatasets = (resData.datasets || []).map(ds => ({
			...ds,
			data: (ds.data || []).map(v => flt((v / 10000000).toFixed(2))),
		}));

		if (kind === 'sales') {
			this.render_sales_chart(resData, formattedDatasets);
		} else {
			this.render_purchases_chart(resData, formattedDatasets);
		}
	}

	set_sales_layout(isStacked) {
		this.salesStacked = isStacked;
		this.wrapper.find('#btn-sales-layout-toggle button').removeClass('active');
		this.wrapper.find(`#btn-sales-layout-toggle button[data-layout="${isStacked ? 'stacked' : 'grouped'}"]`).addClass('active');
		if (this.charts.sales) {
			this.charts.sales.options.scales.x.stacked = isStacked;
			this.charts.sales.options.scales.y.stacked = isStacked;
			(this.charts.sales.data.datasets || []).forEach(ds => {
				ds.stack = isStacked ? 'stack_sales' : undefined;
			});
			this.charts.sales.update();
			this.showToast(__('Sales layout: {0}', [isStacked ? __('Stacked') : __('Grouped (Side-by-Side)')]));
		}
	}

	set_purchases_layout(isStacked) {
		this.purchasesStacked = isStacked;
		this.wrapper.find('#btn-purchases-layout-toggle button').removeClass('active');
		this.wrapper.find(`#btn-purchases-layout-toggle button[data-layout="${isStacked ? 'stacked' : 'grouped'}"]`).addClass('active');
		if (this.charts.purchases) {
			this.charts.purchases.options.scales.x.stacked = isStacked;
			this.charts.purchases.options.scales.y.stacked = isStacked;
			(this.charts.purchases.data.datasets || []).forEach(ds => {
				ds.stack = isStacked ? 'stack_purchases' : undefined;
			});
			this.charts.purchases.update();
			this.showToast(__('Purchases layout: {0}', [isStacked ? __('Stacked') : __('Grouped (Side-by-Side)')]));
		}
	}

	render_sales_chart(resData, datasets) {
		this.wrapper.find('#salesTopUnit').text(resData.top_unit || 'N/A');
		this.wrapper.find('#salesTopShare').text(`${resData.top_unit_share}% Share`);

		const formattedDatasets = datasets.map(ds => ({
			...ds,
			stack: this.salesStacked ? 'stack_sales' : undefined,
		}));

		const ctx = document.getElementById('salesChart');
		if (!ctx || !window.Chart) return;

		if (this.charts.sales) {
			this.charts.sales.data.labels = resData.labels;
			this.charts.sales.data.datasets = formattedDatasets;
			this.charts.sales.options.scales.x.stacked = this.salesStacked;
			this.charts.sales.options.scales.y.stacked = this.salesStacked;
			this.charts.sales.update();
			return;
		}

		this.charts.sales = new Chart(ctx, {
			type: 'bar',
			data: {
				labels: resData.labels,
				datasets: formattedDatasets,
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				plugins: {
					legend: { position: 'bottom', labels: { boxWidth: 8, font: { size: 9.5 } } },
					tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ₹${c.raw} Cr` } },
				},
				scales: {
					x: { stacked: this.salesStacked, grid: { display: false } },
					y: {
						stacked: this.salesStacked,
						title: { display: true, text: 'Sales (₹ in Crores)', font: { size: 9.5 } },
						grid: { color: 'rgba(226, 232, 240, 0.6)' },
					},
				},
			},
		});
	}

	render_purchases_chart(resData, datasets) {
		this.wrapper.find('#purchasesTopUnit').text(resData.top_unit || 'N/A');
		this.wrapper.find('#purchasesTopCost').text(`${this.format_inr(resData.grand_total)} YTD`);

		const formattedDatasets = datasets.map(ds => ({
			...ds,
			stack: this.purchasesStacked ? 'stack_purchases' : undefined,
		}));

		const ctx = document.getElementById('purchasesChart');
		if (!ctx || !window.Chart) return;

		if (this.charts.purchases) {
			this.charts.purchases.data.labels = resData.labels;
			this.charts.purchases.data.datasets = formattedDatasets;
			this.charts.purchases.options.scales.x.stacked = this.purchasesStacked;
			this.charts.purchases.options.scales.y.stacked = this.purchasesStacked;
			this.charts.purchases.update();
			return;
		}

		this.charts.purchases = new Chart(ctx, {
			type: 'bar',
			data: {
				labels: resData.labels,
				datasets: formattedDatasets,
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				plugins: {
					legend: { position: 'bottom', labels: { boxWidth: 8, font: { size: 9.5 } } },
					tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ₹${c.raw} Cr` } },
				},
				scales: {
					x: { stacked: this.purchasesStacked, grid: { display: false } },
					y: {
						stacked: this.purchasesStacked,
						title: { display: true, text: 'Purchases (₹ in Crores)', font: { size: 9.5 } },
						grid: { color: 'rgba(226, 232, 240, 0.6)' },
					},
				},
			},
		});
	}

	render_orders_chart() {
		const ord = this.data.orders_monthly;
		const me = this;
		this.wrapper.find('#orders-total-booked').text(`${ord.total_orders_count} Orders`);
		this.wrapper.find('#orders-total-value').text(this.format_inr(ord.total_orders_value));
		this.wrapper.find('#orders-monthly-mean').text(`${ord.monthly_mean} Orders/Mo`);

		const ctx = document.getElementById('ordersBookedChart');
		if (!ctx || !window.Chart) return;

		if (this.charts.orders) {
			this.charts.orders.data.labels = ord.labels;
			this.charts.orders.data.datasets[0].data = ord.count_series;
			this.charts.orders.update();
			return;
		}

		this.charts.orders = new Chart(ctx, {
			type: 'bar',
			data: {
				labels: ord.labels,
				datasets: [
					{
						label: 'Orders Booked',
						data: ord.count_series,
						backgroundColor: 'rgba(139, 92, 246, 0.8)',
						borderColor: '#8b5cf6',
						borderWidth: 1,
						borderRadius: 4,
					},
				],
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				plugins: {
					legend: { display: false },
					tooltip: {
						callbacks: {
							title: (items) => {
								return items.length ? items[0].label : '';
							},
							label: (c) => {
								const idx = c.dataIndex;
								const ordData = me.data?.orders_monthly;
								const count = c.raw;
								const val = ordData?.value_series ? ordData.value_series[idx] : 0;
								const formattedVal = me.format_inr(val);
								const exactVal = me.format_inr(val, false);
								return [
									`Orders Booked: ${count} Orders`,
									`Booking Value: ${formattedVal} (${exactVal})`
								];
							}
						}
					}
				},
				scales: {
					x: { grid: { display: false } },
					y: {
						title: { display: true, text: 'No. of Orders', font: { size: 9.5 } },
						grid: { color: 'rgba(226, 232, 240, 0.6)' },
					},
				},
			},
		});
	}

	render_ar_ageing() {
		const ar = this.data.ar_ageing;
		const me = this;
		this.wrapper.find('#arSubtitle').html(
			`Total Receivables: <strong style="color: #0f172a;">${this.format_inr(ar.total_outstanding)}</strong> • DSO: ${ar.dso_days} Days`
		);
		this.wrapper.find('#arCurrentBadge').text(`Current: ${ar.current_share}%`);

		const buckets = ar.buckets || [];
		const b1Val = buckets[0] ? buckets[0].amount : (ar.chart_data ? ar.chart_data[0] : 0);
		const b4Val = buckets[3] ? buckets[3].amount : (ar.chart_data ? ar.chart_data[3] : 0);

		this.wrapper.find('#ar-footer-total').text(this.format_inr(ar.total_outstanding));
		this.wrapper.find('#ar-footer-dso').text(`${ar.dso_days} Days`);
		this.wrapper.find('#ar-footer-current').text(this.format_inr(b1Val));
		this.wrapper.find('#ar-footer-overdue').text(this.format_inr(b4Val));

		const chartCrores = (ar.chart_data || []).map(v => flt((v / 10000000).toFixed(2)));

		const ctx = document.getElementById('arAgeingChart');
		if (!ctx || !window.Chart) return;

		if (this.charts.ar) {
			this.charts.ar.data.datasets[0].data = chartCrores;
			this.charts.ar.update();
			return;
		}

		this.charts.ar = new Chart(ctx, {
			type: 'bar',
			data: {
				labels: ['< 30d (Current)', '31-60d', '61-90d', '> 90d (Overdue)'],
				datasets: [{
					label: 'Outstanding',
					data: chartCrores,
					backgroundColor: ['#10b981', '#0284c7', '#f59e0b', '#ef4444'],
					borderRadius: 4,
				}],
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				plugins: {
					legend: { display: false },
					tooltip: {
						callbacks: {
							title: (items) => {
								if (!items.length) return '';
								const idx = items[0].dataIndex;
								const bucketObj = (me.data?.ar_ageing?.buckets || [])[idx];
								return bucketObj ? bucketObj.bucket : items[0].label;
							},
							label: (c) => {
								const idx = c.dataIndex;
								const bucketObj = (me.data?.ar_ageing?.buckets || [])[idx];
								const val = bucketObj ? me.format_inr(bucketObj.amount) : `₹${c.raw} Cr`;
								return `Outstanding: ${val}`;
							}
						}
					}
				},
				scales: {
					x: { grid: { display: false } },
					y: {
						title: { display: true, text: 'Outstanding (₹ in Crores)', font: { size: 9.5 } },
						grid: { color: 'rgba(226, 232, 240, 0.6)' },
						ticks: {
							callback: (val) => `₹${val} Cr`
						}
					},
				},
			},
		});
	}

	render_ap_ageing() {
		const ap = this.data.ap_ageing;
		const me = this;
		this.wrapper.find('#apSubtitle').html(
			`Total Payables: <strong style="color: #0f172a;">${this.format_inr(ap.total_outstanding)}</strong> • DPO: ${ap.dpo_days} Days`
		);
		this.wrapper.find('#apDueBadge').text(`Due Soon: ${ap.due_soon_share}%`);

		const buckets = ap.buckets || [];
		const b1Val = buckets[0] ? buckets[0].amount : (ap.chart_data ? ap.chart_data[0] : 0);
		const b4Val = buckets[3] ? buckets[3].amount : (ap.chart_data ? ap.chart_data[3] : 0);

		this.wrapper.find('#ap-footer-total').text(this.format_inr(ap.total_outstanding));
		this.wrapper.find('#ap-footer-dpo').text(`${ap.dpo_days} Days`);
		this.wrapper.find('#ap-footer-current').text(this.format_inr(b1Val));
		this.wrapper.find('#ap-footer-critical').text(this.format_inr(b4Val));

		const chartCrores = (ap.chart_data || []).map(v => flt((v / 10000000).toFixed(2)));

		const ctx = document.getElementById('apAgeingChart');
		if (!ctx || !window.Chart) return;

		if (this.charts.ap) {
			this.charts.ap.data.datasets[0].data = chartCrores;
			this.charts.ap.update();
			return;
		}

		this.charts.ap = new Chart(ctx, {
			type: 'bar',
			data: {
				labels: ['< 30d (Current)', '31-60d', '61-90d', '> 90d (Critical)'],
				datasets: [{
					label: 'Outstanding',
					data: chartCrores,
					backgroundColor: ['#10b981', '#0284c7', '#f59e0b', '#ef4444'],
					borderRadius: 4,
				}],
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				plugins: {
					legend: { display: false },
					tooltip: {
						callbacks: {
							title: (items) => {
								if (!items.length) return '';
								const idx = items[0].dataIndex;
								const bucketObj = (me.data?.ap_ageing?.buckets || [])[idx];
								return bucketObj ? bucketObj.bucket : items[0].label;
							},
							label: (c) => {
								const idx = c.dataIndex;
								const bucketObj = (me.data?.ap_ageing?.buckets || [])[idx];
								const val = bucketObj ? me.format_inr(bucketObj.amount) : `₹${c.raw} Cr`;
								return `Outstanding: ${val}`;
							}
						}
					}
				},
				scales: {
					x: { grid: { display: false } },
					y: {
						title: { display: true, text: 'Payables Outstanding (₹ in Crores)', font: { size: 9.5 } },
						grid: { color: 'rgba(226, 232, 240, 0.6)' },
						ticks: {
							callback: (val) => `₹${val} Cr`
						}
					},
				},
			},
		});
	}
}