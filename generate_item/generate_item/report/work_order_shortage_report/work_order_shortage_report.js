// Copyright (c) 2025, Finbyz and contributors
// For license information, please see license.txt

frappe.query_reports["Work Order Shortage Report"] = {
	"filters": [
        {
            "label": __("Company"),
            "fieldname": "company",
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_user_default("Company"),
            "reqd": 1
        },
        {
            "label": __("Based On"),
            "fieldname": "based_on",
            "fieldtype": "Select",
            "options": "Creation Date\nPlanned Date\nActual Date",
            "default": "Creation Date"
        },
        {
            "label": __("From Posting Date"),
            "fieldname": "from_date",
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -3),
            "reqd": 1
        },
        {
            "label": __("To Posting Date"),
            "fieldname": "to_date",
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "reqd": 1
        },
        {
            "label": __("Age"),
            "fieldname": "age",
            "fieldtype": "Int",
            "default": "0"
        },
        {
            "fieldname": "status",
            "label": __("Status"),
            "fieldtype": "Select",
            "options": [
                "",
                "Not Started",
                "In Process",
                "Completed",
                "Stopped",
                "Closed"
            ],
            "default": ""
        },
        {
            "fieldname": "production_item",
            "label": __("Production Item"),
            "fieldtype": "Link",
            "options": "Item",
            "get_query": function() {
                return {
                    filters: {
                        "is_stock_item": 1
                    }
                };
            }
        },
        {
            "fieldname": "sales_order",
            "label": __("Sales Order"),
            "fieldtype": "Link",
            "options": "Sales Order"
        },
        {
            "fieldname": "custom_batch_no",
            "label": __("Batch No"),
            "fieldtype": "Link",
            "options": "Batch",
            "get_query": function() {
                return {
                    filters: {
                        "disabled": 0
                    }
                };
            }
        },
        {
            "label": __("Charts Based On"),
            "fieldname": "charts_based_on",
            "fieldtype": "Select",
            "options": ["Status", "Age", "Quantity"],
            "default": "Status"
        },
        {
            "label": __("Branch"),
            "fieldname": "branch",
            "fieldtype": "Link",
            "options": "Branch",
            "default": "Mumbai",
            "reqd":1,
            "placeholder":"Branch"
        }
    ],
    
    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        
        // Color code status
        if (column.fieldname == "status") {
            if (value && value.includes("Completed")) {
                value = `<span style="color: green; font-weight: bold;">${value}</span>`;
            } else if (value && value.includes("In Process")) {
                value = `<span style="color: orange; font-weight: bold;">${value}</span>`;
            } else if (value && value.includes("Stopped") || value.includes("Cancelled")) {
                value = `<span style="color: red; font-weight: bold;">${value}</span>`;
            }
        }
        
        // Color code shortage quantity
        if (column.fieldname == "shortage_qty" && data && data.shortage_qty > 0) {
            value = `<span style="color: red; font-weight: bold;">${value}</span>`;
        }
        
        // Highlight age
        if (column.fieldname == "age" && data && data.age > 30) {
            value = `<span style="color: red; font-weight: bold;">${value}</span>`;
        } else if (column.fieldname == "age" && data && data.age > 15) {
            value = `<span style="color: orange; font-weight: bold;">${value}</span>`;
        }
        if (column.fieldname === "view" && data) {
            return `
                <button class="btn btn-xs btn-default"
                    onclick="show_view_menu(event, '${data.input_item_code || ""}')">
                    View ▼
                </button>
            `;
        }
        return value;
    },
    
    "onload": function(report) {
        // Add custom buttons
        report.page.add_inner_button(__("Export to Excel"), function() {
            frappe.query_report.export_report("Excel");
        });
        
        report.page.add_inner_button(__("Print"), function() {
            frappe.query_report.print_report();
        });
    }
};

window.show_view_menu = function(e, item_code) {
    e.stopPropagation();

    // Remove any existing dropdown
    $('.custom-view-dropdown').remove();

    const menu_items = [
        {
            label: "Stock Balance",
            action: () => {
                frappe.set_route("query-report", "Stock Balance", {
                    item_code: item_code
                });
            }
        },
        {
            label: "Stock Ledger",
            action: () => {
                frappe.set_route("query-report", "Stock Ledger", {
                    item_code: item_code
                });
            }
        },
        {
            label: "Stock Projected Qty",
            action: () => {
                frappe.set_route("query-report", "Stock Projected Qty", {
                    item_code: item_code
                });
            }
        }
    ];

    // Build dropdown HTML
    const dropdown = $(`
        <div class="custom-view-dropdown dropdown-menu show" 
             style="position:fixed; z-index:9999; background:white; 
                    border:1px solid #ccc; border-radius:4px; 
                    box-shadow:0 4px 8px rgba(0,0,0,0.15); min-width:180px;">
        </div>
    `);

    menu_items.forEach(item => {
        const el = $(`<a class="dropdown-item" style="padding:8px 16px; cursor:pointer; display:block;">${item.label}</a>`);
        el.on('click', () => {
            dropdown.remove();
            item.action();
        });
        el.hover(
            function() { $(this).css('background', '#f0f0f0'); },
            function() { $(this).css('background', ''); }
        );
        dropdown.append(el);
    });

    // Position near the button
    const btn = $(e.target);
    const offset = btn.offset();
    dropdown.css({
        top: offset.top + btn.outerHeight() + 2,
        left: offset.left
    });

    $('body').append(dropdown);

    // Close on outside click
    setTimeout(() => {
        $(document).one('click', () => dropdown.remove());
    }, 0);
};