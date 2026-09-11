"""Server-side data services for the Purchase User Dashboard.

The implementation uses Frappe's permission-aware APIs and validates user
permissions so that unauthorized data is never exposed.
"""

from __future__ import annotations

import json
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, nowdate


def _doctype_exists(doctype: str) -> bool:
    return bool(frappe.db.exists("DocType", doctype))


def _parse_date(val: Any) -> str | None:
    """Safely parse input date string into standard YYYY-MM-DD string."""
    if not val:
        return None
    val_str = str(val).strip()
    if not val_str or val_str in ("None", "undefined"):
        return None

    # Handle standard split first to prevent dateutil from parsing DD-MM-YYYY as YY-MM-DD
    clean_str = val_str.replace("/", "-")
    parts = clean_str.split("-")
    if len(parts) == 3:
        if len(parts[0]) == 4:  # yyyy-mm-dd
            return f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
        elif len(parts[2]) == 4:  # dd-mm-yyyy
            return f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"

    try:
        d = getdate(val_str)
        if d:
            return str(d)
    except Exception:
        pass

    return val_str


def clear_user_hierarchy_cache(doc=None, method=None) -> None:
    """Invalidate recursive user hierarchy cache on permission or user changes."""
    try:
        frappe.cache.delete_key("user_subordinates_cache")
    except Exception:
        pass


def get_recursive_subordinate_users(session_user: str) -> list[str]:
    """Recursively resolve all direct and indirect subordinate user IDs for a given user.

    Uses a single batch query against `tabUser Permission` with in-memory BFS graph
    traversal, cycle protection, and Redis caching.
    """
    if not session_user or session_user in ("Administrator", "Guest"):
        return []

    # 1. Check Redis Cache
    cached_users = frappe.cache.hget("user_subordinates_cache", session_user)
    if cached_users is not None:
        return cached_users

    # 2. Single DB Query: Fetch all 'User' permission relationships across the site (0 N+1)
    permissions = frappe.db.sql(
        """
        SELECT up.user, up.for_value
        FROM `tabUser Permission` up
        JOIN `tabUser` u ON u.name = up.for_value
        WHERE up.allow = 'User'
          AND u.enabled = 1
        """,
        as_dict=True,
    )

    # 3. Build Adjacency List: { manager_email: [subordinate_email_1, subordinate_email_2, ...] }
    graph: dict[str, list[str]] = {}
    for p in permissions:
        manager = p.get("user")
        subordinate = p.get("for_value")
        if manager and subordinate and manager != subordinate:
            graph.setdefault(manager, []).append(subordinate)

    # 4. Breadth-First Search (BFS) Traversal with cycle protection
    visited: set[str] = set()
    queue = [session_user]

    while queue:
        current_manager = queue.pop(0)
        for subordinate in graph.get(current_manager, []):
            if subordinate not in visited:
                visited.add(subordinate)
                queue.append(subordinate)

    result = sorted(list(visited))

    # 5. Store in Redis Cache
    frappe.cache.hset("user_subordinates_cache", session_user, result)
    return result


def _get_user_allowed_set(session_user: str | None = None) -> set[str]:
    """Return the complete set of user IDs that the session user is allowed to view."""
    session_user = session_user or frappe.session.user
    if not session_user or session_user == "Guest":
        return set()

    # Only Administrator has unrestricted global scope
    if session_user == "Administrator":
        all_users = frappe.db.get_all(
            "User",
            filters={"enabled": 1},
            fields=["name"],
            limit_page_length=0,
        )
        return {u.get("name") for u in all_users if u.get("name")}

    subordinates = get_recursive_subordinate_users(session_user)
    allowed = set(subordinates)
    allowed.add(session_user)
    return allowed


@frappe.whitelist()
def get_allowed_users() -> list[dict[str, str]]:
    """Return list of allowed users that current session user is permitted to view.

    Includes the session user and all direct/indirect subordinates in the hierarchy.
    """
    session_user = frappe.session.user
    if not session_user or session_user == "Guest":
        return []

    allowed_set = _get_user_allowed_set(session_user)
    if not allowed_set:
        return []

    users = frappe.db.get_all(
        "User",
        filters={"name": ["in", list(allowed_set)], "enabled": 1},
        fields=["name", "full_name"],
        order_by="full_name asc, name asc",
        limit_page_length=0,
    )
    return [
        {
            "value": u.get("name"),
            "label": u.get("full_name") or u.get("name"),
            "description": u.get("name"),
        }
        for u in users
        if u.get("name")
    ]


