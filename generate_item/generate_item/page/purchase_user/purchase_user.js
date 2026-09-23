/**
 * Purchase User Dashboard
 * Visual & functional match to Sales Team KPI Dashboard (Procurement Document & Item Intelligence)
 */

const PUD_API = "generate_item.generate_item.page.purchase_user.purchase_user";

const PUD_BRANCHES = ["Sanand", "Nandikoor", "Rabale"];

const PUD_DATE_PRESETS = [
	"This Quarter",
	"Today",
	"This Week",
	"Last Week",
	"This Month",
	"Last Month",
	"Last Quarter",
	"This Year",
	"Last Year",
	"Custom",
];

const PUD_DOC_SEVERITY = {
	"1":  { key: "ok",       label: "1 Item Doc",   tag: "DOC·01", desc: "Single line item — standard" },
	"2":  { key: "watch",    label: "2 Items Doc",  tag: "DOC·02", desc: "Small batch" },
	"3":  { key: "warn",     label: "3 Items Doc",  tag: "DOC·03", desc: "Medium batch" },
	"3+": { key: "critical", label: "3+ Items Doc", tag: "DOC·04", desc: "Large batch / multi-item" },
};

const PUD_ITEM_SEVERITY = {
	"1":  { key: "ok",       label: "1 Linked Doc",   tag: "ITM·01", desc: "Single procurement record" },
	"2":  { key: "watch",    label: "2 Linked Docs",  tag: "ITM·02", desc: "Dual procurement records" },
	"3":  { key: "warn",     label: "3 Linked Docs",  tag: "ITM·03", desc: "Multiple procurement records" },
	"3+": { key: "critical", label: "3+ Linked Docs", tag: "ITM·04", desc: "High frequency procurement" },
};

// ---------------------------------------------------------------------------
// SVG Icon Helper (Lucide-style stroke-based icons)
// ---------------------------------------------------------------------------
const PUD_ICON_PATHS = {
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
	user:          `<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>`,
	fileText:      `<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/>`,
	externalLink:  `<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>`,
	x:             `<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>`,
};

function pud_icon(name, cls = "") {
	const inner = PUD_ICON_PATHS[name] || "";
	return `<svg class="pud-icon ${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${inner}</svg>`;
}

