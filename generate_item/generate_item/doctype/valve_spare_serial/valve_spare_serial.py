# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document	
import frappe
from frappe.model.naming import make_autoname
from frappe.utils import getdate
from frappe import _
from frappe.utils import cint


class ValveSpareSerial(Document):

    def autoname(self):
        if not self.branch:
            frappe.throw("Branch is mandatory before naming.")

       
        branch = frappe.scrub(self.branch).upper().replace("_", "")

        year = getdate().year

        # Generates:
        # VSS-SANAND2026-000001
        self.name = make_autoname(f"VSS-{branch}{year}-.######")

# ===========================================================================
# VALVE SPARE SERIAL — created/synced on Batch insert AND on SO qty changes
# ===========================================================================
def _sync_valve_spare_serials_for_batch(batch_id: str, target_qty: int, branch: str) -> dict:
	"""
	Brings live (docstatus != 2) Valve Spare Serial count for `batch_id`
	up/down to match `target_qty`.

	target_qty == SO item qty directly 
	adjustment, per requirement.

	Cases:
		existing == target   → no-op
		existing <  target   → create the difference
		existing >  target   → cancel the excess (newest first)
								
	"""
	target_qty = cint(target_qty)

	existing_live = frappe.db.count(
		"Valve Spare Serial", {"batch": batch_id, "docstatus": ["!=", 2]}
	)

	diff = target_qty - existing_live

	if diff == 0:
		return {"created": 0, "cancelled": 0, "short_by": 0}

	if diff > 0:
		created = []
		for _ in range(diff):
			vss = frappe.get_doc({
				"doctype": "Valve Spare Serial",
				"batch":   batch_id,
				"branch":  branch,
			})
			vss.insert(ignore_permissions=True)
			vss.submit()
			created.append(vss.name)

		return {"created": len(created), "cancelled": 0, "short_by": 0}

	# diff < 0  -> qty decreased, cancel the excess
	cancel_count = abs(diff)

	candidates = frappe.db.sql(
		"""
		SELECT name
		FROM `tabValve Spare Serial`
		WHERE batch = %s AND docstatus != 2
		ORDER BY name DESC
		FOR UPDATE
		""",
		[batch_id],
		as_dict=True,
	)

	free = [c.name for c in candidates]
	to_cancel = free[:cancel_count]
	short_by  = cancel_count - len(to_cancel)

	if to_cancel:
		placeholders = ", ".join(["%s"] * len(to_cancel))
		frappe.db.sql(
			f"""
			UPDATE `tabValve Spare Serial`
			SET docstatus = 2, modified = %s, modified_by = %s
			WHERE name IN ({placeholders}) AND docstatus != 2
			""",
			[frappe.utils.now(), frappe.session.user] + to_cancel,
		)


	return {"created": 0, "cancelled": len(to_cancel), "short_by": short_by}


def _create_valve_spare_serials_for_batch(batch_doc):
	"""
	Runs on Batch after_insert — first-time creation.

	Uses fields already present on the Batch doc itself
	(reference_doctype, reference_name, item, branch) instead of a
	reverse-lookup via custom_batch_no on Sales Order Item, which is only
	written back *after* the batch is created client-side and would
	silently miss on every new Sales Order.
	"""
	batch_id = batch_doc.name

	# Only act when the batch is created directly from a Sales Order
	if batch_doc.get("reference_doctype") != "Sales Order":
		return

	so_name = batch_doc.get("reference_name")
	item_code = batch_doc.get("item")
	if not so_name or not item_code:
		return

	product_type = frappe.db.get_value(
		"Item Generator", item_code, "attribute_1_value"
	)
	if product_type != "Valve Spare":
		return

	# Resolve qty from the matching SO Item row
	so_item_qty = frappe.db.get_value(
		"Sales Order Item",
		{"parent": so_name, "item_code": item_code},
		"qty",
	)
	if not so_item_qty:
		return

	# branch comes from the Batch doc first; fall back to Sales Order
	branch = batch_doc.get("branch") or frappe.db.get_value(
		"Sales Order", so_name, "branch"
	)
	if not branch:
		frappe.log_error(
			f"Branch not set on Batch {batch_id} or Sales Order {so_name}. "
			f"Skipping Valve Spare Serial creation.",
			"Valve Spare Serial: Missing Branch",
		)
		return

	result = _sync_valve_spare_serials_for_batch(batch_id, so_item_qty, branch)

	frappe.logger().info(
		f"Valve Spare Serial: batch '{batch_id}' (SO {so_name}, "
		f"item {item_code}) — created {result['created']}."
	)


def after_insert_batch(doc, method):
	try:
		_create_valve_spare_serials_for_batch(doc)
	except Exception:
		frappe.log_error(
			frappe.get_traceback(),
			f"Valve Spare Serial: creation failed for batch {doc.name}",
		)


# ---------------------------------------------------------------------------
# handle SO qty increase/decrease for Valve Spare items
# ---------------------------------------------------------------------------
def _handle_valve_spare_qty_changes(so_doc):
    """
    Runs on every SO save (called from on_update_sales_order).
    For each SO item whose product type is 'Valve Spare' and has a batch
    already linked, syncs Valve Spare Serial count to the current qty.

    Skipped: items with line_status Cancelled/Delivered, or no batch yet
    (batch not created = nothing to sync, after_insert_batch handles that
    first creation once the batch exists).
    """
    branch = so_doc.get("branch")
    if not branch:
        return

    summary = []

    for row in so_doc.get("items", []):
        batch_id = row.get("custom_batch_no")
        if not batch_id:
            continue

        line_status = (row.get("line_status") or "").strip().lower()
        if line_status in ("cancelled", "delivered"):
            continue

        qty = cint(row.get("qty") or 0)
        if qty <= 0:
            continue

        product_type = frappe.db.get_value(
            "Item Generator", row.get("item_code"), "attribute_1_value"
        )
        if product_type != "Valve Spare":
            continue

        try:
            result = _sync_valve_spare_serials_for_batch(batch_id, qty, branch)
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                f"Valve Spare Serial: sync failed for batch {batch_id} (SO {so_doc.name})"
            )
            continue

        if result["created"]:
            summary.append(_("Batch {0}: {1} Valve Spare Serial(s) created (qty increased)")
                            .format(batch_id, result["created"]))
        if result["cancelled"]:
            summary.append(_("Batch {0}: {1} Valve Spare Serial(s) cancelled (qty decreased)")
                            .format(batch_id, result["cancelled"]))

    if summary:
        frappe.msgprint(
            "<br>".join(summary),
            title=_("Valve Spare Serial — Qty Sync"),
            indicator="blue",
        )



# ---------------------------------------------------------------------------
# handle Sales Order cancellation — cancel all live serials for its batches
# ---------------------------------------------------------------------------
def cancel_valve_spare_serials_for_so(so_doc, method=None):
    """
    Wire to Sales Order on_cancel. Zeroes out every Valve Spare batch on
    the SO so no live serials are left pointing at a cancelled order.
    """
    branch = so_doc.get("branch")
    if not branch:
        return

    for row in so_doc.get("items", []):
        batch_id = row.get("custom_batch_no")
        if not batch_id:
            continue

        product_type = frappe.db.get_value(
            "Item Generator", row.get("item_code"), "attribute_1_value"
        )
        if product_type != "Valve Spare":
            continue

        try:
            _sync_valve_spare_serials_for_batch(batch_id, 0, branch)
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                f"Valve Spare Serial: cancel-cleanup failed for batch {batch_id} "
                f"(SO {so_doc.name} cancelled)",
            )