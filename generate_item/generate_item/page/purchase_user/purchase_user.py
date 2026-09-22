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


def get_user_branch_permissions(session_user: str | None = None) -> dict[str, Any]:
    """Return allowed branches for the user based on User Permission records.

    If user is Administrator or has no Branch User Permission records, they have
    access to all branches. In this case, default_branch is "" (All Branches).
    If user has specific Branch User Permission records, they only have access to
    those branches, and default_branch is their default/first permitted branch.
    """
    session_user = session_user or frappe.session.user
    all_db_branches = frappe.db.get_all("Branch", pluck="name", order_by="name asc")

    if not session_user or session_user in ("Administrator", "Guest"):
        return {
            "allowed_branches": all_db_branches,
            "has_all_access": True,
            "default_branch": "",
        }

    perms = frappe.db.get_all(
        "User Permission",
        filters={"user": session_user, "allow": "Branch"},
        fields=["for_value", "is_default"],
    )

    if not perms:
        # No branch permission records -> unrestricted access to all branches
        return {
            "allowed_branches": all_db_branches,
            "has_all_access": True,
            "default_branch": "",
        }

    allowed: list[str] = []
    default_branch = ""
    for p in perms:
        branch_name = p.get("for_value")
        if branch_name and branch_name not in allowed:
            allowed.append(branch_name)
        if p.get("is_default") and not default_branch:
            default_branch = branch_name

    allowed.sort()
    all_set = set(all_db_branches)
    allowed_set = set(allowed)
    has_all_access = all_set.issubset(allowed_set) if all_db_branches else True

    if has_all_access:
        default_branch = ""
    elif not default_branch and allowed:
        default_branch = allowed[0]

    return {
        "allowed_branches": allowed,
        "has_all_access": has_all_access,
        "default_branch": default_branch,
    }


@frappe.whitelist()
def get_branch_permissions() -> dict[str, Any]:
    """Whitelisted endpoint to return branch permissions for current user."""
    return get_user_branch_permissions(frappe.session.user)


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
        ordered_qty = flt(row.get("ordered_qty"))
        received_qty = flt(row.get("received_qty") or row.get("ordered_qty"))
        item_data = {
            "item_code": row.get("item_code") or "",
            "item_name": row.get("item_name") or row.get("item_code") or "",
            "qty": flt(row.get("qty")),
            "ordered_qty": ordered_qty,
            "received_qty": received_qty,
            "uom": row.get("uom") or "",
            "schedule_date": str(row.get("schedule_date") or ""),
            "rate": flt(row.get("rate")),
            "amount": flt(row.get("amount")),
            "warehouse": row.get("warehouse") or "",
        }
        result.setdefault(parent, []).append(item_data)
    return result


def _count_distinct_items_for_prev(doctype: str, filters: dict[str, Any]) -> int | None:
    """Safely return count of distinct item_code for previous period filters."""
    if doctype not in _CHILD_TABLE_MAP:
        return None
    child_dt, _ = _CHILD_TABLE_MAP[doctype]
    if not _doctype_exists(child_dt):
        return None
    try:
        if not frappe.db.count(doctype, filters=filters):
            return 0
        names = frappe.get_all(doctype, filters=filters, pluck="name", limit_page_length=300)
        if not names:
            return 0
        rows = frappe.db.get_all(
            child_dt,
            filters={"parent": ["in", names], "parenttype": doctype},
            fields=["item_code"],
            distinct=True,
            limit_page_length=0,
        )
        return len({r.get("item_code") for r in rows if r.get("item_code")})
    except Exception:
        return None


