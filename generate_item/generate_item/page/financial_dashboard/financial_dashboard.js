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

		// Core filter states
		this.company =
			frappe.defaults.get_default('company') ||
			frappe.defaults.get_user_default('Company') ||
			frappe.defaults.get_default('Company') ||
			(frappe.boot && frappe.boot.sysdefaults ? frappe.boot.sysdefaults.company : '') ||
			'';
		this.date_filter = 'this_fy';
		this.from_date = frappe.datetime.get_today();
		this.to_date = frappe.datetime.get_today();
		this.branch = '';
		this.unit_dimension = 'Branch';

		this.item1Filter = 'all';
		this.salesGrain = 'auto';
		this.salesStacked = true;
		this.purchasesGrain = 'auto';
		this.purchasesStacked = true;

		this.charts = {};
		this.data = null;
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

	format_inr(num, compact = true) {
		const val = flt(num);
		if (isNaN(val)) return '₹0';
		if (!compact) {
			return '₹' + val.toLocaleString('en-IN', { maximumFractionDigits: 2 });
		}
		const absVal = Math.abs(val);
		const sign = val < 0 ? '-' : '';
		if (absVal >= 10000000) {
			return `${sign}₹${(absVal / 10000000).toFixed(2)} Cr`;
		} else if (absVal >= 100000) {
			return `${sign}₹${(absVal / 100000).toFixed(2)} L`;
		} else if (absVal >= 1000) {
			return `${sign}₹${(absVal / 1000).toFixed(1)} K`;
		}
		return `${sign}₹${absVal.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
	}

	format_date_display(dtStr) {
		if (!dtStr) return '';
		try {
			const d = frappe.datetime.str_to_obj(dtStr);
			if (isNaN(d.getTime())) return dtStr;
			return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
		} catch (e) {
			return dtStr;
		}
	}

	render_layout() {
		const html = `
			<div class="fd-root" id="fd-root-container">
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
								<h1 class="fd-brand-title">${__('Financial Dashboard')}</h1>
							</div>
						</div>

						<!-- Controls Group -->
						<div class="fd-controls-group">
							<!-- Date Filter Selector -->
							<div class="fd-control-item" title="${__('Select Date Filter')}">
								<label class="fd-control-label" for="fd-date-filter-select">
									<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
										<rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
										<line x1="16" y1="2" x2="16" y2="6"></line>
										<line x1="8" y1="2" x2="8" y2="6"></line>
										<line x1="3" y1="10" x2="21" y2="10"></line>
									</svg>
									${__('Date Filter')}
								</label>
								<select id="fd-date-filter-select" class="fd-form-select">
									<option value="this_month">${__('This Month')}</option>
									<option value="last_month">${__('Last Month')}</option>
									<option value="this_quarter">${__('This Quarter')}</option>
									<option value="last_quarter">${__('Last Quarter')}</option>
									<option value="this_year">${__('This Year')}</option>
									<option value="last_year">${__('Last Year')}</option>
									<option value="this_fy" selected>${__('This FY')}</option>
									<option value="last_fy">${__('Last FY')}</option>
									<option value="custom">${__('Custom Date')}</option>
								</select>
							</div>

							<!-- Custom Date Range Inputs (hidden by default) -->
							<div class="fd-custom-date-wrap" id="fd-custom-date-container" style="display: none;">
								<div class="fd-control-item">
									<label class="fd-control-label" for="fd-from-date">${__('From')}</label>
									<input type="date" id="fd-from-date" class="fd-form-input" value="${this.from_date}" />
								</div>
								<div class="fd-control-item">
									<label class="fd-control-label" for="fd-to-date">${__('To')}</label>
									<input type="date" id="fd-to-date" class="fd-form-input" value="${this.to_date}" />
								</div>
								<button type="button" class="btn btn-primary btn-sm fd-btn-apply" id="fd-btn-apply-custom">
									${__('Apply')}
								</button>
							</div>

							<!-- Branch Filter Dropdown -->
							<div class="fd-control-item" id="fd-branch-control" title="${__('Filter by Branch')}">
								<label class="fd-control-label" for="fd-branch-select">
									<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
										<path stroke-linecap="round" stroke-linejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
									</svg>
									${__('Branch')}
								</label>
								<select id="fd-branch-select" class="fd-form-select">
									<option value="">${__('All Branches')}</option>
								</select>
							</div>

							<!-- Refresh Button -->
							<button type="button" class="btn btn-default btn-sm fd-btn-refresh" id="fd-btn-refresh" title="${__('Refresh Dashboard')}">
								<svg id="fd-refresh-icon" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
								</svg>
								<span class="fd-btn-text">${__('Refresh')}</span>
							</button>
						</div>
					</div>
				</header>

				<!-- Main Dashboard Body -->
				<main class="fd-main-body">

					<!-- Original KPI Cards Row (Row 1) -->
					<div class="fd-kpi-grid">
						<!-- Original Card 1: Total Net Revenue -->
						<div class="fd-kpi-card" id="fd-kpi-rev" title="${__('Click to open Profit & Loss Statement')}">
							<div class="fd-kpi-header">
								<span class="fd-kpi-label">${__('TOTAL NET REVENUE (INR)')}</span>
								<div class="fd-kpi-icon-pill" style="background: rgba(37, 99, 235, 0.1); color: #2563eb;">
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
						</div>

						<!-- Original Card 2: Operating Margin -->
						<div class="fd-kpi-card" id="fd-kpi-margin" title="${__('Click to open Profit & Loss Statement')}">
							<div class="fd-kpi-header">
								<span class="fd-kpi-label">${__('OPERATING MARGIN')}</span>
								<div class="fd-kpi-icon-pill" style="background: rgba(139, 92, 246, 0.1); color: #7c3aed;">
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
						</div>

						<!-- Original Card 3: Orders Booked -->
						<div class="fd-kpi-card" id="fd-kpi-orders" title="${__('Click to view Sales Orders')}">
							<div class="fd-kpi-header">
								<span class="fd-kpi-label">${__('ORDERS BOOKED')}</span>
								<div class="fd-kpi-icon-pill" style="background: rgba(16, 185, 129, 0.1); color: #059669;">
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
						</div>
					</div>

					<!-- New KPI Cards Row (Row 2, placed below original cards) -->
					<div class="fd-kpi-grid">
						<!-- New Card 1: Total Stock Balance -->
						<div class="fd-kpi-card" id="fd-card-stock" title="${__('Click to open Stock Balance report')}">
							<div class="fd-kpi-header">
								<span class="fd-kpi-label">${__('TOTAL STOCK BALANCE')}</span>
								<div class="fd-kpi-icon-pill" style="background: rgba(37, 99, 235, 0.1); color: #2563eb;">
									<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/>
									</svg>
								</div>
							</div>
							<div class="fd-kpi-value-row">
								<div class="fd-kpi-value" id="kpi-stock-balance">-</div>
							</div>
							<div class="fd-kpi-caption" id="kpi-stock-caption">${__('As of selected end date')}</div>
						</div>

						<!-- New Card 2: Total Purchase -->
						<div class="fd-kpi-card" id="fd-card-purchase" title="${__('Click to view Purchase Invoices for selected period')}">
							<div class="fd-kpi-header">
								<span class="fd-kpi-label">${__('TOTAL PURCHASE')}</span>
								<div class="fd-kpi-icon-pill" style="background: rgba(245, 158, 11, 0.1); color: #d97706;">
									<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z"/>
									</svg>
								</div>
							</div>
							<div class="fd-kpi-value-row">
								<div class="fd-kpi-value" id="kpi-total-purchases">-</div>
							</div>
							<div class="fd-kpi-caption" id="kpi-purchase-caption">${__('Stock items only for period')}</div>
						</div>

						<!-- New Card 3: Total Sales -->
						<div class="fd-kpi-card" id="fd-card-sales" title="${__('Click to view Sales Invoices for selected period')}">
							<div class="fd-kpi-header">
								<span class="fd-kpi-label">${__('TOTAL SALES')}</span>
								<div class="fd-kpi-icon-pill" style="background: rgba(16, 185, 129, 0.1); color: #059669;">
									<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/>
									</svg>
								</div>
							</div>
							<div class="fd-kpi-value-row">
								<div class="fd-kpi-value" id="kpi-total-sales">-</div>
							</div>
							<div class="fd-kpi-caption" id="kpi-sales-caption">${__('Stock items only for period')}</div>
						</div>
					</div>

					<!-- Revenue vs Operating Margin (previously Item 1) -->
					<div class="fd-dash-card" id="fd-card-revenue-margin">
						<div class="fd-dash-card-header">
							<div>
								<h2 class="fd-card-title" id="title-revenue-margin" style="cursor: pointer;" title="${__('Click to open Profit & Loss Statement')}">
									${__('Revenue vs Operating Margin')}
								</h2>
								<p class="fd-card-subtitle">${__('Monthly View • Revenue in ₹ Crores (Left Bar) vs Operating Margin % (Right Line)')}</p>
							</div>

							<div class="fd-chart-header-actions">
								<div style="display: flex; align-items: center; gap: 0.75rem; margin-right: 0.5rem;">
									<span class="fd-legend-item">
										<span class="fd-legend-dot" style="background: #0284c7;"></span> ${__('Revenue (₹ Cr)')}
									</span>
									<span class="fd-legend-item">
										<span class="fd-legend-line" style="background: #f59e0b;"></span> ${__('Op. Margin (%)')}
									</span>
								</div>
								<select id="revMarginMetricFilter" class="fd-form-select" style="border: 1px solid var(--border-color, #d1d5db); border-radius: var(--border-radius-sm, 6px); padding: 0.2rem 0.5rem; font-size: 0.75rem;">
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
							<div class="fd-insights-grid">
								<div class="fd-insight-card">
									<span class="fd-insight-label">${__('Peak Revenue')}</span>
									<p class="fd-insight-val" id="rev-peak">-</p>
								</div>
								<div class="fd-insight-card">
									<span class="fd-insight-label">${__('Best Margin')}</span>
									<p class="fd-insight-val" style="color: #10b981;" id="margin-peak">-</p>
								</div>
								<div class="fd-insight-card">
									<span class="fd-insight-label">${__('Avg Monthly Run-rate')}</span>
									<p class="fd-insight-val" id="rev-run-rate">-</p>
								</div>
								<div class="fd-insight-card">
									<span class="fd-insight-label">${__('Margin Variance')}</span>
									<p class="fd-insight-val" id="margin-spread">-</p>
								</div>
							</div>
						</div>
					</div>

					<!-- Two-Column Grid: Branch Sales & Branch Purchases -->
					<div class="fd-two-col-grid">
						<!-- Sales from Each Unit (Branch Wise Sales) -->
						<div class="fd-dash-card" id="fd-card-branch-sales">
							<div class="fd-dash-card-header">
								<div>
									<h2 class="fd-card-title" id="title-branch-sales" style="cursor: pointer;" title="${__('Click to view Sales Invoices')}">
										${__('Sales from Each Unit (Branch Wise Sales)')}
									</h2>
									<p class="fd-card-subtitle">${__('Branch Wise Sales Breakdown • Stock Items Only in ₹ INR')}</p>
								</div>

								<div class="fd-chart-header-actions">
									<div class="fd-btn-toggle-group" id="btn-sales-grains">
										<!-- Dynamically populated based on period -->
									</div>
									<div class="fd-btn-toggle-group" id="btn-sales-layout-toggle">
										<button type="button" data-layout="stacked" class="active">${__('Stacked')}</button>
										<button type="button" data-layout="grouped">${__('Grouped')}</button>
									</div>
								</div>
							</div>

							<div class="fd-dash-card-body">
								<div class="fd-chart-container-md">
									<canvas id="salesChart" aria-label="${__('Branch Wise Sales Chart')}"></canvas>
								</div>
								<div class="fd-card-footer-strip" id="strip-sales-footer" title="${__('Click to view Sales Invoices')}">
									<span class="fd-footer-text">${__('Top Branch')}: <strong id="salesTopUnit" style="color: var(--text-color);">-</strong></span>
									<span class="fd-footer-highlight" id="salesTopShare">-</span>
								</div>
							</div>
						</div>

						<!-- Purchases from Each Unit (Branch Wise Purchase) -->
						<div class="fd-dash-card" id="fd-card-branch-purchases">
							<div class="fd-dash-card-header">
								<div>
									<h2 class="fd-card-title" id="title-branch-purchases" style="cursor: pointer;" title="${__('Click to view Purchase Invoices')}">
										${__('Purchases from Each Unit (Branch Wise Purchase)')}
									</h2>
									<p class="fd-card-subtitle">${__('Branch Wise Purchase Breakdown • Stock Items Only in ₹ INR')}</p>
								</div>

								<div class="fd-chart-header-actions">
									<div class="fd-btn-toggle-group" id="btn-purchases-grains">
										<!-- Dynamically populated based on period -->
									</div>
									<div class="fd-btn-toggle-group" id="btn-purchases-layout-toggle">
										<button type="button" data-layout="stacked" class="active">${__('Stacked')}</button>
										<button type="button" data-layout="grouped">${__('Grouped')}</button>
									</div>
								</div>
							</div>

							<div class="fd-dash-card-body">
								<div class="fd-chart-container-md">
									<canvas id="purchasesChart" aria-label="${__('Branch Wise Purchase Chart')}"></canvas>
								</div>
								<div class="fd-card-footer-strip" id="strip-purchases-footer" title="${__('Click to view Purchase Invoices')}">
									<span class="fd-footer-text">${__('Major Branch Outflow')}: <strong id="purchasesTopUnit" style="color: var(--text-color);">-</strong></span>
									<span class="fd-footer-highlight" style="color: #f43f5e;" id="purchasesTopCost">-</span>
								</div>
							</div>
						</div>
					</div>

					<!-- No. of Orders Booked -->
					<div class="fd-dash-card" id="fd-card-orders">
						<div class="fd-dash-card-header">
							<div>
								<h2 class="fd-card-title" id="title-orders" style="cursor: pointer;" title="${__('Click to view Sales Orders')}">
									${__('No. of Orders Booked')}
								</h2>
								<p class="fd-card-subtitle">${__('Monthly View • Booked volume and fulfillment run-rate')}</p>
							</div>

							<div class="fd-chart-header-actions">
								<span class="fd-legend-item">
									<span class="fd-legend-dot" style="background: #8b5cf6;"></span> ${__('Orders Booked')}
								</span>
							</div>
						</div>

						<div class="fd-dash-card-body">
							<div class="fd-chart-container-md">
								<canvas id="ordersBookedChart" aria-label="${__('No. of Orders Booked Chart')}"></canvas>
							</div>
							<div class="fd-orders-summary-strip" id="strip-orders-footer" title="${__('Click to view Sales Orders')}">
								<div>
									<span class="fd-metric-label">${__('Total Booked')}</span>
									<p class="fd-metric-val" id="orders-total-booked">-</p>
								</div>
								<div>
									<span class="fd-metric-label">${__('Total Value')}</span>
									<p class="fd-metric-val" style="color: #7c3aed;" id="orders-total-value">-</p>
								</div>
								<div>
									<span class="fd-metric-label">${__('Monthly Mean')}</span>
									<p class="fd-metric-val" id="orders-monthly-mean">-</p>
								</div>
							</div>
						</div>
					</div>

					<!-- Accounts Receivable (AR) Ageing -->
					<div class="fd-dash-card" id="fd-card-ar">
						<div class="fd-dash-card-header">
							<div>
								<h2 class="fd-card-title" id="title-ar" style="cursor: pointer;" title="${__('Click to open Accounts Receivable report')}">
									${__('Accounts Receivable (AR) Ageing')}
								</h2>
								<p class="fd-card-subtitle" id="arSubtitle">${__('Total Receivables: - • DSO: -')}</p>
							</div>
							<span class="fd-status-pill fd-pill-teal" id="arCurrentBadge" title="${__('Click to open Accounts Receivable report')}">-</span>
						</div>

						<div class="fd-dash-card-body">
							<div class="fd-chart-container-md" id="chart-container-ar" style="cursor: pointer;" title="${__('Click to open Accounts Receivable report')}">
								<canvas id="arAgeingChart" aria-label="${__('Accounts Receivable Ageing Bar Chart')}"></canvas>
							</div>
							<div class="fd-metric-summary-strip" id="strip-ar-footer" title="${__('Click to open Accounts Receivable report')}">
								<div class="fd-metric-col">
									<span class="fd-metric-label">${__('Total Receivables')}</span>
									<p class="fd-metric-val" id="ar-footer-total">-</p>
								</div>
								<div class="fd-metric-col">
									<span class="fd-metric-label">${__('DSO')}</span>
									<p class="fd-metric-val" style="color: #2563eb;" id="ar-footer-dso">-</p>
								</div>
								<div class="fd-metric-col">
									<span class="fd-metric-label">${__('Current (< 30d)')}</span>
									<p class="fd-metric-val" style="color: #10b981;" id="ar-footer-current">-</p>
								</div>
								<div class="fd-metric-col">
									<span class="fd-metric-label">${__('Overdue (> 90d)')}</span>
									<p class="fd-metric-val" style="color: #ef4444;" id="ar-footer-overdue">-</p>
								</div>
							</div>
						</div>
					</div>

					<!-- Accounts Payable (AP) Ageing -->
					<div class="fd-dash-card" id="fd-card-ap">
						<div class="fd-dash-card-header">
							<div>
								<h2 class="fd-card-title" id="title-ap" style="cursor: pointer;" title="${__('Click to open Accounts Payable report')}">
									${__('Accounts Payable (AP) Ageing')}
								</h2>
								<p class="fd-card-subtitle" id="apSubtitle">${__('Total Payables: - • DPO: -')}</p>
							</div>
							<span class="fd-status-pill fd-pill-purple" id="apDueBadge" title="${__('Click to open Accounts Payable report')}">-</span>
						</div>

						<div class="fd-dash-card-body">
							<div class="fd-chart-container-md" id="chart-container-ap" style="cursor: pointer;" title="${__('Click to open Accounts Payable report')}">
								<canvas id="apAgeingChart" aria-label="${__('Accounts Payable Ageing Bar Chart')}"></canvas>
							</div>
							<div class="fd-metric-summary-strip" id="strip-ap-footer" title="${__('Click to open Accounts Payable report')}">
								<div class="fd-metric-col">
									<span class="fd-metric-label">${__('Total Payables')}</span>
									<p class="fd-metric-val" id="ap-footer-total">-</p>
								</div>
								<div class="fd-metric-col">
									<span class="fd-metric-label">${__('DPO')}</span>
									<p class="fd-metric-val" style="color: #7c3aed;" id="ap-footer-dpo">-</p>
								</div>
								<div class="fd-metric-col">
									<span class="fd-metric-label">${__('Current (< 30d)')}</span>
									<p class="fd-metric-val" style="color: #10b981;" id="ap-footer-current">-</p>
								</div>
								<div class="fd-metric-col">
									<span class="fd-metric-label">${__('Critical (> 90d)')}</span>
									<p class="fd-metric-val" style="color: #ef4444;" id="ap-footer-critical">-</p>
								</div>
							</div>
						</div>
					</div>

				</main>
			</div>
		`;

		this.page.main.empty().append(html);
		this.bind_events();
	}

	bind_events() {
		const me = this;

		// Refresh Button
		this.wrapper.find('#fd-btn-refresh').on('click', () => {
			const icon = me.wrapper.find('#fd-refresh-icon');
			icon.css({ transition: 'transform 0.5s ease', transform: 'rotate(360deg)' });
			setTimeout(() => icon.css({ transform: 'rotate(0deg)' }), 500);
			me.refresh();
		});

		// Date Filter Select
		this.wrapper.find('#fd-date-filter-select').on('change', function () {
			const val = $(this).val();
			me.date_filter = val;
			if (val === 'custom') {
				me.wrapper.find('#fd-custom-date-container').css('display', 'flex');
			} else {
				me.wrapper.find('#fd-custom-date-container').hide();
				me.refresh();
			}
		});

		// Custom Date Apply Button
		this.wrapper.find('#fd-btn-apply-custom').on('click', () => {
			const f = me.wrapper.find('#fd-from-date').val();
			const t = me.wrapper.find('#fd-to-date').val();
			if (!f || !t) {
				frappe.msgprint(__('Please select both From Date and To Date'));
				return;
			}
			if (f > t) {
				frappe.msgprint(__('From Date cannot be greater than To Date'));
				return;
			}
			me.from_date = f;
			me.to_date = t;
			me.refresh();
		});

		// Branch Filter Select
		this.wrapper.find('#fd-branch-select').on('change', function () {
			me.branch = $(this).val() || '';
			me.refresh();
		});

		// Item 1 Filter (Full Year, H1, H2)
		this.wrapper.find('#revMarginMetricFilter').on('change', function () {
			me.item1Filter = $(this).val();
			me.render_revenue_margin_chart();
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

		// Drilldown Handlers
		this.wrapper.find('#fd-kpi-rev, #fd-kpi-margin').on('click', () => {
			frappe.route_options = {
				company: me.company,
				from_fiscal_year: me.data?.meta?.fiscal_year,
				to_fiscal_year: me.data?.meta?.fiscal_year,
				period_start_date: me.from_date,
				period_end_date: me.to_date,
			};
			if (me.branch) frappe.route_options.branch = me.branch;
			frappe.set_route('query-report', 'Profit and Loss Statement');
		});

		this.wrapper.find('#fd-kpi-orders').on('click', () => {
			frappe.route_options = {
				company: me.company,
				transaction_date: ['between', [me.from_date, me.to_date]],
				docstatus: 1,
			};
			if (me.branch) frappe.route_options.branch = me.branch;
			frappe.set_route('List', 'Sales Order');
		});

		this.wrapper.find('#fd-card-stock').on('click', () => {
			frappe.route_options = {
				company: me.company,
				to_date: me.to_date,
			};
			if (me.branch) frappe.route_options.branch = me.branch;
			frappe.set_route('query-report', 'Stock Balance');
		});

		this.wrapper.find('#fd-card-purchase').on('click', () => {
			frappe.route_options = {
				company: me.company,
				posting_date: ['between', [me.from_date, me.to_date]],
				docstatus: 1,
			};
			if (me.branch) frappe.route_options.branch = me.branch;
			frappe.set_route('List', 'Purchase Invoice');
		});

		this.wrapper.find('#fd-card-sales, #title-branch-sales, #strip-sales-footer').on('click', () => {
			frappe.route_options = {
				company: me.company,
				posting_date: ['between', [me.from_date, me.to_date]],
				docstatus: 1,
			};
			if (me.branch) frappe.route_options.branch = me.branch;
			frappe.set_route('List', 'Sales Invoice');
		});

		this.wrapper.find('#title-revenue-margin').on('click', () => {
			frappe.route_options = {
				company: me.company,
				from_fiscal_year: me.data?.meta?.fiscal_year,
				to_fiscal_year: me.data?.meta?.fiscal_year,
			};
			if (me.branch) frappe.route_options.branch = me.branch;
			frappe.set_route('query-report', 'Profit and Loss Statement');
		});

		this.wrapper.find('#title-branch-purchases, #strip-purchases-footer').on('click', () => {
			frappe.route_options = {
				company: me.company,
				posting_date: ['between', [me.from_date, me.to_date]],
				docstatus: 1,
			};
			if (me.branch) frappe.route_options.branch = me.branch;
			frappe.set_route('List', 'Purchase Invoice');
		});

		this.wrapper.find('#title-orders, #strip-orders-footer').on('click', () => {
			frappe.route_options = {
				company: me.company,
				transaction_date: ['between', [me.from_date, me.to_date]],
				docstatus: 1,
			};
			if (me.branch) frappe.route_options.branch = me.branch;
			frappe.set_route('List', 'Sales Order');
		});

		this.wrapper.find('#title-ar, #arCurrentBadge, #chart-container-ar, #strip-ar-footer').on('click', () => {
			frappe.route_options = {
				company: me.company,
				report_date: me.to_date,
				ageing_based_on: 'Due Date',
				range1: 30,
				range2: 60,
				range3: 90,
				range4: 120,
			};
			if (me.branch) frappe.route_options.branch = me.branch;
			frappe.set_route('query-report', 'Accounts Receivable');
		});

		this.wrapper.find('#title-ap, #apDueBadge, #chart-container-ap, #strip-ap-footer').on('click', () => {
			frappe.route_options = {
				company: me.company,
				report_date: me.to_date,
				ageing_based_on: 'Due Date',
				range1: 30,
				range2: 60,
				range3: 90,
				range4: 120,
			};
			if (me.branch) frappe.route_options.branch = me.branch;
			frappe.set_route('query-report', 'Accounts Payable');
		});
	}

	populate_branch_dropdown() {
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
			if (!silent) frappe.show_progress(__('Loading Financial Dashboard'), 30, 100);

			let res = await frappe.xcall(
				'generate_item.generate_item.page.financial_dashboard.financial_dashboard.get_overview',
				{
					company: this.company || '',
					date_filter: this.date_filter,
					from_date: this.from_date,
					to_date: this.to_date,
					branch: this.branch || null,
					unit_dimension: this.unit_dimension,
				}
			);

			if (!silent) frappe.show_progress(__('Loading Financial Dashboard'), 60, 100);

			if (res && res.message) res = res.message;

			if (res) {
				this.data = res;
				this.update_meta();
				this.render_kpis();
				this.render_revenue_margin_chart();
				this.render_orders_chart();
				this.render_ar_ageing();
				this.render_ap_ageing();

				if (!silent) frappe.show_progress(__('Loading Financial Dashboard'), 85, 100);

				await Promise.all([
					this.load_unit_series('sales'),
					this.load_unit_series('purchases')
				]);
			}
		} catch (err) {
			console.error('Dashboard refresh failed:', err);
		} finally {
			if (!silent) frappe.hide_progress();
		}
	}

	update_meta() {
		if (!this.data || !this.data.meta) return;
		const meta = this.data.meta;
		if (meta.company && !this.company) {
			this.company = meta.company;
		}
		if (meta.from_date) this.from_date = meta.from_date;
		if (meta.to_date) this.to_date = meta.to_date;

		// Sync date filter dropdown & custom date inputs
		if (this.date_filter) {
			this.wrapper.find('#fd-date-filter-select').val(this.date_filter);
		}
		if (this.date_filter === 'custom') {
			this.wrapper.find('#fd-custom-date-container').css('display', 'flex');
		} else {
			this.wrapper.find('#fd-custom-date-container').hide();
		}
		this.wrapper.find('#fd-from-date').val(this.from_date);
		this.wrapper.find('#fd-to-date').val(this.to_date);

		if (meta.all_branches && meta.all_branches.length > 0 && !this.branchesPopulated) {
			this.availableBranches = meta.all_branches;
			this.populate_branch_dropdown();
			this.branchesPopulated = true;
		}
	}

	render_kpis() {
		if (!this.data) return;
		const kpis = this.data.kpis || {};
		const cards = this.data.cards || {};

		// --- Row 1: Original 3 Cards ---
		const netRevenue = flt(kpis.net_revenue !== undefined ? kpis.net_revenue : cards.net_revenue);
		const opMargin = flt(kpis.operating_margin !== undefined ? kpis.operating_margin : cards.operating_margin);
		const ordersCount = cint(kpis.orders_booked_count !== undefined ? kpis.orders_booked_count : cards.orders_booked_count);
		const ordersVal = flt(kpis.orders_booked_value !== undefined ? kpis.orders_booked_value : cards.orders_booked_value);
		const bookToBill = flt(kpis.book_to_bill !== undefined ? kpis.book_to_bill : cards.book_to_bill);

		// 1. Revenue
		this.wrapper.find('#kpi-revenue').text(this.format_inr(netRevenue));
		const revDelta = flt(kpis.revenue_delta || cards.revenue_delta || 0);
		const revTrendEl = this.wrapper.find('#kpi-revenue-trend');
		revTrendEl.toggleClass('negative', revDelta < 0);
		revTrendEl.html(`
			<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" d="${revDelta >= 0 ? 'M5 10l7-7m0 0l7 7m-7-7v18' : 'M19 14l-7 7m0 0l-7-7m7 7V3'}"/>
			</svg>
			${revDelta >= 0 ? '+' : ''}${revDelta.toFixed(1)}%
		`);
		this.wrapper.find('#kpi-revenue-cap').text(kpis.revenue_caption || cards.revenue_caption || __('YTD vs previous year'));

		// 2. Margin
		this.wrapper.find('#kpi-margin').text(`${opMargin.toFixed(0)}%`);
		const marginDelta = flt(kpis.margin_delta || cards.margin_delta || 0);
		const marginTrendEl = this.wrapper.find('#kpi-margin-trend');
		marginTrendEl.toggleClass('negative', marginDelta < 0);
		marginTrendEl.html(`
			<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" d="${marginDelta >= 0 ? 'M5 10l7-7m0 0l7 7m-7-7v18' : 'M19 14l-7 7m0 0l-7-7m7 7V3'}"/>
			</svg>
			${marginDelta >= 0 ? '+' : ''}${marginDelta.toFixed(1)} pts
		`);
		this.wrapper.find('#kpi-margin-cap').text(__('Avg monthly margin'));

		// 3. Orders Booked
		this.wrapper.find('#kpi-orders').text(ordersCount);
		const ordersDelta = flt(kpis.orders_delta || cards.orders_delta || 0);
		const ordersTrendEl = this.wrapper.find('#kpi-orders-trend');
		ordersTrendEl.toggleClass('negative', ordersDelta < 0);
		ordersTrendEl.html(`
			<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" d="${ordersDelta >= 0 ? 'M5 10l7-7m0 0l7 7m-7-7v18' : 'M19 14l-7 7m0 0l-7-7m7 7V3'}"/>
			</svg>
			${ordersDelta >= 0 ? '+' : ''}${ordersDelta.toFixed(1)}%
		`);
		this.wrapper.find('#kpi-orders-cap').text(
			__('Book-to-bill ratio: {0} ({1})', [bookToBill.toFixed(2), this.format_inr(ordersVal)])
		);

		// --- Row 2: 3 New Cards ---
		const stockVal = cards.stock_balance !== undefined ? flt(cards.stock_balance) : flt(kpis.stock_balance || 0);
		const purchaseVal = cards.total_purchases !== undefined ? flt(cards.total_purchases) : flt(kpis.total_purchases || 0);
		const salesVal = cards.total_sales !== undefined ? flt(cards.total_sales) : flt(kpis.total_sales || 0);

		const fromFormatted = this.format_date_display(cards.from_date || this.from_date);
		const toFormatted = this.format_date_display(cards.to_date || this.to_date);

		// New Card 1: Total Stock Balance
		this.wrapper.find('#kpi-stock-balance').text(this.format_inr(stockVal));
		this.wrapper.find('#kpi-stock-caption').text(__('As of {0}', [toFormatted]));

		// New Card 2: Total Purchase
		this.wrapper.find('#kpi-total-purchases').text(this.format_inr(purchaseVal));
		this.wrapper.find('#kpi-purchase-caption').text(
			(cards.from_date || this.from_date) === (cards.to_date || this.to_date)
				? __('Stock items on {0}', [toFormatted])
				: __('Stock items • {0} to {1}', [fromFormatted, toFormatted])
		);

		// New Card 3: Total Sales
		this.wrapper.find('#kpi-total-sales').text(this.format_inr(salesVal));
		this.wrapper.find('#kpi-sales-caption').text(
			(cards.from_date || this.from_date) === (cards.to_date || this.to_date)
				? __('Stock items on {0}', [toFormatted])
				: __('Stock items • {0} to {1}', [fromFormatted, toFormatted])
		);
	}

	render_revenue_margin_chart() {
		if (!this.data || !this.data.revenue_margin) return;
		const rm = this.data.revenue_margin;
		let labels = (rm.labels || []).slice();
		let rev = (rm.revenue_series || []).slice();
		let margin = (rm.margin_series || []).slice();

		const filterSelect = this.wrapper.find('#revMarginMetricFilter');
		if (labels.length < 6) {
			filterSelect.hide();
		} else {
			filterSelect.show();
		}

		let revCrores = rev.map(v => flt((v / 10000000).toFixed(2)));

		if (this.item1Filter === 'h1' && labels.length >= 6) {
			labels = labels.slice(0, 6);
			revCrores = revCrores.slice(0, 6);
			margin = margin.slice(0, 6);
		} else if (this.item1Filter === 'h2' && labels.length >= 12) {
			labels = labels.slice(6, 12);
			revCrores = revCrores.slice(6, 12);
			margin = margin.slice(6, 12);
		}

		// Insights tiles
		const ins = rm.insights || {};
		this.wrapper.find('#rev-peak').text(
			ins.peak_revenue_month && ins.peak_revenue_month !== 'N/A'
				? `${ins.peak_revenue_month} (${this.format_inr(ins.peak_revenue_value)})`
				: '-'
		);
		this.wrapper.find('#margin-peak').text(
			ins.best_margin_month && ins.best_margin_month !== 'N/A'
				? `${ins.best_margin_month} (${ins.best_margin_value}%)`
				: '-'
		);
		this.wrapper.find('#rev-run-rate').text(
			ins.avg_monthly_run_rate > 0
				? `${this.format_inr(ins.avg_monthly_run_rate)} / Mo`
				: '-'
		);
		this.wrapper.find('#margin-spread').text(
			ins.margin_spread !== undefined
				? `${ins.margin_spread}% Spread`
				: '-'
		);

		const ctx = this.wrapper.find('#revenueMarginChart')[0];
		if (!ctx || !window.Chart) return;

		if (this.charts.revMargin) {
			try { this.charts.revMargin.destroy(); } catch (e) {}
			this.charts.revMargin = null;
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
						borderRadius: 4,
						yAxisID: 'yRevenue',
						order: 2,
					},
					{
						type: 'line',
						label: 'Operating Margin (%)',
						data: margin,
						borderColor: '#f59e0b',
						backgroundColor: '#f59e0b',
						borderWidth: 2.5,
						tension: 0.3,
						pointRadius: 3.5,
						pointHoverRadius: 5,
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
						ticks: {
							callback: (val) => `₹${val} Cr`,
						},
					},
					yMargin: {
						type: 'linear',
						position: 'right',
						title: { display: true, text: 'Margin (%)', font: { size: 10 } },
						grid: { display: false },
						ticks: {
							callback: (val) => `${val}%`,
						},
					},
				},
			},
		});
	}

	async load_unit_series(kind = 'sales') {
		const grain = kind === 'sales' ? this.salesGrain : this.purchasesGrain;
		try {
			let res = await frappe.xcall(
				'generate_item.generate_item.page.financial_dashboard.financial_dashboard.get_unit_series',
				{
					company: this.company || '',
					date_filter: this.date_filter,
					from_date: this.from_date,
					to_date: this.to_date,
					branch: this.branch || null,
					kind: kind,
					grain: grain,
					unit_dimension: this.unit_dimension,
				}
			);

			if (res && res.message) res = res.message;

			if (res) {
				const resData = res;
				this.update_grain_buttons(kind, resData.available_grains, resData.grain);

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
		} catch (e) {
			console.error(`Unit series ${kind} load failed:`, e);
		}
	}

	update_grain_buttons(kind, availableGrains, currentGrain) {
		const me = this;
		const containerId = kind === 'sales' ? '#btn-sales-grains' : '#btn-purchases-grains';
		const container = this.wrapper.find(containerId).empty();
		if (!availableGrains || availableGrains.length <= 1) {
			return;
		}

		const grainLabels = {
			days: __('Days'),
			weeks: __('Weeks'),
			months: __('Year-Months'),
			quarters: __('Year-Quarters'),
			years: __('Years'),
		};

		availableGrains.forEach(g => {
			const label = grainLabels[g] || (g.charAt(0).toUpperCase() + g.slice(1));
			const isActive = g === currentGrain ? 'active' : '';
			const btn = $(`<button type="button" data-grain="${g}" class="${isActive}">${label}</button>`);
			btn.on('click', function () {
				const selectedG = $(this).data('grain');
				if (kind === 'sales') {
					me.salesGrain = selectedG;
				} else {
					me.purchasesGrain = selectedG;
				}
				container.find('button').removeClass('active');
				$(this).addClass('active');
				me.load_unit_series(kind);
			});
			container.append(btn);
		});
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
		}
	}

	render_sales_chart(resData, datasets) {
		this.wrapper.find('#salesTopUnit').text(resData.top_unit || 'N/A');
		this.wrapper.find('#salesTopShare').text(
			resData.grand_total > 0
				? `${resData.top_unit_share}% Share (${this.format_inr(resData.grand_total)} Total)`
				: '₹0 Total'
		);

		const formattedDatasets = datasets.map(ds => ({
			...ds,
			stack: this.salesStacked ? 'stack_sales' : undefined,
		}));

		const ctx = this.wrapper.find('#salesChart')[0];
		if (!ctx || !window.Chart) return;

		if (this.charts.sales) {
			try { this.charts.sales.destroy(); } catch (e) {}
			this.charts.sales = null;
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
					legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 10 } } },
					tooltip: {
						callbacks: {
							label: (c) => `${c.dataset.label}: ₹${c.raw} Cr`,
						},
					},
				},
				scales: {
					x: { stacked: this.salesStacked, grid: { display: false } },
					y: {
						stacked: this.salesStacked,
						title: { display: true, text: 'Sales (₹ in Crores)', font: { size: 10 } },
						grid: { color: 'rgba(226, 232, 240, 0.6)' },
					},
				},
			},
		});
	}

	render_purchases_chart(resData, datasets) {
		this.wrapper.find('#purchasesTopUnit').text(resData.top_unit || 'N/A');
		this.wrapper.find('#purchasesTopCost').text(
			resData.grand_total > 0
				? `${this.format_inr(resData.grand_total)} Total`
				: '₹0 Total'
		);

		const formattedDatasets = datasets.map(ds => ({
			...ds,
			stack: this.purchasesStacked ? 'stack_purchases' : undefined,
		}));

		const ctx = this.wrapper.find('#purchasesChart')[0];
		if (!ctx || !window.Chart) return;

		if (this.charts.purchases) {
			try { this.charts.purchases.destroy(); } catch (e) {}
			this.charts.purchases = null;
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
					legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 10 } } },
					tooltip: {
						callbacks: {
							label: (c) => `${c.dataset.label}: ₹${c.raw} Cr`,
						},
					},
				},
				scales: {
					x: { stacked: this.purchasesStacked, grid: { display: false } },
					y: {
						stacked: this.purchasesStacked,
						title: { display: true, text: 'Purchases (₹ in Crores)', font: { size: 10 } },
						grid: { color: 'rgba(226, 232, 240, 0.6)' },
					},
				},
			},
		});
	}

	render_orders_chart() {
		if (!this.data || !this.data.orders_monthly) return;
		const ord = this.data.orders_monthly;
		const me = this;
		this.wrapper.find('#orders-total-booked').text(`${ord.total_orders_count || 0} Orders`);
		this.wrapper.find('#orders-total-value').text(this.format_inr(ord.total_orders_value || 0));
		this.wrapper.find('#orders-monthly-mean').text(`${ord.monthly_mean || 0} Orders/Mo`);

		const ctx = this.wrapper.find('#ordersBookedChart')[0];
		if (!ctx || !window.Chart) return;

		if (this.charts.orders) {
			try { this.charts.orders.destroy(); } catch (e) {}
			this.charts.orders = null;
		}

		this.charts.orders = new Chart(ctx, {
			type: 'bar',
			data: {
				labels: ord.labels || [],
				datasets: [
					{
						label: 'Orders Booked',
						data: ord.count_series || [],
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
							title: (items) => (items.length ? items[0].label : ''),
							label: (c) => {
								const idx = c.dataIndex;
								const ordData = me.data?.orders_monthly;
								const count = c.raw;
								const val = ordData?.value_series ? ordData.value_series[idx] : 0;
								const formattedVal = me.format_inr(val);
								return [
									`Orders Booked: ${count} Orders`,
									`Booking Value: ${formattedVal}`
								];
							},
						},
					},
				},
				scales: {
					x: { grid: { display: false } },
					y: {
						title: { display: true, text: 'No. of Orders', font: { size: 10 } },
						grid: { color: 'rgba(226, 232, 240, 0.6)' },
					},
				},
			},
		});
	}

	render_ar_ageing() {
		if (!this.data || !this.data.ar_ageing) return;
		const ar = this.data.ar_ageing;
		const me = this;
		this.wrapper.find('#arSubtitle').html(
			`Total Receivables: <strong style="color: var(--text-color);">${this.format_inr(ar.total_outstanding)}</strong> • DSO: ${ar.dso_days} Days`
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

		const ctx = this.wrapper.find('#arAgeingChart')[0];
		if (!ctx || !window.Chart) return;

		if (this.charts.ar) {
			try {
				this.charts.ar.destroy();
			} catch (e) {}
			this.charts.ar = null;
		}

		this.charts.ar = new Chart(ctx, {
			type: 'bar',
			data: {
				labels: ['< 30d (Current)', '31-60d', '61-90d', '> 90d (Overdue)'],
				datasets: [{
					label: 'Outstanding',
					data: chartCrores,
					backgroundColor: ['#10b981', '#2563eb', '#f59e0b', '#ef4444'],
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
							},
						},
					},
				},
				scales: {
					x: { grid: { display: false } },
					y: {
						title: { display: true, text: 'Outstanding (₹ in Crores)', font: { size: 10 } },
						grid: { color: 'rgba(226, 232, 240, 0.6)' },
						ticks: {
							callback: (val) => `₹${val} Cr`,
						},
					},
				},
			},
		});
	}

	render_ap_ageing() {
		if (!this.data || !this.data.ap_ageing) return;
		const ap = this.data.ap_ageing;
		const me = this;
		this.wrapper.find('#apSubtitle').html(
			`Total Payables: <strong style="color: var(--text-color);">${this.format_inr(ap.total_outstanding)}</strong> • DPO: ${ap.dpo_days} Days`
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

		const ctx = this.wrapper.find('#apAgeingChart')[0];
		if (!ctx || !window.Chart) return;

		if (this.charts.ap) {
			try {
				this.charts.ap.destroy();
			} catch (e) {}
			this.charts.ap = null;
		}

		this.charts.ap = new Chart(ctx, {
			type: 'bar',
			data: {
				labels: ['< 30d (Current)', '31-60d', '61-90d', '> 90d (Critical)'],
				datasets: [{
					label: 'Outstanding',
					data: chartCrores,
					backgroundColor: ['#10b981', '#2563eb', '#f59e0b', '#ef4444'],
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
							},
						},
					},
				},
				scales: {
					x: { grid: { display: false } },
					y: {
						title: { display: true, text: 'Payables (₹ in Crores)', font: { size: 10 } },
						grid: { color: 'rgba(226, 232, 240, 0.6)' },
						ticks: {
							callback: (val) => `₹${val} Cr`,
						},
					},
				},
			},
		});
	}
}
