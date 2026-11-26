// Copyright (c) 2026, FinByz Tech Pvt Ltd and contributors
// For license information, please see license.txt

// Dotted path of the page's .py file (app: generate_item, module: Generate Item).
const SPD_METHOD =
	"generate_item.generate_item.page.supplier_performance.supplier_performance";

frappe.pages["supplier-performance"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Supplier Performance Dashboard"),
		single_column: true,
	});
	wrapper.spd = new SupplierPerformanceDashboard(page);
};

class SupplierPerformanceDashboard {
	constructor(page) {
		this.page = page;
		this.view = "quarter";
		this.expanded = new Set();
		this.data = null;
		this.ready = false;
		this.refresh = frappe.utils.debounce(() => this.fetch(), 300);

		this.add_style();
		this.make_layout();
		this.make_filters();
		this.bind_events();

		this.page.set_primary_action(__("Refresh"), () => this.fetch(), "refresh");
		this.page.set_secondary_action(__("Export"), () => this.export(), "download");

		this.set_defaults();
	}

	/* ------------------------------------------------------------------ layout */

	make_layout() {
		this.$wrap = $(`
			<div class="spd">
				<div class="spd-filters">
					<div class="spd-spacer"></div>
					<div class="spd-view">
						<div class="spd-view-label">${__("View")}</div>
						<div class="spd-seg">
							<button data-v="month">${__("Month wise")}</button>
							<button data-v="quarter" class="on">${__("Quarter wise")}</button>
						</div>
					</div>
				</div>

				<div class="spd-cards">
					${["delivery", "quality", "score"]
						.map(
							(k) => `
						<div class="spd-card" data-card="${k}">
							<div class="t"><span class="title"></span><span class="hint"></span></div>
							<div class="v">-</div>
							<div class="s"></div>
							<div class="bar"><i></i></div>
						</div>`
						)
						.join("")}
				</div>

				<div class="spd-legend"></div>

				<div class="spd-panel">
					<div class="spd-panel-head">
						<h3>${__("Delivery and Quality Rating")} <span class="spd-count"></span></h3>
						<button class="btn btn-default btn-xs spd-expand">${__("Expand All")}</button>
					</div>
					<div class="spd-tbl-wrap">
						<table class="spd-table">
							<thead>
								<tr>
									<th class="spd-first">${__("Supplier / Quarter")}</th>
									<th>${__("Periods")}</th>
									<th class="grp">${__("Order Qty")}</th>
									<th>${__("Qty Received On Time")}</th>
									<th>${__("Delivery Rating")}</th>
									<th class="grp">${__("Qty Received")}</th>
									<th>${__("Qty Pass")}</th>
									<th>${__("Rejected Qty")}</th>
									<th>${__("Rejection %")}</th>
									<th>${__("Quality Rating")}</th>
									<th class="grp">${__("Supplier Rating")}</th>
									<th class="text-center">${__("Grade")}</th>
								</tr>
							</thead>
							<tbody></tbody>
							<tfoot></tfoot>
						</table>
					</div>
				</div>
			</div>
		`).appendTo($(this.page.body));
	}

