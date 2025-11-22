(function () {
    if (!erpnext || !erpnext.utils || erpnext.utils.__gi_so_child_update_patched) {
        return;
    }

    const original_update_child_items = erpnext.utils.update_child_items;

    const applySalesOrderPatch = function (opts) {
        const frm = opts.frm;
        const cannot_add_row = typeof opts.cannot_add_row === "undefined" ? true : opts.cannot_add_row;
        const child_docname = typeof opts.cannot_add_row === "undefined" ? "items" : opts.child_docname;
        const child_meta = frappe.get_meta(`${frm.doc.doctype} Item`);
        const has_reserved_stock = opts.has_reserved_stock ? true : false;
        const table_fieldname = opts.child_docname || child_docname;
        const custom_fields = ["po_line_no", "tag_no", "line_remark", "description", "custom_shipping_address","item_name"];
        const get_precision = (fieldname) => {
            const meta_fields = (child_meta && child_meta.fields) || [];
            const field = meta_fields.find((f) => f.fieldname === fieldname);
            return field ? field.precision : undefined;
        };

        const source_rows = frm.doc[table_fieldname] || [];
        const source_data = source_rows.map((d) => ({
            docname: d.name,
            name: d.name,
            item_name: d.item_name,
            item_code: d.item_code,
            delivery_date: d.delivery_date,
            conversion_factor: d.conversion_factor,
            qty: d.qty,
            rate: d.rate,
            uom: d.uom,
            po_line_no: d.po_line_no,
            tag_no: d.tag_no,
            line_remark: d.line_remark,
            description: d.description,
            custom_shipping_address: d.custom_shipping_address,
        }));

        const fields = [
            {
                fieldtype: "Data",
                fieldname: "docname",
                read_only: 1,
                hidden: 1,
            },
            {
                fieldtype: "Data",
                fieldname: "item_name",
                label: __("Item Name"),
                in_list_view: 1,
                read_only: 1,
            },
            {
                fieldtype: "Link",
                fieldname: "item_code",
                options: "Item",
                in_list_view: 1,
                read_only: 0,
                disabled: 0,
                label: __("Item Code"),
                get_query: function () {
                    return {
                        query: "erpnext.controllers.queries.item_query",
                        filters: { is_sales_item: 1 },
                    };
                },
                onchange: function () {
                    const me = this;

                    frm.call({
                        method: "erpnext.stock.get_item_details.get_item_details",
                        args: {
                            doc: frm.doc,
                            args: {
                                item_code: this.value,
                                set_warehouse: frm.doc.set_warehouse,
                                customer: frm.doc.customer || frm.doc.party_name,
                                quotation_to: frm.doc.quotation_to,
                                supplier: frm.doc.supplier,
                                currency: frm.doc.currency,
                                is_internal_supplier: frm.doc.is_internal_supplier,
                                is_internal_customer: frm.doc.is_internal_customer,
                                conversion_rate: frm.doc.conversion_rate,
                                price_list: frm.doc.selling_price_list || frm.doc.buying_price_list,
                                price_list_currency: frm.doc.price_list_currency,
                                plc_conversion_rate: frm.doc.plc_conversion_rate,
                                company: frm.doc.company,
                                order_type: frm.doc.order_type,
                                is_pos: cint(frm.doc.is_pos),
                                is_return: cint(frm.doc.is_return),
                                is_subcontracted: frm.doc.is_subcontracted,
                                ignore_pricing_rule: frm.doc.ignore_pricing_rule,
                                doctype: frm.doc.doctype,
                                name: frm.doc.name,
                                qty: me.doc.qty || 1,
                                uom: me.doc.uom,
                                pos_profile: cint(frm.doc.is_pos) ? frm.doc.pos_profile : "",
                                tax_category: frm.doc.tax_category,
                                child_doctype: frm.doc.doctype + " Item",
                                is_old_subcontracting_flow: frm.doc.is_old_subcontracting_flow,
                            },
                        },
                        callback: function (r) {
                            if (r.message) {
                                const { qty, price_list_rate: rate, uom, conversion_factor, bom_no } = r.message;

                                const row = dialog.fields_dict.trans_items.df.data.find(
                                    (doc) => doc.idx == me.doc.idx
                                );
                                if (row) {
                                    Object.assign(row, {
                                        conversion_factor: me.doc.conversion_factor || conversion_factor,
                                        uom: me.doc.uom || uom,
                                        qty: me.doc.qty || qty,
                                        rate: me.doc.rate || rate,
                                        bom_no: bom_no,
                                    });
                                    dialog.fields_dict.trans_items.grid.refresh();
                                }
                            }
                        },
                    });
                },
            },
            {
                fieldtype: "Link",
                fieldname: "uom",
                options: "UOM",
                read_only: 0,
                label: __("UOM"),
                reqd: 1,
                onchange: function () {
                    frappe.call({
                        method: "erpnext.stock.get_item_details.get_conversion_factor",
                        args: { item_code: this.doc.item_code, uom: this.value },
                        callback: (r) => {
                            if (!r.exc) {
                                if (this.doc.conversion_factor == r.message.conversion_factor) return;

                                const docname = this.doc.docname;
                                dialog.fields_dict.trans_items.df.data.some((doc) => {
                                    if (doc.docname == docname) {
                                        doc.conversion_factor = r.message.conversion_factor;
                                        dialog.fields_dict.trans_items.grid.refresh();
                                        return true;
                                    }
                                });
                            }
                        },
                    });
                },
            },
            {
                fieldtype: "Float",
                fieldname: "qty",
                default: 0,
                read_only: 0,
                in_list_view: 1,
                precision: 2,
                label: __("Qty"),
                precision: get_precision("qty"),
            },
            {
                fieldtype: "Currency",
                fieldname: "rate",
                options: "currency",
                default: 0,
                read_only: 0,
                in_list_view: 1,
                label: __("Rate"),
                precision: get_precision("rate"),
            },
            {
                fieldtype: "Data",
                fieldname: "po_line_no",
                label: __("PO Line No"),
                in_list_view: 1,
            },
            {
                fieldtype: "Data",
                fieldname: "tag_no",
                label: __("Tag No"),
                in_list_view: 1,
            },
            {
                fieldtype: "Small Text",
                fieldname: "line_remark",
                label: __("Line Remark"),
                in_list_view: 1,
            },
            {
                fieldtype: "Small Text",
                fieldname: "description",
                label: __("Description"),
            },
            {
                fieldtype: "Link",
                fieldname: "custom_shipping_address",
                options: "Address",
                label: __("Custom Shipping Address"),
                in_list_view: 1,
                get_query: () => {
                    return {
                        filters: [
                            ['Address', 'link_doctype', '=', 'Customer'],
                            ['Address', 'link_name', '=', frm.doc.customer]
                        ]
                    };
                },
            },
        ];

        fields.splice(2, 0, {
            fieldtype: "Date",
            fieldname: "delivery_date",
            in_list_view: 1,
            label: __("Delivery Date"),
            reqd: 1,
        });
        fields.splice(3, 0, {
            fieldtype: "Float",
            fieldname: "conversion_factor",
            label: __("Conversion Factor"),
            precision: 2,
        });

        const dialog = new frappe.ui.Dialog({
            title: __("Update Items"),
            size: "extra-large",
            fields: [
                {
                    fieldname: "trans_items",
                    fieldtype: "Table",
                    label: "Items",
                    cannot_add_rows: cannot_add_row,
                    in_place_edit: false,
                    reqd: 1,
                    data: source_data,
                    get_data: () => source_data,
                    fields: fields,
                },
            ],
            primary_action: function () {
                if (has_reserved_stock) {
                    this.hide();
                    frappe.confirm(
                        __("The reserved stock will be released when you update items. Are you certain you wish to proceed?"),
                        () => this.update_items()
                    );
                } else {
                    this.update_items();
                }
            },
            update_items: function () {
                const dialogInstance = this;
                const trans_items = dialogInstance
                    .get_values()["trans_items"]
                    .filter((item) => !!item.item_code);

                const run_standard_update = () => {
                    frappe.call({
                        method: "erpnext.controllers.accounts_controller.update_child_qty_rate",
                        freeze: true,
                        args: {
                            parent_doctype: frm.doc.doctype,
                            trans_items: trans_items,
                            parent_doctype_name: frm.doc.name,
                            child_docname: table_fieldname,
                        },
                        callback: function () {
                            frm.reload_doc();
                        },
                    });
                    dialogInstance.hide();
                    refresh_field(table_fieldname);
                };

                const custom_payload = trans_items
                    .map((row) => {
                        const docname = row.docname || row.name;
                        if (!docname) {
                            return null;
                        }
                        const filtered = { docname };
                        let hasCustom = false;
                        custom_fields.forEach((field) => {
                            if (row[field] !== undefined) {
                                filtered[field] = row[field];
                                hasCustom = true;
                            }
                        });
                        return hasCustom ? filtered : null;
                    })
                    .filter(Boolean);

                if (custom_payload.length) {
                    frappe.call({
                        method: "generate_item.utils.sales_order.update_sales_order_child_custom_fields",
                        args: {
                            parent: frm.doc.name,
                            items: custom_payload,
                            child_table: table_fieldname,
                        },
                        callback: run_standard_update,
                    });
                } else {
                    run_standard_update();
                }
            },
            primary_action_label: __("Update"),
        });

        dialog.show();
    };

    erpnext.utils.update_child_items = function (opts) {
        if (opts && opts.frm && opts.frm.doc && opts.frm.doc.doctype === "Sales Order") {
            return applySalesOrderPatch(opts);
        }
        return original_update_child_items.apply(this, arguments);
    };

    erpnext.utils.__gi_so_child_update_patched = true;
})();

