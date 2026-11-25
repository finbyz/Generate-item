// ---------------------------------------------------------------------------
// SUPPLIER EVALUATION DASHBOARD — frontend
//
// Supplier Rating = 60% Quality Rating + 40% Delivery Rating, from submitted
// Supplier Scorecard Periods (see supplier_evaluation.py).
// Layout and look follow the Sales Order Tracker page (custom top bar, pill
// filters, panels, light / dark theme).
// ---------------------------------------------------------------------------

const SED_API = "generate_item.generate_item.page.supplier_evaluation.supplier_evaluation";

frappe.pages["supplier-evaluation"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Supplier Evaluation Dashboard"),
		single_column: true,
	});
	wrapper.supplier_evaluation = new SupplierEvaluationDashboard(page, wrapper);
};

class SupplierEvaluationDashboard {
	constructor(page, wrapper) {
		this.page = page;
		this.wrapper = wrapper;
		document.title = __("Supplier Evaluation Dashboard");
		$(this.wrapper).find(".page-head").hide();

		let theme = "light";
		try {
			theme = localStorage.getItem("sed_theme") || "light";
		} catch (e) {
			// storage blocked: stay on light
		}
		this.state = { theme };

		this.render_shell();
		this.refresh();
	}

	// ------------------------------------------------------------ shell
	render_shell() {
		this.$wrap = $(`<div class="sed-wrap">${this.markup()}</div>`);
		$(this.page.body).empty().append(this.$wrap);
		this.$content = this.$wrap.find(".sed-content");

		this._initializing = true;
		this.make_filters();
		this._initializing = false;

		this.bind_events();
		this.apply_theme();
	}

	markup() {
		return `
		<div class="sed-topbar">
			<div class="sed-topbar-title">
				<div class="sed-topbar-badge">SE</div>
				<div>
					<div class="sed-topbar-heading">${__("Supplier Evaluation Dashboard")}</div>
					<div class="sed-topbar-sub">${__("Scorecard")} → ${__("Delivery")} → ${__("Quality")} → ${__("Supplier Rating")}</div>
				</div>
			</div>
			<div class="sed-topbar-actions">
				<button class="sed-icon-btn sed-refresh-btn" title="${__("Refresh")}">${this.icon("refresh")}</button>
				<button class="sed-icon-btn sed-theme-toggle" title="${__("Switch to Dark Mode")}">${this.theme_icon()}</button>
			</div>
		</div>

		<div class="sed-filters">
			<div class="sed-filter-row">
				<div class="sed-filter-group">
					<div class="sed-pill-field sed-field-supplier" title="${__("Supplier")}">
						<span class="sed-pill-icon">${this.icon("user")}</span>
						<div class="sed-f-supplier-wrap sed-pill-input"></div>
					</div>
					<div class="sed-pill-field sed-field-fy" title="${__("Fiscal Year")}">
						<span class="sed-pill-icon">${this.icon("calendar")}</span>
						<div class="sed-f-fy-wrap sed-pill-input"></div>
					</div>
					<div class="sed-pill-field sed-field-quarter" title="${__("Quarter")}">
						<span class="sed-pill-icon">${this.icon("quarter")}</span>
						<div class="sed-f-quarter-wrap sed-pill-input"></div>
					</div>
				</div>
				<div class="sed-filter-actions">
					<button class="sed-reset">${__("Reset")}</button>
				</div>
			</div>
		</div>

		<div class="sed-content"></div>`;
	}

	make_control(selector, df) {
		const control = frappe.ui.form.make_control({
			parent: this.$wrap.find(selector).get(0),
			df: {
				...df,
				onchange: () => {
					if (!this._initializing) this.refresh();
				},
			},
			render_input: true,
		});
		control.refresh();
		return control;
	}

