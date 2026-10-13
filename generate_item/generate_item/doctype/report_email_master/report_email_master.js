// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt

frappe.ui.form.on('Report Email Master', {
	setup: function (frm) {
		// Group Name in email_group child table must only show Group-type documents
		frm.set_query('group_name', 'email_group', function () {
			return {
				filters: {
					type: 'Group'
				}
			};
		});

		// User in receipts child table must only show enabled users
		frm.set_query('user', 'receipts', function () {
			return {
				filters: {
					enabled: 1
				}
			};
		});

		// CC User in cc child table must only show enabled users
		frm.set_query('cc_user', 'cc', function () {
			return {
				filters: {
					enabled: 1
				}
			};
		});
	},

	refresh: function (frm) {
		frm.trigger('toggle_fields');
	},

	type: function (frm) {
		if (frm.doc.type === 'Master') {
			// Clear Group-specific fields
			frm.set_value('group_name', '');
			frm.set_value('branch', '');
			frm.clear_table('receipts');
			frm.clear_table('cc');
			frm.refresh_fields(['receipts', 'cc', 'group_name', 'branch']);
		} else if (frm.doc.type === 'Group') {
			// Clear Master-specific fields
			frm.set_value('source', '');
			frm.set_value('report_name', '');
			frm.set_value('page_name', '');
			frm.clear_table('email_group');
			frm.refresh_fields(['source', 'report_name', 'page_name', 'email_group']);
		}
		frm.trigger('toggle_fields');
	},

	source: function (frm) {
		if (frm.doc.source === 'Report') {
			frm.set_value('page_name', '');
		} else if (frm.doc.source === 'Dashboard' || frm.doc.source === 'Page') {
			frm.set_value('report_name', '');
		}
		frm.refresh_fields(['report_name', 'page_name']);
		frm.trigger('toggle_fields');
	},

	toggle_fields: function (frm) {
		const is_master = frm.doc.type === 'Master';
		const is_group = frm.doc.type === 'Group';

		frm.toggle_display(['source', 'section_source_fields', 'section_email_groups', 'email_group'], is_master);
		frm.toggle_display(['section_group_fields', 'group_name', 'branch', 'section_cc', 'receipts', 'cc'], is_group);

		if (is_master) {
			frm.toggle_display('report_name', frm.doc.source === 'Report');
			frm.toggle_display('page_name', frm.doc.source === 'Dashboard' || frm.doc.source === 'Page');
		}
	}
});

// Child table: Report Email Group
frappe.ui.form.on('Report Email Group', {
	group_name: function (frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.group_name) {
			frappe.call({
				method: 'generate_item.generate_item.doctype.report_email_master.report_email_master.get_group_recipient_count',
				args: {
					group_name: row.group_name
				},
				callback: function (r) {
					if (r.message !== undefined) {
						frappe.model.set_value(cdt, cdn, 'count', r.message);
					}
				}
			});
		} else {
			frappe.model.set_value(cdt, cdn, 'count', 0);
		}
	}
});