frappe.ui.form.on('Sales Order', {
    refresh: function(frm) {
        frm.fields_dict["items"].grid.get_field("component_of").get_query = function(doc, cdt, cdn) {
            // Get all item_code values in the current Sales Order
            const item_codes = (doc.items || [])
                .map(row => row.item_code)
                .filter(code => code && code !== locals[cdt][cdn].item_code); // exclude self
            return {
                filters: [["name", "in", item_codes]]
            };
        };
        if (!frm.doc.__islocal) {
            frm.add_custom_button(__('BOM'), function() {
                let so_items = frm.doc.items || [];

                let d = new frappe.ui.Dialog({
                    title: 'Create BOM',
                    fields: [
                        {
                            label: 'Item',
                            fieldname: 'item',
                            fieldtype: 'Link',
                            options: 'Item',
                            reqd: 1,
                            get_query: () => {
                                return {
                                    filters: {
                                        name: ['in', so_items.map(i => i.item_code)],
                                    }
                                };
                            }
                        }
                    ],
                    primary_action_label: 'Create',
                    primary_action(values) {
                        if (!values.item) {
                            frappe.msgprint(__('Please select an Item'));
                            return;
                        }

                        // Find selected row from Sales Order child table
                        let so_item = so_items.find(r => r.item_code === values.item);

                        if (!so_item) {
                            frappe.msgprint(__('No matching Sales Order Item found.'));
                            return;
                        }

                        // Create BOM with Raw Material child row
                        frappe.call({
                            method: "frappe.client.insert",
                            args: {
                                doc: {
                                    doctype: "BOM",
                                    item: values.item,
                                    custom_batch_no: so_item.custom_batch_no || "",   // from SO child table
                                    quantity: so_item.qty || 1,
                                    sales_order: frm.doc.name,
                                    branch : frm.doc.branch,   
                                    items: [
                                        {
                                            item_code: values.item,
                                            qty: so_item.qty || 1,
                                            uom: so_item.uom || "Nos",
                                            branch: so_item.branch,
                                            sales_order: frm.doc.name,
                                        }
                                    ]
                                }     
                            },
                            callback: function(r) {
                                if (!r.exc && r.message) {
                                    const bom_doc = r.message;
                                    const bom_name = bom_doc.name;
                                    frappe.msgprint(__(' {0} created', [bom_name], 'BOM Created'));
                                    try {
                                        if (so_item && so_item.name) {
                                            frappe.model.set_value(so_item.doctype, so_item.name, 'bom_no', bom_name);
                                        }
                                    } catch (e) {}
                                    d.hide();
                                    frm.save()
                                        .then(() => { try { frm.reload_doc(); } catch (e) {} })
                                        .catch(() => { try { frm.reload_doc(); } catch (e) {} });
                                }
                            }
                        });
                    }
                });

                d.show();
            }, __('Create'));
        }

        const isDraft = frm.doc.docstatus === 0;
        const isDirty = (typeof frm.is_dirty === 'function' ? frm.is_dirty() : !!frm.doc.__unsaved);

        if (isDraft && isDirty) {
            if (!frm.page.btn_primary?.is(':visible')) {
                frm.enable_save();
                frm.page.set_primary_action(__('Save'), () => frm.save());
            }
        } else if (isDraft && !isDirty) {
            // Only clear primary actions for draft documents that are not dirty
            // This allows the standard Amend button to appear for canceled documents
            if (frm.page && frm.page.clear_primary_action) {
                frm.page.clear_primary_action();
            }
            if (frm.page && frm.page.btn_primary && frm.page.btn_primary.is(':visible')) {
                frm.page.btn_primary.hide();
            }
        }
        if (!frm.is_new()) {
            frm.add_custom_button(__('Batch'), function() {
                make_batch(frm);
            }, __('Create'));   
        }

        frm.set_query("company_address", () => {
            return {
                filters: [
                    ["Address", "link_doctype", "=", "Company"],
                    ["Address", "link_name", "=", frm.doc.company]
                ]
            };
        });
        frm.set_query('shipping_address_name', () => {
            return {
                filters: [
                    ['Address', 'link_doctype', '=', 'Customer'],
                    ['Address', 'link_name', '=', frm.doc.customer]
                ]
            };
        });

        frm.add_custom_button("Open Item Generator List", function () {
            try {
                const item_codes = (frm.doc.items || [])
                    .map(d => (d && d.item_code ? String(d.item_code).trim() : ""))
                    .filter(code => !!code);

                const unique_item_codes = Array.from(new Set(item_codes));

                if (unique_item_codes.length > 0) {
                    frappe.route_options = {
                        "created_item": ["in", unique_item_codes]
                    };
                } else {
                    frappe.route_options = {
                        "created_item": ["is", "set"]
                    };
                }
            } catch (e) {}
            frappe.set_route("List", "Item Generator", "List");
        });

        frm.fields_dict["items"].grid.get_field("custom_shipping_address").get_query = function (doc, cdt, cdn) {
            return {
                filters: [
                    ['Address', 'link_doctype', '=', 'Customer'],
                    ['Address', 'link_name', '=', frm.doc.customer]
                ]
            };
        };
        
        let last_entered_item_codes = {};
        
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.addedNodes.length) {
                    $(mutation.addedNodes).find('input[data-fieldname="item_code"]').each(function() {
                        let input = $(this);
                        let row = input.closest('.grid-row').data('name');
                        
                        input.off('input.custom').on('input.custom', function() {
                            last_entered_item_codes[row] = input.val();
                        });
                    });
                }
            });
        });
        
        observer.observe(frm.fields_dict.items.grid.wrapper[0], {
            childList: true,
            subtree: true
        });

        frm.last_entered_item_codes = last_entered_item_codes;

        handle_item_generator_return(frm);
    },
    onload: function(frm) {
        handle_item_generator_return(frm);
    },
    validate: function(frm) {
        const parent_branch = frm.doc.branch || '';
        const rows = frm.doc.items || [];
    
        rows.forEach(row => {
            if (!row.branch) {  // If branch is not set on child row
                frappe.model.set_value(row.doctype, row.name, 'branch', parent_branch);
            }
        });
    
        frm.refresh_field('items');
    },
    branch: function(frm) {
        const branch_value = frm.doc.branch || '';
        const rows = frm.doc.items || [];

        rows.forEach(row => {
            frappe.model.set_value(row.doctype, row.name, 'branch', branch_value);
        });
        frm.refresh_field('items');
    },
    after_save: function(frm) {
        if (frm.doc.amended_from) {
            update_batch_links(frm);
        }
    },
    before_save: function(frm) {
        
        let promises = [];
        
        for (let item of frm.doc.items) {
            if (item.item_code) {
                if (!item.item_name || !item.uom) {
                    promises.push(
                        frappe.db.get_value('Item', item.item_code, ['item_name', 'stock_uom'])
                        .then(r => {
                            if (r.message) {
                                let updates = {};
                                if (!item.item_name && r.message.item_name) {
                                    updates.item_name = r.message.item_name;
                                }
                                if (!item.uom && r.message.stock_uom) {
                                    updates.uom = r.message.stock_uom;
                                }
                                if (Object.keys(updates).length > 0) {
                                    return frappe.model.set_value(item.doctype, item.name, updates);
                                }
                            }
                        })
                    );
                }
            }
        }
        
        if (promises.length > 0) {
            return Promise.all(promises).then(() => {
                frm.refresh_field("items");
            });
        } else {
            frm.refresh_field("items");
        }
    },
    before_workflow_action: function(frm) {
        const action = (frm.selected_workflow_action || "").toLowerCase();
        if (action.includes("reject")) {
            return show_rejection_dialog(frm);
        }

        // Only enforce for approve-like actions
        if (!action.includes("approve")) {
            return;
        }

        // Determine if any item still needs a batch
		const needs_batches = (frm.doc.items || []).some(d => {
			if (!d || !d.item_code) return false;
			// If this is an amended document, only consider custom_batch_no for decision
			if (frm.doc.amended_from) {
				return !d.custom_batch_no;
			}
			return !d.custom_batch_no && !d.batch_no;
		});
        if (!needs_batches) {
            return; // nothing to do
        }

        if (frm.__creating_batches) {
            frappe.msgprint({
                title: __("Please Wait"),
                message: __("Batch creation is already in progress."),
                indicator: "orange"
            });
            return Promise.reject("Batch creation already in progress");
        }

        try { frappe.dom.freeze(__('Creating batches...')); } catch (e) {}
        return make_batch(frm)
            .then(() => {
                try { frappe.dom.unfreeze(); } catch (e) {}
            })
            .catch(error => {
                try { frappe.dom.unfreeze(); } catch (e) {}
                frappe.msgprint({
                    title: __("Batch Creation Failed"),
                    message: __("Error during batch creation: {0}", [error?.message || error]),
                    indicator: "red"
                });
                return Promise.reject(error);
            });
    },
    custom_rejection_reason_2: function(frm) {
        update_all_reasons(frm);
    },
    custom_rejection_reason_3: function(frm) {
        update_all_reasons(frm);
    },
    customer: function(frm) {
        frm.set_query('shipping_address_name', function() {
            return {
                filters: [
                    ['Address', 'link_doctype', '=', 'Customer'],
                    ['Address', 'link_name', '=', frm.doc.customer],
                ]
            };
        });
    },
});

