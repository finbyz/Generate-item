const MR_FIELDS_TO_PROPAGATE = [
    'custom_drawing_no',
    'custom_pattern_drawing_no',
    'custom_purchase_specification_no',
    'custom_drawing_rev_no',
    'custom_pattern_drawing_rev_no',
    'custom_purchase_specification_rev_no',
    'custom_batch_no'
];

function mr_propagate_parent_fields_to_children(frm) {
    if (!frm.doc.items || !Array.isArray(frm.doc.items)) return;
    let changed = false;
    frm.doc.items.forEach(child => {
        MR_FIELDS_TO_PROPAGATE.forEach(fieldname => {
            const parentValue = frm.doc[fieldname];
            const childValue = child[fieldname];
            if (parentValue && childValue !== parentValue) {
                frappe.model.set_value(child.doctype, child.name, fieldname, parentValue);
                changed = true;
            }
        });
    });
    if (changed) {
        frm.refresh_field('items');
        if (frm.doc.docstatus === 0) frm.dirty();
    }
}

frappe.ui.form.on('Material Request', {
    before_save(frm) {
        mr_propagate_parent_fields_to_children(frm);
    },
    linked_batch: function(frm) {
        const batch_value = frm.doc.linked_batch || '';
        const rows = frm.doc.items || [];
    
        // Step 1: Update custom_batch_no for all items
        rows.forEach(row => {
            frappe.model.set_value(row.doctype, row.name, 'custom_batch_no', batch_value);
        });
    
        // Step 2: For each item, find matching BOM and set fields
        const promises = rows.map(row => {
            return new Promise((resolve) => {
                if (!row.sales_order || !row.item_code) {
                    resolve();
                    return;
                }
    
                console.log('Fetching BOM data:', row.sales_order, row.item_code, batch_value);
    
                frappe.call({
                    method: "generate_item.utils.material_request.get_bom_name",
                    args: {
                        linked_batch: batch_value,
                        sales_order: row.sales_order,
                        linked_batch: batch_value, // Use the variable directly
                        item_code: row.item_code
                    },
                    callback: function(r) {
                        if (r.message && Object.keys(r.message).length > 0) {
                            let bom_item = r.message;
                            console.log('BOM Item data received:', bom_item);
    
                            // Set all fields at once to reduce refresh calls
                            frappe.model.set_value(row.doctype, row.name, {
                                "bom_no": bom_item || "",
                            });
                        } else {
                            console.log('No BOM data found for item:', row.item_code);
                        }
                        resolve();
                    }
                });
            });
        });
    
        // Wait for all calls to complete then refresh
        Promise.all(promises).then(() => {
            frm.refresh_field('items');
        });
    },
    refresh(frm) {
        // Populate linked_batch options with batches tied to Partly Delivered SOs
        const df = frappe.meta.get_docfield('Material Request', 'linked_batch');
        if (df && df.fieldtype === 'Select') {
            frappe.call({
                method: 'generate_item.api.material_request.get_batches_linked_to_partly_delivered_sales_orders',
                args: { item_code: null },
                callback: (r) => {
                    if (!r.exc) {
                        const batches = r.message || [];
                        // Ensure empty option first
                        const options = [''].concat(batches);
                        frm.set_df_property('linked_batch', 'options', options);
                        if (batches.length && !frm.doc.linked_batch) {
                            // leave empty; user can choose
                        }
                    }
                }
            });
        }
    },
    custom_drawing_no: mr_propagate_parent_fields_to_children,
    custom_pattern_drawing_no: mr_propagate_parent_fields_to_children,
    custom_purchase_specification_no: mr_propagate_parent_fields_to_children,
    custom_drawing_rev_no: mr_propagate_parent_fields_to_children,
    custom_pattern_drawing_rev_no: mr_propagate_parent_fields_to_children,
    custom_purchase_specification_rev_no: mr_propagate_parent_fields_to_children,
    custom_batch_no: mr_propagate_parent_fields_to_children
});


frappe.ui.form.on("Material Request Item", {
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
                        console.log('BOM Item custom fields:', bom_item);
                        
                        // Update custom fields from BOM Item
                        frappe.model.set_value(row.doctype, row.name, {
                            "custom_drawing_no": bom_item.custom_drawing_no || "",
                            "custom_pattern_drawing_no": bom_item.custom_pattern_drawing_no || "",
                            "custom_purchase_specification_no": bom_item.custom_purchase_specification_no || "",
                            "custom_drawing_rev_no": bom_item.custom_drawing_rev_no || "",
                            "custom_pattern_drawing_rev_no": bom_item.custom_pattern_drawing_rev_no || "",
                            "custom_purchase_specification_rev_no": bom_item.custom_purchase_specification_rev_no || "",
                            "custom_batch_no": bom_item.custom_batch_no || ""
                        });
                        
                        frm.refresh_field('items');
                    }
                }
            });
        }
    }
});
