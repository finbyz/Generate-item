import json
import time
from io import BytesIO
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import (
    now_datetime,
    get_datetime,
    add_days,
    add_months,
    add_to_date,
    getdate,
    today,
    get_first_day,
    get_last_day,
    get_first_day_of_week,
    get_last_day_of_week,
    get_quarter_start,
    get_quarter_ending,
    get_year_start,
    get_year_ending,
    cint,
    cstr,
    flt,
    strip_html,
)

import logging
import cssutils
from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

DATE_FIELDTYPES = {"Date"}
DATETIME_FIELDTYPES = {"Datetime"}
NUMERIC_FIELDTYPES = {"Int", "Float", "Currency", "Percent"}
CHECK_FIELDTYPES = {"Check"}

# cssutils logs a Python-level ERROR for CSS it can't parse (e.g. 8-digit
# hex colors like #0000001a used for RGBA). These are non-fatal — the
# property is just skipped during inlining — but they spam the console
# during frappe.sendmail(). Silence them here.
cssutils.log.setLevel(logging.CRITICAL)


logger = frappe.logger(
    "report_email_scheduled",
    allow_site=True,
    file_count=5,
)


def resolve_date_range(date_range_val):
    """
    Returns (from_date, to_date) as 'YYYY-MM-DD' strings for a given date_range option.
    Supported options:
    - Today
    - Yesterday
    - This Week
    - Last Week
    - This Month
    - Last Month
    - This Quarter
    - Last Quarter / Last Quater
    - This Year
    - Last Year
    - Custom comma-separated: "2026-09-01, 2026-09-30"
    - Single date string: "2026-09-15" -> ("2026-09-15", "2026-09-15")
    """
    if not date_range_val:
        return None, None

    date_range_val = str(date_range_val).strip()

    if "," in date_range_val:
        parts = [p.strip() for p in date_range_val.split(",") if p.strip()]
        if len(parts) >= 2:
            return str(getdate(parts[0])), str(getdate(parts[1]))
        elif len(parts) == 1:
            d = str(getdate(parts[0]))
            return d, d

    val_lower = date_range_val.lower().replace("quater", "quarter")

    # Try frappe.utils.data.get_timespan_date_range first
    try:
        from frappe.utils.data import get_timespan_date_range
        res = get_timespan_date_range(val_lower)
        if res and len(res) == 2:
            return str(getdate(res[0])), str(getdate(res[1]))
    except Exception:
        pass

    # Fallback / manual calculation
    today_dt = getdate(today())

    if val_lower == "today":
        return str(today_dt), str(today_dt)
    elif val_lower == "yesterday":
        yest = add_days(today_dt, -1)
        return str(getdate(yest)), str(getdate(yest))
    elif val_lower == "this week":
        start = get_first_day_of_week(today_dt)
        end = get_last_day_of_week(today_dt)
        return str(getdate(start)), str(getdate(end))
    elif val_lower == "last week":
        prev_week = add_days(today_dt, -7)
        start = get_first_day_of_week(prev_week)
        end = get_last_day_of_week(prev_week)
        return str(getdate(start)), str(getdate(end))
    elif val_lower == "this month":
        start = get_first_day(today_dt)
        end = get_last_day(today_dt)
        return str(getdate(start)), str(getdate(end))
    elif val_lower == "last month":
        prev_month = add_months(today_dt, -1)
        start = get_first_day(prev_month)
        end = get_last_day(prev_month)
        return str(getdate(start)), str(getdate(end))
    elif val_lower == "this quarter":
        start = get_quarter_start(today_dt)
        end = get_quarter_ending(today_dt)
        return str(getdate(start)), str(getdate(end))
    elif val_lower == "last quarter":
        prev_q = add_months(today_dt, -3)
        start = get_quarter_start(prev_q)
        end = get_quarter_ending(prev_q)
        return str(getdate(start)), str(getdate(end))
    elif val_lower == "this year":
        start = get_year_start(today_dt)
        end = get_year_ending(today_dt)
        return str(getdate(start)), str(getdate(end))
    elif val_lower == "last year":
        prev_y = add_to_date(today_dt, years=-1)
        start = get_year_start(prev_y)
        end = get_year_ending(prev_y)
        return str(getdate(start)), str(getdate(end))

    try:
        d = str(getdate(date_range_val))
        return d, d
    except Exception:
        return None, None


