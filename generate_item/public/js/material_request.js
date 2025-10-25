// // const MR_FIELDS_TO_PROPAGATE = [
// //     'custom_drawing_no',
// //     'custom_pattern_drawing_no',
// //     'custom_purchase_specification_no',
// //     'custom_drawing_rev_no',
// //     'custom_pattern_drawing_rev_no',
// //     'custom_purchase_specification_rev_no',
// //     'custom_batch_no'
// // ];

// // function mr_propagate_parent_fields_to_children(frm) {
// //     if (!frm.doc.items || !Array.isArray(frm.doc.items)) return;
// //     let changed = false;
// //     frm.doc.items.forEach(child => {
// //         MR_FIELDS_TO_PROPAGATE.forEach(fieldname => {
// //             const parentValue = frm.doc[fieldname];
// //             const childValue = child[fieldname];
// //             if (parentValue && childValue !== parentValue) {
// //                 frappe.model.set_value(child.doctype, child.name, fieldname, parentValue);
// //                 changed = true;
// //             }
// //         });
// //     });
// //     if (changed) {
// //         frm.refresh_field('items');
// //         if (frm.doc.docstatus === 0) frm.dirty();
// //     }
// // }

// // frappe.ui.form.on('Material Request', {
// //     before_save(frm) {
// //         mr_propagate_parent_fields_to_children(frm);
// //     },
// //     linked_batch: function(frm) {
// //         const batch_value = frm.doc.linked_batch || '';
// //         const rows = frm.doc.items || [];
    
// //         // Step 1: Update custom_batch_no for all items
// //         rows.forEach(row => {
// //             frappe.model.set_value(row.doctype, row.name, 'custom_batch_no', batch_value);
// //         });
    
// //         // Step 2: For each item, find matching BOM and set fields
// //         const promises = rows.map(row => {
// //             return new Promise((resolve) => {
// //                 if (!row.sales_order || !row.item_code) {
// //                     resolve();
// //                     return;
// //                 }
    
// //                 console.log('Fetching BOM data:', row.sales_order, row.item_code, batch_value);
    
// //                 frappe.call({
// //                     method: "generate_item.utils.material_request.get_bom_name",
// //                     args: {
// //                         linked_batch: batch_value,
// //                         sales_order: row.sales_order,
// //                         linked_batch: batch_value, // Use the variable directly
// //                         item_code: row.item_code
// //                     },
// //                     callback: function(r) {
// //                         if (r.message && Object.keys(r.message).length > 0) {
// //                             let bom_item = r.message;
// //                             console.log('BOM Item data received:', bom_item);
    
// //                             // Set all fields at once to reduce refresh calls
// //                             frappe.model.set_value(row.doctype, row.name, {
// //                                 "bom_no": bom_item || "",
// //                             });
// //                         } else {
// //                             console.log('No BOM data found for item:', row.item_code);
// //                         }
// //                         resolve();
// //                     }
// //                 });
// //             });
// //         });
    
// //         // Wait for all calls to complete then refresh
// //         Promise.all(promises).then(() => {
// //             frm.refresh_field('items');
// //         });
// //     },
// //     refresh(frm) {
// //         // Populate linked_batch options with batches tied to Partly Delivered SOs
// //         const df = frappe.meta.get_docfield('Material Request', 'linked_batch');
// //         if (df && df.fieldtype === 'Select') {
// //             frappe.call({
// //                 method: 'generate_item.api.material_request.get_batches_linked_to_partly_delivered_sales_orders',
// //                 args: { item_code: null },
// //                 callback: (r) => {
// //                     if (!r.exc) {
// //                         const batches = r.message || [];
// //                         // Ensure empty option first
// //                         const options = [''].concat(batches);
// //                         frm.set_df_property('linked_batch', 'options', options);
// //                         if (batches.length && !frm.doc.linked_batch) {
// //                             // leave empty; user can choose
// //                         }
// //                     }
// //                 }
// //             });
// //         }
// //     },
// //     custom_drawing_no: mr_propagate_parent_fields_to_children,
// //     custom_pattern_drawing_no: mr_propagate_parent_fields_to_children,
// //     custom_purchase_specification_no: mr_propagate_parent_fields_to_children,
// //     custom_drawing_rev_no: mr_propagate_parent_fields_to_children,
// //     custom_pattern_drawing_rev_no: mr_propagate_parent_fields_to_children,
// //     custom_purchase_specification_rev_no: mr_propagate_parent_fields_to_children,
// //     custom_batch_no: mr_propagate_parent_fields_to_children
// // });


