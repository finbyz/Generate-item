// frappe.ui.form.on("Delivery Note", {
//     refresh(frm) {

//         if (frm.is_new() && frm.doc.items?.some(d => d.against_sales_order)) {
//             validate_and_set_batch_from_sales_order(frm);
//             fetch_and_update_taxes(frm);
//         }
//         const is_delivery_user = frappe.user_roles.includes("Delivery User");

//         frm.fields_dict["items"].grid.update_docfield_property(
//             "qty",
//             "read_only",
//             is_delivery_user ? 0 : 1
//         );

//         frm.fields_dict["items"].grid.refresh();



//         if (
//             !frm.doc.is_return &&
//             (frm.doc.status !== "Closed" || frm.is_new()) &&
//             frm.has_perm("write") &&
//             frappe.model.can_read("Sales Order") &&
//             frm.doc.docstatus === 0
//         ) {
//             frm.add_custom_button(
//                 __("Dispatchable SO"),
//                 function () {
//                     if (!frm.doc.customer) {
//                         frappe.throw({
//                             title: __("Mandatory"),
//                             message: __("Please select a Customer first."),
//                         });
//                         return;
//                     }

//                     frappe.call({
//                         method: "generate_item.utils.delivery_note.get_dispatchable_sales_orders_list",
//                         args: {
//                             customer: frm.doc.customer,
//                             company: frm.doc.company,
//                             project: frm.doc.project,
//                         },
//                         callback: function (r) {
//                             if (r.message && r.message.length > 0) {
//                                 const dispatchable_so_list = r.message.map((so) => so.name);

//                                 erpnext.utils.map_current_doc({
//                                     method: "erpnext.selling.doctype.sales_order.sales_order.make_delivery_note",
//                                     args: { for_reserved_stock: 1 },
//                                     source_doctype: "Sales Order",
//                                     target: frm,
//                                     setters: {
//                                         customer: frm.doc.customer,
//                                     },
//                                     get_query_filters: {
//                                         name: ["in", dispatchable_so_list],
//                                         docstatus: 1,
//                                         status: ["not in", ["Closed", "On Hold"]],
//                                         per_delivered: ["<", 99.99],
//                                         company: frm.doc.company,
//                                         project: frm.doc.project || undefined,
//                                     },
//                                     allow_child_item_selection: true,
//                                     child_fieldname: "items",
//                                     child_columns: [
//                                         "item_code",
//                                         "item_name",
//                                         "qty",
//                                         "delivered_qty",
//                                         "custom_batch_no",
//                                         // "description"
//                                     ],
//                                 });
//                             } else {
//                                 frappe.msgprint(__("No dispatchable Sales Orders found for this customer."));
//                             }
//                         },
//                     });
//                 },
//                 __("Get Items From")
//             );
//         }
//     },
//      onload(frm) {
//         const is_delivery_user = frappe.user_roles.includes("Delivery User");

//         if (is_delivery_user) {
//             frm.set_df_property("customer_address", "read_only", 1);
//         }
//     },
//     items_add(frm, cdt, cdn) {
//         const row = locals[cdt][cdn];
//         if (frm.is_new() && row.against_sales_order) {
//             fetch_and_update_taxes(frm);
//             validate_and_set_batch_from_sales_order(frm);
//         }
//     },

//     // Optional — if user edits an existing row to add sales_order
//     items_on_form_rendered(frm) {
//         if (frm.is_new() && frm.doc.items?.some(d => d.against_sales_order)) {
//             fetch_and_update_taxes(frm);
//             validate_and_set_batch_from_sales_order(frm);
//         }
//     }
// });



// function fetch_and_update_taxes(frm) {
//     if (frm.__fetching_remaining_taxes) return;
//     frm.__fetching_remaining_taxes = true;

//     const sales_orders = [...new Set(
//         frm.doc.items
//             .filter(item => item.against_sales_order)
//             .map(item => item.against_sales_order)
//     )];

//     if (!sales_orders.length) {
//         frappe.msgprint({
//             title: __("No Sales Order"),
//             message: __("No items are linked to a Sales Order."),
//             indicator: "orange"
//         });
//         frm.__fetching_remaining_taxes = false;
//         return;
//     }

//     frappe.call({
//         method: "generate_item.utils.delivery_note.get_remaining_taxes_for_draft",
//         args: {
//             sales_orders: sales_orders,
//             current_dn_name: frm.doc.name || null
//         },
//         freeze: true,
//         freeze_message: __("Fetching remaining taxes..."),
//         callback: function(r) {
//             frm.__fetching_remaining_taxes = false;

//             if (r.message && !r.exc) {
//                 const remaining_taxes = r.message;
//                 let updated = false;

