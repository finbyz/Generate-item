
import frappe, json
from frappe.model.document import Document
from erpnext.controllers.accounts_controller import update_child_qty_rate
from frappe.desk.form.linked_with import (
    get_linked_doctypes,
    get_linked_docs,
)
from frappe import _

import frappe
import re

from frappe.utils import today, now, flt
from frappe.model.document import Document
from frappe.model.naming import make_autoname

from frappe.utils import get_url_to_form


from generate_item.generate_item.modification_task_utils.modification_task import create_bom_task_on_omr_submit

class OrderModificationRequest(Document):


    def autoname(self):

        if self.type == "Sales Order":
            self.name = make_autoname(f"{self.sales_order}-.##")

        elif self.type == "BOM":
            self.name = make_autoname(f"{self.bom}-.##")

    def validate(self):
        create_history_records(self)
        _create_commercial_history(self)
        self.validate_sales_order()
        self.validate_qty_and_rev_qty()
        self.validate_free_item_self_association()
    
  

    def on_submit(self):
        if self.type == "BOM" and self.bom:
            self.update_bom_items_using_db_set()

        # if self.type == "Sales Order" and self.sales_order:
        # 	self.update_sales_order_items_using_db_set()

        if self.type == "Sales Order" and self.sales_order:
            if self.modification_type == "Order Change":
                self.update_sales_order_commercial_details()
                # self.update_so_commercial_fields()

            elif self.modification_type == "Order Item Change":
                # create_history_records(self)

                self.validate_component_of_items(throw=True)
                self.validate_free_item_association_not_removed()  
                self.update_sales_order_values()
                self.update_sales_order_revision()
                create_batches_for_omr(self)
                get_change(self)

        create_bom_task_on_omr_submit(self)
        self.update_production_plan_sales_order_modification()


    def validate_component_of_items(self, throw=False):
        if not self.sales_order or not self.sales_order_item:
            return

        # For each main (non-free) row, only ONE item code is "allowed":
        # - if item is being replaced (rev_item set and different) → ONLY rev_item
        #   (the old item code will be gone from the SO after this OMR applies)
        # - otherwise → the existing item code
        allowed_item_codes = set()
        for row in self.sales_order_item:
            is_free_row = bool(row.is_free_item or getattr(row, "rev_is_free_item", 0))
            if is_free_row:
                continue

            is_replacement = bool(row.rev_item and row.rev_item != row.item)
            effective_item = row.rev_item if is_replacement else row.item

            if effective_item:
                allowed_item_codes.add(effective_item)

        invalid_rows = []
        for row in self.sales_order_item:
            component_of = (row.rev_component_of or "").strip()
            if not component_of:
                continue
            if component_of not in allowed_item_codes:
                invalid_rows.append(
                    _("Row {0}: <b>{1}</b>").format(row.idx, frappe.bold(component_of))
                )

        if not invalid_rows:
            return

        message = _(
            """
            The following <b>Revise Component Of</b> items do not exist in the linked Sales Order:<br><br>
            {0}
            <br><br>
            Cannot Approve the OMR for the Sales Order because the item associated with a Free Item that is being removed and will no longer be available in the Sales Order. Please update the Free Item association before proceeding.
            """
        ).format("<br>".join(invalid_rows))

        if throw:
            frappe.throw(message, title=_("Invalid Revise Component Of"))
        else:
            frappe.msgprint(message, title=_("Validation Warning"), indicator="orange")
    
    def validate_free_item_self_association(self):
        """
        Block a Free Item row's Revise Component Of when it self-references:
        1. rev_component_of == component_of  → no actual change
        2. rev_component_of == item          → free item points at its own item code
        3. rev_component_of == rev_item      → free item points at its own revised item code

        Case 1 is resolved using the actual TARGET ROW (rev_main_item_id) against
        the live Sales Order's current association, not just item-code text —
        because multiple main rows can legitimately share the same item code
        (e.g. same item on two different batches/lines). Comparing text alone
        would wrongly block a valid re-association from one such row to another.
        """
        if not self.sales_order_item:
            return

        errors = []

        for row in self.sales_order_item:
            is_free_row = bool(row.is_free_item or getattr(row, "rev_is_free_item", 0))
            if not is_free_row:
                continue

            rev_component_of = (getattr(row, "rev_component_of", None) or "").strip()
            if not rev_component_of:
                continue

            item = (row.item or "").strip()
            rev_item = (getattr(row, "rev_item", None) or "").strip()
            component_of = (row.component_of or "").strip()

            # Case 2 — self-reference to own item code (unambiguous, no row-identity needed)
            if item and rev_component_of == item:
                errors.append(
                    _("Row {0}: Revised Component Of cannot be the Free Item's own item code ({1}).")
                    .format(row.idx, frappe.bold(item))
                )
                continue

            # Case 3 — self-reference to own revised item code
            if rev_item and rev_component_of == rev_item:
                errors.append(
                    _("Row {0}: Revised Component Of cannot be the Free Item's own revised item code ({1}).")
                    .format(row.idx, frappe.bold(rev_item))
                )
                continue

            # Case 1 — "no real change"
            if component_of and rev_component_of == component_of:
                rev_main_item_id = getattr(row, "rev_main_item_id", None)
                truly_unchanged = True

                if rev_main_item_id and row.sales_order_item_name:
                    live_main_item_id = frappe.db.get_value(
                        "Sales Order Item", row.sales_order_item_name, "main_item_id"
                    )
                    if live_main_item_id and rev_main_item_id != live_main_item_id:
                        # Item code text matches, but the TARGET ROW differs —
                        # genuine re-association across duplicate-item rows. Allow it.
                        truly_unchanged = False

                if truly_unchanged:
                    errors.append(
                        _("Row {0}: Revised Component Of is the same as the current Component Of ({1}) — no change is being made.")
                        .format(row.idx, frappe.bold(component_of))
                    )

        if errors:
            frappe.throw("<br>".join(errors), title=_("Invalid Free Item Association"))

    def validate_free_item_association_not_removed(self):
        """
        Spec: 'Associated Item Removed'.
        Blocks the OMR if a Free Item row is still associated with a main
        Sales Order line that this same OMR is cancelling — unless the Free
        Item itself is being cancelled in the same OMR (that combination is
        allowed, since nothing is left dangling).
        """
        if self.type != "Sales Order" or not self.sales_order_item:
            return

        # Map every main (non-free) row to its unique line key.
        # Prefer sales_order_item_name (existing line); fall back to the
        # OMR row's own name for a line newly added in this same OMR.
        line_key_to_row = {}
        for row in self.sales_order_item:
            is_free = bool(row.is_free_item or getattr(row, "rev_is_free_item", 0))
            if is_free:
                continue
            key = row.sales_order_item_name or row.name
            line_key_to_row[key] = row

        blocked = []

        for row in self.sales_order_item:
            is_free = bool(row.is_free_item or getattr(row, "rev_is_free_item", 0))
            if not is_free:
                continue

            # Prefer the unique line reference; fall back to item-code match
            # only if rev_main_item_id was never set (legacy/manual entry).
            # line_key = getattr(row, "rev_main_item_id", None)

            # if not line_key:
            #     # Fallback: match by effective item code (same rule as the
            #     # component-of check) — best-effort only, since item codes
            #     # can repeat across rows.
            #     component_of = (row.rev_component_of or row.component_of or "").strip()
            #     if not component_of:
            #         continue
            #     match = next(
            #         (
            #             r for r in line_key_to_row.values()
            #             if (
            #                 (r.rev_item if (r.rev_item and r.rev_item != r.item) else r.item)
            #                 == component_of
            #             )
            #         ),
            #         None,
            #     )
            #     main_row = match
            # else:
            #     main_row = line_key_to_row.get(line_key)

            line_key = getattr(row, "rev_main_item_id", None)
            main_row = line_key_to_row.get(line_key) if line_key else None

            if not main_row:
                # Fallback: match by effective item code — covers both
                # "rev_main_item_id never set" and "set but stale" (e.g. new
                # main item + new Free Item added together in the same OMR).
                component_of = (
                    getattr(row, "rev_main_item", None)
                    or row.rev_component_of
                    or row.component_of
                    or ""
                ).strip()
                if not component_of:
                    continue
                match = next(
                    (
                        r for r in line_key_to_row.values()
                        if (
                            (r.rev_item if (r.rev_item and r.rev_item != r.item) else r.item)
                            == component_of
                        )
                    ),
                    None,
                )
                main_row = match

            if not main_row:
                continue  # associated line not found in this OMR at all — nothing to block

            rev_status = (getattr(main_row, "rev_line_status", "") or "").strip()
            orig_status = (getattr(main_row, "line_status", "") or "").strip()
            main_being_cancelled = rev_status == "Cancelled" or (not rev_status and orig_status == "Cancelled")

            free_rev_status = (getattr(row, "rev_line_status", "") or "").strip()
            free_being_cancelled_too = free_rev_status == "Cancelled"

            if main_being_cancelled and not free_being_cancelled_too:
                blocked.append(
                    _("Free Item Row {0} (associated with Row {1}, Item {2})").format(
                        row.idx, main_row.idx, main_row.item_code if hasattr(main_row, "item_code") else main_row.item
                    )
                )

        if blocked:
            frappe.throw(
                _(
                    "Cannot cancel the following Sales Order line(s) — a Free Item is "
                    "still associated with them: {0}. Please reassign or cancel the "
                    "Free Item first before proceeding."
                ).format(", ".join(blocked)),
                title=_("Free Item Association Blocked"),
            )
            
    def update_production_plan_sales_order_modification(self):
        frappe.db.sql(
            """
            UPDATE `tabProduction Plan` pp
            INNER JOIN `tabProduction Plan Item` ppi
                ON ppi.parent = pp.name
            SET
                pp.sales_order_modification = %s
            WHERE
                pp.docstatus in (0,1)
                AND ppi.sales_order = %s
            """,
            (
                "YES",
                self.sales_order,
            ),
        )
    
    def update_sales_order_commercial_details(self):
        """Updates Commercial T&C + Details + Reference Data + Terms & Conditions in Sales Order"""

        # ── Commercial T&C
        commercial_map = {
            "rev_price_basis":            "custom_price_basis",
            "rev_mode_of_dispatch":       "custom_mode_of_dispatch",
            "rev_validity":               "custom_validity",
            "rev_freight_charges":        "custom_freight_charges",
            "rev_transit_insurance":      "custom_transit_insurance",
            "rev_delivery":               "custom_delivery",
            "rev_tpi_agency_charges":     "custom_tpi_agency_charges",
            "rev_inspection":             "custom_inspection",
            "rev_legal_requirement":      "custom_legal_requirement",
            "rev_test_certificate":       "custom_test_certificate",
            "rev_bank_charges":           "custom_bank_charges",
            "rev_liquidate_damage":       "custom_liquidate_damage",
            "rev_packing_and_forwarding": "custom_packing_and_forwarding",
            "rev_packing_type":           "custom_packing_type",
            "rev_painting_specification": "custom_painting_specification",
            "rev_qsl_no":                 "custom_qsl_no",
            "rev_drawing_approvalqap":       "custom_drawing_approvalqap",
            "rev_manufacturing_clearance":"custom_manufacturing_clearance",
            "rev_api_monogram":           "custom_api_monogram",
            "rev_ce_marking":             "custom_ce_marking",
            "rev_eway_bill":              "custom_eway_bill",
            "rev_repeat_order_ref":       "custom_repeat_order_ref",
            "rev_payment_terms":          "custom_payment_terms",
            "rev_bank_guaranty":          "custom_bank_guaranty",
        }

        # ── Details
        details_map = {
            "rev_customers_purchase_order":      "po_no",
            "rev_customers_purchase_order_date": "po_date",
        }

        # ── Reference Data
        reference_map = {
            "rev_qtn_ref_no":            "custom_qtn_ref_no",
            "rev_qtn_ref_date":          "custom_qtn_ref_date",
            "rev_loi_no":                "custom_loi_no",
            "rev_loi_date":              "custom_loi_date",
            "rev_customer_project_name": "custom_customer_project_name",
            "rev_end_user":              "custom_end_user",
        }

        # ── Terms & Conditions
        terms_map = {
            "rev_so_remarks": "terms",
        }

        # ── Merge all maps and build UPDATE query
        all_maps = {
            **commercial_map,
            **details_map,
            **reference_map,
            **terms_map,
        }

        updates = []
        params = {"so_name": self.sales_order}

        for omr_field, so_field in all_maps.items():
            val = self.get(omr_field)
            if val is not None and val != "":
                updates.append(f"`{so_field}` = %({omr_field})s")
                params[omr_field] = val

        if updates:
            frappe.db.sql(f"""
                UPDATE `tabSales Order`
                SET {", ".join(updates)}
                WHERE name = %(so_name)s
            """, params)



    def update_bom_items_using_db_set(self):
        if not self.bom:
            return

        # Collect OMR item codes (use rev_item if set, else item)
        omr_items = {
            row.rev_item if row.rev_item else row.item
            for row in self.items
            if row.item or row.rev_item
        }

        current_max_idx = (
            frappe.db.get_value("BOM Item", {"parent": self.bom}, "max(idx)") or 0
        )

        for row in self.items:
            update_data = {}
             # ── Qty, Rate, Amount ────────────────────────────────────────────────────
            orig_qty  = frappe.utils.flt(row.qty)
            orig_rate = frappe.utils.flt(row.rate)
            rev_qty   = frappe.utils.flt(row.rev_qty)
            rev_rate  = frappe.utils.flt(row.rev_rate)

            # Use rev value if provided, else fall back to original
            final_qty  = rev_qty  if rev_qty  > 0 else orig_qty
            final_rate  = rev_rate if  rev_rate > 0 else orig_rate

            # ── Qty ─────────────────────────────────────────────────────────────
            if row.rev_qty:
                update_data["qty"] = row.rev_qty

            if row.rev_rate:
                update_data["rate"] = row.rev_rate
                update_data["base_rate"] =   final_rate



            if final_qty or final_rate :

                update_data["amount"] = final_qty * final_rate
                update_data["base_amount"] = final_qty * final_rate

            # ── Custom fields ────────────────────────────────────────────────────
            if row.rev_drawing_no:
                update_data["custom_drawing_no"] = row.rev_drawing_no
            if row.rev_drawing_rev_no:
                update_data["custom_drawing_rev_no"] = row.rev_drawing_rev_no
            if row.rev_pattern_drawing_no:
                update_data["custom_pattern_drawing_no"] = row.rev_pattern_drawing_no
            if row.rev_pattern_drawing_rev_no:
                update_data["custom_pattern_drawing_rev_no"] = row.rev_pattern_drawing_rev_no
            if row.rev_purchase_specification_no:
                update_data["custom_purchase_specification_no"] = row.rev_purchase_specification_no
            if row.rev_purchase_specification_rev_no:
                update_data["custom_purchase_specification_rev_no"] = row.rev_purchase_specification_rev_no

            # ── Item replacement ─────────────────────────────────────────────────
            if row.rev_item and row.rev_item != row.item:
                item_name, description = frappe.db.get_value(
                    "Item", row.rev_item, ["item_name", "description"]
                )
                update_data["item_code"] = row.rev_item
                update_data["item_name"] = item_name
                update_data["description"] = description

            # ── Resolve existing BOM item by original item_code ──────────────────
            bom_item_name = frappe.db.get_value(
                "BOM Item",
                {"parent": self.bom, "parenttype": "BOM", "item_code": row.item},
                "name",
            )

            if bom_item_name:
                # Existing item — update only if there is something to update
                if update_data:
                    frappe.db.set_value(
                        "BOM Item", bom_item_name, update_data, update_modified=True
                    )

            else:
                # New item — insert only if update_data has meaningful content
                # (rev_item or rev_qty or any other rev field must be set)
                effective_item = row.rev_item or row.item
                if not effective_item:
                    continue

                has_any_rev_data = (
                    row.rev_item
                    or frappe.utils.flt(row.rev_qty) > 0
                    or frappe.utils.flt(row.rev_rate) > 0
                    or row.rev_drawing_no
                    or row.rev_drawing_rev_no
                    or row.rev_pattern_drawing_no
                    or row.rev_pattern_drawing_rev_no
                    or row.rev_purchase_specification_no
                    or row.rev_purchase_specification_rev_no
                )

                if not has_any_rev_data:
                    continue


                current_max_idx += 1

                new_item_dict = {
                    "doctype": "BOM Item",
                    "parent": self.bom,
                    "parenttype": "BOM",
                    "parentfield": "items",
                    "item_code": effective_item,
                    "idx": current_max_idx,

                }
                new_item_dict.update(update_data)

                new_bom_item = frappe.get_doc(new_item_dict)
                new_bom_item.db_insert()

        # ── Delete BOM items not present in OMR ──────────────────────────────────
        bom_items = frappe.db.get_all(
            "BOM Item",
            filters={"parent": self.bom, "parenttype": "BOM"},
            fields=["name", "item_code"],
        )

        for bom_row in bom_items:
            if bom_row.item_code not in omr_items:
                frappe.db.delete("BOM Item", bom_row.name)

        # ── Finalize ──────────────────────────────────────────────────────────────
        bom_doc = frappe.get_doc("BOM", self.bom)
        bom_doc.calculate_cost()
        bom_doc.db_update()

    def validate_qty_and_rev_qty(self):
        table_items = []
        if self.type == "BOM":
            table_items = self.items or []
        elif self.type == "Sales Order" :
            table_items = self.sales_order_item or []

        for row in table_items:
            qty = frappe.utils.flt(row.qty)
            rev_qty = frappe.utils.flt(row.rev_qty)

            if qty == 0 and rev_qty == 0:
                frappe.throw(
                    f"Row {row.idx}: Rev Qty cannot be 0 when Qty is 0",
                    title="Invalid Quantity",
                )
              #  Normalize values
            # rev_rate = row.rev_rate

            # rev_status = (row.rev_line_status or "").strip()
            rev_rate = frappe.utils.flt(getattr(row, "rev_rate", 0))
            rev_status = (getattr(row, "rev_line_status", "") or "").strip()

            #  1. Skip validation if BOTH are empty
            if not rev_rate and not rev_status:
                continue

            # Convert safely (handles None, "")
            rev_rate = frappe.utils.flt(rev_rate)

            #  2. Allow: Cancelled + 0 rate
            if rev_status == "Live":
                continue
            if rev_status == "Cancelled" and rev_rate == 0:
                continue

            #  3. Block: Not cancelled + 0 rate
            if rev_status != "Cancelled" and rev_rate == 0:
                frappe.throw(
                    f"Row {row.idx}: Rev Rate cannot be 0 when Rev Line Status is not 'Cancelled'",
                    title="Invalid Rate",
                )



    def validate_sales_order(self):
        if not self.sales_order:
            return

        so = frappe.get_doc("Sales Order", self.sales_order)

        #  Check using status
        if so.status == "Cancelled":
            frappe.throw(
                _(
                    "Sales Order {0} is cancelled. You cannot use a cancelled Sales Order."
                ).format(so.name)
            )
        # Completed Sales Order (business rule stop)
        elif so.status == "Completed":
            frappe.throw(
                _(
                    "Sales Order {0} is already completed. You cannot proceed with a completed Sales Order."
                ).format(so.name)
            )

    def update_sales_order_revision(self):
        # Safety check
        if not self.sales_order:
            return

        # Get Sales Order


        now_time = now()
        user = frappe.session.user


        frappe.db.sql("""
        UPDATE `tabSales Order`
        SET
            latest_rev_no = %s,
            rev_date = %s,
            modified = %s,
            modified_by = %s
        WHERE name = %s
    """, (
        self.name,
        today(),
        now_time,
        user,
        self.sales_order
    ))


    def update_sales_order_values(self):

        CUSTOM_FIELD_MAP = [
            ("rev_line_status",      "line_status"),
            ("rev_delivery_date",    "delivery_date"),
            ("rev_tag_no",           "tag_no"),
            ("rev_po_line_no",       "po_line_no"),
            ("rev_line_remark",      "line_remark"),
            ("rev_shipping_address", "custom_shipping_address"),
            ("rev_is_free_item",     "is_free_item"),
            ("rev_component_of",     "component_of"),
            # NEW — mirror fields feeding the Free Item association
            # (main_item_id / main_item already exist on Sales Order Item;
            # they are resolved specially below, not via the generic passthrough)
        ]

        # Fields where False/0 is a valid value to write (don't skip with falsy check)
        ALLOW_FALSY_FIELDS = {"rev_is_free_item"}

        # Fields that should clear on SO if rev is blank but SO currently has a value
        # Maps: rev_field → actual SO Item DB field name
        CLEARABLE_FIELDS = {
            "rev_line_status": "line_status",
        }

        # Fields handled specially (Free Item association) — never pass through
        # the generic CUSTOM_FIELD_MAP loop, resolved via _resolve_free_item_associations
        SPECIAL_ASSOCIATION_FIELDS = {"rev_main_item_id", "rev_main_item", "rev_component_of"}

        so = frappe.get_doc("Sales Order", self.sales_order)

        # ── Step 1: Build trans_items for qty / rate update ──────────────────────
        trans_items = []
        for row in self.sales_order_item:
            qty  = row.rev_qty  if (row.rev_qty  and row.rev_qty  > 0) else row.qty
            # rate = row.rev_rate if (row.rev_rate and row.rev_rate > 0) else row.rate
            is_cancelled = (row.rev_line_status or "").strip() == "Cancelled"

            # For cancelled lines, always use 0. Otherwise use rev_rate if positive.
            if is_cancelled:
                rate = 0
            elif row.rev_rate and row.rev_rate > 0:
                rate = row.rev_rate
            else:
                rate = row.rate

            # - New item: no sales_order_item_name + rev_item is set → use rev_item
            # - Existing item: use row.item
            is_new_item    = bool(not row.sales_order_item_name and getattr(row, "rev_item", None))
            effective_item = row.rev_item if is_new_item else row.item
            # ── Always carry forward the existing SO item description ────────────
            existing_description = ""
            # if row.sales_order_item_name:
            #     existing_description = frappe.db.get_value(
            #         "Sales Order Item", row.sales_order_item_name, "description"
            #     ) or ""
            # Fallback to Item master if SO description is empty
            # if not existing_description:
            lookup_item = row.rev_item or row.item
            is_item_changed = bool(row.rev_item and row.rev_item != row.item)

            if getattr(row, "rev_description", None):
                # 1st priority: explicit reviewer-entered/edited description
                existing_description = row.rev_description

            elif is_item_changed:
                # 2nd priority: item changed but no rev_description given → pull fresh from new Item
                existing_description = frappe.db.get_value("Item", lookup_item, "description") or ""

            else:
                # 3rd priority: unchanged item → keep existing SO description, fallback to Item master
                existing_description = ""
                if row.sales_order_item_name:
                    existing_description = frappe.db.get_value(
                        "Sales Order Item", row.sales_order_item_name, "description"
                    ) or ""
                if not existing_description and lookup_item:
                    existing_description = frappe.db.get_value("Item", lookup_item, "description") or ""
                # lookup_item = row.rev_item or row.item
                # if lookup_item:
                #     existing_description = frappe.db.get_value(
                #         "Item", lookup_item, "description"
                #     ) or ""

            if row.sales_order_item_name:
                # Existing SO item — update in place
                trans_items.append({
                    "docname":   row.sales_order_item_name,
                    "item_code": effective_item,
                    "qty":       qty,
                    "rate":      rate,
                    "description": existing_description,

                })
            else:
                # New item — insert into SO
                trans_items.append({
                    "__islocal": True,
                    "item_code": effective_item,
                    "qty":       qty,
                    "rate":      rate,
                    "description": existing_description,
                    "branch": so.branch or self.branch,
                })

        so.save(ignore_permissions=True)

        if trans_items:
            update_child_qty_rate(
                self.type,
                json.dumps(trans_items),
                self.sales_order,
            )

        # ── Step 1b: Resolve Free Item association references ────────────────────
        # Build a map of OMR-row-level "line keys" (sales_order_item_name for
        # existing lines, or the OMR child row's own `name` for newly added
        # lines) to the *actual* Sales Order Item name now on the SO, and to
        # that line's effective (current) item code. This must run AFTER
        # update_child_qty_rate so newly inserted lines already exist on the SO.
        line_resolution = self._resolve_free_item_line_keys()

        # ── Step 2: Update custom fields via direct SQL ──────────────────────────
        now  = frappe.utils.now()
        user = frappe.session.user

        for row in self.sales_order_item:
            so_item_name = self._find_so_item_name(row)
            if not so_item_name:
                continue

            update_fields = {}

            is_free_row = bool(row.is_free_item or getattr(row, "rev_is_free_item", 0))

            for rev_field, so_field in CUSTOM_FIELD_MAP:
                if rev_field in SPECIAL_ASSOCIATION_FIELDS and is_free_row:
                    # Handled below via resolved association instead of raw passthrough
                    continue

                # FIX: Use getattr with sentinel to distinguish "not set" from False/0
                sentinel  = object()
                rev_value = getattr(row, rev_field, sentinel)

                if rev_value is sentinel:
                    continue

                 # ── Clearable field logic ────────────────────────────────────────
                original_field = CLEARABLE_FIELDS.get(rev_field)
                if original_field:
                    if rev_value == "Live":
                        update_fields[so_field] = ""   # clear SO line_status
                    elif rev_value is not None and rev_value != "":
                        update_fields[so_field] = rev_value  # write new value
                    # blank → skip
                    continue


                if rev_field in ALLOW_FALSY_FIELDS:
                    # Always write — False/0 is a valid intended value
                    update_fields[so_field] = rev_value
                else:
                    # Skip only if truly empty/None/blank
                    if rev_value is not None and rev_value != "":
                        update_fields[so_field] = rev_value

            # ── Free Item association (spec sections 3 & 4) ──────────────────────
            # if is_free_row:
            #     line_key = getattr(row, "rev_main_item_id", None) or row.component_of
            #     resolved = line_resolution.get(line_key) if line_key else None

            #     if resolved:
            #         update_fields["main_item_id"] = resolved["so_item_name"]
            #         update_fields["main_item"] = resolved["item_code"]
            #         update_fields["component_of"] = resolved["item_code"]
            #     elif getattr(row, "rev_component_of", None):
            #         # No resolvable line match — still allow a direct item-code
            #         # override for backward compatibility, without touching main_item_id
            #         update_fields["component_of"] = row.rev_component_of

            # ── Free Item association (spec sections 3 & 4) ──────────────────────
            if is_free_row:
                line_key = getattr(row, "rev_main_item_id", None) or row.component_of
                resolved = line_resolution["by_key"].get(line_key) if line_key else None

                if not resolved:
                    # Fallback for stale/local references — covers new main
                    # item + new Free Item added together in the same OMR.
                    fallback_item = (
                        getattr(row, "rev_main_item", None)
                        or getattr(row, "rev_component_of", None)
                        or row.component_of
                    )
                    if fallback_item:
                        resolved = line_resolution["by_item"].get(fallback_item)

                if resolved:
                    update_fields["main_item_id"] = resolved["so_item_name"]
                    update_fields["main_item"] = resolved["item_code"]
                    update_fields["component_of"] = resolved["item_code"]
                elif getattr(row, "rev_component_of", None):
                    update_fields["component_of"] = row.rev_component_of

                # Explicitly guarantee the Free Item checkbox is set — don't
                # rely on the generic CUSTOM_FIELD_MAP passthrough above, which
                # can be skipped/miss for rows added in the same save as their
                # main item.
                update_fields["is_free_item"] = 1

            # If existing item has no branch, set root level branch from Sales Order
            current_branch = frappe.db.get_value("Sales Order Item", so_item_name, "branch")
            if not current_branch:
                update_fields["branch"] = so.branch or self.branch


            if not update_fields:
                continue

            set_clause = ", ".join([
                f"`{so_field}` = %({so_field})s"
                for so_field in update_fields
            ])

            frappe.db.sql(f"""
                UPDATE `tabSales Order Item`
                SET
                    {set_clause},
                    `modified`    = %(modified)s,
                    `modified_by` = %(modified_by)s
                WHERE
                    `name`   = %(name)s
                    AND `parent` = %(parent)s
            """, {
                **update_fields,
                "name":        so_item_name,
                "parent":      self.sales_order,
                "modified":    now,
                "modified_by": user,
            })

        frappe.db.commit()


    # def _resolve_free_item_line_keys(self):
    #     """
    #     Build a lookup: OMR-side line key → { so_item_name, item_code }

    #     Line key is:
    #       - row.sales_order_item_name, for lines that already existed on the SO
    #       - row.name (the OMR child row's own name), for lines newly added
    #         through this OMR (no sales_order_item_name yet)

    #     Must be called after update_child_qty_rate() so new lines are already
    #     present on the Sales Order.
    #     """
    #     so_items_now = frappe.get_all(
    #         "Sales Order Item",
    #         filters={"parent": self.sales_order},
    #         fields=["name", "item_code", "idx"],
    #         order_by="idx asc",
    #     )

    #     resolution = {}
    #     used_so_names = set()

    #     for row in self.sales_order_item:
    #         is_free_row = bool(row.is_free_item or getattr(row, "rev_is_free_item", 0))
    #         if is_free_row:
    #             continue  # only main (non-free) rows can be association targets

    #         line_key = row.sales_order_item_name or row.name
    #         effective_item = row.rev_item or row.item

    #         if row.sales_order_item_name:
    #             so_item_name = row.sales_order_item_name
    #         else:
    #             # Newly added line — match by item_code among not-yet-used SO items
    #             match = next(
    #                 (d for d in so_items_now
    #                  if d.item_code == effective_item and d.name not in used_so_names),
    #                 None,
    #             )
    #             so_item_name = match.name if match else None

    #         if not so_item_name:
    #             continue

    #         used_so_names.add(so_item_name)

    #         # Prefer the item_code actually on the SO row (authoritative),
    #         # falling back to the OMR's effective item if lookup fails.
    #         so_item_code = frappe.db.get_value("Sales Order Item", so_item_name, "item_code") or effective_item

    #         resolution[line_key] = {
    #             "so_item_name": so_item_name,
    #             "item_code": so_item_code,
    #         }

    #     return resolution

    def _resolve_free_item_line_keys(self):
        """
        Build a lookup: OMR-side line key → { so_item_name, item_code }

        Returns:
        - "by_key":  line key (sales_order_item_name, or the OMR child row's
                    own name for a newly added line) → { so_item_name, item_code }
        - "by_item": effective item code → { so_item_name, item_code }, used as
                    a fallback when "by_key" is missing or stale. This covers
                    the case where a new main item and a new Free Item are
                    both added in the same OMR: the client can only capture
                    the main row's temporary, pre-save docname into
                    rev_main_item_id, and that value never gets updated to
                    the real saved name — so the by_key lookup misses.
                    Only kept when the item code is unambiguous across rows.

        Must be called after update_child_qty_rate() so new lines already exist
        on the Sales Order.
        """
        so_items_now = frappe.get_all(
            "Sales Order Item",
            filters={"parent": self.sales_order},
            fields=["name", "item_code", "idx"],
            order_by="idx asc",
        )

        by_key = {}
        by_item = {}
        used_so_names = set()

        for row in self.sales_order_item:
            is_free_row = bool(row.is_free_item or getattr(row, "rev_is_free_item", 0))
            if is_free_row:
                continue  # only main (non-free) rows can be association targets

            line_key = row.sales_order_item_name or row.name
            effective_item = row.rev_item or row.item

            if row.sales_order_item_name:
                so_item_name = row.sales_order_item_name
            else:
                match = next(
                    (d for d in so_items_now
                    if d.item_code == effective_item and d.name not in used_so_names),
                    None,
                )
                so_item_name = match.name if match else None

            if not so_item_name:
                continue

            used_so_names.add(so_item_name)

            # Prefer the *intended* item code (row.rev_item / row.item) over
            # whatever is currently in the DB — for an existing row being
            # replaced, the DB item_code may still be the old one at this point
            # (the actual swap is finalized later, in get_change()).
            so_item_code = effective_item or frappe.db.get_value(
                "Sales Order Item", so_item_name, "item_code"
            )

            entry = {"so_item_name": so_item_name, "item_code": so_item_code}
            by_key[line_key] = entry

            if effective_item:
                by_item[effective_item] = entry if effective_item not in by_item else None

        by_item = {k: v for k, v in by_item.items() if v}  # drop ambiguous matches

        return {"by_key": by_key, "by_item": by_item}


    def _find_so_item_name(self, row):
        # Always trust explicit link first
        if row.sales_order_item_name:
            return row.sales_order_item_name

        # FIX: For new items, row.item is blank — search by rev_item instead
        is_new_item    = bool(not row.item and getattr(row, "rev_item", None))
        lookup_item    = row.rev_item if is_new_item else row.item

        if not lookup_item:
            frappe.log_error(
                title="OMR – cannot resolve item for SO lookup",
                message=f"Both row.item and row.rev_item are empty. omr={self.name}, row={row.idx}",
            )
            return None

        filters = {
            "parent":     self.sales_order,
            "parenttype": "Sales Order",
            "item_code":  lookup_item,
        }
        if row.po_line_no:
            filters["po_line_no"] = row.po_line_no

        so_item_name = frappe.db.get_value(
            "Sales Order Item",
            filters,
            "name",
            order_by="idx desc",
        )

        if not so_item_name:
            frappe.log_error(
                title="OMR – SO item not found for custom field update",
                message=(
                    f"item={lookup_item}, is_new={is_new_item}, "
                    f"po_line_no={row.po_line_no}, omr={self.name}"
                ),
            )

        return so_item_name
