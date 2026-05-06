// frappe.ui.form.on("Delivery Note", {
//     onload: function(frm) {
//         const is_delivery_user = frappe.user_roles.includes("Delivery User");

//         setTimeout(() => {
//             if (!frm.doc.__islocal && !is_delivery_user) {
//                 set_delivery_fields_readonly(frm, true);
//             }
//         }, 500);
//     },
//     items_on_form_rendered: function(frm) {
//         check_insufficient_items(frm);
//     },
//     refresh(frm) {
//         if (frm.is_new() && frm.doc.items?.some(d => d.against_sales_order)) {
//             validate_and_set_batch_from_sales_order(frm);
//             fetch_and_update_taxes(frm);
//         }
//         const is_delivery_user = frappe.user_roles.includes("Delivery User");

//         if (frm.doc.__islocal) {
//             set_delivery_fields_readonly(frm, false);
//         } else {
//             if (is_delivery_user) {
//                 set_delivery_fields_readonly(frm, false);

//                 frappe.show_alert({
//                     message: __("You can edit items and shipping address as Delivery User"),
//                     indicator: "blue"
//                 }, 3);
//             } else {
//                 set_delivery_fields_readonly(frm, true);

//                 if (frm.doc.items && frm.doc.items.length > 0) {
//                     frappe.show_alert({
//                         message: __("Items and shipping address are locked. Only Delivery Users can modify these fields."),
//                         indicator: "orange"
//                     }, 5);
//                 }
//             }
//         }

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
//                             warehouse: frm.doc.set_warehouse || (frm.doc.items && frm.doc.items.length ? frm.doc.items[0].warehouse : undefined)
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

//     items_add(frm, cdt, cdn) {
//         const row = locals[cdt][cdn];
//         if (frm.is_new() && row.against_sales_order) {
//             validate_and_set_batch_from_sales_order(frm);
//             fetch_and_update_taxes(frm);
//         }
//     },

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
//     if (!frm.is_new() || frm.__setting_batches || !frm.doc.items?.length) return;

//     frm.__setting_batches = true;

//     const items_to_check = frm.doc.items.filter(item => 
//         item.against_sales_order && item.so_detail && !item.custom_batch_no
//     );

//     if (!items_to_check.length) {
//         frm.__setting_batches = false;
//         return;
//     }

//     const items_data = items_to_check.map(item => ({
//         against_sales_order: item.against_sales_order,
//         so_detail: item.so_detail,
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



// function set_delivery_fields_readonly(frm, read_only) {
//     try {
//         // Safety check - don't proceed if form is not ready
//         if (!frm || !frm.fields_dict) {
//             console.log("Form not ready, skipping permission setup");
//             return;
//         }

//         let fields_updated = 0;

//         // Make Items table read-only or editable
//         if (frm.fields_dict["items"] && frm.fields_dict["items"].grid) {
//             const grid = frm.fields_dict["items"].grid;

//             // Wait for grid to be fully loaded
//             if (!grid.grid_rows || grid.grid_rows.length === 0) {
//                 console.log("Grid rows not loaded, retrying...");
//                 setTimeout(() => set_delivery_fields_readonly(frm, read_only), 200);
//                 return;
//             }

//             // Define which fields Delivery Users can edit (if read_only is false)
//             const editable_fields = [
//                 "qty", "batch_no", "serial_no", "warehouse", "custom_batch_no",
//                 "target_warehouse", "quality_inspection", "expense_account"
//             ];

//             // Get all document fields for the grid
//             const docfields = grid.get_docfields ? grid.get_docfields() : [];

//             if (docfields.length > 0) {
//                 // Set fields in items table to read-only based on permissions
//                 docfields.forEach(df => {
//                     try {
//                         // For read-only mode, lock all fields except basic info
//                         // For edit mode, only unlock specific editable fields for Delivery Users
//                         const should_be_readonly = read_only ? 
//                             (df.fieldname !== "item_code" && df.fieldname !== "item_name") : 
//                             !editable_fields.includes(df.fieldname);

//                         frm.fields_dict["items"].grid.update_docfield_property(
//                             df.fieldname,
//                             "read_only",
//                             should_be_readonly ? 1 : 0
//                         );

