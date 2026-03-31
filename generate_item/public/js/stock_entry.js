// frappe.ui.form.on('Stock Entry', {
//     onload: function(frm) {
//         // Handle case when stock entry is loaded with work order already set (backend creation)
//         if (frm.doc.work_order && !frm.doc.custom_batch_no) {
//             set_custom_fields_from_work_order(frm);
//         }
//         if (frm.doc.custom_batch_no) {
//             set_batch_no_in_items(frm, frm.doc.custom_batch_no);
//         }
//         // Fixed: Use frm.is_new() and remove extra arg in call
//         if (frm.doc.subcontracting_order && frm.is_new()) {
//             set_custom_fields_in_items(frm);
//         }
//     },
    
//     work_order: function(frm) {
//         if (!frm.doc.work_order) return;
//         console.log('work_order changed', frm.doc.work_order);
//         // Apply on the UI immediately when Work Order is set
//         set_custom_fields_from_work_order(frm);
//     },
    
//     subcontracting_order: function(frm) {
//         if (frm.doc.subcontracting_order) {
//             set_custom_fields_in_items(frm);
//         }
//     },

//     custom_batch_no: function(frm) {
//         // Whenever batch is manually set/changed, update in items
//         if (frm.doc.custom_batch_no) {
//             set_batch_no_in_items(frm, frm.doc.custom_batch_no);
//         }
//     },
    
//     purpose: function(frm) {
//         // If purpose changes to manufacturing and we have work order, set custom fields
//         if (frm.doc.work_order && frm.doc.items) {
//             if (['Manufacture', 'Material Transfer for Manufacture'].includes(frm.doc.purpose)) {
//                 set_custom_fields_from_work_order(frm);
//             }
//         }
//     }
// });

// // Helper function to set custom fields from work order
// function set_custom_fields_from_work_order(frm) {
//     if (!frm.doc.work_order) return;
    
//     // Fetch full work order document to access required_items
//     frappe.db.get_doc('Work Order', frm.doc.work_order)
//         .then(wo => {
//             if (!wo) return;
//             console.log('work order fetched', wo);
            
//             // Set BOM on parent if available
//             if (wo.bom_no) {
//                 frm.set_value('bom_no', wo.bom_no);
//             }

//             // Set custom_batch_no in parent if available
//             const batch_no = wo.custom_batch_no;
//             if (batch_no && !frm.doc.custom_batch_no) {
//                 frm.set_value('custom_batch_no', batch_no);
//             }
            
//             // Prepare a dictionary of custom fields from work order's required_items, keyed by item_code
//             const required_items_dict = {};
//             wo.required_items.forEach(req_item => {
//                 if (req_item.item_code) {
//                     required_items_dict[req_item.item_code] = {
//                         custom_batch_no: req_item.custom_batch_no,
//                         custom_drawing_no: req_item.custom_drawing_no,
//                         custom_drawing_rev_no: req_item.custom_drawing_rev_no,
//                         custom_pattern_drawing_no: req_item.custom_pattern_drawing_no,
//                         custom_pattern_drawing_rev_no: req_item.custom_pattern_drawing_rev_no,
//                         custom_purchase_specification_no: req_item.custom_purchase_specification_no,
//                         custom_purchase_specification_rev_no: req_item.custom_purchase_specification_rev_no,
//                     };
//                 }
//             });

//         })
//         .catch(err => {
//             console.error('Error fetching work order details:', err);
//         });
// }

