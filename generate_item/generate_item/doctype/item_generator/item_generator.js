// frappe.ui.form.on("Item Generator", {
//     refresh: function (frm) {    
//         // Apply query for template_name
//         frm.set_query("template_name", function () {
//             return { filters: { disabled: 0 } };
//         });

//         if (frm.clear_custom_buttons) frm.clear_custom_buttons();

//         // 👉 Only allow Close/Closed functionality if is_create_with_sales_order = 1
//         if (frm.doc.is_create_with_sales_order == 1) {
//             if (frm.doc.is_closed == 1) {
//                 // Already closed → lock
//                 lock_form(frm);

//                 const btn = frm.add_custom_button("Closed");
//                 if (btn) {
//                     btn.addClass && btn.addClass("btn-disabled");
//                     btn.prop && btn.prop("disabled", true);
//                 }
//             } else {
//                 // Show "Close" button only if not closed
//                 frm.add_custom_button("Close", function () {
//                     frappe.confirm("Are you sure you want to close this record?", function () {
//                         frm.save()
//                             .then(function () {
//                                 frm.set_value("is_closed", 1);
//                                 return frm.save();
//                             })
//                             .then(function () {
//                                 frappe.msgprint("This record has been closed.");
//                                 frm.reload_doc();
//                             })
//                             .catch(function () {
//                                 frappe.msgprint({
//                                     title: __("Cannot Close"),
//                                     message: __("Please complete all mandatory fields before closing."),
//                                     indicator: "red"
//                                 });
//                             });
//                     });
//                 });
//             }
//         }
//         // Handle localStorage return routing logic
//         try {
//             const raw = localStorage.getItem('ig_return_context');
//             if (!raw) return;
//             if (frm.doc.created_item || frm.doc.item_code) {
//                 frappe.run_serially([
//                     () => frm.script_manager.trigger('after_save')
//                 ]);
//             }
//         } catch (e) {}
//         if (frm.doc.custom_conditional_description 
//             && frm.doc.short_description !== frm.doc.custom_conditional_description) {

//             console.log("Updating short_description on refresh");
//             frm.set_value("short_description", frm.doc.custom_conditional_description);
//         }
//     },

//     template_name: function (frm) {
//         if (!frm.doc.short_description) {
//             frm.set_value("short_description", "");
//         }
//     },

//     after_save: function (frm) {
//         update_sort_desc(frm);
//         try {
//             const raw = localStorage.getItem('ig_return_context');
//             if (!raw) return;

//             const ctx = JSON.parse(raw);
//             if (ctx && ctx.so_name && ctx.cdn) {
//                 const item_code = frm.doc.created_item || frm.doc.item_code;
//                 if (item_code) {
//                     const result = {
//                         so_name: ctx.so_name,
//                         cdn: ctx.cdn,
//                         item_code: item_code
//                     };
//                     localStorage.setItem('ig_return_result', JSON.stringify(result));
//                 }
//                 localStorage.removeItem('ig_return_context');
//                 frappe.set_route('Form', 'Sales Order', ctx.so_name);
//             }
//         } catch (e) {}
//     }
// });

// function lock_form(frm) {
//     frm.set_read_only();
//     frm.disable_save();

//     // Lock all fields including child tables
//     (frm.meta.fields || []).forEach(df => {
//         try {
//             frm.set_df_property(df.fieldname, "read_only", 1);

//             if (df.fieldtype === "Table" && frm.fields_dict[df.fieldname]?.grid) {
//                 let grid = frm.fields_dict[df.fieldname].grid;
//                 grid.wrapper?.find('.grid-add-row, .grid-remove-rows, .grid-delete-row, .grid-append-row').hide();
//                 grid.set_allow_on_grid_editing?.(false);
//                 grid.toolbar?.find('.btn').prop('disabled', true);
//             }
//         } catch (e) {}
//     });

//     // ✅ Hide Save button ONLY if doc is closed and not new
//     if (!frm.is_new() && frm.doc.is_closed == 1) {
//         if (frm.page.set_primary_action) {
//             frm.page.set_primary_action(null);  // remove primary action
//         }
//         $(".btn-primary").remove();  // remove Save button from DOM
//     }
// }


