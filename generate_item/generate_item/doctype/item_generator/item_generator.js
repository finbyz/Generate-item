// frappe.ui.form.on("Item Generator", {
//     onload: function(frm) {
//         // Initialize flags and meta objects
//         frm.__attribute_meta__ = {};
//         frm.__attribute_meta_loaded__ = false;
//         frm.doc.__initialSetComplete = false;
//         frm.doc.__fromRefresh = false;
        
//         // Reset attribute fields without forcing
//         reset_attribute_fields(frm, false);

//         // Load template attributes if template is already selected
//         if (frm.doc.template_name) {
//             load_template_attributes(frm, frm.doc.template_name, true);
//         }

//         // Clear stale sessionStorage if not linked to Sales Order
//         if (!frm.doc.is_create_with_sales_order) {
//             sessionStorage.removeItem('ig_return_context');
//             console.log("Cleared ig_return_context from sessionStorage for normal Item Generator");
//         }
//     },

//     refresh: function(frm) {
//         // Apply query for template_name
//         frm.set_query("template_name", function() {
//             return { filters: { disabled: 0 } };
//         });

//         if (frm.clear_custom_buttons) frm.clear_custom_buttons();

//         // Only allow Close/Closed functionality if is_create_with_sales_order = 1
//         if (frm.doc.is_create_with_sales_order == 1) {
//             if (frm.doc.is_closed == 1) {
//                 lock_form(frm);

//                 const btn = frm.add_custom_button("Closed");
//                 if (btn) {
//                     btn.addClass && btn.addClass("btn-disabled");
//                     btn.prop && btn.prop("disabled", true);
//                 }
//             } else {
//                 // Clear existing primary action
//                 if (frm.page && frm.page.set_primary_action) {
//                     frm.page.set_primary_action(null);
//                 }
//                 // Hide default Save button
//                 if (frm.page && frm.page.btn_primary && frm.page.btn_primary.is(':visible')) {
//                     frm.page.btn_primary.hide();
//                 }
//                 // Show "Save and Close" button
//                 frm.add_custom_button("Save And Close", function() {
//                     let dialog = frappe.confirm(
//                         "Are you sure you want to Save And Close this record?",
//                         function() {
//                             if (frm.is_valid && !frm.is_valid()) {
//                                 frappe.msgprint({
//                                     title: __("Cannot Close"),
//                                     message: __("Please complete all mandatory fields before closing."),
//                                     indicator: "red"
//                                 });
//                                 dialog.hide();
//                                 return;
//                             }

//                             // FIRST: Save the document normally
//                             frm.save().then(() => {
//                                 // Set is_closed flag to 1
//                                 return frm.set_value("is_closed", 1);
//                             }).then(() => {
//                                 // Save again to persist the is_closed flag
//                                 return frm.save();
//                             }).then(() => {
//                                 // Lock the form to make it read-only
//                                 lock_form(frm);
                                
//                                 // AFTER successful save, trigger after_save logic
//                                 console.log("Document saved and closed, now executing after_save logic");
                                                                
//                                 frappe.show_alert("This record has been saved and closed.");
                                
//                                 // Reload to ensure form is properly locked
//                                 frm.reload_doc();
//                             }).catch(function(err) {
//                                 frappe.msgprint({
//                                     title: __("Save Error"),
//                                     message: __("Failed to save the document: " + err.message),
//                                     indicator: "red"
//                                 });
//                                 dialog.hide();
//                                 console.error("Save error:", err);
//                             });
//                         },
//                         function() {
//                             dialog.hide();
//                         }
//                     );
//                 });
//             }
//         } else {
//             // Ensure Save button is available/visible
//             try {
//                 frm.enable_save && frm.enable_save();
//                 if (frm.page && frm.page.set_primary_action) {
//                     frm.page.set_primary_action(__('Save'), function() {
//                         frm.save().then(function() {
//                             frappe.show_alert("Document saved successfully.");
//                             frm.refresh();
//                         }).catch(function(err) {
//                             frappe.msgprint({
//                                 title: __("Save Error"),
//                                 message: __("Failed to save the document. Please try again."),
//                                 indicator: "red"
//                             });
//                             console.error("Save error:", err);
//                         });
//                     });
//                 }
//                 if (frm.page && frm.page.btn_primary && !frm.page.btn_primary.is(':visible')) {
//                     frm.page.btn_primary.show();
//                 }
//             } catch (e) {
//                 console.error("Error setting save button:", e);
//             }
//         }

//         // Avoid setting values that mark form as dirty
//         if (
//             frm.doc.custom_conditional_description &&
//             frm.doc.short_description !== frm.doc.custom_conditional_description &&
//             !frm.doc.__islocal &&
//             !frm.doc.__unsaved
//         ) {
//             frm.set_value("short_description", frm.doc.custom_conditional_description).then(() => {
//                 frm.refresh_field("short_description");
//             });
//         }

//         // Initialize attribute meta if not already done
//         if (!frm.__attribute_meta_initialized) {
//             frm.__attribute_meta__ = {};
//             frm.__attribute_meta_loaded__ = false;
//             frm.__attribute_meta_initialized = true;
//         }

//         // Load template attributes if template is selected
//         if (frm.doc.template_name && !frm.__attribute_meta_loaded__) {
//             load_template_attributes(frm, frm.doc.template_name, true);
//         } else if (frm.__attribute_meta_loaded__ && frm.doc.__islocal) {
//             generate_fields(frm);
//         }
//     },

//     after_save: function(frm) {
//         // Prevent duplicate triggers
//         if (frm.__after_save_lock) {
//             console.log("Skipping after_save due to lock");
//             return;
//         }
//         frm.__after_save_lock = true;

//         console.log("Entering after_save for Item Generator:", frm.doc.name);

//         // Only process if this is a Sales Order linked document
//         if (frm.doc.is_create_with_sales_order !== 1) {
//             frm.__after_save_lock = false;
//             return;
//         }

//         // Get the item code that should be created
//         let item_code = frm.doc.created_item || frm.doc.item_code;
//         if (!item_code) {
//             console.log("No item code found, releasing lock");
//             frm.__after_save_lock = false;
//             return;
//         }

//         console.log("Item code to verify:", item_code);

//         // Check if this is a Sales Order linked Item Generator
//         let context = null;
//         try {
//             const raw = sessionStorage.getItem('ig_return_context');
//             if (raw) {
//                 context = JSON.parse(raw);
//                 console.log("Sales Order context found:", context);
//             }
//         } catch (e) {
//             console.error("Error parsing context:", e);
//             frm.__after_save_lock = false;
//             return;
//         }

//         if (!context || !context.so_name) {
//             console.log("No valid Sales Order context found");
//             frm.__after_save_lock = false;
//             return;
//         }

//         // Function to verify item exists and handle Sales Order update
//         function verifyItemAndProceed(retryCount = 0) {
//             const maxRetries = 5;
//             const retryDelay = 1000; // 1 second

//             frappe.call({
//                 method: "frappe.client.get",
//                 args: {
//                     doctype: "Item",
//                     name: item_code
//                 },
//                 callback: function(r) {
//                     if (r.message) {
//                         console.log("Item verified successfully:", item_code);
                        
//                         // Handle Sales Order integration if context exists
//                         if (context && context.so_name) {
//                             // Store result for Sales Order to pick up
//                             const result = {
//                                 so_name: context.so_name,
//                                 cdn: context.cdn,
//                                 item_code: item_code,
//                                 temp_id: context.temp_id,
//                                 row_index: context.row_index
//                             };
//                             sessionStorage.setItem('ig_return_result', JSON.stringify(result));
//                             sessionStorage.removeItem('ig_return_context');
                            
//                             frappe.show_alert({
//                                 message: __("Item {0} created successfully and linked to Sales Order.", [item_code]),
//                                 indicator: "green"
//                             });