@frappe.whitelist()
def get_linked_documents(items):
    """
    items → frm.doc.items (list of dicts)
    """
    if isinstance(items, str):
        items = frappe.parse_json(items)

    EXCLUDED_DOCTYPES = {"Bin", "Order Modification Request"}

    result = []

    for row in items:
        if not row.get("item"):
            continue

        linked_docs = get_all_linked_documents("Item", row.get("item"))

        for d in linked_docs:
            #  Exclude unwanted doctypes
            if d.get("ref_doctype") in EXCLUDED_DOCTYPES:
                continue

            result.append(
                {
                    "ref_doctype": d.get("ref_doctype"),
                    "document_no": d.get("document_no"),
                    "line_item": row.get("idx"),
                }
            )

    return result



def get_all_linked_documents(source_doctype, source_name):
    """
    Wrapper around ERPNext core Linked-With logic.
    Returns linked documents for a given document.
    """

    frappe.has_permission(source_doctype, doc=source_name, throw=True)

    linkinfo = get_linked_doctypes(source_doctype)

    if not linkinfo:
        return []

    linked_docs = get_linked_docs(
        doctype=source_doctype, name=source_name, linkinfo=linkinfo
    )

    result = []

    for ref_doctype, docs in linked_docs.items():
        for doc in docs:
            # Ignore cancelled documents
            if doc.get("docstatus") == 2:
                continue

            result.append(
                {
                    "ref_doctype": ref_doctype,
                    "document_no": doc.get("name"),
                }
            )

    return result