//                         if (should_be_readonly) fields_updated++;
//                     } catch (fieldError) {
//                         console.warn(`Error updating field ${df.fieldname}:`, fieldError);
//                     }
//                 });
//             } else {
//                 // Fallback: update individual fields directly
//                 editable_fields.forEach(fieldname => {
//                     try {
//                         frm.fields_dict["items"].grid.update_docfield_property(
//                             fieldname,
//                             "read_only",
//                             read_only ? 1 : 0
//                         );
//                         fields_updated++;
//                     } catch (e) {
//                         console.warn(`Error updating ${fieldname}:`, e);
//                     }
//                 });
//             }

//             // Hide grid buttons if read-only
//             if (read_only) {
//                 grid.wrapper.find('.grid-add-row, .grid-remove-rows, .grid-delete-row, .grid-append-row').hide();
//                 if (grid.set_allow_on_grid_editing) {
//                     grid.set_allow_on_grid_editing(false);
//                 }
//             } else {
//                 grid.wrapper.find('.grid-add-row, .grid-remove-rows, .grid-delete-row, .grid-append-row').show();
//                 if (grid.set_allow_on_grid_editing) {
//                     grid.set_allow_on_grid_editing(true);
//                 }
//             }
//         }

//         // Make shipping address fields read-only or editable
//         const shipping_fields = ["shipping_address", "shipping_address_name"];
//         shipping_fields.forEach(fieldname => {
//             if (frm.fields_dict[fieldname]) {
//                 try {
//                     frm.set_df_property(fieldname, "read_only", read_only ? 1 : 0);
//                     fields_updated++;
//                 } catch (e) {
//                     console.warn(`Error updating ${fieldname}:`, e);
//                 }
//             }
//         });

//         // Also lock shipping rule if needed
//         if (frm.fields_dict["shipping_rule"]) {
//             try {
//                 frm.set_df_property("shipping_rule", "read_only", read_only ? 1 : 0);
//                 fields_updated++;
//             } catch (e) {
//                 console.warn("Error updating shipping_rule:", e);
//             }
//         }

//         // Refresh fields to apply changes
//         setTimeout(() => {
//             try {
//                 frm.refresh_field("items");
//                 shipping_fields.forEach(fieldname => {
//                     if (frm.fields_dict[fieldname]) {
//                         frm.refresh_field(fieldname);
//                     }
//                 });
//                 if (frm.fields_dict["shipping_rule"]) {
//                     frm.refresh_field("shipping_rule");
//                 }
//             } catch (refreshError) {
//                 console.warn("Error refreshing fields:", refreshError);
//             }
//         }, 100);

//         console.log(`Delivery Note: ${read_only ? 'Locked' : 'Unlocked'} ${fields_updated} fields for ${frm.doc.__islocal ? 'new' : 'saved'} document`);

//     } catch (error) {
//         console.error("Error in set_delivery_fields_readonly:", error);
//     }
// }


// function check_insufficient_items(frm) {
//     frm.remove_custom_button('Remove Insufficient Items');

//     if (!frm.doc.items || frm.doc.items.length === 0) {
//         return;
//     }

//     const has_insufficient_items = frm.doc.items.some(item => {
//         return item.actual_qty < item.qty;
//     });

//     if (has_insufficient_items) {
//         frm.add_custom_button(__('Remove Insufficient Items'), function() {
//             remove_insufficient_items(frm);
//         }).addClass('btn-danger');
//     }
// }

// function remove_insufficient_items(frm) {
//     let removed_items = [];
//     let valid_items = [];

//     frm.doc.items.forEach(item => {
//         if (item.actual_qty < item.qty) {
//             removed_items.push({
//                 item_code: item.item_code,
//                 item_name: item.item_name,
//                 qty: item.qty,
//                 actual_qty: item.actual_qty,
//                 shortage: item.qty - item.actual_qty,
//                 warehouse: item.warehouse
//             });
//         } else {
//             valid_items.push(item);
//         }
//     });

//     if (removed_items.length > 0) {
//         show_removal_confirmation(frm, removed_items, valid_items);
//     }
// }

// function show_removal_confirmation(frm, removed_items, valid_items) {
//     let msg = `<p>${__('The following items have insufficient stock and will be removed:')}</p><ul>`;
//     removed_items.forEach(item => {
//         msg += `<li>${item.item_name} (${item.item_code}) - Qty: ${item.qty}, Actual: ${item.actual_qty}, Shortage: ${item.shortage} ${frm.doc.currency || ''}</li>`;
//     });
//     msg += `</ul><p>${__('Do you want to continue?')}</p>`;

