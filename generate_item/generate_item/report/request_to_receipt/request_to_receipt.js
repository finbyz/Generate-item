// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt


// Report : Request to Receipt
// Tree   : MR (indent=0)  →  PO (indent=1)  →  PR (indent=2)
//
// ── How the tree indentation works ───────────────────────────────────────────
//
// Frappe's DataTable uses virtual scrolling: only visible DOM rows exist at
// any moment, so after_datatable_render / DOM-manipulation approaches are
// unreliable — they only touch the rows rendered at that instant and break
// when the user scrolls.
//
// The correct approach: bake indentation HTML directly into the `row_type`
// column value inside the formatter() callback. formatter() is called for
// every cell every time it is rendered, so it works correctly with virtual
// scroll, filter changes, and pagination alike.
//
// Layout of the `row_type` cell (first column):
//
//   [spacer div width=indent*20px] [coloured badge: MR / PO / PR]
//
// The spacer pushes the badge right, producing the visual tree:
//
//   [MR]  Material Request …
//       [PO]  Purchase Order …
//           [PR]  Receipt …
//           [PR]  Receipt …
//       [PO]  Purchase Order …
// ─────────────────────────────────────────────────────────────────────────────

frappe.query_reports["Request to Receipt"] = {

	// ── Filters ──────────────────────────────────────────────────────────────
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			reqd: 1,
			default: frappe.defaults.get_default("company"),
			width: "100",
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			width: "80",
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.get_today(),
			width: "80",
		},
		{
			
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nReceived\nPending",
			width: "80",
		},
		{
			fieldname: "material_request",
			label: __("Material Request"),
			fieldtype: "Link",
			options: "Material Request",
			width: "80",
			get_query: () => ({
				filters: { docstatus: 1 },
			}),
		},
		{
			fieldname: "item_code",
			label: __("Item"),
			fieldtype: "Link",
			options: "Item",
			width: "80",
			get_query: () => ({
				query: "erpnext.controllers.queries.item_query",
			}),
		},
		{
			fieldname: "branch",
			label: __("Branch"),
			fieldtype: "Link",
			options: "Branch",
			width: "80",
		},
		{
			fieldname: "supplier",
			label: __("Supplier"),
			fieldtype: "Link",
			options: "Supplier",
			width: "80",
		},
		{
			fieldname: "batch",
			label: __("Batch"),
			fieldtype: "Link",
			options: "Batch",
			width: "80",
		},
		{
			fieldname: "po_no",
			label: __("Purchase Order"),
			fieldtype: "Link",
			options: "Purchase Order",
			width: "80",
		},
	],

	// ── Formatter ─────────────────────────────────────────────────────────────
	//
	// Called for EVERY cell on EVERY render (including virtual-scroll redraws).
	// This is the only reliable place to inject visual structure.
	

	formatter(value, row, column, data, default_formatter) {
		if (!data) return default_formatter(value, row, column, data);

		
		const ROW_BG = {
			MR: "#e8f4fd",   
			PO: "#fffbeb",   
			PR: "#f0fdf4",   
		};
		const bg = ROW_BG[data.row_type] || "";

		
		const withBg = (html) =>
			bg
				? `<div style="background:${bg};padding:2px 6px;margin:-3px -6px;">${html}</div>`
				: html;

		if (column.fieldname === "row_type") {
			const indent   = data.indent || 0;
			const spacerPx = indent * 24;
			const BADGE = {
				MR: { bg: "#2563eb", color: "#fff", label: "MR" },
				PO: { bg: "#d97706", color: "#fff", label: "PO" },
				PR: { bg: "#16a34a", color: "#fff", label: "PR" },
			};
			const badge = BADGE[data.row_type];
			if (!badge) return default_formatter(value, row, column, data);

			
			let connector = "";
			if (indent > 0) {
				connector = `<span style="
					display:inline-block;
					width:${spacerPx}px;
					height:16px;
					border-left:2px solid #cbd5e1;
					border-bottom:2px solid #cbd5e1;
					margin-right:4px;
					vertical-align:middle;
					flex-shrink:0;
				"></span>`;
			} else {
				connector = `<span style="display:inline-block;width:4px;flex-shrink:0;"></span>`;
			}

			const badgeHtml = `<span style="
				display:inline-block;
				background:${badge.bg};
				color:${badge.color};
				font-size:0.7rem;
				font-weight:700;
				padding:1px 6px;
				border-radius:3px;
				letter-spacing:0.05em;
				vertical-align:middle;
				white-space:nowrap;
			">${badge.label}</span>`;

			const cellHtml = `<div style="display:flex;align-items:center;gap:0;">${connector}${badgeHtml}</div>`;
			return withBg(cellHtml);
		}

		value = default_formatter(value, row, column, data);

		const raw = String(value || "");
		if (raw.includes("No PO") || raw.includes("No Receipt")) {
			return withBg(
				`<span style="color:#94a3b8;font-style:italic;font-size:0.85em;">${value}</span>`
			);
		}

		
		if (column.fieldname === "mr_status" && value) {
			const STATUS_COLOR = {
				"Received":           { text: "#166534", bg: "#dcfce7", border: "#86efac" },
				"Partially Received": { text: "#92400e", bg: "#fef3c7", border: "#fcd34d" },
				"Pending":            { text: "#991b1b", bg: "#fee2e2", border: "#fca5a5" },
				"Stopped":            { text: "#374151", bg: "#f3f4f6", border: "#d1d5db" },
			};
			const s = STATUS_COLOR[data.mr_status];
			if (s) {
				const badge = `<span style="
					color:${s.text};
					background:${s.bg};
					border:1px solid ${s.border};
					font-size:0.78em;
					font-weight:600;
					padding:2px 8px;
					border-radius:10px;
					white-space:nowrap;
				">${value}</span>`;
				return withBg(badge);
			}
		}

		if (column.fieldname === "balance_qty" && data.balance_qty > 0) {
			return withBg(
				`<span style="color:#dc2626;font-weight:700;">${value}</span>`
			);
		}

		
		if (data.row_type === "MR" && value) {
			return withBg(`<span style="font-weight:600;">${value}</span>`);
		}

		
		return withBg(value || "");
	},
};