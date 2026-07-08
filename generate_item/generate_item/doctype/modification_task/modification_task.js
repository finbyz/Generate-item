// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt
frappe.ui.form.on('Modification Task', {
    refresh(frm) {
        // Remove old toggle if re-rendered
        frm.page.wrapper.find('.custom-toggle-wrapper').remove();

        // Inject CSS once
        if (!document.getElementById('custom-toggle-style')) {
            $('<style id="custom-toggle-style">').text(`
                 .custom-toggle-wrapper label.toggle-switch {
                    margin-bottom: 0 !important;
                }
                .custom-toggle-wrapper {
                    display: inline-flex;
                    align-items: center;
                    gap: 10px;
                    margin-left: 10px;
                }
                .toggle-label-text {
                    font-size: 13px;
                    font-weight: 600;
                    color: #333;
                }
                .toggle-switch {
                    position: relative;
                    width: 55px;
                    height: 23px;
                    cursor: pointer;
                }
                .toggle-switch input {
                    opacity: 0;
                    width: 0;
                    height: 0;
                    position: absolute;
                }
                .toggle-slider {
                    position: absolute;
                    inset: 0;
                    background-color: #333;
                    border-radius: 34px;
                    transition: background-color 0.3s ease;
                    display: flex;
                    align-items: center;
                    justify-content: flex-start;
                    padding-left: 36px;
                    font-size: 11px;
                    font-weight: 700;
                    color: white;
                    letter-spacing: 0.5px;
                    overflow: hidden;
                    user-select: none;
                }
                .toggle-slider::before {
                    content: "";
                    position: absolute;
                    left: 3px;
                    width: 15px;
                    height: 15px;
                    border-radius: 50%;
                    background: white;
                    box-shadow: 0 2px 6px rgba(0,0,0,0.3);
                    transition: transform 0.3s ease;
                    z-index: 2;
                }
                .toggle-switch input:checked + .toggle-slider {
                    background-color: #5cb85c;
                    justify-content: flex-end;
                    padding-left: 0;
                    padding-right: 36px;
                }
                .toggle-switch input:checked + .toggle-slider::before {
                    transform: translateX(36px);
                }
                .toggle-text {
                    z-index: 1;
                    pointer-events: none;
                }
            `).appendTo('head');
        }

        // Only show after submit
        if (frm.doc.docstatus === 1) {
            const isCompleted = frm.doc.status === 'Completed';

            const $wrapper = $(`
                <div class="custom-toggle-wrapper">
                    <span class="toggle-label-text">
                        ${isCompleted ? 'Completed' : 'Pending'}
                    </span>
                    <label class="toggle-switch">
                        <input type="checkbox" id="status-toggle" ${isCompleted ? 'checked disabled' : ''}>
                        <div class="toggle-slider">
                            <span class="toggle-text">${isCompleted ? '' : ''}</span>
                        </div>
                    </label>
                </div>
            `);

            frm.page.wrapper.find('.page-actions').prepend($wrapper);

            // Toggle click logic
            $wrapper.find('#status-toggle').on('change', function () {
                const $checkbox = $(this);
                const newStatus = this.checked ? 'Completed' : 'Pending';
                const label = newStatus === 'Completed' ? '' : '';

                // ---- Validation: required before marking Completed ----
                if (newStatus === 'Completed') {
                    const missing = [];

                    if (!frm.doc.task_status || !frm.doc.task_status.trim()) {
                        missing.push('Task Status');
                    }

                    if (!frm.doc.task_remarks || !frm.doc.task_remarks.trim()) {
                        missing.push('Task Remarks');
                    }

                    if (!frm.doc.assign_to || !frm.doc.assign_to.trim()) {
                        missing.push('Assign To');
                    }

                    // "Assigned To" is stored
                   

                    if (missing.length > 0) {
                        frappe.msgprint({
                            title: __('Cannot Mark as Completed'),
                            indicator: 'red',
                            message: __('Please fill the following field(s) before marking this task as Completed: {0}', [
                                '<b>' + missing.join(', ') + '</b>'
                            ])
                        });

                        // Revert toggle, do not proceed
                        this.checked = false;
                        $wrapper.find('.toggle-text').text('');
                        $wrapper.find('.toggle-label-text').text('Pending');
                        return;
                    }
                }
                // ---- End validation ----

                frappe.confirm(
                    `Mark this task as <b>${newStatus}</b>?`,
                    () => {
                        frappe.call({
                            method: 'frappe.client.set_value',
                            args: {
                                doctype: 'Modification Task',
                                name: frm.doc.name,
                                fieldname: 'status',
                                value: newStatus
                            },
                            callback(r) {
                                if (!r.exc) {
                                    frappe.show_alert({
                                        message: `Status → ${newStatus}`,
                                        indicator: newStatus === 'Completed' ? 'green' : 'red'
                                    });
                                    frm.reload_doc();
                                } else {
                                    // Revert toggle if failed
                                    $checkbox.prop('checked', !$checkbox.prop('checked'));
                                }
                            }
                        });
                    },
                    () => {
                        // User cancelled — revert toggle visually
                        this.checked = !this.checked;
                        $wrapper.find('.toggle-text').text(this.checked ? '' : '');
                        $wrapper.find('.toggle-label-text').text(this.checked ? 'Completed' : 'Pending');
                    }
                );
            });
        }
    }
});