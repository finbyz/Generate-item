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
		frm.set_query("component_item", "items", function (doc, cdt, cdn) {
			return {
				filters: {
					disabled: 0,
					is_stock_item: 1,
				},
			};
		});
	},

	type_of_valve(frm) {
		update_pattern_set_fields(frm);
	},

	size(frm) {
		update_pattern_set_fields(frm);
	},

	class(frm) {
		update_pattern_set_fields(frm);
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

function update_pattern_set_fields(frm) {
	let parts = [];
	if (frm.doc.type_of_valve) parts.push(String(frm.doc.type_of_valve).trim());
	if (frm.doc.size) parts.push(String(frm.doc.size).trim());
	if (frm.doc.class) parts.push(String(frm.doc.class).trim());

	let clean_name = parts.join(" ").trim();
	frm.set_value("pattern_set_name", clean_name);

	if (frm.is_new()) {
		if (frm.doc.type_of_valve && frm.doc.size && frm.doc.class) {
			frappe.call({
				method: "generate_item.mould_set_management.doctype.pattern_set.pattern_set.get_next_pattern_set_name",
				args: {
					type_of_valve: frm.doc.type_of_valve,
					size: frm.doc.size,
					class_val: frm.doc.class,
					exclude_name: null,
				},
				callback: function (r) {
					if (r && r.message) {
						frm.set_value("naming_series", r.message);
					}
				},
			});
		} else {
			frm.set_value("naming_series", clean_name ? clean_name + "-0001" : "");
		}
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