//                 frm.doc.taxes.forEach(tax_row => {
//                     if (tax_row.charge_type === "Actual") {
//                         const account_head = tax_row.account_head;
//                         if (remaining_taxes[account_head] !== undefined) {
//                             const remaining_amount = remaining_taxes[account_head];
//                             frappe.model.set_value(
//                                 tax_row.doctype,
//                                 tax_row.name,
//                                 "tax_amount",
//                                 remaining_amount
//                             );
//                             updated = true;
//                         }
//                     }
//                 });

//                 if (updated) {
//                     frm.trigger("calculate_taxes_and_totals");
//                     frm.refresh_field("taxes");
//                     frappe.show_alert({
//                         message: __("Actual taxes adjusted successfully!"),
//                         indicator: "green"
//                     }, 5);
//                 }
//             }
//         }
//     });
// }


// function validate_and_set_batch_from_sales_order(frm) {
//     if (!frm.is_new() || frm.__setting_batches) return;
//     frm.__setting_batches = true;

//     const items_to_check = frm.doc.items.filter(item => 
//         item.against_sales_order && !item.custom_batch_no
//     );

//     if (!items_to_check.length) {
//         frm.__setting_batches = false;
//         return;
//     }

//     const items_data = items_to_check.map(item => ({
//         against_sales_order: item.against_sales_order,
//         item_code: item.item_code,
//         item_name: item.item_name,
//         dn_item_name: item.name
//     }));

//     frappe.call({
//         method: "generate_item.utils.delivery_note.get_custom_batches_for_dn_items",
//         args: {
//             items_data: items_data
//         },
//         freeze: true,
//         freeze_message: __("Fetching custom batches..."),
//         callback: function(r) {
//             frm.__setting_batches = false;

//             if (r.message && !r.exc) {
//                 const batches = r.message;
//                 let updated_count = 0;

//                 Object.entries(batches).forEach(([dn_item_name, batch_no]) => {
//                     const row = frm.doc.items.find(it => it.name === dn_item_name);
//                     if (row && batch_no) {
//                         frappe.model.set_value(row.doctype, row.name, "custom_batch_no", batch_no);
//                         updated_count++;
//                     }
//                 });

//                 if (updated_count > 0) {
//                     frm.refresh_field("items");
//                     frappe.show_alert({
//                         message: __(`${updated_count} custom batch(es) set successfully!`),
//                         indicator: "green"
//                     }, 3);
//                 }
//             }
//         },
//         error: function(err) {
//             frm.__setting_batches = false;
//             frappe.msgprint({
//                 title: __("Error"),
//                 message: __("Unable to fetch custom batches. Please check permissions or try saving the document."),
//                 indicator: "orange"
//             });
//         }
//     });
// }

frappe.ui.form.on("Delivery Note", {
    refresh(frm) {
        if (frm.is_new() && frm.doc.items?.some(d => d.against_sales_order)) {
            validate_and_set_batch_from_sales_order(frm);
            fetch_and_update_taxes(frm);
        }
        const is_delivery_user = frappe.user_roles.includes("Delivery User");

        frm.fields_dict["items"].grid.update_docfield_property(
            "qty",
            "read_only",
            is_delivery_user ? 0 : 1
        );

        frm.fields_dict["items"].grid.refresh();

        if (
            !frm.doc.is_return &&
            (frm.doc.status !== "Closed" || frm.is_new()) &&
            frm.has_perm("write") &&
            frappe.model.can_read("Sales Order") &&
            frm.doc.docstatus === 0
        ) {
            frm.add_custom_button(
                __("Dispatchable SO"),
                function () {
                    if (!frm.doc.customer) {
                        frappe.throw({
                            title: __("Mandatory"),
                            message: __("Please select a Customer first."),
                        });
                        return;
                    }

                    frappe.call({
                        method: "generate_item.utils.delivery_note.get_dispatchable_sales_orders_list",
                        args: {
                            customer: frm.doc.customer,
                            company: frm.doc.company,
                            project: frm.doc.project,
                            warehouse: frm.doc.set_warehouse || (frm.doc.items && frm.doc.items.length ? frm.doc.items[0].warehouse : undefined)
                        },
                        callback: function (r) {
                            if (r.message && r.message.length > 0) {
                                const dispatchable_so_list = r.message.map((so) => so.name);

                                erpnext.utils.map_current_doc({
                                    method: "erpnext.selling.doctype.sales_order.sales_order.make_delivery_note",
                                    args: { for_reserved_stock: 1 },
                                    source_doctype: "Sales Order",
                                    target: frm,
                                    setters: {
                                        customer: frm.doc.customer,
                                    },
                                    get_query_filters: {
                                        name: ["in", dispatchable_so_list],
                                        docstatus: 1,
                                        status: ["not in", ["Closed", "On Hold"]],
                                        per_delivered: ["<", 99.99],
                                        company: frm.doc.company,
                                        project: frm.doc.project || undefined,
                                    },
                                    allow_child_item_selection: true,
                                    child_fieldname: "items",
                                    child_columns: [
                                        "item_code",
                                        "item_name",
                                        "qty",
                                        "delivered_qty",
                                        "custom_batch_no",
                                        // "description"
                                    ],
                                });
                            } else {
                                frappe.msgprint(__("No dispatchable Sales Orders found for this customer."));
                            }
                        },
                    });
                },
                __("Get Items From")
            );
        }
    },
    onload(frm) {
        const is_delivery_user = frappe.user_roles.includes("Delivery User");

        if (is_delivery_user) {
            frm.set_df_property("customer_address", "read_only", 1);
        }
    },
    items_add(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (frm.is_new() && row.against_sales_order) {
            validate_and_set_batch_from_sales_order(frm);
            fetch_and_update_taxes(frm);
        }
    },

});

