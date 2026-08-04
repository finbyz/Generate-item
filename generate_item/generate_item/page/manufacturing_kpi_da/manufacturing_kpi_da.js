const OCD_API_METHOD = "generate_item.generate_item.page.manufacturing_kpi_da.manufacturing_kpi_da.get_dashboard_data";

const OCD_BRANCHES = ["Sanand", "Nandikoor", "Rabale"];

const OCD_DATE_PRESETS = ["Today", "This Week", "Last Week", "This Month", "Last Month", "This Year", "Last Year", "Custom"];

const OCD_ACCENTS = ["steel", "amber", "moss", "violet", "teal", "rust"];

const OCD_SEVERITY = {
	"1":  { key: "ok",       label: __("1 Revision"),   tag: "OC·01" },
	"2":  { key: "watch",    label: __("2 Revisions"),   tag: "OC·02" },
	"3":  { key: "warn",     label: __("3 Revisions"),   tag: "OC·03" },
	"3+": { key: "critical", label: __("3+ Revisions"),  tag: "OC·04" },
};

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

				<!-- ── Header ── -->
				<div class="ocd-header">
					<div>
						<h2 class="ocd-title">${__("Manufacturing KPI Dashboard")}</h2>
						<div class="ocd-header-meta" data-field="summary">${__("Loading…")}</div>
					</div>
					<div class="ocd-header-actions">
						<button class="ocd-theme-toggle" type="button" title="${__("Toggle theme")}">
							<span class="ocd-theme-track">
								<span class="ocd-theme-thumb">
									<span class="ocd-theme-icon" aria-hidden="true">☀</span>
								</span>
							</span>
							<span class="ocd-theme-text">${__("Light mode")}</span>
						</button>
					</div>
				</div>

				<!-- ── Filter Bar ── -->
				<div class="ocd-filter-bar">
					<div class="ocd-filter-group">
						<span class="ocd-filter-label">${__("Branch")}</span>
						<select class="ocd-select" data-role="branch-select">
							<option value="">${__("All")}</option>
							${OCD_BRANCHES.map(b => `<option value="${b}">${b}</option>`).join("")}
						</select>
					</div>
					<div class="ocd-filter-group ocd-filter-group--right">
						<span class="ocd-filter-label">${__("Period")}</span>
						<select class="ocd-select" data-role="date-preset">
							${OCD_DATE_PRESETS.map(p =>
								`<option value="${p}" ${p === "Today" ? "selected" : ""}>${__(p)}</option>`
							).join("")}
						</select>
						<div class="ocd-custom-dates" data-role="custom-dates">
							<input type="date" class="ocd-date-input" data-role="from-date" />
							<span class="ocd-date-sep">→</span>
							<input type="date" class="ocd-date-input" data-role="to-date" />
						</div>
						<button class="ocd-btn ocd-refresh-btn" type="button">
							<span aria-hidden="true">↻</span> ${__("Refresh")}
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
					${this.section_head("03", __("Order Change Intensity"))}
					<div class="ocd-grid ocd-grid--4"></div>
				</section>

				<!-- ── Section 04 · Batch Change Intensity ── -->
				<section class="ocd-section" data-section="batch">
					${this.section_head("04", __("Batch Change Intensity"))}
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
				<span class="ocd-section-title">${title}</span>
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

		// Branch select
		this.wrapper.querySelector("[data-role='branch-select']").addEventListener("change", (e) => {
			this.filters.branch = e.target.value;
			this.load_data();
		});

		// Date preset
		const presetSel = this.wrapper.querySelector("[data-role='date-preset']");
		const customDates = this.wrapper.querySelector("[data-role='custom-dates']");

		presetSel.addEventListener("change", () => {
			const v = presetSel.value;
			this.filters.preset = v;

			const fromInput = this.wrapper.querySelector("[data-role='from-date']");
			const toInput = this.wrapper.querySelector("[data-role='to-date']");

			if (v !== "Custom") {
				const { from_date, to_date } = this.resolve_preset(v);
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
		});

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
	//   Today       → yesterday
	//   This Week   → same span, shifted back 7 days
	//   Last Week   → the week before that
	//   This Month  → last month (full month)
	//   Last Month  → the month before that (full month)
	//   Year        → last calendar year
	//   Custom      → an equal-length window immediately before it
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
				const cur = toObj(from_date); // Jan 1 of last year
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
		this.wrapper.querySelector('[data-trend-full]').innerHTML = '<div class="ocd-card ocd-skel" style="height:340px"></div>';
		this.wrapper.querySelector(".ocd-grid--branch").innerHTML = this.skeleton_cards(3);
		this.wrapper.querySelector(".ocd-grid--4").innerHTML = this.skeleton_cards(4, 250);
		this.wrapper.querySelector(".ocd-grid--batch-buckets").innerHTML = this.skeleton_cards(4, 250);
		this.wrapper.querySelector(".ocd-leaderboard-grid").innerHTML = `
			<div class="ocd-card ocd-skel" style="height:240px"></div>
			<div class="ocd-card ocd-skel" style="height:240px"></div>
		`;
		this.wrapper.querySelector(".ocd-customers-grid").innerHTML = `<div class="ocd-card ocd-skel" style="height:240px"></div>`;
		this.wrapper.querySelector("[data-role='top-kpis']").innerHTML = this.skeleton_cards(4);
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
		this.render_top_kpis(data, prevData);
		this.render_revision_trend(data.trends || {});
		this.render_period_changes(data);
		this.render_branches(data.branch_wise || []);
		this.render_order_change(data.order_change || {}, prevData.order_change || {});
		this.render_batch_buckets(data.batch_buckets || {}, prevData.batch_buckets || {});
		this.render_leaderboard(data.top_creators_high || [], data.top_creators_low || []);
		this.render_customers(data.top_customers || []);
		this.render_summary(data);

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

		el.innerHTML = `
			${this.kpi_card({ label: __("Total OMRs"), value: totalOmr, previous_value: prevTotalOmr, sub: __("in selected period"), color: "var(--ocd-accent-steel)", action: "total-omrs" })}
			${this.kpi_card({ label: __("Changed Batches"), value: batchCount, previous_value: prevBatchCount, sub: __("unique item+batch pairs"), color: "var(--ocd-accent-teal)" })}
			${this.kpi_card({
				label: __("Order Revision Rate"),
				value: rates.order_rate + "%",
				previous_value: prevRates.order_rate,
				is_rate: true,
				sub: `${rates.revised_sos} of ${rates.total_sos} orders`,
				color: get_color(rates.order_rate)
			})}
			${this.kpi_card({
				label: __("Item Revision Rate"),
				value: rates.item_rate + "%",
				previous_value: prevRates.item_rate,
				is_rate: true,
				sub: `${rates.changed_items} of ${rates.total_items} items`,
				color: get_color(rates.item_rate)
			})}
		`;
		this.animate_values(el);
	}

	kpi_card({ label, value, previous_value, is_rate, sub, color, action }) {
		const actionAttr = action ? `data-action="${action}" class="ocd-kpi-card ocd-clickable-card"` : `class="ocd-kpi-card"`;
		const current = is_rate ? parseFloat(value) : value;
		const deltaHtml = previous_value === undefined || previous_value === null
			? ""
			: this.render_kpi_delta(current, previous_value, !!is_rate);
		return `
			<div ${actionAttr}>
				<div class="ocd-kpi-content">
					<div class="ocd-kpi-label">${frappe.utils.escape_html(label)}</div>
					<div class="ocd-kpi-value" style="color: ${color}">${value}</div>
					<div class="ocd-kpi-sub">${frappe.utils.escape_html(sub)}</div>
					${deltaHtml}
				</div>

			</div>
		`;
	}

	// "vs previous period" chip for the top KPI cards. Rate-type KPIs (the two
	// revision-rate cards) compare in percentage points; count-type KPIs
	// (Total OMRs, Changed Batches) compare as a percent change, same
	// convention as the intensity cards: more = up = bad (red), less = down = good (green).
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

		const trendHtml = `
			<div class="ocd-card ocd-trend-full-card">
				<div class="ocd-trend-full-header">
					<div>
						<div class="ocd-list-title">${__("30-Day Revision Trend")}</div>
						<div class="ocd-list-subtitle">${__("Daily modification request count")}</div>
					</div>
					<div class="ocd-trend-badge">
						<span class="ocd-trend-badge-value ${trends.trend_direction}">
							${trends.trend_emoji} ${trends.change_percentage > 0 ? "+" : ""}${trends.change_percentage}%
						</span>
					</div>
				</div>
				<div class="ocd-sparkline-full" data-sparkline-full></div>
				<div class="ocd-trend-full-summary">
					<div class="ocd-trend-total">
						<span class="ocd-trend-label">${__("Total in Period")}</span>
						<span class="ocd-trend-value">${trends.total_this_month}</span>
					</div>
					<div class="ocd-trend-direction">${
						trends.trend_direction === "down"
							? __("Revisions trending downward — great improvement!")
							: trends.trend_direction === "up"
								? __("Revisions increasing — may need process review")
								: __("Revisions stable — consistent process execution")
					}</div>
				</div>
				<div class="ocd-trend-period-section" data-period-changes></div>
			</div>
		`;

		container.innerHTML = trendHtml;

		const sparklineContainer = container.querySelector("[data-sparkline-full]");
		if (sparklineContainer) {
			this.render_sparkline(sparklineContainer, trends.daily_data || []);
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

		container.innerHTML = `
			<div class="ocd-trend-period-header">
				<span class="ocd-trend-period-title">${this.get_period_title()}</span>
				<span class="ocd-trend-period-subtitle">${__("Changes performed in OMR against Sales Orders")}</span>
			</div>
			<div class="ocd-period-rows">
				${periodData.map((item, i) => {
					const pct = Math.round((item.count / maxCount) * 100);
					return `
						<div class="ocd-row">
							<span class="ocd-row-rank">${i + 1}</span>
							<span class="ocd-row-name" style="flex:1;">${item.label}</span>
							<span class="ocd-row-bar-wrap" style="flex:0 0 150px;">
								<span class="ocd-row-bar" style="--accent:var(--ocd-accent-steel);width:${pct}%"></span>
							</span>
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

		// Get month from first record
		const firstDate = new Date(trends[0].date);
		const year = firstDate.getFullYear();
		const month = firstDate.getMonth();

		// Total days in month
		const daysInMonth = new Date(year, month + 1, 0).getDate();

		// Create week buckets dynamically
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

		// Calculate counts
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
	render_branches(rows) {
		const el = this.wrapper.querySelector(".ocd-grid--branch");
		if (!el) return;

		// Ensure all branches are shown, even with zero count
		const allBranches = OCD_BRANCHES.map(branch => {
			const found = rows.find(r => r.branch === branch);
			return found || { branch: branch, count: 0 };
		});

		const displayRows = allBranches.length > 0 ? allBranches : rows;

		if (!displayRows.length) { el.innerHTML = this.empty_state(__("No submitted OMRs for the selected filters.")); return; }

		// Only flag a best/needs-attention branch when counts actually differ —
		// no point calling out a "worst" branch when every branch is at 0 or tied.
		const counts   = displayRows.map(r => r.count);
		const maxCount = Math.max(...counts);
		const minCount = Math.min(...counts);
		const hasSpread = maxCount > minCount && maxCount > 0;

		el.innerHTML = displayRows.map((row, i) => {
			const accent = OCD_ACCENTS[i % OCD_ACCENTS.length];
			let flag = null;
			if (hasSpread) {
				if (row.count === maxCount) flag = "attention";
				else if (row.count === minCount) flag = "best";
			}
			return this.stat_card({ accent, label: row.branch, value: row.count, action: "branch", action_id: row.branch, flag });
		}).join("");
		this.animate_values(el);
	}

	// ---------------------------------------------------------- order change
	render_order_change(buckets, prevBuckets = {}) {
		const el = this.wrapper.querySelector(".ocd-grid--4");
		const keys = ["1","2","3","3+"];
		const selectedBranch = this.filters.branch;

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
				accent: meta.key
			});
		}).join("");

		this.animate_values(el);
	}

	// ---------------------------------------------------------- batch buckets
	render_batch_buckets(buckets, prevBuckets = {}) {
		const el = this.wrapper.querySelector(".ocd-grid--batch-buckets");
		const keys = ["1","2","3","3+"];
		const selectedBranch = this.filters.branch;

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
				accent: meta.key
			});
		}).join("");

		this.animate_values(el);
	}

	// Build the per-branch counts to show under an intensity card.
	// - No branch filter: use the actual per-branch breakdown from the server.
	// - Branch filter active: the data is already scoped to that branch, so
	//   show the selected branch with the card's total and every other
	//   branch as 0 (rather than hiding the row entirely).
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

	// Wires up the "View More" toggle and the "CSV" export button for each
	// .ocd-list-card inside a container, matched by render order.
	bind_list_card_actions(container, exportGroups) {
		const cards = container.querySelectorAll(".ocd-list-card");
		cards.forEach((card, i) => {
			const vmBtn = card.querySelector(".ocd-viewmore-btn");
			if (vmBtn) {
				vmBtn.addEventListener("click", () => {
					const expanded = card.classList.toggle("ocd-expanded");
					vmBtn.textContent = expanded ? __("View Less") : __("View More");
				});
			}
			const exportBtn = card.querySelector(".ocd-export-btn");
			const group = exportGroups[i];
			if (exportBtn && group) {
				exportBtn.addEventListener("click", () => this.export_rows_csv(group.rows, group.filename));
			}
		});
	}

	// Client-side CSV export for a leaderboard/customer row set.
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
				<div>
					<div class="ocd-list-title">${title}</div>
					<div class="ocd-list-subtitle">${subtitle}</div>
				</div>
				${rows.length ? `<button type="button" class="ocd-export-btn" title="${__("Export CSV")}">⬇ ${__("CSV")}</button>` : ""}
			</div>
		`;

		if (!rows.length) {
			return `
				<div class="ocd-card ocd-list-card">
					${headHtml}
					${this.empty_state(__("No data available."))}
				</div>
			`;
		}
		const max   = Math.max(...rows.map(r => r.count));
		const items = rows.map((row, i) => {
			const pct        = max ? Math.round((row.count / max) * 100) : 0;
			const extraClass = i >= 5 ? " ocd-row-extra" : "";
			const actionAttr = action_type ? `data-action="${action_type}" data-id="${frappe.utils.escape_html(row.id)}"` : "";
			const clickableClass = action_type ? " ocd-clickable-row" : "";
			return `
				<div class="ocd-row${extraClass}${clickableClass}" ${actionAttr}>
					<span class="ocd-row-rank">${i + 1}</span>
					<span class="ocd-avatar" style="--accent:var(--ocd-accent-${accent})">${this.initials(row.full_name)}</span>
					<span class="ocd-row-name" title="${frappe.utils.escape_html(row.full_name)}">${frappe.utils.escape_html(row.full_name)}</span>
					<span class="ocd-row-bar-wrap"><span class="ocd-row-bar" style="--accent:var(--ocd-accent-${accent});width:${pct}%"></span></span>
					<span class="ocd-row-count">${row.count}</span>
				</div>
			`;
		}).join("");
		const vmBtn = rows.length > 5
			? `<button type="button" class="ocd-viewmore-btn">${__("View More")}</button>`
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
	stat_card({ accent, label, value, severity, action, action_id, section, severity_key, flag }) {
		const accentVar = severity ? `var(--ocd-sev-${accent})` : `var(--ocd-accent-${accent})`;
		const actionAttr = section ? `data-action="${section}" data-severity="${severity_key}" class="ocd-card ocd-stat-card ocd-clickable-card"` : (action ? `data-action="${action}" data-branch="${action_id}" class="ocd-card ocd-stat-card ocd-clickable-card"` : `class="ocd-card ocd-stat-card"`);
		const initial = frappe.utils.escape_html(String(label || "?").trim().charAt(0).toUpperCase());
		const flagHtml = flag === "attention"
			? `<span class="ocd-stat-flag ocd-stat-flag-attention">${__("Needs Attention")}</span>`
			: flag === "best"
				? `<span class="ocd-stat-flag ocd-stat-flag-best">${__("Best")}</span>`
				: "";
		return `
			<div ${actionAttr}>
				
				<div class="ocd-stat-avatar" style="background:${accentVar}">${initial}</div>
				<div class="ocd-stat-content">
					<div class="ocd-card-value" data-count="${value}" style="color: ${accentVar}">0</div>
					<div class="ocd-card-label">${frappe.utils.escape_html(label)}</div>
				</div>
			</div>
		`;
	}

	intensity_card({ label, value, previous_value, branches, action, severity_key, accent }) {
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

		return `
		<div class="ocd-card ocd-intensity-card ocd-clickable-card"
			data-action="${action}"
			data-severity="${severity_key}">

			<div class="ocd-intensity-top">
				<div class="ocd-card-value ocd-intensity-value"
					data-count="${value}"
					style="color:var(--ocd-sev-${accent})">0</div>
				<span class="ocd-intensity-badge ocd-intensity-badge-${accent}">${label}</span>
			</div>

			${compareHtml}

			${branchHtml}

		</div>
		`;
	}

	// Builds the "vs previous period" row shown on intensity cards.
	// More revisions/changes than before = up = bad (red); fewer = down = good (green),
	// matching the same convention already used on the 30-Day Revision Trend badge.
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

	empty_state(text) { return `<div class="ocd-empty">${text}</div>`; }

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
		if (!data.length) { container.innerHTML = `<div class="ocd-empty">${__("No trend data")}</div>`; return; }
		const values = data.map(d => d.count);
		const max    = Math.max(...values, 1);
		const w      = container.clientWidth || 500;
		const h      = 60, pad = 2;
		const pts    = values.map((v, i) => {
			const x = (i / (values.length - 1)) * (w - pad * 2) + pad;
			const y = h - ((v / max) * (h - pad * 2)) - pad;
			return `${x},${y}`;
		}).join(" ");
		const isUp = data[data.length - 1].count > data[0].count;
		const gid  = "sg-" + Date.now();
		const col  = isUp ? "var(--ocd-sev-warn)" : "var(--ocd-sev-ok)";
		container.innerHTML = `
			<svg width="100%" height="${h}" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none">
				<defs>
					<linearGradient id="${gid}" x1="0" y1="0" x2="0" y2="1">
						<stop offset="0%" stop-color="${col}" stop-opacity="0.3"/>
						<stop offset="100%" stop-color="${col}" stop-opacity="0.05"/>
					</linearGradient>
				</defs>
				<polyline fill="none" stroke="${col}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" points="${pts}"/>
				<polygon fill="url(#${gid})" points="${pts} ${w - pad},${h} ${pad},${h}"/>
			</svg>
		`;
	}
}

// ---------------------------------------------------------------------------
// CSS
// ---------------------------------------------------------------------------
const OCD_CSS = `
.ocd-root {
	--ocd-bg: #f8f9fa;
	--ocd-surface: #ffffff;
	--ocd-surface-2: #f1f3f5;
	--ocd-border: #e9ecef;
	--ocd-ink: #212529;
	--ocd-muted: #868e96;
	--ocd-accent-steel: #339af0;
	--ocd-accent-amber: #fcc419;
	--ocd-accent-moss: #51cf66;
	--ocd-accent-violet: #845ef7;
	--ocd-accent-teal: #20c997;
	--ocd-accent-rust: #f40f0f;
	--ocd-sev-ok: #51cf66;
	--ocd-sev-watch: #fcc419;
	--ocd-sev-warn: #ff922b;
	--ocd-sev-critical: #fa5252;
	--ocd-shadow: 0 4px 12px rgba(0,0,0,0.05);
	--ocd-radius: 12px;
	--ocd-mono: ui-monospace,SFMono-Regular,"JetBrains Mono",Menlo,Consolas,monospace;
	--ocd-glow-steel: rgba(51,154,240,0.12);
	--ocd-glow-amber: rgba(252,196,25,0.12);
	--ocd-glow-moss: rgba(81,207,102,0.12);
	--ocd-glow-violet: rgba(132,94,247,0.12);
	--ocd-glow-teal: rgba(32,201,151,0.12);
	--ocd-glow-rust: rgba(255,135,135,0.12);
	background:var(--ocd-bg);
	color:var(--ocd-ink);
	padding:24px 32px 48px;
	border-radius:8px;
	font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
	min-height:100vh;
}
.ocd-root[data-theme="dark"] {
	--ocd-bg:#12151a;
	--ocd-surface:#1b1f25;
	--ocd-surface-2:#21262d;
	--ocd-border:rgba(255,255,255,.09);
	--ocd-ink:#e7e9ec;
	--ocd-muted:#99a2ac;
	--ocd-shadow:0 4px 12px rgba(0,0,0,.5);
	--ocd-glow-steel: rgba(51,154,240,0.15);
	--ocd-glow-amber: rgba(252,196,25,0.15);
	--ocd-glow-moss: rgba(81,207,102,0.15);
	--ocd-glow-violet: rgba(132,94,247,0.15);
	--ocd-glow-teal: rgba(32,201,151,0.15);
	--ocd-glow-rust: rgba(255,135,135,0.15);
}
/* ── Header ── */
.ocd-header {
	display:flex;justify-content:space-between;align-items:flex-start;
	gap:16px;flex-wrap:wrap;padding-bottom:16px;
	margin-bottom:0;
}
.ocd-title { margin:0 0 4px;font-size:24px;font-weight:700;letter-spacing:-.02em; }
.ocd-header-meta { font-size:13px;color:var(--ocd-muted); }
.ocd-header-actions { display:flex;gap:8px;padding-top:4px; }

