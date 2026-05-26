


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate
from frappe.utils import flt




class GatePassOutward(Document):

    def before_submit(self):
        create_stock_entry(self)

    def before_cancel(self):
        _on_gpo_before_cancel(self)

    def validate(self):

        self.calculate_totals()

    def calculate_totals(self):

        total_qty = 0
        total_amount = 0

        #  table
        item_table = self.item_detail if self.is_stock_item else self.items
        for row in item_table:

            row.amount = flt(row.qty) * flt(row.rate)

            total_qty += flt(row.qty)
            total_amount += flt(row.amount)

        self.total_gp_qty = total_qty
        self.total_gp_amount = total_amount








# ─────────────────────────────────────────────────────────────────────────────
# CANCEL
# ─────────────────────────────────────────────────────────────────────────────

def _on_gpo_before_cancel(doc, method=None):
    try:
        frappe.flags["cancelling_gpo"] = doc.name 
      

        # 1. Cancel linked submitted GPIs
        _cancel_linked_gpis(doc)

        # 2. Reset GPO item quantities
        #  — check is_stock_item and reset  table
        if doc.is_stock_item:
            for item in doc.item_detail:
                frappe.db.set_value(
                    "Gate Pass Outward Detail",
                    item.name,
                    {"received_qty": 0, "pending_qty": 0}
                )
        else:
            for item in doc.items:
                frappe.db.set_value(
                    "Gate Pass Outward Item",
                    item.name,
                    {"received_qty": 0, "pending_qty": 0}
                )

       
      

        frappe.db.commit()

    except Exception:
        frappe.log_error(
            title=f"GPO Cancel Error — {doc.name}",
            message=frappe.get_traceback()
        )
        raise


def _cancel_linked_gpis(gpo_doc):
    gpi_names = frappe.get_all(
        "Gate Pass Inward",
        filters={"gate_pass_outward": gpo_doc.name, "docstatus": 1},
        pluck="name",
    )
    for gpi_name in gpi_names:
        try:
            frappe.get_doc("Gate Pass Inward", gpi_name).cancel()
        except Exception:
            frappe.log_error(
                title=f"Cascade GPI Cancel Failed — {gpi_name}",
                message=frappe.get_traceback()
            )
            raise




