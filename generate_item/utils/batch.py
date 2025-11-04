import frappe

def before_save(doc, method):
    if not doc.branch and doc.reference_doctype == "Sales Order" and doc.reference_name:
        branch = frappe.get_value("Sales Order", doc.reference_name, "branch")
        if branch:
            doc.branch = branch