	make_filters() {
		this.supplier_control = this.make_control(".sed-f-supplier-wrap", {
			fieldtype: "Link",
			options: "Supplier",
			fieldname: "supplier",
			placeholder: __("All Suppliers"),
		});

		this.fiscal_year_control = this.make_control(".sed-f-fy-wrap", {
			fieldtype: "Link",
			options: "Fiscal Year",
			fieldname: "fiscal_year",
			placeholder: __("All Fiscal Years"),
			get_query: () => ({ filters: { disabled: 0, name: ["not like", "_Test%"] } }),
		});
		this.default_fy = null;
		try {
			this.default_fy = erpnext.utils.get_fiscal_year(frappe.datetime.get_today(), false, false);
		} catch (e) {
			console.error(e);
		}
		if (this.default_fy) this.fiscal_year_control.set_value(this.default_fy);

		this.quarter_control = this.make_control(".sed-f-quarter-wrap", {
			fieldtype: "Select",
			fieldname: "quarter",
			options: [
				{ value: "", label: __("All Quarters") },
				{ value: "Q1", label: __("Q1 (Apr - Jun)") },
				{ value: "Q2", label: __("Q2 (Jul - Sep)") },
				{ value: "Q3", label: __("Q3 (Oct - Dec)") },
				{ value: "Q4", label: __("Q4 (Jan - Mar)") },
			],
		});
	}

	bind_events() {
		this.$wrap.on("click", ".sed-refresh-btn", () => this.refresh(true));
		this.$wrap.on("click", ".sed-theme-toggle", () => this.toggle_theme());
		this.$wrap.on("click", ".sed-reset", async () => {
			this._initializing = true;
			await this.supplier_control.set_value("");
			await this.fiscal_year_control.set_value(this.default_fy || "");
			await this.quarter_control.set_value("");
			this._initializing = false;
			this.refresh();
		});
		// Open / close one supplier's quarter rows (supplier name still opens the supplier).
		this.$wrap.on("click", ".sed-expand-btn", (e) => {
			e.stopPropagation();
			this.toggle_supplier($(e.currentTarget).attr("data-supplier"));
		});
		this.$wrap.on("click", ".sed-rating-table tr.sed-parent-row", (e) => {
			if ($(e.target).closest("a, button").length) return;
			this.toggle_supplier($(e.currentTarget).attr("data-supplier"));
		});
		this.$wrap.on("click", ".sed-toggle-all-btn", (e) => {
			const open = $(e.currentTarget).attr("data-open") !== "1";
			const suppliers = ((this.last_data && this.last_data.rows) || []).map((r) => r.supplier);
			this.expanded = open ? new Set(suppliers) : new Set();
			if (this.last_data) this.render(this.last_data);
		});
		this.$wrap.on("click", ".sed-supplier-link", (e) => {
			e.preventDefault();
			this.supplier_control.set_value($(e.currentTarget).attr("data-supplier"));
		});
	}

	apply_theme() {
		this.$wrap.attr("data-theme", this.state.theme);
		const dark = this.state.theme === "dark";
		this.$wrap
			.find(".sed-theme-toggle")
			.html(this.theme_icon())
			.attr("title", dark ? __("Switch to Light Mode") : __("Switch to Dark Mode"));
	}

	toggle_theme() {
		this.state.theme = this.state.theme === "dark" ? "light" : "dark";
		try {
			localStorage.setItem("sed_theme", this.state.theme);
		} catch (e) {
			// storage blocked: theme lasts for this visit only
		}
		this.apply_theme();
		if (this.last_data) this.render(this.last_data);
	}

	// ------------------------------------------------------------ data
	get_filters() {
		return {
			supplier: this.supplier_control.get_value() || null,
			fiscal_year: this.fiscal_year_control.get_value() || null,
			quarter: this.quarter_control.get_value() || null,
		};
	}

	async refresh(force = false) {
		const filters = this.get_filters();
		const key = JSON.stringify(filters);
		if (!force && this.loaded && key === this.last_key) return;
		this.loaded = true;
		this.last_key = key;
		this.last_supplier = filters.supplier;
		const { supplier, fiscal_year, quarter } = filters;
		if (quarter && !fiscal_year) {
			this.render_message(__("Please select a Fiscal Year to filter by Quarter."));
			return;
		}

		this.render_message(__("Loading..."));
		try {
			const r = await frappe.call({ method: `${SED_API}.get_dashboard_data`, args: filters });
			if (key !== JSON.stringify(this.get_filters())) return;

			const data = r.message || {};
			if (!data.rows || !data.rows.length) {
				const where = [
					supplier ? __("for {0}", [frappe.utils.escape_html(supplier).bold()]) : "",
					fiscal_year ? __("in Fiscal Year {0}", [frappe.utils.escape_html(fiscal_year).bold()]) : "",
					quarter ? __("in Quarter {0}", [quarter.bold()]) : "",
				].filter(Boolean).join(" ");
				this.render_message(__("No submitted Supplier Scorecard Period found {0}.", [where]));
				return;
			}
			this.render(data);
		} catch (e) {
			console.error(e);
			this.loaded = false;
			this.render_message(__("Could not load the dashboard. Please reload the page or contact the administrator."));
		}
	}

