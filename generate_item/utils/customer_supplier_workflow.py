# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint


CS_SETTINGS_DOCTYPE = "Customer Supplier Workflow Settings"

STATUS_DRAFT = "Draft"
STATUS_PENDING_L1 = "Pending L1 Approval"
STATUS_PENDING_FINAL = "Pending Final Approval"
STATUS_APPROVED = "Approved"

CF_BRANCH = "branch"
CF_APPROVAL_STATUS = "cs_approval_status"

_APPROVAL_STATUS_OPTIONS = "\n".join(
    [STATUS_DRAFT, STATUS_PENDING_L1, STATUS_PENDING_FINAL, STATUS_APPROVED]
)


# Frappe document hooks (registered in hooks.py) 
def validate_customer(doc, method=None):
    """validate hook for the Customer DocType."""
    _validate_cs_doc(doc, doctype_key="customer")


def validate_supplier(doc, method=None):
    """validate hook for the Supplier DocType."""
    _validate_cs_doc(doc, doctype_key="supplier")


def set_cs_onload(doc, method=None):
    """onload hook — push the approval control payload to the form so the
    first render does not need an extra server round-trip."""
    doc.set_onload("cs_approval_control", _build_approval_control(doc))


# Whitelisted API (called by JS action buttons) 
@frappe.whitelist()
def get_approval_control(doctype, docname):
    """Return the current approval control payload for a form refresh."""
    _doctype_key(doctype)
    doc = frappe.get_doc(doctype, docname)
    doc.check_permission("read")
    return _build_approval_control(doc)


@frappe.whitelist()
def submit_for_l1_approval(doctype, docname):
    """Draft → Pending L1 Approval.
    Called by a user with the 'Who Create' role."""
    doctype_key = _doctype_key(doctype)
    doc = frappe.get_doc(doctype, docname)
    settings = _get_settings()

    _assert_workflow_enabled(settings, doctype_key)
    _assert_status(doc, STATUS_DRAFT, "submit for L1 Approval")

    if not _can_bypass_approval(settings):
        rule = _get_branch_rule(doc, settings, doctype_key)
        _assert_has_role(
            rule.who_create,
            _("Only users with role {0} can submit this {1} for L1 Approval.").format(
                frappe.bold(rule.who_create), doctype
            ),
        )

    _advance_status(doc, STATUS_PENDING_L1)
    return {"new_status": STATUS_PENDING_L1}


@frappe.whitelist()
def l1_approve(doctype, docname):
    """Pending L1 Approval → Pending Final Approval.
    Called by a user with the L1 Approver role."""
    doctype_key = _doctype_key(doctype)
    doc = frappe.get_doc(doctype, docname)
    settings = _get_settings()

    _assert_workflow_enabled(settings, doctype_key)
    _assert_status(doc, STATUS_PENDING_L1, "give L1 Approval")

    if not _can_bypass_approval(settings):
        rule = _get_branch_rule(doc, settings, doctype_key)
        _assert_has_role(
            rule.l1_approver,
            _("Only users with role {0} can give L1 Approval for this {1}.").format(
                frappe.bold(rule.l1_approver), doctype
            ),
        )

    _advance_status(doc, STATUS_PENDING_FINAL)
    return {"new_status": STATUS_PENDING_FINAL}


@frappe.whitelist()
def final_approve(doctype, docname):
    """Pending Final Approval → Approved.
    Called by a user with the Final Approver role.
    Sets disabled = 0 to activate the record in transactions."""
    doctype_key = _doctype_key(doctype)
    doc = frappe.get_doc(doctype, docname)
    settings = _get_settings()

    _assert_workflow_enabled(settings, doctype_key)
    _assert_status(doc, STATUS_PENDING_FINAL, "give Final Approval")

    if not _can_bypass_approval(settings):
        rule = _get_branch_rule(doc, settings, doctype_key)
        _assert_has_role(
            rule.final_approver,
            _("Only users with role {0} can give Final Approval for this {1}.").format(
                frappe.bold(rule.final_approver), doctype
            ),
        )

    _advance_status(doc, STATUS_APPROVED)
    return {"new_status": STATUS_APPROVED}


