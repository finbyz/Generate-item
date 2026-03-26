// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt

frappe.ui.form.on("Bom Modification Request", {
	refresh(frm) {

	},
     setup(frm) {

        frm.set_query("bom", function () {
            let filters = {
                docstatus: 1,
                is_active: 1,
                
                
            };
            if (frm.doc.branch) {
                filters["branch"] = frm.doc.branch;
            }
            return { filters };
        });

    },
    get_item(frm) {
        
        if ( !frm.doc.bom ) {
            frappe.msgprint(`Please select BOM No first`);
            return;
        }
        

        fetch_items_dynamic(frm);
    },
   
    get_link_documents(frm) {
       
        if (!frm.doc.items || !frm.doc.items.length) {
            frappe.msgprint("Please add BOM Items first");
            return;
        }

        

        // Clear existing rows
        frm.clear_table("link_documents");

        frappe.call({
            method: "generate_item.generate_item.doctype.bom_modification_request.bom_modification_request.get_linked_documents",
            freeze: true,
            freeze_message: __("Fetching Linked Documents..."),
            args: {
                items:  frm.doc.items
            },
            callback: function (r) {
                if (!r.message) return;

                r.message.forEach(row => {
                    let child = frm.add_child("link_documents");
                    child.ref_doctype = row.ref_doctype;
                    child.document_no = row.document_no;
                    child.line_item = row.line_item;
                });

                frm.refresh_field("link_documents");
                // frappe.msgprint("Link Documents fetched");
            }
        });
    }

});



function fetch_items_dynamic(frm) {
    let ref_name;
   
    if (frm.doc.bom) {
        ref_name = frm.doc.bom;
    }
    frappe.call({
        method: "frappe.client.get",
        freeze: true,
        freeze_message: __("Fetching items..."),
        args: {
            doctype: "BOM",          //  dynamic doctype
            name: ref_name     //  dynamic document
        },
        callback(r) {
            if (!r.message) return;
            // BOM
            frm.clear_table("items");
            if (r.message.items ) {
                (r.message.items || []).forEach(item => {
                    let row = frm.add_child("items");
                    row.bom_item_name = item.name ;
                    row.item = item.item_code;
                    row.qty = item.qty;
                    row.rate = item.rate;
                    row.batch_no = item.custom_batch_no || null;
                    row.drawing_no = item.custom_drawing_no;
                    row.drawing_rev_no = item.custom_drawing_rev_no;
                    row.pattern_drawing_no = item.custom_pattern_drawing_no;
                    row.pattern_drawing_rev_no = item.custom_pattern_drawing_rev_no;
                    row.purchase_specification_no = item.custom_purchase_specification_no;
                    row.purchase_specification_rev_no = item.custom_purchase_specification_rev_no;

                });
                frm.refresh_field("items");
            }
        }
    });
}