// // frappe.ui.form.on("Material Request Item", {
// //     bom_no: function(frm, cdt, cdn) {
// //         let row = locals[cdt][cdn];              
// //         // When BOM is changed, fetch custom fields from BOM Item
// //         if (row.bom_no && row.item_code) {
// //             frappe.call({
// //                 method: "generate_item.api.bom_item.get_bom_item_custom_fields",
// //                 args: {
// //                     bom_no: row.bom_no,
// //                     item_code: row.item_code
// //                 },
// //                 callback: function(r) {
// //                     if (r.message && Object.keys(r.message).length > 0) {
// //                         let bom_item = r.message;
// //                         console.log('BOM Item custom fields:', bom_item);
                        
// //                         // Update custom fields from BOM Item
// //                         frappe.model.set_value(row.doctype, row.name, {
// //                             "custom_drawing_no": bom_item.custom_drawing_no || "",
// //                             "custom_pattern_drawing_no": bom_item.custom_pattern_drawing_no || "",
// //                             "custom_purchase_specification_no": bom_item.custom_purchase_specification_no || "",
// //                             "custom_drawing_rev_no": bom_item.custom_drawing_rev_no || "",
// //                             "custom_pattern_drawing_rev_no": bom_item.custom_pattern_drawing_rev_no || "",
// //                             "custom_purchase_specification_rev_no": bom_item.custom_purchase_specification_rev_no || "",
// //                             "custom_batch_no": bom_item.custom_batch_no || ""
// //                         });
                        
// //                         frm.refresh_field('items');
// //                     }
// //                 }
// //             });
// //         }
// //     }
// // });


// const MR_FIELDS_TO_PROPAGATE = [
//     'custom_drawing_no',
//     'custom_pattern_drawing_no',
//     'custom_purchase_specification_no',
//     'custom_drawing_rev_no',
//     'custom_pattern_drawing_rev_no',
//     'custom_purchase_specification_rev_no',
//     'custom_batch_no'
// ];

// function mr_propagate_parent_fields_to_children(frm) {
//     if (!frm.doc.items || !Array.isArray(frm.doc.items)) return;
//     let changed = false;
//     frm.doc.items.forEach(child => {
//         MR_FIELDS_TO_PROPAGATE.forEach(fieldname => {
//             const parentValue = frm.doc[fieldname];
//             const childValue = child[fieldname];
//             if (parentValue && childValue !== parentValue) {
//                 frappe.model.set_value(child.doctype, child.name, fieldname, parentValue);
//                 changed = true;
//             }
//         });
//     });
//     if (changed) {
//         frm.refresh_field('items');
//         if (frm.doc.docstatus === 0) frm.dirty();
//     }
// }

// frappe.ui.form.on('Material Request', {
//     before_save(frm) {
//         mr_propagate_parent_fields_to_children(frm);
//     },
    
//     linked_batch: function(frm) {
//         const batch_value = frm.doc.linked_batch || '';
//         const rows = frm.doc.items || [];
    
//         // Step 1: Update custom_batch_no for all items
//         rows.forEach(row => {
//             frappe.model.set_value(row.doctype, row.name, 'custom_batch_no', batch_value);
//         });
    
//         // Step 2: For each item, find matching BOM and set fields
//         const promises = rows.map(row => {
//             return new Promise((resolve) => {
//                 if (!row.sales_order || !row.item_code) {
//                     resolve();
//                     return;
//                 }
    
//                 console.log('Fetching BOM data:', row.sales_order, row.item_code, batch_value);
    