// function apply_custom_fields_to_item_row(row, custom_fields) {
//     if (custom_fields.custom_batch_no) {
//         frappe.model.set_value(row.doctype, row.name, 'custom_batch_no', custom_fields.custom_batch_no);
//     }
//     if (custom_fields.custom_drawing_no) {
//         frappe.model.set_value(row.doctype, row.name, 'custom_drawing_no', custom_fields.custom_drawing_no);
//     }
//     if (custom_fields.custom_drawing_rev_no) {
//         frappe.model.set_value(row.doctype, row.name, 'custom_drawing_rev_no', custom_fields.custom_drawing_rev_no);
//     }
//     if (custom_fields.custom_pattern_drawing_no) {
//         frappe.model.set_value(row.doctype, row.name, 'custom_pattern_drawing_no', custom_fields.custom_pattern_drawing_no);
//     }
//     if (custom_fields.custom_pattern_drawing_rev_no) {
//         frappe.model.set_value(row.doctype, row.name, 'custom_pattern_drawing_rev_no', custom_fields.custom_pattern_drawing_rev_no);
//     }
//     if (custom_fields.custom_purchase_specification_no) {
//         frappe.model.set_value(row.doctype, row.name, 'custom_purchase_specification_no', custom_fields.custom_purchase_specification_no);
//     }
//     if (custom_fields.custom_purchase_specification_rev_no) {
//         frappe.model.set_value(row.doctype, row.name, 'custom_purchase_specification_rev_no', custom_fields.custom_purchase_specification_rev_no);
//     }
// }

// async function set_custom_fields_from_work_order(frm) {
//     if (!frm.doc.work_order) return;

//     try {
//         const wo = await frappe.db.get_doc('Work Order', frm.doc.work_order);
//         if (!wo) return;
//         console.log('work order fetched', wo);

//         // Set BOM on parent if available
//         if (wo.bom_no) {
//             frm.set_value('bom_no', wo.bom_no);
//         }

//         // Set custom_batch_no in parent if available
//         const batch_no = wo.custom_batch_no;
//         if (batch_no && !frm.doc.custom_batch_no) {
//             frm.set_value('custom_batch_no', batch_no);
//         }

//         // Prepare dictionary of required_items by item_code
//         const required_items_dict = {};
//         (wo.required_items || []).forEach(req_item => {
//             if (req_item.item_code) {
//                 required_items_dict[req_item.item_code] = {
//                     custom_batch_no: req_item.custom_batch_no,
//                     custom_drawing_no: req_item.custom_drawing_no,
//                     custom_drawing_rev_no: req_item.custom_drawing_rev_no,
//                     custom_pattern_drawing_no: req_item.custom_pattern_drawing_no,
//                     custom_pattern_drawing_rev_no: req_item.custom_pattern_drawing_rev_no,
//                     custom_purchase_specification_no: req_item.custom_purchase_specification_no,
//                     custom_purchase_specification_rev_no: req_item.custom_purchase_specification_rev_no
//                 };
//             }
//         });

//         // Apply to each item row in Stock Entry
//         if (frm.doc.items && frm.doc.items.length > 0) {
//             frm.doc.items.forEach(row => {
//                 const custom_fields = required_items_dict[row.item_code];
//                 if (custom_fields) {
//                     apply_custom_fields_to_item_row(row, custom_fields);
//                 }
//             });
//             frm.refresh_field('items');
//         }
//     } catch (err) {
//         console.error('Error fetching work order details:', err);
//     }
// }


// // Helper function to set batch no in items table
// function set_batch_no_in_items(frm, batch_no) {
//     if (frm.doc.items && frm.doc.items.length > 0) {
//         frm.doc.items.forEach(item => {
//             frappe.model.set_value(item.doctype, item.name, 'custom_batch_no', batch_no);
//         });
//         frm.refresh_field('items');
//     }
// }

// frappe.ui.form.on('Stock Entry Detail', {
//     item_code: function(frm, cdt, cdn) {
//         let row = locals[cdt][cdn];

//         // If batch already exists in parent, push it into the row
//         if (frm.doc.custom_batch_no && row.item_code) {
//             frappe.model.set_value(row.doctype, row.name, 'custom_batch_no', frm.doc.custom_batch_no);
//         }
//     }
// });

