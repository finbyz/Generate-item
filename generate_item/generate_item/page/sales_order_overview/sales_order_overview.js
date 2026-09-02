frappe.pages['sales-order-overview'].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Sales Order Overview',
		single_column: true,
	});

	new SalesOrderOverview(page);
};

class SalesOrderOverview {
	constructor(page) {
		this.page = page;
		this.$body = $(page.body);
		this.state = {
			user: 'all',
			period: 'monthly',
			from_date: null,
			to_date: null,
		};
		this.is_manager = true;

		this.inject_styles();
		this.render_shell();
		this.bind_static_events();
		this.load_filter_options();
	}

	// ------------------------------------------------------------------
	// One-time setup
	// ------------------------------------------------------------------
	inject_styles() {
		if (document.getElementById('soo-styles')) return;
		const css = `
			.soo-wrap{max-width:1320px;margin:0 auto;padding:6px 2px 30px;}
			.soo-filterbar{background:var(--card-bg,#fff);border-radius:14px;
				box-shadow:var(--shadow-base,0 1px 2px rgba(0,0,0,.06));padding:10px 14px;
				display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:18px;}
			.soo-pill{display:flex;align-items:center;gap:8px;background:var(--control-bg,#f4f5fa);
				border-radius:10px;padding:7px 12px;font-size:13px;font-weight:600;}
			.soo-pill select,.soo-pill input{border:none;background:transparent;outline:none;
				font-size:13px;font-weight:600;color:var(--text-color);cursor:pointer;}
			.soo-pill input[type=date]{width:130px;font-weight:500;cursor:default;}
			.soo-pill input[disabled]{opacity:.55;cursor:not-allowed;}
			.soo-divider{width:1px;height:20px;background:var(--border-color);}
			.soo-to{font-size:12px;color:var(--text-muted);}
			.soo-spacer{flex:1;}
			.soo-iconbtn{width:34px;height:34px;border-radius:9px;background:var(--control-bg,#f4f5fa);
				border:none;display:flex;align-items:center;justify-content:center;cursor:pointer;}
			.soo-row1{display:grid;grid-template-columns:1.15fr 1fr .95fr;gap:14px;margin-bottom:14px;}
			@media(max-width:980px){.soo-row1{grid-template-columns:1fr;}}
			.soo-card{background:var(--card-bg,#fff);border-radius:16px;
				box-shadow:var(--shadow-base,0 1px 2px rgba(0,0,0,.06));padding:20px;
				transition:transform .12s ease;}
			.soo-card-static{cursor:default;}
			.soo-clickable{cursor:pointer;border-radius:8px;transition:background .12s ease;}
			.soo-clickable:hover{background:rgba(36,144,239,.08);}
			.soo-stat.soo-clickable{padding:4px 8px;margin:-4px -8px;}
			.soo-footlink.soo-clickable{display:inline-block;padding:2px 6px;margin:14px -6px 0;}
			.soo-hero.soo-clickable:hover{background:#1b1e2b;}
			.soo-eyebrow{display:flex;align-items:center;gap:7px;font-size:11.5px;font-weight:700;
				letter-spacing:.04em;color:var(--text-muted);text-transform:uppercase;}
			.soo-eyebrow-ic{width:24px;height:24px;border-radius:7px;display:flex;align-items:center;
				justify-content:center;font-size:12px;}
			.soo-ic-blue{background:#eaf4fe;color:#1668b0;}
			.soo-ic-green{background:#e7f7f0;color:#22a06b;}
			.soo-big{font-size:32px;font-weight:800;margin-top:12px;display:flex;align-items:baseline;gap:5px;}
			.soo-big .unit{font-size:17px;font-weight:700;color:var(--text-muted);}
			.soo-statrow{margin-top:14px;padding-top:12px;border-top:1px solid var(--border-color);
				display:flex;gap:22px;}
			.soo-stat-label{font-size:10.5px;color:var(--text-muted);font-weight:700;
				text-transform:uppercase;letter-spacing:.03em;}
			.soo-stat-val{font-size:17px;font-weight:700;margin-top:2px;}
			.soo-amber{color:#e08a0f;} .soo-red{color:#e0473f;} .soo-green{color:#22a06b;}
			.soo-bar{margin-top:14px;height:6px;border-radius:6px;background:var(--control-bg,#f4f5fa);
				overflow:hidden;display:flex;}
			.soo-bar span{height:100%;}
			.soo-footlink{margin-top:14px;font-size:11.5px;font-weight:600;color:#1668b0;}
			.soo-hero{background:#14161f;color:#fff;border-radius:16px;padding:20px 20px 18px;
				cursor:pointer;display:flex;flex-direction:column;justify-content:space-between;}
			.soo-hero-eyebrow{font-size:11.5px;font-weight:700;letter-spacing:.04em;
				text-transform:uppercase;color:rgba(255,255,255,.6);}
			.soo-hero-numrow{display:flex;align-items:center;gap:8px;margin-top:12px;}
			.soo-hero-num{font-size:34px;font-weight:800;}
			.soo-hero-badge{background:rgba(255,255,255,.12);font-size:11px;font-weight:700;
				padding:3px 9px;border-radius:20px;}
			.soo-hero-badge.down{color:#ff9b93;}
			.soo-hero-sub{margin-top:6px;font-size:12px;color:rgba(255,255,255,.55);}
			.soo-hero-foot{margin-top:16px;padding-top:12px;border-top:1px solid rgba(255,255,255,.12);
				font-size:11.5px;color:rgba(255,255,255,.6);}
			.soo-pipe-head{font-size:11.5px;font-weight:700;letter-spacing:.03em;color:var(--text-muted);
				text-transform:uppercase;margin:4px 0 8px 2px;}
			.soo-pipe{display:flex;gap:14px;flex-wrap:wrap;}
			.soo-plcard{flex:1;min-width:180px;background:var(--card-bg,#fff);
				box-shadow:var(--shadow-base,0 1px 2px rgba(0,0,0,.06));padding:20px 16px;text-align:center;
				border-radius:16px;cursor:pointer;position:relative;transition:transform .12s ease;}
			.soo-plcard:hover{transform:translateY(-2px);}
			.soo-plicon{width:40px;height:40px;border-radius:12px;margin:0 auto 12px;
				display:flex;align-items:center;justify-content:center;font-size:17px;}
			.soo-plnum{font-size:23px;font-weight:800;}
			.soo-pllabel{margin-top:6px;font-size:11px;font-weight:700;text-transform:uppercase;
				letter-spacing:.03em;}
			.soo-plsub{margin-top:2px;font-size:11px;color:var(--text-muted);}
			.soo-flag{position:absolute;top:10px;right:10px;font-size:9px;font-weight:800;
				letter-spacing:.03em;background:#fceae9;color:#e0473f;padding:2px 7px;border-radius:20px;}
			.soo-loading{opacity:.45;pointer-events:none;}
		`;
		const style = document.createElement('style');
		style.id = 'soo-styles';
		style.textContent = css;
		document.head.appendChild(style);
	}