def _build_item_summary(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build a consolidated list of item-wise procurement rows across all stages."""
    grouped: dict[tuple[str, str], dict[str, Any]] = {}

    for c in cards:
        stage_id = c.get("id") or ""
        stage_title = c.get("title") or ""
        stage_color = c.get("color") or "clr-slate"
        doctype = c.get("doctype") or ""

        for doc in c.get("items") or []:
            doc_name = doc.get("ao") or ""
            doc_date = doc.get("date") or ""
            doc_who = doc.get("who") or ""
            doc_branch = doc.get("branch") or ""
            doc_supplier = doc.get("supplier") or ""
            doc_project = doc.get("project") or ""

            for di in doc.get("doc_items") or []:
                item_code = di.get("item_code")
                if not item_code:
                    continue

                key = (item_code, stage_id)
                qty = flt(di.get("qty"))
                rec_qty = flt(di.get("received_qty"))
                rate = flt(di.get("rate"))
                amt = flt(di.get("amount"))

                if key not in grouped:
                    grouped[key] = {
                        "item_code": item_code,
                        "item_name": di.get("item_name") or item_code,
                        "stage_id": stage_id,
                        "stage_title": stage_title,
                        "stage_color": stage_color,
                        "doctype": doctype,
                        "uom": di.get("uom") or "",
                        "qty": 0.0,
                        "received_qty": 0.0,
                        "pending_qty": 0.0,
                        "amount": 0.0,
                        "rates": [],
                        "warehouses": set(),
                        "branches": set(),
                        "suppliers": set(),
                        "projects": set(),
                        "docs": [],
                        "doc_names_set": set(),
                    }

                entry = grouped[key]
                entry["qty"] += qty
                entry["received_qty"] += rec_qty
                if stage_id == "po_pending" or doctype == "Material Request":
                    ordered = flt(di.get("ordered_qty"))
                    rem = max(0.0, qty - ordered)
                    entry["pending_qty"] += rem
                elif stage_id in ("pr_pending", "pi_pending"):
                    rem = max(0.0, qty - rec_qty) if rec_qty > 0 else qty
                    entry["pending_qty"] += rem
                elif stage_id in ("mr_completed", "pi_completed"):
                    entry["pending_qty"] += 0.0
                else:
                    entry["pending_qty"] += qty

                entry["amount"] += amt
                if rate > 0:
                    entry["rates"].append(rate)

                wh = di.get("warehouse")
                if wh:
                    entry["warehouses"].add(wh)
                if doc_branch:
                    entry["branches"].add(doc_branch)
                if doc_supplier:
                    entry["suppliers"].add(doc_supplier)
                if doc_project:
                    entry["projects"].add(doc_project)

                if doc_name and doc_name not in entry["doc_names_set"]:
                    entry["doc_names_set"].add(doc_name)
                    entry["docs"].append({
                        "name": doc_name,
                        "doctype": doctype,
                        "date": doc_date,
                        "who": doc_who,
                        "branch": doc_branch,
                    })

    result: list[dict[str, Any]] = []
    for (icode, sid), data in grouped.items():
        rates = data.pop("rates", [])
        avg_rate = (sum(rates) / len(rates)) if rates else 0.0
        data.pop("doc_names_set", None)

        result.append({
            "item_code": data["item_code"],
            "item_name": data["item_name"],
            "stage_id": data["stage_id"],
            "stage_title": data["stage_title"],
            "stage_color": data["stage_color"],
            "doctype": data["doctype"],
            "uom": data["uom"],
            "qty": round(data["qty"], 2),
            "received_qty": round(data["received_qty"], 2),
            "pending_qty": round(data["pending_qty"], 2),
            "amount": round(data["amount"], 2),
            "rate": round(avg_rate, 2),
            "warehouse": ", ".join(sorted(list(data["warehouses"]))) if data["warehouses"] else "",
            "branch": ", ".join(sorted(list(data["branches"]))) if data["branches"] else "",
            "supplier": ", ".join(sorted(list(data["suppliers"]))) if data["suppliers"] else "",
            "project": ", ".join(sorted(list(data["projects"]))) if data["projects"] else "",
            "docs": data["docs"],
            "doc_count": len(data["docs"]),
        })

    result.sort(key=lambda x: (x["pending_qty"], x["amount"]), reverse=True)
    return result


def _calculate_delta(current: int, previous: int | None) -> dict[str, Any]:
    """Compute directional delta and percentage change compared to previous period."""
    if previous is None:
        return {"previous": None, "pct": None, "display": "", "direction": "stable"}
    if previous == 0 and current == 0:
        return {"previous": 0, "pct": 0, "display": "0%", "direction": "stable"}
    if previous == 0 and current > 0:
        return {"previous": 0, "pct": None, "display": "New", "direction": "up"}

    diff = current - previous
    pct = round((diff / previous) * 100)
    direction = "up" if pct > 0 else ("down" if pct < 0 else "stable")
    display = f"{'+' if pct > 0 else ''}{pct}%"
    return {"previous": previous, "pct": pct, "display": display, "direction": direction}


@frappe.whitelist()
def get_dashboard(
    branch: str | None = None,
    users: list[str] | str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    prev_from_date: str | None = None,
    prev_to_date: str | None = None,
    period: str | None = None,
) -> dict[str, Any]:
    """Return filtered counts, comparison against previous period, and record inspection data for the 5 cards."""
    valid_users = _validate_and_sanitize_users(users)
    branch_perms = get_user_branch_permissions(frappe.session.user)
    has_all_access = branch_perms["has_all_access"]
    allowed_branches = branch_perms["allowed_branches"]

    branch_val = (branch or "").strip()
    if branch_val:
        # If user is restricted to certain branches, ensure requested branch is permitted
        if not has_all_access and branch_val not in allowed_branches:
            branch_filter: Any = allowed_branches[0] if allowed_branches else None
        else:
            branch_filter = branch_val
    else:
        # All Branches requested
        if has_all_access:
            branch_filter = None
        else:
            # User only has access to specific branches
            branch_filter = ["in", allowed_branches] if allowed_branches else ["in", ["__NONE__"]]

    today_str = nowdate()
    from_date = _parse_date(from_date)
    to_date = _parse_date(to_date)
    prev_from_date = _parse_date(prev_from_date)
    prev_to_date = _parse_date(prev_to_date)

    if not from_date or not to_date:
        # Default to This Quarter (last 3 months to today)
        to_date = today_str
        from_date = str(frappe.utils.add_months(today_str, -3))

    if not prev_from_date or not prev_to_date:
        # Default previous range: 3 months prior to from_date and to_date
        prev_from_date = str(frappe.utils.add_months(from_date, -3))
        prev_to_date = str(frappe.utils.add_months(to_date, -3))

    cards = [
        _get_po_pending_card(branch_filter, valid_users, from_date, to_date, prev_from_date, prev_to_date),
        _get_mr_completed_card(branch_filter, valid_users, from_date, to_date, prev_from_date, prev_to_date),
        _get_pr_pending_card(branch_filter, valid_users, from_date, to_date, prev_from_date, prev_to_date),
        _get_pi_pending_card(branch_filter, valid_users, from_date, to_date, prev_from_date, prev_to_date),
        _get_pi_completed_card(branch_filter, valid_users, from_date, to_date, prev_from_date, prev_to_date),
    ]

    item_summary = _build_item_summary(cards)
    total_distinct_items = len({it["item_code"] for it in item_summary})
    trends = _get_mr_trends(branch_filter, valid_users, from_date, to_date)
    po_leaderboard = _get_po_creator_leaderboard(branch_filter, valid_users, from_date, to_date)

    return {
        "cards": cards,
        "item_summary": item_summary,
        "total_distinct_items": total_distinct_items,
        "trends": trends,
        "po_leaderboard": po_leaderboard,
        "active_filters": {
            "branch": branch_val,
            "users": valid_users,
            "period": period or "This Quarter",
            "from_date": from_date,
            "to_date": to_date,
            "prev_from_date": prev_from_date,
            "prev_to_date": prev_to_date,
        },
        "branch_permissions": branch_perms,
    }


def _get_po_creator_leaderboard(
    branch_filter: Any,
    users: list[str],
    from_date: str | None,
    to_date: str | None,
) -> list[dict[str, Any]]:
    """Return creators ranked by count of Purchase Orders created in the filtered period."""
    if not _doctype_exists("Purchase Order") or not frappe.has_permission("Purchase Order", "read"):
        return []

    where_clauses = ["po.docstatus = 1"]
    params: list[Any] = []

    if from_date and to_date:
        where_clauses.append("po.transaction_date BETWEEN %s AND %s")
        params.extend([from_date, to_date])
    elif from_date:
        where_clauses.append("po.transaction_date >= %s")
        params.append(from_date)
    elif to_date:
        where_clauses.append("po.transaction_date <= %s")
        params.append(to_date)

    if users:
        where_clauses.append("po.owner IN %s")
        params.append(tuple(users))

    if branch_filter:
        if isinstance(branch_filter, (list, tuple)) and len(branch_filter) == 2 and branch_filter[0] == "in":
            where_clauses.append("po.branch IN %s")
            params.append(tuple(branch_filter[1]))
        elif isinstance(branch_filter, str):
            where_clauses.append("po.branch = %s")
            params.append(branch_filter)

    where_sql = " AND ".join(where_clauses)

    query = f"""
        SELECT
            po.owner AS user_id,
            COUNT(po.name) AS count,
            COALESCE(SUM(po.grand_total), 0) AS total_amount
        FROM `tabPurchase Order` po
        WHERE {where_sql}
        GROUP BY po.owner
        ORDER BY count DESC, total_amount DESC
    """

    try:
        rows = frappe.db.sql(query, params, as_dict=True)
    except Exception:
        rows = []

    user_ids = [r["user_id"] for r in rows if r.get("user_id")]
    user_names = {}
    if user_ids:
        try:
            user_records = frappe.db.get_all(
                "User",
                filters={"name": ["in", user_ids]},
                fields=["name", "full_name"],
                limit_page_length=0,
            )
            for u in user_records:
                user_names[u["name"]] = u.get("full_name") or u["name"]
        except Exception:
            pass

    result = []
    for r in rows:
        uid = r.get("user_id") or "Unknown"
        result.append({
            "id": uid,
            "full_name": user_names.get(uid) or uid,
            "count": cint(r.get("count")),
            "total_amount": round(flt(r.get("total_amount")), 2),
        })

    return result


def _get_mr_trends(
    branch_filter: Any,
    users: list[str],
    from_date: str | None,
    to_date: str | None,
) -> dict[str, Any]:
    """Calculate daily Material Request item procurement trends for the period."""
    if not _doctype_exists("Material Request"):
        return {"daily_data": [], "trend_direction": "stable", "trend_emoji": "▬", "change_percentage": 0, "total_this_month": 0}

    today_str = nowdate()
    start_d = getdate(from_date) if from_date else getdate(today_str)
    end_d = getdate(to_date) if to_date else getdate(today_str)

    # If start and end date are the same day (e.g. Today filter), expand visualization window to 30 days
    is_single_day = (start_d == end_d)
    vis_start_d = frappe.utils.add_days(end_d, -29) if is_single_day else start_d

    where_clauses = ["mr.docstatus = 1"]
    params: list[Any] = []

    where_clauses.append("mr.transaction_date BETWEEN %s AND %s")
    params.extend([str(vis_start_d), str(end_d)])

    if users:
        where_clauses.append("mr.owner IN %s")
        params.append(tuple(users))

    if branch_filter:
        if isinstance(branch_filter, (list, tuple)) and len(branch_filter) == 2 and branch_filter[0] == "in":
            where_clauses.append("mr.branch IN %s")
            params.append(tuple(branch_filter[1]))
        elif isinstance(branch_filter, str):
            where_clauses.append("mr.branch = %s")
            params.append(branch_filter)

    has_item_dt = _doctype_exists("Material Request Item")
    where_sql = " AND ".join(where_clauses)

    if has_item_dt:
        query = f"""
            SELECT
                mr.transaction_date AS d_date,
                COUNT(mri.name) AS count,
                COUNT(DISTINCT mr.name) AS doc_count,
                COALESCE(SUM(mri.qty), 0) AS total_qty
            FROM `tabMaterial Request` mr
            LEFT JOIN `tabMaterial Request Item` mri
                ON mri.parent = mr.name AND mri.parenttype = 'Material Request'
            WHERE {where_sql}
            GROUP BY mr.transaction_date
            ORDER BY mr.transaction_date ASC
        """
    else:
        query = f"""
            SELECT
                mr.transaction_date AS d_date,
                COUNT(mr.name) AS count,
                COUNT(mr.name) AS doc_count,
                0 AS total_qty
            FROM `tabMaterial Request` mr
            WHERE {where_sql}
            GROUP BY mr.transaction_date
            ORDER BY mr.transaction_date ASC
        """

    try:
        daily_counts = frappe.db.sql(query, params, as_dict=True)
    except Exception:
        daily_counts = []

    date_map = {}
    for row in daily_counts:
        d_val = row.get("d_date")
        if d_val:
            d_str = str(getdate(d_val))
            item_cnt = cint(row.get("count"))
            doc_cnt = cint(row.get("doc_count"))
            date_map[d_str] = item_cnt if item_cnt > 0 else doc_cnt

    trends = []
    cur = getdate(vis_start_d)
    target_end = getdate(end_d)
    safety = 0
    while cur <= target_end and safety < 400:
        d_str = str(cur)
        trends.append({
            "date": d_str,
            "count": date_map.get(d_str, 0),
            "label": cur.strftime("%d %b"),
        })
        cur = frappe.utils.add_days(cur, 1)
        safety += 1

    counts = [t["count"] for t in trends]
    total_in_period = sum(counts)

    # Calculate trend percentage (first half vs second half)
    if len(trends) >= 2:
        mid = len(trends) // 2
        first_half = sum(t["count"] for t in trends[:mid])
        second_half = sum(t["count"] for t in trends[mid:])
        if first_half > 0:
            change_pct = ((second_half - first_half) / first_half) * 100
        else:
            change_pct = 0 if second_half == 0 else 100

        if change_pct < -10:
            trend_direction, trend_emoji = "down", "📉"
        elif change_pct > 10:
            trend_direction, trend_emoji = "up", "📈"
        else:
            trend_direction, trend_emoji = "stable", "📊"
    else:
        change_pct, trend_direction, trend_emoji = 0, "stable", "📊"

    return {
        "daily_data": trends,
        "trend_direction": trend_direction,
        "trend_emoji": trend_emoji,
        "change_percentage": round(change_pct, 1),
        "total_this_month": total_in_period,
    }


def _get_po_pending_card(
    branch: Any,
    users: list[str],
    from_date: str | None,
    to_date: str | None,
    prev_from_date: str | None = None,
    prev_to_date: str | None = None,
) -> dict[str, Any]:
    """Card 1: Mr Pending
    Shows Material Request data with filter:
    docstatus = 1, status in ('Submitted', 'Partially Ordered', 'Pending'), owner in users (Created By)
    """
    doctype = "Material Request"
    if not _doctype_exists(doctype) or not frappe.has_permission(doctype, "read"):
        return {"id": "po_pending", "title": _("MR Pending"), "doctype": doctype, "count": 0, "previous_count": 0, "delta": _calculate_delta(0, 0), "items": []}

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

    # Previous period count
    prev_filters = dict(filters)
    if prev_from_date and prev_to_date:
        prev_filters["transaction_date"] = ["between", [prev_from_date, prev_to_date]]
    elif prev_from_date:
        prev_filters["transaction_date"] = [">=", prev_from_date]
    elif prev_to_date:
        prev_filters["transaction_date"] = ["<=", prev_to_date]
    else:
        prev_filters.pop("transaction_date", None)
    prev_count = frappe.db.count(doctype, filters=prev_filters) if (prev_from_date or prev_to_date) else None
    delta = _calculate_delta(total_count, prev_count)

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

    distinct_items: set[str] = set()
    total_item_qty: float = 0.0
    total_item_amount: float = 0.0
    for r in card_items:
        for di in r.get("doc_items") or []:
            icode = di.get("item_code")
            if icode:
                distinct_items.add(icode)
            total_item_qty += flt(di.get("qty"))
            total_item_amount += flt(di.get("amount"))

    item_count = len(distinct_items)
    prev_item_count = _count_distinct_items_for_prev(doctype, prev_filters) if (prev_from_date or prev_to_date) else None
    item_delta = _calculate_delta(item_count, prev_item_count)

    return {
        "id": "po_pending",
        "title": _("MR Pending"),
        "doctype": doctype,
        "count": total_count,
        "previous_count": prev_count,
        "delta": delta,
        "item_count": item_count,
        "previous_item_count": prev_item_count,
        "item_delta": item_delta,
        "total_item_qty": round(total_item_qty, 2),
        "total_item_amount": round(total_item_amount, 2),
        "color": "clr-cyan",
        "icon": "octicon octicon-file-text",
        "items": card_items,
    }


def _get_mr_completed_card(
    branch: Any,
    users: list[str],
    from_date: str | None,
    to_date: str | None,
    prev_from_date: str | None = None,
    prev_to_date: str | None = None,
) -> dict[str, Any]:
    """Card 2: MR Completed
    Shows Material Request data with filter:
    docstatus = 1, status in ('Partially Received', 'Ordered', 'Issued', 'Transferred', 'Received'), owner in users (Created By)
    """
    doctype = "Material Request"
    if not _doctype_exists(doctype) or not frappe.has_permission(doctype, "read"):
        return {"id": "mr_completed", "title": _("MR Completed"), "doctype": doctype, "count": 0, "previous_count": 0, "delta": _calculate_delta(0, 0), "items": []}

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

    # Previous period count
    prev_filters = dict(filters)
    if prev_from_date and prev_to_date:
        prev_filters["transaction_date"] = ["between", [prev_from_date, prev_to_date]]
    elif prev_from_date:
        prev_filters["transaction_date"] = [">=", prev_from_date]
    elif prev_to_date:
        prev_filters["transaction_date"] = ["<=", prev_to_date]
    else:
        prev_filters.pop("transaction_date", None)
    prev_count = frappe.db.count(doctype, filters=prev_filters) if (prev_from_date or prev_to_date) else None
    delta = _calculate_delta(total_count, prev_count)

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

    distinct_items: set[str] = set()
    total_item_qty: float = 0.0
    total_item_amount: float = 0.0
    for r in card_items:
        for di in r.get("doc_items") or []:
            icode = di.get("item_code")
            if icode:
                distinct_items.add(icode)
            total_item_qty += flt(di.get("qty"))
            total_item_amount += flt(di.get("amount"))

    item_count = len(distinct_items)
    prev_item_count = _count_distinct_items_for_prev(doctype, prev_filters) if (prev_from_date or prev_to_date) else None
    item_delta = _calculate_delta(item_count, prev_item_count)

    return {
        "id": "mr_completed",
        "title": _("MR Completed"),
        "doctype": doctype,
        "count": total_count,
        "previous_count": prev_count,
        "delta": delta,
        "item_count": item_count,
        "previous_item_count": prev_item_count,
        "item_delta": item_delta,
        "total_item_qty": round(total_item_qty, 2),
        "total_item_amount": round(total_item_amount, 2),
        "color": "clr-amber",
        "icon": "octicon octicon-check",
        "items": card_items,
    }


def _get_pr_pending_card(
    branch: Any,
    users: list[str],
    from_date: str | None,
    to_date: str | None,
    prev_from_date: str | None = None,
    prev_to_date: str | None = None,
) -> dict[str, Any]:
    """Card 3: PR Pending
    Shows Purchase Order data with filter:
    docstatus = 1, status in ('To Receive and Bill', 'To Receive'), owner in users (Created By)
    """
    doctype = "Purchase Order"
    if not _doctype_exists(doctype) or not frappe.has_permission(doctype, "read"):
        return {"id": "pr_pending", "title": _("PR Pending"), "doctype": doctype, "count": 0, "previous_count": 0, "delta": _calculate_delta(0, 0), "items": []}

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

    # Previous period count
    prev_filters = dict(filters)
    if prev_from_date and prev_to_date:
        prev_filters["transaction_date"] = ["between", [prev_from_date, prev_to_date]]
    elif prev_from_date:
        prev_filters["transaction_date"] = [">=", prev_from_date]
    elif prev_to_date:
        prev_filters["transaction_date"] = ["<=", prev_to_date]
    else:
        prev_filters.pop("transaction_date", None)
    prev_count = frappe.db.count(doctype, filters=prev_filters) if (prev_from_date or prev_to_date) else None
    delta = _calculate_delta(total_count, prev_count)

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

    distinct_items: set[str] = set()
    total_item_qty: float = 0.0
    total_item_amount: float = 0.0
    for r in card_items:
        for di in r.get("doc_items") or []:
            icode = di.get("item_code")
            if icode:
                distinct_items.add(icode)
            total_item_qty += flt(di.get("qty"))
            total_item_amount += flt(di.get("amount"))

    item_count = len(distinct_items)
    prev_item_count = _count_distinct_items_for_prev(doctype, prev_filters) if (prev_from_date or prev_to_date) else None
    item_delta = _calculate_delta(item_count, prev_item_count)

    return {
        "id": "pr_pending",
        "title": _("PR Pending"),
        "doctype": doctype,
        "count": total_count,
        "previous_count": prev_count,
        "delta": delta,
        "item_count": item_count,
        "previous_item_count": prev_item_count,
        "item_delta": item_delta,
        "total_item_qty": round(total_item_qty, 2),
        "total_item_amount": round(total_item_amount, 2),
        "color": "clr-indigo",
        "icon": "octicon octicon-git-branch",
        "items": card_items,
    }


def _get_pi_pending_card(
    branch: Any,
    users: list[str],
    from_date: str | None,
    to_date: str | None,
    prev_from_date: str | None = None,
    prev_to_date: str | None = None,
) -> dict[str, Any]:
    """Card 4: PI Pending
    Shows Purchase Receipt data with filter:
    docstatus = 1, status in ('Partly Billed', 'To Bill', 'Partially Billed'), owner in users (Created By)
    """
    doctype = "Purchase Receipt"
    if not _doctype_exists(doctype) or not frappe.has_permission(doctype, "read"):
        return {"id": "pi_pending", "title": _("PI Pending"), "doctype": doctype, "count": 0, "previous_count": 0, "delta": _calculate_delta(0, 0), "items": []}

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

    # Previous period count
    prev_filters = dict(filters)
    if prev_from_date and prev_to_date:
        prev_filters["posting_date"] = ["between", [prev_from_date, prev_to_date]]
    elif prev_from_date:
        prev_filters["posting_date"] = [">=", prev_from_date]
    elif prev_to_date:
        prev_filters["posting_date"] = ["<=", prev_to_date]
    else:
        prev_filters.pop("posting_date", None)
    prev_count = frappe.db.count(doctype, filters=prev_filters) if (prev_from_date or prev_to_date) else None
    delta = _calculate_delta(total_count, prev_count)

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

    distinct_items: set[str] = set()
    total_item_qty: float = 0.0
    total_item_amount: float = 0.0
    for r in card_items:
        for di in r.get("doc_items") or []:
            icode = di.get("item_code")
            if icode:
                distinct_items.add(icode)
            total_item_qty += flt(di.get("qty"))
            total_item_amount += flt(di.get("amount"))

    item_count = len(distinct_items)
    prev_item_count = _count_distinct_items_for_prev(doctype, prev_filters) if (prev_from_date or prev_to_date) else None
    item_delta = _calculate_delta(item_count, prev_item_count)

    return {
        "id": "pi_pending",
        "title": _("PI Pending"),
        "doctype": doctype,
        "count": total_count,
        "previous_count": prev_count,
        "delta": delta,
        "item_count": item_count,
        "previous_item_count": prev_item_count,
        "item_delta": item_delta,
        "total_item_qty": round(total_item_qty, 2),
        "total_item_amount": round(total_item_amount, 2),
        "color": "clr-rose",
        "icon": "octicon octicon-clock",
        "items": card_items,
    }


def _get_pi_completed_card(
    branch: Any,
    users: list[str],
    from_date: str | None,
    to_date: str | None,
    prev_from_date: str | None = None,
    prev_to_date: str | None = None,
) -> dict[str, Any]:
    """Card 5: Total PI Completed
    Shows Purchase Invoice data with filter:
    docstatus = 1, is_return = 0, owner in users (Created By)
    """
    doctype = "Purchase Invoice"
    if not _doctype_exists(doctype) or not frappe.has_permission(doctype, "read"):
        return {"id": "pi_completed", "title": _("Total PI Completed"), "doctype": doctype, "count": 0, "previous_count": 0, "delta": _calculate_delta(0, 0), "items": []}

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

    # Previous period count
    prev_filters = dict(filters)
    if prev_from_date and prev_to_date:
        prev_filters["posting_date"] = ["between", [prev_from_date, prev_to_date]]
    elif prev_from_date:
        prev_filters["posting_date"] = [">=", prev_from_date]
    elif prev_to_date:
        prev_filters["posting_date"] = ["<=", prev_to_date]
    else:
        prev_filters.pop("posting_date", None)
    prev_count = frappe.db.count(doctype, filters=prev_filters) if (prev_from_date or prev_to_date) else None
    delta = _calculate_delta(total_count, prev_count)

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

    distinct_items: set[str] = set()
    total_item_qty: float = 0.0
    total_item_amount: float = 0.0
    for r in card_items:
        for di in r.get("doc_items") or []:
            icode = di.get("item_code")
            if icode:
                distinct_items.add(icode)
            total_item_qty += flt(di.get("qty"))
            total_item_amount += flt(di.get("amount"))

    item_count = len(distinct_items)
    prev_item_count = _count_distinct_items_for_prev(doctype, prev_filters) if (prev_from_date or prev_to_date) else None
    item_delta = _calculate_delta(item_count, prev_item_count)

    return {
        "id": "pi_completed",
        "title": _("Total PI Completed"),
        "doctype": doctype,
        "count": total_count,
        "previous_count": prev_count,
        "delta": delta,
        "item_count": item_count,
        "previous_item_count": prev_item_count,
        "item_delta": item_delta,
        "total_item_qty": round(total_item_qty, 2),
        "total_item_amount": round(total_item_amount, 2),
        "color": "clr-emerald",
        "icon": "octicon octicon-checklist",
        "items": card_items,
    }