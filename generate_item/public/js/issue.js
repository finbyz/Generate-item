// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt

frappe.ui.form.on("Issue", {
	onload(frm) {
		if (frm.is_new()) {
			if (!frm.doc.status) {
				frm.set_value("status", "Open");
			}
			if (!frm.doc.custom_complaint_status) {
				frm.set_value("custom_complaint_status", "Open");
			}
			if (!frm.doc.custom_complaint_reg_date) {
				frm.set_value("custom_complaint_reg_date", frappe.datetime.get_today());
			}
		}
	},

	refresh(frm) {
		// Hide custom_complaint_status field so only standard Status (Open, In Process, Closed) is displayed
		frm.set_df_property("custom_complaint_status", "hidden", 1);

		// TASK41458: Sales Order lists only submitted orders of the selected customer
		frm.set_query("custom_sales_order", () => ({
			filters: Object.assign({ docstatus: 1 }, frm.doc.customer ? { customer: frm.doc.customer } : {}),
		}));
		generate_item.valve.setup_serial_button(frm);

		frm.set_query("custom_customer_address", () => ({
			query: "frappe.contacts.doctype.address.address.address_query",
			filters: {
				link_doctype: "Customer",
				link_name: frm.doc.customer,
			},
		}));

		// Filter Product in Multiple Valves to enabled Item Generator Templates
		frm.set_query("product", "custom_valves", () => ({
			filters: { disabled: 0 },
		}));

		// Load dropdown options for Multiple Valves child table matching Item Generator logic
		load_valve_attribute_options(frm);

		// Quick link to Customer Complaint Register report
		frm.add_custom_button(__("Complaint Register"), function () {
			frappe.set_route("query-report", "Customer Complaint Register", {
				customer: frm.doc.customer || undefined,
			});
		}, __("View"));

		// Quick action to add a progress update if not new
		if (!frm.is_new()) {
			frm.add_custom_button(__("Add Progress Update"), function () {
				let d = new frappe.ui.Dialog({
					title: __("Add Complaint Progress Update"),
					fields: [
						{
							fieldname: "status",
							label: __("Status"),
							fieldtype: "Select",
							options: "Open\nIn Process\nClosed",
							default: frm.doc.status || "Open",
							reqd: 1,
						},
						{
							fieldname: "responsible_department",
							label: __("Responsible Department"),
							fieldtype: "Data",
							default: frm.doc.custom_responsible_department || "",
						},
						{
							fieldname: "action_by",
							label: __("Action By"),
							fieldtype: "Data",
							default: frm.doc.custom_action_taken_by || frappe.session.user_fullname,
						},
						{
							fieldname: "action_remarks",
							label: __("Action Decided / Remarks"),
							fieldtype: "Small Text",
							default: frm.doc.custom_action_remarks || "",
						},
						{ fieldtype: "Section Break", label: __("Visit Schedule") },
						{
							fieldname: "ssv_visiting_engineer",
							label: __("SSV Visiting Engineer"),
							fieldtype: "Data",
							default: frm.doc.custom_ssv_visiting_engineer || "",
						},
						{
							fieldname: "visit_schedule_date",
							label: __("Visit Schedule Date"),
							fieldtype: "Date",
							default: frm.doc.custom_visit_schedule_date || "",
						},
						{
							fieldname: "visit_schedule_notes",
							label: __("Visit Schedule Notes"),
							fieldtype: "Small Text",
							default: frm.doc.custom_visit_schedule_notes || "",
						},
					],
					primary_action_label: __("Save Update"),
					primary_action(values) {
						if (frm.is_dirty()) {
							frappe.msgprint({
								title: __("Unsaved Changes"),
								message: __("Please save your current changes on the form first before adding a progress update."),
								indicator: "orange",
							});
							return;
						}

						frappe.call({
							method: "generate_item.customer_complaint.issue.add_complaint_progress_update",
							args: {
								issue_id: frm.doc.name,
								status: values.status,
								complaint_status: values.status,
								responsible_department: values.responsible_department,
								action_by: values.action_by,
								action_remarks: values.action_remarks,
								ssv_visiting_engineer: values.ssv_visiting_engineer,
								visit_schedule_date: values.visit_schedule_date,
								visit_schedule_notes: values.visit_schedule_notes,
							},
							freeze: true,
							freeze_message: __("Saving progress update..."),
							callback(r) {
								if (r.message && r.message.success) {
									d.hide();
									frappe.show_alert({
										message: __("Progress update saved successfully"),
										indicator: "green",
									});
									frm.reload_doc();
								}
							},
						});
					},
				});
				d.show();
			});
		}
	},

	custom_sales_order(frm) {
		const sales_order = frm.doc.custom_sales_order;
		if (!sales_order) {
			return;
		}

		frm.__setting_from_sales_order = true;
		frappe.db.get_value(
			"Sales Order",
			sales_order,
			["customer", "customer_name", "project", "customer_address", "address_display"],
			function (r) {
				if (r && frm.doc.custom_sales_order === sales_order) {
					frm.set_value("customer", r.customer || "");
					frm.set_value("customer_name", r.customer_name || "");
					frm.set_value("custom_project_name", r.project || "");
					if (frm.fields_dict && frm.fields_dict.project) {
						frm.set_value("project", r.project || "");
					}
					if (r.customer_address) {
						frm.set_value("custom_customer_address", r.customer_address);
						frm.set_value("custom_address_display", r.address_display || "");
					} else {
						// Sales Order had no specific address; trigger customer address defaulting
						delete frm.__setting_from_sales_order;
						if (r.customer) {
							frm.trigger("customer");
						} else {
							frm.set_value("custom_customer_address", "");
							frm.set_value("custom_address_display", "");
						}
						return;
					}
				}
				setTimeout(() => {
					delete frm.__setting_from_sales_order;
				}, 500);
			}
		);
	},

	customer(frm) {
		if (frm.__setting_from_sales_order) {
			return;
		}

		const customer = frm.doc.customer;
		generate_item.valve.clear_mismatched_sales_order(frm); // TASK41458
		if (!customer) {
			frm.set_value("customer_name", "");
			frm.set_value("custom_customer_address", "");
			frm.set_value("custom_address_display", "");
			return;
		}

		frappe.db.get_value(
			"Customer",
			customer,
			["customer_name", "customer_primary_address", "primary_address"],
			function (r) {
				if (frm.doc.customer !== customer) {
					return;
				}

				if (r && r.customer_name) {
					frm.set_value("customer_name", r.customer_name);
				}

				if (r && r.customer_primary_address) {
					frm.set_value("custom_customer_address", r.customer_primary_address);
					if (r.primary_address) {
						frm.set_value("custom_address_display", r.primary_address);
					}
					return;
				}

				// If customer_primary_address is not set on Customer doc, query default linked address
				frappe.call({
					method: "frappe.contacts.doctype.address.address.get_default_address",
					args: {
						doctype: "Customer",
						name: customer,
						sort_key: "is_primary_address",
					},
					callback(res) {
						if (frm.doc.customer !== customer) {
							return;
						}
						if (res && res.message) {
							frm.set_value("custom_customer_address", res.message);
						} else {
							frm.set_value("custom_customer_address", "");
							frm.set_value("custom_address_display", "");
						}
					},
				});
			}
		);
	},

	custom_customer_address(frm) {
		const customer_address = frm.doc.custom_customer_address;
		if (!customer_address) {
			frm.set_value("custom_address_display", "");
			return;
		}

		frappe.call({
			method: "frappe.contacts.doctype.address.address.get_address_display",
			args: { address_dict: customer_address },
			callback(r) {
				if (frm.doc.custom_customer_address === customer_address) {
					frm.set_value("custom_address_display", r.message || "");
				}
			},
			error() {
				frappe.msgprint(__("Could not load the selected customer address."));
			},
		});
	},

	custom_order_type(frm) {
		if (frm.doc.custom_order_type === "Old Order") {
			frm.set_value("custom_sales_order", "");
		} else if (frm.doc.custom_order_type === "Current Order") {
			frm.set_value("custom_old_sales_order", "");
		}
		// Manual valve fields show / become mandatory by Order Type (TASK41461)
		frm.refresh_field("custom_valves");

		generate_item.valve.setup_serial_button(frm);

		// Current Order: fill every line from its item and serial (TASK41460 / TASK41459)
		if (frm.doc.custom_order_type === "Current Order") {
			(frm.doc.custom_valves || []).forEach((row) => {
				generate_item.valve.fill_from_item(frm, row.doctype, row.name);
				generate_item.valve.fill_warranty(frm, row.doctype, row.name);
			});
		}
	},

	status(frm) {
		const status = frm.doc.status;
		if (status === "Closed") {
			frm.set_value("custom_complaint_status", "Close");
			if (!frm.doc.custom_closure_date) {
				frm.set_value("custom_closure_date", frappe.datetime.get_today());
			}
			if (!frm.doc.custom_closure_by) {
				frm.set_value("custom_closure_by", frappe.session.user);
			}
		} else if (status === "In Process") {
			frm.set_value("custom_complaint_status", "Action in Progress");
		} else if (status === "Open") {
			frm.set_value("custom_complaint_status", "Open");
		}
	},

	custom_complaint_status(frm) {
		const comp_status = frm.doc.custom_complaint_status;
		if (comp_status === "Close" || comp_status === "Closed") {
			if (frm.doc.status !== "Closed") {
				frm.set_value("status", "Closed");
			}
			if (!frm.doc.custom_closure_date) {
				frm.set_value("custom_closure_date", frappe.datetime.get_today());
			}
			if (!frm.doc.custom_closure_by) {
				frm.set_value("custom_closure_by", frappe.session.user);
			}
		} else if (comp_status === "Action in Progress" || comp_status === "In Process") {
			if (frm.doc.status !== "In Process") {
				frm.set_value("status", "In Process");
			}
		} else if (comp_status === "Open") {
			if (frm.doc.status !== "Open") {
				frm.set_value("status", "Open");
			}
		}
	},
});

