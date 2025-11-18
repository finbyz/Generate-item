frappe.ui.form.on("Item", {
    onload: function(frm) {
        apply_item_permissions(frm);
    },
    refresh: function (frm) {
        apply_item_permissions(frm);
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


function apply_item_permissions(frm) {
    const roles = frappe.user_roles || [];
    const is_sys_mgr = roles.includes('System Manager');

    console.log('System Manager:', is_sys_mgr);

    const restricted_fields = [
        'item_code',
        'item_name',
        'item_group',
        'description'
    ];

    restricted_fields.forEach(field => {
        if (frm.fields_dict[field]) {
            frm.set_df_property(field, 'read_only', is_sys_mgr ? 0 : 1);
        }
    });

    setTimeout(() => {
        restricted_fields.forEach(field => {
            if (frm.fields_dict[field]) {
                frm.refresh_field(field);
            }
        });
    }, 300);
}