class ReportEmailScheduled(Document):

    def validate(self):
        logger.info(
            f"Validating schedule | "
            f"name={self.name} | "
            f"report={self.report}"
        )
        self.validate_schedule()

    def before_save(self):
        logger.info(
            f"Before save | "
            f"name={self.name} | "
            f"enable={self.enable} | "
            f"frequency={self.frequency} | "
            f"time={self.time}"
        )
        self.set_next_execution()
        logger.info(
            f"Next execution calculated | "
            f"name={self.name} | "
            f"next_execution={self.next_execution}"
        )

    def validate_schedule(self):
        logger.info(f"Running schedule validation | name={self.name}")

        if not self.report:
            logger.error(f"Validation failed: Report missing | name={self.name}")
            frappe.throw("Please select a Report.")

        if not self.recipients:
            logger.error(f"Validation failed: Recipients missing | name={self.name}")
            frappe.throw("Please add at least one recipient.")

        if not self.frequency:
            logger.error(f"Validation failed: Frequency missing | name={self.name}")
            frappe.throw("Please select Frequency.")

        if not self.time:
            logger.error(f"Validation failed: Time missing | name={self.name}")
            frappe.throw("Please select Time.")

        if self.frequency == "Weekly" and not self.day_of_week:
            frappe.throw("Please select Day of Week.")

        if self.frequency == "Monthly":
            if not self.day_of_month:
                frappe.throw("Please enter Day of Month.")
            if not 1 <= int(self.day_of_month) <= 31:
                frappe.throw("Day of Month must be between 1 and 31.")
                
        # --- optional: validate CC addresses --------------------------------
        if self.get("cc"):
            from frappe.utils import validate_email_address

            for addr in self.get_cc():
                try:
                    validate_email_address(addr, throw=True)
                except Exception:
                    frappe.throw(f"Invalid CC address: {addr}")

    def set_next_execution(self):
        
        if not self.enable or not self.time:
            logger.info(
                f"Schedule disabled/no time set. "
                f"Clearing next_execution | "
                f"name={self.name}"
            )
            self.next_execution = None
            return

        now = now_datetime()

        # if self.next_execution:
        #     if get_datetime(self.next_execution) > now:
        #         frappe.msgprint(
        #             f"Next execution is already set to {self.next_execution}. "
        #             f"No changes made {now}."
        #         )
        #         return

        self.next_execution = self.get_next_execution(now)

        
    def get_next_execution(self, from_datetime=None):
        from_datetime = from_datetime or now_datetime()

        logger.info(
            f"Calculating next execution | "
            f"name={self.name} | "
            f"frequency={self.frequency} | "
            f"from={from_datetime}"
        )

        time = str(self.time)
        hour, minute, second = map(int, time.split(":"))

        execution_time = from_datetime.replace(
            hour=hour,
            minute=minute,
            second=second,
            microsecond=0,
        )

        if self.frequency == "Daily":
            if execution_time <= from_datetime:
                execution_time = add_days(execution_time, 1)

            logger.info(
                f"Daily next execution | "
                f"name={self.name} | "
                f"next={execution_time}"
            )
            return execution_time

        if self.frequency == "Weekly":
            weekdays = {
                "Monday": 0,
                "Tuesday": 1,
                "Wednesday": 2,
                "Thursday": 3,
                "Friday": 4,
                "Saturday": 5,
                "Sunday": 6,
            }

            target_day = weekdays[self.day_of_week]
            days_ahead = (target_day - from_datetime.weekday()) % 7
            execution_time = add_days(execution_time, days_ahead)

            if execution_time <= from_datetime:
                execution_time = add_days(execution_time, 7)

            logger.info(
                f"Weekly next execution | "
                f"name={self.name} | "
                f"day={self.day_of_week} | "
                f"next={execution_time}"
            )
            return execution_time

        if self.frequency == "Monthly":
            day = int(self.day_of_month)

            try:
                execution_time = execution_time.replace(day=day)
            except ValueError:
                logger.warning(
                    f"Invalid monthly date | "
                    f"name={self.name} | "
                    f"day={day}"
                )
                execution_time = add_months(execution_time, 1)
                execution_time = execution_time.replace(day=day)

            if execution_time <= from_datetime:
                execution_time = add_months(execution_time, 1)
                execution_time = execution_time.replace(day=day)

            logger.info(
                f"Monthly next execution | "
                f"name={self.name} | "
                f"day={day} | "
                f"next={execution_time}"
            )
            return execution_time

        logger.error(
            f"Invalid frequency | "
            f"name={self.name} | "
            f"frequency={self.frequency}"
        )
        frappe.throw(f"Invalid frequency: {self.frequency}")

    def get_filters(self):
        """
        Build a flat dict of filters from the child table plus the schedule's
        own company / customer / date_range fields.

        Whether an individual filter survives depends on the report type — see
        ``_get_supported_filters``.  In particular, Report Builder reports will
        blow up with "Unknown column 'tabX.field'" if we hand them a column
        that doesn't exist on their DocType.
        """
        filter_dict = {}

        report_doc = None
        report_type = None
        ref_doctype = None
        if self.report and frappe.db.exists("Report", self.report):
            try:
                report_doc = frappe.get_doc("Report", self.report)
                report_type = report_doc.report_type
                ref_doctype = report_doc.ref_doctype
            except Exception:
                pass

        supported = self._get_supported_filters()
        restrict = supported is not None

        def _add(fieldname, value):
            if restrict and fieldname not in supported:
                logger.info(
                    f"Skipping unsupported filter '{fieldname}' | "
                    f"report={self.report} | name={self.name}"
                )
                return
            filter_dict[fieldname] = value

        # 1. Child-table filters
        for row in self.get("filters") or []:
            fieldname = row.get("fieldname")
            if not fieldname or row.get("value") is None:
                continue
            _add(fieldname, row.get("value"))

        # 2. Main-document filters
        if self.get("company"):
            _add("company", self.company)

        if self.get("customer"):
            _add("customer", self.customer)
            
        if self.get("group_by"):                      # <-- ADD THESE 2 LINES
            filter_dict["group_by"] = self.group_by

        # 3. Date range -> from_date / to_date or Report Builder date field
        if self.get("date_range"):
            from_date, to_date = resolve_date_range(self.date_range)
            if from_date and to_date:
                if report_type == "Report Builder" and ref_doctype:
                    date_field = self._get_report_builder_date_field(report_doc, ref_doctype)
                    if date_field:
                        filter_dict[date_field] = ["between", [from_date, to_date]]
                    else:
                        _add("from_date", from_date)
                        _add("to_date", to_date)
                else:
                    _add("from_date", from_date)
                    _add("to_date", to_date)

        logger.info(
            f"Filters built for schedule | name={self.name} | "
            f"report={self.report} | restrict={restrict} | filters={filter_dict}"
        )
        return filter_dict

    def _get_report_builder_date_field(self, report_doc, ref_doctype):
        """
        Determine the appropriate Date/Datetime column on ref_doctype
        to apply the date range filter to for a Report Builder report.
        """
        if not ref_doctype:
            return None

        try:
            meta = frappe.get_meta(ref_doctype)
        except Exception:
            return None

        # 1. If child table filters contains a Date / Datetime field on ref_doctype
        for row in self.get("filters") or []:
            fn = row.get("fieldname")
            if fn:
                df = meta.get_field(fn)
                if df and df.fieldtype in ("Date", "Datetime"):
                    return fn

        # 2. Check saved filters in report_doc.json
        if report_doc and report_doc.get("json"):
            try:
                payload = report_doc.json
                if isinstance(payload, str):
                    payload = json.loads(payload)
                for sf in (payload or {}).get("filters") or []:
                    if isinstance(sf, (list, tuple)) and len(sf) >= 2:
                        fn = sf[1]
                        df = meta.get_field(fn)
                        if df and df.fieldtype in ("Date", "Datetime"):
                            return fn
            except Exception:
                pass

        # 3. If ref_doctype has from_date and to_date
        if meta.has_field("from_date") and meta.has_field("to_date"):
            return None

        # 4. Standard common date fieldnames on ref_doctype
        common_date_fields = [
            "posting_date",
            "transaction_date",
            "date_of_call",
            "date",
            "order_date",
            "invoice_date",
            "bill_date",
            "creation",
        ]
        for fn in common_date_fields:
            if fn == "creation" or meta.has_field(fn):
                return fn

        # 5. First Date or Datetime field on DocType
        for f in meta.fields:
            if f.fieldtype in ("Date", "Datetime"):
                return f.fieldname

        return "creation"


    def _get_supported_filters(self):
        """
        Return the set of filter fieldnames that can safely be passed to this
        report, or ``None`` to be permissive.

        Report type matters because Frappe consumes filters differently:

        * Script Report  -> ``filters.get("x")``; unknown keys are ignored.
                            JS filter lists cannot be reliably parsed, so be
                            permissive (otherwise mandatory filters such as
                            ``company`` on General Ledger get silently dropped
                            and ERPNext raises "Company is mandatory").

        * Query Report   -> ``%(x)s`` substitution in the SQL string; unknown
                            placeholders are simply unused.  Permissive.

        * Report Builder -> ``frappe.get_list(doctype, filters=...)``, which
                            turns every key into ``tabX.field = value``.  An
                            unknown key becomes
                            ``Unknown column 'tabX.field' in 'WHERE'``.
                            Restrict to columns that actually exist on the
                            report's DocType.
        """
        try:
            report = frappe.get_doc("Report", self.report)
            report_type = report.report_type

            # ---- Script Report / Query Report: permissive ------------------
            if report_type != "Report Builder":
                logger.info(
                    f"Permissive filters for {report_type} | "
                    f"name={self.name} | report={self.report}"
                )
                return None

            # ---- Report Builder: restrict to valid DocType columns ----------
            ref_doctype = report.ref_doctype
            if not ref_doctype:
                return None

            meta = frappe.get_meta(ref_doctype)
            valid = set(meta.get_valid_columns() or [])
            valid.add("name")  # primary key isn't in get_valid_columns()
            # valid.update(_REPORT_BUILDER_PSEUDO_FILTERS)    

            # Allow anything the report explicitly declares as a filter
            for row in report.get("filters") or []:
                fn = row.get("fieldname")
                if fn:
                    valid.add(fn)

            logger.info(
                f"Report Builder valid filters resolved | name={self.name} | "
                f"report={self.report} | doctype={ref_doctype} | "
                f"count={len(valid)}"
            )
            return valid

        except Exception:
            logger.exception(
                f"Failed to resolve supported filters | name={self.name} | "
                f"report={self.report} — passing filters through unchanged"
            )
            return None

    # ---------- Safe database update with retries and lock handling ----------
    def _safe_set_value(self, *args, retries=5, delay=0.5):
        """
        Wraps frappe.db.set_value with automatic commit, retry, and lock wait handling.
        Accepts the same arguments as frappe.db.set_value.
        """
        if len(args) < 2:
            raise ValueError("At least dt and dn are required")

        # Commit any pending transaction to release locks before attempting update
        try:
            frappe.db.commit()
        except Exception:
            pass

        # Set a longer lock wait timeout for this session (60 seconds)
        try:
            frappe.db.sql("SET SESSION lock_wait_timeout = 60")
        except Exception:
            pass

        for attempt in range(retries):
            try:
                frappe.db.set_value(*args)
                return  # success
            except Exception as e:
                error_msg = str(e)
                # If it's a lock timeout or lost connection, retry
                if ("Lock wait timeout" in error_msg or "Lost connection" in error_msg) and attempt < retries - 1:
                    logger.warning(
                        f"DB error: {error_msg}. Retrying in {delay}s (attempt {attempt + 1}/{retries})"
                    )
                    time.sleep(delay)
                    # Reconnect if connection lost
                    if "Lost connection" in error_msg:
                        frappe.db.close()
                        frappe.db.connect()
                    continue
                # Otherwise re-raise
                raise

    def send_report_email(self, report_name, extension, content):
        recipients = self.get_recipients()
        cc = self.get_cc()

        if not recipients:
            logger.error(f"No recipients found | name={self.name}")
            frappe.throw("No valid email recipients found.")

        filename = f"{report_name}.{extension}"

        message = (self.get("email_message") or "").strip()
        if not message:
            message = f"""
                <p>Hello,</p>
                <p>Please find the scheduled report <b>{self.report}</b> attached.</p>
                <p>Regards,<br>ERPNext</p>
            """

        sendmail_kwargs = {
            "recipients": recipients,
            "subject": f"Scheduled Report - {self.report}",
            "message": message,
            "attachments": [{"fname": filename, "fcontent": content}],
            "reference_doctype": self.doctype,
            "reference_name": self.name,
            "expose_recipients": "header",
        }
        if cc:
            sendmail_kwargs["cc"] = cc

        frappe.sendmail(**sendmail_kwargs)

        # Frappe merged cc into the recipients child table; undo that for display.
        self._strip_cc_from_email_queue(cc)

        logger.info(f"Email send completed | name={self.name}")
    
    def get_recipients(self):
        if not self.recipients:
            return []

        recipients = self.recipients.replace("\n", ",").split(",")
        recipients = [email.strip() for email in recipients if email.strip()]

        logger.info(
            f"Recipients parsed | name={self.name} | count={len(recipients)}"
        )
        return recipients

    def export_report(self, filters):
        """
        Runs the report and converts the resulting rows into an XLSX file.

        * Header labels come from the Report document's declared columns
        (Report Builder `fields`, Query/Script Report `columns` child table).
        * Frappe's auto-injected audit columns (docstatus, modified,
        modified_by, …) are dropped from Report Builder exports.
        * If ``group_by`` is present in ``filters``, rows are aggregated into
        a two-column (group value, count) table — matching the report's
        "Group By …" view.
        """
        filters = dict(filters or {})
        group_by = filters.pop("group_by", None)
        
        try:
            result = get_report_data(self.report, filters)
        except Exception:
            frappe.log_error(
                message=frappe.get_traceback(),
                title=f"Scheduled Report Data Fetch Failed: {self.name}",
            )
            raise

        rows         = result.get("data") or []
        columns      = result.get("columns") or []
        col_defs     = result.get("column_definitions") or []
        report_type  = result.get("report_type")
        is_rb        = report_type == "Report Builder"

        declared     = self._get_report_declared_columns()
        use_declared = bool(declared)

        

        # ===================================================================
        # Branch A — grouped output
        # ===================================================================
        if group_by and rows:
            group_label = declared.get(group_by, {}).get("label") or group_by

            # Runtime column list vs. declared field list, both with
            # Frappe's noise fields removed, are positionally aligned.
            # Use that to translate "reason_for_contact" (declared) into
            # "DocField(df6bd4078b)" (runtime key).
            declared_pairs = [
                (fn, info["label"]) for fn, info in declared.items()
                if fn not in _REPORT_BUILDER_NOISE_FIELDS
            ]
            runtime_cols = [
                c for c in columns
                if c not in _REPORT_BUILDER_NOISE_FIELDS
            ]

            group_col_key = None
            for (fn, _lbl), col in zip(declared_pairs, runtime_cols):
                if fn == group_by:
                    group_col_key = col
                    break

            # Fallbacks, in case zip alignment fails for some reason.
            if group_col_key is None:
                if group_by in columns:
                    group_col_key = group_by          # Query/Script path
                elif group_by in declared:
                    # Walk declared by index, pick the same index from columns.
                    fn_index = list(declared.keys()).index(group_by)
                    if fn_index < len(columns):
                        group_col_key = columns[fn_index]

            logger.info(
                f"Grouped export | name={self.name} | "
                f"group_by={group_by!r} -> runtime key={group_col_key!r} | "
                f"declared_pairs={[fn for fn, _ in declared_pairs]} | "
                f"runtime_cols={runtime_cols}"
            )

            counts = {}
            for row in rows:
                if not isinstance(row, dict):
                    continue
                value = row.get(group_col_key)
                counts[value] = counts.get(value, 0) + 1

            ordered = sorted(
                counts.items(),
                key=lambda kv: (kv[0] in (None, ""), -kv[1]),
            )
            labels = [group_label, "Count"]
            fieldnames = ["group_val", "count"]
            fieldtypes = [declared.get(group_by, {}).get("fieldtype") or "Data", "Int"]
            export_rows = [{"group_val": v, "count": c} for v, c in ordered]

        # ===================================================================
        # Branch B — normal (ungrouped) output
        # ===================================================================
        else:
            labels = []
            fieldnames = []
            fieldtypes = []

            col_def_by_fn = {}
            for cd in col_defs:
                if isinstance(cd, dict):
                    if cd.get("fieldname"):
                        col_def_by_fn[cd["fieldname"]] = cd
                    if cd.get("label"):
                        col_def_by_fn[cd["label"]] = cd

            if is_rb:
                runtime_cols = [
                    c for c in columns
                    if c not in _REPORT_BUILDER_NOISE_FIELDS
                ]
                declared_pairs = [
                    (fn, info["label"]) for fn, info in declared.items()
                    if fn not in _REPORT_BUILDER_NOISE_FIELDS
                ]

                if declared_pairs and len(runtime_cols) == len(declared_pairs):
                    for (fn, label), col in zip(declared_pairs, runtime_cols):
                        labels.append(label)
                        fieldnames.append(col)
                        ftype = declared.get(fn, {}).get("fieldtype") or col_def_by_fn.get(col, {}).get("fieldtype") or "Data"
                        fieldtypes.append(ftype)
                else:
                    for i, col in enumerate(runtime_cols):
                        info = declared.get(col, {})
                        label = info.get("label")
                        ftype = info.get("fieldtype")
                        if not label and i < len(col_defs):
                            label = col_defs[i].get("label")
                            ftype = ftype or col_defs[i].get("fieldtype")
                        labels.append(label or col)
                        fieldnames.append(col)
                        fieldtypes.append(ftype or "Data")
            else:
                for i, col in enumerate(columns):
                    if col in _FRAPPE_AUTO_COLUMNS and col not in declared:
                        continue
                    info = declared.get(col, {})
                    label = info.get("label")
                    ftype = info.get("fieldtype")
                    if not label and i < len(col_defs):
                        label = col_defs[i].get("label")
                        ftype = ftype or col_defs[i].get("fieldtype")
                    labels.append(label or col)
                    fieldnames.append(col)
                    fieldtypes.append(ftype or "Data")

            if not labels and rows and isinstance(rows[0], dict):
                labels = list(rows[0].keys())
                fieldnames = labels
                fieldtypes = ["Data"] * len(labels)
            elif not labels:
                labels = ["No data"]
                fieldnames = ["no_data"]
                fieldtypes = ["Data"]

            export_rows = rows

        # ===================================================================
        # Build Formatted XLSX Workbook
        # ===================================================================
        wb = Workbook()
        ws = wb.active
        sheet_title = (self.report or "Report")[:31]
        for ch in ["\\", "/", "?", "*", ":", "[", "]"]:
            sheet_title = sheet_title.replace(ch, "")
        ws.title = sheet_title or "Report"

        # ---------------- Theme & Styles ----------------
        HEADER_BLUE = "4472C4"
        WHITE = "FFFFFF"

        header_font = Font(name="Calibri", bold=True, color=WHITE, size=10)
        header_fill = PatternFill("solid", fgColor=HEADER_BLUE)
        thin = Side(style="thin", color="B7C6E3")
        thin_border = Border(left=thin, right=thin, top=thin, bottom=thin)
        center = Alignment(horizontal="center", vertical="center", wrap_text=True)
        left_align = Alignment(horizontal="left", vertical="center")
        right_align = Alignment(horizontal="right", vertical="center")

        n_cols = max(len(labels), 1)
        last_col_letter = get_column_letter(n_cols)

        # ---------------- Header Row ----------------
        header_row_idx = 1
        for idx, label in enumerate(labels, start=1):
            cell = ws.cell(row=header_row_idx, column=idx, value=label)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center
            cell.border = thin_border
        ws.row_dimensions[header_row_idx].height = 22

        # Start max_width calculation with header label length + padding (extra for table filter arrows)
        max_width = [len(str(lbl or "")) + 5 for lbl in labels]

        # ---------------- Data Rows ----------------
        start_data_row = header_row_idx + 1
        for r_idx, row in enumerate(export_rows):
            if isinstance(row, dict):
                values = [row.get(fn, "") for fn in fieldnames]
            elif isinstance(row, (list, tuple)):
                values = [row[i] if i < len(row) else "" for i in range(len(fieldnames))]
            else:
                values = [row]

            excel_row_idx = start_data_row + r_idx

            for c_idx, (value, ftype) in enumerate(zip(values, fieldtypes), start=1):
                if isinstance(value, bool):
                    value = "Yes" if value else "No"
                elif ftype in CHECK_FIELDTYPES and value in (1, 0, "1", "0"):
                    value = "Yes" if cint(value) else "No"

                cell = ws.cell(row=excel_row_idx, column=c_idx)

                if value is None or value == "":
                    cell.value = ""
                    cell.alignment = left_align
                elif ftype in ("Currency", "Float"):
                    try:
                        cell.value = flt(value, 2)
                        cell.number_format = "#,##0.00"
                    except Exception:
                        cell.value = value
                    cell.alignment = right_align
                elif ftype == "Percent":
                    try:
                        val_flt = flt(value, 2)
                        cell.value = val_flt / 100.0 if abs(val_flt) > 1 else val_flt
                        cell.number_format = "0.00%"
                    except Exception:
                        cell.value = value
                    cell.alignment = right_align
                elif ftype == "Int":
                    try:
                        cell.value = cint(value)
                        cell.number_format = "#,##0"
                    except Exception:
                        cell.value = value
                    cell.alignment = right_align
                elif ftype in DATE_FIELDTYPES and value:
                    try:
                        cell.value = getdate(value)
                        cell.number_format = "dd-mm-yyyy"
                    except Exception:
                        cell.value = cstr(value)
                    cell.alignment = center
                elif ftype in DATETIME_FIELDTYPES and value:
                    try:
                        cell.value = get_datetime(value)
                        cell.number_format = "dd-mm-yyyy hh:mm"
                    except Exception:
                        cell.value = cstr(value)
                    cell.alignment = center
                else:
                    if isinstance(value, str) and ("<" in value and ">" in value):
                        value = strip_html(value)
                    cell.value = value
                    cell.alignment = left_align

                cell.border = thin_border

                text_value = cstr(cell.value if cell.value is not None else "")
                if len(text_value) + 3 > max_width[c_idx - 1]:
                    max_width[c_idx - 1] = min(len(text_value) + 3, 50)

        # ---------------- Column Widths ----------------
        for idx, width in enumerate(max_width, 1):
            ws.column_dimensions[get_column_letter(idx)].width = min(max(width, 12), 50)

        # ---------------- Freeze Header Row ----------------
        ws.freeze_panes = f"A{start_data_row}"

        # ---------------- Native Excel Table (filters + banded rows) ----------------
        last_row = start_data_row + len(export_rows) - 1
        if export_rows and n_cols > 0 and last_row >= start_data_row:
            clean_name = "".join(ch for ch in (self.report or "Report") if ch.isalnum())[:16]
            table_name = f"Tbl_{clean_name}_{int(time.time())}"
            table = Table(
                displayName=table_name,
                ref=f"A{header_row_idx}:{last_col_letter}{last_row}",
            )
            table.tableStyleInfo = TableStyleInfo(
                name="TableStyleMedium9",
                showFirstColumn=False,
                showLastColumn=False,
                showRowStripes=True,
                showColumnStripes=False,
            )
            ws.add_table(table)

            # negative numbers highlighted in red, for any numeric column
            red_font = Font(color="C00000")
            for c_idx, ftype in enumerate(fieldtypes, start=1):
                if ftype in NUMERIC_FIELDTYPES:
                    col_letter = get_column_letter(c_idx)
                    rng = f"{col_letter}{start_data_row}:{col_letter}{last_row}"
                    ws.conditional_formatting.add(
                        rng, CellIsRule(operator="lessThan", formula=["0"], font=red_font)
                    )

        # ---------------- Save to Buffer ----------------
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        content = buffer.getvalue()

        logger.info(
            f"XLSX built | name={self.name} | report={self.report} | "
            f"rows={len(export_rows)} | grouped={bool(group_by)} | "
            f"bytes={len(content)}"
        )

        return self.report, "xlsx", content



    def send_scheduled_report(self):
        if not self.enable:
            logger.info(f"Schedule disabled. Skipping | name={self.name}")
            return

        try:
            frappe.db.sql("SET SESSION wait_timeout = 7200")
            frappe.db.sql("SET SESSION interactive_timeout = 7200")
        except Exception as e:
            logger.warning(f"Could not set session timeouts: {e}")

        filters = self.get_filters()
        logger.info(
            f"Starting report execution | "
            f"name={self.name} | report={self.report} | filters={filters}"
        )

        # Only a genuine failure (exception) aborts; empty result still sends.
        try:
            report_name, extension, content = self.export_report(filters)
        except Exception:
            logger.exception(
                f"Report execution failed, skipping email | name={self.name}"
            )
            frappe.log_error(
                message=frappe.get_traceback(),
                title=f"Scheduled Report Failed: {self.name}",
            )
            self._safe_set_value(
                self.doctype, self.name, "last_execution", now_datetime()
            )
            return

        logger.info(
            f"Report exported | name={self.name} | "
            f"file={report_name}.{extension} | size={len(content) or 0}"
        )

        self.send_report_email(report_name, extension, content)
        logger.info(f"Email sent successfully | name={self.name}")

        execution_time = now_datetime()
        next_execution = self.get_next_execution(execution_time)

        try:
            frappe.db.commit()
        except Exception:
            pass

        self._safe_set_value(
            self.doctype,
            self.name,
            {"last_execution": execution_time, "next_execution": next_execution},
        )

        try:
            frappe.db.commit()
        except Exception:
            pass

        logger.info(
            f"Execution information updated | name={self.name} | "
            f"last={execution_time} | next={next_execution}"
        )

    @frappe.whitelist()
    def send_now(self):
        """Send the scheduled report immediately on manual trigger."""
        try:
            frappe.db.sql("SET SESSION wait_timeout = 7200")
            frappe.db.sql("SET SESSION interactive_timeout = 7200")
        except Exception as e:
            logger.warning(f"Could not set session timeouts: {e}")

        filters = self.get_filters()
        logger.info(
            f"Manual 'Send Now' triggered | "
            f"name={self.name} | report={self.report} | filters={filters}"
        )

        try:
            report_name, extension, content = self.export_report(filters)
        except Exception:
            logger.exception(
                f"Manual report execution failed | name={self.name}"
            )
            frappe.log_error(
                message=frappe.get_traceback(),
                title=f"Manual Report Send Failed: {self.name}",
            )
            frappe.throw(frappe._("Failed to generate report. Please check Error Log."))

        self.send_report_email(report_name, extension, content)
        logger.info(f"Manual email sent successfully | name={self.name}")

        execution_time = now_datetime()
        try:
            frappe.db.commit()
        except Exception:
            pass

        self._safe_set_value(
            self.doctype,
            self.name,
            "last_execution",
            execution_time,
        )

        try:
            frappe.db.commit()
        except Exception:
            pass

        return {
            "status": "success",
            "message": frappe._("Report email has been sent successfully."),
        }
        
    def get_cc(self):
        """Parse the comma/newline separated `cc` field into a clean list."""
        if not self.get("cc"):
            return []

        cc = self.cc.replace("\n", ",").split(",")
        cc = [email.strip() for email in cc if email.strip()]

        logger.info(
            f"CC parsed | name={self.name} | count={len(cc)}"
        )
        return cc
    
    def _strip_cc_from_email_queue(self, cc):
        """
        Frappe v14's sendmail() unconditionally appends cc addresses to the
        Email Queue's `recipients` child table. Remove them so the UI shows
        only the To addresses there, while the `cc` field keeps the CC list.

        Safe because expose_recipients="header" bakes the Cc: header into the
        outgoing MIME message during message assembly, so the cc row in the
        child table is redundant for delivery.
        """
        if not cc:
            return

        try:
            eq_name = frappe.db.get_value(
                "Email Queue",
                {
                    "reference_doctype": self.doctype,
                    "reference_name": self.name,
                },
                "name",
                order_by="creation desc",
            )
            if not eq_name:
                logger.warning(f"No Email Queue found to strip CC | name={self.name}")
                return

            cc_lower = {c.strip().lower() for c in cc if c.strip()}

            eq = frappe.get_doc("Email Queue", eq_name)
            original = len(eq.recipients)
            eq.recipients = [
                row for row in eq.recipients
                if (row.recipient or "").strip().lower() not in cc_lower
            ]
            removed = original - len(eq.recipients)

            if removed:
                eq.flags.ignore_permissions = True
                eq.flags.ignore_validate_update_after_submit = True
                eq.save(ignore_permissions=True)
                frappe.db.commit()
                logger.info(
                    f"Stripped {removed} CC row(s) from Email Queue {eq_name} | "
                    f"remaining={len(eq.recipients)}"
                )
        except Exception:
            logger.exception(
                f"Failed to strip CC from Email Queue | name={self.name} | cc={cc}"
            )
        
        
    def _get_report_declared_columns(self):
        """
        Return {fieldname: {"fieldname","label","fieldtype","options"}} for the
        columns declared on the Report document.

        * Query / Script Reports: columns live in the `columns` child table.
        * Report Builder reports : columns live in json.fields as
        [[fieldname, doctype], ...] and labels must be resolved from the
        doctype's meta.
        """
        try:
            report_doc = frappe.get_doc("Report", self.report)
        except Exception:
            logger.exception(
                f"Could not load Report doc | report={self.report} | name={self.name}"
            )
            return {}

        declared = {}

        def _add(fieldname, label, fieldtype=None, options=None):
            if not fieldname:
                return
            declared.setdefault(
                fieldname,
                {
                    "fieldname": fieldname,
                    "label": label or fieldname,
                    "fieldtype": fieldtype,
                    "options": options,
                },
            )

        # 1. columns child table (Query Report / Script Report)
        for row in report_doc.get("columns") or []:
            _add(row.get("fieldname"), row.get("label"),
                row.get("fieldtype"), row.get("options"))

        # 2. Report Builder -> json.fields = [[fieldname, doctype], ...]
        if report_doc.report_type == "Report Builder" and report_doc.get("json"):
            try:
                payload = report_doc.json
                if isinstance(payload, str):
                    payload = json.loads(payload)

                for entry in (payload or {}).get("fields") or []:
                    if isinstance(entry, (list, tuple)) and entry:
                        fieldname = entry[0]
                        doctype = entry[1] if len(entry) > 1 else report_doc.ref_doctype
                    elif isinstance(entry, dict):
                        fieldname = entry.get("fieldname")
                        doctype = entry.get("parent") or report_doc.ref_doctype
                    else:
                        continue

                    label = _REPORT_BUILDER_LABEL_OVERRIDES.get(fieldname)
                    fieldtype = None
                    options = None

                    if not label and doctype:
                        try:
                            meta = frappe.get_meta(doctype)
                            field = meta.get_field(fieldname)
                            if field:
                                label = field.label
                                fieldtype = field.fieldtype
                                options = field.options
                        except Exception:
                            logger.warning(
                                f"Could not resolve label for {doctype}.{fieldname}"
                            )

                    _add(fieldname, label, fieldtype, options)
            except Exception:
                logger.exception(
                    f"Could not parse Report Builder json | report={self.report}"
                )

        logger.info(
            f"Declared columns resolved | name={self.name} | "
            f"report={self.report} | count={len(declared)} | "
            f"labels={[v['label'] for v in list(declared.values())[:5]]}"
        )
        return declared
        
        
