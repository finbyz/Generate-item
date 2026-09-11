# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt


def get_custom_item_attribute_doc(heading_names):
    """
    Find and return Custom Item Attribute document matching any of the given names or logic_headings.
    """
    if isinstance(heading_names, str):
        heading_names = [heading_names]

    for name in heading_names:
        if frappe.db.exists("Custom Item Attribute", name):
            try:
                return frappe.get_doc("Custom Item Attribute", name)
            except Exception:
                pass

    for name in heading_names:
        found = frappe.db.get_value("Custom Item Attribute", {"logic_heading": name}, "name")
        if found:
            try:
                return frappe.get_doc("Custom Item Attribute", found)
            except Exception:
                pass

    return None


def get_inch_factor_from_class(item_class, rating_doc=None):
    """
    Match item's Class/Rating in Custom Item Attribute 'FG-Rating' logic table
    using only item_long_description and return the corresponding value (Inches Factor).
    """
    if not item_class:
        return ""

    if not rating_doc:
        rating_doc = get_custom_item_attribute_doc(["FG-Rating", "FG Rating"])

    if not rating_doc:
        return ""

    target = str(item_class).strip().lower()

    for row in getattr(rating_doc, "logic_table", []):
        if getattr(row, "disabled", 0):
            continue
        long_desc = str(getattr(row, "item_long_description", "") or "").strip().lower()
        if long_desc == target:
            return getattr(row, "value", "") or ""

    return ""


def get_value_from_size(item_size, size_doc=None):
    """
    Match item's Size in Custom Item Attribute 'FG-Size' logic table
    using only item_long_description and return the corresponding value.
    """
    if not item_size:
        return ""

    if not size_doc:
        size_doc = get_custom_item_attribute_doc(["FG-Size", "FG Size"])

    if not size_doc:
        return ""

    target = str(item_size).strip().lower()

    for row in getattr(size_doc, "logic_table", []):
        if getattr(row, "disabled", 0):
            continue
        long_desc = str(getattr(row, "item_long_description", "") or "").strip().lower()
        if long_desc == target:
            return getattr(row, "value", "") or ""

    return ""


def calculate_inspector_inches(inch_factor, size_value):
    """
    Inspector Inches = Inches Factor x Value
    """
    if inch_factor is None or size_value is None or str(inch_factor).strip() == "" or str(size_value).strip() == "":
        return ""

    try:
        f = flt(inch_factor)
        v = flt(size_value)
        res = f * v
        if res == int(res):
            return str(int(res))
        else:
            return f"{res:g}"
    except Exception:
        return ""


@frappe.whitelist()
def get_inspector_inches(size=None, rating=None):
    """
    Whitelisted helper to calculate inspector inches given size and rating/class.
    """
    inch_factor = get_inch_factor_from_class(rating) if rating else ""
    size_value = get_value_from_size(size) if size else ""
    inches = calculate_inspector_inches(inch_factor, size_value)
    return {
        "inch_factor": str(inch_factor) if inch_factor is not None and str(inch_factor) != "" else "",
        "value": str(size_value) if size_value is not None and str(size_value) != "" else "",
        "inches": str(inches) if inches is not None and str(inches) != "" else "",
    }


def get_item_description(item_code, default=""):
    """
    Get description from Item or Item Generator.
    """
    if not item_code:
        return default

    item = frappe.db.get_value("Item", item_code, ["description", "item_name"], as_dict=True)
    if item:
        return item.description or item.item_name or default

    item_gen = frappe.db.get_value("Item Generator", item_code, ["description", "short_description"], as_dict=True)
    if item_gen:
        return item_gen.description or item_gen.short_description or default

    return default


def get_all_serials_testing_history(serial_numbers=None):
    """
    Returns a dict {serial_number: history_dict} for the given serial numbers (or all tested serials if None).
    """
    conditions = "WHERE vt.docstatus = 1 AND vti.serial_number IS NOT NULL AND vti.serial_number != ''"
    values = []
    if serial_numbers is not None:
        if not serial_numbers:
            return {}
        conditions += " AND vti.serial_number IN ({})".format(", ".join(["%s"] * len(serial_numbers)))
        values.extend(serial_numbers)

    rows = frappe.db.sql(f"""
        SELECT
            vti.serial_number,
            vt.testing_phase,
            vti.test_ok
        FROM `tabValve Testing Item` vti
        INNER JOIN `tabValve Testing` vt ON vt.name = vti.parent AND vti.parenttype = 'Valve Testing'
        {conditions}
    """, values, as_dict=True)

    history_map = {}
    for r in rows:
        sn = r.serial_number
        if sn not in history_map:
            history_map[sn] = {
                "has_pre_testing": False,
                "pre_accepted": False,
                "has_final_testing": False,
                "final_accepted": False,
                "has_tpi_testing": False,
                "tpi_accepted": False,
                "total_tests": 0,
            }
        hist = history_map[sn]
        hist["total_tests"] += 1
        if r.testing_phase == "Pre Testing":
            hist["has_pre_testing"] = True
            if r.test_ok == "Accepted":
                hist["pre_accepted"] = True
        elif r.testing_phase == "Final Testing":
            hist["has_final_testing"] = True
            if r.test_ok == "Accepted":
                hist["final_accepted"] = True
        elif r.testing_phase == "TPI Testing":
            hist["has_tpi_testing"] = True
            if r.test_ok == "Accepted":
                hist["tpi_accepted"] = True

    return history_map


