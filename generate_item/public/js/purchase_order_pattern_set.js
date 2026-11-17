// Pattern Set Association Details (view-only) for Purchase Order.
// Shows submitted, non-disabled Pattern Sets whose components match PO items on all
// seven fields. Rendered below the Items table. Nothing is saved to the document.

(() => {
	const METHOD =
		"generate_item.mould_set_management.po_pattern_set_association.get_pattern_set_associations";
	const MATCH_FIELDS = [
		"item_code",
		"custom_drawing_no",
		"custom_drawing_rev_no",
		"custom_pattern_drawing_no",
		"custom_pattern_drawing_rev_no",
		"custom_purchase_specification_no",
		"custom_purchase_specification_rev_no",
	];
	const DEBOUNCE_MS = 400;
	const WRAPPER_CLASS = "pattern-set-association";

	const is_blank = (value) =>
		value === undefined || value === null || String(value).trim() === "";

	function get_state(frm) {
		if (!frm.__psa) {
			frm.__psa = {
				request_id: 0,
				timer: null,
				signature: null,
				docname: null,
				data: [],
			};
		}
		return frm.__psa;
	}

	// Only rows with all seven fields filled can match, so only those are sent.
	function get_complete_items(frm) {
		const seen = new Set();
		const items = [];
		(frm.doc.items || []).forEach((row) => {
			if (MATCH_FIELDS.some((field) => is_blank(row[field]))) return;
			const item = {};
			MATCH_FIELDS.forEach((field) => (item[field] = row[field]));
			const key = JSON.stringify(MATCH_FIELDS.map((field) => item[field]));
			if (seen.has(key)) return;
			seen.add(key);
			items.push(item);
		});
		return items;
	}

	function get_wrapper(frm) {
		const items_field = frm.fields_dict.items;
		if (!items_field || !items_field.wrapper) return null;

		const $items = $(items_field.wrapper);
		let $wrapper = $items.next(`.${WRAPPER_CLASS}`);
		if (!$wrapper.length) {
			$wrapper = $(`<div class="${WRAPPER_CLASS} frappe-control" style="margin-top: var(--margin-lg);">
					<div class="control-label" style="margin-bottom: var(--margin-sm);">
						${__("Pattern Set Association Details")}
					</div>
					<div class="${WRAPPER_CLASS}-body"></div>
				</div>`);
			$items.after($wrapper);
		}
		return $wrapper.find(`.${WRAPPER_CLASS}-body`);
	}

	function render_message($body, message, extra_class = "") {
		$body.html(`<div class="text-muted small ${extra_class}"
				style="padding: var(--padding-md); border: 1px solid var(--border-color);
				border-radius: var(--border-radius-md); text-align: center;">
				${message}
			</div>`);
	}

	function render_loading(frm) {
		const $body = get_wrapper(frm);
		if (!$body) return;
		render_message(
			$body,
			`<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"
				style="margin-right: var(--margin-xs);"></span>${__("Loading Pattern Set Association...")}`
		);
	}

	function status_indicator(status) {
		if (is_blank(status)) return "";
		const color = { Complete: "green", Incomplete: "orange" }[status] || "gray";
		return `<span class="indicator-pill ${color}">${frappe.utils.escape_html(__(status))}</span>`;
	}

	function render_table(frm) {
		const $body = get_wrapper(frm);
		if (!$body) return;

		const data = get_state(frm).data || [];
		if (!data.length) {
			render_message($body, __("No Pattern Set Association Found"));
			return;
		}

		const esc = (value) => frappe.utils.escape_html(is_blank(value) ? "" : String(value));
		const can_open = frappe.model.can_read("Pattern Set");

		const rows = data
			.map((row) => {
				const id = esc(row.pattern_set_id);
				const id_html = can_open
					? `<a href="/app/pattern-set/${encodeURIComponent(row.pattern_set_id)}">${id}</a>`
					: id;
				return `<tr>
					<td>${id_html}</td>
					<td>${esc(row.supplier)}</td>
					<td>${esc(row.current_warehouse)}</td>
					<td>${status_indicator(row.completeness_status)}</td>
				</tr>`;
			})
			.join("");

		$body.html(`<div class="table-responsive" style="border: 1px solid var(--border-color);
				border-radius: var(--border-radius-md);">
				<table class="table table-sm" style="margin: 0;">
					<thead style="background-color: var(--subtle-fg);">
						<tr>
							<th>${__("Pattern Set ID")}</th>
							<th>${__("Supplier")}</th>
							<th>${__("Current Warehouse")}</th>
							<th>${__("Completeness Status")}</th>
						</tr>
					</thead>
					<tbody>${rows}</tbody>
				</table>
			</div>`);
	}

	function load(frm, { force = false } = {}) {
		const state = get_state(frm);
		clearTimeout(state.timer);
		state.timer = null;

		const docname = frm.doc.name;
		const items = get_complete_items(frm);
		const signature = JSON.stringify(items);

		// Every call gets a new id, so any request still in flight becomes stale.
		const request_id = ++state.request_id;

		if (!items.length) {
			state.signature = signature;
			state.docname = docname;
			state.data = [];
			render_table(frm);
			return;
		}

		// Same document and same item keys: reuse the last result.
		if (!force && state.signature === signature && state.docname === docname) {
			render_table(frm);
			return;
		}

		render_loading(frm);
		frappe.call({
			method: METHOD,
			args: {
				items: items,
				purchase_order: frm.is_new() ? null : docname,
			},
			callback: (r) => {
				if (request_id !== state.request_id || frm.doc.name !== docname) return;
				state.signature = signature;
				state.docname = docname;
				state.data = r.message || [];
				render_table(frm);
			},
			error: () => {
				if (request_id !== state.request_id || frm.doc.name !== docname) return;
				state.signature = null;
				const $body = get_wrapper(frm);
				$body && render_message($body, __("Could not load Pattern Set Association"), "text-danger");
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
	});

	const child_handlers = {
		items_add: schedule_load,
		items_remove: schedule_load,
		items_delete: schedule_load,
	};
	MATCH_FIELDS.forEach((field) => (child_handlers[field] = schedule_load));
	frappe.ui.form.on("Purchase Order Item", child_handlers);
})();
