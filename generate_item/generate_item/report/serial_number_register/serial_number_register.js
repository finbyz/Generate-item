// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt


frappe.dom.set_style(`
.select-wrapper {
    width: 100%;
}

.custom-select {
    width: 100%;
    border: none !important;
    outline: none;
    background: transparent;
    font-size: 13px;
    padding: 4px 6px;
    cursor: pointer;
}

/* Remove default arrow styling  */
.custom-select {
    appearance: none;
    -webkit-appearance: none;
    -moz-appearance: none;
}

/*  hover effect */
.custom-select:hover {
    background-color: #f8fafc;
}

/*  focus effect */
.custom-select:focus {
    background-color: #eef2ff;
}

/* Make cell look like ERP editable grid */
.dt-cell__content {
    display: flex;
    align-items: center;
}
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
            // Clear options if no batch
            window.mfg_options = [];
            window.api_options = [];
            report.refresh();
            return;
        }

        frappe.call({
            method: "generate_item.generate_item.report.serial_number_register.serial_number_register.get_serial_number_options",
            // args: { batch: batch }, 
            callback: function(r) {
                window.mfg_options = r.message.mfg_type || [];
                window.api_options = r.message.api_monogram_req || [];
                report.refresh();
            }
        });
    }
}
        ,
         {
            fieldname: "mfg_type",
            label: "MFG Type",
            fieldtype: "Select",
            options: window.mfg_options,
         
                

        }, {
            fieldname: "api_monogram_req",
            label: "API Monogram Req",
            fieldtype: "Select",
            options: window.api_options
        }
    ],
     onload: function(report) {
         
        frappe.call({
            method: "generate_item.generate_item.report.serial_number_register.serial_number_register.get_serial_number_options",
            async: false,  
            callback: function(r) {
                window.mfg_options = r.message.mfg_type || [];
                window.api_options = r.message.api_monogram_req || [];
                report.refresh();
                
            }
        });

        report.page.add_inner_button("Save Changes", () => {
            save_changes(report);
        });
    },
   

     formatter: function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (column.fieldname === "mfg_type") {
            let options = (window.mfg_options || []).map(opt =>
                `<option value="${opt}" ${data.mfg_type==opt?"selected":""}>${opt}</option>`
            ).join("");

            return `<select class="mfg_type custom-select " data-serial="${data.serial_no}">
                <option value="">Select</option>
                ${options}
            </select>`;
        }

        if (column.fieldname === "api_monogram_req") {
            let options = (window.api_options || []).map(opt =>
                `<option value="${opt}" ${data.api_monogram_req==opt?"selected":""}>${opt}</option>`
            ).join("");

            return `<select class="api_monogram custom-select " data-serial="${data.serial_no}">
                <option value="">Select</option>
                ${options}
            </select>`;
        }

        return value;
    }
};


function save_changes(report) {

    let updates = [];

    document.querySelectorAll(".mfg_type").forEach(el => {
        let serial = el.dataset.serial;
        let mfg_type = el.value;

        let api_val = document.querySelector(
            `.api_monogram[data-serial="${serial}"]`
        )?.value;

        if (mfg_type || api_val) {
            updates.push({
                serial_number: serial,
                mfg_type: mfg_type,
                api_monogram_req: api_val
            });
        }
    });

    console.log("updates --------", updates);

    if (!updates.length) {
        frappe.msgprint("No changes to update");
        return;
    }

    frappe.call({
        method: "generate_item.generate_item.report.serial_number_register.serial_number_register.update_serial_numbers",
        args: { updates },
        callback: function() {
            frappe.msgprint("Updated Successfully");
            
        }
    });
}