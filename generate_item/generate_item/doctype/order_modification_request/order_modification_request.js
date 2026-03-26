// Copyright (c) 2025, Finbyz and contributors
// For license information, please see license.txt



frappe.ui.form.on("Order Modification Request", {
    refresh: function (frm) {
        toggle_drg_section(frm);
        hide_child_table_delete_buttons(frm);
        make_fields_mandatory_based_on_type(frm);
        handle_ig_return(frm);
        setup_rev_item_tracking(frm);
    },

      onload: function (frm) {
        handle_ig_return(frm);
    },

   

    type: function (frm) {
        toggle_drg_section(frm);
        make_fields_mandatory_based_on_type(frm);
    },
    setup(frm) {

        frm.set_query("sales_order", function () {
            let filters = {
                docstatus: 1,
                status: ["in", ["To Deliver and Bill", "To Deliver"]],
            };
            if (frm.doc.branch) {
                filters["branch"] = frm.doc.branch;
            }
            return { filters };
        });

    },
    branch(frm) {
        // Clear sales_order when branch changes so stale value doesn't stay
        frm.set_value("sales_order", null);
        frm.refresh_field("sales_order");
    },


     get_detail: function(frm) {
        frappe.call({
            method: "generate_item.generate_item.doctype.order_modification_request.order_modification_request.fetch_commercial_details",
            freeze: true,
            freeze_message: __("Fetching Commercial Details..."),
            
            args: {
            doc: frm.doc 
        },
            callback: function(r) {
                console.log(r.message);
                console.log("res---",r)
                if (r.message) {

                    frm.clear_table("commercial_detail");
                    r.message.forEach(row => {
                    let child = frm.add_child("commercial_detail");
                    child.fieldname = row.fieldname;
                    child.label = row.label;
                    child.original_value = row.original_value;
                });
                     
                    frm.refresh_field("commercial_detail");
                }
            }
        });
    },
    get_item(frm) {
        if (!frm.doc.type) {
            frappe.msgprint("Please select Type first");
            return;
        }

        if (frm.doc.type == "Sales Order" && !frm.doc.sales_order ) {
            frappe.msgprint(`Please select Sales Order first`);
            return;
        }

        if (frm.doc.type == "BOM" && !frm.doc.bom ) {
            frappe.msgprint(`Please select BOM No first`);
            return;
        }
        if (frm.doc.type === "Sales Order") {
            frm.clear_table("sales_order_item");
        } else {
            frm.clear_table("items");
        }
        frm.clear_table("original_record");

        fetch_items_dynamic(frm);
    },
    get_link_documents(frm) {
        if (!frm.doc.type) {
            frappe.msgprint("Please select Type first");
            return;
        }

        // SALES ORDER CASE
        if (frm.doc.type === "Sales Order") {

            if (!frm.doc.sales_order_item || !frm.doc.sales_order_item.length) {
                frappe.msgprint("Please add Sales Order Items first");
                return;
            }

        }

        // BOM CASE
        else if (frm.doc.type === "BOM") {

            if (!frm.doc.items || !frm.doc.items.length) {
                frappe.msgprint("Please add BOM Items first");
                return;
            }

        }

        // Clear existing rows
        frm.clear_table("link_documents");

        frappe.call({
            method: "generate_item.generate_item.doctype.order_modification_request.order_modification_request.get_linked_documents",
            freeze: true,
            freeze_message: __("Fetching Linked Documents..."),
            args: {
                items: (frm.doc.type === "Sales Order") ? frm.doc.sales_order_item : frm.doc.items
            },
            callback: function (r) {
                if (!r.message) return;

                r.message.forEach(row => {
                    let child = frm.add_child("link_documents");
                    child.ref_doctype = row.ref_doctype;
                    child.document_no = row.document_no;
                    child.line_item = row.line_item;
                });

                frm.refresh_field("link_documents");
                // frappe.msgprint("Link Documents fetched");
            }
        });
    }

});


