// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt

frappe.pages["sales-team-dashboard"].on_page_load = function (wrapper) {
	frappe.sales_team_dashboard = new SalesTeamDashboard(wrapper);
};

class SalesTeamDashboard {
	constructor(wrapper) {
		this.wrapper = wrapper;
		$(wrapper).addClass("std-fullwidth");
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __("Sales Team Dashboard"),
			single_column: true,
		});
		this.page.set_secondary_action(__("Refresh"), () => this.refresh(), "refresh");
		this.work = { rows: [], doctypes: [], filter: "ALL", show_all: false };
		this.perf = { period: "week" };
		this.rank = { week: "cur", doc: "ALL", metric: "docs", show_all: false };
		this.make_layout();
		this.bind_events();
		this.refresh();
	}

	make_layout() {
		this.$body = $(`
			<div class="std-wrap">
				<div class="std-top">
					<div>
						<h1>${__("Sales Team Dashboard")}</h1>
						<small class="std-mut">${frappe.utils.escape_html(frappe.session.user_fullname || frappe.session.user)}</small>
					</div>
				</div>

				<section class="std-card" data-section="work">
					<div class="std-hd"><h2>${__("1. My work to do")}</h2><small class="std-mut std-work-summary"></small></div>
					<div class="std-seg std-work-filter"></div>
					<div class="std-section-body"></div>
					<p style="margin:12px 0 0"><button class="std-btn std-work-all" hidden></button></p>
				</section>

				<section class="std-card" data-section="performance">
					<div class="std-hd"><h2>${__("2. My performance")}</h2><div class="std-seg std-perf-seg"></div></div>
					<div class="std-section-body"></div>
				</section>

				<section class="std-card" data-section="ranking">
					<div class="std-hd"><h2>${__("3. Ranking")}</h2><div class="std-seg std-rank-week"></div></div>
					<div class="std-seg std-rank-doc" style="margin-bottom:8px"></div>
					<div class="std-seg std-rank-metric" style="margin-bottom:14px"></div>
					<div class="std-section-body"></div>
					<p style="margin:12px 0 0"><button class="std-btn std-rank-all" hidden></button></p>
				</section>
			</div>
		`).appendTo(this.page.main);
	}

	section(name) {
		return this.$body.find(`[data-section="${name}"] .std-section-body`);
	}

	refresh() {
		this.render_work();
		this.render_performance();
		this.render_ranking();
	}

	bind_events() {
		const $w = this.$body.find('[data-section="work"]');
		$w.on("click", ".std-work-filter button", (e) => {
			this.work.filter = $(e.currentTarget).attr("data-filter");
			this.work.show_all = false;
			this.draw_work();
		});
		$w.on("click", ".std-work-all", () => {
			this.work.show_all = !this.work.show_all;
			this.draw_work();
		});
		this.$body.find('[data-section="performance"]').on("click", ".std-perf-seg button", (e) => {
			this.perf.period = $(e.currentTarget).attr("data-period");
			this.render_performance();
		});
		const $r = this.$body.find('[data-section="ranking"]');
		$r.on("click", "[data-rank-key]", (e) => {
			const $t = $(e.currentTarget);
			this.rank[$t.attr("data-rank-key")] = $t.attr("data-rank-val");
			this.rank.show_all = false;
			this.render_ranking();
		});
		$r.on("click", ".std-rank-all", () => {
			this.rank.show_all = !this.rank.show_all;
			this.draw_ranking(this.rank.data);
		});
		$w.on("click", "[data-open]", (e) => {
			e.preventDefault();
			const $t = $(e.currentTarget);
			frappe.set_route("Form", $t.attr("data-doctype"), $t.attr("data-open"));
		});
	}

	// ---------- 1. My work to do ----------
	render_work() {
		this.section("work").html(`<div class="std-na">${__("Loading...")}</div>`);
		frappe
			.xcall("generate_item.generate_item.page.sales_team_dashboard.sales_team_dashboard.get_my_work_to_do")
			.then((r) => {
				this.work.rows = r.rows || [];
				this.work.doctypes = r.doctypes || [];
				this.work.overdue_days = r.overdue_days;
				this.draw_work();
			});
	}

	draw_work() {
		const esc = frappe.utils.escape_html;
		const $sec = this.$body.find('[data-section="work"]');
		const { rows, doctypes, filter, show_all } = this.work;
		const LIMIT = 5;

		// summary
		const overdue = rows.filter((r) => r.overdue).length;
		$sec.find(".std-work-summary").html(
			`<b>${rows.length}</b> ${__("draft documents need your action")}` +
				(overdue ? `, <b style="color:#c62828">${overdue} ${__("overdue")}</b>` : "")
		);

		// doctype filter chips with counts
		const count = (dt) => rows.filter((r) => r.doctype === dt).length;
		$sec.find(".std-work-filter").html(
			[["ALL", __("All"), rows.length], ...doctypes.map((d) => [d.doctype, d.short, count(d.doctype)])]
				.map(
					([v, l, c]) =>
						`<button class="${v === filter ? "on" : ""}" data-filter="${esc(v)}" title="${esc(v === "ALL" ? __("All documents") : __(v))}">${esc(l)}<span class="std-cnt">${c}</span></button>`
				)
				.join("")
		);

		const list = filter === "ALL" ? rows : rows.filter((r) => r.doctype === filter);
		const shown = show_all ? list : list.slice(0, LIMIT);

		const $all = $sec.find(".std-work-all");
		$all.prop("hidden", list.length <= LIMIT);
		$all.text(show_all ? __("Show less") : __("View all {0}", [list.length]));

		if (!list.length) {
			this.section("work").html(`<div class="std-na">${__("All caught up. No draft documents.")}</div>`);
			return;
		}

		const waiting = (a) => (a ? `${a} ${a > 1 ? __("days") : __("day")}` : __("Today"));
		this.section("work").html(`
			<div class="std-sw"><table class="std-tbl">
				<tr><th>${__("Document")}</th><th>${__("Status")}</th><th>${__("For")}</th><th>${__("Date")}</th><th>${__("Waiting")}</th><th></th></tr>
				${shown
					.map(
						(r) => `<tr>
					<td><b>${esc(r.short)}</b> <a class="std-l" href="/app/${frappe.router.slug(r.doctype)}/${encodeURIComponent(r.name)}" data-doctype="${esc(r.doctype)}" data-open="${esc(r.name)}">${esc(r.name)}</a>
						${r.branch ? `<small>${esc(r.branch)}</small>` : ""}</td>
					<td class="std-nw"><span class="std-b ${r.status === "Draft" ? "g" : "w"}">${esc(__(r.status))}</span></td>
					<td>${esc(r.party || "-")}${r.ref ? `<small>${esc(r.ref)}</small>` : ""}</td>
					<td class="std-nw">${r.date ? frappe.datetime.str_to_user(r.date) : "-"}</td>
					<td class="std-nw">${waiting(r.age)}${r.overdue ? `<span class="std-b rd">${__("Overdue")}</span>` : ""}</td>
					<td class="std-nw"><button class="std-btn" data-doctype="${esc(r.doctype)}" data-open="${esc(r.name)}">${__("Open")}</button></td>
				</tr>`
					)
					.join("")}
			</table></div>`);
	}

	// Placeholders — to be implemented as per requirements

	// ---------- 2. My performance (Sales Order) ----------
	render_performance() {
		const period = this.perf.period;
		this.$body.find(".std-perf-seg").html(
			[["day", __("Today")], ["week", __("This week")]]
				.map(([v, l]) => `<button class="${v === period ? "on" : ""}" data-period="${v}">${l}</button>`)
				.join("")
		);
		this.section("performance").html(`<div class="std-na">${__("Loading...")}</div>`);
		frappe
			.xcall("generate_item.generate_item.page.sales_team_dashboard.sales_team_dashboard.get_my_performance", { period })
			.then((r) => {
				if (r.period === this.perf.period) this.draw_performance(r);
			});
	}

	draw_performance(r) {
		const a = r.current, b = r.previous;
		const vs = r.period === "day" ? __("yesterday") : __("last week");
		const money = (v) => format_currency(v, r.currency, 0);
		const delta = (x, y, as_pct) => {
			const d = x - y;
			if (!d) return `<span>● ${__("same as")} ${vs}</span>`;
			const up = d > 0;
			const t = as_pct ? (y ? Math.abs((d / y) * 100).toFixed(0) + "%" : "–") : Math.abs(d).toLocaleString();
			return `<span class="${up ? "std-up" : "std-dn"}">${up ? "▲ +" : "▼ −"}${t}</span> ${__("vs")} ${vs}`;
		};
		const tile = (label, val, sub) => `<div class="std-k"><span>${label}</span><b>${val}</b><small>${sub}</small></div>`;
		const pct = a.created ? Math.round((a.completed / a.created) * 100) : 0;

		let days = "";
		if (r.daily.length) {
			const mx = Math.max(1, ...r.daily.map((d) => d.count));
			const today = frappe.datetime.get_today();
			const label = (d) => moment(d.date).format("ddd");
			days = `<div class="std-days">${r.daily
				.map(
					(d) => `<div class="${d.future ? "fut" : ""} ${d.date === today ? "today" : ""}" title="${frappe.datetime.str_to_user(d.date)}: ${d.count}">
						<b>${d.count || ""}</b><i style="height:${(d.count / mx) * 70}px"></i>${label(d)}</div>`
				)
				.join("")}</div>`;
		}

		const range =
			r.from_date === r.to_date
				? frappe.datetime.str_to_user(r.from_date)
				: `${frappe.datetime.str_to_user(r.from_date)} – ${frappe.datetime.str_to_user(r.to_date)}`;

		this.section("performance").html(`
			<div class="std-grid">
				${tile(__("Documents created"), a.created, delta(a.created, b.created))}
				${tile(__("Completed"), a.completed, delta(a.completed, b.completed))}
				${tile(__("Lines handled"), a.lines, delta(a.lines, b.lines))}
				${tile(__("Document value"), money(a.value), delta(a.value, b.value, true))}
			</div>
			<div class="std-bar"><i style="width:${pct}%"></i></div>
			<small class="std-mut">${__("{0} of {1} Sales Orders completed ({2}%)", [a.completed, a.created, pct])} · ${range}</small>
			${days}
		`);
	}

	// ---------- 3. Ranking ----------
	render_ranking() {
		const R = this.rank;
		const $sec = this.$body.find('[data-section="ranking"]');
		const seg = (key, items) =>
			items
				.map(([v, l]) => `<button class="${R[key] === v ? "on" : ""}" data-rank-key="${key}" data-rank-val="${v}">${l}</button>`)
				.join("");
		$sec.find(".std-rank-week").html(seg("week", [["cur", __("This week")], ["prev", __("Last week")]]));
		$sec.find(".std-rank-doc").html(
			seg("doc", [["ALL", __("All documents")], ["SO", "SO"], ["MR", "MR"], ["DN", "DN"], ["OMR", "OMR"], ["BMR", "BMR"]])
		);
		$sec.find(".std-rank-metric").html(seg("metric", [["docs", __("Documents")], ["lines", __("Lines")], ["value", __("Value")]]));
		$sec.find(".std-rank-all").prop("hidden", true);
		this.section("ranking").html(`<div class="std-na">${__("Loading...")}</div>`);

		const req = { week: R.week, doc: R.doc, metric: R.metric };
		frappe
			.xcall("generate_item.generate_item.page.sales_team_dashboard.sales_team_dashboard.get_ranking", req)
			.then((r) => {
				if (r.week !== R.week || r.doc !== R.doc || r.metric !== R.metric) return;
				R.data = r;
				this.draw_ranking(r);
			});
	}

	draw_ranking(r) {
		const esc = frappe.utils.escape_html;
		const $sec = this.$body.find('[data-section="ranking"]');
		const $all = $sec.find(".std-rank-all");
		const LIMIT = 10;
		const range = `${frappe.datetime.str_to_user(r.from_date)} – ${frappe.datetime.str_to_user(r.to_date)}`;

		if (r.not_applicable) {
			$all.prop("hidden", true);
			this.section("ranking").html(
				`<div class="std-na"><b>N/A</b><br>${__("{0} has no value field, so no value ranking is shown.", [r.doc])}</div>`
			);
			return;
		}
		const rows = r.rows || [];
		if (!rows.length) {
			$all.prop("hidden", true);
			this.section("ranking").html(`<div class="std-na">${__("No one to rank for this week.")}</div>`);
			return;
		}

		const fmt = (v) => (r.metric === "value" ? format_currency(v, r.currency, 0) : (v || 0).toLocaleString());
		const unit = { docs: __("documents"), lines: __("lines"), value: "" }[r.metric];
		const col = r.doc === "ALL" && r.metric === "value"
			? __("Sales Order value")
			: r.doc === "ALL" ? __("Score") : { docs: __("Documents"), lines: __("Lines"), value: __("Value") }[r.metric];

		// hero
		const mi = rows.findIndex((x) => x.user === r.me);
		let hero;
		if (mi < 0) {
			const why = r.doc === "OMR" || r.doc === "BMR"
				? __("Only users who created a Sales Order this week are ranked for {0}.", [r.doc])
				: __("Only users with the {0} role are ranked.", [r.role]);
			hero = `<div class="std-hero"><div><b style="font-size:20px">${__("You are not in this ranking")}</b><br><span>${why}</span></div></div>`;
		} else {
			const me = rows[mi];
			const fi = rows.findIndex((x) => x.rank === me.rank);
			const up = fi > 0 ? rows[fi - 1] : null;
			let msg;
			if (!up) msg = __("You are leading. Keep it up!");
			else if (r.higher_better) msg = __("{0} {1} more to reach {2}", [fmt(up.score - me.score), unit, `<b>#${up.rank}</b>`]);
			else msg = __("{0} fewer {1} to reach {2}", [fmt(me.score - up.score), r.doc, `<b>#${up.rank}</b>`]);
			hero = `<div class="std-hero"><b class="std-hero-rank">#${me.rank}</b><div><b style="font-size:20px">${__("of {0} users", [rows.length])}</b><br><span>${msg}</span></div></div>`;
		}

		// table rows: top N, plus me if outside
		let shown = this.rank.show_all ? rows : rows.slice(0, LIMIT);
		const sep = !this.rank.show_all && mi >= LIMIT;
		if (sep) shown = [...shown, { sep: true }, rows[mi]];
		$all.prop("hidden", rows.length <= LIMIT);
		$all.text(this.rank.show_all ? __("Show less") : __("View all {0}", [rows.length]));

		const keys = r.doc === "ALL" ? r.keys : [];
		const head = `<tr><th>${__("Rank")}</th><th>${__("User")}</th>${keys
			.map((k) => `<th class="std-r" title="${r.signs[k] < 0 ? __("Fewer is better") : __("More is better")}">${k}${r.signs[k] < 0 && r.metric !== "value" ? " (−)" : ""}</th>`)
			.join("")}<th class="std-r">${col}</th></tr>`;
		const body = shown
			.map((x) =>
				x.sep
					? `<tr><td colspan="${3 + keys.length}" class="std-mut" style="text-align:center">⋮</td></tr>`
					: `<tr class="${x.user === r.me ? "std-me" : ""}"><td>${x.rank}</td><td>${x.user === r.me ? `<b>${__("You")}</b> <small>${esc(x.full_name)}</small>` : esc(x.full_name)}</td>${keys
							.map((k) => `<td class="std-r">${fmt(x.breakdown[k])}</td>`)
							.join("")}<td class="std-r"><b>${fmt(x.score)}</b></td></tr>`
			)
			.join("");

		let note = r.higher_better ? __("More is better.") : __("Fewer is better.");
		if (r.doc === "ALL" && r.metric !== "value") note = __("Score = SO + MR + DN − OMR − BMR.");
		if (r.doc === "ALL" && r.metric === "value") note = __("Ranked by Sales Order net value (excl. tax).");

		this.section("ranking").html(`
			${hero}
			<div class="std-sw"><table class="std-tbl">${head}${body}</table></div>
			<small class="std-mut">${note} ${__("Ties share the same rank.")} · ${range}</small>
		`);
	}
}
