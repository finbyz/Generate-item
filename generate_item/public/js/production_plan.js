let actual_qty_set_flags = {};


function custom_transfer_materials(frm)
{
  
            // let $btn = frm.page.body.find('button[data-fieldname="transfer_materials"]');
            let $btn = frm.fields_dict['transfer_materials'].$input;
            console.log("transfer_materials btn ref",$btn)
            
            if ($btn.length) {
                console.log(" Button found via data-fieldname");

                $btn.off("click").on("click", function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    // console.log(" Custom transfer_materials triggered");

                    if (!frm.doc.for_warehouse) {
                        frm.trigger("toggle_for_warehouse");
                        frappe.throw(__("Select the Warehouse"));
                    }

                    frm.set_value("consider_minimum_order_qty", 0);

                    if (!frm.doc.ignore_existing_ordered_qty) {
                        frm.events.get_items_for_material_requests(frm);
                    } else {
                        let warehouses_promise = Promise.resolve([]);

                        if (frm.doc.branch) {
                            warehouses_promise = frappe.db.get_list('Warehouse', {
                                filters: {
                                    branch: frm.doc.branch,
                                    store_warehouse: 1,
                                    disabled: 0,
                                    is_group: 0
                                },
                                fields: ['name'],
                                limit: 1
                            });
                        }

                        warehouses_promise.then((store_warehouses) => {
                            const title = __("Transfer Materials For Warehouse {0}", [frm.doc.for_warehouse]);

                            let default_transfer_warehouses = [];
                            if (store_warehouses?.length) {
                                default_transfer_warehouses = [{ warehouse: store_warehouses[0].name }];
                            }

                            let dialog = new frappe.ui.Dialog({
                                title: title,
                                fields: [
                                    {
                                        label: __("Transfer From Warehouses"),
                                        fieldtype: "Table MultiSelect",
                                        fieldname: "warehouses",
                                        options: "Production Plan Material Request Warehouse",
                                        get_query: function () {
                                            return {
                                                filters: {
                                                    company: frm.doc.company,
                                                },
                                            };
                                        },
                                    },
                                    {
                                        label: __("For Warehouse"),
                                        fieldtype: "Link",
                                        fieldname: "target_warehouse",
                                        read_only: true,
                                        default: frm.doc.for_warehouse,
                                    },
                                ],
                            });

                            dialog.show();

                            if (default_transfer_warehouses.length) {
                                dialog.set_value("warehouses", default_transfer_warehouses);
                            }

                            dialog.set_primary_action(__("Get Items"), () => {
                                let values = dialog.get_values();
                                frm.events.get_items_for_material_requests(frm, values?.warehouses);
                                dialog.hide();
                            });
                        });
                    }
                });
            } else {
                console.warn(" Button with data-fieldname='transfer_materials' not found");
            }

       
}


function get_update_for_production_plan(frm) {
    frappe.confirm(
        __("This will sync Item to Manufacture and raw materials from the linked BOM, for every Work Order under this Production Plan. Continue?"),
        () => {
            frappe.call({
                method: "generate_item.utils.work_order.get_update_for_production_plan",
                args: {
                    docname: frm.doc.name
                },
                freeze: true,
                freeze_message: __("Updating Work Orders..."),
                callback: function (r) {
                    if (!r.exc && r.message) {

                        frappe.call({
                            method: "generate_item.utils.work_order.clear_work_order_updated",
                            args: {
                                docname: frm.doc.name
                            },
                            callback: function () {
                                frappe.show_alert({
                                    message: __("Work Orders updated"),
                                    indicator: "green",
                                });

                                frm.reload_doc();
                            }
                        });

                    }
                },
            });
        }
    );
}


function add_update_work_orders_button(frm, group) {
    if (frm.doc.docstatus !== 1 || !frm.doc.work_order_updated) {
        return;
    }

    frm.add_custom_button(
        __("Update Work Orders"),
        () => get_update_for_production_plan(frm),
        group
    );
}