function hide_child_table_delete_buttons(frm) {

    $(frm.fields_dict['sales_order_item'].grid.wrapper)
        .find('.grid-delete-row')
        .hide();

    $(frm.fields_dict['sales_order_item'].grid.wrapper)
        .find('[data-action="delete_rows"]')
        .hide();

    frm.fields_dict['sales_order_item'].grid.can_delete = false;
    frm.fields_dict['sales_order_item'].grid.refresh();
}


function fetch_items_dynamic(frm) {
    let ref_name;
    if (frm.doc.type === "Sales Order") {
        ref_name = frm.doc.sales_order;
    }
    if (frm.doc.type === "BOM") {
        ref_name = frm.doc.bom;
    }
    frappe.call({
        method: "frappe.client.get",
        freeze: true,
        freeze_message: __("Fetching items..."),
        args: {
            doctype: frm.doc.type,          //  dynamic doctype
            name: ref_name     //  dynamic document
        },
        callback(r) {
            if (!r.message) return;

            // Sales Order
            if (frm.doc.type === "Sales Order") {

                (r.message.items || []).forEach(item => {
                    let row = frm.add_child("sales_order_item");
                    row.sales_order_item_name = item.name;
                    row.item = item.item_code;
                    row.qty = item.qty;
                    row.batch_no = item.custom_batch_no || null;
                    row.po_line_no = item.po_line_no;
                    row.rate = item.rate;

                    // Additional required fields
                    row.line_status = item.line_status || null;
                    row.delivery_date = item.delivery_date || null;
                    row.tag_no = item.tag_no || null;
                    row.line_remark = item.line_remark || null;
                    row.shipping_address = item.custom_shipping_address || null;
                    row.is_free_item = item.is_free_item || 0;
                    row.component_of = item.component_of || null;

                    let history_row = frm.add_child("original_record");
                    history_row.sales_order_item_name = item.name;
                    history_row.item = item.item_code;
                    history_row.qty = item.qty;
                    history_row.batch_no = item.custom_batch_no || null;
                    history_row.po_line_no = item.po_line_no;
                    history_row.rate = item.rate;

                    history_row.line_status = item.line_status || null;
                    history_row.delivery_date = item.delivery_date || null;
                    history_row.tag_no = item.tag_no || null;
                    history_row.line_remark = item.line_remark || null;
                    history_row.shipping_address = item.custom_shipping_address || null;
                    history_row.is_free_item = item.is_free_item || 0;
                    history_row.component_of = item.component_of || null;

                });
                frm.refresh_field("sales_order_item");
            }

            // BOM
            if (frm.doc.type === "BOM") {
                (r.message.items || []).forEach(item => {
                    let row = frm.add_child("items");
                    row.bom_item_name = item.name ;
                    row.item = item.item_code;
                    row.qty = item.qty;
                    row.rate = item.rate;
                    row.batch_no = item.custom_batch_no || null;
                    row.drawing_no = item.custom_drawing_no;
                    row.drawing_rev_no = item.custom_drawing_rev_no;
                    row.pattern_drawing_no = item.custom_pattern_drawing_no;
                    row.pattern_drawing_rev_no = item.custom_pattern_drawing_rev_no;
                    row.purchase_specification_no = item.custom_purchase_specification_no;
                    row.purchase_specification_rev_no = item.custom_purchase_specification_rev_no;

                    let history_row = frm.add_child("original_record");
                    history_row.item = item.item_code;
                    history_row.qty = item.qty;
                    history_row.rate = item.rate;
                    history_row.batch_no = item.custom_batch_no || null;
                    history_row.drawing_no = item.custom_drawing_no;
                    history_row.drawing_rev_no = item.custom_drawing_rev_no;
                    history_row.pattern_drawing_no = item.custom_pattern_drawing_no;
                    history_row.pattern_drawing_rev_no = item.custom_pattern_drawing_rev_no;
                    history_row.purchase_specification_no = item.custom_purchase_specification_no;
                    history_row.purchase_specification_rev_no = item.custom_purchase_specification_rev_no;
                });
                frm.refresh_field("items");
            }


            frm.refresh_field("original_record");
            // frappe.msgprint(`Items fetched from ${frm.doc.type}`);
        }
    });
}


