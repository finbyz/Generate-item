// // Copyright (c) 2025, Finbyz and contributors
// // For license information, please see license.txt

// frappe.ui.form.on("Custom Item Attribute", {
//     refresh: function (frm) {
//         if (typeof frm.doc.is_closed === "undefined") return;

//         // clear buttons
//         frm.clear_custom_buttons();

//         if (frm.doc.is_closed == 1) {
//             lock_form(frm);
//             let btn = frm.add_custom_button("Closed");
//             if (btn) {
//                 btn.addClass("btn-disabled");
//                 btn.prop("disabled", true);
//             }
//         } else {
//             frm.add_custom_button("Close", function () {
//                 frappe.confirm("Are you sure you want to close this record?", function () {
//                     frm.set_value("is_closed", 1);
//                     frm.save()
//                         .then(() => {
//                             frappe.msgprint("This record has been closed.");
//                             frm.reload_doc();
//                         })
//                         .catch(() => {
//                             frappe.msgprint({
//                                 title: __("Cannot Close"),
//                                 message: __("Please complete all mandatory fields before closing."),
//                                 indicator: "red"
//                             });
//                         });
//                 });
//             });
//         }
//     }
// });

// function lock_form(frm) {
//     // disable editing
//     frm.set_read_only(true);

//     // disable form actions (delete, menu, etc.)
//     frm.disable_form();

//     // lock all fields including child tables
//     (frm.meta.fields || []).forEach(df => {
//         try {
//             frm.set_df_property(df.fieldname, "read_only", 1);

//             if (df.fieldtype === "Table" && frm.fields_dict[df.fieldname]?.grid) {
//                 const grid = frm.fields_dict[df.fieldname].grid;

//                 // hide add/delete row buttons
//                 grid.wrapper.find('.grid-add-row, .grid-remove-rows, .grid-delete-row, .grid-append-row').hide();

//                 // disable inline editing
//                 if (grid.set_allow_on_grid_editing) {
//                     grid.set_allow_on_grid_editing(false);
//                 }

//                 // disable toolbar buttons
//                 if (grid.toolbar) {
//                     grid.toolbar.find('.btn').prop('disabled', true);
//                 }
//             }
//         } catch (e) {
//             console.warn("Error locking field:", df.fieldname, e);
//         }
//     });

//     // ✅ Hide Save button ONLY if doc is not new and closed
//     if (!frm.is_new() && frm.doc.is_closed == 1) {
//         if (frm.page.set_primary_action) {
//             frm.page.set_primary_action(null);
//         }
//         $(".btn-primary").remove();
//     }
// }