frappe.ui.form.on("Issue Valve", {
	custom_valves_add(frm, cdt, cdn) {
		// One valve per line (TASK41461)
		frappe.model.set_value(cdt, cdn, "qty", 1);
	},

	item_code(frm, cdt, cdn) {
		generate_item.valve.fill_from_item(frm, cdt, cdn);
	},

	serial_number(frm, cdt, cdn) {
		generate_item.valve.lookup_serial(frm, cdt, cdn);
		generate_item.valve.fill_warranty(frm, cdt, cdn);
	},

	form_render(frm, cdt, cdn) {
		const row = locals[cdt] && locals[cdt][cdn];
		if (row && row.product) {
			load_valve_attribute_options(frm, row.product, cdt, cdn);
		} else if (frm.__valve_attribute_options) {
			apply_valve_attribute_options(frm, frm.__valve_attribute_options);
		}
	},

	product(frm, cdt, cdn) {
		const row = locals[cdt] && locals[cdt][cdn];
		if (!row) return;

		const target_fields = ["valve_type", "size", "rating", "shell_moc", "operator"];

		// Clear previously populated fields so stale data does not linger when switching templates
		target_fields.forEach((fn) => {
			frappe.model.set_value(cdt, cdn, fn, "");
		});

		if (!row.product) {
			load_valve_attribute_options(frm);
			return;
		}

		const template_name = row.product;
		load_valve_attribute_options(frm, template_name, cdt, cdn);
	},
});

