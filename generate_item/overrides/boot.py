# Copyright (c) 2026, your_company and contributors
# License: per project license

"""
User-specific post-login redirect - server side.

Extends `bootinfo` (available on the client as `frappe.boot`) with a
*validated* target route for the currently logged-in user, based on the
`custom_enable_login_redirect` / `custom_login_redirect_route` Custom
Fields on the core `User` DocType.

Design notes
------------
- This module only decides WHAT is safe to expose. It never decides WHEN
  to redirect - that decision is made once, client-side, in
  `public/js/login_redirect.js`. Keeping the "only once, right after
  login" logic on the client (keyed off the session cookie) means this
  hook can run on every boot (login, refresh, new tab) without any risk
  of turning into a route guard or a redirect loop.
- `boot_session` is called for every boot request (frappe/sessions.py ->
  frappe/boot.py), i.e. on login and on every full page load of /app.
  That is standard framework behaviour and is not something this app
  needs to special-case.
- Users who don't have the fields configured (or don't have the columns
  populated at all) simply get `login_redirect_enabled = 0`, which is
  identical to today's behaviour.
"""

import re

import frappe

# Only internal Desk routes are accepted:
#   - must start with /app
#   - every path segment must be non-empty (this also rules out "//"
#     appearing anywhere in the route, so protocol-relative URLs like
#     "//evil.example.com" can never match)
#   - only a safe character set is allowed per segment (letters, digits,
#     space, underscore, hyphen, dot, percent, ampersand) - this excludes
#     ":" (so "javascript:", "data:", "http://" etc. can never match),
#     "?", "#", quotes, angle brackets and backslashes.
ALLOWED_ROUTE_PATTERN = re.compile(r"^/app(/[A-Za-z0-9 _\-.%&]+)*/?$")



def boot_session(bootinfo):
	"""Hooked via `boot_session` in hooks.py."""

	bootinfo.login_redirect_enabled = 0
	bootinfo.login_redirect_route = ""

	user = frappe.session.user
	if not user or user == "Guest":
		return

	try:
		# Check if custom fields exist in the database before querying
		if not (
			frappe.db.has_column("User", "custom_enable_login_redirect")
			and frappe.db.has_column("User", "custom_login_redirect_route")
		):
			return

		row = frappe.db.get_value(
			"User",
			user,
			["custom_enable_login_redirect", "custom_login_redirect_route"],
			as_dict=True,
		)

		# Covers: user predates the custom fields, columns not yet migrated,
		# or the user simply never configured anything. All of these must
		# behave exactly like normal Frappe today.
		if not row:
			return

		enabled = row.get("custom_enable_login_redirect")
		route = (row.get("custom_login_redirect_route") or "").strip()

		if not enabled or not route:
			return

		# Normalize route to always start with /app
		if route.startswith("app/"):
			route = "/" + route
		elif route.startswith("desk/"):
			route = "/app/" + route[5:]
		elif not (route == "/app" or route.startswith("/app/")):
			if route.startswith("/"):
				route = "/app" + route
			else:
				route = "/app/" + route

		if not is_safe_internal_route(route):
			frappe.log_error(
				title="Login Redirect: unsafe route ignored",
				message=f"User {user!r} has an invalid Login Redirect Route configured: {route!r}",
			)
			return

		bootinfo.login_redirect_enabled = 1
		bootinfo.login_redirect_route = route

	except Exception:
		# Graceful fallback: never fail desk boot/login if any database or schema issue occurs
		frappe.logger("generate_item").warning(
			f"Could not load login redirect config for user {user}", exc_info=True
		)


def is_safe_internal_route(route: str) -> bool:
	"""True only for internal Desk routes, e.g. /app/sales-order/SO-00001."""

	if not route:
		return False

	trimmed = route.strip()
	lowered = trimmed.lower()

	if "\n" in trimmed or "\r" in trimmed:
		return False
	if "://" in lowered:
		return False
	if lowered.startswith("//"):
		return False
	if lowered.startswith("javascript:") or lowered.startswith("data:") or lowered.startswith("vbscript:"):
		return False

	return bool(ALLOWED_ROUTE_PATTERN.match(trimmed))
