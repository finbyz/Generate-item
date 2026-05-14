 // Copyright (c) 2026, Finbyz and contributors
 // For license information, please see license.txt


frappe.ui.form.on("Gate Pass Outward", {

    onload(frm) {
        frm.set_query("item", "item_detail", () => ({
            filters: { is_stock_item: 1 }
        }));
    },

    refresh(frm) {
        if (frm.doc.docstatus !== 1) return;
        if (frm.doc.returnable !== "Yes") return;

        frm.add_custom_button(
            __("Gate Pass Inward"),
            () => _handle_create_inward(frm),
            __("Create")
        );
    },

    default_source_warehouse(frm) {
        let transaction_controller = new erpnext.TransactionController();
        transaction_controller.autofill_warehouse(
            frm.doc.item_detail,
            "source_warehouse",
            frm.doc.default_source_warehouse
        );
        frm.refresh_field("item_detail");
    }
});

// ── Child table triggers ─────────────────────────────────────────────────────

frappe.ui.form.on("Gate Pass Outward Item", {
    qty(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.qty) {
            frappe.model.set_value(cdt, cdn, "pending_qty", row.qty);
        }
    }
});

frappe.ui.form.on("Gate Pass Outward Detail", {
    qty(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.qty) {
            frappe.model.set_value(cdt, cdn, "pending_qty", row.qty);
        }
    }
});

// ── Inward creation flow ─────────────────────────────────────────────────────

function _handle_create_inward(frm) {
    const is_stock   = !!frm.doc.is_stock_item;
    const all_items  = is_stock
        ? (frm.doc.item_detail || [])
        : (frm.doc.items || []);

    // pending_qty > 0 filter
    const pending_items = all_items.filter(i => (i.pending_qty || 0) > 0);

    if (!pending_items.length) {
        frappe.msgprint({
            title    : __("Cannot Create Inward"),
            message  : __(`All items in <b>${frm.doc.name}</b> have been fully 
                           received. No pending quantity remains.`),
            indicator: "red"
        });
        return;
    }

    // Draft-check before showing confirm dialog
    frappe.call({
        method  : "generate_item.generate_item.doctype.gate_pass_inward.gate_pass_inward.get_draft_inward_info",
        args    : { gate_pass_outward: frm.doc.name },
        callback(res) {
            const info = res.message;

            if (info.has_draft && info.fully_covered) {
                const links = info.draft_names
                    .map(n => `<a href="/app/gate-pass-inward/${n}">${n}</a>`)
                    .join(", ");
                frappe.msgprint({
                    title    : __("Draft Gate Pass Inward Already Exists"),
                    message  : `The remaining pending quantity of <b>${info.total_pending}</b>
                                is already covered by:<br><br>${links}<br><br>
                                Please <b>submit the existing draft</b> instead.`,
                    indicator: "orange"
                });
                return;
            }

            frappe.confirm(
                __(`Create Gate Pass Inward for <b>${frm.doc.name}</b>?`),
                () => _build_inward_doc(frm, pending_items, is_stock)
            );
        }
    });
}

function _build_inward_doc(frm, pending_items, is_stock) {
    frappe.model.with_doctype("Gate Pass Inward", () => {

        const new_name = frappe.model.make_new_doc_and_get_name("Gate Pass Inward");
        const doc      = frappe.get_doc("Gate Pass Inward", new_name);

        // ── Header ───────────────────────────────────────────────────────────
        doc.gate_pass_outward = frm.doc.name;
        doc.party_name        = frm.doc.party_name;
        doc.date              = frm.doc.date;
        doc.billing_status    = "Without Bill";
        doc.is_stock_item     = frm.doc.is_stock_item;  // carry flag to inward
        doc.branch = frm.doc.branch;

        // ── Clear default empty row ───────────────────────────────────────────
        doc.item_detail = [];
        doc.items       = [];

        if (is_stock) {
            // ── Stock items → populate item_detail child ──────────────────────
            pending_items.forEach(item => {
                const pending = item.pending_qty || 0;
                const row = frappe.model.add_child(doc, "Gate Pass Inward Detail", "item_detail");
                row.item              = item.item;
               
                row.sent_qty          = pending;
                row.pending_qty       = pending;
                row.qty               = pending;
                row.rate              = item.rate || 0;
                row.quality           = "Good";
            });
        } else {
            // ── Non-stock items → populate items child ────────────────────────
            pending_items.forEach(item => {
                const pending = item.pending_qty || 0;
                const row = frappe.model.add_child(doc, "Gate Pass Inward Item", "items");
                row.sub_component = item.sub_component;
                row.sent_qty      = pending;
                row.pending_qty   = pending;
                row.quality       = "Good";
            });
        }

        frappe.set_route("Form", "Gate Pass Inward", new_name);
    });
}


