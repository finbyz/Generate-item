frappe.pages['sales-performance-da'].on_page_load = function (wrapper) {
	new SalesPerformanceDashboard(wrapper);
};

// ---------------------------------------------------------------------------
// Constants & Configuration
// ---------------------------------------------------------------------------
const SPD_API_METHOD = "generate_item.generate_item.page.sales_performance_da.sales_performance_da.get_dashboard_data";

const SPD_BRANCHES = ["Sanand", "Nandikoor", "Rabale"];

const SPD_DATE_PRESETS = [
	"Today", "This Week", "Last Week", "This Month", "Last Month",
	"This Quarter", "Last Quarter", "This Year", "Last Year", "Custom"
];

// ---------------------------------------------------------------------------
// Inline Icon Set
// ---------------------------------------------------------------------------
const SPD_ICON_PATHS = {
	dashboard:     `<rect x="3" y="3" width="7" height="9" rx="2"/><rect x="14" y="3" width="7" height="5" rx="2"/><rect x="14" y="12" width="7" height="9" rx="2"/><rect x="3" y="16" width="7" height="5" rx="2"/>`,
	factory:       `<path d="M3 21h18"/><path d="M5 21V10l5 3.2V10l5 3.2V7l4 2.4V21"/><path d="M5 10l3 2"/><circle cx="8.5" cy="6" r="1.4"/>`,
	calendar:      `<rect x="3" y="4.5" width="18" height="16" rx="2.5"/><path d="M16 2.5v4M8 2.5v4M3 10h18"/>`,
	refresh:       `<path d="M21 12a9 9 0 1 1-3-6.7"/><path d="M21 3v6h-6"/>`,
	rotate:        `<path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 3v6h6"/>`,
	building:      `<rect x="4" y="2" width="16" height="20" rx="1.5"/><path d="M9 22v-4h6v4"/><path d="M8 6.5h.01M12 6.5h.01M16 6.5h.01M8 10.5h.01M12 10.5h.01M16 10.5h.01M8 14.5h.01M12 14.5h.01M16 14.5h.01"/>`,
	chevronDown:   `<path d="M6 9l6 6 6-6"/>`,
	arrowRight:    `<path d="M5 12h14"/><path d="M13 6l6 6-6 6"/>`,
	trendingUp:    `<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>`,
	trendingDown:  `<path d="M3 7l6 6 4-4 8 8"/><path d="M15 17h6v-6"/>`,
	layers:        `<path d="M12 2 2 7l10 5 10-5-10-5Z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>`,
	package:       `<path d="M21 8l-9-5-9 5 9 5 9-5Z"/><path d="M3 8v8l9 5 9-5V8"/><path d="M12 13v8"/>`,
	activity:      `<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>`,
	inbox:         `<path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11Z"/>`,
	eye:           `<path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/>`,
	truck:         `<rect x="1" y="3" width="15" height="13"/><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/>`,
	fileText:      `<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/>`,
	checkCircle:   `<circle cx="12" cy="12" r="9"/><path d="m8.5 12 2.5 2.5 4.5-4.5"/>`,
	clock:         `<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>`,
	dollarSign:    `<line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>`,
	alertTriangle: `<path d="M12 2 1 21h22L12 2Z"/><path d="M12 9v5"/><path d="M12 17h.01"/>`,
};

function spd_icon(name, cls = "") {
	const inner = SPD_ICON_PATHS[name] || "";
	return `<svg class="ocd-icon ${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${inner}</svg>`;
}