function load_valve_attribute_options(frm, template_name, cdt, cdn) {
	frappe.call({
		method: "generate_item.customer_complaint.issue.get_valve_attribute_options",
		args: {
			template_name: template_name || null,
		},
		callback(r) {
			if (r && r.message) {
				if (cdt && cdn) {
					const row = locals[cdt] && locals[cdt][cdn];
					if (!row || row.product !== template_name) {
						return; // In-flight response superseded by a newer selection
					}
				}
				frm.__valve_attribute_options = r.message;
				apply_valve_attribute_options(frm, r.message);
			}
		},
	});
}

function apply_valve_attribute_options(frm, options_map) {
	if (!frm.fields_dict.custom_valves || !frm.fields_dict.custom_valves.grid) {
		return;
	}

	const grid = frm.fields_dict.custom_valves.grid;
	const target_fields = ["valve_type", "size", "rating", "shell_moc", "operator"];

	target_fields.forEach((fieldname) => {
		let opts = options_map[fieldname] || [];
		if (Array.isArray(opts)) {
			if (opts.length > 0 && opts[0] !== "") {
				opts = [""].concat(opts);
			}
		}

		grid.update_docfield_property(fieldname, "options", opts);
		grid.update_docfield_property(fieldname, "fieldtype", "Select");

		let df = frappe.meta.get_docfield("Issue Valve", fieldname, frm.doc.name);
		if (df) {
			df.fieldtype = "Select";
			df.options = Array.isArray(opts) ? opts.join("\n") : opts;
		}

		// Update active row form controls if open
		if (grid.open_grid_row && grid.open_grid_row.fields_dict && grid.open_grid_row.fields_dict[fieldname]) {
			let ctrl = grid.open_grid_row.fields_dict[fieldname];
			let opt_str = Array.isArray(opts) ? opts.join("\n") : opts;
			ctrl.df.options = opt_str;
			if (ctrl.set_options) {
				ctrl.set_options(opt_str);
			}
			if (ctrl.refresh) {
				ctrl.refresh();
			}
		}
	});

	frm.refresh_field("custom_valves");
}

