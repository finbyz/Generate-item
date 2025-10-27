// frappe.ui.form.on('Stock Entry', {
//     onload: function(frm) {
//         // Handle case when stock entry is loaded with work order already set (backend creation)
//         if (frm.doc.work_order && !frm.doc.custom_batch_no) {
//             set_batch_no_from_work_order(frm);
//         }
//         if (frm.doc.custom_batch_no) {
//             set_batch_no_in_items(frm, frm.doc.custom_batch_no);
//         }
//     },
    
//     work_order: function(frm) {
//         if (frm.doc.work_order) {
//             set_batch_no_from_work_order(frm);
//         }
//     },

//     custom_batch_no: function(frm) {
//         // Whenever batch is manually set/changed, update in items
//         if (frm.doc.custom_batch_no) {
//             set_batch_no_in_items(frm, frm.doc.custom_batch_no);
//         }
//     },
    
//     purpose: function(frm) {
//         // If purpose changes to manufacturing and we have work order, set batch numbers
//         if (frm.doc.work_order && frm.doc.custom_batch_no && frm.doc.items) {
//             if (['Manufacture', 'Material Transfer for Manufacture'].includes(frm.doc.purpose)) {
//                 frm.doc.items.forEach(item => {
//                     frappe.model.set_value(item.doctype, item.name, 'custom_batch_no', frm.doc.custom_batch_no);
//                 });
//                 frm.refresh_field('items');
//             }
//         }
//     }
// });

// // Helper function to set batch number from work order
// function set_batch_no_from_work_order(frm) {
//     if (!frm.doc.work_order) return;
    
//     // Get work order details and set custom_batch_no
//     frappe.db.get_value('Work Order', frm.doc.work_order, ['custom_batch_no', 'production_item'])
//         .then(r => {
//             if (r.message && r.message.custom_batch_no) {
//                 // Set custom_batch_no in parent
//                 frm.set_value('custom_batch_no', r.message.custom_batch_no);
                
//                 // Set custom_batch_no in child items
//                 if (frm.doc.items && frm.doc.items.length > 0) {
//                     frm.doc.items.forEach(item => {
//                         // Set for production item or all items in manufacturing entries
//                         if (r.message.production_item && item.item_code === r.message.production_item) {
//                             frappe.model.set_value(item.doctype, item.name, 'custom_batch_no', r.message.custom_batch_no);
//                         } else if (frm.doc.purpose && ['Manufacture', 'Material Transfer for Manufacture'].includes(frm.doc.purpose)) {
//                             frappe.model.set_value(item.doctype, item.name, 'custom_batch_no', r.message.custom_batch_no);
//                         }
//                     });
//                     frm.refresh_field('items');
//                 }
//             }
//         })
//         .catch(err => {
//             console.error('Error fetching work order details:', err);
//         });
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
        // Handle case when stock entry is loaded with work order already set (backend creation)
        if (frm.doc.work_order && !frm.doc.custom_batch_no) {
            set_batch_no_from_work_order(frm);
        }
        if (frm.doc.custom_batch_no) {
            set_batch_no_in_items(frm, frm.doc.custom_batch_no);
        }
        // Fixed: Use frm.is_new() or frm.doc.__islocal instead of frm.__local()
        if (frm.doc.subcontracting_order && frm.is_new()) {
            set_custom_fields_in_items(frm, frm.doc.subcontracting_order);
        }
    },
    
    work_order: function(frm) {
        if (frm.doc.work_order) {
            set_batch_no_from_work_order(frm);
        }
    },
    
    subcontracting_order: function(frm) {
        if (frm.doc.subcontracting_order) {
            set_custom_fields_in_items(frm);
        }
    },

    custom_batch_no: function(frm) {
        // Whenever batch is manually set/changed, update in items
        if (frm.doc.custom_batch_no) {
            set_batch_no_in_items(frm, frm.doc.custom_batch_no);
        }
    },
    
    purpose: function(frm) {
        // If purpose changes to manufacturing and we have work order, set batch numbers
        if (frm.doc.work_order && frm.doc.custom_batch_no && frm.doc.items) {
            if (['Manufacture', 'Material Transfer for Manufacture'].includes(frm.doc.purpose)) {
                frm.doc.items.forEach(item => {
                    frappe.model.set_value(item.doctype, item.name, 'custom_batch_no', frm.doc.custom_batch_no);
                });
                frm.refresh_field('items');
            }
        }
    }
});