//                 frappe.call({
//                     method: "generate_item.utils.material_request.get_bom_name",
//                     args: {
//                         sales_order: row.sales_order,
//                         linked_batch: batch_value,
//                         item_code: row.item_code
//                     },
//                     callback: function(r) {
//                         if (r.message && Object.keys(r.message).length > 0) {
//                             let bom_item = r.message;
//                             console.log('BOM Item data received:', bom_item);
    
//                             frappe.model.set_value(row.doctype, row.name, {
//                                 "bom_no": bom_item || "",
//                             });
//                         } else {
//                             console.log('No BOM data found for item:', row.item_code);
//                         }
//                         resolve();
//                     }
//                 });
//             });
//         });
    
//         // Wait for all calls to complete then refresh
//         Promise.all(promises).then(() => {
//             frm.refresh_field('items');
//         });
//     },
    
//     refresh(frm) {
//         // Add custom button for BOM - THIS IS WHERE IT SHOULD BE
//         if (frm.doc.docstatus == 0) {
//             frm.add_custom_button(
//                 __("Bill of Materials"),
//                 () => frm.events.get_items_from_bom(frm),
//                 __("Get Items From")
//             );
//         }
        
//         // Populate linked_batch options
//         const df = frappe.meta.get_docfield('Material Request', 'linked_batch');
//         if (df && df.fieldtype === 'Select') {
//             frappe.call({
//                 method: 'generate_item.api.material_request.get_batches_linked_to_partly_delivered_sales_orders',
//                 args: { item_code: null },
//                 callback: (r) => {
//                     if (!r.exc) {
//                         const batches = r.message || [];
//                         const options = [''].concat(batches);
//                         frm.set_df_property('linked_batch', 'options', options);
//                     }
//                 }
//             });
//         }
//     },
    
//     custom_drawing_no: mr_propagate_parent_fields_to_children,
//     custom_pattern_drawing_no: mr_propagate_parent_fields_to_children,
//     custom_purchase_specification_no: mr_propagate_parent_fields_to_children,
//     custom_drawing_rev_no: mr_propagate_parent_fields_to_children,
//     custom_pattern_drawing_rev_no: mr_propagate_parent_fields_to_children,
//     custom_purchase_specification_rev_no: mr_propagate_parent_fields_to_children,
//     custom_batch_no: mr_propagate_parent_fields_to_children,
    
//     // MOVED get_items_from_bom HERE - as parent form event
//     get_items_from_bom: function (frm) {
//         var d = new frappe.ui.Dialog({
//             title: __("Get Items from BOM"),
//             fields: [
//                 {
//                     fieldname: "sales_order",
//                     fieldtype: "Link",
//                     label: __("Sales Order"),
//                     options: "Sales Order",
//                     reqd: 0,
//                     get_query: function () {
//                         return { 
//                             filters: {  
//                                 docstatus: 1,
//                                 status: ["not in", ["Closed", "On Hold"]],
//                                 per_delivered: ["<", 99.99],
//                                 company: frm.doc.company
//                             } 
//                         };
//                     },
//                     onchange: function() {
//                         var sales_order = d.get_value("sales_order");
//                         if (sales_order) {
//                             d.set_value("batch_reference", "");
//                             d.set_value("bom", "");
//                         }
//                         d.fields_dict.batch_reference.refresh();
//                         d.fields_dict.bom.refresh();
//                     }
//                 },
//                 {
//                     fieldname: "batch_reference",
//                     fieldtype: "Link",
//                     label: __("Batch Reference"),
//                     options: "Batch",
//                     reqd: 0,
//                     get_query: function () {
//                         var sales_order = d.get_value("sales_order");
//                         if (sales_order) {
//                             return {
//                                 filters: {
//                                     reference_doctype: "Sales Order",
//                                     reference_name: sales_order
//                                 }
//                             };
//                         }
//                         return {
//                             filters: {
//                                 reference_doctype: "Sales Order"
//                             }
//                         };
//                     },
//                     onchange: function() {
//                         var batch_reference = d.get_value("batch_reference");
//                         if (batch_reference) {
//                             d.set_value("bom", "");
//                         }
//                         d.fields_dict.bom.refresh();
//                     }
//                 },
//                 {
//                     fieldname: "bom",
//                     fieldtype: "Link",
//                     label: __("BOM"),
//                     options: "BOM",
//                     reqd: 1,
//                     get_query: function () {
//                         var sales_order = d.get_value("sales_order");
//                         var batch_reference = d.get_value("batch_reference");
                        