function ensure_grid_option(frm, fieldname, value) {
	if (!value || !frm.fields_dict.custom_valves || !frm.fields_dict.custom_valves.grid) {
		return value;
	}

	const grid = frm.fields_dict.custom_valves.grid;
	const df = grid.docfields && grid.docfields.find((d) => d.fieldname === fieldname);
	if (!df) {
		return value;
	}

	let current_opts = Array.isArray(df.options)
		? df.options
		: typeof df.options === "string"
		? df.options.split("\n")
		: [];

	const lower_val = String(value).trim().toLowerCase();
	const existing_match = current_opts.find((opt) => opt && opt.trim().toLowerCase() === lower_val);
	if (existing_match) {
		return existing_match;
	}

	current_opts.push(value);
	grid.update_docfield_property(fieldname, "options", current_opts);

	let meta_df = frappe.meta.get_docfield("Issue Valve", fieldname, frm.doc.name);
	if (meta_df) {
		meta_df.options = current_opts.join("\n");
	}

	return value;
}

// ------------------------------------------------------------------
// Shared valve helpers (TASK41460 / TASK41459). Any valve table with the
// fields item_code, valve_type, size, rating, shell_moc, operator,
// serial_number and warranty_status can use them.
// Only Current Order lines are filled; Old Order lines stay manual.
// ------------------------------------------------------------------
frappe.provide("generate_item.valve");

generate_item.valve.FIELDS = ["valve_type", "size", "rating", "shell_moc", "operator"];

generate_item.valve.fill_from_item = function (frm, cdt, cdn) {
	const row = locals[cdt] && locals[cdt][cdn];
	if (!row || frm.doc.custom_order_type !== "Current Order") return;

	if (!row.item_code) {
		generate_item.valve.FIELDS.forEach((fn) => frappe.model.set_value(cdt, cdn, fn, ""));
		return;
	}

	const item_code = row.item_code;
	frappe.call({
		method: "generate_item.customer_complaint.issue.get_valve_details",
		args: { item_code: item_code },
		callback(r) {
			const current = locals[cdt] && locals[cdt][cdn];
			if (!current || current.item_code !== item_code) return; // superseded
			const details = r.message || {};
			if (!details.found) {
				frappe.show_alert({
					message: __("No Item Generator record found for {0}. Valve details were not filled.", [item_code]),
					indicator: "orange",
				});
				return;
			}
			generate_item.valve.FIELDS.forEach((fn) => {
				const value = ensure_grid_option(frm, fn, details[fn] || "");
				frappe.model.set_value(cdt, cdn, fn, value || "");
			});
		},
	});
};

