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
    2.  Validate: skip items whose batch already has serial numbers.
    3.  Calculate total qty for items that still need serials.
    4.  Reserve counter block atomically (rolled back if anything fails).
    5.  Build per-item serial ranges.
    6.  Chunked bulk INSERT — synchronous, no enqueue, flat memory.
    7.  Return timing stats for the JS popup.
    """
    t_start = time.monotonic()

    so_doc = frappe.get_doc("Sales Order", sales_order_name)
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

    # Step 2: filter batches — skip complete, trim partial, pass new
    items_to_process, skipped = _filter_already_created(items)

    # -----------------------------------------------------------------------
    # Build human-readable batch status summary
    # Only show msgprint if there is something worth reporting
    # -----------------------------------------------------------------------
    skipped_details = []
    partial_count   = 0   # batches where some serials existed, generating diff
    complete_count  = 0   # batches fully done — skipped entirely
    over_count      = 0   # batches over-generated — skipped with warning

    for s in skipped:
        reason = s.get("reason", "complete")

        if reason == "complete":
            complete_count += 1
            skipped_details.append(
                _("Batch {0}: already complete ({1} serials)").format(
                    s["batch_id"], s["existing_count"]
                )
            )
        elif reason == "over_generated":
            over_count += 1
            skipped_details.append(
                _("Batch {0}: OVER-GENERATED ({1} serials exist, SO qty is {2})"
                  " — manual review needed").format(
                    s["batch_id"], s["existing_count"], s["so_qty"]
                )
            )
        elif reason == "partial":
            partial_count += 1
            skipped_details.append(
                _("Batch {0}: {1} already existed, generating {2} more").format(
                    s["batch_id"], s["existing_count"], s["generating"]
                )
            )

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
        frappe.msgprint(
            _("All batches on this Sales Order already have serial numbers. Nothing to generate."),
            title=_("Already Created"),
            indicator="orange",
        )
        return {
            "total":       0,
            "skipped":     complete_count + over_count,
            "partial":     partial_count,
            "elapsed_sec": 0,
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
    # Build skipped summary message for return payload
    # Partials are NOT counted as "skipped" — they were partially processed
    # -----------------------------------------------------------------------
    truly_skipped = complete_count + over_count
    skipped_msg = ""
    if truly_skipped:
        skipped_msg = _(" ({0} batch(es) skipped — already complete)").format(truly_skipped)
    if partial_count:
        skipped_msg += _(" ({0} batch(es) topped up — partial generation)").format(partial_count)

    # Step 7: return stats — JS shows the timing popup
    return {
        "total":        total_qty,
        "skipped":      truly_skipped,
        "partial":      partial_count,
        "branch":       branch,
        "first_serial": series_info["first_serial"],   # safe — series_info guaranteed non-None here
        "elapsed_sec":  elapsed,
        "message":      _(
            "{0} serial numbers generated in {1} seconds.{2}"
        ).format(total_qty, elapsed, skipped_msg),
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
        item_group = frappe.db.get_value("Item", item_code, "item_group")

        # 🔹 Apply validation
        if not item_group or "valve" not in item_group.lower():
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
    For each item, checks existing serial numbers vs SO qty:

    Cases:
        existing == 0          → generate all qty (normal)
        existing == qty        → skip entirely (already complete)
        existing < qty         → generate only the difference (partial)
        existing > qty         → skip, but warn (over-generated, manual fix needed)

    Returns:
        to_process  — items that still need serial numbers (with adjusted qty)
        skipped     — list of { batch_id, existing_count } that were skipped
    """
    to_process = []
    skipped    = []

    for item in items:
        batch_id = item["batch_id"]
        qty      = item["qty"]

        if not batch_id:
            to_process.append(item)
            continue

        existing = frappe.db.count("Serial Number", {"batch": batch_id, "docstatus": 1})

        if existing == 0:
            # Normal case — generate all
            to_process.append(item)

        elif existing >= qty:
            # Already fully generated (or over-generated) — skip
            skipped.append({
                "batch_id":      batch_id,
                "existing_count": existing,
                "so_qty":        qty,
                "reason":        "complete" if existing == qty else "over_generated",
            })

        else:
            # Partial — existing < qty, generate only the difference
            diff = qty - existing
            to_process.append({
                **item,
                "qty": diff,   
            })
            skipped.append({
                "batch_id":      batch_id,
                "existing_count": existing,
                "so_qty":        qty,
                "reason":        "partial",
                "generating":    diff,
            })

    return to_process, skipped


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
    
    

def process_sales_orders_for_serial_creation():
    # Step 1: Get eligible Sales Orders
    sales_orders = frappe.get_all(
        "Sales Order",
        filters={
            "docstatus": 1,  # Submitted only
            "status": ["not in", ["Completed", "Cancelled"]],
        },
        fields=["name"]
    )

    for so in sales_orders:
        so_doc = frappe.get_doc("Sales Order", so.name)

        valid = False

        for item in so_doc.items:
            # Step 2: Line status condition
            if item.line_status not in (None, "", "Hold"):
                continue

            # Step 3: Check batch qty
            if not item.batch_no:
                continue

            batch_qty = frappe.db.get_value(
                "Batch",
                item.batch_no,
                "batch_qty"
            ) or 0

            if batch_qty < item.qty:
                valid = True
                break

        # Step 4: Execute function if valid
        if valid:
            try:
                frappe.enqueue(
                    "generate_item.api.create_serial_numbers_for_sales_order",
                    sales_order=so_doc.name,
                    queue="default",
                    timeout=300
                )
            except Exception as e:
                frappe.log_error(
                    frappe.get_traceback(),
                    f"Scheduler Error for Sales Order {so_doc.name}"
                )