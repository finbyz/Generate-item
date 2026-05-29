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
        if (!frm.doc.purchase_order_no) {
            frappe.msgprint(__("Please select Purchase Order first"));
            return;
        }

        frm.clear_table("items");
        frm.clear_table("original_record");
        fetch_items_dynamic(frm);
    },
    get_detail(frm) {
        if (!frm.doc.purchase_order_no) {
            frappe.msgprint(__("Please select Purchase Order first"));
            return;
        }
        get_detail_from_po(frm);
    }
});



function get_detail_from_po(frm) {
    if (!frm.doc.purchase_order_no) return;

    frappe.call({
        method: "frappe.client.get",
        freeze: true,
        freeze_message: __("Fetching order details..."),
        args: {
            doctype: "Purchase Order",
            name: frm.doc.purchase_order_no,
        },
        callback(r) {
            if (!r.message) return;

            const po = r.message;

            // --- Populate current (editable) fields ---
            frm.set_value("incoterm",                po.incoterm                  || null);
            frm.set_value("payment_terms_template",  po.payment_terms_template    || null);
            frm.set_value("terms",                   po.tc_name                   || null);
            frm.set_value("insurance",               po.custom_insurance          || null);
            frm.set_value("mode_of_dispatch",        po.custom_mode_of_dispatch   || null);
            frm.set_value("freight_charges",         po.freight_charges           || null);
            frm.set_value("po_remarks",              po.po_remarks                   || null);
            frm.set_value("group_same_items",        po.group_same_items          || null);

            // --- Populate history (read-only snapshot) fields ---
            frm.set_value("history_incoterm",                po.incoterm                  || null);
            frm.set_value("history_payment_terms_template",  po.payment_terms_template    || null);
            frm.set_value("history_terms",                   po.tc_name                   || null);
            frm.set_value("history_insurance",               po.custom_insurance          || null);
            frm.set_value("history_mode_of_dispatch",        po.custom_mode_of_dispatch   || null);
            frm.set_value("history_freight_charges",         po.freight_charges           || null);
            frm.set_value("history_po_remarks",              po.po_remarks                   || null);
            frm.set_value("history_group_same_items",        po.group_same_items          || null);


            frm.refresh();
        }
    });
}


function fetch_items_dynamic(frm) {
    if (!frm.doc.purchase_order_no) return;

    frappe.call({
        method: "frappe.client.get",
        freeze: true,
        freeze_message: __("Fetching items..."),
        args: {
            doctype: "Purchase Order",
            name: frm.doc.purchase_order_no,
        },
        callback(r) {
            if (!r.message) return;

            (r.message.items || []).forEach(item => {
                let row = frm.add_child("items");
                row.purchase_order_item_name    = item.name;
                row.item                        = item.item_code;
                row.qty                         = item.qty;
                row.batch_no                    = item.custom_batch_no || null;
                row.po_line_no                  = item.po_line_no || null;
                row.rate                        = item.rate;
                row.required_by                 = item.schedule_date || null;
                row.expected_delivery_date      = item.expected_delivery_date || null;
                row.remarks                     = item.remarks || null;
                row.stock_qty                   = item.stock_qty || 0;
                row.conversion_factor           = item.conversion_factor || 1;
                row.price_list_rate             = item.price_list_rate || 0;
                row.target_warehouse            = item.warehouse || null;
                row.item_tax_template           = item.item_tax_template || null;
                row.is_free_item                = item.is_free_item || 0;

                let history_row = frm.add_child("original_record");
                history_row.purchase_order_item_name    = item.name;
                history_row.item                        = item.item_code;
                history_row.qty                         = item.qty;
                history_row.batch_no                    = item.custom_batch_no || null;
                history_row.po_line_no                  = item.po_line_no || null;
                history_row.rate                        = item.rate;
                history_row.required_by                 = item.schedule_date || null;
                history_row.expected_delivery_date      = item.expected_delivery_date || null;
                history_row.remarks                     = item.remarks || null;
                history_row.stock_qty                   = item.stock_qty || 0;
                history_row.conversion_factor           = item.conversion_factor || 1;
                history_row.price_list_rate             = item.price_list_rate || 0;
                history_row.target_warehouse            = item.warehouse || null;
                history_row.item_tax_template           = item.item_tax_template || null;
                history_row.is_free_item                = item.is_free_item || 0;
            });

            frm.refresh_field("items");
            frm.refresh_field("original_record");
        }
    });
}