/* ── Filter Bar ── */
.ocd-filter-bar {
	display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;
	gap:16px;padding:16px 20px;margin:16px 0 24px;
	background:var(--ocd-surface);border:1px solid var(--ocd-border);
	border-radius:var(--ocd-radius);box-shadow:var(--ocd-shadow);
	backdrop-filter:blur(8px);
	position:sticky;top:8px;
}
.ocd-filter-group { display:flex;align-items:center;gap:12px;flex-wrap:wrap; }
.ocd-filter-group--right { margin-left:auto; }
.ocd-filter-label {
	font-size:12px;text-transform:uppercase;font-weight:600;
	letter-spacing:.05em;color:var(--ocd-muted);white-space:nowrap;
}

/* Date select */
.ocd-select {
	font-size:13px;padding:8px 32px 8px 12px;border-radius:8px;
	border:1px solid var(--ocd-border);background:var(--ocd-surface);
	color:var(--ocd-ink);cursor:pointer;font-family:inherit;font-weight:500;
	appearance:none;
	background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%236b7280'/%3E%3C/svg%3E");
	background-repeat:no-repeat;background-position:right 10px center;
	transition:border-color .2s;
}
.ocd-select:focus { outline:none;border-color:var(--ocd-accent-steel); }
/* Custom date */
.ocd-custom-dates { display:flex;align-items:center;gap:8px; }
.ocd-date-input {
	font-size:13px;padding:7px 10px;border-radius:8px;
	border:1px solid var(--ocd-border);background:var(--ocd-surface);
	color:var(--ocd-ink);font-family:inherit;
	transition:border-color .2s;
}
.ocd-date-input:focus { outline:none;border-color:var(--ocd-accent-steel); }
.ocd-date-sep { color:var(--ocd-muted);font-size:13px; }
/* Filter context chips */
.ocd-filter-context {
	display:flex;gap:8px;flex-wrap:wrap;padding:0 0 16px;
	font-size:13px;color:var(--ocd-muted);
}
.ocd-ctx-chip {
	display:inline-flex;align-items:center;gap:6px;
	padding:4px 12px;border-radius:16px;
	background:var(--ocd-surface);border:1px solid var(--ocd-border);
}
.ocd-ctx-icon { font-size:14px; }

