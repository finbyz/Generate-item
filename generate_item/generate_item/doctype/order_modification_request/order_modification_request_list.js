frappe.listview_settings["Order Modification Request"] = {
    onload: function (listview) {
        listview.page.add_action_item(__("Send Pending Notification"), function () {
            const selected = listview.get_checked_items();

            if (!selected.length) {
                frappe.msgprint(__("Please select at least one Order Modification Request."));
                return;
            }

            const docnames = selected.map((d) => d.name);

            frappe.confirm(
                __("Send pending workflow notifications for {0} selected record(s)?", [docnames.length]),
                () => {
                    frappe.call({
                        method: "workflow_transitions.workflow_transitions.doctype.workflow_email.workflow_email.send_pending_notification",
                        args: { docnames },
                        freeze: true,
                        freeze_message: __("Sending pending notifications..."),
                        callback: function (r) {
                            if (!r.message) return;
                            const { sent, already_sent, in_progress, failed } = r.message;
                            frappe.msgprint({
                                title: __("Send Pending Notification - Result"),
                                indicator: failed.length ? "orange" : "green",
                                message: `
                                    ${__("Sent")}: ${sent.length}${sent.length ? "<br>" + sent.join("<br>") : ""}<br><br>
                                    ${__("Already Sent")}: ${already_sent.length}${already_sent.length ? "<br>" + already_sent.join("<br>") : ""}<br><br>
                                    ${in_progress.length ? __("In Queue / Sending") + ": " + in_progress.length + "<br>" + in_progress.join("<br>") + "<br><br>" : ""}
                                    ${failed.length ? __("Failed") + ": " + failed.length + "<br>" + failed.join("<br>") : ""}
                                `,
                            });
                            listview.refresh();
                        },
                    });
                }
            );
        });
    },
};