def _validate_and_sanitize_users(users: list[str] | str | None) -> list[str]:
    """Validate that requested users are within allowed hierarchy for frappe.session.user."""
    if isinstance(users, str):
        users_str = users.strip()
        if users_str.startswith("[") and users_str.endswith("]"):
            try:
                parsed = json.loads(users_str)
                if isinstance(parsed, list):
                    users = [str(u).strip() for u in parsed if str(u).strip()]
                else:
                    users = [str(parsed).strip()]
            except Exception:
                users = [u.strip() for u in users_str.strip("[]").split(",") if u.strip()]
        else:
            users = [u.strip() for u in users_str.split(",") if u.strip()]
    elif isinstance(users, (list, tuple, set)):
        users = [str(u).strip() for u in users if str(u).strip()]
    else:
        users = []

    session_user = frappe.session.user
    allowed_set = _get_user_allowed_set(session_user)

    if not users:
        # Default when empty: include session user and all their subordinates
        return sorted(list(allowed_set))

    valid_users = [u for u in users if u in allowed_set]
    if not valid_users:
        return sorted(list(allowed_set))
    return valid_users


# ── Child-table field map for document line-item fetching ────────────────────
_CHILD_TABLE_MAP: dict[str, tuple[str, list[str]]] = {
    "Material Request": (
        "Material Request Item",
        ["item_code", "item_name", "qty", "ordered_qty", "received_qty", "uom", "schedule_date", "warehouse", "rate", "amount"],
    ),
    "Purchase Order": (
        "Purchase Order Item",
        ["item_code", "item_name", "qty", "received_qty", "uom", "schedule_date", "warehouse", "rate", "amount"],
    ),
    "Purchase Receipt": (
        "Purchase Receipt Item",
        ["item_code", "item_name", "qty", "received_qty", "uom", "schedule_date", "warehouse", "rate", "amount"],
    ),
    "Purchase Invoice": (
        "Purchase Invoice Item",
        ["item_code", "item_name", "qty", "uom", "rate", "amount", "warehouse"],
    ),
}


def _fetch_child_items_for_docs(
    doctype: str, doc_names: list[str], limit_per_doc: int = 50
) -> dict[str, list[dict[str, Any]]]:
    """Return dict of {doc_name: [item_rows]} for the given parent doctype in a batch query."""
    if not doc_names or doctype not in _CHILD_TABLE_MAP:
        return {}

    child_dt, fields = _CHILD_TABLE_MAP[doctype]
    if not _doctype_exists(child_dt):
        return {}

    try:
        child_meta = frappe.get_meta(child_dt)
        safe_fields = ["parent", "idx"] + [f for f in fields if child_meta.has_field(f)]
        rows = frappe.db.get_all(
            child_dt,
            filters={"parent": ["in", doc_names], "parenttype": doctype},
            fields=safe_fields,
            order_by="idx asc",
            limit_page_length=0,
        )
    except Exception:
        try:
            rows = frappe.db.get_all(
                child_dt,
                filters={"parent": ["in", doc_names]},
                fields=["parent", "item_code", "item_name", "qty"],
                order_by="idx asc",
                limit_page_length=0,
            )
        except Exception:
            return {}

    result: dict[str, list[dict[str, Any]]] = {}
    count_per_parent: dict[str, int] = {}
    for row in rows:
        parent = row.get("parent")
        if not parent:
            continue
        count_per_parent.setdefault(parent, 0)
        if count_per_parent[parent] >= limit_per_doc:
            continue
        count_per_parent[parent] += 1
        item_data = {
            "item_code": row.get("item_code") or "",
            "item_name": row.get("item_name") or row.get("item_code") or "",
            "qty": flt(row.get("qty")),
            "received_qty": flt(row.get("received_qty") or row.get("ordered_qty")),
            "uom": row.get("uom") or "",
            "schedule_date": str(row.get("schedule_date") or ""),
            "rate": flt(row.get("rate")),
            "amount": flt(row.get("amount")),
            "warehouse": row.get("warehouse") or "",
        }
        result.setdefault(parent, []).append(item_data)
    return result


@frappe.whitelist()
def get_dashboard(
    branch: str | None = None,
    users: list[str] | str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
) -> dict[str, Any]:
    """Return filtered counts and record inspection data for the 5 Purchase User Dashboard cards."""
    valid_users = _validate_and_sanitize_users(users)
    branch = (branch or "").strip() or None
    today_str = nowdate()
    from_date = _parse_date(from_date) or frappe.utils.add_months(today_str, -1)
    to_date = _parse_date(to_date) or today_str

    cards = [
        _get_po_pending_card(branch, valid_users, from_date, to_date),
        _get_mr_completed_card(branch, valid_users, from_date, to_date),
        _get_pr_pending_card(branch, valid_users, from_date, to_date),
        _get_pi_pending_card(branch, valid_users, from_date, to_date),
        _get_pi_completed_card(branch, valid_users, from_date, to_date),
    ]

    return {
        "cards": cards,
        "active_filters": {
            "branch": branch or "",
            "users": valid_users,
            "from_date": from_date,
            "to_date": to_date,
        },
    }


