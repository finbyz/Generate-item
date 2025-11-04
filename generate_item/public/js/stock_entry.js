// frappe.ui.form.on('Stock Entry', {
//     onload: function(frm) {
//         // Handle case when stock entry is loaded with work order already set (backend creation)
//         if (frm.doc.work_order && !frm.doc.custom_batch_no) {
//             set_custom_fields_from_work_order(frm);
//         }
//         if (frm.doc.custom_batch_no) {
//             set_batch_no_in_items(frm, frm.doc.custom_batch_no);
//         }
//         // Fixed: Use frm.is_new() and remove extra arg in call
//         if (frm.doc.subcontracting_order && frm.is_new()) {
//             set_custom_fields_in_items(frm);
//         }
//     },
    
//     work_order: function(frm) {
//         if (!frm.doc.work_order) return;
//         console.log('work_order changed', frm.doc.work_order);
//         // Apply on the UI immediately when Work Order is set
//         set_custom_fields_from_work_order(frm);
//     },
    
//     subcontracting_order: function(frm) {
//         if (frm.doc.subcontracting_order) {
//             set_custom_fields_in_items(frm);
//         }
//     },

//     custom_batch_no: function(frm) {
//         // Whenever batch is manually set/changed, update in items
//         if (frm.doc.custom_batch_no) {
//             set_batch_no_in_items(frm, frm.doc.custom_batch_no);
//         }
//     },
    
//     purpose: function(frm) {
//         // If purpose changes to manufacturing and we have work order, set custom fields
//         if (frm.doc.work_order && frm.doc.items) {
//             if (['Manufacture', 'Material Transfer for Manufacture'].includes(frm.doc.purpose)) {
//                 set_custom_fields_from_work_order(frm);
//             }
//         }
//     }
// });

// // Helper function to set custom fields from work order
// function set_custom_fields_from_work_order(frm) {
//     if (!frm.doc.work_order) return;
    
//     // Fetch full work order document to access required_items
//     frappe.db.get_doc('Work Order', frm.doc.work_order)
//         .then(wo => {
//             if (!wo) return;
//             console.log('work order fetched', wo);
            
//             // Set BOM on parent if available
//             if (wo.bom_no) {
//                 frm.set_value('bom_no', wo.bom_no);
//             }

//             // Set custom_batch_no in parent if available
//             const batch_no = wo.custom_batch_no;
//             if (batch_no && !frm.doc.custom_batch_no) {
//                 frm.set_value('custom_batch_no', batch_no);
//             }
            
//             // Prepare a dictionary of custom fields from work order's required_items, keyed by item_code
//             const required_items_dict = {};
//             wo.required_items.forEach(req_item => {
//                 if (req_item.item_code) {
//                     required_items_dict[req_item.item_code] = {
//                         custom_batch_no: req_item.custom_batch_no,
//                         custom_drawing_no: req_item.custom_drawing_no,
//                         custom_drawing_rev_no: req_item.custom_drawing_rev_no,
//                         custom_pattern_drawing_no: req_item.custom_pattern_drawing_no,
//                         custom_pattern_drawing_rev_no: req_item.custom_pattern_drawing_rev_no,
//                         custom_purchase_specification_no: req_item.custom_purchase_specification_no,
//                         custom_purchase_specification_rev_no: req_item.custom_purchase_specification_rev_no,
//                     };
//                 }
//             });

//         })
//         .catch(err => {
//             console.error('Error fetching work order details:', err);
//         });
// }

// function apply_custom_fields_to_item_row(row, custom_fields) {
//     if (custom_fields.custom_batch_no) {
//         frappe.model.set_value(row.doctype, row.name, 'custom_batch_no', custom_fields.custom_batch_no);
//     }
//     if (custom_fields.custom_drawing_no) {
//         frappe.model.set_value(row.doctype, row.name, 'custom_drawing_no', custom_fields.custom_drawing_no);
//     }
//     if (custom_fields.custom_drawing_rev_no) {
//         frappe.model.set_value(row.doctype, row.name, 'custom_drawing_rev_no', custom_fields.custom_drawing_rev_no);
//     }
//     if (custom_fields.custom_pattern_drawing_no) {
//         frappe.model.set_value(row.doctype, row.name, 'custom_pattern_drawing_no', custom_fields.custom_pattern_drawing_no);
//     }
//     if (custom_fields.custom_pattern_drawing_rev_no) {
//         frappe.model.set_value(row.doctype, row.name, 'custom_pattern_drawing_rev_no', custom_fields.custom_pattern_drawing_rev_no);
//     }
//     if (custom_fields.custom_purchase_specification_no) {
//         frappe.model.set_value(row.doctype, row.name, 'custom_purchase_specification_no', custom_fields.custom_purchase_specification_no);
//     }
//     if (custom_fields.custom_purchase_specification_rev_no) {
//         frappe.model.set_value(row.doctype, row.name, 'custom_purchase_specification_rev_no', custom_fields.custom_purchase_specification_rev_no);
//     }
// }

