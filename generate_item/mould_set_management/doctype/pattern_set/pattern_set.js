// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt

frappe.ui.form.on("Pattern Set", {
	onload(frm) {
		load_pattern_set_attribute_options(frm);
	},

	setup(frm) {
		// Filter Item Code to serial-tracked stock items
		let item_filter = function () {
			return {
				filters: {
					disabled: 0,
					is_stock_item: 1,
					has_serial_no: 1,
				},
			};
		};
		frm.set_query("item_code", "items", item_filter);
		frm.set_query("component_item", "items", item_filter);

		// Filter Serial No to Active and Free serials belonging to the row's item
		frm.set_query("serial_no", "items", function (doc, cdt, cdn) {
			let row = locals[cdt][cdn];
			let filters = {
				status: "Active",
				custom_pattern_set: ["in", ["", null]],
			};
			if (row && row.item_code) {
				filters.item_code = row.item_code;
			}
			return { filters: filters };
		});
	},

	refresh(frm) {
		load_pattern_set_attribute_options(frm);
		frm.trigger("render_panels");

		if (frm.doc.docstatus === 1) {
			// Buttons per Section 9.3
			frm.add_custom_button(__("Change Components"), function () {
				frappe.new_doc("Pattern Set Component Change", {
					pattern_set: frm.doc.name,
				});
			});

			frm.add_custom_button(__("Transfer Set"), function () {
				frappe.new_doc("Pattern Set Transfer", {
					pattern_set: frm.doc.name,
				});
			});

			// v2.0 Section 5.3: Users can add open rows on submitted sets!
			frm.fields_dict.items.grid.cannot_add_rows = false;
			// Lock serial_no after submit (only modified via Component Change)
			frm.fields_dict.items.grid.update_docfield_property("serial_no", "read_only", 1);
			frm.refresh_field("items");
		}
	},

	render_panels(frm) {
		if (!frm.is_new() && frm.doc.name) {
			frappe.call({
				method: "generate_item.mould_set_management.doctype.pattern_set.pattern_set.get_set_info_html",
				args: { pattern_set: frm.doc.name },
				callback: function (r) {
					if (r && r.message) {
						frm.set_df_property("set_info", "options", r.message);
						frm.refresh_field("set_info");
					}
				},
			});
		}
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

	bore(frm) {
		update_pattern_set_fields(frm);
	},
});

frappe.ui.form.on("Pattern Set Component", {
	item_code(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.item_code) {
			frappe.model.set_value(cdt, cdn, "component_item", row.item_code);
			fetch_item_and_drawing_info(cdt, cdn, row.item_code);
		}
	},

	component_item(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.component_item) {
			frappe.model.set_value(cdt, cdn, "item_code", row.component_item);
			fetch_item_and_drawing_info(cdt, cdn, row.component_item);
		}
	},

	serial_no(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.serial_no) {
			// Check for duplicate in grid
			let duplicates = (frm.doc.items || []).filter(
				(r) => r.serial_no && r.serial_no === row.serial_no && r.name !== row.name
			);
			if (duplicates.length > 0) {
				frappe.msgprint(__("Serial No {0} is already selected in another row.", [row.serial_no]));
				frappe.model.set_value(cdt, cdn, "serial_no", "");
				frappe.model.set_value(cdt, cdn, "warehouse", "");
				return;
			}

			// Fetch warehouse from Serial No
			frappe.db.get_value("Serial No", row.serial_no, ["warehouse", "item_code"], function (r) {
				if (r) {
					if (row.item_code && r.item_code !== row.item_code) {
						frappe.msgprint(__("Serial No {0} belongs to Item {1}, not {2}.", [row.serial_no, r.item_code, row.item_code]));
						frappe.model.set_value(cdt, cdn, "serial_no", "");
						return;
					}
					frappe.model.set_value(cdt, cdn, "warehouse", r.warehouse || "");
				}
			});
		} else {
			frappe.model.set_value(cdt, cdn, "warehouse", "");
		}
	},

	items_remove(frm, cdt, cdn) {
		// Section 5.3: Delete a row allowed only if serial is blank
		let row = locals[cdt][cdn];
		if (frm.doc.docstatus === 1 && row && row.serial_no) {
			frappe.msgprint(
				__("Cannot delete row with Serial No {0}. A row holding a serial must be detached first through Pattern Set Component Change.", [row.serial_no])
			);
		}
	},
});

function fetch_item_and_drawing_info(cdt, cdn, item_code) {
	frappe.db.get_value(
		"Item",
		item_code,
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
				frappe.model.set_value(cdt, cdn, "item_name", r.item_name);
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

function update_pattern_set_fields(frm) {
	let parts = [];
	if (frm.doc.type_of_valve) parts.push(String(frm.doc.type_of_valve).trim());
	if (frm.doc.size) parts.push(String(frm.doc.size).trim());
	if (frm.doc.class) parts.push(String(frm.doc.class).trim());
	if (frm.doc.bore && String(frm.doc.bore).trim() !== "-") parts.push(String(frm.doc.bore).trim());

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
					bore: frm.doc.bore || null,
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
	load_attribute_options(frm, "bore", ["FG-Bore", "WIP-Bore", "Bore"]);
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
							let allow_dash = fieldname === "bore";
							if (display && (allow_dash || display !== "-") && options.indexOf(display) === -1) {
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