//                             // Navigate back to Sales Order after a short delay
//                             setTimeout(() => {
//                                 frappe.set_route('Form', 'Sales Order', context.so_name);
//                             }, 1500);
//                         } else {
//                             console.log("No Sales Order context, Item Generator save complete");
//                             frappe.show_alert({
//                                 message: __("Item {0} created successfully.", [item_code]),
//                                 indicator: "green"
//                             });
//                         }
//                         frm.__after_save_lock = false;
//                     } else {
//                         // Item not found, retry if we haven't exceeded max retries
//                         if (retryCount < maxRetries) {
//                             console.log(`Item not found, retrying... (${retryCount + 1}/${maxRetries})`);
//                             setTimeout(() => {
//                                 verifyItemAndProceed(retryCount + 1);
//                             }, retryDelay);
//                         } else {
//                             console.error("Item not found after maximum retries:", item_code);
//                             frappe.msgprint({
//                                 title: __("Error"),
//                                 message: __("Item {0} was not created. Please check if all required fields are filled.", [item_code]),
//                                 indicator: "red"
//                             });
//                             frm.__after_save_lock = false;
//                         }
//                     }
//                 },
//                 error: function(err) {
//                     console.error("Error verifying item:", err);
//                     if (retryCount < maxRetries) {
//                         console.log(`API error, retrying... (${retryCount + 1}/${maxRetries})`);
//                         setTimeout(() => {
//                             verifyItemAndProceed(retryCount + 1);
//                         }, retryDelay);
//                     } else {
//                         frappe.msgprint({
//                             title: __("Server Error"),
//                             message: __("Could not verify item creation. Please check manually."),
//                             indicator: "red"
//                         });
//                         frm.__after_save_lock = false;
//                     }
//                 }
//             });
//         }


//         setTimeout(() => {
//             verifyItemAndProceed();
//         }, 500);
//     },

//     template_name: function(frm) {

//         if (!frm.doc.short_description) {
//             frm.set_value("short_description", "");
//         }
//         clear_attribute_values(frm);
        
//         // Reset and load new template
//         if (!frm.doc.template_name) {
//             reset_attribute_fields(frm, true);
//             return;
//         }
//         reset_attribute_fields(frm, false);
//         // load_template_attributes(frm, frm.doc.template_name, false);
//         frappe.call({
//             method: "frappe.client.get",
//             args: {
//                 doctype: "Item Generator Template",
//                 name: frm.doc.template_name
//             },
//             callback: function(r) {
//                 if (r.message && r.message.item_group_name) {
//                     frm.set_value("item_group_name", r.message.item_group_name);
//                 } else if (r.message) {
//                     frm.set_value("item_group_name", ""); // Clear if no item_group_name
//                 }
//                 // Load template attributes after setting item_group_name
//                 load_template_attributes(frm, frm.doc.template_name, false);
//             }
//         });

        
//     },

//     item_descriptor: function(frm) {
//         if (!frm.doc.item_descriptor) return;
        
//         if (!frm.doc.template_name) {
//             frappe.msgprint("Please select a template first.");
//             frm.set_value("item_descriptor", "");
//             return;
//         }
        
//         if (!frm.__attribute_meta_loaded__) {
//             frappe.msgprint("Attributes not loaded yet. Please wait a moment.");
//             return;
//         }
        
//         parse_item_descriptor(frm);
//     }
// });

// // Function to handle Sales Order update
// function updateSalesOrderWithNewItem(frm, context, item_code) {
//     console.log("Updating Sales Order with new item:", context.so_name, item_code);
    
//     // First, get the Sales Order to check if it's saved
//     frappe.call({
//         method: "frappe.client.get",
//         args: {
//             doctype: "Sales Order",
//             name: context.so_name
//         },
//         callback: function(r) {
//             if (r.message) {
//                 // Sales Order exists, now update the specific item
//                 updateSalesOrderItem(frm, context, item_code);
//             } else {
//                 // Sales Order doesn't exist yet (might be unsaved)
//                 console.log("Sales Order not found, might be unsaved");
                
//                 // Store result for Sales Order to pick up later
//                 const result = {
//                     so_name: context.so_name,
//                     cdn: context.cdn,
//                     item_code: item_code
//                 };
//                 sessionStorage.setItem('ig_return_result', JSON.stringify(result));
                
//                 // Close the Item Generator
//                 closeItemGeneratorAndRedirect(frm, context.so_name);
//             }
//         },
//         error: function(err) {
//             console.error("Error checking Sales Order:", err);
//             frm.__after_save_lock = false;
//         }
//     });
// }

// // Function to update Sales Order item
// function updateSalesOrderItem(frm, context, item_code) {
//     if (!context || !context.so_name || !context.cdn) {
//         frappe.msgprint({
//             title: __("Error"),
//             message: __("Missing Sales Order context. Please update manually."),
//             indicator: "red"
//         });
//         return;
//     }

//     // Directly update the target row using the actual row name (cdn)
//     updateSalesOrderItemDirect(frm, context, item_code);
// }

// // Function to update Sales Order item directly by child row name
// function updateSalesOrderItemDirect(frm, context, item_code) {
//     frappe.call({
//         method: "frappe.client.get",
//         args: {
//             doctype: "Sales Order",
//             name: context.so_name
//         },
//         callback: function(r) {
//             if (r.message && r.message.items) {
//                 let targetItem = r.message.items.find(it => it.name === context.cdn);

//                 if (targetItem) {
//                     // Update in client-side model
//                     frappe.model.set_value("Sales Order Item", targetItem.name, {
//                         item_code: item_code,
//                         item_name: frm.doc.item_name,
//                         description: frm.doc.description,
//                         uom: frm.doc.stock_uom
//                     });

//                     // Save the parent Sales Order
//                     frappe.call({
//                         method: "frappe.client.save",
//                         args: {
//                             doc: r.message
//                         },
//                         callback: function() {
//                             frappe.show_alert({
//                                 message: __("Sales Order row updated with new item {0}", [item_code]),
//                                 indicator: "green"
//                             });
//                         }
//                     });
//                 } else {
//                     frappe.msgprint({
//                         title: __("Error"),
//                         message: __("Target Sales Order row not found. Please update manually."),
//                         indicator: "red"
//                     });
//                 }
//             }
//         }
//     });
// }


// // Function to directly update Sales Order item


// // Function to close Item Generator and redirect
// function closeItemGeneratorAndRedirect(frm, so_name) {
//     if (frm.doc.is_closed !== 1) {
//         frappe.call({
//             method: "frappe.client.set_value",
//             args: {
//                 doctype: "Item Generator",
//                 name: frm.doc.name,
//                 fieldname: "is_closed",
//                 value: 1
//             },
//             callback: function() {
//                 console.log("Item Generator closed");
//                 frappe.show_alert({
//                     message: __("Item Generator closed and Sales Order updated"),
//                     indicator: "green"
//                 });
                
//                 // Navigate back to Sales Order
//                 setTimeout(() => {
//                     frappe.set_route('Form', 'Sales Order', so_name);
//                 }, 1500);
//                 frm.__after_save_lock = false;
//             },
//             error: function(err) {
//                 console.error("Error closing Item Generator:", err);
//                 frm.__after_save_lock = false;
//             }
//         });
//     } else {
//         // Navigate back to Sales Order immediately
//         setTimeout(() => {
//             frappe.set_route('Form', 'Sales Order', so_name);
//         }, 1000);
//         frm.__after_save_lock = false;
//     }
// }

// function lock_form(frm) {
//     frm.set_read_only();
//     frm.disable_save();

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

//     if (!frm.is_new() && frm.doc.is_closed === 1) {
//         if (frm.page && frm.page.btn_primary) {
//             frm.page.btn_primary.hide(); 
//         }
//         if (frm.page && frm.page.clear_primary_action) {
//             frm.page.clear_primary_action(); 
//         }
//     }
// }

// function update_sort_desc(frm) {
//     frappe.call({
//         method: "generate_item.generate_item.doctype.item_generator.item_generator.update_short_description",
//         args: {
//             "docname": frm.doc.name
//         },
//         callback: function(r) {
//             if (r.message && r.message.success) {
//                 frm.set_value("short_description", r.message.short_description).then(() => {
//                     frm.set_value("custom_conditional_description", r.message.short_description).then(() => {
//                         frm.refresh_field("short_description");
//                         frm.refresh_field("custom_conditional_description");
//                     });
//                 });
//             }
//         }
//     });
// }

// function clear_attribute_values(frm) {
//     if (frm.__clearing_attributes) {
//         console.log("Skipped duplicate clear_attribute_values");
//         return;
//     }
//     frm.__clearing_attributes = true;

//     console.log("Clearing attribute value fields for:", frm.doc.name);

//     for (let i = 1; i <= 28; i++) {
//         const fieldname = `attribute_${i}_value`;
//         if (frm.fields_dict[fieldname]) {
//             frm.set_value(fieldname, "");
//         }
//     }
//     frm.set_value("custom_conditional_description", "");
//     frm.set_value("description", "");

//     if (!frm.doc.__islocal) {
//         frm.dirty();
//     }

//     // release guard after a tick
//     setTimeout(() => { frm.__clearing_attributes = false; }, 500);
// }

// function load_template_attributes(frm, template_name, is_reload) {
//     frm.__attribute_meta__ = {};
//     frm.__attribute_meta_loaded__ = false;

//     frappe.call({
//         method: "frappe.client.get",
//         args: {
//             doctype: "Item Generator Template",
//             name: template_name
//         },
//         callback: function(r) {
//             if (!r || !r.message) {
//                 frappe.msgprint("Item Generator Template not found: " + template_name);
//                 return;
//             }

//             var attributes = r.message.custom_variants || [];
//             var pending = 0;

//             for (var a = 0; a < attributes.length && a < 28; a++) {
//                 (function(index, attrRow) {
//                     var i = index + 1;
//                     var label_field = "attribute_" + i;
//                     var value_field = "attribute_" + i + "_value";

//                     var heading_raw = attrRow.logic_heading || "";
//                     var heading = heading_raw;
//                     var dashIndex = heading_raw.indexOf("-");
//                     if (dashIndex !== -1 && dashIndex < heading_raw.length - 1) {
//                         heading = heading_raw.substring(dashIndex + 1).trim();
//                     }

//                     frm.set_value(label_field, heading);
//                     frm.set_df_property(value_field, 'label', heading || ("Attribute " + i));
//                     frm.set_df_property(value_field, 'hidden', 0);
//                     frm.set_df_property(value_field, 'reqd', 1);
//                     frm.refresh_field(value_field);

//                     frm.__attribute_meta__[value_field] = {};

//                     pending++;
//                     frappe.call({
//                         method: "frappe.client.get",
//                         args: {
//                             doctype: "Custom Item Attribute",
//                             name: attrRow.logic_heading || ""
//                         },
//                         callback: function(res) {
//                             var dropdown = [];
//                             if (res && res.message) {
//                                 var rows = res.message.logic_table || [];
//                                 for (var j = 0; j < rows.length; j++) {
//                                     var row = rows[j] || {};
//                                     if (row.disabled == 0) {
//                                         var display = String(row.item_long_description || "");
//                                         var code = String(row.code || "");
//                                         var shortdesc = String(row.item_short_description || "");
//                                         dropdown.push(display);

//                                         var keyNorm = display.trim().toLowerCase();
//                                         frm.__attribute_meta__[value_field][keyNorm] = {
//                                             code: code,
//                                             item_long_description: display,
//                                             item_short_description: shortdesc
//                                         };
//                                         frm.__attribute_meta__[value_field][display] = frm.__attribute_meta__[value_field][keyNorm];
//                                     }
//                                 }
//                             }

//                             var uniq = [];
//                             for (var u = 0; u < dropdown.length; u++) {
//                                 if (uniq.indexOf(dropdown[u]) === -1) uniq.push(dropdown[u]);
//                             }
//                             frm.set_df_property(value_field, 'options', uniq);
//                             frm.refresh_field(value_field);

//                             (function(vf) {
//                                 setTimeout(function() {
//                                     var saved = frm.doc[vf];
//                                     if (saved) {
//                                         try { frm.set_value(vf, saved); } catch (err) {}
//                                     }
//                                 }, 50);
//                             })(value_field);

//                             pending--;
//                             if (pending === 0) {
//                                 frm.__attribute_meta_loaded__ = true;
//                                 if (is_reload && frm.doc.__islocal) {
//                                     setTimeout(function() { generate_fields(frm); }, 80);
//                                 }
//                             }
//                         }
//                     });
//                 })(a, attributes[a]);
//             }

//             if (attributes.length === 0) {
//                 frm.__attribute_meta_loaded__ = true;
//                 if (is_reload && frm.doc.__islocal) generate_fields(frm);
//             }
//         }
//     });
// }

// function reset_attribute_fields(frm, force) {
//     if (typeof force === 'undefined') force = false;
    
//     const preserve_item_code = frm.doc.item_code;
//     const preserve_description = frm.doc.description;  
//     const preserve_short_description = frm.doc.short_description;
    
//     for (var i = 1; i <= 28; i++) {
//         var label_field = "attribute_" + i;
//         var value_field = "attribute_" + i + "_value";
//         if (force || !frm.doc[value_field]) {
//             frm.set_value(label_field, "");
//             frm.set_value(value_field, "");
//         }
//         frm.set_df_property(value_field, 'hidden', 1);
//         frm.set_df_property(value_field, 'reqd', 0);
//         frm.set_df_property(value_field, 'label', "Attribute " + i);
//         frm.refresh_field(value_field);
//     }
//     frm.__attribute_meta__ = {};
    
//     if (force) {
//         frm.set_value("item_code", "");
//         frm.set_value("description", "");
//         frm.set_value("short_description", "");
//     } else {
//         if (preserve_item_code) frm.set_value("item_code", preserve_item_code);
//         if (preserve_description) frm.set_value("description", preserve_description);
//         if (preserve_short_description) frm.set_value("short_description", preserve_short_description);
//     }
// }

// function generate_fields(frm) {
//     var code_parts = [];
//     var desc_parts = [];
//     var short_parts = [];

//     for (var i = 1; i <= 28; i++) {
//         var value_field = "attribute_" + i + "_value";
//         var val = frm.doc[value_field];
//         if (!val) continue;
//         // if (!val || val.trim() === "-") continue;

//         val = String(val);
//         var keyNorm = val.trim().toLowerCase();

//         var metaMap = (frm.__attribute_meta__ && frm.__attribute_meta__[value_field]) ? frm.__attribute_meta__[value_field] : null;
//         var meta = null;
//         if (metaMap) {
//             if (metaMap.hasOwnProperty(keyNorm)) {
//                 meta = metaMap[keyNorm];
//             } else if (metaMap.hasOwnProperty(val)) {
//                 meta = metaMap[val];
//             } else {
//                 var keys = Object.keys(metaMap);
//                 for (var k = 0; k < keys.length; k++) {
//                     if (keys[k].toString().trim().toLowerCase() === keyNorm) {
//                         meta = metaMap[keys[k]];
//                         break;
//                     }
//                 }
//             }
//         }

//         if (meta) {
//             code_parts.push(meta.code || "");
            
//             // Only add to desc_parts and short_parts if value is NOT "-"
//             if (val.trim() !== "-") {
//                 desc_parts.push(meta.item_long_description || val);
//                 short_parts.push(meta.item_short_description || val);
//             }
//         } 

//         // if (meta) {
//         //     code_parts.push(meta.code || "");
//         //     desc_parts.push(meta.item_long_description || val);
//         //     short_parts.push(meta.item_short_description || val);
//         // }
//     }

//     frm.set_value("item_code", code_parts.join(""));
//     frm.set_value("description", desc_parts.join(" "));
//     frm.set_value("short_description", short_parts.join(" "));
// }

