// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt

frappe.dom.set_style(`
.select-wrapper { width: 100%; }
.custom-select {
    width: 100%;
    border: none !important;
    outline: none;
    background: transparent;
    font-size: 13px;
    padding: 4px 6px;
    cursor: pointer;
    appearance: none;
    -webkit-appearance: none;
    -moz-appearance: none;
}
.custom-select:hover { background-color: #f8fafc; }
.custom-select:focus { background-color: #eef2ff; }
.dt-cell__content { display: flex; align-items: center; }
`);

frappe.query_reports["Serial Number Register"] = {
    filters: [
        {
            fieldname: "sales_order",
            label: "Sales Order",
            fieldtype: "Link",
            options: "Sales Order"
        },
        {
            fieldname: "customer",
            label: "Customer",
            fieldtype: "Link",
            options: "Customer"
        },
        {
            fieldname: "branch",
            label: "Branch",
            fieldtype: "Link",
            options: "Branch",
            mandatory: 1,
        },
        {
            fieldname: "batch",
            label: "Batch",
            fieldtype: "Link",
            options: "Batch",
            on_change: function(report) {
                let batch = report.get_filter_value("batch");

                if (!batch) {
                    window.mfg_options = [];
                    window.api_options = [];
                    _update_filter_options(report, [], []);
                    // Refresh report even on clear so stale data is removed
                    report.refresh();
                    return;
                }

                frappe.call({
                    method: "generate_item.generate_item.report.serial_number_register.serial_number_register.get_serial_number_options",
                    callback: function(r) {
                        window.mfg_options = r.message.mfg_type || [];
                        window.api_options = r.message.api_monogram_req || [];
                        _update_filter_options(report, window.mfg_options, window.api_options);
                        //   Auto-refresh report after batch is selected & options loaded
                        report.refresh();
                    }
                });
            }
        },
        // {
        //     fieldname: "mfg_type",
        //     label: "MFG Type",
        //     fieldtype: "Select",
        //     options: [""]
        // },
        // {
        //     fieldname: "api_monogram_req",
        //     label: "API Monogram Req",
        //     fieldtype: "Select",
        //     options: [""]
        // }
    ],

    onload: function(report) {
        frappe.call({
            method: "generate_item.generate_item.report.serial_number_register.serial_number_register.get_serial_number_options",
            callback: function(r) {
                window.mfg_options = r.message.mfg_type || [];
                window.api_options = r.message.api_monogram_req || [];
                _update_filter_options(report, window.mfg_options, window.api_options);
            }
        });

        report.page.add_inner_button("Save Changes", () => {
            save_changes(report);
        });

        report.page.add_inner_button("Bulk Update by Batch", () => {
            bulk_update_by_batch(report);
        });
    },

    formatter: function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (column.fieldname === "mfg_type") {
            let options = (window.mfg_options || []).map(opt =>
                `<option value="${opt}" ${data.mfg_type == opt ? "selected" : ""}>${opt}</option>`
            ).join("");
            return `<select class="mfg_type custom-select" data-serial="${data.serial_no}">
                <option value="">Select</option>
                ${options}
            </select>`;
        }

        if (column.fieldname === "api_monogram_req") {
            let options = (window.api_options || []).map(opt =>
                `<option value="${opt}" ${data.api_monogram_req == opt ? "selected" : ""}>${opt}</option>`
            ).join("");
            return `<select class="api_monogram custom-select" data-serial="${data.serial_no}">
                <option value="">Select</option>
                ${options}
            </select>`;
        }

        return value;
    }
};


// ─── Helper: update Select filter options at runtime ──────────────────────
function _update_filter_options(report, mfg_opts, api_opts) {
    let mfg_filter = report.get_filter("mfg_type");
    if (mfg_filter) {
        let mfg_select = mfg_filter.$input[0];
        let current_mfg = mfg_filter.get_value();
        mfg_select.innerHTML = `<option value="">Select</option>` +
            mfg_opts.map(o => `<option value="${o}" ${o == current_mfg ? "selected" : ""}>${o}</option>`).join("");
    }

    let api_filter = report.get_filter("api_monogram_req");
    if (api_filter) {
        let api_select = api_filter.$input[0];
        let current_api = api_filter.get_value();
        api_select.innerHTML = `<option value="">Select</option>` +
            api_opts.map(o => `<option value="${o}" ${o == current_api ? "selected" : ""}>${o}</option>`).join("");
    }
}


