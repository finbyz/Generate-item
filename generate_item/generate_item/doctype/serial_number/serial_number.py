# # Copyright (c) 2026, Finbyz and contributors
# # For license information, please see license.txt


from frappe.model.document import Document


class SerialNumber(Document):
	pass




# import frappe
# from frappe import _
# from frappe import enqueue
# from frappe.utils import now_datetime, cint


# COUNTER_MAX     = 9999
# COUNTER_PADDING = 4
# SERIES_SEQUENCE = ["A", "B", "C", "D"]


# # ─────────────────────────────────────────────────────────────────────────────
# #  HOOKS
# # ─────────────────────────────────────────────────────────────────────────────

# def generate_serial_numbers(doc, method):
#     if doc.workflow_state != "Approved":
#         return
#     if not _get_valve_lines(doc):
#         return
#     enqueue(
#         _generate_background,
#         queue="default",
#         timeout=6000,
#         job_name=f"serial_number_generation_{doc.name}",
#         so_name=doc.name,
#     )


# def reconcile_serial_numbers(doc, method):
#     enqueue(
#         _reconcile_background,
#         queue="default",
#         timeout=6000,
#         job_name=f"serial_number_reconcile_{doc.name}",
#         so_name=doc.name,
#     )


# # def cancel_all_serial_numbers(doc, method):
# #     _cancel_all_for_so(doc.name, "Order cancelled")


# def omr_on_submit(doc, method):
#     enqueue(
#         _omr_reconcile_background,
#         queue="default",
#         timeout=6000,
#         job_name=f"serial_number_omr_{doc.name}",
#         omr_name=doc.name,
#     )


# # ─────────────────────────────────────────────────────────────────────────────
# #  BACKGROUND WORKERS
# # ─────────────────────────────────────────────────────────────────────────────

# def _generate_background(so_name):
#     try:
#         doc = frappe.get_doc("Sales Order", so_name)

#         if not doc.branch:
#             frappe.throw(_("Sales Order is missing Branch."))

#         branch_code = doc.branch[0].upper()
#         year_code   = str(doc.transaction_date.year)[-2:]

#         for item in doc.items:
#             if not _is_valve_item(item.item_code):
#                 continue

#             # Idempotency: skip if SNs already exist for this line
#             if _get_active_sn_count(so_name, item.idx) > 0:
#                 continue

#             _bulk_allocate(item, doc, branch_code, year_code)

#     except Exception:
#         frappe.log_error(frappe.get_traceback(),
#                          f"SN Generation Failed: {so_name}")
#         raise


# def _reconcile_background(so_name):
#     try:
#         doc = frappe.get_doc("Sales Order", so_name)

#         if not doc.branch:
#             return

#         branch_code = doc.branch[0].upper()
#         year_code   = str(doc.transaction_date.year)[-2:]
#         _reconcile_so_lines(doc, branch_code, year_code, so_name)

#     except Exception:
#         frappe.log_error(frappe.get_traceback(),
#                          f"SN Reconcile Failed: {so_name}")
#         raise


# def _omr_reconcile_background(omr_name):
#     try:
#         omr = frappe.get_doc("Order Modification Request", omr_name)
#         so  = frappe.get_doc("Sales Order", omr.sales_order)

#         if not so.branch:
#             frappe.throw(_("Sales Order is missing Branch."))

#         branch_code  = so.branch[0].upper()
#         year_code    = str(so.transaction_date.year)[-2:]
#         original_map = {
#             row.sales_order_item_name: row
#             for row in omr.original_record
#         }

#         for new_row in omr.sales_order_item:
#             if not _is_valve_item(new_row.item):
#                 continue

#             orig_row     = original_map.get(new_row.sales_order_item_name)
#             so_item_name = new_row.sales_order_item_name
#             so_line_idx  = _get_so_line_idx(so_item_name)

#             # ── Line cancelled ────────────────────────────────────────────
#             effective_status = new_row.rev_line_status or new_row.line_status
#             if effective_status == "Cancelled":
#                 # _cancel_sns_for_line(so.name, so_line_idx,"Line cancelled via OMR")
#                 continue

#             # ── Item replaced ─────────────────────────────────────────────
#             orig_item = orig_row.item if orig_row else None
#             if orig_item and orig_item != new_row.item:
#                 # _cancel_sns_for_line(
#                 #     so.name, so_line_idx,
#                 #     f"Item replaced via OMR: {orig_item} → {new_row.item}")

#                 if _is_valve_item(new_row.item):
#                     effective_qty = cint(new_row.rev_qty) or cint(new_row.qty)
#                     if effective_qty > 0:
#                         fake_item = _make_fake_item(
#                             new_row.item, effective_qty,
#                             so_line_idx, new_row.batch_no)
#                         _bulk_allocate(fake_item, so, branch_code, year_code)
#                 continue