//     frappe.confirm(msg, function() {
//         // Remove the items and refresh the field
//         frm.doc.items = valid_items;
//         frm.refresh_field('items');
//         frm.dirty();  // Mark the form as dirty to indicate changes
//         check_insufficient_items(frm);  // Re-check to update button visibility
//         frappe.msgprint(__('Insufficient items removed successfully.'));
//     });
// }




















frappe.ui.form.on("Delivery Note", {
    onload: function (frm) {
        apply_permissions(frm);
    },
    // items_on_form_rendered: function(frm) {      
    //     check_insufficient_items(frm);
    // },
    refresh(frm) {
        
        apply_permissions(frm);
        validate_and_set_batch_from_sales_order(frm)
        if (frm.doc.docstatus === 0) {

            check_insufficient_items(frm);



        }
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
                            branch: frm.doc.branch,
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
                                    },
                                    allow_child_item_selection: true,
                                    child_fieldname: "items",
                                    child_columns: [
                                        "item_code",
                                        "item_name",
                                        "qty",
                                        "delivered_qty",
                                        "custom_batch_no",
                                        "custom_shipping_address"
                                        // "description"
                                    ],
                                    child_map: {
                                        "Sales Order Item": {
                                            // source_field_name_on_so_item: target_field_name_on_dn_item
                                            "custom_shipping_address": "shipping_address"
                                        }
                                    }
                                });
                                // frappe.after_ajax(() => {
                                //     update_shipping_address_from_so_items(frm, dispatchable_so_list);
                                // });
                                console.log("dispatchable_so_list-------", dispatchable_so_list)
                            } else {
                                frappe.msgprint(__("No dispatchable Sales Orders found for this customer for branch."));
                            }
                        },
                    });
                },
                __("Get Items From")
            );

              frm.add_custom_button('Append from Dispatchable SO', function() {
                  show_dispatchable_so_dialog(frm);

              })
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
function handle_dispatchable_so(frm) {
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
            warehouse: frm.doc.set_warehouse ||
                (frm.doc.items?.length ? frm.doc.items[0].warehouse : undefined)
        },
        callback(r) {
            if (!r.message?.length) {
                frappe.msgprint(__("No dispatchable Sales Orders found for this customer."));
                return;
            }

            const dispatchable_so_list = r.message.map(so => so.name);

            erpnext.utils.map_current_doc({
                method: "erpnext.selling.doctype.sales_order.sales_order.make_delivery_note",
                args: { for_reserved_stock: 1 },
                source_doctype: "Sales Order",
                target: frm,
                setters: { customer: frm.doc.customer },
                get_query_filters: {
                    name: ["in", dispatchable_so_list],
                    docstatus: 1,
                    status: ["not in", ["Closed", "On Hold"]],
                    per_delivered: ["<", 99.99],
                    company: frm.doc.company,
                },
                allow_child_item_selection: true,
                child_fieldname: "items",
                child_columns: [
                    "item_code",
                    "item_name",
                    "qty",
                    "delivered_qty",
                    "custom_batch_no",
                    "custom_shipping_address"
                ],
                child_map: {
                    "Sales Order Item": {
                        "custom_shipping_address": "shipping_address"
                    }
                }
            });

            // 🔑 Runs after mapping completes
            // frappe.after_ajax(() => {
            //     update_shipping_address_from_so_items(frm, dispatchable_so_list);
            // });
        }
    });
}

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
        callback: function (r) {
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
        callback: function (r) {
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
        error: function (err) {
            frm.__setting_batches = false;
            frappe.msgprint({
                title: __("Error"),
                message: __("Unable to fetch custom batches. Please check permissions or try saving the document."),
                indicator: "orange"
            });
        }
    });
}

function apply_permissions(frm) {
    const roles = frappe.user_roles || [];
    const is_delivery = roles.includes('Delivery User');

    console.log('Delivery User:', is_delivery);

    // ITEMS TABLE PERMISSIONS
    if (frm.fields_dict.items && frm.fields_dict.items.grid) {
        const grid = frm.fields_dict.items.grid;

        // Make entire table read-only by default
        grid.set_column_property_all?.('read_only', 1);

        if (is_delivery) {
            [
                'qty', 'rate', 'amount', 'uom', 'conversion_factor',
                'stock_qty', 'batch_no', 'serial_no', 'custom_batch_no',
                'warehouse', 'target_warehouse', 'quality_inspection',
                'expense_account'
            ].forEach(f => {
                grid.set_column_property?.(f, 'read_only', 0);
            });
        }
    }
}