//                         var filters = { 
//                             docstatus: 1, 
//                             is_active: 1 
//                         };
                        
//                         if (sales_order) {
//                             filters.sales_order = sales_order;
//                         }
                        
//                         if (batch_reference) {
//                             filters.custom_batch_no = batch_reference;
//                         }
                        
//                         return { filters: filters };
//                     },
//                 },
//                 {
//                     fieldname: "warehouse",
//                     fieldtype: "Link",
//                     label: __("For Warehouse"),
//                     options: "Warehouse",
//                     reqd: 1,
//                 },
//                 { 
//                     fieldname: "qty", 
//                     fieldtype: "Float", 
//                     label: __("Quantity"), 
//                     reqd: 1, 
//                     default: 1 
//                 },
//                 {
//                     fieldname: "fetch_exploded",
//                     fieldtype: "Check",
//                     label: __("Fetch exploded BOM (including sub-assemblies)"),
//                     default: 1,
//                 },
//             ],
//             primary_action_label: __("Get Items"),
//             primary_action(values) {
//                 if (!values) return;
                
//                 // Validate that if Sales Order is selected, Batch Reference should also be selected
//                 if (values.sales_order && !values.batch_reference) {
//                     frappe.msgprint(__("Please select Batch Reference when Sales Order is selected."));
//                     return;
//                 }
                
//                 values["company"] = frm.doc.company;
//                 if (!frm.doc.company) {
//                     frappe.throw(__("Company field is required"));
//                     return;
//                 }
                
//                 frappe.call({
//                     method: "erpnext.manufacturing.doctype.bom.bom.get_bom_items",
//                     args: values,
//                     callback: function (r) {
//                         if (!r.message) {
//                             frappe.throw(__("BOM does not contain any stock item"));
//                         } else {
//                             if (values.batch_reference) {
//                                 frm.set_value("linked_batch", values.batch_reference);
//                             }
//                             erpnext.utils.remove_empty_first_row(frm, "items");
//                             $.each(r.message, function (i, item) {

//                                 var d = frappe.model.add_child(cur_frm.doc, "Material Request Item", "items");
//                                 d.item_code = item.item_code;
//                                 d.item_name = item.item_name;
//                                 d.description = item.description;
//                                 d.warehouse = values.warehouse || "";
//                                 d.uom = item.stock_uom;
//                                 d.stock_uom = item.stock_uom;
//                                 d.conversion_factor = 1;
//                                 d.qty = item.qty;
//                                 d.project = item.project;
//                                 d.bom_no = item.bom_no || values.bom_no || values.bom || "";
                                
//                                 // Set Sales Order and Batch Reference if provided
//                                 if (values.sales_order) {
//                                     d.sales_order = values.sales_order;
//                                 }
//                                 if (values.batch_reference) {
//                                     d.custom_batch_no = values.batch_reference;
//                                 }
//                             });
                            
//                             d.hide();
//                             refresh_field("items");
//                         }
//                     },
//                 });
//             },
//         });

//         d.show();
//     },
    
// });

// // Child table events
// frappe.ui.form.on("Material Request Item", {
//     bom_no: function(frm, cdt, cdn) {
//         let row = locals[cdt][cdn];
        
//         if (row.bom_no && row.item_code) {
//             frappe.call({
//                 method: "generate_item.api.bom_item.get_bom_item_custom_fields",
//                 args: {
//                     bom_no: row.bom_no,
//                     item_code: row.item_code
//                 },
//                 callback: function(r) {
//                     if (r.message && Object.keys(r.message).length > 0) {
//                         let bom_item = r.message;
//                         console.log('BOM Item custom fields:', bom_item);
                        
