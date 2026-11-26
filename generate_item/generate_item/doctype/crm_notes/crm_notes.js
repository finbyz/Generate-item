// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt

frappe.ui.form.on("CRM Notes", {
	refresh(frm) {
		if (frm.is_new() || frm.doc.docstatus !== 0 || !frm.doc.order_number) return;

		frm.add_custom_button(__("Get Update"), () => {
			if (frm.is_dirty()) {
				frappe.msgprint(__("Please save your changes before getting the update from the Sales Order."));
				return;
			}
			frappe
				.call({
					method: "generate_item.utils.crm_notes.get_update_from_sales_order",
					args: { crm_note: frm.doc.name },
					freeze: true,
					freeze_message: __("Getting latest Sales Order values..."),
				})
				.then((r) => {
					const res = r.message || {};
					frm.reload_doc().then(() => {
						if (res.changes && res.changes.length) {
							frappe.msgprint({
								title: __("Updated from Sales Order {0}", [frm.doc.order_number]),
								message: res.message_html,
								indicator: "green",
							});
						} else {
							frappe.show_alert({ message: __("Already up to date"), indicator: "green" });
						}
					});
				});
		});
	},
});
