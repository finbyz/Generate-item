frappe.ui.form.on('Purchase Order', {
	onload: function(frm) {
		// Handle case when purchase order is loaded with production plan already set (backend creation)
		if (frm.doc.production_plan && !frm.doc.custom_batch_no) {
			set_batch_no_from_production_plan(frm);
		}
	},
	
	production_plan: function(frm) {
		if (frm.doc.production_plan) {
			set_batch_no_from_production_plan(frm);
		}
	},
	
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
					child_columns: ['item_code', 'description','custom_batch_no', 'qty', 'ordered_qty']
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

// Helper function to set batch number from production plan
function set_batch_no_from_production_plan(frm) {
	if (!frm.doc.production_plan) return;
	
	// Get production plan details and set custom_batch_no
	frappe.db.get_value('Production Plan', frm.doc.production_plan, ['name'])
		.then(r => {
			if (r.message) {
				// Get custom_batch_no from production plan po_items
				return frappe.db.get_value('Production Plan Item', {
					'parent': frm.doc.production_plan
				}, ['custom_batch_no'], order_by='idx asc', limit=1);
			}
		})
		.then(po_item => {
			if (po_item && po_item.message && po_item.message.custom_batch_no) {
				// Set custom_batch_no in parent
				frm.set_value('custom_batch_no', po_item.message.custom_batch_no);
				
				// Set custom_batch_no in child items
				if (frm.doc.items && frm.doc.items.length > 0) {
					frm.doc.items.forEach(item => {
						frappe.model.set_value(item.doctype, item.name, 'custom_batch_no', po_item.message.custom_batch_no);
					});
					frm.refresh_field('items');
				}
			}
		})
		.catch(err => {
			console.error('Error fetching production plan details:', err);
		});
}

frappe.ui.form.on('Purchase Order Item', {
	item_code: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		
		// If we have production plan and custom_batch_no, set it for new items
		if (frm.doc.production_plan && frm.doc.custom_batch_no && row.item_code) {
			frappe.model.set_value(row.doctype, row.name, 'custom_batch_no', frm.doc.custom_batch_no);
		}
	}
});


