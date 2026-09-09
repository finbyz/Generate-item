// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt

frappe.ui.form.on("Valve Testing", {
    setup(frm) {
        frm.set_df_property("naming_series", "options", [
            "",
            "VTES.fiscal.#####",
            "VTER.fiscal.#####",
            "VTEN.fiscal.#####"
        ]);
    },
    onload(frm) {
        if (frm.is_new() && frm.doc.branch) {
            frm.trigger("branch");
        }
    },
    refresh(frm) {
        if (frm.doc.docstatus === 0) {
            frm.add_custom_button("Get Item from Serial Register", function () {

            let dialog = new frappe.ui.Dialog({
                title: "Get Item from Serial Register",
                size: "extra-large",

                fields: [
                    // Search Section
                    {
                        fieldtype: "Section Break",
                        label: "Search"
                    },

                    {
                        fieldname: "sales_order",
                        label: "Sales Order",
                        fieldtype: "Link",
                        options: "Sales Order"
                    },

                    {
                        fieldtype: "Column Break"
                    },

                    {
                        fieldname: "batch_number",
                        label: "Batch Number",
                        fieldtype: "Link",
                        options: "Batch"
                    },

                    {
                        fieldname: "search",
                        label: "Search",
                        fieldtype: "Button"
                    },

                    // Results Section
                    {
                        fieldtype: "Section Break",
                        label: "Serial Register Items"
                    },

                    {
                        fieldname: "selection_toolbar",
                        fieldtype: "HTML"
                    },

                    {
                        fieldname: "items",
                        fieldtype: "Table",
                        cannot_add_rows: true,
                        in_place_edit: false,
                        fields: [
                            {
                                fieldname: "batch",
                                label: "Batch",
                                fieldtype: "Link",
                                options: "Batch",
                                in_list_view: 1,
                                read_only: 1
                            },
                            {
                                fieldname: "serial_number",
                                label: "Serial Number",
                                fieldtype: "Link",
                                options: "Serial Number",
                                in_list_view: 1,
                                read_only: 1
                            },
                            {
                                fieldname: "item_code",
                                label: "Item Code",
                                fieldtype: "Link",
                                options: "Item",
                                in_list_view: 1,
                                read_only: 1
                            },
                            {
                                fieldname: "item_description",
                                label: "Item Description",
                                fieldtype: "Data",
                                in_list_view: 1,
                                read_only: 1
                            },
                            {
                                fieldname: "sales_order",
                                label: "Sales Order",
                                fieldtype: "Link",
                                options: "Sales Order",
                                in_list_view: 1,
                                read_only: 1
                            }
                        ]
                    }
                ],
                primary_action_label: "Add",
                primary_action(values) {
                    let data = dialog.fields_dict.items.df.data || [];
                    let selected_rows = data.filter(function (row) {
                        return !!row.__checked;
                    });

                    if (!selected_rows.length) {
                        frappe.msgprint(__("Please select at least one item to add."));
                        return;
                    }

                    // Existing serial numbers in child table to prevent duplicates
                    let existing_serials = new Set(
                        (frm.doc.item_serial_number || [])
                            .map(function (d) { return d.serial_number; })
                            .filter(Boolean)
                    );

                    let added_count = 0;
                    let duplicate_count = 0;

                    selected_rows.forEach(function (row) {
                        if (row.serial_number && existing_serials.has(row.serial_number)) {
                            duplicate_count++;
                            return;
                        }

                        if (row.serial_number) {
                            existing_serials.add(row.serial_number);
                        }

                        let child = frm.add_child("item_serial_number");

                        // Existing values
                        child.item_code = row.item_code;
                        child.batch_no = row.batch;
                        child.serial_number = row.serial_number;
                        child.sales_order = row.sales_order;

                        if (frm.doc.posting_date) {
                            child.date = frm.doc.posting_date;
                        }

                        added_count++;

                        // Fetch Item Generator details
                        if (row.item_code) {
                            frappe.db.get_doc("Item Generator", row.item_code)
                                .then(function (item_generator) {
                                    if (!item_generator) return;

                                    // Build label -> value map from the generic attribute fields
                                    let attr_map = {};
                                    for (let i = 1; i <= 28; i++) {
                                        let label = item_generator["attribute_" + i];
                                        let value = item_generator["attribute_" + i + "_value"];
                                        if (label) {
                                            attr_map[label.trim()] = value;
                                        }
                                    }

                                    const cdt = child.doctype;
                                    const cdn = child.name;

                                    // Map child table fields to Item Generator's attribute labels
                                    frappe.model.set_value(cdt, cdn, "size", attr_map["Size"]);
                                    frappe.model.set_value(cdt, cdn, "class", attr_map["Rating"]);
                                    frappe.model.set_value(cdt, cdn, "type",  attr_map["Valve Type"]);
                                    frappe.model.set_value(cdt, cdn, "end_connection", attr_map["Ends"]);
                                    frappe.model.set_value(cdt, cdn, "shell_moc", attr_map["Shell MOC"]);
                                    frappe.model.set_value(cdt, cdn, "wedge_plug_ball_disc_moc", attr_map["Ball MOC"]);
                                    frappe.model.set_value(cdt, cdn, "operation", attr_map["Ball Facing"]);
                                    frappe.model.set_value(cdt, cdn, "seat_ringguide_moc", attr_map["Seat Ring(Guide) MOC"]);
                                    frappe.model.set_value(cdt, cdn, "stem_moc", attr_map["Stem MOC"]);
                                    frappe.model.set_value(cdt, cdn, "gasket", attr_map["Gasket"]);
                                    frappe.model.set_value(cdt, cdn, "gland_packing__oring_moc", attr_map["Gland Packing + O'Ring MOC"]);
                                    frappe.model.set_value(cdt, cdn, "fasteners", attr_map["Fasteners"]);
                                    frappe.model.set_value(cdt, cdn, "operation", attr_map["Operator"]);

                                    // Calculate Inspector Inches using Class and Size
                                    let size = attr_map["Size"];
                                    let rating = attr_map["Rating"];
                                    if (size || rating) {
                                        frappe.call({
                                            method: "generate_item.utils.inspector_inches.get_inspector_inches",
                                            args: {
                                                size: size,
                                                rating: rating
                                            },
                                            callback: function (r) {
                                                if (r.message) {
                                                    frappe.model.set_value(cdt, cdn, "inch_factor", r.message.inch_factor || "");
                                                    frappe.model.set_value(cdt, cdn, "value", r.message.value || "");
                                                    frappe.model.set_value(cdt, cdn, "inches", r.message.inches || "");
                                                }
                                            }
                                        });
                                    }
                                })
                                .catch(function (err) {
                                    console.error("Unable to fetch Item Generator:", row.item_code, err);
                                });
                        }
                    });

                    frm.refresh_field("item_serial_number");

                    if (duplicate_count > 0 && added_count === 0) {
                        frappe.msgprint(__("Selected item(s) are already added in the table."));
                    } else if (duplicate_count > 0) {
                        frappe.show_alert({
                            message: __("{0} items added, {1} duplicate item(s) skipped.", [added_count, duplicate_count]),
                            indicator: "orange"
                        });
                    }

                    dialog.hide();
                }
            });

            // Render toolbar HTML
            function render_toolbar() {
                let html = `
                    <div class="selection-action-bar d-flex justify-content-between align-items-center mb-2">
                        <div class="btn-group">
                            <button type="button" class="btn btn-xs btn-default btn-select-all font-weight-bold">
                                <i class="fa fa-check-square-o mr-1"></i> Select All
                            </button>
                            <button type="button" class="btn btn-xs btn-default btn-unselect-all font-weight-bold ml-1">
                                <i class="fa fa-square-o mr-1"></i> Deselect All
                            </button>
                        </div>
                        <div class="selection-status-badge text-muted" style="font-size: 12px;">
                            <span class="badge badge-light border font-weight-normal py-1 px-2">
                                <span class="selected-count">0</span> of <span class="total-count">0</span> selected
                            </span>
                        </div>
                    </div>
                `;
                dialog.fields_dict.selection_toolbar.$wrapper.html(html);

                dialog.fields_dict.selection_toolbar.$wrapper.find(".btn-select-all").on("click", function () {
                    toggle_select_all(true);
                });

                dialog.fields_dict.selection_toolbar.$wrapper.find(".btn-unselect-all").on("click", function () {
                    toggle_select_all(false);
                });
            }

            // Helper to toggle all rows
            function toggle_select_all(checked) {
                let data = dialog.fields_dict.items.df.data || [];
                data.forEach(function (row) {
                    row.__checked = checked ? 1 : 0;
                });

                if (dialog.fields_dict.items.grid) {
                    dialog.fields_dict.items.grid.wrapper
                        .find(".grid-row-check")
                        .prop("checked", !!checked);

                    if (dialog.fields_dict.items.grid.grid_rows) {
                        dialog.fields_dict.items.grid.grid_rows.forEach(function (grid_row) {
                            grid_row.refresh_check();
                        });
                    }
                }

                sync_selection_summary();
            }

            // Sync selection count badge and grid header checkbox based on current row selections
            function sync_selection_summary() {
                let data = dialog.fields_dict.items.df.data || [];
                let total = data.length;
                let selected = data.filter(function (row) {
                    return !!row.__checked;
                }).length;

                dialog.fields_dict.selection_toolbar.$wrapper.find(".selected-count").text(selected);
                dialog.fields_dict.selection_toolbar.$wrapper.find(".total-count").text(total);

                let all_checked = total > 0 && selected === total;
                dialog.fields_dict.items.grid.wrapper
                    .find(".grid-heading-row .grid-row-check")
                    .prop("checked", all_checked);
            }

            // Bind Grid header checkbox click
            dialog.fields_dict.items.grid.wrapper.on("click", ".grid-heading-row .grid-row-check", function () {
                let checked = $(this).prop("checked") ? 1 : 0;
                toggle_select_all(checked);
            });

            // Bind Grid row checkbox click
            dialog.fields_dict.items.grid.wrapper.on("change click", ".grid-body .grid-row-check", function () {
                let docname = $(this).parents(".grid-row:first")?.attr("data-name");
                let is_checked = $(this).prop("checked") ? 1 : 0;
                if (docname && dialog.fields_dict.items.grid.grid_rows_by_docname && dialog.fields_dict.items.grid.grid_rows_by_docname[docname]) {
                    dialog.fields_dict.items.grid.grid_rows_by_docname[docname].doc.__checked = is_checked;
                }
                setTimeout(sync_selection_summary, 50);
            });

            // Filter Sales Order to show only submitted Sales Orders (docstatus = 1)
            dialog.fields_dict.sales_order.get_query = function () {
                let filters = {
                    docstatus: 1
                };
                if (frm.doc.branch) {
                    filters.branch = frm.doc.branch;
                }
                return {
                    filters: filters
                };
            };

            // Filter Batch Number based on Sales Order
            dialog.fields_dict.batch_number.get_query = function () {
                let sales_order = dialog.get_value("sales_order");

                // If Sales Order is selected
                if (sales_order) {
                    return {
                        filters: {
                            reference_name: sales_order
                        }
                    };
                }

                // If no Sales Order is selected
                // show all batches
                return {};
            };

            // When Sales Order changes, clear selected Batch
            dialog.fields_dict.sales_order.$input.on("change", function () {
                dialog.set_value("batch_number", "");
            });

            // Search button
            dialog.fields_dict.search.$input.on("click", function () {

                let sales_order = dialog.get_value("sales_order");
                let batch_number = dialog.get_value("batch_number");

                if (!sales_order && !batch_number) {
                    frappe.msgprint(
                        "Please select Sales Order or Batch Number."
                    );
                    return;
                }

                frappe.call({
                    method: "generate_item.generate_item.doctype.valve_testing.valve_testing.get_serial_register_items",
                    args: {
                        branch: frm.doc.branch || "",
                        sales_order: sales_order,
                        batch_number: batch_number
                    },
                    callback: function (r) {
                        if (!r.message || !r.message.length) {
                            dialog.fields_dict.items.df.data = [];
                            dialog.fields_dict.items.refresh();
                            sync_selection_summary();
                            frappe.msgprint("No items found for the selected criteria.");
                            return;
                        }

                        let items = r.message.map(function (item) {
                            item.__checked = 0;
                            return item;
                        });

                        dialog.fields_dict.items.df.data = items;
                        dialog.fields_dict.items.refresh();
                        sync_selection_summary();
                        dialog.fields_dict.items.grid.wrapper
                            .find(".grid-heading-row .grid-row-check")
                            .prop("checked", false);
                    }
                });
            });

            dialog.show();
            render_toolbar();
            sync_selection_summary();
        });
        }
    },
    posting_date(frm) {
        (frm.doc.item_serial_number || []).forEach(function (row) {
            row.date = frm.doc.posting_date;
        });
        frm.refresh_field("item_serial_number");
    },
    branch(frm) {
        if (!frm.doc.branch) return;

        let series_map = {
            "Sanand": "VTES.fiscal.#####",
            "Rabale": "VTER.fiscal.#####",
            "Nandikoor": "VTEN.fiscal.#####"
        };

        let selected_series = series_map[frm.doc.branch];

        if (frm.is_new() && selected_series) {
            frm.set_value("naming_series", selected_series);
        }
        frm.refresh_field("naming_series");
    }
});

frappe.ui.form.on("Valve Testing Item", {
    size(frm, cdt, cdn) {
        update_inspector_inches(frm, cdt, cdn);
    },
    class(frm, cdt, cdn) {
        update_inspector_inches(frm, cdt, cdn);
    }
});

function update_inspector_inches(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    if (row.size || row.class) {
        frappe.call({
            method: "generate_item.utils.inspector_inches.get_inspector_inches",
            args: {
                size: row.size,
                rating: row.class
            },
            callback: function (r) {
                if (r.message) {
                    frappe.model.set_value(cdt, cdn, "inch_factor", r.message.inch_factor || "");
                    frappe.model.set_value(cdt, cdn, "value", r.message.value || "");
                    frappe.model.set_value(cdt, cdn, "inches", r.message.inches || "");
                }
            }
        });
    }
}