import frappe
from frappe.desk.query_report import run as run_report


"""
Generic Frappe report executor.

    from your_app.utils import get_report_data

    data = get_report_data("Accounts Receivable", {"company": "Acme"})
    data["columns"]   # ['customer', 'customer_name', 'outstanding', ...]
    data["data"]      # [{'customer': 'CUST-0001', ...}, ...]
    data["count"]     # 42
"""

import inspect
import frappe
from frappe import _
from frappe.utils import add_months, cint, getdate, today

# `get_fiscal_year` lives in erpnext.accounts.utils in current ERPNext builds.
# Older / trimmed benches may not expose it — fall back to a local shim.
try:
    from erpnext.accounts.utils import get_fiscal_year
except Exception:  # pragma: no cover - defensive for non-ERPNext benches
    get_fiscal_year = None

__all__ = ["get_report_data", "REPORT_SPECIFIC_DEFAULTS"]


# ---------------------------------------------------------------------------
# 1. Name-based defaults.
#
#    These are applied to *any* report that happens to use a filter with that
#    name. Extra keys are harmless for 99% of reports (they use filters.get()),
#    and they save us from the classic "report blows up because from_date is
#    missing" problem.
# ---------------------------------------------------------------------------

def _default_company():
    try:
        return (
            frappe.defaults.get_user_default("Company")
            or frappe.defaults.get_global_default("company")
            or frappe.db.get_single_value("Global Defaults", "default_company")
        )
    except Exception:
        return None