# ---------------------------------------------------------------------------
# Batch-ID generator  (mirrors generate_batch_id_sequential in JS)
# ---------------------------------------------------------------------------


def generate_batch_id(so_name: str, index: int) -> str:
    base_name = re.sub(r"-\d+$", "", so_name)
    item_number = str(index + 1).zfill(3)
    return f"{base_name}-{item_number}"


# ---------------------------------------------------------------------------
# Core batch-creation helper
# ---------------------------------------------------------------------------


def _delete_batch_if_exists(batch_id: str) -> None:
    """Delete an existing Batch document that carries this batch_id, if any."""
    existing = frappe.db.get_value("Batch", {"batch_id": batch_id}, "name")
    if existing:
        try:
            frappe.delete_doc("Batch", existing, force=True, ignore_permissions=True)
            frappe.db.commit()
        except Exception as e:
            frappe.log_error(
                title="OMR – could not delete existing batch",
                message=f"batch_id={batch_id}  name={existing}\n{e}",
            )


def _create_batch(
    item_code: str,
    batch_id: str,
    so_name: str,
    manufacturing_date: str,
    branch: str | None,
    uom: str | None,
    customer: str | None,
) -> str:
    """
    Create a Batch document.
    Returns the created document name.
    Mirrors create_new_batch() in the JS.
    """
    batch_doc = frappe.get_doc(
        {
            "doctype": "Batch",
            "item": item_code,
            "batch_id": batch_id,
            "branch": branch,
            "stock_uom": uom,
            "manufacturing_date": manufacturing_date,
            "expiry_date": None,
            "reference_doctype": "Sales Order",
            "reference_name": so_name,
            "customer": customer,
        }
    )
    batch_doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return batch_doc.name


