// ---------------------------------------------------------------------------
// PROCUREMENT DASHBOARD — frontend
//
// Turnaround time = Material Request created to first Purchase Receipt, broken
// down into: MR → PO created → submitted for checking → checked → approved → receipt
// Base document: Material Request. The turnaround table has one row per
// Material Request + Purchase Receipt pair (Purchase Receipt Item.material_request).
// Data and definitions: procurement_dash.py.
// Look follows the Sales Order Tracker page (top bar, pill filters, panels,
// light / dark theme), same as the Supplier Evaluation Dashboard.
// ---------------------------------------------------------------------------

const PD_API = "generate_item.generate_item.page.procurement_dash.procurement_dash";

// Colour per step (tone classes in procurement_dash.css)
const PD_STEP_TONE = {
	mr_to_po: "amber",
	preparation: "gray",
	checking: "blue",
	approval: "green",
	approved_to_pr: "violet",
	receipt_to_invoice: "teal",
};

frappe.pages["procurement-dash"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Procurement Dashboard"),
		single_column: true,
	});
	wrapper.procurement_dashboard = new ProcurementDashboard(page, wrapper);
};

class ProcurementDashboard {
	constructor(page, wrapper) {
		this.page = page;
		this.wrapper = wrapper;
		document.title = __("Procurement Dashboard");
		$(this.wrapper).find(".page-head").hide();

		let theme = "light";
		try {
			theme = localStorage.getItem("pd_theme") || "light";
		} catch (e) {
			// storage blocked: stay on light
		}
		this.state = { theme, sort: "transaction_date", sort_dir: "desc", page: 1, page_size: 50 };
		// Document filters of the Material Request Turnaround table (kept across reloads)
		this.doc_filters = { material_request: "", purchase_order: "", purchase_receipt: "", purchase_invoice: "" };

		this.render_shell();
		this.refresh();
	}

	// ------------------------------------------------------------ shell
	render_shell() {
		this.$wrap = $(`<div class="pd-wrap">${this.markup()}</div>`);
		$(this.page.body).empty().append(this.$wrap);
		this.$content = this.$wrap.find(".pd-content");

		this._initializing = true;
		this.make_filters();
		this._initializing = false;

		this.bind_events();
		this.apply_theme();
	}