// function apply_permissions(frm) {
//     const roles = frappe.user_roles || [];
//     const is_delivery = roles.includes('Delivery User');
//     const is_sales    = roles.includes('Sales User');
//     const is_sys_mgr  = roles.includes('System Manager');

//     const can_edit_shipping = is_delivery || is_sales || is_sys_mgr;

//     const can_edit_billing = is_sys_mgr;

//     const can_edit_items = is_delivery;

//     console.log('Delivery User:', is_delivery, 'Sales User:', is_sales, 'System Manager:', is_sys_mgr);
//     console.log('Can edit shipping:', can_edit_shipping, 'Can edit billing:', can_edit_billing);

//     if (frm.fields_dict.items && frm.fields_dict.items.grid) {
//         const grid = frm.fields_dict.items.grid;
//         grid.set_column_property_all?.('read_only', 1);

//         if (can_edit_items) {
//             ['qty','rate','amount','uom','conversion_factor','stock_qty',
//              'batch_no','serial_no','custom_batch_no','warehouse',
//              'target_warehouse','quality_inspection','expense_account'].forEach(f => {
//                 grid.set_column_property?.(f, 'read_only', 0);
//             });
//             grid.wrapper.find('.grid-add-row, .grid-remove-rows, .grid-delete-row').show();
//         } else {
//             grid.wrapper.find('.grid-add-row, .grid-remove-rows, .grid-delete-row').hide();
//         }
//     }

//     const shipping_fields = [
//         'shipping_address_name',
//     ];

//     shipping_fields.forEach(f => {
//         if (frm.fields_dict[f]) {
//             frm.set_df_property(f, 'read_only', can_edit_shipping ? 0 : 1);
//         }
//     });

//     const billing_fields = [
//         'customer_address',
//     ];

//     billing_fields.forEach(f => {
//         if (frm.fields_dict[f]) {
//             frm.set_df_property(f, 'read_only', can_edit_billing ? 0 : 1);
//         }
//     });

//     setTimeout(() => {
//         shipping_fields.forEach(f => frm.fields_dict[f] && frm.refresh_field(f));
//         billing_fields.forEach(f => frm.fields_dict[f] && frm.refresh_field(f));
//     }, 300);
// }


function check_insufficient_items(frm) {
    frm.remove_custom_button('Remove Insufficient Items');
    // Do NOT auto-trigger non-stock removal here.
    // Keep this function limited to showing/hiding the "Remove Insufficient Items" button.

    if (!frm.doc.items || frm.doc.items.length === 0) {
        return;
    }


    const has_insufficient_items = frm.doc.items.some(item => {
        return item.actual_qty < item.qty;
    });

    if (has_insufficient_items) {
        frm.add_custom_button(__('Remove Insufficient Items'), function () {
            remove_insufficient_items(frm);
            // remove_non_stock_items_and_adjust_qty(frm);
        }).addClass('btn-danger');
    }
}

function remove_insufficient_items(frm) {
    if (!frm.doc.items || frm.doc.items.length === 0) return;

    const item_rows = frm.doc.items.filter(item => item.item_code);
    if (item_rows.length === 0) return;

    const checks = item_rows.map(item => {
        return frappe.call({
            method: 'erpnext.stock.doctype.batch.batch.get_batch_qty',
            args: {
                batch_no: item.custom_batch_no || null,
                warehouse: item.warehouse,
                item_code: item.item_code
            }
        }).then(r => {
            const raw = r.message;
            console.log("all batches ------", raw);

            // Normalize: could be null, a number, an object, or an array
            let batches = [];
            if (Array.isArray(raw)) {
                batches = raw;
            } else if (raw !== null && raw !== undefined) {
                // If it's a plain number (qty directly returned)
                if (typeof raw === 'number') {
                    batches = [{ qty: raw }];
                } else if (typeof raw === 'object') {
                    batches = [raw]; // wrap single object in array
                }
            }

            const total_qty = batches.reduce((sum, b) => sum + (flt(b.qty) || 0), 0);
            const no_batch = batches.length === 0 || total_qty <= 0;

            const should_remove = flt(item.actual_qty) < flt(item.qty) || no_batch;

            return { item, should_remove };
        });
    });

    Promise.all(checks).then(results => {
        let removed_items = [];
        let valid_items = [];

        results.forEach(({ item, should_remove }) => {
            if (should_remove) {
                removed_items.push({
                    item_code: item.item_code,
                    item_name: item.item_name,
                    qty: item.qty,
                    actual_qty: item.actual_qty,
                    shortage: item.qty - item.actual_qty,
                    warehouse: item.warehouse
                });
            } else {
                valid_items.push(item);
            }
        });

        if (removed_items.length > 0) {
            show_removal_confirmation(frm, removed_items, valid_items);
        }
    }).catch(err => {
        console.error('Batch fetch error:', err);
    });
}