/* ── Buttons ── */
.ocd-btn {
	display:inline-flex;align-items:center;gap:6px;font-size:13px;
	padding:8px 16px;border-radius:8px;border:1px solid var(--ocd-border);
	background:var(--ocd-surface);color:var(--ocd-ink);cursor:pointer;
	transition:all .2s ease;font-family:inherit;font-weight:500;
}
.ocd-btn:hover { border-color:var(--ocd-muted); }
.ocd-btn:focus-visible { outline:2px solid var(--ocd-accent-steel);outline-offset:2px; }
.ocd-refresh-btn { background:var(--ocd-surface-2);border:none;color:var(--ocd-ink); }
.ocd-refresh-btn:hover { background:var(--ocd-border); }

/* ── Section ── */
.ocd-section { margin-top:32px; animation: ocd-section-in 0.5s ease forwards; opacity:0; }
@keyframes ocd-section-in { from{opacity:0;transform:translateY(12px)} to{opacity:1;transform:translateY(0)} }
.ocd-section-head { display:flex;align-items:baseline;gap:10px;margin:0 0 16px;position:relative; }
.ocd-section-title { font-size:16px;font-weight:700;color:var(--ocd-ink); }

/* ── KPI Row ── */
.ocd-kpi-row { display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;margin-bottom:32px; }
.ocd-kpi-card {
	position:relative;background:var(--ocd-surface);border:1px solid var(--ocd-border);
	border-radius:var(--ocd-radius);box-shadow:var(--ocd-shadow);
	padding:24px;overflow:hidden;transition:transform .2s,box-shadow .2s;
	display:flex;justify-content:space-between;align-items:center;
}
.ocd-kpi-card:hover { transform:translateY(-2px);box-shadow:0 8px 24px rgba(0,0,0,0.08); }
.ocd-kpi-content { position:relative;z-index:2; }
.ocd-kpi-label { font-size:12px;color:var(--ocd-muted);text-transform:uppercase;letter-spacing:.05em;font-weight:600;margin-bottom:8px; }
.ocd-kpi-value { font-size:36px;font-weight:700;line-height:1;margin-bottom:8px; }
.ocd-kpi-sub { font-size:13px;color:var(--ocd-muted); }
.ocd-kpi-delta {
	display:inline-flex;align-items:center;gap:4px;flex-wrap:wrap;
	font-size:11px;font-weight:700;margin-top:10px;padding:4px 10px;
	border-radius:999px;background:var(--ocd-surface-2);width:fit-content;
}
.ocd-kpi-delta-label { font-weight:500;color:var(--ocd-muted); }
.ocd-kpi-delta-up      { color:var(--ocd-sev-critical); }
.ocd-kpi-delta-down    { color:var(--ocd-sev-ok); }
.ocd-kpi-delta-stable  { color:var(--ocd-sev-watch); }


