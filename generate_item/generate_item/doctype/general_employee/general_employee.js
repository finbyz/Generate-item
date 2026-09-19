// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt

frappe.ui.form.on("General Employee", {
	setup(frm) {
		// Group link inside the Groups child table — filter by is_group=1 + branch (case-insensitive)
		frm.set_query("general_employee", "general_employee_item", function () {
			return {
				query: "generate_item.generate_item.doctype.general_employee.general_employee.general_employee_group_query",
				filters: {
					is_group: 1,
					branch: frm.doc.branch || "",
				},
			};
		});

		frm.add_fetch("general_employee", "department", "department");
	},

	refresh(frm) {
		toggle_group_fields(frm);
	},

	is_group(frm) {
		toggle_group_fields(frm);
	},

	branch(frm) {
		if (frm.doc.branch && frm.doc.general_employee_item) {
			frm.doc.general_employee_item.forEach((row) => {
				if (!row.branch) {
					frappe.model.set_value(row.doctype, row.name, "branch", frm.doc.branch);
				}
			});
		}
	},

	general_employee_item_add(frm, cdt, cdn) {
		if (frm.doc.branch) {
			frappe.model.set_value(cdt, cdn, "branch", frm.doc.branch);
		}
	},
});

frappe.ui.form.on("General Employee Item", {
	general_employee_item_add(frm, cdt, cdn) {
		if (frm.doc.branch) {
			frappe.model.set_value(cdt, cdn, "branch", frm.doc.branch);
		}
	},
});

function toggle_group_fields(frm) {
	const is_group = Boolean(frm.doc.is_group);
	frm.toggle_display("department", is_group);
	frm.toggle_display("section_break_zdfh", !is_group);
	frm.toggle_display("general_employee_item", !is_group);
}