	render_shell() {
		this.$body.html(`
			<div class="soo-wrap">
				<div class="soo-filterbar">
					<div class="soo-pill"><span>👤</span>
						<select class="soo-user-filter"><option value="all">All Users</option></select>
					</div>
					<div class="soo-divider"></div>
					<div class="soo-pill"><span>📅</span>
						<select class="soo-period-filter">
							<option value="monthly" selected>Monthly</option>
							<option value="quarterly">Quarterly</option>
							<option value="half_yearly">Half-Yearly</option>
							<option value="yearly">Yearly</option>
							<option value="all">All</option>
							<option value="custom">Custom</option>
						</select>
					</div>
					<div class="soo-divider"></div>
					<div class="soo-pill">
						<input type="date" class="soo-from-date" disabled>
						<span class="soo-to">to</span>
						<input type="date" class="soo-to-date" disabled>
					</div>
					<div class="soo-spacer"></div>
					<button class="soo-iconbtn soo-refresh" title="Refresh">⟳</button>
				</div>

				<div class="soo-row1">
					<div class="soo-card">
						<div class="soo-eyebrow"><span class="soo-eyebrow-ic soo-ic-blue">🧾</span>No. of Sales Orders</div>
						<div class="soo-big soo-clickable" data-drill="orders_all"><span class="soo-val-count">0</span></div>
						<div class="soo-statrow">
							<div class="soo-stat soo-clickable" data-drill="orders_open">
								<div class="soo-stat-label">Open</div><div class="soo-stat-val soo-amber soo-val-open">0</div>
							</div>
							<div class="soo-stat soo-clickable" data-drill="orders_overdue">
								<div class="soo-stat-label">Overdue</div><div class="soo-stat-val soo-red soo-val-overdue">0</div>
							</div>
							<div class="soo-stat soo-clickable" data-drill="orders_closed">
								<div class="soo-stat-label">Closed</div><div class="soo-stat-val soo-green soo-val-closed">0</div>
							</div>
						</div>
						<div class="soo-bar"><span class="soo-bar-closed" style="background:#22a06b;"></span><span class="soo-bar-open" style="background:#e08a0f;"></span><span class="soo-bar-overdue" style="background:#e0473f;"></span></div>
						<div class="soo-footlink soo-clickable" data-drill="orders_all">View sales order list →</div>
					</div>

					<div class="soo-card soo-card-static">
						<div class="soo-eyebrow"><span class="soo-eyebrow-ic soo-ic-green">₹</span>Total Value of Sales Orders</div>
						<div class="soo-big"><span class="soo-val-value">₹0</span><span class="unit soo-val-unit">L</span></div>
						<div class="soo-statrow">
							<div><div class="soo-stat-label">Total Lines</div><div class="soo-stat-val soo-val-lines">0</div></div>
							<div><div class="soo-stat-label">Avg / Order</div><div class="soo-stat-val soo-val-avgorder">₹0</div></div>
							<div><div class="soo-stat-label">Lines / Order</div><div class="soo-stat-val soo-val-avglines">0</div></div>
						</div>
					</div>

					<div class="soo-hero soo-clickable" data-drill="changes">
						<div>
							<div class="soo-hero-eyebrow">✎ Change Request Rate</div>
							<div class="soo-hero-numrow">
								<div class="soo-hero-num soo-val-rate">0%</div>
								<div class="soo-hero-badge soo-val-rate-badge">—</div>
							</div>
							<div class="soo-hero-sub">Amended orders vs total orders</div>
						</div>
						<div class="soo-hero-foot">This period: <b class="soo-val-change-mini">0</b> change requests logged</div>
					</div>
				</div>

				<div class="soo-pipe-head">Order lines, changes &amp; status</div>
				<div class="soo-pipe">
					<div class="soo-plcard soo-clickable" data-drill="lines">
						<div class="soo-plicon soo-ic-blue">📋</div>
						<div class="soo-plnum soo-pl-lines">0</div>
						<div class="soo-pllabel">Order Lines</div>
						<div class="soo-plsub">across all sales orders</div>
					</div>
					<div class="soo-plcard soo-clickable" data-drill="changes">
						<div class="soo-plicon" style="background:#eeecfe;color:#6a5bf5;">✎</div>
						<div class="soo-plnum soo-pl-change">0</div>
						<div class="soo-pllabel">Change Requests</div>
						<div class="soo-plsub">orders amended</div>
					</div>
					<div class="soo-plcard soo-clickable" data-drill="orders_open">
						<div class="soo-plicon" style="background:#fdf2e0;color:#e08a0f;">⏳</div>
						<div class="soo-plnum soo-pl-open">0</div>
						<div class="soo-pllabel">Open Orders</div>
						<div class="soo-plsub">not fully delivered / billed</div>
					</div>
					<div class="soo-plcard soo-clickable" data-drill="orders_overdue">
						<span class="soo-flag">ATTN</span>
						<div class="soo-plicon" style="background:#fceae9;color:#e0473f;">⚠</div>
						<div class="soo-plnum soo-pl-overdue">0</div>
						<div class="soo-pllabel">Overdue Orders</div>
						<div class="soo-plsub">past delivery date</div>
					</div>
				</div>
			</div>
		`);

		this.$user = this.$body.find('.soo-user-filter');
		this.$period = this.$body.find('.soo-period-filter');
		this.$from = this.$body.find('.soo-from-date');
		this.$to = this.$body.find('.soo-to-date');
	}

