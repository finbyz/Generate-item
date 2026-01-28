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
    onload: function(frm) {
        apply_permissions(frm);
    },
    // items_on_form_rendered: function(frm) {      
    //     check_insufficient_items(frm);
    // },
    refresh(frm) {
        apply_permissions(frm);
        validate_and_set_batch_from_sales_order(frm)
        if( frm.doc.docstatus === 0){

            check_insufficient_items(frm);
            remove_non_stock_items_and_adjust_qty(frm);
            
           
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
                                console.log(dispatchable_so_list)
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
   
    if (!frm.doc.items || frm.doc.items.length === 0) {
        return;
    }
   
    const has_insufficient_items = frm.doc.items.some(item => {
        return item.actual_qty < item.qty;
    });
   
    if (has_insufficient_items) {
        frm.add_custom_button(__('Remove Insufficient Items'), function() {
            remove_insufficient_items(frm);
        }).addClass('btn-danger');
    }
}



function remove_insufficient_items(frm) {
    let removed_items = [];
    let valid_items = [];
   
    frm.doc.items.forEach(item => {
        if (item.actual_qty < item.qty) {
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
}


function show_removal_confirmation(frm, removed_items, valid_items) {
    let msg = `<p>${__('The following items have insufficient stock and will be removed:')}</p><ul>`;
    removed_items.forEach(item => {
        msg += `<li>${item.item_name} (${item.item_code}) - Qty: ${item.qty}, Actual: ${item.actual_qty}, Shortage: ${item.shortage} ${frm.doc.currency || ''}</li>`;
    });
    msg += `</ul><p>${__('Do you want to continue?')}</p>`;

    frappe.confirm(msg, function() {
        frm.doc.items = valid_items;
        frm.refresh_field('items');
        frm.dirty(); 
        check_insufficient_items(frm); 
        frappe.msgprint(__('Insufficient items removed successfully.'));
    });
}

function remove_non_stock_items_and_adjust_qty(frm) {
    if (!frm.doc.items || frm.doc.items.length === 0) {
        frappe.msgprint({
            title: __('No Items'),
            message: __('No items found in Delivery Note.'),
            indicator: 'orange'
        });
        return;
    }

    frappe.call({
        method: "generate_item.utils.delivery_note.get_stock_items_and_batch_qty",
        args: {
            items: frm.doc.items.map(item => ({
                item_code: item.item_code,
                warehouse: item.warehouse,
                batch_no: item.batch_no || item.custom_batch_no || null,
                qty: item.qty,
                name: item.name,
                item_name: item.item_name
            })),
            posting_date: frm.doc.posting_date,
            posting_time: frm.doc.posting_time
        },
        freeze: true,
        freeze_message: __('Checking stock items and batch quantities...'),
        callback: function(r) {
            if (r.message && !r.exc) {
                const result = r.message;
                let removed_items = [];
                let updated_items = [];
                let items_to_keep = [];

                frm.doc.items.forEach(item => {
                    const item_result = result.items_data[item.name];
                    
                    if (!item_result) {
                        // Item not found in result, keep as is
                        items_to_keep.push(item);
                        return;
                    }

                    // Remove non-stock items
                    if (!item_result.is_stock_item) {
                        removed_items.push({
                            item_code: item.item_code,
                            item_name: item.item_name,
                            qty: item.qty,
                            reason: __('Non-stock item')
                        });
                        return;
                    }

                    // For stock items, adjust quantity based on batch-wise stock
                    let adjusted_qty = item.qty;
                    let qty_adjusted = false;
                    let adjustment_reason = '';

                    if (item_result.batch_no && item_result.available_qty !== null) {
                        if (item_result.available_qty < item.qty) {
                            adjusted_qty = item_result.available_qty;
                            qty_adjusted = true;
                            adjustment_reason = __(`Batch {0} has only {1} available (requested: {2})`, 
                                [item_result.batch_no, item_result.available_qty, item.qty]);
                        }
                    } else if (!item_result.batch_no && item_result.available_qty !== null) {
                        // Item without batch - check general stock
                        if (item_result.available_qty < item.qty) {
                            adjusted_qty = item_result.available_qty;
                            qty_adjusted = true;
                            adjustment_reason = __(`Warehouse has only {0} available (requested: {1})`, 
                                [item_result.available_qty, item.qty]);
                        }
                    }

                    if (qty_adjusted && adjusted_qty <= 0) {
                        // Remove item if adjusted quantity is zero or negative
                        removed_items.push({
                            item_code: item.item_code,
                            item_name: item.item_name,
                            qty: item.qty,
                            reason: adjustment_reason || __('No stock available')
                        });
                    } else {
                        // Update item quantity if adjusted
                        if (qty_adjusted) {
                            frappe.model.set_value(item.doctype, item.name, 'qty', adjusted_qty);
                            updated_items.push({
                                item_code: item.item_code,
                                item_name: item.item_name,
                                old_qty: item.qty,
                                new_qty: adjusted_qty,
                                reason: adjustment_reason
                            });
                        }
                        items_to_keep.push(item);
                    }
                });

                // Show confirmation dialog
                let msg = '';
                if (removed_items.length > 0 || updated_items.length > 0) {
                    msg += '<p><b>' + __('The following changes will be made:') + '</b></p>';
                    
                    if (removed_items.length > 0) {
                        msg += '<p><b>' + __('Items to be removed (Non-stock or zero stock):') + '</b></p><ul>';
                        removed_items.forEach(item => {
                            msg += `<li>${item.item_name} (${item.item_code}) - Qty: ${item.qty} - ${item.reason}</li>`;
                        });
                        msg += '</ul>';
                    }

                    if (updated_items.length > 0) {
                        msg += '<p><b>' + __('Items with adjusted quantities:') + '</b></p><ul>';
                        updated_items.forEach(item => {
                            msg += `<li>${item.item_name} (${item.item_code}) - Qty: ${item.old_qty} → ${item.new_qty} - ${item.reason}</li>`;
                        });
                        msg += '</ul>';
                    }

                    msg += '<p>' + __('Do you want to continue?') + '</p>';

                    frappe.confirm(msg, function() {
                        // Update quantities first
                        items_to_update.forEach(update_info => {
                            frappe.model.set_value(
                                update_info.item.doctype,
                                update_info.item.name,
                                'qty',
                                update_info.new_qty
                            );
                        });
                        
                        // Remove non-stock items
                        frm.doc.items = items_to_keep;
                        frm.refresh_field('items');
                        
                        // Trigger recalculation
                        if (items_to_update.length > 0) {
                            frm.trigger('calculate_taxes_and_totals');
                        }
                        
                        frm.dirty();
                        
                        let success_msg = '';
                        if (removed_items.length > 0) {
                            success_msg += __('Removed {0} non-stock item(s). ', [removed_items.length]);
                        }
                        if (updated_items.length > 0) {
                            success_msg += __('Adjusted quantities for {0} item(s).', [updated_items.length]);
                        }
                        if (success_msg) {
                            frappe.show_alert({
                                message: success_msg,
                                indicator: 'green'
                            }, 5);
                        }
                    });
                } else {
                    frappe.msgprint({
                        title: __('No Changes Needed'),
                        message: __('All items are stock items with sufficient batch-wise stock.'),
                        indicator: 'green'
                    });
                }
            }
        },
        error: function(err) {
            frappe.msgprint({
                title: __('Error'),
                message: __('Unable to check stock items. Please try again.'),
                indicator: 'red'
            });
        }
    });
}