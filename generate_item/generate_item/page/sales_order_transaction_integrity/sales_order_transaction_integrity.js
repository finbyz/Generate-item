// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt

const SOTI_ICONS = {
	shield: `<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>`,
	fileText: `<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/>`,
	alertTriangle: `<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>`,
	layers: `<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>`,
	edit: `<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>`,
	refresh: `<polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>`,
	download: `<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>`,
	chevronsDown: `<polyline points="7 13 12 18 17 13"/><polyline points="7 6 12 11 17 6"/>`,
	chevronsUp: `<polyline points="17 11 12 6 7 11"/><polyline points="17 18 12 13 7 18"/>`,
	chevronDown: `<polyline points="6 9 12 15 18 9"/>`,
	chevronRight: `<polyline points="9 18 15 12 9 6"/>`,
	chevronLeft: `<polyline points="15 18 9 12 15 6"/>`,
	chevronsLeft: `<polyline points="11 17 6 12 11 7"/><polyline points="18 17 13 12 18 7"/>`,
	chevronsRight: `<polyline points="13 17 18 12 13 7"/><polyline points="6 17 11 12 6 7"/>`,
	search: `<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>`,
	sliders: `<line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/>`,
	undo: `<path d="M3 7v6h6"/><path d="M21 17a9 9 0 0 0-9-9 9 9 0 0 0-6 2.3L3 13"/>`,
	externalLink: `<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>`,
	checkCircle: `<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>`,
	truck: `<rect x="1" y="3" width="15" height="13"/><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/>`,
	fileSpreadsheet: `<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><path d="M8 13h8"/><path d="M8 17h8"/><path d="M10 9h4"/>`,
	user: `<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>`,
	clock: `<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>`,
	check: `<polyline points="20 6 9 17 4 12"/>`,
	spinner: `<line x1="12" y1="2" x2="12" y2="6"/><line x1="12" y1="18" x2="12" y2="22"/><line x1="4.93" y1="4.93" x2="7.76" y2="7.76"/><line x1="16.24" y1="16.24" x2="19.07" y2="19.07"/><line x1="2" y1="12" x2="6" y2="12"/><line x1="18" y1="12" x2="22" y2="12"/><line x1="4.93" y1="19.07" x2="7.76" y2="16.24"/><line x1="16.24" y1="7.76" x2="19.07" y2="4.93"/>`,
};

function soti_icon(name, cls = "") {
	const inner = SOTI_ICONS[name] || SOTI_ICONS.fileText;
	return `<svg class="soti-icon ${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${inner}</svg>`;
}

const SOTI_DATE_PRESETS = [
	"All Time",
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
];

frappe.pages["sales-order-transaction-integrity"].on_page_load = function (wrapper) {
	frappe.sales_order_transaction_integrity = new SalesOrderTransactionIntegrityReport(wrapper);
};