frappe.ui.form.on('Stock Entry', {
    onload: function(frm) {
        // Case 1: Work Order is already set
        if (frm.doc.work_order && !frm.doc.custom_batch_no) {
            set_custom_fields_from_work_order(frm);
        }
        // Case 2: Batch exists, set in items
        if (frm.doc.custom_batch_no) {
            set_batch_no_in_items(frm, frm.doc.custom_batch_no);
        }
        // Case 3: Subcontracting Order present on new doc
        if (frm.doc.subcontracting_order && frm.is_new()) {
            set_custom_fields_in_items(frm);
        }
    },

    work_order: function(frm) {
        if (!frm.doc.work_order) return;
        console.log('work_order changed:', frm.doc.work_order);
        set_custom_fields_from_work_order(frm);
    },

    subcontracting_order: function(frm) {
        if (frm.doc.subcontracting_order) {
            set_custom_fields_in_items(frm);
        }
    },

    custom_batch_no: function(frm) {
        if (frm.doc.custom_batch_no) {
            set_batch_no_in_items(frm, frm.doc.custom_batch_no);
        }
    },

    purpose: function(frm) {
        if (frm.doc.work_order && frm.doc.items) {
            if (['Manufacture', 'Material Transfer for Manufacture'].includes(frm.doc.purpose)) {
                set_custom_fields_from_work_order(frm);
            }
        }
    }
});


// ✅ Fetch and apply custom fields from Work Order without recreating items
// ✅ Fetch and apply custom fields from Work Order
async function set_custom_fields_from_work_order(frm) {
    if (!frm.doc.work_order) return;

    try {
        const work_order = await frappe.db.get_doc('Work Order', frm.doc.work_order);
        console.log("✅ Work Order fetched:", work_order);

        // Set header fields
        if (work_order.bom_no) {
            frm.set_value('bom_no', work_order.bom_no);
        }
        if (work_order.custom_batch_no) {
            frm.set_value('custom_batch_no', work_order.custom_batch_no);
        }

        // Wait for items to be populated (important for async operations)
        await frappe.timeout(0.5);

        // Check if items exist
        if (!frm.doc.items || frm.doc.items.length === 0) {
            console.log("⚠️ No items found in Stock Entry yet");
            return;
        }

        // Create a map of required_items by item_code for faster lookup
        const required_items_map = {};
        if (work_order.required_items && work_order.required_items.length > 0) {
            work_order.required_items.forEach(req_item => {
                if (req_item.item_code ) {
                    required_items_map[req_item.item_code] = req_item;
                }
            });
        }

        console.log("📦 Required items map:", required_items_map);

        // Apply custom fields to each item in Stock Entry
        let updated_count = 0;
        frm.doc.items.forEach(item => {
            // Match by item_code (primary match)
            const match = required_items_map[item.item_code];
            
            console.log(`🔍 Checking item: ${item.item_code}`, match ? '✅ Match found' : '❌ No match');

            if (match) {
                // Set custom_batch_no
                if (match.custom_batch_no) {
                    frappe.model.set_value(item.doctype, item.name, 'custom_batch_no', match.custom_batch_no);
                }
                
                // Set drawing fields
                if (match.custom_drawing_no) {
                    frappe.model.set_value(item.doctype, item.name, 'custom_drawing_no', match.custom_drawing_no);
                }
                if (match.custom_drawing_rev_no) {
                    frappe.model.set_value(item.doctype, item.name, 'custom_drawing_rev_no', match.custom_drawing_rev_no);
                }
                
                // Set pattern drawing fields
                if (match.custom_pattern_drawing_no) {
                    frappe.model.set_value(item.doctype, item.name, 'custom_pattern_drawing_no', match.custom_pattern_drawing_no);
                }
                if (match.custom_pattern_drawing_rev_no) {
                    frappe.model.set_value(item.doctype, item.name, 'custom_pattern_drawing_rev_no', match.custom_pattern_drawing_rev_no);
                }
                
                // Set purchase specification fields
                if (match.custom_purchase_specification_no) {
                    frappe.model.set_value(item.doctype, item.name, 'custom_purchase_specification_no', match.custom_purchase_specification_no);
                }
                if (match.custom_purchase_specification_rev_no) {
                    frappe.model.set_value(item.doctype, item.name, 'custom_purchase_specification_rev_no', match.custom_purchase_specification_rev_no);
                }
                
                updated_count++;
            }
        });

        frm.refresh_field('items');
        
        if (updated_count > 0) {
            frappe.show_alert({ 
                message: `Custom fields updated for ${updated_count} item(s) from Work Order`, 
                indicator: "green" 
            });
        } else {
            frappe.show_alert({ 
                message: "No matching items found to update", 
                indicator: "orange" 
            });
        }

    } catch (err) {
        console.error("⚠️ Error fetching Work Order:", err);
        frappe.show_alert({ 
            message: "Failed to fetch Work Order details", 
            indicator: "red" 
        });
    }
}


