// Copyright (c) 2025, Finbyz and contributors
// For license information, please see license.txt



frappe.ui.form.on("Order Modification Request", {
    refresh: function (frm) {
        toggle_drg_section(frm);
        hide_child_table_delete_buttons(frm);
    },

    type: function (frm) {
        toggle_drg_section(frm);
    },
    setup(frm) {

        frm.set_query("sales_order", function () {
            let filters = {
                docstatus: 1,
                status: ["in", ["To Deliver and Bill", "To Deliver"]],
            };
            if (frm.doc.branch) {
                filters["branch"] = frm.doc.branch;
            }
            return { filters };
        });

    },
    branch(frm) {
        // Clear sales_order when branch changes so stale value doesn't stay
        frm.set_value("sales_order", null);
        frm.refresh_field("sales_order");
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
        if (frm.doc.type === "Sales Order") {
            frm.clear_table("sales_order_item");
        } else {
            frm.clear_table("items");
        }
        frm.clear_table("original_record");

        fetch_items_dynamic(frm);
    },
    get_link_documents(frm) {
        if (!frm.doc.type) {
            frappe.msgprint("Please select Type first");
            return;
        }

        // SALES ORDER CASE
        if (frm.doc.type === "Sales Order") {

            if (!frm.doc.sales_order_item || !frm.doc.sales_order_item.length) {
                frappe.msgprint("Please add Sales Order Items first");
                return;
            }

        }

        // BOM CASE
        else if (frm.doc.type === "BOM") {

            if (!frm.doc.items || !frm.doc.items.length) {
                frappe.msgprint("Please add BOM Items first");
                return;
            }

        }

        // Clear existing rows
        frm.clear_table("link_documents");

        frappe.call({
            method: "generate_item.generate_item.doctype.order_modification_request.order_modification_request.get_linked_documents",
            freeze: true,
            freeze_message: __("Fetching Linked Documents..."),
            args: {
                items: (frm.doc.type === "Sales Order") ? frm.doc.sales_order_item : frm.doc.items
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


function hide_child_table_delete_buttons(frm) {
    
    $(frm.fields_dict['sales_order_item'].grid.wrapper)
        .find('.grid-delete-row, .btn-open-row')
        .hide();
    
    $(frm.fields_dict['sales_order_item'].grid.wrapper)
        .find('[data-action="delete_rows"]')
        .hide();
    
    frm.fields_dict['sales_order_item'].grid.can_delete = false;
    frm.fields_dict['sales_order_item'].grid.refresh();
}


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
                    let row = frm.add_child("sales_order_item");
                    row.sales_order_item_name = item.name;
                    row.item = item.item_code;
                    row.qty = item.qty;
                    row.batch_no = item.custom_batch_no || null;
                    row.po_line_no = item.po_line_no;
                    row.rate = item.rate;

                    // Additional required fields
                    row.line_status = item.line_status || null;
                    row.delivery_date = item.delivery_date || null;
                    row.tag_no = item.tag_no || null;
                    row.line_remark = item.line_remark || null;
                    row.shipping_address = item.custom_shipping_address || null;
                    row.is_free_item = item.is_free_item || 0;
                    row.component_of = item.component_of || null;

                    let history_row = frm.add_child("original_record");
                    history_row.sales_order_item_name = item.name;
                    history_row.item = item.item_code;
                    history_row.qty = item.qty;
                    history_row.batch_no = item.custom_batch_no || null;
                    history_row.po_line_no = item.po_line_no;
                    history_row.rate = item.rate;

                    history_row.line_status = item.line_status || null;
                    history_row.delivery_date = item.delivery_date || null;
                    history_row.tag_no = item.tag_no || null;
                    history_row.line_remark = item.line_remark || null;
                    history_row.shipping_address = item.custom_shipping_address || null;
                    history_row.is_free_item = item.is_free_item || 0;
                    history_row.component_of = item.component_of || null;

                });
                  frm.refresh_field("sales_order_item");
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
                frm.refresh_field("items");
            }

            
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


function toggle_drg_section(frm) {
    let hide_section = frm.doc.type === "Sales Order";

    if (frm.fields_dict.items) {
        frm.fields_dict.items.grid.update_docfield_property(
            "drg_and_pur_spec_section",
            "hidden",
            hide_section ? 1 : 0
        );
    }

    frm.refresh_field("items");
}