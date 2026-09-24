# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, nowdate, date_diff
from frappe.model.document import Document
from generate_item.utils.inspector_inches import (
    calculate_doc_inspector_inches,
    get_serial_register_items as _get_serial_register_items,
)
from generate_item.utils.naming_series import revert_series_on_trash


# ── DocType class ─────────────────────────────────────────────────────────────

class ValvePainting(Document):

    def validate(self):
        self.validate_line_items()
        self.validate_dates()
        if self.type == "Finished":
            self.validate_finished_serial_numbers()

    def validate_line_items(self):
        if not self.item_serial_number:
            frappe.throw(
                frappe._("Please add at least one item in the <b>Item Serial Number</b> table before saving.")
            )

    def validate_dates(self):
        today = getdate(nowdate())

        if self.posting_date:
            posting = getdate(self.posting_date)
            diff = date_diff(today, posting)
            if diff < 0:
                frappe.throw(
                    frappe._("{0} cannot be a future date.").format(frappe.bold("Posting Date")),
                    title=frappe._("Invalid Date")
                )
            elif diff > 0 and not self.allow_back_date:
                frappe.throw(
                    frappe._("{0} cannot be set to a past date unless {1} is enabled.").format(
                        frappe.bold("Posting Date"), frappe.bold("Allow Back Date")
                    ),
                    title=frappe._("Back-Dating Not Allowed")
                )

        for row in getattr(self, "item_serial_number", []):
            if getattr(row, "date", None):
                row_date = getdate(row.date)
                diff = date_diff(today, row_date)
                if diff < 0:
                    frappe.throw(
                        frappe._("Row #{0}: {1} cannot be a future date.").format(
                            row.idx, frappe.bold("Date")
                        ),
                        title=frappe._("Invalid Date")
                    )
                elif diff > 0 and not self.allow_back_date:
                    frappe.throw(
                        frappe._("Row #{0}: {1} cannot be set to a past date unless {2} is enabled.").format(
                            row.idx, frappe.bold("Date"), frappe.bold("Allow Back Date")
                        ),
                        title=frappe._("Back-Dating Not Allowed")
                    )

    def validate_finished_serial_numbers(self):
        """
        Validations for Type = Finished:
        1. Duplicate serial numbers within document.
        2. Every serial number must exist in a submitted Valve Painting with Type = 'Received'.
        3. Serial number must not have been already processed in another Finished Valve Painting.
        """
        rows = [r for r in getattr(self, "item_serial_number", []) if (getattr(r, "serial_number", None) or "").strip()]
        if not rows:
            return

        sns = [r.serial_number.strip() for r in rows]

        # 1. Duplicate check within document
        seen = set()
        duplicates = set()
        for sn in sns:
            if sn in seen:
                duplicates.add(sn)
            else:
                seen.add(sn)

        if duplicates:
            frappe.throw(
                frappe._("Duplicate Serial Numbers found in this document:<br><br><b>{0}</b>").format(
                    "<br>".join(sorted(duplicates))
                ),
                title=frappe._("Duplicate Serial Numbers")
            )

        # 2. Must exist in a submitted Valve Painting with Type = 'Received'
        branch_cond = "AND vp.branch = %(branch)s" if self.branch else ""
        received_sns = set(frappe.db.sql_list(f"""
            SELECT DISTINCT vpi.serial_number
            FROM `tabValve Painting Item` vpi
            JOIN `tabValve Painting` vp ON vp.name = vpi.parent
            WHERE vp.type = 'Received'
              AND vp.docstatus = 1
              {branch_cond}
              AND vpi.serial_number IN %(sns)s
        """, {"sns": tuple(sns), "branch": self.branch}))

        invalid_sns = [sn for sn in sns if sn not in received_sns]
        if invalid_sns:
            branch_msg = f" for branch <b>{self.branch}</b>" if self.branch else ""
            frappe.throw(
                frappe._("The following Serial Numbers were not found in any submitted <b>Valve Painting (Type = Received)</b>{0}:<br><br><b>{1}</b>").format(
                    branch_msg,
                    "<br>".join(invalid_sns)
                ),
                title=frappe._("Invalid Serial Numbers")
            )

        # 3. Must not already exist in another Finished Valve Painting (docstatus 0 or 1)
        already_finished = frappe.db.sql("""
            SELECT vpi.serial_number, vp.name
            FROM `tabValve Painting Item` vpi
            JOIN `tabValve Painting` vp ON vp.name = vpi.parent
            WHERE vp.type = 'Finished'
              AND vp.docstatus IN (0, 1)
              AND vp.name != %(current_name)s
              AND vpi.serial_number IN %(sns)s
        """, {"sns": tuple(sns), "current_name": self.name or ""}, as_dict=True)

        if already_finished:
            lines = [f"{r.serial_number} (already in <b>{r.name}</b>)" for r in already_finished]
            frappe.throw(
                frappe._("The following Serial Numbers are already processed in another <b>Finished Valve Painting</b> document:<br><br>{0}").format(
                    "<br>".join(lines)
                ),
                title=frappe._("Serial Numbers Already Finished")
            )

    def before_save(self):
        calculate_doc_inspector_inches(self)

    def on_trash(self):
        revert_series_on_trash(self)


