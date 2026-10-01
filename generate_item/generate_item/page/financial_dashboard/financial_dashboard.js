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
		this.fy_start = null;
		this.fy_end = null;
		this.unit_dimension = 'Cost Center';

		this.salesGrain = 'quarters';
		this.purchasesGrain = 'quarters';
		this.isWireframe = false;
		this.salesStacked = true;
		this.purchasesStacked = true;
		this.item1Filter = 'all';

		this.charts = {};
		this.data = null;
		this.unitCache = {};
		this.availableFYs = [];
		this.initialized = false;

		this.specDetails = {
			overview: {
				category: "Architecture Overview",
				title: "Financial Dashboard Specifications",
				items: [
					{ label: "Executive Audience", text: "Chief Financial Officer, Operations Leadership, and Business Unit Controllers." },
					{ label: "Coverage", text: "Implements all 7 requested financial modules with dynamic granularity and dual-axis analytics." },
					{ label: "Data Cadence", text: "Real-time feeds refreshed continuously from core ERPNext ledgers and operational pipelines." }
				]
			},
			item1: {
				category: "Module Spec #1",
				title: "Revenue vs Operating Margin",
				items: [
					{ label: "Spreadsheet Requirement", text: "Item 1: Revenue vs Operating Margin (Monthly View)." },
					{ label: "Chart Architecture", text: "Dual-Axis Combination Chart. Left Axis (Bars): Net Revenue in Millions. Right Axis (Line): Operating Margin in %." },
					{ label: "Controls", text: "Filter by Full Year (12M), First Half (H1), or Second Half (H2) with dynamic summary stat recalculations." }
				]
			},
			item2: {
				category: "Module Spec #2",
				title: "Sales from Each Unit",
				items: [
					{ label: "Spreadsheet Requirement", text: "Item 2: Sales from each unit (Years / Year-Quarters / Year-Months)." },
					{ label: "Grain Selector", text: "Switch instantly between multi-year aggregated view, quarterly run-rates, and monthly trends." },
					{ label: "Units Tracked", text: "Configurable business units (Cost Center / Branch / Company)." }
				]
			},
			item3: {
				category: "Module Spec #3",
				title: "Purchases from Each Unit",
				items: [
					{ label: "Spreadsheet Requirement", text: "Item 3: Purchases from each unit (Years / Year-Quarters / Year-Months)." },
					{ label: "Business Value", text: "Analyzes procurement expenditures and operational cost-centers across each strategic unit." },
					{ label: "Interactive Features", text: "Temporal toggle (Years / Quarters / Months) and Stacked/Grouped comparison mode." }
				]
			},
			item4: {
				category: "Module Spec #4",
				title: "No. of Orders Booked",
				items: [
					{ label: "Spreadsheet Requirement", text: "Item 4: No. of orders booked (Monthly View)." },
					{ label: "Target Benchmarking", text: "Tracks monthly booking volume against corporate budgeted quota line and fulfillment run-rate." }
				]
			},
			item5: {
				category: "Module Spec #5",
				title: "Pending Orders Status",
				items: [
					{ label: "Spreadsheet Requirement", text: "Item 5: Pending Orders status." },
					{ label: "Lifecycle Breakdown", text: "Doughnut pipeline showing Production, QA Inspection, In Transit, Payment Hold, and Open orders." },
					{ label: "Backlog Valuation", text: "Total pending pipeline value with delivery SLA tracking." }
				]
			},
			item6: {
				category: "Module Spec #6",
				title: "Accounts Receivable Ageing",
				items: [
					{ label: "Spreadsheet Requirement", text: "Item 6: Accounts Receivable Ageing." },
					{ label: "Ageing Intervals", text: "< 30 Days (Current), 31-60 Days, 61-90 Days, > 90 Days (Overdue)." },
					{ label: "Health Score", text: "Outstanding balance distribution and DSO tracking." }
				]
			},
			item7: {
				category: "Module Spec #7",
				title: "Accounts Payable Ageing",
				items: [
					{ label: "Spreadsheet Requirement", text: "Item 7: Accounts Payable Ageing." },
					{ label: "Liability Intervals", text: "< 30 Days, 31-60 Days, 61-90 Days, > 90 Days." },
					{ label: "Cash Flow Health", text: "DPO calculation with scheduled payment batch distribution and disbursement actions." }
				]
			}
		};

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

		const today = frappe.datetime.get_today();
		const reportDate = (f.fy_end && f.fy_end < today) ? f.fy_end : today;

		switch (type) {
			case 'pnl':
			case 'revenue':
			case 'margin':
				return {
					company: f.company,
					filter_based_on: 'Fiscal Year',
					from_fiscal_year: f.fiscal_year,
					to_fiscal_year: f.fiscal_year,
					period_start_date: f.fy_start,
					period_end_date: f.fy_end,
					periodicity: 'Monthly',
				};
			case 'orders':
			case 'order_book':
				return {
					company: f.company,
					transaction_date: ['between', [f.fy_start, f.fy_end]],
					docstatus: 1,
				};
			case 'backlog':
			case 'pending_orders':
				return {
					company: f.company,
					transaction_date: ['between', [f.fy_start, f.fy_end]],
					status: ['in', ['To Deliver and Bill', 'To Deliver', 'To Bill', 'On Hold']],
					docstatus: 1,
				};
			case 'sales_invoices':
			case 'sales':
				return {
					company: f.company,
					posting_date: ['between', [f.fy_start, f.fy_end]],
					docstatus: 1,
				};
			case 'purchase_invoices':
			case 'purchases':
				return {
					company: f.company,
					posting_date: ['between', [f.fy_start, f.fy_end]],
					docstatus: 1,
				};
			case 'ar':
				return {
					company: f.company,
					report_date: reportDate,
					ageing_based_on: 'Due Date',
					range1: 30,
					range2: 60,
					range3: 90,
					range4: 120,
				};
			case 'ap':
				return {
					company: f.company,
					report_date: reportDate,
					ageing_based_on: 'Due Date',
					range1: 30,
					range2: 60,
					range3: 90,
					range4: 120,
				};
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
								<div style="display: flex; align-items: center; gap: 0.5rem;">
									<h1 class="fd-brand-title">${__('Financial Dashboard')}</h1>
									<span class="fd-status-badge">
										<span class="fd-pulse-dot"></span> Live Sync
									</span>
									<span class="fd-wf-metric-pill">SPEC v2.6 ACTIVE</span>
								</div>
								<p class="fd-brand-subtitle">${__('Executive financial performance, unit operations & working capital')}</p>
							</div>
						</div>

						<!-- Controls Group -->
						<div class="fd-controls-group">
							<!-- FY Selector Dynamic Toggle -->
							<div style="display: inline-flex; align-items: center; gap: 0.25rem;">
								<span style="font-size: 0.72rem; color: var(--text-secondary); font-weight: 600;">FY:</span>
								<div class="fd-btn-toggle-group" id="fd-fy-toggle-group">
									<!-- Dynamically rendered from ERPNext Fiscal Years -->
								</div>
							</div>

							<!-- Wireframe Mode Toggle Button -->
							<button type="button" class="fd-btn-action" id="fd-btn-wireframe">
								<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z"/>
								</svg>
								<span id="fd-wireframe-label">${__('Blueprint Wireframe')}</span>
							</button>

							<!-- Spec Inspector Drawer Button -->
							<button type="button" class="fd-btn-action fd-spec-btn" id="fd-btn-specs">
								<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
								</svg>
								<span>${__('Wireframe Specs')}</span>
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
								<span class="fd-kpi-label">${__('Total Net Revenue')}</span>
								<div class="fd-kpi-icon-pill" style="background: #e0f2fe; color: #0284c7;">
									<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
								</div>
							</div>
							<div class="fd-kpi-value-row">
								<div class="fd-kpi-value" id="kpi-revenue">-</div>
								<span class="fd-kpi-trend" id="kpi-revenue-trend">
									<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M5 10l7-7m0 0l7 7m-7-7v18"/></svg>+12.4%
								</span>
							</div>
							<div class="fd-kpi-caption" id="kpi-revenue-cap">${__('YTD performance vs target')}</div>
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
									<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M5 10l7-7m0 0l7 7m-7-7v18"/></svg>+1.8 pts
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
									<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M5 10l7-7m0 0l7 7m-7-7v18"/></svg>+8.2%
								</span>
							</div>
							<div class="fd-kpi-caption" id="kpi-orders-cap">${__('Book-to-bill ratio: 1.14')}</div>
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
							<div class="fd-kpi-caption" id="kpi-pending-cap">${__('92% on SLA delivery timeline')}</div>
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
									<button type="button" class="fd-spec-link" data-spec="item1">[Spec]</button>
									<span class="fd-wf-metric-pill">[Dual-Axis Combo | Monthly View]</span>
								</div>
								<p class="fd-card-subtitle">${__('Monthly View • Revenue in Millions (Left Bar) vs Operating Margin % (Right Line)')}</p>
							</div>

							<div style="display: flex; align-items: center; gap: 0.75rem;">
								<div style="display: flex; align-items: center; gap: 0.75rem; font-size: 0.72rem; font-weight: 600;">
									<span style="display: inline-flex; align-items: center; gap: 0.35rem;">
										<span style="width: 10px; height: 10px; border-radius: 2px; background: #0284c7;"></span> ${__('Revenue')}
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

					<!-- ITEM 2 & ITEM 3: Sales & Purchases from Each Unit with Multi-grain Selectors -->
					<div class="fd-two-col-grid">

						<!-- Item 2: Sales from each unit -->
						<div class="fd-dash-card" id="fd-card-item2">
							<div class="fd-dash-card-header">
								<div>
									<div class="fd-card-title-wrap">
										<span class="fd-item-tag fd-tag-green">ITEM 2</span>
										<h2 class="fd-card-title" style="cursor: pointer;" id="title-item2" title="${__('Click to view Sales Invoices')}">${__('Sales from Each Unit')}</h2>
										<button type="button" class="fd-spec-link" data-spec="item2">[Spec]</button>
									</div>
									<p class="fd-card-subtitle">${__('Granularity: Years / Year-Quarters / Year-Months')}</p>
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
									<canvas id="salesChart" aria-label="${__('Sales from Each Unit Chart')}"></canvas>
								</div>
								<div style="margin-top: 0.75rem; padding: 0.4rem 0.65rem; background: #f8fafc; border-radius: 6px; display: flex; justify-content: space-between; font-size: 0.7rem; cursor: pointer;" id="strip-sales-footer" title="${__('Click to view Sales Invoices')}">
									<span style="color: #64748b;">${__('Top Volume Unit')}: <strong id="salesTopUnit">-</strong></span>
									<span style="font-weight: 700; color: #10b981;" id="salesTopShare">-</span>
								</div>
							</div>
						</div>

						<!-- Item 3: Purchases from each unit -->
						<div class="fd-dash-card" id="fd-card-item3">
							<div class="fd-dash-card-header">
								<div>
									<div class="fd-card-title-wrap">
										<span class="fd-item-tag fd-tag-amber">ITEM 3</span>
										<h2 class="fd-card-title" style="cursor: pointer;" id="title-item3" title="${__('Click to view Purchase Invoices')}">${__('Purchases from Each Unit')}</h2>
										<button type="button" class="fd-spec-link" data-spec="item3">[Spec]</button>
									</div>
									<p class="fd-card-subtitle">${__('Granularity: Years / Year-Quarters / Year-Months')}</p>
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
									<canvas id="purchasesChart" aria-label="${__('Purchases from Each Unit Chart')}"></canvas>
								</div>
								<div style="margin-top: 0.75rem; padding: 0.4rem 0.65rem; background: #f8fafc; border-radius: 6px; display: flex; justify-content: space-between; font-size: 0.7rem; cursor: pointer;" id="strip-purchases-footer" title="${__('Click to view Purchase Invoices')}">
									<span style="color: #64748b;">${__('Major Cost Center')}: <strong id="purchasesTopUnit">-</strong></span>
									<span style="font-weight: 700; color: #f43f5e;" id="purchasesTopCost">-</span>
								</div>
							</div>
						</div>

					</div>

					<!-- ITEM 4 & ITEM 5: Orders Booked & Pending Orders Status -->
					<div class="fd-two-col-grid fd-orders-grid">

						<!-- Item 4: No. of orders booked (Monthly View) -->
						<div class="fd-dash-card" id="fd-card-item4">
							<div class="fd-dash-card-header">
								<div>
									<div class="fd-card-title-wrap">
										<span class="fd-item-tag fd-tag-purple">ITEM 4</span>
										<h2 class="fd-card-title" style="cursor: pointer;" id="title-item4" title="${__('Click to view Sales Orders')}">${__('No. of Orders Booked')}</h2>
										<button type="button" class="fd-spec-link" data-spec="item4">[Spec]</button>
									</div>
									<p class="fd-card-subtitle">${__('Monthly View • Booked volume vs Monthly targets and fulfillment run-rate')}</p>
								</div>

								<div style="display: flex; align-items: center; gap: 0.75rem; font-size: 0.72rem; font-weight: 600;">
									<span style="display: inline-flex; align-items: center; gap: 0.35rem;">
										<span style="width: 10px; height: 10px; border-radius: 2px; background: #8b5cf6;"></span> ${__('Orders Booked')}
									</span>
									<span style="display: inline-flex; align-items: center; gap: 0.35rem;">
										<span style="width: 12px; height: 2px; background: #64748b; border: 1px dashed #64748b;"></span> ${__('Target Quota')}
									</span>
								</div>
							</div>

							<div class="fd-dash-card-body">
								<div class="fd-chart-container-md">
									<canvas id="ordersBookedChart" aria-label="${__('No. of Orders Booked Chart')}"></canvas>
								</div>
								<div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 0.5rem; text-align: center; margin-top: 0.75rem; border-top: 1px solid #f1f5f9; padding-top: 0.75rem; font-size: 0.72rem; cursor: pointer;" id="strip-orders-footer" title="${__('Click to view Sales Orders')}">
									<div>
										<span style="color: #64748b;">${__('Total Booked')}</span>
										<p style="font-weight: 700; color: #0f172a; font-size: 0.85rem;" id="orders-total-booked">-</p>
									</div>
									<div>
										<span style="color: #64748b;">${__('Monthly Mean')}</span>
										<p style="font-weight: 700; color: #0f172a; font-size: 0.85rem;" id="orders-monthly-mean">-</p>
									</div>
									<div>
										<span style="color: #64748b;">${__('Target Attainment')}</span>
										<p style="font-weight: 700; color: #10b981; font-size: 0.85rem;" id="orders-target-attain">-</p>
									</div>
								</div>
							</div>
						</div>

						<!-- Item 5: Pending Orders status -->
						<div class="fd-dash-card" id="fd-card-item5">
							<div class="fd-dash-card-header">
								<div>
									<div class="fd-card-title-wrap">
										<span class="fd-item-tag fd-tag-rose">ITEM 5</span>
										<h2 class="fd-card-title" id="title-item5">${__('Pending Orders Status')}</h2>
										<button type="button" class="fd-spec-link" data-spec="item5">[Spec]</button>
									</div>
									<p class="fd-card-subtitle">${__('Operational order pipeline & backlog')}</p>
								</div>
								<span style="font-size: 0.72rem; font-weight: 700; background: #f1f5f9; padding: 0.2rem 0.5rem; border-radius: 4px;" id="pendingUnitsBadge">-</span>
							</div>

							<div class="fd-dash-card-body" style="display: flex; flex-direction: column; align-items: center; justify-content: center;">
								<div style="position: relative; width: 170px; height: 170px; margin: 0 auto;" id="container-pending-donut">
									<canvas id="pendingOrdersChart" aria-label="${__('Pending Orders Doughnut Chart')}"></canvas>
									<div style="position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; pointer-events: none;">
										<span style="font-size: 1.5rem; font-weight: 800; color: #0f172a; line-height: 1;" id="pendingCenterNum">0</span>
										<span style="font-size: 0.65rem; font-weight: 700; color: #64748b; text-transform: uppercase; margin-top: 2px;">PENDING</span>
									</div>
								</div>

								<!-- Status legend list -->
								<div style="width: 100%; margin-top: 1rem; display: flex; flex-direction: column; gap: 0.35rem; font-size: 0.72rem;" id="pendingStagesList">
									<!-- Dynamically populated -->
								</div>
							</div>
						</div>

					</div>

					<!-- ITEM 6 & ITEM 7: Accounts Receivable & Accounts Payable Ageing -->
					<div class="fd-two-col-grid">

						<!-- Item 6: Accounts Receivable Ageing -->
						<div class="fd-dash-card" id="fd-card-item6">
							<div class="fd-dash-card-header">
								<div>
									<div class="fd-card-title-wrap">
										<span class="fd-item-tag fd-tag-teal">ITEM 6</span>
										<h2 class="fd-card-title" style="cursor: pointer;" id="title-item6" title="${__('Click to open Accounts Receivable report')}">${__('Accounts Receivable (AR) Ageing')}</h2>
										<button type="button" class="fd-spec-link" data-spec="item6">[Spec]</button>
									</div>
									<p class="fd-card-subtitle" id="arSubtitle">${__('Total Receivables: - • DSO: -')}</p>
								</div>
								<span style="font-size: 0.72rem; font-weight: 600; color: #0f766e; background: #ccfbf1; padding: 0.2rem 0.5rem; border-radius: 4px; cursor: pointer;" id="arCurrentBadge" title="${__('Click to open Accounts Receivable report')}">-</span>
							</div>

							<div class="fd-dash-card-body">
								<div class="fd-chart-container-sm" style="cursor: pointer;" id="chart-container-ar" title="${__('Click to open Accounts Receivable report')}">
									<canvas id="arAgeingChart" aria-label="${__('Accounts Receivable Ageing Bar Chart')}"></canvas>
								</div>

								<!-- AR Detail Table -->
								<table class="fd-data-table" id="arTable">
									<thead>
										<tr>
											<th>${__('Bucket')}</th>
											<th>${__('Amount')}</th>
											<th>${__('Share')}</th>
											<th>${__('Risk Profile')}</th>
										</tr>
									</thead>
									<tbody>
										<!-- Dynamically populated -->
									</tbody>
								</table>
							</div>
						</div>

						<!-- Item 7: Accounts Payable Ageing -->
						<div class="fd-dash-card" id="fd-card-item7">
							<div class="fd-dash-card-header">
								<div>
									<div class="fd-card-title-wrap">
										<span class="fd-item-tag fd-tag-purple">ITEM 7</span>
										<h2 class="fd-card-title" style="cursor: pointer;" id="title-item7" title="${__('Click to open Accounts Payable report')}">${__('Accounts Payable (AP) Ageing')}</h2>
										<button type="button" class="fd-spec-link" data-spec="item7">[Spec]</button>
									</div>
									<p class="fd-card-subtitle" id="apSubtitle">${__('Total Payables: - • DPO: -')}</p>
								</div>
								<span style="font-size: 0.72rem; font-weight: 600; color: #6d28d9; background: #ede9fe; padding: 0.2rem 0.5rem; border-radius: 4px; cursor: pointer;" id="apDueBadge" title="${__('Click to open Accounts Payable report')}">-</span>
							</div>

							<div class="fd-dash-card-body">
								<div class="fd-chart-container-sm" style="cursor: pointer;" id="chart-container-ap" title="${__('Click to open Accounts Payable report')}">
									<canvas id="apAgeingChart" aria-label="${__('Accounts Payable Ageing Bar Chart')}"></canvas>
								</div>

								<!-- AP Detail Table -->
								<table class="fd-data-table" id="apTable">
									<thead>
										<tr>
											<th>${__('Bucket')}</th>
											<th>${__('Amount')}</th>
											<th>${__('Share')}</th>
											<th>${__('Disbursement Action')}</th>
										</tr>
									</thead>
									<tbody>
										<!-- Dynamically populated -->
									</tbody>
								</table>
							</div>
						</div>

					</div>

					<!-- Interactive Wireframe Architecture & Requirements Spec Matrix -->
					<div class="fd-dash-card" style="background: #0f172a; border-color: #1e293b; color: #e2e8f0;">
						<div class="fd-dash-card-header" style="background: #1e293b; border-color: #334155;">
							<div style="display: flex; align-items: center; justify-content: space-between; width: 100%;">
								<div>
									<h3 style="font-size: 0.85rem; font-weight: 700; color: #ffffff; text-transform: uppercase; letter-spacing: 0.05em; display: flex; align-items: center; gap: 0.4rem; margin: 0;">
										<svg fill="none" stroke="#38bdf8" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
										${__('Spreadsheet Coverage & Wireframe Specs')}
									</h3>
									<p style="font-size: 0.7rem; color: #94a3b8; margin-top: 2px; margin-bottom: 0;">${__('Click any card below to inspect functional data contracts and UI patterns')}</p>
								</div>
								<span style="font-size: 0.7rem; padding: 0.2rem 0.5rem; background: #0369a1; color: #ffffff; border-radius: 4px; font-weight: 600;">7 Modules Ready</span>
							</div>
						</div>

						<div class="fd-dash-card-body" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 0.75rem; font-size: 0.72rem;">
							<div class="fd-spec-trigger-card" data-spec="item1" style="background: #1e293b; padding: 0.65rem; border-radius: 8px; border: 1px solid #334155; cursor: pointer;">
								<strong style="color: #38bdf8; display: block; margin-bottom: 2px;">#1 Revenue vs Margin &rarr;</strong>
								<span style="color: #94a3b8;">Monthly dual-axis bar & line view</span>
							</div>
							<div class="fd-spec-trigger-card" data-spec="item2" style="background: #1e293b; padding: 0.65rem; border-radius: 8px; border: 1px solid #334155; cursor: pointer;">
								<strong style="color: #4ade80; display: block; margin-bottom: 2px;">#2 Sales from Units &rarr;</strong>
								<span style="color: #94a3b8;">Years / Quarters / Months breakdown</span>
							</div>
							<div class="fd-spec-trigger-card" data-spec="item3" style="background: #1e293b; padding: 0.65rem; border-radius: 8px; border: 1px solid #334155; cursor: pointer;">
								<strong style="color: #fbbf24; display: block; margin-bottom: 2px;">#3 Purchases from Units &rarr;</strong>
								<span style="color: #94a3b8;">Procurement outflow across units</span>
							</div>
							<div class="fd-spec-trigger-card" data-spec="item4" style="background: #1e293b; padding: 0.65rem; border-radius: 8px; border: 1px solid #334155; cursor: pointer;">
								<strong style="color: #c084fc; display: block; margin-bottom: 2px;">#4 Orders Booked &rarr;</strong>
								<span style="color: #94a3b8;">Monthly actual vs quota run-rate</span>
							</div>
							<div class="fd-spec-trigger-card" data-spec="item5" style="background: #1e293b; padding: 0.65rem; border-radius: 8px; border: 1px solid #334155; cursor: pointer;">
								<strong style="color: #f87171; display: block; margin-bottom: 2px;">#5 Pending Orders &rarr;</strong>
								<span style="color: #94a3b8;">Pipeline doughnut lifecycle & backlog</span>
							</div>
							<div class="fd-spec-trigger-card" data-spec="item6" style="background: #1e293b; padding: 0.65rem; border-radius: 8px; border: 1px solid #334155; cursor: pointer;">
								<strong style="color: #2dd4bf; display: block; margin-bottom: 2px;">#6 AR Ageing &rarr;</strong>
								<span style="color: #94a3b8;">Receivables intervals & risk bands</span>
							</div>
							<div class="fd-spec-trigger-card" data-spec="item7" style="background: #1e293b; padding: 0.65rem; border-radius: 8px; border: 1px solid #334155; cursor: pointer;">
								<strong style="color: #e879f9; display: block; margin-bottom: 2px;">#7 AP Ageing &rarr;</strong>
								<span style="color: #94a3b8;">Payable liabilities & schedules</span>
							</div>
						</div>
					</div>

				</main>

				<!-- Wireframe Spec Inspector Drawer Modal -->
				<div id="specModal" class="fd-modal-backdrop">
					<div class="fd-modal-panel">
						<div style="padding: 1.25rem; border-bottom: 1px solid #1e293b; display: flex; align-items: center; justify-content: space-between;">
							<div>
								<span id="modalSpecCategory" style="font-family: var(--font-mono); font-size: 0.65rem; color: #38bdf8; text-transform: uppercase; font-weight: 600;">Spec Drawer</span>
								<h3 id="modalSpecTitle" style="font-size: 1.1rem; font-weight: 700; color: #ffffff; margin-top: 2px; margin-bottom: 0;">Component Details</h3>
							</div>
							<button type="button" id="btn-close-modal" style="background: #1e293b; border: 1px solid #334155; color: #94a3b8; padding: 0.4rem; border-radius: 6px; cursor: pointer;">
								<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
							</button>
						</div>

						<div id="modalSpecContent" style="padding: 1.25rem; flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 0.85rem; font-size: 0.78rem;">
							<!-- Dynamically injected -->
						</div>

						<div style="padding: 1rem 1.25rem; border-top: 1px solid #1e293b; display: flex; align-items: center; justify-content: space-between; font-size: 0.72rem;">
							<span style="font-family: var(--font-mono); color: #64748b;">FIN-SPEC-v2.6</span>
							<button type="button" id="btn-close-modal-footer" style="padding: 0.45rem 1rem; border-radius: 6px; background: #0284c7; color: #ffffff; border: none; font-weight: 600; cursor: pointer;">
								${__('Close Inspector')}
							</button>
						</div>
					</div>
				</div>

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

	openSpecDrawer(key) {
		const data = this.specDetails[key] || this.specDetails.overview;
		this.wrapper.find('#modalSpecCategory').text(data.category);
		this.wrapper.find('#modalSpecTitle').text(data.title);
		const container = this.wrapper.find('#modalSpecContent');
		container.html(data.items.map(item => `
			<div style="background: #1e293b; border: 1px solid #334155; padding: 0.85rem; border-radius: 8px;">
				<p style="font-weight: 700; color: #38bdf8; font-size: 0.72rem; text-transform: uppercase; margin-bottom: 0.3rem;">${item.label}</p>
				<p style="color: #cbd5e1; line-height: 1.45; margin: 0;">${item.text}</p>
			</div>
		`).join(''));
		this.wrapper.find('#specModal').addClass('open');
	}

	closeSpecDrawer() {
		this.wrapper.find('#specModal').removeClass('open');
	}

	toggleWireframeMode() {
		this.isWireframe = !this.isWireframe;
		this.wrapper.find('#fd-root-container').toggleClass('wireframe-mode', this.isWireframe);
		this.wrapper.find('#fd-wireframe-label').text(this.isWireframe ? __('Hi-Fi UI Mode') : __('Blueprint Wireframe'));
		this.showToast(this.isWireframe ? __('Blueprint wireframe mode activated') : __('Standard visual mode activated'));
	}

	bind_events() {
		const me = this;

		// Wireframe Mode Button
		this.wrapper.find('#fd-btn-wireframe').on('click', () => me.toggleWireframeMode());

		// Spec Drawer Buttons
		this.wrapper.find('#fd-btn-specs').on('click', () => me.openSpecDrawer('overview'));
		this.wrapper.find('.fd-spec-link, .fd-spec-trigger-card').on('click', function () {
			const key = $(this).data('spec');
			me.openSpecDrawer(key);
		});

		// Modal Close Buttons
		this.wrapper.find('#btn-close-modal, #btn-close-modal-footer').on('click', () => me.closeSpecDrawer());
		this.wrapper.find('#specModal').on('click', function (e) {
			if (e.target === this) me.closeSpecDrawer();
		});

		// Refresh Button Action
		this.wrapper.find('#fd-btn-refresh').on('click', () => {
			const icon = me.wrapper.find('#fd-refresh-icon');
			icon.css({ transition: 'transform 0.5s ease', transform: 'rotate(360deg)' });
			setTimeout(() => icon.css({ transform: 'rotate(0deg)' }), 500);
			me.unitCache = {};
			me.refresh();
			me.showToast(__('Data re-synchronized with ERP ledger'));
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
		this.wrapper.find('#title-item6, #arCurrentBadge, #chart-container-ar').on('click', () => {
			me.drilldown('query-report', 'Accounts Receivable', 'ar');
		});

		// 7. Item 7: Accounts Payable Ageing
		this.wrapper.find('#title-item7, #apDueBadge, #chart-container-ap').on('click', () => {
			me.drilldown('query-report', 'Accounts Payable', 'ap');
		});
	}

	render_fy_pills() {
		const me = this;
		const container = this.wrapper.find('#fd-fy-toggle-group').empty();

		if (!this.availableFYs || this.availableFYs.length === 0) {
			return;
		}

		this.availableFYs.forEach((fy) => {
			const isActive = fy.name === me.fiscal_year;
			let label = fy.name;
			if (fy.name.includes('-')) {
				const parts = fy.name.split('-');
				if (parts.length === 2 && parts[0].length === 4 && parts[1].length === 4) {
					label = `${parts[0]}-${parts[1].slice(2)}`;
				}
			}
			const btn = $(`<button type="button" class="${isActive ? 'active' : ''}" data-fy="${fy.name}" title="${fy.name} (${fy.year_start_date} to ${fy.year_end_date})">${label}</button>`);
			
			btn.on('click', function () {
				me.wrapper.find('#fd-fy-toggle-group button').removeClass('active');
				$(this).addClass('active');
				me.fiscal_year = fy.name;
				me.fy_start = fy.year_start_date;
				me.fy_end = fy.year_end_date;
				me.unitCache = {};
				me.refresh();
				me.showToast(__('Switched fiscal year to {0}', [fy.name]));
			});
			container.append(btn);
		});
	}

	format_compact(num) {
		const val = flt(num);
		if (Math.abs(val) >= 10000000) {
			return `$${(val / 10000000).toFixed(2)}Cr`;
		} else if (Math.abs(val) >= 1000000) {
			return `$${(val / 1000000).toFixed(1)}M`;
		} else if (Math.abs(val) >= 1000) {
			return `$${(val / 1000).toFixed(0)}K`;
		}
		return `$${val.toLocaleString()}`;
	}

	async refresh(silent = false) {
		try {
			if (!silent) frappe.show_progress(__('Loading Financial Dashboard'), 40, 100);
			const r = await frappe.call({
				method: 'generate_item.generate_item.page.financial_dashboard.financial_dashboard.get_overview',
				args: {
					company: this.company,
					fiscal_year: this.fiscal_year,
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
				this.render_pending_orders();
				this.render_ar_ageing();
				this.render_ap_ageing();

				// Load multi-unit series for Items 2 & 3 with the selected fiscal year
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
		this.currency = meta.currency || 'INR';
		this.fiscal_year = meta.fiscal_year;
		this.fy_start = meta.fy_start;
		this.fy_end = meta.fy_end;

		if (meta.all_fiscal_years && meta.all_fiscal_years.length > 0) {
			this.availableFYs = meta.all_fiscal_years;
		}

		// Dynamically render FY pills based on ERPNext records
		this.render_fy_pills();
	}

	render_kpis() {
		const kpi = this.data.kpis;

		// Card 1: Revenue
		this.wrapper.find('#kpi-revenue').text(this.format_compact(kpi.net_revenue));
		const revTrend = this.wrapper.find('#kpi-revenue-trend');
		revTrend.html(`
			<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="${kpi.revenue_delta >= 0 ? 'M5 10l7-7m0 0l7 7m-7-7v18' : 'M19 14l-7 7m0 0l-7-7m7 7V3'}"/></svg>
			${kpi.revenue_delta >= 0 ? '+' : ''}${kpi.revenue_delta}%
		`);
		revTrend.toggleClass('negative', kpi.revenue_delta < 0);
		this.wrapper.find('#kpi-revenue-cap').text(
			kpi.revenue_target > 0
				? `YTD performance vs target (${this.format_compact(kpi.revenue_target)})`
				: __('YTD performance vs previous year')
		);

		// Card 2: Operating Margin
		this.wrapper.find('#kpi-margin').text(`${kpi.operating_margin}%`);
		const marginTrend = this.wrapper.find('#kpi-margin-trend');
		marginTrend.html(`
			<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="${kpi.margin_delta >= 0 ? 'M5 10l7-7m0 0l7 7m-7-7v18' : 'M19 14l-7 7m0 0l-7-7m7 7V3'}"/></svg>
			${kpi.margin_delta >= 0 ? '+' : ''}${kpi.margin_delta} pts
		`);
		marginTrend.toggleClass('negative', kpi.margin_delta < 0);
		this.wrapper.find('#kpi-margin-cap').text(
			kpi.margin_target > 0
				? `Avg monthly margin (Target: ${kpi.margin_target}%)`
				: __('Avg monthly margin')
		);

		// Card 3: Orders Booked
		this.wrapper.find('#kpi-orders').text(kpi.orders_booked_count.toLocaleString());
		const ordersTrend = this.wrapper.find('#kpi-orders-trend');
		ordersTrend.html(`
			<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="${kpi.orders_delta >= 0 ? 'M5 10l7-7m0 0l7 7m-7-7v18' : 'M19 14l-7 7m0 0l-7-7m7 7V3'}"/></svg>
			${kpi.orders_delta >= 0 ? '+' : ''}${kpi.orders_delta}%
		`);
		ordersTrend.toggleClass('negative', kpi.orders_delta < 0);
		this.wrapper.find('#kpi-orders-cap').text(`Book-to-bill ratio: ${kpi.book_to_bill}`);

		// Card 4: Pending Backlog
		this.wrapper.find('#kpi-pending').text(`${kpi.pending_backlog_count} Units`);
		this.wrapper.find('#kpi-pending-value').text(`${this.format_compact(kpi.pending_backlog_value)} Value`);
		this.wrapper.find('#kpi-pending-cap').text(`${kpi.sla_percentage}% on SLA delivery timeline`);
	}

	render_item1_chart() {
		const rm = this.data.revenue_margin;
		let labels = rm.labels || [];
		let rev = rm.revenue_series || [];
		let margin = rm.margin_series || [];

		// Normalize to millions for display
		let revMillions = rev.map(v => flt((v / 1000000).toFixed(2)));

		if (this.item1Filter === 'h1') {
			labels = labels.slice(0, 6);
			revMillions = revMillions.slice(0, 6);
			margin = margin.slice(0, 6);
		} else if (this.item1Filter === 'h2') {
			labels = labels.slice(6, 12);
			revMillions = revMillions.slice(6, 12);
			margin = margin.slice(6, 12);
		}

		// Insights tiles
		const ins = rm.insights || {};
		this.wrapper.find('#rev-peak').text(`${ins.peak_revenue_month} (${this.format_compact(ins.peak_revenue_value)})`);
		this.wrapper.find('#margin-peak').text(`${ins.best_margin_month} (${ins.best_margin_value}%)`);
		this.wrapper.find('#rev-run-rate').text(`${this.format_compact(ins.avg_monthly_run_rate)} / Mo`);
		this.wrapper.find('#margin-spread').text(`${ins.margin_spread}% Spread`);

		const ctx = document.getElementById('revenueMarginChart');
		if (!ctx || !window.Chart) return;

		if (this.charts.revMargin) {
			this.charts.revMargin.data.labels = labels;
			this.charts.revMargin.data.datasets[0].data = revMillions;
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
						label: 'Revenue ($M)',
						data: revMillions,
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
							label: (c) => c.dataset.yAxisID === 'yRevenue' ? `Revenue: $${c.raw}M` : `Op. Margin: ${c.raw}%`,
						},
					},
				},
				scales: {
					x: { grid: { display: false } },
					yRevenue: {
						type: 'linear',
						position: 'left',
						title: { display: true, text: 'Revenue ($ Millions)', font: { size: 10 } },
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
		const cacheKey = `${kind}_${grain}_${this.fiscal_year}_${this.unit_dimension}`;
		let resData = this.unitCache[cacheKey];

		if (!resData) {
			try {
				const r = await frappe.call({
					method: 'generate_item.generate_item.page.financial_dashboard.financial_dashboard.get_unit_series',
					args: {
						company: this.company,
						fiscal_year: this.fiscal_year,
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

		// Normalize numbers to Millions for charting
		const formattedDatasets = (resData.datasets || []).map(ds => ({
			...ds,
			data: (ds.data || []).map(v => flt((v / 1000000).toFixed(2))),
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
		this.wrapper.find('#salesTopUnit').text(resData.top_unit || 'Unit Alpha');
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
					tooltip: { callbacks: { label: (c) => `${c.dataset.label}: $${c.raw}M` } },
				},
				scales: {
					x: { stacked: this.salesStacked, grid: { display: false } },
					y: {
						stacked: this.salesStacked,
						title: { display: true, text: 'Sales ($M)', font: { size: 9.5 } },
						grid: { color: 'rgba(226, 232, 240, 0.6)' },
					},
				},
			},
		});
	}

	render_purchases_chart(resData, datasets) {
		this.wrapper.find('#purchasesTopUnit').text(resData.top_unit || 'Unit Gamma');
		this.wrapper.find('#purchasesTopCost').text(`${this.format_compact(resData.grand_total)} YTD Cost`);

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
					tooltip: { callbacks: { label: (c) => `${c.dataset.label}: $${c.raw}M` } },
				},
				scales: {
					x: { stacked: this.purchasesStacked, grid: { display: false } },
					y: {
						stacked: this.purchasesStacked,
						title: { display: true, text: 'Purchases ($M)', font: { size: 9.5 } },
						grid: { color: 'rgba(226, 232, 240, 0.6)' },
					},
				},
			},
		});
	}

	render_orders_chart() {
		const ord = this.data.orders_monthly;
		this.wrapper.find('#orders-total-booked').text(`${ord.total_orders_count} Orders`);
		this.wrapper.find('#orders-monthly-mean').text(`${ord.monthly_mean} Orders/Mo`);
		this.wrapper.find('#orders-target-attain').text(`${ord.target_attainment}%`);

		const ctx = document.getElementById('ordersBookedChart');
		if (!ctx || !window.Chart) return;

		if (this.charts.orders) {
			this.charts.orders.data.labels = ord.labels;
			this.charts.orders.data.datasets[0].data = ord.count_series;
			this.charts.orders.data.datasets[1].data = ord.target_series;
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
					{
						type: 'line',
						label: 'Monthly Target Quota',
						data: ord.target_series,
						borderColor: '#64748b',
						borderWidth: 2,
						borderDash: [5, 4],
						pointRadius: 0,
						fill: false,
					},
				],
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				plugins: { legend: { display: false } },
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

	render_pending_orders() {
		const pnd = this.data.pending_orders;
		this.wrapper.find('#pendingUnitsBadge').text(`${pnd.total_count} Units`);
		this.wrapper.find('#pendingCenterNum').text(pnd.total_count);

		const stages = pnd.stages || {};
		const labels = Object.keys(stages);
		const counts = labels.map(k => stages[k].count);
		const colors = labels.map(k => stages[k].color);

		const me = this;
		const container = this.wrapper.find('#pendingStagesList').empty();

		labels.forEach(st => {
			const item = stages[st];
			const row = $(`
				<div style="display: flex; justify-content: space-between; align-items: center; padding: 0.25rem 0.5rem; border-radius: 4px; background: #f8fafc;">
					<span style="display: flex; align-items: center; gap: 0.4rem; color: #334155;">
						<span style="width: 8px; height: 8px; border-radius: 50%; background: ${item.color};"></span> ${__(st)}
					</span>
					<span style="font-weight: 600; ${st === 'Payment Hold' ? 'color: #ef4444;' : ''}">
						${item.count} <span style="color: #94a3b8; font-weight: 400;">(${me.format_compact(item.value)})</span>
					</span>
				</div>
			`);
			container.append(row);
		});

		const ctx = document.getElementById('pendingOrdersChart');
		if (!ctx || !window.Chart) return;

		if (this.charts.pending) {
			this.charts.pending.data.labels = labels;
			this.charts.pending.data.datasets[0].data = counts;
			this.charts.pending.data.datasets[0].backgroundColor = colors;
			this.charts.pending.update();
			return;
		}

		this.charts.pending = new Chart(ctx, {
			type: 'doughnut',
			data: {
				labels: labels,
				datasets: [{
					data: counts,
					backgroundColor: colors,
					borderWidth: 2,
					borderColor: '#ffffff',
					hoverOffset: 4,
				}],
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				cutout: '72%',
				plugins: { legend: { display: false } },
			},
		});
	}

	render_ar_ageing() {
		const ar = this.data.ar_ageing;
		this.wrapper.find('#arSubtitle').html(
			`Total Receivables: <strong style="color: #0f172a;">${this.format_compact(ar.total_outstanding)}</strong> • DSO: ${ar.dso_days} Days`
		);
		this.wrapper.find('#arCurrentBadge').text(`Current: ${ar.current_share}%`);

		const me = this;
		const tbody = this.wrapper.find('#arTable tbody').empty();
		(ar.buckets || []).forEach(b => {
			const tr = $(`
				<tr style="cursor: pointer;" title="${__('Click to open Accounts Receivable report')}">
					<td>${b.bucket}</td>
					<td class="fd-num-cell" style="${b.risk === 'High Alert' ? 'color: #dc2626;' : ''}">${me.format_compact(b.amount)}</td>
					<td style="${b.risk === 'High Alert' ? 'color: #dc2626; font-weight: 600;' : ''}">${b.share}%</td>
					<td><span class="fd-risk-badge ${b.risk_class || 'fd-risk-normal'}">${b.risk}</span></td>
				</tr>
			`);
			tr.on('click', () => {
				me.drilldown('query-report', 'Accounts Receivable', 'ar');
			});
			tbody.append(tr);
		});

		const chartMillions = (ar.chart_data || []).map(v => flt((v / 1000000).toFixed(2)));

		const ctx = document.getElementById('arAgeingChart');
		if (!ctx || !window.Chart) return;

		if (this.charts.ar) {
			this.charts.ar.data.datasets[0].data = chartMillions;
			this.charts.ar.update();
			return;
		}

		this.charts.ar = new Chart(ctx, {
			type: 'bar',
			data: {
				labels: ['< 30d', '31-60d', '61-90d', '> 90d'],
				datasets: [{
					data: chartMillions,
					backgroundColor: ['#10b981', '#0284c7', '#f59e0b', '#ef4444'],
					borderRadius: 4,
				}],
			},
			options: {
				indexAxis: 'y',
				responsive: true,
				maintainAspectRatio: false,
				plugins: { legend: { display: false } },
				scales: {
					x: { title: { display: true, text: '$ Millions', font: { size: 9.5 } }, grid: { color: 'rgba(226, 232, 240, 0.6)' } },
					y: { grid: { display: false } },
				},
			},
		});
	}

	render_ap_ageing() {
		const ap = this.data.ap_ageing;
		this.wrapper.find('#apSubtitle').html(
			`Total Payables: <strong style="color: #0f172a;">${this.format_compact(ap.total_outstanding)}</strong> • DPO: ${ap.dpo_days} Days`
		);
		this.wrapper.find('#apDueBadge').text(`Due Soon: ${ap.due_soon_share}%`);

		const me = this;
		const tbody = this.wrapper.find('#apTable tbody').empty();
		(ap.buckets || []).forEach(b => {
			const isCritical = b.bucket.includes('> 90');
			const tr = $(`
				<tr style="cursor: pointer;" title="${__('Click to open Accounts Payable report')}">
					<td>${b.bucket}</td>
					<td class="fd-num-cell" style="${isCritical ? 'color: #dc2626;' : ''}">${me.format_compact(b.amount)}</td>
					<td style="${isCritical ? 'color: #dc2626; font-weight: 600;' : ''}">${b.share}%</td>
					<td style="${isCritical ? '' : 'color: #64748b;'}">
						${isCritical ? '<span class="fd-risk-badge fd-risk-high">Audit Dispute</span>' : b.action}
					</td>
				</tr>
			`);
			tr.on('click', () => {
				me.drilldown('query-report', 'Accounts Payable', 'ap');
			});
			tbody.append(tr);
		});

		const chartMillions = (ap.chart_data || []).map(v => flt((v / 1000000).toFixed(2)));

		const ctx = document.getElementById('apAgeingChart');
		if (!ctx || !window.Chart) return;

		if (this.charts.ap) {
			this.charts.ap.data.datasets[0].data = chartMillions;
			this.charts.ap.update();
			return;
		}

		this.charts.ap = new Chart(ctx, {
			type: 'bar',
			data: {
				labels: ['< 30d', '31-60d', '61-90d', '> 90d'],
				datasets: [{
					data: chartMillions,
					backgroundColor: ['#10b981', '#0284c7', '#f59e0b', '#ef4444'],
					borderRadius: 4,
				}],
			},
			options: {
				indexAxis: 'y',
				responsive: true,
				maintainAspectRatio: false,
				plugins: { legend: { display: false } },
				scales: {
					x: { title: { display: true, text: '$ Millions', font: { size: 9.5 } }, grid: { color: 'rgba(226, 232, 240, 0.6)' } },
					y: { grid: { display: false } },
				},
			},
		});
	}
}