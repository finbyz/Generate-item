# # Copyright (c) 2026, Finbyz and contributors
# # For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document

import frappe
from frappe import _
from frappe.utils import cint
from frappe import enqueue
import math
import time
import calendar
from frappe.utils import nowdate, getdate
from generate_item.generate_item.doctype.valve_spare_serial.valve_spare_serial import _handle_valve_spare_qty_changes

class SerialNumber(Document):
	pass

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SEQUENCE_PER_LETTER = 9999      # 0001 – 9999 per letter bucket
SEQUENCE_DIGITS     = 4         # zero-padded to 4 digits
BULK_COMMIT_EVERY   = 25_000    # commit to DB every N rows
BULK_INSERT_CHUNK   = 10_000    # SQL VALUES chunk size


INSERT_FIELDS = ["name", "creation", "modified", "modified_by", "owner",
                 "serial_number", "batch","branch","docstatus"]


# ===========================================================================
# PUBLIC ENTRY POINT
# ===========================================================================
@frappe.whitelist()
def create_serial_numbers_for_sales_order(sales_order_name: str):
    """
    Called from the "Create Serial Numbers" button on the Sales Order.

    Flow
    ────
    1.  Read SO branch + items.
    2.  Validate: skip items whose batch already has serial numbers,
        top up items whose qty increased, CANCEL excess for items
        whose qty decreased.
    3.  Calculate total qty for items that still need serials.
    4.  Reserve counter block atomically (rolled back if anything fails).
    5.  Build per-item serial ranges.
    6.  Chunked bulk INSERT — synchronous, no enqueue, flat memory.
    7.  Return timing stats for the JS popup.
    """
    t_start = time.monotonic()

    so_doc = frappe.get_doc("Sales Order", sales_order_name)

    # ── Guard: reject Draft / Cancelled SOs ─────────────────────────────────
    if so_doc.docstatus != 1:
        frappe.throw(
            _("Serial Numbers can only be generated for submitted Sales Orders. "
              "This Sales Order is currently in '{0}' state.").format(
                "Draft" if so_doc.docstatus == 0 else "Cancelled"
            ),
            title=_("Invalid Sales Order State"),
        )

    if so_doc.status in ("Draft","Cancelled", "Closed", "Completed"):
        frappe.throw(
            _("Serial Numbers cannot be generated for a Sales Order with status '{0}'.").format(
                so_doc.status
            ),
            title=_("Invalid Sales Order Status"),
        )
    # ────────────────────────────────────────────────────────────────────────

    branch = so_doc.get("branch")
    if not branch:
        frappe.throw(_("Branch is not set on the Sales Order."))

    # Step 1: extract items
    items = _extract_so_items(so_doc)
    if not items:
        frappe.throw(
        _(
            "No eligible items found on the Sales Order to generate Serial Numbers.<br><br>"
            "Possible reasons:<br>"
            "• All items have <b>Line Status = Cancelled</b><br>"
            "• All items have <b>zero or negative quantity</b><br><br>"
            "Please review the Sales Order items and ensure at least one active item exists."
        ),
        title=_("Cannot Generate Serial Numbers"),
    )
        # frappe.throw(_("No items with valid quantity found on the Sales Order."))

    # Step 2: filter batches — skip complete, trim partial, pass new,
    # flag batches whose qty was DECREASED for cancellation
    items_to_process, skipped, to_cancel = _filter_already_created(items)

    # -----------------------------------------------------------------------
    # Build human-readable batch status summary
    # Only show msgprint if there is something worth reporting
    # -----------------------------------------------------------------------
    skipped_details = []
    partial_count   = 0   # batches where some serials existed, generating diff
    complete_count  = 0   # batches fully done — skipped entirely

    for s in skipped:
        reason = s.get("reason", "complete")

        if reason == "complete":
            complete_count += 1
            skipped_details.append(
                _("Batch {0}: already complete ({1} serials)").format(
                    s["batch_id"], s["existing_count"]
                )
            )
        elif reason == "partial":
            partial_count += 1
            skipped_details.append(
                _("Batch {0}: {1} already existed, generating {2} more").format(
                    s["batch_id"], s["existing_count"], s["generating"]
                )
            )

    # -----------------------------------------------------------------------
    # Step 2b: process quantity-DECREASE cancellations
    # Each batch is handled independently — one failure doesn't block others.
    # -----------------------------------------------------------------------
    cancel_count_total = 0
    cancel_short_total = 0

    for c in to_cancel:
        try:
            result = _cancel_excess_serials_for_batch(
                c["batch_id"], c["cancel_count"], branch=branch
            )
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                f"Serial Number cancellation failed for batch {c['batch_id']}"
            )
            skipped_details.append(
                _("Batch {0}: cancellation failed — see Error Log").format(c["batch_id"])
            )
            continue

        cancel_count_total += result["cancelled"]
        cancel_short_total += result["short_by"]

        if result["short_by"]:
            skipped_details.append(
                _("Batch {0}: qty decreased from {1} to {2} — only {3} of {4} serial(s) "
                  "could be cancelled ({5} linked to Stock Entry — manual review needed)").format(
                    c["batch_id"], c["existing_count"], c["so_qty"],
                    result["cancelled"], c["cancel_count"], result["short_by"],
                )
            )
        else:
            skipped_details.append(
                _("Batch {0}: qty decreased from {1} to {2} — {3} serial number(s) cancelled").format(
                    c["batch_id"], c["existing_count"], c["so_qty"], result["cancelled"],
                )
            )

    if to_cancel:
        frappe.db.commit()

    if skipped_details:
        frappe.msgprint(
            "<br>".join(skipped_details),
            title=_("Batch Status"),
            indicator="orange",
        )

    # -----------------------------------------------------------------------
    # Early exit — nothing left to generate
    # -----------------------------------------------------------------------
    if not items_to_process:
        if cancel_count_total:
            msg = _("{0} serial number(s) cancelled for decreased quantities. "
                     "Nothing new to generate.").format(cancel_count_total)
            indicator = "green"
        else:
            msg = _("All batches on this Sales Order already have serial numbers. Nothing to generate.")
            indicator = "orange"

        frappe.msgprint(msg, title=_("Already Created"), indicator=indicator)
        return {
            "total":            0,
            "skipped":          complete_count,
            "partial":          partial_count,
            "cancelled":        cancel_count_total,
            "cancel_short_by":  cancel_short_total,
            "elapsed_sec":      0,
        }

    # Step 3: total qty (sum of adjusted qtys — partials already trimmed)
    total_qty = sum(row["qty"] for row in items_to_process)

    # Step 4 + 5 + 6: reserve counter, build map, insert — all inside try/except
    series_info     = None
    branch_row_name = None
    old_total       = None
    old_sub         = None

    try:
        series_info, branch_row_name, old_total, old_sub = \
            get_next_naming_series_number(branch, total_qty)

        item_serial_map = _build_item_serial_map(series_info, items_to_process)

        _generate_and_insert(
            series_info     = series_info,
            item_serial_map = item_serial_map,
            sales_order     = sales_order_name,
            total_qty       = total_qty,
            branch          = so_doc.branch,
        )

    except Exception:
        # Rollback counters so the next attempt starts from the same position
        if branch_row_name and old_total is not None:
            frappe.db.set_value(
                "Serial Number Configuration Branches",
                branch_row_name,
                {"total_counter": old_total, "sub_counter": old_sub},
            )
            frappe.db.commit()
        frappe.log_error(frappe.get_traceback(), "Serial Number Generation Failed")
        frappe.throw(
            _("Serial number generation failed. Counter has been rolled back. "
              "Please check the Error Log for details.")
        )

    elapsed = round(time.monotonic() - t_start, 3)

    # -----------------------------------------------------------------------
    # Build skipped/cancelled summary message for return payload
    # Partials are NOT counted as "skipped" — they were partially processed
    # -----------------------------------------------------------------------
    skipped_msg = ""
    if complete_count:
        skipped_msg = _(" ({0} batch(es) skipped — already complete)").format(complete_count)
    if partial_count:
        skipped_msg += _(" ({0} batch(es) topped up — partial generation)").format(partial_count)

    cancel_msg = ""
    if cancel_count_total:
        cancel_msg = _(" ({0} serial(s) cancelled for decreased batch(es))").format(cancel_count_total)
    if cancel_short_total:
        cancel_msg += _(" ({0} short — linked to Stock Entry, manual review needed)").format(cancel_short_total)

    # Step 7: return stats — JS shows the timing popup
    return {
        "total":            total_qty,
        "skipped":          complete_count,
        "partial":          partial_count,
        "cancelled":        cancel_count_total,
        "cancel_short_by":  cancel_short_total,
        "branch":           branch,
        "first_serial":     series_info["first_serial"],   # safe — series_info guaranteed non-None here
        "elapsed_sec":      elapsed,
        "message":      _(
            "{0} serial numbers generated in {1} seconds.{2}{3}"
        ).format(total_qty, elapsed, skipped_msg, cancel_msg),
    }

