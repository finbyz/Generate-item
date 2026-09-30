// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt

frappe.query_reports["Pattern Set Stock Status"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "mould_set_item",
			label: __("Pattern Set Item"),
			fieldtype: "Link",
			options: "Item",
			get_query: () => {
				return {
					query: "generate_item.mould_set_management.doctype.pattern_movement.pattern_movement.mould_set_item_query",
				};
			},
		},
		{
			fieldname: "mould_set",
			label: __("Pattern Set"),
			fieldtype: "Link",
			options: "Pattern Set",
		},
		{
			fieldname: "supplier",
			label: __("Supplier"),
			fieldtype: "Link",
			options: "Supplier",
		},
		{
			fieldname: "warehouse",
			label: __("Warehouse"),
			fieldtype: "Link",
			options: "Warehouse",
		},
		{
			fieldname: "is_supplier_warehouse",
			label: __("Supplier Warehouses Only"),
			fieldtype: "Check",
		},
	],
};
