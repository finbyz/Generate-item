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

		// Dynamic queries for child table rows
		frm.set_query('serial_no', 'items', function(doc, cdt, cdn) {
			let row = locals[cdt][cdn];
			if (!doc.pattern_set) {
				frappe.msgprint(__('Please select a Pattern Set first.'));
				return {};
			}

			if (row.action === 'Detach') {
				return {
					filters: {
						custom_pattern_set: doc.pattern_set
					}
				};
			} else {
				// Attach: Active serials not currently in this set
				return {
					filters: {
						status: 'Active',
						custom_pattern_set: ['!=', doc.pattern_set]
					}
				};
			}
		});
	},

	refresh: function(frm) {
		frm.trigger('render_set_info');
	},

	pattern_set: function(frm) {
		frm.trigger('render_set_info');
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
	serial_no: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (!row.serial_no) return;

		frappe.call({
			method: 'generate_item.mould_set_management.doctype.pattern_set_component_change.pattern_set_component_change.get_serial_details',
			args: { serial_no: row.serial_no, pattern_set: frm.doc.pattern_set },
			callback: function(r) {
				if (r.message) {
					frappe.model.set_value(cdt, cdn, 'item_code', r.message.item_code);
					frappe.model.set_value(cdt, cdn, 'warehouse', r.message.warehouse);
					frappe.model.set_value(cdt, cdn, 'previous_set', r.message.previous_set);
				}
			}
		});
	},

	action: function(frm, cdt, cdn) {
		// Clear serial when action switches
		frappe.model.set_value(cdt, cdn, 'serial_no', '');
		frappe.model.set_value(cdt, cdn, 'item_code', '');
		frappe.model.set_value(cdt, cdn, 'warehouse', '');
		frappe.model.set_value(cdt, cdn, 'previous_set', '');
	}
});