// ---------------------------------------------------------------------------
// Sales Performance Dashboard Class
// ---------------------------------------------------------------------------
class SalesPerformanceDashboard {
	constructor(wrapper) {
		this.wrapper = wrapper;
		this.charts = {};
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __("Sales Performance Dashboard"),
			single_column: true,
		});

		this.ensure_chartjs();

		// Default filters: This Quarter, All branches, Sales view
		const defaultDates = this.resolve_preset("This Quarter");
		this.filters = {
			view_type:  "Sales",
			branch:     "",
			preset:     "This Quarter",
			from_date:  defaultDates.from_date,
			to_date:    defaultDates.to_date,
		};

		this.inject_styles();
		this.render_shell();
		this.bind_events();
		this.apply_filters_from_url();
		this.load_data();
	}

	ensure_chartjs() {
		if (!window.Chart) {
			const script = document.createElement("script");
			script.src = "https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js";
			document.head.appendChild(script);
		}
	}

	inject_styles() {
		if (document.getElementById("spd-dashboard-styles")) return;
		const s = document.createElement("style");
		s.id = "spd-dashboard-styles";
		s.textContent = SPD_CSS;
		document.head.appendChild(s);
	}

	get_theme() {
		return localStorage.getItem("ocd_theme") || "light";
	}

	set_theme(theme) {
		localStorage.setItem("ocd_theme", theme);
		this.root.setAttribute("data-theme", theme);
		const icon = this.wrapper.querySelector(".ocd-theme-icon");
		const text = this.wrapper.querySelector(".ocd-theme-text");
		if (icon) icon.textContent = theme === "dark" ? "☾" : "☀";
		if (text) text.textContent = theme === "dark" ? __("Dark mode") : __("Light mode");

		if (this.last_data) {
			this.render_all_charts(this.last_data);
		}
	}

	// ----------------------------------------------------------------- Shell
	render_shell() {
		$(this.page.body).html(`
			<div class="ocd-root" data-theme="${frappe.utils.escape_html(this.get_theme())}">

				<!-- ── Header ── -->
				<header class="ocd-header">
					<div class="ocd-header-left">
						<div class="ocd-header-icon">${spd_icon("trendingUp")}</div>
						<div class="ocd-header-text">
							<div class="ocd-header-titlerow">
								<h1 class="ocd-title">${__("Sales Performance Dashboard")}</h1>
								<span class="ocd-status-chip" title="${__("Data is refreshed on demand")}">
									<span class="ocd-status-dot" aria-hidden="true"></span>${__("Live")}
								</span>
							</div>
							<p class="ocd-subtitle">${__("Order status, booking value, invoicing & OTD analytics across branches")}</p>
							<div class="ocd-header-meta" data-field="summary">${__("Loading…")}</div>
						</div>
					</div>
					<div class="ocd-header-actions">
						<button class="ocd-btn ocd-btn-primary ocd-refresh-btn" type="button" title="${__("Refresh data")}">
							${spd_icon("refresh")}<span>${__("Refresh")}</span>
						</button>
						<button class="ocd-theme-toggle" type="button" title="${__("Toggle theme")}" aria-label="${__("Toggle theme")}">
							<span class="ocd-theme-track">
								<span class="ocd-theme-thumb">
									<span class="ocd-theme-icon" aria-hidden="true">☀</span>
								</span>
							</span>
							<span class="ocd-theme-text">${__("Light mode")}</span>
						</button>
					</div>
				</header>

				<!-- ── Filter Toolbar ── -->
				<div class="ocd-toolbar">
					<div class="ocd-toolbar-group">

						<!-- View Selector Dropdown -->
						<div class="ocd-field ocd-custom-select-wrapper" data-field-name="view_type">
							<span class="ocd-field-icon">${spd_icon("eye")}</span>
							<span class="ocd-field-label">${__("View")}</span>
							<div class="ocd-custom-select" data-role="view-select">
								<div class="ocd-custom-select-trigger">
									<span class="ocd-custom-select-text">${__("Sales")}</span>
									${spd_icon("chevronDown", "ocd-custom-select-arrow")}
								</div>
								<div class="ocd-custom-select-options">
									<div class="ocd-custom-option selected" data-value="Sales">${__("Sales")}</div>
									<div class="ocd-custom-option" data-value="Purchase">${__("Purchase")}</div>
								</div>
							</div>
						</div>

						<!-- Branch Dropdown -->
						<div class="ocd-field ocd-custom-select-wrapper" data-field-name="branch">
							<span class="ocd-field-icon">${spd_icon("building")}</span>
							<span class="ocd-field-label">${__("Branch")}</span>
							<div class="ocd-custom-select" data-role="branch-select">
								<div class="ocd-custom-select-trigger">
									<span class="ocd-custom-select-text">${__("All Branches")}</span>
									${spd_icon("chevronDown", "ocd-custom-select-arrow")}
								</div>
								<div class="ocd-custom-select-options">
									<div class="ocd-custom-option selected" data-value="">${__("All Branches")}</div>
									${SPD_BRANCHES.map(b => `<div class="ocd-custom-option" data-value="${b}">${b}</div>`).join("")}
								</div>
							</div>
						</div>

						<!-- Period Dropdown -->
						<div class="ocd-field ocd-custom-select-wrapper" data-field-name="period">
							<span class="ocd-field-icon">${spd_icon("calendar")}</span>
							<span class="ocd-field-label">${__("Period")}</span>
							<div class="ocd-custom-select" data-role="date-preset">
								<div class="ocd-custom-select-trigger">
									<span class="ocd-custom-select-text">${__("This Quarter")}</span>
									${spd_icon("chevronDown", "ocd-custom-select-arrow")}
								</div>
								<div class="ocd-custom-select-options">
									${SPD_DATE_PRESETS.map(p =>
										`<div class="ocd-custom-option ${p === "This Quarter" ? "selected" : ""}" data-value="${p}">${__(p)}</div>`
									).join("")}
								</div>
							</div>
						</div>

						<!-- Custom Dates Pickers -->
						<div class="ocd-custom-dates" data-role="custom-dates">
							<input type="date" class="ocd-date-input" data-role="from-date" aria-label="${__("From date")}" />
							<span class="ocd-date-sep">${spd_icon("arrowRight")}</span>
							<input type="date" class="ocd-date-input" data-role="to-date" aria-label="${__("To date")}" />
						</div>
					</div>

					<div class="ocd-toolbar-group ocd-toolbar-group--right">
						<button type="button" class="ocd-chip-btn ocd-chip-btn--ghost" data-role="reset-filters" title="${__("Reset filters")}">
							${spd_icon("rotate")}<span>${__("Reset")}</span>
						</button>
					</div>
				</div>

				

				<!-- ── Section 02 · Orders & Approval Pipeline ── -->
				<section class="ocd-section" data-section="orders-pipeline">
					<div class="ocd-section-head">
						<span class="ocd-section-index">01</span>
						<span class="ocd-section-title">${__("Orders by Status & Approval Delay")}</span>
						<span class="ocd-section-line" aria-hidden="true"></span>
					</div>
					<div class="spd-charts-grid-2">
						<div class="ocd-card spd-chart-card">
							<div class="spd-card-header">
								<span class="spd-card-title">${spd_icon("package", "spd-title-icon")}${__("Orders by Status")}</span>
								<span class="spd-card-sub">${__("Distribution in selected period")}</span>
							</div>
							<div class="spd-chart-wrapper" style="height: 280px;">
								<canvas id="ordersStatusChart"></canvas>
							</div>
						</div>
						<div class="ocd-card spd-chart-card">
							<div class="spd-card-header">
								<span class="spd-card-title">${spd_icon("clock", "spd-title-icon")}${__("Order Approval Delay")}</span>
								<span class="spd-card-sub">${__("Pending approval age breakdown")}</span>
							</div>
							<div class="spd-chart-wrapper" style="height: 280px;">
								<canvas id="orderApprovalDelayChart"></canvas>
							</div>
						</div>
					</div>
				</section>

				<!-- ── Section 03 · On-Time Delivery (OTD) Analysis ── -->
				<section class="ocd-section" data-section="otd-analysis">
					<div class="ocd-section-head">
						<span class="ocd-section-index">02</span>
						<span class="ocd-section-title">${__("On-Time Delivery (OTD) Analysis")}</span>
						<span class="ocd-section-line" aria-hidden="true"></span>
					</div>
					<div class="spd-charts-grid-3">
						<div class="ocd-card spd-chart-card">
							<div class="spd-card-header">
								<div class="spd-header-titlerow">
									<span class="spd-card-title">${spd_icon("truck", "spd-title-icon")}${__("Delivery OTD")}</span>
									<span class="spd-otd-pill" id="delivery-otd-pill">—</span>
								</div>
								<span class="spd-card-sub">${__("Actual vs Scheduled Delivery Date")}</span>
							</div>
							<div class="spd-chart-wrapper" style="height: 230px;">
								<canvas id="deliveryOtdChart"></canvas>
							</div>
							<div class="spd-chart-footer" id="delivery-otd-footer"></div>
						</div>

						<div class="ocd-card spd-chart-card">
							<div class="spd-card-header">
								<div class="spd-header-titlerow">
									<span class="spd-card-title">${spd_icon("fileText", "spd-title-icon")}${__("Order Entry OTD")}</span>
									<span class="spd-otd-pill" id="order-entry-otd-pill">—</span>
								</div>
								<span class="spd-card-sub">${__("PO Date to SO Date (≤3 days = On Time)")}</span>
							</div>
							<div class="spd-chart-wrapper" style="height: 230px;">
								<canvas id="orderEntryOtdChart"></canvas>
							</div>
							<div class="spd-chart-footer" id="order-entry-otd-footer"></div>
						</div>

						<div class="ocd-card spd-chart-card">
							<div class="spd-card-header">
								<div class="spd-header-titlerow">
									<span class="spd-card-title">${spd_icon("checkCircle", "spd-title-icon")}${__("Order Approval OTD")}</span>
									<span class="spd-otd-pill" id="order-approval-otd-pill">—</span>
								</div>
								<span class="spd-card-sub">${__("SO Date to Approval (≤5 days = On Time)")}</span>
							</div>
							<div class="spd-chart-wrapper" style="height: 230px;">
								<canvas id="orderApprovalOtdChart"></canvas>
							</div>
							<div class="spd-chart-footer" id="order-approval-otd-footer"></div>
						</div>
					</div>
				</section>

                <!-- ── Section 01 · Key Financial & Booking Metrics ── -->
				<section class="ocd-section" data-section="financial-kpis">
					<div class="ocd-section-head">
						<span class="ocd-section-index">03</span>
						<span class="ocd-section-title">${__("Key Financial & Booking Metrics")}</span>
						<span class="ocd-section-line" aria-hidden="true"></span>
					</div>
					<!-- Summary top row -->
					<div class="spd-kpi-summary-row" data-role="financial-kpis-summary">
						${this.skeleton_cards(1, 64)}
					</div>
					<!-- Grouped metric cards -->
					<div class="spd-metric-groups" data-role="financial-kpis">
						${this.skeleton_cards(3, 130)}
					</div>
				</section>

				<!-- ── Section 04 · BOM Release Pending Delay ── -->
				<section class="ocd-section" data-section="bom-pending">
					<div class="ocd-section-head">
						<span class="ocd-section-index">04</span>
						<span class="ocd-section-title">${__("BOM Release Pending Delay")}</span>
						<span class="ocd-section-line" aria-hidden="true"></span>
					</div>
					<div class="ocd-card spd-chart-card">
						<div class="spd-card-header">
							<span class="spd-card-title">${spd_icon("alertTriangle", "spd-title-icon")}${__("BOM Release Pending Delay (> 2 weeks)")}</span>
							<span class="spd-card-sub">${__("Orders where BOM is not submitted within 2 weeks of SO creation")}</span>
						</div>
						<div class="spd-chart-wrapper" style="height: 280px;">
							<canvas id="bomPendingChart"></canvas>
						</div>
					</div>
				</section>

			</div>
		`);

		this.root = this.wrapper.querySelector(".ocd-root");

		// Initialize date input values
		const fromInput = this.wrapper.querySelector("[data-role='from-date']");
		const toInput = this.wrapper.querySelector("[data-role='to-date']");
		if (fromInput && toInput) {
			fromInput.value = this.filters.from_date;
			toInput.value = this.filters.to_date;
			fromInput.disabled = true;
			toInput.disabled = true;
		}
	}

	skeleton_cards(n, height = 110) {
		let o = "";
		for (let i = 0; i < n; i++) {
			o += `<div class="ocd-card ocd-skel" style="height:${height}px"></div>`;
		}
		return o;
	}

	// ---------------------------------------------------------------- Events
	bind_events() {
		// Theme toggle
		this.wrapper.querySelector(".ocd-theme-toggle").addEventListener("click", () => {
			this.set_theme(this.root.getAttribute("data-theme") === "dark" ? "light" : "dark");
		});
		this.set_theme(this.get_theme());

		// Refresh
		this.wrapper.querySelector(".ocd-refresh-btn").addEventListener("click", () => this.load_data());

		// Date inputs
		this.wrapper.querySelector("[data-role='to-date']").addEventListener("change", () => this.sync_custom_dates());

		this.init_custom_selects();
		this.bind_extra_controls();
	}

	init_custom_selects() {
		const wrappers = this.wrapper.querySelectorAll('.ocd-custom-select-wrapper');

		wrappers.forEach(wrapper => {
			const select = wrapper.querySelector('.ocd-custom-select');
			const trigger = select.querySelector('.ocd-custom-select-trigger');
			const text = select.querySelector('.ocd-custom-select-text');
			const options = select.querySelectorAll('.ocd-custom-option');

			// Toggle dropdown
			trigger.addEventListener('click', (e) => {
				e.stopPropagation();
				this.wrapper.querySelectorAll('.ocd-custom-select.open').forEach(s => {
					if (s !== select) s.classList.remove('open');
				});
				select.classList.toggle('open');
			});

			// Option selection
			options.forEach(option => {
				option.addEventListener('click', (e) => {
					e.stopPropagation();
					const value = option.dataset.value;

					text.textContent = option.textContent;
					options.forEach(o => o.classList.remove('selected'));
					option.classList.add('selected');
					select.classList.remove('open');

					const role = select.dataset.role;

					if (role === 'view-select') {
						if (value === 'Purchase') {
							frappe.set_route('director-dashboard');
						}
					} else if (role === 'branch-select') {
						this.filters.branch = value;
						this.load_data();
					} else if (role === 'date-preset') {
						this.filters.preset = value;
						const fromInput = this.wrapper.querySelector("[data-role='from-date']");
						const toInput = this.wrapper.querySelector("[data-role='to-date']");

						if (value !== "Custom") {
							const { from_date, to_date } = this.resolve_preset(value);
							this.filters.from_date = from_date;
							this.filters.to_date = to_date;
							fromInput.value = from_date;
							toInput.value = to_date;
							fromInput.disabled = true;
							toInput.disabled = true;
							this.load_data();
						} else {
							fromInput.disabled = false;
							toInput.disabled = false;
							if (!fromInput.value) fromInput.value = frappe.datetime.get_today();
							if (!toInput.value) toInput.value = frappe.datetime.get_today();
							this.sync_custom_dates();
						}
					}
				});
			});

			document.addEventListener('click', (e) => {
				if (!select.contains(e.target)) {
					select.classList.remove('open');
				}
			});
		});
	}

	bind_extra_controls() {
		// Reset Filters
		const resetBtn = this.wrapper.querySelector("[data-role='reset-filters']");
		if (resetBtn) {
			resetBtn.addEventListener("click", () => {
				// Reset branch
				const branchSelect = this.wrapper.querySelector("[data-role='branch-select']");
				if (branchSelect) {
					const options = branchSelect.querySelectorAll('.ocd-custom-option');
					const text = branchSelect.querySelector('.ocd-custom-select-text');
					options.forEach(o => o.classList.remove('selected'));
					const allOption = branchSelect.querySelector('[data-value=""]');
					if (allOption) {
						allOption.classList.add('selected');
						text.textContent = allOption.textContent;
					}
				}
				this.filters.branch = "";

				// Reset date preset to This Quarter
				const presetSelect = this.wrapper.querySelector("[data-role='date-preset']");
				if (presetSelect) {
					const options = presetSelect.querySelectorAll('.ocd-custom-option');
					const text = presetSelect.querySelector('.ocd-custom-select-text');
					options.forEach(o => o.classList.remove('selected'));
					const defaultOption = presetSelect.querySelector('[data-value="This Quarter"]');
					if (defaultOption) {
						defaultOption.classList.add('selected');
						text.textContent = defaultOption.textContent;
					}
				}
				this.filters.preset = "This Quarter";
				const { from_date, to_date } = this.resolve_preset("This Quarter");
				this.filters.from_date = from_date;
				this.filters.to_date = to_date;
				const fromInput = this.wrapper.querySelector("[data-role='from-date']");
				const toInput = this.wrapper.querySelector("[data-role='to-date']");
				fromInput.value = from_date;
				toInput.value = to_date;
				fromInput.disabled = true;
				toInput.disabled = true;
				this.load_data();
			});
		}
	}

	sync_custom_dates() {
		const fd = this.wrapper.querySelector("[data-role='from-date']").value;
		const td = this.wrapper.querySelector("[data-role='to-date']").value;
		if (fd && td) {
			this.filters.from_date = fd;
			this.filters.to_date = td;
			this.load_data();
		}
	}

	// ---------------------------------------------------------------- URL Filters
	apply_filters_from_url() {
		const params = new URLSearchParams(window.location.search);
		const read = (key) => {
			if (frappe.route_options && frappe.route_options[key] !== undefined) {
				const val = frappe.route_options[key];
				delete frappe.route_options[key];
				return val;
			}
			return params.get(key) || undefined;
		};

		const urlFrom = read('from_date');
		const urlTo   = read('to_date');
		const urlBranch = read('branch');

		if (frappe.route_options && Object.keys(frappe.route_options).length === 0) {
			frappe.route_options = null;
		}

		if (urlBranch) {
			this.filters.branch = urlBranch;
			const branchSelect = this.wrapper.querySelector("[data-role='branch-select']");
			if (branchSelect) {
				const options = branchSelect.querySelectorAll('.ocd-custom-option');
				const text = branchSelect.querySelector('.ocd-custom-select-text');
				options.forEach(o => {
					o.classList.remove('selected');
					if (o.dataset.value === urlBranch) {
						o.classList.add('selected');
						text.textContent = o.textContent;
					}
				});
			}
		}

		if (urlFrom && urlTo) {
			this.filters.preset = "Custom";
			this.filters.from_date = urlFrom;
			this.filters.to_date = urlTo;

			const fromInput = this.wrapper.querySelector("[data-role='from-date']");
			const toInput = this.wrapper.querySelector("[data-role='to-date']");
			if (fromInput && toInput) {
				fromInput.value = urlFrom;
				toInput.value = urlTo;
				fromInput.disabled = false;
				toInput.disabled = false;
			}

			const presetSelect = this.wrapper.querySelector("[data-role='date-preset']");
			if (presetSelect) {
				const options = presetSelect.querySelectorAll('.ocd-custom-option');
				const text = presetSelect.querySelector('.ocd-custom-select-text');
				options.forEach(o => {
					o.classList.remove('selected');
					if (o.dataset.value === "Custom") {
						o.classList.add('selected');
						text.textContent = o.textContent;
					}
				});
			}
		}
	}

	// ---------------------------------------------------------------- Date Helpers
	resolve_preset(preset) {
		const today     = frappe.datetime.get_today();
		const todayDate = frappe.datetime.str_to_obj(today);

		const fmt       = (d) => frappe.datetime.obj_to_str(d);
		const add       = (d, n) => { const x = new Date(d); x.setDate(x.getDate() + n); return x; };
		const subMonths = (d, n) => { const x = new Date(d); x.setMonth(x.getMonth() - n); return x; };
		const dow       = todayDate.getDay();
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
				const last  = new Date(todayDate.getFullYear(), todayDate.getMonth(), 0);
				return { from_date: fmt(first), to_date: fmt(last) };
			}
			case "This Quarter": {
				const start = subMonths(todayDate, 3);
				return { from_date: fmt(start), to_date: today };
			}
			case "Last Quarter": {
				const thisQStart = subMonths(todayDate, 3);
				const lastQEnd   = add(thisQStart, -1);
				const lastQStart = subMonths(thisQStart, 3);
				return { from_date: fmt(lastQStart), to_date: fmt(lastQEnd) };
			}
			case "This Year": {
				const first = new Date(todayDate.getFullYear(), 0, 1);
				return { from_date: fmt(first), to_date: today };
			}
			case "Last Year": {
				const first = new Date(todayDate.getFullYear() - 1, 0, 1);
				const last  = new Date(todayDate.getFullYear() - 1, 11, 31);
				return { from_date: fmt(first), to_date: fmt(last) };
			}
			default:
				return { from_date: today, to_date: today };
		}
	}

	resolve_previous_range(preset, from_date, to_date) {
		const fmt    = (d) => frappe.datetime.obj_to_str(d);
		const toObj  = (s) => frappe.datetime.str_to_obj(s);
		const addDays = (d, n) => { const x = new Date(d); x.setDate(x.getDate() + n); return x; };

		switch (preset) {
			case "Today": {
				const y = addDays(toObj(from_date), -1);
				return { from_date: fmt(y), to_date: fmt(y) };
			}
			case "This Week":
			case "Last Week": {
				const pf = addDays(toObj(from_date), -7);
				const pt = addDays(toObj(to_date), -7);
				return { from_date: fmt(pf), to_date: fmt(pt) };
			}
			case "This Month":
			case "Last Month": {
				const cur = toObj(from_date);
				const prevFirst = new Date(cur.getFullYear(), cur.getMonth() - 1, 1);
				const prevLast  = new Date(cur.getFullYear(), cur.getMonth(), 0);
				return { from_date: fmt(prevFirst), to_date: fmt(prevLast) };
			}
			case "This Quarter":
			case "Last Quarter": {
				const pf = toObj(from_date); pf.setMonth(pf.getMonth() - 3);
				const pt = toObj(to_date);   pt.setMonth(pt.getMonth() - 3);
				return { from_date: fmt(pf), to_date: fmt(pt) };
			}
			case "This Year": {
				const cur = toObj(from_date);
				const prevFirst = new Date(cur.getFullYear() - 1, 0, 1);
				const prevLast  = new Date(cur.getFullYear() - 1, 11, 31);
				return { from_date: fmt(prevFirst), to_date: fmt(prevLast) };
			}
			case "Last Year": {
				const cur = toObj(from_date);
				const prevFirst = new Date(cur.getFullYear() - 1, 0, 1);
				const prevLast  = new Date(cur.getFullYear() - 1, 11, 31);
				return { from_date: fmt(prevFirst), to_date: fmt(prevLast) };
			}
			case "Custom":
			default: {
				const days = Math.round((toObj(to_date) - toObj(from_date)) / 86400000) + 1;
				const pt = addDays(toObj(from_date), -1);
				const pf = addDays(pt, -(days - 1));
				return { from_date: fmt(pf), to_date: fmt(pt) };
			}
		}
	}

	get_previous_period_label() {
		switch (this.filters.preset) {
			case "Today":        return __("yesterday");
			case "This Week":    return __("last week");
			case "Last Week":    return __("prior week");
			case "This Month":   return __("last month");
			case "Last Month":   return __("prior month");
			case "This Quarter": return __("previous quarter");
			case "Last Quarter": return __("quarter before that");
			case "This Year":    return __("last year");
			case "Last Year":    return __("prior year");
			default:             return __("prior period");
		}
	}

	// ---------------------------------------------------------------- Data Fetching
	load_data() {
		if (this.filters.preset !== "Custom") {
			const { from_date, to_date } = this.resolve_preset(this.filters.preset);
			this.filters.from_date = from_date;
			this.filters.to_date   = to_date;
		}

		this.show_loading();

		const prevRange = this.resolve_previous_range(this.filters.preset, this.filters.from_date, this.filters.to_date);

		const fetch = (from_date, to_date) => new Promise((resolve) => {
			frappe.call({
				method: SPD_API_METHOD,
				args: {
					branch:    this.filters.branch,
					from_date: from_date,
					to_date:   to_date
				},
				callback: (r) => resolve((r && r.message) || null),
				error: () => resolve(null),
			});
		});

		Promise.all([
			fetch(this.filters.from_date, this.filters.to_date),
			fetch(prevRange.from_date, prevRange.to_date),
		]).then(([data, prevData]) => {
			if (!data) {
				this.show_error(__("No data returned."));
				return;
			}
			this.render_data(data, prevData || {});
		});
	}

	show_loading() {
		this.wrapper.querySelector('[data-field="summary"]').textContent = __("Loading…");
		this.wrapper.querySelector('[data-role="financial-kpis"]').innerHTML = this.skeleton_cards(4, 150);
	}

	show_error(msg) {
		this.wrapper.querySelector('[data-field="summary"]').textContent = msg;
	}

	// ---------------------------------------------------------------- Rendering
	render_data(data, prevData = {}) {
		this.last_data = data;
		this.last_prev_data = prevData;

		this.render_summary(data);
		this.render_financial_kpis(data, prevData);
		this.render_all_charts(data, prevData);
	}

	render_summary(data) {
		const branchLabel = this.filters.branch || __("All branches");
		const periodLabel = this.filters.preset;
		const totalOrders = Object.values(data.orders_status || {}).reduce((s, o) => s + (o.count || 0), 0);
		const totalValue  = Object.values(data.orders_status || {}).reduce((s, o) => s + (o.value || 0), 0);

		this.wrapper.querySelector('[data-field="summary"]').textContent =
			__("{0} orders (₹ {1} Lakh) in {2} across {3} · updated {4}", [
				totalOrders.toLocaleString(),
				totalValue.toFixed(2),
				periodLabel,
				branchLabel,
				frappe.datetime.str_to_user(frappe.datetime.now_datetime())
			]);
	}

	render_financial_kpis(data, prevData = {}) {
		const el = this.wrapper.querySelector('[data-role="financial-kpis"]');
		const summaryEl = this.wrapper.querySelector('[data-role="financial-kpis-summary"]');
		if (!el) return;

		const booking = data.order_booking || {};
		const prevBooking = prevData.order_booking || {};
		const invoicing = data.invoicing || {};
		const prevInvoicing = prevData.invoicing || {};
		const coll = data.outstanding_collection || {};
		const prevColl = prevData.outstanding_collection || {};

		const totalOrders = Object.values(data.orders_status || {}).reduce((s, o) => s + (o.count || 0), 0);
		const prevTotalOrders = Object.values(prevData.orders_status || {}).reduce((s, o) => s + (o.count || 0), 0);
		const totalVal = Object.values(data.orders_status || {}).reduce((s, o) => s + (o.value || 0), 0);
		const periodLabel = this.get_previous_period_label();

		// Comparison helper
		const delta = (cur, prev) => {
			if (prev === 0 && cur === 0) return `<span class="spd-delta spd-delta-stable">▬ 0%</span>`;
			if (prev === 0 && cur > 0) return `<span class="spd-delta spd-delta-up">▲ New</span>`;
			const pct = Math.round(((cur - prev) / prev) * 100);
			const cls = pct > 0 ? 'spd-delta-up' : pct < 0 ? 'spd-delta-down' : 'spd-delta-stable';
			const arrow = pct > 0 ? '▲' : pct < 0 ? '▼' : '▬';
			return `<span class="spd-delta ${cls}">${arrow} ${pct > 0 ? '+' : ''}${pct}% <em>vs ${periodLabel}</em></span>`;
		};

		// Summary row — Orders In Period
		if (summaryEl) {
			const pct = prevTotalOrders > 0 ? Math.round(((totalOrders - prevTotalOrders) / prevTotalOrders) * 100) : 0;
			const pctCls = pct > 0 ? 'spd-delta-up' : pct < 0 ? 'spd-delta-down' : 'spd-delta-stable';
			const pctArrow = pct > 0 ? '▲' : pct < 0 ? '▼' : '▬';
			summaryEl.innerHTML = `
				<div class="spd-summary-card ocd-card">
					<div class="spd-summary-icon">${spd_icon("package")}</div>
					<div class="spd-summary-body">
						<div class="spd-summary-label">${__("Orders In Period")}</div>
						<div class="spd-summary-value">${totalOrders.toLocaleString()} <span class="spd-summary-sub">orders · ₹ ${totalVal.toFixed(2)} Lakh total</span></div>
					</div>
					<span class="spd-delta ${pctCls}">${pctArrow} ${pct > 0 ? '+' : ''}${pct}% <em>vs ${periodLabel}</em></span>
				</div>
			`;
		}

		// Grouped metric cards
		el.innerHTML = `
			<!-- Order Booking Value -->
			<div class="ocd-card spd-metric-group-card" style="--grp-accent:var(--ocd-accent-moss)">
				<div class="spd-grp-header">
					<span class="spd-grp-icon" style="color:var(--ocd-accent-moss)">${spd_icon("trendingUp")}</span>
					<span class="spd-grp-title">${__("Order Booking Value")}</span>
				</div>
				<div class="spd-grp-body">
					<div class="spd-grp-metric">
						<div class="spd-grp-metric-label">${__("FY TOTAL (INR)")}</div>
						<div class="spd-grp-metric-value" style="color:var(--ocd-accent-moss)">₹ ${(booking.FY || 0).toFixed(2)}</div>
						<div class="spd-grp-metric-unit">${__(".Lakh")}</div>
						${booking.FY_USD ? `<div class="spd-grp-metric-usd">$${(booking.FY_USD || 0).toFixed(2)} USD</div>` : ''}
						${delta(booking.FY || 0, prevBooking.FY || 0)}
					</div>
					<div class="spd-grp-divider"></div>
					<div class="spd-grp-metric">
						<div class="spd-grp-metric-label">${__("CURRENT MONTH (INR)")}</div>
						<div class="spd-grp-metric-value" style="color:var(--ocd-accent-moss)">₹ ${(booking['Current Month'] || 0).toFixed(2)}</div>
						<div class="spd-grp-metric-unit">${__(".Lakh")}</div>
						${booking['Current Month_USD'] ? `<div class="spd-grp-metric-usd">$${(booking['Current Month_USD'] || 0).toFixed(2)} USD</div>` : ''}
						${delta(booking['Current Month'] || 0, prevBooking['Current Month'] || 0)}
					</div>
				</div>
			</div>

			<!-- Invoicing -->
			<div class="ocd-card spd-metric-group-card" style="--grp-accent:var(--ocd-accent-violet)">
				<div class="spd-grp-header">
					<span class="spd-grp-icon" style="color:var(--ocd-accent-violet)">${spd_icon("dollarSign")}</span>
					<span class="spd-grp-title">${__("Invoicing")}</span>
				</div>
				<div class="spd-grp-body">
					<div class="spd-grp-metric">
						<div class="spd-grp-metric-label">${__("FY TOTAL (INR)")}</div>
						<div class="spd-grp-metric-value" style="color:var(--ocd-accent-violet)">₹ ${(invoicing.FY || 0).toFixed(2)}</div>
						<div class="spd-grp-metric-unit">${__(".Lakh")}</div>
						${invoicing.FY_USD ? `<div class="spd-grp-metric-usd">$${(invoicing.FY_USD || 0).toFixed(2)} USD</div>` : ''}
						${delta(invoicing.FY || 0, prevInvoicing.FY || 0)}
					</div>
					<div class="spd-grp-divider"></div>
					<div class="spd-grp-metric">
						<div class="spd-grp-metric-label">${__("CURRENT MONTH (INR)")}</div>
						<div class="spd-grp-metric-value" style="color:var(--ocd-accent-violet)">₹ ${(invoicing['Current Month'] || 0).toFixed(2)}</div>
						<div class="spd-grp-metric-unit">${__(".Lakh")}</div>
						${invoicing['Current Month_USD'] ? `<div class="spd-grp-metric-usd">$${(invoicing['Current Month_USD'] || 0).toFixed(2)} USD</div>` : ''}
						${delta(invoicing['Current Month'] || 0, prevInvoicing['Current Month'] || 0)}
					</div>
				</div>
			</div>

			<!-- Outstanding vs Collection -->
			<div class="ocd-card spd-metric-group-card" style="--grp-accent:var(--ocd-accent-amber)">
				<div class="spd-grp-header">
					<span class="spd-grp-icon" style="color:var(--ocd-accent-amber)">${spd_icon("checkCircle")}</span>
					<span class="spd-grp-title">${__("Outstanding vs Collection (Current Month)")}</span>
				</div>
				<div class="spd-grp-body">
					<div class="spd-grp-metric">
						<div class="spd-grp-metric-label">${__("OUTSTANDING")}</div>
						<div class="spd-grp-metric-value" style="color:var(--ocd-accent-amber)">₹ ${(coll.Outstanding || 0).toFixed(2)}</div>
						<div class="spd-grp-metric-unit">.Lakh</div>
						${delta(coll.Outstanding || 0, prevColl.Outstanding || 0)}
					</div>
					<div class="spd-grp-divider"></div>
					<div class="spd-grp-metric">
						<div class="spd-grp-metric-label">${__("COLLECTED")}</div>
						<div class="spd-grp-metric-value" style="color:var(--ocd-sev-ok)">₹ ${(coll.Collected || 0).toFixed(2)}</div>
						<div class="spd-grp-metric-unit">.Lakh</div>
						${delta(coll.Collected || 0, prevColl.Collected || 0)}
					</div>
				</div>
			</div>
		`;
	}

	kpi_card({ label, value, previous_value, is_rate, sub, color, icon = "activity", tone = null }) {
		const current = is_rate ? parseFloat(value) : (typeof value === "string" ? parseFloat(value.replace(/[^0-9.-]+/g, "")) : value);
		const deltaHtml = previous_value === undefined || previous_value === null
			? ""
			: this.render_kpi_delta(current, previous_value, !!is_rate);

		const toneHtml = tone ? `<span class="ocd-kpi-tone ocd-kpi-tone-${tone}"></span>` : "";

		return `
			<div class="ocd-kpi-card" style="--kpi-accent:${color}">
				${toneHtml}
				<div class="ocd-kpi-top">
					<div class="ocd-kpi-icon" style="color:${color}">${spd_icon(icon)}</div>
					<div class="ocd-kpi-label">${frappe.utils.escape_html(label)}</div>
				</div>
				<div class="ocd-kpi-value" style="color: ${color}">${value}</div>
				<div class="ocd-kpi-footer">
					<div class="ocd-kpi-sub">${frappe.utils.escape_html(sub)}</div>
					${deltaHtml}
				</div>
			</div>
		`;
	}

	render_kpi_delta(current, previous, isRate) {
		const periodLabel = this.get_previous_period_label();
		let direction, display;

		if (isRate) {
			const diff = Math.round((current - previous) * 10) / 10;
			direction = diff > 0 ? "up" : diff < 0 ? "down" : "stable";
			display = `${diff > 0 ? "+" : ""}${diff} pts`;
		} else if (previous === 0 && current === 0) {
			direction = "stable";
			display = "0%";
		} else if (previous === 0 && current > 0) {
			direction = "up";
			display = __("New");
		} else {
			const pct = Math.round(((current - previous) / previous) * 100);
			direction = pct > 0 ? "up" : pct < 0 ? "down" : "stable";
			display = `${pct > 0 ? "+" : ""}${pct}%`;
		}

		// Higher orders/revenue is good (up -> sev-ok)
		const arrow = direction === "up" ? "▲" : direction === "down" ? "▼" : "▬";
		const deltaClass = direction === "up" ? "spd-kpi-delta-good" : direction === "down" ? "spd-kpi-delta-bad" : "ocd-kpi-delta-stable";

		return `
			<span class="ocd-kpi-delta ${deltaClass}">
				${arrow} ${display} <span class="ocd-kpi-delta-label">${__("vs")} ${periodLabel}</span>
			</span>
		`;
	}

	render_all_charts(data, prevData = {}) {
		if (!window.Chart) {
			setTimeout(() => this.render_all_charts(data, prevData), 150);
			return;
		}

		this.render_orders_status_chart(data.orders_status || {});
		this.render_order_approval_delay_chart(data.order_approval_delay || {});

		this.render_otd_pie("deliveryOtdChart", "delivery-otd-pill", "delivery-otd-footer", data.delivery_otd, (prevData.delivery_otd || {}), __("Delivery"));
		this.render_otd_pie("orderEntryOtdChart", "order-entry-otd-pill", "order-entry-otd-footer", data.order_entry_otd, (prevData.order_entry_otd || {}), __("Entry"));
		this.render_otd_pie("orderApprovalOtdChart", "order-approval-otd-pill", "order-approval-otd-footer", data.order_approval_otd, (prevData.order_approval_otd || {}), __("Approval"));

		this.render_bom_pending_chart(data.bom_pending || {});
	}

	render_orders_status_chart(data) {
		const el = document.getElementById("ordersStatusChart");
		if (!el) return;

		const labels = Object.keys(data);
		const values = labels.map(k => data[k]?.value || 0);

		const colors = {
			'Draft': '#8a8fa3',
			'Pending Approval': '#d98c0e',
			'Pending': '#d98c0e',
			'Approved': '#16a34a',
			'Booked': '#2f6feb'
		};

		if (this.charts.statusChart && typeof this.charts.statusChart.destroy === "function") {
			this.charts.statusChart.destroy();
		}

		const isDark = this.get_theme() === "dark";
		const legendTextColor = isDark ? "#eef0f5" : "#14161f";

		this.charts.statusChart = new Chart(el.getContext("2d"), {
			type: "doughnut",
			data: {
				labels: labels.map(l => `${l} (${data[l]?.count || 0})`),
				datasets: [{
					data: values,
					backgroundColor: labels.map(l => colors[l] || "#7c4fe0"),
					borderWidth: 2,
					borderColor: isDark ? "#171a21" : "#ffffff"
				}]
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				plugins: {
					legend: {
						position: "bottom",
						labels: {
							padding: 12,
							usePointStyle: true,
							color: legendTextColor,
							font: { size: 11, family: "Inter, sans-serif" }
						}
					},
					tooltip: {
						callbacks: {
							label: function(context) {
								const value = context.raw || 0;
								return `₹ ${value.toFixed(2)} Lakh`;
							}
						}
					}
				}
			}
		});
	}

	render_order_approval_delay_chart(data) {
		const el = document.getElementById("orderApprovalDelayChart");
		if (!el) return;
		this.render_distribution_bar_chart(el, data, "orderApprovalDelayChart", "#2f6feb", __("Delay (Days)"));
	}

	render_bom_pending_chart(data) {
		const el = document.getElementById("bomPendingChart");
		if (!el) return;
		this.render_distribution_bar_chart(el, data, "bomPendingChart", "#ea7317", __("Creation Delay (Days)"));
	}

	render_distribution_bar_chart(el, data, chartKey, color, xAxisTitle) {
		if (!data) return;

		const labels = Object.keys(data);
		const values = labels.map(k => {
			const value = data[k]?.value || 0;
			const count = data[k]?.count || 0;
			return (value === 0 && count === 0) ? null : value;
		});

		const counts = labels.map(k => data[k]?.count || 0);

		if (this.charts[chartKey] && typeof this.charts[chartKey].destroy === "function") {
			this.charts[chartKey].destroy();
		}

		const isDark = this.get_theme() === "dark";
		const gridColor = isDark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)";
		const textColor = isDark ? "#b7bccb" : "#4c5166";

		this.charts[chartKey] = new Chart(el.getContext("2d"), {
			type: "bar",
			data: {
				labels: labels,
				datasets: [{
					label: __("Value (Lakhs)"),
					data: values,
					backgroundColor: color,
					borderRadius: 6,
					borderWidth: 0,
					barThickness: 36,
					minBarLength: 6
				}]
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				interaction: { mode: "nearest", axis: "x", intersect: false },
				scales: {
					y: {
						beginAtZero: true,
						grid: { color: gridColor },
						ticks: { color: textColor },
						title: { display: true, text: __("Amount (₹ Lakh)"), font: { size: 10 }, color: textColor }
					},
					x: {
						grid: { display: false },
						ticks: { color: textColor },
						title: { display: true, text: xAxisTitle, font: { size: 10 }, color: textColor }
					}
				},
				plugins: {
					legend: { display: false },
					tooltip: {
						filter: (ctx) => ctx.raw !== null,
						callbacks: {
							label: function(context) {
								const idx = context.dataIndex;
								const val = context.raw || 0;
								const count = counts[idx];
								return [
									`Value: ₹ ${val.toFixed(2)} Lakh`,
									`Count: ${count} Orders`
								];
							}
						}
					}
				}
			}
		});
	}

	render_otd_pie(canvasId, pillId, footerId, data = {}, prevData = {}, title) {
		const el = document.getElementById(canvasId);
		if (!el) return;

		const onTimeObj = data["On Time"] || { count: 0, value: 0 };
		const delayedObj = data["Delayed"] || { count: 0, value: 0 };
		const totalCount = (onTimeObj.count || 0) + (delayedObj.count || 0);

		const onTimeRate = totalCount > 0 ? Math.round((onTimeObj.count / totalCount) * 100) : 0;

		const prevOnTimeObj = prevData["On Time"] || { count: 0, value: 0 };
		const prevDelayedObj = prevData["Delayed"] || { count: 0, value: 0 };
		const prevTotalCount = (prevOnTimeObj.count || 0) + (prevDelayedObj.count || 0);
		const prevOnTimeRate = prevTotalCount > 0 ? Math.round((prevOnTimeObj.count / prevTotalCount) * 100) : 0;

		// Pill
		const pillEl = document.getElementById(pillId);
		if (pillEl) {
			const pillColor = onTimeRate >= 85 ? "spd-otd-pill-green" : onTimeRate >= 60 ? "spd-otd-pill-amber" : "spd-otd-pill-red";
			pillEl.className = `spd-otd-pill ${pillColor}`;
			pillEl.textContent = `${onTimeRate}% ${__("On Time")}`;
		}

		// Footer delta comparison
		const footerEl = document.getElementById(footerId);
		if (footerEl) {
			const diff = onTimeRate - prevOnTimeRate;
			const periodLabel = this.get_previous_period_label();
			const direction = diff > 0 ? "up" : diff < 0 ? "down" : "stable";
			const deltaClass = diff > 0 ? "spd-kpi-delta-good" : diff < 0 ? "spd-kpi-delta-bad" : "ocd-kpi-delta-stable";
			const arrow = direction === "up" ? "▲" : direction === "down" ? "▼" : "▬";

			footerEl.innerHTML = `
				<div class="spd-otd-stats">
					<div class="spd-otd-stat-item">
						<span class="spd-dot spd-dot-green"></span>
						<span>${__("On Time:")} <strong>${onTimeObj.count}</strong> (₹ ${onTimeObj.value}L)</span>
					</div>
					<div class="spd-otd-stat-item">
						<span class="spd-dot spd-dot-red"></span>
						<span>${__("Delayed:")} <strong>${delayedObj.count}</strong> (₹ ${delayedObj.value}L)</span>
					</div>
				</div>
				<span class="ocd-kpi-delta ${deltaClass}">
					${arrow} ${diff > 0 ? "+" : ""}${diff} pts <span class="ocd-kpi-delta-label">${__("vs")} ${periodLabel}</span>
				</span>
			`;
		}

		if (this.charts[canvasId] && typeof this.charts[canvasId].destroy === "function") {
			this.charts[canvasId].destroy();
		}

		const isDark = this.get_theme() === "dark";
		const legendTextColor = isDark ? "#eef0f5" : "#14161f";

		this.charts[canvasId] = new Chart(el.getContext("2d"), {
			type: "pie",
			data: {
				labels: [`On Time (${onTimeObj.count})`, `Delayed (${delayedObj.count})`],
				datasets: [{
					data: [onTimeObj.value, delayedObj.value],
					backgroundColor: ["#16a34a", "#e0393e"],
					borderWidth: 2,
					borderColor: isDark ? "#171a21" : "#ffffff"
				}]
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				plugins: {
					legend: {
						position: "bottom",
						labels: {
							padding: 10,
							usePointStyle: true,
							color: legendTextColor,
							font: { size: 11, family: "Inter, sans-serif" }
						}
					},
					tooltip: {
						callbacks: {
							label: function(context) {
								const value = context.raw || 0;
								return `₹ ${value.toFixed(2)} Lakh`;
							}
						}
					}
				}
			}
		});
	}
}