	bind_static_events() {
		this.$period.on('change', () => {
			this.state.period = this.$period.val();
			const is_custom = this.state.period === 'custom';
			this.$from.prop('disabled', !is_custom);
			this.$to.prop('disabled', !is_custom);
			if (is_custom) {
				// give sensible defaults the first time custom is chosen
				if (!this.$from.val()) this.$from.val(frappe.datetime.month_start());
				if (!this.$to.val()) this.$to.val(frappe.datetime.now_date());
				frappe.show_alert({ message: __('Pick a custom date range'), indicator: 'blue' });
				return; // wait for the user to actually pick dates before refreshing
			}
			this.refresh();
		});

		this.$user.on('change', () => {
			this.state.user = this.$user.val();
			this.refresh();
		});

		this.$from.on('change', () => this.maybe_refresh_custom());
		this.$to.on('change', () => this.maybe_refresh_custom());

		this.$body.find('.soo-refresh').on('click', (e) => {
			$(e.currentTarget).css('transform', 'rotate(360deg)');
			setTimeout(() => $(e.currentTarget).css('transform', ''), 400);
			this.refresh();
		});

		this.$body.on('click', '[data-drill]', (e) => {
			e.stopPropagation();
			this.open_drill_dialog($(e.currentTarget).data('drill'));
		});

		this.page.set_secondary_action(__('Refresh'), () => this.refresh(), 'refresh');
	}

