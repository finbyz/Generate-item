frappe.ui.form.on("User", {
	refresh(frm) {
		if (frm.is_new()) return;

		// Option 2: Button on User form to trigger the same functionality
		frm.add_custom_button(__("Create General Employee"), function () {
			open_general_employee_dialog(frm.doc.name, frm.doc.full_name);
		});
	},

	before_save(frm) {
		if (frm.is_new()) {
			frm.__is_new_user = true;
		}
	},

	after_save(frm) {
		// Option 1: Automatic popup when a new User is created & saved
		if (frm.__is_new_user) {
			delete frm.__is_new_user;
			const user_name = frm.doc.name;
			const full_name = frm.doc.full_name;
			setTimeout(function () {
				open_general_employee_dialog(user_name, full_name);
			}, 500);
		}
	},
});

function open_general_employee_dialog(user_name, full_name) {
	frappe.call({
		method: "generate_item.utils.user.check_general_employee_exists",
		args: { user: user_name },
		callback: function (r) {
			const info = r.message || {};
			show_general_employee_dialog(user_name, full_name, info);
		},
	});
}

function show_general_employee_dialog(user_name, full_name, info) {
	const user_display = info.employee_name || full_name || user_name;
	const initial_has_wh = Boolean(info.has_warehouse_permission);

	const dialog = new frappe.ui.Dialog({
		title: __("Create General Employee"),
		fields: [
			{
				fieldname: "info_html",
				fieldtype: "HTML",
				options: `<div class="text-muted" style="margin-bottom: 12px;">
					Configure <b>General Employee</b> and User Permissions for User: <b>${frappe.utils.escape_html(user_display)}</b>
				</div>`,
			},
			{
				label: __("Branch"),
				fieldname: "branch",
				fieldtype: "Link",
				options: "Branch",
				reqd: 1,
				default: info.branch || "",
				onchange: function () {
					const new_branch = dialog.get_value("branch");
					const current_wh = dialog.get_value("warehouse");
					if (current_wh) {
						if (!new_branch) {
							dialog.set_value("warehouse", "");
						} else {
							frappe.db.get_value("Warehouse", current_wh, "branch").then((res) => {
								if (res && res.message && res.message.branch !== new_branch) {
									dialog.set_value("warehouse", "");
								}
							});
						}
					}
				},
			},
			{
				label: __("Create User Permission with Branch"),
				fieldname: "create_user_permission_branch",
				fieldtype: "Check",
				default: info.has_branch_permission ? 1 : 0,
			},
			{
				label: __("Create User Permission with Warehouse"),
				fieldname: "create_user_permission_warehouse",
				fieldtype: "Check",
				default: initial_has_wh ? 1 : 0,
				onchange: function () {
					const show_wh = Boolean(
						dialog.get_value("create_user_permission_warehouse")
					);
					dialog.set_df_property("warehouse", "hidden", show_wh ? 0 : 1);
					dialog.set_df_property("warehouse", "reqd", show_wh ? 1 : 0);
					if (!show_wh) {
						dialog.set_value("warehouse", "");
					}
				},
			},
			{
				label: __("Warehouse"),
				fieldname: "warehouse",
				fieldtype: "Link",
				options: "Warehouse",
				hidden: initial_has_wh ? 0 : 1,
				reqd: initial_has_wh ? 1 : 0,
				default: info.warehouse || "",
			},
		],
		primary_action_label: __("Create"),
		primary_action(values) {
			if (!values.branch) {
				frappe.msgprint({
					message: __("Please select a Branch."),
					indicator: "orange",
				});
				return;
			}

			if (values.create_user_permission_warehouse && !values.warehouse) {
				frappe.msgprint({
					message: __("Please select a Warehouse for the Warehouse Permission."),
					indicator: "orange",
				});
				return;
			}

			dialog.hide();

			frappe.call({
				method: "generate_item.utils.user.create_general_employee_and_permissions",
				args: {
					user: user_name,
					branch: values.branch,
					create_permission_branch: values.create_user_permission_branch || false,
					create_permission_warehouse: values.create_user_permission_warehouse || false,
					warehouse: values.warehouse || null,
				},
				freeze: true,
				freeze_message: __("Processing General Employee and User Permissions..."),
				callback: function (res) {
					if (res.message) {
						frappe.show_alert(
							{
								message: __(
									"General Employee and selected User Permissions updated successfully."
								),
								indicator: "green",
							},
							7
						);
						if (cur_frm && cur_frm.doc && cur_frm.doc.name === user_name) {
							cur_frm.reload_doc();
						}
					}
				},
			});
		},
	});

	// Setup dynamic link query for Warehouse filtered by selected Branch
	const wh_query = function () {
		const selected_branch = dialog.get_value("branch") || "";
		return {
			filters: {
				branch: selected_branch,
				is_group: 0,
				disabled: 0,
			},
		};
	};
	dialog.set_query("warehouse", wh_query);
	if (dialog.fields_dict.warehouse) {
		dialog.fields_dict.warehouse.get_query = wh_query;
	}

	dialog.show();
}