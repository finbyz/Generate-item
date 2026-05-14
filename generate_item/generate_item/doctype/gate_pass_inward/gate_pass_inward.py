
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate


class GatePassInward(Document):

    def before_submit(self):
        create_stock_entry(self)

    def on_submit(self):
        self.update_outward_quantities()

    def on_cancel(self):
        
        self.update_outward_quantities(cancel=True)

    # ------------------------------------------------------------------ #
    #  GPO qty sync                                                        #
    # ------------------------------------------------------------------ #

    def update_outward_quantities(self, cancel=False):
        if not self.gate_pass_outward:
            return

        if frappe.flags.get("cancelling_gpo") == self.gate_pass_outward:
            return

        gpo      = frappe.get_doc("Gate Pass Outward", self.gate_pass_outward)
        is_stock = bool(gpo.is_stock_item)

        if is_stock:
            self._update_stock_item_qtys(gpo, cancel)
        else:
            self._update_sub_component_qtys(gpo, cancel)

        gpo.reload()
        child_rows    = gpo.item_detail if is_stock else gpo.items
        total_pending = sum((r.pending_qty or 0) for r in child_rows)
        new_status    = "Closed" if total_pending == 0 else "Open"

        frappe.db.set_value(
            "Gate Pass Outward", self.gate_pass_outward, "status", new_status
        )
        frappe.msgprint(
            f"Updated quantities in <b>{self.gate_pass_outward}</b>. "
            f"Status: <b>{new_status}</b>",
            alert=True, indicator="green"
        )

    def _update_stock_item_qtys(self, gpo, cancel):
        outward_map = {row.item: row for row in gpo.item_detail}

        for gpi_row in self.item_detail:
            item_code = gpi_row.item
            if item_code not in outward_map:
                frappe.throw(
                    _(f"Item <b>{item_code}</b> not found in "
                      f"Gate Pass Outward {self.gate_pass_outward}")
                )

            gpo_row    = outward_map[item_code]
            qty_change = gpi_row.qty or 0

            if cancel:
                gpo_row.received_qty = max((gpo_row.received_qty or 0) - qty_change, 0)
            else:
                new_received = (gpo_row.received_qty or 0) + qty_change
                if new_received > (gpo_row.qty or 0):
                    frappe.throw(
                        _(f"Receiving qty for <b>{item_code}</b> exceeds sent qty "
                          f"in {self.gate_pass_outward}. "
                          f"(Sent: {gpo_row.qty}, "
                          f"Already received: {gpo_row.received_qty}, "
                          f"Receiving now: {qty_change})")
                    )
                gpo_row.received_qty = new_received

            gpo_row.pending_qty = (gpo_row.qty or 0) - (gpo_row.received_qty or 0)

            frappe.db.set_value(
                "Gate Pass Outward Detail", gpo_row.name,
                {
                    "received_qty": gpo_row.received_qty,
                    "pending_qty" : gpo_row.pending_qty,
                }
            )

    def _update_sub_component_qtys(self, gpo, cancel):
        outward_map = {row.sub_component: row for row in gpo.items}

        for gpi_row in self.items:
            sc = gpi_row.sub_component
            if sc not in outward_map:
                frappe.throw(
                    _(f"Sub Component <b>{sc}</b> not found in "
                      f"Gate Pass Outward {self.gate_pass_outward}")
                )

            gpo_row    = outward_map[sc]
            qty_change = gpi_row.sent_qty or 0

            if cancel:
                gpo_row.received_qty = max((gpo_row.received_qty or 0) - qty_change, 0)
            else:
                new_received = (gpo_row.received_qty or 0) + qty_change
                if new_received > (gpo_row.qty or 0):
                    frappe.throw(
                        _(f"Receiving qty for <b>{sc}</b> exceeds sent qty "
                          f"in {self.gate_pass_outward}. "
                          f"(Sent: {gpo_row.qty}, "
                          f"Already received: {gpo_row.received_qty}, "
                          f"Receiving now: {qty_change})")
                    )
                gpo_row.received_qty = new_received

            gpo_row.pending_qty = (gpo_row.qty or 0) - (gpo_row.received_qty or 0)

            frappe.db.set_value(
                "Gate Pass Outward Item", gpo_row.name,
                {
                    "received_qty": gpo_row.received_qty,
                    "pending_qty" : gpo_row.pending_qty,
                }
            )


