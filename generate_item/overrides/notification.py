import frappe
from frappe import _
from frappe.email.doctype.notification.notification import Notification
from frappe.utils import cint, validate_email_address


class CustomNotification(Notification):
    """Extend Notification to support workflow Value Editor recipients."""

    def validate(self):
        super().validate()
        self._validate_value_editor_requirements()

    def get_list_of_recipients(self, doc, context):
        recipients, cc, bcc = super().get_list_of_recipients(doc, context)

        if not self._should_send_to_value_editors():
            return (
                self._sanitize_email_list(recipients),
                self._sanitize_email_list(cc),
                self._sanitize_email_list(bcc),
            )

        editor_emails = self._sanitize_email_list(self._get_value_editor_emails(doc))
        if editor_emails:
            merged = set(recipients or [])
            merged.update(editor_emails)
            recipients = list(merged)

        return (
            self._sanitize_email_list(recipients),
            self._sanitize_email_list(cc),
            self._sanitize_email_list(bcc),
        )

    # -------------------------------------------------------------------------
    # Value editor helpers
    # -------------------------------------------------------------------------
    def _validate_value_editor_requirements(self):
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

    def _should_send_to_value_editors(self):
        return (
            cint(self.get("send_all_value_editor"))
            and self.event == "Value Change"
            and (self.value_changed or "").strip().lower() == "workflow_state"
        )

    def _get_value_editor_emails(self, doc):
        role = self._get_allow_edit_role_for_state(doc)
        if not role:
            return []

        users = self._get_active_users_with_role(role)
        if not users:
            return []

        branch_value = self._get_branch_value(doc)
        if branch_value:
            users = self._filter_users_by_branch(users, branch_value, doc.doctype)

        if not users:
            return []

        return self._get_primary_emails(users)

    def _get_allow_edit_role_for_state(self, doc):
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

    def _get_active_users_with_role(self, role):
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

    def _get_branch_value(self, doc):
        try:
            if doc.meta.has_field("branch"):
                return doc.get("branch")
        except Exception:
            pass

        return doc.get("branch")

    def _filter_users_by_branch(self, users, branch, doctype):
        filtered = []
        for user in users:
            if self._is_branch_allowed_for_user(user, branch, doctype):
                filtered.append(user)
        return filtered

    def _is_branch_allowed_for_user(self, user, branch, doctype):
        if not branch:
            return True

        user_permissions = frappe.get_all(
            "User Permission",
            filters={"user": user, "allow": "Branch"},
            fields=["for_value", "apply_to_all_doctypes", "applicable_for"],
        )

        if not user_permissions:
            return False

        for perm in user_permissions:
            applies_to_doctype = perm.apply_to_all_doctypes or not perm.applicable_for or perm.applicable_for == doctype
            if applies_to_doctype and perm.for_value == branch:
                return True

        return False

    def _get_primary_emails(self, users):
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
        sanitized = []
        for email in emails or []:
            if not email:
                continue
            cleaned = validate_email_address(email, throw=False)
            if cleaned:
                sanitized.append(cleaned)
        return sanitized

