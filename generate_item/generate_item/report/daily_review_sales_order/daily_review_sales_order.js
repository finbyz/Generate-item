frappe.query_reports["Daily Review Sales Order"] = {

    // ─── FILTERS ─────────────────────────────────────────────────────────────
    filters: [
        {
            fieldname: "company",
            label:     __("Company"),
            fieldtype: "Link",
            options:   "Company",
            default:   frappe.defaults.get_user_default("Company"),
        },
        {
            fieldname: "branch",
            label:     __("Branch"),
            fieldtype: "Link",
            options:   "Branch",
        },
        {
            fieldname: "from_date",
            label:     __("From Date"),
            fieldtype: "Date",
            default:   frappe.datetime.month_start(),
        },
        {
            fieldname: "to_date",
            label:     __("To Date"),
            fieldtype: "Date",
            default:   frappe.datetime.month_end(),
        },
        {
            fieldname: "customer",
            label:     __("Customer"),
            fieldtype: "Link",
            options:   "Customer",
        },
        {
            fieldname: "sales_order",
            label:     __("Sales Order"),
            fieldtype: "Link",
            options:   "Sales Order",
        },
        {
            fieldname: "batch_no",
            label:     __("Batch No"),
            fieldtype: "Link",
            options:   "Batch",
        },
        {
            fieldname: "order_status",
            label:     __("Order Status"),
            fieldtype: "Select",
            options:   "\nDraft\nOn Hold\nTo Deliver and Bill\nTo Bill\nTo Deliver\nCompleted\nCancelled\nClosed",
        },
        {
            fieldname: "mfg_type",
            label:     __("Mfg Type"),
            fieldtype: "Select",
            options:   "\nIN-HOUSE\nOUTSOURCE",
        },
        
        {
            fieldname: "gad_status",
            label:     __("GAD Status"),
            fieldtype: "Select",
            options:   "\nSSV STD GAD\nNO\nNA\nApproved\nSubmitted\nInprocess",
        },
    ],

    _sn_meta:      null,
    _pending_save: {},

    onload(report) {
        const me = frappe.query_reports["Daily Review Sales Order"];
        me._report = report;

        frappe.call({
            method: "generate_item.generate_item.report.daily_review_sales_order.daily_review_sales_order.get_sn_field_meta",
            callback(r) {
                if (r.message) {
                    me._sn_meta = r.message;
                }
            },
        });

        report.$report.on("click", ".dt-cell", function (e) {
            me._on_cell_click(e, $(this));
        });
    },

    _on_cell_click(e, $cell) {
        const me = frappe.query_reports["Daily Review Sales Order"];
        if (!me._sn_meta) return;

        const col_idx = parseInt($cell.attr("data-col-index"), 10);
        const row_idx = parseInt($cell.attr("data-row-index"), 10);

        const report = me._report;
        
        // FIX: Use datatable instance to get the correct column object
        // This handles hidden columns correctly.
        const col = report.datatable.getColumn(col_idx);

        if (!col || !col.editable) return;
        if ($cell.find(".inline-editor").length) return;

        const row_data = report.data[row_idx];
        if (!row_data) return;

        const sn_name   = row_data.sn_name;
        const batch_key = row_data.batch_key;
        if (!sn_name && !batch_key) return;

        // Use col.id (which is the fieldname in DataTable)
        const fieldname = col.id; 
        const meta      = me._sn_meta[fieldname];
        
        if (!meta) {
            console.error("Metadata not found for field:", fieldname);
            return;
        }

        const cur_value = row_data[fieldname] || "";

        me._render_editor($cell, meta, cur_value, (new_value) => {
            me._save_cell(row_data, row_idx, fieldname, new_value, batch_key, sn_name);
        });
    },

    _render_editor($cell, meta, cur_value, on_save) {
        const me = frappe.query_reports["Daily Review Sales Order"];
        $cell.css("position", "relative");

        let $editor;

        if (meta.fieldtype === "Select") {
            // Fix: handle potential undefined options and prevent empty strings causing issues
            const options_array = (meta.options || "").split("\n");
            const opts = options_array
                .map(o => `<option value="${frappe.utils.escape_html(o)}"${o === cur_value ? " selected" : ""}>${o || "--"}</option>`)
                .join("");

            $editor = $(`
                <select class="inline-editor" style="
                    position:absolute; top:0; left:0; width:100%; height:100%;
                    z-index:100; font-size:12px; border:2px solid var(--primary);
                    background:var(--card-bg); color:var(--text-color); padding:2px;
                ">
                    ${opts}
                </select>
            `);

            $editor.on("change", function () {
                on_save($(this).val());
                $editor.remove();
            });

            $editor.on("keydown", function (e) {
                if (e.key === "Escape") $editor.remove();
            });

        } else if (meta.fieldtype === "Date") {
            $editor = $(`
                <input type="date" class="inline-editor" value="${cur_value || ""}"
                    style="
                        position:absolute; top:0; left:0; width:100%; height:100%;
                        z-index:100; font-size:12px; border:2px solid var(--primary);
                        background:var(--card-bg); color:var(--text-color); padding:2px;
                    "
                />
            `);

            $editor.on("change", function () {
                on_save($(this).val());
                $editor.remove();
            });

            $editor.on("keydown", function (e) {
                if (e.key === "Escape") $editor.remove();
            });

        } else {
            $editor = $(`
                <input type="text" class="inline-editor" value="${frappe.utils.escape_html(cur_value)}"
                    style="
                        position:absolute; top:0; left:0; width:100%; height:100%;
                        z-index:100; font-size:12px; border:2px solid var(--primary);
                        background:var(--card-bg); color:var(--text-color); padding:2px;
                    "
                />
            `);

            $editor.on("blur", function () {
                const val = $(this).val().trim();
                if (val !== cur_value) on_save(val);
                $editor.remove();
            });

            $editor.on("keydown", function (e) {
                if (e.key === "Enter") { $(this).blur(); }
                if (e.key === "Escape") $editor.remove();
            });
        }

        $cell.append($editor);
        $editor.focus();
    },

    _save_cell(row_data, row_idx, fieldname, new_value, batch_key, sn_name) {
        const me = frappe.query_reports["Daily Review Sales Order"];
        const debounce_key = `${sn_name}::${fieldname}`;
        if (me._pending_save[debounce_key]) {
            clearTimeout(me._pending_save[debounce_key].timer);
        }

        me._pending_save[debounce_key] = {
            timer: setTimeout(() => {
                delete me._pending_save[debounce_key];
                me._do_save(row_data, row_idx, fieldname, new_value, batch_key, sn_name);
            }, 300),
        };
    },

    _do_save(row_data, row_idx, fieldname, new_value, batch_key, sn_name) {
        const me = frappe.query_reports["Daily Review Sales Order"];
        const propagate = !me._shift_held;

        row_data[fieldname] = new_value;
        me._report.refresh();

        frappe.call({
            method: "generate_item.generate_item.report.daily_review_sales_order.daily_review_sales_order.row_update_and_propagate",
            args: {
                sn_name:            sn_name,
                fieldname:          fieldname,
                value:              new_value,
                propagate_to_batch: propagate ? 1 : 0,
            },
            freeze: false,
            callback(r) {
                if (!r.exc && r.message) {
                    const msg = propagate
                        ? __("{0} Serial Numbers updated in batch {1}", [r.message.updated, batch_key])
                        : __("1 Serial Number updated");
                    frappe.show_alert({ message: msg, indicator: "green" }, 3);
                }
                me._report.refresh()
            },
            error() {
                frappe.show_alert({ message: __("Update failed. Reverting."), indicator: "red" }, 5);
                me._report.refresh();
            },
        });
    },

    _shift_held: false,

    formatter(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        if (!data) return value;

        


        // Visual for BOTH Delay Days columns
        if (column.fieldname === "bom_delay_days" || column.fieldname === "expected_based_delay_days") {
            if (value === "Released") {
                return `<span class="indicator-pill blue">Released</span>`;
            } else if (value !== "" && !isNaN(value)) {
                const d = parseInt(value, 10);
                const colour = d > 14 ? "red" : d > 7 ? "orange" : "green";
                return `<span style="color:var(--${colour}-600); font-weight:bold;">${value} Days</span>`;
            }
        }


         // Visual for Expected Delay Week
        if (column.fieldname === "expected_based_delay_week" || column.fieldname === "bom_delay_weeks") {
            if (value === "NA") return `<span class="text-muted">NA</span>`;
            if (value && value.startsWith("W")) {
                let color = "green";
                if (value === "W 4" || value === "W 4+") color = "red";
                if (value === "W 3") color = "orange";
                return `<span class="indicator-pill ${color}">${value}</span>`;
            }
        }
         

        if (column.editable) {
            value = `<span style="cursor:cell;" title="${__('Click to edit')}">` +
                    (value || `<span style="color:var(--text-muted);">User Select</span>`) +
                    `</span>`;
        }

        return value;
    },
};

$(document).on("keydown", function (e) {
    if (e.key === "Shift") {
        const me = frappe.query_reports["Daily Review Sales Order"];
        if (me) me._shift_held = true;
    }
});
$(document).on("keyup", function (e) {
    if (e.key === "Shift") {
        const me = frappe.query_reports["Daily Review Sales Order"];
        if (me) me._shift_held = false;
    }
});