#  Core validate logic 
def _validate_cs_doc(doc, doctype_key):
    """Main validate handler shared by Customer and Supplier.

    1. Guard: exit early when the workflow is not enabled for this doctype.
    2. Auto-create required custom fields when the setting flag is on.
    3. New records with an active branch rule require the 'Who Create' role.
    4. New records without a matching rule save as Draft/disabled.
    5. Existing records: prevent manual tampering of cs_approval_status.
    6. Sync the standard `disabled` flag to reflect the current status.
    """
    settings = _get_settings()
    if not _is_workflow_active(settings, doctype_key):
        return

    _ensure_custom_fields(doc.doctype, settings, doctype_key)
    _ensure_disabled_field_available(doc.doctype)
    _validate_branch_selected(doc)

    user_roles = _get_user_roles()
    if doc.is_new():
        _validate_new_record(doc, settings, doctype_key, user_roles)
    elif not doc.flags.in_cs_approval_transition:
        _guard_status_tampering(doc)

    _sync_disabled_flag(doc)


def _validate_new_record(doc, settings, doctype_key, user_roles):
    """Enforce creator role only when an active branch rule exists."""
    rule = _find_branch_rule(doc, settings, doctype_key)
    if not rule:
        doc.set(CF_APPROVAL_STATUS, STATUS_DRAFT)
        return

    if rule.who_create not in user_roles:
        frappe.throw(
            _("Only users with role {0} can create a new {1}.").format(
                frappe.bold(rule.who_create), doc.doctype
            ),
            frappe.PermissionError,
        )

    doc.set(CF_APPROVAL_STATUS, STATUS_DRAFT)


def _ensure_disabled_field_available(doctype):
    field = frappe.get_meta(doctype).get_field("disabled")
    if not field or field.fieldtype != "Check":
        frappe.throw(
            _("{0} must have a standard {1} Check field for approval workflow.").format(
                doctype, frappe.bold("Disabled")
            ),
            frappe.ValidationError,
        )


def _validate_branch_selected(doc):
    if not doc.get(CF_BRANCH):
        frappe.throw(
            _("Please select a {0} before saving this {1}.").format(
                frappe.bold("Branch"), doc.doctype
            ),
            frappe.ValidationError,
        )


def _guard_status_tampering(doc):
    """Revert any manual change to cs_approval_status made through the form.
    Status can only advance via the whitelisted API methods."""
    db_status = frappe.db.get_value(doc.doctype, doc.name, CF_APPROVAL_STATUS) or STATUS_DRAFT
    if _current_status(doc) != db_status:
        doc.set(CF_APPROVAL_STATUS, db_status)


#  Approval control payload (consumed by the JS frontend)
def _build_approval_control(doc):
    """Return a dict that tells the form which action buttons to render and
    what the current workflow status is."""
    doctype_key = _doctype_key(doc.doctype)
    settings = _get_settings()

    if not _is_workflow_active(settings, doctype_key):
        return {"enabled": False}

    current = _current_status(doc)
    user_roles = _get_user_roles()
    if _can_bypass_approval(settings, user_roles):
        return {
            "enabled": True,
            "current_status": current,
            "can_submit_for_l1": current == STATUS_DRAFT,
            "can_l1_approve": current == STATUS_PENDING_L1,
            "can_final_approve": current == STATUS_PENDING_FINAL,
        }

    rule = _find_branch_rule(doc, settings, doctype_key)
    if not rule:
        return {
            "enabled": True,
            "current_status": current,
            "no_rule": True,
            "can_submit_for_l1": False,
            "can_l1_approve": False,
            "can_final_approve": False,
        }

    return {
        "enabled": True,
        "current_status": current,
        "can_submit_for_l1": current == STATUS_DRAFT and rule.who_create in user_roles,
        "can_l1_approve": current == STATUS_PENDING_L1 and rule.l1_approver in user_roles,
        "can_final_approve": current == STATUS_PENDING_FINAL and rule.final_approver in user_roles,
    }


#  Status transition
def _advance_status(doc, new_status):
    """Write the new approval status and sync the disabled flag, then save.
    ignore_permissions is safe here because all callers have already verified
    role eligibility before reaching this function."""
    doc.set(CF_APPROVAL_STATUS, new_status)
    _sync_disabled_flag(doc)
    doc.flags.in_cs_approval_transition = True
    try:
        doc.save(ignore_permissions=True)
    finally:
        doc.flags.in_cs_approval_transition = False


def _sync_disabled_flag(doc):
    """Keep the standard `disabled` field in sync with approval status.
    Approved → disabled = 0 (active in transactions).
    Any other status → disabled = 1 (blocked until fully approved)."""
    _ensure_disabled_field_available(doc.doctype)
    doc.set("disabled", 0 if _current_status(doc) == STATUS_APPROVED else 1)


#  Custom field auto-creation 
def _enable_workflow_for_doctype(doctype, settings=None, doctype_key=None):
    _ensure_custom_fields(doctype, settings, doctype_key)
    initialize_existing_enabled_records(doctype)