function show_removal_confirmation(frm, removed_items, valid_items) {
    let msg = `<p>${__('The following items have insufficient stock and will be removed:')}</p><ul>`;
    removed_items.forEach(item => {
        msg += `<li>${item.item_name} (${item.item_code}) - Qty: ${item.qty}, Actual: ${item.actual_qty}, Shortage: ${item.shortage} ${frm.doc.currency || ''}</li>`;
    });
    msg += `</ul><p>${__('Do you want to continue?')}</p>`;

    frappe.confirm(msg, function () {
        frm.doc.items = valid_items;
        frm.refresh_field('items');
        frm.dirty();
        check_insufficient_items(frm);
        frappe.msgprint(__('Insufficient items removed successfully.'));
    });
}

function remove_non_stock_items_and_adjust_qty(frm) {
    if (!frm.doc.items || frm.doc.items.length === 0) {
        return {
            removed_items: [],
            updated_items: []
        };
    }

    frappe.call({
        method: "generate_item.utils.delivery_note.get_stock_items_and_batch_qty",
        args: {
            items: frm.doc.items.map(item => ({
                item_code: item.item_code,
                warehouse: item.warehouse,
                batch_no: item.batch_no || item.custom_batch_no || null,
                qty: item.qty,
                name: item.name
            })),
            posting_date: frm.doc.posting_date,
            posting_time: frm.doc.posting_time
        },
        freeze: false,
        callback: function (r) {
            if (!r.message || r.exc) return;

            const result = r.message;

            let removed_items = [];
            let updated_items = [];
            let items_to_keep = [];

            frm.doc.items.forEach(item => {
                const item_result = result.items_data[item.name];

                if (!item_result) {
                    items_to_keep.push(item);
                    return;
                }

                //  Remove non-stock items
                if (!item_result.is_stock_item) {
                    removed_items.push({
                        item_code: item.item_code,
                        qty: item.qty,
                        reason: "Non-stock item"
                    });
                    return;
                }

                let adjusted_qty = item.qty;

                if (item_result.available_qty !== null &&
                    item_result.available_qty < item.qty) {
                    adjusted_qty = item_result.available_qty;
                }

                if (adjusted_qty <= 0) {
                    removed_items.push({
                        item_code: item.item_code,
                        qty: item.qty,
                        reason: "No stock available"
                    });
                    return;
                }

                if (adjusted_qty !== item.qty) {
                    frappe.model.set_value(
                        item.doctype,
                        item.name,
                        "qty",
                        adjusted_qty
                    );

                    updated_items.push({
                        item_code: item.item_code,
                        old_qty: item.qty,
                        new_qty: adjusted_qty
                    });
                }

                items_to_keep.push(item);
            });

            // Apply final item list
            frm.doc.items = items_to_keep;
            frm.refresh_field("items");

            if (updated_items.length > 0) {
                frm.trigger("calculate_taxes_and_totals");
            }

            frm.dirty();


            frm._stock_cleanup_result = {
                removed_items,
                updated_items
            };
        }
    });
}


