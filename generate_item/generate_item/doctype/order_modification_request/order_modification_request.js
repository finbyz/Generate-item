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

        if (!frm.doc.sales_order && frm.doc.type == "Sales Order") {
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
                    row.sales_order_item_name = item.name;
                    row.item = item.item_code;
                    row.qty = item.qty;
                    row.batch_no = item.custom_batch_no || null;
                    row.po_line_no = item.po_line_no;
                    row.rate = item.rate;

                    let history_row = frm.add_child("original_record");
                    history_row.sales_order_item_name = item.name;
                    history_row.item = item.item_code;
                    history_row.qty = item.qty;
                    history_row.batch_no = item.custom_batch_no || null;
                    history_row.po_line_no = item.po_line_no;
                    history_row.rate = item.rate;

                });
            }

            // BOM
            if (frm.doc.type === "BOM") {
                (r.message.items || []).forEach(item => {
                    let row = frm.add_child("items");
                    row.item = item.item_code;
                    row.qty = item.qty;
                    row.batch_no = item.custom_batch_no || null;
                    row.drawing_no = item.custom_drawing_no;
                    row.drawing_rev_no = item.custom_drawing_rev_no;
                    row.pattern_drawing_no = item.custom_pattern_drawing_no;
                    row.pattern_drawing_rev_no = item.custom_pattern_drawing_rev_no;
                    row.purchase_specification_no = item.custom_purchase_specification_no;
                    row.purchase_specification_rev_no = item.custom_purchase_specification_rev_no;

                    let history_row = frm.add_child("original_record");
                    history_row.item = item.item_code;
                    history_row.qty = item.qty;
                    history_row.batch_no = item.custom_batch_no || null;
                    history_row.drawing_no = item.custom_drawing_no;
                    history_row.drawing_rev_no = item.custom_drawing_rev_no;
                    history_row.pattern_drawing_no = item.custom_pattern_drawing_no;
                    history_row.pattern_drawing_rev_no = item.custom_pattern_drawing_rev_no;
                    history_row.purchase_specification_no = item.custom_purchase_specification_no;
                    history_row.purchase_specification_rev_no = item.custom_purchase_specification_rev_no;
                });
            }

            frm.refresh_field("items");
            frm.refresh_field("original_record");
            // frappe.msgprint(`Items fetched from ${frm.doc.type}`);
        }
    });
}


frappe.ui.form.on('Order Modification Request Detail', {
    item: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        if (!row.item) return;

        frappe.db.get_value(
            "Item Price",
            {
                item_code: row.item,
                price_list: frm.doc.selling_price_list
            },
            "price_list_rate",
            function (r) {
                if (r && r.price_list_rate) {
                    frappe.model.set_value(cdt, cdn, "rev_rate", r.price_list_rate);
                }
            }
        );
    }
});