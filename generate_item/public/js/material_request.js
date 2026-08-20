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
            callback: function (r) {
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

    setup(frm) {
        frm.set_query('custom_batch_no', 'items', function (doc, cdt, cdn) {
            if (!doc.branch) {
                return {};
            }

            return {
                filters: {
                    branch: doc.branch
                }
            };
        });
    },

    before_save(frm) {
        mr_propagate_parent_fields_to_children(frm);
    },
    branch(frm) {
        // frm.trigger("set_linked_batch_query");
        frm.set_query('custom_batch_no', 'items', function (doc, cdt, cdn) {
            if (!doc.branch) {
                return {};
            }

            return {
                filters: {
                    branch: doc.branch
                }
            };
        });
    },
    // linked_batch: function(frm) {
    //     const batch_value = frm.doc.linked_batch || '';
    //     const rows = frm.doc.items || [];

    //     // Step 1: Update custom_batch_no for all items
    //     rows.forEach(row => {
    //         frappe.model.set_value(row.doctype, row.name, 'custom_batch_no', batch_value);
    //     });

    //     // Step 2: For each item, find matching BOM and set fields
    //     const promises = rows.map(row => {
    //         return new Promise((resolve) => {
    //             if (!row.sales_order || !row.item_code) {
    //                 resolve();
    //                 return;
    //             }

    //             console.log('Fetching BOM data:', row.sales_order, row.item_code, batch_value);

    //             frappe.call({
    //                 method: "generate_item.utils.material_request.get_bom_name",
    //                 args: {
    //                     sales_order: row.sales_order,
    //                     linked_batch: batch_value,
    //                     item_code: row.item_code
    //                 },
    //                 callback: function(r) {
    //                     if (r.message && Object.keys(r.message).length > 0) {
    //                         let bom_item = r.message;
    //                         console.log('BOM Item data received:', bom_item);

    //                         frappe.model.set_value(row.doctype, row.name, {
    //                             "bom_no": bom_item || "",
    //                         });
    //                     } else {
    //                         console.log('No BOM data found for item:', row.item_code);
    //                     }
    //                     resolve();
    //                 }
    //             });
    //         });
    //     });

    //     // Wait for all calls to complete then refresh
    //     Promise.all(promises).then(() => {
    //         frm.refresh_field('items');
    //     });
    // },

    refresh(frm) {
        // frm.trigger("set_linked_batch_query");
        // Add custom button for BOM

        if (frm.doc.docstatus == 1 && frm.doc.advance_mr) {
			// The dialog only makes sense once the MR is submitted
			// (production_plan writes are blocked server-side otherwise).
            frm.add_custom_button(__("Link With Production"), () => open_link_dialog(frm));
			
		}
        if (frm.doc.docstatus == 0) {
            frm.add_custom_button(
                __("Bill of Materials"),
                () => frm.events.get_items_from_bom(frm),
                __("Get Items From")
            );
        }
    },
    // set_linked_batch_query(frm) {
    //     // If no branch selected, show nothing
    //     if (!frm.doc.branch) {
    //         frm.set_query("linked_batch", () => {
    //             return { filters: { name: ["in", []] } };
    //         });
    //         frm.set_value("linked_batch", "");
    //         return;
    //     }

    //     // Use set_query for Link fields
    //     frm.set_query("linked_batch", () => {
    //         return {
    //             query: "generate_item.api.material_request.get_batches_linked_to_partly_delivered_sales_orders",
    //             filters: {
    //                 branch: frm.doc.branch
    //                 // If later you want to filter by item_code also, you can add it here
    //                 // item_code: frm.doc.item_code
    //             }
    //         };
    //     });
    // },

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
                                company: frm.doc.company,
                                branch: frm.doc.branch
                            }
                        };
                    },
                    onchange: function () {
                        var sales_order = d.get_value("sales_order");
                        if (sales_order) {
                            // Clear dependent fields
                            d.set_value("batch_reference", "");
                            d.set_value("bom", "");

                            // Fetch branch from Sales Order
                            frappe.db.get_value("Sales Order", sales_order, "branch")
                                .then(r => {
                                    if (r && r.message && r.message.branch) {
                                        d.set_value("branch", r.message.branch);
                                    } else {
                                        d.set_value("branch", "");
                                    }
                                });
                        } else {
                            d.set_value("branch", "");
                        }

                        d.fields_dict.batch_reference.refresh();
                        d.fields_dict.bom.refresh();

                    }
                },
                {
                    fieldname: "branch",
                    fieldtype: "Data",
                    label: __("Branch"),
                    read_only: 1,
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
                                    reference_name: sales_order,
                                }
                            };
                        }
                        return {
                            filters: {
                                reference_doctype: "Sales Order"
                            }
                        };
                    },
                    onchange: function () {
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
                            // is_active: 1 
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
                    get_query: function () {
                        var branch = d.get_value("branch");
                        if (branch) {
                            return {
                                filters: {
                                    branch: branch
                                }
                            };
                        }
                        return {};
                    }
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
                                // frm.set_value("linked_batch", values.batch_reference);
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
        d.set_value("branch", frm.doc.branch || "");
        // d.set_value("batch_reference", frm.doc.linked_batch || "");

        d.show();
    },

});



