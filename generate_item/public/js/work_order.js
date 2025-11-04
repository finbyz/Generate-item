frappe.ui.form.on('Work Order', {
    refresh: function(frm) {
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