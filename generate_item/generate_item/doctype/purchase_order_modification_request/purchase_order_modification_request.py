# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
import json

from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import today, now, flt
from erpnext.controllers.accounts_controller import update_child_qty_rate


class PurchaseOrderModificationRequest(Document):

    # ──────────────────────────────────────────────────────────────────────────
    # Naming
    # ──────────────────────────────────────────────────────────────────────────

    def autoname(self):
        if self.purchase_order_no:
            self.name = make_autoname(f"{self.purchase_order_no}-.##")

    # ──────────────────────────────────────────────────────────────────────────
    # Lifecycle hooks
    # ──────────────────────────────────────────────────────────────────────────

    def validate(self):
        self.validate_purchase_order()
        self.validate_qty_and_rev_qty()

    def on_submit(self):
        if self.purchase_order_no and self.modification_type == "Order Item Change":
            self.update_purchase_order_values()
            self.create_history_records()

    # ──────────────────────────────────────────────────────────────────────────
    # Validation helpers
    # ──────────────────────────────────────────────────────────────────────────

    def validate_purchase_order(self):
        if not self.purchase_order_no:
            return

        po = frappe.get_doc("Purchase Order", self.purchase_order_no)

        if po.status == "Cancelled":
            frappe.throw(
                _(
                    "Purchase Order {0} is cancelled. "
                    "You cannot use a cancelled Purchase Order."
                ).format(po.name)
            )

        if po.status == "Completed":
            frappe.throw(
                _(
                    "Purchase Order {0} is already completed. "
                    "You cannot proceed with a completed Purchase Order."
                ).format(po.name)
            )

    def validate_qty_and_rev_qty(self):
        for row in self.items or []:
            qty     = flt(row.qty)
            rev_qty = flt(row.rev_qty)

            if qty == 0 and rev_qty == 0:
                frappe.throw(
                    _("Row {0}: Rev Qty cannot be 0 when Qty is also 0.").format(row.idx),
                    title=_("Invalid Quantity"),
                )

    # ──────────────────────────────────────────────────────────────────────────
    # Revision stamp
    # ──────────────────────────────────────────────────────────────────────────

    def update_purchase_order_revision(self):
        if not self.purchase_order_no:
            return

        frappe.db.sql("""
            UPDATE `tabPurchase Order`
            SET
                latest_rev_no = %s,
                rev_date      = %s,
                modified      = %s,
                modified_by   = %s
            WHERE name = %s
        """, (self.name, today(), now(), frappe.session.user, self.purchase_order_no))

    # ──────────────────────────────────────────────────────────────────────────
    # Core item-change update
    # ──────────────────────────────────────────────────────────────────────────
    def update_purchase_order_values(self):
        """
        Full execution order:

        Step 0 — _compute_delta_and_update_mrs
                • For every PMR row where rev_qty > original PO qty:
                    - Compute delta = rev_qty - original_po_qty
                    - Add new row to existing MR for delta qty using SQL INSERT
                    - Insert a delta audit row into this PMR's items table
                • Returns delta_map keyed by PMR row name

        Step 1 — Build trans_items list:
                • Rows WITH delta  → original PO qty unchanged + __islocal delta line
                • Rows WITHOUT delta → normal qty/rate update
                • User-added new lines (no purchase_order_item_name) → __islocal

        Step 2 — Snapshot existing PO item names (before update_child_qty_rate)

        Step 3 — po.save() + update_child_qty_rate
                (adds new PO lines for each __islocal delta entry)

        Step 4 — _link_new_po_lines_to_mrs
                • Diff snapshot → find brand-new PO item rows
                • Match by (item_code, qty) → link material_request / material_request_item

        Step 5 — Custom / line fields via direct SQL
                (schedule_date, po_line_no, is_free_item, branch)

        Step 6 — _apply_item_replacements
                (item_code / item_name / description where rev_item differs)

        Step 7 — frappe.db.commit()
        """
        _now  = now()
        _user = frappe.session.user

        CUSTOM_FIELD_MAP = [
            ("rev_required_by",  "schedule_date"),
            ("rev_po_line_no",   "po_line_no"),
            ("rev_is_free_item", "is_free_item"),
        ]
        ALLOW_FALSY_FIELDS = {"rev_is_free_item"}

        # ── Step 0 ─────────────────────────────────────────────────────────────
        delta_map = self._compute_delta_and_update_mrs(_now, _user)

        # ── Step 1 ─────────────────────────────────────────────────────────────
        # Get the branch to use for new items
        branch = self._get_branch_for_new_item()
        
        trans_items = []
        
        for row in self.items:
            rev_qty  = flt(row.rev_qty)  if (row.rev_qty  and row.rev_qty  > 0) else flt(row.qty)
            rev_rate = flt(row.rev_rate) if (row.rev_rate and row.rev_rate > 0) else flt(row.rate)

            if row.purchase_order_item_name:
                if row.name in delta_map:
                    # Qty increased — keep original PO qty on the existing line.
                    # The delta is added as a brand-new PO line via __islocal.
                    original_po_qty = delta_map[row.name]["original_po_qty"]
                    
                    trans_items.append({
                        "docname":   row.purchase_order_item_name,
                        "item_code": row.item,
                        "qty":       original_po_qty,   # intentionally unchanged
                        "rate":      rev_rate,
                    })
                    trans_items.append({
                        "__islocal": True,
                        "item_code": delta_map[row.name]["item_code"],
                        "qty":       delta_map[row.name]["delta_qty"],
                        "rate":      rev_rate,
                        "branch":    branch,  # Set branch from PMR
                    })
                else:
                    # Normal update: qty decrease, rate-only change, or no MR link
                    trans_items.append({
                        "docname":   row.purchase_order_item_name,
                        "item_code": row.item,
                        "qty":       rev_qty,
                        "rate":      rev_rate,
                    })
            else:
                # Genuinely new line added by the user in the PMR form
                rev_item = getattr(row, "rev_item", None)
                if not rev_item:
                    continue
                
                trans_items.append({
                    "__islocal": True,
                    "item_code": rev_item,
                    "qty":       rev_qty,
                    "rate":      rev_rate,
                    "branch":    branch,  # Set branch from PMR
                })

        # ── Step 2 ─────────────────────────────────────────────────────────────
        po_items_before = self._snapshot_po_item_names()

        # ── Step 3 ─────────────────────────────────────────────────────────────
        po = frappe.get_doc("Purchase Order", self.purchase_order_no)
        po.save(ignore_permissions=True)

        if trans_items:
            update_child_qty_rate(
                "Purchase Order",
                json.dumps(trans_items),
                self.purchase_order_no,
            )

        # ── Step 4: After update_child_qty_rate, ensure branch is set on all new PO items ──
        if delta_map or any(not row.purchase_order_item_name for row in self.items):
            self._ensure_branch_on_new_po_items(po_items_before, branch, _now, _user)

        # ── Step 5 ─────────────────────────────────────────────────────────────
        if delta_map:
            self._link_new_po_lines_to_mrs(delta_map, po_items_before, _now, _user)

        # ── Step 6 ─────────────────────────────────────────────────────────────
        for row in self.items:
            po_item_name = self._find_po_item_name(row)
            if not po_item_name:
                continue

            update_fields = {}

            for pmr_field, po_field in CUSTOM_FIELD_MAP:
                sentinel  = object()
                rev_value = getattr(row, pmr_field, sentinel)

                if rev_value is sentinel:
                    continue

                if pmr_field in ALLOW_FALSY_FIELDS:
                    update_fields[po_field] = rev_value
                else:
                    if rev_value is not None and rev_value != "":
                        if po_field == "po_line_no":
                            try:
                                update_fields[po_field] = int(rev_value)
                            except (ValueError, TypeError):
                                frappe.log_error(
                                    title="Invalid PO Line No - Skipped",
                                    message=f"Row {row.idx}: Rev PO Line No '{rev_value}' is not a valid integer and was not saved. Please enter a plain number.",
                                )
                              
                            continue
                        update_fields[po_field] = rev_value

            if not update_fields:
                continue

            set_clause = ", ".join([f"`{f}` = %({f})s" for f in update_fields])
            frappe.db.sql(
                f"""
                UPDATE `tabPurchase Order Item`
                SET
                    {set_clause},
                    `modified`    = %(modified)s,
                    `modified_by` = %(modified_by)s
                WHERE
                    `name`   = %(name)s
                    AND `parent` = %(parent)s
                """,
                {
                    **update_fields,
                    "name":        po_item_name,
                    "parent":      self.purchase_order_no,
                    "modified":    _now,
                    "modified_by": _user,
                },
            )

        # ── Step 7 ─────────────────────────────────────────────────────────────
        self._apply_item_replacements(_now, _user)

        # update  mr item's ordered qty 
        self.update_order_qty()

        # ── Step 8 ─────────────────────────────────────────────────────────────
        frappe.db.commit()

    def _ensure_branch_on_new_po_items(self, po_items_before, branch, _now, _user):
        """
        After update_child_qty_rate creates new PO items, ensure branch is set.
        This handles cases where update_child_qty_rate doesn't pass branch correctly.
        """
        if not branch:
            return
        
        # Get all current PO items
        all_po_items = frappe.db.get_all(
            "Purchase Order Item",
            filters={
                "parent": self.purchase_order_no,
                "parenttype": "Purchase Order",
            },
            fields=["name", "branch"]
        )
        
        # Find new items and items without branch
        for item in all_po_items:
            if item.name not in po_items_before or not item.branch:
                frappe.db.sql(
                    """
                    UPDATE `tabPurchase Order Item`
                    SET 
                        `branch` = %s,
                        `modified` = %s,
                        `modified_by` = %s
                    WHERE `name` = %s
                    """,
                    (branch, _now, _user, item.name)
                )
                frappe.logger().info(
                    f"PMR {self.name} | Set branch={branch} on PO Item {item.name}"
                )
    def _get_branch_for_new_item(self):
        """
        Get branch for new items being added to PO.
        Priority: PO's branch > First PO item's branch > PMR's branch
        """
        # Try to get branch from the Purchase Order
        branch = frappe.db.get_value("Purchase Order", self.purchase_order_no, "branch")
        
        if not branch:
            # Try to get branch from any existing PO item
            branch = frappe.db.get_value(
                "Purchase Order Item",
                {"parent": self.purchase_order_no},
                "branch",
                order_by="idx asc"
            )
        
        if not branch:
            # Use PMR's branch as last resort
            branch = self.branch
        
        return branch

    # ──────────────────────────────────────────────────────────────────────────
    # Delta computation + MR update
    # ──────────────────────────────────────────────────────────────────────────

    def _get_branch_for_new_item(self):
        """
        Get branch for new items being added to PO.
        Priority: PO's branch > First PO item's branch > PMR's branch
        """
        # Try to get branch from the Purchase Order
        branch = frappe.db.get_value("Purchase Order", self.purchase_order_no, "branch")
        
        if not branch:
            # Try to get branch from any existing PO item
            branch = frappe.db.get_value(
                "Purchase Order Item",
                {"parent": self.purchase_order_no},
                "branch",
                order_by="idx asc"
            )
        
        if not branch:
            # Use PMR's branch as last resort
            branch = self.branch
        
        return branch

    def update_order_qty(self):
        po_doc = frappe.get_doc("Purchase Order", self.purchase_order_no)

        for po_item in po_doc.items:
            if not po_item.material_request_item:
                continue

            frappe.db.set_value(
                "Material Request Item",
                po_item.material_request_item,
                "ordered_qty",
                po_item.qty,
                update_modified=False
            )
            frappe.log_error("update order qty in mr  ",f"{po_item.material_request_item} - {po_item.qty}")

    


    def _compute_delta_and_update_mrs(self, _now, _user):
        """
        Iterates over PMR rows that have an existing PO item reference.
        When rev_qty > original PO qty:
        1. delta = rev_qty - original_po_qty
        2. Add new row to existing MR for delta qty using SQL INSERT
        3. Insert a delta child row into this PMR (audit / visibility in the form)

        Returns delta_map:
            {
                pmr_row_name: {
                    "mr_name":         str,
                    "mr_item_name":    str,
                    "delta_qty":       float,
                    "item_code":       str,
                    "original_po_qty": float,
                }
            }
        """
        delta_map  = {}
        # next_idx used to assign sequential idx to new child rows
        next_idx = max((r.idx for r in self.items), default=0)

        for row in self.items:
            # Only process rows that reference an existing PO item
            if not row.purchase_order_item_name:
                continue

            po_item_data = frappe.db.get_value(
                "Purchase Order Item",
                row.purchase_order_item_name,
                ["qty", "uom", "warehouse", "schedule_date", "material_request", "material_request_item"],
                as_dict=True,
            )
            if not po_item_data:
                continue

            original_po_qty = flt(po_item_data.qty)
            rev_qty = (
                flt(row.rev_qty)
                if (row.rev_qty and row.rev_qty > 0)
                else flt(row.qty)
            )
            delta = rev_qty - original_po_qty

            # Only act when qty is genuinely increasing
            if delta <= 0:
                continue

            item_code     = getattr(row, "rev_item", None) or row.item
            schedule_date = (
                getattr(row, "rev_required_by", None)
                or po_item_data.schedule_date
                or today()
            )
            rate = (
                flt(row.rev_rate)
                if (row.rev_rate and row.rev_rate > 0)
                else flt(row.rate)
            )

            # ── Add new row to existing MR for delta qty ───────────────────────────
            mr_name = None
            mr_item_name = None
            
            if po_item_data.material_request:
                # Generate a unique name for the new MR item
                new_mr_item_name = frappe.generate_hash(length=10)
                
                # Get the next idx for the MR items
                last_idx = frappe.db.sql(
                    """
                    SELECT MAX(idx) 
                    FROM `tabMaterial Request Item`
                    WHERE parent = %s
                    """,
                    po_item_data.material_request
                )[0][0] or 0
                
                new_idx = last_idx + 1
                
                # Insert new row in MR items for delta qty
                frappe.db.sql(
                    """
                    INSERT INTO `tabMaterial Request Item`
                        (name, owner, creation, modified, modified_by,
                        parent, parentfield, parenttype, idx,
                        item_code, item_name, description,
                        qty, stock_qty, uom, conversion_factor,
                        schedule_date, warehouse,
                        docstatus)
                    SELECT
                        %s, %s, %s, %s, %s,
                        %s, 'items', 'Material Request', %s,
                        %s, item_name, description,
                        %s, %s, %s, 1,
                        %s, %s,
                        docstatus
                    FROM `tabItem`
                    WHERE name = %s
                    """,
                    (
                        new_mr_item_name, _user, _now, _now, _user,
                        po_item_data.material_request, new_idx,
                        item_code,
                        delta, delta, po_item_data.uom,
                        schedule_date, po_item_data.warehouse,
                        item_code
                    )
                )
                
                # Update the parent MR's modified timestamp
                # frappe.db.sql(
                #     """
                #     UPDATE `tabMaterial Request`
                #     SET 
                #         `modified` = %s,
                #         `modified_by` = %s
                #     WHERE `name` = %s
                #     """,
                #     (_now, _user, po_item_data.material_request)
                # )
                
                mr_name = po_item_data.material_request
                mr_item_name = new_mr_item_name
                
               
               
            
            if mr_name and mr_item_name:
                delta_map[row.name] = {
                    "mr_name":         mr_name,
                    "mr_item_name":    mr_item_name,
                    "delta_qty":       delta,
                    "item_code":       item_code,
                    "original_po_qty": original_po_qty,
                }

                # ── Insert delta row into PMR items child table (audit trail) ──────
                next_idx += 1
                child_doctype = "Purchase Order Modification Request Detail"

                frappe.db.sql(
                    f"""
                    INSERT INTO `tab{child_doctype}`
                        (name, owner, creation, modified, modified_by,
                        docstatus, idx, parent, parentfield, parenttype,
                        item, rev_qty, rate, rev_rate,
                        purchase_order_item_name)
                    VALUES
                        (%s, %s, %s, %s, %s,
                        1, %s, %s, 'items', 'Purchase Order Modification Request',
                        %s, %s, %s, %s,
                        NULL)
                    """,
                    (
                        frappe.generate_hash(length=10),
                        _user, _now, _now, _user,
                        next_idx,
                        self.name,
                        item_code,
                        delta,
                        rate,
                        rate,
                    ),
                )
            else:
               
                pass

        return delta_map
    # ──────────────────────────────────────────────────────────────────────────
    # PO item snapshot (pre update_child_qty_rate)
    # ──────────────────────────────────────────────────────────────────────────

    def _snapshot_po_item_names(self):
        """
        Returns the set of tabPurchase Order Item names that exist RIGHT NOW
        for this PO, before update_child_qty_rate adds any new lines.
        Used to identify brand-new PO items after the call.
        """
        rows = frappe.db.sql(
            """
            SELECT name
            FROM `tabPurchase Order Item`
            WHERE parent = %s AND parenttype = 'Purchase Order'
            """,
            (self.purchase_order_no,),
        )
        return {r[0] for r in rows}

    # ──────────────────────────────────────────────────────────────────────────
    # Link new PO lines → their delta MRs
    # ──────────────────────────────────────────────────────────────────────────

    def _link_new_po_lines_to_mrs(self, delta_map, po_items_before, _now, _user):
        """
        After update_child_qty_rate has run and new PO items exist in the DB:

        1. Fetch all current PO items.
        2. Diff against snapshot → isolate brand-new rows.
        3. Match each new row to its delta_map entry via (item_code, qty).
        4. Write material_request + material_request_item on the new PO item.

        Matching strategy:
          - Build a dict: (item_code, qty) → [list of new PO item names]
          - Pop one candidate per delta entry (handles multiple rows of same item+qty)
          - Log + warn if no match found (manual linking required)
        """
        all_po_items = frappe.db.get_all(
            "Purchase Order Item",
            filters={
                "parent":     self.purchase_order_no,
                "parenttype": "Purchase Order",
            },
            fields=["name", "item_code", "qty"],
        )

        # Brand-new lines only
        new_po_items = [
            item for item in all_po_items
            if item.name not in po_items_before
        ]

        if not new_po_items:
            frappe.log_error(
                title="PMR - No new PO lines found after update_child_qty_rate",
                message=(
                    f"pmr={self.name}, po={self.purchase_order_no}, "
                    f"delta_map={list(delta_map.keys())}"
                ),
            )
            return

        # (item_code, qty) → [po_item_name, ...]
        new_po_lookup = {}
        for item in new_po_items:
            key = (item.item_code, flt(item.qty))
            new_po_lookup.setdefault(key, []).append(item.name)

        for row_name, di in delta_map.items():
            key        = (di["item_code"], flt(di["delta_qty"]))
            candidates = new_po_lookup.get(key)

            if not candidates:
                frappe.log_error(
                    title="PMR - New PO line not found for MR linking",
                    message=(
                        f"pmr={self.name}, item={di['item_code']}, "
                        f"delta_qty={di['delta_qty']}, MR={di['mr_name']}"
                    ),
                )
               
                continue

            # Pop first candidate — safe for multiple rows of the same item+qty
            po_item_name = candidates.pop(0)

            frappe.db.sql(
                """
                UPDATE `tabPurchase Order Item`
                SET
                    `material_request`      = %s,
                    `material_request_item` = %s,
                    `modified`              = %s,
                    `modified_by`           = %s
                WHERE
                    `name`   = %s
                    AND `parent` = %s
                """,
                (
                    di["mr_name"],
                    di["mr_item_name"],
                    _now,
                    _user,
                    po_item_name,
                    self.purchase_order_no,
                ),
            )

            frappe.logger().info(
                f"PMR {self.name} | linked new PO Item {po_item_name} "
                f"→ MR {di['mr_name']} / MR Item {di['mr_item_name']}"
            )

    # ──────────────────────────────────────────────────────────────────────────
    # Item replacement helper
    # ──────────────────────────────────────────────────────────────────────────

    def _apply_item_replacements(self, _now, _user):
        """
        For every PMR row where rev_item is set and differs from the current
        item_code on the PO item, update item_code / item_name / description
        on tabPurchase Order Item via direct SQL.
        """
        errors = []

        for row in self.items:
            rev_item = getattr(row, "rev_item", None)
            if not rev_item:
                continue

            po_item_name = self._find_po_item_name(row)
            if not po_item_name:
                continue

            # Re-read from DB after update_child_qty_rate has run
            current_item_code = frappe.db.get_value(
                "Purchase Order Item", po_item_name, "item_code"
            )
            if current_item_code == rev_item:
                continue  # already correct — nothing to do

            item_data = frappe.db.get_value(
                "Item",
                rev_item,
                ["item_name", "description"],
                as_dict=True,
            )
            if not item_data:
                errors.append(
                    f"Row {row.idx}: Item '{rev_item}' not found in Item master."
                )
                frappe.log_error(
                    title="PMR - item replacement failed: item not found",
                    message=f"pmr={self.name}, row={row.idx}, rev_item={rev_item}",
                )
                continue

            try:
                frappe.db.sql(
                    """
                    UPDATE `tabPurchase Order Item`
                    SET
                        `item_code`   = %s,
                        `item_name`   = %s,
                        `description` = %s,
                        `modified`    = %s,
                        `modified_by` = %s
                    WHERE
                        `name`   = %s
                        AND `parent` = %s
                    """,
                    (
                        rev_item,
                        item_data.item_name,
                        item_data.description,
                        _now,
                        _user,
                        po_item_name,
                        self.purchase_order_no,
                    ),
                )
            except Exception as e:
                errors.append(f"Row {row.idx}: {e}")
                frappe.log_error(
                    title="PMR - item replacement SQL error",
                    message=(
                        f"pmr={self.name}, row={row.idx}, "
                        f"po_item={po_item_name}, rev_item={rev_item}\n{e}"
                    ),
                )

        if errors:
            frappe.log_error(
                title="PMR - item replacement had errors",
                message=(f"pmr={self.name}, errors={errors}"),
            )
           

    # ──────────────────────────────────────────────────────────────────────────
    # PO item resolver
    # ──────────────────────────────────────────────────────────────────────────

    def _find_po_item_name(self, row):
        if row.purchase_order_item_name:
            return row.purchase_order_item_name

        is_new_item = bool(not row.item and getattr(row, "rev_item", None))
        lookup_item = row.rev_item if is_new_item else row.item

        if not lookup_item:
            frappe.log_error(
                title="PMR - cannot resolve item for PO lookup",
                message=(
                    f"Both row.item and row.rev_item are empty. "
                    f"pmr={self.name}, row={row.idx}"
                ),
            )
            return None

        filters = {
            "parent":     self.purchase_order_no,
            "parenttype": "Purchase Order",
            "item_code":  lookup_item,
        }
        if row.po_line_no:
            filters["po_line_no"] = row.po_line_no

        po_item_name = frappe.db.get_value(
            "Purchase Order Item",
            filters,
            "name",
            order_by="idx desc",
        )

        if not po_item_name:
            frappe.log_error(
                title="PMR - PO item not found for custom field update",
                message=(
                    f"item={lookup_item}, is_new={is_new_item}, "
                    f"po_line_no={row.po_line_no}, pmr={self.name}"
                ),
            )

        return po_item_name

    # ──────────────────────────────────────────────────────────────────────────
    # History / audit trail
    # ──────────────────────────────────────────────────────────────────────────

    def create_history_records(self):
        """
        Compare items with original_record.
        Only keeps rows in original_record where something actually changed
        (item / qty / rate). Clears unchanged rows.
        """
        if not self.items or not self.original_record:
            self.set("original_record", [])
            return

        current_map  = {row.purchase_order_item_name: row for row in self.items}
        rows_to_keep = []

        for old_row in self.original_record:
            current_row = current_map.get(old_row.purchase_order_item_name)
            if not current_row:
                continue

            changed  = False
            old_data = old_row.as_dict()

            # Item changed?
            if old_row.item != current_row.rev_item:
                old_data["new_item"] = current_row.rev_item
                changed = True

            # Qty changed?
            if old_row.rev_qty != current_row.rev_qty:
                old_data["rev_qty"] = current_row.rev_qty
                changed = True

            # Rate changed?
            if old_row.rev_rate != current_row.rev_rate:
                old_data["rev_rate"] = current_row.rev_rate
                changed = True

            if changed:
                rows_to_keep.append(old_data)

        self.set("original_record", [])
        for row in rows_to_keep:
            self.append("original_record", row)