//
//   Link    -> shows MR items that do NOT have a Production Plan yet
//   Re-Link -> shows MR items that ALREADY have a Production Plan
//
// Each row: Item Code / Qty / Batch No (read-only) + Production Plan (editable
// Link control, filtered by that row's own batch_no).

frappe.provide("generate_item.material_request");

generate_item.material_request.ProductionPlanLinker = class {
	constructor(frm) {
		this.frm = frm;
	}

	show(mode = "link") {
		this.mode = mode;
		this.fetch_and_render();
	}

	// Used by the single form button: tries "link" first (items without a
	// Production Plan). If every item already has one, it doesn't dead-end
	// on a message — it falls through to "relink" automatically, since that's
	// the only dialog that can do anything useful (change/unlink) at that point.
	show_auto() {
		const me = this;
		me.mode = "link";

		frappe.call({
			method: "generate_item.utils.material_request.get_linkable_items",
			args: { material_request: me.frm.doc.name, mode: "link" },
			freeze: true,
			freeze_message: __("Fetching Items..."),
			callback(r) {
				const link_rows = r.message || [];
				if (link_rows.length) {
					me.render_dialog(link_rows);
					return;
				}

				me.mode = "relink";
				frappe.call({
					method: "generate_item.utils.material_request.get_linkable_items",
					args: { material_request: me.frm.doc.name, mode: "relink" },
					freeze: true,
					freeze_message: __("Fetching Items..."),
					callback(r2) {
						const relink_rows = r2.message || [];
						if (relink_rows.length) {
							me.render_dialog(relink_rows);
						} else {
							frappe.msgprint(__("No items with a Batch No were found on this Material Request."));
						}
					},
				});
			},
		});
	}

	fetch_and_render() {
		const me = this;

		frappe.call({
			method: "generate_item.utils.material_request.get_linkable_items",
			args: {
				material_request: me.frm.doc.name,
				mode: me.mode,
			},
			freeze: true,
			freeze_message: __("Fetching Items..."),
			callback(r) {
				me.render_dialog(r.message || []);
			},
		});
	}

	render_dialog(rows) {
		const me = this;
		const is_link_mode = this.mode === "link";

		if (!rows.length) {
			frappe.msgprint(
				is_link_mode
					? __("All items already have a Production Plan linked.")
					: __("No items have a Production Plan linked yet.")
			);
			return;
		}

		const toggle_mode = is_link_mode ? "relink" : "link";
		const toggle_label = is_link_mode ? __("Re-Link") : __("Link");

		// Tear down any previous instance of this dialog before opening a new one.
		if (this.dialog) {
			this.dialog.hide();
		}

		this.dialog = new frappe.ui.Dialog({
			title: is_link_mode
				? __("Link Production Plan — items without a Production Plan")
				: __("Re-link Production Plan — items already linked"),
			size: "extra-large",
			fields: [{ fieldtype: "HTML", fieldname: "items_html" }],
			primary_action_label: __("Update"),
			primary_action() {
				me.handle_update();
			},
		});
        this.dialog.$wrapper.addClass("pp-linker-dialog");
        this.dialog.$wrapper.find(".modal-body").css({
            padding: "0"
        });

        this.dialog.$wrapper.find(".form-layout").css({
            padding: "0",
            margin: "0"
        });

        this.dialog.$wrapper.find(".form-section").css({
            padding: "0",
            margin: "0"
        });

        this.dialog.$wrapper.find(".section-body").css({
            padding: "0",
            margin: "0"
        });

		this.dialog.set_secondary_action_label(toggle_label);
		this.dialog.set_secondary_action(() => {
			me.dialog.hide();
			me.show(toggle_mode);
		});

		// Frappe's FieldGroup wraps every field in a section/column with its
		// own padding, even when the field has no label — that's the empty
		// gap above the table. Squash it, scoped to just this dialog so it
		// doesn't touch any other dialog on the site.
		this.dialog.$wrapper.addClass("pp-linker-dialog");
		this.dialog.$wrapper.find(".modal-body").css("padding-top", "0");
		this.dialog.$wrapper
			.find(".form-section, .section-body, .form-column")
			.css({ padding: 0, margin: 0 });

		this.row_controls = {};
		this.render_table(rows);
		this.dialog.show();
	}

	render_table(rows) {
		const me = this;
		const $wrapper = this.dialog.fields_dict.items_html.$wrapper;
		$wrapper.empty();

		const $table = $(`
			<table class="table table-bordered" style="margin:0;">
				<thead>
					<tr>
						<th style="width: 30%">${__("Item Code")}</th>
						<th style="width: 15%">${__("Quantity")}</th>
						<th style="width: 20%">${__("Batch No")}</th>
						<th style="width: 35%">${__("Production Plan")}</th>
					</tr>
				</thead>
				<tbody></tbody>
			</table>
		`);

		const $tbody = $table.find("tbody");

		rows.forEach((row) => {
			const $tr = $(`
				<tr>
					<td>${frappe.utils.escape_html(row.item_code)}</td>
					<td>${frappe.format(row.qty, { fieldtype: "Float" })}</td>
					<td>${frappe.utils.escape_html(row.batch_no)}</td>
					<td class="pp-cell"></td>
				</tr>
			`);

			const control = frappe.ui.form.make_control({
				parent: $tr.find(".pp-cell"),
				render_input: true,
				df: {
					fieldtype: "Link",
					fieldname: "production_plan",
					options: "Production Plan",
					placeholder: __("Select Production Plan"),
					get_query: () => ({
						query: "generate_item.utils.material_request.production_plan_query",
						filters: { batch_no: row.batch_no },
					}),
				},
			});

			control.set_value(row.production_plan || "");
			control.refresh();
            
            $(control.$wrapper).css({
                width: "100%",
                margin: 0,
                padding: 0
            });
            $(control.$wrapper).find(".clearfix").hide();

            $(control.$wrapper).find(".form-group").css({
                margin: 0
            });

            $(control.$wrapper).find(".control-input-wrapper").css({
                padding: 0
            });

            $(control.$wrapper).find(".control-input").css({
                padding: 0
            });

			me.row_controls[row.name] = { control, batch_no: row.batch_no };
			$tbody.append($tr);
		});

		$wrapper.append($table);
	}

	handle_update() {
		const me = this;

		const updates = Object.keys(this.row_controls).map((row_name) => ({
			name: row_name,
			production_plan: me.row_controls[row_name].control.get_value(),
		}));

		frappe.call({
			method: "generate_item.utils.material_request.bulk_update_production_plan",
			freeze: true,
			freeze_message: __("Updating Production Plan..."),
			args: {
				material_request: me.frm.doc.name,
				updates,
			},
			callback(r) {
				if (!r.exc) {
					frappe.show_alert({
						message: r.message.message,
						indicator: "green",
					});
					me.dialog.hide();
					me.frm.reload_doc();
				}
			},
		});
	}
};

// ---- Entry points: call these from custom buttons in Material Request refresh ----

function open_link_dialog(frm) {
	// show_auto() dynamically opens "link" (unlinked items) or falls back to
	// "relink" (already-linked items) if nothing is left to link.
	new generate_item.material_request.ProductionPlanLinker(frm).show_auto();
}



// Child table events
frappe.ui.form.on("Material Request Item", {
    // This will trigger when bom_no field is changed manually
    bom_no: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        console.log('BOM No changed manually:', row.bom_no);

        // Add small delay to ensure the field is fully set
        setTimeout(() => {
            populate_bom_fields(frm, row);
        }, 100);
    }
});