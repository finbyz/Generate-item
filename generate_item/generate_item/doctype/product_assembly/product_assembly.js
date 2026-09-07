// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt

frappe.ui.form.on("Product Assembly", {
    refresh(frm) {
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
                                options: "Serial No",
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
                    let rows = dialog.fields_dict.items.grid.get_selected_children();

                    if (!rows || !rows.length) {
                        rows = dialog.fields_dict.items.df.data || [];
                    }

                    if (!rows.length) {
                        frappe.msgprint("No rows to add.");
                        return;
                    }

                    rows.forEach(function (row) {
                        let child = frm.add_child("item_serial_number");

                        // Existing values
                        child.item_code = row.item_code;
                        child.batch_no = row.batch;
                        child.serial_number = row.serial_number;
                        child.sales_order = row.sales_order;

                        if (frm.doc.posting_date) {
                            child.date = frm.doc.posting_date;
                        }

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
                                })
                                .catch(function (err) {
                                    console.error("Unable to fetch Item Generator:", row.item_code, err);
                                });
                        }
                    });

                    frm.refresh_field("item_serial_number");
                    dialog.hide();
                }
            });

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
                    method: "generate_item.generate_item.doctype.product_assembly.product_assembly.get_serial_register_items",
                    args: {
                        sales_order: sales_order,
                        batch_number: batch_number
                    },
                    callback: function (r) {
                        console.log(r.message);
                        if (!r.message) {
                            return;
                        }

                        dialog.fields_dict.items.df.data = r.message;
                        dialog.fields_dict.items.refresh();
                    }
                });
            });

            dialog.show();
        });
    },
    posting_date(frm) {
        (frm.doc.item_serial_number || []).forEach(function (row) {
            row.date = frm.doc.posting_date;
        });
        frm.refresh_field("item_serial_number");
    }
});