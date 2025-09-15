frappe.ui.form.on('Purchase Order', {
	refresh: function(frm) {
		// Try to replace the standard Material Request mapping button so the dialog shows Description instead of Item Name
		// Depending on ERPNext version, the group label can be 'Get Items From' or 'Get Items'
		const groups = ['Get Items From', 'Get Items'];
		let removed = false;
		groups.forEach(function(group) {
			try {
				frm.remove_custom_button(__('Material Request'), __(group));
				removed = true;
			} catch (e) {
				// ignore
			}
		});

		const add_button = function(group_label) {
			frm.add_custom_button(__('Material Request'), function() {
				erpnext.utils.map_current_doc({
					method: 'erpnext.stock.doctype.material_request.material_request.make_purchase_order',
					source_doctype: 'Material Request',
					target: frm,
					setters: {
						schedule_date: undefined,
					},
					get_query_filters: {
						material_request_type: 'Purchase',
						docstatus: 1,
						status: ['!=', 'Stopped'],
						company: frm.doc.company,
					},
					allow_child_item_selection: true,
					child_fieldname: 'items',
					child_columns: ['item_code', 'description', 'qty', 'ordered_qty']
				});
			}, __(group_label));
		};

		// Prefer to add into the existing group if present, else default to 'Get Items From'
		if (removed) {
			add_button('Get Items From');
		} else {
			// Add a parallel button if we couldn't remove the core one
			add_button('Get Items From');
		}
	}
});