	render_message(message) {
		this.last_data = null;
		this.$content.html(`<div class="sed-panel"><div class="sed-empty-row">${message}</div></div>`);
	}

	// ------------------------------------------------------------ render
	render(data) {
		this.last_data = data;
		const { summary, rows, weights, group_by, grades, quarters, quarter_rows } = data;
		this.group_by = group_by;
		// Trend line only for a single supplier; no bar chart for the all-suppliers view.
		const show_charts = group_by === "period";
		const { fiscal_year, quarter } = this.get_filters();
		const scope = [
			group_by === "supplier"
				? __("{0} supplier(s)", [rows.length])
				: __("{0}, {1} period(s)", [frappe.utils.escape_html(this.last_supplier), rows.length]),
			fiscal_year ? __("Fiscal Year {0}", [frappe.utils.escape_html(fiscal_year)]) : __("All fiscal years"),
			quarter || "",
		].filter(Boolean).join(" · ");

		this.$content.html(`
			<div class="sed-section-head">
				<div class="sed-section-title-wrap">
					<div class="sed-section-title">${__("Overview")}</div>
					<div class="sed-result-count">${scope}</div>
				</div>
			</div>
			<div class="sed-stat-grid">
				${this.card(__("Supplier Rating"), summary.supplier_rating,
					__("{0}% Quality + {1}% Delivery", [weights.quality, weights.delivery]),
					`sed-tone-${summary.grade.toLowerCase()} sed-highlight`,
					this.pill(`${summary.grade} · ${__(summary.performance_level)}`, summary.grade))}
				${this.card(__("Delivery Rating"), summary.delivery_rating,
					__("On Time {0} / Ordered {1}", [this.qty(summary.on_time_qty), this.qty(summary.order_qty)]), "sed-tone-delivery")}
				${this.card(__("Quality Rating"), summary.quality_rating,
					__("Pass {0} / Received {1}", [this.qty(summary.pass_qty), this.qty(summary.received_qty)]), "sed-tone-quality")}
			</div>
			${this.grade_legend(grades)}

			${quarters ? this.quarter_table(quarters, weights, grades) : ""}

			${show_charts ? `
			<div class="sed-chart-grid">
				<div class="sed-panel sed-panel-pad sed-tone-delivery">
					<div class="sed-panel-title">${__("Delivery Rating Trend")}</div>
					<div class="sed-chart sed-delivery-chart"></div>
				</div>
				<div class="sed-panel sed-panel-pad sed-tone-quality">
					<div class="sed-panel-title">${__("Quality Rating Trend")}</div>
					<div class="sed-chart sed-quality-chart"></div>
				</div>
			</div>` : ""}

			${this.rating_section(rows, summary, quarter_rows, weights)}
		`);

		if (show_charts) {
			this.chart(".sed-delivery-chart", rows, "delivery_rating", __("Delivery Rating"), "#2563EB");
			this.chart(".sed-quality-chart", rows, "quality_rating", __("Quality Rating"), "#16A34A");
		}
	}

	card(label, value, note, extra_class = "", extra_html = "") {
		return `
			<div class="sed-stat-card ${extra_class}">
				<div class="sed-stat-head">
					<div class="sed-stat-label">${label}</div>
					${extra_html}
				</div>
				<div class="sed-stat-value">${this.pct(value)}</div>
				<div class="sed-stat-sub">${note}</div>
			</div>`;
	}