	maybe_refresh_custom() {
		if (this.state.period !== 'custom') return;
		const from_date = this.$from.val();
		const to_date = this.$to.val();
		if (!from_date || !to_date) return;
		if (from_date > to_date) {
			frappe.show_alert({ message: __('From Date cannot be after To Date'), indicator: 'red' });
			return;
		}
		this.state.from_date = from_date;
		this.state.to_date = to_date;
		this.refresh();
	}

	// ------------------------------------------------------------------
	// Data loading
	// ------------------------------------------------------------------
	load_filter_options() {
		frappe.call({
			method:
				'generate_item.generate_item.page.sales_order_overview.sales_order_overview.get_filter_options',
			callback: (r) => {
				const res = r.message || {};
				this.is_manager = !!res.is_manager;

				this.$user.empty();
				if (this.is_manager) {
					this.$user.append(`<option value="all">All Users</option>`);
				}
				(res.options || []).forEach((o) => {
					this.$user.append(`<option value="${frappe.utils.escape_html(o.value)}">${frappe.utils.escape_html(o.label)}</option>`);
				});

				if (!this.is_manager) {
					this.$user.prop('disabled', true);
					if (res.own_sales_person) {
						this.$user.val(res.own_sales_person);
						this.state.user = res.own_sales_person;
					}
				}

				this.refresh();
			},
		});
	}

	refresh() {
		this.$body.addClass('soo-loading');
		frappe.call({
			method:
				'generate_item.generate_item.page.sales_order_overview.sales_order_overview.get_dashboard_data',
			args: {
				user: this.state.user,
				period: this.state.period,
				from_date: this.state.from_date,
				to_date: this.state.to_date,
			},
			callback: (r) => {
				this.$body.removeClass('soo-loading');
				if (!r.message) return;
				this.last_response = r.message;
				this.render_data(r.message);
			},
			error: () => this.$body.removeClass('soo-loading'),
		});
	}

