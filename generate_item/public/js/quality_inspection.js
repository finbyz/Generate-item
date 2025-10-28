frappe.ui.form.on("Quality Inspection", {
    reference_name: function(frm) {
        if (frm.doc.reference_name && frm.doc.reference_type) {
            frappe.call({
                method: "generate_item.utils.quality_inspection.get_reference_name",
                args: {
                    reference_name: frm.doc.reference_name,
                    reference_type: frm.doc.reference_type
                },
                callback: function(r) {
                    if (r.message) {
                        frm.set_value("branch", r.message);
                    }
                },
               
            });
        }
        else {
            frm.set_value("branch", "");
        }
    },
});