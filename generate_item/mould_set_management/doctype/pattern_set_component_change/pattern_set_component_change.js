// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt

frappe.ui.form.on('Pattern Set Component Change', {
	setup: function(frm) {
		// Filter Pattern Set to submitted and active sets only
		frm.set_query('pattern_set', function() {
			return {
				filters: {
					docstatus: 1,
					disabled: 0
				}
			};
		});

		// Item Code: only component items of the selected Pattern Set
		frm.set_query('item_code', 'items', function(doc, cdt, cdn) {
			let row = locals[cdt][cdn];
			if (!doc.pattern_set) {
				frappe.msgprint(__('Please select a Pattern Set first.'));
				return {};
			}
			// Attach: only items that still have an empty Serial No row in the set
			let items = row && row.action === 'Attach' ? frm.__empty_items : frm.__set_items;
			return { filters: { name: ['in', (items && items.length) ? items : ['']] } };
		});

		// Serial No: only serials of the row's Item (TASK41453)
		frm.set_query('serial_no', 'items', function(doc, cdt, cdn) {
			let row = locals[cdt][cdn];
			if (!doc.pattern_set) {
				frappe.msgprint(__('Please select a Pattern Set first.'));
				return {};
			}
			if (!row.item_code) {
				frappe.msgprint(__('Please select the Item Code first.'));
				return { filters: { name: '' } };
			}

			if (row.action === 'Detach') {
				return {
					filters: {
						item_code: row.item_code,
						custom_pattern_set: doc.pattern_set
					}
				};
			} else {
				// Attach: only free serials of this item, not linked to any Pattern Set (TASK41454)
				return {
					query: 'generate_item.mould_set_management.doctype.pattern_set_component_change.pattern_set_component_change.free_serial_query',
					filters: { item_code: row.item_code }
				};
			}
		});
	},

	refresh: function(frm) {
		frm.trigger('render_set_info');
		frm.trigger('load_set_items');
	},

	pattern_set: function(frm) {
		frm.trigger('render_set_info');
		frm.trigger('load_set_items');
	},

	load_set_items: function(frm) {
		frm.__set_items = [];
		frm.__empty_items = [];
		if (!frm.doc.pattern_set) return;
		const method = 'generate_item.mould_set_management.doctype.pattern_set_component_change.pattern_set_component_change.get_pattern_set_items';
		frappe.call({
			method: method,
			args: { pattern_set: frm.doc.pattern_set },
			callback: function(r) {
				frm.__set_items = r.message || [];
			}
		});
		// Attach rows: items with an empty Serial No row in the set
		frappe.call({
			method: method,
			args: { pattern_set: frm.doc.pattern_set, only_empty: 1 },
			callback: function(r) {
				frm.__empty_items = r.message || [];
			}
		});
	},

	render_set_info: function(frm) {
		if (frm.doc.pattern_set) {
			frappe.call({
				method: 'generate_item.mould_set_management.doctype.pattern_set.pattern_set.get_set_info_html',
				args: { pattern_set: frm.doc.pattern_set },
				callback: function(r) {
					if (r.message) {
						frm.set_df_property('set_info', 'options', r.message);
						frm.refresh_field('set_info');
					}
				}
			});
		} else {
			frm.set_df_property('set_info', 'options', '<div class="text-muted" style="padding:10px;">Select a Pattern Set to view slots and attached components.</div>');
			frm.refresh_field('set_info');
		}
	}
});

frappe.ui.form.on('Pattern Set Component Change Item', {
	item_code: function(frm, cdt, cdn) {
		// A serial picked for another item is no longer valid (TASK41453)
		let row = locals[cdt][cdn];
		if (row.serial_no) frappe.model.set_value(cdt, cdn, 'serial_no', '');
		frappe.model.set_value(cdt, cdn, 'warehouse', '');
		frappe.model.set_value(cdt, cdn, 'previous_set', '');
	},

	serial_no: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (!row.serial_no) return;

		frappe.call({
			method: 'generate_item.mould_set_management.doctype.pattern_set_component_change.pattern_set_component_change.get_serial_details',
			args: { serial_no: row.serial_no, pattern_set: frm.doc.pattern_set },
			callback: function(r) {
				if (r.message) {
					// The Item is chosen first; the serial picker only offers that item's serials
					frappe.model.set_value(cdt, cdn, 'warehouse', r.message.warehouse);
					frappe.model.set_value(cdt, cdn, 'previous_set', r.message.previous_set);
				}
			}
		});
	},

	action: function(frm, cdt, cdn) {
		// Clear serial when action switches; keep the chosen Item
		let row = locals[cdt][cdn];
		// Attach: the Item must still have an empty Serial No row in the set
		if (row.action === 'Attach' && row.item_code && !(frm.__empty_items || []).includes(row.item_code)) {
			frappe.model.set_value(cdt, cdn, 'item_code', '');
		}
		frappe.model.set_value(cdt, cdn, 'serial_no', '');
		frappe.model.set_value(cdt, cdn, 'warehouse', '');
		frappe.model.set_value(cdt, cdn, 'previous_set', '');
	}
});