// ✅ Helper: Apply to One Item Row
function apply_custom_fields_to_item_row(row, custom_fields) {
    for (const [field, value] of Object.entries(custom_fields)) {
        if (value) frappe.model.set_value(row.doctype, row.name, field, value);
    }
}


// ✅ Helper: Set Batch in All Items
function set_batch_no_in_items(frm, batch_no) {
    if (!batch_no || !frm.doc.items) return;
    frm.doc.items.forEach(item => {
        frappe.model.set_value(item.doctype, item.name, 'custom_batch_no', batch_no);
    });
    frm.refresh_field('items');
}


// ✅ Optional (for Subcontracting Orders)
async function set_custom_fields_in_items(frm) {
    if (!frm.doc.subcontracting_order) return;

    try {
        const so = await frappe.db.get_doc('Subcontracting Order', frm.doc.subcontracting_order);
        if (!so.supplied_items?.length) return;

        frm.doc.items.forEach(item => {
            let supplied_item = so.supplied_items.find(si =>
                si.rm_item_code === item.item_code &&
                si.main_item_code === item.subcontracted_item
            );

            if (supplied_item) {
                const custom_fields = {
                    custom_batch_no: supplied_item.custom_batch_no,
                    custom_drawing_no: supplied_item.custom_drawing_no,
                    custom_drawing_rev_no: supplied_item.custom_drawing_rev_no,
                    custom_pattern_drawing_no: supplied_item.custom_pattern_drawing_no,
                    custom_pattern_drawing_rev_no: supplied_item.custom_pattern_drawing_rev_no,
                    custom_purchase_specification_no: supplied_item.custom_purchase_specification_no,
                    custom_purchase_specification_rev_no: supplied_item.custom_purchase_specification_rev_no,
                    bom_reference: supplied_item.bom_reference
                };
                apply_custom_fields_to_item_row(item, custom_fields);
            }
        });

        frm.refresh_field('items');
    } catch (err) {
        console.error('❌ Error fetching Subcontracting Order details:', err);
    }
}


// ✅ Stock Entry Detail Event
frappe.ui.form.on('Stock Entry Detail', {
    item_code: function(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (frm.doc.custom_batch_no && row.item_code) {
            frappe.model.set_value(row.doctype, row.name, 'custom_batch_no', frm.doc.custom_batch_no);
        }
    },
    fetch_serial_number: function (frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    _validate_and_open(frm, row);
  },
        

});



/**

 * Three allocation scenarios handled:
 *   A  selected == qty  → direct append
 *   B  selected <  qty  → confirm auto-fill remaining serials randomly
 *   C  selected >  qty  → confirm trim to qty by removing randomly
 */



/* ══════════════════════════════════════════════════════════════════════════
   STEP 1 — Validate: batch must exist before we proceed
══════════════════════════════════════════════════════════════════════════ */
function _validate_and_open(frm, row) {
  const batch =  row.batch_no || "";

  if (!batch) {
    frappe.msgprint({
      title: __("Batch Not Selected"),
      message: __(
        "Please select a <strong>Batch Number</strong> " +
        "before allocating serial numbers."
      ),
      indicator: "orange",
    });
    return;
  }

 
  const qty = parseFloat(row.qty) || 0;
  if (qty <= 0) {
    frappe.msgprint(__("Please enter a valid Quantity before allocating serial numbers."));
    return;
  }

  _fetch_and_open(frm, row, batch, qty);
}