// ─── Save Changes (row-level selects) ─────────────────────────────────────
function save_changes(report) {
    let updates = [];

    document.querySelectorAll(".mfg_type").forEach(el => {
        let serial = el.dataset.serial;
        let mfg_type = el.value;
        let api_val = document.querySelector(`.api_monogram[data-serial="${serial}"]`)?.value;

        if (mfg_type || api_val) {
            updates.push({ serial_number: serial, mfg_type, api_monogram_req: api_val });
        }
    });

    if (!updates.length) {
        frappe.msgprint("No changes to update");
        return;
    }

    frappe.call({
        method: "generate_item.generate_item.report.serial_number_register.serial_number_register.update_serial_numbers",
        args: { updates },
        callback: function() {
            frappe.msgprint("Updated Successfully");
            report.refresh();
        }
    });
}


// ─── Bulk Update by Batch ─────────────────────────────────────────────────
function bulk_update_by_batch(report) {

    //  Read currently selected batch from filter
    let selected_batch = report.get_filter_value("batch") || "";

    let mfg_opts = (window.mfg_options || []);
    let api_opts = (window.api_options || []);

    let dialog = new frappe.ui.Dialog({
        title: "Bulk Update Serial Numbers by Batch",
        fields: [
            {
                fieldname: "info",
                fieldtype: "HTML",
                options: `<p class="text-muted" style="margin-bottom:8px;">
                    This will apply to <b>all serial numbers</b> in the selected batch.
                    Leave a field as <b>blank</b> to skip updating it.
                </p>`
            },
            {
                // Batch field pre-filled with filter value
                fieldname: "batch",
                label: "Batch",
                fieldtype: "Link",
                options: "Batch",
                default: selected_batch,         
                reqd: 1,
                description: "Change batch here to update a different batch than the filter",
                onchange: function() {
                    // When user changes batch in dialog, reload the mfg/api options
                    let new_batch = dialog.get_value("batch");
                    if (!new_batch) return;

                    frappe.call({
                        method: "generate_item.generate_item.report.serial_number_register.serial_number_register.get_serial_number_options",
                        callback: function(r) {
                            let new_mfg  = r.message.mfg_type || [];
                            let new_api  = r.message.api_monogram_req || [];

                            // Rebuild mfg_type select options
                            dialog.set_df_property("mfg_type", "options", ["", ...new_mfg].join("\n"));
                            dialog.refresh_field("mfg_type");

                            // Rebuild api_monogram_req select options
                            dialog.set_df_property("api_monogram_req", "options", ["", ...new_api].join("\n"));
                            dialog.refresh_field("api_monogram_req");
                        }
                    });
                }
            },
            {
                fieldname: "mfg_type",
                label: "MFG Type",
                fieldtype: "Select",
                options: ["", ...mfg_opts].join("\n")
            },
            {
                fieldname: "api_monogram_req",
                label: "API Monogram Req",
                fieldtype: "Select",
                options: ["", ...api_opts].join("\n")
            }
        ],
        primary_action_label: "Apply to All",
        primary_action: function(values) {
            if (!values.batch) {
                frappe.msgprint("Please select a Batch.");
                return;
            }
            if (!values.mfg_type && !values.api_monogram_req) {
                frappe.msgprint("Please select at least one field to update.");
                return;
            }

            frappe.confirm(
                `This will update <b>all serial numbers</b> in batch <b>${values.batch}</b>. Proceed?`,
                function() {
                    frappe.call({
                        method: "generate_item.generate_item.report.serial_number_register.serial_number_register.bulk_update_by_batch",
                        args: {
                            batch: values.batch,
                            mfg_type: values.mfg_type || null,
                            api_monogram_req: values.api_monogram_req || null
                        },
                        callback: function(r) {
                            frappe.msgprint(r.message || "Bulk update successful.");
                            dialog.hide();
                            report.refresh();
                        }
                    });
                }
            );
        }
    });

    dialog.show();
}