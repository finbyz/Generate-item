
# JOIN MAP
#   soi  tabSales Order Item        ← spine
#   so   tabSales Order             INNER JOIN  soi.parent = so.name
#   sn   tabSerial Number           LEFT JOIN   sn.batch = soi.custom_batch_no
#                                               ORDER BY sn.name LIMIT 1 (correlated)
#   bom  tabBOM                     LEFT JOIN   latest active BOM per item_code
#   sca  tabState Change Items      correlated  → SO Approved timestamp
# =============================================================================

import frappe
from frappe import _
from frappe.utils import getdate,now_datetime, date_diff, today as get_today
import json



# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

def execute(filters=None):
    filters  = frappe._dict(filters or {})
    columns  = get_columns()
    data     = get_data(filters)
    return columns, data


# ---------------------------------------------------------------------------
# COLUMNS
# ---------------------------------------------------------------------------

def get_columns():
    """
    Each dict may carry two extra keys (not standard Frappe but consumed by JS):
      editable : 1  → JS will render an inline editor
      sn_field : 1  → this column maps to tabSerial Number (used by update API)
    """
    return [
        # ─── IDENTIFIERS (hidden) ────────────────────────────────────────────
        {"fieldname": "soi_name",  "label": _("SOI Name"),  "fieldtype": "Data", "width": 0, "hidden": 1},
        {"fieldname": "sn_name",   "label": _("SN Name"),   "fieldtype": "Data", "width": 0, "hidden": 1},
        {"fieldname": "batch_key", "label": _("Batch Key"), "fieldtype": "Data", "width": 0, "hidden": 1},

        # ─── A : Batch / SO Line ─────────────────────────────────────────────
        {"fieldname": "batch_no",       "label": _("Batch No"), "fieldtype": "Link",  "options": "Batch",        "width": 160},
        {"fieldname": "sales_order",    "label": _("Sales Order"),        "fieldtype": "Link",  "options": "Sales Order",  "width": 150},
        {"fieldname": "order_status",   "label": _("Order Status"),       "fieldtype": "Data",  "width": 130},
        {"fieldname": "so_line_status", "label": _("SO Line Status"),     "fieldtype": "Data",  "width": 110},
        {"fieldname": "customer_name",  "label": _("Customer Name"),      "fieldtype": "Data",  "width": 200},

        # ─── F–Q : Serial Number editable ────────────────────────────────────
        {"fieldname": "mds_status",    "label": _("MDS Status"),   "fieldtype": "Select", "options": "\nYES\nNO\nNA",         "width": 100, "editable": 1, "sn_field": 1},
        {"fieldname": "mds_no",        "label": _("MDS No."),      "fieldtype": "Data",                                       "width": 120, "editable": 1, "sn_field": 1},
        {"fieldname": "mds_rev",       "label": _("MDS Rev."),     "fieldtype": "Select", "options": "\nNA\n00\n01\n02\n03\n04\n05\n06", "width": 90,  "editable": 1, "sn_field": 1},
        {"fieldname": "mds_date",      "label": _("MDS Date"),     "fieldtype": "Date",                                       "width": 110, "editable": 1, "sn_field": 1},
        {"fieldname": "gad_required",  "label": _("GAD Required"), "fieldtype": "Select", "options": "\nYES\nNO\nNA",         "width": 110, "editable": 1, "sn_field": 1},
        {"fieldname": "gad_status",    "label": _("GAD Status"),   "fieldtype": "Select", "options": "\nSSV STD GAD\nNO\nNA\nApproved\nSubmitted\nInprocess", "width": 130, "editable": 1, "sn_field": 1},
        {"fieldname": "gad_rev",       "label": _("GAD Rev."),     "fieldtype": "Select", "options": "\n00\n01\n02\n03\n04\n05\n06\nNO", "width": 90, "editable": 1, "sn_field": 1},
        {"fieldname": "gad_receive_date",                   "label": _("GAD Receive Date"),                   "fieldtype": "Date",   "width": 130, "editable": 1, "sn_field": 1},
        {"fieldname": "after_gad_change_bom_change_required","label": _("AFTER GAD CHANGE BOM CHANGE REQUIRED"),      "fieldtype": "Select", "options": "\nYES\nNO",        "width": 230, "editable": 1, "sn_field": 1},
        {"fieldname": "itpqap",                             "label": _("ITP/QAP"),                            "fieldtype": "Select", "options": "\nYES\nNO",        "width": 90,  "editable": 1, "sn_field": 1},
        {"fieldname": "itpqap_rev",                         "label": _("ITP/QAP Rev."),                       "fieldtype": "Select", "options": "\n00\n01\n02\n03\n04\n05\n06", "width": 100, "editable": 1, "sn_field": 1},
        {"fieldname": "itpqap_receive_date",                "label": _("ITP/QAP Receive Date"),               "fieldtype": "Date",   "width": 150, "editable": 1, "sn_field": 1},

        # ─── R–T : SO Item read-only ──────────────────────────────────────────
        {"fieldname": "item_code",       "label": _("Item Code"),       "fieldtype": "Link", "options": "Item", "width": 180},
        {"fieldname": "main_description","label": _("Main Description"),"fieldtype": "Small Text",              "width": 300},
        {"fieldname": "valve_qty",       "label": _("Valve Qty"),       "fieldtype": "Int",                     "width": 80},

        # ─── U : Mfg Type ─────────────────────────────────────────────────────
        {"fieldname": "mfg_type", "label": _("Mfg Type"), "fieldtype": "Select", "options": "\nIN-HOUSE\nOUTSOURCE", "width": 120,  "sn_field": 1},

        # ─── V : BOM status ───────────────────────────────────────────────────
        {"fieldname": "bom_status", "label": _("BOM Status"), "fieldtype": "Data", "width": 110},

        # ─── W–X ──────────────────────────────────────────────────────────────
        {"fieldname": "after_gad_change_bom_update_or_not", "label": _("AFTER GAD CHANGE BOM Update or NOT"), "fieldtype": "Select", "options": "\nUpdated\nNot Updated", "width": 210, "editable": 1, "sn_field": 1},
        {"fieldname": "after_gad_rev_bom_released",         "label": _("After GAD Rev – BOM Released"), "fieldtype": "Data", "width": 190},

        # ─── Y–AB : dates ─────────────────────────────────────────────────────
        {"fieldname": "so_approved_date",   "label": _("SO Approved Date"),    "fieldtype": "Datetime", "width": 160},
        {"fieldname": "bom_released_date",  "label": _("BOM Released Date"),   "fieldtype": "Date",     "width": 140},
        {"fieldname": "so_amendment_date",  "label": _("SO Amendment Date"),   "fieldtype": "Date",     "width": 150},
        {"fieldname": "bom_amendment_date", "label": _("BOM Amendment Date"),  "fieldtype": "Date",     "width": 150},

        # ─── AC–AD : computed delay ───────────────────────────────────────────
        {"fieldname": "bom_delay_days",  "label": _("BOM Delay Days"),  "fieldtype": "Data",  "width": 120},
        {"fieldname": "bom_delay_weeks", "label": _("BOM Delay Weeks"), "fieldtype": "Data", "width": 130},

        # ─── AE–AH : SN editable ─────────────────────────────────────────────
        {"fieldname": "design_remarks",          "label": _("Design Remarks"),         "fieldtype": "Small Text", "width": 180, "editable": 1, "sn_field": 1},
        {"fieldname": "pattern_status",          "label": _("Pattern Status"),         "fieldtype": "Select", "options": "\nAvailable\nNew Development",           "width": 150, "editable": 1, "sn_field": 1},
        {"fieldname": "advance_action_casting",  "label": _("Advance Action Casting"), "fieldtype": "Select", "options": "\nYES\nNO",                               "width": 160, "editable": 1, "sn_field": 1},
        {"fieldname": "advance_action_trim",     "label": _("Advance Action Trim"),    "fieldtype": "Select", "options": "\nYES\nNO",                               "width": 150, "editable": 1, "sn_field": 1},

        # ─── AI : BOM owner (read-only) ───────────────────────────────────────
        {"fieldname": "erp_bom_created_by", "label": _("ERP BOM Created By"), "fieldtype": "Data", "width": 150},

        # ─── AJ–AM : SN editable ─────────────────────────────────────────────
        {"fieldname": "engg_bom_created_by",              "label": _("Engg. BOM Created By"),           "fieldtype": "Data",       "width": 160, "editable": 1, "sn_field": 1},
        {"fieldname": "release_date_expected",            "label": _("Release Date (Expected)"),        "fieldtype": "Date",       "width": 160, "editable": 1, "sn_field": 1},
        {"fieldname": "expected_based_delay_days",        "label": _("Expected Based Delay Days"),      "fieldtype": "Data",       "width": 180},
        {"fieldname": "expected_based_delay_week",        "label": _("Expected Based Delay Week"),      "fieldtype": "Data", "width": 180, },
        {"fieldname": "bom_released_in_which_gad_revision","label": _("BOM Released In Which GAD Rev."),"fieldtype": "Select", "options": "\n00\n01\n02\n03\n04\n05\n06", "width": 220, "editable": 1, "sn_field": 1},
        {"fieldname": "other_remarks",   "label": _("Other Remarks"),   "fieldtype": "Small Text", "width": 180, "editable": 1, "sn_field": 1},
        {"fieldname": "reason_for_delay","label": _("Reason For Delay"),"fieldtype": "Small Text", "width": 180, "editable": 1, "sn_field": 1},
    ]


