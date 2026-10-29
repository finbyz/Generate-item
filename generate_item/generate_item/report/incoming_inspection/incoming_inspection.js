// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt

frappe.query_reports["Incoming Inspection"] = {

    // ── Config ────────────────────────────────────────────────────────────────
    MTC_STATUS_OPTIONS: [
        "", "RT PENDING", "RECEIVED IN MTC FOLDER", "MTC NOT RECEIVED",
        "MTC CORRCTION", "TRIM PART MTC PENDING IGC PENDING", "UPLOADED IN DMS"
    ],

    PMI_STATUS_OPTIONS: ["", "YES", "NO"],

    // fieldname in report → editor type
    // These MUST match get_columns() fieldnames exactly
    EDITABLE_FIELDS: {
        "mtc_status":  "select_mtc",
        "mtc_remark":  "text",
        "pmi_status":  "select_pmi",
        "ncr_no":      "text",
    },

    // ── Filters ───────────────────────────────────────────────────────────────
    "filters": [
        {
            "fieldname": "date_based_on",
            "label": __("Date Based On"),
            "fieldtype": "Select",
            "options": ["GRN Date", "Creation Date", "Submission Date"].join("\n"),
            "default": "GRN Date",
            "reqd": 1
        },
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "reqd": 1
        },
        {
            "fieldname": "branch",
            "label": __("Branch"),
            "fieldtype": "Link",
            "options": "Branch"
        },
        {
            "fieldname": "supplier",
            "label": __("Supplier"),
            "fieldtype": "Link",
            "options": "Supplier"
        }
    ],

    // ── Lifecycle ─────────────────────────────────────────────────────────────
    onload(report) {
        this._report   = report;
        this._changed  = {};   // { rowIndex: { fieldname: newValue } }
        this._original = {};   // { "rowIndex:fieldname": originalValue }

        // style for edited (unsaved) cells
        if (!document.getElementById("ii-style")) {
            $(`<style id="ii-style">
                .dt-cell.ii-changed,
                .dt-cell.ii-changed .dt-cell__content { background: #fff3a3 !important; }
            </style>`).appendTo("head");
        }

        report.page.add_inner_button(__("Save Changes"), () => {
            this._save_all_changes();
        });

        report.page.add_inner_button(__("Bulk Update"), () => {
            this._open_bulk_update_dialog();
        });

        // Single delegated listener on the report table
        report.$report.on("click", ".dt-cell", (e) => {
            let $cell    = $(e.target).closest(".dt-cell");
            let colIndex = parseInt($cell.attr("data-col-index"));
            let rowIndex = parseInt($cell.attr("data-row-index"));

            if (isNaN(colIndex) || isNaN(rowIndex)) return;

            // Frappe datatable exposes column by index
            let col = report.datatable?.getColumn?.(colIndex);
            if (!col) return;

            // col.id is the fieldname Frappe uses internally
            let fieldname  = col.id || col.fieldname;
            let editorType = this.EDITABLE_FIELDS[fieldname];
            if (!editorType) return;

            e.stopPropagation();
            this._open_editor($cell, rowIndex, fieldname, editorType);
        });
    },

    _open_bulk_update_dialog() {
        const me = this;
        let dialog;

        const set_fields_visible = (visible) => {
            const hidden = visible ? 0 : 1;
            ["fields_to_update", "update_note", "mtc_status", "mtc_remark", "pmi_status", "ncr_no"]
                .forEach((fieldname) => dialog.set_df_property(fieldname, "hidden", hidden));
            dialog.refresh();
        };

        const render_qc_table = (inspections) => {
            const field = dialog.fields_dict.qc_table_html;
            if (!field?.$wrapper) return;

            if (!inspections.length) {
                field.$wrapper.empty();
                dialog.set_df_property("qc_table_html", "hidden", 1);
                set_fields_visible(false);
                frappe.msgprint({
                    title: __("No Quality Inspections Found"),
                    message: __("No active Quality Inspections were found for this Purchase Receipt."),
                    indicator: "orange",
                });
                return;
            }

            dialog.set_df_property("qc_table_html", "hidden", 0);
            field.$wrapper.html(`
                <div style="margin: 4px 0 12px;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:6px; font-size:12px; color:var(--text-muted);">
                        <span><strong class="selected-qc-count">${inspections.length}</strong> of <strong>${inspections.length}</strong> Quality Inspection(s) selected</span>
                        <span>
                            <a href="#" class="qc-select-all">${__("Select All")}</a>
                            &nbsp;|&nbsp;
                            <a href="#" class="qc-deselect-all">${__("Deselect All")}</a>
                        </span>
                    </div>
                    <div style="max-height:220px; overflow-y:auto; border:1px solid var(--border-color); border-radius:6px;">
                        <table class="table table-bordered table-hover" style="margin:0; width:100%; font-size:13px;">
                            <thead style="position:sticky; top:0; z-index:2; background:var(--table-bg, var(--bg-light-gray));">
                                <tr>
                                    <th style="width:44px;"><input type="checkbox" class="qc-select-all-checkbox" checked /></th>
                                    <th>${__("QC Number")}</th>
                                    <th>${__("Status")}</th>
                                    <th>${__("PO No")}</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${inspections.map((inspection) => `
                                    <tr>
                                        <td><input type="checkbox" class="qc-row-checkbox" value="${frappe.utils.escape_html(inspection.qi_name)}" checked /></td>
                                        <td>${frappe.utils.escape_html(inspection.qi_name)}</td>
                                        <td>${frappe.utils.escape_html(inspection.status || "")}</td>
                                        <td>${frappe.utils.escape_html(inspection.po_name || "")}</td>
                                    </tr>
                                `).join("")}
                            </tbody>
                        </table>
                    </div>
                </div>
            `);

            const update_count = () => {
                const checkboxes = field.$wrapper.find(".qc-row-checkbox");
                const checked = checkboxes.filter(":checked").length;
                field.$wrapper.find(".selected-qc-count").text(checked);
                field.$wrapper.find(".qc-select-all-checkbox")
                    .prop("checked", checked === checkboxes.length)
                    .prop("indeterminate", checked > 0 && checked < checkboxes.length);
            };

            field.$wrapper.find(".qc-select-all-checkbox").on("change", function() {
                field.$wrapper.find(".qc-row-checkbox").prop("checked", this.checked);
                update_count();
            });
            field.$wrapper.find(".qc-row-checkbox").on("change", update_count);
            field.$wrapper.find(".qc-select-all, .qc-deselect-all").on("click", function(event) {
                event.preventDefault();
                const checked = $(this).hasClass("qc-select-all");
                field.$wrapper.find(".qc-row-checkbox").prop("checked", checked);
                update_count();
            });
            set_fields_visible(true);
        };

        const fetch_quality_inspections = async () => {
            const purchase_receipt = dialog.get_value("purchase_receipt");
            if (!purchase_receipt) {
                frappe.show_alert({ message: __("Please select a Purchase Receipt first."), indicator: "orange" }, 3);
                return;
            }

            dialog.fields_dict.qc_table_html.$wrapper.empty();
            dialog.set_df_property("qc_table_html", "hidden", 1);
            set_fields_visible(false);

            try {
                const inspections = await frappe.xcall(
                    "generate_item.generate_item.report.incoming_inspection.incoming_inspection.get_quality_inspections_for_receipt",
                    { purchase_receipt }
                );
                render_qc_table(inspections || []);
            } catch (error) {
                frappe.msgprint({
                    title: __("Fetch Failed"),
                    message: error.message || __("Unable to fetch Quality Inspections."),
                    indicator: "red",
                });
            }
        };

        dialog = new frappe.ui.Dialog({
            title: __("Bulk Update Incoming Inspection"),
            fields: [
                {
                    fieldname: "purchase_receipt",
                    label: __("Purchase Receipt"),
                    fieldtype: "Link",
                    options: "Purchase Receipt",
                    reqd: 1,
                    onchange() {
                        dialog.fields_dict.qc_table_html.$wrapper.empty();
                        dialog.set_df_property("qc_table_html", "hidden", 1);
                        set_fields_visible(false);
                    },
                },
                {
                    fieldname: "fetch_qc",
                    label: __("Fetch QC"),
                    fieldtype: "Button",
                    click: fetch_quality_inspections,
                },
                { fieldname: "qc_table_html", fieldtype: "HTML", hidden: 1 },
                { fieldname: "fields_to_update", label: __("Fields to Update"), fieldtype: "Section Break", hidden: 1 },
                {
                    fieldname: "update_note",
                    fieldtype: "HTML",
                    hidden: 1,
                    options: `<div class="text-muted" style="margin-bottom:8px;">
                        ${__("Leave fields blank to skip them; non-empty values will be applied to every selected Quality Inspection.")}
                    </div>`,
                },
                {
                    fieldname: "mtc_status",
                    label: __("MTC Status"),
                    fieldtype: "Select",
                    options: me.MTC_STATUS_OPTIONS.join("\n"),
                    hidden: 1,
                },
                { fieldtype: "Column Break" },
                { fieldname: "mtc_remark", label: __("MTC Remark"), fieldtype: "Small Text", hidden: 1 },
                { fieldtype: "Section Break", hide_border: 1 },
                {
                    fieldname: "pmi_status",
                    label: __("PMI Status"),
                    fieldtype: "Select",
                    options: me.PMI_STATUS_OPTIONS.join("\n"),
                    hidden: 1,
                },
                { fieldtype: "Column Break" },
                { fieldname: "ncr_no", label: __("NCR No"), fieldtype: "Data", hidden: 1 },
            ],
            size: "large",
            primary_action_label: __("Update"),
            primary_action(values) {
                me._execute_bulk_update(values, dialog);
            },
        });
        dialog.show();
    },

    async _execute_bulk_update(values, dialog) {
        const purchase_receipt = values.purchase_receipt;
        const field_value_map = {};
        ["mtc_status", "mtc_remark", "pmi_status", "ncr_no"].forEach((fieldname) => {
            if (values[fieldname] !== undefined && values[fieldname] !== null && values[fieldname] !== "") {
                field_value_map[fieldname] = values[fieldname];
            }
        });

        const qc_table = dialog.fields_dict.qc_table_html.$wrapper;
        const selected_qi_names = [];
        qc_table.find(".qc-row-checkbox:checked").each(function() {
            selected_qi_names.push($(this).val());
        });

        if (!purchase_receipt || !selected_qi_names.length) {
            frappe.show_alert({
                message: __("Select a Purchase Receipt, fetch Quality Inspections, and select at least one row."),
                indicator: "orange",
            }, 4);
            return;
        }
        if (!Object.keys(field_value_map).length) {
            frappe.show_alert({ message: __("Please fill at least one field to update."), indicator: "orange" }, 3);
            return;
        }

        frappe.confirm(
            __("Update {0} field(s) on {1} selected Quality Inspection(s) for Purchase Receipt {2}?", [
                Object.keys(field_value_map).length,
                selected_qi_names.length,
                purchase_receipt,
            ]),
            async () => {
                try {
                    const result = await frappe.xcall(
                        "generate_item.generate_item.report.incoming_inspection.incoming_inspection.bulk_update_inspection_rows",
                        { purchase_receipt, selected_qi_names, field_value_map }
                    );
                    dialog.hide();
                    frappe.show_alert({
                        message: __("Updated {0} Quality Inspection(s).", [result.updated]),
                        indicator: "green",
                    });
                    this._report.refresh();
                } catch (error) {
                    frappe.msgprint({
                        title: __("Bulk Update Failed"),
                        message: error.message || __("Unable to update the selected Quality Inspections."),
                        indicator: "red",
                    });
                }
            }
        );
    },

    // keep yellow highlight when the table re-renders (sort, scroll, etc.)
    after_datatable_render(datatable) {
        this._reapply_highlights();
    },

    _reapply_highlights() {
        let dt = this._report?.datatable;
        if (!dt || !this._changed) return;

        let cols = dt.getColumns?.() || [];
        for (let rowIndex in this._changed) {
            for (let fieldname in this._changed[rowIndex]) {
                let col = cols.find(c => (c.id || c.fieldname) === fieldname);
                if (!col) continue;
                $(this._report.$report)
                    .find(`.dt-cell[data-col-index="${col.colIndex}"][data-row-index="${rowIndex}"]`)
                    .addClass("ii-changed");
            }
        }
    },

    // ── Editor dispatcher ─────────────────────────────────────────────────────
    _open_editor($cell, rowIndex, fieldname, editorType) {
        if ($cell.find(".ii-editor").length) return;  // already open

        let row = this._report.data?.[rowIndex];
        if (!row) return;

        let current = row[fieldname] ?? "";

        // remember the value before the first edit
        let key = `${rowIndex}:${fieldname}`;
        if (!(key in this._original)) this._original[key] = current;

        if      (editorType === "select_mtc") this._make_select_editor($cell, rowIndex, fieldname, current, this.MTC_STATUS_OPTIONS);
        else if (editorType === "select_pmi") this._make_select_editor($cell, rowIndex, fieldname, current, this.PMI_STATUS_OPTIONS);
        else if (editorType === "text")       this._make_text_editor($cell, rowIndex, fieldname, current);
    },

    // ── Select editor ─────────────────────────────────────────────────────────
    _make_select_editor($cell, rowIndex, fieldname, current, options) {
        let $content    = $cell.find(".dt-cell__content");
        let optionsHtml = options.map(o =>
            `<option value="${o}" ${o === current ? "selected" : ""}>${o || "Select"}</option>`
        ).join("");

        let $select = $(`
            <select class="ii-editor" style="
                width:100%; height:26px; font-size:12px;
                border:1.5px solid #5e9bfc; border-radius:3px;
                padding:0 4px; background:#fff; cursor:pointer;
            ">${optionsHtml}</select>
        `);

        $content.html($select);
        $select.focus();

        $select.on("mousedown click keydown", e => e.stopPropagation());

        $select.on("change", (e) => {
            let value = e.target.value;
            this._report.data[rowIndex][fieldname] = value;
            this._record_change(rowIndex, fieldname, value, $cell);
            // close immediately after selection
            $content.html(this._render_cell(fieldname, value));
        });

        $select.on("blur", () => {
            let val = this._report.data?.[rowIndex]?.[fieldname] || "";
            $content.html(this._render_cell(fieldname, val));
        });
    },

    // ── Text editor ───────────────────────────────────────────────────────────
    _make_text_editor($cell, rowIndex, fieldname, current) {
        let $content  = $cell.find(".dt-cell__content");
        let cancelled = false;

        let $input = $(`
            <input type="text" class="ii-editor"
                value="${frappe.utils.escape_html(current)}"
                style="width:100%; height:26px; font-size:12px;
                       border:1.5px solid #5e9bfc; border-radius:3px;
                       padding:0 6px; background:#fff; box-sizing:border-box;"
            />
        `);

        $content.html($input);
        $input.focus().select();

        $input.on("mousedown click keydown", e => e.stopPropagation());

        $input.on("keydown", (e) => {
            if (e.key === "Enter") { $input.blur(); }
            if (e.key === "Escape") {
                cancelled = true;
                let val = this._report.data?.[rowIndex]?.[fieldname] || "";
                $content.html(this._render_cell(fieldname, val));
            }
        });

        $input.on("blur", () => {
            if (cancelled) return;
            let value = $input.val().trim();
            this._report.data[rowIndex][fieldname] = value;
            this._record_change(rowIndex, fieldname, value, $cell);
            $content.html(this._render_cell(fieldname, value));
        });
    },

    // ── Track changes (and yellow highlight) ──────────────────────────────────
    _record_change(rowIndex, fieldname, value, $cell) {
        let key      = `${rowIndex}:${fieldname}`;
        let original = this._original[key] ?? "";

        // value changed back to the original → no longer a pending change
        if ((value ?? "") === original) {
            if (this._changed[rowIndex]) {
                delete this._changed[rowIndex][fieldname];
                if (!Object.keys(this._changed[rowIndex]).length) {
                    delete this._changed[rowIndex];
                }
            }
            $cell.removeClass("ii-changed");
            return;
        }

        if (!this._changed[rowIndex]) this._changed[rowIndex] = {};
        this._changed[rowIndex][fieldname] = value;
        $cell.addClass("ii-changed");
    },

    // ── Cell renderer ─────────────────────────────────────────────────────────
    _render_cell(fieldname, value) {
        if (!value) return `<span style="color:#ccc">—</span>`;

        if (fieldname === "mtc_status" || fieldname === "pmi_status") {
            return `<span>${frappe.utils.escape_html(value)}</span>`;
        }

        return frappe.utils.escape_html(value);
    },

    // ── Save ──────────────────────────────────────────────────────────────────
    async _save_all_changes() {
        let changes = this._changed;
        if (!Object.keys(changes).length) {
            frappe.show_alert({ message: __("No changes to save"), indicator: "orange" });
            return;
        }

        let report = this._report;
        let calls  = [];

        for (let rowIndex in changes) {
            let row     = report.data?.[rowIndex];
            let qi_name = row?.qi_name;

            if (!qi_name) {
                console.warn(`Row ${rowIndex}: no qi_name, skipping`);
                continue;
            }

            // Map report fieldnames → python parameter names
            let c    = changes[rowIndex];
            let args = { qi_name };

            if ("mtc_status" in c) args.mtc_status = c.mtc_status;
            if ("mtc_remark" in c) args.mtc_remark = c.mtc_remark;
            if ("pmi_status" in c) args.pmi_status = c.pmi_status;
            if ("ncr_no"     in c) args.ncr_no     = c.ncr_no;

            calls.push(
                frappe.call({
                    method: "generate_item.generate_item.report.incoming_inspection.incoming_inspection.update_inspection_row",
                    args,
                    freeze: false,
                }).then((r) => {
                    console.log(r.message);
                })
            );
        }

        try {
            await Promise.all(calls);
            frappe.show_alert({ message: __("Saved Successfully"), indicator: "green" });
            this._changed  = {};
            this._original = {};
            // reload: clears yellow and shows the new "MTC Last Updated On"
            this._report.refresh();
        } catch (err) {
            frappe.show_alert({ message: __("Save failed — check console"), indicator: "red" });
            console.error("Save error:", err);
        }
    }
};