def _cleanup_workflow_for_disabled_doctype(doctype):
    cleanup_workflow_custom_fields(doctype)


def _ensure_custom_fields(doctype, settings=None, doctype_key=None):
    """Ensure workflow fields exist with the required metadata."""
    _ensure_branch_field(doctype)

    _ensure_single_custom_field(
        dt=doctype,
        fieldname=CF_APPROVAL_STATUS,
        fieldtype="Select",
        label="Approval Status",
        options=_APPROVAL_STATUS_OPTIONS,
        insert_after=CF_BRANCH,
        default=STATUS_DRAFT,
        read_only=1,
        in_list_view=1,
    )


def initialize_existing_enabled_records(doctype):
    """Mark already-active masters as Approved when workflow is enabled."""
    if not _has_field(doctype, CF_APPROVAL_STATUS):
        return

    frappe.db.set_value(
        doctype,
        {"disabled": 0},
        CF_APPROVAL_STATUS,
        STATUS_APPROVED,
        update_modified=False,
    )
    frappe.clear_cache(doctype=doctype)


def cleanup_workflow_custom_fields(doctype):
    """Remove workflow-created fields when approval is disabled."""
    _delete_custom_field(doctype, CF_APPROVAL_STATUS)
    _delete_custom_branch_field_if_workflow_created(doctype)
    _delete_branch_property_setters(doctype)
    frappe.clear_cache(doctype=doctype)


def _has_field(doctype, fieldname):
    return bool(frappe.get_meta(doctype).get_field(fieldname))


def _delete_custom_field(doctype, fieldname):
    name = frappe.db.exists("Custom Field", {"dt": doctype, "fieldname": fieldname})
    if name:
        frappe.delete_doc("Custom Field", name, ignore_permissions=True, force=True)


def _delete_custom_branch_field_if_workflow_created(doctype):
    name = frappe.db.exists("Custom Field", {"dt": doctype, "fieldname": CF_BRANCH})
    if not name:
        return

    custom_field = frappe.get_doc("Custom Field", name)
    if custom_field.module == "Generate Item":
        frappe.delete_doc("Custom Field", name, ignore_permissions=True, force=True)


def _delete_branch_property_setters(doctype):
    setters = frappe.get_all(
        "Property Setter",
        filters={
            "doc_type": doctype,
            "field_name": CF_BRANCH,
            "property": ["in", ["reqd", "allow_in_quick_entry"]],
            "value": "1",
        },
        pluck="name",
    )
    for setter in setters:
        frappe.delete_doc("Property Setter", setter, ignore_permissions=True, force=True)


def _ensure_branch_field(doctype):
    field = frappe.get_meta(doctype).get_field(CF_BRANCH)
    custom_field = frappe.db.exists(
        "Custom Field", {"dt": doctype, "fieldname": CF_BRANCH}
    )

    if field:
        if field.fieldtype != "Link" or field.options != "Branch":
            frappe.throw(
                _("The {0} Branch field must be a Link field with options set to Branch.").format(
                    doctype
                ),
                frappe.ValidationError,
            )

        if custom_field:
            _ensure_single_custom_field(
                dt=doctype,
                fieldname=CF_BRANCH,
                fieldtype="Link",
                label="Branch",
                options="Branch",
                insert_after="disabled",
                reqd=1,
                allow_in_quick_entry=1,
            )
        else:
            _ensure_field_property(doctype, CF_BRANCH, "reqd", 1, "Check")
            _ensure_field_property(
                doctype, CF_BRANCH, "allow_in_quick_entry", 1, "Check"
            )
        return

    _ensure_single_custom_field(
        dt=doctype,
        fieldname=CF_BRANCH,
        fieldtype="Link",
        label="Branch",
        options="Branch",
        insert_after="disabled",
        reqd=1,
        allow_in_quick_entry=1,
    )


