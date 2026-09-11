const purchase_user_dashboard_routes = [
	"purchase-user",
	"purchase_user",
];

function ensure_purchase_user_dashboard(wrapper) {
	if (wrapper.purchase_user_dashboard) {
		return;
	}
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

// ─── Utility: Format date string (YYYY-MM-DD) → DD/MM/YYYY ──────────────────
function fmt_date(val) {
	if (!val || val === "—") return "—";
	const s = String(val).split(" ")[0]; // strip time if any
	const parts = s.split("-");
	if (parts.length === 3) return `${parts[2]}/${parts[1]}/${parts[0]}`;
	return s;
}

function normalize_date_to_iso(val) {
	if (!val) return "";
	const s = String(val).trim().replace(/\//g, "-");
	const parts = s.split("-");
	if (parts.length === 3) {
		if (parts[0].length === 4) return `${parts[0]}-${parts[1].padStart(2, "0")}-${parts[2].padStart(2, "0")}`;
		if (parts[2].length === 4) return `${parts[2]}-${parts[1].padStart(2, "0")}-${parts[0].padStart(2, "0")}`;
	}
	if (frappe.datetime && frappe.datetime.user_to_str) {
		try {
			const converted = frappe.datetime.user_to_str(val);
			if (converted) return converted;
		} catch (_e) {}
	}
	return s;
}

class PurchaseUserDashboard {
	constructor(wrapper) {
		this.wrapper = wrapper;
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __("Purchase User Dashboard"),
			single_column: true,
		});
		this.api = "generate_item.generate_item.page.purchase_user.purchase_user";
		this.cards = [];
		this.controls = {};
		this.loading = false;
		this.suppress_filter_refresh = true;
		this._control_ready_promises = [];

		this.build();
		this.suppress_filter_refresh = false;
		this.bind_events();
		this.configure_page_actions();
		Promise.all(this._control_ready_promises).then(() => this.refresh());
	}

	build() {
		this.$main = $(`
			<div class="mel-purchase-dashboard">
				<div class="toast-box" id="mel-toasts"></div>
				<div class="modal-wrap" id="mel-modal">
					<div class="modal-bg"></div>
					<div class="modal-box" id="mel-modalBody" style="max-width:920px;width:92%;"></div>
				</div>

				<div class="sec-bar">
					<div>
						<div class="sec-title">${__("Purchase User Overview")}</div>
						<div class="sec-sub">${__("Click any card to view detailed stage records")}</div>
					</div>
					<div class="mel-filter-grid">
						<div class="mel-filter-control" data-filter="branch"></div>
						<div class="mel-filter-control" data-filter="user"></div>
						<div class="mel-filter-control" data-filter="from_date"></div>
						<div class="mel-filter-control" data-filter="to_date"></div>
						<button class="btn btn-default mel-clear-filters" type="button">${__("Clear")}</button>
					</div>
				</div>

				<div style="padding: 12px 24px 28px 24px;">
					<div class="grid-5" id="mel-cardGrid"></div>
				</div>
			</div>
		`).appendTo(this.page.main);

		this.make_filter_controls();
	}

	make_filter_controls() {
		const today = frappe.datetime.get_today();
		const from_date = frappe.datetime.add_months(today, -1);

		// 1. Branch Filter
		this.controls.branch = this.make_control("branch", {
			fieldtype: "Link",
			options: "Branch",
			label: __("Branch"),
			placeholder: __("All Branches"),
		});

		// 2. User MultiSelect Filter (defaults to session.user, filtered by Created By / owner)
		this.controls.user = this.make_control("user", {
			fieldtype: "MultiSelectList",
			label: __("Created By (User)"),
			placeholder: __("Select Users..."),
			get_data: () => {
				return this.call("get_allowed_users").then((users) => {
					return (users || []).map((u) => ({
						value: u.value,
						label: u.label,
						description: u.description || u.value,
					}));
				});
			},
			default: [frappe.session.user],
		});

		// 3. From Date (default 1 month ago)
		this.controls.from_date = this.make_control("from_date", {
			fieldtype: "Date",
			label: __("From Date"),
			default: from_date,
		});

		// 4. To Date (default today)
		this.controls.to_date = this.make_control("to_date", {
			fieldtype: "Date",
			label: __("To Date"),
			default: today,
		});
	}

	make_control(slot, df) {
		const parent = this.$main.find(`[data-filter="${slot}"]`).empty();
		const control = frappe.ui.form.make_control({
			parent,
			df: {
				...df,
				onchange: () => {
					if (!this.suppress_filter_refresh) this.refresh();
				},
			},
			render_input: true,
		});
		control.refresh();

		this._control_ready_promises = this._control_ready_promises || [];
		if (df.default !== undefined) {
			this._control_ready_promises.push(Promise.resolve(control.set_value(df.default)));
		}
		return control;
	}

	get_filters() {
		const today = frappe.datetime.get_today();
		const default_from_date = frappe.datetime.add_months(today, -1);

		let users = this.controls.user?.get_value() || [];
		if (typeof users === "string") {
			users = users ? [users] : [];
		}

		let raw_from = this.controls.from_date?.get_value();
		let raw_to = this.controls.to_date?.get_value();

		if (!raw_from && this.controls.from_date?.value) {
			raw_from = this.controls.from_date.value;
		}
		if (!raw_to && this.controls.to_date?.value) {
			raw_to = this.controls.to_date.value;
		}
		if (!raw_from) raw_from = default_from_date;
		if (!raw_to) raw_to = today;

		return {
			branch: this.controls.branch?.get_value() || "",
			users: users.length ? users : [frappe.session.user],
			from_date: normalize_date_to_iso(raw_from),
			to_date: normalize_date_to_iso(raw_to),
		};
	}

	configure_page_actions() {
		this.page.set_primary_action(__("Refresh"), () => this.refresh(), "refresh");
	}

	bind_events() {
		this.$main.on("click", ".modal-bg, [data-close-modal]", () => this.close_modal());
		this.$main.on("click", ".mel-clear-filters", () => this.clear_filters());

		this.$main.on("click", ".dash-card", (e) => {
			const cid = $(e.currentTarget).data("cid");
			this.open_stage_list_dialog(cid);
		});

		this.$main.on("click", ".mel-open-filtered-desk-list", (e) => {
			const $t = $(e.currentTarget);
			const cid = $t.data("cid");
			const doctype = $t.data("doctype");
			this.open_filtered_desk_list(cid, doctype);
		});

		$(document).on("keydown.mel-purchase-dash", (e) => {
			if (e.key === "Escape") {
				this.close_modal();
			}
		});
	}

	clear_filters() {
		this.suppress_filter_refresh = true;
		const today = frappe.datetime.get_today();
		const from_date = frappe.datetime.add_months(today, -1);

		const p1 = Promise.resolve(this.controls.branch.set_value(""));
		const p2 = Promise.resolve(this.controls.user.set_value([frappe.session.user]));
		const p3 = Promise.resolve(this.controls.from_date.set_value(from_date));
		const p4 = Promise.resolve(this.controls.to_date.set_value(today));

		Promise.all([p1, p2, p3, p4]).then(() => {
			this.suppress_filter_refresh = false;
			this.refresh();
		});
	}

	async call(method, args = {}) {
		const response = await frappe.call({
			method: `${this.api}.${method}`,
			args,
		});
		return response.message;
	}

	async refresh() {
		if (this.loading) return;
		this.loading = true;

		try {
			const filters = this.get_filters();
			const data = await this.call("get_dashboard", filters);
			this.cards = data?.cards || [];
			this.render_cards();
		} catch (error) {
			this.toast(error?.message || __("Could not refresh dashboard."));
		} finally {
			this.loading = false;
		}
	}

	render_cards() {
		const $grid = this.$main.find("#mel-cardGrid").empty();
		const cards = this.cards || [];

		const render_card = (c) => {
			const color_class = c.color || "clr-amber";
			const icon_class = c.icon || "octicon octicon-file";
			return `
				<div class="dash-card ${color_class}" data-cid="${c.id}">
					<div class="card-icon"><i class="${icon_class}"></i></div>
					<div class="card-num">${c.count}</div>
					<div class="card-label">${frappe.utils.escape_html(c.title)}</div>
					<div class="card-hint"><i class="octicon octicon-link-external" style="margin-right:6px;"></i>${__("Click to View")}</div>
				</div>
			`;
		};

		$grid.html(
			cards.map(render_card).join("") ||
			`<div class="text-muted p-4">${__("No dashboard cards available")}</div>`
		);
	}

	// ─── Stage Dialog (Detailed records inspection with AO grouping & line items) ──
	open_stage_list_dialog(cid) {
		const cards = this.cards || [];
		const card = cards.find((c) => c.id === cid);
		if (!card) return;

		const card_default_doctype = card.doctype || "Material Request";
		const items = card.items || [];
		const filters = this.get_filters();

		// Group records by AO / Project / Supplier
		const groups = new Map();
		items.forEach((it) => {
			const ao_key = (it.project && String(it.project).trim()) || (it.supplier && String(it.supplier).trim()) || __("General Records");
			if (!groups.has(ao_key)) groups.set(ao_key, []);
			groups.get(ao_key).push(it);
		});

		let rows_html = "";
		if (items.length) {
			let group_idx = 0;
			for (const [ao_label, group_items] of groups.entries()) {
				const group_id = `mel-group-${group_idx}`;
				let inner_rows_html = "";

				group_items.forEach((it, item_idx) => {
					const row_id = `${group_id}-row-${item_idx}`;
					const row_doctype = it.doctype || card_default_doctype;
					const date_display = fmt_date(it.date);

					const status_lc = (it.status || "").toLowerCase();
					let status_cls = "bdg-slate";
					if (status_lc.includes("draft")) status_cls = "bdg-amber";
					else if (status_lc.includes("unpaid") || status_lc.includes("overdue")) status_cls = "bdg-rose";
					else if (status_lc.includes("paid") || status_lc.includes("completed") || status_lc.includes("received") || status_lc.includes("transferred") || status_lc.includes("issued") || status_lc.includes("ordered")) status_cls = "bdg-green";
					else if (status_lc.includes("part") || status_lc.includes("pending")) status_cls = "bdg-amber";

					inner_rows_html += `
						<div class="mel-collapsible-row" id="${row_id}">
							<div class="mel-row-header" data-row-toggle="${row_id}">
								<span class="mel-row-chevron" id="${row_id}-icon">▶</span>
								<a class="mel-row-docid" onclick="event.stopPropagation();frappe.set_route('Form', '${row_doctype}', '${frappe.utils.escape_html(it.ao)}')">
									${frappe.utils.escape_html(it.ao)}
								</a>
								<span class="mel-row-doctype-hint">${frappe.utils.escape_html(it.item || "")}</span>
								${it.who ? `<span class="bdg bdg-slate" style="font-size:11px;" title="${__("Created By")}">${frappe.utils.escape_html(it.who)}</span>` : ""}
								${it.branch ? `<span class="bdg bdg-slate" style="font-size:11px;">${frappe.utils.escape_html(it.branch)}</span>` : ""}
								<span class="mel-row-date-badge">${date_display}</span>
								<span class="bdg ${status_cls}">${frappe.utils.escape_html(it.status || "")}</span>
							</div>
							<div class="mel-row-detail" id="${row_id}-detail" style="display:none;">
							${(() => {
								const doc_items = it.doc_items || [];
								if (!doc_items.length) {
									return `<div class="text-center text-muted" style="padding:10px 0;font-size:12px;">${__("No line items found")}</div>`;
								}
								const has_received_col = doc_items.some((di) => di.received_qty > 0);
								const has_rate_col = doc_items.some((di) => di.rate > 0);
								const trows = doc_items.map((di) => {
									const rem = has_received_col ? (di.qty - (di.received_qty || 0)) : null;
									const rem_cls = rem !== null && rem > 0 ? "bdg-amber" : "bdg-green";
									return `<tr>
										<td><span class="bdg bdg-indigo" style="font-size:11px;">${frappe.utils.escape_html(di.item_code)}</span></td>
										<td style="font-weight:600;">${frappe.utils.escape_html(di.item_name)}</td>
										<td style="text-align:right;"><span class="bdg bdg-slate">${di.qty} ${frappe.utils.escape_html(di.uom || "")}</span></td>
										${has_received_col ? `<td style="text-align:right;"><span class="bdg ${rem_cls}">${rem} ${__("rem")}</span></td>` : ""}
										<td style="color:#64748b;">${di.schedule_date ? fmt_date(di.schedule_date) : "—"}</td>
										${has_rate_col ? `<td style="color:#475569;">${di.rate > 0 ? (frappe.format ? frappe.format(di.rate, { fieldtype: "Currency" }) : di.rate) : "—"}</td>` : ""}
									</tr>`;
								}).join("");
								return `
								<div style="overflow-x:auto;">
									<table class="mel-doc-items-table">
										<thead>
											<tr>
												<th>${__("Item Code")}</th>
												<th>${__("Item Name")}</th>
												<th style="text-align:right;">${__("Qty")}</th>
												${has_received_col ? `<th style="text-align:right;">${__("Remaining")}</th>` : ""}
												<th>${__("Req. Date")}</th>
												${has_rate_col ? `<th>${__("Rate")}</th>` : ""}
											</tr>
										</thead>
										<tbody>${trows}</tbody>
									</table>
								</div>`;
							})()}
							<div style="margin-top:12px;display:flex;justify-content:flex-end;">
								<button class="btn-b" type="button" onclick="frappe.set_route('Form', '${row_doctype}', '${frappe.utils.escape_html(it.ao)}')">
									<i class="octicon octicon-link-external" style="margin-right:6px;"></i>${__("Open Form")}
								</button>
							</div>
						</div>
						</div>
					`;
				});

				rows_html += `
					<div class="mel-ao-group" id="${group_id}">
						<div class="mel-ao-group-header" data-group-toggle="${group_id}">
							<span class="mel-ao-group-chevron" id="${group_id}-icon">▶</span>
							<span style="margin-right:6px;">📁</span>
							<span class="mel-ao-group-title">${frappe.utils.escape_html(ao_label)}</span>
							<span class="mel-ao-group-count">${group_items.length} ${__("records")}</span>
						</div>
						<div class="mel-ao-group-body" id="${group_id}-body" style="display:none;">
							${inner_rows_html}
						</div>
					</div>
				`;
				group_idx++;
			}
		} else {
			rows_html = `<div class="text-center text-muted p-4">${__("No records found for this stage with current filters.")}</div>`;
		}

		const date_info = (filters.from_date || filters.to_date)
			? `${fmt_date(filters.from_date)} → ${fmt_date(filters.to_date)}`
			: __("All Dates");

		const content = `
			<div class="modal-head">
				<div>
					<div class="modal-head-title">${frappe.utils.escape_html(card.title)} — ${__("Record Inspection")}</div>
					<div class="modal-head-sub">${items.length} ${__("records in view")} · ${groups.size} ${__("group(s)")} · <span style="color:#0f172a;font-weight:600;">${date_info}</span></div>
				</div>
				<button class="btn-x" data-close-modal type="button">✕</button>
			</div>
			<div style="padding:16px 24px 8px 24px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;">
				<input type="text" class="f-input-light" id="mel-dialogSearch" placeholder="${__("Search document ID or records...")}" style="width:280px;">
				<div style="display:flex;align-items:center;gap:12px;">
					<button class="btn-s mel-expand-all-groups" type="button" data-expanded="false">
						<i class="octicon octicon-unfold" style="margin-right:4px;"></i>${__("Expand All")}
					</button>
					<span style="font-size:13px;color:#64748b;">${__("DocType")}: <strong>${card_default_doctype}</strong></span>
				</div>
			</div>
			<div style="padding:8px 24px 20px 24px;max-height:55vh;overflow-y:auto;" id="mel-modal-list">
				${rows_html}
			</div>
			<div style="padding:14px 24px;border-top:1px solid #e2e8f0;display:flex;justify-content:space-between;align-items:center;background:#f8fafc;border-bottom-left-radius:16px;border-bottom-right-radius:16px;">
				<span style="font-size:13px;color:#64748b;">${items.length} ${__("records loaded")}</span>
				<button class="btn-b mel-open-filtered-desk-list" data-cid="${cid}" data-doctype="${card_default_doctype}" type="button">
					<i class="octicon octicon-filter" style="margin-right:6px;"></i>${__("Open Filtered List View")}
				</button>
			</div>
		`;

		this.$main.find("#mel-modalBody").html(content);
		this.$main.find("#mel-modal").addClass("show");

		// Expand All / Collapse All
		this.$main.find(".mel-expand-all-groups").off("click").on("click", (e) => {
			const $btn = $(e.currentTarget);
			const isExpanded = $btn.data("expanded") === true || $btn.data("expanded") === "true";
			const willExpand = !isExpanded;

			this.$main.find(".mel-ao-group-body").toggle(willExpand);
			this.$main.find(".mel-ao-group-chevron").text(willExpand ? "▼" : "▶");
			$btn.data("expanded", willExpand);
			$btn.html(
				willExpand
					? `<i class="octicon octicon-fold" style="margin-right:4px;"></i>${__("Collapse All")}`
					: `<i class="octicon octicon-unfold" style="margin-right:4px;"></i>${__("Expand All")}`
			);
		});

		// Group toggle
		this.$main.find("#mel-modal-list").off("click", "[data-group-toggle]").on("click", "[data-group-toggle]", (e) => {
			e.stopPropagation();
			const gid = $(e.currentTarget).data("group-toggle");
			const $body = this.$main.find(`#${gid}-body`);
			const $icon = this.$main.find(`#${gid}-icon`);
			const isOpen = $body.is(":visible");
			$body.toggle(!isOpen);
			$icon.text(isOpen ? "▶" : "▼");
		});

		// Row detail toggle
		this.$main.find("#mel-modal-list").off("click", "[data-row-toggle]").on("click", "[data-row-toggle]", (e) => {
			e.stopPropagation();
			const rid = $(e.currentTarget).data("row-toggle");
			const $detail = this.$main.find(`#${rid}-detail`);
			const $icon = this.$main.find(`#${rid}-icon`);
			const isOpen = $detail.is(":visible");

			this.$main.find(".mel-row-detail").hide();
			this.$main.find(".mel-row-chevron").text("▶");

			if (!isOpen) {
				$detail.show();
				$icon.text("▼");
			}
		});

		// Search inside modal
		this.$main.find("#mel-dialogSearch").off("input").on("input", (e) => {
			const q = $(e.currentTarget).val().toLowerCase();
			this.$main.find(".mel-ao-group").each((_, group) => {
				const $group = $(group);
				const groupTitle = $group.find(".mel-ao-group-title").text().toLowerCase();
				let visible = groupTitle.includes(q);

				$group.find(".mel-collapsible-row").each((_, row) => {
					const text = $(row).text().toLowerCase();
					const match = !q || text.includes(q) || groupTitle.includes(q);
					$(row).toggle(match);
					if (match) visible = true;
				});

				$group.toggle(visible);
				if (q && visible) {
					$group.find(".mel-ao-group-body").show();
					$group.find(".mel-ao-group-chevron").text("▼");
				}
			});
		});
	}

	open_filtered_desk_list(cid, doctype) {
		const filters = this.get_filters();
		const route_options = {};

		// Apply branch filter if selected
		if (filters.branch) {
			route_options.branch = filters.branch;
		}

		// Apply user filter (owner / Created By IN selected users)
		if (filters.users && filters.users.length) {
			if (filters.users.length === 1) {
				route_options.owner = filters.users[0];
			} else {
				route_options.owner = ["in", filters.users];
			}
		}

		// Date field determination per doctype
		const date_field = (doctype === "Purchase Receipt" || doctype === "Purchase Invoice")
			? "posting_date"
			: "transaction_date";

		if (filters.from_date && filters.to_date) {
			route_options[date_field] = ["between", [filters.from_date, filters.to_date]];
		} else if (filters.from_date) {
			route_options[date_field] = [">=", filters.from_date];
		} else if (filters.to_date) {
			route_options[date_field] = ["<=", filters.to_date];
		}

		// 1. PO Pending: Material Request with docstatus=1, status in submitted, partially ordered, pending
		if (cid === "po_pending") {
			route_options.docstatus = 1;
			route_options.status = ["in", ["Submitted", "Partially Ordered", "Pending"]];
		}
		// 2. MR Completed: Material Request with docstatus=1, status in partially received, ordered, issued, transferred, received
		else if (cid === "mr_completed") {
			route_options.docstatus = 1;
			route_options.status = ["in", ["Partially Received", "Ordered", "Issued", "Transferred", "Received"]];
		}
		// 3. PR Pending: Purchase Order with docstatus=1, status in to receive and bill, to receive
		else if (cid === "pr_pending") {
			route_options.docstatus = 1;
			route_options.status = ["in", ["To Receive and Bill", "To Receive"]];
		}
		// 4. PI Pending: Purchase Receipt with docstatus=1, status in partially billed, to bill
		else if (cid === "pi_pending") {
			route_options.docstatus = 1;
			route_options.status = ["in", ["Partly Billed", "To Bill"]];
		}
		// 5. Total PI Completed: Purchase Invoice with docstatus=1, is_return=0
		else if (cid === "pi_completed") {
			route_options.docstatus = 1;
			route_options.is_return = 0;
		}

		frappe.route_options = route_options;
		frappe.set_route("List", doctype);
	}

	close_modal() {
		this.$main.find("#mel-modal").removeClass("show");
	}

	toast(msg) {
		const $box = this.$main.find("#mel-toasts");
		const $t = $(`<div class="toast-msg">${frappe.utils.escape_html(msg)}</div>`).appendTo($box);
		setTimeout(() => $t.remove(), 2600);
	}
}