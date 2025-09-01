frappe.ui.form.on("Item", {
    refresh: function (frm) {
        frm.add_custom_button("Open Item Generator", function () {
            frappe.db.get_value("Item Generator", { created_item: frm.doc.name }, "name")
                .then(r => {
                    if (r && r.message && r.message.name) {
                        // If an Item Generator exists → open it
                        frappe.set_route("Form", "Item Generator", r.message.name);
                    } else {
                        // Else → create new Item Generator with this Item pre-filled
                        frappe.msgprint("No Item Generator found")
                    }
                });
        });
    }
});