// function parse_item_descriptor(frm) {
//     let code = frm.doc.item_descriptor.trim();
//     let cursor = 0;
//     let error_found = false;

//     for (let i = 1; i <= 28; i++) {
//         let value_field = "attribute_" + i + "_value";
//         let metaMap = frm.__attribute_meta__[value_field];
//         if (!metaMap) continue;

//         let codeLen = 0;
//         let rows = Object.values(metaMap);
//         if (rows.length && rows[0].code) {
//             codeLen = rows[0].code.length;
//         }
//         if (!codeLen) continue;

//         let codePart = code.slice(cursor, cursor + codeLen);
//         cursor += codeLen;

//         let matched = Object.entries(metaMap).find(([key, meta]) => {
//             return (meta.code || "").toUpperCase() === codePart.toUpperCase();
//         });

//         if (matched) {
//             frm.set_value(value_field, matched[1].item_long_description);
//         } else {
//             frappe.msgprint(`No match found for code part "${codePart}" at position ${i}.`);
//             error_found = true;
//         }
//     }

//     if (!error_found) {
//         generate_fields(frm);
//         setTimeout(() => {
//             frm.set_value("item_descriptor", "");
//             frm.refresh_field("item_descriptor");
//         }, 300);
//     } else {
//         frm.set_value("item_descriptor", "");
//     }
// }

// function focus_next_field(frm, currentIndex) {
//     var next = currentIndex + 1;
//     var next_field = "attribute_" + next + "_value";
//     if (next <= 28 && frm.fields_dict[next_field] && !frm.fields_dict[next_field].df.hidden) {
//         setTimeout(function() {
//             var $el = $('[data-fieldname="' + next_field + '"] input');
//             if ($el && $el.length) $el.focus();
//         }, 150);
//     }
// }

// function attribute_change_handler_factory(index) {
//     return function(frm) {
//         generate_fields(frm);
//         focus_next_field(frm, index);
//     };
// }

// var _events = {};
// for (var idx = 1; idx <= 28; idx++) {
//     _events["attribute_" + idx + "_value"] = attribute_change_handler_factory(idx);
// }
// frappe.ui.form.on('Item Generator', _events);

// // Enhanced Sales Order Integration Functions
// function handle_sales_order_integration(frm) {
//     const created_item = frm.doc.created_item || frm.doc.item_code;
    
//     if (!created_item) {
//         frappe.msgprint({
//             title: __("Warning"),
//             message: __("No item code found. Item may not have been created yet."),
//             indicator: "orange"
//         });
//         frm.__after_save_lock = false;
//         return;
//     }

//     console.log("🔍 Verifying item creation:", created_item);

//     // Enhanced item verification with retry mechanism
//     verify_item_creation(created_item, 0, (success) => {
//         if (success) {
//             console.log("✅ Item verified successfully:", created_item);
            
//             // Check if this is a Sales Order integration
//             if (frm.doc.is_create_with_sales_order === 1) {
//                 handle_sales_order_return(frm, created_item);
//             } else {
//                 frappe.show_alert({
//                     message: __("Item {0} created successfully.", [created_item]),
//                     indicator: "green"
//                 });
//                 frm.__after_save_lock = false;
//             }
//         } else {
//             frappe.msgprint({
//                 title: __("Error"),
//                 message: __("Failed to verify item creation. Please check if item {0} exists.", [created_item]),
//                 indicator: "red"
//             });
//             frm.__after_save_lock = false;
//         }
//     });
// }

// function verify_item_creation(item_code, retry_count, callback) {
//     const max_retries = 5;
//     const retry_delay = 1000; // 1 second

//     frappe.call({
//         method: "frappe.client.get",
//         args: {
//             doctype: "Item",
//             name: item_code
//         },
//         callback: function(r) {
//             if (r.message) {
//                 // Item found successfully
//                 callback(true);
//             } else if (retry_count < max_retries) {
//                 // Retry after delay
//                 setTimeout(() => {
//                     verify_item_creation(item_code, retry_count + 1, callback);
//                 }, retry_delay);
//             } else {
//                 // Max retries reached
//                 callback(false);
//             }
//         },
//         error: function(err) {
//             if (retry_count < max_retries) {
//                 setTimeout(() => {
//                     verify_item_creation(item_code, retry_count + 1, callback);
//                 }, retry_delay);
//             } else {
//                 callback(false);
//             }
//         }
//     });
// }

// function handle_sales_order_return(frm, created_item) {
//     // Get context from sessionStorage
//     const raw = sessionStorage.getItem('ig_return_context');
//     if (!raw) {
//         frappe.show_alert({
//             message: __("Item created but no Sales Order context found."),
//             indicator: "orange"
//         });
//         frm.__after_save_lock = false;
//         return;
//     }

//     let context;
//     try {
//         context = JSON.parse(raw);
//     } catch (e) {
//         frappe.msgprint({
//             title: __("Error"),
//             message: __("Invalid return context data."),
//             indicator: "red"
//         });
//         frm.__after_save_lock = false;
//         return;
//     }

//     if (!context.so_name || !context.cdn) {
//         frappe.show_alert({
//             message: __("Item created but Sales Order context is incomplete."),
//             indicator: "orange"
//         });
//         frm.__after_save_lock = false;
//         return;
//     }

//     // Update the specific Sales Order Item row
//     update_sales_order_item(context, created_item, (success) => {
//         if (success) {
//             // Store result for Sales Order to pick up
//             const result = {
//                 so_name: context.so_name,
//                 cdn: context.cdn,
//                 item_code: created_item
//             };
//             sessionStorage.setItem('ig_return_result', JSON.stringify(result));
//             sessionStorage.removeItem('ig_return_context');

//             frappe.show_alert({
//                 message: __("Item {0} created and linked to Sales Order.", [created_item]),
//                 indicator: "green"
//             });

//             // Navigate back to Sales Order after a short delay
//             setTimeout(() => {
//                 frappe.set_route('Form', 'Sales Order', context.so_name);
//             }, 1500);
//         } else {
//             frappe.msgprint({
//                 title: __("Warning"),
//                 message: __("Item created successfully but failed to update Sales Order. Please update manually."),
//                 indicator: "orange"
//             });
//         }
//         frm.__after_save_lock = false;
//     });
// }

// function update_sales_order_item(context, item_code, callback) {
//     frappe.call({
//         method: "frappe.client.set_value",
//         args: {
//             doctype: "Sales Order Item",
//             name: context.cdn,
//             fieldname: "item_code",
//             value: item_code
//         },
//         callback: function(r) {
//             if (r && !r.exc) { 
//                 frappe.call({
//                     method: "frappe.client.get_value",
//                     args: {
//                         doctype: "Item",
//                         filters: {"name": item_code},
//                         fieldname: ["item_name", "stock_uom"]
//                     },
//                     callback: function(item_r) {
//                         if (item_r.message) {
//                             // Update item_name and uom if they exist
//                             const updates = {};
//                             if (item_r.message.item_name) {
//                                 updates.item_name = item_r.message.item_name;
//                             }
//                             if (item_r.message.stock_uom) {
//                                 updates.uom = item_r.message.stock_uom;
//                             }

//                             if (Object.keys(updates).length > 0) {
//                                 frappe.call({
//                                     method: "frappe.client.set_value",
//                                     args: {
//                                         doctype: "Sales Order Item",
//                                         name: context.cdn,
//                                         fieldname: updates
//                                     },
//                                     callback: function() {
//                                         callback(true);
//                                     }
//                                 });
//                             } else {
//                                 callback(true);
//                             }
//                         } else {
//                             callback(true);
//                         }
//                     }
//                 });
//             } else {
//                 callback(false);
//             }
//         },
//         error: function(err) {
//             callback(false);
//         }
//     });
// }