/* ══════════════════════════════════════════════════════════════════════════
   STEP 2 — Fetch serial numbers for the batch (all pages)
   Large datasets: frappe.call returns a JSON list; we push through all
   results using limit_start pagination so the browser never hangs.
══════════════════════════════════════════════════════════════════════════ */
function _fetch_and_open(frm, row, batch, qty) {
  const PAGE_SIZE = 500;
  let allSerials = [];
  let start = 0;



  function fetchPage() {
    frappe.call({
      method: "frappe.client.get_list",
      args: {
        doctype: "Serial Number",
        filters: {
          docstatus: 1,
          batch: batch,
         stock_entry:""
        },
        fields: ["name"],
        limit_start: start,
        limit_page_length: PAGE_SIZE,
        order_by: "name asc",
      },
      freeze: true,
      freeze_message: __("Fetching Serial Numbers…"),
      callback: function (r) {
        const page = (r.message || []).map((s) => s.name);
        allSerials = allSerials.concat(page);

        if (page.length === PAGE_SIZE) {
          // There may be more — fetch next page
          start += PAGE_SIZE;
          fetchPage();
        } else {
          // All pages done
     

          if (!allSerials.length) {
            frappe.msgprint({
              title: __("No Serial Numbers Found"),
              message: __(
                `No serial numbers found for Batch ` +
                `<strong>${frappe.utils.escape_html(batch)}</strong>.`
              ),
              indicator: "red",
            });
            return;
          }

          const existing = _parse_existing_serials(row);
          _build_dialog(frm, row, batch, qty, allSerials, existing);
        }
      },
      error: function () {
     
        frappe.msgprint({
          title: __("Error"),
          message: __("Failed to fetch serial numbers. Please try again."),
          indicator: "red",
        });
      },
    });
  }

  fetchPage();
}

/* ══════════════════════════════════════════════════════════════════════════
   STEP 3 — Build the selection dialog
   Virtual-scroll renders rows in chunks of CHUNK_SIZE so even 50 000+
   serials feel instant. Only DOM nodes in view are ever created.
══════════════════════════════════════════════════════════════════════════ */
const CHUNK_SIZE = 100; // rows appended per scroll batch