# ---------------------------------------------------------------------------
# DATA FETCH
# ---------------------------------------------------------------------------

def get_data(filters):
    raw  = _fetch_rows(filters)
    return _post_process(raw)


# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------

def _fetch_rows(filters):
    conditions, values = _build_conditions(filters)

    # The representative-SN sub-query picks the FIRST (oldest) SN per batch.
    # All SNs in a batch are kept in sync by the bulk-update API, so the
    # first SN always reflects the canonical field values for the entire batch.

    sql = f"""
        SELECT
            /*── Hidden keys ──────────────────────────────────────────────────*/
            soi.name                                            AS soi_name,
            rep_sn.sn_name                                      AS sn_name,
            soi.custom_batch_no                                 AS batch_key,

            /*── A-E : SO + SO Item ───────────────────────────────────────────*/
            soi.custom_batch_no                                 AS batch_no,
            so.name                                             AS sales_order,
            so.status                                           AS order_status,
            soi.line_status                                     AS so_line_status,
            so.customer_name,

            /*── F-Q : Serial Number editable fields ──────────────────────────*/
            rep_sn.mds_status,
            rep_sn.mds_no,
            rep_sn.mds_rev,
            rep_sn.mds_date,
            rep_sn.gad_required,
            rep_sn.gad_status,
            rep_sn.gad_rev,
            rep_sn.gad_receive_date,
            rep_sn.after_gad_change_bom_change_required,
            rep_sn.itpqap,
            rep_sn.itpqap_rev,
            rep_sn.itpqap_receive_date,

            /*── R-T : SO Item ────────────────────────────────────────────────*/
            soi.item_code,
            soi.description                                     AS main_description,
            soi.qty                                             AS valve_qty,

            /*── U : Mfg Type ─────────────────────────────────────────────────*/
            rep_sn.mfg_type,

            /*── V : BOM ──────────────────────────────────────────────────────*/
            # bom.status                                          AS bom_status,

            /*── W : After-GAD BOM update flag ───────────────────────────────*/
            rep_sn.after_gad_change_bom_update_or_not,

            /*── Y : SO Approved timestamp via State Change Items ─────────────*/
            (
                SELECT sc.modification_time
                FROM   `tabState Change Items` sc
                WHERE  sc.parent         = so.name
                  AND  sc.workflow_state = 'Approved'
                ORDER  BY sc.modification_time DESC
                LIMIT  1
            )                                                   AS so_approved_date,

            /*── Z : BOM Released Date ────────────────────────────────────────*/
            CASE
                WHEN bom.docstatus = 1 THEN DATE(bom.creation)
                ELSE NULL
            END                                                 AS bom_released_date,

            /*── AA : SO Amendment Date ───────────────────────────────────────*/
        
            so.rev_date as so_amendment_date,

            /*── AB : BOM Amendment Date ──────────────────────────────────────*/
    

            (
                SELECT MAX(bi.rev_date) 
                FROM `tabBOM Item` bi 
                WHERE bi.parent = bom.name
            )  as bom_amendment_date,
            



            /*── AI : ERP BOM owner ───────────────────────────────────────────*/
            bom.owner                                           AS erp_bom_created_by,
            /*── V : BOM ──────────────────────────────────────────────────────*/
            bom.name                                            AS bom_id,
            bom.docstatus                                       AS bom_docstatus,

            /*── AJ-AP : more SN editable fields ─────────────────────────────*/
            rep_sn.engg_bom_created_by,
            rep_sn.release_date_expected,
            # rep_sn.expected_based_delay_week,
            rep_sn.bom_released_in_which_gad_revision,
            rep_sn.design_remarks,
            rep_sn.pattern_status,
            rep_sn.advance_action_casting,
            rep_sn.advance_action_trim,
            rep_sn.other_remarks,
            rep_sn.reason_for_delay

        FROM `tabSales Order Item` soi

        /*── Sales Order ──────────────────────────────────────────────────────*/
        INNER JOIN `tabSales Order` so
               ON  so.name      = soi.parent
               AND so.docstatus = 1

        /*── Representative Serial Number
             We use a derived table that picks the FIRST SN per batch
             (ORDER BY name ASC).  This is a single indexed scan per batch
             and avoids 5 000-row fan-out in the join.                        */
        LEFT JOIN (
            SELECT
                sn.batch,
                sn.name                                         AS sn_name,
                sn.mds_status,
                sn.mds_no,
                sn.mds_rev,
                sn.mds_date,
                sn.gad_required,
                sn.gad_status,
                sn.gad_rev,
                sn.gad_receive_date,
                sn.after_gad_change_bom_change_required,
                sn.itpqap,
                sn.itpqap_rev,
                sn.itpqap_receive_date,
                sn.mfg_type,
                sn.after_gad_change_bom_update_or_not,
                sn.engg_bom_created_by,
                sn.release_date_expected,
                # sn.expected_based_delay_week,
                sn.bom_released_in_which_gad_revision,
                sn.design_remarks,
                sn.pattern_status,
                sn.advance_action_casting,
                sn.advance_action_trim,
                sn.other_remarks,
                sn.reason_for_delay
            FROM `tabSerial Number` sn
            /*
              MariaDB does not support DISTINCT ON or ROW_NUMBER in older
              versions.  The self-join below picks the minimum (first) name
              per batch using a plain GROUP BY + MIN — fully index-friendly.
            */
            INNER JOIN (
                SELECT batch, MIN(name) AS first_name
                FROM   `tabSerial Number`
                WHERE  batch IS NOT NULL
                  AND  batch != ''
                GROUP  BY batch
            ) AS first_sn
               ON first_sn.batch      = sn.batch
               AND first_sn.first_name = sn.name
        ) AS rep_sn
               ON rep_sn.batch = soi.custom_batch_no

        /*── Latest active / submitted BOM per item ───────────────────────────
             Correlated sub-query: docstatus DESC then creation DESC.
             is_active=1 guard avoids obsolete BOMs.                          */
        # LEFT JOIN `tabBOM` bom
        #        ON bom.name = (
        #            SELECT b.name
        #            FROM   `tabBOM` b
        #            WHERE  b.item       = soi.item_code
        #              AND  b.docstatus  IN (0, 1)
        #              AND  b.is_active  = 1
        #            ORDER  BY b.docstatus DESC,
        #                      b.creation  DESC
        #            LIMIT  1
        #        )

        /*── BOM Joined by Batch ───────────────────────────────────────────*/

        LEFT JOIN `tabBOM` bom
            ON bom.name = (
                SELECT b.name
                FROM `tabBOM` b
                WHERE b.custom_batch_no = soi.custom_batch_no
                    AND b.is_active = 1
                ORDER BY b.docstatus DESC, b.creation DESC
                LIMIT 1
            )
                    

        WHERE soi.docstatus = 1
          AND soi.custom_batch_no IS NOT NULL
          AND soi.custom_batch_no != ''
          AND so.status NOT IN('Completed','Cancelled','Closed')
          {conditions}

        ORDER BY so.transaction_date DESC,
                 so.name             ASC,
                 soi.idx             ASC
    """

    return frappe.db.sql(sql, values, as_dict=True)


