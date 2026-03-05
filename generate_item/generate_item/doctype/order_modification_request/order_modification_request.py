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
from frappe.utils import today


from frappe.utils import get_url_to_form


class OrderModificationRequest(Document):

    def validate(self):
        self.validate_sales_order()
        self.validate_qty_and_rev_qty()

    def on_submit(self):
        if self.type == "BOM" and self.bom:
            self.update_bom_items_using_db_set()

        # if self.type == "Sales Order" and self.sales_order:
        # 	self.update_sales_order_items_using_db_set()

        if self.type == "Sales Order" and self.sales_order:
            self.update_sales_order_values()
            self.update_sales_order_revision()
            create_batches_for_omr(self)
            create_history_records(self)
            get_change(self)

    def update_sales_order_items_using_db_set(self):
        if not self.sales_order:
            return

        #  Collect OMR item codes and line numbers for tracking
        omr_items = {(row.item, row.po_line_no) for row in self.items if row.item}

        # Get the current maximum index for new items
        current_max_idx = (
            frappe.db.get_value(
                "Sales Order Item", {"parent": self.sales_order}, "max(idx)"
            )
            or 0
        )

        #  Update or Insert items
        for row in self.items:
            # Construct update_data only with fields that have values
            update_data = {}

            # Always include qty if it's part of the revision
            if row.rev_qty:
                update_data["qty"] = row.rev_qty

            # Check if item exists in Sales Order using both item_code and po_line_no
            filters = {
                "parent": self.sales_order,
                "parenttype": "Sales Order",
                "item_code": row.item,
            }

            # Add po_line_no to filters if it exists
            if row.po_line_no:
                filters["po_line_no"] = row.po_line_no

            so_item_name = frappe.db.get_value("Sales Order Item", filters, "name")

            if so_item_name:
                # Update existing record in submitted Sales Order
                frappe.db.set_value(
                    "Sales Order Item", so_item_name, update_data, update_modified=True
                )

            elif frappe.utils.flt(row.rev_qty) > 0:
                # Insert new record at the end
                current_max_idx += 1

                # Combine basic info with the revision data
                new_item_dict = {
                    "doctype": "Sales Order Item",
                    "parent": self.sales_order,
                    "parenttype": "Sales Order",
                    "parentfield": "items",
                    "item_code": row.item,
                    "idx": current_max_idx,
                }

                # Add po_line_no if it exists
                if row.po_line_no:
                    new_item_dict["po_line_no"] = row.po_line_no

                new_item_dict.update(update_data)

                new_so_item = frappe.get_doc(new_item_dict)
                # new_so_item.db_insert()
                new_so_item.save()

        #  Delete Sales Order items not present in OMR
        so_items = frappe.db.get_all(
            "Sales Order Item",
            filters={"parent": self.sales_order, "parenttype": "Sales Order"},
            fields=["name", "item_code", "po_line_no"],
        )

        for so_row in so_items:
            # Check if the combination of item_code and po_line_no exists in OMR
            if (so_row.item_code, so_row.get("po_line_no")) not in omr_items:
                frappe.db.delete("Sales Order Item", so_row.name)

        # Finalize
        # Recalculate totals for the submitted Sales Order and update the header
        so_doc = frappe.get_doc("Sales Order", self.sales_order)
        so_doc.calculate_taxes_and_totals()
        so_doc.save()
        # so_doc.db_update()

    def update_bom_items_using_db_set(self):
        if not self.bom:
            return

        #  Collect OMR item codes
        omr_items = {row.item for row in self.items if row.item}

        # Get the current maximum index for new items
        current_max_idx = (
            frappe.db.get_value("BOM Item", {"parent": self.bom}, "max(idx)") or 0
        )

        #  Update or Insert items
        for row in self.items:
            # Construct update_data only with fields that have values
            update_data = {}

            # Always include qty if it's part of the revision
            if row.rev_qty:
                update_data["qty"] = row.rev_qty

            # Use if-blocks for the custom fields to prevent overwriting with None/Empty
            if row.rev_drawing_no:
                update_data["custom_drawing_no"] = row.rev_drawing_no
            if row.rev_drawing_rev_no:
                update_data["custom_drawing_rev_no"] = row.rev_drawing_rev_no
            if row.rev_pattern_drawing_no:
                update_data["custom_pattern_drawing_no"] = row.rev_pattern_drawing_no
            if row.rev_pattern_drawing_rev_no:
                update_data["custom_pattern_drawing_rev_no"] = (
                    row.rev_pattern_drawing_rev_no
                )
            if row.rev_purchase_specification_no:
                update_data["custom_purchase_specification_no"] = (
                    row.rev_purchase_specification_no
                )
            if row.rev_purchase_specification_rev_no:
                update_data["custom_purchase_specification_rev_no"] = (
                    row.rev_purchase_specification_rev_no
                )
            # Check if item exists in BOM
            bom_item_name = frappe.db.get_value(
                "BOM Item",
                {"parent": self.bom, "parenttype": "BOM", "item_code": row.item},
                "name",
            )

            if bom_item_name:
                # Update existing record in submitted BOM
                frappe.db.set_value(
                    "BOM Item", bom_item_name, update_data, update_modified=True
                )

            elif frappe.utils.flt(row.rev_qty) > 0:
                # Insert new record at the end
                current_max_idx += 1

                # Combine basic info with the revision data
                new_item_dict = {
                    "doctype": "BOM Item",
                    "parent": self.bom,
                    "parenttype": "BOM",
                    "parentfield": "items",
                    "item_code": row.item,
                    "idx": current_max_idx,
                }
                new_item_dict.update(update_data)

                new_bom_item = frappe.get_doc(new_item_dict)
                new_bom_item.db_insert()

        #  Delete BOM items not present in OMR
        bom_items = frappe.db.get_all(
            "BOM Item",
            filters={"parent": self.bom, "parenttype": "BOM"},
            fields=["name", "item_code"],
        )

        for bom_row in bom_items:
            if bom_row.item_code not in omr_items:
                frappe.db.delete("BOM Item", bom_row.name)

        #  Finalize
        # Recalculate cost for the submitted BOM and update the header
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
        so = frappe.get_doc("Sales Order", self.sales_order)

        # Update revision fields
        if so:
            so.latest_rev_no = self.name
            so.rev_date = today()
            so.save(ignore_permissions=True)

  

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
        ]

        # Fields where False/0 is a valid value to write (don't skip with falsy check)
        ALLOW_FALSY_FIELDS = {"rev_is_free_item"}

        so = frappe.get_doc("Sales Order", self.sales_order)

        # ── Step 1: Build trans_items for qty / rate update ──────────────────────
        trans_items = []
        for row in self.sales_order_item:
            qty  = row.rev_qty  if (row.rev_qty  and row.rev_qty  > 0) else row.qty
            rate = row.rev_rate if (row.rev_rate and row.rev_rate > 0) else row.rate

            # - New item: no sales_order_item_name + rev_item is set → use rev_item
            # - Existing item: use row.item
            is_new_item    = bool(not row.sales_order_item_name and getattr(row, "rev_item", None))
            effective_item = row.rev_item if is_new_item else row.item

            if row.sales_order_item_name:
                # Existing SO item — update in place
                trans_items.append({
                    "docname":   row.sales_order_item_name,
                    "item_code": effective_item,
                    "qty":       qty,
                    "rate":      rate,
                })
            else:
                # New item — insert into SO
                trans_items.append({
                    "__islocal": True,
                    "item_code": effective_item,  
                    "qty":       qty,
                    "rate":      rate,
                })

        so.save(ignore_permissions=True)

        if trans_items:
            update_child_qty_rate(
                self.type,
                json.dumps(trans_items),
                self.sales_order,
            )

        # ── Step 2: Update custom fields via direct SQL ──────────────────────────
        now  = frappe.utils.now()
        user = frappe.session.user

        for row in self.sales_order_item:
            so_item_name = self._find_so_item_name(row)
            if not so_item_name:
                continue

            update_fields = {}
            for rev_field, so_field in CUSTOM_FIELD_MAP:
                # FIX: Use getattr with sentinel to distinguish "not set" from False/0
                sentinel  = object()
                rev_value = getattr(row, rev_field, sentinel)

                if rev_value is sentinel:
                    continue  

                if rev_field in ALLOW_FALSY_FIELDS:
                    # Always write — False/0 is a valid intended value
                    update_fields[so_field] = rev_value
                else:
                    # Skip only if truly empty/None/blank
                    if rev_value is not None and rev_value != "":
                        update_fields[so_field] = rev_value

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
                {"custom_batch_no": entry["batch_id"]},
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
        frappe.msgprint("No mismatched item codes found.")
        return

    updated, updated_boms = update_sales_order_items(self, mismatched_rows)

    created_requests = create_order_modification_requests(updated_boms)

    update_child_rows_with_omr(self, created_requests)

    omr_list = [entry["new_omr"] for entry in created_requests]

    frappe.msgprint(
        f"Created {len(omr_list)} Order Modification Request(s): "
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
            item_name = frappe.db.get_value("Item", row.rev_item, "item_name")

            # 1️⃣ Update Sales Order Item
            frappe.db.sql(
                """
                UPDATE `tabSales Order Item`
                SET item_code = %s,
                    item_name = %s,
                    modified = %s,
                    modified_by = %s
                WHERE name = %s
                AND parent = %s
            """,
                (row.rev_item, item_name, frappe.utils.now(), frappe.session.user,
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
                bom_name = update_finish_item_bom(custom_batch_no, row.rev_item)
                if bom_name:
                    updated_boms.append({"row_name": row.name, "bom": bom_name})

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


def update_finish_item_bom(custom_batch_no, new_item):
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
        LIMIT 1
    """,
        (custom_batch_no,),
        as_dict=True,
    )

    if not bom_name:
        return None

    bom_name = bom_name[0]["name"]

    # Update finished item directly
    frappe.db.sql(
        """
        UPDATE `tabBOM`
        SET item = %s
        WHERE name = %s
    """,
        (new_item, bom_name),
    )

    frappe.db.commit()

    return bom_name


def create_order_modification_requests(updated_boms):

    created_docs = []

    for entry in updated_boms:

        bom_name = entry["bom"]
        row_name = entry["row_name"]

        doc = frappe.new_doc("Order Modification Request")
        doc.type = "BOM"
        doc.bom = bom_name

        doc.insert(ignore_permissions=True)

        fetch_items_from_reference(doc)

        doc.save(ignore_permissions=True)

        frappe.db.commit()

        created_docs.append({"row": row_name, "new_omr": doc.name})

    return created_docs


def fetch_items_from_reference(doc):
    """
    Works like the JS get_item() function.
    Fetches items from Sales Order or BOM
    and fills child table 'items'.
    """

    if not doc.type:
        return

    # Determine reference document
    if doc.type == "Sales Order":
        ref_name = doc.sales_order
    elif doc.type == "BOM":
        ref_name = doc.bom
    else:
        return

    if not ref_name:
        return

    # Get reference document
    reference_doc = frappe.get_doc(doc.type, ref_name)

    # Clear existing child table (optional but recommended)
    doc.set("items", [])
    doc.set("sales_order_item", [])

    # -------- SALES ORDER --------
    if doc.type == "Sales Order":
        for item in reference_doc.items:
            row = doc.append("sales_order_item", {})
            row.sales_order_item_name = item.name
            row.item = item.item_code
            row.qty = item.qty
            row.batch_no = item.custom_batch_no
            row.po_line_no = item.po_line_no
            row.rate = item.rate

    # -------- BOM --------
    elif doc.type == "BOM":
        for item in reference_doc.items:
            row = doc.append("items", {})
            row.item = item.item_code
            row.qty = item.qty
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
    Update child table field `bom_update_request`
    based on created OMR mapping.
    """

    if not created_requests:
        return

    row_map = {row.name: row for row in self.items}

    for entry in created_requests:
        row_name = entry.get("row")
        new_omr = entry.get("new_omr")

        child_row = row_map.get(row_name)

        if child_row and new_omr:
            child_row.bom_update_request = new_omr


def create_history_records(self):
    """
    Compare items with original_record.
    If changed:
        - store new item in new_item
        - store new qty in rev_qty
        - store new rate in rev_rate
    Keep only changed rows in original_record.
    """

    if not self.sales_order_item or not self.original_record:
        self.set("original_record", [])
        return
        

    # Map current items using stable key
    current_map = {row.sales_order_item_name: row for row in self.sales_order_item}

    rows_to_keep = []

    for old_row in self.original_record:

        current_row = current_map.get(old_row.sales_order_item_name)
        if not current_row:
            continue

        changed = False
        old_data = old_row.as_dict()

        # 1️⃣ Check Item Change
        if old_row.item != current_row.item:
            old_data["new_item"] = current_row.item
            changed = True

        # 2️⃣ Check Qty Change
        if old_row.rev_qty != current_row.rev_qty:
            old_data["rev_qty"] = current_row.rev_qty
            changed = True

        # 3️⃣ Check Rate Change
        if old_row.rev_rate != current_row.rev_rate:
            old_data["rev_rate"] = current_row.rev_rate
            changed = True

        if changed:
            rows_to_keep.append(old_data)

    # Clear table
    self.set("original_record", [])

    # Add only changed rows
    for row in rows_to_keep:
        self.append("original_record", row)