frappe.ui.form.on("Item Generator", {
    onload: function(frm) {
        // Initialize flags and meta objects
        frm.__attribute_meta__ = {};
        frm.__attribute_meta_loaded__ = false;
        frm.doc.__initialSetComplete = false;
        frm.doc.__fromRefresh = false;
        
        // Load selective products for filtering
        load_selective_products(frm);
        
        // Reset attribute fields without forcing
        reset_attribute_fields(frm, false);

        // Load template attributes if template is already selected
        if (frm.doc.template_name) {
            load_template_attributes(frm, frm.doc.template_name, true);
        }

        // Clear stale sessionStorage if not linked to Sales Order
        if (!frm.doc.is_create_with_sales_order) {
            sessionStorage.removeItem('ig_return_context');
            console.log("Cleared ig_return_context from sessionStorage for normal Item Generator");
        }
    },

    refresh: function(frm) {
        // Apply query for template_name
        frm.set_query("template_name", function() {
            return { filters: { disabled: 0 } };
        });

        if (frm.clear_custom_buttons) frm.clear_custom_buttons();

        // Only allow Close/Closed functionality if is_create_with_sales_order = 1
        if (frm.doc.is_create_with_sales_order == 1) {
            if (frm.doc.is_closed == 1) {
                lock_form(frm);

                const btn = frm.add_custom_button("Closed");
                if (btn) {
                    btn.addClass && btn.addClass("btn-disabled");
                    btn.prop && btn.prop("disabled", true);
                }
            } else {
                // Clear existing primary action
                if (frm.page && frm.page.set_primary_action) {
                    frm.page.set_primary_action(null);
                }
                // Hide default Save button
                if (frm.page && frm.page.btn_primary && frm.page.btn_primary.is(':visible')) {
                    frm.page.btn_primary.hide();
                }
                // Show "Save and Close" button
                frm.add_custom_button("Save And Close", function() {
                    let dialog = frappe.confirm(
                        "Are you sure you want to Save And Close this record?",
                        function() {
                            if (frm.is_valid && !frm.is_valid()) {
                                frappe.msgprint({
                                    title: __("Cannot Close"),
                                    message: __("Please complete all mandatory fields before closing."),
                                    indicator: "red"
                                });
                                dialog.hide();
                                return;
                            }

                            // FIRST: Save the document normally
                            frm.save().then(() => {
                                // Set is_closed flag to 1
                                return frm.set_value("is_closed", 1);
                            }).then(() => {
                                // Save again to persist the is_closed flag
                                return frm.save();
                            }).then(() => {
                                // Lock the form to make it read-only
                                lock_form(frm);
                                
                                // AFTER successful save, trigger after_save logic
                                console.log("Document saved and closed, now executing after_save logic");
                                                                
                                frappe.show_alert("This record has been saved and closed.");
                                
                                // Reload to ensure form is properly locked
                                frm.reload_doc();
                            }).catch(function(err) {
                                frappe.msgprint({
                                    title: __("Save Error"),
                                    message: __("Failed to save the document: " + err.message),
                                    indicator: "red"
                                });
                                dialog.hide();
                                console.error("Save error:", err);
                            });
                        },
                        function() {
                            dialog.hide();
                        }
                    );
                });
            }
        } else {
            // Ensure Save button is available/visible
            try {
                frm.enable_save && frm.enable_save();
                if (frm.page && frm.page.set_primary_action) {
                    frm.page.set_primary_action(__('Save'), function() {
                        frm.save().then(function() {
                            frappe.show_alert("Document saved successfully.");
                            frm.refresh();
                        }).catch(function(err) {
                            frappe.msgprint({
                                title: __("Save Error"),
                                message: __("Failed to save the document. Please try again."),
                                indicator: "red"
                            });
                            console.error("Save error:", err);
                        });
                    });
                }
                if (frm.page && frm.page.btn_primary && !frm.page.btn_primary.is(':visible')) {
                    frm.page.btn_primary.show();
                }
            } catch (e) {
                console.error("Error setting save button:", e);
            }
        }

        // Avoid setting values that mark form as dirty
        if (
            frm.doc.custom_conditional_description &&
            frm.doc.short_description !== frm.doc.custom_conditional_description &&
            !frm.doc.__islocal &&
            !frm.doc.__unsaved
        ) {
            frm.set_value("short_description", frm.doc.custom_conditional_description).then(() => {
                frm.refresh_field("short_description");
            });
        }

        // Initialize attribute meta if not already done
        if (!frm.__attribute_meta_initialized) {
            frm.__attribute_meta__ = {};
            frm.__attribute_meta_loaded__ = false;
            frm.__attribute_meta_initialized = true;
        }

        // Load template attributes if template is selected
        if (frm.doc.template_name && !frm.__attribute_meta_loaded__) {
            load_template_attributes(frm, frm.doc.template_name, true);
        } else if (frm.__attribute_meta_loaded__ && frm.doc.__islocal) {
            generate_fields(frm);
        }
    },

    after_save: function(frm) {
        // Prevent duplicate triggers
        if (frm.__after_save_lock) {
            console.log("Skipping after_save due to lock");
            return;
        }
        frm.__after_save_lock = true;

        console.log("Entering after_save for Item Generator:", frm.doc.name);

        // Only process if this is a Sales Order linked document
        if (frm.doc.is_create_with_sales_order !== 1) {
            frm.__after_save_lock = false;
            return;
        }

        // Get the item code that should be created
        let item_code = frm.doc.created_item || frm.doc.item_code;
        if (!item_code) {
            console.log("No item code found, releasing lock");
            frm.__after_save_lock = false;
            return;
        }

        console.log("Item code to verify:", item_code);

        // Check if this is a Sales Order linked Item Generator
        let context = null;
        try {
            const raw = sessionStorage.getItem('ig_return_context');
            if (raw) {
                context = JSON.parse(raw);
                console.log("Sales Order context found:", context);
            }
        } catch (e) {
            console.error("Error parsing context:", e);
            frm.__after_save_lock = false;
            return;
        }

        if (!context || !context.so_name) {
            console.log("No valid Sales Order context found");
            frm.__after_save_lock = false;
            return;
        }

        // Function to verify item exists and handle Sales Order update
        function verifyItemAndProceed(retryCount = 0) {
            const maxRetries = 5;
            const retryDelay = 1000; // 1 second

            frappe.call({
                method: "frappe.client.get",
                args: {
                    doctype: "Item",
                    name: item_code
                },
                callback: function(r) {
                    if (r.message) {
                        console.log("Item verified successfully:", item_code);
                        
                        // Handle Sales Order integration if context exists
                        if (context && context.so_name) {
                            // Store result for Sales Order to pick up
                            const result = {
                                so_name: context.so_name,
                                cdn: context.cdn,
                                item_code: item_code,
                                temp_id: context.temp_id,
                                row_index: context.row_index
                            };
                            sessionStorage.setItem('ig_return_result', JSON.stringify(result));
                            sessionStorage.removeItem('ig_return_context');
                            
                            frappe.show_alert({
                                message: __("Item {0} created successfully and linked to Sales Order.", [item_code]),
                                indicator: "green"
                            });

                            // Navigate back to Sales Order after a short delay
                            setTimeout(() => {
                                frappe.set_route('Form', 'Sales Order', context.so_name);
                            }, 1500);
                        } else {
                            console.log("No Sales Order context, Item Generator save complete");
                            frappe.show_alert({
                                message: __("Item {0} created successfully.", [item_code]),
                                indicator: "green"
                            });
                        }
                        frm.__after_save_lock = false;
                    } else {
                        // Item not found, retry if we haven't exceeded max retries
                        if (retryCount < maxRetries) {
                            console.log(`Item not found, retrying... (${retryCount + 1}/${maxRetries})`);
                            setTimeout(() => {
                                verifyItemAndProceed(retryCount + 1);
                            }, retryDelay);
                        } else {
                            console.error("Item not found after maximum retries:", item_code);
                            frappe.msgprint({
                                title: __("Error"),
                                message: __("Item {0} was not created. Please check if all required fields are filled.", [item_code]),
                                indicator: "red"
                            });
                            frm.__after_save_lock = false;
                        }
                    }
                },
                error: function(err) {
                    console.error("Error verifying item:", err);
                    if (retryCount < maxRetries) {
                        console.log(`API error, retrying... (${retryCount + 1}/${maxRetries})`);
                        setTimeout(() => {
                            verifyItemAndProceed(retryCount + 1);
                        }, retryDelay);
                    } else {
                        frappe.msgprint({
                            title: __("Server Error"),
                            message: __("Could not verify item creation. Please check manually."),
                            indicator: "red"
                        });
                        frm.__after_save_lock = false;
                    }
                }
            });
        }

        setTimeout(() => {
            verifyItemAndProceed();
        }, 500);
    },

    template_name: function(frm) {
        if (!frm.doc.short_description) {
            frm.set_value("short_description", "");
        }
        clear_attribute_values(frm);
        
        // Reset and load new template
        if (!frm.doc.template_name) {
            reset_attribute_fields(frm, true);
            return;
        }
        reset_attribute_fields(frm, false);
        
        frappe.call({
            method: "frappe.client.get",
            args: {
                doctype: "Item Generator Template",
                name: frm.doc.template_name
            },
            callback: function(r) {
                if (r.message && r.message.item_group_name) {
                    frm.set_value("item_group_name", r.message.item_group_name);
                } else if (r.message) {
                    frm.set_value("item_group_name", "");
                }
                // Load template attributes after setting item_group_name
                load_template_attributes(frm, frm.doc.template_name, false);
            }
        });
    },

    item_descriptor: function(frm) {
        if (!frm.doc.item_descriptor) return;
        
        if (!frm.doc.template_name) {
            frappe.msgprint("Please select a template first.");
            frm.set_value("item_descriptor", "");
            return;
        }
        
        if (!frm.__attribute_meta_loaded__) {
            frappe.msgprint("Attributes not loaded yet. Please wait a moment.");
            return;
        }
        
        parse_item_descriptor(frm);
    }
});