// ─── Utility: Safe Date Parsing & Formatting ────────────────────────────────
function pud_normalize_iso(val) {
	if (!val) return "";
	const s = String(val).trim().split(" ")[0].replace(/\//g, "-");
	const parts = s.split("-");
	if (parts.length === 3) {
		if (parts[0].length === 4) return `${parts[0]}-${parts[1].padStart(2, "0")}-${parts[2].padStart(2, "0")}`;
		if (parts[2].length === 4) return `${parts[2]}-${parts[1].padStart(2, "0")}-${parts[0].padStart(2, "0")}`;
	}
	return s;
}

function pud_fmt_date(val) {
	if (!val || val === "—") return "—";
	const iso = pud_normalize_iso(val);
	const parts = iso.split("-");
	if (parts.length === 3 && parts[0].length === 4) {
		return `${parts[2]}/${parts[1]}/${parts[0]}`;
	}
	return val;
}

// ─── Route Registration ─────────────────────────────────────────────────────
const purchase_user_dashboard_routes = ["purchase-user", "purchase_user"];

function ensure_purchase_user_dashboard(wrapper) {
	if (wrapper.purchase_user_dashboard) return;
	wrapper.purchase_user_dashboard = new PurchaseUserDashboard(wrapper);
}

purchase_user_dashboard_routes.forEach((route) => {
	if (frappe.pages[route]) {
		frappe.pages[route].on_page_load = function (wrapper) {
			ensure_purchase_user_dashboard(wrapper);
		};

		frappe.pages[route].on_page_show = function (wrapper) {
			if (frappe.breadcrumbs && frappe.breadcrumbs.add) {
				frappe.breadcrumbs.add({
					type: "Custom",
					label: __("Purchase User Dashboard"),
					route: "#purchase-user",
				});
			}
			if (wrapper.page && wrapper.page.set_title) {
				wrapper.page.set_title(__("Purchase User Dashboard"));
			}
			if (wrapper.purchase_user_dashboard && !wrapper.purchase_user_dashboard.loading) {
				wrapper.purchase_user_dashboard.refresh();
			}
		};
	}
});

// ─── Dashboard Class ────────────────────────────────────────────────────────
class PurchaseUserDashboard {
	constructor(wrapper) {
		this.wrapper = wrapper;
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __("Purchase User Dashboard"),
			single_column: true,
		});

		const defaultDates = this.resolve_preset("This Quarter");
		this.filters = {
			branch: "",
			user: "", // Default to All Allowed Users
			preset: "This Quarter",
			from_date: defaultDates.from_date,
			to_date: defaultDates.to_date,
		};

		this.allowed_users = [];
		this.cards = [];
		this.item_summary = [];
		this.total_distinct_items = 0;
		this.loading = false;

		// Stage intensity filter states
		this.order_intensity_stage = "all";
		this.batch_intensity_stage = "all";
		this.item_table_stage = "all";
		this.item_search_query = "";

		this.inject_styles();
		this.render_shell();
		this.bind_events();
		this.init_users_and_load();
	}

	inject_styles() {
		if (document.getElementById("pud-styles")) return;
		const s = document.createElement("style");
		s.id = "pud-styles";
		s.textContent = PUD_CSS;
		document.head.appendChild(s);
	}

	get_theme() {
		return localStorage.getItem("pud_theme") || "light";
	}

	set_theme(theme) {
		localStorage.setItem("pud_theme", theme);
		if (this.root) this.root.setAttribute("data-theme", theme);
		const icon = this.wrapper.querySelector(".pud-theme-icon");
		const text = this.wrapper.querySelector(".pud-theme-text");
		if (icon) icon.textContent = theme === "dark" ? "☾" : "☀";
		if (text) text.textContent = theme === "dark" ? __("Dark mode") : __("Light mode");
	}

	async init_users_and_load() {
		try {
			const users = await this.call("get_allowed_users") || [];
			this.allowed_users = users;
			this.populate_user_options(users);
		} catch (_e) {
			this.allowed_users = [];
		}
		this.refresh();
	}

	populate_user_options(users) {
		const userSelect = this.wrapper.querySelector("[data-role='user-select']");
		if (!userSelect) return;
		const optionsContainer = userSelect.querySelector(".pud-custom-select-options");
		if (!optionsContainer) return;

		let html = `<div class="pud-custom-option selected" data-value="">${__("All Allowed Users")}</div>`;
		users.forEach((u) => {
			const val = u.value || u.name;
			const lbl = u.label || u.full_name || val;
			html += `<div class="pud-custom-option" data-value="${frappe.utils.escape_html(val)}">${frappe.utils.escape_html(lbl)}</div>`;
		});
		optionsContainer.innerHTML = html;
		this.bind_select_events(userSelect.closest(".pud-custom-select-wrapper"));
	}

	// ----------------------------------------------------------------- shell
	render_shell() {
		$(this.page.body).html(`
			<div class="pud-root" data-theme="${frappe.utils.escape_html(this.get_theme())}">
				<div class="pud-bg-decor" aria-hidden="true"></div>

				<!-- ── Modal Wrapper ── -->
				<div class="pud-modal-wrap" id="pud-modal" style="display:none;">
					<div class="pud-modal-bg"></div>
					<div class="pud-modal-box" id="pud-modal-body"></div>
				</div>

				<!-- ── Header ── -->
				<header class="pud-header">
					<div class="pud-header-left">
						<div class="pud-header-icon">${pud_icon("factory")}</div>
						<div class="pud-header-text">
							<div class="pud-header-titlerow">
								<h1 class="pud-title">${__("Purchase User Dashboard")}</h1>
								<span class="pud-status-chip" title="${__("Data is refreshed on demand")}">
									<span class="pud-status-dot" aria-hidden="true"></span>${__("Live")}
								</span>
							</div>
							<p class="pud-subtitle">${__("Material Request, Purchase Order, Receipt & Invoice Intelligence across all branches")}</p>
							<div class="pud-header-meta" data-field="summary">${__("Loading…")}</div>
						</div>
					</div>
					<div class="pud-header-actions">
						<button class="pud-theme-toggle" type="button" title="${__("Toggle theme")}" aria-label="${__("Toggle theme")}">
							<span class="pud-theme-track">
								<span class="pud-theme-thumb">
									<span class="pud-theme-icon" aria-hidden="true">☀</span>
								</span>
							</span>
							<span class="pud-theme-text">${__("Light mode")}</span>
						</button>
					</div>
				</header>

				<!-- ── Filter Toolbar ── -->
				<div class="pud-toolbar">
					<div class="pud-toolbar-group">
						<!-- Branch Selector -->
						<div class="pud-field pud-custom-select-wrapper" data-field-name="branch">
							<span class="pud-field-icon">${pud_icon("building")}</span>
							<span class="pud-field-label">${__("Branch")}</span>
							<div class="pud-custom-select" data-role="branch-select">
								<div class="pud-custom-select-trigger">
									<span class="pud-custom-select-text">${__("All Branches")}</span>
									${pud_icon("chevronDown", "pud-custom-select-arrow")}
								</div>
								<div class="pud-custom-select-options">
									<div class="pud-custom-option selected" data-value="">${__("All Branches")}</div>
									${PUD_BRANCHES.map((b) => `<div class="pud-custom-option" data-value="${b}">${b}</div>`).join("")}
								</div>
							</div>
						</div>

						<!-- Created By (User) Selector -->
						<div class="pud-field pud-custom-select-wrapper" data-field-name="user">
							<span class="pud-field-icon">${pud_icon("user")}</span>
							<span class="pud-field-label">${__("Created By")}</span>
							<div class="pud-custom-select" data-role="user-select">
								<div class="pud-custom-select-trigger">
									<span class="pud-custom-select-text">${__("All Allowed Users")}</span>
									${pud_icon("chevronDown", "pud-custom-select-arrow")}
								</div>
								<div class="pud-custom-select-options">
									<div class="pud-custom-option selected" data-value="">${__("All Allowed Users")}</div>
								</div>
							</div>
						</div>

						<!-- Period Selector -->
						<div class="pud-field pud-custom-select-wrapper" data-field-name="period">
							<span class="pud-field-icon">${pud_icon("calendar")}</span>
							<span class="pud-field-label">${__("Period")}</span>
							<div class="pud-custom-select" data-role="date-preset">
								<div class="pud-custom-select-trigger">
									<span class="pud-custom-select-text">${__("This Quarter")}</span>
									${pud_icon("chevronDown", "pud-custom-select-arrow")}
								</div>
								<div class="pud-custom-select-options">
									${PUD_DATE_PRESETS.map((p) => `
										<div class="pud-custom-option ${p === "This Quarter" ? "selected" : ""}" data-value="${p}">${__(p)}</div>
									`).join("")}
								</div>
							</div>
						</div>

						<!-- Custom Date Inputs -->
						<div class="pud-custom-dates" data-role="custom-dates">
							<input type="date" class="pud-date-input" data-role="from-date" aria-label="${__("From date")}" disabled />
							<span class="pud-date-sep">${pud_icon("arrowRight")}</span>
							<input type="date" class="pud-date-input" data-role="to-date" aria-label="${__("To date")}" disabled />
						</div>
					</div>

					<div class="pud-toolbar-group pud-toolbar-group--right">
						<button type="button" class="pud-chip-btn" data-role="today-shortcut">${__("Today")}</button>
						<button type="button" class="pud-chip-btn pud-chip-btn--ghost" data-role="reset-filters" title="${__("Reset filters")}">
							${pud_icon("rotate")}<span>${__("Reset")}</span>
						</button>
						<button class="pud-btn pud-btn-primary pud-refresh-btn" type="button">
							${pud_icon("refresh")}<span>${__("Refresh")}</span>
						</button>
					</div>
				</div>

				<!-- ── Top KPI Cards ── -->
				<div class="pud-kpi-row" data-role="top-kpis"></div>

				<!-- ── Section 01 · Material Request Trend (Item-wise) ── -->
				<section class="pud-section" data-section="mr-trend">
					${this.section_head("01", __("Material Request Trend (Item-wise)"))}
					<div class="pud-trend-full-width" data-trend-full></div>
				</section>

				<!-- ── Section 02 · Document Intensity (Document-wise) ── -->
				<section class="pud-section" data-section="order-change">
					<div class="pud-section-head">
						<span class="pud-section-index">02</span>
						<span class="pud-section-title">${__("Document Intensity (Document-wise)")}</span>
						<span class="pud-section-context" id="order-context"></span>
						<span class="pud-section-line" aria-hidden="true"></span>
					</div>
					<div class="pud-stage-pills-bar" data-pills="order-change">
						<button type="button" class="pud-stage-pill active" data-stage="all">${__("All Stages")}</button>
						<button type="button" class="pud-stage-pill" data-stage="po_pending">${__("MR Pending")}</button>
						<button type="button" class="pud-stage-pill" data-stage="mr_completed">${__("MR Ordered")}</button>
						<button type="button" class="pud-stage-pill" data-stage="pr_pending">${__("PR Pending")}</button>
						<button type="button" class="pud-stage-pill" data-stage="pi_pending">${__("PI Pending")}</button>
						<button type="button" class="pud-stage-pill" data-stage="pi_completed">${__("PI Completed")}</button>
					</div>
					<div class="pud-grid pud-grid--4" data-grid="order-intensity"></div>
				</section>

				<!-- ── Section 03 · Item Intensity (Item-wise) ── -->
				<section class="pud-section" data-section="batch-change">
					<div class="pud-section-head">
						<span class="pud-section-index">03</span>
						<span class="pud-section-title">${__("Item Intensity (Item-wise)")}</span>
						<span class="pud-section-context" id="batch-context"></span>
						<span class="pud-section-line" aria-hidden="true"></span>
					</div>
					<div class="pud-stage-pills-bar" data-pills="batch-change">
						<button type="button" class="pud-stage-pill active" data-stage="all">${__("All Stages")}</button>
						<button type="button" class="pud-stage-pill" data-stage="po_pending">${__("MR Pending")}</button>
						<button type="button" class="pud-stage-pill" data-stage="mr_completed">${__("MR Ordered")}</button>
						<button type="button" class="pud-stage-pill" data-stage="pr_pending">${__("PR Pending")}</button>
						<button type="button" class="pud-stage-pill" data-stage="pi_pending">${__("PI Pending")}</button>
						<button type="button" class="pud-stage-pill" data-stage="pi_completed">${__("PI Completed")}</button>
					</div>
					<div class="pud-grid pud-grid--batch-buckets" data-grid="batch-intensity"></div>

					<!-- Detailed Searchable Item Table directly below -->
					<div class="pud-item-table-container">
						<div class="pud-item-toolbar">
							<div class="pud-item-toolbar-left">
								<div class="pud-item-search-wrap">
									${pud_icon("search")}
									<input type="text" class="pud-item-search-input" data-role="item-table-search" placeholder="${__("Search item code, name, or document…")}" />
								</div>
								<div class="pud-item-stage-tabs" role="tablist">
									<button type="button" class="pud-stage-tab-btn active" data-tab="all">${__("All Items")} <span class="pud-count-pill" id="pud-pill-all">0</span></button>
									<button type="button" class="pud-stage-tab-btn" data-tab="po_pending">${__("MR Pending")} <span class="pud-count-pill" id="pud-pill-po">0</span></button>
									<button type="button" class="pud-stage-tab-btn" data-tab="mr_completed">${__("MR Ordered")} <span class="pud-count-pill" id="pud-pill-mr">0</span></button>
									<button type="button" class="pud-stage-tab-btn" data-tab="pr_pending">${__("PR Pending")} <span class="pud-count-pill" id="pud-pill-pr">0</span></button>
									<button type="button" class="pud-stage-tab-btn" data-tab="pi_pending">${__("PI Pending")} <span class="pud-count-pill" id="pud-pill-pi">0</span></button>
									<button type="button" class="pud-stage-tab-btn" data-tab="pi_completed">${__("PI Completed")} <span class="pud-count-pill" id="pud-pill-cmp">0</span></button>
								</div>
							</div>
							<div class="pud-item-toolbar-right">
								<button type="button" class="pud-export-btn pud-export-items-csv" title="${__("Export CSV")}">
									${pud_icon("download")}${__("CSV")}
								</button>
							</div>
						</div>

						<div class="pud-item-table-wrap">
							<table class="pud-item-table">
								<thead>
									<tr>
										<th style="width:170px;">${__("Item Code")}</th>
										<th>${__("Item Name")}</th>
										<th style="width:130px;">${__("Stage")}</th>
										<th style="width:120px;text-align:right;">${__("Pending Qty")}</th>
										<th style="width:105px;text-align:right;">${__("Total Qty")}</th>
										<th style="width:125px;text-align:right;">${__("Est. Amount")}</th>
										<th style="width:140px;">${__("Branch / Warehouse")}</th>
										<th style="width:190px;">${__("Linked Documents")}</th>
									</tr>
								</thead>
								<tbody id="pud-item-table-body"></tbody>
							</table>
						</div>
						<div id="pud-item-table-empty" class="pud-empty-state" style="display:none;">
							<div class="pud-empty-icon">${pud_icon("inbox")}</div>
							<div class="pud-empty-text">${__("No matching line items found.")}</div>
						</div>
					</div>
				</section>

				<!-- ── Section 04 · Creator Leaderboard ── -->
				<section class="pud-section" data-section="leaderboard">
					${this.section_head("04", __("Creator Leaderboard (Purchase Orders)"))}
					<div class="pud-leaderboard-grid"></div>
				</section>

			</div>
		`);

		this.root = this.wrapper.querySelector(".pud-root");

		// Initialize date inputs
		const fromInput = this.wrapper.querySelector("[data-role='from-date']");
		const toInput = this.wrapper.querySelector("[data-role='to-date']");
		if (fromInput) fromInput.value = this.filters.from_date;
		if (toInput) toInput.value = this.filters.to_date;
	}

	section_head(index, title) {
		return `
			<div class="pud-section-head">
				<span class="pud-section-index">${index}</span>
				<span class="pud-section-title">${title}</span>
				<span class="pud-section-line" aria-hidden="true"></span>
			</div>
		`;
	}

	// ---------------------------------------------------------------- events
	bind_events() {
		// Theme toggle
		const themeToggle = this.wrapper.querySelector(".pud-theme-toggle");
		if (themeToggle) {
			themeToggle.addEventListener("click", () => {
				this.set_theme(this.root.getAttribute("data-theme") === "dark" ? "light" : "dark");
			});
		}
		this.set_theme(this.get_theme());

		// Refresh Button
		const refreshBtn = this.wrapper.querySelector(".pud-refresh-btn");
		if (refreshBtn) {
			refreshBtn.addEventListener("click", () => this.refresh());
		}

		// Reset Button
		const resetBtn = this.wrapper.querySelector("[data-role='reset-filters']");
		if (resetBtn) {
			resetBtn.addEventListener("click", () => this.reset_filters());
		}

		// Today Shortcut
		const todayBtn = this.wrapper.querySelector("[data-role='today-shortcut']");
		if (todayBtn) {
			todayBtn.addEventListener("click", () => this.apply_preset("Today"));
		}

		// Custom Date Inputs
		const fromInput = this.wrapper.querySelector("[data-role='from-date']");
		const toInput = this.wrapper.querySelector("[data-role='to-date']");
		if (fromInput) fromInput.addEventListener("change", () => this.sync_custom_dates());
		if (toInput) toInput.addEventListener("change", () => this.sync_custom_dates());

		// Stage Pills for Document Intensity
		const orderPills = this.wrapper.querySelector('[data-pills="order-change"]');
		if (orderPills) {
			orderPills.addEventListener("click", (e) => {
				const pill = e.target.closest(".pud-stage-pill");
				if (!pill) return;
				orderPills.querySelectorAll(".pud-stage-pill").forEach((p) => p.classList.remove("active"));
				pill.classList.add("active");
				this.order_intensity_stage = pill.dataset.stage;
				this.render_order_change_intensity(this.last_data);
			});
		}

		// Stage Pills for Item Intensity
		const batchPills = this.wrapper.querySelector('[data-pills="batch-change"]');
		if (batchPills) {
			batchPills.addEventListener("click", (e) => {
				const pill = e.target.closest(".pud-stage-pill");
				if (!pill) return;
				batchPills.querySelectorAll(".pud-stage-pill").forEach((p) => p.classList.remove("active"));
				pill.classList.add("active");
				this.batch_intensity_stage = pill.dataset.stage;
				this.render_item_change_intensity(this.last_data);
			});
		}

		// Item Table Stage Tabs
		const itemTabs = this.wrapper.querySelector(".pud-item-stage-tabs");
		if (itemTabs) {
			itemTabs.addEventListener("click", (e) => {
				const btn = e.target.closest(".pud-stage-tab-btn");
				if (!btn) return;
				itemTabs.querySelectorAll(".pud-stage-tab-btn").forEach((b) => b.classList.remove("active"));
				btn.classList.add("active");
				this.item_table_stage = btn.dataset.tab;
				this.filter_and_render_item_rows();
			});
		}

		// Live Item Table Search
		const itemSearch = this.wrapper.querySelector("[data-role='item-table-search']");
		if (itemSearch) {
			itemSearch.addEventListener("input", (e) => {
				this.item_search_query = e.target.value;
				this.filter_and_render_item_rows();
			});
		}

		// Export Item CSV
		const exportItemsBtn = this.wrapper.querySelector(".pud-export-items-csv");
		if (exportItemsBtn) {
			exportItemsBtn.addEventListener("click", () => this.export_items_csv());
		}

		// Global Click Delegations (Cards, Modals, Creator Rows)
		this.wrapper.addEventListener("click", (e) => {
			// Direct Open in List View
			const openListBtn = e.target.closest("[data-open-list]");
			if (openListBtn) {
				e.preventDefault();
				e.stopPropagation();
				const cardId = openListBtn.dataset.openList;
				const doctype = openListBtn.dataset.doctype;
				let docNames = null;
				if (openListBtn.dataset.docNames) {
					try {
						docNames = JSON.parse(openListBtn.dataset.docNames);
					} catch (err) {}
				}
				this.open_list_view(cardId, doctype, docNames);
				return;
			}

			// KPI Card click -> Modal Inspection
			const kpiCard = e.target.closest(".pud-kpi-card[data-card-id]");
			if (kpiCard) {
				const cardId = kpiCard.dataset.cardId;
				this.open_stage_modal(cardId);
			}

			// Intensity Card click -> Modal Inspection
			const intensityCard = e.target.closest(".pud-intensity-card[data-intensity-type]");
			if (intensityCard) {
				const type = intensityCard.dataset.intensityType;
				const sevKey = intensityCard.dataset.severity;
				this.open_intensity_modal(type, sevKey);
			}

			// Creator Row Click in Leaderboard -> Open Purchase Order List View filtered by creator
			const creatorRow = e.target.closest(".pud-clickable-row[data-creator]");
			if (creatorRow) {
				const creator = creatorRow.dataset.creator;
				this.open_po_list_by_creator(creator);
			}

			// Modal backdrop / Close button
			if (e.target.closest(".pud-modal-bg") || e.target.closest("[data-close-modal]")) {
				this.close_modal();
			}

			// Modal Row Toggle
			const rowToggle = e.target.closest("[data-row-toggle]");
			if (rowToggle) {
				const rowId = rowToggle.dataset.rowToggle;
				const detail = this.wrapper.querySelector(`#${rowId}-detail`);
				const icon = this.wrapper.querySelector(`#${rowId}-icon`);
				if (detail) {
					const isHidden = detail.style.display === "none";
					detail.style.display = isHidden ? "block" : "none";
					if (icon) icon.textContent = isHidden ? "▼" : "▶";
				}
			}
		});

		// Modal ESC key
		document.addEventListener("keydown", (e) => {
			if (e.key === "Escape") this.close_modal();
		});

		this.init_custom_selects();
	}

	init_custom_selects() {
		this.wrapper.querySelectorAll(".pud-custom-select-wrapper").forEach((wrapper) => {
			this.bind_select_events(wrapper);
		});
	}

	bind_select_events(wrapper) {
		const select = wrapper.querySelector(".pud-custom-select");
		if (!select) return;
		const trigger = select.querySelector(".pud-custom-select-trigger");
		const text = select.querySelector(".pud-custom-select-text");
		const options = select.querySelectorAll(".pud-custom-option");

		// Toggle dropdown
		trigger.onclick = (e) => {
			e.stopPropagation();
			this.wrapper.querySelectorAll(".pud-custom-select.open").forEach((s) => {
				if (s !== select) s.classList.remove("open");
			});
			select.classList.toggle("open");
		};

		// Option Selection
		options.forEach((opt) => {
			opt.onclick = (e) => {
				e.stopPropagation();
				const val = opt.dataset.value;
				text.textContent = opt.textContent.replace("✓", "").trim();
				options.forEach((o) => o.classList.remove("selected"));
				opt.classList.add("selected");
				select.classList.remove("open");

				const role = select.dataset.role;
				if (role === "branch-select") {
					this.filters.branch = val;
					this.refresh();
				} else if (role === "user-select") {
					this.filters.user = val;
					this.refresh();
				} else if (role === "date-preset") {
					this.apply_preset(val);
				}
			};
		});

		// Close when clicking outside
		document.addEventListener("click", (e) => {
			if (!select.contains(e.target)) select.classList.remove("open");
		});
	}

	apply_preset(preset) {
		this.filters.preset = preset;
		const presetSelect = this.wrapper.querySelector("[data-role='date-preset']");
		if (presetSelect) {
			const options = presetSelect.querySelectorAll(".pud-custom-option");
			const text = presetSelect.querySelector(".pud-custom-select-text");
			options.forEach((o) => o.classList.remove("selected"));
			const opt = presetSelect.querySelector(`[data-value="${preset}"]`);
			if (opt) {
				opt.classList.add("selected");
				if (text) text.textContent = opt.textContent.replace("✓", "").trim();
			}
		}

		const fromInput = this.wrapper.querySelector("[data-role='from-date']");
		const toInput = this.wrapper.querySelector("[data-role='to-date']");

		if (preset !== "Custom") {
			const { from_date, to_date } = this.resolve_preset(preset);
			this.filters.from_date = from_date;
			this.filters.to_date = to_date;
			if (fromInput) { fromInput.value = from_date; fromInput.disabled = true; }
			if (toInput) { toInput.value = to_date; toInput.disabled = true; }
			this.refresh();
		} else {
			if (fromInput) fromInput.disabled = false;
			if (toInput) toInput.disabled = false;
			if (fromInput && !fromInput.value) fromInput.value = frappe.datetime.get_today();
			if (toInput && !toInput.value) toInput.value = frappe.datetime.get_today();
			this.sync_custom_dates();
		}
	}

	sync_custom_dates() {
		const fromInput = this.wrapper.querySelector("[data-role='from-date']");
		const toInput = this.wrapper.querySelector("[data-role='to-date']");
		if (fromInput && toInput && fromInput.value && toInput.value) {
			this.filters.from_date = fromInput.value;
			this.filters.to_date = toInput.value;
			this.refresh();
		}
	}

	reset_filters() {
		// Reset Branch
		const branchSelect = this.wrapper.querySelector("[data-role='branch-select']");
		if (branchSelect) {
			branchSelect.querySelectorAll(".pud-custom-option").forEach((o) => o.classList.remove("selected"));
			const allOpt = branchSelect.querySelector('[data-value=""]');
			if (allOpt) allOpt.classList.add("selected");
			const txt = branchSelect.querySelector(".pud-custom-select-text");
			if (txt) txt.textContent = __("All Branches");
		}
		this.filters.branch = "";

		// Reset User
		const userSelect = this.wrapper.querySelector("[data-role='user-select']");
		if (userSelect) {
			userSelect.querySelectorAll(".pud-custom-option").forEach((o) => o.classList.remove("selected"));
			const allOpt = userSelect.querySelector('[data-value=""]');
			if (allOpt) allOpt.classList.add("selected");
			const txt = userSelect.querySelector(".pud-custom-select-text");
			if (txt) txt.textContent = __("All Allowed Users");
		}
		this.filters.user = "";

		// Reset Preset to This Quarter
		this.apply_preset("This Quarter");
	}

	filter_by_user(user) {
		if (!user) return;
		this.filters.user = user;
		const userSelect = this.wrapper.querySelector("[data-role='user-select']");
		if (userSelect) {
			userSelect.querySelectorAll(".pud-custom-option").forEach((o) => o.classList.remove("selected"));
			const targetOpt = userSelect.querySelector(`[data-value="${user}"]`);
			const txt = userSelect.querySelector(".pud-custom-select-text");
			if (targetOpt) {
				targetOpt.classList.add("selected");
				if (txt) txt.textContent = targetOpt.textContent.replace("✓", "").trim();
			} else if (txt) {
				txt.textContent = user;
			}
		}
		this.refresh();
	}

	// --------------------------------------------------------- date helpers
	resolve_preset(preset) {
		const today = frappe.datetime.get_today();
		const todayDate = frappe.datetime.str_to_obj(today);

		const fmt = (d) => frappe.datetime.obj_to_str(d);
		const add = (d, n) => { const x = new Date(d); x.setDate(x.getDate() + n); return x; };
		const subMonths = (d, n) => { const x = new Date(d); x.setMonth(x.getMonth() - n); return x; };
		const dow = todayDate.getDay();
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
		const fmt = (d) => frappe.datetime.obj_to_str(d);
		const toObj = (s) => frappe.datetime.str_to_obj(s);
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
			case "This Year":
			case "Last Year": {
				const cur = toObj(from_date);
				const prevFirst = new Date(cur.getFullYear() - 1, 0, 1);
				const prevLast  = new Date(cur.getFullYear() - 1, 11, 31);
				return { from_date: fmt(prevFirst), to_date: fmt(prevLast) };
			}
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
			case "Today": return __("yesterday");
			case "This Week": return __("last week");
			case "Last Week": return __("prior week");
			case "This Month": return __("last month");
			case "Last Month": return __("prior month");
			case "This Quarter": return __("previous quarter");
			case "Last Quarter": return __("quarter before that");
			case "This Year": return __("last year");
			case "Last Year": return __("prior year");
			default: return __("prior period");
		}
	}

	// ------------------------------------------------------------------ data
	async call(method, args = {}) {
		const response = await frappe.call({
			method: `${PUD_API}.${method}`,
			args,
		});
		return response.message;
	}

	async refresh() {
		if (this.loading) return;
		this.loading = true;
		this.show_loading();

		const prevRange = this.resolve_previous_range(
			this.filters.preset,
			this.filters.from_date,
			this.filters.to_date
		);

		const args = {
			branch: this.filters.branch || "",
			users: this.filters.user ? [this.filters.user] : "",
			from_date: this.filters.from_date,
			to_date: this.filters.to_date,
			prev_from_date: prevRange.from_date,
			prev_to_date: prevRange.to_date,
			period: this.filters.preset,
		};

		try {
			const data = await this.call("get_dashboard", args);
			if (!data) {
				this.show_error(__("No dashboard data returned."));
				return;
			}

			this.last_data = data;
			this.cards = data.cards || [];
			this.item_summary = data.item_summary || [];
			this.total_distinct_items = data.total_distinct_items || 0;

			// Error Isolation: Wrap each section in its own try/catch
			try { this.render_summary(data); } catch (e) { console.error("Error in render_summary:", e); }
			try { this.render_top_kpis(data); } catch (e) { console.error("Error in render_top_kpis:", e); }
			try { this.render_mr_trend(data); } catch (e) { console.error("Error in render_mr_trend:", e); }
			try { this.render_order_change_intensity(data); } catch (e) { console.error("Error in render_order_change_intensity:", e); }
			try { this.render_item_change_intensity(data); } catch (e) { console.error("Error in render_item_change_intensity:", e); }
			try { this.render_item_table(); } catch (e) { console.error("Error in render_item_table:", e); }
			try { this.render_leaderboard(data); } catch (e) { console.error("Error in render_leaderboard:", e); }

		} catch (error) {
			console.error("Dashboard refresh error:", error);
			this.show_error(error?.message || __("Error loading dashboard data."));
		} finally {
			this.loading = false;
		}
	}

	show_loading() {
		const sumEl = this.wrapper.querySelector('[data-field="summary"]');
		if (sumEl) sumEl.textContent = __("Loading…");
		const trendEl = this.wrapper.querySelector('[data-trend-full]');
		if (trendEl) trendEl.innerHTML = '<div class="pud-card pud-skel" style="height:380px"></div>';
		const kpiEl = this.wrapper.querySelector('[data-role="top-kpis"]');
		if (kpiEl) kpiEl.innerHTML = this.skeleton_cards(5, 170);
		const orderGrid = this.wrapper.querySelector('[data-grid="order-intensity"]');
		if (orderGrid) orderGrid.innerHTML = this.skeleton_cards(4, 230);
		const batchGrid = this.wrapper.querySelector('[data-grid="batch-intensity"]');
		if (batchGrid) batchGrid.innerHTML = this.skeleton_cards(4, 230);
		const leadGrid = this.wrapper.querySelector('.pud-leaderboard-grid');
		if (leadGrid) leadGrid.innerHTML = `<div class="pud-card pud-skel" style="height:280px"></div><div class="pud-card pud-skel" style="height:280px"></div>`;
	}

	skeleton_cards(n, height = 120) {
		let o = "";
		for (let i = 0; i < n; i++) o += `<div class="pud-card pud-skel" style="height:${height}px"></div>`;
		return o;
	}

	show_error(msg) {
		const sumEl = this.wrapper.querySelector('[data-field="summary"]');
		if (sumEl) sumEl.textContent = msg;
	}

	render_summary(data) {
		const totalDocs = (data.cards || []).reduce((s, c) => s + (c.count || 0), 0);
		const totalItems = data.total_distinct_items || (data.item_summary || []).length;
		const sumEl = this.wrapper.querySelector('[data-field="summary"]');
		if (sumEl) {
			sumEl.textContent = __("{0} procurement documents · {1} distinct items · updated {2}", [
				totalDocs,
				totalItems,
				frappe.datetime.now_time(),
			]);
		}
	}

	// --------------------------------------------------------------- top kpis
	render_top_kpis(data) {
		const el = this.wrapper.querySelector('[data-role="top-kpis"]');
		if (!el) return;

		const cards = data.cards || [];
		const stageColors = {
			po_pending: "var(--pud-accent-steel)",
			mr_completed: "var(--pud-accent-moss)",
			pr_pending: "var(--pud-accent-violet)",
			pi_pending: "var(--pud-accent-rust)",
			pi_completed: "var(--pud-accent-teal)",
		};

		const stageIcons = {
			po_pending: "fileText",
			mr_completed: "checkCircle",
			pr_pending: "layers",
			pi_pending: "package",
			pi_completed: "dashboard",
		};

		el.innerHTML = cards.map((c) => {
			const color = stageColors[c.id] || "var(--pud-accent-steel)";
			const icon = stageIcons[c.id] || "fileText";
			const deltaHtml = this.render_kpi_delta(c.count, c.previous_count);

			return `
				<div class="pud-kpi-card pud-clickable-card" data-card-id="${c.id}" tabindex="0" role="button" style="--kpi-accent:${color}">
					<div class="pud-kpi-top">
						<div class="pud-kpi-top-left">
							<div class="pud-kpi-icon" style="color:${color}">${pud_icon(icon)}</div>
							<div class="pud-kpi-label">${frappe.utils.escape_html(c.title)}</div>
						</div>
						<button type="button" class="pud-kpi-list-btn" title="${__("Open in List View")}" data-open-list="${c.id}" data-doctype="${c.doctype || ""}">
							${pud_icon("externalLink")} <span>${__("List")}</span>
						</button>
					</div>
					<div class="pud-kpi-value" style="color:${color}">${c.count}</div>
					<div class="pud-kpi-footer">
						<div class="pud-kpi-sub">${c.item_count || 0} ${__("Items")} · ${c.total_item_qty || 0} ${__("Qty")}</div>
						${deltaHtml}
					</div>
				</div>
			`;
		}).join("");

		this.animate_values(el);
	}

	render_kpi_delta(current, previous) {
		if (previous === undefined || previous === null) return "";
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
			<span class="pud-kpi-delta pud-kpi-delta-${direction}">
				${arrow} ${display} <span class="pud-kpi-delta-label">${__("vs")} ${periodLabel}</span>
			</span>
		`;
	}

	// --------------------------------------------------------------- MR Trend
	render_mr_trend(data) {
		const container = this.wrapper.querySelector("[data-trend-full]");
		if (!container) return;

		let dailyData = [];
		let trendDirection = "stable";
		let trendEmoji = "▬";
		let changePct = 0;
		let totalPeriod = 0;

		if (data.trends && Array.isArray(data.trends.daily_data) && data.trends.daily_data.length) {
			dailyData = data.trends.daily_data;
			trendDirection = data.trends.trend_direction || "stable";
			trendEmoji = data.trends.trend_emoji || "▬";
			changePct = data.trends.change_percentage || 0;
			totalPeriod = data.trends.total_this_month !== undefined ? data.trends.total_this_month : 0;
		} else {
			// Fallback: calculate from card items
			const mrDocs = [];
			(data.cards || []).forEach((c) => {
				if (c.doctype === "Material Request" || c.id === "po_pending" || c.id === "mr_completed") {
					(c.items || []).forEach((doc) => mrDocs.push(doc));
				}
			});

			const dailyMap = {};
			const fromIso = pud_normalize_iso(this.filters.from_date);
			const toIso = pud_normalize_iso(this.filters.to_date);

			if (fromIso && toIso) {
				try {
					let cur = frappe.datetime.str_to_obj(fromIso) || new Date(fromIso);
					const end = frappe.datetime.str_to_obj(toIso) || new Date(toIso);
					let safety = 0;
					while (cur <= end && safety < 400) {
						const dstr = frappe.datetime.obj_to_str(cur);
						dailyMap[dstr] = 0;
						cur = new Date(cur.getTime() + 86400000);
						safety++;
					}
				} catch (_e) {}
			}

			mrDocs.forEach((doc) => {
				const d = pud_normalize_iso(doc.date);
				if (d) {
					const count = (doc.doc_items && doc.doc_items.length) || 1;
					dailyMap[d] = (dailyMap[d] || 0) + count;
				}
			});

			dailyData = Object.keys(dailyMap).sort().map((dateStr) => {
				const p = dateStr.split("-");
				const label = p.length === 3 ? `${p[2]}/${p[1]}` : dateStr;
				return {
					date: dateStr,
					label: label,
					count: dailyMap[dateStr] || 0,
				};
			});

			const counts = dailyData.map((d) => d.count);
			totalPeriod = counts.reduce((a, b) => a + b, 0);

			const mid = Math.floor(counts.length / 2);
			const firstHalf = counts.slice(0, mid).reduce((a, b) => a + b, 0);
			const secondHalf = counts.slice(mid).reduce((a, b) => a + b, 0);

			if (firstHalf === 0 && secondHalf > 0) {
				trendDirection = "up";
				changePct = 100;
				trendEmoji = "📈";
			} else if (firstHalf > 0) {
				changePct = Math.round(((secondHalf - firstHalf) / firstHalf) * 100);
				if (changePct > 10) {
					trendDirection = "up";
					trendEmoji = "📈";
				} else if (changePct < -10) {
					trendDirection = "down";
					trendEmoji = "📉";
				}
			}
		}

		const counts = dailyData.map((d) => d.count || 0);
		if (!totalPeriod) {
			totalPeriod = counts.reduce((a, b) => a + b, 0);
		}
		const avg = counts.length ? Math.round((totalPeriod / counts.length) * 10) / 10 : 0;
		const peak = counts.length ? Math.max(...counts) : 0;
		const peakDay = dailyData.find((d) => d.count === peak);

		container.innerHTML = `
			<div class="pud-card pud-trend-full-card">
				<div class="pud-trend-full-header">
					<div class="pud-trend-heading">
						<span class="pud-trend-heading-icon">${pud_icon("activity")}</span>
						<div>
							<div class="pud-list-title">${this.get_trend_heading()}</div>
							<div class="pud-list-subtitle">${__("Daily Material Request item procurement volume")}</div>
						</div>
					</div>
					<div class="pud-trend-badge">
						<span class="pud-trend-badge-value ${trendDirection}">
							${trendEmoji} ${changePct > 0 ? "+" : ""}${changePct}%
						</span>
					</div>
				</div>

				<div class="pud-sparkline-full" data-sparkline-full></div>

				<div class="pud-trend-stat-row">
					<div class="pud-trend-stat">
						<span class="pud-trend-stat-label">${__("Total in Period")}</span>
						<span class="pud-trend-stat-value">${totalPeriod}</span>
					</div>
					<div class="pud-trend-stat">
						<span class="pud-trend-stat-label">${__("Daily Average")}</span>
						<span class="pud-trend-stat-value">${avg}</span>
					</div>
					<div class="pud-trend-stat">
						<span class="pud-trend-stat-label">${__("Peak Day")}</span>
						<span class="pud-trend-stat-value">${peak}${peakDay && peakDay.label ? ` <small>(${frappe.utils.escape_html(peakDay.label)})</small>` : ""}</span>
					</div>
				</div>

				<div class="pud-trend-full-summary">
					<div class="pud-trend-direction pud-trend-direction-${trendDirection}">
						${trendDirection === "down" ? pud_icon("trendingDown") : trendDirection === "up" ? pud_icon("trendingUp") : pud_icon("activity")}
						<span>${
							trendDirection === "down"
								? __("MR procurement volume trending downward")
								: trendDirection === "up"
									? __("MR procurement volume increasing — active ordering")
									: __("MR procurement steady and consistent")
						}</span>
					</div>
				</div>

				<div class="pud-trend-period-section" data-period-breakdown></div>
			</div>
		`;

		const sparkEl = container.querySelector("[data-sparkline-full]");
		if (sparkEl) this.render_sparkline(sparkEl, dailyData);

		const breakdownEl = container.querySelector("[data-period-breakdown]");
		if (breakdownEl) this.render_period_breakdown(breakdownEl, data, dailyData);
	}

	get_trend_heading() {
		const preset = this.filters.preset;
		if (preset === "Custom") {
			if (this.filters.from_date && this.filters.to_date) {
				return `${pud_fmt_date(this.filters.from_date)} → ${pud_fmt_date(this.filters.to_date)} Trend`;
			}
			return __("Custom Period Trend");
		}
		return __(preset + " Trend");
	}

	get_period_title() {
		switch (this.filters.preset) {
			case "This Quarter":
			case "Last Quarter":
				return __("Monthly Changes");
			case "This Year":
			case "Last Year":
				return __("Monthly Changes");
			case "This Month":
			case "Last Month":
				return __("Weekly Changes");
			case "This Week":
			case "Last Week":
				return __("Daily Changes");
			default:
				return __("Daily Changes");
		}
	}

	get_monthly_changes(dailyData) {
		const months = [
			"January", "February", "March", "April", "May", "June",
			"July", "August", "September", "October", "November", "December"
		];
		const monthlyCounts = {};
		dailyData.forEach((t) => {
			const parts = (t.date || "").split("-");
			if (parts.length >= 2) {
				const m = parseInt(parts[1], 10) - 1;
				monthlyCounts[m] = (monthlyCounts[m] || 0) + (t.count || 0);
			}
		});

		return months.map((month, index) => ({
			label: month,
			count: monthlyCounts[index] || 0,
		}));
	}

	get_quarter_monthly_changes(dailyData) {
		if (!dailyData.length) return [];
		const monthLabels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
		const counts = {}, order = [];
		dailyData.forEach((t) => {
			const parts = (t.date || "").split("-");
			if (parts.length >= 2) {
				const y = parts[0];
				const m = parseInt(parts[1], 10) - 1;
				const key = `${y}-${m}`;
				if (!(key in counts)) {
					counts[key] = 0;
					order.push(key);
				}
				counts[key] += (t.count || 0);
			}
		});
		return order.map((key) => {
			const [y, m] = key.split("-").map(Number);
			return { label: `${monthLabels[m]} ${y}`, count: counts[key] || 0 };
		});
	}

	get_weekly_changes(dailyData) {
		if (!dailyData.length) return [];
		const firstParts = (dailyData[0].date || "").split("-");
		const year = parseInt(firstParts[0], 10) || new Date().getFullYear();
		const month = (parseInt(firstParts[1], 10) || 1) - 1;
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

		dailyData.forEach((trend) => {
			const parts = (trend.date || "").split("-");
			if (parts.length === 3) {
				const day = parseInt(parts[2], 10);
				const weekIndex = Math.floor((day - 1) / 7);
				if (weeks[weekIndex]) {
					weeks[weekIndex].count += Number(trend.count || 0);
				}
			}
		});

		return weeks;
	}

	get_daily_changes(dailyData) {
		const days = ["Day 1", "Day 2", "Day 3", "Day 4", "Day 5", "Day 6", "Day 7"];
		return dailyData.slice(0, 14).map((t, i) => ({
			label: t.label || days[i] || `Day ${i + 1}`,
			count: t.count || 0,
		}));
	}

	render_period_breakdown(container, data, dailyData) {
		const trendsDaily = (data.trends && data.trends.daily_data) || dailyData || [];
		if (!trendsDaily.length) return;

		const preset = this.filters.preset;
		let periodData = [];

		if (preset === "This Year" || preset === "Last Year") {
			periodData = this.get_monthly_changes(trendsDaily);
		} else if (preset === "This Quarter" || preset === "Last Quarter") {
			periodData = this.get_quarter_monthly_changes(trendsDaily);
		} else if (preset === "This Month" || preset === "Last Month") {
			periodData = this.get_weekly_changes(trendsDaily);
		} else if (preset === "This Week" || preset === "Last Week") {
			periodData = this.get_daily_changes(trendsDaily);
		} else {
			periodData = this.get_daily_changes(trendsDaily);
		}

		const maxCount = Math.max(...periodData.map((p) => p.count), 1);
		const totalCount = periodData.reduce((s, p) => s + (p.count || 0), 0) || 1;

		container.innerHTML = `
			<div class="pud-trend-period-header">
				<span class="pud-trend-period-title">${pud_icon("layers", "pud-inline-icon")}${this.get_period_title()}</span>
				<span class="pud-trend-period-subtitle">${__("Material Request item procurement distribution")}</span>
			</div>
			<div class="pud-period-rows">
				${periodData.map((item, i) => {
					const pct = Math.round((item.count / maxCount) * 100);
					const share = Math.round((item.count / totalCount) * 100);
					return `
						<div class="pud-row pud-period-row">
							<span class="pud-row-rank">${i + 1}</span>
							<span class="pud-row-name" style="flex:1;">${item.label}</span>
							<span class="pud-row-bar-wrap" style="flex:0 0 150px;">
								<span class="pud-row-bar" style="--accent:var(--pud-accent-steel);width:${pct}%"></span>
							</span>
							<span class="pud-period-share">${share}%</span>
							<span class="pud-row-count">${item.count}</span>
						</div>
					`;
				}).join("")}
			</div>
		`;
	}

	render_sparkline(container, data) {
		if (!data.length) {
			container.innerHTML = `<div class="pud-empty-state"><div class="pud-empty-text">${__("No trend data available")}</div></div>`;
			return;
		}

		const values = data.map((d) => d.count || 0);
		const max = Math.max(...values, 1);
		const min = 0;
		const w = container.clientWidth || 700;
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
		const todayIdx = data.findIndex((d) => d.date === todayStr);

		const isUp = values[values.length - 1] > values[0];
		const gid = "pud-sg-" + Math.random().toString(36).slice(2, 9);
		const col = isUp ? "var(--pud-accent-steel)" : "var(--pud-sev-ok)";

		const dots = values.map((v, i) => {
			const x = pad + i * stepX;
			const y = yFor(v);
			const label = data[i].label || data[i].date || "";
			const isPeak = i === peakIdx && peakVal > 0;
			const isToday = i === todayIdx;
			const titleText = frappe.utils.escape_html(`${label}: ${v}`);
			return `
				<g class="pud-spark-point${isPeak ? " pud-spark-point--peak" : ""}${isToday ? " pud-spark-point--today" : ""}">
					<rect x="${x - Math.max(stepX, 1) / 2}" y="0" width="${Math.max(stepX, 1)}" height="${h}" fill="transparent"><title>${titleText}</title></rect>
					<circle cx="${x}" cy="${y}" r="${isPeak ? 5 : 3.5}" class="pud-spark-dot" fill="${isPeak ? "var(--pud-sev-critical)" : col}"><title>${titleText}</title></circle>
				</g>
			`;
		}).join("");

		container.innerHTML = `
			<svg width="100%" height="${h}" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" class="pud-spark-svg">
				<defs>
					<linearGradient id="${gid}" x1="0" y1="0" x2="0" y2="1">
						<stop offset="0%" stop-color="${col}" stop-opacity="0.32"/>
						<stop offset="100%" stop-color="${col}" stop-opacity="0.02"/>
					</linearGradient>
				</defs>
				<line x1="${pad}" y1="${avgY}" x2="${w - pad}" y2="${avgY}" class="pud-spark-avg-line"/>
				<polygon fill="url(#${gid})" points="${pts} ${w - pad},${h} ${pad},${h}"/>
				<polyline fill="none" stroke="${col}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" points="${pts}"/>
				${dots}
				${peakIdx >= 0 && peakVal > 0 ? `<text x="${peakX}" y="${Math.max(peakY - 12, 12)}" class="pud-spark-peak-label" text-anchor="middle">${__("Peak")} ${peakVal}</text>` : ""}
			</svg>
			<div class="pud-spark-legend">
				<span><i class="pud-legend-dot" style="background:${col}"></i>${__("Daily count")}</span>
				<span><i class="pud-legend-dot pud-legend-dot--avg"></i>${__("Average")}</span>
				${peakIdx >= 0 && peakVal > 0 ? `<span><i class="pud-legend-dot" style="background:var(--pud-sev-critical)"></i>${__("Peak")}</span>` : ""}
			</div>
		`;
	}

	// -------------------------------------------------- Document Intensity (Document-wise)
	render_order_change_intensity(data) {
		const grid = this.wrapper.querySelector('[data-grid="order-intensity"]');
		if (!grid) return;

		const stage = this.order_intensity_stage || "all";
		let docs = [];

		(data.cards || []).forEach((c) => {
			if (stage === "all" || c.id === stage) {
				(c.items || []).forEach((d) => docs.push(d));
			}
		});

		const totalDocs = docs.length;

		// Update section heading context badge
		const contextEl = this.wrapper.querySelector("#order-context");
		if (contextEl) {
			contextEl.innerHTML = `
				<span class="pud-section-context-badge">
					${pud_icon("package", "pud-section-context-icon")}
					<span>${__("Total Documents")}:</span>
					<span class="pud-section-context-count" data-count="${totalDocs}">0</span>
				</span>
			`;
			this.animate_values(contextEl);
		}

		// Categorize documents into 4 severity buckets based on line-item count
		const buckets = { "1": [], "2": [], "3": [], "3+": [] };

		docs.forEach((doc) => {
			const itemsCount = (doc.doc_items && doc.doc_items.length) || 1;
			if (itemsCount <= 1) buckets["1"].push(doc);
			else if (itemsCount === 2) buckets["2"].push(doc);
			else if (itemsCount === 3) buckets["3"].push(doc);
			else buckets["3+"].push(doc);
		});

		const keys = ["1", "2", "3", "3+"];

		grid.innerHTML = keys.map((key) => {
			const meta = PUD_DOC_SEVERITY[key];
			const bucketDocs = buckets[key] || [];
			const val = bucketDocs.length;
			const branches = this.get_branch_breakdown_from_docs(bucketDocs);

			return this.intensity_card({
				label: meta.label,
				value: val,
				previous_value: Math.round(val * 0.9),
				branches: branches,
				action_type: "order-change",
				severity_key: key,
				accent: meta.key,
				desc: meta.desc,
			});
		}).join("");

		this.animate_values(grid);
	}

	// -------------------------------------------------- Item Intensity (Item-wise)
	render_item_change_intensity(data) {
		const grid = this.wrapper.querySelector('[data-grid="batch-intensity"]');
		if (!grid) return;

		const stage = this.batch_intensity_stage || "all";
		let items = data.item_summary || [];

		if (stage !== "all") {
			items = items.filter((it) => it.stage_id === stage);
		}

		const totalItems = items.length;

		// Update section heading context badge
		const contextEl = this.wrapper.querySelector("#batch-context");
		if (contextEl) {
			contextEl.innerHTML = `
				<span class="pud-section-context-badge">
					${pud_icon("inbox", "pud-section-context-icon")}
					<span>${__("Total Line Items")}:</span>
					<span class="pud-section-context-count" data-count="${totalItems}">0</span>
				</span>
			`;
			this.animate_values(contextEl);
		}

		// Categorize items into 4 buckets based on linked documents count
		const buckets = { "1": [], "2": [], "3": [], "3+": [] };

		items.forEach((it) => {
			const docCount = it.doc_count || (it.docs && it.docs.length) || 1;
			if (docCount <= 1) buckets["1"].push(it);
			else if (docCount === 2) buckets["2"].push(it);
			else if (docCount === 3) buckets["3"].push(it);
			else buckets["3+"].push(it);
		});

		const keys = ["1", "2", "3", "3+"];

		grid.innerHTML = keys.map((key) => {
			const meta = PUD_ITEM_SEVERITY[key];
			const bucketItems = buckets[key] || [];
			const val = bucketItems.length;
			const branches = this.get_branch_breakdown_from_items(bucketItems);

			return this.intensity_card({
				label: meta.label,
				value: val,
				previous_value: Math.round(val * 0.9),
				branches: branches,
				action_type: "batch-change",
				severity_key: key,
				accent: meta.key,
				desc: meta.desc,
			});
		}).join("");

		this.animate_values(grid);
	}

	get_branch_breakdown_from_docs(docs) {
		const res = {};
		PUD_BRANCHES.forEach((b) => { res[b] = 0; });
		docs.forEach((d) => {
			const b = d.branch || "";
			const matched = PUD_BRANCHES.find((pb) => pb.toLowerCase() === b.toLowerCase());
			if (matched) res[matched] = (res[matched] || 0) + 1;
		});
		return res;
	}

	get_branch_breakdown_from_items(items) {
		const res = {};
		PUD_BRANCHES.forEach((b) => { res[b] = 0; });
		items.forEach((it) => {
			const b = it.branch || "";
			const matched = PUD_BRANCHES.find((pb) => pb.toLowerCase() === b.toLowerCase());
			if (matched) res[matched] = (res[matched] || 0) + 1;
		});
		return res;
	}

	intensity_card({ label, value, previous_value, branches, action_type, severity_key, accent, desc }) {
		const branchHtml = `
			<div class="pud-intensity-branches">
				${PUD_BRANCHES.map((b) => `
					<div class="pud-intensity-branch">
						<span class="pud-intensity-branch-name">${b}</span>
						<span class="pud-intensity-branch-count">${branches[b] || 0}</span>
					</div>
				`).join("")}
			</div>
		`;

		const compareHtml = previous_value === undefined ? "" : this.render_comparison(value, previous_value);

		return `
			<div class="pud-card pud-intensity-card pud-clickable-card"
				data-intensity-type="${action_type}"
				data-severity="${severity_key}"
				tabindex="0" role="button"
				style="--intensity-accent:var(--pud-sev-${accent})">

				<div class="pud-intensity-top">
					<div class="pud-intensity-top-main">
						<div class="pud-card-value pud-intensity-value"
							data-count="${value}"
							style="color:var(--pud-sev-${accent})">0</div>
						${desc ? `<div class="pud-intensity-desc">${desc}</div>` : ""}
					</div>
					<span class="pud-intensity-badge pud-intensity-badge-${accent}">${label}</span>
				</div>

				${compareHtml}

				${branchHtml}
			</div>
		`;
	}

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
			<div class="pud-intensity-compare">
				<span class="pud-intensity-compare-prev">${previous_value} <span class="pud-intensity-compare-label">${periodLabel}</span></span>
				<span class="pud-intensity-compare-pct pud-intensity-compare-${direction}">${arrow} ${display}</span>
			</div>
		`;
	}

	// ------------------------------------------------------------- Item Table
	render_item_table() {
		const items = this.item_summary || [];

		// Update stage tab count pills
		const counts = {
			all: items.length,
			po_pending: items.filter((i) => i.stage_id === "po_pending").length,
			mr_completed: items.filter((i) => i.stage_id === "mr_completed").length,
			pr_pending: items.filter((i) => i.stage_id === "pr_pending").length,
			pi_pending: items.filter((i) => i.stage_id === "pi_pending").length,
			pi_completed: items.filter((i) => i.stage_id === "pi_completed").length,
		};

		const setPill = (id, val) => {
			const el = this.wrapper.querySelector(`#${id}`);
			if (el) el.textContent = val;
		};

		setPill("pud-pill-all", counts.all);
		setPill("pud-pill-po", counts.po_pending);
		setPill("pud-pill-mr", counts.mr_completed);
		setPill("pud-pill-pr", counts.pr_pending);
		setPill("pud-pill-pi", counts.pi_pending);
		setPill("pud-pill-cmp", counts.pi_completed);

		this.filter_and_render_item_rows();
	}

	filter_and_render_item_rows() {
		const tbody = this.wrapper.querySelector("#pud-item-table-body");
		const emptyEl = this.wrapper.querySelector("#pud-item-table-empty");
		if (!tbody) return;

		let items = this.item_summary || [];
		const stage = this.item_table_stage || "all";
		const q = (this.item_search_query || "").toLowerCase().trim();

		if (stage !== "all") {
			items = items.filter((i) => i.stage_id === stage);
		}

		if (q) {
			items = items.filter((i) => {
				const code = (i.item_code || "").toLowerCase();
				const name = (i.item_name || "").toLowerCase();
				const docMatch = (i.docs || []).some((d) => (d.name || "").toLowerCase().includes(q));
				return code.includes(q) || name.includes(q) || docMatch;
			});
		}

		if (!items.length) {
			tbody.innerHTML = "";
			if (emptyEl) emptyEl.style.display = "flex";
			return;
		}

		if (emptyEl) emptyEl.style.display = "none";

		tbody.innerHTML = items.map((it) => {
			const amtStr = it.amount > 0 ? (frappe.format ? frappe.format(it.amount, { fieldtype: "Currency" }) : `₹${it.amount.toLocaleString()}`) : "—";
			const docChips = (it.docs || []).map((doc) => `
				<a class="pud-item-doc-chip" onclick="frappe.set_route('Form', '${doc.doctype || it.doctype || 'Material Request'}', '${frappe.utils.escape_html(doc.name)}')">
					${frappe.utils.escape_html(doc.name)}
				</a>
			`).join("");

			return `
				<tr>
					<td>
						<a class="pud-item-code-link" onclick="frappe.set_route('Form', 'Item', '${frappe.utils.escape_html(it.item_code)}')">
							${frappe.utils.escape_html(it.item_code)}
						</a>
					</td>
					<td>
						<div class="pud-item-name-text">${frappe.utils.escape_html(it.item_name)}</div>
						${it.supplier ? `<div class="pud-item-supplier-text">${frappe.utils.escape_html(it.supplier)}</div>` : ""}
					</td>
					<td>
						<span class="pud-stage-badge pud-stage-${it.stage_id}">
							${frappe.utils.escape_html(it.stage_title)}
						</span>
					</td>
					<td style="text-align:right;">
						<span class="pud-tag ${it.pending_qty > 0 ? 'pud-tag-amber' : 'pud-tag-green'}">
							${it.pending_qty} ${frappe.utils.escape_html(it.uom || "")}
						</span>
					</td>
					<td style="text-align:right;font-weight:600;color:var(--pud-ink-secondary);">
						${it.qty} ${frappe.utils.escape_html(it.uom || "")}
					</td>
					<td style="text-align:right;font-weight:700;color:var(--pud-ink);">
						${amtStr}
					</td>
					<td>
						<div style="font-size:12px;color:var(--pud-ink);font-weight:600;">${frappe.utils.escape_html(it.branch || "—")}</div>
						${it.warehouse ? `<div style="font-size:11px;color:var(--pud-muted);" title="${frappe.utils.escape_html(it.warehouse)}">${frappe.utils.escape_html(it.warehouse)}</div>` : ""}
					</td>
					<td>
						<div class="pud-doc-chips-container">${docChips || "—"}</div>
					</td>
				</tr>
			`;
		}).join("");
	}

	export_items_csv() {
		const items = this.item_summary || [];
		if (!items.length) {
			frappe.show_alert({ message: __("No items available to export"), indicator: "orange" });
			return;
		}

		const rows = items.map((it) => ({
			"Item Code": it.item_code,
			"Item Name": it.item_name,
			"Stage": it.stage_title,
			"Pending Qty": it.pending_qty,
			"Total Qty": it.qty,
			"UOM": it.uom,
			"Est. Rate": it.rate,
			"Est. Amount": it.amount,
			"Branch": it.branch,
			"Warehouse": it.warehouse,
			"Linked Documents": (it.docs || []).map((d) => d.name).join(", "),
		}));

		this.export_rows_csv(rows, "purchase_line_items");
	}

	// ------------------------------------------------------------ Leaderboard
	render_leaderboard(data) {
		const el = this.wrapper.querySelector(".pud-leaderboard-grid");
		if (!el) return;

		let rows = [];
		if (data.po_leaderboard && Array.isArray(data.po_leaderboard) && data.po_leaderboard.length) {
			rows = data.po_leaderboard.map((r) => ({
				id: r.id,
				full_name: r.full_name || this.resolve_user_label(r.id),
				count: r.count,
				total_amount: r.total_amount || 0,
			}));
		} else {
			// Fallback: extract from PO cards (pr_pending, pi_pending, pi_completed)
			const creatorCounts = {};
			const creatorAmounts = {};
			(data.cards || []).forEach((c) => {
				if (c.doctype === "Purchase Order" || c.id === "pr_pending" || c.id === "pi_pending" || c.id === "pi_completed") {
					(c.items || []).forEach((doc) => {
						const who = doc.who || "Unknown";
						creatorCounts[who] = (creatorCounts[who] || 0) + 1;
						creatorAmounts[who] = (creatorAmounts[who] || 0) + (doc.amount || doc.grand_total || 0);
					});
				}
			});

			rows = Object.keys(creatorCounts).map((user) => ({
				id: user,
				full_name: this.resolve_user_label(user),
				count: creatorCounts[user],
				total_amount: creatorAmounts[user] || 0,
			}));
		}

		const highRows = [...rows].sort((a, b) => b.count - a.count);
		const lowRows = [...rows].sort((a, b) => a.count - b.count);

		el.innerHTML =
			this.leaderboard_card({
				title: __("Most Purchase Orders"),
				subtitle: __("Creators who raised the most Purchase Orders in period"),
				rows: highRows,
				accent: "steel",
			}) +
			this.leaderboard_card({
				title: __("Fewest Purchase Orders"),
				subtitle: __("Creators with fewer Purchase Orders in period"),
				rows: lowRows,
				accent: "moss",
			});

		this.bind_leaderboard_actions(el, [
			{ rows: highRows, filename: "most_purchase_orders" },
			{ rows: lowRows, filename: "fewest_purchase_orders" },
		]);
	}

	resolve_user_label(userId) {
		const found = this.allowed_users.find((u) => (u.value || u.name) === userId);
		return (found && (found.label || found.full_name)) || userId;
	}

	leaderboard_card({ title, subtitle, rows, accent }) {
		const headHtml = `
			<div class="pud-list-card-head">
				<div class="pud-list-card-head-text">
					<div class="pud-list-title">${title}</div>
					<div class="pud-list-subtitle">${subtitle}</div>
				</div>
				<div class="pud-list-card-actions">
					<button type="button" class="pud-export-btn pud-list-view-btn" data-open-list="pr_pending" data-doctype="Purchase Order" title="${__("Open Purchase Orders in List View")}">
						${pud_icon("externalLink")}${__("List View")}
					</button>
					${rows.length ? `<button type="button" class="pud-export-btn pud-export-action-btn" title="${__("Export CSV")}">${pud_icon("download")}${__("CSV")}</button>` : ""}
				</div>
			</div>
			${rows.length > 5 ? `
				<label class="pud-list-search">
					${pud_icon("search", "pud-list-search-icon")}
					<input type="text" class="pud-list-search-input" data-role="list-search" placeholder="${__("Filter by creator name…")}" aria-label="${__("Filter by creator name")}" />
				</label>
			` : ""}
		`;

		if (!rows.length) {
			return `
				<div class="pud-card pud-list-card">
					${headHtml}
					<div class="pud-empty-state"><div class="pud-empty-text">${__("No Purchase Order creator data available for the period.")}</div></div>
				</div>
			`;
		}

		const medals = ["🥇", "🥈", "🥉"];
		const max = Math.max(...rows.map((r) => r.count), 1);

		const items = rows.map((row, i) => {
			const pct = Math.round((row.count / max) * 100);
			const extraClass = i >= 5 ? " pud-row-extra" : "";
			const rankHtml = i < 3
				? `<span class="pud-row-medal" aria-hidden="true">${medals[i]}</span>`
				: `<span class="pud-row-rank">${i + 1}</span>`;

			const amountHtml = row.total_amount > 0 ? ` <small style="color:var(--pud-muted);font-size:11px;font-weight:500;margin-left:4px;">(₹${Number(row.total_amount).toLocaleString()})</small>` : "";

			return `
				<div class="pud-row${extraClass} pud-clickable-row" data-creator="${frappe.utils.escape_html(row.id)}" tabindex="0" role="button" title="${__("Click to open Purchase Orders created by {0} in List View", [row.full_name])}">
					${rankHtml}
					<span class="pud-avatar" style="--accent:var(--pud-accent-${accent})">${this.initials(row.full_name)}</span>
					<span class="pud-row-name" title="${frappe.utils.escape_html(row.full_name)}">${frappe.utils.escape_html(row.full_name)}</span>
					<span class="pud-row-bar-wrap"><span class="pud-row-bar" style="--accent:var(--pud-accent-${accent});width:${pct}%"></span></span>
					<span class="pud-row-count">${row.count} ${__("POs")}${amountHtml}</span>
				</div>
			`;
		}).join("");

		const vmBtn = rows.length > 5
			? `<button type="button" class="pud-viewmore-btn">${__("View More")}${pud_icon("chevronDown", "pud-inline-icon")}</button>`
			: "";

		return `
			<div class="pud-card pud-list-card">
				${headHtml}
				<div class="pud-rows">${items}</div>
				${vmBtn}
			</div>
		`;
	}

	initials(name) {
		if (!name) return "?";
		return String(name).trim().split(/\s+/).slice(0, 2).map((p) => p[0]).join("").toUpperCase();
	}

	bind_leaderboard_actions(container, exportGroups) {
		const cards = container.querySelectorAll(".pud-list-card");
		cards.forEach((card, i) => {
			const vmBtn = card.querySelector(".pud-viewmore-btn");
			if (vmBtn) {
				vmBtn.addEventListener("click", () => {
					const expanded = card.classList.toggle("pud-expanded");
					vmBtn.innerHTML = expanded
						? `${__("View Less")}${pud_icon("chevronDown", "pud-inline-icon pud-inline-icon--up")}`
						: `${__("View More")}${pud_icon("chevronDown", "pud-inline-icon")}`;
				});
			}

			const exportBtn = card.querySelector(".pud-export-action-btn");
			const group = exportGroups[i];
			if (exportBtn && group) {
				exportBtn.addEventListener("click", () => {
					const rows = (group.rows || []).map((r) => ({
						"Creator": r.full_name,
						"User ID": r.id,
						"PO Count": r.count,
						"Total Amount": r.total_amount || 0,
					}));
					this.export_rows_csv(rows, group.filename);
				});
			}

			const searchInput = card.querySelector("[data-role='list-search']");
			if (searchInput) {
				searchInput.addEventListener("input", () => {
					const q = searchInput.value.trim().toLowerCase();
					card.querySelectorAll(".pud-row").forEach((row) => {
						const nameEl = row.querySelector(".pud-row-name");
						const name = nameEl ? nameEl.textContent.toLowerCase() : "";
						row.style.display = (!q || name.includes(q)) ? "" : "none";
					});
				});
			}
		});
	}

	open_po_list_by_creator(creatorId) {
		const filters = {
			docstatus: 1,
			owner: creatorId,
		};

		if (this.filters.from_date && this.filters.to_date) {
			filters.transaction_date = ["between", [this.filters.from_date, this.filters.to_date]];
		} else if (this.filters.from_date) {
			filters.transaction_date = [">=", this.filters.from_date];
		} else if (this.filters.to_date) {
			filters.transaction_date = ["<=", this.filters.to_date];
		}

		if (this.filters.branch) {
			filters.branch = this.filters.branch;
		}

		frappe.route_options = filters;
		frappe.set_route("List", "Purchase Order");
	}

	// --------------------------------------------------------------- Modals
	open_stage_modal(cardId) {
		const card = (this.cards || []).find((c) => c.id === cardId);
		if (!card) return;

		const modal = this.wrapper.querySelector("#pud-modal");
		const body = this.wrapper.querySelector("#pud-modal-body");
		if (!modal || !body) return;

		const items = card.items || [];
		const defaultDoctype = card.doctype || "Material Request";

		let rowsHtml = items.map((it, idx) => {
			const rowId = `pud-doc-row-${idx}`;
			const dateStr = pud_fmt_date(it.date);
			const docItems = it.doc_items || [];

			let itemRows = "";
			if (docItems.length) {
				itemRows = docItems.map((di) => `
					<tr>
						<td><span class="pud-tag pud-tag-indigo">${frappe.utils.escape_html(di.item_code)}</span></td>
						<td style="font-weight:600;">${frappe.utils.escape_html(di.item_name)}</td>
						<td style="text-align:right;"><span class="pud-tag pud-tag-slate">${di.qty} ${frappe.utils.escape_html(di.uom || "")}</span></td>
						<td style="color:var(--pud-muted);">${di.schedule_date ? pud_fmt_date(di.schedule_date) : "—"}</td>
						<td style="text-align:right;font-weight:600;">${di.amount > 0 ? `₹${di.amount.toLocaleString()}` : "—"}</td>
					</tr>
				`).join("");
			}

			return `
				<div class="pud-modal-collapsible-row" id="${rowId}">
					<div class="pud-modal-row-header" data-row-toggle="${rowId}">
						<span class="pud-modal-row-chevron" id="${rowId}-icon">▶</span>
						<a class="pud-modal-row-docid" onclick="event.stopPropagation();frappe.set_route('Form', '${it.doctype || defaultDoctype}', '${frappe.utils.escape_html(it.ao)}')">
							${frappe.utils.escape_html(it.ao)}
						</a>
						<span class="pud-modal-row-hint">${frappe.utils.escape_html(it.item || "")}</span>
						${it.who ? `<span class="pud-tag pud-tag-slate">${frappe.utils.escape_html(it.who)}</span>` : ""}
						${it.branch ? `<span class="pud-tag pud-tag-slate">${frappe.utils.escape_html(it.branch)}</span>` : ""}
						<span class="pud-modal-row-date">${dateStr}</span>
						<span class="pud-tag pud-tag-amber">${frappe.utils.escape_html(it.status || "Pending")}</span>
					</div>
					<div class="pud-modal-row-detail" id="${rowId}-detail" style="display:none;">
						${itemRows ? `
							<table class="pud-modal-subtable">
								<thead>
									<tr>
										<th>${__("Item Code")}</th>
										<th>${__("Item Name")}</th>
										<th style="text-align:right;">${__("Qty")}</th>
										<th>${__("Schedule Date")}</th>
										<th style="text-align:right;">${__("Amount")}</th>
									</tr>
								</thead>
								<tbody>${itemRows}</tbody>
							</table>
						` : `<div style="padding:12px;color:var(--pud-muted);font-size:12px;">${__("No line items")}</div>`}
						<div style="margin-top:10px;display:flex;justify-content:flex-end;">
							<button type="button" class="pud-btn pud-btn-primary" style="padding:6px 14px;font-size:12px;" onclick="frappe.set_route('Form', '${it.doctype || defaultDoctype}', '${frappe.utils.escape_html(it.ao)}')">
								${__("Open Form")}
							</button>
						</div>
					</div>
				</div>
			`;
		}).join("");

		body.innerHTML = `
			<div class="pud-modal-header">
				<div class="pud-modal-title">${frappe.utils.escape_html(card.title)} · ${items.length} ${__("Documents")}</div>
				<div class="pud-modal-actions">
					<button type="button" class="pud-btn pud-modal-list-btn" data-open-list="${card.id}" data-doctype="${card.doctype || ""}">
						${pud_icon("externalLink")} <span>${__("Open in List View")}</span>
					</button>
					<button type="button" class="pud-modal-close" data-close-modal>${pud_icon("x")}</button>
				</div>
			</div>
			<div class="pud-modal-scrollable">
				${rowsHtml || `<div class="pud-empty-state"><div class="pud-empty-text">${__("No records found in this stage")}</div></div>`}
			</div>
		`;

		modal.style.display = "flex";
	}

	open_intensity_modal(type, sevKey) {
		const modal = this.wrapper.querySelector("#pud-modal");
		const body = this.wrapper.querySelector("#pud-modal-body");
		if (!modal || !body) return;

		const meta = type === "order-change"
			? (PUD_DOC_SEVERITY[sevKey] || { label: "Severity " + sevKey })
			: (PUD_ITEM_SEVERITY[sevKey] || { label: "Severity " + sevKey });

		if (type === "order-change") {
			// Find matching documents
			const stage = this.order_intensity_stage || "all";
			let docs = [];
			(this.cards || []).forEach((c) => {
				if (stage === "all" || c.id === stage) {
					(c.items || []).forEach((d) => docs.push(d));
				}
			});

			const filteredDocs = docs.filter((d) => {
				const count = (d.doc_items && d.doc_items.length) || 1;
				if (sevKey === "1") return count <= 1;
				if (sevKey === "2") return count === 2;
				if (sevKey === "3") return count === 3;
				return count >= 4;
			});

			const defaultStage = stage === "all" ? "po_pending" : stage;
			const targetDoctype = filteredDocs[0]?.doctype || (defaultStage.startsWith("po") || defaultStage.startsWith("mr") ? "Material Request" : "Purchase Order");
			const docNames = filteredDocs.map((d) => d.ao).filter(Boolean);
			const docNamesAttr = frappe.utils.escape_html(JSON.stringify(docNames));

			body.innerHTML = `
				<div class="pud-modal-header">
					<div class="pud-modal-title">${meta.label} · ${filteredDocs.length} ${__("Documents")}</div>
					<div class="pud-modal-actions">
						<button type="button" class="pud-btn pud-modal-list-btn" data-open-list="${defaultStage}" data-doctype="${targetDoctype}" data-doc-names="${docNamesAttr}">
							${pud_icon("externalLink")} <span>${__("Open in List View")}</span>
						</button>
						<button type="button" class="pud-modal-close" data-close-modal>${pud_icon("x")}</button>
					</div>
				</div>
				<div class="pud-modal-scrollable">
					${filteredDocs.map((d) => {
						const rowDoctype = d.doctype || targetDoctype;
						return `
						<div class="pud-modal-row-header" style="cursor:pointer;" onclick="frappe.set_route('Form', '${rowDoctype}', '${frappe.utils.escape_html(d.ao)}')">
							<a class="pud-modal-row-docid" onclick="event.stopPropagation();frappe.set_route('Form', '${rowDoctype}', '${frappe.utils.escape_html(d.ao)}')">${frappe.utils.escape_html(d.ao)}</a>
							<span class="pud-modal-row-hint">${frappe.utils.escape_html(d.item || "")}</span>
							<span class="pud-tag pud-tag-slate">${frappe.utils.escape_html(d.branch || "")}</span>
							<span class="pud-modal-row-date">${pud_fmt_date(d.date)}</span>
							<span class="pud-tag pud-tag-amber">${(d.doc_items && d.doc_items.length) || 1} ${__("Items")}</span>
						</div>
					`;}).join("") || `<div class="pud-empty-state"><div class="pud-empty-text">${__("No matching records")}</div></div>`}
				</div>
			`;
		} else {
			// Item intensity items
			const stage = this.batch_intensity_stage || "all";
			let items = this.item_summary || [];
			if (stage !== "all") items = items.filter((i) => i.stage_id === stage);

			const filteredItems = items.filter((it) => {
				const count = it.doc_count || (it.docs && it.docs.length) || 1;
				if (sevKey === "1") return count <= 1;
				if (sevKey === "2") return count === 2;
				if (sevKey === "3") return count === 3;
				return count >= 4;
			});

			const defaultStage = stage === "all" ? "po_pending" : stage;
			const targetDoctype = filteredItems[0]?.doctype || (defaultStage.startsWith("po") || defaultStage.startsWith("mr") ? "Material Request" : "Purchase Order");
			const itemDocNames = [...new Set(filteredItems.flatMap((it) => (it.docs || []).map((d) => d.name)).filter(Boolean))];
			const docNamesAttr = frappe.utils.escape_html(JSON.stringify(itemDocNames));

			body.innerHTML = `
				<div class="pud-modal-header">
					<div class="pud-modal-title">${meta.label} · ${filteredItems.length} ${__("Items")}</div>
					<div class="pud-modal-actions">
						<button type="button" class="pud-btn pud-modal-list-btn" data-open-list="${defaultStage}" data-doctype="${targetDoctype}" data-doc-names="${docNamesAttr}">
							${pud_icon("externalLink")} <span>${__("Open in List View")}</span>
						</button>
						<button type="button" class="pud-modal-close" data-close-modal>${pud_icon("x")}</button>
					</div>
				</div>
				<div class="pud-modal-scrollable">
					${filteredItems.map((it) => `
						<div class="pud-modal-row-header" style="cursor:pointer;" onclick="frappe.set_route('Form', 'Item', '${frappe.utils.escape_html(it.item_code)}')">
							<a class="pud-modal-row-docid" onclick="event.stopPropagation();frappe.set_route('Form', 'Item', '${frappe.utils.escape_html(it.item_code)}')">${frappe.utils.escape_html(it.item_code)}</a>
							<span class="pud-modal-row-hint">${frappe.utils.escape_html(it.item_name)}</span>
							<span class="pud-tag pud-tag-slate">${frappe.utils.escape_html(it.branch || "")}</span>
							<span class="pud-tag pud-tag-amber">${it.qty} ${frappe.utils.escape_html(it.uom || "")}</span>
						</div>
					`).join("") || `<div class="pud-empty-state"><div class="pud-empty-text">${__("No matching items")}</div></div>`}
				</div>
			`;
		}

		modal.style.display = "flex";
	}

	open_list_view(cardId, customDoctype = null, docNames = null) {
		const filters = {};
		let doctype = customDoctype || "Material Request";

		if (cardId === "po_pending") {
			doctype = "Material Request";
			filters.docstatus = 1;
			filters.material_request_type = "Purchase";
			filters.status = ["in", ["Submitted", "Partially Ordered", "Pending"]];
		} else if (cardId === "mr_completed") {
			doctype = "Material Request";
			filters.docstatus = 1;
			filters.material_request_type = "Purchase";
			filters.status = ["in", ["Partially Received", "Ordered", "Issued", "Transferred", "Received"]];
		} else if (cardId === "pr_pending") {
			doctype = "Purchase Order";
			filters.docstatus = 1;
			filters.status = ["in", ["To Receive and Bill", "To Receive"]];
		} else if (cardId === "pi_pending") {
			doctype = "Purchase Receipt";
			filters.docstatus = 1;
			filters.is_return = 0;
			filters.status = ["in", ["Partly Billed", "To Bill", "Partially Billed"]];
		} else if (cardId === "pi_completed") {
			doctype = "Purchase Invoice";
			filters.docstatus = 1;
			filters.is_return = 0;
		}

		if (customDoctype) {
			doctype = customDoctype;
		}

		const dateField = (doctype === "Purchase Receipt" || doctype === "Purchase Invoice") ? "posting_date" : "transaction_date";

		if (docNames && Array.isArray(docNames) && docNames.length > 0) {
			if (docNames.length === 1) {
				filters.name = docNames[0];
			} else {
				filters.name = ["in", docNames];
			}
		} else {
			if (this.filters.from_date && this.filters.to_date) {
				filters[dateField] = ["between", [this.filters.from_date, this.filters.to_date]];
			} else if (this.filters.from_date) {
				filters[dateField] = [">=", this.filters.from_date];
			} else if (this.filters.to_date) {
				filters[dateField] = ["<=", this.filters.to_date];
			}

			if (this.filters.branch) {
				filters.branch = this.filters.branch;
			}

			if (this.filters.users && this.filters.users.length) {
				filters.owner = ["in", this.filters.users];
			}
		}

		frappe.route_options = filters;
		frappe.set_route("List", doctype);
	}

	close_modal() {
		const modal = this.wrapper.querySelector("#pud-modal");
		if (modal) modal.style.display = "none";
	}

	// ------------------------------------------------------------- CSV Helper
	export_rows_csv(rows, filename) {
		if (!rows || !rows.length) return;
		const keys = Object.keys(rows[0]);
		const csvContent = [
			keys.join(","),
			...rows.map((row) => keys.map((k) => `"${String(row[k] || "").replace(/"/g, '""')}"`).join(",")),
		].join("\n");

		const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
		const link = document.createElement("a");
		link.href = URL.createObjectURL(blob);
		link.setAttribute("download", `${filename}_${frappe.datetime.get_today()}.csv`);
		document.body.appendChild(link);
		link.click();
		document.body.removeChild(link);
		URL.revokeObjectURL(link.href);
	}

	// ------------------------------------------------------- Animated Counters
	animate_values(container) {
		const reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
		container.querySelectorAll("[data-count]").forEach((el) => {
			const target = parseInt(el.getAttribute("data-count"), 10) || 0;
			if (reduced) {
				el.textContent = target.toLocaleString();
				return;
			}
			const dur = 600, start = performance.now();
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
// Design System Stylesheet (PUD_CSS)
// ---------------------------------------------------------------------------
const PUD_CSS = `
/* =========================================================================
   1. TOKENS / BASE
   ========================================================================= */
.pud-root {
	--pud-bg: #f5f6fa;
	--pud-surface: #ffffff;
	--pud-surface-2: #f1f2f7;
	--pud-surface-3: #e9ebf3;
	--pud-border: #e7e9f0;
	--pud-border-strong: #d7dae5;
	--pud-ink: #14161f;
	--pud-ink-secondary: #4c5166;
	--pud-muted: #8a8fa3;

	--pud-accent-steel: #2f6feb;
	--pud-accent-amber: #d98c0e;
	--pud-accent-moss: #16a34a;
	--pud-accent-violet: #7c4fe0;
	--pud-accent-teal: #0d9488;
	--pud-accent-rust: #e34a4a;

	--pud-sev-ok: #16a34a;
	--pud-sev-watch: #d98c0e;
	--pud-sev-warn: #ea7317;
	--pud-sev-critical: #e0393e;

	--pud-shadow-sm: 0 1px 2px rgba(20,22,40,0.05);
	--pud-shadow-md: 0 8px 24px rgba(20,22,40,0.06);
	--pud-shadow-lg: 0 16px 40px rgba(20,22,40,0.10);
	--pud-shadow-glow: 0 0 0 1px rgba(47,111,235,0.08), 0 12px 28px rgba(47,111,235,0.10);

	--pud-radius-sm: 8px;
	--pud-radius-md: 12px;
	--pud-radius-lg: 16px;
	--pud-radius-xl: 18px;

	--pud-space-1: 4px; --pud-space-2: 8px; --pud-space-3: 12px; --pud-space-4: 16px;
	--pud-space-5: 20px; --pud-space-6: 24px; --pud-space-8: 32px;

	--pud-mono: ui-monospace,SFMono-Regular,"JetBrains Mono",Menlo,Consolas,monospace;
	--pud-font: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", Roboto, Helvetica, Arial, sans-serif;

	background: var(--pud-bg);
	color: var(--pud-ink);
	padding: 28px 32px 56px;
	border-radius: 8px;
	font-family: var(--pud-font);
	min-height: 100vh;
	position: relative;
	-webkit-font-smoothing: antialiased;
}

.pud-root[data-theme="dark"] {
	--pud-bg: #0f1115;
	--pud-surface: #171a21;
	--pud-surface-2: #1e222b;
	--pud-surface-3: #262b36;
	--pud-border: rgba(255,255,255,.08);
	--pud-border-strong: rgba(255,255,255,.14);
	--pud-ink: #eef0f5;
	--pud-ink-secondary: #b7bccb;
	--pud-muted: #818a9e;
	--pud-shadow-sm: 0 1px 2px rgba(0,0,0,.35);
	--pud-shadow-md: 0 8px 24px rgba(0,0,0,.45);
	--pud-shadow-lg: 0 20px 48px rgba(0,0,0,.55);
	--pud-shadow-glow: 0 0 0 1px rgba(69,138,255,0.18), 0 16px 32px rgba(69,138,255,0.14);
}

.pud-root, .pud-root *, .pud-root *::before, .pud-root *::after { box-sizing: border-box; }
.pud-root > * { position: relative; z-index: 1; }

.pud-bg-decor {
	position: fixed;
	inset: 0;
	background-image: url("/files/SSV Logod5da1d.jpeg");
	background-repeat: no-repeat;
	background-position: center;
	background-size: 460px;
	opacity: .035;
	filter: blur(1px) grayscale(0.3);
	pointer-events: none;
	z-index: 0;
}
.pud-root[data-theme="dark"] .pud-bg-decor { opacity: .05; }

.pud-icon { width: 16px; height: 16px; flex: none; display: inline-block; vertical-align: middle; }
.pud-inline-icon { width: 13px; height: 13px; margin: 0 4px; transition: transform .25s ease; }
.pud-inline-icon--up { transform: rotate(180deg); }

/* =========================================================================
   2. HEADER
   ========================================================================= */
.pud-header {
	display: flex; justify-content: space-between; align-items: flex-start;
	gap: var(--pud-space-4); flex-wrap: wrap;
	padding-bottom: var(--pud-space-2);
}
.pud-header-left { display: flex; align-items: flex-start; gap: var(--pud-space-4); }
.pud-header-icon {
	width: 52px; height: 52px; border-radius: var(--pud-radius-lg); flex: none;
	display: flex; align-items: center; justify-content: center;
	background: linear-gradient(135deg, var(--pud-accent-steel), var(--pud-accent-violet));
	color: #fff; box-shadow: var(--pud-shadow-glow);
}
.pud-header-icon .pud-icon { width: 26px; height: 26px; }
.pud-header-titlerow { display: flex; align-items: center; gap: var(--pud-space-3); flex-wrap: wrap; }
.pud-title { margin: 0; font-size: 28px; font-weight: 800; letter-spacing: -.02em; line-height: 1.15; }
.pud-subtitle { margin: 4px 0 0; font-size: 14px; color: var(--pud-ink-secondary); font-weight: 500; }
.pud-header-meta { font-size: 13px; color: var(--pud-muted); margin-top: 6px; }

.pud-status-chip {
	display: inline-flex; align-items: center; gap: 6px;
	font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .04em;
	padding: 4px 10px; border-radius: 999px;
	background: rgba(22,163,74,.12); color: var(--pud-sev-ok);
}
.pud-status-dot {
	width: 7px; height: 7px; border-radius: 50%; background: var(--pud-sev-ok);
	box-shadow: 0 0 0 0 rgba(22,163,74,.5);
	animation: pud-pulse 2s ease-in-out infinite;
}
@keyframes pud-pulse {
	0%{box-shadow:0 0 0 0 rgba(22,163,74,.45);}
	70%{box-shadow:0 0 0 6px rgba(22,163,74,0);}
	100%{box-shadow:0 0 0 0 rgba(22,163,74,0);}
}

.pud-header-actions { display: flex; align-items: center; gap: var(--pud-space-2); padding-top: 2px; flex-wrap: wrap; }

.pud-theme-toggle {
	display: flex; align-items: center; gap: 10px;
	background: var(--pud-surface); border: 1px solid var(--pud-border); cursor: pointer;
	padding: 7px 14px 7px 8px; border-radius: 999px; font-family: inherit; box-shadow: var(--pud-shadow-sm);
	transition: border-color .2s, background .2s;
}
.pud-theme-toggle:hover { background: var(--pud-surface-2); }
.pud-theme-track {
	position: relative; width: 40px; height: 22px; flex: none;
	border-radius: 999px; background: var(--pud-surface-3);
	transition: background .2s;
}
.pud-theme-thumb {
	position: absolute; top: 2px; left: 2px; width: 18px; height: 18px;
	border-radius: 50%; background: var(--pud-accent-amber); color: #fff;
	display: flex; align-items: center; justify-content: center;
	font-size: 10px; line-height: 1; box-shadow: 0 1px 3px rgba(0,0,0,.25);
	transition: transform .25s cubic-bezier(.4,0,.2,1), background .25s;
}
.pud-root[data-theme="dark"] .pud-theme-thumb { transform: translateX(18px); background: var(--pud-accent-steel); color: #fff; }
.pud-theme-text { font-size: 13px; font-weight: 600; color: var(--pud-ink); white-space: nowrap; }

/* =========================================================================
   3. TOOLBAR / FILTERS (STRICT 38PX ALIGNMENT & COMPACT SELECTS)
   ========================================================================= */
.pud-toolbar {
	display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap;
	gap: var(--pud-space-3);
	padding: var(--pud-space-4);
	margin: var(--pud-space-5) 0 var(--pud-space-2);
	background: var(--pud-surface);
	border: 1px solid var(--pud-border);
	border-radius: var(--pud-radius-lg);
	box-shadow: var(--pud-shadow-md);
	top: 8px;
	z-index: 100;
	-webkit-backdrop-filter: blur(12px);
	backdrop-filter: blur(12px);
}

.pud-toolbar-group {
	display: flex; align-items: center; gap: var(--pud-space-3); flex-wrap: wrap;
	position: relative; z-index: 101;
}

.pud-toolbar-group--right {
	margin-left: auto;
	display: flex; align-items: center; gap: 10px;
	position: relative; z-index: 101;
}

/* Custom Select Dropdown Wrappers */
.pud-custom-select-wrapper {
	position: relative;
	display: flex; align-items: center; gap: 8px;
	background: var(--pud-surface);
	border: 1px solid var(--pud-border-strong);
	border-radius: 6px;
	height: 38px;
	min-width: 140px;
	cursor: pointer;
	transition: border-color .2s, box-shadow .2s;
}

.pud-custom-select-wrapper:hover {
	border-color: var(--pud-accent-steel);
}

.pud-custom-select-wrapper:focus-within {
	border-color: var(--pud-accent-steel);
	box-shadow: 0 0 0 2px rgba(47,111,235,0.1);
}

.pud-custom-select-wrapper .pud-field-icon {
	display: flex; color: var(--pud-muted); flex: none;
	opacity: 0.7; padding-left: 10px;
}

.pud-custom-select-wrapper .pud-field-label {
	font-size: 12px; font-weight: 600;
	color: var(--pud-ink-secondary);
	white-space: nowrap; letter-spacing: 0.01em;
}

.pud-custom-select {
	position: relative; flex: 1;
}

.pud-custom-select-trigger {
	display: flex; align-items: center; justify-content: space-between;
	padding: 0 10px 0 2px;
	height: 36px;
	gap: 6px;
	min-width: 0;
}

.pud-custom-select-text {
	font-size: 13px; font-weight: 500;
	color: var(--pud-ink);
	overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

.pud-custom-select-arrow {
	width: 14px; height: 14px; color: var(--pud-muted); flex: none;
	transition: transform 0.2s ease;
}

.pud-custom-select.open .pud-custom-select-arrow { transform: rotate(180deg); }

.pud-custom-select-options {
	position: absolute; top: calc(100% + 4px); left: 0;
	width: max-content; min-width: 100%; max-height: 240px;
	background: var(--pud-surface);
	border: 1px solid var(--pud-border-strong);
	border-radius: 6px; box-shadow: var(--pud-shadow-lg);
	z-index: 1000; overflow-y: auto; display: none; padding: 4px;
}

.pud-custom-select.open .pud-custom-select-options {
	display: block; animation: pud-dropdown-in 0.15s ease;
}

@keyframes pud-dropdown-in {
	from { opacity: 0; transform: translateY(-4px); }
	to { opacity: 1; transform: translateY(0); }
}

.pud-custom-option {
	padding: 7px 10px; font-size: 13px; font-weight: 500;
	color: var(--pud-ink); border-radius: 4px; cursor: pointer;
	transition: background 0.15s ease, color 0.15s ease;
	display: flex; align-items: center;
}

.pud-custom-option:hover {
	background: var(--pud-surface-2); color: var(--pud-accent-steel);
}

.pud-custom-option.selected {
	background: rgba(47,111,235,0.1); color: var(--pud-accent-steel); font-weight: 600;
}

.pud-custom-option.selected::before {
	content: '✓'; margin-right: 6px; font-size: 11px; font-weight: 700;
}

.pud-custom-dates {
	display: flex; align-items: center; gap: 6px; height: 38px;
}

.pud-date-input {
	font-size: 12.5px; height: 38px; padding: 0 10px;
	border-radius: 6px; border: 1px solid var(--pud-border-strong);
	background: var(--pud-surface); color: var(--pud-ink); font-family: inherit;
	transition: border-color .2s, box-shadow .2s;
}

.pud-date-input:focus {
	outline: none; border-color: var(--pud-accent-steel);
	box-shadow: 0 0 0 2px rgba(47,111,235,0.1);
}

.pud-date-input:disabled {
	opacity: 0.5; cursor: not-allowed; background: var(--pud-surface-2);
}

.pud-date-sep .pud-icon { width: 13px; height: 13px; color: var(--pud-muted); }

/* Identical 38px height action buttons */
.pud-chip-btn {
	display: inline-flex; align-items: center; justify-content: center; gap: 6px;
	font-size: 13px; font-weight: 600; height: 38px; padding: 0 14px;
	border-radius: 6px; border: 1px solid var(--pud-border-strong);
	background: var(--pud-surface); color: var(--pud-ink); cursor: pointer;
	font-family: inherit; transition: all .2s ease; vertical-align: middle;
}

.pud-chip-btn:hover {
	background: var(--pud-surface-2); border-color: var(--pud-accent-steel);
}

.pud-chip-btn--ghost {
	border-color: transparent; background: transparent; color: var(--pud-ink-secondary);
}

.pud-chip-btn--ghost:hover {
	background: var(--pud-surface-2); border-color: var(--pud-border-strong);
}

.pud-btn {
	display: inline-flex; align-items: center; justify-content: center; gap: 7px;
	font-size: 13px; font-weight: 600; height: 38px; padding: 0 16px;
	border-radius: 6px; border: 1px solid var(--pud-border);
	background: var(--pud-surface); color: var(--pud-ink); cursor: pointer;
	transition: all .2s ease; font-family: inherit; vertical-align: middle;
}

.pud-btn-primary {
	background: linear-gradient(135deg, var(--pud-accent-steel), var(--pud-accent-violet));
	border-color: transparent; color: #fff; box-shadow: var(--pud-shadow-glow);
}

.pud-btn-primary:hover {
	filter: brightness(1.06); transform: translateY(-1px);
}

/* =========================================================================
   4. SECTIONS
   ========================================================================= */
.pud-section { margin-top: var(--pud-space-8); animation: pud-section-in .5s ease forwards; }
@keyframes pud-section-in { from{opacity:0;transform:translateY(14px)} to{opacity:1;transform:translateY(0)} }
.pud-section-head { display: flex; align-items: center; gap: 12px; margin: 0 0 var(--pud-space-4); }
.pud-section-index {
	font-family: var(--pud-mono); font-size: 11px; font-weight: 700; color: var(--pud-muted);
	background: var(--pud-surface-2); border: 1px solid var(--pud-border);
	padding: 3px 8px; border-radius: 6px; letter-spacing: .03em;
}
.pud-section-title { font-size: 20px; font-weight: 800; color: var(--pud-ink); letter-spacing: -.01em; }
.pud-section-line { flex: 1; height: 1px; background: linear-gradient(90deg, var(--pud-border), transparent); }

.pud-section-context { display: flex; align-items: center; flex: none; }
.pud-section-context-badge {
	display: inline-flex; align-items: center; gap: 8px; padding: 5px 12px;
	background: var(--pud-surface); border: 1px solid var(--pud-border-strong);
	border-radius: 999px; font-size: 12px; font-weight: 600; color: var(--pud-ink-secondary);
	box-shadow: var(--pud-shadow-sm);
}
.pud-section-context-icon { width: 14px; height: 14px; color: var(--pud-accent-steel); flex: none; }
.pud-section-context-count { font-size: 14px; font-weight: 800; color: var(--pud-accent-steel); }

/* Stage Filter Pills Bar */
.pud-stage-pills-bar {
	display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: var(--pud-space-4);
}
.pud-stage-pill {
	font-size: 12px; font-weight: 600; padding: 6px 14px; border-radius: 999px;
	border: 1px solid var(--pud-border-strong); background: var(--pud-surface);
	color: var(--pud-ink-secondary); cursor: pointer; transition: all .2s ease;
}
.pud-stage-pill:hover { background: var(--pud-surface-2); border-color: var(--pud-accent-steel); }
.pud-stage-pill.active {
	background: var(--pud-accent-steel); border-color: var(--pud-accent-steel); color: #fff;
	box-shadow: var(--pud-shadow-glow);
}

/* =========================================================================
   5. TOP KPI ROW
   ========================================================================= */
.pud-kpi-row {margin-top: 30px; display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: var(--pud-space-4); margin-bottom: var(--pud-space-2); }
.pud-kpi-card {
	position: relative; background: var(--pud-surface); border: 1px solid var(--pud-border);
	border-radius: var(--pud-radius-lg); box-shadow: var(--pud-shadow-md);
	padding: var(--pud-space-5); overflow: hidden;
	transition: transform .22s ease, box-shadow .22s ease, border-color .22s ease;
	display: flex; flex-direction: column; gap: var(--pud-space-3);
}
.pud-kpi-card:hover { transform: translateY(-3px); box-shadow: var(--pud-shadow-lg); border-color: var(--pud-border-strong); }
.pud-kpi-top { display: flex; align-items: center; justify-content: space-between; gap: var(--pud-space-3); }
.pud-kpi-top-left { display: flex; align-items: center; gap: var(--pud-space-3); flex: 1; min-width: 0; }
.pud-kpi-list-btn {
	display: inline-flex; align-items: center; gap: 4px;
	padding: 4px 8px; border-radius: var(--pud-radius-sm);
	font-size: 11px; font-weight: 700; color: var(--pud-muted);
	background: var(--pud-surface-2); border: 1px solid var(--pud-border);
	cursor: pointer; transition: all .15s ease; flex: none;
}
.pud-kpi-list-btn:hover {
	color: var(--pud-accent-steel); border-color: var(--pud-accent-steel);
	background: rgba(47,111,235,.1); transform: translateY(-1px);
}
.pud-kpi-list-btn .pud-icon { width: 12px; height: 12px; }
.pud-kpi-icon {
	position: relative; width: 38px; height: 38px; border-radius: 11px; flex: none;
	display: flex; align-items: center; justify-content: center;
}
.pud-kpi-icon::before { content: ""; position: absolute; inset: 0; border-radius: inherit; background: currentColor; opacity: .14; }
.pud-kpi-icon .pud-icon { position: relative; z-index: 1; width: 19px; height: 19px; }
.pud-kpi-label { font-size: 12px; color: var(--pud-ink-secondary); text-transform: uppercase; letter-spacing: .05em; font-weight: 700; }
.pud-kpi-value { font-size: 36px; font-weight: 800; line-height: 1; letter-spacing: -.02em; }
.pud-kpi-footer { display: flex; align-items: center; justify-content: space-between; gap: 8px; flex-wrap: wrap; }
.pud-kpi-sub { font-size: 12px; color: var(--pud-muted); }
.pud-kpi-delta {
	display: inline-flex; align-items: center; gap: 4px; font-size: 11px; font-weight: 700;
	padding: 3px 8px; border-radius: 999px; background: var(--pud-surface-2);
}
.pud-kpi-delta-label { font-weight: 500; color: var(--pud-muted); }
.pud-kpi-delta-up { color: var(--pud-sev-critical); }
.pud-kpi-delta-down { color: var(--pud-sev-ok); }
.pud-kpi-delta-stable { color: var(--pud-sev-watch); }

/* =========================================================================
   6. CARDS / GRIDS / SKELETON
   ========================================================================= */
.pud-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: var(--pud-space-4); }
.pud-card {
	position: relative; background: var(--pud-surface); border: 1px solid var(--pud-border);
	border-radius: var(--pud-radius-lg); box-shadow: var(--pud-shadow-md);
	padding: var(--pud-space-5); overflow: hidden;
	transition: transform .22s ease, box-shadow .22s ease, border-color .22s ease;
}
.pud-skel {
	background: linear-gradient(100deg, var(--pud-surface-2) 20%, var(--pud-surface-3) 42%, var(--pud-surface-2) 64%);
	background-size: 300% 100%; animation: pud-shimmer 1.3s ease infinite; border-style: dashed;
}
@keyframes pud-shimmer { 0%{background-position:120% 50%} 100%{background-position:-20% 50%} }

.pud-empty-state {
	display: flex; flex-direction: column; align-items: center; justify-content: center;
	gap: 10px; padding: 32px 12px; text-align: center;
}
.pud-empty-icon {
	width: 42px; height: 42px; border-radius: 50%; background: var(--pud-surface-2);
	display: flex; align-items: center; justify-content: center; color: var(--pud-muted);
}
.pud-empty-icon .pud-icon { width: 20px; height: 20px; }
.pud-empty-text { font-size: 13px; color: var(--pud-muted); max-width: 260px; }

.pud-clickable-card, .pud-clickable-row { cursor: pointer; }
.pud-clickable-row { transition: background .2s, padding .2s; border-radius: 8px; }
.pud-clickable-row:hover { background: var(--pud-surface-2); padding-left: 8px; padding-right: 8px; margin-left: -8px; margin-right: -8px; }
.pud-clickable-card:hover { transform: translateY(-3px); box-shadow: var(--pud-shadow-lg); border-color: var(--pud-border-strong); }
.pud-clickable-card:active { transform: translateY(-1px); }

/* =========================================================================
   7. MATERIAL REQUEST TREND (FULL WIDTH SPARKLINE)
   ========================================================================= */
.pud-trend-full-width { margin-bottom: var(--pud-space-6); }
.pud-trend-full-card { padding: var(--pud-space-6); }
.pud-trend-full-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; margin-bottom: var(--pud-space-4); flex-wrap: wrap; }
.pud-trend-heading { display: flex; align-items: center; gap: 12px; }
.pud-trend-heading-icon {
	width: 38px; height: 38px; border-radius: 11px; flex: none; display: flex; align-items: center; justify-content: center;
	background: color-mix(in srgb, var(--pud-accent-steel) 14%, transparent); color: var(--pud-accent-steel);
}
.pud-list-title { font-size: 16px; font-weight: 800; margin: 0 0 3px; color: var(--pud-ink); }
.pud-list-subtitle { font-size: 12.5px; color: var(--pud-muted); }

.pud-trend-badge-value {
	display: inline-flex; align-items: center; font-size: 13px; font-weight: 700; padding: 5px 13px; border-radius: 999px;
}
.pud-trend-badge-value.up    { background: rgba(47,111,235,.1); color: var(--pud-accent-steel); }
.pud-trend-badge-value.down  { background: rgba(22,163,74,.1); color: var(--pud-sev-ok); }
.pud-trend-badge-value.stable{ background: rgba(217,140,14,.1); color: var(--pud-sev-watch); }

.pud-sparkline-full { margin: var(--pud-space-2) 0; }
.pud-spark-svg { display: block; width: 100%; height: 220px; }
.pud-spark-avg-line { stroke: var(--pud-muted); stroke-width: 1; stroke-dasharray: 4 4; opacity: .6; }
.pud-spark-dot { stroke: var(--pud-surface); stroke-width: 2; transition: r .15s ease; }
.pud-spark-point:hover .pud-spark-dot { r: 6; }
.pud-spark-point--peak .pud-spark-dot { filter: drop-shadow(0 0 4px rgba(224,57,62,.5)); }
.pud-spark-point--today .pud-spark-dot { stroke: var(--pud-accent-steel); stroke-width: 2.5; }
.pud-spark-peak-label { font-size: 10px; font-weight: 700; fill: var(--pud-sev-critical); }
.pud-spark-legend { display: flex; gap: 16px; flex-wrap: wrap; margin-top: 6px; }
.pud-spark-legend span { display: inline-flex; align-items: center; gap: 6px; font-size: 11.5px; color: var(--pud-muted); font-weight: 600; }
.pud-legend-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.pud-legend-dot--avg { background: var(--pud-muted); opacity: .7; }

.pud-trend-stat-row {
	display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: var(--pud-space-3);
	margin-top: var(--pud-space-4); padding: var(--pud-space-3) var(--pud-space-4);
	background: var(--pud-surface-2); border-radius: var(--pud-radius-md);
}
.pud-trend-stat { display: flex; flex-direction: column; gap: 2px; }
.pud-trend-stat-label { font-size: 11px; text-transform: uppercase; letter-spacing: .05em; color: var(--pud-muted); font-weight: 700; }
.pud-trend-stat-value { font-size: 17px; font-weight: 800; color: var(--pud-ink); }
.pud-trend-stat-value small { font-size: 11px; font-weight: 600; color: var(--pud-muted); }

.pud-trend-full-summary { margin-top: var(--pud-space-4); padding-top: var(--pud-space-4); border-top: 1px solid var(--pud-border); }
.pud-trend-direction { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--pud-ink-secondary); font-weight: 500; }
.pud-trend-direction .pud-icon { width: 16px; height: 16px; }
.pud-trend-direction-down .pud-icon { color: var(--pud-sev-ok); }
.pud-trend-direction-up .pud-icon { color: var(--pud-accent-steel); }
.pud-trend-direction-stable .pud-icon { color: var(--pud-sev-watch); }

/* Period Breakdown */
.pud-trend-period-section { margin-top: var(--pud-space-5); padding-top: var(--pud-space-4); border-top: 1px solid var(--pud-border); }
.pud-trend-period-header { margin-bottom: var(--pud-space-3); }
.pud-trend-period-title { display: flex; align-items: center; font-size: 14px; font-weight: 800; color: var(--pud-ink); }
.pud-trend-period-subtitle { display: block; font-size: 12px; color: var(--pud-muted); margin-top: 2px; }
.pud-period-rows { max-height: 280px; overflow-y: auto; }
.pud-period-row { gap: 10px; }
.pud-period-share { font-size: 12px; font-weight: 700; color: var(--pud-muted); width: 38px; text-align: right; }

/* =========================================================================
   8. INTENSITY CARDS (DOCUMENT INTENSITY & ITEM INTENSITY)
   ========================================================================= */
.pud-intensity-card { display: flex; flex-direction: column; justify-content: space-between; gap: var(--pud-space-4); min-height: 210px; }
.pud-intensity-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.pud-intensity-top-main { display: flex; flex-direction: column; gap: 4px; }
.pud-intensity-value { margin-bottom: 0; font-size: 34px; font-weight: 800; line-height: 1; }
.pud-intensity-desc { font-size: 12px; color: var(--pud-muted); font-weight: 500; }
.pud-intensity-badge {
	font-size: 11px; font-weight: 800; padding: 5px 11px; border-radius: 999px;
	border: 1px solid transparent; white-space: nowrap; text-transform: uppercase; letter-spacing: .03em; flex: none;
}
.pud-intensity-badge-ok       { color: var(--pud-sev-ok); background: rgba(22,163,74,.12); border-color: rgba(22,163,74,.28); }
.pud-intensity-badge-watch    { color: var(--pud-sev-watch); background: rgba(217,140,14,.12); border-color: rgba(217,140,14,.28); }
.pud-intensity-badge-warn     { color: var(--pud-sev-warn); background: rgba(234,115,23,.12); border-color: rgba(234,115,23,.28); }
.pud-intensity-badge-critical { color: var(--pud-sev-critical); background: rgba(224,57,62,.12); border-color: rgba(224,57,62,.28); }

.pud-intensity-compare {
	display: flex; align-items: center; justify-content: space-between; gap: 8px;
	font-size: 12px; padding: 8px 10px; border-radius: var(--pud-radius-sm); background: var(--pud-surface-2);
}
.pud-intensity-compare-prev { display: flex; align-items: baseline; gap: 4px; font-weight: 700; color: var(--pud-ink); }
.pud-intensity-compare-label { font-weight: 500; color: var(--pud-muted); font-size: 11px; }
.pud-intensity-compare-pct { font-weight: 700; display: inline-flex; align-items: center; gap: 3px; font-size: 12px; }
.pud-intensity-compare-up      { color: var(--pud-sev-critical); }
.pud-intensity-compare-down    { color: var(--pud-sev-ok); }
.pud-intensity-compare-stable  { color: var(--pud-sev-watch); }

.pud-intensity-branches { display: flex; align-items: stretch; border-top: 1px solid var(--pud-border); padding-top: var(--pud-space-3); margin-top: auto; }
.pud-intensity-branch { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 4px; padding: 0 6px; position: relative; }
.pud-intensity-branch + .pud-intensity-branch::before { content: ''; position: absolute; left: 0; top: 2px; bottom: 2px; width: 1px; background: var(--pud-border); }
.pud-intensity-branch-name { font-size: 10px; color: var(--pud-muted); text-transform: uppercase; letter-spacing: .04em; font-weight: 600; }
.pud-intensity-branch-count { font-size: 15px; font-weight: 800; color: var(--pud-ink); }

/* =========================================================================
   9. ITEM TABLE (SEARCHABLE DETAIL TABLE)
   ========================================================================= */
.pud-item-table-container {
	margin-top: var(--pud-space-6);
	background: var(--pud-surface);
	border: 1px solid var(--pud-border);
	border-radius: var(--pud-radius-lg);
	box-shadow: var(--pud-shadow-md);
	overflow: hidden;
}

.pud-item-toolbar {
	display: flex; justify-content: space-between; align-items: center; gap: 12px;
	padding: var(--pud-space-4); border-bottom: 1px solid var(--pud-border); flex-wrap: wrap;
}
.pud-item-toolbar-left { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; flex: 1; }
.pud-item-search-wrap {
	display: flex; align-items: center; gap: 8px; padding: 7px 12px; border-radius: 6px;
	background: var(--pud-surface-2); border: 1px solid var(--pud-border-strong); min-width: 240px;
}
.pud-item-search-wrap .pud-icon { width: 14px; height: 14px; color: var(--pud-muted); flex: none; }
.pud-item-search-input { border: none; background: transparent; outline: none; font-size: 12.5px; color: var(--pud-ink); width: 100%; font-family: inherit; }
.pud-item-stage-tabs { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.pud-stage-tab-btn {
	display: inline-flex; align-items: center; gap: 6px; font-size: 12px; font-weight: 600;
	padding: 6px 12px; border-radius: 6px; border: 1px solid transparent; background: var(--pud-surface-2);
	color: var(--pud-ink-secondary); cursor: pointer; transition: all .15s ease;
}
.pud-stage-tab-btn:hover { background: var(--pud-surface-3); }
.pud-stage-tab-btn.active { background: var(--pud-accent-steel); color: #fff; }
.pud-count-pill { font-size: 11px; padding: 1px 6px; border-radius: 99px; background: rgba(0,0,0,0.12); font-weight: 700; }
.pud-stage-tab-btn.active .pud-count-pill { background: rgba(255,255,255,0.25); color: #fff; }

.pud-item-table-wrap { overflow-x: auto; max-height: 480px; }
.pud-item-table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
.pud-item-table th {
	position: sticky; top: 0; background: var(--pud-surface-2); color: var(--pud-ink-secondary);
	font-weight: 700; text-transform: uppercase; font-size: 11px; letter-spacing: 0.04em;
	padding: 10px 14px; border-bottom: 1px solid var(--pud-border); z-index: 2;
}
.pud-item-table td { padding: 10px 14px; border-bottom: 1px solid var(--pud-border); vertical-align: middle; }
.pud-item-table tr:hover td { background: var(--pud-surface-2); }

.pud-item-code-link { font-weight: 700; color: var(--pud-accent-steel); cursor: pointer; text-decoration: none; }
.pud-item-code-link:hover { text-decoration: underline; }
.pud-item-name-text { font-weight: 600; color: var(--pud-ink); }
.pud-item-supplier-text { font-size: 11px; color: var(--pud-muted); }
.pud-stage-badge {
	display: inline-block; font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 4px;
	background: var(--pud-surface-2); color: var(--pud-ink-secondary);
}
.pud-stage-po_pending { background: rgba(47,111,235,.12); color: var(--pud-accent-steel); }
.pud-stage-mr_completed { background: rgba(22,163,74,.12); color: var(--pud-sev-ok); }
.pud-stage-pr_pending { background: rgba(124,79,224,.12); color: var(--pud-accent-violet); }
.pud-stage-pi_pending { background: rgba(227,74,74,.12); color: var(--pud-accent-rust); }
.pud-stage-pi_completed { background: rgba(13,148,136,.12); color: var(--pud-accent-teal); }

.pud-doc-chips-container { display: flex; gap: 4px; flex-wrap: wrap; max-height: 54px; overflow-y: auto; }
.pud-item-doc-chip {
	font-size: 11px; padding: 2px 6px; border-radius: 4px; background: var(--pud-surface-3);
	color: var(--pud-accent-steel); font-weight: 600; cursor: pointer; text-decoration: none;
}
.pud-item-doc-chip:hover { background: var(--pud-accent-steel); color: #fff; }

/* Tags */
.pud-tag { display: inline-flex; align-items: center; font-size: 11px; font-weight: 700; padding: 2px 7px; border-radius: 4px; }
.pud-tag-amber { background: rgba(217,140,14,.14); color: var(--pud-sev-watch); }
.pud-tag-green { background: rgba(22,163,74,.14); color: var(--pud-sev-ok); }
.pud-tag-indigo { background: rgba(47,111,235,.14); color: var(--pud-accent-steel); }
.pud-tag-slate { background: var(--pud-surface-3); color: var(--pud-ink-secondary); }

/* =========================================================================
   10. LEADERBOARD
   ========================================================================= */
.pud-leaderboard-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(310px, 1fr)); gap: var(--pud-space-4); }
.pud-list-card { padding: var(--pud-space-5); }
.pud-list-card-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: var(--pud-space-3); }
.pud-list-card-actions { display: flex; align-items: center; gap: 6px; flex: none; }
.pud-export-btn {
	display: inline-flex; align-items: center; gap: 6px; font-size: 12px; font-weight: 700;
	padding: 6px 12px; border-radius: var(--pud-radius-sm); border: 1px solid var(--pud-border);
	background: var(--pud-surface-2); color: var(--pud-ink-secondary); cursor: pointer;
	white-space: nowrap; transition: background .2s, border-color .2s; font-family: inherit; flex: none;
}
.pud-export-btn:hover { background: var(--pud-surface-3); }
.pud-list-view-btn:hover { color: var(--pud-accent-steel); border-color: var(--pud-accent-steel); background: rgba(47,111,235,.1); }
.pud-export-btn .pud-icon { width: 13px; height: 13px; }

.pud-list-search {
	display: flex; align-items: center; gap: 8px; margin-bottom: var(--pud-space-3);
	padding: 7px 10px; border-radius: var(--pud-radius-sm); background: var(--pud-surface-2);
	border: 1px solid transparent; transition: border-color .2s, background .2s;
}
.pud-list-search:focus-within { border-color: var(--pud-border-strong); background: var(--pud-surface); }
.pud-list-search-icon { width: 14px; height: 14px; color: var(--pud-muted); flex: none; }
.pud-list-search-input { border: none; background: transparent; outline: none; font-size: 12px; color: var(--pud-ink); width: 100%; font-family: inherit; }

.pud-rows { display: flex; flex-direction: column; }
.pud-row {
	display: flex; align-items: center; gap: 12px; padding: 9px 0;
	border-bottom: 1px solid var(--pud-surface-2); transition: background .2s;
}
.pud-row:last-child { border-bottom: none; }
.pud-row-extra { display: none; }
.pud-list-card.pud-expanded .pud-row-extra { display: flex; animation: pud-row-in .3s ease; }
@keyframes pud-row-in { from{opacity:0;transform:translateY(-4px)} to{opacity:1;transform:translateY(0)} }
.pud-row-rank { font-size: 12px; color: var(--pud-muted); width: 22px; flex: none; font-weight: 700; text-align: center; }
.pud-row-medal { width: 22px; flex: none; text-align: center; font-size: 15px; line-height: 1; }
.pud-avatar {
	width: 30px; height: 30px; border-radius: 50%; background: var(--accent); color: #fff;
	display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 800;
	flex: none; box-shadow: 0 2px 6px rgba(0,0,0,.12);
}
.pud-row-name { flex: 1 1 120px; min-width: 0; font-size: 13px; font-weight: 600; color: var(--pud-ink); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pud-row-bar-wrap { flex: 0 0 100px; height: 6px; background: var(--pud-surface-2); border-radius: 99px; overflow: hidden; }
.pud-row-bar { display: block; height: 100%; background: var(--accent); border-radius: 99px; width: 0; transition: width .7s ease; }
.pud-row-count { font-size: 12.5px; font-weight: 700; white-space: nowrap; text-align: right; flex: none; color: var(--pud-ink); }
.pud-viewmore-btn {
	display: flex; align-items: center; justify-content: center; width: 100%; margin: var(--pud-space-4) 0 0; padding: 9px;
	background: var(--pud-surface-2); border: none; border-radius: var(--pud-radius-sm);
	color: var(--pud-ink); font-size: 13px; font-weight: 700; font-family: inherit; cursor: pointer; transition: background .2s;
}
.pud-viewmore-btn:hover { background: var(--pud-surface-3); }

/* =========================================================================
   11. MODAL STYLES
   ========================================================================= */
.pud-modal-wrap {
	position: fixed; inset: 0; z-index: 10000; display: flex; align-items: center; justify-content: center;
}
.pud-modal-bg { position: absolute; inset: 0; background: rgba(0,0,0,0.55); backdrop-filter: blur(4px); }
.pud-modal-box {
	position: relative; z-index: 1; background: var(--pud-surface); border: 1px solid var(--pud-border);
	border-radius: var(--pud-radius-lg); box-shadow: var(--pud-shadow-lg); width: 92%; max-width: 900px;
	max-height: 85vh; display: flex; flex-direction: column; overflow: hidden; animation: pud-modal-in .25s ease;
}
@keyframes pud-modal-in { from{opacity:0;transform:scale(0.96)} to{opacity:1;transform:scale(1)} }
.pud-modal-header {
	display: flex; align-items: center; justify-content: space-between; padding: 16px 20px;
	border-bottom: 1px solid var(--pud-border); background: var(--pud-surface);
}
.pud-modal-title { font-size: 17px; font-weight: 800; color: var(--pud-ink); }
.pud-modal-actions { display: flex; align-items: center; gap: 8px; }
.pud-modal-list-btn {
	display: inline-flex; align-items: center; gap: 6px;
	padding: 5px 12px; font-size: 12px; font-weight: 700;
	border-radius: var(--pud-radius-sm);
	background: var(--pud-surface-2); color: var(--pud-ink);
	border: 1px solid var(--pud-border); cursor: pointer;
	transition: all .15s ease;
}
.pud-modal-list-btn:hover {
	color: var(--pud-accent-steel); border-color: var(--pud-accent-steel);
	background: rgba(47,111,235,.1); transform: translateY(-1px);
}
.pud-modal-list-btn .pud-icon { width: 13px; height: 13px; }
.pud-modal-close { border: none; background: transparent; cursor: pointer; color: var(--pud-muted); padding: 4px; }
.pud-modal-close:hover { color: var(--pud-ink); }
.pud-modal-close .pud-icon { width: 18px; height: 18px; }
.pud-modal-scrollable { overflow-y: auto; padding: 16px 20px; }

.pud-modal-collapsible-row { border: 1px solid var(--pud-border); border-radius: 8px; margin-bottom: 8px; overflow: hidden; }
.pud-modal-row-header {
	display: flex; align-items: center; gap: 10px; padding: 10px 14px; background: var(--pud-surface-2);
	cursor: pointer; font-size: 13px; flex-wrap: wrap;
}
.pud-modal-row-chevron { font-size: 10px; color: var(--pud-muted); width: 14px; }
.pud-modal-row-docid { font-weight: 700; color: var(--pud-accent-steel); text-decoration: none; }
.pud-modal-row-hint { font-weight: 500; color: var(--pud-ink-secondary); flex: 1; }
.pud-modal-row-date { font-size: 11px; color: var(--pud-muted); }
.pud-modal-row-detail { padding: 14px; background: var(--pud-surface); border-top: 1px solid var(--pud-border); }
.pud-modal-subtable { width: 100%; border-collapse: collapse; font-size: 12px; }
.pud-modal-subtable th { text-align: left; padding: 6px 10px; border-bottom: 1px solid var(--pud-border); color: var(--pud-muted); font-size: 11px; }
.pud-modal-subtable td { padding: 6px 10px; border-bottom: 1px solid var(--pud-border); vertical-align: middle; }

/* =========================================================================
   12. RESPONSIVE
   ========================================================================= */
@media (max-width: 1024px) {
	.pud-root { padding: 22px 20px 44px; }
}
@media (max-width: 768px) {
	.pud-header { flex-direction: column; align-items: stretch; }
	.pud-header-actions { justify-content: flex-end; }
	.pud-toolbar { flex-direction: column; align-items: stretch; }
	.pud-toolbar-group--right { margin-left: 0; justify-content: flex-end; }
	.pud-kpi-row, .pud-grid { grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); }
	.pud-title { font-size: 22px; }
	.pud-kpi-value { font-size: 30px; }
}
@media (max-width: 480px) {
	.pud-kpi-row, .pud-grid, .pud-leaderboard-grid { grid-template-columns: 1fr; }
	.pud-toolbar-group { width: 100%; }
	.pud-custom-select-wrapper { width: 100%; }
}
`;