def _fiscal_year_range():
    """(start_date, end_date) of the fiscal year containing today."""
    try:
        fy = get_fiscal_year(today())
        # v13+ returns (name, start_date, end_date); older versions return a str
        if isinstance(fy, (list, tuple)) and len(fy) >= 3:
            return getdate(fy[1]), getdate(fy[2])
    except Exception:
        pass
    end = getdate(today())
    return add_months(end, -12), end


def _current_fiscal_year():
    try:
        fy = get_fiscal_year(today())
        return fy[0] if isinstance(fy, (list, tuple)) else fy
    except Exception:
        return None


COMMON_FILTER_DEFAULTS = {
    # organisation
    "company": _default_company,
    # "as on" style single dates (safe: reports that don't use them ignore them,
    # reports that DO use them get a sensible value, and they do NOT restrict
    # a vouchers-by-period style query)
    "report_date": today,
    "as_on_date": today,
    "as_on": today,
    # ageing buckets
    "range1": lambda: 30,
    "range2": lambda: 60,
    "range3": lambda: 90,
    "range4": lambda: 120,
    # NOTE: from_date / to_date / start_date / end_date / period_* / fiscal_year
    # were intentionally removed. They can silently restrict reports such as
    # Accounts Receivable / Payable to a window and produce empty results.
    # Add them per-report in REPORT_SPECIFIC_DEFAULTS or via extra_defaults.
}