# ===========================================================================
# SUB-FUNCTION 0a  –  _extract_so_items
# ===========================================================================
def _extract_so_items(so_doc) -> list:
    """
    Returns [{ item_code, item_name, qty, batch_id }, ...] from SO items.
    Items with qty <= 0 are skipped.
    """
    result        = []
   

    for row in so_doc.get("items", []):
        qty = cint(row.get("qty") or 0)
        if qty <= 0:
            continue

         # ── Skip cancelled lines 
        
        line_status = (row.get("line_status") or "").strip().lower()
        if line_status == "cancelled" or line_status == "delivered":
            continue

        if not row.custom_batch_no:
            continue


        item_code = row.get("item_code")

        # 🔹 Fetch item group
        item_group = frappe.db.get_value("Item Generator", item_code, "attribute_1_value")

        # 🔹 Apply validation
        # if not item_group or "valve" not in item_group.lower():
        #     continue

        if  item_group != "Valve":
            continue
        
        result.append({
            "item_code": row.get("item_code") or "",
            "item_name": row.get("item_name") or "",
            "qty":       qty,
            "batch_id":  row.get("custom_batch_no") or "",
        })
    return result


# ===========================================================================
# SUB-FUNCTION 0b  –  _filter_already_created  (duplicate validation)
# ===========================================================================


