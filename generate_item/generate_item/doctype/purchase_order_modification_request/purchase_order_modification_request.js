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
            frm.set_value("incoterm", po.incoterm || null);
            frm.set_value("payment_terms_template", po.payment_terms_template || null);
            frm.set_value("terms", po.tc_name || null);
            frm.set_value("insurance", po.custom_insurance || null);
            frm.set_value("mode_of_dispatch", po.custom_mode_of_dispatch || null);
            frm.set_value("freight_charges", po.freight_charges || null);
            frm.set_value("po_remarks", po.po_remarks || null);
            frm.set_value("group_same_items", po.group_same_items || null);

            // --- Populate history (read-only snapshot) fields ---
            frm.set_value("history_incoterm", po.incoterm || null);
            frm.set_value("history_payment_terms_template", po.payment_terms_template || null);
            frm.set_value("history_terms", po.tc_name || null);
            frm.set_value("history_insurance", po.custom_insurance || null);
            frm.set_value("history_mode_of_dispatch", po.custom_mode_of_dispatch || null);
            frm.set_value("history_freight_charges", po.freight_charges || null);
            frm.set_value("history_po_remarks", po.po_remarks || null);
            frm.set_value("history_group_same_items", po.group_same_items || null);


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
                let message =  frappe.db.get_value("Item", item.item_code,"description");
                row.purchase_order_item_name = item.name;
                row.item = item.item_code;
                row.qty = item.qty;
                row.uom = item.uom;
                row.stock_uom = item.stock_uom;
                row.rev_uom = item.uom;
                row.rev_stock_uom = item.stock_uom;
                row.description = item.description || (message.description || "").replace(/<[^>]*>/g, '');
               
                
                row.batch_no = item.custom_batch_no || null;
                row.po_line_no = item.po_line_no || null;
                row.rate = item.rate;
                row.required_by = item.schedule_date || null;
                row.line_status = item.line_status || null;
                row.expected_delivery_date = item.expected_delivery_date || null;
                row.remarks = item.remarks || null;
                row.stock_qty = item.stock_qty || 0;
                row.conversion_factor = item.conversion_factor || 1;
                row.price_list_rate = item.price_list_rate || 0;
                row.target_warehouse = item.warehouse || null;
                row.item_tax_template = item.item_tax_template || null;
                row.is_free_item = item.is_free_item || 0;

                let history_row = frm.add_child("original_record");
                history_row.purchase_order_item_name = item.name;
                history_row.item = item.item_code;
                history_row.qty = item.qty;
                history_row.uom = item.uom;
                history_row.stock_uom = item.stock_uom;
                history_row.rev_uom = item.uom;
                history_row.rev_stock_uom = item.stock_uom;
                
                history_row.batch_no = item.custom_batch_no || null;
                history_row.po_line_no = item.po_line_no || null;
                history_row.rate = item.rate;
                history_row.required_by = item.schedule_date || null;
                history_row.line_status = item.line_status || null;
                history_row.expected_delivery_date = item.expected_delivery_date || null;
                history_row.remarks = item.remarks || null;
                history_row.stock_qty = item.stock_qty || 0;
                history_row.conversion_factor = item.conversion_factor || 1;
                history_row.price_list_rate = item.price_list_rate || 0;
                history_row.target_warehouse = item.warehouse || null;
                history_row.item_tax_template = item.item_tax_template || null;
                history_row.is_free_item = item.is_free_item || 0;
            });

            frm.refresh_field("items");
            frm.refresh_field("original_record");
        }
    });
}
frappe.ui.form.on("Purchase Order Modification Request Detail", {
    rev_item(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.rev_item) return;

        frappe.db.get_value("Item", row.rev_item, ["stock_uom","description"])
            .then(({ message }) => {
                if (!message) return;
              

                frappe.model.set_value(cdt, cdn, "rev_uom", message.stock_uom);
                frappe.model.set_value(cdt, cdn, "rev_stock_uom", message.stock_uom);
                frappe.model.set_value(cdt, cdn, "rev_description", (message.description || "").replace(/<[^>]*>/g, ''));  

                // Recalculate conversion factor whenever UOM is (re)set
                calculate_rev_conversion_factor(frm, cdt, cdn);
            });
    },

    rev_uom(frm, cdt, cdn) {
        calculate_rev_conversion_factor(frm, cdt, cdn);
    },

    rev_qty(frm, cdt, cdn) {
        calculate_rev_conversion_factor(frm, cdt, cdn);
    },

    rev_stock_qty(frm, cdt, cdn) {
        calculate_rev_conversion_factor(frm, cdt, cdn);
    },
    rev_conversion_factor(frm, cdt, cdn){
        const row = locals[cdt][cdn];
        if (!row.rev_conversion_factor) return;
        frappe.model.set_value(
        cdt,
        cdn,
        "rev_stock_qty",
        flt(row.rev_qty * row.rev_conversion_factor)
    );
    }
});


function calculate_rev_conversion_factor(frm, cdt, cdn) {
    const row = locals[cdt][cdn];

    let conversion_factor = 1;

    if (row.rev_uom && row.rev_stock_uom) {
        if (row.rev_uom === row.rev_stock_uom) {
            conversion_factor = 1;
        } else if (flt(row.rev_qty) !== 0) {
            conversion_factor = flt(row.rev_stock_qty, 9) / flt(row.rev_qty, 9);
        } else {
            conversion_factor = 0;
        }
    }

    frappe.model.set_value(
        cdt,
        cdn,
        "rev_conversion_factor",
        flt(conversion_factor, 9)
    );
}