# ---------------------------------------------------------------------------
# 2. Report-specific defaults.
#
#    Add entries here for reports that need a value which the generic layer
#    cannot guess. Keys are report names, values are {filter_name: value}.
#    Values may also be callables - they will be invoked at runtime.
# ---------------------------------------------------------------------------

_AGEING_BUCKETS = {
    "range1": 30,
    "range2": 60,
    "range3": 90,
    "range4": 120,
}

REPORT_SPECIFIC_DEFAULTS = {
    "Accounts Receivable": {
        **_AGEING_BUCKETS,
        "ageing_based_on": "Posting Date",
        "calculate_ageing_with": "Report Date",
        "show_future_payments": 0,
        "show_remarks": 0,
    },
    "Accounts Payable": {
        **_AGEING_BUCKETS,
        "ageing_based_on": "Posting Date",
        "calculate_ageing_with": "Report Date",
        "show_future_payments": 0,
        "show_remarks": 0,
    },
    "Accounts Receivable Summary": {
        **_AGEING_BUCKETS,
        "ageing_based_on": "Posting Date",
        "calculate_ageing_with": "Report Date",
    },
    "Accounts Payable Summary": {
        **_AGEING_BUCKETS,
        "ageing_based_on": "Posting Date",
        "calculate_ageing_with": "Report Date",
    },
    "General Ledger": {
        "group_by": "Group by Voucher (Consolidated)",
        "show_cancelled_entries": 0,
        "with_period_closing_entry": 1,
    },
    "Trial Balance": {
        "show_zero_values": 0,
    },
}


