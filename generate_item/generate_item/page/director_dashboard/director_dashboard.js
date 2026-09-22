frappe.pages['director-dashboard'].on_page_load = function (wrapper) {
	new DirectorDashboard(wrapper);
};

// ---------------------------------------------------------------------------
// Constants & Configuration
// ---------------------------------------------------------------------------
const DIR_API_ORDER_WISE = "generate_item.generate_item.page.director_dashboard.director_dashboard.get_dashboard_data";
const DIR_API_ITEM_WISE  = "generate_item.generate_item.page.director_dashboard.director_dashboard.get_item_wise_data";

const DIR_BRANCHES = ["Sanand", "Nandikoor", "Rabale"];

const DIR_DATE_PRESETS = [
	"Today", "This Week", "Last Week", "This Month", "Last Month",
	"This Quarter", "Last Quarter", "This Year", "Last Year", "Custom"
];

const DIR_BUCKETS = [
	{ key: "0-7",   label: "0–7 d",   accent: "moss",   cls: "bucket-0-7",   color: "#16a34a" },
	{ key: "8-14",  label: "8–14 d",  accent: "steel",  cls: "bucket-8-14",  color: "#2f6feb" },
	{ key: "15-21", label: "15–21 d", accent: "amber",  cls: "bucket-15-21", color: "#d98c0e" },
	{ key: "22-28", label: "22–28 d", accent: "warn",   cls: "bucket-22-28", color: "#ea7317" },
	{ key: "28+",   label: "28+ d",   accent: "rust",   cls: "bucket-28plus",color: "#e0393e" },
];

const DIR_SECTIONS = [
	{ id: "mr", index: "01", key: "pending_mr", title: "Material Requests", short: "MR", docUnit: "MRs", itemUnit: "Items", icon: "inbox" },
	{ id: "po", index: "02", key: "pending_po", title: "Purchase Orders",   short: "PO", docUnit: "POs", itemUnit: "Items", icon: "package" },
	{ id: "pr", index: "03", key: "pending_pr", title: "Purchase Receipts", short: "PR", docUnit: "PRs", itemUnit: "Items", icon: "layers" },
	{ id: "pi", index: "04", key: "pending_pi", title: "Purchase Invoices", short: "PI", docUnit: "PIs", itemUnit: "Items", icon: "activity" },
];

// ---------------------------------------------------------------------------
// Inline Icon Set (matching Sales Team KPI Dashboard)
// ---------------------------------------------------------------------------
const DIR_ICON_PATHS = {
	factory:       `<path d="M3 21h18"/><path d="M5 21V10l5 3.2V10l5 3.2V7l4 2.4V21"/><path d="M5 10l3 2"/><circle cx="8.5" cy="6" r="1.4"/>`,
	calendar:      `<rect x="3" y="4.5" width="18" height="16" rx="2.5"/><path d="M16 2.5v4M8 2.5v4M3 10h18"/>`,
	refresh:       `<path d="M21 12a9 9 0 1 1-3-6.7"/><path d="M21 3v6h-6"/>`,
	rotate:        `<path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 3v6h6"/>`,
	building:      `<rect x="4" y="2" width="16" height="20" rx="1.5"/><path d="M9 22v-4h6v4"/><path d="M8 6.5h.01M12 6.5h.01M16 6.5h.01M8 10.5h.01M12 10.5h.01M16 10.5h.01M8 14.5h.01M12 14.5h.01M16 14.5h.01"/>`,
	chevronDown:   `<path d="M6 9l6 6 6-6"/>`,
	arrowRight:    `<path d="M5 12h14"/><path d="M13 6l6 6-6 6"/>`,
	layers:        `<path d="M12 2 2 7l10 5 10-5-10-5Z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>`,
	package:       `<path d="M21 8l-9-5-9 5 9 5 9-5Z"/><path d="M3 8v8l9 5 9-5V8"/><path d="M12 13v8"/>`,
	activity:      `<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>`,
	inbox:         `<path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11Z"/>`,
	eye:           `<path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/>`,
	filter:        `<polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>`,
};

function dir_icon(name, cls = "") {
	const inner = DIR_ICON_PATHS[name] || "";
	return `<svg class="ocd-icon ${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${inner}</svg>`;
}

