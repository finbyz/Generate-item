let actual_qty_set_flags = {};
frappe.ui.form.on('Production Plan', {
    onload: function(frm) {
        if (frm.doc.docstatus === 0)
            {
                update_actual_qty_for_items(frm);
            }
    },
    
    refresh: function(frm) {
        if (frm.doc.docstatus === 0)
        {
            update_actual_qty_for_items(frm);
        }
        
        // Ensure the form is fully loaded and the document name is available
        if (!frm.doc.name) return;

        // Check if Work Order exists for the current Production Plan
        frappe.db.get_list('Work Order', {
            filters: { 'production_plan': frm.doc.name },
            fields: ['name'],
            limit: 1
        }).then(result => {
            // Check if the "Work Order / Subcontract PO" button exists in the Create menu
            const button_label = 'Work Order / Subcontract PO';

            // Remove the button if a Work Order exists
            if (result.length > 0) {
                try {
                    frm.remove_custom_button(button_label, 'Create');
                } catch (e) {
                    console.warn(`Could not remove button "${button_label}" from Create menu:`, e);
                }
            } else {
                // Add the button if no Work Order exists
                try {
                    if (frm.docstatus == 0 )
                    {
                        frm.add_custom_button(__(button_label), function() {
                        frappe.call({
                            method: 'erpnext.manufacturing.doctype.production_plan.production_plan.ProductionPlan.make_work_order',
                            args: { name: frm.doc.name },
                            callback: function(r) {
                                if (r.message) {
                                    frappe.msgprint(__('Work Order(s) and/or Purchase Order(s) created successfully.'));
                                    frm.reload_doc();
                                }
                            }
                        });
                    }, __('Create'));
                    }
                } catch (e) {
                    console.warn(`Could not add button "${button_label}" to Create menu:`, e);
                }
            }
        }).catch(err => {
            console.error('Error checking Work Order existence:', err);
            frappe.msgprint({
                title: __('Error'),
                message: __('Failed to check Work Order existence. Please try again or contact the administrator.'),
                indicator: 'red'
            });
        });
    },
    
    setup: function(frm) {
        frm.set_query('custom_batch_wise_assembly', function() {
            // Get all custom_batch_no values from po_items child table
            let batch_nos = (frm.doc.po_items || [])
                .filter(row => row.custom_batch_no)
                .map(row => row.custom_batch_no);

            return {
                filters: [
                    ['Batch', 'name', 'in', batch_nos]
                ]
            };
        });
    },
    custom_batch_wise_assembly: function(frm) {
        let selected_batch = frm.doc.custom_batch_wise_assembly;
        if (!selected_batch) {
            frm.trigger("get_sales_orders");
            frm.trigger("get_items");
            return;
        }

        let filtered_items = (frm.doc.po_items || []).filter(row => row.custom_batch_no === selected_batch);
        let filtered_ppi_names = new Set(filtered_items.map(r => r.name));

        // Filter parent table
        frm.doc.po_items = filtered_items;
        frm.refresh_field('po_items');

        // Also filter sub_assembly_items whose production_plan_item points to remaining po_items
        if (Array.isArray(frm.doc.sub_assembly_items)) {
            frm.doc.sub_assembly_items = (frm.doc.sub_assembly_items || []).filter(r => {
                return !r.production_plan_item || filtered_ppi_names.has(r.production_plan_item);
            });
            frm.refresh_field('sub_assembly_items');
        }

        // Also filter sales_orders to those referenced by remaining po_items (if linkage exists)
        let linked_sales_orders = new Set((filtered_items || [])
            .map(row => row.sales_order)
            .filter(so => !!so));

        if (frm.doc.sales_orders && frm.doc.sales_orders.length) {
            frm.doc.sales_orders = (frm.doc.sales_orders || []).filter(r => linked_sales_orders.has(r.sales_order));
            frm.refresh_field('sales_orders');
        }
    },
    custom_default_supplier: function(frm) {
        const supplier_value = frm.doc.custom_default_supplier || '';
        const rows = frm.doc.sub_assembly_items || [];

        rows.forEach(row => {
            frappe.model.set_value(row.doctype, row.name, 'supplier', supplier_value);
        });
        frm.refresh_field('sub_assembly_items');
    } 
});

// Handle Production Plan Item changes
frappe.ui.form.on('Production Plan Item', {
    planned_qty: function(frm, cdt, cdn) {
        
        // When user changes planned_qty, update pending_qty to match
        let row = locals[cdt][cdn];
         if (row.planned_qty > row.actual_qty) {
            frappe.msgprint({
                title: __('Invalid Quantity'),
                message: __('Planned Quantity cannot exceed Actual Quantity.'),
                indicator: 'red'
            });
            console.log(row.actual_qty);
            frappe.model.set_value(cdt, cdn, 'planned_qty', row.actual_qty);

        }
        if (row.planned_qty !== undefined) {
            row.pending_qty = row.planned_qty;
            frm.refresh_field('po_items');
        }
    },
    
    pending_qty: function(frm, cdt, cdn) {
        // When user changes pending_qty, update planned_qty to match
        let row = locals[cdt][cdn];
        if (row.pending_qty !== undefined) {
            row.planned_qty = row.pending_qty;
            frm.refresh_field('po_items');
        }
    }
});


function update_actual_qty_for_items(frm) {
    frm.doc.po_items.forEach((row) => {
        if ((!row.actual_qty || row.actual_qty === 0) && !actual_qty_set_flags[row.name]) {
            actual_qty_set_flags[row.name] = true;

            frappe.call({
                method: 'generate_item.utils.production_plan.set_actual_qty_for_child_row',
                args: {
                    cdt: 'Production Plan Item',
                    cdn: row.name
                },
                callback: function(r) {
                    if (r.message) {
                        frappe.model.set_value('Production Plan Item', row.name, 'actual_qty', r.message);
                    }
                }
            });
        }
    });
}