# ---------------------------------------------------------------------------
# POST-PROCESS (computed columns)
# ---------------------------------------------------------------------------

_BOM_DONE = {"Active", "Submitted"}
def _post_process(rows):
    today = getdate(get_today())

    for r in rows:
         # ── 1 : BOM Status Custom Logic ──
        # Conditions:
        # - No BOM linked to batch -> BOM Pending
        # - BOM linked + Docstatus 0 -> Draft
        # - BOM linked + Docstatus 1 -> BOM Released
        
        bom_id = r.get("bom_id")
        docstatus = r.get("bom_docstatus")

        if not bom_id:
            r["bom_status"] = "BOM Pending"
        elif docstatus == 0:
            r["bom_status"] = "BOM In Draft"
        elif docstatus == 1:
            r["bom_status"] = "BOM Released"
        else:
            r["bom_status"] = ""

        

        # ── 1 : After GAD Status Logic ──
        val = r.get("after_gad_change_bom_update_or_not")
        status = "" 
        if val == "NA": status = "Not Applicable"
        elif val == "NO": status = "Not Received"
        elif not val or val == "00" or val == "": status = ""
        elif val in ["01", "02", "03", "04", "05", "06","07"]: status = "Not Released"
        elif "UPDATED" in str(val) : status = "RE-Released"
        r["after_gad_rev_bom_released"] = status

        # ── 2 : BOM Delay Days & Weeks (Based on SO Approval) ──
        so_approved  = r.get("so_approved_date")
        bom_released = r.get("bom_released_date")

        if not bom_released:
            if so_approved:
                delay_days = date_diff(today, getdate(so_approved))
                r["bom_delay_days"] = delay_days
                r["bom_delay_weeks"] = f"{delay_days // 7}W {delay_days % 7}D" if delay_days >= 0 else ""
            else:
                r["bom_delay_days"] = ""
                r["bom_delay_weeks"] = ""
        else:
            r["bom_delay_days"] = "Released"
            r["bom_delay_weeks"] = "NA"

        # ── 3 : Expected Based Delay Days & Weeks (Based on Expected Date) ──
        # Logic: If BOM is Released -> Released/NA. Else -> Calculate based on Expected Date.
        if r["bom_delay_days"] == "Released":
            r["expected_based_delay_days"] = "Released"
            r["expected_based_delay_week"] = "NA"
        else:
            exp_date = r.get("release_date_expected")
            if exp_date:
                delay_days = date_diff(today, getdate(exp_date))
                r["expected_based_delay_days"] = delay_days
                r["expected_based_delay_week"] = f"{delay_days // 7}W {delay_days % 7}D" if delay_days >= 0 else ""

                

    return rows