// ---------------------------------------------------------------------------
// Director Dashboard Class
// ---------------------------------------------------------------------------
class DirectorDashboard {
	constructor(wrapper) {
		this.wrapper = wrapper;
		this.charts = {};
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __("Director Dashboard"),
			single_column: true,
		});

		// Ensure Chart.js is loaded
		this.ensure_chartjs();

		// Default filters: This Quarter, All branches, Purchase, Order Wise
		const defaultDates = this.resolve_preset("This Quarter");
		this.filters = {
			view_type:  "Purchase",
			count_type: "Order Wise",
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
		if (document.getElementById("dir-dashboard-styles")) return;
		const s = document.createElement("style");
		s.id = "dir-dashboard-styles";
		s.textContent = DIR_CSS;
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

		// Re-render bar charts with theme adjustments if data exists
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
						<div class="ocd-header-icon">${dir_icon("factory")}</div>
						<div class="ocd-header-text">
							<div class="ocd-header-titlerow">
								<h1 class="ocd-title">${__("Director Dashboard")}</h1>
								<span class="ocd-status-chip" title="${__("Data is refreshed on demand")}">
									<span class="ocd-status-dot" aria-hidden="true"></span>${__("Live")}
								</span>
							</div>
							<p class="ocd-subtitle">${__("Pending Purchase pipeline & aging analysis across branches")}</p>
							<div class="ocd-header-meta" data-field="summary">${__("Loading…")}</div>
						</div>
					</div>
					<div class="ocd-header-actions">
						<button class="ocd-btn ocd-btn-primary ocd-refresh-btn" type="button" title="${__("Refresh data")}">
							${dir_icon("refresh")}<span>${__("Refresh")}</span>
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
							<span class="ocd-field-icon">${dir_icon("eye")}</span>
							<span class="ocd-field-label">${__("View")}</span>
							<div class="ocd-custom-select" data-role="view-select">
								<div class="ocd-custom-select-trigger">
									<span class="ocd-custom-select-text">${__("Purchase")}</span>
									${dir_icon("chevronDown", "ocd-custom-select-arrow")}
								</div>
								<div class="ocd-custom-select-options">
									<div class="ocd-custom-option selected" data-value="Purchase">${__("Purchase")}</div>
									<div class="ocd-custom-option" data-value="Sales">${__("Sales")}</div>
								</div>
							</div>
						</div>

						<!-- Count Type Dropdown (Order Wise / Item Wise) -->
						<div class="ocd-field ocd-custom-select-wrapper" data-field-name="count_type">
							<span class="ocd-field-icon">${dir_icon("filter")}</span>
							<span class="ocd-field-label">${__("Mode")}</span>
							<div class="ocd-custom-select" data-role="count-type-select">
								<div class="ocd-custom-select-trigger">
									<span class="ocd-custom-select-text">${__("Order Wise")}</span>
									${dir_icon("chevronDown", "ocd-custom-select-arrow")}
								</div>
								<div class="ocd-custom-select-options">
									<div class="ocd-custom-option selected" data-value="Order Wise">${__("Order Wise")}</div>
									<div class="ocd-custom-option" data-value="Item Wise">${__("Item Wise")}</div>
								</div>
							</div>
						</div>

						<!-- Branch Dropdown -->
						<div class="ocd-field ocd-custom-select-wrapper" data-field-name="branch">
							<span class="ocd-field-icon">${dir_icon("building")}</span>
							<span class="ocd-field-label">${__("Branch")}</span>
							<div class="ocd-custom-select" data-role="branch-select">
								<div class="ocd-custom-select-trigger">
									<span class="ocd-custom-select-text">${__("All Branches")}</span>
									${dir_icon("chevronDown", "ocd-custom-select-arrow")}
								</div>
								<div class="ocd-custom-select-options">
									<div class="ocd-custom-option selected" data-value="">${__("All Branches")}</div>
									${DIR_BRANCHES.map(b => `<div class="ocd-custom-option" data-value="${b}">${b}</div>`).join("")}
								</div>
							</div>
						</div>

						<!-- Period Dropdown -->
						<div class="ocd-field ocd-custom-select-wrapper" data-field-name="period">
							<span class="ocd-field-icon">${dir_icon("calendar")}</span>
							<span class="ocd-field-label">${__("Period")}</span>
							<div class="ocd-custom-select" data-role="date-preset">
								<div class="ocd-custom-select-trigger">
									<span class="ocd-custom-select-text">${__("This Quarter")}</span>
									${dir_icon("chevronDown", "ocd-custom-select-arrow")}
								</div>
								<div class="ocd-custom-select-options">
									${DIR_DATE_PRESETS.map(p =>
										`<div class="ocd-custom-option ${p === "This Quarter" ? "selected" : ""}" data-value="${p}">${__(p)}</div>`
									).join("")}
								</div>
							</div>
						</div>

						<!-- Custom Dates Pickers -->
						<div class="ocd-custom-dates" data-role="custom-dates">
							<input type="date" class="ocd-date-input" data-role="from-date" aria-label="${__("From date")}" />
							<span class="ocd-date-sep">${dir_icon("arrowRight")}</span>
							<input type="date" class="ocd-date-input" data-role="to-date" aria-label="${__("To date")}" />
						</div>
					</div>

					<div class="ocd-toolbar-group ocd-toolbar-group--right">
						<button type="button" class="ocd-chip-btn ocd-chip-btn--ghost" data-role="reset-filters" title="${__("Reset filters")}">
							${dir_icon("rotate")}<span>${__("Reset")}</span>
						</button>
					</div>
				</div>

				<!-- ── Dashboard Sections (MR, PO, PR, PI) ── -->
				<div class="dir-sections-container">
					${DIR_SECTIONS.map(sec => `
						<section class="ocd-section" data-section="${sec.id}">
							<div class="ocd-section-head">
								<span class="ocd-section-index">${sec.index}</span>
								<span class="ocd-section-title">${__(sec.title)}</span>
								<div class="ocd-section-context" id="${sec.id}-context-badge"></div>
								<span class="ocd-section-line" aria-hidden="true"></span>
							</div>
							
							<div class="dir-section-card" id="${sec.id}-section-card">
								<div class="dir-bucket-grid" id="${sec.id}-bucket-grid">
									${this.skeleton_cards(5, 120)}
								</div>
								<div class="dir-chart-col">
									<canvas id="${sec.id}PendingChart"></canvas>
								</div>
							</div>
						</section>
					`).join("")}
				</div>
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
						if (value === 'Sales') {
							frappe.set_route('sales-performance-da');
						}
					} else if (role === 'count-type-select') {
						this.filters.count_type = value;
						this.load_data();
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

				// Reset count type
				const countTypeSelect = this.wrapper.querySelector("[data-role='count-type-select']");
				if (countTypeSelect) {
					const options = countTypeSelect.querySelectorAll('.ocd-custom-option');
					const text = countTypeSelect.querySelector('.ocd-custom-select-text');
					options.forEach(o => o.classList.remove('selected'));
					const defaultMode = countTypeSelect.querySelector('[data-value="Order Wise"]');
					if (defaultMode) {
						defaultMode.classList.add('selected');
						text.textContent = defaultMode.textContent;
					}
				}
				this.filters.count_type = "Order Wise";

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
		const method = this.filters.count_type === "Item Wise" ? DIR_API_ITEM_WISE : DIR_API_ORDER_WISE;

		const fetch = (from_date, to_date) => new Promise((resolve) => {
			frappe.call({
				method,
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
		DIR_SECTIONS.forEach(sec => {
			const bg = this.wrapper.querySelector(`#${sec.id}-bucket-grid`);
			if (bg) bg.innerHTML = this.skeleton_cards(5, 110);
		});
	}

	show_error(msg) {
		this.wrapper.querySelector('[data-field="summary"]').textContent = msg;
	}

	// ---------------------------------------------------------------- Rendering
	render_data(data, prevData = {}) {
		this.last_data = data;
		this.last_prev_data = prevData;

		const unit = this.filters.count_type === "Item Wise" ? "Items" : "Orders";

		DIR_SECTIONS.forEach(sec => {
			const currentSecData = data[sec.key] || {};
			const prevSecData    = prevData[sec.key] || {};
			const sectionUnit    = this.filters.count_type === "Item Wise" ? sec.itemUnit : sec.docUnit;

			this.render_section_data(sec, currentSecData, prevSecData, sectionUnit);
		});

		this.render_summary(data);
		this.render_all_charts(data);
	}

	render_summary(data) {
		let grandTotal = 0;
		DIR_SECTIONS.forEach(sec => {
			const sData = data[sec.key] || {};
			grandTotal += DIR_BUCKETS.reduce((sum, b) => sum + ((sData[b.key] || {}).count || 0), 0);
		});
		const branchLabel = this.filters.branch || __("All branches");
		const modeLabel   = this.filters.count_type;
		this.wrapper.querySelector('[data-field="summary"]').textContent =
			__("{0} total pending ({1}) across {2} · updated {3}", [
				grandTotal.toLocaleString(),
				modeLabel,
				branchLabel,
				frappe.datetime.str_to_user(frappe.datetime.now_datetime())
			]);
	}

	render_section_data(sec, currentData, prevData, unit) {
		const totalCurrent = DIR_BUCKETS.reduce((s, b) => s + ((currentData[b.key] || {}).count || 0), 0);
		const totalPrev    = DIR_BUCKETS.reduce((s, b) => s + ((prevData[b.key] || {}).count || 0), 0);

		// Section context badge with comparison %
		const contextBadge = this.wrapper.querySelector(`#${sec.id}-context-badge`);
		if (contextBadge) {
			const deltaHtml = this.render_comparison_pill(totalCurrent, totalPrev);
			contextBadge.innerHTML = `
				<div class="ocd-section-context-badge">
					${dir_icon(sec.icon, "ocd-section-context-icon")}
					<span>${__("Total Pending:")}</span>
					<strong class="ocd-section-context-count">${totalCurrent.toLocaleString()} ${unit}</strong>
					${deltaHtml}
				</div>
			`;
		}



		// Bucket cards grid
		const grid = this.wrapper.querySelector(`#${sec.id}-bucket-grid`);
		if (grid) {
			grid.innerHTML = DIR_BUCKETS.map(b => {
				const count = (currentData[b.key] || {}).count || 0;
				const prevCount = (prevData[b.key] || {}).count || 0;
				const compareHtml = this.render_bucket_comparison(count, prevCount);

				return `
					<div class="ocd-card dir-bucket-card ${b.cls}" style="--stat-accent:var(--ocd-accent-${b.accent})">
						<div class="bucket-range">${b.label}</div>
						<div class="bucket-count" data-count="${count}">${count}</div>
						<div class="bucket-unit">${unit}</div>
						${compareHtml}
					</div>
				`;
			}).join("");

			this.animate_values(grid);
		}
	}

	render_all_charts(data) {
		if (!window.Chart) {
			setTimeout(() => this.render_all_charts(data), 150);
			return;
		}

		DIR_SECTIONS.forEach(sec => {
			const sData = data[sec.key] || {};
			const unit  = this.filters.count_type === "Item Wise" ? sec.itemUnit : sec.docUnit;
			this.render_bar_chart(`${sec.id}PendingChart`, sData, unit);
		});
	}

	render_bar_chart(chartId, data, unit) {
		const el = document.getElementById(chartId);
		if (!el) return;

		const counts = DIR_BUCKETS.map(b => (data[b.key] || {}).count || 0);

		if (this.charts[chartId] && typeof this.charts[chartId].destroy === "function") {
			this.charts[chartId].destroy();
		}

		const isDark = this.get_theme() === "dark";
		const gridColor = isDark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)";
		const textColor = isDark ? "#b7bccb" : "#4c5166";

		this.charts[chartId] = new Chart(el.getContext("2d"), {
			type: "bar",
			data: {
				labels: DIR_BUCKETS.map(b => b.key),
				datasets: [{
					label: `Pending ${unit}`,
					data: counts,
					backgroundColor: DIR_BUCKETS.map(b => b.color),
					borderRadius: 6,
					borderWidth: 0,
					barThickness: 32,
				}]
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				interaction: { mode: "index", intersect: false },
				scales: {
					y: {
						beginAtZero: true,
						grid: { color: gridColor },
						ticks: { precision: 0, stepSize: 1, color: textColor },
						title: { display: true, text: `Count of ${unit}`, font: { size: 10 }, color: textColor }
					},
					x: {
						grid: { display: false },
						ticks: { color: textColor },
						title: { display: true, text: __("Pending Days Bucket"), font: { size: 10 }, color: textColor }
					}
				},
				plugins: {
					legend: { display: false },
					tooltip: {
						callbacks: {
							title: items => `${items[0].label} days pending`,
							label: ctx => `  ${ctx.raw} ${unit}`,
						}
					}
				}
			}
		});
	}

	// ---------------------------------------------------------------- Comparison Helpers
	render_comparison_pill(current, previous) {
		const periodLabel = this.get_previous_period_label();
		let direction, display;

		if (previous === 0 && current === 0) {
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

		// Note for pending items: reduction (down) is positive/good (green), increase (up) is warning (red)
		const arrow = direction === "up" ? "▲" : direction === "down" ? "▼" : "▬";

		return `
			<span class="ocd-kpi-delta ocd-kpi-delta-${direction}">
				${arrow} ${display} <span class="ocd-kpi-delta-label">${__("vs")} ${periodLabel}</span>
			</span>
		`;
	}

	render_bucket_comparison(current, previous) {
		const periodLabel = this.get_previous_period_label();
		let direction, display;

		if (previous === 0 && current === 0) {
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

		const arrow = direction === "up" ? "▲" : direction === "down" ? "▼" : "▬";

		return `
			<div class="ocd-intensity-compare">
				<span class="ocd-intensity-compare-prev">${previous} <span class="ocd-intensity-compare-label">${periodLabel}</span></span>
				<span class="ocd-intensity-compare-pct ocd-intensity-compare-${direction}">${arrow} ${display}</span>
			</div>
		`;
	}

	animate_values(container) {
		const reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
		container.querySelectorAll("[data-count]").forEach(el => {
			const target = parseInt(el.getAttribute("data-count"), 10) || 0;
			if (reduced) { el.textContent = target.toLocaleString(); return; }
			const dur = 700, start = performance.now();
			const step = (now) => {
				const p = Math.min((now - start) / dur, 1);
				el.textContent = Math.round((1 - Math.pow(1 - p, 3)) * target).toLocaleString();
				if (p < 1) requestAnimationFrame(step);
			};
			requestAnimationFrame(step);
		});
	}
}

// ---------------------------------------------------------------------------
// CSS STYLES (Matching Sales Team KPI Dashboard)
// ---------------------------------------------------------------------------
const DIR_CSS = `
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
.ocd-inline-icon { width:13px; height:13px; margin:0 4px; }

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
.ocd-custom-select-wrapper[data-field-name="count_type"] { min-width:130px; }
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

.ocd-section-context {
    display: flex;
    align-items: center;
    flex: none;
}

.ocd-section-context-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 6px 14px;
    background: var(--ocd-surface);
    border: 1px solid var(--ocd-border-strong);
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
    color: var(--ocd-ink-secondary);
    white-space: nowrap;
    box-shadow: var(--ocd-shadow-sm);
}

.ocd-section-context-icon {
    width: 14px;
    height: 14px;
    color: var(--ocd-accent-steel);
    flex: none;
}

.ocd-section-context-count {
    font-size: 14px;
    font-weight: 800;
    color: var(--ocd-accent-steel);
}

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

/* Section Container Grid: Bucket Cards (5 cards) | Doc Type Badge | Bar Chart */
.dir-section-card {
	background: var(--ocd-surface);
	border-radius: var(--ocd-radius-lg);
	border: 1px solid var(--ocd-border);
	box-shadow: var(--ocd-shadow-md);
	margin-bottom: 24px;
	display: grid;
	grid-template-columns: 1fr 1.2fr;
	align-items: center;
	min-height: 280px;
	overflow: hidden;
}

.dir-bucket-grid {
	display: grid;
	grid-template-columns: repeat(3, 1fr);
	gap: 12px;
	padding: 20px;
}
.dir-bucket-grid .dir-bucket-card:nth-child(4) { grid-column: 1; }
.dir-bucket-grid .dir-bucket-card:nth-child(5) { grid-column: 2; }

.dir-bucket-card {
	background: var(--ocd-surface-2);
	border-radius: var(--ocd-radius-md);
	padding: 16px 14px;
	text-align: center;
	border: 1px solid var(--ocd-border);
	transition: transform 0.2s ease, box-shadow 0.2s ease;
	display: flex;
	flex-direction: column;
	justify-content: space-between;
	min-height: 120px;
}
.dir-bucket-card:hover {
	transform: translateY(-2px);
	box-shadow: var(--ocd-shadow-md);
	border-color: var(--ocd-border-strong);
}
.dir-bucket-card .bucket-range {
	font-size: 12px;
	font-weight: 700;
	color: var(--ocd-muted);
	text-transform: uppercase;
	letter-spacing: 0.4px;
	margin-bottom: 6px;
}
.dir-bucket-card .bucket-count {
	font-size: 30px;
	font-weight: 800;
	line-height: 1.1;
	letter-spacing: -0.02em;
}
.dir-bucket-card .bucket-unit {
	font-size: 11.5px;
	color: var(--ocd-muted);
	margin-top: 4px;
	font-weight: 600;
}

/* Color accents on top of bucket cards */
.bucket-0-7    { border-top: 3px solid var(--ocd-sev-ok); }
.bucket-0-7    .bucket-count { color: var(--ocd-sev-ok); }
.bucket-8-14   { border-top: 3px solid var(--ocd-accent-steel); }
.bucket-8-14   .bucket-count { color: var(--ocd-accent-steel); }
.bucket-15-21  { border-top: 3px solid var(--ocd-sev-watch); }
.bucket-15-21  .bucket-count { color: var(--ocd-sev-watch); }
.bucket-22-28  { border-top: 3px solid var(--ocd-sev-warn); }
.bucket-22-28  .bucket-count { color: var(--ocd-sev-warn); }
.bucket-28plus { border-top: 3px solid var(--ocd-sev-critical); }
.bucket-28plus .bucket-count { color: var(--ocd-sev-critical); }



/* Right Chart Area */
.dir-chart-col {
	padding: 20px 28px;
	height: 380px;
	position: relative;
	box-sizing: border-box;
}

/* Comparison Badges */
.ocd-kpi-delta {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	flex-wrap: wrap;
	font-size: 11px;
	font-weight: 700;
	padding: 3px 8px;
	border-radius: 999px;
	background: var(--ocd-surface-2);
	width: fit-content;
}
.ocd-kpi-delta-label { font-weight: 500; color: var(--ocd-muted); }
.ocd-kpi-delta-up     { color: var(--ocd-sev-critical); }
.ocd-kpi-delta-down   { color: var(--ocd-sev-ok); }
.ocd-kpi-delta-stable { color: var(--ocd-sev-watch); }

.ocd-intensity-compare {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 4px;
	font-size: 11px;
	padding: 4px 6px;
	margin-top: 6px;
	border-radius: var(--ocd-radius-sm);
	background: var(--ocd-surface);
	border: 1px solid var(--ocd-border);
}
.ocd-intensity-compare-prev { display: flex; align-items: baseline; gap: 3px; font-weight: 700; color: var(--ocd-ink); font-size: 11px; }
.ocd-intensity-compare-label { font-weight: 500; color: var(--ocd-muted); font-size: 9.5px; }
.ocd-intensity-compare-pct { font-weight: 700; display: inline-flex; align-items: center; gap: 2px; font-size: 10.5px; }
.ocd-intensity-compare-up     { color: var(--ocd-sev-critical); }
.ocd-intensity-compare-down   { color: var(--ocd-sev-ok); }
.ocd-intensity-compare-stable { color: var(--ocd-sev-watch); }

/* =========================================================================
   5. RESPONSIVE
   ========================================================================= */
@media (max-width: 1024px) {
	.ocd-root { padding: 22px 20px 44px; }
	.dir-section-card { grid-template-columns: 1fr; }
	.dir-chart-col { height: 300px; }
}

@media (max-width: 768px) {
	.ocd-header { flex-direction:column;align-items:stretch; }
	.ocd-header-actions { justify-content:flex-end; }
	.ocd-toolbar { flex-direction:column;align-items:stretch; }
	.ocd-toolbar-group--right { margin-left:0;justify-content:flex-end;flex-wrap:wrap; }
	.dir-bucket-grid { grid-template-columns: repeat(2, 1fr); }
	.dir-bucket-grid .dir-bucket-card:nth-child(4),
	.dir-bucket-grid .dir-bucket-card:nth-child(5) { grid-column: auto; }
}
`;