	quarter_table(data, weights, grades) {
		const cols = data.avg
			? [...data.quarters, { ...data.avg, label: __("Avg"), months: "", is_avg: true }]
			: data.quarters;
		const dash = `<span class="sed-faint">-</span>`;
		const value = (q, key) => (q.has_data ? this.pct(q[key]) : dash);
		const grade = (q) => (q.has_data ? this.grade_text(grades, q.grade) : dash);
		const row = (label, scale, cell, cls = "") => `
			<tr class="${cls}">
				<td>${label}</td>
				<td class="sed-num-c">${scale}</td>
				${cols.map((q) => `<td class="sed-num-c ${q.is_avg ? "sed-q-avg" : ""}">${cell(q)}</td>`).join("")}
			</tr>`;

		return `
			<div class="sed-section-head">
				<div class="sed-section-title-wrap">
					<div class="sed-section-title">${__("Supplier Rating Weighted")}</div>
					<div class="sed-result-count">${data.avg
						? __("Quarters of the fiscal year. Avg is the average of quarters with data.")
						: __("Selected quarter of the fiscal year.")}</div>
				</div>
			</div>
			<div class="sed-panel">
				<div class="sed-table-wrap">
					<table class="sed-status-table sed-quarter-table">
						<thead><tr>
							<th>${__("Parameter")}</th>
							<th class="sed-num-c">${__("Scale")}</th>
							${cols.map((q) => `<th class="sed-num-c ${q.is_avg ? "sed-q-avg" : ""}">
								${q.label}${q.months ? `<div class="sed-q-months">${q.months}</div>` : ""}
							</th>`).join("")}
						</tr></thead>
						<tbody>
							${row(__("Delivery Performance"), `${weights.delivery}%`, (q) => value(q, "delivery_weighted"))}
							${row(__("Quality Performance"), `${weights.quality}%`, (q) => value(q, "quality_weighted"))}
							${row(__("Supplier Rating"), "100%", (q) => value(q, "supplier_rating"), "sed-q-total")}
							${row(__("Performance Grade"), this.grade_text(grades, grades[0].grade), grade)}
						</tbody>
					</table>
				</div>
			</div>`;
	}

	// Status pill in the grade's colour (Sales Order Tracker style).
	pill(label, grade, title = "") {
		const esc = frappe.utils.escape_html;
		return `<span class="sed-pill sed-grade-${String(grade).toLowerCase()}" title="${esc(title)}">${esc(label)}</span>`;
	}

	grade_badge(row) {
		return this.pill(row.grade, row.grade, __(row.performance_level));
	}

	grade_range(grades, i) {
		const g = grades[i];
		if (i === 0) return __("{0}% and above", [g.min]);
		if (g.min === 0) return __("Below {0}%", [grades[i - 1].min]);
		return __("{0}% to below {1}%", [g.min, grades[i - 1].min]);
	}

	// Grade as full text: level name in the grade colour, score range below.
	grade_text(grades, grade) {
		const i = grades.findIndex((g) => g.grade === grade);
		if (i < 0) return `<span class="sed-faint">-</span>`;
		return `${this.pill(__(grades[i].level), grade)}
			<div class="sed-q-months">${this.grade_range(grades, i)}</div>`;
	}

	grade_legend(grades) {
		return `
			<div class="sed-legend">
				<span class="sed-legend-title">${__("Supplier Grade")}</span>
				${grades.map((g, i) => `
					<span class="sed-legend-item">
						${this.grade_badge({ grade: g.grade, performance_level: g.level })}
						<span class="sed-legend-level">${__(g.level)}</span>
						<span class="sed-faint">${this.grade_range(grades, i)}</span>
					</span>`).join("")}
			</div>`;
	}

	// Delivery and Quality Rating, Sales Order Tracker table style: one header
	// row, pinned first column, plain numbers, coloured pills for ratings,
	// Supplier Wise / Quarter Wise switch and a "Showing" footer.
	toggle_supplier(supplier) {
		if (!supplier) return;
		this.expanded = this.expanded || new Set();
		const open = !this.expanded.has(supplier);
		if (open) this.expanded.add(supplier);
		else this.expanded.delete(supplier);

		const $table = this.$wrap.find(".sed-rating-table");
		const match = (i, el) => $(el).attr("data-supplier") === supplier;
		$table.find("tr.sed-parent-row").filter(match).toggleClass("expanded", open);
		$table.find("tr.sed-sub-row").filter(match).toggleClass("sed-hidden", !open);

		const suppliers = ((this.last_data && this.last_data.rows) || []).map((r) => r.supplier);
		const all_open = suppliers.length && suppliers.every((s) => this.expanded.has(s));
		this.$wrap.find(".sed-toggle-all-btn")
			.attr("data-open", all_open ? 1 : 0)
			.html(`${this.icon(all_open ? "collapse" : "expand", 13)}<span>${all_open ? __("Collapse All") : __("Expand All")}</span>`);
	}

