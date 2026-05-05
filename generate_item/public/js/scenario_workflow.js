frappe.ui.form.on("Stock Entry", {
	refresh(frm) {
        console.log("refresh SE using custom workflow")
		apply_scenario_submit_control(frm);
	},
});

frappe.ui.form.on("Material Request", {
	refresh(frm) {
        console.log("refresh MR using custom workflow")
		apply_scenario_submit_control(frm);
	},
});

function apply_scenario_submit_control(frm) {
	if (!should_control_submit_action(frm)) {
		return;
	}

	const onload_control = frm.doc.__onload && frm.doc.__onload.scenario_submit_control;
	if (onload_control) {
		apply_submit_control_result(frm, onload_control);
		return;
	}

	hide_submit_action(frm);

	frm.__scenario_submit_control_request_id = (frm.__scenario_submit_control_request_id || 0) + 1;
	const request_id = frm.__scenario_submit_control_request_id;

	frappe.call({
		method: "generate_item.utils.scenario_workflow.get_submit_control",
		args: {
			doc: frm.doc,
		},
		callback(r) {
			if (frm.__scenario_submit_control_request_id !== request_id) {
				return;
			}

			apply_submit_control_result(frm, r.message || {});
		},
		error() {
			if (frm.__scenario_submit_control_request_id === request_id) {
				restore_submit_action(frm);
			}
		},
	});
}

function should_control_submit_action(frm) {
	return (
		!frm.is_new() &&
		frm.doc.docstatus === 0 &&
		frm.toolbar &&
		frm.toolbar.get_action_status &&
		frm.toolbar.get_action_status() === "Submit"
	);
}

function apply_submit_control_result(frm, control) {
	if (control.hide_submit) {
		hide_submit_action(frm);
	} else {
		restore_submit_action(frm);
	}
}

function hide_submit_action(frm) {
	frm.page.clear_primary_action();
}

function restore_submit_action(frm) {
	if (frm.toolbar && frm.toolbar.set_primary_action) {
		frm.toolbar.set_primary_action();
	}
}
