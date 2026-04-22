// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt


frappe.query_reports["RT Inward Register"] = {

    filters: [
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            default: frappe.defaults.get_user_default("Company"),
            reqd: 1,
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
            reqd: 1,
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
            reqd: 1,
        },
        {
            fieldname: "branch",
            label: __("Branch"),
            fieldtype: "Link",
            options: "Branch",
        },
        {
            fieldname: "supplier",
            label: __("Supplier"),
            fieldtype: "Link",
            options: "Supplier",
        },
        
    
        {
            fieldname: "sales_order",
            label: __("Sales Order"),
            fieldtype: "Link",
            options: "Sales Order",
        },
    ],

    // ─────────────────────────────────────────────

    onload(report) {
        const me = this;
        me._report = report;
        me._changed = {};

        // ✅ Save Button
        report.page.add_inner_button("Save Changes", () => {
            me._save_all_changes();
        });

        // ✅ Click handler
        report.$report.on("click", ".dt-cell", function () {
            let $cell = $(this);
            let colIndex = $cell.attr("data-col-index");
            let col = report.datatable.getColumn(colIndex);

            if (col.fieldname === "used") {
                me._make_select_editable($cell);
            }
        });
    },

    // ✅ Dropdown editor
    _make_select_editable($cell) {
        let report = this._report;
        let rowIndex = $cell.attr("data-row-index");
        let row = report.data[rowIndex];

        if (!row) return;

        let current = row.used || "";

        let $content = $cell.find(".dt-cell__content");

        if (!$content.length) {
            $content = $('<div class="dt-cell__content"></div>');
            $cell.append($content);
        }

        if ($content.find("select").length) return;

        let select = $(`
            <select style="width:100%; height:28px;">
                <option value="">Select</option>
                <option value="YES">YES</option>
                <option value="NO">NO</option>
            </select>
        `);

        select.val(current);

        $content.html(select);

        select.focus();

        select.on("mousedown click", function(e){
            e.stopPropagation();
        });

        select.on("change", (e) => {
            let value = e.target.value;

            this._changed[row.heat_no_name] = value;
            row.used = value;

            $content.html(value || `<span style="color:#999">Select</span>`);
        });

        select.on("blur", () => {
            $content.html(row.used || `<span style="color:#999">Select</span>`);
        });
    },

    // ✅ Save logic
    async _save_all_changes() {
        let updates = this._changed;

        if (!Object.keys(updates).length) {
            frappe.msgprint("No changes");
            return;
        }

        let calls = [];

        for (let name in updates) {
            calls.push(
                frappe.call({
                    method: "generate_item.generate_item.report.rt_inward_register.rt_inward_register.update_heat_no",
                    args: {
                        name: name,
                        used: updates[name]
                    }
                })
            );
        }

        await Promise.all(calls);

        frappe.show_alert({
            message: "Updated Successfully",
            indicator: "green"
        });

        this._changed = {};
        this._report.refresh();
    }
};