# ── Whitelisted APIs ──────────────────────────────────────────────────────────

@frappe.whitelist()
def get_serial_register_items(sales_order=None, batch_number=None, serial_number=None, branch=None):
    """
    Get Serial Number records from Serial Number DocType for Valve Painting (Type = Received).
    """
    return _get_serial_register_items(
        doctype="Valve Painting",
        sales_order=sales_order,
        batch_number=batch_number,
        serial_number=serial_number,
        branch=branch,
    )


@frappe.whitelist()
def get_received_painting_items(sales_order=None, batch_number=None, serial_number=None, branch=None, current_doc=None):
    """
    Get Serial Number records that were received via submitted Valve Painting (Type = 'Received')
    and have not yet been processed in a Finished Valve Painting.
    """
    filters = [
        "vp.type = 'Received'",
        "vp.docstatus = 1",
        "vpi.serial_number IS NOT NULL",
        "vpi.serial_number != ''",
    ]
    values = {}

    if branch:
        filters.append("vp.branch = %(branch)s")
        values["branch"] = branch

    if sales_order:
        filters.append("vpi.sales_order = %(sales_order)s")
        values["sales_order"] = sales_order

    if batch_number:
        filters.append("vpi.batch_no = %(batch_number)s")
        values["batch_number"] = batch_number

    if serial_number:
        filters.append("vpi.serial_number = %(serial_number)s")
        values["serial_number"] = serial_number

    finished_cond = "AND vpf.docstatus IN (0, 1)"
    if current_doc:
        finished_cond += " AND vpf.name != %(current_doc)s"
        values["current_doc"] = current_doc

    where_clause = " AND ".join(filters)

    items = frappe.db.sql(f"""
        SELECT DISTINCT
            vpi.serial_number,
            vpi.batch_no AS batch,
            vpi.item_code,
            vpi.sales_order
        FROM `tabValve Painting Item` vpi
        JOIN `tabValve Painting` vp ON vp.name = vpi.parent
        WHERE {where_clause}
          AND vpi.serial_number NOT IN (
              SELECT DISTINCT vpi_fin.serial_number
              FROM `tabValve Painting Item` vpi_fin
              JOIN `tabValve Painting` vpf ON vpf.name = vpi_fin.parent
              WHERE vpf.type = 'Finished' {finished_cond}
                AND vpi_fin.serial_number IS NOT NULL
                AND vpi_fin.serial_number != ''
          )
        ORDER BY vpi.serial_number ASC
    """, values, as_dict=True)

    if not items:
        return []

    all_item_codes = {item.get("item_code") for item in items if item.get("item_code")}
    item_desc_map = {}
    if all_item_codes:
        items_data = frappe.get_all(
            "Item",
            filters={"name": ["in", list(all_item_codes)]},
            fields=["name", "description", "item_name"],
        )
        for itm in items_data:
            item_desc_map[itm.name] = itm.description or itm.item_name or ""

    for item in items:
        item["item_description"] = item_desc_map.get(item.get("item_code"), "")

    return items


@frappe.whitelist()
def received_serial_number_query(doctype, txt, searchfield, start, page_len, filters):
    """
    Query serial numbers received in submitted Valve Painting (Type = 'Received')
    excluding those already processed in Finished Valve Painting.
    """
    if isinstance(filters, str):
        filters = frappe.parse_json(filters)
    filters = filters or {}
    branch = filters.get("branch")
    sales_order = filters.get("sales_order")
    batch_number = filters.get("batch_number")
    current_doc = filters.get("current_doc")

    where_clauses = [
        "vp.type = 'Received'",
        "vp.docstatus = 1",
        "vpi.serial_number IS NOT NULL",
        "vpi.serial_number != ''",
        "vpi.serial_number LIKE %(txt)s",
    ]
    values = {
        "txt": f"%{txt}%",
        "start": int(start or 0),
        "page_len": int(page_len or 20),
    }

    if branch:
        where_clauses.append("vp.branch = %(branch)s")
        values["branch"] = branch
    if sales_order:
        where_clauses.append("vpi.sales_order = %(sales_order)s")
        values["sales_order"] = sales_order
    if batch_number:
        where_clauses.append("vpi.batch_no = %(batch_number)s")
        values["batch_number"] = batch_number

    finished_cond = "AND vpf.docstatus IN (0, 1)"
    if current_doc:
        finished_cond += " AND vpf.name != %(current_doc)s"
        values["current_doc"] = current_doc

    where_sql = " AND ".join(where_clauses)

    return frappe.db.sql(f"""
        SELECT DISTINCT vpi.serial_number, vpi.batch_no
        FROM `tabValve Painting Item` vpi
        JOIN `tabValve Painting` vp ON vp.name = vpi.parent
        WHERE {where_sql}
          AND vpi.serial_number NOT IN (
              SELECT DISTINCT vpi_fin.serial_number
              FROM `tabValve Painting Item` vpi_fin
              JOIN `tabValve Painting` vpf ON vpf.name = vpi_fin.parent
              WHERE vpf.type = 'Finished' {finished_cond}
                AND vpi_fin.serial_number IS NOT NULL
                AND vpi_fin.serial_number != ''
          )
        ORDER BY vpi.serial_number ASC
        LIMIT %(page_len)s OFFSET %(start)s
    """, values)


