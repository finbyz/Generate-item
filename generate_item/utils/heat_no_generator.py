import frappe
from frappe import _
from frappe.utils import cint, flt

@frappe.whitelist()
def generate_heat_numbers(docname, series_value, start_value, end_value,
                          uom, stock_uom, received_qty, rejected_qty,
                          received_qty_in_stock_uom, rejected_qty_in_stock_uom):
    
    series_value = series_value
    start_value  = cint(start_value)
    end_value    = cint(end_value)

    if not series_value:
        frappe.throw(_("Series Value is required to generate heat numbers."))
    if end_value < start_value:
        frappe.throw(_("End Value must be greater than or equal to Start Value."))

    uom_is_same = (uom == stock_uom) if (uom and stock_uom) else True

    if uom_is_same:
        received_qty = flt(received_qty)
        rejected_qty = flt(rejected_qty)
    else:
        received_qty = flt(received_qty_in_stock_uom)
        rejected_qty = flt(rejected_qty_in_stock_uom)

    total_qty = flt(received_qty) - flt(rejected_qty)
    if total_qty <= 0:
        frappe.throw(_("Total quantity (received − rejected) must be greater than 0."))

    full_range  = (end_value - start_value) + 1
    total_qty_i = int(total_qty)

    qty_less_than_range = full_range > total_qty_i
    row_count           = min(full_range, total_qty_i)

    base_qty  = int(total_qty_i // row_count)
    remainder = int(total_qty_i % row_count)

    # Still need the doc to save the child rows
    doc = frappe.get_doc("Quality Inspection", docname)
    doc.set("heat_no", [])

    for i in range(row_count):
        num     = start_value + i
        heat_no = f"{series_value}{num}"
        qty     = base_qty + (1 if i < remainder else 0)
        doc.append("heat_no", {"heat_no": heat_no, "qty": qty})

    doc.save(ignore_permissions=True)

    if qty_less_than_range:
        message = (
            f"Your range ({start_value} to {end_value}) has {full_range} numbers, "
            f"but your quantity is only {total_qty_i}. "
            f"Generated {row_count} heat numbers instead of {full_range}."
        )
        warn = True
    else:
        message = f"Generated {row_count} heat numbers. Total qty distributed: {total_qty_i}."
        warn = False

    return {
        "message":             message,
        "row_count":           row_count,
        "total_qty":           total_qty_i,
        "full_range":          full_range,
        "qty_less_than_range": warn,
    }