def _ensure_single_custom_field(
    dt, fieldname, fieldtype, label, options=None, insert_after=None,
    default=None, read_only=0, reqd=0, allow_in_quick_entry=0, in_list_view=0
):
    """Create or update a Custom Field so workflow metadata stays correct."""
    filters = {"dt": dt, "fieldname": fieldname}
    existing = frappe.db.exists("Custom Field", filters)
    if existing:
        cf = frappe.get_doc("Custom Field", existing)
        changed = False
        for key, value in {
            "fieldtype": fieldtype,
            "label": label,
            "options": options or "",
            "insert_after": insert_after or "amended_from",
            "default": default or "",
            "read_only": cint(read_only),
            "reqd": cint(reqd),
            "allow_in_quick_entry": cint(allow_in_quick_entry),
            "in_list_view": cint(in_list_view),
        }.items():
            if cf.get(key) != value:
                cf.set(key, value)
                changed = True

        if changed:
            cf.save(ignore_permissions=True)
            frappe.clear_cache(doctype=dt)
        return

    cf = frappe.get_doc({
        "doctype": "Custom Field",
        "dt": dt,
        "fieldname": fieldname,
        "fieldtype": fieldtype,
        "label": label,
        "options": options or "",
        "insert_after": insert_after or "amended_from",
        "default": default or "",
        "read_only": cint(read_only),
        "reqd": cint(reqd),
        "allow_in_quick_entry": cint(allow_in_quick_entry),
        "in_list_view": cint(in_list_view),
        "module": "Generate Item",
        "translatable": 0,
    })
    cf.flags.ignore_permissions = True
    cf.insert()
    frappe.clear_cache(doctype=dt)


def _ensure_field_property(doctype, fieldname, property_name, value, property_type):
    meta = frappe.get_meta(doctype)
    field = meta.get_field(fieldname)
    if not field:
        return

    if cint(field.get(property_name)) == cint(value):
        return

    from frappe.custom.doctype.property_setter.property_setter import make_property_setter

    make_property_setter(
        doctype, fieldname, property_name, value, property_type,
        for_doctype=False, validate_fields_for_doctype=False
    )
    frappe.clear_cache(doctype=doctype)


#  Small utility functions
def _get_settings():
    if not frappe.db.exists("DocType", CS_SETTINGS_DOCTYPE):
        return None
    return frappe.get_cached_doc(CS_SETTINGS_DOCTYPE)


def _is_workflow_active(settings, doctype_key):
    if not settings:
        return False
    if doctype_key == "customer":
        return cint(settings.enable_customer_approval)
    return cint(settings.enable_supplier_approval)


def _get_user_roles(user=None):
    return set(frappe.get_roles(user or frappe.session.user))


def _can_bypass_approval(settings, user_roles=None):
    user_roles = user_roles or _get_user_roles()
    return (
        (
            cint(settings.get("allow_system_manager_approval_bypass"))
            and "System Manager" in user_roles
        )
        or (
            settings.get("approval_bypass_role")
            and settings.get("approval_bypass_role") in user_roles
        )
    )


def _current_status(doc):
    return doc.get(CF_APPROVAL_STATUS) or STATUS_DRAFT


def _doctype_key(doctype):
    if doctype == "Customer":
        return "customer"
    if doctype == "Supplier":
        return "supplier"

    frappe.throw(
        _("Customer & Supplier Approval Workflow only supports Customer and Supplier."),
        frappe.ValidationError,
    )


def _find_branch_rule(doc, settings, doctype_key):
    """Return the active rule row matching the document's branch, or None."""
    branch = doc.get(CF_BRANCH)
    if not branch:
        return None

    rules_fieldname = (
        "customer_approval_rules" if doctype_key == "customer" else "supplier_approval_rules"
    )

    for row in settings.get(rules_fieldname) or []:
        if row.branch == branch and not cint(row.disabled):
            return row

    return None


def _get_branch_rule(doc, settings, doctype_key):
    """Return the active rule row matching the document's branch.
    Raises frappe.ValidationError if branch is missing or not configured."""
    if not doc.get(CF_BRANCH):
        frappe.throw(
            _("Please select a {0} on this {1} to determine the approval chain.").format(
                frappe.bold("Branch"), doc.doctype
            )
        )

    rule = _find_branch_rule(doc, settings, doctype_key)
    if rule:
        return rule

    branch = doc.get(CF_BRANCH)
    frappe.throw(
        _(
            "No active approval rule is configured for Branch {0} in "
            "{1}. Please add a row for this branch."
        ).format(
            frappe.bold(branch),
            frappe.bold("Customer Supplier Workflow Settings"),
        ),
        frappe.ValidationError,
    )


def _assert_workflow_enabled(settings, doctype_key):
    if not _is_workflow_active(settings, doctype_key):
        frappe.throw(
            _("The Customer & Supplier Approval Workflow is not enabled for this DocType.")
        )


def _assert_status(doc, expected_status, action_label):
    """Throw a clear error if the document is not in the expected status."""
    current = _current_status(doc)
    if current != expected_status:
        frappe.throw(
            _("Cannot {0}. Current status is {1}.").format(
                action_label, frappe.bold(current)
            ),
            frappe.ValidationError,
        )


def _assert_has_role(required_role, error_message):
    if required_role not in _get_user_roles():
        frappe.throw(error_message, frappe.PermissionError)