@frappe.whitelist()
def received_batch_query(doctype, txt, searchfield, start, page_len, filters):
    """
    Query batches received in submitted Valve Painting (Type = 'Received')
    excluding those where all serial numbers are already Finished.
    """
    if isinstance(filters, str):
        filters = frappe.parse_json(filters)
    filters = filters or {}
    branch = filters.get("branch")
    sales_order = filters.get("sales_order")
    current_doc = filters.get("current_doc")

    where_clauses = [
        "vp.type = 'Received'",
        "vp.docstatus = 1",
        "vpi.batch_no IS NOT NULL",
        "vpi.batch_no != ''",
        "vpi.batch_no LIKE %(txt)s",
    ]
    values = {
        "txt": f"%{txt}%",
        "start": int(start or 0),
        "page_len": int(page_len or 20),
    }

    if branch:
        where_clauses.append("vp.branch = %(branch)s")
        values["branch"] = branch
    if sales_order:
        where_clauses.append("vpi.sales_order = %(sales_order)s")
        values["sales_order"] = sales_order

    finished_cond = "AND vpf.docstatus IN (0, 1)"
    if current_doc:
        finished_cond += " AND vpf.name != %(current_doc)s"
        values["current_doc"] = current_doc

    where_sql = " AND ".join(where_clauses)

    return frappe.db.sql(f"""
        SELECT DISTINCT vpi.batch_no, vpi.sales_order
        FROM `tabValve Painting Item` vpi
        JOIN `tabValve Painting` vp ON vp.name = vpi.parent
        WHERE {where_sql}
          AND vpi.serial_number NOT IN (
              SELECT DISTINCT vpi_fin.serial_number
              FROM `tabValve Painting Item` vpi_fin
              JOIN `tabValve Painting` vpf ON vpf.name = vpi_fin.parent
              WHERE vpf.type = 'Finished' {finished_cond}
                AND vpi_fin.serial_number IS NOT NULL
                AND vpi_fin.serial_number != ''
          )
        ORDER BY vpi.batch_no ASC
        LIMIT %(page_len)s OFFSET %(start)s
    """, values)


@frappe.whitelist()
def received_sales_order_query(doctype, txt, searchfield, start, page_len, filters):
    """
    Query Sales Orders received in submitted Valve Painting (Type = 'Received')
    excluding those where all serial numbers are already Finished.
    """
    if isinstance(filters, str):
        filters = frappe.parse_json(filters)
    filters = filters or {}
    branch = filters.get("branch")
    current_doc = filters.get("current_doc")

    where_clauses = [
        "vp.type = 'Received'",
        "vp.docstatus = 1",
        "vpi.sales_order IS NOT NULL",
        "vpi.sales_order != ''",
        "vpi.sales_order LIKE %(txt)s",
    ]
    values = {
        "txt": f"%{txt}%",
        "start": int(start or 0),
        "page_len": int(page_len or 20),
    }

    if branch:
        where_clauses.append("vp.branch = %(branch)s")
        values["branch"] = branch

    finished_cond = "AND vpf.docstatus IN (0, 1)"
    if current_doc:
        finished_cond += " AND vpf.name != %(current_doc)s"
        values["current_doc"] = current_doc

    where_sql = " AND ".join(where_clauses)

    return frappe.db.sql(f"""
        SELECT DISTINCT vpi.sales_order
        FROM `tabValve Painting Item` vpi
        JOIN `tabValve Painting` vp ON vp.name = vpi.parent
        WHERE {where_sql}
          AND vpi.serial_number NOT IN (
              SELECT DISTINCT vpi_fin.serial_number
              FROM `tabValve Painting Item` vpi_fin
              JOIN `tabValve Painting` vpf ON vpf.name = vpi_fin.parent
              WHERE vpf.type = 'Finished' {finished_cond}
                AND vpi_fin.serial_number IS NOT NULL
                AND vpi_fin.serial_number != ''
          )
        ORDER BY vpi.sales_order ASC
        LIMIT %(page_len)s OFFSET %(start)s
    """, values)
