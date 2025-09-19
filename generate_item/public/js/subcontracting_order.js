frappe.ui.form.on('Subcontracting Order', {
    onload: function(frm) {
        if (frm.doc.custom_batch_no) {
            set_batch_no_in_items(frm, frm.doc.custom_batch_no);
        }
    },

    custom_batch_no: function(frm) {
        // Whenever batch is manually set/changed, update in items
        if (frm.doc.custom_batch_no) {
            set_batch_no_in_items(frm, frm.doc.custom_batch_no);
        }
    }
});

// Helper function to set batch no in items table
function set_batch_no_in_items(frm, batch_no) {
    if (frm.doc.items && frm.doc.items.length > 0) {
        frm.doc.items.forEach(item => {
            frappe.model.set_value(item.doctype, item.name, 'custom_batch_no', batch_no);
        });
        frm.refresh_field('items');
    }
}

frappe.ui.form.on('Subcontracting Order Item', {
    item_code: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        // If batch already exists in parent, push it into the row
        if (frm.doc.custom_batch_no && row.item_code) {
            frappe.model.set_value(row.doctype, row.name, 'custom_batch_no', frm.doc.custom_batch_no);
        }
    }
});
