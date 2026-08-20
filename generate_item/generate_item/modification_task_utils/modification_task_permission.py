import frappe

# ---------------------------------------------------------------------------
# Role → allowed Modification Task categories
# ---------------------------------------------------------------------------

ROLE_CATEGORY_MAP = {
    "Design User":             ["BOM Modification"],
    "Design Manager":          ["BOM Modification"],

    "Planning User":           ["Production Plan Update", "Work Order Update"],
    "Planning Manager":        ["Production Plan Update", "Work Order Update"],

    "Purchase User":           ["Purchase Order Modification"],
    "Purchase Manager":        ["Purchase Order Modification"],
    "Purchase Master Manager": ["Purchase Order Modification"],

    "Sales User":              ["Sales Order Modification"],
    "Sales Manager":           ["Sales Order Modification"],
    "Sales Master Manager":    ["Sales Order Modification"],
}


# ===========================================================================
# PUBLIC HOOKS
# ===========================================================================

def get_permission_query_conditions(user=None):
   
    if not user:
        user = frappe.session.user

    if _is_unrestricted(user):
        return ""

    conditions = []

    # --- 1. Role / category filter ---
    category_condition = _build_category_condition(user)
    if category_condition is None:
        # User has no mapped role at all → show nothing
        return "`tabModification Task`.`name` IS NULL"
    if category_condition:
        conditions.append(category_condition)

    # --- 2. Branch filter (reads branch stamped directly on the task) ---
    branch_condition = _build_branch_condition(user)
    if branch_condition:
        conditions.append(branch_condition)

    return " AND ".join(f"({c})" for c in conditions) if conditions else ""


def has_permission(doc, ptype="read", user=None):
   
    if not user:
        user = frappe.session.user

    if _is_unrestricted(user):
        return True

    # --- 1. Role / category check ---
    allowed_categories = _get_allowed_categories(user)
    if allowed_categories is None or doc.category not in allowed_categories:
        return False

    # --- 2. Branch check — read directly from doc.branch (stamped at creation) ---
    user_branches = get_user_branches(user)
    if user_branches and doc.branch not in user_branches:
        return False

    return True


# ===========================================================================
# BRANCH HELPERS  (also imported by modification_task_creator.py)
# ===========================================================================

def get_user_branches(user=None):
    """
    Returns branch values from the user's User Permission records (allow=Branch).
    Empty list  → no branch restriction → user sees all branches.
    Non-empty   → user restricted to only those branch values.
    Branch names are never hardcoded — sourced entirely from DB at runtime.
    """
    if not user:
        user = frappe.session.user

    rows = frappe.db.get_all(
        "User Permission",
        filters={"user": user, "allow": "Branch"},
        fields=["for_value"],
    )
    return [row.for_value for row in rows]


def get_document_branch(doctype, docname):
    """
    Dynamically resolves the branch field on any doctype by inspecting
    DocField metadata — finds a Link field whose options = 'Branch'.
    No field name is hardcoded.
    Used by modification_task_creator.py to stamp branch on the task at creation.
    """
    branch_field = _get_branch_field_for_doctype(doctype)
    if not branch_field:
        return None
    return frappe.db.get_value(doctype, docname, branch_field)


# ===========================================================================
# INTERNAL HELPERS
# ===========================================================================

def _is_unrestricted(user):
    """
    Only Administrator gets a full bypass.

    """
    return user == "Administrator"


def _get_allowed_categories(user):
    """
    Returns a set of allowed categories based on the user's roles.
    Returns None if the user holds none of the mapped roles (hard deny).
    """
    user_roles  = frappe.get_roles(user)
    allowed     = set()
    matched_any = False

    for role in user_roles:
        if role in ROLE_CATEGORY_MAP:
            matched_any = True
            allowed.update(ROLE_CATEGORY_MAP[role])

    return allowed if matched_any else None


def _build_category_condition(user):
    """
    SQL fragment for the role / category filter.
    Returns None → deny (no applicable role).
    Returns ""   → no restriction.
    Returns str  → IN(...) clause on `category`.
    """
    allowed_categories = _get_allowed_categories(user)
    if allowed_categories is None:
        return None
    if not allowed_categories:
        return ""

    escaped = ", ".join(frappe.db.escape(cat) for cat in allowed_categories)
    return f"`tabModification Task`.`category` IN ({escaped})"


def _build_branch_condition(user):
    """
    SQL fragment for the branch filter.

    Reads `tabModification Task`.`branch` directly — the branch field is
    stamped onto every task at creation time by get_document_branch(), which
    resolves the branch field name dynamically from DocField metadata.

    No branch name and no field name is hardcoded here.
    Branch values come entirely from User Permission records at runtime.

    Returns "" → user has no Branch User Permission → no branch filter applied.
    Returns str → IN(...) clause on `branch`.
    """
    user_branches = get_user_branches(user)

    if not user_branches:
        # No Branch User Permission records → unrestricted by branch
        return ""

    escaped_branches = ", ".join(frappe.db.escape(b) for b in user_branches)
    return f"`tabModification Task`.`branch` IN ({escaped_branches})"


def _get_branch_field_for_doctype(doctype):
    """
    Dynamically finds the fieldname on `doctype` that is a Link to 'Branch',
    by querying DocField metadata. Result is cached on frappe.local so the
    DB is hit at most once per doctype per request.
    """
    cache_key = f"_branch_field_{doctype}"
    cached = getattr(frappe.local, cache_key, None)
    if cached is not None:
        return None if cached == "__none__" else cached

    result = frappe.db.get_value(
        "DocField",
        filters={"parent": doctype, "fieldtype": "Link", "options": "Branch"},
        fieldname="fieldname",
    )

    setattr(frappe.local, cache_key, result if result else "__none__")
    return result