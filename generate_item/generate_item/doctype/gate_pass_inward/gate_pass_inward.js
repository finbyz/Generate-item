
// // Copyright (c) 2026, Finbyz and contributors
// // For license information, please see license.txt


frappe.ui.form.on("Gate Pass Inward", {

    onload(frm) {
        frm.set_query("gate_pass_outward", () => ({
            filters: { returnable: "Yes", docstatus: 1 }
        }));
    },

    gate_pass_outward(frm) {
        const gpo = frm.doc.gate_pass_outward;

        if (!gpo) {
            frm.set_value({ party_name: "", date: "", billing_status: "" });
            frm.clear_table("items");
            frm.clear_table("item_detail");
            frm.refresh_field("items");
            frm.refresh_field("item_detail");
            frm._gpo_pending    = {};
            frm._gpo_is_stock   = false;
            return;
        }

        // ── Step 1: Draft check ───────────────────────────────────────────────
        frappe.call({
            method        : "generate_item.generate_item.doctype.gate_pass_inward.gate_pass_inward.get_draft_inward_info",
            args          : { gate_pass_outward: gpo },
            freeze        : true,
            freeze_message: __("Checking pending inward entries…"),

            callback(res) {
                const info = res.message;

                if (info.has_draft && info.fully_covered) {
                    frappe.model.set_value(frm.doctype, frm.docname, "gate_pass_outward", "");
                    const links = info.draft_names
                        .map(n => `<a href="/app/gate-pass-inward/${n}">${n}</a>`)
                        .join(", ");
                    frappe.msgprint({
                        title    : __("Draft Gate Pass Inward Already Exists"),
                        message  : `The pending quantity of <b>${info.total_pending}</b>
                                    for <b>${gpo}</b> is already covered by:<br><br>
                                    ${links}<br><br>
                                    Please <b>submit the existing draft</b> instead.`,
                        indicator: "orange"
                    });
                    return;
                }

                // ── Step 2: Fetch GPO and populate ───────────────────────────
                frappe.call({
                    method        : "frappe.client.get",
                    args          : { doctype: "Gate Pass Outward", name: gpo },
                    freeze        : true,
                    freeze_message: __("Fetching Outward details…"),

                    callback(r) {
                        if (!r.message) {
                            frappe.msgprint(__("Could not fetch Gate Pass Outward: {0}", [gpo]));
                            return;
                        }

                        const outward    = r.message;
                        const is_stock   = !!outward.is_stock_item;
                        const all_items  = is_stock
                            ? (outward.item_detail || [])
                            : (outward.items || []);

                        // ── All received check ────────────────────────────────
                        const has_pending = all_items.some(i => (i.pending_qty || 0) > 0);
                        if (!has_pending) {
                            frappe.model.set_value(frm.doctype, frm.docname, "gate_pass_outward", "");
                            frappe.msgprint({
                                title    : __("Cannot Select Outward"),
                                message  : __(`All items in <b>${gpo}</b> have been
                                              fully received. No pending quantity remains.`),
                                indicator: "red"
                            });
                            return;
                        }

                        // ── Cache key → pending_qty for child triggers ────────
                        // key = item (stock) or sub_component (non-stock)
                        frm._gpo_is_stock = is_stock;
                        frm._gpo_pending  = {};
                        all_items.forEach(i => {
                            const key = is_stock ? i.item : i.sub_component;
                            frm._gpo_pending[key] = i.pending_qty || 0;
                        });

                        // ── Header ────────────────────────────────────────────
                        frm.set_value({
                            party_name    : outward.party_name,
                            date          : outward.date,
                            billing_status: "Without Bill",
                            is_stock_item : outward.is_stock_item,  // mirror flag
                            branch        : outward.branch
                        });

                        // ── Clear both child tables ───────────────────────────
                        frm.clear_table("items");
                        frm.clear_table("item_detail");

                        const pending_items = all_items.filter(i => (i.pending_qty || 0) > 0);

                        if (is_stock) {
                            // ── Stock: populate item_detail ───────────────────
                            pending_items.forEach(item => {
                                const row             = frm.add_child("item_detail");
                                row.item              = item.item;
                                row.qty               = item.pending_qty || 0;
                                row.sent_qty          = item.pending_qty || 0;
                                row.pending_qty       = item.pending_qty || 0;
                                row.rate              = item.rate || 0;
                                row.quality           = "Good";
                            });
                            frm.refresh_field("item_detail");

                        } else {
                            // ── Non-stock: populate items ─────────────────────
                            pending_items.forEach(item => {
                                const row         = frm.add_child("items");
                                row.sub_component = item.sub_component;
                                row.sent_qty      = item.pending_qty || 0;
                                row.pending_qty   = item.pending_qty || 0;
                                row.quality       = "Good";
                            });
                            frm.refresh_field("items");
                        }

                        frappe.show_alert({
                            message  : __("Data populated from {0}", [gpo]),
                            indicator: "green"
                        }, 4);
                    }
                });
            }
        });
    },
     default_target_warehouse(frm) {
        let transaction_controller = new erpnext.TransactionController();
        transaction_controller.autofill_warehouse(
            frm.doc.item_detail,
            "target_warehouse",
            frm.doc.default_target_warehouse
        );
        frm.refresh_field("item_detail");
    }
});

