frappe.ui.form.on('BOM', {
    item: async function(frm) {
        await set_available_batches_query(frm);
    },
    branch: async function(frm) {
        await set_available_batches_query(frm);
    },
    sales_order: function(frm) {
        if (!frm.doc.custom_batch_no) {
            frm.set_value("sales_order", "");
            frappe.msgprint({
                title: __("Missing Batch Number"),
                message: __("Please select a valid Batch before choosing a Sales Order."),
                indicator: "red"
            });
        }
    },

    // item: async function(frm) {
    //     if (!frm.doc.item) return;

    //     // Find batches already used for this item in other BOMs
    //     const used_batches = (await frappe.db.get_list('BOM', {
    //         fields: ['custom_batch_no'],
    //         filters: {
    //             item: frm.doc.item,
    //             custom_batch_no: ['is', 'set'],
    //             docstatus: ['!=', 2],
    //             name: ['!=', frm.doc.name]
    //         }
    //     })).map(r => r.custom_batch_no);

    //     // Apply filter on custom_batch_no
    //     frm.set_query("custom_batch_no", function() {
    //         return {
    //             filters: [
    //                 ['Batch', 'item', '=', frm.doc.item],              // same item only
    //                 ['Batch', 'name', 'not in', used_batches],         // exclude already used
    //                 ['Batch', 'branch', '=', frm.doc.branch],     // include branch filter
    //                 ['Batch', 'reference_doctype', '=', "Sales Order"]           // include branch filter
    //             ]
                
    //         };
    //     });

    //     frm.refresh_field('custom_batch_no');
    // },

    refresh: function(frm) {
        setTimeout(() => {
            $('.dropdown-menu a').each(function() {
                if ($(this).text().trim() === 'Material Request') {
                    $(this).hide();
                }
            });
        }, 100);
        
        frm.set_query("custom_batch_no", function() {
            return {
                filters: {
                    item: frm.doc.item,  
                    reference_doctype: "Sales Order",
                    branch: frm.doc.branch,
                    item: frm.doc.item ,
                }
            };
        });
        frm.set_query("sales_order", function() {
            // If no batch is selected → return an empty filter (no results)
            if (!frm.doc.custom_batch_no) {
                return {
                    filters: {
                        name: ["is", "set to", null]  // Always false condition
                    }
                };
            }

            // When batch is selected → apply real filters
            return {
                filters: { 
                    docstatus: ["in", [0, 1]],
                    branch: frm.doc.branch
                }
            };
        });

        
        
        // frm.set_query("sales_order", function() {
        //     return {
        //         filters: { 
        //             docstatus:["in",["0","1"]],
        //             branch: frm.doc.branch,
        //         }
        //     };
        // });
        frm.add_custom_button(__('Material Request'), function() {
            create_material_request_from_bom(frm);
        }, __('Create'));
        
        frm.set_query('bom_no', 'items', function(doc, cdt, cdn) {
            let row = locals[cdt][cdn];
            return {
                filters: [
                    ['item', '=', row.item_code],
                    ['is_active', '=', 1],
                    ['docstatus', 'in', [0, 1]]
                ]
            };
        });
    },
    branch: function(frm) {
        const branch_value = frm.doc.branch || '';
        
        // Branch abbreviation mapping
        const branch_abbr_map = {
            'Rabale': 'RA',
            'Nandikoor': 'NA',
            'Sanand': 'SA'
        };
        
        // Set branch abbreviation based on branch value
        if (branch_abbr_map[branch_value]) {
            frm.set_value('branch_abbr', branch_abbr_map[branch_value]);
        } else {
            frm.set_value('branch_abbr', '');
        }
        
        // Update branch in child table items
        const rows = frm.doc.items || [];
        
        if (rows.length > 0) {
            rows.forEach(row => {
                frappe.model.set_value(row.doctype, row.name, 'branch', branch_value);
            });
            frm.refresh_field('items');
        }
    },
    custom_batch_no: async function(frm) {
        if (!frm.doc.custom_batch_no) return;

        try {
            // Step 1: Check if Batch exists and matches item, branch, and sales order linkage
            const batch = await frappe.db.get_value("Batch", frm.doc.custom_batch_no, [
                "name",
                "item",
                "branch",
                "reference_doctype",
                "reference_name"
            ]);

            if (!batch || !batch.message || !batch.message.name) {
                frappe.msgprint({
                    title: __("Invalid Batch"),
                    message: __("Batch <b>{0}</b> does not exist.", [frm.doc.custom_batch_no]),
                    indicator: "red"
                });
                frm.set_value("custom_batch_no", "");
                return;
            }

            const b = batch.message;

            // Step 2: Validate that batch belongs to correct item and branch
            if (b.item !== frm.doc.item || b.branch !== frm.doc.branch) {
                frm.set_value("custom_batch_no", "");
                frm.set_value("sales_order", "");
                frappe.msgprint({
                    title: __("Batch Mismatch"),
                    message: __(
                        "Batch <b>{0}</b> does not match the Item <b>{1}</b> and Branch <b>{2}</b>.",
                        [frm.doc.custom_batch_no, frm.doc.item, frm.doc.branch]
                    ),
                    indicator: "red"
                });
                return;
            }

            // Step 3: Validate that batch is linked with a Sales Order
            if (b.reference_doctype !== "Sales Order" || !b.reference_name) {
                frm.set_value("custom_batch_no", "");
                frm.set_value("sales_order", "");
                frappe.msgprint({
                    title: __("Invalid Batch Link"),
                    message: __(
                        "Batch <b>{0}</b> must be linked with a Sales Order.",
                        [frm.doc.custom_batch_no]
                    ),
                    indicator: "red"
                });
                return;
            }

            // Step 4: Check duplicate use in another active BOM
            const existing_boms = await frappe.db.get_list("BOM", {
                fields: ["name"],
                filters: {
                    custom_batch_no: frm.doc.custom_batch_no,
                    name: ["!=", frm.doc.name],
                    docstatus: ["!=", 2]
                },
                limit: 1
            });

            if (existing_boms && existing_boms.length > 0) {
                frappe.msgprint({
                    title: __("Duplicate Batch Number"),
                    message: __(
                        "Batch No <b>{0}</b> is already used in BOM <b>{1}</b>.",
                        [frm.doc.custom_batch_no, existing_boms[0].name]
                    ),
                    indicator: "red"
                });
                frm.set_value("custom_batch_no", "");
                frm.set_value("sales_order", "");
                return;
            }


        } catch (err) {
            console.error(err);
            frappe.msgprint({
                title: __("Error"),
                message: __("An unexpected error occurred while validating the Batch."),
                indicator: "red"
            });
            frm.set_value("custom_batch_no", "");
            frm.set_value("sales_order", "");
        }
    }
    // custom_batch_no: function(frm) {
    //     if (frm.doc.custom_batch_no) {
    //         frappe.db.get_list('BOM', {
    //             fields: ['name', 'custom_batch_no'],
    //             filters: {
    //                 custom_batch_no: frm.doc.custom_batch_no,
    //                 name: ['!=', frm.doc.name] ,
    //                 docstatus: ['!=', 2],
    //             },
    //             limit: 1
    //         }).then(records => {
    //             if (records && records.length > 0) {
    //                 frappe.msgprint({
    //                     title: __('Duplicate Batch Number'),
    //                     message: __('Batch No <b>{0}</b> is already used in BOM <b>{1}</b>.', [frm.doc.custom_batch_no, records[0].name]),
    //                     indicator: 'red'
    //                 });
    //                 frm.set_value('custom_batch_no', '');
    //             }
    //         });
    //     }
    // }
})


        
function create_material_request_from_bom(frm) {
    if (!frm.doc.items || frm.doc.items.length === 0) {
        frappe.msgprint(__('No BOM items found to create a Material Request.'));
        return;
    }

    const schedule_date = frappe.datetime.get_today();


    const items = (frm.doc.items || [])
        .filter(i => i.item_code)
        .map(i => ({
            item_code: i.item_code,
            qty: i.qty || i.stock_qty || 0,
            uom: i.uom,
            schedule_date: schedule_date,
            bom_no: frm.doc.name,
            
            

        }));

    if (!items.length) {
        frappe.msgprint(__('No valid items to add in Material Request.'));
        return;
    }

    const mr_doc = {
        doctype: 'Material Request',
        material_request_type: 'Purchase',
        company: frm.doc.company || undefined,
        schedule_date: schedule_date,
        custom_ga_drawing_no: frm.doc.custom_ga_drawing_no,
        custom_ga_drawing_rev_no: frm.doc.custom_ga_drawing_rev_no,
        items: items,
    };

    frappe.call({
        method: 'frappe.client.insert',
        args: { doc: mr_doc },
        freeze: true,
        callback: function(r) {
            if (!r.exc) {
                const name = r.message && r.message.name;
                const safeName = frappe.utils.escape_html(name);
                const linkBtn = `<a class="btn btn-link p-0" href="/app/material-request/${encodeURIComponent(name)}">${safeName}</a>`;
                frappe.msgprint({
                    title: __('Material Request Created'),
                    message: __('Created {0} from this BOM', [linkBtn]),
                    indicator: 'green',
                    wide: false
                });
            } else {
                frappe.msgprint({
                    title: __('Error'),
                    message: __('Failed to create Material Request: ') + r.exc,
                    indicator: 'red'
                });
            }
        }
    });
}


async function set_available_batches_query(frm) {
    if (!frm.doc.item || !frm.doc.branch) {
        frm.set_query("custom_batch_no", () => ({}));
        return;
    }

    try {
        const r = await frappe.call({
            method: "generate_item.utils.bom.get_available_batches",
            args: {
                item: frm.doc.item,
                branch: frm.doc.branch,
                current_bom: frm.doc.name
            }
        });

        const available_batches = r.message || [];

        // Apply filter dynamically
        frm.set_query("custom_batch_no", function() {
            if (available_batches.length === 0) {
                frappe.msgprint(__('No available batches found for this Item and Branch.'));
            }
            return {
                filters: [
                    ['Batch', 'name', 'in', available_batches]
                ]
            };
        });

        console.log("Available batches:", available_batches); // debug line
        frm.refresh_field('custom_batch_no');

    } catch (err) {
        console.error("Failed to fetch available batches:", err);
        frappe.msgprint({
            title: __('Error'),
            message: __('Could not fetch available batches. Please try again.'),
            indicator: 'red'
        });
    }
}
