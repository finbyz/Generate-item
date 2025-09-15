frappe.listview_settings['Item Generator'] = {
    onload: function(listview) {
        listview.page.add_actions_menu_item(__('Create Sub Assembly'), function() {
            let selected = listview.get_checked_items();

            if (!selected.length) {
                frappe.msgprint(__('Please select at least one item.'));
                return;
            }

            // Process all selected items
            selected.forEach(doc => {
                // Fetch the full document of the selected item
                frappe.call({
                    method: "frappe.client.get",
                    args: {
                        doctype: "Item Generator",
                        name: doc.name
                    },
                    callback: function(r) {
                        if (r.message) {
                            let base_item = r.message;

                            // Check if item is already duplicated
                            if (base_item.duplicated === 1) {
                                frappe.msgprint({
                                    title: __('Cannot Duplicate'),
                                    message: __('Item {0} is already a sub-assembly item and cannot be duplicated again.', [base_item.item_code]),
                                    indicator: 'red'
                                });
                                return;
                            }

                            // Check if item already ends with A4
                            if (base_item.item_code && base_item.item_code.endsWith("A4")) {
                                frappe.msgprint({
                                    title: __('Cannot Duplicate'),
                                    message: __('Item {0} appears to already be a sub-assembly item (ends with A4).', [base_item.item_code]),
                                    indicator: 'orange'
                                });
                                return;
                            }

                            // Duplicate all fields
                            let new_item = Object.assign({}, base_item);

                            // Remove system fields
                            delete new_item.name;
                            delete new_item.__unsaved;
                            delete new_item.creation;
                            delete new_item.modified;
                            delete new_item.modified_by;
                            delete new_item.owner;
                            delete new_item.docstatus;
                            delete new_item.idx;

                            // Apply changes
                            new_item.item_code = base_item.item_code + "A4";
                            new_item.short_description = (base_item.short_description || "") + " SUB ASSY KIT";
                            new_item.description = (base_item.description || "") + " SUB ASSEMBLY KIT";
                            new_item.item_group_name = "Ready Valves";
                            new_item.duplicated = 1;

                            // Insert the new item
                            frappe.call({
                                method: "frappe.client.insert",
                                args: { doc: new_item },
                                callback: function(res) {
                                    if (!res.exc) {
                                        frappe.show_alert({
                                            message: __("Created Sub Assembly Item: {0}", [res.message.item_code]),
                                            indicator: 'green'
                                        });
                                        listview.refresh();
                                    } else {
                                        // Handle specific errors
                                        if (res.exc && res.exc.includes("Duplicate")) {
                                            frappe.msgprint({
                                                title: __('Duplicate Error'),
                                                message: __('Item {0} already exists. Please use a different base item.', [new_item.item_code]),
                                                indicator: 'red'
                                            });
                                        } else {
                                            frappe.msgprint({
                                                title: __('Error'),
                                                message: __('Failed to create sub-assembly item: {0}', [res.exc]),
                                                indicator: 'red'
                                            });
                                        }
                                    }
                                }
                            });
                        }
                    }
                });
            });
        });
    }
};