// NEW FUNCTION: Load selective products
function load_selective_products(frm) {
    frappe.call({
        method: "frappe.client.get",
        args: {
            doctype: "Selective Products",
            name: "Selective Products"
        },
        callback: function(r) {
            if (r.message && r.message.products) {
                frm.__selective_templates__ = r.message.products.map(p => p.product_name);
                console.log("Loaded selective products:", frm.__selective_templates__);
            } else {
                frm.__selective_templates__ = [];
            }
        },
        error: function(err) {
            console.error("Error loading Selective Products:", err);
            frm.__selective_templates__ = [];
        }
    });
}

function lock_form(frm) {
    frm.set_read_only();
    frm.disable_save();

    (frm.meta.fields || []).forEach(df => {
        try {
            frm.set_df_property(df.fieldname, "read_only", 1);

            if (df.fieldtype === "Table" && frm.fields_dict[df.fieldname]?.grid) {
                let grid = frm.fields_dict[df.fieldname].grid;
                grid.wrapper?.find('.grid-add-row, .grid-remove-rows, .grid-delete-row, .grid-append-row').hide();
                grid.set_allow_on_grid_editing?.(false);
                grid.toolbar?.find('.btn').prop('disabled', true);
            }
        } catch (e) {}
    });

    if (!frm.is_new() && frm.doc.is_closed === 1) {
        if (frm.page && frm.page.btn_primary) {
            frm.page.btn_primary.hide(); 
        }
        if (frm.page && frm.page.clear_primary_action) {
            frm.page.clear_primary_action(); 
        }
    }
}

function update_sort_desc(frm) {
    frappe.call({
        method: "generate_item.generate_item.doctype.item_generator.item_generator.update_short_description",
        args: {
            "docname": frm.doc.name
        },
        callback: function(r) {
            if (r.message && r.message.success) {
                frm.set_value("short_description", r.message.short_description).then(() => {
                    frm.set_value("custom_conditional_description", r.message.short_description).then(() => {
                        frm.refresh_field("short_description");
                        frm.refresh_field("custom_conditional_description");
                    });
                });
            }
        }
    });
}

function clear_attribute_values(frm) {
    if (frm.__clearing_attributes) {
        console.log("Skipped duplicate clear_attribute_values");
        return;
    }
    frm.__clearing_attributes = true;

    console.log("Clearing attribute value fields for:", frm.doc.name);

    for (let i = 1; i <= 28; i++) {
        const fieldname = `attribute_${i}_value`;
        if (frm.fields_dict[fieldname]) {
            frm.set_value(fieldname, "");
        }
    }
    frm.set_value("custom_conditional_description", "");
    frm.set_value("description", "");

    if (!frm.doc.__islocal) {
        frm.dirty();
    }

    // release guard after a tick
    setTimeout(() => { frm.__clearing_attributes = false; }, 500);
}

function load_template_attributes(frm, template_name, is_reload) {
    frm.__attribute_meta__ = {};
    frm.__attribute_meta_loaded__ = false;

    frappe.call({
        method: "frappe.client.get",
        args: {
            doctype: "Item Generator Template",
            name: template_name
        },
        callback: function(r) {
            if (!r || !r.message) {
                frappe.msgprint("Item Generator Template not found: " + template_name);
                return;
            }

            var attributes = r.message.custom_variants || [];
            var pending = 0;

            for (var a = 0; a < attributes.length && a < 28; a++) {
                (function(index, attrRow) {
                    var i = index + 1;
                    var label_field = "attribute_" + i;
                    var value_field = "attribute_" + i + "_value";

                    var heading_raw = attrRow.logic_heading || "";
                    var heading = heading_raw;
                    var dashIndex = heading_raw.indexOf("-");
                    if (dashIndex !== -1 && dashIndex < heading_raw.length - 1) {
                        heading = heading_raw.substring(dashIndex + 1).trim();
                    }

                    frm.set_value(label_field, heading);
                    frm.set_df_property(value_field, 'label', heading || ("Attribute " + i));
                    frm.set_df_property(value_field, 'hidden', 0);
                    frm.set_df_property(value_field, 'reqd', 1);
                    frm.refresh_field(value_field);

                    frm.__attribute_meta__[value_field] = {};

                    pending++;
                    frappe.call({
                        method: "frappe.client.get",
                        args: {
                            doctype: "Custom Item Attribute",
                            name: attrRow.logic_heading || ""
                        },
                        callback: function(res) {
                            var dropdown = [];
                            if (res && res.message) {
                                var rows = res.message.logic_table || [];
                                for (var j = 0; j < rows.length; j++) {
                                    var row = rows[j] || {};
                                    if (row.disabled == 0) {
                                        var display = String(row.item_long_description || "");
                                        var code = String(row.code || "");
                                        var shortdesc = String(row.item_short_description || "");
                                        dropdown.push(display);

                                        var keyNorm = display.trim().toLowerCase();
                                        frm.__attribute_meta__[value_field][keyNorm] = {
                                            code: code,
                                            item_long_description: display,
                                            item_short_description: shortdesc
                                        };
                                        frm.__attribute_meta__[value_field][display] = frm.__attribute_meta__[value_field][keyNorm];
                                    }
                                }
                            }

                            var uniq = [];
                            for (var u = 0; u < dropdown.length; u++) {
                                if (uniq.indexOf(dropdown[u]) === -1) uniq.push(dropdown[u]);
                            }
                            frm.set_df_property(value_field, 'options', uniq);
                            frm.refresh_field(value_field);

                            (function(vf) {
                                setTimeout(function() {
                                    var saved = frm.doc[vf];
                                    if (saved) {
                                        try { frm.set_value(vf, saved); } catch (err) {}
                                    }
                                }, 50);
                            })(value_field);

                            pending--;
                            if (pending === 0) {
                                frm.__attribute_meta_loaded__ = true;
                                if (is_reload && frm.doc.__islocal) {
                                    setTimeout(function() { generate_fields(frm); }, 80);
                                }
                            }
                        }
                    });
                })(a, attributes[a]);
            }

            if (attributes.length === 0) {
                frm.__attribute_meta_loaded__ = true;
                if (is_reload && frm.doc.__islocal) generate_fields(frm);
            }
        }
    });
}

