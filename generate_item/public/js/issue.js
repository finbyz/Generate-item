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