class SalesOrderTransactionIntegrityReport {
	constructor(wrapper) {
		this.wrapper = wrapper;
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __("Sales Order Transaction Integrity"),
			single_column: true,
		});

		this.filters = {
			period: "All Time",
			from_date: "",
			to_date: "",
			branch: "",
			customer: "",
			sales_order: "",
			transaction_type: "",
			transaction_status: "",
		};

		this.controls = {};
		this.raw_data = [];
		this.summary = {};
		this.pagination = {
			page: 1,
			page_length: 25,
			total_records: 0,
			total_pages: 1,
		};
		this.search_query = "";
		this.sort_field = "transaction_date";
		this.sort_order = "desc";
		this.expanded_sos = new Set();
		this.filter_meta = {};
		this.active_kpi = "with-open";
		this.auto_expand_on_render = false;
		this.filter_debounce_timer = null;
		this.is_programmatic_change = false;
		this.request_counter = 0;

		this.render_page_actions();
		this.render_shell();
		this.is_programmatic_change = true;
		this.init_filter_controls();
		this.is_programmatic_change = false;
		this.bind_events();
		this.load_data();
	}

	render_page_actions() {
		this.page.clear_actions();

		// Single clean page action in Frappe Desk top-bar
		this.page.add_button(__("Refresh"), () => {
			this.load_data();
		}, { icon: "refresh", btn_class: "btn-secondary" });
	}

	render_shell() {
		const html = `
			<div class="soti-wrapper">
				<!-- Hero Banner (Cleaned up, no duplicate buttons) -->
				<div class="soti-hero">
					<div class="soti-hero-left">
						<div class="soti-hero-icon">
							${soti_icon("shield")}
						</div>
						<div class="soti-hero-title-group">
							<h1>
								${__("Sales Order Transaction Integrity Report")}
								<span class="soti-hero-badge">
									<span class="soti-live-dot"></span>
									${__("Audit Active")}
								</span>
							</h1>
							<p>${__("Monitors completed Sales Orders that still have open or draft linked transactions across the fulfillment cycle.")}</p>
						</div>
					</div>
				</div>

				<!-- 4 KPI Summary Cards with Crisp Inline SVG Icons -->
				<div class="soti-cards-grid">
					<!-- Card 1: Completed SOs Checked -->
					<div class="soti-card card-checked" data-kpi="checked" role="button" tabindex="0" title="${__("Click to show all checked Sales Orders")}">
						<div class="soti-card-header">
							<span class="soti-card-title">${__("Completed SO Checked")}</span>
							<div class="soti-card-icon">
								${soti_icon("fileText")}
							</div>
						</div>
						<div class="soti-card-body">
							<span class="soti-card-value" id="soti-kpi-checked">0</span>
						</div>
						<div class="soti-card-subtext">
							<span>${__("Orders evaluated under filters")}</span>
						</div>
					</div>

					<!-- Card 2: SOs With Open Transactions -->
					<div class="soti-card card-with-open" data-kpi="with-open" role="button" tabindex="0" title="${__("Click to show Sales Orders with open transactions")}">
						<div class="soti-card-header">
							<span class="soti-card-title">${__("SO With Open Transactions")}</span>
							<div class="soti-card-icon">
								${soti_icon("alertTriangle")}
							</div>
						</div>
						<div class="soti-card-body">
							<span class="soti-card-value" id="soti-kpi-with-open">0</span>
							<span class="soti-card-badge" id="soti-kpi-with-open-pct">0%</span>
						</div>
						<div class="soti-card-subtext">
							<span>${__("Require fulfillment closure")}</span>
						</div>
					</div>

					<!-- Card 3: Total Open Transactions -->
					<div class="soti-card card-total-open" data-kpi="total-open" role="button" tabindex="0" title="${__("Click to expand and view all open transactions")}">
						<div class="soti-card-header">
							<span class="soti-card-title">${__("Total Open Transactions")}</span>
							<div class="soti-card-icon">
								${soti_icon("layers")}
							</div>
						</div>
						<div class="soti-card-body">
							<span class="soti-card-value" id="soti-kpi-total-open">0</span>
						</div>
						<div class="soti-card-subtext">
							<span>${__("Across all linked DocTypes")}</span>
						</div>
					</div>

					<!-- Card 4: Open Draft Transactions -->
					<div class="soti-card card-draft" data-kpi="draft" role="button" tabindex="0" title="${__("Click to filter by Open Draft transactions")}">
						<div class="soti-card-header">
							<span class="soti-card-title">${__("Open Draft Transactions")}</span>
							<div class="soti-card-icon">
								${soti_icon("edit")}
							</div>
						</div>
						<div class="soti-card-body">
							<span class="soti-card-value" id="soti-kpi-draft">0</span>
							<span class="soti-card-badge" id="soti-kpi-draft-pct">0%</span>
						</div>
						<div class="soti-card-subtext">
							<span>${__("Unsubmitted draft records")}</span>
						</div>
					</div>
				</div>

				<!-- Filter Card (with Sales Team KPI Dashboard period presets) -->
				<div class="soti-filter-card">
					<div class="soti-filter-header">
						<div class="soti-filter-title">
							${soti_icon("sliders")}
							<span>${__("Report Filters")}</span>
						</div>
						<div class="soti-filter-actions">
							<button class="btn btn-default btn-xs" id="soti-reset-filters-btn">
								${soti_icon("undo")} ${__("Reset")}
							</button>
							<button class="btn btn-primary btn-xs" id="soti-apply-filters-btn">
								${soti_icon("sliders")} ${__("Apply Filters")}
							</button>
						</div>
					</div>
					<div class="soti-filter-grid">
						<div class="soti-filter-group">
							<span class="soti-filter-label">${__("Period")}</span>
							<div class="soti-control-period"></div>
						</div>
						<div class="soti-filter-group">
							<span class="soti-filter-label">${__("From Date")}</span>
							<div class="soti-control-from-date"></div>
						</div>
						<div class="soti-filter-group">
							<span class="soti-filter-label">${__("To Date")}</span>
							<div class="soti-control-to-date"></div>
						</div>
						<div class="soti-filter-group">
							<span class="soti-filter-label">${__("Branch")}</span>
							<div class="soti-control-branch"></div>
						</div>
						<div class="soti-filter-group">
							<span class="soti-filter-label">${__("Customer")}</span>
							<div class="soti-control-customer"></div>
						</div>
						<div class="soti-filter-group">
							<span class="soti-filter-label">${__("Sales Order")}</span>
							<div class="soti-control-sales-order"></div>
						</div>
						<div class="soti-filter-group">
							<span class="soti-filter-label">${__("Transaction Type")}</span>
							<div class="soti-control-tx-type"></div>
						</div>
						<div class="soti-filter-group">
							<span class="soti-filter-label">${__("Transaction Status")}</span>
							<div class="soti-control-tx-status"></div>
						</div>
					</div>
				</div>

				<!-- Action Toolbar (Moved Above Table View and Below Filter Section) -->
				<div class="soti-action-toolbar">
					<div class="soti-toolbar-left">
						<button class="soti-btn soti-btn-default" id="soti-expand-all-btn" title="${__("Expand all Sales Orders")}">
							${soti_icon("chevronsDown")} ${__("Expand All")}
						</button>
						<button class="soti-btn soti-btn-default" id="soti-collapse-all-btn" title="${__("Collapse all Sales Orders")}">
							${soti_icon("chevronsUp")} ${__("Collapse All")}
						</button>
						<button class="soti-btn soti-btn-excel" id="soti-export-excel-btn" title="${__("Export all matching transactions to Excel/CSV")}">
							${soti_icon("fileSpreadsheet")} ${__("Export to Excel")}
						</button>
					</div>
					<div class="soti-toolbar-right">
						<div class="soti-table-info">
							<span id="soti-table-counts-label">${__("Loading records...")}</span>
						</div>
						<div class="soti-search-box">
							<span class="soti-search-icon">${soti_icon("search")}</span>
							<input type="text" id="soti-search-input" placeholder="${__("Search by SO ID, Customer, Transaction ID, Status...")}" />
						</div>
						<div class="soti-page-size-wrap">
							<span style="font-size: 11px; color: var(--soti-muted); margin-right: 6px;">${__("Rows:")}</span>
							<select id="soti-page-size-select" class="form-control input-xs" style="width: auto; display: inline-block;">
								<option value="10">10</option>
								<option value="25" selected>25</option>
								<option value="50">50</option>
								<option value="100">100</option>
							</select>
						</div>
					</div>
				</div>

				<!-- Main Data Table Card -->
				<div class="soti-table-card">
					<div id="soti-table-container">
						<!-- Content rendered dynamically -->
					</div>
					<!-- Pagination Bar with Crisp Arrow Buttons -->
					<div class="soti-pagination" id="soti-pagination-bar" style="display: none;">
						<div class="soti-page-info">
							<span id="soti-pagination-text">Showing 0 of 0</span>
						</div>
						<div class="soti-page-btns">
							<button class="soti-page-btn" id="soti-btn-first" title="${__("First Page")}">
								${soti_icon("chevronsLeft")}
							</button>
							<button class="soti-page-btn" id="soti-btn-prev" title="${__("Previous Page")}">
								${soti_icon("chevronLeft")}
							</button>
							<span class="soti-page-indicator" id="soti-page-number-display">Page 1 of 1</span>
							<button class="soti-page-btn" id="soti-btn-next" title="${__("Next Page")}">
								${soti_icon("chevronRight")}
							</button>
							<button class="soti-page-btn" id="soti-btn-last" title="${__("Last Page")}">
								${soti_icon("chevronsRight")}
							</button>
						</div>
					</div>
				</div>
			</div>
		`;

		$(this.page.body).html(html);
	}

	init_filter_controls() {
		const body = $(this.page.body);

		// 1. Period Preset (Matching Sales Team KPI Dashboard)
		this.controls.period = frappe.ui.form.make_control({
			parent: body.find(".soti-control-period"),
			df: {
				fieldtype: "Select",
				options: SOTI_DATE_PRESETS,
				default: this.filters.period,
				input_class: "input-xs",
				change: () => {
					if (this.is_programmatic_change) return;
					const val = this.controls.period.get_value();
					this.filters.period = val;
					if (val !== "Custom") {
						const dates = this.resolve_preset(val);
						if (dates) {
							this.is_programmatic_change = true;
							try {
								this.controls.from_date.set_value(dates.from_date || "");
								this.controls.to_date.set_value(dates.to_date || "");
								this.filters.from_date = dates.from_date || "";
								this.filters.to_date = dates.to_date || "";
							} finally {
								this.is_programmatic_change = false;
							}
						}
					}
					this.on_filter_change();
				},
			},
			render_input: true,
		});

		// 2. From Date
		this.controls.from_date = frappe.ui.form.make_control({
			parent: body.find(".soti-control-from-date"),
			df: {
				fieldtype: "Date",
				default: this.filters.from_date,
				input_class: "input-xs",
				change: () => {
					if (this.is_programmatic_change) return;
					const val = this.controls.from_date.get_value() || "";
					if (this.filters.from_date === val) return;
					this.filters.from_date = val;
					if (this.filters.period !== "Custom") {
						this.is_programmatic_change = true;
						try {
							this.controls.period.set_value("Custom");
							this.filters.period = "Custom";
						} finally {
							this.is_programmatic_change = false;
						}
					}
					this.on_filter_change();
				},
			},
			render_input: true,
		});

		// 3. To Date
		this.controls.to_date = frappe.ui.form.make_control({
			parent: body.find(".soti-control-to-date"),
			df: {
				fieldtype: "Date",
				default: this.filters.to_date,
				input_class: "input-xs",
				change: () => {
					if (this.is_programmatic_change) return;
					const val = this.controls.to_date.get_value() || "";
					if (this.filters.to_date === val) return;
					this.filters.to_date = val;
					if (this.filters.period !== "Custom") {
						this.is_programmatic_change = true;
						try {
							this.controls.period.set_value("Custom");
							this.filters.period = "Custom";
						} finally {
							this.is_programmatic_change = false;
						}
					}
					this.on_filter_change();
				},
			},
			render_input: true,
		});

		// 4. Branch
		this.controls.branch = frappe.ui.form.make_control({
			parent: body.find(".soti-control-branch"),
			df: {
				fieldtype: "Link",
				options: "Branch",
				placeholder: __("All Branches"),
				input_class: "input-xs",
				change: () => {
					if (this.is_programmatic_change) return;
					const val = this.controls.branch.get_value() || "";
					if (this.filters.branch === val) return;
					this.filters.branch = val;
					this.on_filter_change();
				},
			},
			render_input: true,
		});

		// 5. Customer
		this.controls.customer = frappe.ui.form.make_control({
			parent: body.find(".soti-control-customer"),
			df: {
				fieldtype: "Link",
				options: "Customer",
				placeholder: __("Select Customer"),
				input_class: "input-xs",
				change: () => {
					if (this.is_programmatic_change) return;
					const val = this.controls.customer.get_value() || "";
					if (this.filters.customer === val) return;
					this.filters.customer = val;
					this.on_filter_change();
				},
			},
			render_input: true,
		});

		// 6. Sales Order
		this.controls.sales_order = frappe.ui.form.make_control({
			parent: body.find(".soti-control-sales-order"),
			df: {
				fieldtype: "Link",
				options: "Sales Order",
				placeholder: __("Select Sales Order"),
				input_class: "input-xs",
				get_query: () => {
					return {
						filters: {
							status: "Completed",
							docstatus: 1,
						},
					};
				},
				change: () => {
					if (this.is_programmatic_change) return;
					const val = this.controls.sales_order.get_value() || "";
					if (this.filters.sales_order === val) return;
					this.filters.sales_order = val;
					this.on_filter_change();
				},
			},
			render_input: true,
		});

		// 7. Transaction Type
		this.controls.transaction_type = frappe.ui.form.make_control({
			parent: body.find(".soti-control-tx-type"),
			df: {
				fieldtype: "Select",
				options: [
					"",
					"Delivery Note",
					"Sales Invoice",
					"Payment Entry",
					"Work Order",
					"Production Plan",
					"Material Request",
					"Purchase Order",
					"Purchase Receipt",
					"Purchase Invoice",
					"Stock Entry",
					"Subcontracting Order",
					"Subcontracting Receipt",
					"Pick List",
					"Order Modification Request",
					"BOM",
					"Bom Modification Request",
					"Valve Painting",
					// "Valve Painting Item",
					"Valve Testing",
					// "Valve Testing Item",
					"Valve Assembly",
					// "Assembly Item Serial No",
					"Proforma Invoice",
					// "Proforma Invoice Item",
				],
				placeholder: __("All Transaction Types"),
				input_class: "input-xs",
				change: () => {
					if (this.is_programmatic_change) return;
					const val = this.controls.transaction_type.get_value() || "";
					if (this.filters.transaction_type === val) return;
					this.filters.transaction_type = val;
					if (this.active_kpi === "checked" && val) {
						this.active_kpi = "with-open";
					}
					this.on_filter_change();
				},
			},
			render_input: true,
		});

		// 8. Transaction Status
		this.controls.transaction_status = frappe.ui.form.make_control({
			parent: body.find(".soti-control-tx-status"),
			df: {
				fieldtype: "Select",
				options: [
					"",
					"Draft",
					"To Bill",
					"Partly Billed",
					"Not Started",
					"In Process",
					"Submitted",
					"Material Requested",
					"Pending",
					"Ordered",
					"Partially Ordered",
					"Partially Received",
					"To Receive and Bill",
					"To Receive",
					"Open",
					"Material Transferred",
					"Partial Material Transferred",
				],
				placeholder: __("All Statuses"),
				input_class: "input-xs",
				change: () => {
					if (this.is_programmatic_change) return;
					const val = this.controls.transaction_status.get_value() || "";
					if (this.filters.transaction_status === val) return;
					this.filters.transaction_status = val;
					if (val === "Draft") {
						this.active_kpi = "draft";
					} else if (this.active_kpi === "checked" && val) {
						this.active_kpi = "with-open";
					}
					this.on_filter_change();
				},
			},
			render_input: true,
		});
	}

	on_filter_change(immediate = false) {
		if (this.is_programmatic_change) return;

		clearTimeout(this.filter_debounce_timer);
		this.pagination.page = 1;

		if (immediate) {
			this.load_data();
			return;
		}

		// Automatically refresh dashboard data with a safe debounce (200ms)
		// Coalesces rapid filter changes and prevents duplicate API calls
		this.filter_debounce_timer = setTimeout(() => {
			this.load_data();
		}, 200);
	}

	resolve_preset(preset) {
		const today = frappe.datetime.get_today();
		const todayDate = frappe.datetime.str_to_obj(today);

		const fmt = (d) => frappe.datetime.obj_to_str(d);
		const add = (d, n) => {
			const x = new Date(d);
			x.setDate(x.getDate() + n);
			return x;
		};
		const subMonths = (d, n) => {
			const x = new Date(d);
			x.setMonth(x.getMonth() - n);
			return x;
		};
		const dow = todayDate.getDay();
		const daysToMon = dow === 0 ? -6 : 1 - dow;

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
			case "All Time":
				return { from_date: "", to_date: "" };
			case "Custom":
			default:
				return null;
		}
	}

	bind_events() {
		const body = $(this.page.body);

		// Action Toolbar buttons
		body.on("click", "#soti-expand-all-btn", () => {
			this.toggle_expand_all(true);
		});

		body.on("click", "#soti-collapse-all-btn", () => {
			this.toggle_expand_all(false);
		});

		body.on("click", "#soti-export-excel-btn", () => {
			this.export_data();
		});

		// Filter buttons
		body.on("click", "#soti-apply-filters-btn", () => {
			this.on_filter_change(true);
		});

		body.on("click", "#soti-reset-filters-btn", () => {
			this.reset_filters();
		});

		// Search input (debounced)
		let searchTimer = null;
		body.on("input", "#soti-search-input", (e) => {
			clearTimeout(searchTimer);
			searchTimer = setTimeout(() => {
				this.search_query = $(e.target).val().trim();
				this.pagination.page = 1;
				this.load_data();
			}, 300);
		});

		// Page size change
		body.on("change", "#soti-page-size-select", (e) => {
			this.pagination.page_length = parseInt($(e.target).val(), 10) || 25;
			this.pagination.page = 1;
			this.load_data();
		});

		// Pagination button clicks
		body.on("click", "#soti-btn-first", () => {
			if (this.pagination.page > 1) {
				this.pagination.page = 1;
				this.load_data(true);
			}
		});

		body.on("click", "#soti-btn-prev", () => {
			if (this.pagination.page > 1) {
				this.pagination.page--;
				this.load_data(true);
			}
		});

		body.on("click", "#soti-btn-next", () => {
			if (this.pagination.page < this.pagination.total_pages) {
				this.pagination.page++;
				this.load_data(true);
			}
		});

		body.on("click", "#soti-btn-last", () => {
			if (this.pagination.page < this.pagination.total_pages) {
				this.pagination.page = this.pagination.total_pages;
				this.load_data(true);
			}
		});

		// Row Expand/Collapse Click
		body.on("click", ".soti-row-parent", (e) => {
			if ($(e.target).closest("a, button").length) return;
			const so_name = $(e.currentTarget).data("sales-order");
			this.toggle_expand_row(so_name);
		});

		body.on("click", ".soti-expand-btn", (e) => {
			e.stopPropagation();
			const so_name = $(e.currentTarget).data("sales-order");
			this.toggle_expand_row(so_name);
		});

		// KPI Summary Cards click & keyboard navigation
		body.on("click", ".soti-card", (e) => {
			const kpi = $(e.currentTarget).data("kpi");
			if (!kpi) return;
			this.handle_kpi_click(kpi);
		});

		body.on("keydown", ".soti-card", (e) => {
			if (e.key === "Enter" || e.key === " ") {
				e.preventDefault();
				const kpi = $(e.currentTarget).data("kpi");
				if (!kpi) return;
				this.handle_kpi_click(kpi);
			}
		});
	}

	handle_kpi_click(kpi) {
		this.active_kpi = kpi;

		if (kpi === "draft") {
			// Toggle draft filter
			if (this.filters.transaction_status === "Draft") {
				this.is_programmatic_change = true;
				try {
					this.controls.transaction_status.set_value("");
					this.filters.transaction_status = "";
				} finally {
					this.is_programmatic_change = false;
				}
				this.active_kpi = "with-open";
				this.auto_expand_on_render = false;
			} else {
				this.is_programmatic_change = true;
				try {
					this.controls.transaction_status.set_value("Draft");
					this.filters.transaction_status = "Draft";
				} finally {
					this.is_programmatic_change = false;
				}
				this.auto_expand_on_render = true;
			}
		} else if (kpi === "total-open") {
			// Clear status filter if set and expand all rows to show open transactions
			if (this.filters.transaction_status) {
				this.is_programmatic_change = true;
				try {
					this.controls.transaction_status.set_value("");
					this.filters.transaction_status = "";
				} finally {
					this.is_programmatic_change = false;
				}
			}
			this.auto_expand_on_render = true;
		} else if (kpi === "checked") {
			// Clear transaction status and type filters to show all checked completed SOs
			if (this.filters.transaction_status) {
				this.is_programmatic_change = true;
				try {
					this.controls.transaction_status.set_value("");
					this.filters.transaction_status = "";
				} finally {
					this.is_programmatic_change = false;
				}
			}
			if (this.filters.transaction_type) {
				this.is_programmatic_change = true;
				try {
					this.controls.transaction_type.set_value("");
					this.filters.transaction_type = "";
				} finally {
					this.is_programmatic_change = false;
				}
			}
			this.auto_expand_on_render = false;
		} else if (kpi === "with-open") {
			// Reset status filter to show SOs with open transactions
			if (this.filters.transaction_status) {
				this.is_programmatic_change = true;
				try {
					this.controls.transaction_status.set_value("");
					this.filters.transaction_status = "";
				} finally {
					this.is_programmatic_change = false;
				}
			}
			this.auto_expand_on_render = false;
		}

		clearTimeout(this.filter_debounce_timer);
		this.pagination.page = 1;
		this.load_data(true);
	}

	reset_filters() {
		clearTimeout(this.filter_debounce_timer);
		this.is_programmatic_change = true;

		this.filters = {
			period: "All Time",
			from_date: "",
			to_date: "",
			branch: "",
			customer: "",
			sales_order: "",
			transaction_type: "",
			transaction_status: "",
		};

		try {
			this.controls.period.set_value("All Time");
			this.controls.from_date.set_value("");
			this.controls.to_date.set_value("");
			this.controls.branch.set_value("");
			this.controls.customer.set_value("");
			this.controls.sales_order.set_value("");
			this.controls.transaction_type.set_value("");
			this.controls.transaction_status.set_value("");
		} finally {
			this.is_programmatic_change = false;
		}

		$("#soti-search-input").val("");
		this.search_query = "";
		this.pagination.page = 1;
		this.active_kpi = "with-open";
		this.auto_expand_on_render = false;

		this.load_data();
	}

	toggle_expand_row(so_name) {
		if (this.expanded_sos.has(so_name)) {
			this.expanded_sos.delete(so_name);
			$(`.soti-row-parent[data-sales-order="${so_name}"]`).removeClass("is-expanded");
			$(`.soti-row-nested[data-sales-order="${so_name}"]`).hide();
		} else {
			this.expanded_sos.add(so_name);
			$(`.soti-row-parent[data-sales-order="${so_name}"]`).addClass("is-expanded");
			$(`.soti-row-nested[data-sales-order="${so_name}"]`).show();
		}
	}

	toggle_expand_all(expand = true) {
		if (expand) {
			this.raw_data.forEach((so) => this.expanded_sos.add(so.sales_order));
			$(".soti-row-parent").addClass("is-expanded");
			$(".soti-row-nested").show();
		} else {
			this.expanded_sos.clear();
			$(".soti-row-parent").removeClass("is-expanded");
			$(".soti-row-nested").hide();
		}
	}

	load_data(scroll_to_table = false) {
		const container = $("#soti-table-container");
		container.html(`
			<div class="soti-empty-state">
				<div class="soti-empty-icon" style="color: #0284c7;">
					${soti_icon("spinner", "fa-spin")}
				</div>
				<h3>${__("Analyzing Transaction Integrity...")}</h3>
				<p>${__("Verifying completed Sales Orders and checking linked DocTypes for open records.")}</p>
			</div>
		`);

		this.request_counter = (this.request_counter || 0) + 1;
		const req_id = this.request_counter;

		const args = {
			from_date: this.filters.from_date || undefined,
			to_date: this.filters.to_date || undefined,
			branch: this.filters.branch || undefined,
			customer: this.filters.customer || undefined,
			sales_order: this.filters.sales_order || undefined,
			transaction_type: this.filters.transaction_type || undefined,
			transaction_status: this.filters.transaction_status || undefined,
			search_term: this.search_query || undefined,
			sort_field: this.sort_field,
			sort_order: this.sort_order,
			page: this.pagination.page,
			page_length: this.pagination.page_length,
			kpi: this.active_kpi,
		};

		frappe.call({
			method: "generate_item.generate_item.page.sales_order_transaction_integrity.sales_order_transaction_integrity.get_transaction_integrity_data",
			args: args,
			callback: (r) => {
				if (req_id !== this.request_counter) {
					return;
				}
				if (r.message) {
					this.raw_data = r.message.data || [];
					this.summary = r.message.summary || {};
					this.pagination = Object.assign(this.pagination, r.message.pagination || {});
					this.filter_meta = r.message.filter_meta || {};

					this.update_summary_cards();
					this.render_table();
					this.update_pagination_ui();

					if (this.auto_expand_on_render) {
						this.toggle_expand_all(true);
						this.auto_expand_on_render = false;
					}

					if (scroll_to_table) {
						$('html, body').animate({
							scrollTop: $(".soti-action-toolbar").offset().top - 20
						}, 200);
					}
				}
			},
			error: () => {
				if (req_id !== this.request_counter) {
					return;
				}
				container.html(`
					<div class="soti-empty-state">
						<div class="soti-empty-icon" style="color: #ef4444;">
							${soti_icon("alertTriangle")}
						</div>
						<h3>${__("Failed to Load Data")}</h3>
						<p>${__("An error occurred while fetching transaction integrity data. Please check your permissions and try again.")}</p>
					</div>
				`);
			},
		});
	}

	update_summary_cards() {
		const s = this.summary;
		const checked = s.completed_sos_checked || 0;
		const withOpen = s.sos_with_open_tx || 0;
		const totalOpen = s.total_open_tx || 0;
		const openDraft = s.open_draft_tx || 0;

		const withOpenPct = checked > 0 ? Math.round((withOpen / checked) * 100) : 0;
		const draftPct = totalOpen > 0 ? Math.round((openDraft / totalOpen) * 100) : 0;

		$("#soti-kpi-checked").text(checked.toLocaleString());
		$("#soti-kpi-with-open").text(withOpen.toLocaleString());
		$("#soti-kpi-with-open-pct").text(`${withOpenPct}%`);
		$("#soti-kpi-total-open").text(totalOpen.toLocaleString());
		$("#soti-kpi-draft").text(openDraft.toLocaleString());
		$("#soti-kpi-draft-pct").text(`${draftPct}% Draft`);

		$("#soti-table-counts-label").text(
			__("Showing {0} of {1} Sales Orders ({2} Open Transactions)", [
				this.raw_data.length,
				this.pagination.total_records || 0,
				totalOpen.toLocaleString(),
			])
		);

		// Synchronize active card state
		$(".soti-card").removeClass("is-active");
		if (this.active_kpi === "checked") {
			$(".soti-card.card-checked").addClass("is-active");
		} else if (this.active_kpi === "draft" || this.filters.transaction_status === "Draft") {
			$(".soti-card.card-draft").addClass("is-active");
		} else if (this.active_kpi === "total-open") {
			$(".soti-card.card-total-open").addClass("is-active");
		} else {
			$(".soti-card.card-with-open").addClass("is-active");
		}
	}

	render_table() {
		const container = $("#soti-table-container");

		if (!this.raw_data || this.raw_data.length === 0) {
			if (this.active_kpi === "checked") {
				container.html(`
					<div class="soti-empty-state">
						<div class="soti-empty-icon">
							${soti_icon("fileText")}
						</div>
						<h3>${__("No Completed Sales Orders Found")}</h3>
						<p>${__("No completed Sales Orders found for the currently selected filters.")}</p>
					</div>
				`);
			} else {
				container.html(`
					<div class="soti-empty-state">
						<div class="soti-empty-icon">
							${soti_icon("checkCircle")}
						</div>
						<h3>${__("All Transactions Completed!")}</h3>
						<p>${__("No open or draft linked transactions found for the selected completed Sales Orders.")}</p>
					</div>
				`);
			}
			$("#soti-pagination-bar").hide();
			return;
		}

		let html = `
			<table class="soti-main-table">
				<thead>
					<tr>
						<th style="width: 38px; text-align: center;"></th>
						<th>${__("Sales Order")}</th>
						<th>${__("Customer")}</th>
						<th>${__("Transaction Date")}</th>
						<th>${__("Branch")}</th>
						<th>${__("Status")}</th>
						<th>${__("Open Transactions")}</th>
						<th style="text-align: right;">${__("Actions")}</th>
					</tr>
				</thead>
				<tbody>
		`;

		this.raw_data.forEach((so) => {
			const isExpanded = this.expanded_sos.has(so.sales_order);
			const openTx = so.open_transactions || [];
			const hasDraft = openTx.some((t) => t.is_draft);
			const draftCount = openTx.filter((t) => t.is_draft).length;
			const isZero = (so.open_transactions_count || 0) === 0;

			html += `
				<tr class="soti-row-parent ${isExpanded ? "is-expanded" : ""}" data-sales-order="${frappe.utils.escape_html(so.sales_order)}">
					<td style="text-align: center;">
						<button class="soti-expand-btn" data-sales-order="${frappe.utils.escape_html(so.sales_order)}" title="${isZero ? __("Click to view details (all transactions completed)") : __("Click to toggle open transactions")}">
							${soti_icon("chevronRight")}
						</button>
					</td>
					<td>
						<a class="soti-doc-link" href="/app/sales-order/${encodeURIComponent(so.sales_order)}" target="_blank" onclick="event.stopPropagation();">
							${soti_icon("fileText")}
							<strong>${frappe.utils.escape_html(so.sales_order)}</strong>
						</a>
					</td>
					<td>
						<div style="font-weight: 500;">${frappe.utils.escape_html(so.customer_name)}</div>
						${so.customer && so.customer !== so.customer_name ? `<div style="font-size: 11px; color: var(--soti-muted);">${frappe.utils.escape_html(so.customer)}</div>` : ""}
					</td>
					<td>${so.transaction_date_formatted || "-"}</td>
					<td>
						<span class="soti-badge soti-badge-secondary">${frappe.utils.escape_html(so.branch)}</span>
					</td>
					<td>
						<span class="soti-badge soti-badge-success">
							${soti_icon("check")} ${frappe.utils.escape_html(so.status)}
						</span>
					</td>
					<td>
						<span class="soti-count-pill ${isZero ? "is-zero" : (hasDraft ? "has-draft" : "")}">
							${soti_icon(isZero ? "checkCircle" : (hasDraft ? "edit" : "clock"))}
							${so.open_transactions_count || 0} Open
							${hasDraft ? `(${draftCount} Draft)` : ""}
						</span>
					</td>
					<td style="text-align: right;">
						<a class="btn btn-default btn-xs" href="/app/sales-order/${encodeURIComponent(so.sales_order)}" target="_blank" onclick="event.stopPropagation();">
							${soti_icon("externalLink")} ${__("View")}
						</a>
					</td>
				</tr>

				<!-- Sub-table for Linked Transactions -->
				<tr class="soti-row-nested" data-sales-order="${frappe.utils.escape_html(so.sales_order)}" style="${isExpanded ? "" : "display: none;"}">
					<td colspan="8">
						<div class="soti-subtable-wrap">
							<div class="soti-subtable-header">
								<div class="soti-subtable-title">
									${soti_icon("chevronDown")}
									<span>${__("Open Linked Transactions for Sales Order:")} <strong>${frappe.utils.escape_html(so.sales_order)}</strong></span>
								</div>
								<span style="font-size: 11px; color: var(--soti-muted);">
									${openTx.length} ${__("records pending completion")}
								</span>
							</div>
							${openTx.length > 0 ? `
							<table class="soti-subtable">
								<thead>
									<tr>
										<th>${__("Transaction Type")}</th>
										<th>${__("Transaction ID")}</th>
										<th>${__("Date")}</th>
										<th>${__("Status")}</th>
										<th>${__("Owner")}</th>
										<th>${__("Responsible User")}</th>
										<th style="text-align: right; width: 80px;">${__("Action")}</th>
									</tr>
								</thead>
								<tbody>
							` : `
							<div style="padding: 16px 20px; color: var(--soti-muted); font-size: 12px; display: flex; align-items: center; gap: 8px;">
								<span style="color: #16a34a;">${soti_icon("checkCircle")}</span>
								${__("All linked transactions for this Sales Order are completed. No open or draft records found.")}
							</div>
							`}
			`;

			openTx.forEach((tx) => {
				const doctypeSlug = frappe.router.slug(tx.doctype);
				const statusBadgeClass = this.get_status_badge_class(tx);
				const docIcon = this.get_doctype_icon_name(tx.doctype);

				html += `
					<tr>
						<td>
							<span class="soti-badge soti-badge-info" style="font-weight: 600;">
								${soti_icon(docIcon)}
								${frappe.utils.escape_html(tx.doctype)}
							</span>
						</td>
						<td>
							<a class="soti-doc-link" href="/app/${doctypeSlug}/${encodeURIComponent(tx.name)}" target="_blank">
								${frappe.utils.escape_html(tx.name)}
							</a>
						</td>
						<td>${tx.posting_date_formatted || "-"}</td>
						<td>
							<span class="soti-badge ${statusBadgeClass}">
								${tx.is_draft ? `${soti_icon("edit")} ` : ""}
								${frappe.utils.escape_html(tx.status)}
							</span>
						</td>
						<td>
							<div style="font-size: 11.5px; display: inline-flex; align-items: center; gap: 4px;">
								<span style="color: var(--soti-muted);">${soti_icon("user")}</span>
								${frappe.utils.escape_html(tx.owner_name || tx.owner || "-")}
							</div>
						</td>
						<td>
							<div style="font-size: 11.5px; font-weight: 500; display: inline-flex; align-items: center; gap: 4px;">
								<span style="color: #0284c7;">${soti_icon("user")}</span>
								${frappe.utils.escape_html(tx.responsible_user || tx.owner_name || "-")}
							</div>
						</td>
						<td style="text-align: right;">
							<a class="btn btn-default btn-xs" href="/app/${doctypeSlug}/${encodeURIComponent(tx.name)}" target="_blank">
								${soti_icon("externalLink")} ${__("Open")}
							</a>
						</td>
					</tr>
				`;
			});

			if (openTx.length > 0) {
				html += `
								</tbody>
							</table>
				`;
			}

			html += `
						</div>
					</td>
				</tr>
			`;
		});

		html += `
				</tbody>
			</table>
		`;

		container.html(html);
		$("#soti-pagination-bar").show();
	}

	get_doctype_icon_name(dt) {
		switch (dt) {
			case "Delivery Note": return "truck";
			case "Sales Invoice":
			case "Purchase Invoice": return "fileSpreadsheet";
			case "Payment Entry": return "layers";
			case "Work Order":
			case "Production Plan": return "sliders";
			case "Material Request": return "fileText";
			case "Purchase Order": return "layers";
			case "Purchase Receipt": return "truck";
			case "Stock Entry": return "layers";
			case "BOM": return "layers";
			case "Bom Modification Request":
			case "BOM Modification Request":
			case "Order Modification Request": return "edit";
			case "Valve Painting":
			case "Valve Painting Item": return "edit";
			case "Valve Testing":
			case "Valve Testing Item": return "checkCircle";
			case "Valve Assembly":
			case "Assembly Item Serial No": return "sliders";
			case "Proforma Invoice":
			case "Proforma Invoice Item": return "fileSpreadsheet";
			default: return "fileText";
		}
	}

	get_status_badge_class(tx) {
		if (tx.is_draft) {
			return "soti-badge-warning";
		}
		const s = (tx.status || "").toLowerCase();
		if (s.includes("overdue") || s.includes("danger") || s.includes("stopped")) {
			return "soti-badge-danger";
		}
		if (s.includes("unpaid") || s.includes("to bill") || s.includes("to receive") || s.includes("pending")) {
			return "soti-badge-warning";
		}
		if (s.includes("process") || s.includes("ordered") || s.includes("requested")) {
			return "soti-badge-info";
		}
		return "soti-badge-secondary";
	}

	update_pagination_ui() {
		const p = this.pagination;
		const total = p.total_records || 0;
		const start = total === 0 ? 0 : (p.page - 1) * p.page_length + 1;
		const end = Math.min(start + p.page_length - 1, total);

		$("#soti-pagination-text").text(
			__("Showing {0} - {1} of {2} Sales Orders", [start, end, total])
		);
		$("#soti-page-number-display").text(
			__("Page {0} of {1}", [p.page, p.total_pages || 1])
		);

		// Button states
		$("#soti-btn-first, #soti-btn-prev").prop("disabled", p.page <= 1);
		$("#soti-btn-next, #soti-btn-last").prop("disabled", p.page >= p.total_pages);
	}

	export_data() {
		const args = {
			from_date: this.filters.from_date || undefined,
			to_date: this.filters.to_date || undefined,
			branch: this.filters.branch || undefined,
			customer: this.filters.customer || undefined,
			sales_order: this.filters.sales_order || undefined,
			transaction_type: this.filters.transaction_type || undefined,
			transaction_status: this.filters.transaction_status || undefined,
			search_term: this.search_query || undefined,
		};

		frappe.show_alert({ message: __("Generating export file..."), indicator: "blue" });

		frappe.call({
			method: "generate_item.generate_item.page.sales_order_transaction_integrity.sales_order_transaction_integrity.export_transaction_integrity_data",
			args: args,
			callback: (r) => {
				const rows = r.message || [];
				if (!rows || rows.length === 0) {
					frappe.msgprint(__("No data available to export under selected filters."));
					return;
				}

				const headers = [
					"Sales Order",
					"Customer Code",
					"Customer Name",
					"Branch",
					"SO Date",
					"SO Status",
					"Transaction DocType",
					"Transaction ID",
					"Transaction Date",
					"Transaction Status",
					"Owner",
					"Responsible User",
				];

				const csvContent = [];
				csvContent.push(headers.map((h) => `"${h}"`).join(","));

				rows.forEach((row) => {
					const line = [
						row.sales_order,
						row.customer,
						row.customer_name,
						row.branch,
						row.so_date,
						row.so_status,
						row.transaction_doctype,
						row.transaction_id,
						row.transaction_date,
						row.transaction_status,
						row.owner,
						row.responsible_user,
					].map((val) => `"${(val || "").toString().replace(/"/g, '""')}"`);
					csvContent.push(line.join(","));
				});

				const blob = new Blob([csvContent.join("\r\n")], { type: "text/csv;charset=utf-8;" });
				const link = document.createElement("a");
				const filename = `Sales_Order_Transaction_Integrity_${frappe.datetime.now_date()}.csv`;
				link.href = URL.createObjectURL(blob);
				link.setAttribute("download", filename);
				document.body.appendChild(link);
				link.click();
				document.body.removeChild(link);

				frappe.show_alert({ message: __("Export complete ({0} rows downloaded)", [rows.length]), indicator: "green" });
			},
		});
	}
}