def _get_po_pending_card(
    branch: str | None,
    users: list[str],
    from_date: str | None,
    to_date: str | None,
) -> dict[str, Any]:
    """Card 1: PO Pending
    Shows Material Request data with filter:
    docstatus = 1, status in ('Submitted', 'Partially Ordered', 'Pending'), owner in users (Created By)
    """
    doctype = "Material Request"
    if not _doctype_exists(doctype) or not frappe.has_permission(doctype, "read"):
        return {"id": "po_pending", "title": _("PO Pending"), "doctype": doctype, "count": 0, "items": []}

    filters: dict[str, Any] = {
        "docstatus": 1,
        "status": ["in", ["Submitted", "Partially Ordered", "Pending"]],
    }
    if users:
        filters["owner"] = ["in", users]
    if branch:
        filters["branch"] = branch
    if from_date and to_date:
        filters["transaction_date"] = ["between", [from_date, to_date]]
    elif from_date:
        filters["transaction_date"] = [">=", from_date]
    elif to_date:
        filters["transaction_date"] = ["<=", to_date]

    mr_meta = frappe.get_meta(doctype)
    fields = ["name", "transaction_date", "material_request_type", "status", "owner"]
    if mr_meta.has_field("schedule_date"):
        fields.append("schedule_date")
    if mr_meta.has_field("branch"):
        fields.append("branch")
    if mr_meta.has_field("project"):
        fields.append("project")

    records = frappe.get_all(
        doctype,
        filters=filters,
        fields=fields,
        order_by="transaction_date desc, modified desc",
        limit_page_length=100,
    )
    total_count = frappe.db.count(doctype, filters=filters)

    card_items = [
        {
            "ao": r.get("name"),
            "date": str(r.get("transaction_date") or ""),
            "schedule_date": str(r.get("schedule_date") or ""),
            "item": f"{r.get('material_request_type') or 'MR'} ({r.get('name')})",
            "material_request_type": r.get("material_request_type") or "",
            "status": r.get("status") or "Pending",
            "who": r.get("owner") or "—",
            "branch": r.get("branch") or "",
            "project": r.get("project") or "",
            "doctype": doctype,
        }
        for r in records
    ]

    doc_names = [r["ao"] for r in card_items]
    items_map = _fetch_child_items_for_docs(doctype, doc_names)
    for it in card_items:
        it["doc_items"] = items_map.get(it["ao"], [])

    return {
        "id": "po_pending",
        "title": _("PO Pending"),
        "doctype": doctype,
        "count": total_count,
        "color": "clr-cyan",
        "icon": "octicon octicon-file-text",
        "items": card_items,
    }


def _get_mr_completed_card(
    branch: str | None,
    users: list[str],
    from_date: str | None,
    to_date: str | None,
) -> dict[str, Any]:
    """Card 2: MR Completed
    Shows Material Request data with filter:
    docstatus = 1, status in ('Partially Received', 'Ordered', 'Issued', 'Transferred', 'Received'), owner in users (Created By)
    """
    doctype = "Material Request"
    if not _doctype_exists(doctype) or not frappe.has_permission(doctype, "read"):
        return {"id": "mr_completed", "title": _("MR Completed"), "doctype": doctype, "count": 0, "items": []}

    filters: dict[str, Any] = {
        "docstatus": 1,
        "status": ["in", ["Partially Received", "Ordered", "Issued", "Transferred", "Received"]],
    }
    if users:
        filters["owner"] = ["in", users]
    if branch:
        filters["branch"] = branch
    if from_date and to_date:
        filters["transaction_date"] = ["between", [from_date, to_date]]
    elif from_date:
        filters["transaction_date"] = [">=", from_date]
    elif to_date:
        filters["transaction_date"] = ["<=", to_date]

    mr_meta = frappe.get_meta(doctype)
    fields = ["name", "transaction_date", "material_request_type", "status", "owner"]
    if mr_meta.has_field("schedule_date"):
        fields.append("schedule_date")
    if mr_meta.has_field("branch"):
        fields.append("branch")
    if mr_meta.has_field("project"):
        fields.append("project")

    records = frappe.get_all(
        doctype,
        filters=filters,
        fields=fields,
        order_by="transaction_date desc, modified desc",
        limit_page_length=100,
    )
    total_count = frappe.db.count(doctype, filters=filters)

    card_items = [
        {
            "ao": r.get("name"),
            "date": str(r.get("transaction_date") or ""),
            "schedule_date": str(r.get("schedule_date") or ""),
            "item": f"{r.get('material_request_type') or 'MR'} ({r.get('name')})",
            "material_request_type": r.get("material_request_type") or "",
            "status": r.get("status") or "Completed",
            "who": r.get("owner") or "—",
            "branch": r.get("branch") or "",
            "project": r.get("project") or "",
            "doctype": doctype,
        }
        for r in records
    ]

    doc_names = [r["ao"] for r in card_items]
    items_map = _fetch_child_items_for_docs(doctype, doc_names)
    for it in card_items:
        it["doc_items"] = items_map.get(it["ao"], [])

    return {
        "id": "mr_completed",
        "title": _("MR Completed"),
        "doctype": doctype,
        "count": total_count,
        "color": "clr-amber",
        "icon": "octicon octicon-check",
        "items": card_items,
    }