	// ------------------------------------------------------------------
	// Rendering
	// ------------------------------------------------------------------
	render_data(res) {
		const cur = res.current;
		const prev = res.previous;

		// reflect the server-resolved range in the (possibly disabled) date inputs
		if (this.state.period !== 'custom') {
			this.$from.val(res.start);
			this.$to.val(res.end);
		}

		const closed = cur.closed;
		const openOnly = Math.max(cur.open - cur.overdue, 0);
		const total = cur.count || 1;

		this.$body.find('.soo-val-count').text(cur.count);
		this.$body.find('.soo-val-open').text(cur.open);
		this.$body.find('.soo-val-overdue').text(cur.overdue);
		this.$body.find('.soo-val-closed').text(closed);

		this.$body.find('.soo-bar-closed').css('width', (closed / total * 100) + '%');
		this.$body.find('.soo-bar-open').css('width', (openOnly / total * 100) + '%');
		this.$body.find('.soo-bar-overdue').css('width', (cur.overdue / total * 100) + '%');

		const valFmt = this.fmtCr(cur.value);
		this.$body.find('.soo-val-value').text(valFmt.num);
		this.$body.find('.soo-val-unit').text(valFmt.unit);
		this.$body.find('.soo-val-lines').text(cur.lines);
		this.$body.find('.soo-val-avgorder').text(this.fmtCompact(cur.value / (cur.count || 1)));
		this.$body.find('.soo-val-avglines').text((cur.lines / (cur.count || 1)).toFixed(1));

		this.$body.find('.soo-val-rate').text(cur.rate.toFixed ? cur.rate.toFixed(1) + '%' : cur.rate + '%');
		this.$body.find('.soo-val-change-mini').text(cur.change);

		const $badge = this.$body.find('.soo-val-rate-badge');
		if (prev) {
			const diff = cur.rate - prev.rate;
			$badge.text((diff >= 0 ? '▲ ' : '▼ ') + Math.abs(diff).toFixed(1) + '%');
			$badge.toggleClass('down', diff < 0);
		} else {
			$badge.text('—').removeClass('down');
		}

		this.$body.find('.soo-pl-lines').text(cur.lines);
		this.$body.find('.soo-pl-change').text(cur.change);
		this.$body.find('.soo-pl-open').text(cur.open);
		this.$body.find('.soo-pl-overdue').text(cur.overdue);
	}

	fmtCr(v) {
		if (v >= 10000000) return { num: '₹' + (v / 10000000).toFixed(2), unit: 'Cr' };
		return { num: '₹' + (v / 100000).toFixed(1), unit: 'L' };
	}
	fmtCompact(v) {
		if (v >= 100000) return '₹' + (v / 100000).toFixed(1) + 'L';
		return '₹' + (v / 1000).toFixed(1) + 'K';
	}

	// ------------------------------------------------------------------
	// Drill-down dialog: preview the actual filtered records (paginated),
	// then let the user jump into the full List View with those filters.
	// ------------------------------------------------------------------
	open_drill_dialog(kind) {
		if (!this.last_response) return;

		const titles = {
			orders_all: __('All Sales Orders'),
			orders_open: __('Open Sales Orders'),
			orders_overdue: __('Overdue Sales Orders'),
			orders_closed: __('Closed Sales Orders'),
			lines: __('Order Lines'),
			changes: __('Change Requests'),
		};

		const dialog = new frappe.ui.Dialog({
			title: titles[kind] || __('Details'),
			size: 'large',
			fields: [{ fieldtype: 'HTML', fieldname: 'preview_html' }],
			primary_action_label: __('Open in List View'),
			primary_action: () => {
				if (!dialog._list_doctype) return;
				frappe.set_route('List', dialog._list_doctype, dialog._list_filters || {});
				dialog.hide();
			},
		});

		dialog._kind = kind;
		dialog._page = 0;
		dialog._page_length = 10;

		dialog.$wrapper.on('click', '.soo-page-prev', () => {
			if (dialog._page > 0) {
				dialog._page -= 1;
				this.load_drill_page(dialog);
			}
		});
		dialog.$wrapper.on('click', '.soo-page-next', () => {
			const max_page = Math.max(Math.ceil((dialog._total || 0) / dialog._page_length) - 1, 0);
			if (dialog._page < max_page) {
				dialog._page += 1;
				this.load_drill_page(dialog);
			}
		});

		dialog.show();
		this.load_drill_page(dialog);
	}

