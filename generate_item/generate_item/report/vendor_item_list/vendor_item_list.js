// Copyright (c) 2016, Finbyz Tech Pvt Ltd and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Vendor Item List"] = {
    "filters": [{
            "fieldname": "supplier",
            "label": __("Supplier"),
            "fieldtype": "Link",
            "options": "Supplier"
        },
        {
            "fieldname": "item_code",
            "label": __("Item"),
            "fieldtype": "Link",
            "options": "Item",
            "get_query": function() {
                return {
                    query: "erpnext.controllers.queries.item_query"
                }
            }
        },
    ]
};
$(document).ready(function() {

    // setTimeout(function() {
    //     console.log("ready!");
    //     $('.dt-row').css({ "top": "auto!important", "height": "auto!important", "position": "relative!important" });
    //     $('.dt-instance-1.dt-cell').css({ "height": "auto!important" });
    // }, 9000)
});