function add_get_update_button(frm, group) {
    if (!frm.doc.bom_modification && !frm.doc.sales_order_modification) {
        return;
    }

    frm.add_custom_button(
        __("Get Update"),
        () => {
            frappe.confirm(
                __("This will sync planned qty from the Sales Order, regenerate sub-assembly items and material request items. Continue?"),
                () => {
                    frappe.call({
                        method: "generate_item.utils.production_plan.get_update_for_submitted_pp",
                        args: { docname: frm.doc.name },
                        freeze: true,
                        freeze_message: __("Updating Production Plan..."),
                        callback: function (r) {
                            if (!r.exc) {
                                frappe.show_alert({
                                    message: __("Production Plan updated"),
                                    indicator: "green",
                                });
                                frm.reload_doc();
                            }
                        },
                    });
                }
            );
        },
        group
    );
}

function add_create_material_request_button(frm, group) {
    // Only relevant for submitted plans that actually have raw material rows
    if (frm.doc.docstatus !== 1 || !(frm.doc.mr_items || []).length || !frm.doc.production_plan_updated) {
        return;
    }

    frappe.call({
        method: "generate_item.utils.production_plan.get_pending_mr_items",
        args: { docname: frm.doc.name },
        callback: function (r) {
            // re-check production_plan_updated in case it changed by the time this resolves
            if (!r.message || !r.message.pending_count) {
                return;
            }

            const pending_count = r.message.pending_count;
            const pending_items = r.message.pending_items;

            frm.add_custom_button(
                __("Create Material Request"),
                function () {
                    frappe.confirm(
                        __("This will create a Material Request for {0} pending item(s): {1}", [
                            pending_count,
                            pending_items.join(", "),
                        ]),
                        function () {
                            frappe.call({
                                method:
                                    "generate_item.utils.production_plan.create_material_request_for_pending_items",
                                args: { docname: frm.doc.name },
                                freeze: true,
                                freeze_message: __("Creating Material Request..."),
                                callback: function (r) {
                                    if (!r.message) return;

                                    if (r.message.created) {
                                        frappe.show_alert(
                                            { message: r.message.message, indicator: "green" },
                                            5
                                        );
                                    } else {
                                        frappe.msgprint(r.message.message);
                                    }
                                    frm.reload_doc();
                                },
                                error: function () {
                                    frappe.msgprint(
                                        __("Could not create Material Request. Please try again in a moment.")
                                    );
                                },
                            });
                        }
                    );
                },
                group
            );
        },
    });
}

// ============================================================
// Client Script - Doctype: Production Plan
// Renders a 2-column table (Item Code, Stock Qty) from the
// exploded_items of the BOM(s) linked in this Production Plan.
// Row color: YELLOW if item_code already exists in this PP's
// raw material tables (mr_items / tracking_raw_materials),
// GREEN if it does not.
// ============================================================

frappe.ui.form.on('Production Plan', {
    onload: function (frm) {
        render_bom_exploded_table(frm);
    },
    refresh: function (frm) {
        render_bom_exploded_table(frm);
    }
});

function render_bom_exploded_table(frm) {
    // >>> CHANGE THIS to the actual fieldname of your HTML field <<<
    const HTML_FIELDNAME = 'raw_materials';

    if (!frm.fields_dict[HTML_FIELDNAME]) {
        console.warn(`HTML field "${HTML_FIELDNAME}" not found on this form. Update HTML_FIELDNAME in the script.`);
        return;
    }

    const $wrapper = $(frm.fields_dict[HTML_FIELDNAME].wrapper);

    // 1. Collect item_codes already present as raw materials in this PP
    const pp_raw_material_codes = new Set();

    (frm.doc.mr_items || []).forEach(row => {
        if (row.item_code) pp_raw_material_codes.add(row.item_code);
    });

    

    // 2. Collect the BOM(s) used by the main item(s) in this PP
    const bom_numbers = new Set();
    (frm.doc.po_items || []).forEach(row => {
        if (row.bom_no) bom_numbers.add(row.bom_no);
    });

    if (bom_numbers.size === 0) {
        $wrapper.html('<p class="text-muted">No BOM found in this Production Plan yet.</p>');
        return;
    }

    $wrapper.html('<p class="text-muted">Loading BOM exploded items...</p>');

    // 3. Fetch each BOM's full document (so we get the exploded_items child table)
    const bom_promises = Array.from(bom_numbers).map(bom_no =>
        frappe.db.get_doc('BOM', bom_no)
    );

    Promise.all(bom_promises)
        .then(bom_docs => {
            // Merge exploded_items from all fetched BOMs
            let exploded_items = [];
            bom_docs.forEach(bom => {
                (bom.exploded_items || []).forEach(item => {
                    exploded_items.push({
                        item_code: item.item_code,
                        stock_qty: item.stock_qty
                    });
                });
            });
            build_table($wrapper, exploded_items, pp_raw_material_codes);
        })
        .catch(err => {
            console.error(err);
            $wrapper.html('<p class="text-danger">Failed to load BOM exploded items.</p>');
        });
}

