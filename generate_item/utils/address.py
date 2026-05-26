import frappe
from frappe import _

def validate(doc, method=None):
    """
    Validate PAN embedded in GSTIN matches the PAN on linked Supplier/Customer.
    GSTIN format: SS AAAAA NNNN A N Z C  (positions 3-12 = PAN, 0-indexed 2:12)
    """
    
    VALID_LINK_TYPES = ["Supplier", "Customer"]
    
    if not doc.gstin:
        return  # No GSTIN to validate against

    # Extract PAN from GSTIN (characters at index 2 to 11, i.e., positions 3–12)
    pan_in_gstin = doc.gstin[2:12].upper()

    for link in doc.get("links", []):
        link_doctype = (link.link_doctype or "").strip()

        # Only validate for Supplier / Customer links
        if link_doctype not in VALID_LINK_TYPES:
            continue

        link_name = link.link_name
        if not link_name:
            continue

        # Fetch the linked document's PAN field
        try:
            linked_doc = frappe.get_doc(link_doctype, link_name)
        except frappe.DoesNotExistError:
            frappe.throw(
                _("{0} <b>{1}</b> does not exist. Cannot validate PAN against GSTIN.").format(
                    link_doctype, link_name
                )
            )
            continue

        pan_on_record = (getattr(linked_doc, "pan", None) or "").strip().upper()

        if not pan_on_record:
            frappe.msgprint(
                msg=_(
                    "PAN is not set on {0} <b>{1}</b>. "
                    "Cannot validate against GSTIN <b>{2}</b>.<br><br>"
                    "Please update the PAN on the {0} record first."
                ).format(link_doctype, link_name, doc.gstin),
                title=_("PAN Missing — Validation Skipped"),
                indicator="orange",
            )
            continue

        if pan_in_gstin != pan_on_record:
            frappe.throw(
                msg=_(
                    "<b>PAN Mismatch Detected</b><br><br>"
                    "The PAN embedded in GSTIN <b>{gstin}</b> "
                    "(<b>{pan_gstin}</b>) "
                    "does not match the PAN on {doctype} <b>{name}</b> "
                    "(<b>{pan_record}</b>).<br><br>"
                    "Please verify:<br>"
                    "• The correct GSTIN has been entered, <b>or</b><br>"
                    "• The PAN on the {doctype} record is up to date."
                ).format(
                    gstin=doc.gstin,
                    pan_gstin=pan_in_gstin,
                    doctype=link_doctype,
                    name=link_name,
                    pan_record=pan_on_record,
                ),
                title=_("GSTIN / PAN Mismatch"),
            )
        # else: PAN matches — validation passed silently