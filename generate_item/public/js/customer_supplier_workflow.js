// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt
const CS_WF = {
	STATUS_DRAFT: "Draft",
	STATUS_PENDING_L1: "Pending L1 Approval",
	STATUS_PENDING_FINAL: "Pending Final Approval",
	STATUS_APPROVED: "Approved",
	METHOD_PREFIX: "generate_item.utils.customer_supplier_workflow",
};

const CS_WF_INDICATOR_COLORS = {
	[CS_WF.STATUS_DRAFT]: "gray",
	[CS_WF.STATUS_PENDING_L1]: "orange",
	[CS_WF.STATUS_PENDING_FINAL]: "blue",
	[CS_WF.STATUS_APPROVED]: "green",
};

// Form hooks

frappe.ui.form.on("Customer", {
	refresh(frm) { _apply_cs_approval_control(frm); },
});

frappe.ui.form.on("Supplier", {
	refresh(frm) { _apply_cs_approval_control(frm); },
});

// Core controller

function _apply_cs_approval_control(frm) {
	_clear_cs_approval_buttons(frm);

	if (frm.is_new()) return;

	// Immediately set the indicator to prevent Frappe from showing "Disabled"
	// while we wait for the backend approval control payload.
	if (frm.doc.cs_approval_status) {
		_set_cs_form_indicator(frm, frm.doc.cs_approval_status);
	}

	// Use onload data once; later refreshes must fetch fresh control state.
	const onload = frm.doc.__onload && frm.doc.__onload.cs_approval_control;
	if (onload && !frm.__cs_onload_control_rendered) {
		frm.__cs_onload_control_rendered = true;
		_render_control(frm, onload);
		return;
	}

	// Track request id so stale responses from previous refreshes are ignored
	frm.__cs_req = (frm.__cs_req || 0) + 1;
	const req_id = frm.__cs_req;

	frappe.call({
		method: `${CS_WF.METHOD_PREFIX}.get_approval_control`,
		args: { doctype: frm.doctype, docname: frm.docname },
		callback(r) {
			if (frm.__cs_req !== req_id) return;
			_render_control(frm, r.message || {});
		},
	});
}

function _render_control(frm, control) {
	if (!control || !control.enabled) return;
	_set_cs_form_indicator(frm, control.current_status || frm.doc.cs_approval_status);
	if (control.no_rule) return;

	if (control.can_submit_for_l1) {
		_add_action_btn(frm, __("Submit for Approval"), "submit_for_l1_approval",
			__("Submit this record for L1 Approval?"));
	}
	if (control.can_l1_approve) {
		_add_action_btn(frm, __("L1 Approve"), "l1_approve",
			__("Confirm L1 Approval?"));
	}
	if (control.can_final_approve) {
		_add_action_btn(frm, __("Final Approve"), "final_approve",
			__("Confirm Final Approval? This will activate the record."));
	}
}

// Helpers

function _set_cs_form_indicator(frm, status) {
	if (!status) return;
	frm.page.set_indicator(__(status), CS_WF_INDICATOR_COLORS[status] || "gray");
}

function _clear_cs_approval_buttons(frm) {
	[
		__("Submit for Approval"),
		__("L1 Approve"),
		__("Final Approve"),
	].forEach((label) => frm.remove_custom_button(label, __("Approval")));
}

function _add_action_btn(frm, label, method_name, confirm_msg) {
	frm.page.add_inner_button(label, () => {
		frappe.confirm(confirm_msg, () => {
			frappe.call({
				method: `${CS_WF.METHOD_PREFIX}.${method_name}`,
				args: { doctype: frm.doctype, docname: frm.docname },
				freeze: true,
				freeze_message: __("Processing..."),
				callback(r) {
					if (r.message && r.message.new_status) {
						frappe.show_alert({
							message: __("Status updated to: {0}", [__(r.message.new_status)]),
							indicator: "green",
						}, 5);
						frm.reload_doc();
					}
				},
			});
		});
	}, __("Approval"));
}