def _filter_already_created(items: list):
    """
    For each item, checks existing LIVE (docstatus=1) serial numbers vs SO qty:

    Cases:
        existing == 0          → generate all qty (normal)
        existing == qty        → skip entirely (already complete)
        existing < qty         → generate only the difference (partial / increase)
        existing > qty         → CANCEL the excess (quantity was decreased)

    NOTE: the docstatus=1 filter on the count is critical — without it,
    already-cancelled serials would still count as "existing" and would
    permanently block regeneration after a decrease-then-increase cycle.

    Returns:
        to_process  — items that still need serial numbers (with adjusted qty)
        skipped     — list of { batch_id, existing_count, reason } — informational
        to_cancel   — list of { batch_id, existing_count, so_qty, cancel_count }
                      for batches whose qty decreased and need excess cancelled
    """
    to_process = []
    skipped    = []
    to_cancel  = []

    for item in items:
        batch_id = item["batch_id"]
        qty      = item["qty"]

        if not batch_id:
            to_process.append(item)
            continue

        existing = frappe.db.count(
            "Serial Number", {"batch": batch_id, "docstatus": 1}
        )

        if existing == 0:
            # Normal case — generate all
            to_process.append(item)

        elif existing == qty:
            # Already fully generated — skip
            skipped.append({
                "batch_id":       batch_id,
                "existing_count": existing,
                "so_qty":         qty,
                "reason":         "complete",
            })

        elif existing < qty:
            # Partial — existing < qty, generate only the difference
            diff = qty - existing
            to_process.append({
                **item,
                "qty": diff,
            })
            skipped.append({
                "batch_id":       batch_id,
                "existing_count": existing,
                "so_qty":         qty,
                "reason":         "partial",
                "generating":     diff,
            })

        else:
            # existing > qty  →  quantity was DECREASED — cancel the excess
            to_cancel.append({
                "batch_id":       batch_id,
                "existing_count": existing,
                "so_qty":         qty,
                "cancel_count":   existing - qty,
            })

    return to_process, skipped, to_cancel


# ===========================================================================
# SUB-FUNCTION 0c  –  _build_item_serial_map
# ===========================================================================
def _build_item_serial_map(series_info: dict, items: list) -> list:
    """
    Assigns a contiguous slice of the reserved counter block to each item.

    Example (branch Sanand, counter starts at 0):
        Item A  qty=5  start_total=0  -> S26A0001 ... S26A0005
        Item B  qty=3  start_total=5  -> S26A0006 ... S26A0008
    """
    cursor     = series_info["start_total"]
    assignment = []
    for item in items:
        assignment.append({
            "batch_id":    item["batch_id"],
            "qty":         item["qty"],
            "start_total": cursor,
        })
        cursor += item["qty"]
    return assignment


# ===========================================================================
# SUB-FUNCTION 1  –  get_next_naming_series_number
# ===========================================================================
def get_next_naming_series_number(branch: str, qty: int):
    """
    Reads Serial Number Configuration, validates capacity, advances counters.

    Returns:
        series_info     -- dict(prefix, fy, start_total, first_serial)
        branch_row_name -- row PK (needed for rollback on failure)
        old_total       -- value before increment (for rollback)
        old_sub         -- value before increment (for rollback)
    """
    config = frappe.get_single("Serial Number Configuration")
    prefix = _get_branch_prefix(branch, config)
    fy_raw = config.get("fy_year") or str(frappe.utils.nowdate()[:4])
    fy     = str(fy_raw).strip()[-2:]

    branch_row = _get_or_create_branch_row(config, branch)
    old_total  = cint(branch_row.total_counter)
    old_sub    = cint(branch_row.sub_counter)

    max_serials = 26 * SEQUENCE_PER_LETTER
    if old_total + qty > max_serials:
        frappe.throw(
            _("Cannot generate {0} serial numbers for branch '{1}'. "
              "Only {2} slots remain in this fiscal year.").format(
                qty, branch, max_serials - old_total
            )
        )

    first_letter_idx = old_total // SEQUENCE_PER_LETTER
    first_seq        = (old_total % SEQUENCE_PER_LETTER) + 1
    first_letter     = chr(ord('A') + first_letter_idx)
    first_serial     = f"{prefix}{fy}{first_letter}{str(first_seq).zfill(SEQUENCE_DIGITS)}"

    new_total = old_total + qty
    new_sub   = (new_total % SEQUENCE_PER_LETTER) or SEQUENCE_PER_LETTER

    frappe.db.set_value(
        "Serial Number Configuration Branches",
        branch_row.name,
        {"total_counter": new_total, "sub_counter": new_sub},
    )
    frappe.db.commit()

    series_info = {
        "prefix":       prefix,
        "fy":           fy,
        "branch":       branch,
        "start_total":  old_total,
        "end_total":    new_total,
        "first_serial": first_serial,
    }
    return series_info, branch_row.name, old_total, old_sub