# ---------------------------------------------------------------------------
# 3. Public API
# ---------------------------------------------------------------------------

def get_report_data(
    report_name,
    filters=None,
    *,
    apply_defaults=True,
    extra_defaults=None,
    required_filters=None,
    strict=False,
    limit=None,
    ignore_prepared_report=True,
):
    """Execute ``report_name`` and return its data in a normalised structure.

    :param report_name:        Name of the ``Report`` document.
    :param filters:            Caller supplied filters (always win).
    :param apply_defaults:     Auto-fill missing filters (default ``True``).
    :param extra_defaults:     Per-call defaults, e.g. ``{"company": "Acme"}``.
                               Override report-specific + generic defaults.
    :param required_filters:   Escape hatch for Script Reports (whose filters
                               live in JS and cannot be introspected server
                               side). Either ``["company", "from_date"]`` or
                               ``[("company", "Acme"), "from_date"]``.
    :param strict:             Raise instead of logging when a filter marked
                               as required is still missing.
    :param limit:              Optional row limit (only passed if supported).
    :param ignore_prepared_report: Pass through to ``Report.get_data``.

    :returns: dict with keys
        ``report_name``, ``doctype``, ``report_type``, ``columns``,
        ``column_definitions``, ``filters``, ``data``, ``count``
        plus ``chart`` / ``report_summary`` / ``message`` when the report
        returns them.
    """
    filters = dict(filters or {})

    if not frappe.db.exists("Report", report_name):
        frappe.throw(_("Report {0} does not exist").format(report_name))

    report = frappe.get_doc("Report", report_name)

    if report.get("disabled"):
        frappe.throw(_("Report {0} is disabled").format(report_name))

    # ---- 1. discover the report's filters -------------------------------
    filter_definitions = _get_filter_definitions(report, report_name, required_filters)

    # ---- 2. fill in whatever is missing ---------------------------------
    if apply_defaults:
        if apply_defaults:
            _apply_defaults(
                report_name,
                filters,
                filter_definitions,
                extra_defaults,
                report_type=report.report_type,      # <-- MUST be here
            )

    # ---- 3. sanity check -------------------------------------------------
    missing = _missing_required_filters(filters, filter_definitions)
    if missing:
        message = _("Report {0} is missing required filter(s): {1}").format(
            report_name, ", ".join(missing)
        )
        if strict:
            frappe.throw(message)
        frappe.logger("report").warning("%s | filters=%s", message, filters)

    # ---- 4. run ----------------------------------------------------------
    raw_result = _execute_report(
        report, report_name, filters, limit, ignore_prepared_report
    )

    # ---- 5. normalise ----------------------------------------------------
    return _normalise(raw_result, report, report_name, filters)


# ---------------------------------------------------------------------------
# 4. Filter discovery
# ---------------------------------------------------------------------------

def _get_filter_definitions(report, report_name, required_filters=None):
    """Best-effort collection of the filters a report understands.

    Sources, in order of precedence:
      a) the ``filters`` child table on the Report document
         (Query Reports and Report Builder reports),
      b) ``frappe.desk.query_report.get_report_filters`` (Script Reports on
         builds that expose it),
      c) whatever the caller declared via ``required_filters``.
    """
    definitions = {}

    # (a) filters declared on the Report document itself
    for row in report.get("filters") or []:
        fieldname = row.get("fieldname") or row.get("label")
        if not fieldname:
            continue
        definitions[fieldname] = {
            "fieldname": fieldname,
            "label": row.get("label") or fieldname,
            "fieldtype": row.get("fieldtype") or "Data",
            "options": row.get("options"),
            "reqd": cint(row.get("reqd")),
            "default": row.get("default"),
        }

    # (b) Script Reports - not available on every Frappe version
    try:
        from frappe.desk.query_report import get_report_filters

        for row in get_report_filters(report_name) or []:
            fieldname = row.get("fieldname")
            if fieldname and fieldname not in definitions:
                definitions[fieldname] = {
                    "fieldname": fieldname,
                    "label": row.get("label") or fieldname,
                    "fieldtype": row.get("fieldtype") or "Data",
                    "options": row.get("options"),
                    "reqd": cint(row.get("reqd")),
                    "default": row.get("default"),
                }
    except Exception:
        # Function/endpoint not present - not fatal.
        pass

    # (c) caller-declared requirements
    for item in required_filters or []:
        if isinstance(item, str):
            fieldname, default = item, None
        elif isinstance(item, (list, tuple)) and item:
            fieldname = item[0]
            default = item[1] if len(item) > 1 else None
        else:
            continue

        definition = definitions.setdefault(
            fieldname,
            {
                "fieldname": fieldname,
                "label": fieldname,
                "fieldtype": "Data",
                "options": None,
                "default": None,
                "reqd": 0,
            },
        )
        definition["reqd"] = 1
        if default is not None:
            definition["default"] = default

    return definitions