// ---------------------------------------------------------------------------
// CSS STYLES
// ---------------------------------------------------------------------------
const SPD_CSS = `
/* =========================================================================
   1. TOKENS / BASE
   ========================================================================= */
.ocd-root {
	--ocd-bg: #f5f6fa;
	--ocd-surface: #ffffff;
	--ocd-surface-2: #f1f2f7;
	--ocd-surface-3: #e9ebf3;
	--ocd-border: #e7e9f0;
	--ocd-border-strong: #d7dae5;
	--ocd-ink: #14161f;
	--ocd-ink-secondary: #4c5166;
	--ocd-muted: #8a8fa3;

	--ocd-accent-steel: #2f6feb;
	--ocd-accent-amber: #d98c0e;
	--ocd-accent-moss: #16a34a;
	--ocd-accent-violet: #7c4fe0;
	--ocd-accent-teal: #0d9488;
	--ocd-accent-rust: #e34a4a;

	--ocd-sev-ok: #16a34a;
	--ocd-sev-watch: #d98c0e;
	--ocd-sev-warn: #ea7317;
	--ocd-sev-critical: #e0393e;

	--ocd-shadow-sm: 0 1px 2px rgba(20,22,40,0.05);
	--ocd-shadow-md: 0 8px 24px rgba(20,22,40,0.06);
	--ocd-shadow-lg: 0 16px 40px rgba(20,22,40,0.10);
	--ocd-shadow-glow: 0 0 0 1px rgba(47,111,235,0.08), 0 12px 28px rgba(47,111,235,0.10);

	--ocd-radius-sm: 8px;
	--ocd-radius-md: 12px;
	--ocd-radius-lg: 16px;
	--ocd-radius-xl: 18px;

	--ocd-space-1: 4px; --ocd-space-2: 8px; --ocd-space-3: 12px; --ocd-space-4: 16px;
	--ocd-space-5: 20px; --ocd-space-6: 24px; --ocd-space-8: 32px;

	--ocd-mono: ui-monospace,SFMono-Regular,"JetBrains Mono",Menlo,Consolas,monospace;
	--ocd-font: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", Roboto, Helvetica, Arial, sans-serif;

	background:var(--ocd-bg);
	color:var(--ocd-ink);
	padding:28px 32px 56px;
	border-radius:8px;
	font-family:var(--ocd-font);
	min-height:100vh;
	position:relative;
	-webkit-font-smoothing:antialiased;
}
.ocd-root[data-theme="dark"] {
	--ocd-bg:#0f1115;
	--ocd-surface:#171a21;
	--ocd-surface-2:#1e222b;
	--ocd-surface-3:#262b36;
	--ocd-border:rgba(255,255,255,.08);
	--ocd-border-strong:rgba(255,255,255,.14);
	--ocd-ink:#eef0f5;
	--ocd-ink-secondary:#b7bccb;
	--ocd-muted:#818a9e;
	--ocd-shadow-sm: 0 1px 2px rgba(0,0,0,.35);
	--ocd-shadow-md: 0 8px 24px rgba(0,0,0,.45);
	--ocd-shadow-lg: 0 20px 48px rgba(0,0,0,.55);
	--ocd-shadow-glow: 0 0 0 1px rgba(69,138,255,0.18), 0 16px 32px rgba(69,138,255,0.14);
}
.ocd-root, .ocd-root *, .ocd-root *::before, .ocd-root *::after { box-sizing:border-box; }
.ocd-root > * { position:relative; z-index:1; }

.ocd-icon { width:16px; height:16px; flex:none; display:inline-block; vertical-align:middle; }

/* =========================================================================
   2. HEADER
   ========================================================================= */
.ocd-header {
	display:flex;justify-content:space-between;align-items:flex-start;
	gap:var(--ocd-space-4);flex-wrap:wrap;
	padding-bottom:var(--ocd-space-2);
}
.ocd-header-left { display:flex;align-items:flex-start;gap:var(--ocd-space-4); }
.ocd-header-icon {
	width:52px;height:52px;border-radius:var(--ocd-radius-lg);flex:none;
	display:flex;align-items:center;justify-content:center;
	background:linear-gradient(135deg,var(--ocd-accent-steel),var(--ocd-accent-violet));
	color:#fff;box-shadow:var(--ocd-shadow-glow);
}
.ocd-header-icon .ocd-icon { width:26px;height:26px; }
.ocd-header-titlerow { display:flex;align-items:center;gap:var(--ocd-space-3);flex-wrap:wrap; }
.ocd-title { margin:0;font-size:28px;font-weight:800;letter-spacing:-.02em;line-height:1.15; }
.ocd-subtitle { margin:4px 0 0;font-size:14px;color:var(--ocd-ink-secondary);font-weight:500; }
.ocd-header-meta { font-size:13px;color:var(--ocd-muted);margin-top:6px; }

.ocd-status-chip {
	display:inline-flex;align-items:center;gap:6px;
	font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;
	padding:4px 10px;border-radius:999px;
	background:rgba(22,163,74,.12);color:var(--ocd-sev-ok);
}
.ocd-status-dot {
	width:7px;height:7px;border-radius:50%;background:var(--ocd-sev-ok);
	animation:ocd-pulse 2s ease-in-out infinite;
}
@keyframes ocd-pulse {
	0%{box-shadow:0 0 0 0 rgba(22,163,74,.45);}
	70%{box-shadow:0 0 0 6px rgba(22,163,74,0);}
	100%{box-shadow:0 0 0 0 rgba(22,163,74,0);}
}

.ocd-header-actions { display:flex;align-items:center;gap:var(--ocd-space-2);padding-top:2px;flex-wrap:wrap; }

/* Theme Toggle */
.ocd-theme-toggle {
	display:flex;align-items:center;gap:10px;
	background:var(--ocd-surface);border:1px solid var(--ocd-border);cursor:pointer;
	padding:7px 14px 7px 8px;border-radius:999px;font-family:inherit;box-shadow:var(--ocd-shadow-sm);
	transition:border-color .2s,background .2s;
}
.ocd-theme-toggle:hover { background:var(--ocd-surface-2); }
.ocd-theme-track {
	position:relative;width:40px;height:22px;flex:none;
	border-radius:999px;background:var(--ocd-surface-3);
	transition:background .2s;
}
.ocd-theme-thumb {
	position:absolute;top:2px;left:2px;width:18px;height:18px;
	border-radius:50%;background:var(--ocd-accent-amber);color:#fff;
	display:flex;align-items:center;justify-content:center;
	font-size:10px;line-height:1;box-shadow:0 1px 3px rgba(0,0,0,.25);
	transition:transform .25s cubic-bezier(.4,0,.2,1), background .25s, color .25s;
}
.ocd-root[data-theme="dark"] .ocd-theme-thumb { transform:translateX(18px);background:var(--ocd-accent-steel);color:#fff; }
.ocd-theme-text { font-size:13px;font-weight:600;color:var(--ocd-ink);white-space:nowrap; }

/* =========================================================================
   3. TOOLBAR / FILTERS
   ========================================================================= */
.ocd-toolbar {
	position:relative;
	display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;
	gap:8px 10px;
	padding:10px 16px;
	margin:var(--ocd-space-4) 0 var(--ocd-space-2);
	background:var(--ocd-surface);
	border:1px solid var(--ocd-border);
	border-radius:var(--ocd-radius-lg);
	box-shadow:var(--ocd-shadow-md);
	z-index:10;
	-webkit-backdrop-filter:blur(12px);
	backdrop-filter:blur(12px);
}

.ocd-toolbar-group { 
	display:flex;align-items:center;gap:8px;flex-wrap:wrap; 
	position:relative;
	z-index:101;
}

.ocd-toolbar-group--right { 
	margin-left:auto;
	display:flex;align-items:center;gap:8px;flex-wrap:nowrap;
	position:relative;
	z-index:101;
}

.ocd-custom-select-wrapper {
	position:relative;
	display:flex;align-items:center;gap:6px;
	background:var(--ocd-surface);
	border:1px solid var(--ocd-border-strong);
	border-radius:6px;
	padding:0;
	transition:border-color .2s, box-shadow .2s;
	min-width:0;
	height:34px;
	box-sizing:border-box;
	cursor:pointer;
}

.ocd-custom-select-wrapper:hover { 
	border-color:var(--ocd-accent-steel);
}

.ocd-custom-select-wrapper:focus-within {
	border-color:var(--ocd-accent-steel);
	box-shadow:0 0 0 2px rgba(47,111,235,0.1);
}

.ocd-custom-select-wrapper .ocd-field-icon { 
	display:flex;align-items:center;color:var(--ocd-muted);flex:none;
	opacity:0.7;
	padding-left:8px;
}

.ocd-custom-select-wrapper .ocd-field-icon .ocd-icon { 
	width:14px;height:14px;
}

.ocd-custom-select-wrapper .ocd-field-label {
	font-size:11.5px;
	font-weight:600;
	color:var(--ocd-ink-secondary);
	white-space:nowrap;
	letter-spacing:0.01em;
	padding:0;
}

.ocd-custom-select {
	position:relative;
	flex:1;
}

.ocd-custom-select-trigger {
	display:flex;align-items:center;justify-content:space-between;
	padding:0 8px 0 2px;
	gap:6px;
	min-width:0;
	height:34px;
	box-sizing:border-box;
}

.ocd-custom-select-text {
	font-size:13px;
	font-weight:500;
	color:var(--ocd-ink);
	overflow:hidden;
	text-overflow:ellipsis;
	white-space:nowrap;
}

.ocd-custom-select-arrow {
	width:13px;height:13px;
	color:var(--ocd-muted);
	flex:none;
	transition:transform 0.2s ease;
}

.ocd-custom-select.open .ocd-custom-select-arrow {
	transform:rotate(180deg);
}

.ocd-custom-select-options {
	position:absolute;
	top:calc(100% + 4px);
	left:0;
	right:auto;
	width:max-content;
	min-width:100%;
	background:var(--ocd-surface);
	border:1px solid var(--ocd-border-strong);
	border-radius:6px;
	box-shadow:var(--ocd-shadow-lg);
	z-index:1000;
	max-height:240px;
	overflow-y:auto;
	display:none;
	padding:4px;
}

.ocd-custom-select.open .ocd-custom-select-options {
	display:block;
	animation:ocd-dropdown-in 0.15s ease;
}

@keyframes ocd-dropdown-in {
	from { opacity:0; transform:translateY(-4px); }
	to   { opacity:1; transform:translateY(0); }
}

.ocd-custom-option {
	padding:7px 10px;
	font-size:13px;
	font-weight:500;
	color:var(--ocd-ink);
	border-radius:4px;
	cursor:pointer;
	transition:background 0.15s ease, color 0.15s ease;
	display:flex;align-items:center;
}

.ocd-custom-option:hover {
	background:var(--ocd-surface-2);
	color:var(--ocd-accent-steel);
}

.ocd-custom-option.selected {
	background:rgba(47,111,235,0.1);
	color:var(--ocd-accent-steel);
	font-weight:600;
}

.ocd-custom-option.selected::before {
	content:'✓';
	margin-right:6px;
	font-size:11px;
	font-weight:700;
}

.ocd-custom-select-wrapper[data-field-name="view_type"] { min-width:115px; }
.ocd-custom-select-wrapper[data-field-name="branch"] { min-width:135px; }
.ocd-custom-select-wrapper[data-field-name="period"] { min-width:145px; }

.ocd-custom-dates { 
	display:flex;align-items:center;gap:6px;
	position:relative;
	z-index:101;
	height:34px;
}

.ocd-date-input {
	font-size:12px;
	padding:0 6px;
	height:34px;
	line-height:34px;
	width:118px;
	box-sizing:border-box;
	border-radius:6px;
	border:1px solid var(--ocd-border-strong);
	background:var(--ocd-surface);
	color:var(--ocd-ink);
	font-family:inherit;
	transition:border-color .2s, box-shadow .2s;
}

.ocd-date-input:focus {
	outline:none;
	border-color:var(--ocd-accent-steel);
	box-shadow:0 0 0 2px rgba(47,111,235,0.1);
}

.ocd-date-input:disabled { 
	opacity:0.6;
	cursor:not-allowed;
	background:var(--ocd-surface-2);
}

.ocd-date-sep {
	display:flex;align-items:center;
}

.ocd-date-sep .ocd-icon { 
	width:13px;height:13px;color:var(--ocd-muted);
}

.ocd-chip-btn {
	display:inline-flex;align-items:center;gap:5px;
	font-size:12.5px;font-weight:600;
	padding:0 12px;
	height:34px;
	box-sizing:border-box;
	border-radius:6px;
	border:1px solid var(--ocd-border-strong);
	background:var(--ocd-surface);
	color:var(--ocd-ink);
	cursor:pointer;
	font-family:inherit;
	transition:all .2s ease;
	white-space:nowrap;
}

.ocd-chip-btn:hover { 
	background:var(--ocd-surface-2);
	border-color:var(--ocd-accent-steel);
}

.ocd-chip-btn--ghost { 
	border-color:transparent;
	background:transparent;
	color:var(--ocd-ink-secondary);
}

.ocd-chip-btn--ghost:hover { 
	background:var(--ocd-surface-2);
	border-color:var(--ocd-border-strong);
}

.ocd-btn {
	display:inline-flex;align-items:center;gap:6px;
	font-size:12.5px;font-weight:600;
	padding:0 15px;
	height:34px;
	box-sizing:border-box;
	border-radius:6px;
	border:1px solid var(--ocd-border);
	background:var(--ocd-surface);
	color:var(--ocd-ink);
	cursor:pointer;
	transition:all .2s ease;
	font-family:inherit;
	white-space:nowrap;
}
	background:var(--ocd-surface);
	color:var(--ocd-ink);
	cursor:pointer;
	transition:all .2s ease;
	font-family:inherit;
}

.ocd-btn-primary {
	background:linear-gradient(135deg,var(--ocd-accent-steel),var(--ocd-accent-violet));
	border-color:transparent;
	color:#fff;
	box-shadow:var(--ocd-shadow-glow);
}

.ocd-btn-primary:hover { 
	filter:brightness(1.06);
	transform:translateY(-1px);
}

/* =========================================================================
   4. SECTIONS & CARDS
   ========================================================================= */
.ocd-section { margin-top:var(--ocd-space-8); animation:ocd-section-in .5s ease forwards; opacity:0; }
@keyframes ocd-section-in { from{opacity:0;transform:translateY(14px)} to{opacity:1;transform:translateY(0)} }

.ocd-section-head { display:flex;align-items:center;gap:12px;margin:0 0 var(--ocd-space-4); }
.ocd-section-index {
	font-family:var(--ocd-mono);font-size:11px;font-weight:700;color:var(--ocd-muted);
	background:var(--ocd-surface-2);border:1px solid var(--ocd-border);
	padding:3px 8px;border-radius:6px;letter-spacing:.03em;
}
.ocd-section-title { font-size:20px;font-weight:800;color:var(--ocd-ink);letter-spacing:-.01em; }
.ocd-section-line { flex:1;height:1px;background:linear-gradient(90deg,var(--ocd-border),transparent); }

.ocd-card {
	position:relative;background:var(--ocd-surface);border:1px solid var(--ocd-border);
	border-radius:var(--ocd-radius-lg);box-shadow:var(--ocd-shadow-md);
	padding:var(--ocd-space-5);overflow:hidden;
	transition:transform .22s ease,box-shadow .22s ease,border-color .22s ease;
}

.ocd-skel {
	background:linear-gradient(100deg,var(--ocd-surface-2) 20%,var(--ocd-surface-3) 42%,var(--ocd-surface-2) 64%);
	background-size:300% 100%;animation:ocd-shimmer 1.3s ease infinite;
	border-style:dashed;
}
@keyframes ocd-shimmer { 0%{background-position:120% 50%} 100%{background-position:-20% 50%} }

/* KPI Row */
.ocd-kpi-row { display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:var(--ocd-space-4);margin-bottom:var(--ocd-space-2); }
.ocd-kpi-card {
	position:relative;background:var(--ocd-surface);border:1px solid var(--ocd-border);
	border-radius:var(--ocd-radius-lg);box-shadow:var(--ocd-shadow-md);
	padding:var(--ocd-space-5);overflow:hidden;
	transition:transform .22s ease,box-shadow .22s ease,border-color .22s ease;
	display:flex;flex-direction:column;gap:var(--ocd-space-3);
}
.ocd-kpi-card:hover { transform:translateY(-3px); box-shadow:var(--ocd-shadow-lg); border-color:var(--ocd-border-strong); }
.ocd-kpi-tone { position:absolute;top:0;left:18px;right:18px;height:3px;border-radius:0 0 6px 6px; }
.ocd-kpi-tone-ok { background:var(--ocd-sev-ok); }
.ocd-kpi-tone-watch { background:var(--ocd-sev-watch); }
.ocd-kpi-tone-critical { background:var(--ocd-sev-critical); }

.ocd-kpi-top { display:flex;align-items:center;gap:var(--ocd-space-3); }
.ocd-kpi-icon {
	position:relative;width:38px;height:38px;border-radius:11px;flex:none;
	display:flex;align-items:center;justify-content:center;
}
.ocd-kpi-icon::before { content:"";position:absolute;inset:0;border-radius:inherit;background:currentColor;opacity:.14; }
.ocd-kpi-icon .ocd-icon { position:relative;z-index:1;width:19px;height:19px; }
.ocd-kpi-label { font-size:12px;color:var(--ocd-ink-secondary);text-transform:uppercase;letter-spacing:.05em;font-weight:700; }
.ocd-kpi-value { font-size:32px;font-weight:800;line-height:1.1;letter-spacing:-.02em; }
.ocd-kpi-footer { display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap; }
.ocd-kpi-sub { font-size:12px;color:var(--ocd-muted);font-weight:500; }

.ocd-kpi-delta {
	display:inline-flex;align-items:center;gap:4px;flex-wrap:wrap;
	font-size:11px;font-weight:700;padding:3px 8px;
	border-radius:999px;background:var(--ocd-surface-2);width:fit-content;
}
.ocd-kpi-delta-label { font-weight:500;color:var(--ocd-muted); }
.spd-kpi-delta-good { color:var(--ocd-sev-ok); }
.spd-kpi-delta-bad  { color:var(--ocd-sev-critical); }
.ocd-kpi-delta-stable  { color:var(--ocd-sev-watch); }

/* Chart Grids */
.spd-charts-grid-2 {
	display:grid;grid-template-columns:repeat(auto-fit,minmax(380px,1fr));gap:var(--ocd-space-4);
}
.spd-charts-grid-3 {
	display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:var(--ocd-space-4);
}

.spd-chart-card {
	display:flex;flex-direction:column;justify-content:space-between;
}
.spd-card-header {
	margin-bottom:12px;
}
.spd-header-titlerow {
	display:flex;align-items:center;justify-content:space-between;gap:8px;
}
.spd-card-title {
	font-size:15px;font-weight:800;color:var(--ocd-ink);display:flex;align-items:center;gap:8px;
}
.spd-title-icon { width:16px;height:16px;color:var(--ocd-accent-steel); }
.spd-card-sub {
	font-size:12px;color:var(--ocd-muted);margin-top:2px;display:block;
}

.spd-chart-wrapper {
	position:relative;
	width:100%;
}

.spd-otd-pill {
	font-size:11px;font-weight:800;padding:3px 9px;border-radius:999px;
	letter-spacing:0.02em;text-transform:uppercase;white-space:nowrap;
}
.spd-otd-pill-green { background:rgba(22,163,74,.12);color:var(--ocd-sev-ok);border:1px solid rgba(22,163,74,.3); }
.spd-otd-pill-amber { background:rgba(217,140,14,.12);color:var(--ocd-sev-watch);border:1px solid rgba(217,140,14,.3); }
.spd-otd-pill-red   { background:rgba(224,57,62,.12);color:var(--ocd-sev-critical);border:1px solid rgba(224,57,62,.3); }

.spd-chart-footer {
	margin-top:12px;padding-top:10px;border-top:1px solid var(--ocd-border);
	display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;
}
.spd-otd-stats {
	display:flex;flex-direction:column;gap:3px;font-size:11.5px;color:var(--ocd-ink-secondary);
}
.spd-otd-stat-item {
	display:flex;align-items:center;gap:6px;
}
.spd-dot { width:7px;height:7px;border-radius:50%;display:inline-block; }
.spd-dot-green { background:var(--ocd-sev-ok); }
.spd-dot-red   { background:var(--ocd-sev-critical); }

/* =========================================================================
   5. RESPONSIVE
   ========================================================================= */
@media (max-width: 1024px) {
	.ocd-root { padding:22px 20px 44px; }
}
@media (max-width: 768px) {
	.ocd-header { flex-direction:column;align-items:stretch; }
	.ocd-header-actions { justify-content:flex-end; }
	.ocd-toolbar { flex-direction:column;align-items:stretch; }
	.ocd-toolbar-group--right { margin-left:0;justify-content:flex-end;flex-wrap:wrap; }
	.spd-charts-grid-2, .spd-charts-grid-3 { grid-template-columns:1fr; }
	.spd-grp-body { flex-direction:column; }
	.spd-grp-divider { width:100%;height:1px; }
}

/* =========================================================================
   6. GROUPED METRIC CARDS (Section 01)
   ========================================================================= */

/* Summary row — Orders In Period */
.spd-kpi-summary-row { margin-bottom:var(--ocd-space-3); }
.spd-summary-card {
	display:flex;align-items:center;gap:var(--ocd-space-4);
	padding:var(--ocd-space-4) var(--ocd-space-5);
	border-left:4px solid var(--ocd-accent-steel);
}
.spd-summary-icon {
	width:40px;height:40px;border-radius:10px;flex:none;
	display:flex;align-items:center;justify-content:center;
	background:rgba(47,111,235,.12);color:var(--ocd-accent-steel);
}
.spd-summary-icon .ocd-icon { width:20px;height:20px; }
.spd-summary-body { flex:1;min-width:0; }
.spd-summary-label {
	font-size:11px;font-weight:700;text-transform:uppercase;
	letter-spacing:.05em;color:var(--ocd-ink-secondary);margin-bottom:2px;
}
.spd-summary-value {
	font-size:26px;font-weight:800;color:var(--ocd-ink);line-height:1.1;
}
.spd-summary-sub { font-size:13px;font-weight:500;color:var(--ocd-muted);margin-left:6px; }

/* Stacked metric group container */
.spd-metric-groups {
	display:flex;flex-direction:column;gap:var(--ocd-space-3);
}

/* Each grouped card (Order Booking, Invoicing, Outstanding) */
.spd-metric-group-card {
	padding:0;overflow:hidden;
	border-top:3px solid var(--grp-accent, var(--ocd-accent-steel));
}
.spd-metric-group-card:hover { transform:translateY(-2px);box-shadow:var(--ocd-shadow-lg); }

.spd-grp-header {
	display:flex;align-items:center;gap:10px;
	padding:12px var(--ocd-space-5) 10px;
	border-bottom:1px solid var(--ocd-border);
}
.spd-grp-icon { display:flex;align-items:center;flex:none; }
.spd-grp-icon .ocd-icon { width:16px;height:16px; }
.spd-grp-title {
	font-size:13px;font-weight:800;text-transform:uppercase;
	letter-spacing:.04em;color:var(--ocd-ink);
}

/* Two-column body: FY | Divider | Current Month */
.spd-grp-body {
	display:flex;align-items:stretch;
}
.spd-grp-metric {
	flex:1;padding:var(--ocd-space-4) var(--ocd-space-5);
	display:flex;flex-direction:column;gap:4px;
}
.spd-grp-divider {
	width:1px;background:var(--ocd-border);flex:none;margin:12px 0;
}
.spd-grp-metric-label {
	font-size:10.5px;font-weight:700;text-transform:uppercase;
	letter-spacing:.05em;color:var(--ocd-muted);
}
.spd-grp-metric-value {
	font-size:28px;font-weight:800;letter-spacing:-.02em;line-height:1.1;
}
.spd-grp-metric-unit {
	font-size:12px;color:var(--ocd-muted);font-weight:500;margin-top:-2px;
}
.spd-grp-metric-usd {
	font-size:11.5px;color:var(--ocd-ink-secondary);font-weight:600;
}

/* Inline delta badges for grouped metrics */
.spd-delta {
	display:inline-flex;align-items:center;gap:4px;
	font-size:11px;font-weight:700;padding:3px 9px;
	border-radius:999px;width:fit-content;margin-top:4px;
	white-space:nowrap;
}
.spd-delta em { font-style:normal;font-weight:500;color:inherit;opacity:.75;font-size:10.5px; }
.spd-delta-up   { background:rgba(22,163,74,.1);color:var(--ocd-sev-ok); }
.spd-delta-down { background:rgba(224,57,62,.1);color:var(--ocd-sev-critical); }
.spd-delta-stable { background:var(--ocd-surface-2);color:var(--ocd-sev-watch); }
`;