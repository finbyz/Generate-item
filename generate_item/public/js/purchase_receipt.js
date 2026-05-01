frappe.ui.form.on('Purchase Receipt Item', {
    custom_add_heat: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        if (row.custom_heat_no && row.custom_heat_no.trim() !== '') {
            add_heat_number_to_ref(frm, cdt, cdn, row.custom_heat_no.trim());
        } else {
            frappe.msgprint(__('Please enter a heat number before adding.'));
            frm.focus('custom_heat_no');
        }
    },
    rejected_stock_qty: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        let stock = row.stock_qty || 0;
        let rejected = row.rejected_stock_qty || 0;

        frappe.model.set_value(cdt, cdn, "received_stock_qty", stock + rejected);
    },

    stock_qty: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        let stock = row.stock_qty || 0;
        let rejected = row.rejected_stock_qty || 0;

        frappe.model.set_value(cdt, cdn, "received_stock_qty", stock + rejected);
    }

});

function add_heat_number_to_ref(frm, cdt, cdn, custom_heat_no) {
    let row = locals[cdt][cdn];

    if (row.custom_heat_no_ref) {
        let existing_heat_numbers = row.custom_heat_no_ref.split('\n').map(num => num.trim()).filter(num => num !== '');
        if (!existing_heat_numbers.includes(custom_heat_no)) {
            row.custom_heat_no_ref += '\n' + custom_heat_no;
            frappe.show_alert({
                message: __('Heat number "{0}" added successfully', [custom_heat_no]),
                indicator: 'green'
            });
        } else {
            frappe.msgprint(__('Heat number "{0}" already exists in the reference list.', [custom_heat_no]));
            return;
        }
    } else {
        row.custom_heat_no_ref = custom_heat_no;
        frappe.show_alert({
            message: __('Heat number "{0}" added successfully', [custom_heat_no]),
            indicator: 'green'
        });
    }

    row.custom_heat_no = '';

    // Refresh both fields to show the updated values
    frm.refresh_field('custom_heat_no_ref');
    frm.refresh_field('custom_heat_no');
    frm.refresh_field('items');

    frm.dirty();
}