# ---------------------------------------------------------------------------
# FILTER CONDITIONS
# ---------------------------------------------------------------------------

def _build_conditions(filters):
    parts, values = [], {}

    _eq(filters, parts, values, "company",      "so.company")
    _eq(filters, parts, values, "branch",       "so.branch")
    _eq(filters, parts, values, "customer",     "so.customer")
    _eq(filters, parts, values, "sales_order",  "so.name")
    _eq(filters, parts, values, "order_status", "so.status")
    _eq(filters, parts, values, "mfg_type",     "rep_sn.mfg_type")
    _eq(filters, parts, values, "bom_status",   "bom.status")
    _eq(filters, parts, values, "gad_status",   "rep_sn.gad_status")
    _eq(filters, parts, values, "batch_no",   "rep_sn.batch")

    if filters.get("from_date"):
        parts.append("AND so.transaction_date >= %(from_date)s")
        values["from_date"] = filters.from_date

    if filters.get("to_date"):
        parts.append("AND so.transaction_date <= %(to_date)s")
        values["to_date"] = filters.to_date

    return "\n          ".join(parts), values


def _eq(filters, parts, values, key, col):
    if filters.get(key):
        parts.append(f"AND {col} = %({key})s")
        values[key] = filters[key]


# ---------------------------------------------------------------------------
# METADATA HELPER – used by JS to build inline editor dropdowns dynamically
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_sn_field_meta():
    """
    Returns fieldtype + options for every editable Serial Number field.
    Called once on report load so the JS can render the correct editor widget
    (Select dropdown, Date picker, or text input) without hard-coding options.
    """
    EDITABLE_FIELDS = [
        "mds_status", "mds_no", "mds_rev", "mds_date",
        "gad_required", "gad_status", "gad_rev", "gad_receive_date",
        "after_gad_change_bom_change_required",
        "itpqap", "itpqap_rev", "itpqap_receive_date",
        # "mfg_type", 
        "after_gad_change_bom_update_or_not",
        "design_remarks", "pattern_status",
        "advance_action_casting", "advance_action_trim",
        "engg_bom_created_by", "release_date_expected",
        # "expected_based_delay_week",
        "bom_released_in_which_gad_revision",
        "other_remarks", "reason_for_delay",
    ]

    meta    = frappe.get_meta("Serial Number")
    result  = {}

    for fname in EDITABLE_FIELDS:
        df = meta.get_field(fname)
        if not df: continue
        
        fieldtype = df.fieldtype
        
        
        result[fname] = {
            "fieldtype": fieldtype, 
            "label": df.label,
            "options": df.options or "",
            "reqd": df.reqd,
        }
    return result





