import frappe
import json

from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import today, now, flt
from erpnext.controllers.accounts_controller import get_payment_terms, update_child_qty_rate


class PurchaseOrderModificationRequest(Document):

    def autoname(self):
        if self.purchase_order_no:
            self.name = make_autoname(f"{self.purchase_order_no}-.##")

    def validate(self):
        self.validate_purchase_order()
        self.validate_qty_and_rev_qty()
        self._create_order_change_history()
        self.create_history_records()

    def on_submit(self):
        if self.modification_type == "Order Change":
            self.update_purchase_order_commercial_details()
            
            

        if self.purchase_order_no and self.modification_type == "Order Item Change":
            self.update_purchase_order_values()
            

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
            if row.is_delete:
                continue

            qty     = flt(row.qty)
            rev_qty = flt(row.rev_qty)

            if qty == 0 and rev_qty == 0:
                frappe.throw(
                    _("Row {0}: Rev Qty cannot be 0 when Qty is also 0.").format(row.idx),
                    title=_("Invalid Quantity"),
                )

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

    def _create_order_change_history(self):
        """
        Only snapshot fields where the user actually made a change.
        If rev_* is empty or same as original — skip it entirely.
        History fields are only set for genuinely changed fields.
        """

        ORDER_CHANGE_FIELD_MAP = [
            # (original_field, rev_field, history_orig_field, history_rev_field)
            ("incoterm",               "rev_incoterm",               "history_incoterm",               "history_rev_incoterm"),
            ("payment_terms_template", "rev_payment_terms_template", "history_payment_terms_template", "history_rev_payment_terms_template"),
            ("terms",                  "rev_terms",                  "history_terms",                  "history_rev_terms"),
            ("insurance",              "rev_insurance",              "history_insurance",              "history_rev_insurance"),
            ("mode_of_dispatch",       "rev_mode_of_dispatch",       "history_mode_of_dispatch",       "history_rev_mode_of_dispatch"),
            ("freight_charges",        "rev_freight_charges",        "history_freight_charges",        "history_rev_freight_charges"),
            ("po_remarks",             "rev_po_remarks",             "history_po_remarks",             "history_rev_po_remarks"),
            ("group_same_items",       "rev_group_same_items",       "history_group_same_items",       "history_rev_group_same_items")
        ]

        # Clear all history fields first
        for _, _, hist_orig_field, hist_rev_field in ORDER_CHANGE_FIELD_MAP:
            self.set(hist_orig_field, None)
            self.set(hist_rev_field,  None)

        for orig_field, rev_field, hist_orig_field, hist_rev_field in ORDER_CHANGE_FIELD_MAP:
            rev_value  = self.get(rev_field)
            orig_value = self.get(orig_field)

            # Skip if user left rev field empty
            if rev_value is None or rev_value == "":
                continue

            # Skip if user typed the same value as original (no real change)
            if str(rev_value) == str(orig_value if orig_value is not None else ""):
                continue

            # Genuine change — snapshot both sides into history
            self.set(hist_orig_field, orig_value)
            self.set(hist_rev_field,  rev_value)

    # def update_purchase_order_commercial_details(self):
    #     """Update only the changed Order Change fields back onto the Purchase Order"""

    #     ORDER_CHANGE_MAP = [
    #         # (pmr_rev_field, po_field)
    #         ("rev_incoterm",               "incoterm"),
    #         ("rev_payment_terms_template", "payment_terms_template"),
    #         ("rev_terms",                  "tc_name"),
    #         ("rev_insurance",              "custom_insurance"),
    #         ("rev_mode_of_dispatch",       "custom_mode_of_dispatch"),
    #         ("rev_freight_charges",        "freight_charges"),
    #         ("rev_po_remarks",             "po_remarks"),
    #         ("rev_group_same_items",       "group_same_items"),
    #     ]

    #     updates = []
    #     params  = {"po_name": self.purchase_order_no}

    #     for pmr_field, po_field in ORDER_CHANGE_MAP:
    #         val = self.get(pmr_field)
    #         if val is not None and val != "":
    #             orig_val = self.get(pmr_field.replace("rev_", ""))
    #             # Only update if the value actually changed
    #             if str(val) != str(orig_val if orig_val is not None else ""):
    #                 updates.append(f"`{po_field}` = %({pmr_field})s")
    #                 params[pmr_field] = val

    #     if updates:
    #         frappe.db.sql(f"""
    #             UPDATE `tabPurchase Order`
    #             SET {", ".join(updates)}
    #             WHERE name = %(po_name)s
    #         """, params)

    #         frappe.db.set_value(
    #             "Purchase Order",
    #             self.purchase_order_no,
    #             "modified",
    #             frappe.utils.now(),
    #             update_modified=False,
    #         )
    #         frappe.db.commit()

    

    def update_purchase_order_commercial_details(self):
        """Update only the changed Order Change fields back onto the Purchase Order"""

        ORDER_CHANGE_MAP = [
            # (pmr_rev_field, po_field)
            ("rev_incoterm",               "incoterm"),
            ("rev_payment_terms_template", "payment_terms_template"),
            ("rev_terms",                  "tc_name"),
            ("rev_insurance",              "custom_insurance"),
            ("rev_mode_of_dispatch",       "custom_mode_of_dispatch"),
            ("rev_freight_charges",        "freight_charges"),
            ("rev_po_remarks",             "po_remarks"),
            ("rev_group_same_items",       "group_same_items"),
        ]

        updates = []
        params  = {"po_name": self.purchase_order_no}
        payment_terms_changed = False

        for pmr_field, po_field in ORDER_CHANGE_MAP:
            val = self.get(pmr_field)
            if val is not None and val != "":
                orig_val = self.get(pmr_field.replace("rev_", ""))
                # Only update if the value actually changed
                if str(val) != str(orig_val if orig_val is not None else ""):
                    updates.append(f"`{po_field}` = %({pmr_field})s")
                    params[pmr_field] = val

                    if pmr_field == "rev_payment_terms_template":
                        payment_terms_changed = True

        if updates:
            frappe.db.sql(f"""
                UPDATE `tabPurchase Order`
                SET {", ".join(updates)}
                WHERE name = %(po_name)s
            """, params)

            frappe.db.set_value(
                "Purchase Order",
                self.purchase_order_no,
                "modified",
                frappe.utils.now(),
                update_modified=False,
            )
            frappe.db.commit()

        # ── Payment Schedule Sync ──────────────────────────────────────────────
        if payment_terms_changed:
            self._sync_payment_schedule_to_po()


    def _sync_payment_schedule_to_po(self):
        """
        Mirrors the JS payment_terms_template() logic:
        calls get_payment_terms and rewrites the PO's payment_schedule child table.
        """
        po = frappe.get_doc("Purchase Order", self.purchase_order_no)

        new_terms_template = self.rev_payment_terms_template
        posting_date = po.get("transaction_date") or po.get("posting_date")

        grand_total      = po.get("rounded_total") or po.get("grand_total")
        base_grand_total = po.get("base_rounded_total") or po.get("base_grand_total")
        bill_date        = po.get("bill_date")

        # Fetch the new schedule — same server call the JS front-end makes
        new_schedule = get_payment_terms(
            terms_template   = new_terms_template,
            posting_date     = posting_date,
            grand_total      = grand_total,
            base_grand_total = base_grand_total,
            bill_date        = bill_date,
        )

        if not new_schedule:
            return

        # Delete the existing child rows from the DB
        frappe.db.delete("Payment Schedule", {"parent": po.name, "parenttype": "Purchase Order"})

        # Insert the fresh rows
        for idx, term in enumerate(new_schedule, start=1):
            row = frappe.new_doc("Payment Schedule")
            row.update(term)
            row.update({
                "parent":      po.name,
                "parenttype":  "Purchase Order",
                "parentfield": "payment_schedule",
                "idx":         idx,
            })
            row.db_insert()

        # Bump the PO's modified timestamp so the UI knows to reload
        frappe.db.set_value(
            "Purchase Order",
            po.name,
            "modified",
            frappe.utils.now(),
            update_modified=False,
        )
        frappe.db.commit()


    def update_purchase_order_values(self):
        _now  = now()
        _user = frappe.session.user

        CUSTOM_FIELD_MAP = [
            ("rev_required_by",             "schedule_date"),
            ("rev_expected_delivery_date",  "expected_delivery_date"),
            ("rev_remarks",                 "remarks"),
            ("rev_stock_qty",               "stock_qty"),
            ("rev_conversion_factor",       "conversion_factor"),
            ("rev_price_list_rate",         "price_list_rate"),
            ("rev_target_warehouse", "warehouse"),
            ("rev_item_tax_template",       "item_tax_template"),
        ]
        ALLOW_FALSY_FIELDS = set()

        delta_map = self._compute_delta_and_update_mrs(_now, _user)

        for row in self.items:
            if not row.is_delete:
                continue

            po_item_to_delete = row.purchase_order_item_name

            if not po_item_to_delete:
                filters = {
                    "parent":     self.purchase_order_no,
                    "parenttype": "Purchase Order",
                    "item_code":  row.item,
                }
                if row.po_line_no:
                    filters["po_line_no"] = row.po_line_no

                po_item_to_delete = frappe.db.get_value(
                    "Purchase Order Item",
                    filters,
                    "name",
                    order_by="idx asc",
                )

            if not po_item_to_delete:
                frappe.log_error(
                    title="PMR - is_delete: PO item not found, skipping",
                    message=(
                        f"pmr={self.name}, row.idx={row.idx}, "
                        f"item={row.item}, po_line_no={row.po_line_no}, "
                        f"purchase_order_item_name='{row.purchase_order_item_name}'"
                    ),
                )
                continue

            self._clear_mr_link_on_po_item_delete_by_name(po_item_to_delete, row)
            frappe.db.delete("Purchase Order Item", po_item_to_delete)
            frappe.logger().info(
                f"PMR {self.name} | Deleted PO Item {po_item_to_delete} "
                f"(item={row.item}, row.idx={row.idx})"
            )

        po_items_ordered = frappe.get_all(
            "Purchase Order Item",
            filters={"parent": self.purchase_order_no, "parenttype": "Purchase Order"},
            fields=["name"],
            order_by="idx asc",
        )
        for i, d in enumerate(po_items_ordered, start=1):
            frappe.db.set_value("Purchase Order Item", d.name, "idx", i, update_modified=False)

        branch = self._get_branch_for_new_item()
        trans_items = []

        for row in self.items:
            if row.is_delete:
                continue

            rev_qty  = flt(row.rev_qty)  if (row.rev_qty  and row.rev_qty  > 0) else flt(row.qty)
            rev_rate = flt(row.rev_rate) if (row.rev_rate and row.rev_rate > 0) else flt(row.rate)

            if row.purchase_order_item_name:
                if row.name in delta_map:
                    original_po_qty = delta_map[row.name]["original_po_qty"]
                    trans_items.append({
                        "docname":   row.purchase_order_item_name,
                        "item_code": row.item,
                        "qty":       original_po_qty,
                        "rate":      rev_rate,
                    })
                    trans_items.append({
                        "__islocal": True,
                        "item_code": delta_map[row.name]["item_code"],
                        "qty":       delta_map[row.name]["delta_qty"],
                        "rate":      rev_rate,
                        "branch":    branch,
                    })
                else:
                    trans_items.append({
                        "docname":   row.purchase_order_item_name,
                        "item_code": row.item,
                        "qty":       rev_qty,
                        "rate":      rev_rate,
                    })
            else:
                rev_item = getattr(row, "rev_item", None)
                if not rev_item:
                    continue

                trans_items.append({
                    "__islocal": True,
                    "item_code": rev_item,
                    "qty":       rev_qty,
                    "rate":      rev_rate,
                    "branch":    branch,
                })

        po_items_before = self._snapshot_po_item_names()

        po = frappe.get_doc("Purchase Order", self.purchase_order_no)
        po.save(ignore_permissions=True)

        if trans_items:
            update_child_qty_rate(
                "Purchase Order",
                json.dumps(trans_items),
                self.purchase_order_no,
            )

        if delta_map or any(not row.purchase_order_item_name for row in self.items if not row.is_delete):
            self._ensure_branch_on_new_po_items(po_items_before, branch, _now, _user)

        if delta_map:
            self._link_new_po_lines_to_mrs(delta_map, po_items_before, _now, _user)

        for row in self.items:
            if row.is_delete:
                continue

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
                    if rev_value is not None and rev_value != "" and rev_value != 0:
                        update_fields[po_field] = rev_value

            if update_fields:
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

           
            
            # ── Line Status (mirrors OMR CLEARABLE_FIELDS logic) ────────────────────
            rev_line_status = getattr(row, "rev_line_status", None)

            if rev_line_status is not None and rev_line_status != "":
                if rev_line_status == "Live":
                    # "Live" means clear the field on PO item
                    so_line_status_value = ""
                else:
                    # "Cancelled" or any other value → write it
                    so_line_status_value = rev_line_status

                frappe.db.sql(
                    """
                    UPDATE `tabPurchase Order Item`
                    SET
                        `line_status` = %s,
                        `modified`           = %s,
                        `modified_by`        = %s
                    WHERE
                        `name`   = %s
                        AND `parent` = %s
                    """,
                    (so_line_status_value, _now, _user, po_item_name, self.purchase_order_no),
                )
           

        self._apply_item_replacements(_now, _user)
        self.update_order_qty()
        frappe.db.commit()

    def _clear_mr_link_on_po_item_delete_by_name(self, po_item_name, row):
        po_item_data = frappe.db.get_value(
            "Purchase Order Item",
            po_item_name,
            ["material_request", "material_request_item", "qty"],
            as_dict=True,
        )
        if not po_item_data:
            return

        if po_item_data.material_request_item:
            frappe.db.set_value(
                "Material Request Item",
                po_item_data.material_request_item,
                "ordered_qty",
                0,
                update_modified=False,
            )
            frappe.logger().info(
                f"PMR {self.name} | Cleared ordered_qty on MR Item "
                f"{po_item_data.material_request_item} due to PO item delete "
                f"(item={row.item}, qty={po_item_data.qty})"
            )

    def _clear_mr_link_on_po_item_delete(self, row):
        if not row.purchase_order_item_name:
            return
        self._clear_mr_link_on_po_item_delete_by_name(row.purchase_order_item_name, row)

    def _ensure_branch_on_new_po_items(self, po_items_before, branch, _now, _user):
        if not branch:
            return

        all_po_items = frappe.db.get_all(
            "Purchase Order Item",
            filters={
                "parent":     self.purchase_order_no,
                "parenttype": "Purchase Order",
            },
            fields=["name", "branch"]
        )

        for item in all_po_items:
            if item.name not in po_items_before or not item.branch:
                frappe.db.sql(
                    """
                    UPDATE `tabPurchase Order Item`
                    SET
                        `branch`      = %s,
                        `modified`    = %s,
                        `modified_by` = %s
                    WHERE `name` = %s
                    """,
                    (branch, _now, _user, item.name)
                )

    def _get_branch_for_new_item(self):
        branch = frappe.db.get_value("Purchase Order", self.purchase_order_no, "branch")

        if not branch:
            branch = frappe.db.get_value(
                "Purchase Order Item",
                {"parent": self.purchase_order_no},
                "branch",
                order_by="idx asc"
            )

        if not branch:
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

    def _compute_delta_and_update_mrs(self, _now, _user):
        delta_map = {}
        next_idx  = max((r.idx for r in self.items), default=0)

        for row in self.items:
            if row.is_delete:
                continue

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

            mr_name      = None
            mr_item_name = None

            if po_item_data.material_request:
                new_mr_item_name = frappe.generate_hash(length=10)

                last_idx = frappe.db.sql(
                    """
                    SELECT MAX(idx)
                    FROM `tabMaterial Request Item`
                    WHERE parent = %s
                    """,
                    po_item_data.material_request
                )[0][0] or 0

                new_idx = last_idx + 1

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

                mr_name      = po_item_data.material_request
                mr_item_name = new_mr_item_name

            if mr_name and mr_item_name:
                delta_map[row.name] = {
                    "mr_name":         mr_name,
                    "mr_item_name":    mr_item_name,
                    "delta_qty":       delta,
                    "item_code":       item_code,
                    "original_po_qty": original_po_qty,
                }

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

        return delta_map

    def _snapshot_po_item_names(self):
        rows = frappe.db.sql(
            """
            SELECT name
            FROM `tabPurchase Order Item`
            WHERE parent = %s AND parenttype = 'Purchase Order'
            """,
            (self.purchase_order_no,),
        )
        return {r[0] for r in rows}

    def _link_new_po_lines_to_mrs(self, delta_map, po_items_before, _now, _user):
        all_po_items = frappe.db.get_all(
            "Purchase Order Item",
            filters={
                "parent":     self.purchase_order_no,
                "parenttype": "Purchase Order",
            },
            fields=["name", "item_code", "qty"],
        )

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

    def _apply_item_replacements(self, _now, _user):
        errors = []

        for row in self.items:
            if row.is_delete:
                continue

            rev_item = getattr(row, "rev_item", None)
            if not rev_item:
                continue

            po_item_name = self._find_po_item_name(row)
            if not po_item_name:
                continue

            current_item_code = frappe.db.get_value(
                "Purchase Order Item", po_item_name, "item_code"
            )
            if current_item_code == rev_item:
                continue

            item_data = frappe.db.get_value(
                "Item",
                rev_item,
                ["item_name", "description"],
                as_dict=True,
            )
            if not item_data:
                errors.append(f"Row {row.idx}: Item '{rev_item}' not found in Item master.")
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
                    message=f"pmr={self.name}, row={row.idx}, po_item={po_item_name}, rev_item={rev_item}\n{e}",
                )

        if errors:
            frappe.log_error(
                title="PMR - item replacement had errors",
                message=f"pmr={self.name}, errors={errors}",
            )

    def _find_po_item_name(self, row):
        if row.purchase_order_item_name:
            return row.purchase_order_item_name

        is_new_item = bool(not row.item and getattr(row, "rev_item", None))
        lookup_item = row.rev_item if is_new_item else row.item

        if not lookup_item:
            frappe.log_error(
                title="PMR - cannot resolve item for PO lookup",
                message=f"Both row.item and row.rev_item are empty. pmr={self.name}, row={row.idx}",
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
                message=f"item={lookup_item}, is_new={is_new_item}, po_line_no={row.po_line_no}, pmr={self.name}",
            )

        return po_item_name

    def create_history_records(self):
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

            if old_row.item != current_row.rev_item:
                old_data["new_item"] = current_row.rev_item
                changed = True

            if flt(old_row.qty) != flt(current_row.rev_qty) and flt(current_row.rev_qty) > 0:
                old_data["rev_qty"] = current_row.rev_qty
                changed = True

            if flt(old_row.rate) != flt(current_row.rev_rate) and flt(current_row.rev_rate) > 0:
                old_data["rev_rate"] = current_row.rev_rate
                changed = True

            if old_row.required_by != current_row.rev_required_by and current_row.rev_required_by:
                old_data["rev_required_by"] = current_row.rev_required_by
                changed = True
            if old_row.rev_line_status != current_row.rev_line_status and current_row.rev_line_status:
                old_data["rev_line_status"] = current_row.rev_line_status
                changed = True

            if old_row.expected_delivery_date != current_row.rev_expected_delivery_date and current_row.rev_expected_delivery_date:
                old_data["rev_expected_delivery_date"] = current_row.rev_expected_delivery_date
                changed = True

            if old_row.remarks != current_row.rev_remarks and current_row.rev_remarks:
                old_data["rev_remarks"] = current_row.rev_remarks
                changed = True

            if flt(old_row.stock_qty) != flt(current_row.rev_stock_qty) and flt(current_row.rev_stock_qty) > 0:
                old_data["rev_stock_qty"] = current_row.rev_stock_qty
                changed = True

            if flt(old_row.conversion_factor) != flt(current_row.rev_conversion_factor) and flt(current_row.rev_conversion_factor) > 0:
                old_data["rev_conversion_factor"] = current_row.rev_conversion_factor
                changed = True

            if flt(old_row.price_list_rate) != flt(current_row.rev_price_list_rate) and flt(current_row.rev_price_list_rate) > 0:
                old_data["rev_price_list_rate"] = current_row.rev_price_list_rate
                changed = True

            if old_row.target_warehouse != current_row.rev_target_warehouse and current_row.rev_target_warehouse:
                old_data["rev_target_warehouse"] = current_row.rev_target_warehouse
                changed = True

            if old_row.item_tax_template != current_row.rev_item_tax_template and current_row.rev_item_tax_template:
                old_data["rev_item_tax_template"] = current_row.rev_item_tax_template
                changed = True

            if current_row.is_delete:
                old_data["is_delete"] = 1
                changed = True

            if changed:
                rows_to_keep.append(old_data)

        self.set("original_record", [])
        for row in rows_to_keep:
            self.append("original_record", row)


        