def is_serial_eligible_for_phase(history, testing_phase):
    """
    Check if a serial number's testing history makes it eligible for the given testing_phase:
    1. Pre-Testing: Allowed if not previously accepted in Pre-Testing.
    2. Final Testing: Allowed for all serials regardless of Pre-Testing, unless already accepted in Final Testing.
    3. TPI Testing: Allowed only for serials accepted in Final Testing (and not already accepted in TPI Testing).
    """
    if not testing_phase:
        return True

    if testing_phase == "Pre Testing":
        if history and history.get("pre_accepted"):
            return False
        return True

    elif testing_phase == "Final Testing":
        if history and history.get("final_accepted"):
            return False
        return True

    elif testing_phase == "TPI Testing":
        if not history or not history.get("final_accepted"):
            return False
        if history.get("tpi_accepted"):
            return False
        return True

    return True


def validate_serial_for_testing_phase(serial_number, testing_phase):
    """
    Validates if a serial number can be used in the given testing_phase.
    Returns (is_valid: bool, error_message: str | None).
    """
    if not testing_phase or not serial_number:
        return True, None

    # Check stock entry link
    stock_entry = frappe.db.get_value("Serial Number", serial_number, "stock_entry")
    if stock_entry:
        return False, frappe._("Serial Number {0} is already linked to Stock Entry {1} and cannot be used in Valve Testing.").format(
            serial_number, stock_entry
        )

    history_map = get_all_serials_testing_history([serial_number])
    history = history_map.get(serial_number)

    if testing_phase == "Pre Testing":
        if history and history.get("pre_accepted"):
            return False, frappe._("Serial Number {0} was already Accepted in Pre Testing earlier and cannot be tested in Pre Testing again.").format(
                serial_number
            )

    elif testing_phase == "Final Testing":
        if history and history.get("final_accepted"):
            return False, frappe._("Serial Number {0} was already Accepted in Final Testing earlier and cannot be tested in Final Testing again.").format(
                serial_number
            )

    elif testing_phase == "TPI Testing":
        if not history or not history.get("final_accepted"):
            return False, frappe._("Serial Number {0} has not been Accepted in Final Testing. Only Serial Numbers that have passed Final Testing are eligible for TPI Testing.").format(
                serial_number
            )
        if history.get("tpi_accepted"):
            return False, frappe._("Serial Number {0} was already Accepted in TPI Testing earlier.").format(
                serial_number
            )

    return True, None


@frappe.whitelist()
def get_valve_testing_serial_query(doctype, txt, searchfield, start, page_len, filters):
    """
    Custom query for serial_number Link field in Valve Testing child table and dialog.
    Filters by branch, sales_order, batch, stock_entry is not set, and testing_phase eligibility.
    """
    filters = filters or {}
    branch = filters.get("branch")
    testing_phase = filters.get("testing_phase")
    batch = filters.get("batch")
    sales_order = filters.get("sales_order")

    conditions = ["docstatus = 1", "(stock_entry IS NULL OR stock_entry = '')"]
    values = {}

    if branch:
        conditions.append("branch = %(branch)s")
        values["branch"] = branch

    if batch:
        conditions.append("batch = %(batch)s")
        values["batch"] = batch
    elif sales_order:
        batch_names = frappe.get_all("Batch", filters={"reference_name": sales_order}, pluck="name")
        if not batch_names:
            return []
        batch_placeholders = ", ".join([f"%(so_batch_{i})s" for i in range(len(batch_names))])
        conditions.append(f"batch IN ({batch_placeholders})")
        for i, b in enumerate(batch_names):
            values[f"so_batch_{i}"] = b

    if txt:
        conditions.append("(name LIKE %(txt)s OR batch LIKE %(txt)s)")
        values["txt"] = f"%{txt}%"

    cond_str = " AND ".join(conditions)

    candidates = frappe.db.sql(f"""
        SELECT name, batch
        FROM `tabSerial Number`
        WHERE {cond_str}
        ORDER BY creation DESC
    """, values, as_dict=True)

    if not candidates:
        return []

    if testing_phase:
        candidate_names = [c.name for c in candidates]
        history_map = get_all_serials_testing_history(candidate_names)
        eligible = []
        for c in candidates:
            hist = history_map.get(c.name)
            if is_serial_eligible_for_phase(hist, testing_phase):
                eligible.append(c)
        candidates = eligible

    start = int(start or 0)
    page_len = int(page_len or 20)
    paged = candidates[start : start + page_len]

    return [[c.name, c.batch or ""] for c in paged]


