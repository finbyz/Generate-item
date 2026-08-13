/**
 * User-specific post-login redirect - client side.
 *
 * Fires once per NEW login (detected via a change in the `sid` session
 * cookie compared to the last boot we saw), and only redirects when the
 * current user has Login Redirect enabled with a route the server has
 * already validated (frappe.boot.login_redirect_enabled /
 * frappe.boot.login_redirect_route, populated in overrides/boot.py).
 *
 * This is intentionally NOT a route guard:
 *   - after the one-time redirect, the user can navigate anywhere
 *   - refreshing the browser on any page will NOT bounce them back to
 *     the configured landing page
 *   - logging out and back in triggers exactly one more redirect
 */
(function () {
	"use strict";

	var STORAGE_KEY = "generate_item:login_redirect:last_sid";

	function get_sid() {
		// The 'sid' cookie is HttpOnly in Frappe v15+, so we cannot read it via document.cookie.
		// However, frappe.csrf_token is unique per session and changes on every login,
		// making it a perfect substitute for detecting a fresh session.
		return window.frappe && frappe.csrf_token ? frappe.csrf_token : null;
	}

	// Defense in depth: re-validate on the client even though the server
	// already filtered the value. Only internal /app/... routes - no
	// scheme, no protocol-relative URLs, no javascript:/data: URIs.
  
	function is_safe_route(route) {
		if (!route || typeof route !== "string") return false;
		var trimmed = route.trim();
	    if (!(trimmed === "/app" || trimmed.indexOf("/app/") === 0)) return false;
		if (trimmed.indexOf("//") === 0) return false;

		var lowered = trimmed.toLowerCase();
		if (
			lowered.indexOf("://") !== -1 ||
			lowered.indexOf("javascript:") === 0 ||
			lowered.indexOf("data:") === 0 ||
			lowered.indexOf("vbscript:") === 0
		) {
			return false;
		}

		return /^\/app(\/[A-Za-z0-9 _\-.%&]+)*\/?$/.test(trimmed);
	}

	function redirect_to(route) {
		// Strip the leading "/app" and hand the remaining tokens to
		// frappe.set_route, which stays inside the SPA router instead of
		// doing a full page navigation to an arbitrary URL. This also
		// means query-report / doc-name routes with spaces (e.g.
		// "/app/query-report/My Report") are parsed the same way Frappe
		// itself parses them everywhere else.
		var path = route.replace(/^\/app\/?/, "");
		if (!path) return;

		var parts = path.split("/").filter(function (p) {
			return p.length > 0;
		});

		if (!parts.length) return;

		frappe.set_route(parts);
	}

	function maybe_redirect_after_login() {
		// console.log("Login Redirect: Checking if we should redirect...");
		if (!window.frappe || !frappe.boot || !frappe.session) {
			// console.log("Login Redirect: Missing frappe, boot, or session");
			return;
		}
		if (!frappe.session.user || frappe.session.user === "Guest") {
			// console.log("Login Redirect: User is Guest or missing");
			return;
		}
		if (!frappe.boot.login_redirect_enabled || !frappe.boot.login_redirect_route) {
			// console.log("Login Redirect: Not enabled or no route in bootinfo", frappe.boot.login_redirect_enabled, frappe.boot.login_redirect_route);
			return;
		}

		var current_sid = get_sid();
		var last_sid = window.localStorage.getItem(STORAGE_KEY);

		// console.log("Login Redirect: current_sid =", current_sid, "last_sid =", last_sid);

		if (current_sid) {
			window.localStorage.setItem(STORAGE_KEY, current_sid);
		}

		if (!current_sid || current_sid === last_sid) {
			// console.log("Login Redirect: Same session, not redirecting");
			// Same session as the last boot we recorded - this is a route
			// change, a refresh, or a re-render, NOT a fresh login. Leave
			// the user wherever they currently are.
			return;
		}

		var route = frappe.boot.login_redirect_route;
		// console.log("Login Redirect: Route from bootinfo =", route);
		if (!is_safe_route(route)) {
			// console.log("Login Redirect: Route is not safe!", route);
			return;
		}

		// console.log("Login Redirect: Redirecting to", route);
		redirect_to(route);
	}

	$(document).on("app_ready", function () {
		// console.log("Login Redirect: app_ready fired");
		if (window._login_redirect_bound) return;
		window._login_redirect_bound = true;

		// Frappe's router is async and will overwrite our redirect if we fire
		// it immediately. Wait for the first route change to finish.
		frappe.router.on("change", function () {
			// console.log("Login Redirect: router change fired");
			if (window._login_redirect_done) return;
			window._login_redirect_done = true;
			
			// Small delay to ensure the initial page render is fully complete
			setTimeout(function () {
				maybe_redirect_after_login();
			}, 100);
		});
	});
})();
