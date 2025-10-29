// frappe.ui.form.on("Quality Inspection", {
//     reference_name: function(frm) {
//         if (frm.doc.reference_name && frm.doc.reference_type) {
//             frappe.call({
//                 method: "generate_item.utils.quality_inspection.get_reference_name",
//                 args: {
//                     reference_name: frm.doc.reference_name,
//                     reference_type: frm.doc.reference_type
//                 },
//                 callback: function(r) {
//                     if (r.message) {
//                         frm.set_value("branch", r.message);
//                     }
//                 },
               
//             });
//         }
//         else {
//             frm.set_value("branch", "");
//         }
//     },

// });

frappe.ui.form.on("Quality Inspection", {
    // Existing logic to set 'branch' from the Quality Inspection's reference document
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

    // ➡️ MODIFIED: No custom logic for item_code means it shows the complete list
    item_code: function(frm) {
        // Clear batch if item code changes
        frm.set_value('batch_no_ref', null);
        
        // 1. Filter Batch No based on the newly selected Item Code
        // This filter remains to ensure the batch selection is item-specific.
        frm.fields_dict.batch_no_ref.get_query = function() {
            return {
                filters: {
                    // Filter Batches where the 'item' field is the current Quality Inspection's item_code
                    'item': frm.doc.item_code
                }
            };
        };
    },
    
    // 2. Set Branch based on the selected Batch's reference document
    batch_no_ref: function(frm) {
        if (frm.doc.batch_no_ref) {
            frappe.db.get_value('Batch', frm.doc.batch_no_ref, ['reference_doctype', 'reference_name'])
                .then(r => {
                    const batch_doc = r.message;
                    if (batch_doc && batch_doc.reference_doctype && batch_doc.reference_name) {
                        // Using frappe.client.get_value to fetch the branch from the Batch's reference document
                        frappe.call({
                            method: "frappe.client.get_value", 
                            args: {
                                doctype: batch_doc.reference_doctype,
                                filters: { 'name': batch_doc.reference_name },
                                fieldname: 'branch' // Assuming the reference doctype has a 'branch' field
                            },
                            callback: function(res) {
                                if (res.message && res.message.branch) {
                                    frm.set_value("branch", res.message.branch);
                                }
                            }
                        });
                    }
                });

			// Also fetch custom fields from BOM Item based on item and batch
			if (frm.doc.item_code) {
				frappe.call({
					method: "generate_item.utils.quality_inspection.get_bom_item_custom_fields",
					args: {
						item_code: frm.doc.item_code,
						batch_no_ref: frm.doc.batch_no_ref,
						fields: ["custom_drawing_no","custom_pattern_drawing_no","custom_purchase_specification_no","custom_drawing_rev_no","custom_pattern_drawing_rev_no","custom_purchase_specification_rev_no"]
					},
					callback: function(r) {
						if (r.message) {
                            
							if (r.message.custom_drawing_no) {
								frm.set_value("custom_drawing_no", r.message.custom_drawing_no);
							}
							if (r.message.custom_pattern_drawing_no) {
								frm.set_value("custom_pattern_drawing_no", r.message.custom_pattern_drawing_no);
							}
							if (r.message.custom_purchase_specification_no) {
								frm.set_value("custom_purchase_specification_no", r.message.custom_purchase_specification_no);
							}
							if (r.message.custom_drawing_rev_no) {
								frm.set_value("custom_drawing_rev_no", r.message.custom_drawing_rev_no);
							}
							if (r.message.custom_pattern_drawing_rev_no) {
								frm.set_value("custom_pattern_drawing_rev_no", r.message.custom_pattern_drawing_rev_no);
							}
							if (r.message.custom_purchase_specification_rev_no) {
								frm.set_value("custom_purchase_specification_rev_no", r.message.custom_purchase_specification_rev_no);
							}
						}
					}
				});
			}
        }
        else {
            frm.set_value("branch", "");
            frm.set_value("custom_drawing_no", "");
            frm.set_value("custom_pattern_drawing_no", "");
            frm.set_value("custom_purchase_specification_no", "");
            frm.set_value("custom_drawing_rev_no", "");
            frm.set_value("custom_pattern_drawing_rev_no", "");
            frm.set_value("custom_purchase_specification_rev_no", "");
            frm.refresh_field("batch_no_ref");
        }
    },
    
    // Initial setup on form load to apply the batch filter
    setup: function(frm) {
        if (frm.doc.item_code) {
            frm.fields_dict.batch_no_ref.get_query = function() {
                return {
                    filters: {
                        'item': frm.doc.item_code
                    }
                };
            };
        }
    }
});