// function update_sort_desc(frm){
//     frappe.call({
//             method:"generate_item.generate_item.doctype.item_generator.item_generator.update_short_description",
//             args: {
//                 "docname": frm.doc.name
//             },
//             callback: function(r) {
//                 if (r.message && r.message.success) {
//                     setTimeout(function() {
//                     frm.set_value("short_description", r.message.short_description);
//                     frm.set_value("custom_conditional_description", r.message.short_description);
//                     frm.refresh_field("short_description");
//                     }, 50); 
                    
//                 }
//             }
//         });
// }

frappe.ui.form.on("Item Generator", {
    refresh: function (frm) {    
        // Apply query for template_name
        frm.set_query("template_name", function () {
            return { filters: { disabled: 0 } };
        });

        if (frm.clear_custom_buttons) frm.clear_custom_buttons();

        // 👉 Only allow Close/Closed functionality if is_create_with_sales_order = 1
        if (frm.doc.is_create_with_sales_order == 1) {
            if (frm.doc.is_closed == 1) {
                // Already closed → lock
                lock_form(frm);

                const btn = frm.add_custom_button("Closed");
                if (btn) {
                    btn.addClass && btn.addClass("btn-disabled");
                    btn.prop && btn.prop("disabled", true);
                }
            } else {
                // Show "Close" button only if not closed
                frm.add_custom_button("Close", function () {
                    frappe.confirm("Are you sure you want to close this record?", function () {
                        frm.save()
                            .then(function () {
                                frm.set_value("is_closed", 1);
                                return frm.save();
                            })
                            .then(function () {
                                frappe.msgprint("This record has been closed.");
                                frm.reload_doc();
                            })
                            .catch(function () {
                                frappe.msgprint({
                                    title: __("Cannot Close"),
                                    message: __("Please complete all mandatory fields before closing."),
                                    indicator: "red"
                                });
                            });
                    });
                });
            }
        }
        
        // Set short_description from custom_conditional_description after 100ms if it exists
        // But only if we're not processing a localStorage return
        try {
            const raw = localStorage.getItem('ig_return_context');
            if (!raw && frm.doc.custom_conditional_description && !frm.doc.__initialSetComplete) {
                console.log("Setting initial short_description from custom_conditional_description");
                frm.doc.__initialSetComplete = true;
                setTimeout(function() {
                    frm.set_value("short_description", frm.doc.custom_conditional_description);
                }, 2000); 
            }
        } catch (e) {}    

        // Handle localStorage return routing logic - DON'T trigger after_save here
        try {
            const raw = localStorage.getItem('ig_return_context');
            if (!raw) return;
            
            // Instead of triggering after_save, directly handle what you need
            if (frm.doc.created_item || frm.doc.item_code) {
                const ctx = JSON.parse(raw);
                if (ctx && ctx.so_name && ctx.cdn) {
                    const item_code = frm.doc.created_item || frm.doc.item_code;
                    if (item_code) {
                        const result = {
                            so_name: ctx.so_name,
                            cdn: ctx.cdn,
                            item_code: item_code
                        };
                        localStorage.setItem('ig_return_result', JSON.stringify(result));
                    }
                    localStorage.removeItem('ig_return_context');
                    frappe.set_route('Form', 'Sales Order', ctx.so_name);
                }
            }
        } catch (e) {}
    },

    template_name: function (frm) {
        frm.set_value("short_description", "");
    },

    after_save: function (frm) {
        // Only update if this is a genuine save, not a refresh-triggered operation
        if (!frm.doc.__fromRefresh) {
            update_sort_desc(frm);
        }
    }
});

function update_sort_desc(frm){
    frappe.call({
        method:"generate_item.generate_item.doctype.item_generator.item_generator.update_short_description",
        args: {
            "docname": frm.doc.name
        },
        callback: function(r) {
            if (r.message && r.message.success) {
                setTimeout(function() {
                    frm.set_value("short_description", r.message.short_description);
                    frm.set_value("custom_conditional_description", r.message.short_description);
                }, 50); 
            }
        }
    });
}

// Add this to handle form refresh events properly
frappe.ui.form.on("Item Generator", "onload", function(frm) {
    frm.doc.__initialSetComplete = false;
    frm.doc.__fromRefresh = false;
});