frappe.ui.form.on('Sales Order Item', {
    component_of: function(frm, cdt, cdn) {
        frm.refresh_field("items"); // Ensures UI & backend sync
    },
    is_free_item: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.is_free_item) {
            frappe.model.set_value(cdt, cdn, 'rate', 0);
        }
    },   
    item_code: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        let entered_item_code = frm.last_entered_item_codes ? frm.last_entered_item_codes[cdn] : null;
        if (entered_item_code) {
            frappe.db.get_value('Item', entered_item_code, 'item_group')
                .then(r => {
                    if (r.message && r.message.item_group === "Services") {
                        frappe.model.set_value(cdt, cdn, 'qty', 1);
                            row.is_service_item = true;
                    } else {
                        row.is_service_item = false;
                    }
                    
                    // Refresh the field
                    frm.refresh_field('items');
                });
            }

        

        if (!row.item_code && entered_item_code && entered_item_code.trim() !== '') {
            frappe.db.exists('Item', entered_item_code).then(exists => {
                if (!exists) {
                    frappe.confirm(
                        `Item "${entered_item_code}" does not exist. Create it using Item Generator?`,
                        function() {
                            open_item_generator_doc(frm, cdn);
                        },
                        function() {
                            delete frm.last_entered_item_codes[cdn];
                        }
                    );
                }
            });
        }
    },
     qty: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        
        // Check if it's a service item and qty is not provided
        if (row.is_service_item && (!row.qty || row.qty <= 0)) {
            frappe.msgprint(__('Service items require quantity greater than 0.'));
            frappe.model.set_value(cdt, cdn, 'qty', 1);
            frm.refresh_field('items');
        }
    },
    
    custom_item_generator: async function(frm, cdt, cdn) {
        try {
            let row = locals[cdt][cdn];
            
            if (!row) {
                frappe.show_alert({
                    message: __('Row not found'),
                    indicator: 'red'
                }, 5);
                return;
            }
    
            if (!row.item_code) {
                open_item_generator_doc(frm, cdn);
                return;
            }
    
            const exists = await frappe.db.exists('Item', row.item_code);
            
            if (!exists) {
                open_item_generator_doc(frm, cdn);
            } else {
                frappe.show_alert({
                    message: __('Item "{0}" already exists.', [row.item_code]),
                    indicator: 'green'
                }, 5);
            }
            
        } catch (error) {
            console.error('Error in custom_item_generator:', error);
            frappe.show_alert({
                message: __('Error: {0}', [error.message]),
                indicator: 'red'
            }, 5);
        }
    },
});

