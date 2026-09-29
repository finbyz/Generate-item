// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt

frappe.ui.form.on("Pattern Set", {
	onload(frm) {
		load_pattern_set_attribute_options(frm);
	},

	refresh(frm) {
		load_pattern_set_attribute_options(frm);
	},

	setup(frm) {
		frm.set_query("item", function () {
			return {
				filters: {
					disabled: 0,
					is_stock_item: 1,
				},
			};
		});

		frm.set_query("component_item", "items", function (doc, cdt, cdn) {
			let filters = {
				disabled: 0,
				is_stock_item: 1,
			};
			if (doc.item) {
				filters.name = ["!=", doc.item];
			}
			return { filters: filters };
		});
	},

	type_of_valve(frm) {
		update_pattern_set_name(frm);
	},

	size(frm) {
		update_pattern_set_name(frm);
	},

	class(frm) {
		update_pattern_set_name(frm);
	},

	is_default(frm) {
		if (frm.doc.is_default) {
			if (frm.doc.disable) {
				frm.set_value("disable", 0);
			}
			if (frm.doc.item) {
				frappe.show_alert({
					message: __("Setting this as Default will disable all other Pattern Sets for Item {0}.", [frm.doc.item]),
					indicator: "orange",
				});
			}
		}
	},

	disable(frm) {
		if (frm.doc.disable && frm.doc.is_default) {
			frm.set_value("is_default", 0);
		}
	},

	item(frm) {
		if (frm.doc.item) {
			frappe.db.get_value(
				"Item",
				frm.doc.item,
				["item_name", "description"],
				function (r) {
					if (r) {
						frm.set_value("item_name", r.item_name);
						frm.set_value("description", r.description);
					}
				}
			);
		} else {
			frm.set_value("item_name", "");
			frm.set_value("description", "");
		}
	},
});

frappe.ui.form.on("Pattern Set Component", {
	component_item(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.component_item) {
			frappe.db.get_value(
				"Item",
				row.component_item,
				[
					"item_name",
					"stock_uom",
					"custom_drawing_no",
					"custom_drawing_rev_no",
					"custom_pattern_drawing_no",
					"custom_pattern_drawing_rev_no",
				],
				function (r) {
					if (r) {
						frappe.model.set_value(cdt, cdn, "component_name", r.item_name);
						frappe.model.set_value(cdt, cdn, "uom", r.stock_uom);
						frappe.model.set_value(cdt, cdn, "drawing_no", r.custom_drawing_no || "");
						frappe.model.set_value(cdt, cdn, "drawing_rev_no", r.custom_drawing_rev_no || "");
						frappe.model.set_value(cdt, cdn, "pattern_drawing_no", r.custom_pattern_drawing_no || "");
						frappe.model.set_value(cdt, cdn, "pattern_drawing_rev_no", r.custom_pattern_drawing_rev_no || "");
					}
				}
			);
		}
	},
});

function update_pattern_set_name(frm) {
	let parts = [];
	if (frm.doc.type_of_valve) parts.push(String(frm.doc.type_of_valve).trim());
	if (frm.doc.size) parts.push(String(frm.doc.size).trim());
	if (frm.doc.class) parts.push(String(frm.doc.class).trim());

	let name = parts.join(" ").trim();
	if (name) {
		frm.set_value("pattern_set_name", name);
	}
}

function load_pattern_set_attribute_options(frm) {
	load_attribute_options(frm, "type_of_valve", ["WIP-Type Of Valve", "FG-Valve Type", "Type Of Valve"]);
	load_attribute_options(frm, "size", ["WIP-Size", "FG-Size", "Size"]);
	load_attribute_options(frm, "class", ["WIP-Class", "FG-Rating", "Class"]);
}

function load_attribute_options(frm, fieldname, possible_attr_names) {
	function try_load(idx) {
		if (idx >= possible_attr_names.length) return;
		let attr_name = possible_attr_names[idx];
		frappe.call({
			method: "frappe.client.get",
			args: {
				doctype: "Custom Item Attribute",
				name: attr_name,
			},
			callback: function (r) {
				if (r && r.message && r.message.logic_table && r.message.logic_table.length) {
					let options = [""];
					let rows = r.message.logic_table;
					for (let i = 0; i < rows.length; i++) {
						let row = rows[i];
						if (row && row.disabled == 0) {
							let display = String(row.item_long_description || "").trim();
							if (display && display !== "-" && options.indexOf(display) === -1) {
								options.push(display);
							}
						}
					}
					frm.set_df_property(fieldname, "options", options);
					frm.refresh_field(fieldname);
				} else {
					try_load(idx + 1);
				}
			},
			error: function () {
				try_load(idx + 1);
			},
		});
	}
	try_load(0);
}

