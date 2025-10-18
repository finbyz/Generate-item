frappe.ui.form.on('BOM Creator', {
    custom_batch_no: function(frm) {
        if (frm.doc.custom_batch_no) {
            get_sales_order_from_batch(frm);
        } else {
            // Clear sales order if no batch selected
            frm.set_value('sales_order', '');
            frm.refresh_field('sales_order');
        }
    },
    
    setup: function(frm) {
        frm.set_query('sales_order', function() {
            if (frm.doc.custom_batch_no) {
                return {
                    filters: [
                        ['Sales Order', 'docstatus', '=', 1],
                        ['Sales Order Item', 'custom_batch_no', '=', frm.doc.custom_batch_no]
                    ]
                };
            }
        });
    }
});

function get_sales_order_from_batch(frm) {
    if (!frm.doc.custom_batch_no) {
        frappe.msgprint(__('Please select a batch first'));
        return;
    }
    
    // Get batch details and extract sales order
    frappe.call({
        method: 'frappe.client.get_value',
        args: {
            doctype: 'Batch',
            filters: { name: frm.doc.custom_batch_no, reference_doctype: 'Sales Order' },
            fieldname: ['reference_name']
        },
        callback: function(r) {
            if (r.message) {
                if (r.message.reference_name) {
                    frm.set_value('sales_order', r.message.reference_name);
                    frm.refresh_field('sales_order');
                } 
            } 
        }
    });
}