function open_item_generator_doc(frm, cdn) {
    try {
        const row = frm.doc.items.find(item => item.name === cdn);
        const context = {
            so_name: frm.doc.name,
            cdn: cdn,
            row_index: frm.doc.items.findIndex(item => item.name === cdn),
            temp_id: row ? row.temp_id || `temp_${Date.now()}_${Math.random().toString(36).substr(2, 9)}` : null
        };
        
        if (row && !row.temp_id) {
            frappe.model.set_value(row.doctype, row.name, 'temp_id', context.temp_id);
        }
        
        sessionStorage.setItem('ig_return_context', JSON.stringify(context));
        console.log("Setting ig_return_context in sessionStorage:", context);
    } catch (e) {
        console.error("Error setting ig_return_context:", e);
        frappe.msgprint({
            title: __("Error"),
            message: __("Failed to set context for Item Generator: " + e.message),
            indicator: "red"
        });
    }

    let new_doc = frappe.model.get_new_doc('Item Generator');
    new_doc.is_create_with_sales_order = 1;
    frappe.set_route('Form', 'Item Generator', new_doc.name);
}

function show_rejection_dialog(frm) {
    return new Promise((resolve, reject) => {
        let settled = false;

        try { frappe.dom.unfreeze(); } catch (e) {}

        let d = new frappe.ui.Dialog({
            title: "Rejection Reason",
            fields: [
                {
                    label: "Reason",
                    fieldname: "reason",
                    fieldtype: "Small Text",
                    reqd: 1
                }
            ],
            primary_action_label: "Submit",
            primary_action(values) {
                const reason = (values && values.reason ? String(values.reason) : "").trim();
                if (!reason) {
                    frappe.msgprint({
                        title: __("Validation"),
                        message: __("Please enter a rejection reason."),
                        indicator: "orange"
                    });
                    return;
                }

                let targetField = null;
                if (!frm.doc.custom_rejection_reason) {
                    targetField = "custom_rejection_reason";
                } else if (!frm.doc.custom_rejection_reason_2) {
                    targetField = "custom_rejection_reason_2";
                } else if (!frm.doc.custom_rejection_reason_3) {
                    targetField = "custom_rejection_reason_3";
                } else {
                    frappe.msgprint({
                        title: __("Maximum Rejections Reached"),
                        message: __("You have already given 3 rejection reasons. Please contact to Manager."),
                        indicator: "red"
                    });
                    return;
                }

                const persistAndProceed = async () => {
                    try {
                        await frm.set_value(targetField, reason);
                        try { update_all_reasons(frm); } catch (e) {}
                        await frm.save();
                    } catch (e) {
                        frappe.msgprint({
                            title: __("Error"),
                            message: e.message || e,
                            indicator: "red"
                        });
                        return;
                    }

                    d.hide();
                    if (!settled) { settled = true; resolve(); }
                };

                persistAndProceed();
            },
            secondary_action_label: "Cancel",
            secondary_action() {
                d.hide();
                try { frappe.dom.unfreeze(); } catch (e) {}
                if (!settled) { settled = true; reject(); }
            }
        });

        d.$wrapper.on('hidden.bs.modal', function() {
            if (!settled) {
                try { frappe.dom.unfreeze(); } catch (e) {}
                settled = true;
                reject();
            }
        });

        d.show();
    });
}