# ─────────────────────────────────────────────────────────────────────────────
# STOCK ENTRY — exact same pattern as GPO working code
# ─────────────────────────────────────────────────────────────────────────────

def create_stock_entry(doc):
    """
    Smart Stock Entry lifecycle tied to GPI submission.
    Always Material Transfer (items returning from job work).

    ┌──────────────────────┬─────────────────────────────────────────────────┐
    │ stock_entry field    │ Behaviour                                       │
    ├──────────────────────┼─────────────────────────────────────────────────┤
    │ Empty                │ Create new SE → try submit                      │
    │                      │  ✓ success → GPI proceeds (ref saved via doc)  │
    │                      │  ✗ error   → rollback to draft, ref saved, STOP│
    ├──────────────────────┼─────────────────────────────────────────────────┤
    │ Has ref (draft SE)   │ Update existing SE → try submit                 │
    │                      │  ✓ success → GPI proceeds                      │
    │                      │  ✗ error   → keep draft updated, STOP          │
    ├──────────────────────┼─────────────────────────────────────────────────┤
    │ Has ref (submitted)  │ Already done — skip entirely                    │
    └──────────────────────┴─────────────────────────────────────────────────┘
    """
    if not doc.is_stock_item:
        return

    if not doc.item_detail:
        frappe.throw(
            _("No items found in Gate Pass Inward {0}").format(doc.name)
        )

    purpose = "Material Transfer"

    # ── 1. Pre-flight validation ───────────────────────────────────────────
    _validate_item_rows(doc)

    # ── 2. Resolve: new SE or update existing draft ───────────────────────
    se, is_new = _resolve_stock_entry(doc, doc.get("stock_entry"))

    if se is None:
        return   # already submitted — skip

    # ── 3. Rebuild items from current GPI item_detail ─────────────────────
    se.items = []
    for row in doc.item_detail:
        se.append("items", {
            "item_code"                : row.item,
            "qty"                      : row.qty,
            "s_warehouse"              : row.source_warehouse,
            "t_warehouse"              : row.target_warehouse or doc.get("default_target_warehouse"),
            "basic_rate"               : row.rate or 0,
            "allow_zero_valuation_rate": 1 if not row.rate else 0,
            "branch"                   : doc.branch,
            "use_serial_batch_fields"  : 1,
            "serial_no"                : row.get("serial_no") or "",
            "batch_no"                 : row.get("batch_no") or "",
        })

    # ── 4. Persist SE (insert new or save existing draft) ─────────────────
    if is_new:
        se.insert(ignore_permissions=True)
    else:
        se.save(ignore_permissions=True)

    # ── 5. Store reference on in-memory doc object ────────────────────────
    doc.stock_entry = se.name

    # ── 6. Attempt SE submission using a savepoint ────────────────────────
    SAVEPOINT = "gpi_se_submit"
    frappe.db.savepoint(SAVEPOINT)

    try:
        se.submit()
        frappe.msgprint(
            _("Stock Entry {0} ({1}) submitted successfully.").format(
                frappe.bold(se.name), purpose
            ),
            indicator="green",
            alert=True,
        )

    except Exception as e:
        frappe.db.rollback(save_point=SAVEPOINT)

        frappe.db.sql(
            """UPDATE `tabGate Pass Inward`
               SET stock_entry = %s
               WHERE name = %s""",
            (se.name, doc.name)
        )
        frappe.db.commit()

        _throw_se_error(se.name, str(e))




# ─────────────────────────────────────────────────────────────────────────────
# Helpers — same structure as GPO
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_stock_entry(doc, existing_se_name):
    if existing_se_name and frappe.db.exists("Stock Entry", existing_se_name):
        se = frappe.get_doc("Stock Entry", existing_se_name)

        if se.docstatus == 1:
            return None, False

        if se.docstatus == 2:
            frappe.msgprint(
                _("Previous Stock Entry {0} was cancelled. Creating a new one.").format(
                    frappe.bold(existing_se_name)
                ),
                indicator="orange", alert=True,
            )
            return _build_new_se(doc), True

        # docstatus == 0 — update draft in place
        se.stock_entry_type = "Material Transfer"
        se.purpose          = "Material Transfer"
        se.posting_date     = doc.date or nowdate()
        se.branch           = doc.branch
        se.remarks          = _("Auto-created via Gate Pass Inward: {0}").format(doc.name)
        return se, False

    return _build_new_se(doc), True


