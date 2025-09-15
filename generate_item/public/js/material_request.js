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
    custom_drawing_no: mr_propagate_parent_fields_to_children,
    custom_pattern_drawing_no: mr_propagate_parent_fields_to_children,
    custom_purchase_specification_no: mr_propagate_parent_fields_to_children,
    custom_drawing_rev_no: mr_propagate_parent_fields_to_children,
    custom_pattern_drawing_rev_no: mr_propagate_parent_fields_to_children,
    custom_purchase_specification_rev_no: mr_propagate_parent_fields_to_children,
    custom_batch_no: mr_propagate_parent_fields_to_children
});

frappe.ui.form.on('Material Request Item', {
    // Placeholder for row-specific logic if needed later
});