// ---------------------------------------------------------------------------
// Entry point — called from form button
// ---------------------------------------------------------------------------
function show_dispatchable_so_dialog(frm) {
    const dialog = new frappe.ui.Dialog({
        title: __('Append from Dispatchable Sales Order'),
        fields: [
            {
                label:       __('Sales Order'),
                fieldname:   'sales_order',
                fieldtype:   'Link',
                options:     'Sales Order',
                reqd:        1,
                description: __('Only dispatchable Sales Orders are shown'),
                get_query() {
                    return {
                        query:   'generate_item.utils.delivery_note.get_dispatchable_so_for_query',
                       
                    };
                },
            },
        ],
        primary_action_label: __('Get Items'),
        primary_action() {
            const so = dialog.get_value('sales_order');
            if (!so) {
                frappe.msgprint(__('Please select a Sales Order'));
                return;
            }
            dialog.hide();
            show_items_selection_dialog(frm, so);
        },
    });

    dialog.show();
}

// ---------------------------------------------------------------------------
// Items selection dialog
// ---------------------------------------------------------------------------
function show_items_selection_dialog(frm, sales_order) {
    // frappe.freeze(__('Fetching items from Sales Order…'));

    frappe.call({
        method:  'generate_item.utils.delivery_note.get_so_items_for_selection',
        args:    { sales_order },
        // always() { frappe.unfreeze(); },
        callback(r) {
            const items = r.message;
            console.log("items", items)

            if (!items || !items.length) {
                frappe.msgprint({
                    title:     __('No Pending Items'),
                    message:   __('This Sales Order has no items with pending delivery or available stock.'),
                    indicator: 'orange',
                });
                return;
            }

            const items_dialog = new frappe.ui.Dialog({
                title: __('Select Items from Sales Order') + ': ' + sales_order,
                size:  'extra-large',
                fields: [
                    {
                        fieldtype: 'HTML',
                        fieldname: 'items_table',
                        label:     __('Sales Order Items'),
                    },
                ],
                primary_action_label: __('Add Selected Items'),
                primary_action() {
                    const selected = get_selected_items(items_dialog, items);
                    if (!selected.length) {
                        frappe.msgprint(__('Please select at least one item to add.'));
                        return;
                    }
                    add_items_to_delivery_note(frm, sales_order, selected);
                    items_dialog.hide();
                },
            });

            items_dialog.fields_dict.items_table.$wrapper.html(
                build_items_table_html(items, sales_order)
            );
            setup_item_selection_handlers(items_dialog, items);
            items_dialog.show();
        },
        error() {
            frappe.msgprint({
                title:     __('Error'),
                message:   __('Failed to fetch items. Please try again.'),
                indicator: 'red',
            });
        },
    });
}