/* ── Cards ── */
.ocd-grid { display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px; }
.ocd-card {
	position:relative;background:var(--ocd-surface);border:1px solid var(--ocd-border);
	border-radius:var(--ocd-radius);box-shadow:var(--ocd-shadow);
	padding:20px;overflow:hidden;transition:transform .2s,box-shadow .2s;
}
.ocd-stat-card { display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;gap:12px;min-height:170px; }
.ocd-stat-card:hover { transform:translateY(-2px);box-shadow:0 8px 24px rgba(0,0,0,0.08); }
.ocd-stat-avatar { width:44px;height:44px;border-radius:50%;display:flex;align-items:center;justify-content:center;color:#fff;font-size:16px;font-weight:700;box-shadow:0 4px 10px rgba(0,0,0,.15); }
.ocd-stat-content { position:relative;z-index:2;display:flex;flex-direction:column;align-items:center;gap:4px; }
.ocd-grid--branch { grid-template-columns:repeat(auto-fit,minmax(180px,220px));justify-content:center; }
.ocd-stat-flag {
	position:absolute;top:12px;right:12px;z-index:3;
	font-size:10px;font-weight:700;padding:3px 9px;border-radius:999px;
	text-transform:uppercase;letter-spacing:.03em;white-space:nowrap;
}
.ocd-stat-flag-attention { color:var(--ocd-sev-critical); background:rgba(250,82,82,.12); }
.ocd-stat-flag-best      { color:var(--ocd-sev-ok);       background:rgba(81,207,102,.12); }
.ocd-card-value {
	font-size:32px;font-weight:700;letter-spacing:-.02em;
	line-height:1;margin-bottom:8px;
}
.ocd-card-label { font-size:13px;color:var(--ocd-muted);font-weight:500; }
.ocd-empty { font-size:14px;color:var(--ocd-muted);padding:24px 4px;text-align:center; }
.ocd-skel {
	background:linear-gradient(90deg,var(--ocd-surface-2) 25%,var(--ocd-border) 37%,var(--ocd-surface-2) 63%);
	background-size:400% 100%;animation:ocd-shimmer 1.4s ease infinite;
}
@keyframes ocd-shimmer { 0%{background-position:100% 50%} 100%{background-position:0 50%} }

/* ── Revision Trend Full Width ── */
.ocd-trend-full-width { margin-bottom: 24px; }
.ocd-trend-full-card { padding: 24px; }
.ocd-trend-full-header { display:flex; justify-content:space-between; align-items:flex-start; margin-bottom: 20px; }
.ocd-sparkline-full { margin: 16px 0; height: 80px; }
.ocd-trend-full-summary { margin-top: 20px; padding-top: 16px; border-top: 1px solid var(--ocd-border); }

/* ── Trend Badge ── */
.ocd-trend-badge-value {
	font-size:13px;font-weight:600;padding:4px 12px;border-radius:16px;
}
.ocd-trend-badge-value.up    { background:rgba(250,82,82,.1);color:var(--ocd-sev-critical); }
.ocd-trend-badge-value.down  { background:rgba(81,207,102,.1);color:var(--ocd-sev-ok); }
.ocd-trend-badge-value.stable{ background:rgba(252,196,25,.1);color:var(--ocd-sev-watch); }
.ocd-trend-total { display:flex;justify-content:space-between;align-items:center;margin-bottom:8px; }
.ocd-trend-label { font-size:12px;color:var(--ocd-muted);text-transform:uppercase;letter-spacing:.05em;font-weight:600; }
.ocd-trend-value { font-size:18px;font-weight:700; }
.ocd-trend-direction { font-size:13px;color:var(--ocd-muted); }

/* ── Period Changes (nested inside Revision Trend card) ── */
.ocd-trend-period-section { margin-top:20px;padding-top:16px;border-top:1px solid var(--ocd-border); }
.ocd-trend-period-header { margin-bottom:12px; }
.ocd-trend-period-title { display:block;font-size:14px;font-weight:700; }
.ocd-trend-period-subtitle { display:block;font-size:12px;color:var(--ocd-muted);margin-top:2px; }
.ocd-period-rows { max-height:280px;overflow-y:auto; }

/* ── Leaderboard & Customers ── */
.ocd-leaderboard-grid, .ocd-customers-grid { display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px; }
.ocd-list-card { padding:20px; }
.ocd-list-card-head { display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:16px; }
.ocd-list-title { font-size:16px;font-weight:700;margin:0 0 4px; }
.ocd-list-subtitle { font-size:13px;color:var(--ocd-muted); }
.ocd-export-btn {
	display:inline-flex;align-items:center;gap:4px;font-size:12px;font-weight:600;
	padding:6px 10px;border-radius:8px;border:1px solid var(--ocd-border);
	background:var(--ocd-surface-2);color:var(--ocd-ink);cursor:pointer;
	white-space:nowrap;transition:background .2s,border-color .2s;
	font-family:inherit;flex:none;
}
.ocd-export-btn:hover { background:var(--ocd-border); }
.ocd-rows { display:flex;flex-direction:column; }
.ocd-row {
	display:flex;align-items:center;gap:12px;padding:10px 0;
	border-bottom:1px solid var(--ocd-surface-2);
}
.ocd-row:last-child { border-bottom:none; }
.ocd-row-extra { display:none; }
.ocd-list-card.ocd-expanded .ocd-row-extra { display:flex; }
.ocd-row-rank { font-size:12px;color:var(--ocd-muted);width:16px;flex:none;font-weight:600; }
.ocd-avatar {
	width:32px;height:32px;border-radius:50%;background:var(--accent);color:#fff;
	display:flex;align-items:center;justify-content:center;
	font-size:12px;font-weight:700;flex:none;
}
.ocd-row-name { flex:1 1 auto;min-width:0;font-size:14px;font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap; }
.ocd-row-bar-wrap { flex:0 0 100px;height:6px;background:var(--ocd-surface-2);border-radius:3px;overflow:hidden; }
.ocd-row-bar { display:block;height:100%;background:var(--accent);border-radius:3px;width:0;transition:width .7s ease; }
.ocd-row-count { font-size:14px;font-weight:600;width:32px;text-align:right;flex:none; }
.ocd-viewmore-btn {
	display:block;width:100%;margin:16px 0 0;padding:10px;background:var(--ocd-surface-2);
	border:none;border-radius:8px;color:var(--ocd-ink);
	font-size:13px;font-weight:600;font-family:inherit;cursor:pointer;
	transition:background .2s;
}
.ocd-viewmore-btn:hover { background:var(--ocd-border); }

/* ── Clickable Elements ── */
.ocd-clickable-card, .ocd-clickable-row { cursor: pointer; transition: background 0.2s, transform 0.2s, box-shadow 0.2s; }
.ocd-clickable-row:hover { background: var(--ocd-surface-2); border-radius: 6px; padding-left: 8px; padding-right: 8px; margin-left: -8px; margin-right: -8px; }
.ocd-clickable-card:hover { transform: translateY(-3px); box-shadow: 0 12px 32px rgba(0,0,0,0.12); border-color:var(--ocd-accent-steel); }
.ocd-clickable-card:active { transform: translateY(-1px); }
.ocd-stat-card.ocd-clickable-card::after,
.ocd-intensity-card.ocd-clickable-card::after {
	content:'';position:absolute;bottom:0;left:0;right:0;height:3px;
	background:linear-gradient(90deg,var(--ocd-accent-steel),var(--ocd-accent-violet),var(--ocd-accent-teal));
	border-radius:0 0 var(--ocd-radius) var(--ocd-radius);
	opacity:0;transition:opacity 0.3s ease;z-index:2;
}
.ocd-stat-card.ocd-clickable-card:hover::after,
.ocd-intensity-card.ocd-clickable-card:hover::after { opacity:1; }

@media(prefers-reduced-motion:reduce){
	.ocd-card,.ocd-row-bar,.ocd-skel,.ocd-kpi-card { transition:none;animation:none; }
	.ocd-section { animation:none;opacity:1; }
	.ocd-stat-card.ocd-clickable-card::after,
	.ocd-intensity-card.ocd-clickable-card::after { display:none; }
}

/* ── Intensity Cards (Order Change / Batch Change) ── */
.ocd-intensity-card { display:flex;flex-direction:column;justify-content:space-between;gap:16px;min-height:190px; }
.ocd-intensity-top { display:flex;align-items:flex-start;justify-content:space-between;gap:12px; }
.ocd-intensity-value { margin-bottom:0; }
.ocd-intensity-badge {
	font-size:11px;font-weight:700;padding:4px 10px;border-radius:999px;
	border:1px solid transparent;white-space:nowrap;
	text-transform:uppercase;letter-spacing:.03em;flex:none;
}
.ocd-intensity-badge-ok       { color:var(--ocd-sev-ok);       background:rgba(81,207,102,.12);  border-color:rgba(81,207,102,.3); }
.ocd-intensity-badge-watch    { color:var(--ocd-sev-watch);    background:rgba(252,196,25,.12);  border-color:rgba(252,196,25,.3); }
.ocd-intensity-badge-warn     { color:var(--ocd-sev-warn);     background:rgba(255,146,43,.12);  border-color:rgba(255,146,43,.3); }
.ocd-intensity-badge-critical { color:var(--ocd-sev-critical); background:rgba(250,82,82,.12);   border-color:rgba(250,82,82,.3); }

.ocd-intensity-compare {
	display:flex;align-items:center;justify-content:space-between;gap:8px;
	font-size:12px;padding:8px 10px;border-radius:8px;
	background:var(--ocd-surface-2);
}
.ocd-intensity-compare-prev { display:flex;align-items:baseline;gap:4px;font-weight:700;color:var(--ocd-ink); }
.ocd-intensity-compare-label { font-weight:500;color:var(--ocd-muted);font-size:11px; }
.ocd-intensity-compare-pct { font-weight:700;display:inline-flex;align-items:center;gap:3px;font-size:12px; }
.ocd-intensity-compare-up      { color:var(--ocd-sev-critical); }
.ocd-intensity-compare-down    { color:var(--ocd-sev-ok); }
.ocd-intensity-compare-stable  { color:var(--ocd-sev-watch); }

.ocd-intensity-branches { display:flex;align-items:stretch;border-top:1px solid var(--ocd-border);padding-top:14px;margin-top:auto; }
.ocd-intensity-branch { flex:1;display:flex;flex-direction:column;align-items:center;gap:4px;padding:0 6px;position:relative; }
.ocd-intensity-branch + .ocd-intensity-branch::before { content:'';position:absolute;left:0;top:2px;bottom:2px;width:1px;background:var(--ocd-border); }
.ocd-intensity-branch-name { font-size:10px;color:var(--ocd-muted);text-transform:uppercase;letter-spacing:.04em; }
.ocd-intensity-branch-count { font-size:15px;font-weight:700;color:var(--ocd-ink); }
.ocd-intensity-spacer { flex:1; }

.ocd-root{
    position: relative;
    min-height: 100vh;
}

.ocd-root::before{
    content: "";
    position: fixed;
    inset: 0;

  background-image: url("/files/SSV Logod5da1d.jpeg");
    background-repeat: no-repeat;
    background-position: center;
    background-size: 500px;

    opacity: .05;
    pointer-events: none;
    z-index: 0;
}

.ocd-root > *{
    position: relative;
    z-index: 1;
}

/* ── Theme Toggle (Light/Dark switch) ── */
.ocd-theme-toggle {
	display:flex;align-items:center;gap:10px;
	background:transparent;border:none;cursor:pointer;
	padding:6px 4px;font-family:inherit;
}
.ocd-theme-toggle:focus-visible { outline:2px solid var(--ocd-accent-steel);outline-offset:2px;border-radius:999px; }

.ocd-theme-track {
	position:relative;width:46px;height:24px;flex:none;
	border-radius:999px;border:2px solid var(--ocd-muted);
	background:var(--ocd-surface-2);
	transition:border-color .2s, background .2s;
}
.ocd-theme-toggle:hover .ocd-theme-track { border-color:var(--ocd-ink); }

.ocd-theme-thumb {
	position:absolute;top:1px;left:1px;width:16px;height:16px;
	border-radius:50%;background:var(--ocd-accent-amber);color:#fff;
	display:flex;align-items:center;justify-content:center;
	font-size:10px;line-height:1;
	transition:transform .25s cubic-bezier(.4,0,.2,1), background .25s, color .25s;
}
.ocd-root[data-theme="dark"] .ocd-theme-thumb {
	transform:translateX(21px);
	background:var(--ocd-surface);color:var(--ocd-muted);
}

.ocd-theme-text {
	font-size:13px;font-weight:600;color:var(--ocd-ink);white-space:nowrap;
}
`;