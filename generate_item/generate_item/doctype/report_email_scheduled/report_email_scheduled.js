// Copyright (c) 2026, FinByz Tech and contributors
// For license information, please see license.txt

frappe.ui.form.on('Report Email Scheduled', {
	refresh: function (frm) {
		set_frequency_fields(frm);

		if (!frm.is_new()) {
			frm.add_custom_button(__('Send Now'), function () {
				if (frm.is_dirty()) {
					frappe.msgprint(__('Please save your changes before sending.'));
					return;
				}

				frappe.confirm(
					__('Are you sure you want to send this report email now to the configured recipients?'),
					function () {
						frappe.show_alert({
							message: __('Sending report email...'),
							indicator: 'blue'
						});

						frm.call({
							doc: frm.doc,
							method: 'send_now',
							freeze: true,
							freeze_message: __('Generating report and sending email...'),
							callback: function (r) {
								if (!r.exc) {
									frappe.show_alert({
										message: __('Report email sent successfully!'),
										indicator: 'green'
									});
									frm.reload_doc();
								}
							}
						});
					}
				);
			}).addClass('btn-primary');
		}
	},
	frequency: function (frm) {
		set_frequency_fields(frm);
	},

	// This triggers when your 'Get Filters' Button field is clicked
	get_filters: function (frm) {
		if (!frm.doc.report) {
			frappe.msgprint(__('Please select a Report first.'));
			return;
		}

		let report_name = frm.doc.report;

		// Replace 'filters' with the actual fieldname of your child table
		frm.clear_table('filters');

		frappe.call({
			method: "ibtevolve.ibtevolve.doctype.report_email_scheduled.report_email_scheduled.get_report_filters", // <--- UPDATE THIS PATH
			args: {
				report_name: report_name
			},
			callback: function (r) {
				if (r.message && r.message.length > 0) {
					r.message.forEach(f => {
						let child = frm.add_child('filters');
						// Maps to your 'Filter' field (Label fallback to Fieldname)
						child.filter = f.label || f.fieldname;
						// Maps to your 'fieldname' field
						child.fieldname = f.fieldname;
						// Maps to your 'value' field (Default value)
						child.value = f.default || '';
					});
					frm.refresh_field('filters');
					frappe.show_alert({ message: __('Filters loaded successfully'), indicator: 'green' });
				} else {
					frappe.msgprint(__('No filters found for this report.'));
				}
			}
		});
	}
});


function set_frequency_fields(frm) {
	const frequency = frm.doc.frequency;

	// Hide both fields by default
	frm.toggle_display('day_of_week', false);
	frm.toggle_display('day_of_month', false);

	if (frequency === 'Daily') {
		// Both hidden
		frm.toggle_display('day_of_week', false);
		frm.toggle_display('day_of_month', false);

	} else if (frequency === 'Weekly') {
		// Show day of week
		frm.toggle_display('day_of_week', true);

	} else if (frequency === 'Monthly') {
		// Show day of month
		frm.toggle_display('day_of_month', true);
	}
}