// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt




frappe.query_reports["OMR Item Change"] = {
    "filters": [
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1)
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today()
        },
        {
            "fieldname": "omr_number",
            "label": __("OMR Number"),
            "fieldtype": "Link",
            "options": "Order Modification Request"
        },
        {
            "fieldname": "customer",
            "label": __("Customer"),
            "fieldtype": "Link",
			"options":"Customer"
        },
        {
            "fieldname": "branch",
            "label": __("Branch"),
            "fieldtype": "Link",
            "options": "Branch"
        },
        {
            "fieldname": "status",
            "label": __("OMR Status"),
            "fieldtype": "MultiSelectList",
            "get_data": function() {
                return [
					{value: "Draft", description: "Draft"},
                    {value: "Checking Pending", description: "Checking Pending"},
					{value:"Approval Pending",description:"Approval Pending"},
                    {value: "Approved", description: "Approved"},
					
                   
                ]
            }
        }
    ]
};