// ---------------------------------------------------------------------------
// Build table HTML
// ---------------------------------------------------------------------------
function build_items_table_html(items, sales_order) {
    const rows = items.map((item, idx) => {
        const max_qty   = Math.min(item.pending_qty, item.available_batch_qty);
        const no_stock  = max_qty <= 0;
        const partial   = !no_stock && max_qty < item.pending_qty;
        const row_style = no_stock ? 'background:#fff3f3;'
                        : partial  ? 'background:#fffaf0;'
                        : '';

        const pending_color = item.pending_qty > 0 ? '#e67e22' : '#27ae60';
        const default_qty   = no_stock ? item.pending_qty : max_qty;

        return `
<tr data-idx="${idx}" style="${row_style}">
    <td style="text-align:center;">
        <input type="checkbox" class="select-item" data-idx="${idx}"
               ${no_stock ? 'disabled' : ''}>
    </td>
    <td style="text-align:center;">${item.idx}</td>
    <td>${frappe.utils.escape_html(item.custom_batch_no)}</td>
    <td>${frappe.utils.escape_html(item.item_code)}</td>
    <td>${frappe.utils.escape_html(item.item_name || '')}</td>
    <td style="text-align:right;">${format_number(item.ordered_qty)}</td>
    <td style="text-align:right;">${format_number(item.delivered_qty)}</td>
    <td style="text-align:right;color:${pending_color};">${format_number(item.pending_qty)}</td>
    <td style="text-align:right;" class="${no_stock ? 'text-danger' : ''}">${format_number(item.available_batch_qty)}</td>
    <td>
        <input type="number"
               class="form-control item-qty" data-idx="${idx}"
               style="text-align:right;padding:5px;"
               value="${format_number(default_qty)}"
               min="0" max="${max_qty}" step="0.01"
               ${no_stock ? 'disabled' : ''}>
    </td>
    <td>${frappe.utils.escape_html(item.uom)}</td>
    <td style="text-align:right;">${format_number(item.rate)}</td>
</tr>`;
    }).join('');

    return `
<div style="margin-bottom:12px;">
    <div class="row">
        <div class="col-md-6">
            <strong>${__('Sales Order')}:</strong> ${frappe.utils.escape_html(sales_order)}
        </div>
        <div class="col-md-6 text-right">
            <button class="btn btn-sm btn-default" id="dn_select_all">${__('Select All')}</button>
            <button class="btn btn-sm btn-default" id="dn_deselect_all">${__('Deselect All')}</button>
        </div>
    </div>
</div>
<div style="max-height:450px;overflow-y:auto;border:1px solid #d1d8dd;border-radius:4px;">
    <table class="table table-bordered" style="margin-bottom:0;">
        <thead style="position:sticky;top:0;background:#f5f5f5;z-index:1;">
            <tr>
                <th style="width:40px;text-align:center;">
                    <input type="checkbox" id="dn_select_all_hdr">
                </th>
                <th style="width:55px;">${__('Line')}</th>
                <th style="width:140px;">${__('Batch No')}</th>
                <th style="width:140px;">${__('Item Code')}</th>
                <th style="min-width:180px;">${__('Item Name')}</th>
                <th style="width:80px;">${__('Ordered')}</th>
                <th style="width:80px;">${__('Delivered')}</th>
                <th style="width:80px;">${__('Pending')}</th>
                <th style="width:90px;">${__('Available')}</th>
                <th style="width:115px;">${__('Qty to Deliver')}</th>
                <th style="width:70px;">${__('UOM')}</th>
                <th style="width:90px;">${__('Rate')}</th>
            </tr>
        </thead>
        <tbody>${rows}</tbody>
    </table>
</div>
<div style="margin-top:12px;padding:10px;background:#f9f9f9;border-radius:4px;">
    <small>
        <strong>${__('Note')}:</strong>
        ${__('Red row = no stock. Yellow row = partial stock. Only rows with stock can be selected.')}
    </small>
</div>`;
}

// ---------------------------------------------------------------------------
// Event handlers (namespaced to prevent accumulation across dialog opens)
// ---------------------------------------------------------------------------
function setup_item_selection_handlers(dialog, items) {
    const $w = dialog.$wrapper;
    const ns = '.dn_so_dialog';

    // Clear any stale handlers before attaching fresh ones
    $w.off(ns);

    // Header checkbox — toggle all enabled rows
    $w.on(`change${ns}`, '#dn_select_all_hdr', function () {
        $w.find('.select-item:not(:disabled)').prop('checked', $(this).is(':checked'));
    });

    // Select All button
    $w.on(`click${ns}`, '#dn_select_all', () => {
        $w.find('.select-item:not(:disabled)').prop('checked', true);
        $w.find('#dn_select_all_hdr').prop('checked', true);
    });

    // Deselect All button
    $w.on(`click${ns}`, '#dn_deselect_all', () => {
        $w.find('.select-item').prop('checked', false);
        $w.find('#dn_select_all_hdr').prop('checked', false);
    });

    // Individual checkbox — keep header in sync
    $w.on(`change${ns}`, '.select-item', function () {
        const total   = $w.find('.select-item:not(:disabled)').length;
        const checked = $w.find('.select-item:not(:disabled):checked').length;
        $w.find('#dn_select_all_hdr').prop('checked', total > 0 && total === checked);
    });

    // Qty input — validate and auto-tick the row checkbox
    $w.on(`change${ns} input${ns}`, '.item-qty', function () {
        const idx     = parseInt($(this).data('idx'), 10);
        const item    = items[idx];
        const max_qty = Math.min(item.pending_qty, item.available_batch_qty);
        let   val     = parseFloat($(this).val()) || 0;

        if (val > max_qty) {
            val = max_qty;
            $(this).val(format_number(max_qty));
            frappe.show_alert({
                message:   __('Quantity capped at available: ') + format_number(max_qty),
                indicator: 'orange',
            });
        } else if (val < 0) {
            val = 0;
            $(this).val(0);
        }

        if (max_qty > 0) {
            $w.find(`.select-item[data-idx="${idx}"]`).prop('checked', val > 0);
            const total   = $w.find('.select-item:not(:disabled)').length;
            const checked = $w.find('.select-item:not(:disabled):checked').length;
            $w.find('#dn_select_all_hdr').prop('checked', total > 0 && total === checked);
        }
    });
}

