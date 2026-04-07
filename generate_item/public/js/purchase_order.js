

function set_supplier_warehouse(frm) {
	if (!frm.doc.branch || !frm.doc.supplier) return;

	frappe.db.get_list("Warehouse", {
		filters: [
			["Warehouse", "branch", "=", frm.doc.branch],
			["Warehouse", "is_group", "=", 0],
			["Warehouse", "name", "like", `%${frm.doc.supplier}%`]
		],
		fields: ["name"],
		order_by: "name asc",
		limit: 1
	}).then(r => {
		if (r.length) {
			frm.set_value("supplier_warehouse", r[0].name);
		}
	});
}



frappe.ui.form.on('Purchase Order', {

	onload: function (frm) {
		// Handle case when purchase order is loaded with production plan already set (backend creation)
		if (frm.doc.production_plan && !frm.doc.custom_batch_no) {
			set_batch_no_from_production_plan(frm);
		}
		set_po_defaults(frm);
	},

	production_plan: function (frm) {
		if (frm.doc.production_plan) {
			set_batch_no_from_production_plan(frm);
		}
	},
	supplier: function (frm) {
		console.log("supplier", frm.doc.supplier);
		setTimeout(() => {
			console.log("Timer Works");
			if (frm.doc.supplier_address) {
				frappe.db.get_value("Contact", {
					address: frm.doc.supplier_address
				}, "name").then(r => {
					if (r.message) {
						// frm.set_value('shipping_address_name', r.message);

						frappe.msgprint(`Linked Contact: ${r.message}`);
					}
					// If r.message is null/undefined (no contact found), the field remains cleared from step 1.
				});
			}

		}, 1000);
		set_supplier_warehouse(frm)

	},
	branch: function (frm) {
		set_supplier_warehouse(frm)
		set_po_defaults(frm)

	},
	order_type: function(frm) {
        set_po_defaults(frm);
    },

	schedule_date: function (frm) {
		if (!frm.doc.items || frm.doc.items.length === 0) return;

		// Loop through each child item
		frm.doc.items.forEach(function (row) {
			// Update the schedule_date of the child row to match parent
			frappe.model.set_value(row.doctype, row.name, 'schedule_date', frm.doc.schedule_date);
		});

		// Refresh the items table to update UI
		frm.refresh_field('items');
	},

	refresh: function (frm) {
		// Make qty field read-only for Purchase User role only if Material Request exists in items
		// if (frappe.user_roles.includes('Purchase User')) {
		// 	let hasMaterialRequest = false;

		// 	// Check if any item has material_request field populated
		// 	if (frm.doc.items && frm.doc.items.length > 0) {
		// 		hasMaterialRequest = frm.doc.items.some(item => item.material_request || item.production_plan);
		// 	}

		// 	if (hasMaterialRequest) {
		// 		frm.fields_dict.items.grid.wrapper
		// 			.find('[data-fieldname="qty"]')
		// 			.prop('readonly', true);

		// 		frm.fields_dict["items"].grid.update_docfield_property(
		// 			"qty", "read_only", 1
		// 		);
		// 	}
		// }
		// Check if items exist and iterate properly

		set_po_defaults(frm);





		frm.set_query("custom_batch_no", "items", function (doc, cdt, cdn) {
			let row = locals[cdt][cdn];

			// Safety checks
			if (!doc.is_subcontracted || !doc.branch || !row.fg_item) {
				return {
					filters: {
						name: ["=", ""]
					}
				};
			}

			return {
				query: "generate_item.utils.purchase_order.get_valid_batches",
				filters: {
					branch: doc.branch,
					item: row.fg_item,
					is_active: 1
				}
			};
		});

		if (frm.doc.docstatus == 1) {
			if (frm.doc.items && frm.doc.items.length > 0) {
				// Check only the first item that meets the condition
				const itemToUpdate = frm.doc.items.find(item => !item.po_line_no);

				if (itemToUpdate) {
					frappe.call({
						method: "generate_item.utils.purchase_order.update_po_line",
						args: {
							po: frm.doc.name
						},
						callback: function (r) {
							if (!r.exc && r.message) {
								frm.refresh();
							}
						}
					});
				}
			}
		}

		// Try to replace the standard Material Request mapping button so the dialog shows Description instead of Item Name
		// Depending on ERPNext version, the group label can be 'Get Items From' or 'Get Items'
		const groups = ['Get Items From', 'Get Items'];
		let removed = false;
		groups.forEach(function (group) {
			try {
				frm.remove_custom_button(__('Material Request'), __(group));
				removed = true;
			} catch (e) {
				// ignore
			}
		});

		const add_button = function (group_label) {
			frm.add_custom_button(__('Material Request'), function () {

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
						status: ['in', ['Partially Received', 'Pending', 'Partially Ordered']],
						company: frm.doc.company,
						branch: frm.doc.branch,
					},
					get_query: function () {
						return {
							query: 'generate_item.utils.purchase_order.get_material_requests_with_pending_qty',
							filters: {
								material_request_type: 'Purchase',
								docstatus: 1,
								status: ['in', ['Partially Received', 'Pending', 'Partially Ordered']],
								company: frm.doc.company,
							}
						};
					},
					allow_child_item_selection: true,
					child_fieldname: 'items',
					child_columns: ['item_code', 'description', 'custom_batch_no', 'qty', 'ordered_qty']
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
				}, ['custom_batch_no'], order_by = 'idx asc', limit = 1);
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

	item_code: function (frm, cdt, cdn) {
		let row = locals[cdt][cdn];

		// If we have production plan and custom_batch_no, set it for new items
		if (frm.doc.production_plan && frm.doc.custom_batch_no && row.item_code) {
			frappe.model.set_value(row.doctype, row.name, 'custom_batch_no', frm.doc.custom_batch_no);
		}
		// Item Tax Template
		 if (row.item_code) {
            frappe.db.get_doc("Item", row.item_code)
                .then(item => {

                    if (item.taxes && item.taxes.length > 0) {

                        // Get first Item Tax Template
                        let tax_template = item.taxes[0].item_tax_template;

                        // Set in Purchase Order Item
                        frappe.model.set_value(cdt, cdn, "item_tax_template", tax_template);
                    }
                });
        }
	}
});


function update_date_field_readonly(frm) {
	// Get checkbox value (replace 'enable_date_field' with your actual checkbox fieldname)
	let enable_date = frm.doc.editable_required_date;  // Change this fieldname

	if (enable_date) {
		// Make schedule_date field editable
		frm.set_df_property('schedule_date', 'read_only', 0);
		frappe.show_alert({
			message: __('Required by Date is now editable'),
			indicator: 'green'
		});
	} else {
		// Make schedule_date field read-only
		frm.set_df_property('schedule_date', 'read_only', 1);
	}
}


frappe.ui.form.on('Purchase Order Item', {
	stock_qty: function (frm, cdt, cdn) {
		let row = locals[cdt][cdn];

		// Set pending_qty_in_stock_uom equal to stock_qty
		frappe.model.set_value(cdt, cdn, 'pending_qty_in_stock_uom', row.stock_qty);
	}
});




function set_po_defaults(frm) {

    // Stop if values not selected
    if (!frm.doc.branch || !frm.doc.order_type) return;

    const config = {

        "Sanand": {
            "Domestic Purchase": { series: "SD.fiscal.#####", billing: "Steelstrong-Sanand", shipping: "Steelstrong-Sanand" },
            "Import Purchase": { series: "SI.fiscal.#####", billing: "Steelstrong-Sanand", shipping: "Steelstrong-Sanand" },
            "Consumable Purchase": { series: "SC.fiscal.#####", billing: "Steelstrong-Sanand", shipping: "Steelstrong-Sanand" },
            "Job Work Order": { series: "SJ.fiscal.#####", billing: "Steelstrong-Sanand", shipping: "Steelstrong-Sanand" },
            "Service Order": { series: "SS.fiscal.#####", billing: "Steelstrong-Sanand", shipping: "Steelstrong-Sanand" },
            "Asset Purchase": { series: "SA.fiscal.#####", billing: "Steelstrong-Sanand", shipping: "Steelstrong-Sanand" }
        },

        "Rabale": {
            "Domestic Purchase": { series: "RD.fiscal.#####", billing: "Steelstrong-Rabale", shipping: "Steelstrong-Rabale" },
            "Import Purchase": { series: "RI.fiscal.#####", billing: "Steelstrong-Rabale", shipping: "Steelstrong-Rabale" },
            "Consumable Purchase": { series: "RC.fiscal.#####", billing: "Steelstrong-Rabale", shipping: "Steelstrong-Rabale" },
            "Job Work Order": { series: "RJ.fiscal.#####", billing: "Steelstrong-Rabale", shipping: "Steelstrong-Rabale" },
            "Service Order": { series: "RS.fiscal.#####", billing: "Steelstrong-Rabale", shipping: "Steelstrong-Rabale" },
            "Asset Purchase": { series: "RA.fiscal.#####", billing: "Steelstrong-Rabale", shipping: "Steelstrong-Rabale" }
        },

        "Nandikoor": {
            "Domestic Purchase": { series: "ND.fiscal.#####", billing: "Steelstrong-Nandikoor", shipping: "Steelstrong-Nandikoor" },
            "Import Purchase": { series: "NI.fiscal.#####", billing: "Steelstrong-Nandikoor", shipping: "Steelstrong-Nandikoor" },
            "Consumable Purchase": { series: "NC.fiscal.#####", billing: "Steelstrong-Nandikoor", shipping: "Steelstrong-Nandikoor" },
            "Job Work Order": { series: "NJ.fiscal.#####", billing: "Steelstrong-Nandikoor", shipping: "Steelstrong-Nandikoor" },
            "Service Order": { series: "NS.fiscal.#####", billing: "Steelstrong-Nandikoor", shipping: "Steelstrong-Nandikoor" },
            "Asset Purchase": { series: "NA.fiscal.#####", billing: "Steelstrong-Nandikoor", shipping: "Steelstrong-Nandikoor" }
        }
    };

    let branch = frm.doc.branch;
    let order_type = frm.doc.order_type;

    // Check mapping exists
    if (config[branch] && config[branch][order_type]) {

        let data = config[branch][order_type];

        //  Set Naming Series
        // if (frm.doc.naming_series !== data.series) {
        //     frm.set_value('naming_series', data.series);
        // }

		 //  ONLY for NEW DOC
        if (frm.is_new()) {
           if (frm.doc.naming_series !== data.series) {
            frm.set_value('naming_series', data.series);
        	}
        }

        //  Set Billing Address
        if (frm.doc.billing_address !== data.billing) {
            frm.set_value('billing_address', data.billing);
        }

        //  Set Shipping Address
        if (frm.doc.shipping_address !== data.shipping) {
            frm.set_value('shipping_address', data.shipping);
        }

        // Refresh fields (important)
        frm.refresh_field('naming_series');
        frm.refresh_field('billing_address');
        frm.refresh_field('shipping_address');
    }
}