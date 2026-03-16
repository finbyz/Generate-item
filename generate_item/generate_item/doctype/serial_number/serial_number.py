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
                 "serial_number", "batch"]


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
        frappe.throw(_("No items with valid quantity found on the Sales Order."))

    # Step 2: skip batches that already have serial numbers
    items_to_process, skipped = _filter_already_created(items)

    if not items_to_process:
        frappe.msgprint(
            _("All batches on this Sales Order already have serial numbers. Nothing to generate."),
            title=_("Already Created"),
            indicator="orange",
        )
        return {"total": 0, "skipped": len(skipped), "elapsed_sec": 0}

    # Step 3: total qty
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
            series_info    = series_info,
            item_serial_map= item_serial_map,
            sales_order    = sales_order_name,
            total_qty      = total_qty,
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

    skipped_msg = (
        _(" ({0} batch(es) skipped — already had serial numbers)").format(len(skipped))
        if skipped else ""
    )

    # Step 7: return stats — JS shows the timing popup
    return {
        "total":        total_qty,
        "skipped":      len(skipped),
        "branch":       branch,
        "first_serial": series_info["first_serial"],
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
    result = []
    for row in so_doc.get("items", []):
        qty = cint(row.get("qty") or 0)
        if qty <= 0:
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
    For each item, checks if its batch already has >= 1 serial number.
    If yes — skip that item (do not generate again).

    Returns:
        to_process  — items that still need serial numbers
        skipped     — list of { batch_id, existing_count } that were skipped
    """
    to_process = []
    skipped    = []

    for item in items:
        batch_id = item["batch_id"]
        if not batch_id:
            to_process.append(item)
            continue

        existing = frappe.db.count("Serial Number", {"batch": batch_id})
        if existing > 0:
            skipped.append({"batch_id": batch_id, "existing_count": existing})
        else:
            to_process.append(item)

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

            rows = generate_serial_ids(series_info, sliced, user)
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