function reset_attribute_fields(frm, force) {
    if (typeof force === 'undefined') force = false;
    
    const preserve_item_code = frm.doc.item_code;
    const preserve_description = frm.doc.description;  
    const preserve_short_description = frm.doc.short_description;
    
    for (var i = 1; i <= 28; i++) {
        var label_field = "attribute_" + i;
        var value_field = "attribute_" + i + "_value";
        if (force || !frm.doc[value_field]) {
            frm.set_value(label_field, "");
            frm.set_value(value_field, "");
        }
        frm.set_df_property(value_field, 'hidden', 1);
        frm.set_df_property(value_field, 'reqd', 0);
        frm.set_df_property(value_field, 'label', "Attribute " + i);
        frm.refresh_field(value_field);
    }
    frm.__attribute_meta__ = {};
    
    if (force) {
        frm.set_value("item_code", "");
        frm.set_value("description", "");
        frm.set_value("short_description", "");
    } else {
        if (preserve_item_code) frm.set_value("item_code", preserve_item_code);
        if (preserve_description) frm.set_value("description", preserve_description);
        if (preserve_short_description) frm.set_value("short_description", preserve_short_description);
    }
}

// MODIFIED FUNCTION: Enhanced generate_fields with short description logic
function generate_fields(frm) {
    var code_parts = [];
    var desc_parts = [];
    var short_parts = [];

    // Required attributes for selective products short description
    const required_attributes = [
        "TYPE OF PRODUCT",
        "VALVE TYPE",
        "SIZE",
        "RATING",
        "ENDS",
        "SHELL MOC",
        "OPERATOR"
    ];

    var selective_short_parts = [];
    var is_selective_template = frm.__selective_templates__ && 
                                 frm.__selective_templates__.includes(frm.doc.template_name);

    for (var i = 1; i <= 28; i++) {
        var label_field = "attribute_" + i;
        var value_field = "attribute_" + i + "_value";
        var label = frm.doc[label_field] || "";
        var val = frm.doc[value_field];
        
        if (!val) continue;

        val = String(val);
        var keyNorm = val.trim().toLowerCase();

        var metaMap = (frm.__attribute_meta__ && frm.__attribute_meta__[value_field]) ? 
                      frm.__attribute_meta__[value_field] : null;
        var meta = null;
        
        if (metaMap) {
            if (metaMap.hasOwnProperty(keyNorm)) {
                meta = metaMap[keyNorm];
            } else if (metaMap.hasOwnProperty(val)) {
                meta = metaMap[val];
            } else {
                var keys = Object.keys(metaMap);
                for (var k = 0; k < keys.length; k++) {
                    if (keys[k].toString().trim().toLowerCase() === keyNorm) {
                        meta = metaMap[keys[k]];
                        break;
                    }
                }
            }
        }

        if (meta) {
            code_parts.push(meta.code || "");
            
            // Only add to desc_parts and short_parts if value is NOT "-"
            if (val.trim() !== "-") {
                desc_parts.push(meta.item_long_description || val);
                short_parts.push(meta.item_short_description || val);
                
                // For selective products, check if this attribute is required
                if (is_selective_template) {
                    var label_upper = label.trim().toUpperCase();
                    if (required_attributes.includes(label_upper)) {
                        selective_short_parts.push(meta.item_short_description || val);
                    }
                }
            }
        }
    }

    // Set item code and description
    frm.set_value("item_code", code_parts.join(""));
    frm.set_value("description", desc_parts.join(" "));
    
    // Determine which short description to use
    var final_short_desc = "";
    
    if (is_selective_template && selective_short_parts.length > 0) {
        // Use filtered short description for selective products
        final_short_desc = selective_short_parts.join(" ");
        
        // Handle kit suffixes if present
        var suffix = "";
        if (frm.doc.duplicated_subassembly == 1) {
            suffix = " SUB ASSY KIT";
        } else if (frm.doc.duplicated_machining_kit == 1) {
            suffix = " M/C KIT";
        }
        
        // Apply suffix and enforce 140 char limit
        if (suffix) {
            var room = 140 - suffix.length;
            if (room < 0) {
                final_short_desc = suffix.substring(0, 140);
            } else {
                final_short_desc = (final_short_desc.substring(0, room).trim() + suffix).trim();
            }
        } else {
            final_short_desc = final_short_desc.substring(0, 140);
        }
        
        console.log("Generated selective short description:", final_short_desc);
    } else {
        // Use regular short description for non-selective templates
        final_short_desc = short_parts.join(" ");
    }
    
    // Set short description
    frm.set_value("short_description", final_short_desc);
    
    // Also update custom_conditional_description if it exists
    if (frm.fields_dict.custom_conditional_description) {
        frm.set_value("custom_conditional_description", final_short_desc);
    }
}

function parse_item_descriptor(frm) {
    let code = frm.doc.item_descriptor.trim();
    let cursor = 0;
    let error_found = false;

    for (let i = 1; i <= 28; i++) {
        let value_field = "attribute_" + i + "_value";
        let metaMap = frm.__attribute_meta__[value_field];
        if (!metaMap) continue;

        let codeLen = 0;
        let rows = Object.values(metaMap);
        if (rows.length && rows[0].code) {
            codeLen = rows[0].code.length;
        }
        if (!codeLen) continue;

        let codePart = code.slice(cursor, cursor + codeLen);
        cursor += codeLen;

        let matched = Object.entries(metaMap).find(([key, meta]) => {
            return (meta.code || "").toUpperCase() === codePart.toUpperCase();
        });

        if (matched) {
            frm.set_value(value_field, matched[1].item_long_description);
        } else {
            frappe.msgprint(`No match found for code part "${codePart}" at position ${i}.`);
            error_found = true;
        }
    }

    if (!error_found) {
        generate_fields(frm);
        setTimeout(() => {
            frm.set_value("item_descriptor", "");
            frm.refresh_field("item_descriptor");
        }, 300);
    } else {
        frm.set_value("item_descriptor", "");
    }
}

function focus_next_field(frm, currentIndex) {
    var next = currentIndex + 1;
    var next_field = "attribute_" + next + "_value";
    if (next <= 28 && frm.fields_dict[next_field] && !frm.fields_dict[next_field].df.hidden) {
        setTimeout(function() {
            var $el = $('[data-fieldname="' + next_field + '"] input');
            if ($el && $el.length) $el.focus();
        }, 150);
    }
}

function attribute_change_handler_factory(index) {
    return function(frm) {
        generate_fields(frm);
        focus_next_field(frm, index);
    };
}

var _events = {};
for (var idx = 1; idx <= 28; idx++) {
    _events["attribute_" + idx + "_value"] = attribute_change_handler_factory(idx);
}
frappe.ui.form.on('Item Generator', _events);

// Function to handle Sales Order update
function updateSalesOrderWithNewItem(frm, context, item_code) {
    console.log("Updating Sales Order with new item:", context.so_name, item_code);
    
    // First, get the Sales Order to check if it's saved
    frappe.call({
        method: "frappe.client.get",
        args: {
            doctype: "Sales Order",
            name: context.so_name
        },
        callback: function(r) {
            if (r.message) {
                // Sales Order exists, now update the specific item
                updateSalesOrderItem(frm, context, item_code);
            } else {
                // Sales Order doesn't exist yet (might be unsaved)
                console.log("Sales Order not found, might be unsaved");
                
                // Store result for Sales Order to pick up later
                const result = {
                    so_name: context.so_name,
                    cdn: context.cdn,
                    item_code: item_code
                };
                sessionStorage.setItem('ig_return_result', JSON.stringify(result));
                
                // Close the Item Generator
                closeItemGeneratorAndRedirect(frm, context.so_name);
            }
        },
        error: function(err) {
            console.error("Error checking Sales Order:", err);
            frm.__after_save_lock = false;
        }
    });
}