def _resolve_default(value):
    """Defaults may be plain values or zero-arg callables."""
    if callable(value):
        try:
            return value()
        except Exception:
            return None
    return value


def _apply_defaults(report_name, filters, definitions, extra_defaults=None,
                    report_type=None):
    """
    Mutate ``filters`` in place, filling every blank / None value.

    Priority (lowest -> highest):
        generic name based defaults
        -> defaults declared on the report's own filter definitions
        -> REPORT_SPECIFIC_DEFAULTS
        -> extra_defaults passed to this call
        -> filters passed by the caller (never overwritten)

    Report Builder reports get an additional guard: generic / report-specific
    defaults are only applied for fieldnames the report actually declares,
    because ``frappe.get_list`` will turn unknown keys into SQL columns.
    """
    declared = set(definitions.keys())
    layer = {}

    # 1. Generic defaults
    if report_type == "Report Builder":
        # Restrictive: only apply defaults the report actually declares.
        for fieldname, value in COMMON_FILTER_DEFAULTS.items():
            if fieldname in declared:
                layer[fieldname] = value
    else:
        # Script / Query reports: unknown filter keys are harmless.
        layer.update(COMMON_FILTER_DEFAULTS)

    # 2. Defaults declared on the Report doc itself
    for fieldname, definition in definitions.items():
        default = definition.get("default")
        if default not in (None, ""):
            layer[fieldname] = default

    # 3. Report-specific defaults (already namespaced per report)
    for fieldname, value in (REPORT_SPECIFIC_DEFAULTS.get(report_name) or {}).items():
        if fieldname in declared:
            layer[fieldname] = value

    # 4. Caller-supplied extra defaults
    layer.update(extra_defaults or {})

    for fieldname, value in layer.items():
        if filters.get(fieldname) not in (None, ""):
            continue
        resolved = _resolve_default(value)
        if resolved is not None and resolved != "":
            filters[fieldname] = resolved

    if "start_date" in declared and filters.get("start_date") in (None, "") and filters.get("from_date"):
        filters["start_date"] = filters["from_date"]
    if "end_date" in declared and filters.get("end_date") in (None, "") and filters.get("to_date"):
        filters["end_date"] = filters["to_date"]
    if "period_start_date" in declared and filters.get("period_start_date") in (None, "") and filters.get("from_date"):
        filters["period_start_date"] = filters["from_date"]
    if "period_end_date" in declared and filters.get("period_end_date") in (None, "") and filters.get("to_date"):
        filters["period_end_date"] = filters["to_date"]
    if "report_date" in declared and filters.get("report_date") in (None, "") and filters.get("to_date"):
        filters["report_date"] = filters["to_date"]
    if "as_on_date" in declared and filters.get("as_on_date") in (None, "") and filters.get("to_date"):
        filters["as_on_date"] = filters["to_date"]


def _missing_required_filters(filters, definitions):
    missing = []
    for fieldname, definition in definitions.items():
        if not (definition.get("reqd") or definition.get("mandatory")):
            continue
        value = filters.get(fieldname)
        if value is None or value == "":
            missing.append(fieldname)
    return missing


# ---------------------------------------------------------------------------
# 5. Execution
# ---------------------------------------------------------------------------

def _execute_report(report, report_name, filters, limit=None,
                    ignore_prepared_report=True):
    """Call ``Report.get_data`` with only the kwargs that build supports."""

    # ------------------------------------------------------------------
    # LAST-LINE DEFENCE for Report Builder reports.
    #
    # Report Builder is executed via frappe.get_list(doctype, filters=...),
    # which turns *every* key in the filters dict into a SQL predicate
    # ``tabX.field = value``.  Any key that is not a real column on the
    # report's DocType raises:
    #     Unknown column 'tabX.field' in 'WHERE'
    #
    # Upstream gating (get_filters / _apply_defaults) can miss this when
    # the report type isn't threaded through, when get_valid_columns()
    # raises, or when a caller passes filters directly.  Do the check
    # here so no path can bypass it.
    # ------------------------------------------------------------------
    if report.report_type == "Report Builder":
        ref_doctype = report.ref_doctype
        if ref_doctype:
            try:
                meta = frappe.get_meta(ref_doctype)
                valid = {f.fieldname for f in meta.fields if f.fieldname}
                valid.add("name")
                valid.update(_REPORT_BUILDER_PSEUDO_FILTERS)

                dropped = sorted(k for k in filters if k not in valid)
                if dropped:
                    ...
                    filters = {k: v for k, v in filters.items() if k in valid}
            except Exception:
                logger.exception(
                    f"Could not validate filters against {ref_doctype} | "
                    f"name={report_name} — passing through unchanged"
                )

        if report.get("json"):
            try:
                params = json.loads(report.json)
                saved_filters = params.get("filters") or []
                cleaned_filters = []
                for sf in saved_filters:
                    if isinstance(sf, (list, tuple)) and len(sf) >= 2:
                        fn = sf[1]
                        if fn in filters:
                            continue
                    cleaned_filters.append(sf)
                params["filters"] = cleaned_filters
                report.json = json.dumps(params)
            except Exception:
                pass

    # Log exactly what is about to be executed, so future failures are
    # one grep away.
    logger.info(
        f"Executing report | name={report_name} | "
        f"type={report.report_type} | doctype={report.ref_doctype} | "
        f"filters={filters}"
    )

    wanted = {
        "filters": filters,
        "ignore_prepared_report": ignore_prepared_report,
    }
    if limit is not None:
        wanted["limit"] = limit

    try:
        accepted = inspect.signature(report.get_data).parameters
        kwargs = {key: value for key, value in wanted.items() if key in accepted}
    except (TypeError, ValueError):
        kwargs = {"filters": filters}

    kwargs.setdefault("filters", filters)

    try:
        return report.get_data(**kwargs)

    except KeyError as exc:
        key = exc.args[0] if exc.args else "unknown"
        message = _(
            "Report {0} could not run because the filter '{1}' was not supplied. "
            "Pass it explicitly, add it to `extra_defaults`, or declare it in "
            "`required_filters`."
        ).format(report_name, key)
        frappe.log_error(
            "{0}\n\nFilters: {1}\n\n{2}".format(
                message, filters, frappe.get_traceback()
            ),
            "get_report_data",
        )
        raise frappe.ValidationError(message) from exc

    except Exception:
        frappe.log_error(
            "get_data failed for {0}\nFilters: {1}\n\n{2}".format(
                report_name, filters, frappe.get_traceback()
            ),
            "get_report_data",
        )
        raise


# ---------------------------------------------------------------------------
# 6. Normalisation
# ---------------------------------------------------------------------------

def _normalise(raw_result, report, report_name, filters):
    meta = {}

    if isinstance(raw_result, tuple):
        columns = raw_result[0] if len(raw_result) > 0 else []
        data = raw_result[1] if len(raw_result) > 1 else []
    elif isinstance(raw_result, dict):
        columns = raw_result.get("columns") or []
        data = raw_result.get("result")
        if data is None:
            data = raw_result.get("data") or []
        meta = {
            key: value
            for key, value in raw_result.items()
            if key not in ("columns", "result", "data")
        }
    else:
        raise TypeError(
            "Unexpected result type for report {0}: {1}".format(
                report_name, type(raw_result)
            )
        )

    column_names, column_definitions = _normalise_columns(columns)
    rows = _normalise_rows(data, column_names)

    payload = {
        "report_name": report_name,
        "doctype": report.ref_doctype,
        "report_type": report.report_type,
        "columns": column_names,
        "column_definitions": column_definitions,
        "filters": dict(filters),
        "data": rows,
        "count": len(rows),
    }

    # chart / report_summary / message / skip_total_row ...
    for key, value in meta.items():
        payload.setdefault(key, value)

    return payload


