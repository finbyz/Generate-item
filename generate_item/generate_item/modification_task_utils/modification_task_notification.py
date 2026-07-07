import frappe
from frappe import _


CATEGORY_NOTIFY_ROLES = {
    "BOM Modification":          ["Design User", "Design Manager"],
    "Production Plan Update":    ["Planning User", "Planning Manager"],
    "Work Order Update":         ["Planning User", "Planning Manager"],
    "Purchase Order Modification": ["Purchase User", "Purchase Manager", "Purchase Master Manager"],
    "Sales Order Modification":  ["Sales User", "Sales Manager", "Sales Master Manager"],
}

# ---------------------------------------------------------------------------
# Category → human-readable document type label (for notification message)
# ---------------------------------------------------------------------------

CATEGORY_LABEL = {
    "BOM Modification":            "BOM",
    "Production Plan Update":      "Production Plan",
    "Work Order Update":           "Work Order",
    "Purchase Order Modification": "Purchase Order",
    "Sales Order Modification":    "Sales Order",
}



def send_modification_task_notification(doc, method=None):
    """
    Sends a Frappe Notification Log to every eligible user when a
    Modification Task is submitted.

    Eligibility criteria (both must pass):
      1. Role match   — user has a role mapped to doc.category
      2. Branch match — user has no branch restriction, OR their branch
                        restriction includes doc.branch
    """
    if doc.docstatus != 1:
        return  # safety guard — only run on submitted docs

    notify_roles = CATEGORY_NOTIFY_ROLES.get(doc.category)
    if not notify_roles:
        return  # unknown category — nothing to do

    eligible_users = _get_eligible_users(
        roles=notify_roles,
        task_branch=doc.branch,
        exclude_user=doc.owner,   # don't notify the person who created the task
    )

    if not eligible_users:
        return

    subject, message = _build_notification_content(doc)

    for user in eligible_users:
        _create_notification_log(
            user=user,
            subject=subject,
            message=message,
            doc=doc,
        )


# ===========================================================================
# HELPERS
# ===========================================================================

def _get_eligible_users(roles, task_branch, exclude_user=None):
    """
    Returns a list of usernames who:
      1. Are enabled (not disabled)
      2. Hold at least one of the given roles
      3. Pass the branch check:
           - If user has NO Branch User Permission records → eligible (sees all branches)
           - If user HAS Branch User Permission records → eligible only if task_branch
             is in their allowed branch list

    exclude_user: typically the task creator — skip them to avoid self-notification.
    """
    if not roles:
        return []

    # --- Step 1: find all enabled users who have at least one matching role ---
    # Query HasRole child table joined to User
    role_placeholders = ", ".join(["%s"] * len(roles))
    sql = f"""
        SELECT DISTINCT
            hr.parent AS user
        FROM
            `tabHas Role` hr
        INNER JOIN
            `tabUser` u ON u.name = hr.parent
        WHERE
            hr.role IN ({role_placeholders})
            AND u.enabled = 1
            AND u.user_type = 'System User'
    """
    params = list(roles)

    if exclude_user:
        sql += " AND hr.parent != %s"
        params.append(exclude_user)

    rows = frappe.db.sql(sql, params, as_dict=True)
    candidate_users = [row.user for row in rows]

    if not candidate_users:
        return []

    # --- Step 2: apply branch filter per user ---
    eligible = []
    for user in candidate_users:
        user_branches = _get_user_branches(user)

        if not user_branches:
            # No branch restriction → eligible for all branches
            eligible.append(user)
        elif task_branch and task_branch in user_branches:
            # Branch restriction exists and task branch matches
            eligible.append(user)
        elif not task_branch:
            # Task has no branch stamped → don't restrict by branch
            eligible.append(user)

    return eligible


def _get_user_branches(user):
    """
    Returns the list of branch values from the user's User Permission records
    (allow = 'Branch'). Empty list = no restriction.
    """
    rows = frappe.db.get_all(
        "User Permission",
        filters={"user": user, "allow": "Branch"},
        fields=["for_value"],
    )
    return [row.for_value for row in rows]


def _build_notification_content(doc):
    """
    Builds the notification subject and message body for a given task.
    """
    doc_label = CATEGORY_LABEL.get(doc.category, doc.category)
    ref_link  = f'<a href="/app/{doc.reference_doctype.lower().replace(" ", "-")}/{doc.reference_document_name}">{doc.reference_document_name}</a>'
    task_link = f'<a href="/app/modification-task/{doc.name}">{doc.name}</a>'

    branch_info = f" (Branch: <strong>{doc.branch}</strong>)" if doc.branch else ""

    subject = f"Action Required: {doc.category} — {doc.reference_document_name}{branch_info}"

    message = f"""
        <p>A new <strong>{doc.category}</strong> task has been created and requires your attention.</p>
        <table style="border-collapse:collapse; width:100%; font-size:14px;">
            <tr>
                <td style="padding:6px 12px; font-weight:600; width:180px;">Task</td>
                <td style="padding:6px 12px;">{task_link}</td>
            </tr>
            <tr style="background:#f9f9f9;">
                <td style="padding:6px 12px; font-weight:600;">Document Type</td>
                <td style="padding:6px 12px;">{doc_label}</td>
            </tr>
            <tr>
                <td style="padding:6px 12px; font-weight:600;">Reference Document</td>
                <td style="padding:6px 12px;">{ref_link}</td>
            </tr>
            <tr style="background:#f9f9f9;">
                <td style="padding:6px 12px; font-weight:600;">Branch</td>
                <td style="padding:6px 12px;">{doc.branch or "—"}</td>
            </tr>
            <tr>
                <td style="padding:6px 12px; font-weight:600;">Status</td>
                <td style="padding:6px 12px;">{doc.status}</td>
            </tr>
            <tr style="background:#f9f9f9;">
                <td style="padding:6px 12px; font-weight:600;">Remarks</td>
                <td style="padding:6px 12px;">{doc.remarks or "—"}</td>
            </tr>
        </table>
        <p style="margin-top:16px;">
            Please open the task and complete the required steps as described in the task description.
        </p>
    """

    return subject, message


def _create_notification_log(user, subject, message, doc):
    """
    Creates a Frappe Notification Log record for the given user.
    This appears in the bell (🔔) notification panel in the Frappe UI.
    """
    notification = frappe.get_doc({
        "doctype":       "Notification Log",
        "for_user":      user,
        "from_user":     frappe.session.user,
        "subject":       subject,
        "email_content": message,
        "document_type": doc.doctype,
        "document_name": doc.name,
        "type":          "Alert",
        "read":          0,
    })
    notification.insert(ignore_permissions=True)