# ===========================================================================
# SUB-FUNCTION 2  –  generate_serial_ids
# ===========================================================================
def generate_serial_ids(
    series_info: dict,
    item_assignment: dict,
    user: str,
    branch:str,
) -> list:
    """
    Pure CPU — no DB calls.
    Builds INSERT-ready tuples for one item slice.

    Tuple order matches INSERT_FIELDS exactly:
        name, creation, modified, modified_by, owner, serial_number, batch
    """
    prefix      = series_info["prefix"]
    fy          = series_info["fy"]
    start_total = item_assignment["start_total"]
    qty         = item_assignment["qty"]
    batch_id    = item_assignment["batch_id"]

    now_time = frappe.utils.get_datetime()
    rows     = []

    for i in range(qty):
        pos        = start_total + i
        letter_idx = pos // SEQUENCE_PER_LETTER
        seq        = (pos % SEQUENCE_PER_LETTER) + 1   # 1-based

        letter    = chr(ord('A') + letter_idx)
        serial_no = f"{prefix}{fy}{letter}{str(seq).zfill(SEQUENCE_DIGITS)}"

        rows.append((
            serial_no,   # name          (PK)
            now_time,    # creation
            now_time,    # modified
            user,        # modified_by
            user,        # owner
            serial_no,   # serial_number
            batch_id,    # batch
            series_info["branch"],
            1
        ))

    return rows


# ===========================================================================
# SUB-FUNCTION 3  –  _bulk_insert_serials
# ===========================================================================
def _bulk_insert_serials(rows: list):
    """
    Inserts rows via chunked raw SQL.

    Fix for 'not all arguments converted during string formatting':
    ───────────────────────────────────────────────────────────────
    The original bug: VALUES clause had N placeholder groups, but pymysql
    received the flat values list as positional args for Python's % operator
    instead of as SQL bind parameters.

    Correct approach:
        - Build the VALUES string as N copies of the placeholder group.
        - Pass flat_values as the second arg to frappe.db.sql().
        - Validate len(flat_values) == len(chunk) * len(INSERT_FIELDS) before
          every execute to catch any future field/tuple mismatch immediately.
    """
    if not rows:
        return

    n_fields    = len(INSERT_FIELDS)
    field_str   = ", ".join(f"`{f}`" for f in INSERT_FIELDS)
    placeholder = "(" + ", ".join(["%s"] * n_fields) + ")"

    for chunk_start in range(0, len(rows), BULK_INSERT_CHUNK):
        chunk       = rows[chunk_start : chunk_start + BULK_INSERT_CHUNK]
        flat_values = [val for row in chunk for val in row]

        # Guard: catch field/tuple length mismatch before hitting the DB
        expected = len(chunk) * n_fields
        if len(flat_values) != expected:
            frappe.throw(
                _(
                    "SQL placeholder mismatch — expected {0} values, got {1}. "
                    "INSERT_FIELDS has {2} fields but each row has {3} values."
                ).format(expected, len(flat_values), n_fields, len(chunk[0]))
            )

        values_sql = ", ".join([placeholder] * len(chunk))

        frappe.db.sql(
            f"INSERT IGNORE INTO `tabSerial Number` ({field_str}) VALUES {values_sql}",
            flat_values,
        )


# ===========================================================================
# CORE EXECUTOR  –  chunked bulk INSERT
# ===========================================================================
def _generate_and_insert(
    series_info: dict,
    item_serial_map: list,
    sales_order: str,
    total_qty: int,
    branch:str,
):
    """
    Iterates over each item assignment, slices into BULK_COMMIT_EVERY chunks,
    inserts + commits each chunk. At peak only one chunk lives in RAM.
    """
    total_inserted = 0
    user           = frappe.session.user

    for item_assignment in item_serial_map:
        item_qty = item_assignment["qty"]

        for slice_offset in range(0, item_qty, BULK_COMMIT_EVERY):
            slice_qty = min(BULK_COMMIT_EVERY, item_qty - slice_offset)

            sliced = {
                **item_assignment,
                "start_total": item_assignment["start_total"] + slice_offset,
                "qty":         slice_qty,
            }

            rows = generate_serial_ids(series_info, sliced, user,branch)
            _bulk_insert_serials(rows)
            frappe.db.commit()

            total_inserted += slice_qty

            frappe.publish_realtime(
                event="serial_no_progress",
                message={
                    "percent":     round(total_inserted / total_qty * 100, 1),
                    "inserted":    total_inserted,
                    "total":       total_qty,
                    "sales_order": sales_order,
                },
                user=user,
            )