function build_table($wrapper, exploded_items, pp_raw_material_codes) {
    if (!exploded_items.length) {
        $wrapper.html('<p class="text-muted">No exploded items found in the BOM.</p>');
        return;
    }

    const YELLOW = '#fff3cd';
    const GREEN = '#d4edda';

    let rows = '';
   exploded_items.forEach((item, index) => {
    const already_in_pp = pp_raw_material_codes.has(item.item_code);
    const bg_color = already_in_pp ? YELLOW : GREEN;

    rows += `
        <tr style="background-color: ${bg_color};">
            <td style="padding:6px 10px; border:1px solid #ddd; text-align:center; width:50px;">${index + 1}</td>
            <td style="padding:6px 10px; border:1px solid #ddd;">${frappe.utils.escape_html(item.item_code)}</td>
            <td style="padding:6px 10px; border:1px solid #ddd; text-align:center;">${item.stock_qty}</td>
        </tr>`;
});

   

    const html = `
        <table style="width:100%; border-collapse:collapse; font-size:13px; margin-top:5px;">
            <thead>
                <tr style="background-color:#f5f5f5;">
                 <th style="padding:6px 10px; border:1px solid #ddd; width:50px;">Sr No</th>
                    <th style="padding:6px 10px; border:1px solid #ddd; text-align:left;">Item Code</th>
                    <th style="padding:6px 10px; border:1px solid #ddd;">Stock Qty</th>
                </tr>
            </thead>
            <tbody>
                ${rows}
            </tbody>
        </table>`;

    $wrapper.html(html);
}
frappe.ui.form.on('Production Plan', {
    onload: function (frm) {
        if (frm.doc.docstatus === 0) {
            update_actual_qty_for_items(frm);
        }
        custom_transfer_materials(frm)
    

    },

    refresh: function (frm) {
        const UPDATE_GROUP = __("Update");
        if (frm.doc.docstatus === 1  ) {
    
        add_update_work_orders_button(frm, UPDATE_GROUP);
        add_get_update_button(frm, UPDATE_GROUP);
        add_create_material_request_button(frm, UPDATE_GROUP);
    
           
        
        }
        
        

         custom_transfer_materials(frm)


        if (frm.doc.docstatus === 0) {
            update_actual_qty_for_items(frm);
        }
        frm.set_query("for_warehouse", function (doc) {
            return {
                filters: {
                    company: doc.company,
                    is_group: 0,
                    branch: frm.doc.branch
                },
            };
        });

        // Ensure the form is fully loaded and the document name is available
        if (!frm.doc.name) return;

        // Check if Work Order exists for the current Production Plan
        const button_label = 'Work Order / Subcontract PO';

// Only show button on submitted Production Plan
if (frm.doc.docstatus !== 1) {
    try { frm.remove_custom_button(button_label, 'Create'); } catch(e) {}
    return;
}

// Count existing Work Orders vs total needed
frappe.db.get_list('Work Order', {
    filters: { 'production_plan': frm.doc.name },
    fields: ['name']
}).then(wo_results => {
    const existing_wo_count = wo_results.length;
    const po_items_count = (frm.doc.po_items || []).length;
    const sub_items_count = (frm.doc.sub_assembly_items || []).length;
    const total_needed = po_items_count + sub_items_count;

    // Remove button first to avoid duplicates
    try { frm.remove_custom_button(button_label, 'Create'); } catch(e) {}

    // Show button if any work order is still missing
    if (existing_wo_count < total_needed) {
        frm.add_custom_button(__(button_label), function () {
            frappe.call({
                method: 'run_doc_method',
                args: {
                    dt: frm.doctype,
                    dn: frm.doc.name,
                    method: 'make_work_order'
                },
                callback: function(r) {
                    frm.reload_doc();
                }
            });
        }, __('Create'));
    }
}).catch(err => {
    console.error('Error checking Work Order count:', err);

        });
    },

  

    setup: function (frm) {
        frm.set_query('custom_batch_wise_assembly', function () {
            let batch_nos = (frm.doc.po_items || [])
                .filter(row => row.custom_batch_no)
                .map(row => row.custom_batch_no);

            return {
                filters: [
                    ['Batch', 'name', 'in', batch_nos]
                ]
            };
        });
    },
    setup_queries(frm) {
        frm.set_query("sales_order", "sales_orders", () => {
            return {
                query: "erpnext.manufacturing.doctype.production_plan.production_plan.sales_order_query",
                filters: {
                    company: frm.doc.company,
                    item_code: frm.doc.item_code,
                    branch: frm.doc.branch
                },
            };
        });
    },
    naming_series: function (frm) {
        if (!frm.doc.naming_series) return;

        const series_branch_map = {
            "PPOS.fiscal.####": "Sanand",
            "PPOR.fiscal.####": "Rabale",
            "PPON.fiscal.####": "Nandikoor"
        };

        let branch = series_branch_map[frm.doc.naming_series];

        if (branch && frm.doc.branch !== branch) {
            frm.set_value("branch", branch);
        }
    },

    branch: function (frm) {
        if (!frm.doc.branch) return;

        const branch_series_map = {
            "Sanand": "PPOS.fiscal.####",
            "Rabale": "PPOR.fiscal.####",
            "Nandikoor": "PPON.fiscal.####"
        };

        const sub_assembly_warehouse_map = {
            "Sanand": "Sanand Semi Finished - SVIPL",
            "Rabale": "Rabale Semi Finished - SVIPL",
            "Nandikoor": "Nandikoor Semi Finished - SVIPL"
        };

        let naming_series = branch_series_map[frm.doc.branch];

        if (naming_series && frm.doc.naming_series !== naming_series) {
            frm.set_value("naming_series", naming_series);
        }

        // Sub Assembly Warehouse
        const sub_assembly_warehouse =
            sub_assembly_warehouse_map[frm.doc.branch];

        if (sub_assembly_warehouse) {
            frm.set_value(
                "sub_assembly_warehouse",
                sub_assembly_warehouse
            );
        } else {
            frm.set_value("sub_assembly_warehouse", "");
        }

       
        if (frm.doc.sales_orders && frm.doc.sales_orders.length > 0) {
            frm.trigger("get_sales_orders");
        }

        // Step 1: Clear the existing for_warehouse
        frm.set_value('for_warehouse', '');

        // Step 2: If branch is selected, fetch the first matching raw material warehouse
        if (frm.doc.branch) {
            frappe.db.get_list('Warehouse', {
                filters: {
                    branch: frm.doc.branch,
                    raw_material_warehouse: 1,
                    disabled: 0
                },
                fields: ['name'],
                limit: 1
            }).then(function (warehouses) {
                if (warehouses && warehouses.length > 0) {
                    frm.set_value('for_warehouse', warehouses[0].name);
                } else {
                    frappe.msgprint({
                        title: __('No Warehouse Found'),
                        message: __('No raw material warehouse found for the selected branch: <b>' + frm.doc.branch + '</b>'),
                        indicator: 'orange'
                    });
                }
            });
        }
    },

   

    // Remove recursive get_sales_orders handler; server-side override handles branch filtering
    custom_batch_wise_assembly: function (frm) {
        let selected_batch = frm.doc.custom_batch_wise_assembly;
        if (!selected_batch) {
            frm.trigger("get_sales_orders");
            frm.trigger("get_items");
            return;
        }

        let filtered_items = (frm.doc.po_items || []).filter(row => row.custom_batch_no === selected_batch);
        let filtered_ppi_names = new Set(filtered_items.map(r => r.name));

        // Filter parent table
        frm.doc.po_items = filtered_items;
        frm.refresh_field('po_items');

        // Also filter sub_assembly_items whose production_plan_item points to remaining po_items
        if (Array.isArray(frm.doc.sub_assembly_items)) {
            frm.doc.sub_assembly_items = (frm.doc.sub_assembly_items || []).filter(r => {
                return !r.production_plan_item || filtered_ppi_names.has(r.production_plan_item);
            });
            frm.refresh_field('sub_assembly_items');
        }

        // Also filter sales_orders to those referenced by remaining po_items (if linkage exists)
        let linked_sales_orders = new Set((filtered_items || [])
            .map(row => row.sales_order)
            .filter(so => !!so));

        if (frm.doc.sales_orders && frm.doc.sales_orders.length) {
            frm.doc.sales_orders = (frm.doc.sales_orders || []).filter(r => linked_sales_orders.has(r.sales_order));
            frm.refresh_field('sales_orders');
        }
    },
    custom_default_supplier: function (frm) {
        const supplier_value = frm.doc.custom_default_supplier || '';
        const rows = frm.doc.sub_assembly_items || [];

        rows.forEach(row => {
            frappe.model.set_value(row.doctype, row.name, 'supplier', supplier_value);
        });
        frm.refresh_field('sub_assembly_items');
    }
});
frappe.ui.form.on('Production Plan Sales Order', {
    sales_order: function (frm, cdt, cdn) {
        // When sales order is added, fetch and set its branch
        let row = locals[cdt][cdn];
        if (row.sales_order) {
            frappe.db.get_value('Sales Order', row.sales_order, 'branch', (r) => {
                if (r && r.branch) {
                    frappe.model.set_value(cdt, cdn, 'branch', r.branch);
                }
            });
        }
    }
});

