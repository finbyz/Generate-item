// Copyright (c) 2025, Finbyz and contributors
// For license information, please see license.txt



frappe.ui.form.on("Order Modification Request", {
    setup(frm) {
        frm.set_query("sales_order", function () {
            return {
                filters: {
                    docstatus: 1,
                   
                }
            };
        });
        
    },
    
    get_item(frm) {
        if (!frm.doc.type) {
            frappe.msgprint("Please select Type first");
            return;
        }
    
        if (!frm.doc.sales_order && frm.doc.type == "Sales Order" ) {
            frappe.msgprint(`Please select Sales Order first`);
            return;
        }
    
        if (!frm.doc.bom && frm.doc.type == "BOM") {
            frappe.msgprint(`Please select BOM No first`);
            return;
        }
        frm.clear_table("items");
    
        fetch_items_dynamic(frm);
    },
    get_link_documents(frm) {
        console.log("get_link_documents called..")
        if (!frm.doc.items || !frm.doc.items.length) {
            frappe.msgprint("Please add items first");
            return;
        }
    
        // Clear existing rows
        frm.clear_table("link_documents");
    
        frappe.call({
            method: "generate_item.generate_item.doctype.order_modification_request.order_modification_request.get_linked_documents",
            freeze: true,
            freeze_message: __("Fetching Linked Documents..."),
            args: {
                items: frm.doc.items
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
    if (frm.doc.type === "Sales Order") {
        ref_name = frm.doc.sales_order;
    }
    if (frm.doc.type === "BOM") {
        ref_name = frm.doc.bom;
    }
    frappe.call({
        method: "frappe.client.get",
        freeze: true,
        freeze_message: __("Fetching items..."),
        args: {
            doctype: frm.doc.type,          //  dynamic doctype
            name: ref_name     //  dynamic document
        },
        callback(r) {
            if (!r.message) return;

            // Sales Order
            if (frm.doc.type === "Sales Order") {
                (r.message.items || []).forEach(item => {
                    let row = frm.add_child("items");
                    row.item = item.item_code;
                    row.qty = item.qty;
                    row.batch_no = item.custom_batch_no || null;
                    row.po_line_no = item.po_line_no;
                });
            }

            // BOM
            if (frm.doc.type === "BOM") {
                (r.message.items || []).forEach(item => {
                    let row = frm.add_child("items");
                    row.item = item.item_code;
                    row.qty = item.qty;
                    row.batch_no = item.custom_batch_no || null;
                   
                });
            }

            frm.refresh_field("items");
            // frappe.msgprint(`Items fetched from ${frm.doc.type}`);
        }
    });
}
