const OCD_API_METHOD = "generate_item.generate_item.page.manufacturing_kpi_da.manufacturing_kpi_da.get_dashboard_data";

const OCD_BRANCHES = ["Sanand", "Nandikoor", "Rabale"];

const OCD_DATE_PRESETS = ["Today", "This Week", "Last Week", "This Month", "Last Month", "This Year", "Last Year", "Custom"];

const OCD_ACCENTS = ["steel", "amber", "moss", "violet", "teal", "rust"];

const OCD_SEVERITY = {
	"1":  { key: "ok",       label: __("1 Revision"),   tag: "OC·01", desc: __("Single revision — normal") },
	"2":  { key: "watch",    label: __("2 Revisions"),  tag: "OC·02", desc: __("Worth keeping an eye on") },
	"3":  { key: "warn",     label: __("3 Revisions"),  tag: "OC·03", desc: __("Frequent changes") },
	"3+": { key: "critical", label: __("3+ Revisions"), tag: "OC·04", desc: __("Needs process review") },
};

// ---------------------------------------------------------------------------
// Lightweight inline icon set (lucide-style, stroke-based). Purely decorative.
// ---------------------------------------------------------------------------
const OCD_ICON_PATHS = {
	dashboard:     `<rect x="3" y="3" width="7" height="9" rx="2"/><rect x="14" y="3" width="7" height="5" rx="2"/><rect x="14" y="12" width="7" height="9" rx="2"/><rect x="3" y="16" width="7" height="5" rx="2"/>`,
	factory:       `<path d="M3 21h18"/><path d="M5 21V10l5 3.2V10l5 3.2V7l4 2.4V21"/><path d="M5 10l3 2"/><circle cx="8.5" cy="6" r="1.4"/>`,
	calendar:      `<rect x="3" y="4.5" width="18" height="16" rx="2.5"/><path d="M16 2.5v4M8 2.5v4M3 10h18"/>`,
	refresh:       `<path d="M21 12a9 9 0 1 1-3-6.7"/><path d="M21 3v6h-6"/>`,
	sun:           `<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4-1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>`,
	moon:          `<path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8Z"/>`,
	search:        `<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>`,
	download:      `<path d="M12 3v12"/><path d="M7 10l5 5 5-5"/><path d="M5 21h14"/>`,
	chevronDown:   `<path d="M6 9l6 6 6-6"/>`,
	alertTriangle: `<path d="M12 2 1 21h22L12 2Z"/><path d="M12 9v5"/><path d="M12 17h.01"/>`,
	checkCircle:   `<circle cx="12" cy="12" r="9"/><path d="m8.5 12 2.5 2.5 4.5-4.5"/>`,
	trendingUp:    `<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>`,
	trendingDown:  `<path d="M3 7l6 6 4-4 8 8"/><path d="M15 17h6v-6"/>`,
	arrowRight:    `<path d="M5 12h14"/><path d="M13 6l6 6-6 6"/>`,
	building:      `<rect x="4" y="2" width="16" height="20" rx="1.5"/><path d="M9 22v-4h6v4"/><path d="M8 6.5h.01M12 6.5h.01M16 6.5h.01M8 10.5h.01M12 10.5h.01M16 10.5h.01M8 14.5h.01M12 14.5h.01M16 14.5h.01"/>`,
	rotate:        `<path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 3v6h6"/>`,
	layers:        `<path d="M12 2 2 7l10 5 10-5-10-5Z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>`,
	package:       `<path d="M21 8l-9-5-9 5 9 5 9-5Z"/><path d="M3 8v8l9 5 9-5V8"/><path d="M12 13v8"/>`,
	activity:      `<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>`,
	inbox:         `<path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11Z"/>`,
};

function ocd_icon(name, cls = "") {
	const inner = OCD_ICON_PATHS[name] || "";
	return `<svg class="ocd-icon ${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${inner}</svg>`;
}

frappe.pages["manufacturing-kpi-da"].on_page_load = function (wrapper) {
	new OrderChangeDashboard(wrapper);
};