def _normalise_columns(raw_columns):
    """Return (list_of_fieldnames, list_of_column_dicts)."""
    names = []
    definitions = []

    for col in raw_columns or []:
        if isinstance(col, dict):
            fieldname = col.get("fieldname") or col.get("label") or col.get("name")
            names.append(fieldname)
            definitions.append(
                {
                    "fieldname": fieldname,
                    "label": col.get("label") or fieldname,
                    "fieldtype": col.get("fieldtype") or "Data",
                    "options": col.get("options"),
                    "width": col.get("width"),
                }
            )

        elif isinstance(col, str):
            # Legacy query-report format: "Label:fieldname:fieldtype/options:width"
            parts = col.split(":")
            if len(parts) >= 3:
                label, fieldname = parts[0].strip(), parts[1].strip()
                fieldtype = parts[2].strip() or "Data"
                width = parts[3].strip() if len(parts) > 3 else None
            else:
                fieldname = parts[0].strip()
                label, fieldtype, width = fieldname, "Data", None

            names.append(fieldname)
            definitions.append(
                {
                    "fieldname": fieldname,
                    "label": label or fieldname,
                    "fieldtype": fieldtype,
                    "options": None,
                    "width": width,
                }
            )

        else:
            names.append(str(col))
            definitions.append(
                {
                    "fieldname": str(col),
                    "label": str(col),
                    "fieldtype": "Data",
                    "options": None,
                    "width": None,
                }
            )

    # Duplicate fieldnames would silently clobber each other in dict(zip(...))
    names = _make_unique(names)
    for definition, unique_name in zip(definitions, names):
        definition["fieldname"] = unique_name

    return names, definitions


def _make_unique(names):
    seen = {}
    result = []
    for name in names:
        if name in seen:
            seen[name] += 1
            result.append("{0}_{1}".format(name, seen[name]))
        else:
            seen[name] = 0
            result.append(name)
    return result


def _normalise_rows(raw_data, column_names):
    rows = []
    for row in raw_data or []:
        if isinstance(row, dict):
            rows.append(dict(row))
        elif isinstance(row, (list, tuple)):
            rows.append(
                {
                    name: (row[index] if index < len(row) else None)
                    for index, name in enumerate(column_names)
                }
            )
        else:
            # Scalars / totals rows are passed through untouched
            rows.append(row)
    return rows


import frappe
import json
import os
import re

@frappe.whitelist()
def get_report_filters(report_name):
    report = frappe.get_doc("Report", report_name)
    
    # 1. Query Report / Report Builder (Stored in Database)
    if report.report_type in ["Query Report", "Report Builder"]:
        if report.filters:
            return json.loads(report.filters) if isinstance(report.filters, str) else report.filters
        return []
        
    # 2. Script Report (Stored in JS file or Database)
    if report.report_type == "Script Report":
        content = ""
        
        # A. Check if it's a custom report stored in the Database
        if report.javascript:
            content = report.javascript
        else:
            # B. Check the file system (Standard ERPNext reports)
            app = frappe.local.module_app.get(frappe.scrub(report.module))
            if app:
                js_file_path = frappe.get_app_path(
                    app, report.module, "report", 
                    frappe.scrub(report_name), frappe.scrub(report_name) + ".js"
                )
                if os.path.exists(js_file_path):
                    with open(js_file_path, "r") as f:
                        content = f.read()
                        
        if not content:
            return []
            
        # 3. Extract the "filters: [ ... ]" array using bracket counting
        match = re.search(r'filters\s*:\s*(\[)', content)
        if not match:
            return []
            
        start_idx = match.start(1)
        bracket_count = 0
        end_idx = -1
        
        for i in range(start_idx, len(content)):
            if content[i] == '[':
                bracket_count += 1
            elif content[i] == ']':
                bracket_count -= 1
                if bracket_count == 0:
                    end_idx = i + 1
                    break
                    
        if end_idx == -1:
            return []
            
        filters_str = content[start_idx:end_idx]
        
        # 4. Extract individual filter blocks { ... }
        # This regex finds everything between { and }
        blocks = re.findall(r'\{([^{}]+)\}', filters_str)
        parsed_filters = []
        
        for block in blocks:
            f = {}
            
            # Extract fieldname
            m = re.search(r'fieldname\s*:\s*[\'"]([^\'"]+)[\'"]', block)
            if m: f['fieldname'] = m.group(1)
            
            # Extract label (handles __("Label") and "Label")
            m = re.search(r'label\s*:\s*(?:__\([\'"]([^\'"]+)[\'"]\)|[\'"]([^\'"]+)[\'"])', block)
            if m: f['label'] = m.group(1) or m.group(2)
            
            # Extract fieldtype
            m = re.search(r'fieldtype\s*:\s*[\'"]([^\'"]+)[\'"]', block)
            if m: f['fieldtype'] = m.group(1)
            
            # Extract options
            m = re.search(r'options\s*:\s*[\'"]([^\'"]+)[\'"]', block)
            if m: f['options'] = m.group(1)
            
            # Extract reqd
            m = re.search(r'reqd\s*:\s*([0-9]+|true|false)', block, re.IGNORECASE)
            if m:
                val = m.group(1).lower()
                f['reqd'] = 1 if val in ['1', 'true'] else 0
                
            # Extract default (handles strings and JS function calls)
            m = re.search(r'default\s*:\s*(?:[\'"]([^\'"]*)[\'"]|([a-zA-Z0-9_.]+\(.*?\)))', block)
            if m:
                if m.group(1) is not None:
                    f['default'] = m.group(1)
                elif m.group(2) is not None:
                    func_call = m.group(2)
                    # Translate common JS functions to Python
                    if "get_today" in func_call:
                        f['default'] = frappe.utils.today()
                    elif "get_user_default" in func_call:
                        def_match = re.search(r'get_user_default\([\'"]([^\'"]+)[\'"]\)', func_call)
                        if def_match:
                            f['default'] = frappe.defaults.get_user_default(def_match.group(1)) or ""
                    else:
                        f['default'] = "" # Fallback for unknown functions
                        
            # Only add to list if it has a fieldname
            if f.get('fieldname'):
                parsed_filters.append(f)
                
        return parsed_filters
    
    
# Frappe appends these to every query-report result. They are not part of
# the report definition and should not end up in the exported file unless
# the report author explicitly added them.
_FRAPPE_AUTO_COLUMNS = {
    "docstatus", "modified", "modified_by", "creation", "owner", "idx",
}


# Report Builder stores columns as [fieldname, doctype] pairs in json.fields.
# These three are auto-injected by Frappe for every Report Builder report —
# the report author didn't add them, and they're almost never wanted in an
# export.  Drop them regardless of whether the report's fields list contains
# them.
_REPORT_BUILDER_NOISE_FIELDS = {
    "docstatus", "modified", "modified_by",
    "creation", "owner", "idx",
}

# Report Builder pseudo-filters that are valid keys in the filters dict but
# are NOT columns on the DocType.  The column whitelist must not strip them.
_REPORT_BUILDER_PSEUDO_FILTERS = {"group_by", "sort_by", "order_by"}

# Labels for fields that don't live in DocType meta.
_REPORT_BUILDER_LABEL_OVERRIDES = {
    "name": "ID",
}