// Helper function to set batch number from work order
function set_batch_no_from_work_order(frm) {
    if (!frm.doc.work_order) return;
    
    // Get work order details and set custom_batch_no
    frappe.db.get_value('Work Order', frm.doc.work_order, ['custom_batch_no', 'production_item'])
        .then(r => {
            if (r.message && r.message.custom_batch_no) {
                // Set custom_batch_no in parent
                frm.set_value('custom_batch_no', r.message.custom_batch_no);
                
                // Set custom_batch_no in child items
                if (frm.doc.items && frm.doc.items.length > 0) {
                    frm.doc.items.forEach(item => {
                        // Set for production item or all items in manufacturing entries
                        if (r.message.production_item && item.item_code === r.message.production_item) {
                            frappe.model.set_value(item.doctype, item.name, 'custom_batch_no', r.message.custom_batch_no);
                        } else if (frm.doc.purpose && ['Manufacture', 'Material Transfer for Manufacture'].includes(frm.doc.purpose)) {
                            frappe.model.set_value(item.doctype, item.name, 'custom_batch_no', r.message.custom_batch_no);
                        }
                    });
                    frm.refresh_field('items');
                }
            }
        })
        .catch(err => {
            console.error('Error fetching work order details:', err);
        });
}

async function set_custom_fields_in_items(frm) {
    if (!frm.doc.subcontracting_order) return;

    try {
        const so = await frappe.db.get_doc('Subcontracting Order', frm.doc.subcontracting_order);

        if (!so.supplied_items || so.supplied_items.length === 0) return;


        frm.doc.items?.forEach(item => {
            // Method 1: Use sco_rm_detail field to find exact match
            let supplied_item = null;
            
            if (item.sco_rm_detail) {
                // Direct reference via sco_rm_detail field
                supplied_item = so.supplied_items.find(si => si.name === item.sco_rm_detail);
            }
            
            // Method 2: Fallback to matching by item_code and subcontracted_item
            if (!supplied_item) {
                supplied_item = so.supplied_items.find(si => 
                    si.rm_item_code === item.item_code && 
                    si.main_item_code === item.subcontracted_item
                );
            }
            

            if (supplied_item) {
                // Set all custom fields from supplied items
                if (supplied_item.custom_batch_no) {
                    frappe.model.set_value(item.doctype, item.name, 'custom_batch_no', supplied_item.custom_batch_no);
                }
                if (supplied_item.custom_drawing_no) {
                    frappe.model.set_value(item.doctype, item.name, 'custom_drawing_no', supplied_item.custom_drawing_no);
                }
                if (supplied_item.custom_drawing_rev_no) {
                    frappe.model.set_value(item.doctype, item.name, 'custom_drawing_rev_no', supplied_item.custom_drawing_rev_no);
                }
                if (supplied_item.custom_pattern_drawing_no) {
                    frappe.model.set_value(item.doctype, item.name, 'custom_pattern_drawing_no', supplied_item.custom_pattern_drawing_no);
                }
                if (supplied_item.custom_pattern_drawing_rev_no) {
                    frappe.model.set_value(item.doctype, item.name, 'custom_pattern_drawing_rev_no', supplied_item.custom_pattern_drawing_rev_no);
                }
                if (supplied_item.custom_purchase_specification_no) {
                    frappe.model.set_value(item.doctype, item.name, 'custom_purchase_specification_no', supplied_item.custom_purchase_specification_no);
                }
                if (supplied_item.custom_purchase_specification_rev_no) {
                    frappe.model.set_value(item.doctype, item.name, 'custom_purchase_specification_rev_no', supplied_item.custom_purchase_specification_rev_no);
                }
                if (supplied_item.bom_reference) {
                    frappe.model.set_value(item.doctype, item.name, 'bom_reference', supplied_item.bom_reference);
                }
            }
        });

        frm.refresh_field('items');
    } catch (err) {
        console.error('Error fetching Subcontracting Order details:', err);
    }
}

// Helper function to set batch no in items table
function set_batch_no_in_items(frm, batch_no) {
    if (frm.doc.items && frm.doc.items.length > 0) {
        frm.doc.items.forEach(item => {
            frappe.model.set_value(item.doctype, item.name, 'custom_batch_no', batch_no);
        });
        frm.refresh_field('items');
    }
}

frappe.ui.form.on('Stock Entry Detail', {
    item_code: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        // If batch already exists in parent, push it into the row
        if (frm.doc.custom_batch_no && row.item_code) {
            frappe.model.set_value(row.doctype, row.name, 'custom_batch_no', frm.doc.custom_batch_no);
        }
    }
});