generate_item.valve.fill_warranty = function (frm, cdt, cdn, { quiet = false } = {}) {
	const row = locals[cdt] && locals[cdt][cdn];
	if (!row || frm.doc.custom_order_type !== "Current Order") return;

	// No serial: the line has no warranty to show
	if (!row.serial_number) {
		if (row.warranty_status) frappe.model.set_value(cdt, cdn, "warranty_status", "");
		if (row.remaining_warranty_days != null) frappe.model.set_value(cdt, cdn, "remaining_warranty_days", null);
		return;
	}

	const serial_no = row.serial_number;
	frappe.call({
		method: "generate_item.customer_complaint.issue.get_warranty_info",
		args: { serial_no: serial_no },
		callback(r) {
			const current = locals[cdt] && locals[cdt][cdn];
			if (!current || current.serial_number !== serial_no) return; // superseded
			const info = r.message || {};
			// Always replace the old values, so nothing from a previous serial or date stays
			frappe.model.set_value(cdt, cdn, "warranty_status", info.status || "");
			frappe.model.set_value(cdt, cdn, "remaining_warranty_days", info.remaining_days ?? null);
			if (!info.expiry_date && !quiet) {
				frappe.show_alert({
					message: __("Serial {0} has no warranty expiry date. Please select the Warranty Status.", [serial_no]),
					indicator: "orange",
				});
			}
		},
	});
};

// ------------------------------------------------------------------
// TASK41458: Current Order serial picker and reverse lookup
// ------------------------------------------------------------------

// Button on Draft complaints with Order Type = Current Order
generate_item.valve.setup_serial_button = function (frm) {
	const label = __("Get Serials from Sales Order");
	frm.remove_custom_button(label);
	if (frm.doc.docstatus !== 0 || frm.doc.custom_order_type !== "Current Order") return;
	frm.add_custom_button(label, () => generate_item.valve.open_serial_picker(frm));
};

// Typing a serial on a Current Order line fills Sales Order, batch, item and customer
generate_item.valve.lookup_serial = function (frm, cdt, cdn) {
	const row = locals[cdt] && locals[cdt][cdn];
	if (!row || frm.doc.custom_order_type !== "Current Order" || !row.serial_number) return;

	const serial_no = row.serial_number;
	frappe.call({
		method: "generate_item.customer_complaint.serial_lookup.get_serial_details",
		args: { serial_no: serial_no },
		callback(r) {
			const current = locals[cdt] && locals[cdt][cdn];
			if (!current || current.serial_number !== serial_no) return; // superseded
			const d = r.message || {};
			if (!d.item_code && !d.sales_order) {
				frappe.show_alert({ message: __("Serial {0} was not found in stock or in the serial register.", [serial_no]), indicator: "orange" });
				return;
			}
			if (d.batch_no) frappe.model.set_value(cdt, cdn, "batch_no", d.batch_no);
			if (d.sales_order) frappe.model.set_value(cdt, cdn, "sales_order", d.sales_order);
			if (d.item_code && current.item_code !== d.item_code) {
				frappe.model.set_value(cdt, cdn, "item_code", d.item_code); // fills the valve details
			}
			if (d.customer && !frm.doc.customer) frm.set_value("customer", d.customer);
			if (d.sales_order && !frm.doc.custom_sales_order) frm.set_value("custom_sales_order", d.sales_order);
			if (d.customer && frm.doc.customer && d.customer !== frm.doc.customer) {
				frappe.show_alert({
					message: __("Serial {0} was delivered to {1}, not to {2}.", [serial_no, d.customer, frm.doc.customer]),
					indicator: "orange",
				}, 8);
			}
		},
	});
};