def _get_pr_pending_card(
    branch: str | None,
    users: list[str],
    from_date: str | None,
    to_date: str | None,
) -> dict[str, Any]:
    """Card 3: PR Pending
    Shows Purchase Order data with filter:
    docstatus = 1, status in ('To Receive and Bill', 'To Receive'), owner in users (Created By)
    """
    doctype = "Purchase Order"
    if not _doctype_exists(doctype) or not frappe.has_permission(doctype, "read"):
        return {"id": "pr_pending", "title": _("PR Pending"), "doctype": doctype, "count": 0, "items": []}

    filters: dict[str, Any] = {
        "docstatus": 1,
        "status": ["in", ["To Receive and Bill", "To Receive"]],
    }
    if users:
        filters["owner"] = ["in", users]
    if branch:
        filters["branch"] = branch
    if from_date and to_date:
        filters["transaction_date"] = ["between", [from_date, to_date]]
    elif from_date:
        filters["transaction_date"] = [">=", from_date]
    elif to_date:
        filters["transaction_date"] = ["<=", to_date]

    po_meta = frappe.get_meta(doctype)
    fields = ["name", "transaction_date", "supplier", "supplier_name", "grand_total", "currency", "status", "owner"]
    if po_meta.has_field("schedule_date"):
        fields.append("schedule_date")
    if po_meta.has_field("branch"):
        fields.append("branch")
    if po_meta.has_field("project"):
        fields.append("project")

    records = frappe.get_all(
        doctype,
        filters=filters,
        fields=fields,
        order_by="transaction_date desc, modified desc",
        limit_page_length=100,
    )
    total_count = frappe.db.count(doctype, filters=filters)

    card_items = [
        {
            "ao": r.get("name"),
            "date": str(r.get("transaction_date") or ""),
            "schedule_date": str(r.get("schedule_date") or ""),
            "item": r.get("supplier_name") or r.get("supplier") or r.get("name"),
            "supplier": r.get("supplier_name") or r.get("supplier") or "",
            "status": r.get("status") or "To Receive",
            "amount": flt(r.get("grand_total")),
            "currency": r.get("currency") or "",
            "who": r.get("owner") or "—",
            "branch": r.get("branch") or "",
            "project": r.get("project") or "",
            "doctype": doctype,
        }
        for r in records
    ]

    doc_names = [r["ao"] for r in card_items]
    items_map = _fetch_child_items_for_docs(doctype, doc_names)
    for it in card_items:
        it["doc_items"] = items_map.get(it["ao"], [])

    return {
        "id": "pr_pending",
        "title": _("PR Pending"),
        "doctype": doctype,
        "count": total_count,
        "color": "clr-indigo",
        "icon": "octicon octicon-git-branch",
        "items": card_items,
    }