def create_stock_entry(doc):
    """
    Smart Stock Entry lifecycle tied to GPO submission.

    ┌──────────────────────┬─────────────────────────────────────────────────┐
    │ stock_entry field    │ Behaviour                                       │
    ├──────────────────────┼─────────────────────────────────────────────────┤
    │ Empty                │ Create new SE → try submit                      │
    │                      │  ✓ success → GPO proceeds (ref saved via doc)  │
    │                      │  ✗ error   → rollback to draft, ref saved, STOP│
    ├──────────────────────┼─────────────────────────────────────────────────┤
    │ Has ref (draft SE)   │ Update existing SE → try submit                 │
    │                      │  ✓ success → GPO proceeds                      │
    │                      │  ✗ error   → keep draft updated, STOP          │
    ├──────────────────────┼─────────────────────────────────────────────────┤
    │ Has ref (submitted)  │ Already done — skip entirely                    │
    └──────────────────────┴─────────────────────────────────────────────────┘
    """
    if not doc.is_stock_item:
        return

    if not doc.item_detail:
        frappe.throw(_("No items found in Gate Pass Outward {0}").format(doc.name))

    purpose = "Material Transfer" if doc.returnable == "Yes" else "Material Issue"

    # ── 1. Pre-flight validation (before touching SE) ─────────────────────
    _validate_item_rows(doc, purpose)

    # ── 2. Resolve: new SE or update existing draft ───────────────────────
    se, is_new = _resolve_stock_entry(doc, purpose, doc.get("stock_entry"))

    if se is None:
        # Linked SE is already submitted — nothing to do
        return

    # ── 3. Rebuild items from current GPO item_detail ─────────────────────
    se.items = []
    for row in doc.item_detail:
        item_args = {
            "item_code"                : row.item,
            "qty"                      : row.qty,
            "s_warehouse"              : row.source_warehouse or doc.default_source_warehouse,
            "basic_rate"               : row.rate or 0,
            "allow_zero_valuation_rate": 1 if not row.rate else 0,
            "branch"                   : doc.branch,
            "use_serial_batch_fields"  : 1,          # use serial_no directly
            "serial_no"                : row.get("serial_no") or "",
            "batch_no"                 : row.get("batch_no") or "",
            
           
        }
        if purpose == "Material Transfer":
            item_args["t_warehouse"] = row.target_warehouse
        se.append("items", item_args)

    # ── 4. Persist SE (insert new or save existing draft) ─────────────────
    if is_new:
        se.insert(ignore_permissions=True)
    else:
        se.save(ignore_permissions=True)

    # ── 5. Store reference on in-memory doc object ────────────────────────
    
    doc.stock_entry = se.name  # ← in-memory (persisted by Frappe's db_update)

    # ── 6. Attempt SE submission using a savepoint ────────────────────────
    
    SAVEPOINT = "gpo_se_submit"
    frappe.db.savepoint(SAVEPOINT)

    try:
        se.submit()
        # ── Success ──────────────────────────────────────────────────────
        # doc.stock_entry is already set above; Frappe will persist it.
        frappe.msgprint(
            _("Stock Entry {0} ({1}) submitted successfully.").format(
                frappe.bold(se.name), purpose
            ),
            indicator="green",
            alert=True,
        )

    except Exception as e:
        # ── Failure: roll back SE to draft, keep reference on GPO ─────────
      
        frappe.db.rollback(save_point=SAVEPOINT)

        # SE is now cleanly docstatus=0 (draft) in the DB.
        # doc.stock_entry is already set in memory above — it will NOT be
        # persisted because we are about to throw (GPO won't submit).
        # Use a direct SQL write + commit to save the reference durably.
        frappe.db.sql(
            """UPDATE `tabGate Pass Outward`
               SET stock_entry = %s
               WHERE name = %s""",
            (se.name, doc.name)
        )
        frappe.db.commit()  

        _throw_se_error(se.name, purpose, str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_stock_entry(doc, purpose, existing_se_name):
    """
    Returns (se_doc, is_new).
    Returns (None, False) when the linked SE is already submitted — skip.
    """
    if existing_se_name and frappe.db.exists("Stock Entry", existing_se_name):
        se = frappe.get_doc("Stock Entry", existing_se_name)

        if se.docstatus == 1:
            return None, False                  # already submitted, skip

        if se.docstatus == 2:                   # cancelled — start fresh
            frappe.msgprint(
                _("Previous Stock Entry {0} was cancelled. Creating a new one.").format(
                    frappe.bold(existing_se_name)
                ),
                indicator="orange",
                alert=True,
            )
            return _build_new_se(doc, purpose), True

        # docstatus == 0: update existing draft in place
        se.stock_entry_type = purpose
        se.purpose          = purpose
        se.posting_date     = doc.date or nowdate()
        se.branch           = doc.branch
        se.remarks          = _("Auto-created via Gate Pass Outward: {0}").format(doc.name)
        return se, False

    return _build_new_se(doc, purpose), True


def _build_new_se(doc, purpose):
    """Instantiate a bare (unsaved) Stock Entry."""
    se = frappe.new_doc("Stock Entry")
    se.stock_entry_type = purpose
    se.purpose          = purpose
    se.branch           = doc.branch
    se.posting_date     = doc.date or nowdate()
    se.company          = frappe.defaults.get_user_default("Company")
    se.remarks          = _("Auto-created via Gate Pass Outward: {0}").format(doc.name)
    return se

def _validate_item_rows(doc, purpose):
    for row in doc.item_detail:
        if not row.qty or row.qty <= 0:
            frappe.throw(
                _("Row {0}: Quantity must be greater than zero "
                  "for item <b>{1}</b>.").format(row.idx, row.item)
            )
        if purpose == "Material Transfer" and not row.target_warehouse:
            frappe.throw(
                _("Row {0}: <b>Target Warehouse</b> is required "
                  "for item <b>{1}</b>.").format(row.idx, row.item)
            )

        # ── Check if item is serial/batch tracked ─────────────────────
        has_serial = frappe.db.get_value("Item", row.item, "has_serial_no")
        has_batch  = frappe.db.get_value("Item", row.item, "has_batch_no")

        if has_serial and not row.get("serial_no"):
            frappe.throw(
                _("Row {0}: <b>Serial No</b> is required for item "
                  "<b>{1}</b> (item is serial-tracked). "
                  "Please fill it in the item table before submitting.").format(
                    row.idx, row.item
                )
            )
        if has_batch and not row.get("batch_no"):
            frappe.throw(
                _("Row {0}: <b>Batch No</b> is required for item "
                  "<b>{1}</b> (item is batch-tracked). "
                  "Please fill it in the item table before submitting.").format(
                    row.idx, row.item
                )
            )

def _throw_se_error(se_name, purpose, raw_error):
    """User-friendly error after SE submit failure."""
    clean_error = raw_error.replace("<br>", "\n").split("\n")[0].strip()
    frappe.throw(
        _(
            "Stock Entry {se} was saved as <b>Draft</b> — "
            "automatic submission failed.<br><br>"
            "<b>Reason:</b> {err}<br><br>"
            "<b>What to do next:</b><br>"
            "1. Fix the issue on this Gate Pass Outward "
            "(e.g., fill in <b>Serial / Batch No.</b> in the item table, "
            "correct warehouses, etc.).<br>"
            "2. Re-submit — the existing draft Stock Entry "
            "<b>{se}</b> will be updated automatically, not duplicated."
        ).format(se=se_name, err=clean_error),
        title=_("Stock Entry Draft Saved — Action Required")
    )