// Dialog modelled on Valve Assembly "Get Item from Serial Register", reading delivered serials
generate_item.valve.open_serial_picker = function (frm) {
	if (!frm.doc.customer) {
		frappe.msgprint(__("Please select the Customer first."));
		return;
	}

	const dialog = new frappe.ui.Dialog({
		title: __("Get Serials from Sales Order"),
		size: "extra-large",
		fields: [
			{ fieldtype: "Section Break", label: __("Search") },
			{
				fieldname: "sales_order", label: __("Sales Order"), fieldtype: "Link", options: "Sales Order", reqd: 1,
				default: frm.doc.custom_sales_order || "",
				get_query: () => ({ filters: { docstatus: 1, customer: frm.doc.customer } }),
				onchange: () => { dialog.set_value("batch_no", ""); dialog.__batches = null; },
			},
			{ fieldtype: "Column Break" },
			{
				fieldname: "batch_no", label: __("Batch No"), fieldtype: "Link", options: "Batch",
				get_query: () => ({ filters: { name: ["in", dialog.__batches || [""]] } }),
			},
			{ fieldtype: "Column Break" },
			{ fieldname: "txt", label: __("Serial No / Item"), fieldtype: "Data", description: __("Part of a serial number or item code") },
			{ fieldtype: "Column Break" },
			{ fieldname: "search", label: __("Search"), fieldtype: "Button" },
			{ fieldtype: "Section Break", label: __("Delivered Serials") },
			{ fieldname: "selection_toolbar", fieldtype: "HTML" },
			{
				fieldname: "items", fieldtype: "Table", cannot_add_rows: true, cannot_delete_rows: true, in_place_edit: false, data: [],
				fields: [
					{ fieldname: "serial_no", label: __("Serial No"), fieldtype: "Link", options: "Serial No", in_list_view: 1, read_only: 1, columns: 2 },
					{ fieldname: "item_code", label: __("Item Code"), fieldtype: "Link", options: "Item", in_list_view: 1, read_only: 1, columns: 2 },
					{ fieldname: "item_name", label: __("Item Name"), fieldtype: "Data", in_list_view: 1, read_only: 1, columns: 3 },
					{ fieldname: "batch_no", label: __("Batch No"), fieldtype: "Link", options: "Batch", in_list_view: 1, read_only: 1, columns: 1 },
					{ fieldname: "delivery_note", label: __("Delivery Note"), fieldtype: "Link", options: "Delivery Note", in_list_view: 1, read_only: 1, columns: 1 },
					{ fieldname: "posting_date", label: __("Delivered On"), fieldtype: "Date", in_list_view: 1, read_only: 1, columns: 1 },
					{ fieldname: "sales_order", label: __("Sales Order"), fieldtype: "Link", options: "Sales Order", read_only: 1 },
				],
			},
		],
		primary_action_label: __("Add Selected"),
		primary_action() {
			const selected = (dialog.fields_dict.items.df.data || []).filter((r) => r.__checked);
			if (!selected.length) {
				frappe.msgprint(__("Please select at least one serial number."));
				return;
			}
			const existing = new Set((frm.doc.custom_valves || []).map((r) => r.serial_number).filter(Boolean));
			let added = 0, skipped = 0;
			selected.forEach((s) => {
				if (existing.has(s.serial_no)) { skipped++; return; }
				existing.add(s.serial_no);
				// set values directly so each row is filled once, by the helpers below
				const child = frm.add_child("custom_valves", {
					item_code: s.item_code, serial_number: s.serial_no, batch_no: s.batch_no, sales_order: s.sales_order, qty: 1,
				});
				generate_item.valve.fill_from_item(frm, child.doctype, child.name);
				generate_item.valve.fill_warranty(frm, child.doctype, child.name, { quiet: true });
				added++;
			});
			if (!frm.doc.custom_sales_order) frm.set_value("custom_sales_order", dialog.get_value("sales_order"));
			frm.refresh_field("custom_valves");
			dialog.hide();
			frappe.show_alert({
				message: skipped
					? __("{0} line(s) added, {1} already on this complaint.", [added, skipped])
					: __("{0} line(s) added.", [added]),
				indicator: "green",
			});
		},
	});

	const grid = () => dialog.fields_dict.items.grid;
	const data = () => dialog.fields_dict.items.df.data || [];

	function sync_summary() {
		const total = data().length, selected = data().filter((r) => r.__checked).length;
		const $t = dialog.fields_dict.selection_toolbar.$wrapper;
		$t.find(".selected-count").text(selected);
		$t.find(".total-count").text(total);
		grid().wrapper.find(".grid-heading-row .grid-row-check").prop("checked", total > 0 && selected === total);
	}

	function toggle_all(checked) {
		data().forEach((r) => (r.__checked = checked ? 1 : 0));
		grid().wrapper.find(".grid-row-check").prop("checked", !!checked);
		(grid().grid_rows || []).forEach((gr) => gr.refresh_check && gr.refresh_check());
		sync_summary();
	}

	dialog.fields_dict.selection_toolbar.$wrapper.html(`
		<div class="d-flex justify-content-between align-items-center" style="margin-bottom: var(--margin-sm);">
			<div>
				<button class="btn btn-xs btn-default btn-select-all">${__("Select All")}</button>
				<button class="btn btn-xs btn-default btn-unselect-all" style="margin-left: 6px;">${__("Unselect All")}</button>
			</div>
			<span class="badge badge-light border font-weight-normal py-1 px-2 text-muted">
				<span class="selected-count">0</span> ${__("of")} <span class="total-count">0</span> ${__("selected")}
			</span>
		</div>`);
	dialog.fields_dict.selection_toolbar.$wrapper.find(".btn-select-all").on("click", () => toggle_all(true));
	dialog.fields_dict.selection_toolbar.$wrapper.find(".btn-unselect-all").on("click", () => toggle_all(false));
	grid().wrapper.on("click", ".grid-heading-row .grid-row-check", function () { toggle_all($(this).prop("checked")); });
	grid().wrapper.on("change click", ".grid-body .grid-row-check", function () {
		const name = $(this).parents(".grid-row:first").attr("data-name");
		const gr = name && grid().grid_rows_by_docname && grid().grid_rows_by_docname[name];
		if (gr) gr.doc.__checked = $(this).prop("checked") ? 1 : 0;
		setTimeout(sync_summary, 50);
	});

	// batches of the chosen order, for the Batch filter
	dialog.fields_dict.batch_no.$input.on("focus", () => {
		const so = dialog.get_value("sales_order");
		if (!so || dialog.__batches) return;
		frappe.call({ method: "generate_item.customer_complaint.serial_lookup.get_delivered_batches", args: { sales_order: so } }).then((r) => (dialog.__batches = r.message || []));
	});

	function search() {
		const so = dialog.get_value("sales_order");
		if (!so) {
			frappe.msgprint(__("Please select a Sales Order."));
			return;
		}
		frappe.call({
			method: "generate_item.customer_complaint.serial_lookup.get_delivered_serials",
			args: {
				sales_order: so,
				batch_no: dialog.get_value("batch_no") || null,
				txt: dialog.get_value("txt") || null,
				exclude: (frm.doc.custom_valves || []).map((r) => r.serial_number).filter(Boolean),
			},
			freeze: true,
			callback(r) {
				const res = r.message || { rows: [] };
				dialog.fields_dict.items.df.data = (res.rows || []).map((row) => Object.assign(row, { __checked: 0 }));
				dialog.fields_dict.items.refresh();
				sync_summary();
				if (!res.rows || !res.rows.length) {
					frappe.show_alert({ message: __("No delivered serial numbers found for this search."), indicator: "orange" });
				} else if (res.truncated) {
					frappe.show_alert({ message: __("Showing the first {0} of {1} serials. Narrow the search by Batch or Serial No.", [res.rows.length, res.total]), indicator: "orange" }, 8);
				}
			},
		});
	}

	dialog.fields_dict.search.$input.on("click", search);
	dialog.fields_dict.txt.$input.on("keydown", (e) => { if (e.key === "Enter") search(); });
	dialog.show();
	dialog.fields_dict.search.$wrapper.css("margin-top", "24px");
	dialog.fields_dict.search.$wrapper.find("button").removeClass("btn-default").addClass("btn-primary").html('<i class="fa fa-search" style="margin-right: 4px;"></i>' + __("Search"));
	if (dialog.get_value("sales_order")) search();
};

// Current Order: a Sales Order of another customer is cleared when the customer changes (TASK41458)
generate_item.valve.clear_mismatched_sales_order = function (frm) {
	const so = frm.doc.custom_sales_order;
	if (!so || frm.doc.custom_order_type !== "Current Order") return;
	if (!frm.doc.customer) {
		frm.set_value("custom_sales_order", "");
		return;
	}
	frappe.db.get_value("Sales Order", so, "customer").then((r) => {
		const so_customer = r && r.message && r.message.customer;
		if (so_customer && so_customer !== frm.doc.customer && frm.doc.custom_sales_order === so) {
			frm.set_value("custom_sales_order", "");
			frappe.show_alert({ message: __("Sales Order {0} cleared: it belongs to {1}.", [so, so_customer]), indicator: "orange" });
		}
	});
};