# ---------------------------------------------------------------------------
# Main entry-point called from OrderModificationRequest.on_submit
# ---------------------------------------------------------------------------


def create_batches_for_omr(omr_doc) -> None:
    """
    For every OMR item row whose corresponding SO item does NOT yet have a
    batch, generate a batch_id (same sequential logic as the SO client script),
    create the Batch document, and write batch_no + custom_batch_no back onto
    the SO item row.
    """
    if not omr_doc.sales_order:
        return

    so_doc = frappe.get_doc("Sales Order", omr_doc.sales_order)
    manufacturing_date = so_doc.transaction_date or frappe.utils.today()

    # Build a quick lookup: SO item name  →  SO item row (for updating later)
    so_items_by_name = {row.name: row for row in so_doc.items}

    created: list[dict] = []
    skipped: list[str] = []
    errors: list[dict] = []

    for omr_row in omr_doc.sales_order_item:
        if not omr_row.rev_item:
            continue

        # ── 1. Resolve the SO item row ──────────────────────────────────────
        so_item_name = omr_row.sales_order_item_name
        if so_item_name:
            so_item = so_items_by_name.get(so_item_name)
        else:

            so_item = next(
                (
                    r
                    for r in so_doc.items
                    if r.item_code == omr_row.rev_item and not r.custom_batch_no
                ),
                None,
            )
            if so_item:
                so_item_name = so_item.name

        if not so_item_name:
            skipped.append(omr_row.rev_item)
            continue

        # ── 2. Skip if SO item already has a batch ──────────────────────────
        existing_batch = frappe.db.get_value(
            "Sales Order Item", so_item_name, "custom_batch_no"
        )
        if existing_batch:
            skipped.append(f"{omr_row.rev_item} (already has batch: {existing_batch})")
            continue

        # ── 3. Check item is batch-enabled ──────────────────────────────────
        has_batch_no = frappe.db.get_value("Item", omr_row.rev_item, "has_batch_no")
        if not has_batch_no:
            errors.append({"item": omr_row.rev_item, "error": "Item is not batch-enabled"})
            frappe.log_error(
                title="OMR – Item not batch-enabled",
                message=f"Item: {omr_row.rev_item}\nReason: Item is not batch-enabled",
            )

            continue

        # ── 4. Determine the index for batch_id generation ──────────────────

        so_item_idx = (
            frappe.db.get_value("Sales Order Item", so_item_name, "idx") or omr_row.idx
        )
        index = int(so_item_idx) - 1

        # ── 5. Derive SO base name (strip amendment suffix, same as JS) ──────

        so_base_name = so_doc.amended_from if so_doc.amended_from else so_doc.name
        batch_id = generate_batch_id(so_base_name, index)

        # ── 6. Delete pre-existing batch with same batch_id (mirror JS) ─────
        _delete_batch_if_exists(batch_id)

        # ── 7. Create the Batch document ─────────────────────────────────────
        try:
            branch = getattr(so_item, "branch", None) if so_item else None
            uom = getattr(so_item, "uom", None) if so_item else None

            batch_name = _create_batch(
                item_code=omr_row.rev_item,
                batch_id=batch_id,
                so_name=so_doc.name,
                manufacturing_date=str(manufacturing_date),
                branch=branch,
                uom=uom,
                customer=so_doc.customer,
            )

            created.append(
                {
                    "item": omr_row.rev_item,
                    "batch_id": batch_id,
                    "batch_doc": batch_name,
                    "so_item_name": so_item_name,
                }
            )

        except Exception as e:
            err_str = str(e)
            if "Duplicate" in err_str or "DuplicateEntryError" in err_str:
                err_str = "Duplicate batch ID – batch may already exist"
            errors.append({"item": omr_row.rev_item, "error": err_str})
            frappe.log_error(
                title="OMR – batch creation error",
                message=f"item={omr_row.rev_item}  batch_id={batch_id}\n{e}",
            )

    # ── 8. Write custom_batch_no back to SO item rows ───────────────────────

    for entry in created:
        so_item_name = entry["so_item_name"]
        # Verify the item still belongs to this SO (same guard as the whitelisted fn)
        if frappe.db.exists(
            "Sales Order Item", {"name": so_item_name, "parent": so_doc.name}
        ):
            frappe.db.set_value(
                "Sales Order Item",
                so_item_name,
                {"custom_batch_no": entry["batch_id"],
                "branch": so_doc.branch or ""
                },
                update_modified=False,
            )

    frappe.db.commit()

    if errors:
        frappe.msgprint(
            _(
                "Batches were created for {0} item(s), but {1} item(s) had errors. "
                "Check the Error Log for details."
            ).format(len(created), len(errors)),
            title=_("Batch Creation – Partial Errors"),
            indicator="orange",
        )