def _build_new_se(doc):
    se = frappe.new_doc("Stock Entry")
    se.stock_entry_type = "Material Transfer"
    se.purpose          = "Material Transfer"
    se.branch           = doc.branch
    se.posting_date     = doc.date or nowdate()
    se.company          = frappe.defaults.get_user_default("Company")
    se.remarks          = _("Auto-created via Gate Pass Inward: {0}").format(doc.name)
    return se


def _validate_item_rows(doc):
    for row in doc.item_detail:
        if not row.qty or row.qty <= 0:
            frappe.throw(
                _("Row {0}: Quantity must be greater than zero "
                  "for item <b>{1}</b>.").format(row.idx, row.item)
            )
        if not row.source_warehouse:
            frappe.throw(
                _("Row {0}: <b>Source Warehouse</b> is required "
                  "for item <b>{1}</b>.").format(row.idx, row.item)
            )
        if not row.get("target_warehouse") and not doc.get("default_target_warehouse"):
            frappe.throw(
                _("Row {0}: <b>Target Warehouse</b> is required "
                  "for item <b>{1}</b>.").format(row.idx, row.item)
            )

        has_serial = frappe.db.get_value("Item", row.item, "has_serial_no")
        has_batch  = frappe.db.get_value("Item", row.item, "has_batch_no")

        if has_serial and not row.get("serial_no"):
            frappe.throw(
                _("Row {0}: <b>Serial No</b> is required for item <b>{1}</b>. "
                  "Please fill it in the item table before submitting.").format(
                    row.idx, row.item
                )
            )
        if has_batch and not row.get("batch_no"):
            frappe.throw(
                _("Row {0}: <b>Batch No</b> is required for item <b>{1}</b>. "
                  "Please fill it in the item table before submitting.").format(
                    row.idx, row.item
                )
            )


def _throw_se_error(se_name, raw_error):
    clean_error = raw_error.replace("<br>", "\n").split("\n")[0].strip()
    frappe.throw(
        _(
            "Stock Entry {se} was saved as <b>Draft</b> — "
            "automatic submission failed.<br><br>"
            "<b>Reason:</b> {err}<br><br>"
            "<b>What to do next:</b><br>"
            "1. Fix the issue on this Gate Pass Inward "
            "(e.g., fill in <b>Serial / Batch No.</b> in the item table, "
            "correct warehouses, etc.).<br>"
            "2. Re-submit — the existing draft Stock Entry "
            "<b>{se}</b> will be updated automatically, not duplicated."
        ).format(se=se_name, err=clean_error),
        title=_("Stock Entry Draft Saved — Action Required")
    )


# ─────────────────────────────────────────────────────────────────────────────
# Shared whitelist utility
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_draft_inward_info(gate_pass_outward):
    draft_entries = frappe.get_all(
        "Gate Pass Inward",
        filters={"gate_pass_outward": gate_pass_outward, "docstatus": 0},
        fields=["name"]
    )
    if not draft_entries:
        return {"has_draft": False}

    gpo      = frappe.get_doc("Gate Pass Outward", gate_pass_outward)
    is_stock = bool(gpo.is_stock_item)

    if is_stock:
        pending_map = {row.item: (row.pending_qty or 0) for row in gpo.item_detail}
    else:
        pending_map = {row.sub_component: (row.pending_qty or 0) for row in gpo.items}

    total_pending   = sum(pending_map.values())
    total_draft_qty = 0
    draft_names     = []

    for entry in draft_entries:
        gpi_doc    = frappe.get_doc("Gate Pass Inward", entry.name)
        draft_names.append(entry.name)
        child_rows = gpi_doc.item_detail if is_stock else gpi_doc.items
        for row in child_rows:
            total_draft_qty += (row.qty if is_stock else row.sent_qty) or 0

    return {
        "has_draft"      : True,
        "draft_names"    : draft_names,
        "total_pending"  : total_pending,
        "total_draft_qty": total_draft_qty,
        "fully_covered"  : total_draft_qty >= total_pending,
        "is_stock_item"  : is_stock,
    }