import frappe

def validate(doc, method):
    for i in doc.items:
        if i.rate == 0:
            frappe.throw(f"Please enter a valid rate for item in line No. {i.idx}. The rate cannot be 0.",
                         title="Zero Rate Found")