def get_change(self):

    mismatched_rows = get_mismatched_items(self)

    if not mismatched_rows:
        # frappe.msgprint("No mismatched item codes found.")
        return

    updated, updated_boms = update_sales_order_items(self, mismatched_rows)

    created_requests = create_order_modification_requests(updated_boms, self.branch)

    update_child_rows_with_omr(self, created_requests)

    omr_list = [entry["new_omr"]for entry in created_requests]
    actions = [entry["action"] for entry in created_requests]

    # If any were updated, show "Updated", else "Created"
    action = "Updated" if "Updated" in actions else "Created"

    frappe.msgprint(
        f"{action} {len(omr_list)} Bom Modification Request(s): "
        f"{', '.join(omr_list)}"
    )


def get_mismatched_items(self):
    if not self.sales_order:
        return []

    # Fetch all Sales Order Items in one query
    sales_order_items = frappe.get_all(
        "Sales Order Item",
        filters={"parent": self.sales_order},
        fields=["name", "item_code"],
    )

    # Convert to dictionary for fast lookup
    so_item_map = {d.name: d.item_code for d in sales_order_items}

    mismatched_rows = []

    for row in self.sales_order_item:
        if row.sales_order_item_name in so_item_map:
            so_item_code = so_item_map[row.sales_order_item_name]

            # Compare: rev_item is set AND SO still has the old item
            if row.rev_item and so_item_code != row.rev_item:
                mismatched_rows.append(
                    {
                        "row_name": row.name,
                        "sales_order_item_name": row.sales_order_item_name,
                    }
                )

    return mismatched_rows


def update_sales_order_items(self, mismatched_rows):
    """
    Update item_code in Sales Order Item table
    and update Batch item if custom_batch_no exists.
    """

    if not mismatched_rows:
        return []

    row_map = {row.name: row for row in self.sales_order_item}

    updated = []

    updated_boms = []

    for mismatch in mismatched_rows:
        row = row_map.get(mismatch["row_name"])

        if row:
            # item_name = frappe.db.get_value("Item", row.rev_item, "item_name")
            item_name, item_description = frappe.db.get_value(
                "Item", row.rev_item, ["item_name", "description"]
            )
            description = getattr(row, "rev_description", None) or item_description


            # 1️⃣ Update Sales Order Item
            frappe.db.sql(
                """
                UPDATE `tabSales Order Item`
                SET item_code = %s,
                    item_name = %s,
                    description = %s,
                    modified = %s,
                    modified_by = %s
                WHERE name = %s
                AND parent = %s
            """,
                (row.rev_item, item_name,description, frappe.utils.now(), frappe.session.user,
                row.sales_order_item_name, self.sales_order),
            )

            updated.append(row.sales_order_item_name)

            # 2️⃣ Get custom_batch_no from Sales Order Item
            custom_batch_no = frappe.db.get_value(
                "Sales Order Item", row.sales_order_item_name, "custom_batch_no"
            )

            # 3️⃣ Update Batch if exists
            if custom_batch_no:
                update_batch_item(custom_batch_no, row.rev_item)
                bom_name = update_finish_item_bom(custom_batch_no, row.rev_item,row.item)
                if bom_name:
                    bom_docstatus = frappe.db.get_value("BOM", bom_name, "docstatus")
                    if bom_docstatus == 1:
                        updated_boms.append({
                            "row_name": row.name,
                            "bom": bom_name,
                            "custom_batch_no": custom_batch_no,
                        })

                    # updated_boms.append({"row_name": row.name, "bom": bom_name, "custom_batch_no": custom_batch_no})

    if updated or updated_boms:
        frappe.db.commit()

    return updated, updated_boms