def _get_pi_pending_card(
    branch: str | None,
    users: list[str],
    from_date: str | None,
    to_date: str | None,
) -> dict[str, Any]:
    """Card 4: PI Pending
    Shows Purchase Receipt data with filter:
    docstatus = 1, status in ('Partly Billed', 'To Bill', 'Partially Billed'), owner in users (Created By)
    """
    doctype = "Purchase Receipt"
    if not _doctype_exists(doctype) or not frappe.has_permission(doctype, "read"):
        return {"id": "pi_pending", "title": _("PI Pending"), "doctype": doctype, "count": 0, "items": []}

    filters: dict[str, Any] = {
        "docstatus": 1,
        "status": ["in", ["Partly Billed", "To Bill", "Partially Billed"]],
    }
    if users:
        filters["owner"] = ["in", users]
    if branch:
        filters["branch"] = branch
    if from_date and to_date:
        filters["posting_date"] = ["between", [from_date, to_date]]
    elif from_date:
        filters["posting_date"] = [">=", from_date]
    elif to_date:
        filters["posting_date"] = ["<=", to_date]

    pr_meta = frappe.get_meta(doctype)
    fields = ["name", "posting_date", "supplier", "supplier_name", "grand_total", "currency", "status", "owner"]
    if pr_meta.has_field("branch"):
        fields.append("branch")
    if pr_meta.has_field("project"):
        fields.append("project")

    records = frappe.get_all(
        doctype,
        filters=filters,
        fields=fields,
        order_by="posting_date desc, modified desc",
        limit_page_length=100,
    )
    total_count = frappe.db.count(doctype, filters=filters)

    card_items = [
        {
            "ao": r.get("name"),
            "date": str(r.get("posting_date") or ""),
            "item": r.get("supplier_name") or r.get("supplier") or r.get("name"),
            "supplier": r.get("supplier_name") or r.get("supplier") or "",
            "status": r.get("status") or "To Bill",
            "amount": flt(r.get("grand_total")),
            "currency": r.get("currency") or "",
            "who": r.get("owner") or "—",
            "branch": r.get("branch") or "",
            "project": r.get("project") or "",
            "doctype": doctype,
        }
        for r in records
    ]

    doc_names = [r["ao"] for r in card_items]
    items_map = _fetch_child_items_for_docs(doctype, doc_names)
    for it in card_items:
        it["doc_items"] = items_map.get(it["ao"], [])

    return {
        "id": "pi_pending",
        "title": _("PI Pending"),
        "doctype": doctype,
        "count": total_count,
        "color": "clr-rose",
        "icon": "octicon octicon-clock",
        "items": card_items,
    }


def _get_pi_completed_card(
    branch: str | None,
    users: list[str],
    from_date: str | None,
    to_date: str | None,
) -> dict[str, Any]:
    """Card 5: Total PI Completed
    Shows Purchase Invoice data with filter:
    docstatus = 1, is_return = 0, owner in users (Created By)
    """
    doctype = "Purchase Invoice"
    if not _doctype_exists(doctype) or not frappe.has_permission(doctype, "read"):
        return {"id": "pi_completed", "title": _("Total PI Completed"), "doctype": doctype, "count": 0, "items": []}

    filters: dict[str, Any] = {
        "docstatus": 1,
        "is_return": 0,
    }
    if users:
        filters["owner"] = ["in", users]
    if branch:
        filters["branch"] = branch
    if from_date and to_date:
        filters["posting_date"] = ["between", [from_date, to_date]]
    elif from_date:
        filters["posting_date"] = [">=", from_date]
    elif to_date:
        filters["posting_date"] = ["<=", to_date]

    pi_meta = frappe.get_meta(doctype)
    fields = [
        "name",
        "posting_date",
        "due_date",
        "supplier",
        "supplier_name",
        "grand_total",
        "outstanding_amount",
        "currency",
        "status",
        "owner",
    ]
    if pi_meta.has_field("branch"):
        fields.append("branch")
    if pi_meta.has_field("project"):
        fields.append("project")

    records = frappe.get_all(
        doctype,
        filters=filters,
        fields=fields,
        order_by="posting_date desc, modified desc",
        limit_page_length=100,
    )
    total_count = frappe.db.count(doctype, filters=filters)

    card_items = [
        {
            "ao": r.get("name"),
            "date": str(r.get("posting_date") or ""),
            "due_date": str(r.get("due_date") or ""),
            "item": r.get("supplier_name") or r.get("supplier") or r.get("name"),
            "supplier": r.get("supplier_name") or r.get("supplier") or "",
            "status": r.get("status") or "Submitted",
            "amount": flt(r.get("grand_total")),
            "outstanding_amount": flt(r.get("outstanding_amount")),
            "currency": r.get("currency") or "",
            "who": r.get("owner") or "—",
            "branch": r.get("branch") or "",
            "project": r.get("project") or "",
            "doctype": doctype,
        }
        for r in records
    ]

    doc_names = [r["ao"] for r in card_items]
    items_map = _fetch_child_items_for_docs(doctype, doc_names)
    for it in card_items:
        it["doc_items"] = items_map.get(it["ao"], [])

    return {
        "id": "pi_completed",
        "title": _("Total PI Completed"),
        "doctype": doctype,
        "count": total_count,
        "color": "clr-emerald",
        "icon": "octicon octicon-checklist",
        "items": card_items,
    }