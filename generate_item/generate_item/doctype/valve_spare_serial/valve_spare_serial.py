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
		frappe.db.commit()
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
		frappe.db.commit()

	return {"created": 0, "cancelled": len(to_cancel), "short_by": short_by}


def _create_valve_spare_serials_for_batch(batch_id: str):
    """
    Runs on Batch after_insert — first-time creation.
    """
    so_item = frappe.db.get_value(
        "Sales Order Item",
        {"custom_batch_no": batch_id},
        ["parent", "item_code", "qty"],
        as_dict=True,
    )
    if not so_item:
        return

    product_type = frappe.db.get_value(
        "Item Generator", so_item.item_code, "attribute_1_value"
    )
    if product_type != "Valve Spare":
        return

    branch = frappe.db.get_value("Sales Order", so_item.parent, "branch")
    if not branch:
        frappe.log_error(
            f"Branch not set on Sales Order {so_item.parent}. "
            f"Skipping Valve Spare Serial creation for batch {batch_id}."
        )
        return

    result = _sync_valve_spare_serials_for_batch(batch_id, so_item.qty, branch)

    frappe.logger().info(
        f"Valve Spare Serial: batch '{batch_id}' (SO {so_item.parent}, "
        f"item {so_item.item_code}) — created {result['created']}."
    )


def after_insert_batch(doc, method):
	try: 
		frappe.log_error(
			f"Valve Spare Serial: calling {doc.name}",
		)

		_create_valve_spare_serials_for_batch(doc.name)
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