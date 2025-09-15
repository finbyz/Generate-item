frappe.ui.form.on('BOM', {
    refresh: function(frm) {
        frm.add_custom_button(__('Material Request'), function() {
            create_material_request_from_bom(frm);
        }, __('Create'));
        
        frm.set_query('bom_no', 'items', function(doc, cdt, cdn) {
            let row = locals[cdt][cdn];
            return {
                filters: [
                    ['item', '=', row.item_code],
                    ['is_active', '=', 1],
                    ['docstatus', 'in', [0, 1]]
                ]
            };
        });
    }})


        
function create_material_request_from_bom(frm) {
    if (!frm.doc.items || frm.doc.items.length === 0) {
        frappe.msgprint(__('No BOM items found to create a Material Request.'));
        return;
    }

    const schedule_date = frappe.datetime.get_today();


    const items = (frm.doc.items || [])
        .filter(i => i.item_code)
        .map(i => ({
            item_code: i.item_code,
            qty: i.qty || i.stock_qty || 0,
            uom: i.uom,
            schedule_date: schedule_date,
            bom_no: frm.doc.name,
            

        }));

    if (!items.length) {
        frappe.msgprint(__('No valid items to add in Material Request.'));
        return;
    }

    const mr_doc = {
        doctype: 'Material Request',
        material_request_type: 'Purchase',
        company: frm.doc.company || undefined,
        schedule_date: schedule_date,
        custom_ga_drawing_no: frm.doc.custom_ga_drawing_no,
        custom_ga_drawing_rev_no: frm.doc.custom_ga_drawing_rev_no,
        items: items,
    };

    frappe.call({
        method: 'frappe.client.insert',
        args: { doc: mr_doc },
        freeze: true,
        callback: function(r) {
            if (!r.exc) {
                const name = r.message && r.message.name;
                const safeName = frappe.utils.escape_html(name);
                const linkBtn = `<a class="btn btn-link p-0" href="/app/material-request/${encodeURIComponent(name)}">${safeName}</a>`;
                frappe.msgprint({
                    title: __('Material Request Created'),
                    message: __('Created {0} from this BOM', [linkBtn]),
                    indicator: 'green',
                    wide: false
                });
            } else {
                frappe.msgprint({
                    title: __('Error'),
                    message: __('Failed to create Material Request: ') + r.exc,
                    indicator: 'red'
                });
            }
        }
    });
}