function update_all_reasons(frm) {
    let reasons = [];

    if (frm.doc.custom_rejection_reason) {
        reasons.push("Rejection Reason 1 = " + frm.doc.custom_rejection_reason);
    }
    if (frm.doc.custom_rejection_reason_2) {
        reasons.push("Rejection Reason 2 = " + frm.doc.custom_rejection_reason_2);
    }
    if (frm.doc.custom_rejection_reason_3) {
        reasons.push("Rejection Reason 3 = " + frm.doc.custom_rejection_reason_3);
    }

    frm.set_value("custom_rejection_reason_all", reasons.join("\n"));
}

function make_batch(frm) {
    return new Promise((resolve, reject) => {
        if (!frm.doc.items || frm.doc.items.length === 0) {
            frappe.msgprint({
                title: __("Validation"),
                message: __("Please add items to create batches."),
                indicator: "red"
            });
            frm.__creating_batches = false;
            reject("No items to process");
            return;
        }

		// If this is an amended Sales Order, and all rows already have custom_batch_no,
		// skip creating new batches.
		if (frm.doc.amended_from) {
			const rows_needing_batch = (frm.doc.items || []).filter(d => d && d.item_code && !d.custom_batch_no);
			if (rows_needing_batch.length === 0) {
				frappe.msgprint({
					title: __("Info"),
					message: __("All items already have a Custom Batch on this amended order. No new batches were created."),
					indicator: "blue"
				});
				frm.__creating_batches = false;
				resolve();
				return;
			}
		}

        if (frm.__creating_batches) {
            reject("Batch creation already in progress");
            return;
        }
        frm.__creating_batches = true;

        let created_batches = [];
        let errors = [];
        let processed = 0;
        const total = frm.doc.items.length;

        frm.doc.items.forEach(function(item, index) {
            if (item.custom_batch_no) {
                processed++;
                if (processed === total) {
                    finalize_batch_process(frm, created_batches, errors).then(resolve).catch(reject);
                }
                return;
            }
            frappe.db.get_value('Item', item.item_code, 'has_batch_no')
            .then(r => {
                if (r.message.has_batch_no) {
                    create_batch_for_item(frm, item, index)
                    .then((batch_data) => {
                        created_batches.push(batch_data);
                        processed++;
                        if (processed === total) {
                            finalize_batch_process(frm, created_batches, errors).then(resolve).catch(reject);
                        }
                    })
                    .catch(error => {
                        errors.push({item: item.item_code, error: error.message || error});
                        processed++;
                        if (processed === total) {
                            finalize_batch_process(frm, created_batches, errors).then(resolve).catch(reject);
                        }
                    });
                } else {
                    errors.push({item: item.item_code, error: 'Item not batch-enabled'});
                    processed++;
                    if (processed === total) {
                        finalize_batch_process(frm, created_batches, errors).then(resolve).catch(reject);
                    }
                }
            })
            .catch(error => {
                errors.push({item: item.item_code, error: 'Item not found'});
                processed++;
                if (processed === total) {
                    finalize_batch_process(frm, created_batches, errors).then(resolve).catch(reject);
                }
            });
        });
    });
}

