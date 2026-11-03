// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt

frappe.ui.form.on('Serial No', {
	refresh: function(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__('Pairing History'), function() {
				frappe.set_route('List', 'Component Pairing Log', {
					serial_no: frm.doc.name
				});
			});
		}
	}
});

