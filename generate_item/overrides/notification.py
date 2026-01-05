import frappe
from frappe import _
from frappe.email.doctype.notification.notification import Notification
from frappe.utils import cint, validate_email_address


class CustomNotification(Notification):
    """Extend Notification to support workflow Value Editor recipients with strict branch permissions."""

    def validate(self):
        super().validate()
        self._validate_value_editor_requirements()

    def get_list_of_recipients(self, doc, context):
        """
        Get recipients with strict branch permission filtering.
        All recipients (base + value editors) must have explicit branch access.
        """
        recipients, cc, bcc = super().get_list_of_recipients(doc, context)

        # Add value editor recipients if applicable
        if self._should_send_to_value_editors():
            editor_emails = self._get_value_editor_emails(doc)
            if editor_emails:
                merged = set(recipients or [])
                merged.update(editor_emails)
                recipients = list(merged)

        # Apply strict branch permission filtering to ALL recipients
        recipients = self._filter_by_permission(doc, recipients)
        cc = self._filter_by_permission(doc, cc)
        bcc = self._filter_by_permission(doc, bcc)
        frappe.log_error(
    message=f"Recipients after merge & permission filter:\n{recipients}",
    title="Notification Recipient Debug"
)

        return (
            self._sanitize_email_list(recipients),
            self._sanitize_email_list(cc),
            self._sanitize_email_list(bcc),
        )

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------
    def _validate_value_editor_requirements(self):
        """Validate configuration for value editor recipients."""
        if not cint(self.get("send_all_value_editor")):
            return

        if self.event != "Value Change":
            frappe.throw(
                _("Enable Value Editor recipients only with event 'Value Change'."),
                title=_("Invalid Notification Configuration"),
            )

        if (self.value_changed or "").strip().lower() != "workflow_state":
            frappe.throw(
                _("Set 'Value Changed' to exactly 'workflow_state' when Value Editor recipients are enabled."),
                title=_("Invalid Notification Configuration"),
            )

    # -------------------------------------------------------------------------
    # Value Editor Recipients
    # -------------------------------------------------------------------------
    def _should_send_to_value_editors(self):
        """Check if value editor recipients should be included."""
        return (
            cint(self.get("send_all_value_editor"))
            and self.event == "Value Change"
            and (self.value_changed or "").strip().lower() == "workflow_state"
        )

    def _get_value_editor_emails(self, doc):
        """
        Get emails of users who can edit current workflow state.
        Pre-filtered by branch permissions for efficiency.
        """
        role = self._get_allow_edit_role_for_state(doc)
        if not role:
            return []

        # Get branch early for filtering
        branch = doc.get("branch") if doc.meta.has_field("branch") else None
        
        # Get users with role AND branch permission in one query
        users = self._get_permitted_users_for_role_and_branch(role, branch, doc.doctype)
        
        if not users:
            return []

        return self._get_primary_emails(users)

    def _get_allow_edit_role_for_state(self, doc):
        """Get the role that can edit the current workflow state."""
        workflow_state = doc.get("workflow_state")
        if not workflow_state:
            return None

        workflows = frappe.get_all(
            "Workflow",
            filters={"document_type": doc.doctype, "is_active": 1},
            fields=["name"],
            order_by="creation asc",
        )

        if not workflows:
            return None

        for workflow in workflows:
            state_row = frappe.db.get_value(
                "Workflow Document State",
                {"parent": workflow.name, "state": workflow_state},
                ["allow_edit"],
                as_dict=True,
            )
            if state_row and state_row.get("allow_edit"):
                return state_row.get("allow_edit")

        return None

    def _get_permitted_users_for_role_and_branch(self, role, branch, doctype):
        """
        Get users who have:
        1. The specified role
        2. Permission for the branch (if applicable)
        3. Are active users
        
        This is an optimized query that filters by branch upfront.
        """
        if not branch:
            # No branch restriction needed, just get users with role
            return self._get_active_users_with_role(role)
        
        # Combined query for role + branch permissions
        query = """
            SELECT DISTINCT u.name
            FROM `tabUser` u
            INNER JOIN `tabHas Role` hr 
                ON hr.parent = u.name 
                AND hr.parenttype = 'User' 
                AND hr.role = %(role)s
            LEFT JOIN `tabUser Permission` up 
                ON up.user = u.name 
                AND up.allow = 'Branch'
                AND up.for_value = %(branch)s
                AND (
                    up.apply_to_all_doctypes = 1 
                    OR up.applicable_for IS NULL 
                    OR up.applicable_for = '' 
                    OR up.applicable_for = %(doctype)s
                )
            WHERE 
                u.enabled = 1
                AND u.user_type != 'Website User'
                AND (
                    -- Has specific branch permission
                    up.name IS NOT NULL
                    OR
                    -- Has no branch restrictions (global access)
                    -- REMOVED: This was allowing users without permissions
                    -- Now we require explicit permission
                    0 = 1
                )
        """
        
        users = frappe.db.sql(
            query,
            {"role": role, "branch": branch, "doctype": doctype},
            pluck="name"
        )
        
        return users or []

    def _get_active_users_with_role(self, role):
        """Get all active users with a specific role."""
        if not role:
            return []

        user_names = frappe.get_all(
            "Has Role",
            filters={"role": role, "parenttype": "User"},
            pluck="parent",
        )

        if not user_names:
            return []

        active_users = frappe.get_all(
            "User",
            filters={
                "name": ["in", user_names],
                "enabled": 1,
                "user_type": ("!=", "Website User"),
            },
            pluck="name",
        )

        return active_users or []

    # -------------------------------------------------------------------------
    # Permission Filtering
    # -------------------------------------------------------------------------
    def _filter_by_permission(self, doc, emails):
        """
        Filter emails by strict user permissions.
        Users MUST have explicit branch permission to receive notifications.
        """
        if not emails:
            return []

        # Quick optimization: check if doc has branch field
        has_branch_field = doc.meta.has_field("branch")
        doc_branch = doc.get("branch") if has_branch_field else None

        filtered = []
        for email in emails:
            # Find user by email
            user = frappe.db.get_value("User", {"email": email}, "name")
            if not user and frappe.db.exists("User", email):
                user = email

            if not user:
                # External email (not a User in the system)
                # Decision: Allow external emails or block them?
                # Current: Allow (they're not subject to internal permissions)
                # To block: comment out the next line
                filtered.append(email)
                continue

            # Check if user has permission
            if self._check_user_permission(doc, user):
                filtered.append(email)
            else:
                # Log denied access for debugging
                self._log_permission_denial(doc, user, email, doc_branch)

        return filtered

    def _check_user_permission(self, doc, user):
        """
        Strict branch permission check.
        Returns True only if user explicitly has access to the document's branch.
        """
        # 1. Standard Frappe permission check (respects Role Permission Manager)
        if not doc.has_permission(user=user):
            return False

        # 2. If document doesn't have branch field, allow
        if not doc.meta.has_field("branch"):
            return True

        doc_branch = doc.get("branch")
        
        # 3. If document has no branch value, allow
        # (Some documents might not have branch set yet)
        if not doc_branch:
            return True

        # 4. Get user's branch permissions
        user_permissions = frappe.get_all(
            "User Permission",
            filters={"user": user, "allow": "Branch"},
            fields=["for_value", "apply_to_all_doctypes", "applicable_for"],
        )

        # 5. STRICT MODE: No branch permissions = NO ACCESS
        if not user_permissions:
            return False

        # 6. Check if user has permission for this specific branch
        for perm in user_permissions:
            is_applicable = (
                perm.apply_to_all_doctypes 
                or not perm.applicable_for 
                or perm.applicable_for == doc.doctype
            )
            if is_applicable and perm.for_value == doc_branch:
                return True

        # 7. User has branch restrictions but not for this branch
        return False

    def _log_permission_denial(self, doc, user, email, branch):
        """Log permission denials for debugging."""
        message = f"""
        Notification Permission Denied:
        - User: {user} ({email})
        - Document: {doc.doctype} - {doc.name}
        - Branch: {branch or "None"}
        - Reason: User does not have permission for this branch
        """
        
        frappe.log_error(
            message.strip(),
            title="Notification Permission Denied"
        )

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------
    def _get_primary_emails(self, users):
        """Get primary email addresses for a list of users."""
        if not users:
            return []

        user_records = frappe.get_all(
            "User",
            filters={"name": ["in", users]},
            fields=["name", "email"],
        )

        emails = []
        for record in user_records:
            email = record.get("email") or record.get("name")
            if email:
                emails.append(email)

        return emails

    def _sanitize_email_list(self, emails):
        """Validate and clean email addresses."""
        sanitized = []
        for email in emails or []:
            if not email:
                continue
            cleaned = validate_email_address(email, throw=False)
            if cleaned:
                sanitized.append(cleaned)
        return sanitized