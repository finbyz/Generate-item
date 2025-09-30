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

frappe.ui.form.on('Material Request', {
    before_save(frm) {
        mr_propagate_parent_fields_to_children(frm);
    },
    refresh(frm) {
        // Populate linked_batch options with batches tied to Partly Delivered SOs
        const df = frappe.meta.get_docfield('Material Request', 'linked_batch');
        if (df && df.fieldtype === 'Select') {
            frappe.call({
                method: 'generate_item.api.material_request.get_batches_linked_to_partly_delivered_sales_orders',
                args: { item_code: null },
                callback: (r) => {
                    if (!r.exc) {
                        const batches = r.message || [];
                        // Ensure empty option first
                        const options = [''].concat(batches);
                        frm.set_df_property('linked_batch', 'options', options);
                        if (batches.length && !frm.doc.linked_batch) {
                            // leave empty; user can choose
                        }
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
    custom_batch_no: mr_propagate_parent_fields_to_children
});
