

function set_supplier_warehouse(frm) {
	if (!frm.doc.supplier) {
		render_po_mould_set_info(frm);
		return;
	}

	// 1. Primary: Use 'warehouse' field configured under Supplier master
	frappe.db.get_value("Supplier", frm.doc.supplier, "warehouse").then(r => {
		if (r && r.message && r.message.warehouse) {
			frm.set_value("supplier_warehouse", r.message.warehouse);
			render_po_mould_set_info(frm);
		} else if (frm.doc.branch) {
			// 2. Fallback: match warehouse by branch and supplier name
			frappe.db.get_list("Warehouse", {
				filters: [
					["Warehouse", "branch", "=", frm.doc.branch],
					["Warehouse", "is_group", "=", 0],
					["Warehouse", "name", "like", `%${frm.doc.supplier}%`]
				],
				fields: ["name"],
				order_by: "name asc",
				limit: 1
			}).then(res => {
				if (res.length) {
					frm.set_value("supplier_warehouse", res[0].name);
				}
				render_po_mould_set_info(frm);
			});
		} else {
			render_po_mould_set_info(frm);
		}
	});
}

function render_po_mould_set_info(frm) {
	if (!frm.fields_dict.mould_set_info) return;

	let items = (frm.doc.items || []).map(row => ({
		item_code: row.item_code,
		fg_item: row.fg_item || ''
	}));

	frappe.call({
		method: "generate_item.mould_set_management.po_enhancement.get_po_mould_set_info",
		args: {
			po_name: frm.doc.name || '',
			supplier: frm.doc.supplier || '',
			supplier_warehouse: frm.doc.supplier_warehouse || '',
			items: JSON.stringify(items)
		},
		callback: function (r) {
			if (r.message && frm.fields_dict.mould_set_info) {
				frm.fields_dict.mould_set_info.$wrapper.html(r.message.html);
			}
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

						// frappe.msgprint(`Linked Contact: ${r.message}`);
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
	supplier_warehouse: function (frm) {
		render_po_mould_set_info(frm);
	},
	items_add: function (frm) {
		render_po_mould_set_info(frm);
	},
	items_remove: function (frm) {
		render_po_mould_set_info(frm);
	},
	order_type: function (frm) {
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

	items_on_form_rendered: function (frm, grid_row) {
		_attach_fetch_serial_button(frm, grid_row);
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
		render_po_mould_set_info(frm);

		if (frm.doc.docstatus !== 0) {
			frm.fields_dict.items?.grid?.wrapper?.find('.fetch-serial-btn-wrapper').remove();
		}







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

	form_render: function (frm, cdt, cdn) {
		let grid_row = frm.fields_dict.items?.grid?.grid_rows_by_docname?.[cdn];
		_attach_fetch_serial_button(frm, grid_row);
	},

	fetch_serial_number: function (frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		_validate_and_open_po(frm, row);
	},

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
		render_po_mould_set_info(frm);
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
	qty: update_pending_qty,
	uom: update_pending_qty,
	stock_qty: update_pending_qty
});

function update_pending_qty(frm, cdt, cdn) {
	let row = locals[cdt][cdn];

	if (row.uom && row.stock_uom) {
		if (row.uom === row.stock_uom) {
			frappe.model.set_value(
				cdt,
				cdn,
				'pending_qty_in_stock_uom',
				row.qty || 0
			);
		} else {
			frappe.model.set_value(
				cdt,
				cdn,
				'pending_qty_in_stock_uom',
				row.stock_qty || 0
			);
		}
	}
}




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

/* ══════════════════════════════════════════════════════════════════════════
   SERIAL NUMBER ALLOCATION FOR PURCHASE ORDER
   Identical functionality to stock_entry.js, saving serial numbers
   as a comma-separated list in line 'remarks'.
══════════════════════════════════════════════════════════════════════════ */

function _attach_fetch_serial_button(frm, grid_row) {
	if (!grid_row || !grid_row.grid_form) return;

	// Do not show button after PO submission (only show in Draft mode)
	if (frm.doc.docstatus !== 0) {
		grid_row.grid_form.$wrapper?.find('.fetch-serial-btn-wrapper').remove();
		return;
	}

	const row = grid_row.doc;
	const batch_field = grid_row.grid_form.fields_dict['custom_batch_no'];
	if (!batch_field || !batch_field.$wrapper) return;

	if (batch_field.$wrapper.find('.btn-fetch-serial-no').length) return;

	const icon_html = frappe.utils?.icon
		? frappe.utils.icon('list', 'xs')
		: '<i class="fa fa-list"></i>';

	const $btn_container = $(`
		<div style="margin-top: 6px;" class="fetch-serial-btn-wrapper">
			<button type="button" class="btn btn-xs btn-default btn-fetch-serial-no" style="font-weight: 500; display: inline-flex; align-items: center; gap: 5px;">
				${icon_html}<span>${__("Fetch Serial Number")}</span>
			</button>
		</div>
	`);

	$btn_container.find('button').on('click', function (e) {
		e.preventDefault();
		e.stopPropagation();
		_validate_and_open_po(frm, row);
	});

	batch_field.$wrapper.append($btn_container);
}

function _validate_and_open_po(frm, row) {
	const batch = row.custom_batch_no || row.batch_no || "";

	if (!batch) {
		frappe.msgprint({
			title: __("Batch Not Selected"),
			message: __(
				"Please select a <strong>Batch Number</strong> " +
				"before allocating serial numbers."
			),
			indicator: "orange",
		});
		return;
	}

	const qty = parseFloat(row.qty) || 0;
	if (qty <= 0) {
		frappe.msgprint(__("Please enter a valid Quantity before allocating serial numbers."));
		return;
	}

	_fetch_and_open_po(frm, row, batch, qty);
}

function _fetch_and_open_po(frm, row, batch, qty) {
	const PAGE_SIZE = 500;
	let allSerials = [];
	let start = 0;

	function fetchPage() {
		frappe.call({
			method: "frappe.client.get_list",
			args: {
				doctype: "Serial Number",
				filters: {
					docstatus: 1,
					batch: batch,
					purchase_order: ""
				},
				fields: ["name"],
				limit_start: start,
				limit_page_length: PAGE_SIZE,
				order_by: "name asc",
			},
			freeze: true,
			freeze_message: __("Fetching Serial Numbers…"),
			callback: function (r) {
				const page = (r.message || []).map((s) => s.name);
				allSerials = allSerials.concat(page);

				if (page.length === PAGE_SIZE) {
					start += PAGE_SIZE;
					fetchPage();
				} else {
					const existing = _parse_existing_serials_po(row);
					// Ensure any already-assigned serials on this row are available in pool
					existing.forEach((sn) => {
						if (!allSerials.includes(sn)) {
							allSerials.push(sn);
						}
					});
					allSerials.sort();

					if (!allSerials.length) {
						frappe.msgprint({
							title: __("No Serial Numbers Found"),
							message: __(
								`No serial numbers found for Batch ` +
								`<strong>${frappe.utils.escape_html(batch)}</strong>.`
							),
							indicator: "red",
						});
						return;
					}

					_build_dialog_po(frm, row, batch, qty, allSerials, existing);
				}
			},
			error: function () {
				frappe.msgprint({
					title: __("Error"),
					message: __("Failed to fetch serial numbers. Please try again."),
					indicator: "red",
				});
			},
		});
	}

	fetchPage();
}

const CHUNK_SIZE_PO = 100;

function _build_dialog_po(frm, row, batch, qty, allSerials, preSelected) {
	const STYLE_ID = "sna-style";
	if (!document.getElementById(STYLE_ID)) {
		const style = document.createElement("style");
		style.id = STYLE_ID;
		style.textContent = `
			.sna-root { font-family: var(--font-stack, sans-serif); }
			.sna-info-bar {
				display: flex; flex-wrap: wrap; gap: 8px;
				padding: 10px 0 14px;
				border-bottom: 1px solid var(--border-color, #ddd);
				margin-bottom: 12px;
			}
			.sna-chip {
				display: flex; flex-direction: column;
				background: var(--control-bg, #f5f7fa);
				border: 1px solid var(--border-color, #d1d8dd);
				border-radius: 6px; padding: 6px 14px;
				min-width: 110px;
			}
			.sna-label {
				font-size: 10px; color: var(--text-muted, #888);
				text-transform: uppercase; letter-spacing: .5px;
			}
			.sna-chip strong { font-size: 14px; margin-top: 3px; }
			.sna-chip.primary strong { color: var(--primary, #5e64ff); }
			.sna-chip.success strong { color: var(--green-600, #28a745); }
			.sna-toolbar {
				display: flex; align-items: center; gap: 8px;
				margin-bottom: 10px;
			}
			.sna-search { flex: 1; }
			.sna-bulk-btns { display: flex; gap: 6px; white-space: nowrap; }
			.sna-list-wrap {
				border: 1px solid var(--border-color, #d1d8dd);
				border-radius: 6px;
				height: 360px;
				overflow-y: auto;
				background: var(--card-bg, #fff);
				will-change: scroll-position;
			}
			.sna-row {
				display: flex; align-items: center;
				padding: 7px 12px;
				border-bottom: 1px solid var(--border-color, #f0f0f0);
				cursor: pointer;
				transition: background .1s;
				user-select: none;
			}
			.sna-row:last-child { border-bottom: none; }
			.sna-row:hover     { background: var(--blue-50, #f0f4ff); }
			.sna-row.selected  { background: var(--green-50, #f0faf4); }
			.sna-row input[type=checkbox] {
				margin-right: 10px; width: 15px; height: 15px;
				cursor: pointer; flex-shrink: 0;
				accent-color: var(--primary, #5e64ff);
			}
			.sna-serial-label {
				font-size: 13px;
				font-family: var(--monospace-font, "Courier New", monospace);
				flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
			}
			.sna-badge {
				flex-shrink: 0; font-size: 10px; padding: 2px 7px;
				border-radius: 10px; margin-left: 8px;
				background: var(--green-100, #d4edda);
				color: var(--green-700, #155724);
				display: none;
			}
			.sna-row.selected .sna-badge { display: inline; }
			.sna-empty {
				padding: 40px; text-align: center;
				color: var(--text-muted, #888); font-size: 13px;
			}
			.sna-status-bar {
				margin-top: 10px; font-size: 12px;
				color: var(--text-muted, #888);
				display: flex; justify-content: space-between;
			}
			.sna-status-bar .warn { color: var(--orange-500, #e67e22); font-weight: 600; }
			.sna-status-bar .ok   { color: var(--green-600, #28a745); font-weight: 600; }
		`;
		document.head.appendChild(style);
	}

	const html = `
		<div class="sna-root">
			<div class="sna-info-bar">
				<div class="sna-chip">
					<span class="sna-label">Batch</span>
					<strong title="${frappe.utils.escape_html(batch)}">
						${frappe.utils.escape_html(batch)}
					</strong>
				</div>
				<div class="sna-chip primary">
					<span class="sna-label">Required QTY</span>
					<strong>${qty}</strong>
				</div>
				<div class="sna-chip success">
					<span class="sna-label">Selected</span>
					<strong class="js-sel-count">0</strong>
				</div>
				<div class="sna-chip">
					<span class="sna-label">Available</span>
					<strong>${allSerials.length}</strong>
				</div>
			</div>

			<div class="sna-toolbar">
				<input type="text" class="sna-search form-control"
					   placeholder="&#128269;  Search serial numbers…" />
				<div class="sna-bulk-btns">
					<button class="btn btn-xs btn-default js-select-visible">
						Select All Visible
					</button>
					<button class="btn btn-xs btn-default js-clear-all">
						Clear All
					</button>
				</div>
			</div>

			<div class="sna-list-wrap js-wrap">
				<div class="sna-list js-list"></div>
			</div>

			<div class="sna-status-bar">
				<span class="js-showing">Showing 0 of ${allSerials.length}</span>
				<span class="js-diff"></span>
			</div>
		</div>
	`;

	const dialog = new frappe.ui.Dialog({
		title: __("Add Serial Numbers"),
		size: "large",
		fields: [{ fieldtype: "HTML", fieldname: "sna_body" }],
		primary_action_label: __("Add Serial Numbers"),
		primary_action: function () {
			const selected = Array.from(selectedSet);
			_handle_allocation_po(frm, row, allSerials, selected, qty, dialog, batch);
		},
		secondary_action_label: __("Cancel"),
		secondary_action: function () { dialog.hide(); },
	});

	dialog.fields_dict.sna_body.$wrapper.html(html);
	dialog.show();

	const selectedSet = new Set(preSelected);
	let visibleSerials = [...allSerials];
	let renderedCount = 0;

	const $root     = dialog.$wrapper.find(".sna-root");
	const $list     = $root.find(".js-list");
	const $wrap     = $root.find(".js-wrap");
	const $selCount = $root.find(".js-sel-count");
	const $showing  = $root.find(".js-showing");
	const $diff     = $root.find(".js-diff");
	const $search   = $root.find(".sna-search");

	function renderChunk(reset) {
		if (reset) {
			$list.empty();
			renderedCount = 0;
		}

		const slice = visibleSerials.slice(renderedCount, renderedCount + CHUNK_SIZE_PO);
		if (!slice.length) {
			if (!renderedCount) {
				$list.html('<div class="sna-empty">No serial numbers found for this search.</div>');
			}
			return;
		}

		const frag = document.createDocumentFragment();
		slice.forEach((sn) => {
			const sel = selectedSet.has(sn);
			const div = document.createElement("div");
			div.className = "sna-row" + (sel ? " selected" : "");
			div.dataset.sn = sn;
			div.innerHTML =
				`<input type="checkbox" ${sel ? "checked" : ""} />` +
				`<span class="sna-serial-label" title="${frappe.utils.escape_html(sn)}">${frappe.utils.escape_html(sn)}</span>` +
				`<span class="sna-badge">&#10003;</span>`;
			frag.appendChild(div);
		});

		$list[0].appendChild(frag);
		renderedCount += slice.length;
		$showing.text(`Showing ${renderedCount} of ${visibleSerials.length}`);
	}

	function updateCounter() {
		const n = selectedSet.size;
		$selCount.text(n);
		const diff = n - qty;
		if (diff === 0) {
			$diff.removeClass("warn").addClass("ok").text("✓ Exact match");
		} else if (diff < 0) {
			$diff.removeClass("ok").addClass("warn").text(`${Math.abs(diff)} short of QTY`);
		} else {
			$diff.removeClass("ok").addClass("warn").text(`${diff} over QTY`);
		}
	}

	renderChunk(true);
	updateCounter();

	$wrap.on("scroll", function () {
		if (this.scrollHeight - this.scrollTop - this.clientHeight < 200) {
			renderChunk(false);
		}
	});

	$list.on("click", ".sna-row", function (e) {
		const sn = this.dataset.sn;
		const cb = this.querySelector("input[type=checkbox]");

		if (e.target !== cb) cb.checked = !cb.checked;

		if (cb.checked) {
			selectedSet.add(sn);
			this.classList.add("selected");
		} else {
			selectedSet.delete(sn);
			this.classList.remove("selected");
		}
		updateCounter();
	});

	let searchTimer;
	$search.on("input", function () {
		clearTimeout(searchTimer);
		searchTimer = setTimeout(() => {
			const q = this.value.trim().toLowerCase();
			visibleSerials = q
				? allSerials.filter((s) => s.toLowerCase().includes(q))
				: [...allSerials];
			renderChunk(true);
		}, 200);
	});

	$root.find(".js-select-visible").on("click", function () {
		visibleSerials.forEach((sn) => selectedSet.add(sn));
		$list.find(".sna-row").each(function () {
			this.classList.add("selected");
			this.querySelector("input[type=checkbox]").checked = true;
		});
		updateCounter();
	});

	$root.find(".js-clear-all").on("click", function () {
		selectedSet.clear();
		$list.find(".sna-row").each(function () {
			this.classList.remove("selected");
			this.querySelector("input[type=checkbox]").checked = false;
		});
		updateCounter();
	});
}

function _handle_allocation_po(frm, row, allSerials, selected, qty, dialog, batch) {
	const selCount = selected.length;

	/* ── A: Exact match ─────────────────────────────────────────────────── */
	if (selCount === qty) {
		_apply_serials_po(frm, row, selected);
		dialog.hide();
		frappe.show_alert({
			message: __(`${selCount} serial number(s) added successfully.`),
			indicator: "green",
		});
		return;
	}

	/* ── B: Fewer than qty ──────────────────────────────────────────────── */
	if (selCount < qty) {
		const needed = qty - selCount;

		frappe.confirm(
			__(
				`You selected <strong>${selCount}</strong> serial number(s), ` +
				`but the required QTY is <strong>${qty}</strong>.<br><br>` +
				`<strong>${needed}</strong> remaining serial number(s) will be ` +
				`<strong>auto-selected randomly</strong> from the available pool.<br><br>` +
				`Do you want to proceed?`
			),
			function () {
				const unselected = allSerials.filter((s) => !selected.includes(s));

				if (unselected.length < needed) {
					frappe.msgprint({
						title: __("Insufficient Serial Numbers"),
						message: __(
							`Only <strong>${allSerials.length}</strong> serial number(s) ` +
							`are available for Batch <strong>${frappe.utils.escape_html(batch)}</strong>, ` +
							`which is not enough to fulfil QTY of <strong>${qty}</strong>.`
						),
						indicator: "red",
					});
					return;
				}

				const autoFilled = _random_sample_po(unselected, needed);
				const final = [...selected, ...autoFilled];
				_apply_serials_po(frm, row, final);
				dialog.hide();
				frappe.show_alert({
					message: __(
						`${selCount} manually selected + ${autoFilled.length} auto-filled ` +
						`= <strong>${final.length}</strong> serial number(s) added.`
					),
					indicator: "green",
				});
			},
			function () { /* no-op */ }
		);
		return;
	}

	/* ── C: More than qty ───────────────────────────────────────────────── */
	if (selCount > qty) {
		const excess = selCount - qty;

		frappe.confirm(
			__(
				`You selected <strong>${selCount}</strong> serial number(s), ` +
				`but the required QTY is only <strong>${qty}</strong>.<br><br>` +
				`<strong>${excess}</strong> serial number(s) will be ` +
				`<strong>removed randomly</strong> so that exactly ${qty} are added.<br><br>` +
				`Do you want to proceed?`
			),
			function () {
				const trimmed = _random_sample_po(selected, qty);
				_apply_serials_po(frm, row, trimmed);
				dialog.hide();
				frappe.show_alert({
					message: __(
						`Trimmed to <strong>${qty}</strong> serial number(s) and added successfully.`
					),
					indicator: "green",
				});
			},
			function () { /* no-op */ }
		);
		return;
	}
}

/** Write the comma-separated serial list to row remarks and refresh the form */
function _apply_serials_po(frm, row, serials) {
	frappe.model.set_value(row.doctype, row.name, "remarks", serials.join(", "));
	frm.dirty();
	frm.refresh_field("items");
}

/** Parse comma / newline separated serials from existing row remarks */
function _parse_existing_serials_po(row) {
	return (row.remarks || "")
		.split(/[\n,]/)
		.map((s) => s.trim())
		.filter(Boolean);
}

function _random_sample_po(arr, k) {
	if (k >= arr.length) return [...arr];
	const pool = [...arr];
	for (let i = 0; i < k; i++) {
		const j = i + Math.floor(Math.random() * (pool.length - i));
		const tmp = pool[i];
		pool[i] = pool[j];
		pool[j] = tmp;
	}
	return pool.slice(0, k);
}