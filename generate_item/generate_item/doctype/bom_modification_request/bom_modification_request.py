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

	def on_submit(self):
		if self.bom:
			self.update_bom_items_using_db_set()
			self.update_bom_item_revision()

	def validate(self):
		self.validate_qty_and_rev_qty()


	def validate_qty_and_rev_qty(self):
		table_items = []
		if self.bom:
			table_items = self.items or []
		

		for row in table_items:
			qty = frappe.utils.flt(row.qty)
			rev_qty = frappe.utils.flt(row.rev_qty)

			if qty == 0 and rev_qty == 0:
				frappe.throw(
					f"Row {row.idx}: Rev Qty cannot be 0 when Qty is 0",
					title="Invalid Quantity",
				)

	def update_bom_item_revision(self):
		if not self.bom:
			return

		frappe.db.sql("""
			UPDATE `tabBOM Item`
			SET
				rev_no = %s,
				rev_date = %s,
				modified = %s,
				modified_by = %s
			WHERE parent = %s
		""", (
			self.name,          # BMR reference
			today(),
			now(),
			frappe.session.user,
			self.bom           # BOM name
		))

	# Sync batch_no_ref & so_ref to rev_bom_no ────────────────────
	def _sync_batch_so_to_rev_bom(self, row):
		"""
		
		Two cases:
		  1. Row has NO existing bom_no  → source is the root BOM (self.bom)
		     • Fetch batch_no_ref & so_ref from root BOM
		     • Write them into rev_bom_no BOM  (root BOM is NOT cleared)
 
		  2. Row HAS an existing bom_no  → source is that child bom_no
		     • Fetch batch_no_ref & so_ref from the existing  BOM
		     • Clear those fields on the existing  BOM
		     • Write them into rev_bom_no BOM
 
		Does nothing if rev_bom_no is blank or matches the source BOM.
		"""
		rev_bom_no = row.get("rev_bom_no") if hasattr(row, "get") else getattr(row, "rev_bom_no", None)
		if not rev_bom_no:
			return
 
		# ── Check actual bom_no stored in tabBOM Item (DB truth, not form data) ─
		bom_no = row.get("bom_no") if hasattr(row, "get") else getattr(row, "bom_no", None)			
 
		# ── Determine source BOM ────────────────────────────────────────────────
		if bom_no:
			# Case 2: existing BOM Item has a bom_no in DB → source is that child BOM
			source_bom = bom_no
		else:
			# Case 1: bom_no is blank in DB → source is the root BOM
			source_bom = self.bom
 
		# Avoid self-referential no-op
		if source_bom == rev_bom_no:
			return
 
		# ── Fetch batch & SO from source BOM ────────────────────────────────────
		source_values = frappe.db.get_value(
			"BOM",
			source_bom,
			["custom_batch_no", "sales_order"],  
			as_dict=True,
		)
 
		if not source_values:
			frappe.log_error(
				f"BOM Modification Request {self.name}: source BOM '{source_bom}' not found "
				f"while syncing batch/SO to '{rev_bom_no}'.",
				"BMR: Source BOM Missing",
			)
			return
 
		batch_no_ref = source_values.get("custom_batch_no") or ""
		so_ref       = source_values.get("sales_order") or ""
 
		# ── Case 2 only: clear source child BOM ─────────────────────────────────
		if bom_no:
			frappe.db.set_value(
				"BOM",
				bom_no,
				{
					"custom_batch_no": "",
					"sales_order": "",
				},
				update_modified=False,
			)
			
 
		# ── Write batch & SO to rev_bom_no BOM ──────────────────────────────────
		frappe.db.set_value(
			"BOM",
			rev_bom_no,
			{
				"custom_batch_no": batch_no_ref,
				"sales_order": so_ref,
			},
			update_modified=False,
		)
		
 
	# ── END HELPER ───────────────────────────────────────────────────────────────
				

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
		 # Track whether any bom_no change happened — to decide explosion rebuild
		needs_explosion_rebuild = False
		branch = self.branch

		for row in self.items:

			# ── DELETE LOGIC ─────────────────────────────────────────────
			if row.is_delete and row.bom_item_name:
				frappe.db.delete("BOM Item", row.bom_item_name)
				needs_explosion_rebuild = True

				continue

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

			# ── BOM No & Do Not Explode ───────────────────────────────────────────
			# Mirrors ERPNext core: do_not_explode clears bom_no
			if hasattr(row, "rev_do_not_explode") and row.rev_do_not_explode:
				update_data["do_not_explode"] = 1
				update_data["bom_no"] = ""        
				needs_explosion_rebuild = True

			elif hasattr(row, "rev_bom_no") and row.rev_bom_no:
	
				update_data["bom_no"]         = row.rev_bom_no
				update_data["do_not_explode"] = 0
				needs_explosion_rebuild = True

				# Sync batch_no_ref & so_ref to the revised sub-BOM 
				self._sync_batch_so_to_rev_bom(row)

			# ── Item replacement ─────────────────────────────────────────────────
			if row.rev_item and row.rev_item != row.item:
				item_name, description,stock_uom,is_stock_item,allow_alternative_item,has_variants,include_item_in_manufacturing = frappe.db.get_value(
					"Item", row.rev_item, ["item_name", "description","stock_uom","is_stock_item","allow_alternative_item","has_variants","include_item_in_manufacturing"]
				)
				update_data["item_code"] = row.rev_item
				update_data["item_name"] = item_name
				update_data["branch"] = branch
				update_data["is_stock_item"] = is_stock_item
				update_data["allow_alternative_item"] = allow_alternative_item
				update_data["has_variants"] = has_variants
				update_data["include_item_in_manufacturing"] = include_item_in_manufacturing

				update_data["uom"] = stock_uom
				update_data["stock_uom"] = stock_uom
				update_data["description"] = description
				needs_explosion_rebuild = True

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
						"BOM Item", bom_item_name, update_data, update_modified=False
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
					or (hasattr(row, "rev_bom_no") and row.rev_bom_no)
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
				needs_explosion_rebuild = True

	
		# ── REINDEX ─────────────────────────────────────────────
		bom_items = frappe.get_all(
			"BOM Item",
			filters={"parent": self.bom, "parenttype": "BOM"},
			fields=["name"],
			order_by="idx asc"
		)

		for i, d in enumerate(bom_items, start=1):
			frappe.db.set_value(
				"BOM Item",
				d.name,
				"idx",
				i,
				update_modified=False
			)

			# ── Finalize ──────────────────────────────────────────────────────────────
		bom_doc = frappe.get_doc("BOM", self.bom)
		bom_doc.reload()
		# ── Rebuild explosion table only when needed ──────────────────────────────

		if needs_explosion_rebuild:
			bom_doc.flags.ignore_validate_update_after_submit = True
			bom_doc.flags.ignore_permissions = True
			bom_doc.update_exploded_items(save=True)
		bom_doc.calculate_cost()
		bom_doc.db_update()





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


@frappe.whitelist()
def get_linked_documents(items):
    """
    items → frm.doc.items (list of dicts)
    """
    if isinstance(items, str):
        items = frappe.parse_json(items)

    EXCLUDED_DOCTYPES = {"Bin", "Order Modification Request","BOM Modification Request"}

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