// ---------------------------------------------------------------------------
// Collect selected rows
// ---------------------------------------------------------------------------
function get_selected_items(dialog, items) {
    const selected = [];
    const $w       = dialog.$wrapper;

    items.forEach((item, idx) => {
        if (!$w.find(`.select-item[data-idx="${idx}"]`).is(':checked')) return;

        const max_qty = Math.min(item.pending_qty, item.available_batch_qty);
        const qty     = parseFloat($w.find(`.item-qty[data-idx="${idx}"]`).val()) || 0;

        if (qty <= 0) return;

        if (qty > max_qty) {
            frappe.msgprint({
                title:     __('Invalid Quantity'),
                message:   __(                                            __('Item {0}: qty {1} exceeds available {2}'),
                              item.item_code, format_number(qty), format_number(max_qty)
                           ),
                indicator: 'red',
            });
            return;
        }

        selected.push({ ...item, qty });
    });

    return selected;
}

// ---------------------------------------------------------------------------
// Add rows to Delivery Note child table
// ---------------------------------------------------------------------------
function add_items_to_delivery_note(frm, sales_order, selected_items) {
    const existing = new Set(
        frm.doc.items
            .filter(r => r.against_sales_order === sales_order && r.so_detail)
            .map(r => r.so_detail)
    );

    let added   = 0;
    let skipped = 0;
    const errors = [];

    selected_items.forEach(sel => {
        if (existing.has(sel.name)) { skipped++; return; }

        try {
            const row = frm.add_child('items');

            // Core fields
            row.item_code         = sel.item_code;
            row.item_name         = sel.item_name;
            row.description       = sel.description;
            row.gst_hsn_code      = sel.gst_hsn_code;
            row.qty               = sel.qty;
            row.uom               = sel.uom;
            row.stock_uom         = sel.stock_uom;
            row.conversion_factor = sel.conversion_factor;
            row.rate              = sel.rate;
            row.amount            = sel.qty * sel.rate;
            row.net_rate          = sel.net_rate;
            row.net_amount        = sel.qty * sel.net_rate;
            row.base_net_rate     = sel.base_net_rate;
            row.base_net_amount   = sel.base_net_amount;
            row.taxable_value     = sel.taxable_value;

            // Links
            row.against_sales_order = sales_order;
            row.so_detail           = sel.name;

            // GST rates
            row.igst_rate = sel.igst_rate || 0;
            row.cgst_rate = sel.cgst_rate || 0;
            row.sgst_rate = sel.sgst_rate || 0;
            row.cess_rate = sel.cess_rate || 0;

            // GST amounts
            if (row.igst_rate > 0) {
                row.igst_amount = (row.net_amount * row.igst_rate) / 100;
            } else {
                row.cgst_amount = (row.net_amount * row.cgst_rate) / 100;
                row.sgst_amount = (row.net_amount * row.sgst_rate) / 100;
            }

            // Warehouse
            row.warehouse = sel.warehouse || frm.doc.set_warehouse;

            // Weight
            row.weight_per_unit = sel.weight_per_unit;
            row.weight_uom      = sel.weight_uom;

            // Optional custom fields
            const optionals = [
                'custom_batch_no', 'branch', 'project', 'cost_center', 'expense_account',
                'custom_drg_and_pur_spec', 'custom_drawing_no', 'custom_drawing_rev_no',
                'custom_pattern_drawing_no', 'custom_pattern_drawing_rev_no',
                'custom_purchase_specification_no', 'custom_purchase_specification_rev_no',
            ];
            optionals.forEach(f => { if (sel[f]) row[f] = sel[f]; });

            added++;

        } catch (err) {
            errors.push(sel.item_code);
            console.error('DN add_child error for', sel.item_code, err);
        }
    });

    // Fix idx after adding items
    frm.doc.items.forEach((item, i) => item.idx = i + 1);
    frm.refresh_field('items');

  

    if (added) frm.trigger('calculate_taxes_and_totals');
}

// ---------------------------------------------------------------------------
// Formatter
// ---------------------------------------------------------------------------
function format_number(v) {
    if (v === undefined || v === null) return '0.00';
    return parseFloat(v).toFixed(2);
}