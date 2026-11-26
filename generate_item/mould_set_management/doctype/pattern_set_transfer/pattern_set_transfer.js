// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt

frappe.ui.form.on('Pattern Set Transfer', {
	setup: function(frm) {
		// Filter Pattern Set to submitted, active sets
		frm.set_query('pattern_set', function() {
			let filters = {
				docstatus: 1,
				disabled: 0,
				disable: 0,
				status: 'Complete',
				completeness_status: 'Complete'
			};

			if (frm.doc.purpose === 'Transfer') {
				filters.engineering_status = 'Approved';
			} else {
				filters.engineering_status = ['in', ['Open', 'Approved', 'Rejected']];
			}

			return { filters: filters };
		});

		// Filter Target Warehouse based on purpose and transfer context
		frm.set_query('target_warehouse', function(doc) {
			let filters = {
				is_group: 0,
				disabled: 0
			};
			if (doc.company) {
				filters['company'] = doc.company;
			}
			if (doc.source_warehouse) {
				filters['name'] = ['!=', doc.source_warehouse];
			}
			if (doc.purpose === 'Return') {
				filters['custom_supplier'] = ['is', 'not set'];
			}
			return { filters: filters };
		});
	},

	refresh: function(frm) {
		frm.refresh_field('pattern_set');
		frm.refresh_field('target_warehouse');
		frm.trigger('update_counts');
		frm.trigger('show_incomplete_warning');
		frm.trigger('lock_required_rows');
	},

	purpose: function(frm) {
		frm.trigger('refresh_purpose_filters');
	},

	refresh_purpose_filters: function(frm) {
		frm.refresh_field('pattern_set');
		frm.refresh_field('target_warehouse');
		frm.trigger('show_incomplete_warning');

		let pattern_set = frm.doc.pattern_set;
		if (pattern_set) {
			frappe.db.get_value(
				'Pattern Set',
				pattern_set,
				['docstatus', 'disabled', 'disable', 'status', 'completeness_status', 'engineering_status'],
				function(r) {
					if (frm.doc.pattern_set !== pattern_set) {
						return;
					}

					let allowed_engineering_statuses = frm.doc.purpose === 'Transfer'
						? ['Approved']
						: ['Open', 'Approved', 'Rejected'];
					if (!r || r.docstatus !== 1 || r.disabled || r.disable
						|| r.status !== 'Complete' || r.completeness_status !== 'Complete'
						|| !allowed_engineering_statuses.includes(r.engineering_status)) {
						frm.set_value('pattern_set', '');
					}
				}
			);
		}

		let target_warehouse = frm.doc.target_warehouse;
		if (frm.doc.purpose === 'Return' && target_warehouse) {
			frappe.db.get_value('Warehouse', target_warehouse, 'custom_supplier', function(r) {
				if (frm.doc.target_warehouse !== target_warehouse || frm.doc.purpose !== 'Return') {
					return;
				}

				if (r && r.custom_supplier) {
					frm.set_value('target_warehouse', '');
				}
			});
		}
	},

	pattern_set: function(frm) {
		if (!frm.doc.pattern_set) {
			frm.set_value('source_warehouse', '');
			frm.set_value('source_supplier', '');
			frm.set_value('set_status', '');
			frm.set_value('completeness_status', '');
			frm.set_value('engineering_status', '');
			frm.clear_table('items');
			frm.refresh_field('items');
			frm.trigger('show_incomplete_warning');
			return;
		}

		frappe.call({
			method: 'generate_item.mould_set_management.doctype.pattern_set_transfer.pattern_set_transfer.get_pattern_set_transfer_data',
			args: { pattern_set: frm.doc.pattern_set },
			callback: function(r) {
				if (r.message) {
					frm.set_value('source_warehouse', r.message.source_warehouse);
					frm.set_value('source_supplier', r.message.source_supplier || '');
					frm.set_value('set_status', r.message.set_status);
					frm.set_value('completeness_status', r.message.completeness_status);
					frm.set_value('engineering_status', r.message.engineering_status);
					frm.doc._missing_items = r.message.missing_items;

					frm.clear_table('items');
					(r.message.items || []).forEach(function(row) {
						let child = frm.add_child('items');
						Object.assign(child, row);
					});
					frm.refresh_field('items');

					frm.trigger('update_counts');
					frm.trigger('show_incomplete_warning');
					frm.trigger('lock_required_rows');
					frm.trigger('calculate_transfer_type');
				}
			}
		});
	},

	target_warehouse: function(frm) {
		if (frm.doc.target_warehouse) {
			frappe.db.get_value('Warehouse', frm.doc.target_warehouse, 'custom_supplier', function(r) {
				frm.set_value('target_supplier', (r && r.custom_supplier) ? r.custom_supplier : '');
				frm.trigger('calculate_transfer_type');
			});
		} else {
			frm.set_value('target_supplier', '');
			frm.trigger('calculate_transfer_type');
		}
	},

	calculate_transfer_type: function(frm) {
		let src_sup = frm.doc.source_supplier;
		let tgt_sup = frm.doc.target_supplier;

		if (frm.doc.source_warehouse && frm.doc.target_warehouse) {
			if (!src_sup && tgt_sup) {
				frm.set_value('transfer_type', 'Company to Supplier');
			} else if (src_sup && tgt_sup) {
				frm.set_value('transfer_type', 'Supplier to Supplier');
			} else if (src_sup && !tgt_sup) {
				frm.set_value('transfer_type', 'Supplier to Company');
			} else {
				frm.set_value('transfer_type', 'Company to Company');
			}
		}
	},

	show_incomplete_warning: function(frm) {
		if (frm.doc.pattern_set
			&& (frm.doc.set_status !== 'Complete' || frm.doc.completeness_status !== 'Complete')) {
			let missing_str = (frm.doc._missing_items && frm.doc._missing_items.length)
				? frm.doc._missing_items.join(', ')
				: __('one or more required components');
			frm.dashboard.set_headline_alert(
				__('<strong>Blocked:</strong> Pattern Set must be Complete (missing: {0}).', [missing_str]),
				'red'
			);
		} else if (frm.doc.pattern_set && frm.doc.purpose === 'Transfer'
			&& frm.doc.engineering_status !== 'Approved') {
			frm.dashboard.set_headline_alert(
				__('<strong>Blocked:</strong> Pattern Set Engineering Status must be Approved for Purpose Transfer. Current status: <strong>{0}</strong>.', [frm.doc.engineering_status]),
				'red'
			);
		} else {
			frm.dashboard.clear_headline();
		}
	},

	update_counts: function(frm) {
		let moving = 0;
		let left_behind = 0;
		(frm.doc.items || []).forEach(function(row) {
			if (row.include) {
				moving++;
			} else {
				left_behind++;
			}
		});
		frm.set_value('total_moving', moving);
		frm.set_value('total_left_behind', left_behind);
	},

	lock_required_rows: function(frm) {
		// Ensure include checkbox cannot be unticked for non-optional rows
		frm.fields_dict.items.grid.grid_rows.forEach(function(grid_row) {
			if (!grid_row.doc.is_optional) {
				grid_row.get_field('include').df.read_only = 1;
				grid_row.refresh_field('include');
			}
		});
	},

	before_submit: function(frm) {
		if (frm._transfer_confirmed) {
			frm._transfer_confirmed = false;
			return;
		}

		// Confirmation dialog on Submit (Section 7.1 step 6)
		frappe.validated = false;
		let action_label = get_pattern_set_action_label(frm.doc.engineering_status);
		let d = new frappe.ui.Dialog({
			title: __('Confirm {0}', [action_label]),
			fields: [
				{
					fieldtype: 'HTML',
					fieldname: 'summary_html',
					options: `
						<table class="table table-bordered table-sm">
							<tr><td><strong>${__('Pattern Set')}</strong></td><td>${frm.doc.pattern_set}</td></tr>
							<tr><td><strong>${__('From Warehouse')}</strong></td><td>${frm.doc.source_warehouse}</td></tr>
							<tr><td><strong>${__('To Warehouse')}</strong></td><td>${frm.doc.target_warehouse}</td></tr>
							<tr><td><strong>${__('Serials Moving')}</strong></td><td><span class="badge bg-success text-white">${frm.doc.total_moving}</span></td></tr>
							<tr><td><strong>${__('Serials Left Behind')}</strong></td><td><span class="badge bg-warning text-dark">${frm.doc.total_left_behind}</span></td></tr>
						</table>
						<p class="text-muted" style="font-size:12px;">${__('Submitting this document will automatically transfer moving serials via Stock Entry, and detach any unticked optional components.')}</p>
					`
				}
			],
			primary_action_label: action_label,
			primary_action: function() {
				frm._transfer_confirmed = true;
				d.hide();
				frm.savesubmit();
			}
		});
		d.show();
	}
});