// async function set_custom_fields_from_work_order(frm) {
//     if (!frm.doc.work_order) return;

//     try {
//         const wo = await frappe.db.get_doc('Work Order', frm.doc.work_order);
//         if (!wo) return;
//         console.log('work order fetched', wo);

//         // Set BOM on parent if available
//         if (wo.bom_no) {
//             frm.set_value('bom_no', wo.bom_no);
//         }

//         // Set custom_batch_no in parent if available
//         const batch_no = wo.custom_batch_no;
//         if (batch_no && !frm.doc.custom_batch_no) {
//             frm.set_value('custom_batch_no', batch_no);
//         }

//         // Prepare dictionary of required_items by item_code
//         const required_items_dict = {};
//         (wo.required_items || []).forEach(req_item => {
//             if (req_item.item_code) {
//                 required_items_dict[req_item.item_code] = {
//                     custom_batch_no: req_item.custom_batch_no,
//                     custom_drawing_no: req_item.custom_drawing_no,
//                     custom_drawing_rev_no: req_item.custom_drawing_rev_no,
//                     custom_pattern_drawing_no: req_item.custom_pattern_drawing_no,
//                     custom_pattern_drawing_rev_no: req_item.custom_pattern_drawing_rev_no,
//                     custom_purchase_specification_no: req_item.custom_purchase_specification_no,
//                     custom_purchase_specification_rev_no: req_item.custom_purchase_specification_rev_no
//                 };
//             }
//         });

//         // Apply to each item row in Stock Entry
//         if (frm.doc.items && frm.doc.items.length > 0) {
//             frm.doc.items.forEach(row => {
//                 const custom_fields = required_items_dict[row.item_code];
//                 if (custom_fields) {
//                     apply_custom_fields_to_item_row(row, custom_fields);
//                 }
//             });
//             frm.refresh_field('items');
//         }
//     } catch (err) {
//         console.error('Error fetching work order details:', err);
//     }
// }


// // Helper function to set batch no in items table
// function set_batch_no_in_items(frm, batch_no) {
//     if (frm.doc.items && frm.doc.items.length > 0) {
//         frm.doc.items.forEach(item => {
//             frappe.model.set_value(item.doctype, item.name, 'custom_batch_no', batch_no);
//         });
//         frm.refresh_field('items');
//     }
// }

// frappe.ui.form.on('Stock Entry Detail', {
//     item_code: function(frm, cdt, cdn) {
//         let row = locals[cdt][cdn];

//         // If batch already exists in parent, push it into the row
//         if (frm.doc.custom_batch_no && row.item_code) {
//             frappe.model.set_value(row.doctype, row.name, 'custom_batch_no', frm.doc.custom_batch_no);
//         }
//     }
// });

frappe.ui.form.on('Stock Entry', {
    onload: function(frm) {
        // Case 1: Work Order is already set
        if (frm.doc.work_order && !frm.doc.custom_batch_no) {
            set_custom_fields_from_work_order(frm);
        }
        // Case 2: Batch exists, set in items
        if (frm.doc.custom_batch_no) {
            set_batch_no_in_items(frm, frm.doc.custom_batch_no);
        }
        // Case 3: Subcontracting Order present on new doc
        if (frm.doc.subcontracting_order && frm.is_new()) {
            set_custom_fields_in_items(frm);
        }
    },

    work_order: function(frm) {
        if (!frm.doc.work_order) return;
        console.log('work_order changed:', frm.doc.work_order);
        set_custom_fields_from_work_order(frm);
    },

    subcontracting_order: function(frm) {
        if (frm.doc.subcontracting_order) {
            set_custom_fields_in_items(frm);
        }
    },

    custom_batch_no: function(frm) {
        if (frm.doc.custom_batch_no) {
            set_batch_no_in_items(frm, frm.doc.custom_batch_no);
        }
    },

    purpose: function(frm) {
        if (frm.doc.work_order && frm.doc.items) {
            if (['Manufacture', 'Material Transfer for Manufacture'].includes(frm.doc.purpose)) {
                set_custom_fields_from_work_order(frm);
            }
        }
    }
});