# Two modes
#   1. BULK  – update all SNs in a batch in one SQL UPDATE statement
#   2. ROW   – update a single SN (the representative one shown in report)
#              then immediately propagate to all siblings in the same batch
#              so the whole batch stays in sync.

EDITABLE_SN_FIELDS = frozenset({
    "mds_status",
    "mds_no",
    "mds_rev",
    "mds_date",
    "gad_required",
    "gad_status",
    "gad_rev",
    "gad_receive_date",
    "after_gad_change_bom_change_required",
    "itpqap",
    "itpqap_rev",
    "itpqap_receive_date",
    "after_gad_change_bom_update_or_not",
    "design_remarks",
    "pattern_status",
    "advance_action_casting",
    "advance_action_trim",
    "engg_bom_created_by",
    "release_date_expected",
    "bom_released_in_which_gad_revision",
    "other_remarks",
    "reason_for_delay",
})


CHUNK_SIZE = 1000


# ---------------------------------------------------------------------------
# PUBLIC API 1 : BULK UPDATE (one field, all SNs in a batch)
# ---------------------------------------------------------------------------

@frappe.whitelist()
def bulk_update_batch(batch_name, fieldname, value):
    """
    Update `fieldname` = `value` on EVERY Serial Number that belongs to
    `batch_name` in a single SQL UPDATE statement.

    Called from JS when the user edits a cell in the report.

    Args:
        batch_name  (str) : value of `custom_batch_no` / `sn.batch`
        fieldname   (str) : Serial Number field to update
        value       (str) : new value (empty string clears the field)

    Returns:
        dict  { updated: <int>, batch: <str>, field: <str> }
    """
    _validate_field(fieldname)
    _check_permission()

    # Sanitise: convert JSON-stringified None / "null" to empty string
    value = _clean_value(value)

    # Count before update (for response)
    count = frappe.db.count("Serial Number", filters={"batch": batch_name})

    if count == 0:
        frappe.throw(_("No Serial Numbers found for batch {0}").format(batch_name))

    # Single UPDATE — fastest possible for any batch size.
    # frappe.db.sql uses parameterised queries; fieldname is validated above.
    frappe.db.sql(
        f"""
        UPDATE `tabSerial Number`
        SET    `{fieldname}` = %(value)s,
               `modified`   = %(now)s,
               `modified_by`= %(user)s
        WHERE  `batch`      = %(batch)s
        """,
        {
            "value": value,
            "now":   now_datetime(),
            "user":  frappe.session.user,
            "batch": batch_name,
        },
    )

    frappe.db.commit()

    return {
        "status":  "ok",
        "updated": count,
        "batch":   batch_name,
        "field":   fieldname,
    }


# ---------------------------------------------------------------------------
# PUBLIC API 2 : MULTI-FIELD BULK UPDATE (multiple fields, all SNs in batch)
# ---------------------------------------------------------------------------

@frappe.whitelist()
def bulk_update_batch_multifield(batch_name, field_value_map):
    """
    Update multiple fields at once for all SNs in a batch.
    More efficient than calling bulk_update_batch repeatedly.

    Args:
        batch_name      (str)  : batch identifier
        field_value_map (str)  : JSON-encoded dict  { fieldname: value, ... }

    Returns:
        dict  { updated: <int>, batch: <str>, fields: [<str>, ...] }
    """
    _check_permission()

    if isinstance(field_value_map, str):
        field_value_map = json.loads(field_value_map)

    if not field_value_map:
        frappe.throw(_("No fields provided for update."))

    # Validate all field names before touching the DB
    for fn in field_value_map:
        _validate_field(fn)

    count = frappe.db.count("Serial Number", filters={"batch": batch_name})
    if count == 0:
        frappe.throw(_("No Serial Numbers found for batch {0}").format(batch_name))

    # Build SET clause dynamically from validated field names
    set_parts  = [f"`{fn}` = %({fn}_val)s" for fn in field_value_map]
    set_parts += ["`modified` = %(now)s", "`modified_by` = %(user)s"]

    params = {f"{fn}_val": _clean_value(v) for fn, v in field_value_map.items()}
    params.update({
        "now":   now_datetime(),
        "user":  frappe.session.user,
        "batch": batch_name,
    })

    frappe.db.sql(
        f"""
        UPDATE `tabSerial Number`
        SET    {', '.join(set_parts)}
        WHERE  `batch` = %(batch)s
        """,
        params,
    )

    frappe.db.commit()

    return {
        "status":  "ok",
        "updated": count,
        "batch":   batch_name,
        "fields":  list(field_value_map.keys()),
    }