@frappe.whitelist()
def get_serial_register_items(doctype="Valve Testing", sales_order=None, batch_number=None, serial_number=None, branch=None, testing_phase=None):
    """
    Get Serial Number records from Serial Number DocType with item description.
    Excludes serial numbers already used or ineligible based on testing phase.
    """
    filters = {"docstatus": 1}
    if branch:
        filters["branch"] = branch

    if doctype in ["Valve Testing"]:
        filters["stock_entry"] = ["is", "not set"]

    batch_info_map = {}

    # Case 1: Serial Number is specified
    if serial_number:
        filters["name"] = serial_number
        if batch_number:
            filters["batch"] = batch_number
        elif sales_order:
            batches = frappe.get_all(
                "Batch",
                filters={"reference_name": sales_order},
                fields=["name", "item", "reference_name"],
            )
            if not batches:
                return []
            batch_info_map = {
                b.name: {"item": b.item, "sales_order": b.reference_name}
                for b in batches
            }
            filters["batch"] = ["in", list(batch_info_map.keys())]

    # Case 2: Batch is selected (no serial_number)
    elif batch_number:
        filters["batch"] = batch_number

    # Case 3: Sales Order selected but Batch is not selected
    elif sales_order:
        batches = frappe.get_all(
            "Batch",
            filters={"reference_name": sales_order},
            fields=["name", "item", "reference_name"],
        )

        if not batches:
            return []

        batch_info_map = {
            b.name: {"item": b.item, "sales_order": b.reference_name}
            for b in batches
        }
        filters["batch"] = ["in", list(batch_info_map.keys())]

    # Exclude already used serials for Valve Assembly
    if doctype not in ["Valve Testing"]:
        child_doctype = "Assembly Item Serial No"
        used_serials = frappe.get_all(
            child_doctype,
            filters={
                "docstatus": 1,
                "parenttype": "Valve Assembly",
            },
            pluck="serial_number",
        )
        if used_serials:
            if serial_number:
                if serial_number in used_serials:
                    return []
            else:
                filters["name"] = ["not in", list(set(used_serials))]

    # Get Serial Number records
    serial_numbers = frappe.get_all(
        "Serial Number",
        filters=filters,
        fields=[
            "batch",
            "name as serial_number",
        ],
        order_by="creation asc",
    )

    # For Valve Testing, filter by testing_phase eligibility
    if doctype in ["Valve Testing"] and serial_numbers:
        candidate_names = [s.serial_number for s in serial_numbers]
        history_map = get_all_serials_testing_history(candidate_names)
        serial_numbers = [
            s for s in serial_numbers
            if is_serial_eligible_for_phase(history_map.get(s.serial_number), testing_phase)
        ]

    if not serial_numbers:
        return []

    # Attach item_code and sales_order from Batch
    if not batch_info_map:
        involved_batches = list({s.batch for s in serial_numbers if s.batch})
        if involved_batches:
            batch_info_map = {
                b.name: {"item": b.item, "reference_name": b.reference_name}
                for b in frappe.get_all(
                    "Batch",
                    filters={"name": ["in", involved_batches]},
                    fields=["name", "item", "reference_name"],
                )
            }

    # Fetch Item descriptions in bulk
    all_item_codes = set()
    for s in serial_numbers:
        info = batch_info_map.get(s.batch, {})
        s["item_code"] = info.get("item")
        s["sales_order"] = info.get("sales_order") if "sales_order" in info else info.get("reference_name")
        if s.get("item_code"):
            all_item_codes.add(s["item_code"])

    item_desc_map = {}
    if all_item_codes:
        items_data = frappe.get_all(
            "Item",
            filters={"name": ["in", list(all_item_codes)]},
            fields=["name", "description", "item_name"],
        )
        for itm in items_data:
            item_desc_map[itm.name] = itm.description or itm.item_name or ""

    for s in serial_numbers:
        s["item_description"] = item_desc_map.get(s.get("item_code"), "")

    return serial_numbers


def calculate_doc_inspector_inches(doc):
    """
    Ensure all rows in doc.item_serial_number have inch_factor, value, and inches populated.
    """
    if not getattr(doc, "item_serial_number", None):
        return

    rating_doc = get_custom_item_attribute_doc(["FG-Rating", "FG Rating"])
    size_doc = get_custom_item_attribute_doc(["FG-Size", "FG Size"])

    for row in doc.item_serial_number:
        if not getattr(row, "inch_factor", None) and getattr(row, "class", None):
            row.inch_factor = str(get_inch_factor_from_class(getattr(row, "class"), rating_doc) or "")
        if not getattr(row, "value", None) and getattr(row, "size", None):
            row.value = str(get_value_from_size(getattr(row, "size"), size_doc) or "")
        if (getattr(row, "inch_factor", None) or getattr(row, "value", None)) and not getattr(row, "inches", None):
            row.inches = str(calculate_inspector_inches(row.inch_factor, row.value) or "")
