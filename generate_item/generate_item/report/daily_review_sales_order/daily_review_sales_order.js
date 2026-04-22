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

    // ─── STATE ────────────────────────────────────────────────────────────────
    _sn_meta:         null,
    _pending_changes: {},  
    _save_btn:        null,

    // ─── LIFECYCLE ────────────────────────────────────────────────────────────
    onload(report) {
        const me = frappe.query_reports["Daily Review Sales Order"];
        me._report = report;

        frappe.call({
            method: "generate_item.generate_item.report.daily_review_sales_order.daily_review_sales_order.get_sn_field_meta",
            callback(r) {
                if (r.message) me._sn_meta = r.message;
            },
        });

        // ── Save Changes toolbar button ──────────────────────────────────────
        me._save_btn = report.page.add_inner_button(__("Save Changes"), () => {
            me._save_all_changes();
        });
        me._update_save_button();

        // ── Cell click → open inline editor ─────────────────────────────────
        report.$report.on("click", ".dt-cell", function (e) {
            me._on_cell_click(e, $(this));
        });
    },

    // ─── CELL CLICK ───────────────────────────────────────────────────────────
    _on_cell_click(e, $cell) {
        const me = frappe.query_reports["Daily Review Sales Order"];
        if (!me._sn_meta) return;

        const col_idx = parseInt($cell.attr("data-col-index"), 10);
        const row_idx = parseInt($cell.attr("data-row-index"), 10);

        const col = me._report.datatable.getColumn(col_idx);
        if (!col || !col.editable) return;
        if ($cell.find(".inline-editor").length) return;   // already open

        const row_data = me._report.data[row_idx];
        if (!row_data) return;

        const sn_name   = row_data.sn_name;
        const batch_key = row_data.batch_key;
        if (!sn_name && !batch_key) return;

        const fieldname = col.fieldname || col.id;
        const meta      = me._sn_meta[fieldname];
        if (!meta) {
            meta = { fieldtype: "Data" };
            console.error("Metadata not found for field:", fieldname);
            
        }

        // Use the already-staged value if the cell was edited before
        const pending_key = `${sn_name}::${fieldname}`;
        const cur_value   = me._pending_changes[pending_key]
            ? me._pending_changes[pending_key].new_value
            : (row_data[fieldname] || "");

        me._render_editor($cell, meta, cur_value, (new_value) => {
            me._stage_change($cell, row_data, fieldname, new_value, batch_key, sn_name);
        });
    },

    // ─── EDITOR RENDERER ──────────────────────────────────────────────────────
    _render_editor($cell, meta, cur_value, on_stage) {
        $cell.css("position", "relative");

        let $editor;

        if (meta.fieldtype === "Select") {
            // ── Select ───────────────────────────────────────────────────────
            const options_array = (meta.options || "").split("\n");
            const opts = options_array
                .map(o => `<option value="${frappe.utils.escape_html(o)}"${o === cur_value ? " selected" : ""}>${o || "--"}</option>`)
                .join("");

            $editor = $(`
                <select class="inline-editor" style="
                    position:absolute; top:0; left:0; width:100%; height:100%;
                    z-index:100; font-size:12px; border:2px solid var(--primary);
                    background:var(--card-bg); color:var(--text-color); padding:2px;
                ">${opts}</select>
            `);

            $editor.on("change", function () {
                on_stage($(this).val());
                $editor.remove();
            });
            $editor.on("keydown", function (e) {
                if (e.key === "Escape") $editor.remove();
            });

        } else if (meta.fieldtype === "Date") {
            // ── Date ─────────────────────────────────────────────────────────
            $editor = $(`
                <input type="date" class="inline-editor" value="${cur_value || ""}" style="
                    position:absolute; top:0; left:0; width:100%; height:100%;
                    z-index:100; font-size:12px; border:2px solid var(--primary);
                    background:var(--card-bg); color:var(--text-color); padding:2px;
                "/>
            `);

            $editor.on("change", function () {
                on_stage($(this).val());
                $editor.remove();
            });
            $editor.on("keydown", function (e) {
                if (e.key === "Escape") $editor.remove();
            });

        } 
        else {
            // ── Data / Small Text / plain text ────────────────────────────────
            
            let _closed = false;

            const _close = (should_save) => {
                if (_closed) return;     // ← guard: execute only once
                _closed = true;

                if (should_save) {
                    const val = $editor.val().trim();
                    if (val !== cur_value) on_stage(val);
                }
                // Detach after we've read the value — order matters
                $editor.remove();
            };

            $editor = $(`
                <input type="text" class="inline-editor" value="${frappe.utils.escape_html(cur_value)}" style="
                    position:absolute; top:0; left:0; width:100%; height:100%;
                    z-index:100; font-size:12px; border:2px solid var(--primary);
                    background:var(--card-bg); color:var(--text-color); padding:2px;
                "/>
            `);

            $editor.on("blur",    ()  => _close(true));
            $editor.on("keydown", (e) => {
                if (e.key === "Enter")  { e.preventDefault(); _close(true);  }
                if (e.key === "Escape") {                      _close(false); }
            });
        }

        $cell.append($editor);
        $editor.focus();
    },

    // ─── STAGE A CHANGE (NO REPORT REFRESH) ──────────────────────────────────
    _stage_change($cell, row_data, fieldname, new_value, batch_key, sn_name) {
        const me  = frappe.query_reports["Daily Review Sales Order"];
        const key = `${sn_name}::${fieldname}`;

        me._pending_changes[key] = { sn_name, batch_key, fieldname, new_value };

        // Keep in-memory row in sync for subsequent editor opens
        row_data[fieldname] = new_value;

        // Update only this cell's DOM — no full grid refresh
        me._paint_cell($cell, new_value, true /* pending */);

        me._update_save_button();
    },


    _paint_cell($cell, value, pending) {
        const display = frappe.utils.escape_html(value || "");
        const empty   = `<span style="color:var(--text-muted);">User Select</span>`;

        const inner_html = pending
            ? `<span style="
                    display:block;
                    background:var(--yellow-50,#fef9c3);
                    border-left:3px solid var(--yellow-400,#facc15);
                    padding:2px 6px;
                    border-radius:2px;
                    cursor:cell;
               " title="${__('Unsaved — click Save Changes to apply')}">
                   ${display || empty}
               </span>`
            : `<span style="cursor:cell;" title="${__('Click to edit')}">
                   ${display || empty}
               </span>`;

       
        let $target = $cell.find(".dt-cell__content");
        if (!$target.length) {
            $target = $('<div class="dt-cell__content"></div>');
            // Prepend so the absolutely-positioned inline-editor stays on top
            $cell.prepend($target);
        }

        $target.html(inner_html);
    },

    // ─── SAVE BUTTON STATE ────────────────────────────────────────────────────
    _update_save_button() {
        const me    = frappe.query_reports["Daily Review Sales Order"];
        if (!me._save_btn) return;

        const count = Object.keys(me._pending_changes).length;

        if (count > 0) {
            me._save_btn
                .html(`<i class="fa fa-save mr-1"></i>${__("Save Changes")} (${count})`)
                .removeClass("btn-default btn-secondary")
                .addClass("btn-warning");
        } else {
            me._save_btn
                .html(__("Save Changes"))
                .removeClass("btn-warning")
                .addClass("btn-default");
        }
    },

    // ─── BATCH-SAVE ALL STAGED CHANGES ────────────────────────────────────────
    async _save_all_changes() {
        const me      = frappe.query_reports["Daily Review Sales Order"];
        const changes = me._pending_changes;

        if (!Object.keys(changes).length) {
            frappe.show_alert({ message: __("No pending changes to save."), indicator: "blue" }, 3);
            return;
        }

        // Group by batch_key
        const by_batch = {};
        for (const key of Object.keys(changes)) {
            const { batch_key, fieldname, new_value } = changes[key];
            if (!by_batch[batch_key]) by_batch[batch_key] = {};
            by_batch[batch_key][fieldname] = new_value;
        }

        const batch_names    = Object.keys(by_batch);
        const total_batches  = batch_names.length;
        const failed_batches = [];
        let   total_sns      = 0;

        me._save_btn && me._save_btn.prop("disabled", true).html(
            `<i class="fa fa-spinner fa-spin mr-1"></i>${__("Saving…")}`
        );

        frappe.show_alert({
            message:   __("Saving changes for {0} batch(es)…", [total_batches]),
            indicator: "blue",
        }, 2);

        for (const batch_name of batch_names) {
            try {
                const result = await frappe.xcall(
                    "generate_item.generate_item.report.daily_review_sales_order.daily_review_sales_order.bulk_update_batch_multifield",
                    { batch_name, field_value_map: by_batch[batch_name] }
                );
                if (result && result.updated) total_sns += result.updated;
            } catch (err) {
                console.error("Save failed for batch:", batch_name, err);
                failed_batches.push(batch_name);
            }
        }

        me._save_btn && me._save_btn.prop("disabled", false);

        if (failed_batches.length === 0) {
            me._pending_changes = {};
            me._update_save_button();
            frappe.show_alert({
                message:   __("Saved — {0} batch(es), {1} Serial Number(s) updated.", [total_batches, total_sns]),
                indicator: "green",
            }, 5);
            me._report.refresh();   // single refresh only after explicit save

        } else {
            const failed_set = new Set(failed_batches);
            for (const key of Object.keys(me._pending_changes)) {
                if (!failed_set.has(me._pending_changes[key].batch_key)) {
                    delete me._pending_changes[key];
                }
            }
            me._update_save_button();
            me._report.refresh();

            frappe.msgprint({
                title:     __("Partial Save Failure"),
                message:   __(
                    "Saved {0} of {1} batch(es).<br><br><strong>Failed (still pending):</strong><br>{2}",
                    [total_batches - failed_batches.length, total_batches, failed_batches.join("<br>")]
                ),
                indicator: "orange",
            });
        }
    },

    formatter(value, row, column, data, default_formatter) {
        const me = frappe.query_reports["Daily Review Sales Order"];
        value = default_formatter(value, row, column, data);
        if (!data) return value;

        if (data.sn_name && me._pending_changes) {
            const pending_key = `${data.sn_name}::${column.fieldname}`;
            if (me._pending_changes[pending_key]) {
                const display = frappe.utils.escape_html(
                    me._pending_changes[pending_key].new_value || ""
                );
                return `<span style="
                    display:block;
                    background:var(--yellow-50,#fef9c3);
                    border-left:3px solid var(--yellow-400,#facc15);
                    padding:2px 6px; border-radius:2px; cursor:cell;
                " title="${__('Unsaved — click Save Changes to apply')}">
                    ${display || `<span style="color:var(--text-muted);">User Select</span>`}
                </span>`;
            }
        }

        if (column.fieldname === "bom_delay_days" || column.fieldname === "expected_based_delay_days") {
            if (value === "Released") {
                return `<span class="indicator-pill blue">Released</span>`;
            } else if (value !== "" && !isNaN(value)) {
                const d      = parseInt(value, 10);
                const colour = d > 14 ? "red" : d > 7 ? "orange" : "green";
                return `<span style="color:var(--${colour}-600); font-weight:bold;">${value} Days</span>`;
            }
        }

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
            value = `<span style="cursor:cell;" title="${__("Click to edit")}">` +
                    (value || `<span style="color:var(--text-muted);">User Select</span>`) +
                    `</span>`;
        }

        return value;
    },
};