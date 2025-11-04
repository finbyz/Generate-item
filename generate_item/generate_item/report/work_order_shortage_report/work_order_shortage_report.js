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
            "default": " ",
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