class OrderChangeDashboard {
	constructor(wrapper) {
		this.wrapper = wrapper;
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __("Manufacturing KPI Dashboard"),
			single_column: true,
		});
		// default filters: Today, All branches
		this.filters = {
			branch:    "",
			preset:    "Today",
			from_date: frappe.datetime.get_today(),
			to_date:   frappe.datetime.get_today(),
		};
		this.inject_styles();
		this.render_shell();
		this.bind_events();
		this.load_data();
	}

	// ---------------------------------------------------------------- styles
	inject_styles() {
		if (document.getElementById("ocd-styles")) return;
		const s = document.createElement("style");
		s.id = "ocd-styles";
		s.textContent = OCD_CSS;
		document.head.appendChild(s);
	}

	get_theme() { return localStorage.getItem("ocd_theme") || "light"; }

	set_theme(theme) {
		localStorage.setItem("ocd_theme", theme);
		this.root.setAttribute("data-theme", theme);
		const icon = this.wrapper.querySelector(".ocd-theme-icon");
		const text = this.wrapper.querySelector(".ocd-theme-text");
		if (icon) icon.textContent = theme === "dark" ? "☾" : "☀";
		if (text) text.textContent = theme === "dark" ? __("Dark mode") : __("Light mode");
	}

	// ----------------------------------------------------------------- shell
	render_shell() {
		$(this.page.body).html(`
			<div class="ocd-root" data-theme="${frappe.utils.escape_html(this.get_theme())}">
				<div class="ocd-bg-decor" aria-hidden="true"></div>

				<!-- ── Header ── -->
				<header class="ocd-header">
					<div class="ocd-header-left">
						<div class="ocd-header-icon">${ocd_icon("factory")}</div>
						<div class="ocd-header-text">
							<div class="ocd-header-titlerow">
								<h1 class="ocd-title">${__("Manufacturing KPI Dashboard")}</h1>
								<span class="ocd-status-chip" title="${__("Data is refreshed on demand")}">
									<span class="ocd-status-dot" aria-hidden="true"></span>${__("Live")}
								</span>
							</div>
							<p class="ocd-subtitle">${__("Order & batch revision intelligence across all branches")}</p>
							<div class="ocd-header-meta" data-field="summary">${__("Loading…")}</div>
						</div>
					</div>
					<div class="ocd-header-actions">
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
						<div class="ocd-field ocd-custom-select-wrapper" data-field-name="branch">
							<span class="ocd-field-icon">${ocd_icon("building")}</span>
							<span class="ocd-field-label">${__("Branch")}</span>
							<div class="ocd-custom-select" data-role="branch-select">
								<div class="ocd-custom-select-trigger">
									<span class="ocd-custom-select-text">${__("All Branches")}</span>
									${ocd_icon("chevronDown", "ocd-custom-select-arrow")}
								</div>
								<div class="ocd-custom-select-options">
									<div class="ocd-custom-option selected" data-value="">${__("All Branches")}</div>
									${OCD_BRANCHES.map(b => `<div class="ocd-custom-option" data-value="${b}">${b}</div>`).join("")}
								</div>
							</div>
						</div>

						<div class="ocd-field ocd-custom-select-wrapper" data-field-name="period">
							<span class="ocd-field-icon">${ocd_icon("calendar")}</span>
							<span class="ocd-field-label">${__("Period")}</span>
							<div class="ocd-custom-select" data-role="date-preset">
								<div class="ocd-custom-select-trigger">
									<span class="ocd-custom-select-text">${__("Today")}</span>
									${ocd_icon("chevronDown", "ocd-custom-select-arrow")}
								</div>
								<div class="ocd-custom-select-options">
									${OCD_DATE_PRESETS.map(p =>
										`<div class="ocd-custom-option ${p === "Today" ? "selected" : ""}" data-value="${p}">${__(p)}</div>`
									).join("")}
								</div>
							</div>
						</div>

						<div class="ocd-custom-dates" data-role="custom-dates">
							<input type="date" class="ocd-date-input" data-role="from-date" aria-label="${__("From date")}" />
							<span class="ocd-date-sep">${ocd_icon("arrowRight")}</span>
							<input type="date" class="ocd-date-input" data-role="to-date" aria-label="${__("To date")}" />
						</div>
					</div>

					<div class="ocd-toolbar-group ocd-toolbar-group--right">
						<button type="button" class="ocd-chip-btn" data-role="today-shortcut">${__("Today")}</button>
						<button type="button" class="ocd-chip-btn ocd-chip-btn--ghost" data-role="reset-filters" title="${__("Reset filters")}">
							${ocd_icon("rotate")}<span>${__("Reset")}</span>
						</button>
						<button class="ocd-btn ocd-btn-primary ocd-refresh-btn" type="button">
							${ocd_icon("refresh")}<span>${__("Refresh")}</span>
						</button>
					</div>
				</div>

				<!-- ── Active filter context ── -->
				 <div class="ocd-filter-context" data-role="filter-context"></div>

				<!-- ── Top KPI Cards ── -->
				<div class="ocd-kpi-row" data-role="top-kpis"></div>

				<!-- ── Section 01 · Revision Trend (Full Width, now includes Period-wise Changes) ── -->
				<section class="ocd-section" data-section="revision-trend">
					${this.section_head("01", __("Revision Trend"))}
					<div class="ocd-trend-full-width" data-trend-full></div>
				</section>

				<!-- ── Section 02 · Branch Distribution ── -->
				<section class="ocd-section" data-section="branch">
					${this.section_head("02", __("Branch Distribution"))}
					<div class="ocd-grid ocd-grid--branch"></div>
				</section>

				<!-- ── Section 03 · Order Change Intensity ── -->
<section class="ocd-section" data-section="order-change">
    <div class="ocd-section-head">
        <span class="ocd-section-index">03</span>
        <span class="ocd-section-title">${__("Order Change Intensity")}</span>
        <span class="ocd-section-context" id="order-context"></span>
        <span class="ocd-section-line" aria-hidden="true"></span>
    </div>
    <div class="ocd-grid ocd-grid--4"></div>
</section>

<!-- ── Section 04 · Batch Change Intensity ── -->
<section class="ocd-section" data-section="batch">
    <div class="ocd-section-head">
        <span class="ocd-section-index">04</span>
        <span class="ocd-section-title">${__("Batch Change Intensity")}</span>
        <span class="ocd-section-context" id="batch-context"></span>
        <span class="ocd-section-line" aria-hidden="true"></span>
    </div>
    <div class="ocd-grid ocd-grid--batch-buckets"></div>
</section>

				<!-- ── Section 05 · Revision Leaderboard ── -->
				<section class="ocd-section" data-section="leaderboard">
					${this.section_head("05", __("Revision Leaderboard"))}
					<div class="ocd-leaderboard-grid"></div>
				</section>

				<!-- ── Section 06 · Top Customers ── -->
				<section class="ocd-section" data-section="customers">
					${this.section_head("06", __("Top Customers by Revisions"))}
					<div class="ocd-customers-grid"></div>
				</section>

			</div>
		`);
		this.root = this.wrapper.querySelector(".ocd-root");

		// Initialize date inputs
		const fromInput = this.wrapper.querySelector("[data-role='from-date']");
		const toInput = this.wrapper.querySelector("[data-role='to-date']");
		fromInput.value = this.filters.from_date;
		toInput.value = this.filters.to_date;
		fromInput.disabled = true;
		toInput.disabled = true;
	}

	section_head(index, title) {
		return `
			<div class="ocd-section-head">
				<span class="ocd-section-index">${index}</span>
				<span class="ocd-section-title">${title}</span>
				<span class="ocd-section-line" aria-hidden="true"></span>
			</div>
		`;
	}

	// ---------------------------------------------------------------- events
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

		// Clickable routing
		this.wrapper.addEventListener("click", (e) => {
			// Branch Card
			const branchCard = e.target.closest(".ocd-stat-card[data-action='branch']");
			if (branchCard) {
				const branch = branchCard.dataset.branch;
				const filters = { docstatus: 1 };
				if (branch !== "Not Set") filters.branch = branch;
				if (this.filters.from_date && this.filters.to_date) {
					filters.creation = ["between", [this.filters.from_date, this.filters.to_date + " 23:59:59"]];
				}
				frappe.route_options = filters;
				frappe.set_route("List", "Order Modification Request");
			}

			// Total OMRs KPI
			const totalOmrsCard = e.target.closest(".ocd-kpi-card[data-action='total-omrs']");
			if (totalOmrsCard) {
				const filters = { docstatus: 1 };
				if (this.filters.branch) filters.branch = this.filters.branch;
				if (this.filters.from_date && this.filters.to_date) {
					filters.creation = ["between", [this.filters.from_date, this.filters.to_date + " 23:59:59"]];
				}
				frappe.route_options = filters;
				frappe.set_route("List", "Order Modification Request");
			}

			// Leaderboard User
			const userRow = e.target.closest(".ocd-clickable-row[data-action='user']");
			if (userRow) {
				const owner = userRow.dataset.id;
				const filters = { docstatus: 1, owner: owner };
				if (this.filters.from_date && this.filters.to_date) {
					filters.creation = ["between", [this.filters.from_date, this.filters.to_date + " 23:59:59"]];
				}
				frappe.route_options = filters;
				frappe.set_route("List", "Order Modification Request");
			}

			// Top Customer
			const customerRow = e.target.closest(".ocd-clickable-row[data-action='customer']");
			if (customerRow) {
				const customer = customerRow.dataset.id;
				const filters = { customer: customer };
				frappe.route_options = filters;
				frappe.set_route("List", "Sales Order");
			}

			// Order Change Severity Card → navigate to SO list
			const severityCard = e.target.closest(".ocd-intensity-card[data-action='order-change']");
			if (severityCard) {
				const sevKey = severityCard.dataset.severity;
				const soNames = (this.drill_order_change && this.drill_order_change[sevKey]) || [];
				if (soNames.length) {
					frappe.route_options = { name: ["in", soNames] };
					frappe.set_route("List", "Sales Order");
				}
			}

			// Batch Intensity Severity Card → navigate to OMR list
			const batchCard = e.target.closest(".ocd-intensity-card[data-action='batch']");
			if (batchCard) {
				const sevKey = batchCard.dataset.severity;
				const omrNames = (this.drill_batch_buckets && this.drill_batch_buckets[sevKey]) || [];
				if (omrNames.length) {
					frappe.route_options = { name: ["in", omrNames] };
					frappe.set_route("List", "Order Modification Request");
				}
			}
		});

		this.init_custom_selects();
		this.bind_extra_controls();
	}

	// Initialize custom dropdown selects
	init_custom_selects() {
		const wrappers = this.wrapper.querySelectorAll('.ocd-custom-select-wrapper');
		
		wrappers.forEach(wrapper => {
			const select = wrapper.querySelector('.ocd-custom-select');
			const trigger = select.querySelector('.ocd-custom-select-trigger');
			const text = select.querySelector('.ocd-custom-select-text');
			const options = select.querySelectorAll('.ocd-custom-option');
			const optionsContainer = select.querySelector('.ocd-custom-select-options');
			
			// Toggle dropdown
			trigger.addEventListener('click', (e) => {
				e.stopPropagation();
				const isOpen = select.classList.contains('open');
				
				// Close all other dropdowns
				this.wrapper.querySelectorAll('.ocd-custom-select.open').forEach(s => {
					if (s !== select) s.classList.remove('open');
				});
				
				select.classList.toggle('open');
			});
			
			// Select option
			options.forEach(option => {
				option.addEventListener('click', (e) => {
					e.stopPropagation();
					const value = option.dataset.value;
					
					// Update text
					text.textContent = option.textContent;
					
					// Update selected state
					options.forEach(o => o.classList.remove('selected'));
					option.classList.add('selected');
					
					// Close dropdown
					select.classList.remove('open');
					
					// Trigger change event for data-role handlers
					const role = select.dataset.role;
					if (role === 'branch-select') {
						this.filters.branch = value;
						this.load_data();
					} else if (role === 'date-preset') {
						this.filters.preset = value;
						const fromInput = this.wrapper.querySelector("[data-role='from-date']");
						const toInput = this.wrapper.querySelector("[data-role='to-date']");
						const customDates = this.wrapper.querySelector("[data-role='custom-dates']");
						
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
			
			// Close dropdown when clicking outside
			document.addEventListener('click', (e) => {
				if (!select.contains(e.target)) {
					select.classList.remove('open');
				}
			});
		});
	}

	// Additive, purely presentational controls (today shortcut / reset / header
	// export). None of these touch data-fetch logic — they just drive the
	// existing selects/handlers or export data already in memory.
	bind_extra_controls() {
		const todayBtn = this.wrapper.querySelector("[data-role='today-shortcut']");
		if (todayBtn) {
			todayBtn.addEventListener("click", () => {
				const presetSelect = this.wrapper.querySelector("[data-role='date-preset']");
				if (!presetSelect) return;
				const options = presetSelect.querySelectorAll('.ocd-custom-option');
				const text = presetSelect.querySelector('.ocd-custom-select-text');
				options.forEach(o => o.classList.remove('selected'));
				const todayOption = presetSelect.querySelector('[data-value="Today"]');
				if (todayOption) {
					todayOption.classList.add('selected');
					text.textContent = todayOption.textContent;
				}
				this.filters.preset = "Today";
				const { from_date, to_date } = this.resolve_preset("Today");
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
				
				// Reset date preset
				const presetSelect = this.wrapper.querySelector("[data-role='date-preset']");
				if (presetSelect) {
					const options = presetSelect.querySelectorAll('.ocd-custom-option');
					const text = presetSelect.querySelector('.ocd-custom-select-text');
					options.forEach(o => o.classList.remove('selected'));
					const todayOption = presetSelect.querySelector('[data-value="Today"]');
					if (todayOption) {
						todayOption.classList.add('selected');
						text.textContent = todayOption.textContent;
					}
				}
				this.filters.preset = "Today";
				const { from_date, to_date } = this.resolve_preset("Today");
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

		const exportBtn = this.wrapper.querySelector("[data-role='export-btn']");
		if (exportBtn) {
			exportBtn.addEventListener("click", () => {
				if (!this.last_data) return;
				const totalOmr = (this.last_data.branch_wise || []).reduce((s, b) => s + (b.count || 0), 0);
				const batchCount = this.last_data.batch_change ? this.last_data.batch_change.total : 0;
				this.export_rows_csv([
					{ full_name: __("Total OMRs"), count: totalOmr },
					{ full_name: __("Changed Batches"), count: batchCount },
				], "dashboard_overview");
			});
		}
	}

	sync_custom_dates() {
		const fd = this.wrapper.querySelector("[data-role='from-date']").value;
		const td = this.wrapper.querySelector("[data-role='to-date']").value;
		if (fd && td) {
			this.filters.from_date = fd;
			this.filters.to_date   = td;
		}
	}

	// --------------------------------------------------------- date helpers
	resolve_preset(preset) {
		const today     = frappe.datetime.get_today();
		const todayDate = frappe.datetime.str_to_obj(today);

		const fmt  = (d) => frappe.datetime.obj_to_str(d);
		const add  = (d, n) => { const x = new Date(d); x.setDate(x.getDate() + n); return x; };
		const dow  = todayDate.getDay();
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

	// Resolve the "previous equivalent period" for a given preset + range,
	// used to power the comparison shown on the intensity cards.
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

	// Short label describing the previous period, shown next to the comparison %.
	get_previous_period_label() {
		switch (this.filters.preset) {
			case "Today":      return __("yesterday");
			case "This Week":  return __("last week");
			case "Last Week":  return __("prior week");
			case "This Month": return __("last month");
			case "Last Month": return __("prior month");
			case "This Year":  return __("last year");
			case "Last Year":  return __("prior year");
			default:           return __("prior period");
		}
	}

	// ------------------------------------------------------------------ data
	load_data() {
		if (this.filters.preset !== "Custom") {
			const { from_date, to_date } = this.resolve_preset(this.filters.preset);
			this.filters.from_date = from_date;
			this.filters.to_date   = to_date;
		} else {
			this.sync_custom_dates();
		}
		this.show_loading();

		const prevRange = this.resolve_previous_range(this.filters.preset, this.filters.from_date, this.filters.to_date);

		const fetch = (from_date, to_date) => new Promise((resolve) => {
			frappe.call({
				method: OCD_API_METHOD,
				args: { branch: this.filters.branch, from_date, to_date },
				callback: (r) => resolve((r && r.message) || null),
				error: () => resolve(null),
			});
		});

		Promise.all([
			fetch(this.filters.from_date, this.filters.to_date),
			fetch(prevRange.from_date, prevRange.to_date),
		]).then(([data, prevData]) => {
			if (!data) { this.show_error(__("No data returned.")); return; }
			this.render_data(data, prevData || {});
		});
	}

	show_loading() {
		this.wrapper.querySelector('[data-field="summary"]').textContent = __("Loading…");
		this.wrapper.querySelector('[data-trend-full]').innerHTML = '<div class="ocd-card ocd-skel" style="height:420px"></div>';
		this.wrapper.querySelector(".ocd-grid--branch").innerHTML = this.skeleton_cards(3, 190);
		this.wrapper.querySelector(".ocd-grid--4").innerHTML = this.skeleton_cards(4, 260);
		this.wrapper.querySelector(".ocd-grid--batch-buckets").innerHTML = this.skeleton_cards(4, 260);
		this.wrapper.querySelector(".ocd-leaderboard-grid").innerHTML = `
			<div class="ocd-card ocd-skel" style="height:260px"></div>
			<div class="ocd-card ocd-skel" style="height:260px"></div>
		`;
		this.wrapper.querySelector(".ocd-customers-grid").innerHTML = `<div class="ocd-card ocd-skel" style="height:260px"></div>`;
		this.wrapper.querySelector("[data-role='top-kpis']").innerHTML = this.skeleton_cards(4, 170);
	}

	skeleton_cards(n, height = 110) {
		let o = "";
		for (let i = 0; i < n; i++) o += `<div class="ocd-card ocd-skel" style="height:${height}px"></div>`;
		return o;
	}

	show_error(msg) {
		this.wrapper.querySelector('[data-field="summary"]').textContent = msg;
	}

	render_data(data, prevData = {}) {
		this.last_data = data;

		this.render_top_kpis(data, prevData);
		this.render_revision_trend(data.trends || {});
		this.render_period_changes(data);
		this.render_branches(data.branch_wise || [], prevData.branch_wise || []);
		this.render_order_change(data.order_change || {}, prevData.order_change || {});
		this.render_batch_buckets(data.batch_buckets || {}, prevData.batch_buckets || {});
		this.render_leaderboard(data.top_creators_high || [], data.top_creators_low || []);
		this.render_customers(data.top_customers || []);
		this.render_summary(data);
		// this.render_filter_chips();

		// Store drill-down data
		this.drill_order_change = (data.order_change && data.order_change._drill) || {};
		this.drill_batch_buckets = (data.batch_buckets && data.batch_buckets._drill) || {};
	}

	render_summary(data) {
		const totalOmr   = (data.branch_wise || []).reduce((s, b) => s + (b.count || 0), 0);
		const branchCount = (data.branch_wise || []).length;
		const stamp       = data.generated_at ? frappe.datetime.str_to_user(data.generated_at) : "";
		this.wrapper.querySelector('[data-field="summary"]').textContent =
			__("{0} submitted OMRs across {1} branch(es) · updated {2}", [totalOmr, branchCount, stamp]);
	}

	// Renders the small "active filters" chip row under the toolbar.
	// render_filter_chips() {
	// 	const el = this.wrapper.querySelector("[data-role='filter-context']");
	// 	if (!el) return;
	// 	const periodLabel = this.filters.preset === "Custom" && this.filters.from_date && this.filters.to_date
	// 		? `${frappe.datetime.str_to_user(this.filters.from_date)} → ${frappe.datetime.str_to_user(this.filters.to_date)}`
	// 		: __(this.filters.preset);
	// 	el.innerHTML = `
	// 		<span class="ocd-ctx-chip">${ocd_icon("building", "ocd-ctx-icon")}${frappe.utils.escape_html(this.filters.branch || __("All Branches"))}</span>
	// 		<span class="ocd-ctx-chip">${ocd_icon("calendar", "ocd-ctx-icon")}${frappe.utils.escape_html(periodLabel)}</span>
	// 	`;
	// }

	// --------------------------------------------------------------- top kpis
	render_top_kpis(data, prevData = {}) {
		const el = this.wrapper.querySelector("[data-role='top-kpis']");
		if (!el) return;

		const totalOmr = (data.branch_wise || []).reduce((s, b) => s + (b.count || 0), 0);
		const prevTotalOmr = (prevData.branch_wise || []).reduce((s, b) => s + (b.count || 0), 0);

		const batchCount = data.batch_change ? data.batch_change.total : 0;
		const prevBatchCount = prevData.batch_change ? prevData.batch_change.total : 0;

		const rates = data.revision_rates || {};
		const prevRates = prevData.revision_rates || {};

		const get_color = (pct) => {
			if (pct > 15) return "var(--ocd-sev-critical)";
			if (pct >= 5) return "var(--ocd-sev-watch)";
			return "var(--ocd-sev-ok)";
		};
		const get_tone = (pct) => {
			if (pct > 15) return "critical";
			if (pct >= 5) return "watch";
			return "ok";
		};

		const trendSpark = ((data.trends && data.trends.daily_data) || []).map(d => d.count || 0);

		el.innerHTML = `
			${this.kpi_card({ label: __("Total OMRs"), value: totalOmr, previous_value: prevTotalOmr, sub: __("in selected period"), color: "var(--ocd-accent-steel)", action: "total-omrs", icon: "layers", spark: trendSpark })}
			${this.kpi_card({ label: __("Changed Batches"), value: batchCount, previous_value: prevBatchCount, sub: __("unique item+batch pairs"), color: "var(--ocd-accent-teal)", icon: "package" })}
			${this.kpi_card({
				label: __("Order Revision Rate"),
				value: rates.order_rate + "%",
				previous_value: prevRates.order_rate,
				is_rate: true,
				sub: `${rates.revised_sos} of ${rates.total_sos} orders`,
				color: get_color(rates.order_rate),
				icon: "trendingUp",
				tone: get_tone(rates.order_rate)
			})}
			${this.kpi_card({
				label: __("Item Revision Rate"),
				value: rates.item_rate + "%",
				previous_value: prevRates.item_rate,
				is_rate: true,
				sub: `${rates.changed_items} of ${rates.total_items} items`,
				color: get_color(rates.item_rate),
				icon: "activity",
				tone: get_tone(rates.item_rate)
			})}
		`;
		this.animate_values(el);
	}

	kpi_card({ label, value, previous_value, is_rate, sub, color, action, icon = "activity", spark = null, tone = null }) {
		const actionAttr = action
			? `data-action="${action}" tabindex="0" role="button" class="ocd-kpi-card ocd-clickable-card"`
			: `class="ocd-kpi-card"`;
		const current = is_rate ? parseFloat(value) : value;
		const deltaHtml = previous_value === undefined || previous_value === null
			? ""
			: this.render_kpi_delta(current, previous_value, !!is_rate);
		const sparkHtml = spark && spark.length > 1 ? this.mini_sparkline(spark, color) : "";
		const toneHtml = tone ? `<span class="ocd-kpi-tone ocd-kpi-tone-${tone}"></span>` : "";
		return `
			<div ${actionAttr} style="--kpi-accent:${color}">
				${toneHtml}
				<div class="ocd-kpi-top">
					<div class="ocd-kpi-icon" style="color:${color}">${ocd_icon(icon)}</div>
					<div class="ocd-kpi-label">${frappe.utils.escape_html(label)}</div>
				</div>
				<div class="ocd-kpi-value" style="color: ${color}">${value}</div>
				<div class="ocd-kpi-footer">
					<div class="ocd-kpi-sub">${frappe.utils.escape_html(sub)}</div>
					${deltaHtml}
				</div>
				${sparkHtml}
			</div>
		`;
	}

	mini_sparkline(values, color) {
		const w = 108, h = 30, pad = 2;
		const max = Math.max(...values, 1);
		const min = Math.min(...values, 0);
		const range = (max - min) || 1;
		const pts = values.map((v, i) => {
			const x = values.length > 1 ? (i / (values.length - 1)) * (w - pad * 2) + pad : w / 2;
			const y = h - ((v - min) / range) * (h - pad * 2) - pad;
			return `${x},${y}`;
		}).join(" ");
		return `
			<svg class="ocd-kpi-spark" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" aria-hidden="true">
				<polyline fill="none" stroke="${color}" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" points="${pts}" opacity="0.85"/>
			</svg>
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

		const arrow = direction === "up" ? "▲" : direction === "down" ? "▼" : "▬";

		return `
			<span class="ocd-kpi-delta ocd-kpi-delta-${direction}">
				${arrow} ${display} <span class="ocd-kpi-delta-label">${__("vs")} ${periodLabel}</span>
			</span>
		`;
	}

	// --------------------------------------------------------------- revision trend
	render_revision_trend(trends) {
		const container = this.wrapper.querySelector("[data-trend-full]");
		if (!container || !trends.daily_data) return;

		const daily = trends.daily_data || [];
		const counts = daily.map(d => d.count || 0);
		const avg = counts.length ? Math.round((counts.reduce((a, b) => a + b, 0) / counts.length) * 10) / 10 : 0;
		const peak = counts.length ? Math.max(...counts) : 0;
		const peakDay = daily.find(d => d.count === peak);

		const trendHtml = `
			<div class="ocd-card ocd-trend-full-card">
				<div class="ocd-trend-full-header">
					<div class="ocd-trend-heading">
						<span class="ocd-trend-heading-icon">${ocd_icon("activity")}</span>
						<div>
							<div class="ocd-list-title">${this.get_trend_heading()}</div>
							<div class="ocd-list-subtitle">${__("Daily modification request count")}</div>
						</div>
					</div>
					<div class="ocd-trend-badge">
						<span class="ocd-trend-badge-value ${trends.trend_direction}">
							${trends.trend_emoji} ${trends.change_percentage > 0 ? "+" : ""}${trends.change_percentage}%
						</span>
					</div>
				</div>

				<div class="ocd-sparkline-full" data-sparkline-full></div>

				<div class="ocd-trend-stat-row">
					<div class="ocd-trend-stat">
						<span class="ocd-trend-stat-label">${__("Total in Period")}</span>
						<span class="ocd-trend-stat-value">${trends.total_this_month}</span>
					</div>
					<div class="ocd-trend-stat">
						<span class="ocd-trend-stat-label">${__("Daily Average")}</span>
						<span class="ocd-trend-stat-value">${avg}</span>
					</div>
					<div class="ocd-trend-stat">
						<span class="ocd-trend-stat-label">${__("Peak Day")}</span>
						<span class="ocd-trend-stat-value">${peak}${peakDay && peakDay.label ? ` <small>(${frappe.utils.escape_html(peakDay.label)})</small>` : ""}</span>
					</div>
				</div>

				<div class="ocd-trend-full-summary">
					<div class="ocd-trend-direction ocd-trend-direction-${trends.trend_direction}">
						${trends.trend_direction === "down" ? ocd_icon("trendingDown") : trends.trend_direction === "up" ? ocd_icon("trendingUp") : ocd_icon("activity")}
						<span>${
							trends.trend_direction === "down"
								? __("Revisions trending downward — great improvement!")
								: trends.trend_direction === "up"
									? __("Revisions increasing — may need process review")
									: __("Revisions stable — consistent process execution")
						}</span>
					</div>
				</div>

				<div class="ocd-trend-period-section" data-period-changes></div>
			</div>
		`;

		container.innerHTML = trendHtml;

		const sparklineContainer = container.querySelector("[data-sparkline-full]");
		if (sparklineContainer) {
			this.render_sparkline(sparklineContainer, daily);
		}
	}

	// --------------------------------------------------------------- period changes
	render_period_changes(data) {
		const container = this.wrapper.querySelector("[data-period-changes]");
		if (!container) return;

		const preset = this.filters.preset;
		let periodData = [];

		if (preset === "This Year" || preset === "Last Year") {
			periodData = this.get_monthly_changes(data);
		} else if (preset === "This Month" || preset === "Last Month") {
			periodData = this.get_weekly_changes(data);
		} else if (preset === "This Week" || preset === "Last Week") {
			periodData = this.get_daily_changes(data);
		} else {
			periodData = this.get_daily_changes(data);
		}

		const maxCount = Math.max(...periodData.map(p => p.count), 1);
		const totalCount = periodData.reduce((s, p) => s + (p.count || 0), 0) || 1;

		container.innerHTML = `
			<div class="ocd-trend-period-header">
				<span class="ocd-trend-period-title">${ocd_icon("layers", "ocd-inline-icon")}${this.get_period_title()}</span>
				<span class="ocd-trend-period-subtitle">${__("Changes performed in OMR against Sales Orders")}</span>
			</div>
			<div class="ocd-period-rows">
				${periodData.map((item, i) => {
					const pct = Math.round((item.count / maxCount) * 100);
					const share = Math.round((item.count / totalCount) * 100);
					return `
						<div class="ocd-row ocd-period-row">
							<span class="ocd-row-rank">${i + 1}</span>
							<span class="ocd-row-name" style="flex:1;">${item.label}</span>
							<span class="ocd-row-bar-wrap" style="flex:0 0 150px;">
								<span class="ocd-row-bar" style="--accent:var(--ocd-accent-steel);width:${pct}%"></span>
							</span>
							<span class="ocd-period-share">${share}%</span>
							<span class="ocd-row-count">${item.count}</span>
						</div>
					`;
				}).join("")}
			</div>
		`;
	}

	get_period_title() {
		switch(this.filters.preset) {
			case "This Year":
			case "Last Year": return __("Monthly Changes");
			case "This Month":
			case "Last Month": return __("Weekly Changes");
			case "This Week":
			case "Last Week": return __("Daily Changes");
			default: return __("Daily Changes");
		}
	}

	get_trend_heading() {
		const preset = this.filters.preset;
		if (preset === "Custom") {
			if (this.filters.from_date && this.filters.to_date) {
				return `${frappe.datetime.str_to_user(this.filters.from_date)} to ${frappe.datetime.str_to_user(this.filters.to_date)} Trend`;
			}
			return __("Custom Period Trend");
		}
		return __(preset + " Trend");
	}

	get_monthly_changes(data) {
		const months = [
			"January", "February", "March", "April", "May", "June",
			"July", "August", "September", "October", "November", "December"
		];

		const trends = data.trends?.daily_data || [];
		const monthlyCounts = {};

		trends.forEach(t => {
			const month = new Date(t.date).getMonth();
			monthlyCounts[month] = (monthlyCounts[month] || 0) + t.count;
		});

		return months.map((month, index) => ({
			label: month,
			count: monthlyCounts[index] || 0
		}));
	}

	get_weekly_changes(data) {
		const trends = data.trends?.daily_data || [];

		if (!trends.length) {
			return [];
		}

		const firstDate = new Date(trends[0].date);
		const year = firstDate.getFullYear();
		const month = firstDate.getMonth();
		const daysInMonth = new Date(year, month + 1, 0).getDate();

		const weeks = Array.from(
			{ length: Math.ceil(daysInMonth / 7) },
			(_, index) => {
				const start = index * 7 + 1;
				const end = Math.min(start + 6, daysInMonth);
				return {
					label: `Week ${index + 1} (${start}-${end})`,
					count: 0,
				};
			}
		);

		trends.forEach(trend => {
			const day = new Date(trend.date).getDate();
			const weekIndex = Math.floor((day - 1) / 7);
			if (weeks[weekIndex]) {
				weeks[weekIndex].count += Number(trend.count || 0);
			}
		});

		return weeks;
	}

	get_daily_changes(data) {
		const trends = data.trends?.daily_data || [];
		const days = ["Day 1", "Day 2", "Day 3", "Day 4", "Day 5", "Day 6", "Day 7"];

		return trends.slice(0, 7).map((t, i) => ({
			label: t.label || (days[i] || `Day ${i + 1}`),
			count: t.count
		}));
	}

	// --------------------------------------------------------------- branch
	render_branches(rows, prevRows = []) {
		const el = this.wrapper.querySelector(".ocd-grid--branch");
		if (!el) return;

		// Ensure all branches are shown, even with zero count
		const allBranches = OCD_BRANCHES.map(branch => {
			const found = rows.find(r => r.branch === branch);
			return found || { branch: branch, count: 0 };
		});

		const displayRows = allBranches.length > 0 ? allBranches : rows;

		if (!displayRows.length) { el.innerHTML = this.empty_state(__("No submitted OMRs for the selected filters.")); return; }

		const counts   = displayRows.map(r => r.count);
		const total = counts.reduce((a, b) => a + b, 0) || 1;

		el.innerHTML = displayRows.map((row, i) => {
			const accent = OCD_ACCENTS[i % OCD_ACCENTS.length];
			const prevRow = (prevRows || []).find(r => r.branch === row.branch);
			const pct = Math.round((row.count / total) * 100);
			return this.stat_card({
				accent, label: row.branch, value: row.count, action: "branch", action_id: row.branch,
				percent: pct, previous_value: prevRow ? prevRow.count : undefined, rank: i + 1
			});
		}).join("");
		this.animate_values(el);
	}

	// ---------------------------------------------------------- order change
	// render_order_change(buckets, prevBuckets = {}) {
	// 	const el = this.wrapper.querySelector(".ocd-grid--4");
	// 	const keys = ["1","2","3","3+"];
	// 	const selectedBranch = this.filters.branch;

	// 	el.innerHTML = keys.map(key => {
	// 		const meta = OCD_SEVERITY[key];
	// 		const bucket = buckets[key] || {};
	// 		const prevBucket = prevBuckets[key] || {};
	// 		const branches = this.get_branch_breakdown(bucket, selectedBranch);

	// 		return this.intensity_card({
	// 			label: meta.label,
	// 			value: bucket.total || 0,
	// 			previous_value: prevBucket.total || 0,
	// 			branches: branches,
	// 			action: "order-change",
	// 			severity_key: key,
	// 			accent: meta.key,
	// 			desc: meta.desc
	// 		});
	// 	}).join("");

	// 	this.animate_values(el);
	// }

	// // ---------------------------------------------------------- batch buckets
	// render_batch_buckets(buckets, prevBuckets = {}) {
	// 	const el = this.wrapper.querySelector(".ocd-grid--batch-buckets");
	// 	const keys = ["1","2","3","3+"];
	// 	const selectedBranch = this.filters.branch;

	// 	el.innerHTML = keys.map(key => {
	// 		const meta = OCD_SEVERITY[key];
	// 		const bucket = buckets[key] || {};
	// 		const prevBucket = prevBuckets[key] || {};
	// 		const branches = this.get_branch_breakdown(bucket, selectedBranch);

	// 		return this.intensity_card({
	// 			label: meta.label.replace("Revision","OMR"),
	// 			value: bucket.total || 0,
	// 			previous_value: prevBucket.total || 0,
	// 			branches: branches,
	// 			action: "batch",
	// 			severity_key: key,
	// 			accent: meta.key,
	// 			desc: meta.desc
	// 		});
	// 	}).join("");

	// 	this.animate_values(el);
	// }

	// Update the intensity_card method to accept and display context counts
intensity_card({ label, value, previous_value, branches, action, severity_key, accent, desc, context_count, context_label }) {
    const branchHtml = branches
        ? `
        <div class="ocd-intensity-branches">
            ${OCD_BRANCHES.map(b => `
                <div class="ocd-intensity-branch">
                    <span class="ocd-intensity-branch-name">${b}</span>
                    <span class="ocd-intensity-branch-count">${branches[b] || 0}</span>
                </div>
            `).join("")}
        </div>
        `
        : `<div class="ocd-intensity-spacer"></div>`;

    const compareHtml = previous_value === undefined ? "" : this.render_comparison(value, previous_value);
    
    // Context count display (SO count for order change, line item count for batch change)
    const contextHtml = context_count !== undefined && context_count !== null ? `
        <div class="ocd-intensity-context">
            <span class="ocd-intensity-context-label">${context_label || __("Total")}:</span>
            <span class="ocd-intensity-context-value">${context_count}</span>
        </div>
    ` : '';

    return `
    <div class="ocd-card ocd-intensity-card ocd-clickable-card"
        data-action="${action}"
        data-severity="${severity_key}"
        tabindex="0" role="button"
        style="--intensity-accent:var(--ocd-sev-${accent})">

        <div class="ocd-intensity-top">
            <div class="ocd-intensity-top-main">
                <div class="ocd-card-value ocd-intensity-value"
                    data-count="${value}"
                    style="color:var(--ocd-sev-${accent})">0</div>
                ${desc ? `<div class="ocd-intensity-desc">${desc}</div>` : ""}
            </div>
            <span class="ocd-intensity-badge ocd-intensity-badge-${accent}">${label}</span>
        </div>

        ${contextHtml}

        ${compareHtml}

        ${branchHtml}

    </div>
    `;
}

render_order_change(buckets, prevBuckets = {}) {
    const el = this.wrapper.querySelector(".ocd-grid--4");
    const keys = ["1","2","3","3+"];
    const selectedBranch = this.filters.branch;
    const approvedSOCount = buckets.approved_so_count || 0;

    // Update the section heading with SO count
    const contextEl = this.wrapper.querySelector("#order-context");
    if (contextEl) {
        contextEl.innerHTML = `
            <span class="ocd-section-context-badge">
                ${ocd_icon("package", "ocd-section-context-icon")}
                <span>${__("Approved SOs")}:</span>
                <span class="ocd-section-context-count" data-count="${approvedSOCount}">0</span>
            </span>
        `;
    }

    el.innerHTML = keys.map(key => {
        const meta = OCD_SEVERITY[key];
        const bucket = buckets[key] || {};
        const prevBucket = prevBuckets[key] || {};
        const branches = this.get_branch_breakdown(bucket, selectedBranch);

        return this.intensity_card({
            label: meta.label,
            value: bucket.total || 0,
            previous_value: prevBucket.total || 0,
            branches: branches,
            action: "order-change",
            severity_key: key,
            accent: meta.key,
            desc: meta.desc
        });
    }).join("");

    this.animate_values(el);
    if (contextEl) this.animate_values(contextEl);
}
render_batch_buckets(buckets, prevBuckets = {}) {
    const el = this.wrapper.querySelector(".ocd-grid--batch-buckets");
    const keys = ["1","2","3","3+"];
    const selectedBranch = this.filters.branch;
    const totalLineItems = buckets.total_line_items || 0;

    // Update the section heading with line items count
    const contextEl = this.wrapper.querySelector("#batch-context");
    if (contextEl) {
        contextEl.innerHTML = `
            <span class="ocd-section-context-badge">
                ${ocd_icon("inbox", "ocd-section-context-icon")}
                <span>${__("Total Line Items")}:</span>
                <span class="ocd-section-context-count" data-count="${totalLineItems}">0</span>
            </span>
        `;
    }

    el.innerHTML = keys.map(key => {
        const meta = OCD_SEVERITY[key];
        const bucket = buckets[key] || {};
        const prevBucket = prevBuckets[key] || {};
        const branches = this.get_branch_breakdown(bucket, selectedBranch);

        return this.intensity_card({
            label: meta.label.replace("Revision","OMR"),
            value: bucket.total || 0,
            previous_value: prevBucket.total || 0,
            branches: branches,
            action: "batch",
            severity_key: key,
            accent: meta.key,
            desc: meta.desc
        });
    }).join("");

    this.animate_values(el);
    if (contextEl) this.animate_values(contextEl);
}

	get_branch_breakdown(bucket, selectedBranch) {
		if (!selectedBranch) {
			return bucket.branches || {};
		}
		const branches = {};
		OCD_BRANCHES.forEach(b => { branches[b] = 0; });
		branches[selectedBranch] = bucket.total || 0;
		return branches;
	}

	// --------------------------------------------------------- leaderboard
	render_leaderboard(high, low) {
		const el = this.wrapper.querySelector(".ocd-leaderboard-grid");
		const highRows = high.map(r => ({ ...r, id: r.owner }));
		const lowRows  = low.map(r => ({ ...r, id: r.owner }));

		el.innerHTML =
			this.leaderboard_card({ title: __("Most Revisions"), subtitle: __("Creators raising the most modification requests"), rows: highRows, accent: "rust", action_type: "user" }) +
			this.leaderboard_card({ title: __("Fewest Revisions"), subtitle: __("Creators with the cleanest revision record"), rows: lowRows, accent: "moss", action_type: "user" });

		this.bind_list_card_actions(el, [
			{ rows: highRows, filename: "most_revisions" },
			{ rows: lowRows, filename: "fewest_revisions" },
		]);
	}

	// --------------------------------------------------------- customers
	render_customers(rows) {
		const el = this.wrapper.querySelector(".ocd-customers-grid");
		const customerRows = rows.map(r => ({ id: r.customer, full_name: r.customer_name || r.customer, count: r.count }));

		el.innerHTML = this.leaderboard_card({
			title: __("Top Customers"),
			subtitle: __("Customers with the most order modifications"),
			rows: customerRows,
			accent: "steel",
			action_type: "customer"
		});

		this.bind_list_card_actions(el, [
			{ rows: customerRows, filename: "top_customers" },
		]);
	}

	bind_list_card_actions(container, exportGroups) {
		const cards = container.querySelectorAll(".ocd-list-card");
		cards.forEach((card, i) => {
			const vmBtn = card.querySelector(".ocd-viewmore-btn");
			if (vmBtn) {
				vmBtn.addEventListener("click", () => {
					const expanded = card.classList.toggle("ocd-expanded");
					vmBtn.innerHTML = expanded
						? `${__("View Less")}${ocd_icon("chevronDown", "ocd-inline-icon ocd-inline-icon--up")}`
						: `${__("View More")}${ocd_icon("chevronDown", "ocd-inline-icon")}`;
				});
			}
			const exportBtn = card.querySelector(".ocd-export-btn");
			const group = exportGroups[i];
			if (exportBtn && group) {
				exportBtn.addEventListener("click", () => this.export_rows_csv(group.rows, group.filename));
			}
			const searchInput = card.querySelector("[data-role='list-search']");
			if (searchInput) {
				searchInput.addEventListener("input", () => {
					const q = searchInput.value.trim().toLowerCase();
					card.querySelectorAll(".ocd-row").forEach(row => {
						const nameEl = row.querySelector(".ocd-row-name");
						const name = nameEl ? nameEl.textContent.toLowerCase() : "";
						row.style.display = (!q || name.includes(q)) ? "" : "none";
					});
				});
			}
		});
	}

	export_rows_csv(rows, filename) {
		if (!rows || !rows.length) return;
		const lines = [["Name", "Count"].join(",")];
		rows.forEach(r => {
			const name = String(r.full_name || "").replace(/"/g, '""');
			lines.push(`"${name}",${r.count}`);
		});
		const csv  = lines.join("\n");
		const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
		const url  = URL.createObjectURL(blob);
		const a    = document.createElement("a");
		a.href = url;
		a.download = `${filename}_${frappe.datetime.get_today()}.csv`;
		document.body.appendChild(a);
		a.click();
		document.body.removeChild(a);
		URL.revokeObjectURL(url);
	}

	leaderboard_card({ title, subtitle, rows, accent, action_type }) {
		const headHtml = `
			<div class="ocd-list-card-head">
				<div class="ocd-list-card-head-text">
					<div class="ocd-list-title">${title}</div>
					<div class="ocd-list-subtitle">${subtitle}</div>
				</div>
				${rows.length ? `<button type="button" class="ocd-export-btn" title="${__("Export CSV")}">${ocd_icon("download")}${__("CSV")}</button>` : ""}
			</div>
			${rows.length > 5 ? `
				<label class="ocd-list-search">
					${ocd_icon("search", "ocd-list-search-icon")}
					<input type="text" class="ocd-list-search-input" data-role="list-search" placeholder="${__("Filter by name…")}" aria-label="${__("Filter by name")}" />
				</label>
			` : ""}
		`;

		if (!rows.length) {
			return `
				<div class="ocd-card ocd-list-card">
					${headHtml}
					${this.empty_state(__("No data available."))}
				</div>
			`;
		}
		const medals = ["🥇", "🥈", "🥉"];
		const max   = Math.max(...rows.map(r => r.count));
		const items = rows.map((row, i) => {
			const pct        = max ? Math.round((row.count / max) * 100) : 0;
			const extraClass = i >= 5 ? " ocd-row-extra" : "";
			const actionAttr = action_type ? `data-action="${action_type}" data-id="${frappe.utils.escape_html(row.id)}" tabindex="0" role="button"` : "";
			const clickableClass = action_type ? " ocd-clickable-row" : "";
			const rankHtml = i < 3
				? `<span class="ocd-row-medal" aria-hidden="true">${medals[i]}</span>`
				: `<span class="ocd-row-rank">${i + 1}</span>`;
			return `
				<div class="ocd-row${extraClass}${clickableClass}" ${actionAttr}>
					${rankHtml}
					<span class="ocd-avatar" style="--accent:var(--ocd-accent-${accent})">${this.initials(row.full_name)}</span>
					<span class="ocd-row-name" title="${frappe.utils.escape_html(row.full_name)}">${frappe.utils.escape_html(row.full_name)}</span>
					<span class="ocd-row-bar-wrap"><span class="ocd-row-bar" style="--accent:var(--ocd-accent-${accent});width:${pct}%"></span></span>
					<span class="ocd-row-count">${row.count}</span>
				</div>
			`;
		}).join("");
		const vmBtn = rows.length > 5
			? `<button type="button" class="ocd-viewmore-btn">${__("View More")}${ocd_icon("chevronDown", "ocd-inline-icon")}</button>`
			: "";
		return `
			<div class="ocd-card ocd-list-card">
				${headHtml}
				<div class="ocd-rows">${items}</div>
				${vmBtn}
			</div>
		`;
	}

	initials(name) {
		if (!name) return "?";
		return String(name).trim().split(/\s+/).slice(0, 2).map(p => p[0]).join("").toUpperCase();
	}

	// ---------------------------------------------------------- primitives
	stat_card({ accent, label, value, severity, action, action_id, section, severity_key, percent, previous_value, rank }) {
		const accentVar = severity ? `var(--ocd-sev-${accent})` : `var(--ocd-accent-${accent})`;
		const actionAttr = section
			? `data-action="${section}" data-severity="${severity_key}" tabindex="0" role="button" class="ocd-card ocd-stat-card ocd-clickable-card"`
			: (action ? `data-action="${action}" data-branch="${action_id}" tabindex="0" role="button" class="ocd-card ocd-stat-card ocd-clickable-card"` : `class="ocd-card ocd-stat-card"`);
		const initial = frappe.utils.escape_html(String(label || "?").trim().charAt(0).toUpperCase());
		const compareHtml = previous_value === undefined ? "" : this.render_comparison(value, previous_value);
		return `
			<div ${actionAttr} style="--stat-accent:${accentVar}">
				${rank ? `<span class="ocd-stat-rank">#${rank}</span>` : ""}
				<div class="ocd-stat-avatar" style="background:${accentVar}">${initial}</div>
				<div class="ocd-stat-content">
					<div class="ocd-card-value" data-count="${value}" style="color: ${accentVar}">0</div>
					<div class="ocd-card-label">${frappe.utils.escape_html(label)}</div>
					${typeof percent === "number" && isFinite(percent) ? `
						<div class="ocd-stat-percent-wrap">
							<div class="ocd-stat-percent-bar"><div class="ocd-stat-percent-fill" style="width:${percent}%;background:${accentVar}"></div></div>
							<span class="ocd-stat-percent-label">${percent}% ${__("of total")}</span>
						</div>
					` : ""}
				</div>
				${compareHtml}
			</div>
		`;
	}

	// intensity_card({ label, value, previous_value, branches, action, severity_key, accent, desc }) {
	// 	const branchHtml = branches
	// 		? `
	// 		<div class="ocd-intensity-branches">
	// 			${OCD_BRANCHES.map(b => `
	// 				<div class="ocd-intensity-branch">
	// 					<span class="ocd-intensity-branch-name">${b}</span>
	// 					<span class="ocd-intensity-branch-count">${branches[b] || 0}</span>
	// 				</div>
	// 			`).join("")}
	// 		</div>
	// 		`
	// 		: `<div class="ocd-intensity-spacer"></div>`;

	// 	const compareHtml = previous_value === undefined ? "" : this.render_comparison(value, previous_value);

	// 	return `
	// 	<div class="ocd-card ocd-intensity-card ocd-clickable-card"
	// 		data-action="${action}"
	// 		data-severity="${severity_key}"
	// 		tabindex="0" role="button"
	// 		style="--intensity-accent:var(--ocd-sev-${accent})">

	// 		<div class="ocd-intensity-top">
	// 			<div class="ocd-intensity-top-main">
	// 				<div class="ocd-card-value ocd-intensity-value"
	// 					data-count="${value}"
	// 					style="color:var(--ocd-sev-${accent})">0</div>
	// 				${desc ? `<div class="ocd-intensity-desc">${desc}</div>` : ""}
	// 			</div>
	// 			<span class="ocd-intensity-badge ocd-intensity-badge-${accent}">${label}</span>
	// 		</div>

	// 		${compareHtml}

	// 		${branchHtml}

	// 	</div>
	// 	`;
	// }

	render_comparison(value, previous_value) {
		const periodLabel = this.get_previous_period_label();
		let direction, display;

		if (previous_value === 0 && value === 0) {
			direction = "stable";
			display = "0%";
		} else if (previous_value === 0 && value > 0) {
			direction = "up";
			display = __("New");
		} else {
			const pct = Math.round(((value - previous_value) / previous_value) * 100);
			direction = pct > 0 ? "up" : pct < 0 ? "down" : "stable";
			display = `${pct > 0 ? "+" : ""}${pct}%`;
		}

		const arrow = direction === "up" ? "▲" : direction === "down" ? "▼" : "▬";

		return `
			<div class="ocd-intensity-compare">
				<span class="ocd-intensity-compare-prev">${previous_value} <span class="ocd-intensity-compare-label">${periodLabel}</span></span>
				<span class="ocd-intensity-compare-pct ocd-intensity-compare-${direction}">${arrow} ${display}</span>
			</div>
		`;
	}

	empty_state(text) {
		return `
			<div class="ocd-empty-state">
				<div class="ocd-empty-icon">${ocd_icon("inbox")}</div>
				<div class="ocd-empty-text">${text}</div>
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

	render_sparkline(container, data) {
		if (!data.length) { container.innerHTML = this.empty_state(__("No trend data")); return; }

		const values = data.map(d => d.count || 0);
		const max = Math.max(...values, 1);
		const min = 0;
		const w = container.clientWidth || 600;
		const h = 220, pad = 14;
		const stepX = values.length > 1 ? (w - pad * 2) / (values.length - 1) : 0;
		const yFor = (v) => h - pad - ((v - min) / ((max - min) || 1)) * (h - pad * 2);
		const pts = values.map((v, i) => `${pad + i * stepX},${yFor(v)}`).join(" ");

		const avg = values.reduce((a, b) => a + b, 0) / values.length;
		const avgY = yFor(avg);

		const peakVal = Math.max(...values);
		const peakIdx = values.indexOf(peakVal);
		const peakX = pad + peakIdx * stepX;
		const peakY = yFor(peakVal);

		const todayStr = frappe.datetime.get_today();
		const todayIdx = data.findIndex(d => d.date === todayStr);

		const isUp = values[values.length - 1] > values[0];
		const gid  = "ocd-sg-" + Math.random().toString(36).slice(2, 9);
		const col  = isUp ? "var(--ocd-sev-warn)" : "var(--ocd-sev-ok)";

		const dots = values.map((v, i) => {
			const x = pad + i * stepX;
			const y = yFor(v);
			const label = data[i].label || data[i].date || "";
			const isPeak = i === peakIdx;
			const isToday = i === todayIdx;
			const titleText = frappe.utils.escape_html(`${label}: ${v}`);
			return `
				<g class="ocd-spark-point${isPeak ? " ocd-spark-point--peak" : ""}${isToday ? " ocd-spark-point--today" : ""}">
					<rect x="${x - Math.max(stepX, 1) / 2}" y="0" width="${Math.max(stepX, 1)}" height="${h}" fill="transparent"><title>${titleText}</title></rect>
					<circle cx="${x}" cy="${y}" r="${isPeak ? 5 : 3.5}" class="ocd-spark-dot" fill="${isPeak ? "var(--ocd-sev-critical)" : col}"><title>${titleText}</title></circle>
				</g>
			`;
		}).join("");

		container.innerHTML = `
			<svg width="100%" height="${h}" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" class="ocd-spark-svg">
				<defs>
					<linearGradient id="${gid}" x1="0" y1="0" x2="0" y2="1">
						<stop offset="0%" stop-color="${col}" stop-opacity="0.32"/>
						<stop offset="100%" stop-color="${col}" stop-opacity="0.02"/>
					</linearGradient>
				</defs>
				<line x1="${pad}" y1="${avgY}" x2="${w - pad}" y2="${avgY}" class="ocd-spark-avg-line"/>
				<polygon fill="url(#${gid})" points="${pts} ${w - pad},${h} ${pad},${h}"/>
				<polyline fill="none" stroke="${col}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" points="${pts}"/>
				${dots}
				${peakIdx >= 0 ? `<text x="${peakX}" y="${Math.max(peakY - 12, 12)}" class="ocd-spark-peak-label" text-anchor="middle">${__("Peak")} ${peakVal}</text>` : ""}
			</svg>
			<div class="ocd-spark-legend">
				<span><i class="ocd-legend-dot" style="background:${col}"></i>${__("Daily count")}</span>
				<span><i class="ocd-legend-dot ocd-legend-dot--avg"></i>${__("Average")}</span>
				${peakIdx >= 0 ? `<span><i class="ocd-legend-dot" style="background:var(--ocd-sev-critical)"></i>${__("Peak")}</span>` : ""}
			</div>
		`;
	}
}

// ---------------------------------------------------------------------------
// CSS
// ---------------------------------------------------------------------------
const OCD_CSS = `
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

/* Background watermark */
.ocd-bg-decor {
	content:"";
	position:fixed;
	inset:0;
	background-image: url("/files/SSV Logod5da1d.jpeg");
	background-repeat:no-repeat;
	background-position:center;
	background-size:460px;
	opacity:.035;
	filter:blur(1px) grayscale(0.3);
	pointer-events:none;
	z-index:0;
}
.ocd-root[data-theme="dark"] .ocd-bg-decor { opacity:.05; }

.ocd-icon { width:16px; height:16px; flex:none; display:inline-block; vertical-align:middle; }
.ocd-inline-icon { width:13px; height:13px; margin:0 4px; transition:transform .25s ease; }
.ocd-inline-icon--up { transform:rotate(180deg); }

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
	box-shadow:0 0 0 0 rgba(22,163,74,.5);
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
   3. TOOLBAR / FILTERS (FIXED Z-INDEX + CUSTOM ERPNEXT-STYLE DROPDOWNS)
   ========================================================================= */
.ocd-toolbar {
	display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;
	gap:var(--ocd-space-3);
	padding:var(--ocd-space-4);
	margin:var(--ocd-space-5) 0 var(--ocd-space-2);
	background:var(--ocd-surface);
	border:1px solid var(--ocd-border);
	border-radius:var(--ocd-radius-lg);
	box-shadow:var(--ocd-shadow-md);
	// position:sticky;
	top:8px;
	z-index:100;
	-webkit-backdrop-filter:blur(12px);
	backdrop-filter:blur(12px);
}

.ocd-toolbar-group { 
	display:flex;align-items:center;gap:var(--ocd-space-3);flex-wrap:wrap; 
	position:relative;
	z-index:101;
}

.ocd-toolbar-group--right { 
	margin-left:auto;
	position:relative;
	z-index:101;
}

/* Custom Select Wrapper */
.ocd-custom-select-wrapper {
	position:relative;
	display:flex;align-items:center;gap:10px;
	background:var(--ocd-surface);
	border:1px solid var(--ocd-border-strong);
	border-radius:6px;
	padding:0;
	transition:border-color .2s, box-shadow .2s;
	min-width:200px;
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
	display:flex;color:var(--ocd-muted);flex:none;
	opacity:0.7;
	padding-left:12px;
}

.ocd-custom-select-wrapper .ocd-field-icon .ocd-icon { 
	width:16px;height:16px;
}

.ocd-custom-select-wrapper .ocd-field-label {
	font-size:12px;
	font-weight:600;
	color:var(--ocd-ink-secondary);
	white-space:nowrap;
	letter-spacing:0.01em;
	padding:8px 0;
}

/* Custom Select */
.ocd-custom-select {
	position:relative;
	flex:1;
}

.ocd-custom-select-trigger {
	display:flex;align-items:center;justify-content:space-between;
	padding:8px 12px 8px 0;
	gap:8px;
	min-width:0;
}

.ocd-custom-select-text {
	font-size:14px;
	font-weight:500;
	color:var(--ocd-ink);
	overflow:hidden;
	text-overflow:ellipsis;
	white-space:nowrap;
}

.ocd-custom-select-arrow {
	width:16px;height:16px;
	color:var(--ocd-muted);
	flex:none;
	transition:transform 0.2s ease;
}

.ocd-custom-select.open .ocd-custom-select-arrow {
	transform:rotate(180deg);
}

/* Dropdown Options */
.ocd-custom-select-options {
	position:absolute;
	top:calc(100% + 4px);
	left:0;
	right:0;
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
/* Make both filter dropdowns fit content width */
.ocd-custom-select-wrapper[data-field-name="branch"] .ocd-custom-select-options,
.ocd-custom-select-wrapper[data-field-name="period"] .ocd-custom-select-options {
	right: auto;
	width: max-content;
	min-width: 100%;
}
.ocd-custom-select.open .ocd-custom-select-options {
	display:block;
	animation:ocd-dropdown-in 0.15s ease;
}

@keyframes ocd-dropdown-in {
	from {
		opacity:0;
		transform:translateY(-4px);
	}
	to {
		opacity:1;
		transform:translateY(0);
	}
}

/* Option Items */
.ocd-custom-option {
	padding:8px 12px;
	font-size:14px;
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
	margin-right:8px;
	font-size:12px;
	font-weight:700;
}

/* Scrollbar styling for options */
.ocd-custom-select-options::-webkit-scrollbar {
	width:6px;
}

.ocd-custom-select-options::-webkit-scrollbar-track {
	background:transparent;
}

.ocd-custom-select-options::-webkit-scrollbar-thumb {
	background:var(--ocd-border-strong);
	border-radius:3px;
}

.ocd-custom-select-options::-webkit-scrollbar-thumb:hover {
	background:var(--ocd-muted);
}

/* Remove old select styles */
.ocd-select {
	display:none;
}

.ocd-select-caret {
	display:none;
}

.ocd-custom-dates { 
	display:flex;align-items:center;gap:8px;
	position:relative;
	z-index:101;
}

.ocd-date-input {
	font-size:13px;
	padding:8px 12px;
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
	opacity:0.5;
	cursor:not-allowed;
	background:var(--ocd-surface-2);
}

.ocd-date-sep .ocd-icon { 
	width:14px;height:14px;color:var(--ocd-muted);
}

/* Action buttons */
.ocd-chip-btn {
	display:inline-flex;align-items:center;gap:6px;
	font-size:13px;font-weight:600;
	padding:8px 16px;
	border-radius:6px;
	border:1px solid var(--ocd-border-strong);
	background:var(--ocd-surface);
	color:var(--ocd-ink);
	cursor:pointer;
	font-family:inherit;
	transition:all .2s ease;
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

.ocd-chip-btn .ocd-icon { 
	width:14px;height:14px;
}

.ocd-btn {
	display:inline-flex;align-items:center;gap:7px;
	font-size:13px;font-weight:600;
	padding:9px 18px;
	border-radius:6px;
	border:1px solid var(--ocd-border);
	background:var(--ocd-surface);
	color:var(--ocd-ink);
	cursor:pointer;
	transition:all .2s ease;
	font-family:inherit;
}

.ocd-btn:hover { 
	border-color:var(--ocd-muted);
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

.ocd-btn .ocd-icon { 
	width:15px;height:15px;
}

/* Active filter chips */
.ocd-filter-context {
	display:flex;gap:8px;flex-wrap:wrap;
	padding:var(--ocd-space-3) 2px var(--ocd-space-2);
	font-size:12px;
	color:var(--ocd-muted);
	position:relative;
	z-index:1;
}

.ocd-ctx-chip {
	display:inline-flex;align-items:center;gap:6px;
	padding:5px 12px;
	border-radius:6px;
	font-weight:600;
	color:var(--ocd-ink-secondary);
	background:var(--ocd-surface);
	border:1px solid var(--ocd-border);
}

.ocd-ctx-icon { 
	width:12px;height:12px;
	color:var(--ocd-muted);
}

/* =========================================================================
   4. SECTIONS
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

/* =========================================================================
   5. KPI ROW
   ========================================================================= */
.ocd-kpi-row { display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:var(--ocd-space-4);margin-bottom:var(--ocd-space-2); }
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
.ocd-kpi-value { font-size:38px;font-weight:800;line-height:1;letter-spacing:-.02em; }
.ocd-kpi-footer { display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap; }
.ocd-kpi-sub { font-size:12.5px;color:var(--ocd-muted); }
.ocd-kpi-delta {
	display:inline-flex;align-items:center;gap:4px;flex-wrap:wrap;
	font-size:11px;font-weight:700;padding:4px 10px;
	border-radius:999px;background:var(--ocd-surface-2);width:fit-content;
}
.ocd-kpi-delta-label { font-weight:500;color:var(--ocd-muted); }
.ocd-kpi-delta-up      { color:var(--ocd-sev-critical); }
.ocd-kpi-delta-down    { color:var(--ocd-sev-ok); }
.ocd-kpi-delta-stable  { color:var(--ocd-sev-watch); }
.ocd-kpi-spark { display:block;margin-top:2px;width:100%;height:30px; }

/* =========================================================================
   6. GENERIC CARD / GRID
   ========================================================================= */
.ocd-grid { display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:var(--ocd-space-4); }
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

/* Empty state */
.ocd-empty-state { display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;padding:36px 12px;text-align:center; }
.ocd-empty-icon { width:44px;height:44px;border-radius:50%;background:var(--ocd-surface-2);display:flex;align-items:center;justify-content:center;color:var(--ocd-muted); }
.ocd-empty-icon .ocd-icon { width:20px;height:20px; }
.ocd-empty-text { font-size:13.5px;color:var(--ocd-muted);max-width:260px; }

/* Clickable elements */
.ocd-clickable-card, .ocd-clickable-row { cursor:pointer; }
.ocd-clickable-row { transition:background .2s,padding .2s; border-radius:8px; }
.ocd-clickable-row:hover { background:var(--ocd-surface-2); padding-left:8px;padding-right:8px;margin-left:-8px;margin-right:-8px; }
.ocd-clickable-card:hover { transform:translateY(-3px); box-shadow:var(--ocd-shadow-lg); border-color:var(--ocd-border-strong); }
.ocd-clickable-card:active { transform:translateY(-1px); }
.ocd-stat-card.ocd-clickable-card::after,
.ocd-intensity-card.ocd-clickable-card::after {
	content:'';position:absolute;bottom:0;left:0;right:0;height:3px;
	background:linear-gradient(90deg,var(--ocd-accent-steel),var(--ocd-accent-violet),var(--ocd-accent-teal));
	border-radius:0 0 var(--ocd-radius-lg) var(--ocd-radius-lg);
	opacity:0;transition:opacity .25s ease;z-index:2;
}
.ocd-stat-card.ocd-clickable-card:hover::after,
.ocd-intensity-card.ocd-clickable-card:hover::after { opacity:1; }

/* =========================================================================
   7. BRANCH STAT CARDS
   ========================================================================= */
.ocd-grid--branch { grid-template-columns:repeat(auto-fit,minmax(200px,240px));justify-content:center; }
.ocd-stat-card {
	display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;
	gap:10px;min-height:200px;
}
.ocd-stat-avatar {
	width:46px;height:46px;border-radius:50%;display:flex;align-items:center;justify-content:center;
	color:#fff;font-size:16px;font-weight:800;box-shadow:0 6px 14px rgba(0,0,0,.15);
}
.ocd-stat-content { position:relative;z-index:2;display:flex;flex-direction:column;align-items:center;gap:4px;width:100%; }
.ocd-stat-rank {
	position:absolute;top:12px;left:12px;z-index:3;font-family:var(--ocd-mono);
	font-size:11px;font-weight:700;color:var(--ocd-muted);
}
.ocd-card-value { font-size:34px;font-weight:800;letter-spacing:-.02em;line-height:1; }
.ocd-card-label { font-size:13px;color:var(--ocd-ink-secondary);font-weight:600; }
.ocd-stat-percent-wrap { width:100%;display:flex;flex-direction:column;align-items:center;gap:4px;margin-top:6px; }
.ocd-stat-percent-bar { width:100%;height:5px;background:var(--ocd-surface-2);border-radius:99px;overflow:hidden; }
.ocd-stat-percent-fill { height:100%;border-radius:99px;transition:width .7s ease; }
.ocd-stat-percent-label { font-size:11px;color:var(--ocd-muted);font-weight:600; }
.ocd-stat-card .ocd-intensity-compare { width:100%;margin-top:4px; }

/* =========================================================================
   8. REVISION TREND
   ========================================================================= */
.ocd-trend-full-width { margin-bottom:var(--ocd-space-6); }
.ocd-trend-full-card { padding:var(--ocd-space-6); }
.ocd-trend-full-header { display:flex;justify-content:space-between;align-items:flex-start;gap:12px;margin-bottom:var(--ocd-space-4);flex-wrap:wrap; }
.ocd-trend-heading { display:flex;align-items:center;gap:12px; }
.ocd-trend-heading-icon {
	width:38px;height:38px;border-radius:11px;flex:none;display:flex;align-items:center;justify-content:center;
	background:color-mix(in srgb, var(--ocd-accent-steel) 14%, transparent);color:var(--ocd-accent-steel);
}
.ocd-list-title { font-size:16px;font-weight:800;margin:0 0 3px;color:var(--ocd-ink); }
.ocd-list-subtitle { font-size:12.5px;color:var(--ocd-muted); }

.ocd-trend-badge-value {
	display:inline-flex;align-items:center;font-size:13px;font-weight:700;padding:5px 13px;border-radius:999px;
}
.ocd-trend-badge-value.up    { background:rgba(224,57,62,.1);color:var(--ocd-sev-critical); }
.ocd-trend-badge-value.down  { background:rgba(22,163,74,.1);color:var(--ocd-sev-ok); }
.ocd-trend-badge-value.stable{ background:rgba(217,140,14,.1);color:var(--ocd-sev-watch); }

.ocd-sparkline-full { margin:var(--ocd-space-2) 0; }
.ocd-spark-svg { display:block;width:100%;height:220px; }
.ocd-spark-avg-line { stroke:var(--ocd-muted); stroke-width:1; stroke-dasharray:4 4; opacity:.6; }
.ocd-spark-dot { stroke:var(--ocd-surface); stroke-width:2; transition:r .15s ease; }
.ocd-spark-point:hover .ocd-spark-dot { r:6; }
.ocd-spark-point--peak .ocd-spark-dot { filter:drop-shadow(0 0 4px rgba(224,57,62,.5)); }
.ocd-spark-point--today .ocd-spark-dot { stroke:var(--ocd-accent-steel); stroke-width:2.5; }
.ocd-spark-peak-label { font-size:10px;font-weight:700;fill:var(--ocd-sev-critical); }
.ocd-spark-legend { display:flex;gap:16px;flex-wrap:wrap;margin-top:6px; }
.ocd-spark-legend span { display:inline-flex;align-items:center;gap:6px;font-size:11.5px;color:var(--ocd-muted);font-weight:600; }
.ocd-legend-dot { width:8px;height:8px;border-radius:50%;display:inline-block; }
.ocd-legend-dot--avg { background:var(--ocd-muted);opacity:.7; }

.ocd-trend-stat-row {
	display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:var(--ocd-space-3);
	margin-top:var(--ocd-space-4);padding:var(--ocd-space-3) var(--ocd-space-4);
	background:var(--ocd-surface-2);border-radius:var(--ocd-radius-md);
}
.ocd-trend-stat { display:flex;flex-direction:column;gap:2px; }
.ocd-trend-stat-label { font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--ocd-muted);font-weight:700; }
.ocd-trend-stat-value { font-size:17px;font-weight:800;color:var(--ocd-ink); }
.ocd-trend-stat-value small { font-size:11px;font-weight:600;color:var(--ocd-muted); }

.ocd-trend-full-summary { margin-top:var(--ocd-space-4);padding-top:var(--ocd-space-4);border-top:1px solid var(--ocd-border); }
.ocd-trend-direction { display:flex;align-items:center;gap:8px;font-size:13px;color:var(--ocd-ink-secondary);font-weight:500; }
.ocd-trend-direction .ocd-icon { width:16px;height:16px; }
.ocd-trend-direction-down .ocd-icon { color:var(--ocd-sev-ok); }
.ocd-trend-direction-up .ocd-icon { color:var(--ocd-sev-critical); }
.ocd-trend-direction-stable .ocd-icon { color:var(--ocd-sev-watch); }

/* Period changes */
.ocd-trend-period-section { margin-top:var(--ocd-space-5);padding-top:var(--ocd-space-4);border-top:1px solid var(--ocd-border); }
.ocd-trend-period-header { margin-bottom:var(--ocd-space-3); }
.ocd-trend-period-title { display:flex;align-items:center;font-size:14px;font-weight:800;color:var(--ocd-ink); }
.ocd-trend-period-subtitle { display:block;font-size:12px;color:var(--ocd-muted);margin-top:2px; }
.ocd-period-rows { max-height:280px;overflow-y:auto; }
.ocd-period-row { gap:10px; }
.ocd-period-share { font-size:12px;font-weight:700;color:var(--ocd-muted);width:38px;text-align:right; }

/* =========================================================================
   9. LEADERBOARD / CUSTOMERS
   ========================================================================= */
.ocd-leaderboard-grid, .ocd-customers-grid { display:grid;grid-template-columns:repeat(auto-fit,minmax(310px,1fr));gap:var(--ocd-space-4); }
.ocd-list-card { padding:var(--ocd-space-5); }
.ocd-list-card-head { display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:var(--ocd-space-3); position:sticky; top:0; background:var(--ocd-surface); z-index:2; }
.ocd-export-btn {
	display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:700;
	padding:7px 12px;border-radius:var(--ocd-radius-sm);
	border:1px solid var(--ocd-border);
	background:var(--ocd-surface-2);color:var(--ocd-ink-secondary);cursor:pointer;
	white-space:nowrap;transition:background .2s,border-color .2s;
	font-family:inherit;flex:none;
}
.ocd-export-btn .ocd-icon { width:13px;height:13px; }
.ocd-export-btn:hover { background:var(--ocd-surface-3); }

.ocd-list-search {
	display:flex;align-items:center;gap:8px;margin-bottom:var(--ocd-space-3);
	padding:8px 12px;border-radius:var(--ocd-radius-sm);
	background:var(--ocd-surface-2);border:1px solid transparent;
	transition:border-color .2s,background .2s;
}
.ocd-list-search:focus-within { border-color:var(--ocd-border-strong);background:var(--ocd-surface); }
.ocd-list-search-icon { width:14px;height:14px;color:var(--ocd-muted);flex:none; }
.ocd-list-search-input { border:none;background:transparent;outline:none;font-size:12.5px;color:var(--ocd-ink);width:100%;font-family:inherit; }
.ocd-list-search-input::placeholder { color:var(--ocd-muted); }

.ocd-rows { display:flex;flex-direction:column; }
.ocd-row {
	display:flex;align-items:center;gap:12px;padding:10px 0;
	border-bottom:1px solid var(--ocd-surface-2);
	transition:background .2s;
}
.ocd-row:last-child { border-bottom:none; }
.ocd-row-extra { display:none; }
.ocd-list-card.ocd-expanded .ocd-row-extra { display:flex;animation:ocd-row-in .3s ease; }
@keyframes ocd-row-in { from{opacity:0;transform:translateY(-4px)} to{opacity:1;transform:translateY(0)} }
.ocd-row-rank { font-size:12px;color:var(--ocd-muted);width:18px;flex:none;font-weight:700;text-align:center; }
.ocd-row-medal { width:18px;flex:none;text-align:center;font-size:15px;line-height:1; }
.ocd-avatar {
	width:32px;height:32px;border-radius:50%;background:var(--accent);color:#fff;
	display:flex;align-items:center;justify-content:center;
	font-size:12px;font-weight:800;flex:none;box-shadow:0 3px 8px rgba(0,0,0,.15);
}
.ocd-row-name { flex:1 1 auto;min-width:0;font-size:13.5px;font-weight:600;color:var(--ocd-ink);overflow:hidden;text-overflow:ellipsis;white-space:nowrap; }
.ocd-row-bar-wrap { flex:0 0 100px;height:6px;background:var(--ocd-surface-2);border-radius:99px;overflow:hidden; }
.ocd-row-bar { display:block;height:100%;background:var(--accent);border-radius:99px;width:0;transition:width .7s ease; }
.ocd-row-count { font-size:13.5px;font-weight:700;width:34px;text-align:right;flex:none;color:var(--ocd-ink); }
.ocd-viewmore-btn {
	display:flex;align-items:center;justify-content:center;width:100%;margin:var(--ocd-space-4) 0 0;padding:10px;
	background:var(--ocd-surface-2);border:none;border-radius:var(--ocd-radius-sm);
	color:var(--ocd-ink);font-size:13px;font-weight:700;font-family:inherit;cursor:pointer;transition:background .2s;
}
.ocd-viewmore-btn:hover { background:var(--ocd-surface-3); }

/* =========================================================================
   10. INTENSITY CARDS (Order Change / Batch Change)
   ========================================================================= */
.ocd-intensity-card { display:flex;flex-direction:column;justify-content:space-between;gap:var(--ocd-space-4);min-height:210px; }
.ocd-intensity-top { display:flex;align-items:flex-start;justify-content:space-between;gap:12px; }
.ocd-intensity-top-main { display:flex;flex-direction:column;gap:4px; }
.ocd-intensity-value { margin-bottom:0; }
.ocd-intensity-desc { font-size:12px;color:var(--ocd-muted);font-weight:500; }
.ocd-intensity-badge {
	font-size:11px;font-weight:800;padding:5px 11px;border-radius:999px;
	border:1px solid transparent;white-space:nowrap;
	text-transform:uppercase;letter-spacing:.03em;flex:none;
}
.ocd-intensity-badge-ok       { color:var(--ocd-sev-ok);       background:rgba(22,163,74,.12);  border-color:rgba(22,163,74,.28); }
.ocd-intensity-badge-watch    { color:var(--ocd-sev-watch);    background:rgba(217,140,14,.12);  border-color:rgba(217,140,14,.28); }
.ocd-intensity-badge-warn     { color:var(--ocd-sev-warn);     background:rgba(234,115,23,.12);  border-color:rgba(234,115,23,.28); }
.ocd-intensity-badge-critical { color:var(--ocd-sev-critical); background:rgba(224,57,62,.12);   border-color:rgba(224,57,62,.28); }

.ocd-intensity-compare {
	display:flex;align-items:center;justify-content:space-between;gap:8px;
	font-size:12px;padding:9px 11px;border-radius:var(--ocd-radius-sm);
	background:var(--ocd-surface-2);
}
.ocd-intensity-compare-prev { display:flex;align-items:baseline;gap:4px;font-weight:700;color:var(--ocd-ink); }
.ocd-intensity-compare-label { font-weight:500;color:var(--ocd-muted);font-size:11px; }
.ocd-intensity-compare-pct { font-weight:700;display:inline-flex;align-items:center;gap:3px;font-size:12px; }
.ocd-intensity-compare-up      { color:var(--ocd-sev-critical); }
.ocd-intensity-compare-down    { color:var(--ocd-sev-ok); }
.ocd-intensity-compare-stable  { color:var(--ocd-sev-watch); }

.ocd-intensity-branches { display:flex;align-items:stretch;border-top:1px solid var(--ocd-border);padding-top:var(--ocd-space-3);margin-top:auto; }
.ocd-intensity-branch { flex:1;display:flex;flex-direction:column;align-items:center;gap:4px;padding:0 6px;position:relative; }
.ocd-intensity-branch + .ocd-intensity-branch::before { content:'';position:absolute;left:0;top:2px;bottom:2px;width:1px;background:var(--ocd-border); }
.ocd-intensity-branch-name { font-size:10px;color:var(--ocd-muted);text-transform:uppercase;letter-spacing:.04em;font-weight:600; }
.ocd-intensity-branch-count { font-size:15px;font-weight:800;color:var(--ocd-ink); }
.ocd-intensity-spacer { flex:1; }

/* =========================================================================
   11. ACCESSIBILITY / FOCUS
   ========================================================================= */
.ocd-root select:focus-visible,
.ocd-root button:focus-visible,
.ocd-root input:focus-visible,
.ocd-root [tabindex]:focus-visible {
	outline:2px solid var(--ocd-accent-steel);
	outline-offset:2px;
	border-radius:8px;
}

/* =========================================================================
   12. RESPONSIVE
   ========================================================================= */
@media (max-width: 1024px) {
	.ocd-root { padding:22px 20px 44px; }
	.ocd-toolbar { top:4px; }
}
@media (max-width: 768px) {
	.ocd-header { flex-direction:column;align-items:stretch; }
	.ocd-header-actions { justify-content:flex-end; }
	.ocd-toolbar { flex-direction:column;align-items:stretch;position:static; }
	.ocd-toolbar-group--right { margin-left:0;justify-content:flex-end;flex-wrap:wrap; }
	.ocd-kpi-row, .ocd-grid { grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); }
	.ocd-title { font-size:22px; }
	.ocd-kpi-value { font-size:30px; }
}
@media (max-width: 480px) {
	.ocd-kpi-row, .ocd-grid, .ocd-leaderboard-grid, .ocd-customers-grid { grid-template-columns:1fr; }
	.ocd-toolbar-group { width:100%; }
	.ocd-field { flex:1;min-width:0; }
}

/* =========================================================================
   13. REDUCED MOTION
   ========================================================================= */
@media (prefers-reduced-motion:reduce) {
	.ocd-card, .ocd-row-bar, .ocd-skel, .ocd-kpi-card, .ocd-status-dot,
	.ocd-theme-thumb, .ocd-icon-btn, .ocd-chip-btn, .ocd-btn-primary,
	.ocd-clickable-row, .ocd-inline-icon, .ocd-stat-percent-fill { transition:none;animation:none; }
	.ocd-section { animation:none;opacity:1; }
	.ocd-stat-card.ocd-clickable-card::after,
	.ocd-intensity-card.ocd-clickable-card::after { display:none; }
	.ocd-list-card.ocd-expanded .ocd-row-extra { animation:none; }
}
	/* Section Heading Context Badge */
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
    font-size: 15px;
    font-weight: 800;
    color: var(--ocd-accent-steel);
}

@media (max-width: 768px) {
    .ocd-section-context-badge {
        padding: 5px 10px;
        gap: 6px;
        font-size: 11px;
    }
    .ocd-section-context-count {
        font-size: 14px;
    }
}

`;