	markup() {
		return `
		<div class="pd-topbar">
			<div class="pd-topbar-title">
				<div class="pd-topbar-badge">PD</div>
				<div>
					<div class="pd-topbar-heading">${__("Procurement Dashboard")}</div>
					<div class="pd-topbar-sub">${__("Material Request")} → ${__("Purchase Order")} → ${__("Checking")} → ${__("Approval")} → ${__("Purchase Receipt")}</div>
				</div>
			</div>
			<div class="pd-topbar-actions">
				<button class="pd-icon-btn pd-refresh-btn" title="${__("Refresh")}">${this.icon("refresh")}</button>
				<button class="pd-icon-btn pd-theme-toggle" title="${__("Switch to Dark Mode")}">${this.theme_icon()}</button>
			</div>
		</div>

		<div class="pd-filters">
			<div class="pd-filter-row">
				<div class="pd-filter-group">
					<div class="pd-pill-field pd-field-date" title="${__("MR Date From")}">
						<span class="pd-pill-icon">${this.icon("calendar")}</span>
						<div class="pd-f-from-wrap pd-pill-input"></div>
					</div>
					<span class="pd-date-sep">${__("to")}</span>
					<div class="pd-pill-field pd-field-date" title="${__("MR Date To")}">
						<span class="pd-pill-icon">${this.icon("calendar")}</span>
						<div class="pd-f-to-wrap pd-pill-input"></div>
					</div>
					<div class="pd-pill-field pd-field-branch" title="${__("Branch")}">
						<span class="pd-pill-icon">${this.icon("branch")}</span>
						<div class="pd-f-branch-wrap pd-pill-input"></div>
					</div>
					<div class="pd-pill-field pd-field-supplier" title="${__("Supplier")}">
						<span class="pd-pill-icon">${this.icon("user")}</span>
						<div class="pd-f-supplier-wrap pd-pill-input"></div>
					</div>
				</div>
				<div class="pd-filter-actions">
					<button class="pd-reset">${__("Reset")}</button>
				</div>
			</div>
		</div>

		<div class="pd-content"></div>`;
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

	default_dates() {
		const to = frappe.datetime.get_today();
		return { from: frappe.datetime.add_months(to, -6), to };
	}

	make_filters() {
		const d = this.default_dates();
		this.from_control = this.make_control(".pd-f-from-wrap", {
			fieldtype: "Date", fieldname: "from_date", placeholder: __("From Date"),
		});
		this.to_control = this.make_control(".pd-f-to-wrap", {
			fieldtype: "Date", fieldname: "to_date", placeholder: __("To Date"),
		});
		this.branch_control = this.make_control(".pd-f-branch-wrap", {
			fieldtype: "Link", options: "Branch", fieldname: "branch", placeholder: __("All Branches"),
		});
		this.supplier_control = this.make_control(".pd-f-supplier-wrap", {
			fieldtype: "Link", options: "Supplier", fieldname: "supplier", placeholder: __("All Suppliers"),
		});
		this.from_control.set_value(d.from);
		this.to_control.set_value(d.to);
	}

	bind_events() {
		this.$wrap.on("click", ".pd-refresh-btn", () => this.refresh(true));
		this.$wrap.on("click", ".pd-theme-toggle", () => this.toggle_theme());
		this.$wrap.on("click", ".pd-reset", async () => {
			const d = this.default_dates();
			this._initializing = true;
			await this.from_control.set_value(d.from);
			await this.to_control.set_value(d.to);
			await this.branch_control.set_value("");
			await this.supplier_control.set_value("");
			this._initializing = false;
			this.refresh();
		});
		this.$wrap.on("click", ".pd-doc-clear", async () => {
			this.doc_filters = { material_request: "", purchase_order: "", purchase_receipt: "", purchase_invoice: "" };
			for (const control of Object.values(this.doc_controls || {})) {
				await control.set_value("");
			}
			this.state.page = 1;
			this.render_po_list();
		});
		// PO list: sort and paging
		this.$wrap.on("click", ".pd-po-table th[data-sort]", (e) => {
			const key = $(e.currentTarget).attr("data-sort");
			if (this.state.sort === key) {
				this.state.sort_dir = this.state.sort_dir === "desc" ? "asc" : "desc";
			} else {
				this.state.sort = key;
				this.state.sort_dir = "desc";
			}
			this.state.page = 1;
			this.render_po_list();
		});
		this.$wrap.on("click", ".pd-page-btn", (e) => {
			const step = Number($(e.currentTarget).attr("data-step"));
			this.state.page = Math.max(1, Math.min(this.total_pages || 1, this.state.page + step));
			this.render_po_list();
		});
		this.$wrap.on("change", ".pd-page-size", (e) => {
			this.state.page_size = Number($(e.currentTarget).val());
			this.state.page = 1;
			this.render_po_list();
		});
	}

	apply_theme() {
		this.$wrap.attr("data-theme", this.state.theme);
		const dark = this.state.theme === "dark";
		this.$wrap
			.find(".pd-theme-toggle")
			.html(this.theme_icon())
			.attr("title", dark ? __("Switch to Light Mode") : __("Switch to Dark Mode"));
	}

	toggle_theme() {
		this.state.theme = this.state.theme === "dark" ? "light" : "dark";
		try {
			localStorage.setItem("pd_theme", this.state.theme);
		} catch (e) {
			// storage blocked: theme lasts for this visit only
		}
		this.apply_theme();
		if (this.data) this.render(this.data);
	}

	// ------------------------------------------------------------ data
	get_filters() {
		return {
			from_date: this.from_control.get_value() || null,
			to_date: this.to_control.get_value() || null,
			branch: this.branch_control.get_value() || null,
			supplier: this.supplier_control.get_value() || null,
		};
	}

	async refresh(force = false) {
		const filters = this.get_filters();
		const key = JSON.stringify(filters);
		if (!force && this.loaded && key === this.last_key) return;
		this.loaded = true;
		this.last_key = key;

		this.render_message(__("Loading..."));
		try {
			const r = await frappe.call({ method: `${PD_API}.get_dashboard_data`, args: filters });
			if (key !== JSON.stringify(this.get_filters())) return;
			const data = r.message || {};
			if (!data.summary) {
				this.render_message(__("No submitted Material Request found for these filters."));
				return;
			}
			this.state.page = 1;
			this.render(data);
		} catch (e) {
			console.error(e);
			this.loaded = false;
			this.render_message(__("Could not load the dashboard. Please reload the page or contact the administrator."));
		}
	}

	render_message(message) {
		this.data = null;
		this.$content.html(`<div class="pd-panel"><div class="pd-empty-row">${message}</div></div>`);
	}

	// ------------------------------------------------------------ render
	render(data) {

		this.data = data;
		this.$content.html(`
			<div class="pd-cycle-section"></div>

			<div class="pd-section-head">
				<div class="pd-section-title-wrap">
					<div class="pd-section-title">${__("Material Request Turnaround")}</div>
					<div class="pd-result-count pd-mr-count"></div>
				</div>
			</div>
			<div class="pd-filters pd-doc-filters">
				<div class="pd-filter-row">
					<div class="pd-filter-group">
						<div class="pd-pill-field pd-field-doc" title="${__("Material Request")}">
							<span class="pd-pill-icon">${this.icon("doc")}</span>
							<div class="pd-f-mr-wrap pd-pill-input"></div>
						</div>
						<div class="pd-pill-field pd-field-doc" title="${__("Purchase Order")}">
							<span class="pd-pill-icon">${this.icon("doc")}</span>
							<div class="pd-f-po-wrap pd-pill-input"></div>
						</div>
						<div class="pd-pill-field pd-field-doc" title="${__("Purchase Receipt")}">
							<span class="pd-pill-icon">${this.icon("box")}</span>
							<div class="pd-f-pr-wrap pd-pill-input"></div>
						</div>
						<div class="pd-pill-field pd-field-doc" title="${__("Purchase Invoice")}">
							<span class="pd-pill-icon">${this.icon("invoice")}</span>
							<div class="pd-f-pi-wrap pd-pill-input"></div>
						</div>
					</div>
					<div class="pd-filter-actions">
						<button class="pd-reset pd-doc-clear">${__("Clear")}</button>
					</div>
				</div>
			</div>
			<div class="pd-po-list"></div>
		`);

		this.make_doc_filters();
		this.render_po_list();
		this.render_cycle(data);
	}

	// ------------------------------------------------------------ cycle time
	// Average time per step (MR → PO → checking → approval → receipt → invoice)
	// and the monthly trend of PO cycle, checking and approval time.
	render_cycle(data) {
		const s = data.summary;
		const steps = data.steps || [];
		const avg = (key) => (s[key] && s[key].avg != null ? this.dur(s[key].avg, true) : `<span class="pd-faint">—</span>`);
		const n = (key) => (s[key] && s[key].count ? __("{0} records", [format_number(s[key].count, null, 0)]) : __("No data"));
		const STEP_NOTE = {
			mr_to_po: __("MR created to PO created"),
			preparation: __("PO created to sent for checking"),
			checking: __("Sent for checking to checked"),
			approval: __("Checked to approved"),
			approved_to_pr: __("PO approved to first receipt"),
			receipt_to_invoice: __("Receipt to Purchase Invoice"),
		};
		const STEP_STYLE = {
			mr_to_po: { color: "var(--pd-accent-amber)", icon: "doc" },
			preparation: { color: "var(--pd-gray-ink)", icon: "clock" },
			checking: { color: "var(--pd-accent-steel)", icon: "search" },
			approval: { color: "var(--pd-accent-moss)", icon: "checkCircle" },
			approved_to_pr: { color: "var(--pd-accent-violet)", icon: "box" },
			receipt_to_invoice: { color: "var(--pd-accent-teal)", icon: "invoice" },
		};
		const esc = frappe.utils.escape_html;
		// KPI card, same look as the dashboard's earlier number cards
		const card = ({ label, key, note, color, icon, badge = "", big = false }) => `
			<div class="pd-kpi-card pd-cycle-card ${big ? "pd-cycle-big" : ""}" title="${esc(note)}">
				<div class="pd-kpi-top">
					<div class="pd-kpi-icon">${this.icon(icon, 16)}</div>
					<div class="pd-kpi-label">${esc(label)}</div>
					${badge ? `<span class="pd-step-no">${badge}</span>` : ""}
				</div>
				<div class="pd-kpi-value">${avg(key)}</div>
				<div class="pd-kpi-footer">
					<div class="pd-kpi-sub">${note}</div>
					<span class="pd-kpi-chip">${n(key)}</span>
				</div>
			</div>`;

		this.$content.find(".pd-cycle-section").html(`
			<div class="pd-section-head">
				<div class="pd-section-title-wrap">
					<div class="pd-section-title">${__("Purchase Cycle Time")}</div>
					<div class="pd-result-count">${__("Average time · MR Date {0}", [`${frappe.datetime.str_to_user(data.from_date)} – ${frappe.datetime.str_to_user(data.to_date)}`])}</div>
				</div>
			</div>
			<div class="pd-kpi-row pd-cycle-headline">
				${card({ label: __("Full Purchase Cycle"), key: "full_cycle", note: __("Material Request to Purchase Invoice"), color: "var(--pd-accent-teal)", icon: "invoice", big: true })}
				${card({ label: __("Turnaround"), key: "turnaround", note: __("Material Request to Purchase Receipt"), color: "var(--pd-accent-violet)", icon: "box", big: true })}
				${card({ label: __("PO Cycle"), key: "po_cycle", note: __("PO created to approved"), color: "var(--pd-accent-amber)", icon: "cycle", big: true })}
			</div>

			<div class="pd-section-head">
				<div class="pd-section-title-wrap">
					<div class="pd-section-title">${__("Time Taken at Each Step")}</div>
					<div class="pd-result-count">${__("Material Request → Purchase Order → Checking → Approval → Receipt → Invoice")}</div>
				</div>
			</div>
			<div class="pd-kpi-row pd-step-row">
				${steps.map((st, i) => card({
					label: __(st.label), key: st.key, note: STEP_NOTE[st.key] || "",
					color: (STEP_STYLE[st.key] || {}).color || "var(--pd-accent-steel)",
					icon: (STEP_STYLE[st.key] || {}).icon || "clock",
					badge: __("Step {0}", [i + 1]),
				})).join("")}
			</div>

			<div class="pd-section-head">
				<div class="pd-section-title-wrap">
					<div class="pd-section-title">${__("Full Purchase Cycle by Month")}</div>
					<div class="pd-result-count">${__("Average days from Material Request to Purchase Invoice, by Material Request month · hover a bar to see each step")}</div>
				</div>
			</div>
			<div class="pd-panel pd-panel-pad pd-trend-panel">
				<div class="pd-trend-chart"></div>
			</div>`);

		// one bar per month = sum of the 6 step averages, MR to Purchase Invoice (days)
		const TREND_STEPS = [
			["mr_to_po", __("MR to PO")],
			["preparation", __("PO Preparation")],
			["checking", __("Checking")],
			["approval", __("Approval")],
			["approved_to_pr", __("Approved to Receipt")],
			["receipt_to_invoice", __("Receipt to Invoice")],
		];
		const to_days = (h) => (h == null ? null : Math.round((h / 24) * 10) / 10);
		// months with no finished step at all would plot as 0 days: leave them out
		const months = (data.months || []).filter((m) => TREND_STEPS.some(([k]) => m[k] != null));
		const $chart = this.$content.find(".pd-trend-chart");
		if (!months.length) {
			$chart.html(`<div class="pd-empty-row">${__("No data for these filters.")}</div>`);
			return;
		}
		const totals = months.map((m) => Math.round(TREND_STEPS.reduce((a, [k]) => a + (to_days(m[k]) || 0), 0) * 10) / 10);
		// tooltip: month, then a small table of days per step and the total
		const split = {};
		months.forEach((m, i) => {
			const steps = TREND_STEPS.map(([k, label], n) => `<tr><td>${n + 1}. ${label}</td><td>${m[k] == null
				? `<span class="pd-tip-muted">${__("Not yet")}</span>`
				: `${format_number(to_days(m[k]), null, 1)} ${__("Days")}`}</td></tr>`).join("");
			split[m.label] = `<div class="pd-tip">
				<div class="pd-tip-title">${m.label}</div>
				<table>${steps}<tr class="pd-tip-total"><td>${__("Full Cycle")}</td><td>${format_number(totals[i], null, 1)} ${__("Days")}</td></tr></table>
				<div class="pd-tip-muted">${__("{0} Material Requests · {1} receipts", [format_number(m.mr_count, null, 0), format_number(m.received, null, 0)])}</div>
			</div>`;
		});
		this.trend_chart = new frappe.Chart($chart.get(0), {
			type: "bar",
			height: 260,
			data: {
				labels: months.map((m) => m.label),
				datasets: [{ name: __("Full Cycle"), values: totals }],
			},
			colors: ["#0289F7"],
			valuesOverPoints: 1,
			barOptions: { spaceRatio: 0.6 },
			tooltipOptions: {
				formatTooltipX: (label) => split[label] || label,
				formatTooltipY: (v) => `${format_number(v, null, 1)} ${__("Days")}`,
			},
		});

		// With values printed on the bars, frappe.Chart only opens the tooltip when the
		// pointer is on the number. Open it for the whole bar column too (same maths as
		// the library's own handler).
		const chart = this.trend_chart;
		chart.container.addEventListener("mousemove", (e) => {
			if (e.target.getAttribute("class") === "data-point-value") return;
			const m = chart.measures;
			const rect = chart.container.getBoundingClientRect();
			const x = e.clientX - rect.left - (m.margins.left + m.paddings.left);
			const y = e.clientY - rect.top;
			const top = m.titleHeight + m.margins.top + m.paddings.top;
			if (y > top && y < chart.height + top) chart.mapTooltipXPosition(x, -20);
		});
	}

	make_doc_filters() {
		const make = (selector, key, doctype, placeholder) => {
			const control = frappe.ui.form.make_control({
				parent: this.$content.find(selector).get(0),
				df: {
					fieldtype: "Link",
					options: doctype,
					fieldname: key,
					placeholder,
					get_query: () => ({
						filters: doctype === "Material Request"
							? { docstatus: 1, material_request_type: "Purchase" }
							: { docstatus: 1 },
					}),
					onchange: () => {
						const value = control.get_value() || "";
						if (value === this.doc_filters[key]) return;
						this.doc_filters[key] = value;
						this.state.page = 1;
						this.render_po_list();
					},
				},
				render_input: true,
			});
			control.refresh();
			if (this.doc_filters[key]) control.set_value(this.doc_filters[key]);
			return control;
		};
		this.doc_controls = {
			material_request: make(".pd-f-mr-wrap", "material_request", "Material Request", __("Material Request")),
			purchase_order: make(".pd-f-po-wrap", "purchase_order", "Purchase Order", __("Purchase Order")),
			purchase_receipt: make(".pd-f-pr-wrap", "purchase_receipt", "Purchase Receipt", __("Purchase Receipt")),
			purchase_invoice: make(".pd-f-pi-wrap", "purchase_invoice", "Purchase Invoice", __("Purchase Invoice")),
		};
	}

	// Row matches the table's document filters (PO / receipt: any of the MR's documents)
	match_doc_filters(r) {
		const f = this.doc_filters;
		if (f.material_request && r.name !== f.material_request) return false;
		if (f.purchase_order && r.purchase_order !== f.purchase_order) return false;
		if (f.purchase_receipt && r.purchase_receipt !== f.purchase_receipt) return false;
		if (f.purchase_invoice && r.purchase_invoice !== f.purchase_invoice) return false;
		return true;
	}

	render_po_list() {
		if (!this.data) return;
		const { sort, sort_dir, page_size } = this.state;
		const rows = (this.data.rows || []).filter((r) => this.match_doc_filters(r)).sort((a, b) => {
			const av = a[sort];
			const bv = b[sort];
			if (av == null && bv == null) return 0;
			if (av == null) return 1;
			if (bv == null) return -1;
			const cmp = typeof av === "string" ? av.localeCompare(bv) : av - bv;
			return sort_dir === "desc" ? -cmp : cmp;
		});
		this.total_pages = Math.max(1, Math.ceil(rows.length / page_size));
		this.state.page = Math.min(this.state.page, this.total_pages);
		const start = (this.state.page - 1) * page_size;
		const page_rows = rows.slice(start, start + page_size);
		const esc = frappe.utils.escape_html;
		const muted = `<span class="pd-faint">—</span>`;
		const STAGE_TONE = {
			Invoiced: "green", "Awaiting Invoice": "teal", "Awaiting Receipt": "amber", "PO in Approval": "blue",
			"Awaiting PO": "red", Stopped: "gray",
		};

		const cols = [
			{ key: "mr_to_po", label: __("MR to PO") },
			{ key: "preparation", label: __("Preparation") },
			{ key: "checking", label: __("Checking"), tone: "blue" },
			{ key: "approval", label: __("Approval"), tone: "green" },
			{ key: "approved_to_pr", label: __("Approved to Receipt") },
			{ key: "receipt_to_invoice", label: __("Receipt to Invoice") },
			{ key: "po_cycle", label: __("PO Cycle"), tone: "amber" },
			{ key: "turnaround", label: __("Turnaround"), tone: "violet" },
			{ key: "full_cycle", label: __("Full Cycle"), tone: "teal" },
		];
		const pi_cell = (r) => {
			if (!r.purchase_invoice) return muted;
			const more = r.invoice_count > 1
				? ` <span class="pd-chip" title="${__("{0} Purchase Invoices for this receipt; the first is used", [r.invoice_count])}">+${r.invoice_count - 1}</span>`
				: "";
			return `<a class="pd-so-link" href="/app/purchase-invoice/${encodeURIComponent(r.purchase_invoice)}">${esc(r.purchase_invoice)}</a>${more}`;
		};
		const arrow = (key) => (sort === key ? (sort_dir === "desc" ? " ▾" : " ▴") : "");
		const th = (key, label, cls = "pd-num-cell") =>
			`<th class="${cls} pd-sortable" data-sort="${key}">${label}${arrow(key)}</th>`;
		const po_cell = (r) => {
			if (!r.purchase_order) return muted;
			return `<a class="pd-so-link" href="/app/purchase-order/${encodeURIComponent(r.purchase_order)}">${esc(r.purchase_order)}</a>`;
		};
		const pr_cell = (r) => {
			if (!r.purchase_receipt) return muted;
			const of = r.receipt_count > 1
				? ` <span class="pd-chip" title="${__("Receipt {0} of {1} for this Material Request", [r.receipt_no, r.receipt_count])}">${r.receipt_no}/${r.receipt_count}</span>`
				: "";
			return `<a class="pd-so-link" href="/app/purchase-receipt/${encodeURIComponent(r.purchase_receipt)}">${esc(r.purchase_receipt)}</a>${of}`;
		};

		const filtered = Object.values(this.doc_filters).some(Boolean);
		this.$content.find(".pd-mr-count").text(
			filtered
				? __("{0} of {1} rows match the filters ({2} Material Requests) · click a column to sort", [rows.length, (this.data.rows || []).length, new Set(rows.map((r) => r.name)).size])
				: __("{0} rows · {1} Material Requests · one row per Purchase Receipt · click a column to sort", [rows.length, new Set(rows.map((r) => r.name)).size])
		);

		this.$content.find(".pd-po-list").html(`
			<div class="pd-table-scroll">
				<table class="pd-status-table pd-po-table">
					<thead><tr>
						${th("name", __("Material Request"), "pd-lead")}
						${th("branch", __("Branch"), "")}
						${th("transaction_date", __("MR Date"), "")}
						${th("stage", __("Stage"), "")}
						${th("purchase_order", __("Purchase Order"), "")}
						${th("supplier", __("Supplier"), "")}
						${th("purchase_receipt", __("Purchase Receipt"), "")}
						${th("receipt_date", __("Receipt Date"), "")}
						${th("purchase_invoice", __("Purchase Invoice"), "")}
						${th("invoice_date", __("Invoice Date"), "")}
						${cols.map((c) => th(c.key, c.label)).join("")}
						${th("rework", __("Rework"))}
						${th("age", __("Open Age"))}
					</tr></thead>
					<tbody>
						${page_rows.length ? "" : `<tr><td colspan="20" class="pd-empty-row">${__("No Material Request matches these filters.")}</td></tr>`}
						${page_rows.map((r) => `<tr>
							<td class="pd-lead"><a class="pd-so-link" href="/app/material-request/${encodeURIComponent(r.name)}">${esc(r.name)}</a></td>
							<td>${r.branch ? `<span class="pd-branch-badge">${esc(r.branch)}</span>` : muted}</td>
							<td class="pd-date-cell">${frappe.datetime.str_to_user(r.transaction_date)}</td>
							<td><span class="pd-mini-pill pd-stage-pill pd-stage-${STAGE_TONE[r.stage] || "gray"}">${__(r.stage)}</span></td>
							<td class="pd-po-cell">${po_cell(r)}</td>
							<td class="pd-customer-cell" title="${esc(r.supplier || "")}">${r.supplier ? esc(r.supplier) : muted}</td>
							<td class="pd-po-cell">${pr_cell(r)}</td>
							<td class="pd-date-cell">${r.receipt_date ? frappe.datetime.str_to_user(r.receipt_date) : muted}</td>
							<td class="pd-po-cell">${pi_cell(r)}</td>
							<td class="pd-date-cell">${r.invoice_date ? frappe.datetime.str_to_user(r.invoice_date) : muted}</td>
							${cols.map((c) => `<td class="pd-num-cell">${
								r[c.key] == null ? muted
									: c.tone ? `<span class="pd-mini-pill pd-tone-${c.tone}">${this.dur(r[c.key])}</span>`
									: this.dur(r[c.key])
							}</td>`).join("")}
							<td class="pd-num-cell">${r.rework ? `<span class="pd-mini-pill pd-tone-red">${r.rework}</span>` : muted}</td>
							<td class="pd-num-cell">${r.age == null ? muted : this.dur(r.age)}</td>
						</tr>`).join("")}
					</tbody>
				</table>
			</div>
			<div class="pd-pagination-bar">
				<div class="pd-page-info">${__("Showing {0}–{1} of {2} rows", [
					rows.length ? start + 1 : 0, Math.min(start + page_size, rows.length), rows.length])}</div>
				<div class="pd-page-controls">
					<button class="pd-page-btn" data-step="-1" ${this.state.page <= 1 ? "disabled" : ""}>‹ ${__("Prev")}</button>
					<span class="pd-page-num">${__("Page {0} of {1}", [this.state.page, this.total_pages])}</span>
					<button class="pd-page-btn" data-step="1" ${this.state.page >= this.total_pages ? "disabled" : ""}>${__("Next")} ›</button>
					<select class="pd-page-size">
						${[25, 50, 100].map((n) => `<option value="${n}" ${n === page_size ? "selected" : ""}>${n} / ${__("page")}</option>`).join("")}
					</select>
				</div>
			</div>`);
	}

	// Hours as a short duration: minutes under 1 h, hours under 2 days, else days.
	// long = true gives "Mins / Hrs / Days" (used on the number cards).
	dur(hours, long = false) {
		if (hours == null) return `<span class="pd-faint">—</span>`;
		if (hours < 1) return `${format_number(Math.round(hours * 60), null, 0)} ${long ? __("Mins") : __("min")}`;
		if (hours < 48) return `${format_number(hours, null, 1)} ${long ? __("Hrs") : __("h")}`;
		return `${format_number(hours / 24, null, 1)} ${long ? __("Days") : __("d")}`;
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
			doc: `<path d="M6 2.5h9l3 3V20a1.2 1.2 0 0 1-1.2 1.2H6A1.2 1.2 0 0 1 4.8 20V3.7A1.2 1.2 0 0 1 6 2.5Z"/><path d="M9 9h6M9 13h6M9 17h3.5"/>`,
			clock: `<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>`,
			cycle: `<path d="M21 12a9 9 0 0 1-15.5 6.2L3 16"/><path d="M3 12A9 9 0 0 1 18.5 5.8L21 8"/><path d="M21 3v5h-5M3 21v-5h5"/>`,
			search: `<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>`,
			checkCircle: `<circle cx="12" cy="12" r="9"/><path d="m8.5 12 2.5 2.5 4.5-4.5"/>`,
			layers: `<path d="M12 2 2 7l10 5 10-5-10-5Z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>`,
			invoice: `<path d="M5 2.5h14v19l-3-2-2 2-2-2-2 2-2-2-3 2z"/><path d="M9 8h6M9 12h6M9 16h3"/>`,
			box: `<path d="M21 8 12 3 3 8v8l9 5 9-5V8z"/><path d="m3 8 9 5 9-5M12 13v8"/>`,
			branch: `<line x1="6" y1="3" x2="6" y2="15"/><circle cx="18" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M18 9a9 9 0 0 1-9 9"/>`,
		};
		return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">${paths[name] || ""}</svg>`;
	}
}