frappe.ui.form.on('Order Modification Request Detail', {
    item: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        if (!row.item) return;

        frappe.db.get_value(
            "Item Price",
            {
                item_code: row.item,
                price_list: frm.doc.selling_price_list
            },
            "price_list_rate",
            function (r) {
                if (r && r.price_list_rate) {
                    frappe.model.set_value(cdt, cdn, "rev_rate", r.price_list_rate);
                }
            }
        );
    }
});


function toggle_drg_section(frm) {
    let hide_section = frm.doc.type === "Sales Order";

    if (frm.fields_dict.items) {
        frm.fields_dict.items.grid.update_docfield_property(
            "drg_and_pur_spec_section",
            "hidden",
            hide_section ? 1 : 0
        );
    }

    frm.refresh_field("items");
}

function make_fields_mandatory_based_on_type(frm) {

    if (frm.doc.type === "Sales Order") {

        frm.set_df_property("sales_order", "reqd", 1);
        frm.set_df_property("bom", "reqd", 0);

    } else if (frm.doc.type === "BOM") {

        frm.set_df_property("sales_order", "reqd", 0);
        frm.set_df_property("bom", "reqd", 1);

    } else {

        frm.set_df_property("sales_order", "reqd", 0);
        frm.set_df_property("bom", "reqd", 0);

    }
}


frappe.ui.form.on('Sales Order Item For OMR', {

    // ── Fires when the rev_item Link field resolves (or fails) ──
    rev_item: function (frm, cdt, cdn) {
        const row = locals[cdt][cdn];

        // frm.__omr_rev_typed[cdn] holds exactly what the user typed
        const entered = (frm.__omr_rev_typed && frm.__omr_rev_typed[cdn])
            ? frm.__omr_rev_typed[cdn].trim()
            : '';

        // rev_item cleared → typed value did not match any Item
        if (!row.rev_item && entered) {
            frappe.db.exists('Item', entered).then(exists => {
                if (!exists) {
                    frappe.confirm(
                        __('Item "{0}" does not exist. Create it using Item Generator?', [entered]),
                        function () {
                            // User said Yes
                            open_item_generator_for_omr(frm, cdn);
                        },
                        function () {
                            // User said No — clear tracking entry
                            if (frm.__omr_rev_typed) {
                                delete frm.__omr_rev_typed[cdn];
                            }
                        }
                    );
                }
            });
        }
    },

    
    item_generator: async function (frm, cdt, cdn) {
        try {
            const row = locals[cdt][cdn];

            if (!row) {
                frappe.show_alert({ message: __('Row not found'), indicator: 'red' }, 5);
                return;
            }

            // If rev_item is already set and exists, warn the user
            if (row.rev_item) {
                const exists = await frappe.db.exists('Item', row.rev_item);
                if (exists) {
                    frappe.show_alert({
                        message: __('Revised item "{0}" already exists.', [row.rev_item]),
                        indicator: 'green'
                    }, 5);
                    return;
                }
            }

            // Open Item Generator for this row
            open_item_generator_for_omr(frm, cdn);

        } catch (err) {
            console.error('[OMR] item_generator error:', err);
            frappe.show_alert({ message: __('Error: {0}', [err.message]), indicator: 'red' }, 5);
        }
    }

});

// ---------------------------------------------------------------
// Track raw keystrokes in the rev_item column so we know what
// the user typed even after the Link widget clears the field
// ---------------------------------------------------------------
function setup_rev_item_tracking(frm) {
    // Init the map once
    if (!frm.__omr_rev_typed) {
        frm.__omr_rev_typed = {};
    }

    // Attach MutationObserver only once per form lifecycle
    if (frm.__omr_rev_item_observer) return;

    const grid = frm.fields_dict['sales_order_item'] &&
                 frm.fields_dict['sales_order_item'].grid;

    if (!grid || !grid.wrapper) return;
    

    const observer = new MutationObserver(function (mutations) {
        mutations.forEach(function (mutation) {
            if (!mutation.addedNodes.length) return;

            // Find rev_item inputs that just appeared in the grid
            $(mutation.addedNodes)
                .find('input[data-fieldname="rev_item"]')
                .each(function () {
                    const input    = $(this);
                    const row_name = input.closest('.grid-row').data('name');

                    // Record every keystroke
                    input.off('input.omr_rev_track')
                         .on('input.omr_rev_track', function () {
                             frm.__omr_rev_typed[row_name] = input.val();
                         });
                });
        });
    });

    observer.observe(grid.wrapper[0], { childList: true, subtree: true });
    frm.__omr_rev_item_observer = observer;
}

