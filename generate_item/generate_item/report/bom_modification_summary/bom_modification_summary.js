// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt



frappe.query_reports["BOM Modification Summary"] = {
	filters: [
		{
			fieldname: "bom",
			label: __("BOM"),
			fieldtype: "Link",
			options: "BOM",
		},
		{
			fieldname: "batch_no_ref",
			label: __("Batch No Ref"),
			fieldtype: "Link",
			options: "Batch",
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
		},
	],

	onload: function (report) {
		// Fix: the BOM (Link) filter's autocomplete dropdown renders behind
		// the report's datatable header/rows. This happens because the
		// datatable creates its own stacking context, trapping the
		// Awesomplete dropdown even though its own z-index is high.
		// Raising the filter row's stacking context above the datatable's
		// fixes it.
		if (document.getElementById("bom-modification-summary-zindex-fix")) {
			return;
		}

		const style = document.createElement("style");
		style.id = "bom-modification-summary-zindex-fix";
		style.innerHTML = `
			.page-form {
				position: relative;
				z-index: 5;
			}
			.awesomplete ul,
			ul.awesomplete-list {
				z-index: 9999 !important;
			}
			.datatable {
				z-index: 1;
			}
		`;
		document.head.appendChild(style);
	},
};