function create_batch_for_item(frm, item, index) {
    return new Promise((resolve, reject) => {
        const batch_id = generate_batch_id_sequential(frm, item, index);
        const manufacturing_date = frm.doc.transaction_date || frappe.datetime.get_today();

        let batch_doc = {
            'doctype': 'Batch',
            'item': item.item_code,
            'batch_id': batch_id,
            'branch': item.branch,
            // 'batch_qty': item.qty,
            'stock_uom': item.uom,
            'manufacturing_date': manufacturing_date,
            'expiry_date': null,
            'reference_doctype': 'Sales Order',
            'reference_name': frm.doc.name,
            'supplier': frm.doc.supplier || null,
            'customer': frm.doc.customer || null
        };

        frappe.call({
            method: 'frappe.client.insert',
            args: {
                doc: batch_doc
            },
            callback: function(r) {
                if (!r.exc) {
                    try {
                        frappe.model.set_value(item.doctype, item.name, 'custom_batch_no', batch_id);
                        frappe.model.set_value(item.doctype, item.name, 'batch_no', batch_id);
                    } catch (e) {
                        console.error('Error setting batch values:', e);
                    }

                    // try {
                    //     if (item.bom_no) {
                    //         console.log('Updating BOM:', item.bom_no, 'with batch:', batch_id);
                    //         // update_bom_batch_no(frm, item, batch_id);
                    //     }
                    // } catch (e) {
                    //     console.log('BOM update error:', e);
                    // }
                    
                    resolve({
                        batch_id: batch_id,
                        document_name: r.message.name,
                        item_code: item.item_code,
                        row_name: item.name,
                        success: true,
                        created: true
                    });
                } else {
                    reject(r.exc);
                }
            }
        });
    });
}

