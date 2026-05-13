// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt

frappe.ui.form.on("Purchase Order Modification Request", {
	
    
    setup(frm) {

        frm.set_query("purchase_order_no", function () {
            let filters = {};
            if (frm.doc.branch) {
                filters["branch"] = frm.doc.branch;
            }
            return { filters };
        });

    },
     get_item(frm) {
        

        if ( !frm.doc.purchase_order_no ) {
            frappe.msgprint(`Please select Purchase Order first`);
            return;
        }

        frm.clear_table("items");
        frm.clear_table("original_record");

        fetch_items_dynamic(frm);
    },
});




function fetch_items_dynamic(frm) {
    let ref_name;
    if (frm.doc.purchase_order_no) {
        ref_name = frm.doc.purchase_order_no;
    }
    
    frappe.call({
        method: "frappe.client.get",
        freeze: true,
        freeze_message: __("Fetching items..."),
        args: {
            doctype: "Purchase Order",          //  dynamic doctype
            name: ref_name     //  dynamic document
        },
        callback(r) {
            if (!r.message) return;

            // Purchase Order
            if (frm.doc.purchase_order_no) {

                (r.message.items || []).forEach(item => {
                    let row = frm.add_child("items");
                    row.purchase_order_item_name = item.name;
                    row.item = item.item_code;
                    row.qty = item.qty;
                    row.batch_no = item.custom_batch_no || null;
                    row.po_line_no = item.po_line_no;
                    row.rate = item.rate;
                    row.required_by = item.schedule_date || null;
                    row.is_free_item = item.is_free_item || 0;


                    let history_row = frm.add_child("original_record");
                    history_row.purchase_order_item_name = item.name;
                    history_row.item = item.item_code;
                    history_row.qty = item.qty;
                    history_row.batch_no = item.custom_batch_no || null;
                    history_row.po_line_no = item.po_line_no;
                    history_row.rate = item.rate;

                  
                    history_row.required_by = item.schedule_date || null;
                    history_row.is_free_item = item.is_free_item || 0;
           

                });
                frm.refresh_field("items");
                frm.refresh_field("original_record");
            }

           


        }
    });
}