//                         frappe.model.set_value(row.doctype, row.name, {
//                             "custom_drawing_no": bom_item.custom_drawing_no || "",
//                             "custom_pattern_drawing_no": bom_item.custom_pattern_drawing_no || "",
//                             "custom_purchase_specification_no": bom_item.custom_purchase_specification_no || "",
//                             "custom_drawing_rev_no": bom_item.custom_drawing_rev_no || "",
//                             "custom_pattern_drawing_rev_no": bom_item.custom_pattern_drawing_rev_no || "",
//                             "custom_purchase_specification_rev_no": bom_item.custom_purchase_specification_rev_no || "",
//                             "custom_batch_no": bom_item.custom_batch_no || bom_item.parent_custom_batch_no || "",
//                             "bom_no": bom_item.parent || "",
//                             "custom_batch_no": bom_item.custom_batch_no || "",
//                         });
                        
//                         frm.refresh_field('items');
//                     }
//                 }
//             });
//         }
//     }
// });

























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

// Helper function to fetch and populate BOM fields
function populate_bom_fields(frm, row) {
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
                    
                    frappe.model.set_value(row.doctype, row.name, {
                        "custom_drawing_no": bom_item.custom_drawing_no || "",
                        "custom_pattern_drawing_no": bom_item.custom_pattern_drawing_no || "",
                        "custom_purchase_specification_no": bom_item.custom_purchase_specification_no || "",
                        "custom_drawing_rev_no": bom_item.custom_drawing_rev_no || "",
                        "custom_pattern_drawing_rev_no": bom_item.custom_pattern_drawing_rev_no || "",
                        "custom_purchase_specification_rev_no": bom_item.custom_purchase_specification_rev_no || "",
                        "custom_batch_no": bom_item.custom_batch_no || bom_item.parent_custom_batch_no || "",
                    });
                    
                    frm.refresh_field('items');
                }
            }
        });
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
                        sales_order: row.sales_order,
                        linked_batch: batch_value,
                        item_code: row.item_code
                    },
                    callback: function(r) {
                        if (r.message && Object.keys(r.message).length > 0) {
                            let bom_item = r.message;
                            console.log('BOM Item data received:', bom_item);
    
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
        // Add custom button for BOM
        if (frm.doc.docstatus == 0) {
            frm.add_custom_button(
                __("Bill of Materials"),
                () => frm.events.get_items_from_bom(frm),
                __("Get Items From")
            );
        }
        
        // Populate linked_batch options
        const df = frappe.meta.get_docfield('Material Request', 'linked_batch');
        if (df && df.fieldtype === 'Select') {
            frappe.call({
                method: 'generate_item.api.material_request.get_batches_linked_to_partly_delivered_sales_orders',
                args: { item_code: null },
                callback: (r) => {
                    if (!r.exc) {
                        const batches = r.message || [];
                        const options = [''].concat(batches);
                        frm.set_df_property('linked_batch', 'options', options);
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
    custom_batch_no: mr_propagate_parent_fields_to_children,
    
    get_items_from_bom: function (frm) {
        var d = new frappe.ui.Dialog({
            title: __("Get Items from BOM"),
            fields: [
                {
                    fieldname: "sales_order",
                    fieldtype: "Link",
                    label: __("Sales Order"),
                    options: "Sales Order",
                    reqd: 0,
                    get_query: function () {
                        return { 
                            filters: {  
                                docstatus: 1,
                                status: ["not in", ["Closed", "On Hold"]],
                                per_delivered: ["<", 99.99],
                                company: frm.doc.company
                            } 
                        };
                    },
                    onchange: function() {
                        var sales_order = d.get_value("sales_order");
                        if (sales_order) {
                            d.set_value("batch_reference", "");
                            d.set_value("bom", "");
                        }
                        d.fields_dict.batch_reference.refresh();
                        d.fields_dict.bom.refresh();
                    }
                },
                {
                    fieldname: "batch_reference",
                    fieldtype: "Link",
                    label: __("Batch Reference"),
                    options: "Batch",
                    reqd: 0,
                    get_query: function () {
                        var sales_order = d.get_value("sales_order");
                        if (sales_order) {
                            return {
                                filters: {
                                    reference_doctype: "Sales Order",
                                    reference_name: sales_order
                                }
                            };
                        }
                        return {
                            filters: {
                                reference_doctype: "Sales Order"
                            }
                        };
                    },
                    onchange: function() {
                        var batch_reference = d.get_value("batch_reference");
                        if (batch_reference) {
                            d.set_value("bom", "");
                        }
                        d.fields_dict.bom.refresh();
                    }
                },
                {
                    fieldname: "bom",
                    fieldtype: "Link",
                    label: __("BOM"),
                    options: "BOM",
                    reqd: 1,
                    get_query: function () {
                        var sales_order = d.get_value("sales_order");
                        var batch_reference = d.get_value("batch_reference");
                        
                        var filters = { 
                            docstatus: 1, 
                            is_active: 1 
                        };
                        
                        if (sales_order) {
                            filters.sales_order = sales_order;
                        }
                        
                        if (batch_reference) {
                            filters.custom_batch_no = batch_reference;
                        }
                        
                        return { filters: filters };
                    },
                },
                {
                    fieldname: "warehouse",
                    fieldtype: "Link",
                    label: __("For Warehouse"),
                    options: "Warehouse",
                    reqd: 1,
                },
                { 
                    fieldname: "qty", 
                    fieldtype: "Float", 
                    label: __("Quantity"), 
                    reqd: 1, 
                    default: 1 
                },
                {
                    fieldname: "fetch_exploded",
                    fieldtype: "Check",
                    label: __("Fetch exploded BOM (including sub-assemblies)"),
                    default: 1,
                },
            ],
            primary_action_label: __("Get Items"),
            primary_action(values) {
                if (!values) return;
                
                if (values.sales_order && !values.batch_reference) {
                    frappe.msgprint(__("Please select Batch Reference when Sales Order is selected."));
                    return;
                }
                
                values["company"] = frm.doc.company;
                if (!frm.doc.company) {
                    frappe.throw(__("Company field is required"));
                    return;
                }
                
                frappe.call({
                    method: "erpnext.manufacturing.doctype.bom.bom.get_bom_items",
                    args: values,
                    callback: function (r) {
                        if (!r.message) {
                            frappe.throw(__("BOM does not contain any stock item"));
                        } else {
                            if (values.batch_reference) {
                                frm.set_value("linked_batch", values.batch_reference);
                            }
                            erpnext.utils.remove_empty_first_row(frm, "items");
                            
                            const added_rows = [];
                            
                            $.each(r.message, function (i, item) {
                                var d = frappe.model.add_child(cur_frm.doc, "Material Request Item", "items");
                                d.item_code = item.item_code;
                                d.item_name = item.item_name;
                                d.description = item.description;
                                d.warehouse = values.warehouse || "";
                                d.uom = item.stock_uom;
                                d.stock_uom = item.stock_uom;
                                d.conversion_factor = 1;
                                d.qty = item.qty;
                                d.project = item.project;
                                d.bom_no = item.bom_no || values.bom_no || values.bom || "";
                                
                                if (values.sales_order) {
                                    d.sales_order = values.sales_order;
                                }
                                if (values.batch_reference) {
                                    d.custom_batch_no = values.batch_reference;
                                }
                                
                                // Store the row for later processing
                                added_rows.push(d);
                            });
                            
                            d.hide();
                            refresh_field("items");
                            
                            // Now fetch BOM custom fields for each added row
                            setTimeout(() => {
                                added_rows.forEach(row => {
                                    if (row.bom_no && row.item_code) {
                                        populate_bom_fields(frm, row);
                                    }
                                });
                            }, 300);
                        }
                    },
                });
            },
        });

        d.show();
    },
    
});

// Child table events
frappe.ui.form.on("Material Request Item", {
    // This will trigger when bom_no field is changed manually
    bom_no: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        console.log('BOM No changed manually:', row.bom_no);
        
        // Add small delay to ensure the field is fully set
        setTimeout(() => {
            populate_bom_fields(frm, row);
        }, 100);
    }
});