	rating_section(rows, summary, quarter_rows, weights) {
		const by_supplier = this.group_by === "supplier";
		const by_quarter = !!quarter_rows;
		// Collapsible quarter rows under each supplier (closed by default).
		const collapsible = by_supplier && by_quarter;
		this.expanded = this.expanded || new Set();

		const cols = [
			{ label: __("Order Qty"), key: "order_qty", type: "qty" },
			{ label: __("Qty Received On Time"), key: "on_time_qty", type: "qty" },
			{ label: __("Delivery Rating"), key: "delivery_rating", type: "rating", tone: "delivery",
				title: __("Qty Received On Time x 100 / Order Qty") },
			{ label: __("Qty Received"), key: "received_qty", type: "qty" },
			{ label: __("Qty Pass"), key: "pass_qty", type: "qty" },
			{ label: __("Rejected Qty"), type: "qty", calc: (r) => (r.received_qty || 0) - (r.pass_qty || 0) },
			{ label: __("Rejection %"), type: "rate",
				calc: (r) => (r.received_qty ? ((r.received_qty - (r.pass_qty || 0)) * 100) / r.received_qty : 0) },
			{ label: __("Quality Rating"), key: "quality_rating", type: "rating", tone: "quality",
				title: __("Qty Pass x 100 / Qty Received") },
			{ label: __("Supplier Rating"), key: "supplier_rating", type: "rating", tone: "rating",
				title: __("{0}% Quality + {1}% Delivery", [weights.quality, weights.delivery]) },
			{ label: __("Grade"), type: "grade" },
		];

		const muted = `<span class="sed-faint">—</span>`;
		const cell = (row, c) => {
			if (row.has_data === false) return muted;
			if (c.type === "grade") {
				return row.grade
					? this.pill(`${row.grade} · ${__(row.performance_level)}`, row.grade, __(row.performance_level))
					: muted;
			}
			const value = c.calc ? c.calc(row) : row[c.key];
			if (c.type === "qty") return this.qty(value);
			if (c.type === "rating") return `<span class="sed-mini-pill sed-tone-${c.tone}">${this.pct(value)}</span>`;
			return this.pct(value);
		};
		const td_class = (c) => (c.type === "grade" ? "sed-grade-cell" : c.type === "rating" ? "sed-rating-cell" : "sed-num-cell");
		const value_cells = (row) => cols.map((c) => `<td class="${td_class(c)}">${cell(row, c)}</td>`).join("");

		const esc = frappe.utils.escape_html;
		const supplier_lead = (row) => `
			<div class="sed-lead-main">
				${collapsible ? `<button type="button" class="sed-expand-btn" data-supplier="${esc(row.supplier)}"
					title="${__("Show / hide quarters")}">${this.icon("chevron", 12)}</button>` : ""}
				${this.row_link(row)}
			</div>`;
		const quarter_lead = (q) => `
			<span class="sed-chip">${q.label}</span>
			<span class="sed-faint sed-chip-sub">${q.months}</span>`;
		const line = (lead, row, cls = "", attrs = "") => `
			<tr class="${cls}" ${attrs}>
				<td class="sed-lead">${lead}</td>
				<td class="sed-num-cell">${row.has_data === false ? muted : (row.periods ?? 1)}</td>
				${value_cells(row)}
			</tr>`;

		let body;
		let count;
		let noun;
		if (by_supplier && by_quarter) {
			body = rows.map((row) => {
				const open = this.expanded.has(row.supplier);
				const key = `data-supplier="${esc(row.supplier)}"`;
				return line(supplier_lead(row), row, `sed-parent-row ${open ? "expanded" : ""}`, key)
					+ (quarter_rows[row.supplier] || [])
						.map((q) => line(quarter_lead(q), q, `sed-sub-row ${open ? "" : "sed-hidden"}`, key))
						.join("");
			}).join("");
			count = rows.length;
			noun = __("Suppliers");
		} else if (by_supplier) {
			body = rows.map((row) => line(supplier_lead(row), row)).join("");
			count = rows.length;
			noun = __("Suppliers");
		} else if (by_quarter) {
			const qs = quarter_rows[this.last_supplier] || [];
			body = qs.map((q) => line(quarter_lead(q), q)).join("");
			count = qs.length;
			noun = __("Quarters");
		} else {
			body = rows.map((row) => line(supplier_lead(row), row)).join("");
			count = rows.length;
			noun = __("Periods");
		}

		const lead_label = by_supplier ? (by_quarter ? __("Supplier / Quarter") : __("Supplier"))
			: (by_quarter ? __("Quarter") : __("Period"));
		const total_periods = rows.reduce((n, r) => n + (r.periods || 1), 0);

		const all_open = collapsible && rows.every((r) => this.expanded.has(r.supplier));
		const toggle = collapsible ? `
			<button type="button" class="sed-toggle-all-btn" data-open="${all_open ? 1 : 0}">
				${this.icon(all_open ? "collapse" : "expand", 13)}
				<span>${all_open ? __("Collapse All") : __("Expand All")}</span>
			</button>` : "";

		return `
			<div class="sed-section-head">
				<div class="sed-section-title-wrap">
					<div class="sed-section-title">${__("Delivery and Quality Rating")}</div>
					<div class="sed-result-count">${count} ${noun}</div>
				</div>
				${toggle}
			</div>
			<div class="sed-table-scroll">
				<table class="sed-status-table sed-rating-table">
					<thead><tr>
						<th class="sed-lead">${lead_label}</th>
						<th class="sed-num-cell">${__("Periods")}</th>
						${cols.map((c) => `<th class="${td_class(c)}" ${c.title ? `title="${frappe.utils.escape_html(c.title)}"` : ""}>${c.label}</th>`).join("")}
					</tr></thead>
					<tbody>${body}</tbody>
					<tfoot><tr>
						<td class="sed-lead">${__("Total")}</td>
						<td class="sed-num-cell">${total_periods}</td>
						${value_cells(summary)}
					</tr></tfoot>
				</table>
			</div>
			<div class="sed-pagination-bar">
				<div class="sed-page-info">${__("Showing {0} of {1} {2}", [count ? `1–${count}` : "0", count, noun])}</div>
				<div class="sed-page-legend">
					<span class="sed-mini-pill sed-tone-delivery">${__("Delivery")}</span>
					<span class="sed-mini-pill sed-tone-quality">${__("Quality")}</span>
					<span class="sed-mini-pill sed-tone-rating">${__("Supplier Rating")}</span>
				</div>
			</div>`;
	}

