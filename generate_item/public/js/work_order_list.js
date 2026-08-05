frappe.listview_settings['Work Order'] = frappe.listview_settings['Work Order'] || {};

const original_onload = frappe.listview_settings['Work Order'].onload;

frappe.listview_settings['Work Order'].onload = function(listview) {
    if (original_onload) {
        original_onload(listview);
    }

    listview.page.add_inner_button(__('Export to Excel'), function () {

        let selected = listview.get_checked_items();

        if (!selected.length) {
            frappe.msgprint(__('Please select Work Orders'));
            return;
        }

        let names = selected.map(d => d.name);

        frappe.call({
            method: "generate_item.utils.work_order.export_work_orders",
            args: {
                work_orders: names
            },
            callback(r) {
                if (r.message) {
                    window.open(r.message);
                }
            }
        });

    });

};