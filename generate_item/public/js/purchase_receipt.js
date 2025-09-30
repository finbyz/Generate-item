frappe.ui.form.on('Purchase Receipt Item', {  
    custom_add_heat: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];        
        
        if (row.custom_heat_no && row.custom_heat_no.trim() !== '') {
            add_heat_number_to_ref(frm, cdt, cdn, row.custom_heat_no.trim());
        } else {
            frappe.msgprint(__('Please enter a heat number before adding.'));
            frm.focus('custom_heat_no');
        }
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
    onload: function(frm) {
        if (frm.is_new()  && frm.doc.docstatus === 0) {
            if (frm.doc.items) {
                frm.doc.items.forEach(item => {
                    if (!item.po_qty && !item.po_line_no && item.purchase_order) {
                        frappe.call({
                            method:"generate_item.utils.purchase_receipt.get_po_items",
                            args: {
                                purchase_order: item.purchase_order
                            },
                            callback: function(r) {
                                if (r.message) {
                                    let po_doc = r.message;
    
                                    for (let po_item of po_doc.items) {
                                        if (po_item.item_code === item.item_code) {
                                            frappe.model.set_value(item.doctype, item.name, 'po_qty', po_item.qty);
                                            frappe.model.set_value(item.doctype, item.name, 'po_line_no', po_item.idx);
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
    refresh: function(frm) {
        
        if (frm.doc.docstatus !== 0 || frm.doc.is_return) {
            return;
        }
        
        try {
            frm.remove_custom_button(__('Purchase Order'), __('Get Items From'));
        } catch (e) {}

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
                child_columns: ['idx', 'item_code','item_name','qty', 'received_qty']
            });
        }, __('Get Items From'));
    }
});