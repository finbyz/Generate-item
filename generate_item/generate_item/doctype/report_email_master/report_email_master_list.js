// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt

frappe.listview_settings['Report Email Master'] = {
	add_fields: ['type', 'source', 'report_name', 'page_name'],
	get_indicator: function (doc) {
		if (doc.type === 'Master') {
			return [__('Master'), 'blue', 'type,=,Master'];
		} else if (doc.type === 'Group') {
			return [__('Group'), 'orange', 'type,=,Group'];
		}
	}
};
