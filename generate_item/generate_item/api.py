import json
import copy
import traceback
from io import BytesIO

import frappe
from frappe import _
from frappe.desk.query_report import get_column_as_dict, run
from frappe.utils import cint, cstr, flt, get_datetime
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, Side
from openpyxl.utils import get_column_letter
from frappe.utils import strip_html

DATE_FIELDTYPES = {"Date"}
DATETIME_FIELDTYPES = {"Datetime"}
NUMERIC_FIELDTYPES = {"Int", "Float", "Currency", "Percent"}


class _ReportFilters(frappe._dict):
    """frappe._dict that is always truthy, even when empty.
    Supports .get(), .attr, and missing keys -> None."""

    def __bool__(self):
        return True


def _to_report_filters(value):
    if isinstance(value, dict):
        return _ReportFilters({k: _to_report_filters(v) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return [_to_report_filters(v) for v in value]
    return value


def normalize_report_filters(raw):
    """Return a NEW filters object. Never mutates raw. Raises on invalid input."""
    if raw is None or raw == "":
        return _ReportFilters()
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError as e:
            frappe.throw(_("Report filters are not valid JSON: {0}").format(e))
        if raw is None:
            return _ReportFilters()
    if not isinstance(raw, dict):
        frappe.throw(_("Report filters must be an object, got {0}.").format(type(raw).__name__))
    return _to_report_filters(copy.deepcopy(dict(raw)))


@frappe.whitelist()
def export_query_report(form_params):
    """
    Export ANY Query Report / Script Report to a clean Excel
    workbook without formula or colors, and stream it
    straight back as a browser download. No File doc is created.
    """

    if isinstance(form_params, str):
        form_params = json.loads(form_params)

    if not isinstance(form_params, dict):
        frappe.throw(_("Invalid parameters."))

    form_params = frappe._dict(form_params)
    report_name = form_params.get("report_name")
    if not report_name:
        frappe.throw(_("report_name is required."))

    # CHANGE 1: normalized copy, supports filters.x and filters.get("x")
    filters = normalize_report_filters(form_params.get("filters"))

    # Normalize date_range if passed as a string or if from_date/to_date are passed
    if "date_range" in filters and isinstance(filters["date_range"], str):
        try:
            filters["date_range"] = json.loads(filters["date_range"])
        except ValueError:
            if "," in filters["date_range"]:
                filters["date_range"] = [d.strip() for d in filters["date_range"].split(",")]
            elif " to " in filters["date_range"]:
                filters["date_range"] = [d.strip() for d in filters["date_range"].split(" to ")]

    if not filters.get("date_range"):
        if filters.get("from_date") and filters.get("to_date"):
            filters["date_range"] = [filters.get("from_date"), filters.get("to_date")]
        elif report_name in ("GST Sales Register", "GST Purchase Register"):
            from frappe.utils import add_months, get_first_day, get_last_day, today

            last_month = add_months(today(), -1)
            filters["date_range"] = [str(get_first_day(last_month)), str(get_last_day(last_month))]

    if report_name in ("GST Sales Register", "GST Purchase Register"):
        if not filters.get("company"):
            filters["company"] = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value(
                "Global Defaults", "default_company"
            )

    # CHANGE 2: ignore_prepared_report=True runs the report live with the real filters.
    # CHANGE 3: errors are logged and shown, not swallowed.
    try:
        data = run(
            report_name,
            filters,
            ignore_prepared_report=True,
            are_default_filters=False,
        )
    except (frappe.PermissionError, frappe.ValidationError):
        raise
    except Exception as e:
        frappe.log_error(message=traceback.format_exc(), title=f"Excel export failed: {report_name}")
        frappe.throw(
            _("Could not export report {0}: {1}: {2}").format(report_name, type(e).__name__, e),
            title=_("Excel export failed"),
        )
    data = frappe._dict(data)

    # CHANGE 3 (cont.): never produce a silent blank sheet
    if "columns" not in data:
        frappe.throw(
            _("Report {0} returned no columns (keys: {1}).").format(
                report_name, ", ".join(data.keys())
            )
        )

    columns = data.get("columns") or []
    rows = data.get("result") or []

    col_dicts = [get_column_as_dict(col) for col in columns]
    fieldnames = [c.get("fieldname") for c in col_dicts]
    labels = [c.get("label") or c.get("fieldname") for c in col_dicts]
    fieldtypes = [c.get("fieldtype") or "Data" for c in col_dicts]

    wb = Workbook()
    ws = wb.active
    ws.title = report_name[:31]

    # ---------------- clean theme (no colors / no fills) ----------------
    header_font = Font(bold=True, size=10)
    thin = Side(style="thin", color="000000")
    thin_border = Border(left=thin, right=thin, top=thin, bottom=thin)
    center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    left_align = Alignment(horizontal="left", vertical="center")
    right_align = Alignment(horizontal="right", vertical="center")

    n_cols = max(len(labels), 1)
    last_col_letter = get_column_letter(n_cols)

    # ---------------- header row ----------------
    header_row_idx = 1
    for idx, label in enumerate(labels, start=1):
        cell = ws.cell(row=header_row_idx, column=idx, value=label)
        cell.font = header_font
        cell.alignment = center
        cell.border = thin_border
    ws.row_dimensions[header_row_idx].height = 20

    max_width = [len(str(lbl)) + 4 for lbl in labels]

    # ---------------- data rows ----------------
    start_data_row = header_row_idx + 1
    for r_idx, row in enumerate(rows):
        if isinstance(row, dict):
            values = [row.get(fn, "") for fn in fieldnames]
        else:
            values = [row[i] if i < len(row) else "" for i in range(len(fieldnames))]

        excel_row_idx = start_data_row + r_idx

        for c_idx, (value, ftype) in enumerate(zip(values, fieldtypes), start=1):
            if isinstance(value, bool):
                value = "Yes" if value else "No"
            if value is None:
                value = ""

            cell = ws.cell(row=excel_row_idx, column=c_idx)

            if ftype in ("Currency", "Float") and isinstance(value, (int, float)):
                cell.value = flt(value, 2)
                cell.number_format = "#,##0.00"
                cell.alignment = right_align
            elif ftype == "Percent" and isinstance(value, (int, float)):
                cell.value = flt(value, 2) / 100
                cell.number_format = "0.00%"
                cell.alignment = right_align
            elif ftype == "Int" and isinstance(value, (int, float)):
                cell.value = cint(value)
                cell.number_format = "#,##0"
                cell.alignment = right_align
            elif ftype in DATE_FIELDTYPES and value:
                try:
                    cell.value = get_datetime(value).date()
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
                if isinstance(value, str) and value.startswith("="):
                    cell.value = f"'{value}"
                else:
                    cell.value = value
                cell.alignment = left_align

            cell.border = thin_border

            text_value = cstr(value)
            if len(text_value) + 2 > max_width[c_idx - 1]:
                max_width[c_idx - 1] = min(len(text_value) + 2, 45)

    # ---------------- column widths ----------------
    for idx, width in enumerate(max_width, 1):
        ws.column_dimensions[get_column_letter(idx)].width = min(max(width, 10), 45)

    # ---------------- freeze header row ----------------
    ws.freeze_panes = f"A{start_data_row}"

    # ---------------- direct download, no File doc ----------------
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    filename = frappe.scrub(report_name) + ".xlsx"
    frappe.local.response.filename = filename
    frappe.local.response.filecontent = buffer.getvalue()
    frappe.local.response.type = "download"
    frappe.local.response.content_type = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )