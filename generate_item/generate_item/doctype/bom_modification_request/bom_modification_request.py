# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt
import frappe, json
from frappe import _
from frappe.model.naming import make_autoname
from frappe.model.document import Document
from frappe.desk.form.linked_with import (
	get_linked_doctypes,
	get_linked_docs,
)
from frappe.utils import today, now, flt


class BomModificationRequest(Document):

    def autoname(self):
        if self.bom:
            self.name = make_autoname(f"{self.bom}-.##")

    def validate(self):
        self.validate_qty_and_rev_qty()

    def on_submit(self):
        if self.bom:
            self.update_bom_items_using_db_set()  # step 1: apply changes
            self.update_bom_item_revision()        # step 2: stamp + heal zeros

    
    def validate_qty_and_rev_qty(self):
        for row in (self.items or []):
            if not self.bom:
                continue
            if flt(row.qty) == 0 and flt(row.rev_qty) == 0:
                frappe.throw(
                    f"Row {row.idx}: Rev Qty cannot be 0 when Qty is 0",
                    title="Invalid Quantity",
                )

  
    def _qty_fields(self, qty):
       
        q = flt(qty)
        return {
            "qty":                   q,
            # "qty_consumed_per_unit": q,  # ← WO required_qty source
            "conversion_factor":     1,  # ← must be 1 for stock items
            # "stock_qty":             q,  # ← BOM cost calculation source
        }

    
    def _resolve_bom_item_name(self, row):
        
        # PRIMARY: exact PK stored on the BMR child row by the form
        bom_item_name = getattr(row, "bom_item_name", None)
        if bom_item_name:
            if frappe.db.exists("BOM Item", bom_item_name):
                return bom_item_name
            # bom_item_name present but stale (row was deleted externally)
            return None

        # FALLBACK: item_code query — only safe when item_code is unique in BOM
        item_code = getattr(row, "item", None)
        if not item_code:
            return None

        return frappe.db.get_value(
            "BOM Item",
            {"parent": self.bom, "parenttype": "BOM", "item_code": item_code},
            "name",
        )

   
    def update_bom_item_revision(self):
        
        if not self.bom:
            return

        frappe.db.sql("""
            UPDATE `tabBOM Item`
            SET
                rev_no      = %s,
                rev_date    = %s,
                modified    = %s,
                modified_by = %s,

                conversion_factor = CASE
                    WHEN conversion_factor = 0
                      OR conversion_factor IS NULL
                    THEN 1
                    ELSE conversion_factor
                END,

                qty_consumed_per_unit = CASE
                    WHEN qty_consumed_per_unit = 0
                      OR qty_consumed_per_unit IS NULL
                    THEN qty
                    ELSE qty_consumed_per_unit
                END,

                stock_qty = CASE
                    WHEN stock_qty = 0
                      OR stock_qty IS NULL
                    THEN qty
                    ELSE stock_qty
                END

            WHERE parent = %s
        """, (self.name, today(), now(), frappe.session.user, self.bom))


    def _sync_batch_so_to_rev_bom(self, row):
        """
        Two cases:
          1. Row has NO existing bom_no → source is the root BOM (self.bom)
             Fetch batch_no_ref & so_ref from root BOM and write to rev_bom_no.
             Root BOM is NOT cleared.

          2. Row HAS an existing bom_no → source is that child bom_no.
             Clear batch/SO from the existing child BOM, write to rev_bom_no.
        """
        rev_bom_no = getattr(row, "rev_bom_no", None)
        if not rev_bom_no:
            return

        bom_no     = getattr(row, "bom_no", None)
        source_bom = bom_no if bom_no else self.bom

        if source_bom == rev_bom_no:
            return

        source_values = frappe.db.get_value(
            "BOM", source_bom, ["custom_batch_no", "sales_order"], as_dict=True
        )
        if not source_values:
            frappe.log_error(
                f"BMR {self.name}: source BOM '{source_bom}' not found "
                f"while syncing batch/SO to '{rev_bom_no}'.",
                "BMR: Source BOM Missing",
            )
            return

        if bom_no:
            frappe.db.set_value(
                "BOM", bom_no,
                {"custom_batch_no": "", "sales_order": ""},
                update_modified=False,
            )

        frappe.db.set_value(
            "BOM", rev_bom_no,
            {
                "custom_batch_no": source_values.get("custom_batch_no") or "",
                "sales_order":     source_values.get("sales_order") or "",
            },
            update_modified=False,
        )

    def _get_sub_assembly_bom(self, row):
        """
        Return the sub-assembly BOM name linked to this row, or None.
        Uses DB truth (bom_item_name → bom_no), not form data.
        """
        bom_item_name = getattr(row, "bom_item_name", None)
        if not bom_item_name:
            return None
        return frappe.db.get_value("BOM Item", bom_item_name, "bom_no") or None

    def _clear_batch_so_on_sub_assembly_delete(self, row):
        """
        When a sub-assembly row is deleted (is_delete=1), clear
        custom_batch_no and sales_order from that sub-assembly BOM.
        Does nothing for regular component rows.
        """
        sub_assembly_bom = self._get_sub_assembly_bom(row)
        if not sub_assembly_bom:
            return
        frappe.db.set_value(
            "BOM", sub_assembly_bom,
            {"custom_batch_no": "", "sales_order": ""},
            update_modified=False,
        )

   
    def update_bom_items_using_db_set(self):
        if not self.bom:
            return

        # current_max_idx = (
        #     frappe.db.get_value("BOM Item", {"parent": self.bom}, "max(idx)") or 0
        # )
        current_max_idx = (
            frappe.db.sql(
                "SELECT COALESCE(MAX(idx), 0) FROM `tabBOM Item` WHERE parent = %s",
                (self.bom,),
            )[0][0] or 0
        )
        needs_explosion_rebuild = False
        branch = self.branch

        for row in self.items:

            # ── DELETE ────────────────────────────────────────────────────────
            if row.is_delete and row.bom_item_name:
                self._clear_batch_so_on_sub_assembly_delete(row)
                frappe.db.delete("BOM Item", row.bom_item_name)
                needs_explosion_rebuild = True
                continue

            update_data = {}

            # ── Qty / Rate / Amount ───────────────────────────────────────────
            orig_qty  = flt(row.qty)
            orig_rate = flt(row.rate)
            rev_qty   = flt(row.rev_qty)
            rev_rate  = flt(row.rev_rate)

            final_qty  = rev_qty  if rev_qty  > 0 else orig_qty
            final_rate = rev_rate if rev_rate > 0 else orig_rate

            if row.rev_qty:
                # LAYER 2: use _qty_fields() — never set qty alone
                update_data.update(self._qty_fields(row.rev_qty))

            if row.rev_rate:
                update_data["rate"]      = row.rev_rate
                update_data["base_rate"] = final_rate
                
            # ── UOM Change ──────────────────────────────────────────────
            if row.rev_uom:
                update_data["uom"] = row.rev_uom
                update_data["stock_uom"] = row.rev_uom

            if final_qty or final_rate:
                update_data["amount"]      = final_qty * final_rate
                update_data["base_amount"] = final_qty * final_rate

            # ── Custom drawing / spec fields ──────────────────────────────────
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

            # ── BOM No / Do Not Explode ───────────────────────────────────────
            if getattr(row, "rev_do_not_explode", None):
                update_data["do_not_explode"] = 1
                update_data["bom_no"]         = ""
                needs_explosion_rebuild       = True
                if row.bom_item_name:
                    old_bom_no = frappe.db.get_value("BOM Item", row.bom_item_name, "bom_no")
                    if old_bom_no:
                        frappe.db.set_value(
                            "BOM", old_bom_no,
                            {"custom_batch_no": "", "sales_order": ""},
                            update_modified=False,
                        )

            elif getattr(row, "rev_bom_no", None):
                update_data["bom_no"]         = row.rev_bom_no
                update_data["do_not_explode"] = 0
                needs_explosion_rebuild       = True
                self._sync_batch_so_to_rev_bom(row)

            # ── Item replacement ──────────────────────────────────────────────
            if row.rev_item and row.rev_item != getattr(row, "item", None):
                (
                    item_name, description, stock_uom,
                    is_stock_item, allow_alternative_item,
                    has_variants, include_item_in_manufacturing,
                ) = frappe.db.get_value(
                    "Item", row.rev_item,
                    [
                        "item_name", "description", "stock_uom",
                        "is_stock_item", "allow_alternative_item",
                        "has_variants", "include_item_in_manufacturing",
                    ],
                )
                effective_uom = row.rev_uom or stock_uom
                update_data.update({
                    "item_code":                     row.rev_item,
                    "item_name":                     item_name,
                    "description":                   description,
                    "uom":                           effective_uom,
                    "stock_uom":                     effective_uom,
                    "branch":                        branch,
                    "is_stock_item":                 is_stock_item,
                    "allow_alternative_item":        allow_alternative_item,
                    "has_variants":                  has_variants,
                    "include_item_in_manufacturing": include_item_in_manufacturing,
                })
                needs_explosion_rebuild = True

            # ── LAYER 1: resolve existing vs new using exact PK ───────────────
            resolved_bom_item_name = self._resolve_bom_item_name(row)

            if resolved_bom_item_name:
                # Existing BOM Item — update only changed fields
                if update_data:
                    frappe.db.set_value(
                        "BOM Item", resolved_bom_item_name,
                        update_data, update_modified=False,
                    )

            else:
                # ── NEW ITEM INSERT ───────────────────────────────────────────
                effective_item = getattr(row, "rev_item", None) or getattr(row, "item", None)
                if not effective_item:
                    continue

                has_any_rev_data = (
                    row.rev_item
                    or flt(row.rev_qty) > 0
                    or flt(row.rev_rate) > 0
                    or  row.rev_uom
                    or row.rev_drawing_no
                    or row.rev_drawing_rev_no
                    or row.rev_pattern_drawing_no
                    or row.rev_pattern_drawing_rev_no
                    or row.rev_purchase_specification_no
                    or row.rev_purchase_specification_rev_no
                    or getattr(row, "rev_bom_no", None)
                )
                if not has_any_rev_data:
                    continue

                current_max_idx += 1

                # Fetch item master defaults for the new row
                (
                    new_item_name, new_description, new_stock_uom,
                    new_is_stock_item, new_allow_alt,
                    new_has_variants, new_include_mfg,
                ) = frappe.db.get_value(
                    "Item", effective_item,
                    [
                        "item_name", "description", "stock_uom",
                        "is_stock_item", "allow_alternative_item",
                        "has_variants", "include_item_in_manufacturing",
                    ],
                )

                # LAYER 2: seed all WO-facing fields via _qty_fields()
                effective_uom = row.rev_uom or new_stock_uom
                new_item_defaults = {
                    "item_name":                     new_item_name,
                    "description":                   new_description,
                    "uom":                           effective_uom,
                    "stock_uom":                     effective_uom,
                    "is_stock_item":                 new_is_stock_item,
                    "allow_alternative_item":        new_allow_alt,
                    "has_variants":                  new_has_variants,
                    "include_item_in_manufacturing": new_include_mfg,
                    "branch":                        branch,
                }
                new_item_defaults.update(self._qty_fields(flt(row.rev_qty)))

                new_item_dict = {
                    "doctype":     "BOM Item",
                    "parent":      self.bom,
                    "parenttype":  "BOM",
                    "parentfield": "items",
                    "item_code":   effective_item,
                    "idx":         current_max_idx,
                }
                # defaults first, then rev_ fields win on any overlap
                new_item_dict.update(new_item_defaults)
                new_item_dict.update(update_data)

                new_bom_item = frappe.get_doc(new_item_dict)
                new_bom_item.db_insert()
                needs_explosion_rebuild = True

        # ── REINDEX ───────────────────────────────────────────────────────────
        bom_items = frappe.get_all(
            "BOM Item",
            filters={"parent": self.bom, "parenttype": "BOM"},
            fields=["name"],
            order_by="idx asc",
        )
        for i, d in enumerate(bom_items, start=1):
            frappe.db.set_value("BOM Item", d.name, "idx", i, update_modified=False)

        # ── Rebuild explosion + recalculate cost ──────────────────────────────
        bom_doc = frappe.get_doc("BOM", self.bom)
        bom_doc.flags.ignore_validate_update_after_submit = True
        bom_doc.flags.ignore_permissions = True
        bom_doc.reload()

        bom_doc.update_stock_qty()
        # if needs_explosion_rebuild:
           
        bom_doc.update_exploded_items(save=True)

        bom_doc.calculate_cost()
        bom_doc.update_cost(update_parent=True, from_child_bom=False, update_hour_rate=True, save=True)
		
        # bom_doc.db_update()
        bom_doc.save(ignore_permissions=True)
        frappe.db.commit()



def get_all_linked_documents(source_doctype, source_name):
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
            if doc.get("docstatus") == 2:
                continue
            result.append({
                "ref_doctype": ref_doctype,
                "document_no": doc.get("name"),
            })
    return result


@frappe.whitelist()
def get_linked_documents(items):
    if isinstance(items, str):
        items = frappe.parse_json(items)

    EXCLUDED_DOCTYPES = {"Bin", "Order Modification Request", "BOM Modification Request"}
    result = []

    for row in items:
        if not row.get("item"):
            continue
        for d in get_all_linked_documents("Item", row.get("item")):
            if d.get("ref_doctype") in EXCLUDED_DOCTYPES:
                continue
            result.append({
                "ref_doctype": d.get("ref_doctype"),
                "document_no": d.get("document_no"),
                "line_item":   row.get("idx"),
            })

    return result