function fetch_and_update_taxes(frm) {
    if (frm.__fetching_remaining_taxes) return;
    frm.__fetching_remaining_taxes = true;

    const sales_orders = [...new Set(
        frm.doc.items
            .filter(item => item.against_sales_order)
            .map(item => item.against_sales_order)
    )];

    if (!sales_orders.length) {
        frappe.msgprint({
            title: __("No Sales Order"),
            message: __("No items are linked to a Sales Order."),
            indicator: "orange"
        });
        frm.__fetching_remaining_taxes = false;
        return;
    }

    frappe.call({
        method: "generate_item.utils.delivery_note.get_remaining_taxes_for_draft",
        args: {
            sales_orders: sales_orders,
            current_dn_name: frm.doc.name || null
        },
        freeze: true,
        freeze_message: __("Fetching remaining taxes..."),
        callback: function(r) {
            frm.__fetching_remaining_taxes = false;

            if (r.message && !r.exc) {
                const remaining_taxes = r.message;
                let updated = false;

                frm.doc.taxes.forEach(tax_row => {
                    if (tax_row.charge_type === "Actual") {
                        const account_head = tax_row.account_head;
                        if (remaining_taxes[account_head] !== undefined) {
                            const remaining_amount = remaining_taxes[account_head];
                            frappe.model.set_value(
                                tax_row.doctype,
                                tax_row.name,
                                "tax_amount",
                                remaining_amount
                            );
                            updated = true;
                        }
                    }
                });

                if (updated) {
                    frm.trigger("calculate_taxes_and_totals");
                    frm.refresh_field("taxes");
                    frappe.show_alert({
                        message: __("Actual taxes adjusted successfully!"),
                        indicator: "green"
                    }, 5);
                }
            }
        }
    });
}

function validate_and_set_batch_from_sales_order(frm) {
    if (!frm.is_new() || frm.__setting_batches || !frm.doc.items?.length) return;

    frm.__setting_batches = true;

    const items_to_check = frm.doc.items.filter(item => 
        item.against_sales_order && item.so_detail && !item.custom_batch_no
    );

    if (!items_to_check.length) {
        frm.__setting_batches = false;
        return;
    }

    const items_data = items_to_check.map(item => ({
        against_sales_order: item.against_sales_order,
        so_detail: item.so_detail,
        item_code: item.item_code,
        item_name: item.item_name,
        dn_item_name: item.name
    }));

    frappe.call({
        method: "generate_item.utils.delivery_note.get_custom_batches_for_dn_items",
        args: {
            items_data: items_data
        },
        freeze: true,
        freeze_message: __("Fetching custom batches..."),
        callback: function(r) {
            frm.__setting_batches = false;

            if (r.message && !r.exc) {
                const batches = r.message;
                let updated_count = 0;

                Object.entries(batches).forEach(([dn_item_name, batch_no]) => {
                    const row = frm.doc.items.find(it => it.name === dn_item_name);
                    if (row && batch_no) {
                        frappe.model.set_value(row.doctype, row.name, "custom_batch_no", batch_no);
                        updated_count++;
                    }
                });

                if (updated_count > 0) {
                    frm.refresh_field("items");
                    frappe.show_alert({
                        message: __(`${updated_count} custom batch(es) set successfully!`),
                        indicator: "green"
                    }, 3);
                }
            }
        },
        error: function(err) {
            frm.__setting_batches = false;
            frappe.msgprint({
                title: __("Error"),
                message: __("Unable to fetch custom batches. Please check permissions or try saving the document."),
                indicator: "orange"
            });
        }
    });
}