# ===========================================================================
# INTERNAL HELPERS
# ===========================================================================
def _get_branch_prefix(branch: str, config) -> str:
    """
    Matches branch against Serial Number Configuration branches child table.
    Converts to UPPER, returns first character as prefix.
    e.g. 'sanand' -> 'SANAND' -> 'S'
    """
    branch_lower = branch.strip().lower()
    for row in config.get("branches", []):
        if row.branch.strip().lower() == branch_lower:
            return row.branch.strip().upper()[0]
    frappe.throw(
        _("Branch '{0}' is not configured in Serial Number Configuration. "
          "Please add it to the Branches table.").format(branch)
    )


def _get_or_create_branch_row(config, branch: str):
    """
    Returns the child-table row for the branch, creating it if absent.
    """
    branch_lower = branch.strip().lower()
    for row in config.get("branches", []):
        if row.branch.strip().lower() == branch_lower:
            return row
    row = config.append("branches", {
        "branch":        branch,
        "sub_counter":   0,
        "total_counter": 0,
    })
    config.save(ignore_permissions=True)
    frappe.db.commit()
    return row

# cancel serial numbers 

def cancel_serial_numbers_for_sales_order(sales_order_name: str):
    """
    Called on Sales Order cancel event.
    Cancels all Serial Numbers matching the SO's branch + item batches.
    """
    so_doc = frappe.get_doc("Sales Order", sales_order_name)
    branch = so_doc.get("branch")

    if not branch:
        frappe.throw(_("Branch is not set on the Sales Order."))

    # Collect unique batch IDs from SO items
    batch_ids = list({
        row.get("custom_batch_no")
        for row in so_doc.get("items", [])
        if row.get("custom_batch_no")
    })

    if not batch_ids:
        frappe.msgprint(
            _("No batches found on this Sales Order. Nothing to cancel."),
            title=_("No Batches"),
            indicator="orange",
        )
        return {"cancelled": 0}

    # Bulk cancel: set docstatus = 2 where batch IN (...) AND branch = ? AND docstatus = 1
    placeholders = ", ".join(["%s"] * len(batch_ids))
    params = batch_ids + [branch]

    frappe.db.sql(
        f"""
        UPDATE `tabSerial Number`
        SET    docstatus = 2,
               modified  = NOW(),
               modified_by = %s
        WHERE  batch   IN ({placeholders})
          AND  branch  = %s
          AND  docstatus = 1
        """,
        [frappe.session.user] + batch_ids + [branch],
    )
    frappe.db.commit()

    # Count how many were cancelled for feedback
    cancelled_count = frappe.db.sql(
        f"""
        SELECT COUNT(*) FROM `tabSerial Number`
        WHERE  batch  IN ({placeholders})
          AND  branch = %s
          AND  docstatus = 2
        """,
        batch_ids + [branch],
    )[0][0]

    frappe.msgprint(
        _("{0} Serial Number(s) cancelled for branch '{1}'.").format(cancelled_count, branch),
        title=_("Serial Numbers Cancelled"),
        indicator="green",
    )

    return {"cancelled": cancelled_count, "branch": branch, "batches": batch_ids}


def get_cancelled_line_items(so_doc) -> list:
    """
    Returns items from SO where line_status == 'Cancelled' and batch exists.
    Used to determine which serials to cancel after a status update.
    """
    cancelled = []
    for row in so_doc.get("items", []):
        line_status = (row.get("line_status") or "").strip().lower()
        batch_id    = row.get("custom_batch_no") or ""
        if line_status == "cancelled"  and batch_id:
            cancelled.append({
                "item_code": row.get("item_code") or "",
                "batch_id":  batch_id,
            })
    return cancelled

def cancel_serials_for_items(items_with_batch: list, branch: str) -> dict:
    
    if not items_with_batch or not branch:
        return {"cancelled": 0, "batches": [], "branch": branch}

    # Collect unique non-empty batch IDs
    batch_ids = list({
        item["batch_id"]
        for item in items_with_batch
        if item.get("batch_id")
    })

    if not batch_ids:
        return {"cancelled": 0, "batches": [], "branch": branch}

    placeholders = ", ".join(["%s"] * len(batch_ids))

    # ── Step 1: Count submitted serials BEFORE cancel 
    qty_to_reduce = frappe.db.sql(
        f"""
        SELECT COUNT(*) FROM `tabSerial Number`
        WHERE  batch     IN ({placeholders})
          AND  branch    = %s
          AND  docstatus = 1
        """,
        batch_ids + [branch],
    )[0][0]

    if not qty_to_reduce:
        return {"cancelled": 0, "batches": batch_ids, "branch": branch}

    # ── Step 2: Bulk cancel 
    frappe.db.sql(
        f"""
        UPDATE `tabSerial Number`
        SET    docstatus   = 2,
               modified    = NOW(),
               modified_by = %s
        WHERE  batch     IN ({placeholders})
          AND  branch    = %s
          AND  docstatus = 1
        """,
        [frappe.session.user] + batch_ids + [branch],
    )

    frappe.db.commit()

    return {
        "cancelled": qty_to_reduce,
        "batches":   batch_ids,
        "branch":    branch,
    }


