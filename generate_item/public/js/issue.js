// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt

frappe.ui.form.on("Issue", {
	onload(frm) {
		if (frm.is_new()) {
			if (!frm.doc.custom_complaint_status) {
				frm.set_value("custom_complaint_status", "Open");
			}
			if (!frm.doc.custom_complaint_reg_date) {
				frm.set_value("custom_complaint_reg_date", frappe.datetime.get_today());
			}
		}
	},

	refresh(frm) {
		// Quick link to Customer Complaint Register report
		frm.add_custom_button(__("Complaint Register"), function () {
			frappe.set_route("query-report", "Customer Complaint Register", {
				customer: frm.doc.customer || undefined,
			});
		}, __("View"));

		// Quick action to add a progress update if not new
		if (!frm.is_new()) {
			frm.add_custom_button(__("Add Progress Update"), function () {
				let d = new frappe.ui.Dialog({
					title: __("Add Complaint Progress Update"),
					fields: [
						{
							fieldname: "complaint_status",
							label: __("Complaint Status"),
							fieldtype: "Select",
							options: "Open\nAction in Progress\nClose",
							default: frm.doc.custom_complaint_status || "Open",
							reqd: 1,
						},
						{
							fieldname: "responsible_department",
							label: __("Responsible Department"),
							fieldtype: "Data",
							default: frm.doc.custom_responsible_department || "",
						},
						{
							fieldname: "action_by",
							label: __("Action By"),
							fieldtype: "Data",
							default: frm.doc.custom_action_taken_by || frappe.session.user_fullname,
						},
						{
							fieldname: "action_remarks",
							label: __("Action Decided / Remarks"),
							fieldtype: "Small Text",
							default: frm.doc.custom_action_remarks || "",
						},
						{ fieldtype: "Section Break", label: __("Visit Schedule") },
						{
							fieldname: "ssv_visiting_engineer",
							label: __("SSV Visiting Engineer"),
							fieldtype: "Data",
							default: frm.doc.custom_ssv_visiting_engineer || "",
						},
						{
							fieldname: "visit_schedule_date",
							label: __("Visit Schedule Date"),
							fieldtype: "Date",
							default: frm.doc.custom_visit_schedule_date || "",
						},
						{
							fieldname: "visit_schedule_notes",
							label: __("Visit Schedule Notes"),
							fieldtype: "Small Text",
							default: frm.doc.custom_visit_schedule_notes || "",
						},
					],
					primary_action_label: __("Save Update"),
					primary_action(values) {
						if (frm.is_dirty()) {
							frappe.msgprint({
								title: __("Unsaved Changes"),
								message: __("Please save your current changes on the form first before adding a progress update."),
								indicator: "orange",
							});
							return;
						}

						frappe.call({
							method: "generate_item.customer_complaint.issue.add_complaint_progress_update",
							args: {
								issue_id: frm.doc.name,
								complaint_status: values.complaint_status,
								responsible_department: values.responsible_department,
								action_by: values.action_by,
								action_remarks: values.action_remarks,
								ssv_visiting_engineer: values.ssv_visiting_engineer,
								visit_schedule_date: values.visit_schedule_date,
								visit_schedule_notes: values.visit_schedule_notes,
							},
							freeze: true,
							freeze_message: __("Saving progress update..."),
							callback(r) {
								if (r.message && r.message.success) {
									d.hide();
									frappe.show_alert({
										message: __("Progress update saved successfully"),
										indicator: "green",
									});
									frm.reload_doc();
								}
							},
						});
					},
				});
				d.show();
			});
		}
	},

	custom_sales_order(frm) {
		if (frm.doc.custom_sales_order) {
			frappe.db.get_value(
				"Sales Order",
				frm.doc.custom_sales_order,
				["customer","project"],
				function (r) {
					if (r) {
						if (!frm.doc.customer && r.customer) {
							frm.set_value("customer", r.customer);
						}
						let project_name = r.project;
						if (!frm.doc.custom_project_name && project_name) {
							frm.set_value("custom_project_name", project_name);
						}
					}
				}
			);
		}
	},

	custom_complaint_status(frm) {
		if (frm.doc.custom_complaint_status === "Close") {
			if (!frm.doc.custom_closure_date) {
				frm.set_value("custom_closure_date", frappe.datetime.get_today());
			}
			if (!frm.doc.custom_closure_by) {
				frm.set_value("custom_closure_by", frappe.session.user);
			}
		}
	},
});