// ── Purchase Order creation (unchanged) ─────────────────────────────────────

function open_service_item_picker(frm) {
    frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype          : "Item",
            filters          : [["is_stock_item", "=", 0]],
            fields           : ["name", "item_name", "item_group", "stock_uom", "description"],
            limit_page_length: 500
        },
        freeze        : true,
        freeze_message: __("Fetching service items…"),
        callback(r) {
            if (!r.message || !r.message.length) {
                frappe.msgprint(__("No service items found (maintain stock = 0)."));
                return;
            }
            show_item_picker_dialog(frm, r.message);
        }
    });
}

function show_item_picker_dialog(frm, service_items) {
    const sub_components = (frm.doc.items || []).map(i => i.sub_component).filter(Boolean);

    const rows_html = service_items.map(item => `
        <div class="gpo-item-row row"
             style="padding:6px 0; border-bottom:1px solid var(--border-color);">
            <div class="col-1">
                <input type="checkbox" class="item-checkbox"
                       data-item="${item.name}" style="margin-top:4px;">
            </div>
            <div class="col-4" style="font-weight:500;">${item.name}</div>
            <div class="col-4" style="color:var(--text-muted);">${item.item_name || ""}</div>
            <div class="col-3" style="color:var(--text-muted);">${item.item_group || ""}</div>
        </div>
    `).join("");

    const dialog = new frappe.ui.Dialog({
        title : __("Select Service Items for Purchase Order"),
        size  : "large",
        fields: [{
            fieldtype: "HTML",
            fieldname: "item_list",
            options  : `
                <input id="gpo-search" type="text" class="form-control"
                       placeholder="Search…" style="margin-bottom:8px;">
                <div style="display:flex;gap:8px;margin-bottom:8px;">
                    <button class="btn btn-xs btn-default" id="gpo-sel-all">Select All</button>
                    <button class="btn btn-xs btn-default" id="gpo-clr-all">Clear All</button>
                </div>
                <div class="row" style="font-weight:bold;padding:4px 0;
                     border-bottom:2px solid var(--border-color);">
                    <div class="col-1"></div>
                    <div class="col-4">Item Code</div>
                    <div class="col-4">Item Name</div>
                    <div class="col-3">Item Group</div>
                </div>
                <div id="gpo-item-list" style="max-height:360px;overflow-y:auto;">
                    ${rows_html}
                </div>`
        }],
        primary_action_label: __("Create Purchase Order"),
        primary_action() {
            const selected = [];
            dialog.$wrapper.find(".item-checkbox:checked").each(function () {
                selected.push($(this).data("item"));
            });
            if (!selected.length) {
                frappe.msgprint(__("Please select at least one service item."));
                return;
            }
            dialog.hide();
            create_purchase_order(frm, selected, sub_components, service_items);
        }
    });

    dialog.show();

    dialog.$wrapper.find("#gpo-search").on("input", function () {
        const q = $(this).val().toLowerCase();
        dialog.$wrapper.find(".gpo-item-row").each(function () {
            $(this).toggle($(this).text().toLowerCase().includes(q));
        });
    });
    dialog.$wrapper.find("#gpo-sel-all").on("click", () =>
        dialog.$wrapper.find(".item-checkbox:visible").prop("checked", true));
    dialog.$wrapper.find("#gpo-clr-all").on("click", () =>
        dialog.$wrapper.find(".item-checkbox").prop("checked", false));
}

function create_purchase_order(frm, selected_items, sub_components, all_service_items) {
    const item_map = {};
    all_service_items.forEach(i => { item_map[i.name] = i; });

    frappe.model.with_doctype("Purchase Order", () => {
        const new_name = frappe.model.make_new_doc_and_get_name("Purchase Order");
        const doc      = frappe.get_doc("Purchase Order", new_name);

        doc.supplier           = frm.doc.party_name;
        doc.gate_pass_outword  = frm.doc.name;
        doc.items              = [];

        selected_items.forEach((item_code, idx) => {
            const row = frappe.model.add_child(doc, "Purchase Order Item", "items");
            row.item_code             = item_code;
            row.item_name             = item_map[item_code]?.item_name || item_code;
            row.description           = item_map[item_code]?.description || "";
            row.qty                   = 1;
            row.uom                   = item_map[item_code]?.stock_uom || "Nos";
            row.stock_uom             = item_map[item_code]?.stock_uom || "Nos";
            row.conversion_factor     = 1;
            row.rate                  = 0;
            row.asset_subcomponent    = sub_components[idx] || sub_components[0] || "";
        });

        frappe.set_route("Form", "Purchase Order", new_name);
    });
}