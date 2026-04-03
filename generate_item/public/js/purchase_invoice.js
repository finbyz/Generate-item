frappe.ui.form.on('Purchase Invoice Item', {
    item_code: function (frm, cdt, cdn) {
		let row = locals[cdt][cdn];

		// Item Tax Template
		 if (row.item_code) {
            frappe.db.get_doc("Item", row.item_code)
                .then(item => {

                    if (item.taxes && item.taxes.length > 0) {

                        // Get first Item Tax Template
                        let tax_template = item.taxes[0].item_tax_template;

                        // Set in Purchase Invoice Item
                        frappe.model.set_value(cdt, cdn, "item_tax_template", tax_template);
                    }
                });
        }
	}
	
});