frappe.ui.form.on('Subcontracting Order Item', {
    // item_code: function(frm, cdt, cdn) {
    //     let row = locals[cdt][cdn];

    //     // If batch already exists in parent, push it into the row
    //     if (frm.doc.custom_batch_no && row.item_code) {
    //         frappe.model.set_value(row.doctype, row.name, 'custom_batch_no', frm.doc.custom_batch_no);
    //     }
    // },
   

    bom_no: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        
        // When BOM is changed, fetch custom fields from BOM Item
        if (row.bom_no && row.item_code) {
            frappe.call({
                method: "generate_item.api.bom_item.get_bom_item_custom_fields",
                args: {
                    bom_no: row.bom_no,
                    item_code: row.item_code
                },
                callback: function(r) {
                    if (r.message && Object.keys(r.message).length > 0) {
                        let bom_item = r.message;
                        // Update custom fields from BOM Item to items table
                        frappe.model.set_value(row.doctype, row.name, {
                            "custom_drawing_no": bom_item.custom_drawing_no || "",
                            "custom_pattern_drawing_no": bom_item.custom_pattern_drawing_no || "",
                            "custom_purchase_specification_no": bom_item.custom_purchase_specification_no || "",
                            "custom_drawing_rev_no": bom_item.custom_drawing_rev_no || "",
                            "custom_pattern_drawing_rev_no": bom_item.custom_pattern_drawing_rev_no || "",
                            "custom_purchase_specification_rev_no": bom_item.custom_purchase_specification_rev_no || "",
                            "custom_batch_no": bom_item.custom_batch_no || "",
                            "bom_reference": bom_item.parent || ""
                        });
                        
                        frm.refresh_field('items');
                        
                        // Also check supplied_items table for any items that match BOM Item
                        if (frm.doc.supplied_items && frm.doc.supplied_items.length > 0) {
                            frm.doc.supplied_items.forEach(supplied_row => {
                                // Check if this supplied_item's rm_item_code matches any BOM Item
                                if (supplied_row.rm_item_code) {
                                    // Fetch custom fields for supplied_items using rm_item_code
                                    frappe.call({
                                        method: "generate_item.api.bom_item.get_bom_item_custom_fields",
                                        args: {
                                            bom_no: row.bom_no,
                                            item_code: supplied_row.rm_item_code
                                        },
                                        callback: function(supplied_r) {
                                            if (supplied_r.message && Object.keys(supplied_r.message).length > 0) {
                                                let supplied_bom_item = supplied_r.message;
                                                
                                                // Update custom fields in supplied_items
                                                frappe.model.set_value(supplied_row.doctype, supplied_row.name, {
                                                    "custom_drawing_no": supplied_bom_item.custom_drawing_no || "",
                                                    "custom_pattern_drawing_no": supplied_bom_item.custom_pattern_drawing_no || "",
                                                    "custom_purchase_specification_no": supplied_bom_item.custom_purchase_specification_no || "",
                                                    "custom_drawing_rev_no": supplied_bom_item.custom_drawing_rev_no || "",
                                                    "custom_pattern_drawing_rev_no": supplied_bom_item.custom_pattern_drawing_rev_no || "",
                                                    "custom_purchase_specification_rev_no": supplied_bom_item.custom_purchase_specification_rev_no || "",
                                                    "custom_batch_no": supplied_bom_item.custom_batch_no || "",
                                                    "bom_reference": supplied_bom_item.parent || ""
                                                });
                                                
                                                frm.refresh_field('supplied_items');
                                            }
                                        }
                                    });
                                }
                            });
                        }
                    }
                }
            });
        }
    }
    
});



frappe.ui.form.on('Subcontracting Order', {
    onload: function(frm) {
        if (frm.is_new() && frm.doc.custom_batch_no) {
            set_batch_no_in_items(frm, frm.doc.custom_batch_no);
        }
    },

    after_save: async function(frm) {
        await fetch_bom_custom_fields_on_load(frm);
    },

    custom_batch_no: function(frm) {
        if (frm.doc.custom_batch_no) {
            set_batch_no_in_items(frm, frm.doc.custom_batch_no);
        }
    }
});

function set_batch_no_in_items(frm, batch_no) {
    if (frm.doc.items?.length > 0) {
        frm.doc.items.forEach(item => {
            frappe.model.set_value(item.doctype, item.name, 'custom_batch_no', batch_no);
        });
        frm.refresh_field('items');
    }
}

async function fetch_bom_custom_fields_on_load(frm) {
    let calls = [];

    const make_call = (args, target, fieldname) => {
        return new Promise(resolve => {
            frappe.call({
                method: "generate_item.api.bom_item.get_bom_item_custom_fields",
                args,
                callback: function(r) {
                    if (r.message && Object.keys(r.message).length > 0) {
                        let updated_fields = {
                            "custom_drawing_no": r.message.custom_drawing_no || "",
                            "custom_pattern_drawing_no": r.message.custom_pattern_drawing_no || "",
                            "custom_purchase_specification_no": r.message.custom_purchase_specification_no || "",
                            "custom_drawing_rev_no": r.message.custom_drawing_rev_no || "",
                            "custom_pattern_drawing_rev_no": r.message.custom_pattern_drawing_rev_no || "",
                            "custom_purchase_specification_rev_no": r.message.custom_purchase_specification_rev_no || "",
                            "custom_batch_no": r.message.custom_batch_no || "",
                            "bom_reference": r.message.parent || ""
                        };
                        Object.assign(target, updated_fields);
                    }
                    resolve();
                }
            });
        });
    };

    // main items
    if (frm.doc.items?.length > 0) {
        frm.doc.items.forEach(item => {
            const bom_value = item.bom_no || item.bom;
            if (bom_value && item.item_code) {
                calls.push(make_call({ bom_no: bom_value, item_code: item.item_code }, item, 'items'));
            }
        });
    }

    // supplied items
    if (frm.doc.supplied_items?.length > 0) {
        frm.doc.supplied_items.forEach(supplied_item => {
            if (supplied_item.rm_item_code) {
                const corresponding_item = frm.doc.items.find(i => i.item_code === supplied_item.main_item_code);
                const corresponding_bom = corresponding_item ? (corresponding_item.bom_no || corresponding_item.bom) : null;

                if (corresponding_bom) {
                    calls.push(make_call(
                        { bom_no: corresponding_bom, item_code: supplied_item.rm_item_code },
                        supplied_item,
                        'supplied_items'
                    ));
                }
            }
        });
    }

    await Promise.all(calls);

    // update directly to DB (no update popup)
    await frappe.call({
        method: "generate_item.utils.subcontracting_order.update_supplied_items_in_db",
        args: {
            parent: frm.doc.name,
            data: JSON.stringify(frm.doc.supplied_items)
        },
        callback: function(r) {
        }
    });
}