#             # ── Qty changed ───────────────────────────────────────────────
#             new_qty        = cint(new_row.rev_qty) if cint(new_row.rev_qty) \
#                              else cint(new_row.qty)
#             existing_count = _get_active_sn_count(so.name, so_line_idx)
#             delta          = new_qty - existing_count

#             if delta > 0:
#                 fake_item = _make_fake_item(
#                     new_row.item, delta, so_line_idx, new_row.batch_no)
#                 _bulk_allocate(fake_item, so, branch_code, year_code)

#             # elif delta < 0:
#                 # _cancel_lifo(so.name, so_line_idx, abs(delta),
#                 #              "Qty reduced via OMR")

#         frappe.db.commit()

#     except Exception:
#         frappe.log_error(frappe.get_traceback(),
#                          f"SN OMR Reconcile Failed: {omr_name}")
#         raise


# # ─────────────────────────────────────────────────────────────────────────────
# #  CORE: BULK ALLOCATE
# # ─────────────────────────────────────────────────────────────────────────────

# def _bulk_allocate(item, so_doc, branch_code, year_code):
#     """
#     Counter  : Serial Number Configuration Branches — sub_counter, total_counter
#     Series   : derived from total_counter // COUNTER_MAX (no extra field)
#     Lock     : FOR UPDATE on branch row
#     Output   : bulk insert into Serial Number DocType
#     Fields written: serial_number, batch, so_id, so_line,
#                     item_code, counter_value, status, generated_at
#     """
#     CHUNK_SIZE    = 25000
#     remaining_qty = cint(item.qty)
#     user          = frappe.session.user
#     values        = []

#     branch_row_name = _get_branch_row_name(branch_code)

#     while remaining_qty > 0:

#         # ── Lock branch row ───────────────────────────────────────────────
#         frappe.db.sql(
#             """SELECT name FROM `tabSerial Number Configuration Branches`
#                WHERE name = %s FOR UPDATE""",
#             (branch_row_name,)
#         )

#         # Re-read after lock acquired
#         branch_row = frappe.db.get_value(
#             "Serial Number Configuration Branches",
#             branch_row_name,
#             ["sub_counter", "total_counter"],
#             as_dict=True,
#         )

#         sub_counter   = cint(branch_row.sub_counter)
#         total_counter = cint(branch_row.total_counter)

#         # ── Derive series from total_counter — no field needed ────────────
#         # 0–9998      → index 0 → A  (sub 1–9999)
#         # 9999–19997  → index 1 → B  (sub 1–9999)
#         # 19998–29996 → index 2 → C
#         # 29997–39995 → index 3 → D
#         series_index = total_counter // COUNTER_MAX
#         if series_index >= len(SERIES_SEQUENCE):
#             frappe.throw(
#                 _(f"All series ({', '.join(SERIES_SEQUENCE)}) exhausted "
#                   f"for branch {branch_code}. Contact administrator.")
#             )
#         current_series = SERIES_SEQUENCE[series_index]

#         available = COUNTER_MAX - sub_counter
#         take      = min(remaining_qty, available)
#         start     = sub_counter + 1
#         now       = now_datetime()

#         for counter in range(start, start + take):
#             serial_number = (
#                 branch_code
#                 + year_code
#                 + current_series
#                 + _getseries(counter, COUNTER_PADDING)
#             )

#             values.append((
#                 serial_number,                           # name
#                 serial_number,                           # serial_number
#                 item.get("batch_no") or
#                 item.get("custom_batch_no") or "",       # batch
                                       
#                 total_counter + (counter - sub_counter), # counter_value
    
#             ))

#             if len(values) >= CHUNK_SIZE:
#                 _bulk_insert_sn_rows(values)
#                 frappe.db.commit()
#                 values = []

#         new_sub_counter   = sub_counter + take
#         new_total_counter = total_counter + take

#         # sub_counter resets to 0 when series boundary crossed
#         # total_counter keeps climbing — drives series_index on next call
#         if new_sub_counter >= COUNTER_MAX:
#             new_sub_counter = 0

#         frappe.db.set_value(
#             "Serial Number Configuration Branches",
#             branch_row_name,
#             {
#                 "sub_counter":   new_sub_counter,
#                 "total_counter": new_total_counter,
#             }
#         )
#         frappe.db.commit()   # releases FOR UPDATE lock

#         remaining_qty -= take

#     if values:
#         _bulk_insert_sn_rows(values)
#         frappe.db.commit()


# def _bulk_insert_sn_rows(values):
#     frappe.db.bulk_insert(
#         "Serial Number",
#         fields=[
#             "name", 
#             "serial_number", "batch",
#             "counter_value", 
#         ],
#         values=values,
#         ignore_duplicates=True,
#     )


# # ─────────────────────────────────────────────────────────────────────────────
# #  VALVE ITEM CHECK
# # ─────────────────────────────────────────────────────────────────────────────

