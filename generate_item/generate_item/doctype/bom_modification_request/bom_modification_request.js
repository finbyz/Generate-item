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
    bom(frm) {
        if (!frm.doc.bom) return;

        // Call to fetch BOM details
        frappe.call({
            method: "frappe.client.get",
            args: {
                doctype: "BOM",
                name: frm.doc.bom
            },
            callback: function(r) {
                if (!r.message) return;

                let bom = r.message;

                //  Set FG Item (Finished Good)
                frm.set_value("fg_item_code", bom.item);
                // Set Item Name & Description
                frm.set_value("fg_item_name", bom.item_name);
                frm.set_value("item_description", bom.description);
                frm.set_value("batch_no_ref", bom.custom_batch_no || "");

               
            }
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
                    row.item_description = item.description;
                    row.uom = item.uom;
                    row.do_not_explode = item.do_not_explode;
                    row.rev_do_not_explode = item.do_not_explode;
                    row.bom_no = item.bom_no;
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



frappe.ui.form.on('Order Modification Request Detail', {
    rev_item: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        //  Clear old values FIRST (VERY IMPORTANT)
        let fields_to_clear = [
            "rev_rate",
            "rev_drawing_no",
            "rev_drawing_rev_no",
            "rev_pattern_drawing_no",
            "rev_pattern_drawing_rev_no",
            "rev_purchase_specification_no",
            "rev_purchase_specification_rev_no"
        ];

        fields_to_clear.forEach(field => {
            frappe.model.set_value(cdt, cdn, field, "");
        });

        if (!row.rev_item) return;

        // Fetch Item Price
        frappe.db.get_value(
            "Item Price",
            {
                item_code: row.rev_item,
                price_list: frm.doc.selling_price_list
            },
            "price_list_rate"
        ).then(r => {
            if (r.message && r.message.price_list_rate) {
                frappe.model.set_value(cdt, cdn, "rev_rate", r.message.price_list_rate);
            }
        });

        //  Fetch Item Master Data
        frappe.db.get_value(
            "Item",
            row.rev_item,
            [
                "custom_drawing_no",
                "custom_drawing_rev_no",
                "custom_pattern_drawing_no",
                "custom_pattern_drawing_rev_no",
                "custom_purchase_specification_no",
                "custom_purchase_specification_rev_no"
            ]
        ).then(r => {
            if (r.message) {
                let d = r.message;

                frappe.model.set_value(cdt, cdn, {
                    "rev_drawing_no": d.custom_drawing_no || "",
                    "rev_drawing_rev_no": d.custom_drawing_rev_no || "",
                    "rev_pattern_drawing_no": d.custom_pattern_drawing_no || "",
                    "rev_pattern_drawing_rev_no": d.custom_pattern_drawing_rev_no || "",
                    "rev_purchase_specification_no": d.custom_purchase_specification_no || "",
                    "rev_purchase_specification_rev_no": d.custom_purchase_specification_rev_no || ""
                });
            }
        });
    }
});