function _build_dialog(frm, row, batch, qty, allSerials, preSelected) {

  /* ── Styles (injected once) ─────────────────────────────────────────── */
  const STYLE_ID = "sna-style";
  if (!document.getElementById(STYLE_ID)) {
    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = `
      .sna-root { font-family: var(--font-stack, sans-serif); }

      /* Info chips */
      .sna-info-bar {
        display: flex; flex-wrap: wrap; gap: 8px;
        padding: 10px 0 14px;
        border-bottom: 1px solid var(--border-color, #ddd);
        margin-bottom: 12px;
      }
      .sna-chip {
        display: flex; flex-direction: column;
        background: var(--control-bg, #f5f7fa);
        border: 1px solid var(--border-color, #d1d8dd);
        border-radius: 6px; padding: 6px 14px;
        min-width: 110px;
      }
      .sna-label {
        font-size: 10px; color: var(--text-muted, #888);
        text-transform: uppercase; letter-spacing: .5px;
      }
      .sna-chip strong { font-size: 14px; margin-top: 3px; }
      .sna-chip.primary strong { color: var(--primary, #5e64ff); }
      .sna-chip.success strong { color: var(--green-600, #28a745); }

      /* Toolbar */
      .sna-toolbar {
        display: flex; align-items: center; gap: 8px;
        margin-bottom: 10px;
      }
      .sna-search { flex: 1; }
      .sna-bulk-btns { display: flex; gap: 6px; white-space: nowrap; }

      /* List container */
      .sna-list-wrap {
        border: 1px solid var(--border-color, #d1d8dd);
        border-radius: 6px;
        height: 360px;
        overflow-y: auto;
        background: var(--card-bg, #fff);
        will-change: scroll-position;
      }

      /* Individual row */
      .sna-row {
        display: flex; align-items: center;
        padding: 7px 12px;
        border-bottom: 1px solid var(--border-color, #f0f0f0);
        cursor: pointer;
        transition: background .1s;
        user-select: none;
      }
      .sna-row:last-child { border-bottom: none; }
      .sna-row:hover     { background: var(--blue-50, #f0f4ff); }
      .sna-row.selected  { background: var(--green-50, #f0faf4); }

      .sna-row input[type=checkbox] {
        margin-right: 10px; width: 15px; height: 15px;
        cursor: pointer; flex-shrink: 0;
        accent-color: var(--primary, #5e64ff);
      }
      .sna-serial-label {
        font-size: 13px;
        font-family: var(--monospace-font, "Courier New", monospace);
        flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
      }
      .sna-badge {
        flex-shrink: 0; font-size: 10px; padding: 2px 7px;
        border-radius: 10px; margin-left: 8px;
        background: var(--green-100, #d4edda);
        color: var(--green-700, #155724);
        display: none;
      }
      .sna-row.selected .sna-badge { display: inline; }

      /* Empty state */
      .sna-empty {
        padding: 40px; text-align: center;
        color: var(--text-muted, #888); font-size: 13px;
      }

      /* Status bar */
      .sna-status-bar {
        margin-top: 10px; font-size: 12px;
        color: var(--text-muted, #888);
        display: flex; justify-content: space-between;
      }
      .sna-status-bar .warn { color: var(--orange-500, #e67e22); font-weight: 600; }
      .sna-status-bar .ok   { color: var(--green-600, #28a745); font-weight: 600; }
    `;
    document.head.appendChild(style);
  }

  /* ── Dialog HTML ────────────────────────────────────────────────────── */
  const html = `
    <div class="sna-root">
      <div class="sna-info-bar">
        <div class="sna-chip">
          <span class="sna-label">Batch</span>
          <strong title="${frappe.utils.escape_html(batch)}">
            ${frappe.utils.escape_html(batch)}
          </strong>
        </div>
        <div class="sna-chip primary">
          <span class="sna-label">Required QTY</span>
          <strong>${qty}</strong>
        </div>
        <div class="sna-chip success">
          <span class="sna-label">Selected</span>
          <strong class="js-sel-count">0</strong>
        </div>
        <div class="sna-chip">
          <span class="sna-label">Available</span>
          <strong>${allSerials.length}</strong>
        </div>
      </div>

      <div class="sna-toolbar">
        <input type="text" class="sna-search form-control"
               placeholder="&#128269;  Search serial numbers…" />
        <div class="sna-bulk-btns">
          <button class="btn btn-xs btn-default js-select-visible">
            Select All Visible
          </button>
          <button class="btn btn-xs btn-default js-clear-all">
            Clear All
          </button>
        </div>
      </div>

      <div class="sna-list-wrap js-wrap">
        <div class="sna-list js-list"></div>
      </div>

      <div class="sna-status-bar">
        <span class="js-showing">Showing 0 of ${allSerials.length}</span>
        <span class="js-diff"></span>
      </div>
    </div>
  `;

  /* ── Create Frappe dialog ───────────────────────────────────────────── */
  const dialog = new frappe.ui.Dialog({
    title: __("Add Serial Numbers"),
    size: "large",
    fields: [{ fieldtype: "HTML", fieldname: "sna_body" }],
    primary_action_label: __("Add Serial Numbers"),
    primary_action: function () {
      const selected = Array.from(selectedSet);
      _handle_allocation(frm, row, allSerials, selected, qty, dialog, batch);
    },
    secondary_action_label: __("Cancel"),
    secondary_action: function () { dialog.hide(); },
  });

  dialog.fields_dict.sna_body.$wrapper.html(html);
  dialog.show();

  /* ── Local state ────────────────────────────────────────────────────── */
  const selectedSet = new Set(preSelected);
  let visibleSerials = [...allSerials]; // filtered view
  let renderedCount = 0;               // how many rows are in DOM

  /* ── jQuery shorthand ───────────────────────────────────────────────── */
  const $root     = dialog.$wrapper.find(".sna-root");
  const $list     = $root.find(".js-list");
  const $wrap     = $root.find(".js-wrap");
  const $selCount = $root.find(".js-sel-count");
  const $showing  = $root.find(".js-showing");
  const $diff     = $root.find(".js-diff");
  const $search   = $root.find(".sna-search");

  /* ── Render helpers ─────────────────────────────────────────────────── */
  function renderChunk(reset) {
    if (reset) {
      $list.empty();
      renderedCount = 0;
    }

    const slice = visibleSerials.slice(renderedCount, renderedCount + CHUNK_SIZE);
    if (!slice.length) {
      if (!renderedCount) {
        $list.html('<div class="sna-empty">No serial numbers found for this search.</div>');
      }
      return;
    }

    const frag = document.createDocumentFragment();
    slice.forEach((sn) => {
      const sel = selectedSet.has(sn);
      const div = document.createElement("div");
      div.className = "sna-row" + (sel ? " selected" : "");
      div.dataset.sn = sn;
      div.innerHTML =
        `<input type="checkbox" ${sel ? "checked" : ""} />` +
        `<span class="sna-serial-label" title="${frappe.utils.escape_html(sn)}">${frappe.utils.escape_html(sn)}</span>` +
        `<span class="sna-badge">&#10003;</span>`;
      frag.appendChild(div);
    });

    $list[0].appendChild(frag);
    renderedCount += slice.length;
    $showing.text(`Showing ${renderedCount} of ${visibleSerials.length}`);
  }

  function updateCounter() {
    const n = selectedSet.size;
    $selCount.text(n);
    const diff = n - qty;
    if (diff === 0) {
      $diff.removeClass("warn").addClass("ok").text("✓ Exact match");
    } else if (diff < 0) {
      $diff.removeClass("ok").addClass("warn").text(`${Math.abs(diff)} short of QTY`);
    } else {
      $diff.removeClass("ok").addClass("warn").text(`${diff} over QTY`);
    }
  }

  /* ── Initial render ─────────────────────────────────────────────────── */
  renderChunk(true);
  updateCounter();

  /* ── Infinite scroll ────────────────────────────────────────────────── */
  $wrap.on("scroll", function () {
    if (this.scrollHeight - this.scrollTop - this.clientHeight < 200) {
      renderChunk(false);
    }
  });

  /* ── Row toggle (event delegation – O(1) regardless of list size) ───── */
  $list.on("click", ".sna-row", function (e) {
    const sn = this.dataset.sn;
    const cb = this.querySelector("input[type=checkbox]");

    // If the click wasn't directly on the checkbox, toggle it
    if (e.target !== cb) cb.checked = !cb.checked;

    if (cb.checked) {
      selectedSet.add(sn);
      this.classList.add("selected");
    } else {
      selectedSet.delete(sn);
      this.classList.remove("selected");
    }
    updateCounter();
  });

  /* ── Search (debounced 200 ms) ──────────────────────────────────────── */
  let searchTimer;
  $search.on("input", function () {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      const q = this.value.trim().toLowerCase();
      visibleSerials = q
        ? allSerials.filter((s) => s.toLowerCase().includes(q))
        : [...allSerials];
      renderChunk(true);
    }, 200);
  });

  /* ── Bulk: Select all visible ───────────────────────────────────────── */
  $root.find(".js-select-visible").on("click", function () {
    // Add only rendered visible serials (user can scroll more)
    visibleSerials.forEach((sn) => selectedSet.add(sn));
    $list.find(".sna-row").each(function () {
      this.classList.add("selected");
      this.querySelector("input[type=checkbox]").checked = true;
    });
    updateCounter();
  });

  /* ── Bulk: Clear all ────────────────────────────────────────────────── */
  $root.find(".js-clear-all").on("click", function () {
    selectedSet.clear();
    $list.find(".sna-row").each(function () {
      this.classList.remove("selected");
      this.querySelector("input[type=checkbox]").checked = false;
    });
    updateCounter();
  });
}

