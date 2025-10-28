frappe.ui.form.on("Sales Invoice", {
    refresh(frm) {
        if (frm.is_new() && frm.doc.items?.some(d => d.sales_order)) {
            fetch_and_update_taxes(frm);
        }
        if (
            !frm.doc.is_return &&
            (frm.doc.status !== "Closed" || frm.is_new()) &&
            frm.has_perm("write") &&
            frappe.model.can_read("Sales Order") &&
            frm.doc.docstatus === 0
        ) {
            frm.add_custom_button(
                __("Dispatchable SO"),
                function () {
                    if (!frm.doc.customer) {
                        frappe.throw({
                            title: __("Mandatory"),
                            message: __("Please select a Customer first."),
                        });
                        return;
                    }

                    frappe.call({
                        method: "generate_item.utils.delivery_note.get_dispatchable_sales_orders_list",
                        args: {
                            customer: frm.doc.customer,
                            company: frm.doc.company,
                            project: frm.doc.project,
                        },
                        callback: function (r) {
                            if (r.message && r.message.length > 0) {
                                const dispatchable_so_list = r.message.map((so) => so.name);

                                erpnext.utils.map_current_doc({
                                    method: "erpnext.selling.doctype.sales_order.sales_order.make_sales_invoice",
                                    source_doctype: "Sales Order",
                                    target: frm,
                                    setters: {
                                        customer: frm.doc.customer,
                                    },
                                    get_query_filters: {
                                        name: ["in", dispatchable_so_list],
                                        docstatus: 1,
                                        status: ["not in", ["Closed", "On Hold"]],
                                        per_billed: ["<", 99.99],
                                        company: frm.doc.company,
                                        project: frm.doc.project || undefined,
                                    },
                                    allow_child_item_selection: true,
                                    child_fieldname: "items",
                                    child_columns: [
                                        "item_code",
                                        "item_name",
                                        "qty",
                                        "billed_amt",
                                        // "description"
                                    ],
                                });
                            } else {
                                frappe.msgprint(__("No dispatchable Sales Orders found for this customer."));
                            }
                        },
                    });
                },
                __("Get Items From")
            );
        }
    },
    // Also handle case where user adds items after opening new form
    items_add(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (frm.is_new() && row.sales_order) {
            fetch_and_update_taxes(frm);
        }
    },

    // Optional — if user edits an existing row to add sales_order
    items_on_form_rendered(frm) {
        if (frm.is_new() && frm.doc.items?.some(d => d.sales_order)) {
            fetch_and_update_taxes(frm);
        }
    }
});

function fetch_and_update_taxes(frm) {    // Avoid multiple triggers in same session
    if (frm.__fetching_remaining_taxes) return;
    frm.__fetching_remaining_taxes = true;

    const sales_orders = [...new Set(
        frm.doc.items
            .filter(item => item.sales_order)
            .map(item => item.sales_order)
    )];

    if (!sales_orders.length) {
        frappe.msgprint({
            title: __("No Sales Order"),
            message: __("No items are linked to a Sales Order."),
            indicator: "orange"
        });
        frm.__fetching_remaining_taxes = false;
        return;
    }

    frappe.call({
        method: "generate_item.utils.sales_invoice.get_remaining_taxes_for_draft",
        args: {
            sales_orders: sales_orders,
            current_invoice_name: frm.doc.name || null
        },
        freeze: true,
        freeze_message: __("Fetching remaining taxes..."),
        callback: function(r) {
            frm.__fetching_remaining_taxes = false;

            if (r.message && !r.exc) {
                const remaining_taxes = r.message;
                let updated = false;

                frm.doc.taxes.forEach(tax_row => {
                    if (tax_row.charge_type === "Actual") {
                        const account_head = tax_row.account_head;
                        if (remaining_taxes[account_head] !== undefined) {
                            const remaining_amount = remaining_taxes[account_head];
                            frappe.model.set_value(
                                tax_row.doctype,
                                tax_row.name,
                                "tax_amount",
                                remaining_amount
                            );
                            updated = true;
                        }
                    }
                });

                if (updated) {
                    frm.trigger("calculate_taxes_and_totals");
                    frm.refresh_field("taxes");
                    frappe.show_alert({
                        message: __("Actual taxes adjusted successfully!"),
                        indicator: "green"
                    }, 5);
                }
            }
        }
    });
}