# ===========================================================================
# NEW: SHARED CANCEL CORE — used by both the SO button path (decrease case)
#      and the scheduler (decrease case). Different from the two functions
#      above: those cancel an ENTIRE batch's serials unconditionally when a
#      line is fully cancelled. This one cancels a specific COUNT, preferring
#      newest-first and never touching serials linked to a Stock Entry.
# ===========================================================================
def _cancel_excess_serials_for_batch(batch_id: str, cancel_count: int, branch: str = None) -> dict:
    """
    Cancels up to `cancel_count` LIVE (docstatus=1) serials for a batch.

    Rule
    ────
    1. Sort candidates by name DESC (cancel newest-generated first — mirrors
       the order they were appended in during generation).
    2. Skip any serial that has `stock_entry` set — it is NEVER cancelled,
       not even as a fallback to hit the target count.
    3. If not enough free (unlinked) serials exist, cancel only what's
       available and report the shortfall via `short_by` — caller decides
       how to surface that (msgprint / log).
    """
    if cancel_count <= 0:
        return {"cancelled": 0, "short_by": 0, "cancelled_serials": [], "batch_id": batch_id}

    where  = "batch = %s AND docstatus = 1"
    params = [batch_id]
    if branch:
        where += " AND branch = %s"
        params.append(branch)

    # Lock candidate rows so a concurrent call (button click landing at the
    # same moment as a scheduler tick) can't double-process the same batch.
    serials = frappe.db.sql(
        f"""
        SELECT name, stock_entry
        FROM `tabSerial Number`
        WHERE {where}
        ORDER BY name DESC
        FOR UPDATE
        """,
        params,
        as_dict=True,
    )

    free_serials = [s.name for s in serials if not s.stock_entry]
    to_cancel    = free_serials[:cancel_count]
    short_by     = cancel_count - len(to_cancel)

    if to_cancel:
        placeholders = ", ".join(["%s"] * len(to_cancel))
        frappe.db.sql(
            f"""
            UPDATE `tabSerial Number`
            SET docstatus = 2, modified = %s, modified_by = %s
            WHERE name IN ({placeholders}) AND docstatus = 1
            """,
            [frappe.utils.now(), frappe.session.user] + to_cancel,
        )

    return {
        "cancelled":         len(to_cancel),
        "short_by":          short_by,
        "cancelled_serials": to_cancel,
        "batch_id":          batch_id,
    }


def _handle_cancelled_lines(doc):
    """
    Core logic — finds lines with line_status='Cancelled',
    checks if they have submitted serials, cancels them.
    """
    branch = doc.get("branch")
    if not branch:
        return

    cancelled_items = get_cancelled_line_items(doc)
    if not cancelled_items:
        return

    result = cancel_serials_for_items(cancelled_items, branch)

    if result["cancelled"]:
        frappe.msgprint(
            _("{0} Serial Number(s) cancelled for {1} batch(es) with cancelled line status "
              "on branch '{2}'.").format(
                result["cancelled"],
                len(result["batches"]),
                branch,
            ),
            title=_("Serial Numbers Auto-Cancelled"),
            indicator="orange",
        )





def _cancel_linked_omrs(so_doc):
    """
    Finds all submitted/open OMRs linked to this SO and cancels them.
    OMR docstatus:
        0 = Draft
        1 = Submitted
        2 = Cancelled
    """
    so_name = so_doc.name
    branch  = so_doc.get("branch")

    if not branch:
        return

    # ── Fetch all non-cancelled OMRs linked to this SO + branch ─────────────
    linked_omrs = frappe.get_all(
        "Order Modification Request",
        filters={
            "sales_order": so_name,
            "branch":      branch,
            "docstatus":   1  
        },
        fields=["name", "docstatus"],
        order_by="creation asc",
    )

    if not linked_omrs:
        return

    for omr in linked_omrs:
        omr_name = omr["name"]
        try:
            omr_doc = frappe.get_doc("Order Modification Request", omr_name)
            if omr_doc.docstatus == 1:
                omr_doc.cancel()

        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                f"Failed to cancel OMR {omr_name} before SO {so_name} cancellation"
            )
            

# event hooks

def on_update_sales_order(doc, method):
    """
    Triggered on every SO save/update (including Update Item button).
    Checks for any lines that became 'Cancelled' and cancels their serials.
    """
    # frappe.log_error("trigger on_update_sales_order")
    _handle_cancelled_lines(doc)
    _handle_valve_spare_qty_changes(doc)



def on_cancel_sales_order(doc, method):
    cancel_serial_numbers_for_sales_order(doc.name)


def before_cancel_sales_order(doc, method):
    """
    Before SO cancels:
    1. Find all linked OMRs (by sales_order + branch)
    2. Cancel each submitted OMR first
    3. Then allow SO cancellation to proceed
    """
    _cancel_linked_omrs(doc)



    