function update_bom_batch_no(frm, item, batch_id) {
    if (!item.bom_no) {
        return;
    }
    // Only set if BOM.custom_batch_no is empty
    frappe.db.get_value('BOM', item.bom_no, ['custom_batch_no', 'is_active']).then(r => {
        const data = r && r.message ? r.message : null;
        if (data && data.is_active) {
            // Only update if active and custom_batch_no is not already set
            if (!data.custom_batch_no) {
                frappe.db.set_value('BOM', item.bom_no, 'custom_batch_no', batch_id);
            }
        }
    });
    
}

function generate_batch_id_sequential(frm, item, index) {
    if (frm.doc.amended_from) {
        so_name = frm.doc.amended_from;
    } else {
        so_name = frm.doc.name;
    }
    so_name = so_name.replace(/-\d+$/, "");
    const item_number = (index + 1).toString().padStart(3, '0');
    return `${so_name}-${item_number}`;
}

function show_results_with_doc_names(created_batches, errors) {
    let message = '';
    
    const newly_created = created_batches.filter(b => b.created);
    const linked_existing = created_batches.filter(b => !b.created);

    if (newly_created.length > 0) {
        message += __('<b>Successfully created {0} batches:</b>', [newly_created.length]);
        newly_created.forEach(batch => {
            const url = `#/app/batch/${batch.batch_id}`;
            const linkBtn = `<button class="btn btn-link p-0" onclick="window.open('${url}', '_blank')">${batch.batch_id}</button>`;
            message += `<br>• ${linkBtn} - For item: ${batch.item_code} - Document: ${batch.document_name}`;
        });
    }

    if (linked_existing.length > 0) {
        if (message) message += '<br><br>';
        message += __('<b>Linked to existing batches ({0}):</b>', [linked_existing.length]);
        linked_existing.forEach(batch => {
            const url = `#/app/batch/${batch.batch_id}`;
            const linkBtn = `<button class="btn btn-link p-0" onclick="window.open('${url}', '_blank')">${batch.batch_id}</button>`;
            message += `<br>• ${linkBtn} - For item: ${batch.item_code}`;
        });
    }
    
    if (errors.length > 0) {
        if (created_batches.length > 0) {
            message += '<br><br>';
        }
        message += __('<b>Errors ({0}):</b>', [errors.length]);
        errors.forEach(error => {
            message += `<br>• ${error.item}: ${error.error}`;
        });
    }
    
    if (created_batches.length === 0 && errors.length === 0) {
        message = __('No batches were created. Please check if items are batch-enabled.');
    }
    
    // frappe.msgprint({
    //     title: __('Batch Creation Results'),
    //     message: message,
    //     indicator: errors.length > 0 ? 'orange' : 'green',
    //     wide: true
    // });
}

function finalize_batch_process(frm, created_batches, errors) {
    return new Promise((resolve, reject) => {
        // Show results immediately
        try {
            show_results_with_doc_names(created_batches, errors);
        } catch (e) {
            console.error('Error showing results:', e);
        }

        const persist = async (retry=false) => {
            try {
                if (created_batches.length > 0) {
                    // Ensure form is refreshed before saving
                    frm.refresh();
                    await frm.save();
                }
                resolve();
            } catch (e) {
                const msg = String((e && e.message) ? e.message : e || '');
                if (!retry && msg.includes('Document has been modified')) {
                    try {
                        await frm.reload_doc();
                        (created_batches || []).forEach(b => {
                            try {
                                const row = (frm.doc.items || []).find(it => it.name === b.row_name);
                                if (row) {
                                    frappe.model.set_value(row.doctype, row.name, 'batch_no', b.batch_id);
                                    frappe.model.set_value(row.doctype, row.name, 'custom_batch_no', b.batch_id);
                                }
                            } catch (se) {
                                console.error('Error setting batch values on retry:', se);
                            }
                        });
                        frm.refresh();
                        await persist(true);
                    } catch (re) {
                        reject(re);
                    }
                } else {
                    reject(e);
                }
            } finally {
                frm.__creating_batches = false;
                try { frappe.dom.unfreeze(); } catch (e) {}
            }
        };

        persist(false);
    });
}