	make_filters() {
		const grade_options = [{ value: "", label: __("All") }].concat(
			[
				["A", "Excellent"],
				["B", "Very Good"],
				["C", "Good"],
				["D", "Need Improvements"],
				["E", "Need Actions"],
			].map(([g, l]) => ({ value: g, label: `${g} - ${__(l)}` }))
		);

		const defs = [
			{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company" },
			{
				fieldname: "fiscal_year",
				label: __("Fiscal Year"),
				fieldtype: "Link",
				options: "Fiscal Year",
				on_change: () => this.on_fiscal_year_change(),
			},
			{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date" },
			{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date" },
			{ fieldname: "supplier", label: __("Supplier"), fieldtype: "Link", options: "Supplier" },
			{
				fieldname: "supplier_group",
				label: __("Supplier Group"),
				fieldtype: "Link",
				options: "Supplier Group",
			},
			{ fieldname: "grade", label: __("Grade"), fieldtype: "Select", options: grade_options },
		];

		this.fields = {};
		const $spacer = this.$wrap.find(".spd-spacer");
		defs.forEach((def) => {
			const { on_change, ...df } = def;
			const $parent = $(`<div class="spd-f"></div>`).insertBefore($spacer);
			this.fields[df.fieldname] = frappe.ui.form.make_control({
				parent: $parent,
				df: {
					...df,
					change: () => {
						if (!this.ready) return;
						on_change ? on_change() : this.refresh();
					},
				},
				render_input: true,
			});
			this.fields[df.fieldname].refresh();
		});
	}

	bind_events() {
		const me = this;

		this.$wrap.on("click", ".spd-seg button", function () {
			me.$wrap.find(".spd-seg button").removeClass("on");
			$(this).addClass("on");
			me.view = $(this).attr("data-v");
			me.fetch();
		});

		this.$wrap.on("click", "tr.sup", function (e) {
			if ($(e.target).closest("a").length) return;
			const idx = $(this).attr("data-idx");
			const name = me.data.suppliers[idx].supplier;
			const open = !me.expanded.has(name);
			open ? me.expanded.add(name) : me.expanded.delete(name);
			$(this).toggleClass("open", open);
			me.$wrap.find(`tr.per[data-p="${idx}"]`).toggleClass("hide", !open);
			me.update_expand_button();
		});

		this.$wrap.on("click", ".spd-expand", () => {
			const rows = (this.data && this.data.suppliers) || [];
			const all_open = rows.length && rows.every((r) => this.expanded.has(r.supplier));
			rows.forEach((r) => (all_open ? this.expanded.delete(r.supplier) : this.expanded.add(r.supplier)));
			this.render_table();
		});
	}

	/* ----------------------------------------------------------------- filters */

	async set_defaults() {
		const company = frappe.defaults.get_user_default("Company") || frappe.defaults.get_default("company");
		let fiscal_year = null;
		let from_date = frappe.datetime.year_start();
		let to_date = frappe.datetime.year_end();

		const today = frappe.datetime.get_today();
		const fy = await frappe.db.get_list("Fiscal Year", {
			fields: ["name", "year_start_date", "year_end_date"],
			filters: { disabled: 0, year_start_date: ["<=", today], year_end_date: [">=", today] },
			order_by: "year_start_date desc",
			limit: 1,
		});
		if (fy && fy.length) {
			fiscal_year = fy[0].name;
			from_date = fy[0].year_start_date;
			to_date = fy[0].year_end_date;
		}

		await this.fields.company.set_value(company || "");
		await this.fields.fiscal_year.set_value(fiscal_year || "");
		await this.fields.from_date.set_value(from_date);
		await this.fields.to_date.set_value(to_date);

		this.ready = true;
		this.fetch();
	}

	async on_fiscal_year_change() {
		const fy = this.fields.fiscal_year.get_value();
		if (fy) {
			const r = await frappe.db.get_value("Fiscal Year", fy, ["year_start_date", "year_end_date"]);
			const v = (r && r.message) || {};
			this.ready = false;
			await this.fields.from_date.set_value(v.year_start_date);
			await this.fields.to_date.set_value(v.year_end_date);
			this.ready = true;
		}
		this.refresh();
	}

	get_filters() {
		const f = {};
		Object.keys(this.fields).forEach((k) => (f[k] = this.fields[k].get_value() || ""));
		f.view = this.view;
		if (!f.from_date || !f.to_date) {
			frappe.show_alert({ message: __("Please set From Date and To Date"), indicator: "orange" });
			return null;
		}
		if (f.from_date > f.to_date) {
			frappe.show_alert({ message: __("From Date cannot be after To Date"), indicator: "orange" });
			return null;
		}
		return f;
	}

	/* -------------------------------------------------------------------- data */

	fetch() {
		const filters = this.get_filters();
		if (!filters) return;
		this.$wrap.addClass("spd-loading");
		frappe
			.call({ method: `${SPD_METHOD}.get_dashboard_data`, args: { filters } })
			.then((r) => {
				this.data = r.message || { suppliers: [], cards: {}, grades: [] };
				this.render();
			})
			.always(() => this.$wrap.removeClass("spd-loading"));
	}

	export() {
		const filters = this.get_filters();
		if (!filters) return;
		open_url_post(`/api/method/${SPD_METHOD}.export_excel`, { filters: JSON.stringify(filters) });
	}

	/* ------------------------------------------------------------------ render */

	render() {
		this.render_cards();
		this.render_legend();
		this.render_table();
	}

	render_cards() {
		const c = this.data.cards || {};
		const sub = __("Across {0} scorecard periods, {1} suppliers", [c.periods || 0, c.suppliers || 0]);
		const cards = {
			delivery: [__("Avg Delivery Rating"), `${this.num(c.delivery_weight, 0)}% ${__("weight")}`, c.delivery],
			quality: [__("Avg Quality Rating"), `${this.num(c.quality_weight, 0)}% ${__("weight")}`, c.quality],
			score: [__("Avg Period Score"), __("Supplier rating"), c.score],
		};
		Object.entries(cards).forEach(([key, [title, hint, value]]) => {
			const $card = this.$wrap.find(`[data-card="${key}"]`);
			const has = c.periods > 0;
			$card.find(".title").text(title);
			$card.find(".hint").text(hint);
			$card.find(".v").text(has ? this.pct(value) : "-");
			$card.find(".s").text(sub);
			$card
				.find(".bar i")
				.css({ width: `${has ? Math.min(100, Math.max(0, value)) : 0}%`, background: this.bar_color(value) });
		});
	}

	render_legend() {
		const grades = this.data.grades || [];
		this.$wrap.find(".spd-legend").html(
			`<span class="spd-legend-title">${__("Supplier Grade")}</span>` +
				grades
					.map(
						(g) => `<span class="spd-legend-item">${this.grade_pill(g.grade)}
							<b>${__(g.label)}</b><span class="text-muted">${__(g.range)}</span></span>`
					)
					.join("")
		);
	}

	render_table() {
		const rows = this.data.suppliers || [];
		const month = this.data.view === "month";
		const esc = frappe.utils.escape_html;

		this.$wrap.find(".spd-first").text(month ? __("Supplier / Month") : __("Supplier / Quarter"));

		let html = "";
		rows.forEach((r, i) => {
			const open = this.expanded.has(r.supplier);
			const id = r.supplier !== r.supplier_name ? `<span class="spd-sub">${esc(r.supplier)}</span>` : "";
			html += `<tr class="sup ${open ? "open" : ""}" data-idx="${i}">
				<td><span class="caret">&#9656;</span>${esc(r.supplier_name)}${id}</td>${this.cells(r)}</tr>`;

			(r.children || []).forEach((c) => {
				const link = c.period
					? `<a class="pid" href="/app/supplier-scorecard-period/${encodeURIComponent(c.period)}">${esc(c.period)}</a>`
					: "";
				html += `<tr class="per ${open ? "" : "hide"}" data-p="${i}">
					<td>${esc(c.label)}${link}</td>${this.cells(c)}</tr>`;
			});
		});

		this.$wrap
			.find(".spd-table tbody")
			.html(
				html ||
					`<tr><td colspan="12" class="spd-empty">${__(
						"No Supplier Scorecard Period found for the selected filters"
					)}</td></tr>`
			);
		this.$wrap
			.find(".spd-table tfoot")
			.html(
				rows.length && this.data.total
					? `<tr><td>${__("Total ({0} suppliers)", [rows.length])}</td>${this.cells(this.data.total)}</tr>`
					: ""
			);
		this.$wrap.find(".spd-count").text(__("{0} Suppliers", [rows.length]));
		this.update_expand_button();
	}

	update_expand_button() {
		const rows = (this.data && this.data.suppliers) || [];
		const all_open = rows.length && rows.every((r) => this.expanded.has(r.supplier));
		this.$wrap.find(".spd-expand").text(all_open ? __("Collapse All") : __("Expand All"));
	}

	cells(t) {
		return `<td>${t.periods}</td>
			<td class="grp">${this.qty(t.ordered)}</td>
			<td>${this.qty(t.ontime)}</td>
			<td class="${this.rc(t.delivery)}">${this.pct(t.delivery)}</td>
			<td class="grp">${this.qty(t.received)}</td>
			<td>${this.qty(t.accepted)}</td>
			<td>${this.qty(t.rejected)}</td>
			<td>${this.pct(t.rejection)}</td>
			<td class="${this.rc(t.quality)}">${this.pct(t.quality)}</td>
			<td class="grp ${this.rc(t.score)}"><b>${this.pct(t.score)}</b></td>
			<td class="text-center">${this.grade_pill(t.grade)}</td>`;
	}

	/* ------------------------------------------------------------------ format */

	num(v, precision) {
		return format_number(flt(v), null, precision);
	}
	qty(v) {
		v = flt(v);
		return this.num(v, Number.isInteger(v) ? 0 : 2);
	}
	pct(v) {
		return `${this.num(v, 2)}%`;
	}
	rc(v) {
		v = flt(v);
		return v >= 80 ? "r-good" : v >= 60 ? "r-mid" : "r-bad";
	}
	bar_color(v) {
		v = flt(v);
		return v >= 80 ? "var(--green-500, #28a745)" : v >= 60 ? "var(--yellow-500, #e8a317)" : "var(--red-500, #e03636)";
	}
	grade_pill(g) {
		return g ? `<span class="spd-grade g${g}">${g}</span>` : "";
	}

	/* ------------------------------------------------------------------- style */

	add_style() {
		if (document.getElementById("spd-style")) return;
		const css = `
		.spd { padding: 4px 0 40px; font-size: var(--text-sm, 13px); }
		.spd-loading .spd-panel, .spd-loading .spd-cards { opacity: .55; pointer-events: none; }

		.spd-filters { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: var(--border-radius-md, 8px);
			padding: 12px 16px 4px; display: flex; flex-wrap: wrap; gap: 0 12px; align-items: flex-end; margin-bottom: 16px; }
		.spd-f { flex: 0 1 180px; min-width: 150px; }
		.spd-spacer { flex: 1; }
		.spd-view { margin-bottom: 12px; }
		.spd-view-label { font-size: var(--text-xs, 11px); color: var(--text-muted); margin-bottom: 4px; }
		.spd-seg { display: inline-flex; background: var(--control-bg); border-radius: 6px; padding: 2px; border: 1px solid var(--border-color); }
		.spd-seg button { border: 0; background: transparent; padding: 4px 14px; font-size: 12px; border-radius: 5px; color: var(--text-muted); font-weight: 500; }
		.spd-seg button.on { background: var(--card-bg); color: var(--text-color); box-shadow: 0 1px 2px rgba(0,0,0,.12); }

		.spd-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 12px; }
		.spd-card { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: var(--border-radius-md, 8px); padding: 16px 18px; }
		.spd-card .t { font-size: 12px; color: var(--text-muted); font-weight: 500; display: flex; justify-content: space-between; }
		.spd-card .v { font-size: 28px; font-weight: 600; margin-top: 8px; color: var(--text-color); }
		.spd-card .s { font-size: 11px; color: var(--text-muted); margin-top: 4px; }
		.spd-card .bar { height: 6px; background: var(--control-bg); border-radius: 3px; margin-top: 10px; overflow: hidden; }
		.spd-card .bar i { display: block; height: 100%; border-radius: 3px; width: 0; transition: width .3s; }

		.spd-legend { display: flex; flex-wrap: wrap; gap: 8px 18px; align-items: center; background: var(--card-bg);
			border: 1px solid var(--border-color); border-radius: var(--border-radius-md, 8px); padding: 10px 16px; margin-bottom: 16px; font-size: 12px; }
		.spd-legend:empty { display: none; }
		.spd-legend-title { font-weight: 600; color: var(--text-muted); text-transform: uppercase; font-size: 11px; letter-spacing: .04em; }
		.spd-legend-item { display: inline-flex; gap: 6px; align-items: center; }

		.spd-panel { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: var(--border-radius-md, 8px); }
		.spd-panel-head { display: flex; justify-content: space-between; align-items: center; padding: 14px 16px; }
		.spd-panel-head h3 { margin: 0; font-size: 13px; letter-spacing: .04em; color: var(--text-muted); font-weight: 600; text-transform: uppercase; }
		.spd-panel-head h3 span { text-transform: none; letter-spacing: 0; font-weight: 400; margin-left: 6px; }
		.spd-tbl-wrap { overflow-x: auto; border-top: 1px solid var(--border-color); }
		.spd-table { width: 100%; border-collapse: collapse; min-width: 1250px; }
		.spd-table th { background: var(--subtle-fg, #f8f9fa); font-size: 10.5px; text-transform: uppercase; letter-spacing: .03em;
			color: var(--text-muted); font-weight: 600; text-align: right; padding: 10px 12px; border-bottom: 1px solid var(--border-color); white-space: nowrap; }
		.spd-table th:first-child { text-align: left; position: sticky; left: 0; z-index: 2; border-right: 1px solid var(--border-color); min-width: 250px; }
		.spd-table td { padding: 9px 12px; border-bottom: 1px solid var(--border-color); text-align: right; white-space: nowrap; color: var(--text-color); }
		.spd-table td:first-child { text-align: left; position: sticky; left: 0; z-index: 1; background: inherit; border-right: 1px solid var(--border-color); }
		.spd-table td.grp, .spd-table th.grp { border-left: 1px solid var(--border-color); }
		.spd-table tr.sup { background: var(--card-bg); cursor: pointer; font-weight: 600; }
		.spd-table tr.sup:hover { background: var(--subtle-fg, #fafbfc); }
		.spd-table tr.per { background: var(--subtle-accent, #fbfcfd); }
		.spd-table tr.per td:first-child { padding-left: 38px; font-weight: 400; }
		.spd-table tr.per.hide { display: none; }
		.spd-table tfoot td { background: var(--subtle-fg, #f8f9fa); font-weight: 600; }
		.spd-table tfoot td:first-child { background: var(--subtle-fg, #f8f9fa); z-index: 2; }
		.spd-table .caret { display: inline-block; width: 16px; color: var(--text-muted); transition: transform .15s; }
		.spd-table tr.sup.open .caret { transform: rotate(90deg); }
		.spd .pid { display: block; font-size: 10.5px; color: var(--blue-500, #2490ef); margin-top: 1px; }
		.spd .spd-sub { display: block; font-size: 10.5px; color: var(--text-muted); font-weight: 400; margin-left: 16px; }
		.spd-empty { padding: 30px !important; text-align: center !important; color: var(--text-muted) !important; }

		.spd-grade { display: inline-block; min-width: 26px; text-align: center; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; }
		.spd-grade.gA { background: var(--bg-green, #e4f5e9); color: var(--text-on-green, #1e7b34); }
		.spd-grade.gB { background: var(--bg-blue, #e6f1fd); color: var(--text-on-blue, #1a6fc2); }
		.spd-grade.gC { background: var(--bg-yellow, #fff3dc); color: var(--text-on-yellow, #a66a00); }
		.spd-grade.gD { background: var(--bg-orange, #ffeedd); color: var(--text-on-orange, #c25a00); }
		.spd-grade.gE { background: var(--bg-red, #fde8e8); color: var(--text-on-red, #b52a2a); }
		.spd .r-good { color: var(--text-on-green, #1e7b34); }
		.spd .r-mid { color: var(--text-on-yellow, #a66a00); }
		.spd .r-bad { color: var(--text-on-red, #b52a2a); }

		@media (max-width: 991px) { .spd-cards { grid-template-columns: 1fr; } }
		`;
		$(`<style id="spd-style">${css}</style>`).appendTo("head");
	}
}