def before_cancel_stock_entry(doc, method=None):
    """
    Before Stock Entry cancels:
    Clear the stock_entry reference ONLY on Serial Numbers that are
    explicitly listed in the child rows' serial_no field.
    """
    # if doc.stock_entry_type != "Manufacture":
    #     return

    # ── Collect all serial numbers from child rows ────────────────────────
    serial_nos = []
    for row in (doc.items or []):
        if row.get("use_serial_batch_fields") and row.get("serial_no"):
            parsed = [
                s.strip()
                for s in (row.serial_no or "").splitlines()
                if s.strip()
            ]
            serial_nos.extend(parsed)

    # Deduplicate while preserving order
    serial_nos = list(dict.fromkeys(serial_nos))

    if not serial_nos:
        frappe.log_error(
            f"[SerialAlloc] Cancel {doc.name}: no serial numbers found in child rows — skipping."
        )
        return

    # ── Bulk clear stock_entry only for serials belonging to this entry ───
    placeholders = ", ".join(["%s"] * len(serial_nos))

    updated = frappe.db.sql(
        f"""
        UPDATE `tabSerial Number`
        SET    stock_entry  = ''
               
        WHERE  name         IN ({placeholders})
          AND  stock_entry  = %s
        """,
        [ *serial_nos, doc.name],
        auto_commit=False,   # let Frappe's transaction wrapper handle commit
    )

    frappe.log_error(
        f"[SerialAlloc] Cancel {doc.name}: cleared stock_entry on serials {serial_nos}."
    )  



# ===========================================================================
# SCHEDULER  –  process_sales_orders_for_serial_creation
# ===========================================================================

def process_sales_orders_for_serial_creation():
    """
    Scheduled job — runs periodically to auto-generate/cancel serial numbers.

    Logic per SO item:
        required   = MAX(0, pending_qty - batch_qty)   # how many still needed
        difference = required - serial_count

        difference >  0  → generate `difference` more serials  (qty increased)
        difference == 0  → skip (already correct)
        difference <  0  → CANCEL `abs(difference)` serials    (qty decreased)

    Only processes:
       
        - Workflow state = 'Approved'
        - Status NOT IN ('Draft', 'Cancelled', 'Completed')
        - Items where item_group contains 'valve' (matches _extract_so_items logic)
        - Items with a custom_batch_no set
        - Items with line_status NOT IN ('Cancelled', 'Delivered')
    """

    # ── Step 1: Fetch eligible Sales Orders ─────────────────────────────────
    eligible_sos = frappe.db.sql("""
        SELECT DISTINCT so.name
        FROM   `tabSales Order` so
        WHERE  so.docstatus      = 1
          AND  so.workflow_state = 'Approved'
          AND  so.status NOT IN ('Draft','Closed', 'Cancelled', 'Completed','To Bill')
          
    """, as_dict=True)

    # testing of scheduler

    # eligible_sos = [{'name': 'SODR25180'}]

    # frappe.log_error("list of so ----",eligible_sos)

    if not eligible_sos:
        frappe.logger().info("Serial Scheduler: No eligible Sales Orders found.")
        return

    frappe.logger().info(
        f"Serial Scheduler: Processing {len(eligible_sos)} Sales Order(s)."
    )

    for so_row in eligible_sos:
        so_name = so_row["name"]
        try:
            _process_single_so_for_serial_creation(so_name)
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                f"Serial Scheduler: Failed for Sales Order {so_name}",
            )


