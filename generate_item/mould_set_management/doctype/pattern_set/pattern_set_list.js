// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt

frappe.listview_settings['Pattern Set'] = {
	get_indicator: function(doc) {
		if (doc.status === 'Complete') {
			return [__('Complete'), 'green', 'status,=,Complete'];
		} else if (doc.status === 'Incomplete') {
			return [__('Incomplete'), 'orange', 'status,=,Incomplete'];
		} else if (doc.status === 'Disabled') {
			return [__('Disabled'), 'gray', 'status,=,Disabled'];
		} else if (doc.status === 'Draft') {
			return [__('Draft'), 'red', 'status,=,Draft'];
		} else if (doc.status === 'Cancelled') {
			return [__('Cancelled'), 'darkgray', 'status,=,Cancelled'];
		}
	}
};