function handle_item_generator_return(frm) {
    try {
        const raw = sessionStorage.getItem('ig_return_result');
        console.log("🔍 Checking for return result:", raw ? "Found" : "Not found");
        if (!raw) {
            return;
        }

        const result = JSON.parse(raw);
        console.log("📦 Processing return from Item Generator:", result);

        if (!result.so_name || !result.cdn || !result.item_code) {
            console.log("⚠️ Incomplete return result");
            sessionStorage.removeItem('ig_return_result');
            return;
        }

        if (frm.doc.name !== result.so_name) {
            console.log("⚠️ Return result is for different Sales Order");
            return;
        }

        let target_row = null;
        
        if (result.temp_id) {
            target_row = frm.doc.items.find(item => item.temp_id === result.temp_id);
            console.log("🔍 Looking for row by temp_id:", result.temp_id, target_row ? "Found" : "Not found");
        }
        
        if (!target_row && result.cdn) {
            target_row = frm.doc.items.find(item => item.name === result.cdn);
            console.log("🔍 Looking for row by cdn:", result.cdn, target_row ? "Found" : "Not found");
        }
        
        if (!target_row && result.row_index !== undefined) {
            target_row = frm.doc.items[result.row_index];
            console.log("🔍 Looking for row by index:", result.row_index, target_row ? "Found" : "Not found");
        }
        
        if (!target_row) {
            console.log("⚠️ Target row not found with any method. Available rows:", frm.doc.items.map(item => ({name: item.name, temp_id: item.temp_id})));
            sessionStorage.removeItem('ig_return_result');
            return;
        }

        frappe.model.set_value(target_row.doctype, target_row.name, 'item_code', result.item_code);
        
        frappe.db.get_value('Item', result.item_code, ['item_name', 'stock_uom', 'item_group', 'brand'])
        .then(r => {
            if (r.message) {
                if (r.message.item_name) {
                    frappe.model.set_value(target_row.doctype, target_row.name, 'item_name', r.message.item_name);
                }
                if (r.message.stock_uom) {
                    frappe.model.set_value(target_row.doctype, target_row.name, 'uom', r.message.stock_uom);
                }
                if (r.message.item_group) {
                    frappe.model.set_value(target_row.doctype, target_row.name, 'item_group', r.message.item_group);
                }
                if (r.message.brand) {
                    frappe.model.set_value(target_row.doctype, target_row.name, 'brand', r.message.brand);
                }
            }
            
            frm.refresh_field('items');
            
            sessionStorage.removeItem('ig_return_result');
            
            if (frm.events.cal_total) {
                frm.events.cal_total(frm);
            }
            
            frappe.show_alert({
                message: __("Item {0} has been added to the Sales Order.", [result.item_code]),
                indicator: "green"
            }, 3);
        })
        .catch(err => {
            console.error("Error fetching item details:", err);
            frappe.show_alert({
                message: __("Item {0} added but some details could not be loaded.", [result.item_code]),
                indicator: "orange"
            }, 3);
            sessionStorage.removeItem('ig_return_result');
        });

    } catch (e) {
        console.error("Error in handle_item_generator_return:", e);
        sessionStorage.removeItem('ig_return_result');
    }
}


function update_batch_links(frm) {
    const items = frm.doc.items || [];
    const promises = [];

    items.forEach(item => {
        if (item.custom_batch_no) {
            promises.push(
                new Promise((resolve, reject) => {
                    frappe.db.get_value('Batch', item.custom_batch_no, ['reference_name'])
                        .then(r => {
                            if (r.message) {
                                const batch_ref_name = r.message.reference_name;
                               
                                if (batch_ref_name === frm.doc.name ) {
                                    // match, skip
                                    resolve();
                                } else {
                                    // update reference_name
                                    frappe.db.set_value('Batch', item.custom_batch_no, {
                                        'reference_name': frm.doc.name,
        
                                    })
                                        .then(() => {
                                            resolve();
                                        })
                                        .catch(reject);
                                }
                            } else {
                                // batch does not exist, skip or handle error
                                console.warn(`Batch ${item.custom_batch_no} does not exist.`);
                                resolve();
                            }
                        })
                        .catch(reject);
                })
            );
        }
    });

    return Promise.all(promises);
}