/* ══════════════════════════════════════════════════════════════════════════
   STEP 4 — Handle the three allocation scenarios
══════════════════════════════════════════════════════════════════════════ */
function _handle_allocation(frm, row, allSerials, selected, qty, dialog, batch) {
  const selCount = selected.length;

  /* ── A: Exact match ─────────────────────────────────────────────────── */
  if (selCount === qty) {
    _apply_serials(frm, row, selected);
    dialog.hide();
    frappe.show_alert({
      message: __(`${selCount} serial number(s) added successfully.`),
      indicator: "green",
    });
    return;
  }

  /* ── B: Fewer than qty ──────────────────────────────────────────────── */
  if (selCount < qty) {
    const needed = qty - selCount;

    frappe.confirm(
      __(
        `You selected <strong>${selCount}</strong> serial number(s), ` +
        `but the required QTY is <strong>${qty}</strong>.<br><br>` +
        `<strong>${needed}</strong> remaining serial number(s) will be ` +
        `<strong>auto-selected randomly</strong> from the available pool.<br><br>` +
        `Do you want to proceed?`
      ),
      /* ── Yes ── */
      function () {
        const unselected = allSerials.filter((s) => !selected.includes(s));

        if (unselected.length < needed) {
          frappe.msgprint({
            title: __("Insufficient Serial Numbers"),
            message: __(
              `Only <strong>${allSerials.length}</strong> serial number(s) ` +
              `are available for Batch <strong>${frappe.utils.escape_html(batch)}</strong>, ` +
              `which is not enough to fulfil QTY of <strong>${qty}</strong>.`
            ),
            indicator: "red",
          });
          return;
        }

        const autoFilled = _random_sample(unselected, needed);
        const final = [...selected, ...autoFilled];
        _apply_serials(frm, row, final);
        dialog.hide();
        frappe.show_alert({
          message: __(
            `${selCount} manually selected + ${autoFilled.length} auto-filled ` +
            `= <strong>${final.length}</strong> serial number(s) added.`
          ),
          indicator: "green",
        });
      },
      /* ── No: fall back to dialog (stays open) ── */
      function () { /* no-op */ }
    );
    return;
  }

  /* ── C: More than qty ───────────────────────────────────────────────── */
  if (selCount > qty) {
    const excess = selCount - qty;

    frappe.confirm(
      __(
        `You selected <strong>${selCount}</strong> serial number(s), ` +
        `but the required QTY is only <strong>${qty}</strong>.<br><br>` +
        `<strong>${excess}</strong> serial number(s) will be ` +
        `<strong>removed randomly</strong> so that exactly ${qty} are added.<br><br>` +
        `Do you want to proceed?`
      ),
      /* ── Yes ── */
      function () {
        const trimmed = _random_sample(selected, qty);
        _apply_serials(frm, row, trimmed);
        dialog.hide();
        frappe.show_alert({
          message: __(
            `Trimmed to <strong>${qty}</strong> serial number(s) and added successfully.`
          ),
          indicator: "green",
        });
      },
      /* ── No: fall back to dialog (stays open) ── */
      function () { /* no-op */ }
    );
    return;
  }
}

/* ══════════════════════════════════════════════════════════════════════════
   HELPERS
══════════════════════════════════════════════════════════════════════════ */

/** Write the final serial list to the child-row field and refresh the form */
function _apply_serials(frm, row, serials) {
  frappe.model.set_value(row.doctype, row.name, "serial_no", serials.join("\n"));
  frm.dirty();
  frm.refresh_field("items");
}

/** Parse newline / comma separated serials from the existing field value */
function _parse_existing_serials(row) {
  return (row.serial_no || "")
    .split(/[\n,]/)
    .map((s) => s.trim())
    .filter(Boolean);
}

/**
 * Partial Fisher-Yates random sample.
 * O(k) time, O(n) space — safe for very large arrays.
 *
 * @param {string[]} arr  - source array (will NOT be mutated)
 * @param {number}   k    - number of items to pick
 * @returns {string[]}    - sampled array of length k
 */
function _random_sample(arr, k) {
  if (k >= arr.length) return [...arr];
  const pool = [...arr];
  for (let i = 0; i < k; i++) {
    const j = i + Math.floor(Math.random() * (pool.length - i));
    const tmp = pool[i];
    pool[i] = pool[j];
    pool[j] = tmp;
  }
  return pool.slice(0, k);
}