def update_batch_item(batch_name, new_item_code):
    """
    Update item field in Batch doctype
    where batch name matches.
    """

    if not batch_name:
        return False

    # Optional safety check (recommended)
    sle_exists = frappe.db.exists("Stock Ledger Entry", {"batch_no": batch_name})

    if sle_exists:
        frappe.msgprint(
            f"Batch {batch_name} has stock transactions. Skipped batch update."
        )
        return False

    item_name = frappe.db.get_value("Item", new_item_code, "item_name")

    frappe.db.sql(
        """
        UPDATE `tabBatch`
        SET item = %s,
            item_name = %s
        WHERE name = %s
    """,
        (new_item_code, item_name, batch_name),
    )

    return True


def update_finish_item_bom(custom_batch_no, new_item,old_item):
    """
    Update submitted BOM using direct SQL.
    Returns updated BOM name.
    """

    if not custom_batch_no:
        return None

    # Get BOM name
    bom_name = frappe.db.sql(
        """
        SELECT name
        FROM `tabBOM`
        WHERE custom_batch_no = %s
        AND item = %s
        LIMIT 1
    """,
        (custom_batch_no,old_item),
        as_dict=True,
    )

    if not bom_name:
        return None



    bom_name = bom_name[0]["name"]
    item_name, description = frappe.db.get_value(
                    "Item", new_item, ["item_name", "description"]
                )

    # Update finished item directly
    frappe.db.sql(
        """
        UPDATE `tabBOM`
        SET item = %s,
            item_name = %s,
            description = %s
        WHERE name = %s
    """,
        (new_item,item_name,description, bom_name),
    )

    frappe.db.commit()

    return bom_name


def create_order_modification_requests(updated_boms, branch):

    created_docs = []


    for entry in updated_boms:

        bom_name = entry["bom"]
        row_name = entry["row_name"]
        custom_batch_no = entry["custom_batch_no"]


        # ── Fetch BOM header fields once ──────────────────────────────────────
        bom_header = frappe.db.get_value(
            "BOM",
            bom_name,
            ["item", "item_name", "description","custom_batch_no"],
            as_dict=True,
        ) or {}

        fg_item_code  = bom_header.get("item")
        fg_item_name  = bom_header.get("item_name")
        # Fall back to Item master description if BOM.description is blank
        item_description = bom_header.get("description") or (
            frappe.db.get_value("Item", fg_item_code, "description")
            if fg_item_code else None
        )

        bom_custom_batch_no = bom_header.get("custom_batch_no")
        actual_batch = bom_custom_batch_no or custom_batch_no




        # ── Check if Draft BOM Modification Request already exists for this BOM ──
        existing_draft = frappe.db.get_value(
            "Bom Modification Request",
            {"bom": bom_name, "batch_no_ref": custom_batch_no, "docstatus": 0},  # docstatus 0 = Draft
            "name"
        )

        if existing_draft:
            action = "Updated"
            # ── Draft exists → Update it, do NOT create new ──
            doc = frappe.get_doc("Bom Modification Request", existing_draft)
            doc.branch = branch
            doc.reason_for_change = "Sales Order Modification"

        else:
            action = "Created"
            doc = frappe.new_doc("Bom Modification Request")
            # doc.type = "BOM"
            doc.bom = bom_name
            doc.branch = branch
            doc.reason_for_change = "Sales Order Modification"

            doc.insert(ignore_permissions=True)

        # ── Always (re)populate these fields ─────────────────────────────────
        doc.batch_no_ref      = actual_batch
        doc.fg_item_code      = fg_item_code
        doc.fg_item_name      = fg_item_name
        doc.item_description  = item_description

        fetch_items_from_reference(doc)

        doc.save(ignore_permissions=True)

        frappe.db.commit()

        created_docs.append({"row": row_name, "new_omr": doc.name, "action": action})

    return created_docs

def fetch_items_from_reference(doc):
    """
    Works like the JS get_item() function.
    Fetches items from Sales Order or BOM
    and fills child table 'items'.
    """

    if doc.bom:
        ref_name = doc.bom
        doc_type = "BOM"

    if not ref_name:
        return

    # Get reference document
    reference_doc = frappe.get_doc(doc_type, ref_name)

    # Clear existing child table (optional but recommended)
    doc.set("items", [])

    # -------- BOM --------
    if reference_doc.items:
        for item in reference_doc.items:
            row = doc.append("items", {})
            row.bom_item_name = item.name
            row.item = item.item_code
            if item.item_code:
                description = frappe.db.get_value(
                    "Item", item.item_code, "description"
                )
                row.description = description
            row.uom = item.uom
            row.do_not_explode = item.do_not_explode
            row.rev_do_not_explode = item.do_not_explode
            row.bom_no = item.bom_no
            row.qty = item.qty
            row.rate = item.rate
            row.batch_no = item.custom_batch_no
            row.drawing_no = item.custom_drawing_no
            row.drawing_rev_no = item.custom_drawing_rev_no
            row.pattern_drawing_no = item.custom_pattern_drawing_no
            row.pattern_drawing_rev_no = item.custom_pattern_drawing_rev_no
            row.purchase_specification_no = item.custom_purchase_specification_no
            row.purchase_specification_rev_no = (
                item.custom_purchase_specification_rev_no
            )


def update_child_rows_with_omr(self, created_requests):
    """
    Update child table field `bom_update_request` on sales_order_item rows
    (item-change rows only) after BOM Modification Requests are created.

    created_requests entries: {"row": <omr sales_order_item child name>, "new_omr": <bmr name>}
    """

    if not created_requests:
        return

    # Build map: child row name → new BMR name
    omr_map = {
        entry["row"]: entry["new_omr"]
        for entry in created_requests
        if entry.get("row") and entry.get("new_omr")
    }

    if not omr_map:
        return


    child_doctype = frappe.get_meta(self.doctype).get_field("sales_order_item").options

    for row in self.sales_order_item:
        new_omr = omr_map.get(row.name)
        if not new_omr:
            continue


        row.bom_update_request = new_omr

        #  Persist to DB
        frappe.db.set_value(
            child_doctype,
            row.name,
            "bom_update_request",
            new_omr,
            update_modified=False,
        )

    # frappe.db.commit()


def create_history_records(self):
    """
    Compare each sales_order_item row's original values with revised values.
    Only keep rows in original_record where actual changes were made.
    The original values are stored in the main fields (item, qty, rate, etc.)
    The revised values are in the rev_* fields (rev_item, rev_qty, rev_rate, etc.)
    """
    if not self.sales_order_item:
        self.set("original_record", [])
        return

    # Check if any rev fields are actually populated
    has_any_revision = False
    for row in self.sales_order_item:
        if (row.rev_item or
            flt(row.rev_qty) > 0 or
            flt(row.rev_rate) > 0 or
            (row.rev_line_status and row.rev_line_status.strip()) or
            row.rev_delivery_date or
            row.rev_tag_no or
            row.rev_shipping_address or
            row.rev_line_remark or
            row.rev_po_line_no or
            row.rev_component_of or
            getattr(row, "rev_main_item_id", None) or
            row.rev_is_free_item not in (None, 0, False)):
            has_any_revision = True
            break

    if not has_any_revision:
        # Clear history if no changes
        self.set("original_record", [])
        return

    # Clear existing history
    self.set("original_record", [])

    # Compare each row's original vs revised values
    for row in self.sales_order_item:
        if not row.sales_order_item_name:
            continue

        changed = False
        history_data = {
            "sales_order_item_name": row.sales_order_item_name,
            "item": row.item,  # Original item
            "qty": row.qty,  # Original qty
            "rate": row.rate,  # Original rate
            "batch_no": row.batch_no,  # Original batch
            "po_line_no": row.po_line_no,  # Original PO line
            "line_status": row.line_status,  # Original line status
            "delivery_date": row.delivery_date,  # Original delivery date
            "tag_no": row.tag_no,  # Original tag no
            "shipping_address": row.shipping_address,  # Original shipping address
            "line_remark": row.line_remark,  # Original line remark
            "is_free_item": row.is_free_item,  # Original is_free_item
            "component_of": row.component_of,  # Original component_of
            "description": row.get("description") if row.get("description") else None,
        }

        # Check item change
        if row.rev_item and row.rev_item != row.item:
            history_data["new_item"] = row.rev_item
            changed = True
        # Check description change
        if getattr(row, "rev_description", None) and row.rev_description != getattr(row, "description", None):
            history_data["rev_description"] = row.rev_description
            changed = True

        # Check qty change (only if rev_qty is provided and different)
        if flt(row.rev_qty) > 0 and flt(row.rev_qty) != flt(row.qty):
            history_data["rev_qty"] = row.rev_qty
            changed = True

        # Check rate change (only if rev_rate is provided and different)
        if flt(row.rev_rate) > 0 and flt(row.rev_rate) != flt(row.rate):
            history_data["rev_rate"] = row.rev_rate
            changed = True

        # Check line status change
        if row.rev_line_status and row.rev_line_status != row.line_status:
            history_data["rev_line_status"] = row.rev_line_status
            changed = True

        # Check delivery date change
        if row.rev_delivery_date and str(row.rev_delivery_date) != str(row.delivery_date):
            history_data["rev_delivery_date"] = row.rev_delivery_date
            changed = True

        # Check tag no change
        if row.rev_tag_no and row.rev_tag_no != row.tag_no:
            history_data["rev_tag_no"] = row.rev_tag_no
            changed = True

        # Check shipping address change
        if row.rev_shipping_address and row.rev_shipping_address != row.shipping_address:
            history_data["rev_shipping_address"] = row.rev_shipping_address
            changed = True

        # Check line remark change
        if row.rev_line_remark and row.rev_line_remark != row.line_remark:
            history_data["rev_line_remark"] = row.rev_line_remark
            changed = True

        # Check PO line no change
        if row.rev_po_line_no and row.rev_po_line_no != row.po_line_no:
            history_data["rev_po_line_no"] = row.rev_po_line_no
            changed = True

        # Check component_of change
        if row.rev_component_of and row.rev_component_of != row.component_of:
            history_data["rev_component_of"] = row.rev_component_of
            changed = True

        # Check Free Item association line change (spec section 4)
        if getattr(row, "rev_main_item_id", None) and row.rev_main_item_id != getattr(row, "main_item_id", None):
            history_data["rev_main_item_id"] = row.rev_main_item_id
            changed = True

        # Check is_free_item change (boolean field)
        if row.rev_is_free_item not in (None, 0, False) and row.rev_is_free_item != row.is_free_item:
            history_data["rev_is_free_item"] = row.rev_is_free_item
            changed = True

        # Only add to history if at least one field changed
        if changed:
            self.append("original_record", history_data)


def _create_commercial_history(self):
    """Create history records for commercial-level changes - one row per changed field"""

    COMMERCIAL_FIELD_MAP = [
        # Commercial T&C
        ("price_basis", "rev_price_basis", "Price Basis"),
        ("mode_of_dispatch", "rev_mode_of_dispatch", "Mode of Dispatch"),
        ("validity", "rev_validity", "Validity"),
        ("freight_charges", "rev_freight_charges", "Freight Charges"),
        ("transit_insurance", "rev_transit_insurance", "Transit Insurance"),
        ("delivery", "rev_delivery", "Delivery"),
        ("tpi_agency_charges", "rev_tpi_agency_charges", "TPI Agency Charges"),
        ("inspection", "rev_inspection", "Inspection"),
        ("legal_requirement", "rev_legal_requirement", "Legal Requirement"),
        ("test_certificate", "rev_test_certificate", "Test Certificate"),
        ("bank_charges", "rev_bank_charges", "Bank Charges"),
        ("liquidate_damage", "rev_liquidate_damage", "Liquidate Damage"),
        ("packing_and_forwarding", "rev_packing_and_forwarding", "Packing and Forwarding"),
        ("packing_type", "rev_packing_type", "Packing Type"),
        ("painting_specification", "rev_painting_specification", "Painting Specification"),
        ("qsl_no", "rev_qsl_no", "QSL No"),
        ("drawing_approvalqap", "rev_drawing_approvalqap", "Drawing Approval QAP"),
        ("manufacturing_clearance", "rev_manufacturing_clearance", "Manufacturing Clearance"),
        ("api_monogram", "rev_api_monogram", "API Monogram"),
        ("ce_marking", "rev_ce_marking", "CE Marking"),
        ("eway_bill", "rev_eway_bill", "E-way Bill"),
        ("repeat_order_ref", "rev_repeat_order_ref", "Repeat Order Ref"),
        ("payment_terms", "rev_payment_terms", "Payment Terms"),
        ("bank_guaranty", "rev_bank_guaranty", "Bank Guaranty"),

        # Details
        ("customers_purchase_order", "rev_customers_purchase_order", "Customer's P.O."),
        ("customers_purchase_order_date", "rev_customers_purchase_order_date", "Customer's P.O. Date"),

        # Reference Data
        ("qtn_ref_no", "rev_qtn_ref_no", "QTN Ref No"),
        ("qtn_ref_date", "rev_qtn_ref_date", "QTN Ref Date"),
        ("loi_no", "rev_loi_no", "LOI No"),
        ("loi_date", "rev_loi_date", "LOI Date"),
        ("customer_project_name", "rev_customer_project_name", "Customer Project Name"),
        ("end_user", "rev_end_user", "End User"),

        # Terms & Conditions
        ("so_remarks", "rev_so_remarks", "SO Remarks"),
    ]

    # Clear existing commercial details
    self.set("commercial_details", [])

    # Add one row per changed field
    changes_count = 0
    for orig_field, rev_field, display_name in COMMERCIAL_FIELD_MAP:
        orig_value = self.get(orig_field)
        rev_value = self.get(rev_field)

        # Skip if rev value is empty/None
        if rev_value is None or rev_value == "":
            continue

        # Convert to string for comparison
        orig_str = str(orig_value) if orig_value is not None else ""
        rev_str = str(rev_value) if rev_value is not None else ""

        # Only add row if values are different
        if orig_str != rev_str:
            row = self.append("commercial_details", {})
            row.label = display_name
            row.original_value = orig_str
            row.revise_value = rev_str
            changes_count += 1

    # If no changes found, table remains empty
    if changes_count == 0:
        self.set("commercial_details", [])