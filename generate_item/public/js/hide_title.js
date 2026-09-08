frappe.ui.form.on('*', {
    refresh: function(frm) {
        if (frm.fields_dict && frm.fields_dict.title) {
            frm.set_df_property('title', 'hidden', 1);
            frm.refresh_field('title');
        }
    }
});