# ---------------------------------------------------------------------------
# PUBLIC API 3 : ROW-WISE UPDATE (one SN + propagate to batch siblings)
# ---------------------------------------------------------------------------

@frappe.whitelist()
def row_update_and_propagate(sn_name, fieldname, value, propagate_to_batch=True):
    """
    Update `fieldname` = `value` on a single Serial Number, then optionally
    propagate the same change to all siblings in the same batch.

    This keeps the "representative SN" approach consistent: whatever the
    user sets on the displayed row is immediately mirrored across the batch.

    Args:
        sn_name             (str)  : Serial Number document name
        fieldname           (str)  : field to update
        value               (str)  : new value
        propagate_to_batch  (bool) : default True; set False for true row-only edit

    Returns:
        dict  { updated: <int>, propagated: <bool>, sn: <str> }
    """
    try:

        _validate_field(fieldname)
        _check_permission()

        value = _clean_value(value)

        # Fetch batch name for this SN (one indexed read)
        batch_name = frappe.db.get_value("Serial Number", sn_name, "batch")

        if propagate_to_batch and batch_name:
            # Propagate to entire batch via single SQL UPDATE (same as bulk API)
            result = bulk_update_batch(batch_name, fieldname, value)
            return {
                "status":     "ok",
                "updated":    result["updated"],
                "propagated": True,
                "sn":         sn_name,
                "batch":      batch_name,
            }
        else:
            # Update only the single row
            frappe.db.sql(
                f"""
                UPDATE `tabSerial Number`
                SET    `{fieldname}` = %(value)s,
                    `modified`   = %(now)s,
                    `modified_by`= %(user)s
                WHERE  `name`       = %(sn_name)s
                """,
                {
                    "value":   value,
                    "now":     now_datetime(),
                    "user":    frappe.session.user,
                    "sn_name": sn_name,
                },
            )
            frappe.db.commit()
            return {
                "status":     "ok",
                "updated":    1,
                "propagated": False,
                "sn":         sn_name,
            }
    except Exception as e:
        #  Rollback DB changes
        frappe.db.rollback()

        #  Log full error (very important for debugging)
        frappe.log_error(
            title="Row Update and Propagate Failed in daily_review_sales_order",
            message=frappe.get_traceback()
        )
        return {
            "status":     "error",
            "updated":    0,
            "propagated": False,
            "sn":         sn_name,
        }


