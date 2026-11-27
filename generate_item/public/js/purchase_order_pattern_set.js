// Pattern association for Purchase Order lines (view-only, TASK40942).
// A casting item matches a "Patterns and Die" item when the pattern drawing no AND the
// pattern drawing revision are equal. The supplier's warehouses are the warehouses whose
// Supplier is the PO supplier (Set Target Warehouse and Supplier Warehouse are not used).
// Shows complete / incomplete Pattern Sets held by that supplier in those warehouses,
// the pattern stock at those warehouses and the pattern stock in the whole company.
// Rendered below the Items table. Nothing is saved.

(() => {
	const METHOD = "generate_item.mould_set_management.po_pattern_set_association.get_pattern_set_info";
	const DEBOUNCE_MS = 300;
	const WRAPPER_CLASS = "pattern-set-association";

	const esc = (v) => frappe.utils.escape_html(v === undefined || v === null ? "" : String(v));

	function get_state(frm) {
		if (!frm.__psa) frm.__psa = { request_id: 0, timer: null, signature: null, data: null };
		return frm.__psa;
	}

	function get_items(frm) {
		return (frm.doc.items || [])
			.filter((row) => row.item_code)
			.map((row) => ({ row: row.name, idx: row.idx, item_code: row.item_code }));
	}

	function get_wrapper(frm) {
		const items_field = frm.fields_dict.items;
		if (!items_field || !items_field.wrapper) return null;

		const $items = $(items_field.wrapper);
		let $wrapper = $items.next(`.${WRAPPER_CLASS}`);
		if (!$wrapper.length) {
			$wrapper = $(`<div class="${WRAPPER_CLASS} frappe-control" style="margin-top: var(--margin-lg);">
					<div class="control-label" style="margin-bottom: var(--margin-sm);">
						${__("Pattern Association")}
					</div>
					<div class="${WRAPPER_CLASS}-body"></div>
				</div>`);
			$items.after($wrapper);
		}
		return $wrapper.find(`.${WRAPPER_CLASS}-body`);
	}

	function box(message, extra_class = "") {
		return `<div class="text-muted small ${extra_class}"
				style="padding: var(--padding-md); border: 1px solid var(--border-color);
				border-radius: var(--border-radius-md); text-align: center;">${message}</div>`;
	}

	function render_message(frm, message, extra_class) {
		const $body = get_wrapper(frm);
		$body && $body.html(box(message, extra_class));
	}

	function set_links(names, color) {
		if (!names || !names.length) return `<span class="text-muted">0</span>`;
		const can_open = frappe.model.can_read("Pattern Set");
		const list = names
			.map((n) => (can_open ? `<a href="/app/pattern-set/${encodeURIComponent(n)}">${esc(n)}</a>` : esc(n)))
			.join("<br>");
		return `<span class="indicator-pill ${color}" title="${esc(names.join(", "))}">${names.length}</span>
			<div class="small" style="margin-top: 4px;">${list}</div>`;
	}

	function qty(v) {
		return v === null || v === undefined ? `<span class="text-muted">-</span>` : esc(format_number(v, null, 2));
	}

	function header_note(data) {
		if (!data.supplier) {
			return `<div class="small text-warning" style="margin-bottom: var(--margin-sm);">
				${__("Select the Supplier to see pattern sets and stock at the supplier.")}</div>`;
		}
		const warehouses = data.warehouses || [];
		if (!warehouses.length) {
			return `<div class="small text-warning" style="margin-bottom: var(--margin-sm);">
				${__("No warehouse is linked to Supplier {0}. Set the Supplier on the supplier's Warehouse to see its pattern sets and stock.", [
					`<b>${esc(data.supplier)}</b>`,
				])}</div>`;
		}
		return "";
	}

	function render(frm) {
		const $body = get_wrapper(frm);
		if (!$body) return;

		const data = get_state(frm).data || { rows: [] };
		const rows = data.rows || [];
		const note = header_note(data);
		const has_wh = (data.warehouses || []).length > 0;

		if (!rows.length) {
			$body.html(note + box(__("No item on this Purchase Order has a pattern drawing no.")));
			return;
		}

		const lines = rows
			.map((r) => {
				const patterns = r.patterns || [];
				const has = patterns.length > 0;
				const pattern_html = has
					? patterns
							.map(
								(p) => `<div><a href="/app/item/${encodeURIComponent(p.item_code)}">${esc(p.item_code)}</a>
									<div class="small text-muted">${esc(p.item_name)}</div></div>`
							)
							.join("")
					: `<span class="text-muted">${__("No matching pattern found")}</span>`;
				return `<tr>
					<td>${esc(r.idx)}</td>
					<td>${esc(r.item_code)}<div class="small text-muted">${esc(r.item_name)}</div></td>
					<td>${esc(r.pattern_drawing_no)}</td>
					<td>${esc(r.pattern_drawing_rev_no)}</td>
					<td>${pattern_html}</td>
					<td>${has && has_wh ? set_links(r.complete_sets, "green") : "-"}</td>
					<td>${has && has_wh ? set_links(r.incomplete_sets, "orange") : "-"}</td>
					<td class="text-right">${has ? qty(r.warehouse_qty) : "-"}</td>
					<td class="text-right">${has ? qty(r.company_qty) : "-"}</td>
				</tr>`;
			})
			.join("");

		$body.html(`${note}
			<div class="table-responsive" style="border: 1px solid var(--border-color); border-radius: var(--border-radius-md);">
				<table class="table table-sm" style="margin: 0;">
					<thead style="background-color: var(--subtle-fg);">
						<tr>
							<th>${__("Row")}</th>
							<th>${__("Casting Item")}</th>
							<th>${__("Pattern Drg No")}</th>
							<th>${__("Rev")}</th>
							<th>${__("Pattern Item")}</th>
							<th>${__("Complete Sets")}</th>
							<th>${__("Incomplete Sets")}</th>
							<th class="text-right">${__("Actual Qty at Warehouse")}</th>
							<th class="text-right">${__("Actual Qty at Company")}</th>
						</tr>
					</thead>
					<tbody>${lines}</tbody>
				</table>
			</div>`);
	}

	function load(frm, { force = false } = {}) {
		const state = get_state(frm);
		clearTimeout(state.timer);
		state.timer = null;

		const items = get_items(frm);
		const supplier = frm.doc.supplier || null;
		const company = frm.doc.company || null;
		const signature = JSON.stringify([frm.doc.name, supplier, company, items]);
		const request_id = ++state.request_id; // any request still in flight becomes stale

		if (!items.length) {
			state.signature = signature;
			state.data = { rows: [] };
			render_message(frm, __("Add items to see the pattern association."));
			return;
		}
		if (!force && state.signature === signature && state.data) {
			render(frm);
			return;
		}

		render_message(
			frm,
			`<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"
				style="margin-right: var(--margin-xs);"></span>${__("Loading pattern association...")}`
		);
		frappe.call({
			method: METHOD,
			args: {
				items: items,
				supplier: supplier,
				company: company,
				purchase_order: frm.is_new() ? null : frm.doc.name,
			},
			callback: (r) => {
				if (request_id !== state.request_id) return;
				state.signature = signature;
				state.data = r.message || { rows: [] };
				render(frm);
			},
			error: () => {
				if (request_id !== state.request_id) return;
				state.signature = null;
				render_message(frm, __("Could not load pattern association"), "text-danger");
			},
		});
	}

	function schedule_load(frm) {
		const state = get_state(frm);
		clearTimeout(state.timer);
		state.timer = setTimeout(() => load(frm), DEBOUNCE_MS);
	}

	frappe.ui.form.on("Purchase Order", {
		refresh(frm) {
			load(frm, { force: true });
		},
		onload_post_render: schedule_load,
		supplier: schedule_load,
		company: schedule_load,
	});

	frappe.ui.form.on("Purchase Order Item", {
		item_code: schedule_load,
		items_add: schedule_load,
		items_remove: schedule_load,
		items_delete: schedule_load,
	});
})();