// Function to update Sales Order item
function updateSalesOrderItem(frm, context, item_code) {
    if (!context || !context.so_name || !context.cdn) {
        frappe.msgprint({
            title: __("Error"),
            message: __("Missing Sales Order context. Please update manually."),
            indicator: "red"
        });
        return;
    }

    // Directly update the target row using the actual row name (cdn)
    updateSalesOrderItemDirect(frm, context, item_code);
}

// Function to update Sales Order item directly by child row name
function updateSalesOrderItemDirect(frm, context, item_code) {
    frappe.call({
        method: "frappe.client.get",
        args: {
            doctype: "Sales Order",
            name: context.so_name
        },
        callback: function(r) {
            if (r.message && r.message.items) {
                let targetItem = r.message.items.find(it => it.name === context.cdn);

                if (targetItem) {
                    // Update in client-side model
                    frappe.model.set_value("Sales Order Item", targetItem.name, {
                        item_code: item_code,
                        item_name: frm.doc.item_name,
                        description: frm.doc.description,
                        uom: frm.doc.stock_uom
                    });

                    // Save the parent Sales Order
                    frappe.call({
                        method: "frappe.client.save",
                        args: {
                            doc: r.message
                        },
                        callback: function() {
                            frappe.show_alert({
                                message: __("Sales Order row updated with new item {0}", [item_code]),
                                indicator: "green"
                            });
                        }
                    });
                } else {
                    frappe.msgprint({
                        title: __("Error"),
                        message: __("Target Sales Order row not found. Please update manually."),
                        indicator: "red"
                    });
                }
            }
        }
    });
}

// Function to close Item Generator and redirect
function closeItemGeneratorAndRedirect(frm, so_name) {
    if (frm.doc.is_closed !== 1) {
        frappe.call({
            method: "frappe.client.set_value",
            args: {
                doctype: "Item Generator",
                name: frm.doc.name,
                fieldname: "is_closed",
                value: 1
            },
            callback: function() {
                console.log("Item Generator closed");
                frappe.show_alert({
                    message: __("Item Generator closed and Sales Order updated"),
                    indicator: "green"
                });
                
                // Navigate back to Sales Order
                setTimeout(() => {
                    frappe.set_route('Form', 'Sales Order', so_name);
                }, 1500);
                frm.__after_save_lock = false;
            },
            error: function(err) {
                console.error("Error closing Item Generator:", err);
                frm.__after_save_lock = false;
            }
        });
    } else {
        // Navigate back to Sales Order immediately
        setTimeout(() => {
            frappe.set_route('Form', 'Sales Order', so_name);
        }, 1000);
        frm.__after_save_lock = false;
    }
}

// Enhanced Sales Order Integration Functions
function handle_sales_order_integration(frm) {
    const created_item = frm.doc.created_item || frm.doc.item_code;
    
    if (!created_item) {
        frappe.msgprint({
            title: __("Warning"),
            message: __("No item code found. Item may not have been created yet."),
            indicator: "orange"
        });
        frm.__after_save_lock = false;
        return;
    }

    console.log("🔍 Verifying item creation:", created_item);

    // Enhanced item verification with retry mechanism
    verify_item_creation(created_item, 0, (success) => {
        if (success) {
            console.log("✅ Item verified successfully:", created_item);
            
            // Check if this is a Sales Order integration
            if (frm.doc.is_create_with_sales_order === 1) {
                handle_sales_order_return(frm, created_item);
            } else {
                frappe.show_alert({
                    message: __("Item {0} created successfully.", [created_item]),
                    indicator: "green"
                });
                frm.__after_save_lock = false;
            }
        } else {
            frappe.msgprint({
                title: __("Error"),
                message: __("Failed to verify item creation. Please check if item {0} exists.", [created_item]),
                indicator: "red"
            });
            frm.__after_save_lock = false;
        }
    });
}

function verify_item_creation(item_code, retry_count, callback) {
    const max_retries = 5;
    const retry_delay = 1000; // 1 second

    frappe.call({
        method: "frappe.client.get",
        args: {
            doctype: "Item",
            name: item_code
        },
        callback: function(r) {
            if (r.message) {
                // Item found successfully
                callback(true);
            } else if (retry_count < max_retries) {
                // Retry after delay
                setTimeout(() => {
                    verify_item_creation(item_code, retry_count + 1, callback);
                }, retry_delay);
            } else {
                // Max retries reached
                callback(false);
            }
        },
        error: function(err) {
            if (retry_count < max_retries) {
                setTimeout(() => {
                    verify_item_creation(item_code, retry_count + 1, callback);
                }, retry_delay);
            } else {
                callback(false);
            }
        }
    });
}

function handle_sales_order_return(frm, created_item) {
    // Get context from sessionStorage
    const raw = sessionStorage.getItem('ig_return_context');
    if (!raw) {
        frappe.show_alert({
            message: __("Item created but no Sales Order context found."),
            indicator: "orange"
        });
        frm.__after_save_lock = false;
        return;
    }

    let context;
    try {
        context = JSON.parse(raw);
    } catch (e) {
        frappe.msgprint({
            title: __("Error"),
            message: __("Invalid return context data."),
            indicator: "red"
        });
        frm.__after_save_lock = false;
        return;
    }

    if (!context.so_name || !context.cdn) {
        frappe.show_alert({
            message: __("Item created but Sales Order context is incomplete."),
            indicator: "orange"
        });
        frm.__after_save_lock = false;
        return;
    }

    // Update the specific Sales Order Item row
    update_sales_order_item(context, created_item, (success) => {
        if (success) {
            // Store result for Sales Order to pick up
            const result = {
                so_name: context.so_name,
                cdn: context.cdn,
                item_code: created_item
            };
            sessionStorage.setItem('ig_return_result', JSON.stringify(result));
            sessionStorage.removeItem('ig_return_context');

            frappe.show_alert({
                message: __("Item {0} created and linked to Sales Order.", [created_item]),
                indicator: "green"
            });

            // Navigate back to Sales Order after a short delay
            setTimeout(() => {
                frappe.set_route('Form', 'Sales Order', context.so_name);
            }, 1500);
        } else {
            frappe.msgprint({
                title: __("Warning"),
                message: __("Item created successfully but failed to update Sales Order. Please update manually."),
                indicator: "orange"
            });
        }
        frm.__after_save_lock = false;
    });
}

function update_sales_order_item(context, item_code, callback) {
    frappe.call({
        method: "frappe.client.set_value",
        args: {
            doctype: "Sales Order Item",
            name: context.cdn,
            fieldname: "item_code",
            value: item_code
        },
        callback: function(r) {
            if (r && !r.exc) { 
                frappe.call({
                    method: "frappe.client.get_value",
                    args: {
                        doctype: "Item",
                        filters: {"name": item_code},
                        fieldname: ["item_name", "stock_uom"]
                    },
                    callback: function(item_r) {
                        if (item_r.message) {
                            // Update item_name and uom if they exist
                            const updates = {};
                            if (item_r.message.item_name) {
                                updates.item_name = item_r.message.item_name;
                            }
                            if (item_r.message.stock_uom) {
                                updates.uom = item_r.message.stock_uom;
                            }

                            if (Object.keys(updates).length > 0) {
                                frappe.call({
                                    method: "frappe.client.set_value",
                                    args: {
                                        doctype: "Sales Order Item",
                                        name: context.cdn,
                                        fieldname: updates
                                    },
                                    callback: function() {
                                        callback(true);
                                    }
                                });
                            } else {
                                callback(true);
                            }
                        } else {
                            callback(true);
                        }
                    }
                });
            } else {
                callback(false);
            }
        },
        error: function(err) {
            callback(false);
        }
    });
}