function get_pattern_set_action_label(engineering_status) {
	return __(engineering_status === 'Approved' ? 'Transfer Set' : 'Issue Set');
}

frappe.ui.form.on('Pattern Set Transfer Item', {
	include: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (!row.is_optional && !row.include) {
			frappe.msgprint(__('Required components cannot be unticked from the transfer.'));
			frappe.model.set_value(cdt, cdn, 'include', 1);
		}
		frm.trigger('update_counts');
	}
});

// ------------------------------------------------------------------
// Outward details: address and total qty
// ------------------------------------------------------------------
frappe.ui.form.on('Pattern Set Transfer', {
	setup: function(frm) {
		// Address: only addresses linked to the Target Supplier, when there is one
		frm.set_query('address', function(doc) {
			if (!doc.target_supplier) return {};
			return {
				query: 'frappe.contacts.doctype.address.address.address_query',
				filters: { link_doctype: 'Supplier', link_name: doc.target_supplier },
			};
		});
	},

	target_supplier: function(frm) {
		if (!frm.doc.target_supplier) {
			frm.set_value('address', '');
			return;
		}
		frappe.call({
			method: 'generate_item.mould_set_management.doctype.pattern_set_transfer.pattern_set_transfer.get_supplier_default_address',
			args: { supplier: frm.doc.target_supplier },
			callback: function(r) {
				let res = r.message || {};
				frm.set_value('address', res.address || '');
				frm.set_value('address_display', res.address_display || '');
			},
		});
	},

	address: function(frm) {
		if (!frm.doc.address) {
			frm.set_value('address_display', '');
			return;
		}
		frappe.call({
			method: 'frappe.contacts.doctype.address.address.get_address_display',
			args: { address_dict: frm.doc.address },
			callback: function(r) {
				frm.set_value('address_display', r.message || '');
			},
		});
	},
});

frappe.ui.form.on('Pattern Set Transfer Item', {
	include: function(frm) {
		let total = (frm.doc.items || []).filter(row => row.include).length;
		frm.set_value('total_qty', total);
	},
});
