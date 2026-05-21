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
                            if (base_item.duplicated_subassembly === 1) {
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

                            // FIXED: Handle short description with 140 char limit
                            let suffix = " SUB ASSY KIT";
                            let base_short_desc = (base_item.short_description || "").trim();
                            let room = 140 - suffix.length;

                            if (room < 0) {
                                new_item.short_description = suffix.substring(0, 140);
                            } else {
                                new_item.short_description = (base_short_desc.substring(0, room).trim() + suffix).trim();
                            }

                            new_item.description = (base_item.description || "") + " SUB ASSEMBLY KIT";
                            new_item.item_group_name = "Ready Valves";
                            new_item.duplicated_subassembly = 1;

                            // Also set custom_conditional_description to match
                            new_item.custom_conditional_description = new_item.short_description;

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

        listview.page.add_actions_menu_item(__('Create Machining Kit'), function() {
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
                            if (base_item.duplicated_machining_kit === 1) {
                                frappe.msgprint({
                                    title: __('Cannot Duplicate'),
                                    message: __('Item {0} is already a sub-machine kit item and cannot be duplicated again.', [base_item.item_code]),
                                    indicator: 'red'
                                });
                                return;
                            }

                            // Check if item already ends with M4
                            if (base_item.item_code && base_item.item_code.endsWith("M4")) {
                                frappe.msgprint({
                                    title: __('Cannot Duplicate'),
                                    message: __('Item {0} appears to already be a sub-machine kit item (ends with M4).', [base_item.item_code]),
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
                            new_item.item_code = base_item.item_code + "M4";

                            // FIXED: Handle short description with 140 char limit
                            let suffix = " M/C KIT";
                            let base_short_desc = (base_item.short_description || "").trim();
                            let room = 140 - suffix.length;

                            if (room < 0) {
                                new_item.short_description = suffix.substring(0, 140);
                            } else {
                                new_item.short_description = (base_short_desc.substring(0, room).trim() + suffix).trim();
                            }

                            new_item.description = (base_item.description || "") + " SUB MACHINING KIT";
                            // new_item.item_group_name = base_item.item_group_name;
                            new_item.item_group_name = "Sub Assembly";
                            new_item.duplicated_machining_kit = 1;

                            // Also set custom_conditional_description to match
                            new_item.custom_conditional_description = new_item.short_description;

                            // Insert the new item
                            frappe.call({
                                method: "frappe.client.insert",
                                args: { doc: new_item },
                                callback: function(res) {
                                    if (!res.exc) {
                                        frappe.show_alert({
                                            message: __("Created Sub Machine Kit Item: {0}", [res.message.item_code]),
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
                                                message: __('Failed to create sub-machine kit item: {0}', [res.exc]),
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

    
    listview.page.add_actions_menu_item(__('Verify Items'), async function () {

    let selected_items = listview.get_checked_items();

    if (!selected_items.length) {
        frappe.msgprint(__('Please select items'));
        return;
    }

    console.log("Selected Items:", selected_items);

    frappe.confirm(
        __('Verify {0} items?', [selected_items.length]),

        async function () {

            frappe.dom.freeze(__('Verifying Items...'));

            let success = [];
            let failed = [];

            // LOOP START
            for (let i = 0; i < selected_items.length; i++) {

                let row = selected_items[i];


                try {

                    let doctype = 'Item Generator';
                    let docname = row.name;

                    // STEP 1
                    console.log("STEP 1 => Loading Doctype");

                    await new Promise((resolve, reject) => {

                        frappe.model.with_doctype(doctype, async () => {

                            try {

                                console.log("STEP 2 => Doctype Loaded");

                                // STEP 3
                                console.log("STEP 3 => Loading Document");

                                await frappe.model.with_doc(doctype, docname);

                                console.log("STEP 4 => Document Loaded");

                                // STEP 5
                                console.log("STEP 5 => Creating Form");

                                let frm = new frappe.ui.form.Form(
                                    doctype,
                                    $('<div></div>'),
                                    false
                                );

                                // STEP 6
                                console.log("STEP 6 => Refresh Form");

                                await frm.refresh(docname);

                                await frappe.after_ajax();

                                await wait_for_attributes(frm);

                                console.log("Attributes fully loaded");

                                console.log("STEP 7 => Form Refreshed");

                                console.log("DOCUMENT BEFORE REFILL");
                                console.log(JSON.parse(JSON.stringify(frm.doc)));

                                // STEP 8
                                console.log("STEP 8 => Calling refill_data");

                                try {

                                    await refill_data(frm);

                                } catch (refill_error) {

                                    console.error("REFILL DATA ERROR");
                                    console.error(refill_error);

                                    throw refill_error;
                                }

                                console.log("STEP 9 => refill_data Completed");

                                console.log("DOCUMENT AFTER REFILL");
                                console.log(JSON.parse(JSON.stringify(frm.doc)));

                                // STEP 10
                                console.log("STEP 10 => Mark Dirty");

                                frm.dirty();

                                console.log("IS DIRTY:", frm.is_dirty());

                                // STEP 11
                                console.log("STEP 11 => Saving Document");

                                try {

                                    let save_res = await frm.save();

                                    console.log("SAVE RESPONSE");
                                    console.log(save_res);

                                } catch (save_error) {

                                    console.error("SAVE ERROR");
                                    console.error(save_error);

                                    // full server response
                                    if (save_error?.messages) {
                                        console.error(save_error.messages);
                                    }

                                    throw save_error;
                                }

                                console.log("STEP 12 => Document Saved");

                                resolve();

                            } catch (inner_error) {

                                console.error("INNER ERROR");
                                console.error(inner_error);

                                reject(inner_error);
                            }

                        });

                    });

                    // STEP 13
                    console.log("STEP 13 => Calling update_item_master");

                    let update_res = await frappe.call({
                        method: 'generate_item.generate_item.doctype.item_generator.item_generator.update_item_master',
                        args: {
                            item_generator_name: row.name
                        }
                    });

                    console.log("UPDATE RESPONSE");
                    console.log(update_res);

                    if (update_res.exc) {

                        console.error("UPDATE ERROR");
                        console.error(update_res.exc);

                        throw new Error(update_res.exc);
                    }

                    console.log(`SUCCESS => ${row.name}`);

                    success.push(row.name);

                } catch (e) {

                    console.error("FINAL ERROR");
                    console.error(e);

                    failed.push({
                        name: row.name,
                        error: e.message || String(e)
                    });
                }

                console.log(`END PROCESSING => ${row.name}`);
            }

            frappe.dom.unfreeze();

            console.log("ALL PROCESS COMPLETED");

            console.log("SUCCESS ITEMS");
            console.log(success);

            console.log("FAILED ITEMS");
            console.log(failed);

            let message = `
                <b>Verification Complete</b><br><br>
                Success: ${success.length}<br>
                Failed: ${failed.length}
            `;

            if (failed.length) {

                message += '<br><br><b>Failed Items:</b><br>';

                failed.forEach(d => {
                    message += `• ${d.name}: ${d.error}<br>`;
                });
            }

            frappe.msgprint({
                title: __('Result'),
                message: message,
                indicator: failed.length ? 'orange' : 'green'
            });

            listview.refresh();
        }
    );
});
    }
};



async function wait_for_attributes(frm, timeout = 15000) {

    let start = Date.now();

    while (!frm.__attribute_meta_loaded__) {

        console.log("Waiting for attribute metadata...");

        await frappe.utils.sleep(200);

        if (Date.now() - start > timeout) {
            throw new Error("Attribute metadata loading timeout");
        }
    }

    console.log("Attribute metadata loaded successfully");
}




async function refill_data(frm) {

    frm.doc.item_descriptor = frm.doc.created_item;

    if (!frm.doc.item_descriptor) return;

    if (!frm.doc.template_name) {
        frappe.msgprint("Please select a template first.");
        await frm.set_value("item_descriptor", "");
        return;
    }

    await wait_for_attributes(frm);

    console.log("Refilling data...");

    await parse_item_descriptor(frm);
}



async function parse_item_descriptor(frm) {

    let code = (frm.doc.item_descriptor || "").trim();

    let cursor = 0;
    let error_found = false;

    for (let i = 1; i <= 28; i++) {

        let value_field = "attribute_" + i + "_value";

        let metaMap = frm.__attribute_meta__[value_field];

        if (!metaMap) continue;

        let codeLen = 0;

        let rows = Object.values(metaMap);

        if (rows.length && rows[0].code) {
            codeLen = rows[0].code.length;
        }

        if (!codeLen) continue;

        let codePart = code.slice(cursor, cursor + codeLen);

        cursor += codeLen;

        let matched = Object.entries(metaMap).find(([key, meta]) => {

            return (meta.code || "").toUpperCase() === codePart.toUpperCase();

        });

        if (matched) {

            await frm.set_value(
                value_field,
                matched[1].item_long_description
            );

        } else {

            frappe.msgprint(
                `No match found for code part "${codePart}" at position ${i}.`
            );

            error_found = true;
        }
    }

    if (!error_found) {

        await generate_fields(frm);

        await frm.set_value("item_descriptor", "");

        frm.refresh_field("item_descriptor");

    } else {

        await frm.set_value("item_descriptor", "");
    }
}


async function generate_fields(frm) {

    let code_parts = [];
    let desc_parts = [];
    let short_parts = [];

    const required_attributes = [
        "TYPE OF PRODUCT",
        "VALVE TYPE",
        "SIZE",
        "RATING",
        "ENDS",
        "SHELL MOC",
        "OPERATOR"
    ];

    let selective_short_parts = [];

    let is_selective_template =
        frm.__selective_templates__ &&
        frm.__selective_templates__.includes(frm.doc.template_name);

    for (let i = 1; i <= 28; i++) {

        let label_field = "attribute_" + i;
        let value_field = "attribute_" + i + "_value";

        let label = frm.doc[label_field] || "";
        let val = frm.doc[value_field];

        if (!val) continue;

        val = String(val);

        let keyNorm = val.trim().toLowerCase();

        let metaMap =
            frm.__attribute_meta__ &&
            frm.__attribute_meta__[value_field]
                ? frm.__attribute_meta__[value_field]
                : null;

        let meta = null;

        if (metaMap) {

            if (metaMap.hasOwnProperty(keyNorm)) {

                meta = metaMap[keyNorm];

            } else if (metaMap.hasOwnProperty(val)) {

                meta = metaMap[val];

            } else {

                let keys = Object.keys(metaMap);

                for (let k = 0; k < keys.length; k++) {

                    if (
                        keys[k].toString().trim().toLowerCase() === keyNorm
                    ) {
                        meta = metaMap[keys[k]];
                        break;
                    }
                }
            }
        }

        if (meta) {

            code_parts.push(meta.code || "");

            if (val.trim() !== "-") {

                desc_parts.push(meta.item_long_description || val);

                short_parts.push(meta.item_short_description || val);

                if (is_selective_template) {

                    let label_upper = label.trim().toUpperCase();

                    if (required_attributes.includes(label_upper)) {

                        selective_short_parts.push(
                            meta.item_short_description || val
                        );
                    }
                }
            }
        }
    }

    let final_short_desc = "";

    if (is_selective_template && selective_short_parts.length > 0) {

        final_short_desc = selective_short_parts.join(" ");

        let suffix = "";

        if (frm.doc.duplicated_subassembly == 1) {
            suffix = " SUB ASSY KIT";
        } else if (frm.doc.duplicated_machining_kit == 1) {
            suffix = " M/C KIT";
        }

        if (suffix) {

            let room = 140 - suffix.length;

            if (room < 0) {

                final_short_desc = suffix.substring(0, 140);

            } else {

                final_short_desc =
                    (
                        final_short_desc
                            .substring(0, room)
                            .trim() + suffix
                    ).trim();
            }

        } else {

            final_short_desc =
                final_short_desc.substring(0, 140);
        }

        console.log(
            "Generated selective short description:",
            final_short_desc
        );

    } else {

        final_short_desc = short_parts.join(" ");
    }

    await frm.set_value("item_code", code_parts.join(""));

    await frm.set_value("description", desc_parts.join(" "));

    await frm.set_value("short_description", final_short_desc);

    if (frm.fields_dict.custom_conditional_description) {

        await frm.set_value(
            "custom_conditional_description",
            final_short_desc
        );
    }
}