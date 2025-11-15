frappe.ui.form.on('Work Order', {
    refresh: function(frm) {
        if (!frappe.user.has_role("System Manager")) {
            frm.set_df_property('billing_address', 'read_only', 1);
            frm.set_df_property('shipping_address', 'read_only', 1);
        } else {
            frm.set_df_property('billing_address', 'read_only', 0);
            frm.set_df_property('shipping_address', 'read_only', 0);
        }
        frm.set_query("sales_order", function() {
            return {
                filters: {
                    branch: frm.doc.branch,
                    status: ["not in", ["Closed", "On Hold"]],
                }
            };
        });
        frm.set_query("bom_no", function() {
            return {
                filters: {
                    branch: frm.doc.branch,
                }
            };
        });
        frm.set_query("bom_no", function () {
			if (frm.doc.production_item) {
				return {
					query: "erpnext.controllers.queries.bom",
					filters: { item: cstr(frm.doc.production_item) },
				};
			} else {
				frappe.msgprint(__("Please enter Production Item first"));
			}
		});
    },
    work_order: function(frm) {
        frappe.get_doc('Work Order', frm.doc.work_order).then(wo => {
            if (wo) {
                frm.set_value('ga_drawing_no', wo.custom_ga_drawing_no);
                frm.set_value('ga_drawing_rev_no', wo.custom_ga_drawing_rev_no);

            }
        })
        .catch(err => {
            console.error('Error fetching work order details:', err);
        });
    },
});

// Override get_max_transferable_qty with standard ERPNext implementation
// This overrides the incorrect implementation from foundry app
erpnext.work_order = erpnext.work_order || {};
erpnext.work_order.get_max_transferable_qty = (frm, purpose) => {
	let max = 0;
	if (purpose === "Disassemble") {
		return flt(frm.doc.produced_qty - frm.doc.disassembled_qty);
	}

	if (frm.doc.skip_transfer) {
		max = flt(frm.doc.qty) - flt(frm.doc.produced_qty);
	} else {
		if (purpose === "Manufacture") {
			max = flt(frm.doc.material_transferred_for_manufacturing) - flt(frm.doc.produced_qty);
		} else {
			max = flt(frm.doc.qty) - flt(frm.doc.material_transferred_for_manufacturing);
		}
	}
	return flt(max, precision("qty"));
};


// get_max_transferable_qty: (frm, purpose) => {
	// 	console.log(frm.doc.qty)
	// 	let max = frm.doc.qty;
	// 	if (frm.doc.skip_transfer) {
	// 		max = flt(frm.doc.pending_finish) - flt(frm.doc.material_transferred_for_manufacturing);
	// 	} else {
	// 		if (purpose === 'Manufacture') {
	// 			max = flt(frm.doc.pending_finish) - flt(frm.doc.material_transferred_for_manufacturing);
	// 		} else {
	// 			max = flt(frm.doc.pending_finish) - flt(frm.doc.material_transferred_for_manufacturing);
	// 		}
	// 	}
	// 	return flt(max, precision('qty'));
	// },

	// get_max_transferable_qty: (frm, purpose) => {
	// 	let default_qty = flt(frm.doc.qty);
	// 	let transferred = [];
	
	// 	if (frm.doc.required_items && frm.doc.required_items.length) {
	// 		transferred = frm.doc.required_items.map(i => flt(i.transferred_qty));
	// 	}
	
	// 	let has_non_zero = transferred.some(qty => qty > 0);
	// 	let max = has_non_zero ? Math.max(...transferred) : default_qty;
	// 	return flt(max, precision('qty'));
	// },