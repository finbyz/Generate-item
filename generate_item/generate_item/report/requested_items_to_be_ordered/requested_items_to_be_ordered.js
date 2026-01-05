

let PO_SERIES_OPTIONS = [];
frappe.query_reports["Requested Items To Be Ordered"] = {

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
            fieldname: "status",
            label: __("Status"),
            fieldtype: "Select",
            options: "\nPending\nPartially Ordered\nSubmitted\nStopped\nCancelled\nReceived\nIssued\nTransferred\nPartially Received",
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
            fieldname: "drawing_no",
            label: __("Drawing Number"),
            fieldtype: "Data",
            on_change: function () {
                frappe.query_report.refresh().then(() => {
                    unchecked_all_checkbox();
                });
            },
        },
        {
            fieldname: "drawing_rev_no",
            label: __("Drawing Rev No"),
            fieldtype: "Data",
            on_change: function () {
                frappe.query_report.refresh().then(() => {
                    unchecked_all_checkbox();
                });
            },
        },
      
        
        
        
    ],
    onload: function (report) {

         frappe.call({
        method: "generate_item.generate_item.report.requested_items_to_be_ordered.requested_items_to_be_ordered.get_po_naming_series",
        callback: function (r) {
            // console.log("series-------",r)
            if (r.message) {
                
                PO_SERIES_OPTIONS = r.message;
            }
        }
    });
        report.page.add_inner_button(
            __("Past Purchase History"),
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
                        <th>PO No</th>
                        <th>PO Date</th>
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
                    <a href="/app/purchase-order/${d.po_no}" target="_blank">
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
        title: __("Last Purchase History (Approved PO Only)"),
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
        method: "generate_item.generate_item.report.requested_items_to_be_ordered.requested_items_to_be_ordered.get_last_purchase_history",
        args: { item_codes },
        callback: function (r) {
            if (r.message && r.message.length) {
                show_purchase_history_dialog(r.message);
            } else {
                frappe.msgprint(__("No purchase history found."));
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
        let supplier = row.party_type || "__NO_SUPPLIER__";

        if (!grouped[supplier]) {
            grouped[supplier] = [];
        }
        grouped[supplier].push(row);
    });

    return grouped;
}


/* Create Purchase order grouped by supplier */
function create_purchase_order_by_supplier() {
    const selected_rows = frappe.query_report.get_checked_items() || [];
	// console.log("selected row -----",selected_rows)
    
    if (selected_rows.length === 0) {
        frappe.msgprint(__("Please select at least one row to create purchase order."));
        return;
    }

    // Group rows by supplier
    const grouped_by_supplier = group_rows_by_supplier(selected_rows);
	console.log("grouped by supplier---",grouped_by_supplier)
    
    if (Object.keys(grouped_by_supplier).length === 0) {
        frappe.msgprint(__("No rows with supplier found. Please select rows that have supplier assigned."));
        return;
    }

    // Show confirmation dialog
    const supplier_count = Object.keys(grouped_by_supplier).length;
    const item_count = selected_rows.length;

    
    frappe.confirm(
        __(`This will create ${supplier_count} Purchase Order(s)  Continue?`),
        function() {
            // User clicked Yes
            let supplier = null;

            if (grouped_by_supplier["__NO_SUPPLIER__"]) {
                frappe.prompt(
                    [
                        {
                            fieldname: "supplier",
                            fieldtype: "Link",
                            options: "Supplier",
                            label: __("Select Supplier"),
                            reqd: 1
                        },
                        {
                            fieldname: "po_series",
                            fieldtype: "Select",
                            label: __("PO Series"),
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
                        supplier = values.supplier;

                        // call_create_po(grouped_by_supplier);
                        let no_supplier_rows = grouped_by_supplier["__NO_SUPPLIER__"] || [];

                        if (!grouped_by_supplier[supplier]) {
                            grouped_by_supplier[supplier] = [];
                        }

                        // MERGE rows
                        grouped_by_supplier[supplier] =
                            grouped_by_supplier[supplier].concat(no_supplier_rows);

                        // REMOVE placeholder group
                        delete grouped_by_supplier["__NO_SUPPLIER__"];

                        call_create_po(grouped_by_supplier ,values.po_series, values.branch);

                    }
                );
                return;
            }

            call_create_po(grouped_by_supplier);

            function call_create_po(grouped_by_supplier, po_series=null, branch=null) {

                if (!po_series) {
                    frappe.msgprint(__("Please select PO Series"));
                    return;
                }
                
                if (!branch) {
                    frappe.msgprint(__("Please select Branch"));
                    return;
                }
                frappe.call({
                    method: 'generate_item.generate_item.report.requested_items_to_be_ordered.requested_items_to_be_ordered.create_purchase_order_by_supplier',
                    args: {
                        "grouped_items": grouped_by_supplier,
                        "company": frappe.query_report.get_filter_value("company"),
                        "po_series": po_series ,
                        "branch": branch 
                    },
                    freeze: true,
                    freeze_message: __("Creating Purchase Order..."),
                    callback: function (r) {
                        if (r.message) {
                            console.log("Purchase Order created:", r.message);
                            
                            // Show success message with links
                            let message = __("Purchase Order created successfully:") + "<br><br>";
							r.message.forEach(invoice => {
								message += `<a href="/app/purchase-order/${invoice.name}" target="_blank">${invoice.name}</a> (${invoice.supplier})<br>`;
                            });
                            
                            frappe.msgprint({
                                title: __('Success'),
                                indicator: 'green',
                                message: message
                            });
                            
                            // Refresh the report
                            frappe.query_report.refresh();
                        }
                    },
                    error: function(r) {
                        frappe.msgprint(__("Error creating purchase order. Please check the error log."));
                    }
                });
            }
            

          
        }
    );
}


function select_rows_with_supplier(checked) {
    total_pending_qty = 0;

    frappe.query_report.data.forEach((row, index) => {
        let node = `.dt-row.dt-row-${index}.vrow`;
        let checkbox = $(node).find("[type='checkbox']");

        if (checked && row.party_type && row.pending_qty > 0) {
            checkbox.prop("checked", true);
            total_pending_qty += row.pending_qty || 0;
        } else {
            checkbox.prop("checked", false);
        }
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
    frappe.query_report.page.add_action_item('Create Purchase Order', function () {
        create_purchase_order_by_supplier();
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