// ✅ Fetch and apply custom fields from Work Order without recreating items
// ✅ Fetch and apply custom fields from Work Order
async function set_custom_fields_from_work_order(frm) {
    if (!frm.doc.work_order) return;

    try {
        const work_order = await frappe.db.get_doc('Work Order', frm.doc.work_order);
        console.log("✅ Work Order fetched:", work_order);

        // Set header fields
        if (work_order.bom_no) {
            frm.set_value('bom_no', work_order.bom_no);
        }
        if (work_order.custom_batch_no) {
            frm.set_value('custom_batch_no', work_order.custom_batch_no);
        }

        // Wait for items to be populated (important for async operations)
        await frappe.timeout(0.5);

        // Check if items exist
        if (!frm.doc.items || frm.doc.items.length === 0) {
            console.log("⚠️ No items found in Stock Entry yet");
            return;
        }

        // Create a map of required_items by item_code for faster lookup
        const required_items_map = {};
        if (work_order.required_items && work_order.required_items.length > 0) {
            work_order.required_items.forEach(req_item => {
                if (req_item.item_code ) {
                    required_items_map[req_item.item_code] = req_item;
                }
            });
        }

        console.log("📦 Required items map:", required_items_map);

        // Apply custom fields to each item in Stock Entry
        let updated_count = 0;
        frm.doc.items.forEach(item => {
            // Match by item_code (primary match)
            const match = required_items_map[item.item_code];
            
            console.log(`🔍 Checking item: ${item.item_code}`, match ? '✅ Match found' : '❌ No match');

            if (match) {
                // Set custom_batch_no
                if (match.custom_batch_no) {
                    frappe.model.set_value(item.doctype, item.name, 'custom_batch_no', match.custom_batch_no);
                }
                
                // Set drawing fields
                if (match.custom_drawing_no) {
                    frappe.model.set_value(item.doctype, item.name, 'custom_drawing_no', match.custom_drawing_no);
                }
                if (match.custom_drawing_rev_no) {
                    frappe.model.set_value(item.doctype, item.name, 'custom_drawing_rev_no', match.custom_drawing_rev_no);
                }
                
                // Set pattern drawing fields
                if (match.custom_pattern_drawing_no) {
                    frappe.model.set_value(item.doctype, item.name, 'custom_pattern_drawing_no', match.custom_pattern_drawing_no);
                }
                if (match.custom_pattern_drawing_rev_no) {
                    frappe.model.set_value(item.doctype, item.name, 'custom_pattern_drawing_rev_no', match.custom_pattern_drawing_rev_no);
                }
                
                // Set purchase specification fields
                if (match.custom_purchase_specification_no) {
                    frappe.model.set_value(item.doctype, item.name, 'custom_purchase_specification_no', match.custom_purchase_specification_no);
                }
                if (match.custom_purchase_specification_rev_no) {
                    frappe.model.set_value(item.doctype, item.name, 'custom_purchase_specification_rev_no', match.custom_purchase_specification_rev_no);
                }
                
                updated_count++;
            }
        });

        frm.refresh_field('items');
        
        if (updated_count > 0) {
            frappe.show_alert({ 
                message: `Custom fields updated for ${updated_count} item(s) from Work Order`, 
                indicator: "green" 
            });
        } else {
            frappe.show_alert({ 
                message: "No matching items found to update", 
                indicator: "orange" 
            });
        }

    } catch (err) {
        console.error("⚠️ Error fetching Work Order:", err);
        frappe.show_alert({ 
            message: "Failed to fetch Work Order details", 
            indicator: "red" 
        });
    }
}


// ✅ Helper: Apply to One Item Row
function apply_custom_fields_to_item_row(row, custom_fields) {
    for (const [field, value] of Object.entries(custom_fields)) {
        if (value) frappe.model.set_value(row.doctype, row.name, field, value);
    }
}


// ✅ Helper: Set Batch in All Items
function set_batch_no_in_items(frm, batch_no) {
    if (!batch_no || !frm.doc.items) return;
    frm.doc.items.forEach(item => {
        frappe.model.set_value(item.doctype, item.name, 'custom_batch_no', batch_no);
    });
    frm.refresh_field('items');
}


// ✅ Optional (for Subcontracting Orders)
async function set_custom_fields_in_items(frm) {
    if (!frm.doc.subcontracting_order) return;

    try {
        const so = await frappe.db.get_doc('Subcontracting Order', frm.doc.subcontracting_order);
        if (!so.supplied_items?.length) return;

        frm.doc.items.forEach(item => {
            let supplied_item = so.supplied_items.find(si =>
                si.rm_item_code === item.item_code &&
                si.main_item_code === item.subcontracted_item
            );

            if (supplied_item) {
                const custom_fields = {
                    custom_batch_no: supplied_item.custom_batch_no,
                    custom_drawing_no: supplied_item.custom_drawing_no,
                    custom_drawing_rev_no: supplied_item.custom_drawing_rev_no,
                    custom_pattern_drawing_no: supplied_item.custom_pattern_drawing_no,
                    custom_pattern_drawing_rev_no: supplied_item.custom_pattern_drawing_rev_no,
                    custom_purchase_specification_no: supplied_item.custom_purchase_specification_no,
                    custom_purchase_specification_rev_no: supplied_item.custom_purchase_specification_rev_no,
                    bom_reference: supplied_item.bom_reference
                };
                apply_custom_fields_to_item_row(item, custom_fields);
            }
        });

        frm.refresh_field('items');
    } catch (err) {
        console.error('❌ Error fetching Subcontracting Order details:', err);
    }
}


// ✅ Stock Entry Detail Event
frappe.ui.form.on('Stock Entry Detail', {
    item_code: function(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (frm.doc.custom_batch_no && row.item_code) {
            frappe.model.set_value(row.doctype, row.name, 'custom_batch_no', frm.doc.custom_batch_no);
        }
    }
});
