import frappe
@frappe.whitelist()
def get_reference_name(reference_name, reference_type):
    ref_data = frappe.get_value(reference_type, reference_name, "branch")
    return ref_data


def before_save(doc, method=None):
    if doc.reference_name and doc.reference_type:
        ref_data = frappe.get_value(doc.reference_type, doc.reference_name, "branch")
        doc.branch = ref_data
        doc.refresh_field("branch")
        