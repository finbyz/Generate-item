import frappe
from frappe.utils import flt
from erpnext.manufacturing.doctype.bom.bom import BOM as OriginalBOM
from generate_item.utils.bom_naming import get_custom_bom_name, get_available_bom_name

class CustomBOM(OriginalBOM):

    def autoname(self):
        """Override autoname to use custom naming pattern"""
        if not self.name and self.item:
            try:
                # Get branch abbreviation from the document
                branch_abbr = getattr(self, 'branch_abbr', None)
                
                # Generate custom BOM name
                custom_name = get_custom_bom_name(self.item, branch_abbr)
                if custom_name:
                    # Ensure name uniqueness by suffixing when a duplicate exists
                    self.name = get_available_bom_name(custom_name)
                    return
            except Exception as e:
                frappe.log_error(
                    "Custom BOM Autoname Error",
                    f"Failed to generate custom name for BOM {self.item}: {str(e)}"
                )
        
        # Fallback to standard naming
        super().autoname()

    def validate(self):
        super().validate()  # Call original validations
        # No strict enforcement for child BOM submission here; handled in on_submit

    def before_save(self):
        # Add any custom pre-save validation if needed here
        return

    def validate_materials(self):
        """Relax child BOM status check while saving; keep other base validations."""
        if not self.get("items"):
            frappe.throw("Raw Materials cannot be blank.")

        for row in self.get("items"):
            if row.bom_no:
                # Allow Draft or Submitted while saving
                self._custom_validate_bom_no(row.item_code, row.bom_no, require_submitted=False)
            if flt(row.qty) <= 0:
                frappe.throw(f"Quantity required for Item {row.item_code} in row {row.idx}")

    def on_submit(self):
        """Enforce that all child BOMs are submitted when parent is submitted."""
        # Strictly require submitted child BOMs at submit
        for row in self.get("items"):
            if row.bom_no:
                self._custom_validate_bom_no(row.item_code, row.bom_no, require_submitted=True)
        super().on_submit()

    def _custom_validate_bom_no(self, item_code: str, bom_no: str, require_submitted: bool):
        """Validate child BOM similar to core but optionally allow Draft status.

        - Ensures BOM exists, is active, and belongs to the same item tree
        - When require_submitted is True (on submit), enforce docstatus == 1
        - When require_submitted is False (on save), allow docstatus in (0, 1)
        """
        bom = frappe.get_doc("BOM", bom_no)

        if not bom.is_active:
            frappe.throw(f"BOM {bom_no} must be active")

        if require_submitted:
            if bom.docstatus != 1:
                frappe.throw(f"BOM {bom_no} must be submitted")
        else:
            if bom.docstatus not in (0, 1):
                frappe.throw(
                    f"BOM '{bom_no}' must be Draft or Submitted, found status {bom.docstatus}"
                )

        if item_code:
            rm_item_exists = False
            for d in bom.items:
                if d.item_code and d.item_code.lower() == item_code.lower():
                    rm_item_exists = True
            for d in bom.scrap_items:
                if d.item_code and d.item_code.lower() == item_code.lower():
                    rm_item_exists = True

            parent_item = bom.item.lower() if bom.item else ""
            item_lower = item_code.lower()
            variant_of = frappe.db.get_value("Item", item_code, "variant_of")
            variant_lower = (variant_of or "").lower()

            if parent_item == item_lower or parent_item == variant_lower:
                rm_item_exists = True

            if not rm_item_exists:
                frappe.throw(f"BOM {bom_no} does not belong to Item {item_code}")

    def get_child_exploded_items(self, bom_no, stock_qty):
        """Add all items from Flat BOM of child BOM.

        Relaxed to include child BOMs in Draft (docstatus in 0,1) so parent `exploded_items`
        is populated even when referenced `bom_no` is not yet submitted.
        """
        child_fb_items = frappe.db.sql(
            """
            SELECT
                bom_item.item_code,
                bom_item.item_name,
                bom_item.description,
                bom_item.source_warehouse,
                bom_item.operation,
                bom_item.stock_uom,
                bom_item.stock_qty,
                bom_item.rate,
                bom_item.include_item_in_manufacturing,
                bom_item.sourced_by_supplier,
                bom_item.stock_qty / ifnull(bom.quantity, 1) AS qty_consumed_per_unit
            FROM `tabBOM Explosion Item` bom_item, `tabBOM` bom
            WHERE
                bom_item.parent = bom.name
                AND bom.name = %s
                AND bom.docstatus in (0, 1)
        """,
            bom_no,
            as_dict=1,
        )

        for d in child_fb_items:
            self.add_to_cur_exploded_items(
                frappe._dict(
                    {
                        "item_code": d["item_code"],
                        "item_name": d["item_name"],
                        "source_warehouse": d["source_warehouse"],
                        "operation": d["operation"],
                        "description": d["description"],
                        "stock_uom": d["stock_uom"],
                        "stock_qty": d["qty_consumed_per_unit"] * stock_qty,
                        "rate": flt(d["rate"]),
                        "include_item_in_manufacturing": d.get("include_item_in_manufacturing", 0),
                        "sourced_by_supplier": d.get("sourced_by_supplier", 0),
                    }
                )
            )
