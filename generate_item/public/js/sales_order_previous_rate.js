frappe.ui.form.on("Sales Order", {
    refresh(frm) {

        frm.add_custom_button(__("Previous Sales Rates"), async function () {

            if (!frm.doc.customer) {
                frappe.msgprint(__("Please select a Customer first."));
                return;
            }

            let items = (frm.doc.items || [])
                .filter(row => row.item_code)
                .map(row => row.item_code);

            if (!items.length) {
                frappe.msgprint(__("Please add at least one Item."));
                return;
            }

            // ── Currency formatter ─────────────────────────────────────────────
            // format_currency() is a Frappe global (number_format.js), always available.
            // Falls back to plain number if somehow unavailable.
            const fmt = (val) => {
                try {
                    return format_currency(flt(val), frappe.boot.sysdefaults.currency);
                } catch (_) {
                    return flt(val).toFixed(2);
                }
            };

            frappe.show_progress(__("Loading..."), 0, 100, __("Fetching rate history..."));

            try {
                // ── 1. Sales Invoice Items ────────────────────────────────────────
                let si_items = await frappe.db.get_list("Sales Invoice Item", {
                    fields: ["item_code", "rate", "parent", "creation"],
                    filters: { item_code: ["in", items] },
                    order_by: "creation desc",
                    limit: 500
                });

                frappe.show_progress(__("Loading..."), 20, 100);

                // ── 2. Invoice → Customer map (one batched call) ──────────────────
                let unique_invoices = [...new Set(si_items.map(d => d.parent))];
                let invoice_customer_map = {};

                if (unique_invoices.length) {
                    let invoices = await frappe.db.get_list("Sales Invoice", {
                        fields: ["name", "customer"],
                        filters: { name: ["in", unique_invoices] },
                        limit: unique_invoices.length + 1
                    });
                    invoices.forEach(inv => {
                        invoice_customer_map[inv.name] = inv.customer;
                    });
                }

                frappe.show_progress(__("Loading..."), 40, 100);

                // ── 3. Quotation Items — same customer only ───────────────────────

                let quotations = await frappe.db.get_list("Quotation", {
                    fields: ["name", "party_name"],
                    filters: {
                        quotation_to: "Customer",
                        party_name: frm.doc.customer,
                        docstatus: 1
                    },
                    limit: 500
                });
                
                let quotation_names = quotations.map(q => q.name);
                
                let quot_result = [];
                
                if (quotation_names.length) {
                
                    quot_result = await frappe.db.get_list("Quotation Item", {
                        fields: ["parent", "item_code", "rate", "creation"],
                        filters: {
                            parent: ["in", quotation_names],
                            item_code: ["in", items]
                        },
                        order_by: "creation desc",
                        limit: 200
                    });
                }
                
                let quotation_map = {};
                
                items.forEach(item => {
                    quotation_map[item] = quot_result
                        .filter(d => d.item_code === item)
                        .slice(0, 10);
                });

                frappe.show_progress(__("Loading..."), 60, 100);

                // ── 4. Purchase Invoice Items ─────────────────────────────────────
                let pur_items = await frappe.db.get_list("Purchase Invoice Item", {
                    fields: ["parent", "item_code", "rate", "creation"],
                    filters: { item_code: ["in", items] },
                    order_by: "creation desc",
                    limit: 100
                });

                let purchase_map = {};
                items.forEach(item => {
                    purchase_map[item] = pur_items
                        .filter(d => d.item_code === item)
                        .slice(0, 5);
                });

                frappe.show_progress(__("Loading..."), 80, 100);

                // ── 5. Valuation Rate + Item Name ─────────────────────────────────
                let valuation_map = {};
                for (let item of items) {
                    let res = await frappe.db.get_value("Item", item, [
                        "valuation_rate",
                        "item_name"
                    ]);
                    valuation_map[item] = res.message || {};
                }

                frappe.hide_progress();

                // ── 6. Build HTML ─────────────────────────────────────────────────
                const tableRow = (cells) =>
                    `<tr>${cells.map(c => `<td>${c}</td>`).join("")}</tr>`;

                const emptyRow = (cols) =>
                    `<tr><td colspan="${cols}" class="psr-empty">No records found</td></tr>`;

                let html = `
                    <style>
                        .psr-wrapper { font-family: inherit; padding: 4px 2px; }
                        .psr-item-block {
                            margin-bottom: 28px;
                            border: 1px solid #e2e8f0;
                            border-radius: 8px;
                            overflow: hidden;
                        }
                        .psr-item-header {
                            background: #2d3748;
                            color: #fff;
                            padding: 10px 16px;
                            font-size: 14px;
                            font-weight: 700;
                        }
                        .psr-section {
                            padding: 12px 16px;
                            border-bottom: 1px solid #edf2f7;
                        }
                        .psr-section:last-child { border-bottom: none; }
                        .psr-section-title {
                            font-size: 11.5px;
                            font-weight: 700;
                            text-transform: uppercase;
                            letter-spacing: 0.6px;
                            color: #4a5568;
                            margin-bottom: 8px;
                        }
                        .psr-badge {
                            display: inline-block;
                            background: #ebf8ff;
                            color: #2b6cb0;
                            border-radius: 4px;
                            padding: 1px 7px;
                            font-size: 11px;
                            font-weight: 600;
                            margin-left: 6px;
                            text-transform: none;
                            letter-spacing: 0;
                        }
                        .psr-table {
                            width: 100%;
                            border-collapse: collapse;
                            font-size: 12.5px;
                        }
                        .psr-table th {
                            background: #f7fafc;
                            color: #718096;
                            font-weight: 600;
                            text-align: left;
                            padding: 6px 10px;
                            border: 1px solid #e2e8f0;
                            font-size: 11.5px;
                        }
                        .psr-table td {
                            padding: 6px 10px;
                            border: 1px solid #e2e8f0;
                            color: #2d3748;
                        }
                        .psr-table tr:hover td { background: #f7fafc; }
                        .psr-rate { font-weight: 600; color: #276749; }
                        .psr-empty { color: #a0aec0; font-style: italic; font-size: 12px; }
                    </style>
                    <div class="psr-wrapper">
                `;

                for (let item of items) {
                    let vmap       = valuation_map[item] || {};
                    let item_label = vmap.item_name ? `${item} — ${vmap.item_name}` : item;
                    let val_rate   = vmap.valuation_rate || 0;

                    let same_cust = si_items.filter(
                        d => d.item_code === item &&
                             invoice_customer_map[d.parent] === frm.doc.customer
                    );
                    let other_cust = si_items.filter(
                        d => d.item_code === item &&
                             invoice_customer_map[d.parent] !== frm.doc.customer
                    );
                    let quot_rows = quotation_map[item] || [];
                    let pur_rows  = purchase_map[item]  || [];

                    const rateCell = (rate) =>
                        `<span class="psr-rate">${fmt(rate)}</span>`;

                    const docLink = (doctype_slug, name) =>
                        `<a href="/app/${doctype_slug}/${encodeURIComponent(name)}" target="_blank">${name}</a>`;

                    html += `
                        <div class="psr-item-block">
                            <div class="psr-item-header">${item_label}</div>

                            <div class="psr-section">
                                <div class="psr-section-title">
                                    1. Previous Sales Rate — Same Customer
                                    <span class="psr-badge">${frm.doc.customer}</span>
                                </div>
                                <table class="psr-table">
                                    <tr><th>Sales Invoice</th><th>Rate</th><th>Date</th></tr>
                                    ${same_cust.length
                                        ? same_cust.map(d => tableRow([
                                            docLink("sales-invoice", d.parent),
                                            rateCell(d.rate),
                                            frappe.datetime.str_to_user(d.creation)
                                          ])).join("")
                                        : emptyRow(3)}
                                </table>
                            </div>

                            <div class="psr-section">
                                <div class="psr-section-title">2. Previous Sales Rate — Other Customers</div>
                                <table class="psr-table">
                                    <tr><th>Sales Invoice</th><th>Customer</th><th>Rate</th><th>Date</th></tr>
                                    ${other_cust.length
                                        ? other_cust.map(d => tableRow([
                                            docLink("sales-invoice", d.parent),
                                            invoice_customer_map[d.parent] || "—",
                                            rateCell(d.rate),
                                            frappe.datetime.str_to_user(d.creation)
                                          ])).join("")
                                        : emptyRow(4)}
                                </table>
                            </div>

                            <div class="psr-section">
                                <div class="psr-section-title">
                                    3. Quotation Rate — Same Customer
                                    <span class="psr-badge">${frm.doc.customer}</span>
                                </div>
                                <table class="psr-table">
                                    <tr><th>Quotation</th><th>Rate</th><th>Date</th></tr>
                                    ${quot_rows.length
                                        ? quot_rows.map(d => tableRow([
                                            docLink("quotation", d.parent),
                                            rateCell(d.rate),
                                            frappe.datetime.str_to_user(d.creation)
                                          ])).join("")
                                        : emptyRow(3)}
                                </table>
                            </div>

                            <div class="psr-section">
                                <div class="psr-section-title">4. Purchase Rate</div>
                                <table class="psr-table">
                                    <tr><th>Purchase Invoice</th><th>Rate</th><th>Date</th></tr>
                                    ${pur_rows.length
                                        ? pur_rows.map(d => tableRow([
                                            docLink("purchase-invoice", d.parent),
                                            rateCell(d.rate),
                                            frappe.datetime.str_to_user(d.creation)
                                          ])).join("")
                                        : emptyRow(3)}
                                </table>
                            </div>

                            <div class="psr-section">
                                <div class="psr-section-title">5. Valuation Rate</div>
                                <table class="psr-table">
                                    <tr><th>Valuation Rate</th></tr>
                                    <tr><td>${rateCell(val_rate)}</td></tr>
                                </table>
                            </div>
                        </div>
                    `;
                }

                html += `</div>`;

                // ── 7. Show dialog ────────────────────────────────────────────────
                let d = new frappe.ui.Dialog({
                    title: __("Previous Sales Rates"),
                    size: "extra-large",
                    fields: [{ fieldtype: "HTML", fieldname: "rate_html" }]
                });

                d.$wrapper.find(".modal-body").css({
                    "max-height": "75vh",
                    "overflow-y": "auto"
                });

                d.fields_dict.rate_html.$wrapper.html(html);
                d.show();

            } catch (err) {
                frappe.hide_progress();
                frappe.msgprint({
                    title: __("Error"),
                    indicator: "red",
                    message: __("Failed to load rate history. Check console for details.")
                });
                console.error("Previous Sales Rates Error:", err);
            }
        });
    }
});