// ---------------------------------------------------------------
// Store context and navigate to a new Item Generator document
// ---------------------------------------------------------------
function open_item_generator_for_omr(frm, cdn) {
    try {
        const rows = frm.doc.sales_order_item || [];
        const row  = rows.find(r => r.name === cdn);

        // Stable temp_id so we can match this row when we come back
        const temp_id = (row && row.temp_id)
            ? row.temp_id
            : `omr_tmp_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

        if (row && !row.temp_id) {
            frappe.model.set_value(row.doctype, row.name, 'temp_id', temp_id);
        }

        const context = {
            omr_name  : frm.doc.name,
            cdn       : cdn,
            row_index : rows.findIndex(r => r.name === cdn),
            temp_id   : temp_id
        };

        sessionStorage.setItem('omr_ig_context', JSON.stringify(context));
        console.log('[OMR] Stored omr_ig_context:', context);

    } catch (e) {
        console.error('[OMR] Failed to store context:', e);
        frappe.msgprint({
            title    : __('Error'),
            message  : __('Could not prepare Item Generator context: {0}', [e.message]),
            indicator: 'red'
        });
        return;
    }

 
    const new_doc = frappe.model.get_new_doc('Item Generator');
    new_doc.is_create_with_sales_order = 1;
    frappe.set_route('Form', 'Item Generator', new_doc.name);
}

// ---------------------------------------------------------------
// Called on every refresh / onload.
// Reads the result Item Generator wrote to sessionStorage and
// writes the new item code into rev_item on the correct row.
// ---------------------------------------------------------------
function handle_ig_return(frm) {
    try {
        const raw = sessionStorage.getItem('omr_ig_result');
        if (!raw) return;

        const result = JSON.parse(raw);
        console.log('[OMR] handle_ig_return:', result);

        // Basic validation
        if (!result.omr_name || !result.item_code) {
            console.warn('[OMR] Incomplete result — discarding.');
            sessionStorage.removeItem('omr_ig_result');
            return;
        }

        // Ignore results meant for a different OMR document
        if (frm.doc.name !== result.omr_name) {
            console.log('[OMR] Result is for a different OMR, skipping.');
            return;
        }

        // ── Locate the target row ────────────────────────────────
        // Try temp_id first (most reliable), then cdn, then row_index
        const rows = frm.doc.sales_order_item || [];
        let target_row = null;

        if (result.temp_id) {
            target_row = rows.find(r => r.temp_id === result.temp_id);
            console.log('[OMR] Lookup by temp_id:', result.temp_id,
                        target_row ? 'found' : 'not found');
        }
        if (!target_row && result.cdn) {
            target_row = rows.find(r => r.name === result.cdn);
            console.log('[OMR] Lookup by cdn:', result.cdn,
                        target_row ? 'found' : 'not found');
        }
        if (!target_row && result.row_index !== undefined) {
            target_row = rows[result.row_index];
            console.log('[OMR] Lookup by row_index:', result.row_index,
                        target_row ? 'found' : 'not found');
        }

        if (!target_row) {
            console.warn('[OMR] Target row not found. Available rows:',
                rows.map(r => ({ name: r.name, temp_id: r.temp_id })));
            sessionStorage.removeItem('omr_ig_result');
            return;
        }

        // ── Write to rev_item (the revised item field) ───────────
        frappe.model.set_value(target_row.doctype, target_row.name, 'rev_item', result.item_code);

        frm.refresh_field('sales_order_item');

        frappe.show_alert({
            message  : __('Revised item {0} has been set on the OMR row.', [result.item_code]),
            indicator: 'green'
        }, 4);

        sessionStorage.removeItem('omr_ig_result');

    } catch (e) {
        console.error('[OMR] handle_ig_return error:', e);
        sessionStorage.removeItem('omr_ig_result');
    }
}