// Copyright (c) 2025, Finbyz and contributors
// For license information, please see license.txt

frappe.query_reports["Item-wise Batch Summary"] = {
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
            "fieldname": "sales_order",
            "label": __("Sales Order"), 
            "fieldtype": "Link",
            "options": "Sales Order",
            "width": 150,
            "get_query": function() {
                return {
                    filters: {
                        "docstatus": ["!=", 2]
                    }
                }
            }
        },
        {
            "fieldname": "production_plan",
            "label": __("Production Plan"),
            "fieldtype": "Link",
            "options": "Production Plan",
            "width": 150,
            "get_query": function() {
                return {
                    filters: { "docstatus": ["!=", 2] }
                }
            }
        },
        {
            "fieldname": "customer",
            "label": __("Customer"),
            "fieldtype": "Link",
            "options": "Customer",
            "width": 150
        },
       
        {
            "fieldname": "so_item_code",
            "label": __("Item Code"),
            "fieldtype": "Link",
            "options": "Item",
            "width": 150,
            "get_query": function() {
                return {
                    query: "erpnext.controllers.queries.item_query"
                }
            }
        },
        {
            "fieldname": "so_item_name",
            "label": __("Item Name"),
            "fieldtype": "Data",
            "width": 150
        },
        {
            "fieldname": "so_custom_batch_no",
            "label": __("Batch No (Sales Order)"),
            "fieldtype": "Link",
            "width": 150,
			"options": "Batch"
        },
		//  {
        //     "fieldname": "bom_custom_batch_no",
        //     "label": __("Batch No (BOM)"),
        //     "fieldtype": "Link",
        //     "width": 150,
		// 	"options": "Batch"
        // },
        {
            "fieldname": "bom_no",
            "label": __("BOM"),
            "fieldtype": "Link",
            "options": "BOM",
            "width": 150,
            "get_query": function() {
                return {
                    filters: {
                        "docstatus": ["!=", 2]
                    }
                }
            }
        },
        {
            "fieldname": "bom_status",
            "label": __("BOM Status"),
            "fieldtype": "MultiSelectList",
            "get_data": function() {
                return [
                    { value: "Draft", description: __("Draft BOMs") },
                    { value: "Submitted", description: __("Submitted BOMs") },
                    { value: "Not Available", description: __("BOMs Not Available") }
                ];
            },
            "width": 120
        }
    ],
    
    "tree": true,
    "name_field": "batch_no",
    "parent_field": "parent",
    "initial_depth": 0,
    "get_children": function(parent) {
        return frappe.query_report.data.filter(function(d) {
            return d.parent === parent;
        });
    },
    
    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        
        // Add icons based on type
        if (data && data.type) {
            let icon = "";
            if (data.is_group && column.fieldname === "batch_no") {
                icon = '<i class="fa fa-folder" style="margin-right: 5px;"></i>';
            } else if (data.type === "Production Plan" && column.fieldname === "production_plan") {
                icon = '<i class="fa fa-industry" style="margin-right: 5px; color: #137333;"></i>';
            } else if (data.type === "Sales Order" && column.fieldname === "sales_order") {
                icon = '<i class="fa fa-shopping-cart" style="margin-right: 5px; color: #1a73e8;"></i>';
            } else if (data.type === "BOM" && column.fieldname === "bom_no") {
                icon = '<i class="fa fa-cogs" style="margin-right: 5px; color: #d93025;"></i>';
            } else if (data.type === "BOM Item" && column.fieldname === "item_code") {
                icon = '<i class="fa fa-cube" style="margin-right: 5px; color: #666;"></i>';
            }
            value = `${icon}${value}`;
        }
        
        // Highlight rows based on BOM status
        if (column.fieldname == "bom_status") {
            if (value == "Submitted") {
                value = `<span style="color: green; font-weight: bold;">${value}</span>`;
            } else if (value == "Draft") {
                value = `<span style="color: orange; font-weight: bold;">${value}</span>`;
            } else if (value == "Not Available") {
                value = `<span style="color: gray; font-style: italic;">${value}</span>`;
            }
        }
        
        // Highlight Has BOM column
        if (column.fieldname == "has_bom") {
            if (value == "Yes") {
                value = `<span style="color: green; font-weight: bold;">${value}</span>`;
            } else if (value == "No") {
                value = `<span style="color: red; font-weight: bold;">${value}</span>`;
            }
        }
        

        // Type-specific styling
        if (data && data.type) {
            if (data.type === "Batch") {
                value = `<span style="font-weight: bold; color: #2c3e50;">${value}</span>`;
            } else if (data.type === "Production Plan") {
                value = `<span style="font-weight: 600; color: #137333;">${value}</span>`;
            } else if (data.type === "Sales Order") {
                value = `<span style="font-weight: 600; color: #1a73e8;">${value}</span>`;
            } else if (data.type === "BOM") {
                value = `<span style="font-weight: 600; color: #d93025;">${value}</span>`;
            } else if (data.type === "BOM Item") {
                value = `<span style="color: #666;">${value}</span>`;
            }
        }
        
        return value;
    },
    
    "onload": function(report) {
        report.page.add_inner_button(__("Export"), function() {
            frappe.query_report.export_report();
        });

        // Validate filters before refreshing the report
        report.page.set_primary_action(__("Refresh"), function() {
            let from_date = frappe.query_report.get_filter_value("from_date");
            let to_date = frappe.query_report.get_filter_value("to_date");
            
            if (!from_date || !to_date) {
                frappe.msgprint(__("Please select both From Date and To Date"));
                return;
            }
            if (from_date > to_date) {
                frappe.msgprint(__("From Date cannot be greater than To Date"));
                return;
            }
            frappe.query_report.refresh();
        });
    }
};