# ---------------------------------------------------------------------------
# PUBLIC API 4 : CHUNKED BULK UPDATE (for very large batches > CHUNK_SIZE)
# ---------------------------------------------------------------------------

@frappe.whitelist()
def bulk_update_batch_chunked(batch_name, fieldname, value):
    """
    Same as bulk_update_batch but processes in chunks of CHUNK_SIZE.
    Use this when the SN table is extremely large and the DBA wants
    smaller transaction windows to avoid locking.

    For most cases, bulk_update_batch (single UPDATE) is preferred.
    This is provided for environments with strict lock-timeout policies.

    Returns:
        dict  { updated: <int>, chunks: <int> }
    """
    _validate_field(fieldname)
    _check_permission()

    value = _clean_value(value)

    # Fetch all SN names in the batch using a generator-style approach
    sn_names = frappe.db.sql(
        "SELECT name FROM `tabSerial Number` WHERE batch = %(batch)s ORDER BY name",
        {"batch": batch_name},
        as_list=True,
    )
    sn_names = [row[0] for row in sn_names]

    total   = len(sn_names)
    chunks  = 0
    updated = 0

    for i in range(0, total, CHUNK_SIZE):
        chunk = sn_names[i : i + CHUNK_SIZE]

        # Use IN list for the chunk — still parameterised
        placeholders = ", ".join(["%s"] * len(chunk))
        frappe.db.sql(
            f"""
            UPDATE `tabSerial Number`
            SET    `{fieldname}` = %s,
                   `modified`   = %s,
                   `modified_by`= %s
            WHERE  `name` IN ({placeholders})
            """,
            [value, now_datetime(), frappe.session.user] + chunk,
        )
        frappe.db.commit()
        updated += len(chunk)
        chunks  += 1

    return {
        "status":  "ok",
        "updated": updated,
        "chunks":  chunks,
        "batch":   batch_name,
        "field":   fieldname,
    }


# ---------------------------------------------------------------------------
# PUBLIC API 5 : GET BATCH SN COUNT (JS uses this to decide bulk vs chunked)
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_batch_sn_count(batch_name):
    """Return the number of Serial Numbers in a batch."""
    count = frappe.db.count("Serial Number", filters={"batch": batch_name})
    return {"count": count, "chunk_size": CHUNK_SIZE}


# ---------------------------------------------------------------------------
# INTERNAL HELPERS
# ---------------------------------------------------------------------------

def _validate_field(fieldname):
    """Raise if fieldname is not in the allowed set (whitelist guard)."""
    if fieldname not in EDITABLE_SN_FIELDS:
        frappe.throw(
            _("Field '{0}' is not editable via this report. Allowed fields: {1}").format(
                fieldname,
                ", ".join(sorted(EDITABLE_SN_FIELDS)),
            )
        )


def _check_permission():
    """Raise if the current user lacks write permission on Serial Number."""
    if not frappe.has_permission("Serial Number", ptype="write"):
        frappe.throw(
            _("You do not have permission to update Serial Number records."),
            frappe.PermissionError,
        )


def _clean_value(value):
    """
    Normalise incoming value:
    • JSON null / Python None → empty string (clears the field)
    • Strings are stripped
    """
    if value is None or value == "null":
        return ""
    if isinstance(value, str):
        return value.strip()
    return value