frappe.ui.form.on('Purchase Receipt', {
    onload: function (frm) {
        if (frm.is_new() && frm.doc.docstatus === 0) {
            if (frm.doc.items) {
                frm.doc.items.forEach(item => {
                    if (!item.po_qty && !item.po_line_no && item.purchase_order) {
                        frappe.call({
                            method: "generate_item.utils.purchase_receipt.get_po_items",
                            args: {
                                purchase_order: item.purchase_order
                            },
                            callback: function (r) {
                                if (r.message) {
                                    let po_doc = r.message;
                                    console.log(po_doc)

                                    for (let po_item of po_doc.items) {
                                        if (po_item.item_code === item.item_code && item.purchase_order_item == po_item.name) {
                                            frappe.model.set_value(item.doctype, item.name, 'po_line_no', po_item.idx);
                                            frappe.model.set_value(item.doctype, item.name, 'po_qty', po_item.qty);
                                            break;
                                        }
                                    }
                                }
                            }
                        });
                    }
                });
            }
        }
    },
    refresh: function (frm) {

        // if (frm.is_new()) {
        //     update_stock_qty_from_po(frm);
        // }

        if (frm.doc.docstatus !== 0 || frm.doc.is_return) {
            return;
        }

        try {
            frm.remove_custom_button(__('Purchase Order'), __('Get Items From'));
        } catch (e) { }

        // Add back with custom child_columns to show Description and idx
        frm.add_custom_button(__('Purchase Order'), function () {
            if (!frm.doc.supplier) {
                frappe.throw({
                    title: __('Mandatory'),
                    message: __('Please Select a Supplier')
                });
            }
            erpnext.utils.map_current_doc({
                method: 'erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_receipt',
                source_doctype: 'Purchase Order',
                target: frm,
                setters: {
                    supplier: frm.doc.supplier,
                    schedule_date: undefined,
                },
                get_query_filters: {
                    docstatus: 1,
                    status: ['not in', ['Closed', 'On Hold']],
                    per_received: ['<', 99.99],
                    company: frm.doc.company,
                },
                allow_child_item_selection: true,
                child_fieldname: 'items',
                child_columns: ['po_line_no', 'item_code', 'item_name', 'qty', 'received_qty']
            });
        }, __('Get Items From'));

        // =============================
        frm.add_custom_button('Append from PO (Line Wise)', function() {

            // Step 1: Select Purchase Order
            frappe.prompt([
                {
                    label: 'Purchase Order',
                    fieldname: 'po',
                    fieldtype: 'Link',
                    options: 'Purchase Order',
                    reqd: 1
                }
            ], function(values) {

                // Step 2: Fetch PO
                frappe.call({
                    method: 'frappe.client.get',
                    args: {
                        doctype: 'Purchase Order',
                        name: values.po
                    },
                    callback: function(r) {

                        let po = r.message;
                        if (!po) return;

                        // =========================
                        // Build Table HTML
                        // =========================
                        let html = `
                            <table class="table table-bordered" style="width:100%;">
                                <thead>
                                    <tr>
                                        <th><input type="checkbox" id="select_all"></th>
                                        <th>Line No</th>
                                        <th>Item Code</th>
                                        <th>Item Name</th>
                                        <th>Qty</th>
                                        <th>Received Qty</th>
                                        <th>Pending Qty</th>
                                    
                                    </tr>
                                </thead>
                                <tbody>
                        `;

                        po.items.forEach(item => {

                            let ordered = item.qty || 0;
                            let received = item.received_qty || 0;
                            let pending = ordered - received;

                            html += `
                                <tr>
                                    <td>
                                        <input type="checkbox" class="po-line" value="${item.name}">
                                    </td>
                                    <td>${item.po_line_no || item.idx}</td>
                                    <td>${item.item_code}</td>
                                    <td>${item.item_name || ''}</td>
                                    <td>${item.qty}</td>
                                    <td>${received}</td>
                                    <td style="color:${pending > 0 ? 'red' : 'green'};">
                                        ${pending}
                                    </td>
                                </tr>
                            `;
                        });

                        html += `</tbody></table>`;

                        // =========================
                        // Dialog
                        // =========================
                        let d = new frappe.ui.Dialog({
                            title: 'Select PO Lines',
                            size: 'large',
                            fields: [
                                {
                                    fieldtype: 'HTML',
                                    fieldname: 'po_table'
                                }
                            ],
                            primary_action_label: 'Add Items',
                            primary_action() {

                                let selected_lines = [];

                                // Get selected checkboxes
                                d.$wrapper.find('.po-line:checked').each(function() {
                                    selected_lines.push($(this).val());
                                });

                                po.items.forEach(function(item) {

                                    // Filter selected
                                    if (
                                        selected_lines.length > 0 &&
                                        !selected_lines.includes(item.name)
                                    ) {
                                        return;
                                    }

                                    // Duplicate check
                                    let exists = frm.doc.items.some(d =>
                                        d.purchase_order === po.name &&
                                        d.purchase_order_item === item.name
                                    );

                                    if (!exists) {

                                        let row = frm.add_child('items');

                                        // 🔹 Standard fields
                                        row.item_code = item.item_code;
                                        row.item_name = item.item_name;
                                        row.description = item.description;
                                        row.gst_hsn_code = item.gst_hsn_code;
                                        row.qty = item.qty;
                                        row.uom = item.uom;
                                        row.rate = item.rate;

                                        row.net_rate = item.net_rate;
                                        row.net_amount = item.net_amount;
                                        row.base_net_amount = item.base_net_amount;
                                        row.base_net_rate = item.base_net_rate;
                                        row.taxable_value = item.taxable_value;

                                        // 🔹 Links
                                        row.purchase_order = po.name;
                                        row.purchase_order_item = item.name;
                                        row.material_request = item.material_request;
                                        
                                        // GST DETAILS
                                        row.cgst_rate = item.cgst_rate;
                                        row.igst_rate = item.igst_rate;
                                        row.sgst_rate = item.sgst_rate;
                                        row.cess_rate = item.cess_rate;
                                        row.cess_non_advol_rate = item.cess_non_advol_rate;
                                        row.igst_amount = item.igst_amount;
                                        row.cgst_amount = item.cgst_amount;
                                        row.sgst_amount = item.sgst_amount;
                                        row.cess_amount = item.cess_amount;
                                        row.cess_non_advol_amount = item.cess_non_advol_amount;

                                        // 🔹 Warehouse
                                        row.warehouse = item.warehouse || frm.doc.set_warehouse;

                                        // Item Weight Details 
                                        row.weight_per_unit = item.weight_per_unit 
                                        row.weight_uom = item.weight_uom 

                                        // 🔹 Custom mappings
                                        row.custom_batch_no = item.custom_batch_no;
                                        row.branch = item.branch;

                                        // PO qty reference
                                        row.po_qty = item.qty;
                                        row.po_rate = item.rate;


                                        row.project = item.project;

                                        row.qty_in_stock_uom = item.qty_in_stock_uom;
                                        row.expense_account = item.expense_account;

                                        row.custom_drg_and_pur_spec = item.custom_drg_and_pur_spec;
                                        row.custom_drawing_no = item.custom_drawing_no;
                                        row.custom_drawing_rev_no = item.custom_drawing_rev_no;

                                        row.custom_pattern_drawing_no = item.custom_pattern_drawing_no;
                                        row.custom_pattern_drawing_rev_no = item.custom_pattern_drawing_rev_no;

                                        row.custom_purchase_specification_no = item.custom_purchase_specification_no;
                                        row.custom_purchase_specification_rev_no = item.custom_purchase_specification_rev_no;

                                        // Pending stock qty
                                        row.stock_qty = item.pending_qty_in_stock_uom;

                                        // PO Line No
                                        if (item.po_line_no) {
                                            row.po_line_no = item.po_line_no;
                                        }
                                    }

                                });

                                frm.refresh_field('items');
                                d.hide();
                            }
                        });

                        // Set HTML
                        d.fields_dict.po_table.$wrapper.html(html);

                        d.show();

                        // =========================
                        // Select All checkbox
                        // =========================
                        d.$wrapper.on('change', '#select_all', function() {
                            let checked = $(this).prop('checked');
                            d.$wrapper.find('.po-line').prop('checked', checked);
                        });

                    }
                });

            }, 'Select Purchase Order');

        });
    // =============================================
    },
});

function update_stock_qty_from_po(frm) {
    if (!frm.doc.items || !frm.doc.items.length) return;

    frm.doc.items.forEach(function (row) {
        if (row.purchase_order_item) {
            frappe.call({
                method: "generate_item.utils.purchase_receipt.get_pending_qty", // adjust path
                args: {
                    po_item_name: row.purchase_order_item
                },
                callback: function (r) {
                    if (r.message != null) {
                        frappe.model.set_value(
                            row.doctype,
                            row.name,
                            "stock_qty",
                            r.message
                        );
                    }
                }
            });
        }
    });
}