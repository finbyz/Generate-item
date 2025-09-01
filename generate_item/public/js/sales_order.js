// // frappe.ui.form.on("Sales Order", {
// //     refresh: function (frm) {
//         // frm.add_custom_button("Open Item Generator List", function () {
//         //     frappe.set_route("List", "Item Generator");
//         // });
// //     }
// // });

// frappe.ui.form.on('Sales Order', {
//     refresh: function(frm) {
//         frm.add_custom_button("Open Item Generator List", function () {
//             frappe.set_route("List", "Item Generator");
//         });
        
//         let last_entered_item_codes = {};
        
//         // Use mutation observer to detect changes in the grid
//         const observer = new MutationObserver(function(mutations) {
//             mutations.forEach(function(mutation) {
//                 if (mutation.addedNodes.length) {
//                     $(mutation.addedNodes).find('input[data-fieldname="item_code"]').each(function() {
//                         let input = $(this);
//                         let row = input.closest('.grid-row').data('name');
                        
//                         input.off('input.custom').on('input.custom', function() {
//                             last_entered_item_codes[row] = input.val();
//                         });
//                     });
//                 }
//             });
//         });
        
//         // Start observing the grid wrapper
//         observer.observe(frm.fields_dict.items.grid.wrapper[0], {
//             childList: true,
//             subtree: true
//         });

//         frappe.ui.form.on('Sales Order Item', {
//             item_code: function(frm, cdt, cdn) {
//                 let row = locals[cdt][cdn];
//                 let entered_item_code = last_entered_item_codes[cdn];

//                 if (!row.item_code && entered_item_code && entered_item_code.trim() !== '') {
//                     frappe.db.exists('Item', entered_item_code).then(exists => {
//                         if (!exists) {
//                             frappe.confirm(
//                                 `Item "${entered_item_code}" does not exist. Create it using Item Generator?`,
//                                 function() {
//                                     // just call server method — do not save SO
//                                     call_item_generator_method(entered_item_code);
//                                 },
//                                 function() {
//                                     delete last_entered_item_codes[cdn];
//                                 }
//                             );
                            
//                         }
//                     });
//                 }
//             }
//         });


// function create_item_generator(frm, row, item_code, cdn) {
//     console.log("create_item_generator", frm, row, item_code, cdn);
//     frappe.call({
//         method: "frappe.client.insert",
//         args: {
//             doc: {
//                 doctype: "Item Generator",
//                 item_code: item_code,
//                 is_create_with_sales_order : 1,
//                          // optional link
//             }
//         },
//         callback: function(r) {
//             if (!r.exc) {
//                 frappe.msgprint(`Item Generator created for <b>${item_code}</b>`);
//                 // Optionally, set the row.item_code to blank so user must select from Item Generator
//                 row.item_code = "";
//                 frm.refresh_field("items");
//                 frappe.set_route("Form", "Item Generator", r.message.name);
//             }
//         }
//     });
// }
// }
// });


frappe.ui.form.on('Sales Order', {
    refresh: function(frm) {
        frm.add_custom_button("Open Item Generator List", function () {
            frappe.set_route("List", "Item Generator");
        });
        
        let last_entered_item_codes = {};
        
        // Use mutation observer to detect changes in the grid
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.addedNodes.length) {
                    $(mutation.addedNodes).find('input[data-fieldname="item_code"]').each(function() {
                        let input = $(this);
                        let row = input.closest('.grid-row').data('name');
                        
                        input.off('input.custom').on('input.custom', function() {
                            last_entered_item_codes[row] = input.val();
                        });
                    });
                }
            });
        });
        
        // Start observing the grid wrapper
        observer.observe(frm.fields_dict.items.grid.wrapper[0], {
            childList: true,
            subtree: true
        });

        frm.last_entered_item_codes = last_entered_item_codes;

        // If coming back from Item Generator, apply returned item code
        try {
            const raw = localStorage.getItem('ig_return_result');
            if (raw) {
                const data = JSON.parse(raw);
                if (data && data.so_name === frm.doc.name && data.cdn && data.item_code) {
                    const row = locals['Sales Order Item'] && locals['Sales Order Item'][data.cdn];
                    if (row) {
                        row.item_code = data.item_code;
                        frm.refresh_field('items');
                    }
                }
                localStorage.removeItem('ig_return_result');
            }
        } catch (e) {}
    }
});

frappe.ui.form.on('Sales Order Item', {
    item_code: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        let entered_item_code = frm.last_entered_item_codes ? frm.last_entered_item_codes[cdn] : null;

        if (!row.item_code && entered_item_code && entered_item_code.trim() !== '') {
            frappe.db.exists('Item', entered_item_code).then(exists => {
                if (!exists) {
                    frappe.confirm(
                        `Item "${entered_item_code}" does not exist. Create it using Item Generator?`,
                        function() {
                            // Open Item Generator and let it auto-generate, then return
                            open_item_generator_doc(frm, cdn);
                        },
                        function() {
                            delete frm.last_entered_item_codes[cdn];
                        }
                    );
                }
            });
        }
    }
});

function open_item_generator_doc(frm, cdn) {
    // Save return context so Item Generator can route back and update this SO row
    try {
        const context = {
            so_name: frm.doc.name,
            cdn: cdn
        };
        localStorage.setItem('ig_return_context', JSON.stringify(context));
    } catch (e) {}

    // Open new Item Generator with the SO marker
    let new_doc = frappe.model.get_new_doc('Item Generator');
    new_doc.is_create_with_sales_order = 1;
    frappe.set_route('Form', 'Item Generator', new_doc.name);
}