	load_drill_page(dialog) {
		dialog.set_value(
			'preview_html',
			`<div class="text-muted" style="padding:24px 0;text-align:center;">${__('Loading…')}</div>`
		);
		dialog.get_primary_btn().prop('disabled', true);

		frappe.call({
			method:
				'generate_item.generate_item.page.sales_order_overview.sales_order_overview.get_drilldown_data',
			args: {
				kind: dialog._kind,
				user: this.state.user,
				period: this.state.period,
				from_date: this.state.from_date,
				to_date: this.state.to_date,
				page: dialog._page,
				page_length: dialog._page_length,
			},
			callback: (r) => {
				const res = r.message || {};
				dialog._list_doctype = res.list_doctype;
				dialog._list_filters = res.list_filters || {};
				dialog._total = res.total || 0;
				dialog.set_value('preview_html', this.build_preview_html(res));
				dialog.get_primary_btn().prop('disabled', !res.total);
			},
			error: () => {
				dialog.set_value(
					'preview_html',
					`<div class="text-muted" style="padding:24px 0;text-align:center;">${__('Could not load data.')}</div>`
				);
			},
		});
	}

	build_preview_html(res) {
		const columns = res.columns || [];
		const rows = res.rows || [];
		const total = res.total || 0;
		const page = res.page || 0;
		const page_length = res.page_length || 10;

		if (!columns.length || !rows.length) {
			return `<div class="text-muted" style="padding:24px 0;text-align:center;">${__('No matching records for this period.')}</div>`;
		}

		const format_cell = (col, val) => {
			if (val === null || val === undefined || val === '') return '';
			if (col.type === 'currency') return this.fmtCompact(flt(val));
			return frappe.utils.escape_html(String(val));
		};

		let html = `<table class="table table-bordered" style="margin-bottom:0;">
			<thead><tr>${columns.map((c) => `<th>${frappe.utils.escape_html(c.label)}</th>`).join('')}</tr></thead>
			<tbody>`;
		rows.forEach((row) => {
			html += `<tr>${columns.map((c) => `<td>${format_cell(c, row[c.key])}</td>`).join('')}</tr>`;
		});
		html += `</tbody></table>`;

		const from_n = total ? page * page_length + 1 : 0;
		const to_n = Math.min((page + 1) * page_length, total);
		const max_page = Math.max(Math.ceil(total / page_length) - 1, 0);

		html += `
			<div style="display:flex;align-items:center;justify-content:space-between;margin-top:12px;">
				<div class="text-muted" style="font-size:12px;">${__('Showing {0}–{1} of {2}', [from_n, to_n, total])}</div>
				<div style="display:flex;gap:6px;">
					<button class="btn btn-default btn-sm soo-page-prev" ${page <= 0 ? 'disabled' : ''}>← ${__('Prev')}</button>
					<button class="btn btn-default btn-sm soo-page-next" ${page >= max_page ? 'disabled' : ''}>${__('Next')} →</button>
				</div>
			</div>`;

		if (res.note) {
			html += `<div class="text-muted" style="margin-top:8px;font-size:12px;">${frappe.utils.escape_html(res.note)}</div>`;
		}

		return html;
	}
}