// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt

frappe.ui.form.on("Component Transfer", {
	setup(frm) {
		// Filter mould_set_item to items that have an active Mould Set
		frm.set_query("mould_set_item", function () {
			return {
				query: "generate_item.mould_set_management.doctype.component_transfer.component_transfer.mould_set_item_query",
			};
		});

		// Filter component to only components linked to selected Mould Set
		frm.set_query("component", function () {
			if (!frm.doc.mould_set) {
				return { filters: { name: ["in", []] } };
			}
			return {
				query: "generate_item.mould_set_management.doctype.component_transfer.component_transfer.component_item_query",
				filters: { mould_set: frm.doc.mould_set },
			};
		});

		// Filter mould_set to active non-disabled Mould Sets
		frm.set_query("mould_set", function () {
			let filters = { docstatus: ["!=", 2], disable: 0 };
			if (frm.doc.mould_set_item) {
				filters.item = frm.doc.mould_set_item;
			}
			return { filters: filters };
		});

		// Warehouse filters
		frm.set_query("to_warehouse", function () {
			let filters = { is_group: 0 };
			if (frm.doc.from_warehouse) {
				filters.name = ["!=", frm.doc.from_warehouse];
			}
			return { filters: filters };
		});

		frm.set_query("from_warehouse", function () {
			let filters = { is_group: 0 };
			if (frm.doc.to_warehouse) {
				filters.name = ["!=", frm.doc.to_warehouse];
			}
			return { filters: filters };
		});

		// Batch filter for items child table
		frm.set_query("batch_no", "items", function (doc, cdt, cdn) {
			let row = locals[cdt][cdn];
			let filters = {};
			if (row && row.component_item) {
				filters.item = row.component_item;
			}
			return { filters: filters };
		});
	},

	refresh(frm) {
		if (frm.doc.docstatus === 1 && frm.doc.stock_entry) {
			frm.add_custom_button(__("View Stock Entry"), function () {
				frappe.set_route("Form", "Stock Entry", frm.doc.stock_entry);
			}, __("Stock"));
		}
	},

	mould_set_item(frm) {
		frm.trigger("fetch_components");
	},

	transfer_type(frm) {
		if (frm.doc.transfer_type === "All Components (Complete Set)") {
			frm.set_value("component", "");
			frm.trigger("fetch_components");
		} else {
			// Clear items until user selects a component
			frm.clear_table("items");
			frm.refresh_field("items");
		}
	},

	component(frm) {
		if (frm.doc.transfer_type === "Specific Component" && frm.doc.component) {
			frm.trigger("fetch_components");
		}
	},

	set_qty(frm) {
		if (frm.doc.mould_set_item) {
			frm.trigger("fetch_components");
		}
	},

	from_warehouse(frm) {
		if (frm.doc.from_warehouse) {
			(frm.doc.items || []).forEach((row) => {
				frappe.model.set_value(row.doctype, row.name, "source_warehouse", frm.doc.from_warehouse);
			});
			frm.trigger("fetch_components");
		}
	},

	to_warehouse(frm) {
		if (frm.doc.to_warehouse) {
			(frm.doc.items || []).forEach((row) => {
				frappe.model.set_value(row.doctype, row.name, "target_warehouse", frm.doc.to_warehouse);
			});
		}
	},

	fetch_components(frm) {
		if (!frm.doc.mould_set_item) {
			frm.set_value("mould_set", "");
			frm.clear_table("items");
			frm.refresh_field("items");
			return;
		}

		frappe.call({
			method: "generate_item.mould_set_management.doctype.component_transfer.component_transfer.get_mould_set_components",
			args: {
				mould_set_item: frm.doc.mould_set_item,
				transfer_type: frm.doc.transfer_type || "All Components (Complete Set)",
				component: frm.doc.component || null,
				set_qty: frm.doc.set_qty || 1.0,
				from_warehouse: frm.doc.from_warehouse || null,
				to_warehouse: frm.doc.to_warehouse || null,
			},
			callback: function (r) {
				if (r.message) {
					frm.set_value("mould_set", r.message.mould_set);
					frm.clear_table("items");
					(r.message.items || []).forEach((item) => {
						let row = frm.add_child("items");
						Object.assign(row, item);
					});
					frm.refresh_field("items");
				}
			},
		});
	},
});