def _process_single_so_for_serial_creation(so_name: str):
    """
    Processes one Sales Order:
      1. Joins SO items → Batch → live Serial Number count
      2. Calculates how many serials still need to be generated OR cancelled
      3. Cancels excess first (decrease), then generates any shortfall (increase)
    """

    # ── Step 2: Pull items with batch qty + LIVE serial count in one query ───
    # NOTE: added "AND docstatus = 1" to the sn_counts subquery below.
    # Without it, cancelled serials (docstatus=2) would still be counted as
    # live, which would silently break both the increase and decrease math
    # the moment any cancellation happens.
    rows = frappe.db.sql("""
            SELECT
                soi.name            AS soi_name,
                soi.item_code,
                soi.item_name,
                soi.qty             AS so_qty,
                soi.delivered_qty,
                soi.custom_batch_no AS batch_id,
                COALESCE(b.batch_qty, 0)        AS batch_qty,
                COALESCE(sn_counts.sn_count, 0) AS serial_count
            FROM
                `tabSales Order Item` soi
                -- Join Batch to get available batch_qty
                LEFT JOIN `tabBatch` b
                    ON b.name = soi.custom_batch_no
                -- Join pre-aggregated LIVE serial number counts
                LEFT JOIN (
                    SELECT batch, COUNT(*) AS sn_count
                    FROM   `tabSerial Number`
                    WHERE  (stock_entry IS NULL OR stock_entry = "")
                       AND docstatus = 1
                    GROUP  BY batch
                ) sn_counts
                    ON sn_counts.batch = soi.custom_batch_no
                -- Join Item Generator to filter by Type Of Product = 'Valve'
                INNER JOIN `tabItem Generator` ig
                    ON ig.item_code = soi.item_code
                    AND ig.attribute_1       = 'Type Of Product'
                    AND ig.attribute_1_value = 'Valve'
            WHERE
                soi.parent          = %(so_name)s
                AND soi.custom_batch_no IS NOT NULL
                AND soi.custom_batch_no != ''
                AND soi.qty             > 0
                AND LOWER(COALESCE(soi.line_status, '')) NOT IN ('cancelled', 'delivered')
        """, {"so_name": so_name}, as_dict=True)

    if not rows:
        return

    # ── Step 2b: Get branch from the SO up front (needed for both paths) ────
    branch = frappe.db.get_value("Sales Order", so_name, "branch")

    # ── Step 3: Calculate required generation / cancellation per item ───────
    items_to_generate = []
    items_to_cancel   = []   # NEW — decrease case

    for row in rows:
        so_qty        = cint(row["so_qty"])
        delivered_qty = cint(row["delivered_qty"])
        batch_qty     = cint(row["batch_qty"])
        serial_count  = cint(row["serial_count"])

        # Required = how many still need to exist to cover pending qty
        pending_qty = so_qty - delivered_qty
        required    = pending_qty - batch_qty
        if required < 0:
            required = 0   # can never require a negative count

        # Difference = how many still need to be generated (or cancelled)
        difference = required - serial_count

        if difference > 0:
            items_to_generate.append({
                "item_code": row["item_code"],
                "item_name": row["item_name"],
                "qty":       difference,      # only generate the gap
                "batch_id":  row["batch_id"],
            })
        elif difference < 0:
            # NEW: quantity effectively decreased for this batch — cancel excess
            items_to_cancel.append({
                "batch_id":     row["batch_id"],
                "cancel_count": abs(difference),
            })
        # difference == 0 -> already correct, nothing to do

    # ── Step 3b: process cancellations first (decrease path) ────────────────
    if items_to_cancel and branch:
        cancel_total = 0
        cancel_short = 0

        for c in items_to_cancel:
            try:
                result = _cancel_excess_serials_for_batch(
                    c["batch_id"], c["cancel_count"], branch=branch
                )
            except Exception:
                frappe.log_error(
                    frappe.get_traceback(),
                    f"Serial Scheduler: cancellation failed for batch {c['batch_id']} (SO {so_name})",
                )
                continue

            cancel_total += result["cancelled"]
            cancel_short += result["short_by"]

        if cancel_total or cancel_short:
            frappe.db.commit()
            frappe.logger().info(
                f"Serial Scheduler: SO {so_name} — cancelled {cancel_total} serial(s) "
                f"for decreased quantities"
                + (f", {cancel_short} short (linked to Stock Entry)" if cancel_short else "")
                + "."
            )
        if cancel_short:
            frappe.log_error(
                f"SO {so_name}: {cancel_short} serial(s) could not be cancelled — "
                f"linked to Stock Entry. Manual review needed.",
                "Serial Scheduler: Partial Cancellation",
            )
    elif items_to_cancel and not branch:
        frappe.log_error(
            f"Branch not set on Sales Order {so_name}. Skipping serial cancellation.",
            "Serial Scheduler: Missing Branch (cancel)",
        )

    if not items_to_generate:
        frappe.logger().info(
            f"Serial Scheduler: SO {so_name} — all items already satisfied, skipping generation."
        )
        return

    # ── Step 4: Confirm branch is set before generation ──────────────────────
    if not branch:
        frappe.log_error(
            f"Branch not set on Sales Order {so_name}. Skipping serial generation.",
            "Serial Scheduler: Missing Branch",
        )
        return

    # ── Step 5: Reserve counter block + generate serials ────────────────────
    total_qty       = sum(item["qty"] for item in items_to_generate)
    series_info     = None
    branch_row_name = None
    old_total       = None
    old_sub         = None

    try:
        series_info, branch_row_name, old_total, old_sub = \
            get_next_naming_series_number(branch, total_qty)

        item_serial_map = _build_item_serial_map(series_info, items_to_generate)

        _generate_and_insert(
            series_info    = series_info,
            item_serial_map= item_serial_map,
            sales_order    = so_name,
            total_qty      = total_qty,
            branch         = branch,
        )

        frappe.logger().info(
            f"Serial Scheduler: SO {so_name} — generated {total_qty} serial(s) "
            f"starting from {series_info['first_serial']}."
        )

    except Exception:
        # Rollback counters so the next run starts from the correct position
        if branch_row_name and old_total is not None:
            frappe.db.set_value(
                "Serial Number Configuration Branches",
                branch_row_name,
                {"total_counter": old_total, "sub_counter": old_sub},
            )
            frappe.db.commit()

        frappe.log_error(
            frappe.get_traceback(),
            f"Serial Scheduler: Generation failed for SO {so_name} — counter rolled back.",
        )