// Handle Production Plan Item changes
frappe.ui.form.on('Production Plan Item', {
    planned_qty: function (frm, cdt, cdn) {

        // When user changes planned_qty, update pending_qty to match
        let row = locals[cdt][cdn];
        if (row.planned_qty > row.actual_qty) {
            frappe.msgprint({
                title: __('Invalid Quantity'),
                message: __('Planned Quantity cannot exceed Actual Quantity.'),
                indicator: 'red'
            });
            console.log(row.actual_qty);
            frappe.model.set_value(cdt, cdn, 'planned_qty', row.actual_qty);

        }
        if (row.planned_qty !== undefined) {
            row.pending_qty = row.planned_qty;
            frm.refresh_field('po_items');
        }
    },

    pending_qty: function (frm, cdt, cdn) {
        // When user changes pending_qty, update planned_qty to match
        let row = locals[cdt][cdn];
        if (row.pending_qty !== undefined) {
            row.planned_qty = row.pending_qty;
            frm.refresh_field('po_items');
        }
    }
});


function update_actual_qty_for_items(frm) {
    frm.doc.po_items.forEach((row) => {
        if ((!row.actual_qty || row.actual_qty === 0) && !actual_qty_set_flags[row.name]) {
            actual_qty_set_flags[row.name] = true;

            frappe.call({
                method: 'generate_item.utils.production_plan.set_actual_qty_for_child_row',
                args: {
                    cdt: 'Production Plan Item',
                    cdn: row.name
                },
                callback: function (r) {
                    if (r.message) {
                        frappe.model.set_value('Production Plan Item', row.name, 'actual_qty', r.message);
                    }
                }
            });
        }
    });
}



