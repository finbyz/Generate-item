// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt

frappe.ui.form.on("Pattern Set Engineering Change", {
	refresh(frm) {
		if (frm.doc.docstatus === 1 && frm.doc.status === "Approved") {
			frm.add_custom_button(__("View Impacted Sets"), function () {
				let sets = frm.doc.impacted_pattern_sets.map(d => d.pattern_set);
				frappe.set_route("List", "Pattern Set", { name: ["in", sets] });
			});
		}
	}
});

