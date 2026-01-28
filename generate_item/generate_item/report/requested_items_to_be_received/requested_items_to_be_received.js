// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt


let PO_SERIES_OPTIONS = [];
frappe.query_reports["Requested Items To Be Received"] = {

    get_datatable_options(options) {
        options.checkboxColumn = true;
        return options;
    },
    filters: [
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            default: frappe.defaults.get_user_default("Company"),
            reqd: 1,
            on_change: function () {
                frappe.query_report.refresh().then(() => {
                    unchecked_all_checkbox();
                });
            },
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            on_change: function () {
                frappe.query_report.refresh().then(() => {
                    unchecked_all_checkbox();
                });
            },
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            on_change: function () {
                frappe.query_report.refresh().then(() => {
                    unchecked_all_checkbox();
                });
            },
        },
        
        {
            fieldname: "created_by",
            label: __("Created By"),
            fieldtype: "MultiSelectList",
            get_data: function (txt) {
                return frappe.db.get_link_options("User", txt);
            },
            on_change: function () {
                frappe.query_report.refresh().then(() => {
                    unchecked_all_checkbox();
                });
            },
        },
        {
            fieldname: "supplier",
            label: __("Supplier"),
            fieldtype: "Link",
            options: "Supplier",
           
            on_change: function () {
                frappe.query_report.refresh().then(() => {
                    unchecked_all_checkbox();
                });
            },
        },
        {
            fieldname: "item_code",
            label: __("Item"),
            fieldtype: "Link",
            options: "Item",
           
            on_change: function () {
                frappe.query_report.refresh().then(() => {
                    unchecked_all_checkbox();
                });
            },
        },
        {
            fieldname: "purchase_no",
            label: __("Purchase Order"),
            fieldtype: "Link",
            options: "Purchase Order",
           
            on_change: function () {
                frappe.query_report.refresh().then(() => {
                    unchecked_all_checkbox();
                });
            },
        },
        {
            fieldname: "branch",
            label: __("Branch"),
            fieldtype: "Link",
            options: "Branch",
           
            on_change: function () {
                frappe.query_report.refresh().then(() => {
                    unchecked_all_checkbox();
                });
            },
        },
        
       
      
        
        
        
    ],
    onload: function (report) {

         frappe.call({
        method: "generate_item.generate_item.report.requested_items_to_be_received.requested_items_to_be_received.get_pr_naming_series",
        callback: function (r) {
            // console.log("series-------",r)
            if (r.message) {
                
                PO_SERIES_OPTIONS = r.message;
            }
        }
    });
        report.page.add_inner_button(
            __("Past Purchase Receipt History"),
            function () {
                show_past_purchase_history();
            }
        );
    }
    
};



function show_purchase_history_dialog(data) {
    let html = `
        <div style="overflow-x:auto;">
            <table class="table table-bordered table-hover">
                <thead>
                    <tr>
                        <th>Item</th>
                        <th>PR No</th>
                        <th>PR Date</th>
                        <th>Supplier</th>
                        <th class="text-right">Qty</th>
                        <th class="text-right">Rate</th>
                    </tr>
                </thead>
                <tbody>
    `;

    data.forEach(d => {
        html += `
            <tr>
                <td style="white-space:nowrap">${d.item_code}</td>
                <td>
                    <a href="/app/purchase-receipt/${d.po_no}" target="_blank">
                        ${d.po_no}
                    </a>
                </td>
                <td>${frappe.datetime.str_to_user(d.po_date)}</td>
                <td style="max-width:260px; white-space:normal;">
                    ${d.supplier}
                </td>
                <td class="text-right">${d.qty}</td>
                <td class="text-right">${format_currency(d.rate)}</td>
            </tr>
        `;
    });

    html += `
                </tbody>
            </table>
        </div>
    `;

    let dialog = new frappe.ui.Dialog({
        title: __("Last Purchase Receipt History (Approved PR Only)"),
        size: "large",
        fields: [
            {
                fieldtype: "HTML",
                fieldname: "history_html"
            }
        ]
    });

    dialog.fields_dict.history_html.$wrapper.html(html);

    dialog.show();
}

function show_past_purchase_history() {
    const rows = frappe.query_report.get_checked_items() || [];

    if (!rows.length) {
        frappe.msgprint(__("Please select at least one row."));
        return;
    }

    const item_codes = [...new Set(rows.map(r => r.item_code))];

    frappe.call({
        method: "generate_item.generate_item.report.requested_items_to_be_received.requested_items_to_be_received.get_last_purchase_history",
        args: { item_codes },
        callback: function (r) {
            if (r.message && r.message.length) {
                show_purchase_history_dialog(r.message);
            } else {
                frappe.msgprint(__("No purchase receipt history found."));
            }
        }
    });
}



var total_pending_qty = 0;