# def _is_valve_item(item_code):
#     if not item_code:
#         return False
#     result = frappe.db.get_value(
#         "Item Generator",
#         {"created_item": item_code},
#         [ "attribute_1_value"],
#         as_dict=True,
#     )
#     if not result:
#         return False
    
    # val = (result.get("attribute_1_value") or "").strip()
	# if val == "Valve"
    # return bool(val) and val != "-"


# def _get_valve_lines(doc):
#     return [
#         item for item in doc.items
#         if _is_valve_item(item.item_code)
#     ]


# # ─────────────────────────────────────────────────────────────────────────────
# #  RECONCILE
# # ─────────────────────────────────────────────────────────────────────────────

# def _reconcile_so_lines(doc, branch_code, year_code, so_name):
#     for item in doc.items:
#         if not _is_valve_item(item.item_code):
#             continue

#         existing_count = _get_active_sn_count(so_name, item.idx)

#         if item.get("line_status") == "Cancelled":
#             # _cancel_sns_for_line(so_name, item.idx, "Line cancelled")
#             continue

#         delta = cint(item.qty) - existing_count

#         if delta > 0:
#             item.qty = delta
#             _bulk_allocate(item, doc, branch_code, year_code)

#         # elif delta < 0:
#         #     _cancel_lifo(so_name, item.idx, abs(delta), "Qty reduced")

#     # Cancel SNs for lines removed entirely from SO
#     current_line_idxs = {item.idx for item in doc.items}
#     orphan_lines = frappe.db.sql("""
#         SELECT DISTINCT so_line
#         FROM `tabSerial Number`
#         WHERE  AND status = 'Active'
#     """, (so_name,), as_dict=True)

#     # for row in orphan_lines:
#     #     if row.so_line not in current_line_idxs:
#     #         _cancel_sns_for_line(so_name, row.so_line,
#     #                              "Line removed from order")

#     frappe.db.commit()


# # ─────────────────────────────────────────────────────────────────────────────
# #  CANCEL HELPERS
# # ─────────────────────────────────────────────────────────────────────────────

# # def _cancel_sns_for_line(so_name, so_line, reason):
# #     sns = frappe.get_all(
# #         "Serial Number",
# #         filters={"so_id": so_name, "so_line": so_line, "status": "Active"},
# #         pluck="name",
# #     )
# #     for name in sns:
# #         _cancel_sn_row(name, reason)


# # def _cancel_lifo(so_name, so_line, count, reason):
# #     sns = frappe.get_all(
# #         "Serial Number",
# #         filters={"so_id": so_name, "so_line": so_line, "status": "Active"},
# #         fields=["name", "counter_value"],
# #         order_by="counter_value desc",
# #         limit=count,
# #     )
# #     for sn in sns:
# #         _cancel_sn_row(sn.name, reason)


# # def _cancel_sn_row(sn_name, reason):
# #     frappe.db.set_value("Serial Number", sn_name, {
# #         "status":        "Cancelled",
# #         "cancelled_at":  now_datetime(),
# #         "cancel_reason": reason,
# #     })


# # def _cancel_all_for_so(so_name, reason):
# #     sns = frappe.get_all(
# #         "Serial Number",
# #         filters={"so_id": so_name, "status": "Active"},
# #         pluck="name",
# #     )
# #     for name in sns:
# #         _cancel_sn_row(name, reason)
# #     if sns:
# #         frappe.db.commit()


# def _get_active_sn_count(so_name, so_line):
#     return frappe.db.count(
#         "Serial Number",
#         # filters={"so_id": so_name, "so_line": so_line, "status": "Active"},
#     )


# # ─────────────────────────────────────────────────────────────────────────────
# #  UTILITIES
# # ─────────────────────────────────────────────────────────────────────────────

# def _getseries(current, digits):
#     return ('%0' + str(digits) + 'd') % current


# def _get_branch_row_name(branch_code):
#     """
#     S → Sanand row name
#     N → Nandikoor row name
#     R → Rabale row name
#     Reads directly from DB — no config doc load needed.
#     """
#     rows = frappe.db.sql("""
#         SELECT name, branch
#         FROM `tabSerial Number Configuration Branches`
#         WHERE parent = 'Serial Number Configuration'
#     """, as_dict=True)

#     for row in rows:
#         if row.branch and row.branch[0].upper() == branch_code:
#             return row.name

#     frappe.throw(
#         _(f"No branch starting with '{branch_code}' found in "
#           f"Serial Number Configuration → Branches.")
#     )


# def _get_so_line_idx(so_item_name):
#     return cint(frappe.db.get_value(
#         "Sales Order Item", so_item_name, "idx"))


# def _make_fake_item(item_code, qty, idx, batch_no):
#     class _FakeItem:
#         pass
#     obj           = _FakeItem()
#     obj.item_code = item_code
#     obj.qty       = qty
#     obj.idx       = idx
#     obj.batch_no  = batch_no or ""
#     return obj