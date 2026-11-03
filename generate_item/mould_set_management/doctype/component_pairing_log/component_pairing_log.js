// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt

frappe.ui.form.on('Component Pairing Log', {
	refresh: function(frm) {
		frm.disable_save();
		frm.page.clear_primary_action();
	}
});