/* Uncheck all rows */
function unchecked_all_checkbox() {
    if (!frappe.query_report.data) return;
    
    frappe.query_report.data.forEach((row, index) => {
        let node = `.dt-row.dt-row-${index}.vrow`;
        $(node).find("[type='checkbox']").prop("checked", false);
    });
    document.querySelectorAll(".dt-row--highlight").forEach((row) => {
        row.classList.remove("dt-row--highlight");
    });
}

/* Checkbox change listener */
function listner_to_checkbox() {
    if (!frappe.query_report.data) return;
    
    frappe.query_report.data.forEach((row, index) => {
        if (row.name) {
            let node = `.dt-row.dt-row-${index}.vrow`;
            let checkbox = $(node).find("[type='checkbox']");

            checkbox.off('change').on('change', function () {
                if (this.checked) {
                    total_pending_qty += row.pending_qty || 0;
                } else {
                    total_pending_qty -= row.pending_qty || 0;
                }

                if (total_pending_qty < 0) total_pending_qty = 0;
              
            });
        }
    });
}






function group_rows_by_supplier(selected_rows) {
    const grouped = {};

    selected_rows.forEach(row => {
        if (!row.supplier) return;

        if (!grouped[row.supplier]) {
            grouped[row.supplier] = [];
        }
        grouped[row.supplier].push(row);
    });

    return grouped;
}




function create_purchase_receipt_by_supplier() {
    const selected_rows = frappe.query_report.get_checked_items() || [];

    if (!selected_rows.length) {
        frappe.msgprint(__("Please select at least one row to create purchase receipt."));
        return;
    }

    const grouped_by_supplier = group_rows_by_supplier(selected_rows);

    if (!Object.keys(grouped_by_supplier).length) {
        frappe.msgprint(__("Selected rows do not have supplier."));
        return;
    }

    const supplier_count = Object.keys(grouped_by_supplier).length;

    frappe.confirm(
        __(`This will create ${supplier_count} Purchase Receipt(s). Continue?`),
        function () {

            frappe.prompt(
                [
                    {
                        fieldname: "pr_series",
                        fieldtype: "Select",
                        label: __("PR Series"),
                        options: PO_SERIES_OPTIONS.join("\n"),
                        reqd: 1
                    },
                    {
                        fieldname: "branch",
                        fieldtype: "Link",
                        label: __("Branch"),
                        options: "Branch",
                        reqd: 1
                    }
                ],
                function (values) {
                    call_create_po(
                        grouped_by_supplier,
                        values.pr_series,
                        values.branch
                    );
                }
            );
        }
    );

    function call_create_po(grouped_by_supplier, pr_series, branch) {

        frappe.call({
            method: "generate_item.generate_item.report.requested_items_to_be_received.requested_items_to_be_received.create_purchase_receipt_by_supplier",
            args: {
                "grouped_items": grouped_by_supplier,
                "company": frappe.query_report.get_filter_value("company"),
                "pr_series": pr_series,
                "branch": branch
            },
            freeze: true,
            freeze_message: __("Creating Purchase Receipt..."),
            callback: function (r) {
                if (r.message) {
                    console.log("res----------naming series",r.message)
                    let message = __("Purchase Receipt created successfully:") + "<br><br>";

                    r.message.forEach(pr => {
                        message += `
                            <a href="/app/purchase-receipt/${pr.name}" target="_blank">
                                ${pr.name}
                            </a> (${pr.supplier})<br>
                        `;
                    });

                    frappe.msgprint({
                        title: __("Success"),
                        indicator: "green",
                        message: message
                    });

                    frappe.query_report.refresh();
                }
            }
        });
    }
}



function select_rows_with_supplier(checked) {
    total_pending_qty = 0;

    frappe.query_report.data.forEach((row, index) => {
        let node = `.dt-row.dt-row-${index}.vrow`;
        let checkbox = $(node).find("[type='checkbox']");

        checkbox.prop("checked", false);
        
    });
}

function bind_header_checkbox() {
    let header_checkbox = $(".dt-cell__content.dt-cell__content--header-0")
        .find("[type='checkbox']");

    header_checkbox.off("change").on("change", function () {
        select_rows_with_supplier(this.checked);
    });
}


$(function () {
    // footer element to show total line count below the report
    let $total_footer = $('<div class="report-footer-total-lines" style="margin-top: 8px; font-weight: bold;"></div>');
    $('.layout-main-section').append($total_footer);

    // Add action button
    frappe.query_report.page.add_action_item('Create Purchase Receipt', function () {
        create_purchase_receipt_by_supplier();
    }, __("Action"));

    // Periodically update checkbox states and listeners
    setInterval(function () {
        try {
            if (frappe.query_report && frappe.query_report.data) {
                bind_header_checkbox();     // 👈 THIS LINE IS IMPORTANT
                listner_to_checkbox();

                // update total line count below the report
                const total_rows = frappe.query_report.data.length || 0;
                $total_footer.text(__("Total Lines: {0}", [total_rows]));
            }
        } catch (error) {
            console.log(error);
        }
    }, 300);
    
    
    // Remove chart if not needed
    if (frappe.query_report.$chart) {
        frappe.query_report.$chart.remove();
    }
});


