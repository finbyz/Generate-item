// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt

frappe.query_reports["Incoming Inspection"] = {

    // ── Config ────────────────────────────────────────────────────────────────
    MTC_STATUS_OPTIONS: [
        "", "RT PENDING", "RECEIVED IN MTC FOLDER", "MTC NOT RECEIVED",
        "MTC CORRCTION", "TRIM PART MTC PENDING", "IGC PENDING", "UPLOADED IN DMS"
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
            "label": __("Site"),
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
        this._report  = report;
        this._changed = {};   

        report.page.add_inner_button(__("Save Changes"), () => {
            this._save_all_changes();
        });

        // Single delegated listener on the report table
        report.$report.on("click", ".dt-cell", (e) => {
            let $cell    = $(e.target).closest(".dt-cell");
            let colIndex = parseInt($cell.attr("data-col-index"));
            let rowIndex = parseInt($cell.attr("data-row-index"));

            if (isNaN(colIndex) || isNaN(rowIndex)) return;

            // Frappe datatable exposes column by index
            let col       = report.datatable?.getColumn?.(colIndex);
            if (!col) return;

            // col.id is the fieldname Frappe uses internally
            let fieldname  = col.id || col.fieldname;
            let editorType = this.EDITABLE_FIELDS[fieldname];
            if (!editorType) return;

            e.stopPropagation();
            this._open_editor($cell, rowIndex, fieldname, editorType);
        });
    },

    // ── Editor dispatcher ─────────────────────────────────────────────────────
    _open_editor($cell, rowIndex, fieldname, editorType) {
        if ($cell.find(".ii-editor").length) return;  // already open

        let row = this._report.data?.[rowIndex];
        if (!row) return;

        let current = row[fieldname] ?? "";

        if      (editorType === "select_mtc") this._make_select_editor($cell, rowIndex, fieldname, current, this.MTC_STATUS_OPTIONS);
        else if (editorType === "select_pmi") this._make_select_editor($cell, rowIndex, fieldname, current, this.PMI_STATUS_OPTIONS);
        else if (editorType === "text")       this._make_text_editor($cell, rowIndex, fieldname, current);
    },

    // ── Select editor ─────────────────────────────────────────────────────────
    _make_select_editor($cell, rowIndex, fieldname, current, options) {
        let $content   = $cell.find(".dt-cell__content");
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
            this._record_change(rowIndex, fieldname, value);
            this._report.data[rowIndex][fieldname] = value;
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
        let $content = $cell.find(".dt-cell__content");

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
            if (e.key === "Enter")  { $input.blur(); }
            if (e.key === "Escape") {
                let val = this._report.data?.[rowIndex]?.[fieldname] || "";
                $content.html(this._render_cell(fieldname, val));
            }
        });

        $input.on("blur", () => {
            let value = $input.val().trim();
            this._record_change(rowIndex, fieldname, value);
            this._report.data[rowIndex][fieldname] = value;
            $content.html(this._render_cell(fieldname, value));
        });
    },

    // ── Track changes ─────────────────────────────────────────────────────────
    _record_change(rowIndex, fieldname, value) {
        if (!this._changed[rowIndex]) this._changed[rowIndex] = {};
        this._changed[rowIndex][fieldname] = value;
    },

    // ── Cell renderer ─────────────────────────────────────────────────────────
    _render_cell(fieldname, value) {
        if (!value) return `<span style="color:#ccc">—</span>`;

        if (fieldname === "mtc_status") {
           
          
            return `<span>${value}</span>`;
        }

        if (fieldname === "pmi_status") {
        
            return `<span>${value}</span>`;
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

        // frappe.show_alert({ message: __("Saving…"), indicator: "blue" });

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
            let c = changes[rowIndex];
            let args = { qi_name };

            if ("mtc_status"  in c) args.mtc_status  = c.mtc_status;
            if ("mtc_remark"  in c) args.mtc_remark  = c.mtc_remark;
            if ("pmi_status"  in c) args.pmi_status  = c.pmi_status;
            if ("ncr_no"      in c) args.ncr_no      = c.ncr_no;
         

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
            this._changed = {};
        } catch (err) {
            frappe.show_alert({ message: __("Save failed — check console"), indicator: "red" });
            console.error("Save error:", err);
        }
    }
};