	row_link(row) {
		if (this.group_by === "supplier") {
			const name = frappe.utils.escape_html(row.supplier);
			return `<a href="#" class="sed-supplier-link sed-so-link" data-supplier="${name}"
				title="${__("Show periods for this supplier")}">${name}</a>`;
		}
		return `<a class="sed-so-link" href="/app/supplier-scorecard-period/${encodeURIComponent(row.period)}">${this.row_label(row)}</a>`;
	}

	row_label(row) {
		if (this.group_by === "supplier") return row.supplier;
		return `${frappe.datetime.str_to_user(row.start_date)} - ${frappe.datetime.str_to_user(row.end_date)}`;
	}

	chart(selector, rows, key, label, color) {
		new frappe.Chart(this.$content.find(selector)[0], {
			type: "line",
			height: 220,
			colors: [color],
			data: {
				labels: rows.map((row) => this.row_label(row)),
				datasets: [{ name: label, values: rows.map((row) => row[key]) }],
			},
			lineOptions: { dotSize: 4, regionFill: 1 },
			tooltipOptions: { formatTooltipY: (v) => this.pct(v) },
		});
	}

	pct(value) {
		return `${format_number(value || 0, null, 2)}%`;
	}

	qty(value) {
		// Whole quantities without decimals, others with 2.
		const v = flt(value || 0, 2);
		return format_number(v, null, Number.isInteger(v) ? 0 : 2);
	}

	// ------------------------------------------------------------ icons
	theme_icon() {
		return this.icon(this.state.theme === "dark" ? "sun" : "moon", 16);
	}

	icon(name, size = 15) {
		const paths = {
			refresh: `<path d="M21 12a9 9 0 11-9-9c2.5 0 4.7 1 6.4 2.6L21 8M21 3v5h-5"/>`,
			sun: `<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/>`,
			moon: `<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>`,
			user: `<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>`,
			calendar: `<rect x="3.5" y="5" width="17" height="16" rx="2.2"/><path d="M8 3v4M16 3v4M3.5 10h17"/>`,
			quarter: `<circle cx="12" cy="12" r="9"/><path d="M12 3v9h9"/>`,
			chevron: `<path d="m9 6 6 6-6 6"/>`,
			expand: `<path d="m7 15 5 5 5-5"/><path d="m7 9 5-5 5 5"/>`,
			collapse: `<path d="m7 20 5-5 5 5"/><path d="m7 4 5 5 5-5"/>`,
			list: `<line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/>`,
			grid: `<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>`,
		};
		return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">${paths[name] || ""}</svg>`;
	}
}
