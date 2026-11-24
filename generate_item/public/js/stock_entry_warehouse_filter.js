// Stock Entry: restrict Source / Target Warehouse to warehouses WITHOUT a Supplier
// (Warehouse.custom_supplier is not set) for every Stock Entry Type except the
// excluded subcontracting / customer-material types below. Users with the
// System Manager role are exempt and see all warehouses.
//
// ERPNext core installs its own warehouse queries (company, is_group, transit,
// sample retention) in onload and again asynchronously. Instead of replacing
// them, this script wraps them: the core filters stay, and the supplier
// condition is added on top only when the current Stock Entry Type needs it.
// The type is read each time the query runs, so changing the Stock Entry Type
// takes effect at once and no stale filter is left behind.

(function () {
	const SUPPLIER_FILTER_EXCLUDED_TYPES = [
		"Send to Subcontractor",
		"Receive from Customer",
		"Return Raw Material to Customer",
		"Subcontracting Delivery",
		"Subcontracting Return",
	];

	const HEADER_WAREHOUSE_FIELDS = ["from_warehouse", "to_warehouse"];
	const ITEM_WAREHOUSE_FIELDS = ["s_warehouse", "t_warehouse"];

	// Users with these roles are exempt and see all warehouses.
	const SUPPLIER_FILTER_EXEMPT_ROLES = ["System Manager"];

	function needs_supplier_filter(doc) {
		if (!doc || !doc.stock_entry_type) return false;
		if (SUPPLIER_FILTER_EXEMPT_ROLES.some((role) => frappe.user.has_role(role))) return false;
		return (
			!SUPPLIER_FILTER_EXCLUDED_TYPES.includes(doc.stock_entry_type) &&
			!SUPPLIER_FILTER_EXCLUDED_TYPES.includes(doc.purpose)
		);
	}

	function add_supplier_condition(query) {
		const q = Object.assign({}, query || {});
		const filters = q.filters;

		if (Array.isArray(filters)) {
			q.filters = filters.concat([["Warehouse", "custom_supplier", "is", "not set"]]);
		} else {
			q.filters = Object.assign({}, filters || {}, { custom_supplier: ["is", "not set"] });
		}
		return q;
	}

	function wrap_warehouse_query(frm, base_query) {
		if (base_query && base_query.__supplier_wh_wrapped) return base_query;

		const wrapped = function (doc, cdt, cdn) {
			const query = typeof base_query === "function" ? base_query(doc, cdt, cdn) : base_query;
			if (!needs_supplier_filter(frm.doc)) return query;
			return add_supplier_condition(query);
		};
		wrapped.__supplier_wh_wrapped = true;
		return wrapped;
	}

	function is_target_field(fieldname, parentfield) {
		if (parentfield) {
			return parentfield === "items" && ITEM_WAREHOUSE_FIELDS.includes(fieldname);
		}
		return HEADER_WAREHOUSE_FIELDS.includes(fieldname);
	}

	// Wrap any warehouse query that is already installed on the form.
	function ensure_queries_wrapped(frm) {
		HEADER_WAREHOUSE_FIELDS.forEach((fieldname) => {
			const field = frm.fields_dict[fieldname];
			if (field) field.get_query = wrap_warehouse_query(frm, field.get_query);
		});

		const grid = frm.fields_dict.items && frm.fields_dict.items.grid;
		if (grid) {
			ITEM_WAREHOUSE_FIELDS.forEach((fieldname) => {
				const df = grid.get_field(fieldname);
				if (df) df.get_query = wrap_warehouse_query(frm, df.get_query);
			});
		}
	}

	// Intercept later set_query calls (core sets warehouse queries in onload,
	// on company change, and inside an async Company lookup).
	function patch_set_query(frm) {
		if (frm.__supplier_wh_set_query_patched) return;
		frm.__supplier_wh_set_query_patched = true;

		const original_set_query = frm.set_query;
		frm.set_query = function (fieldname, opt1, opt2) {
			if (opt2) {
				if (is_target_field(fieldname, opt1)) opt2 = wrap_warehouse_query(frm, opt2);
				return original_set_query.call(this, fieldname, opt1, opt2);
			}
			if (is_target_field(fieldname)) opt1 = wrap_warehouse_query(frm, opt1);
			return original_set_query.call(this, fieldname, opt1);
		};
	}

	frappe.ui.form.on("Stock Entry", {
		setup(frm) {
			patch_set_query(frm);
			ensure_queries_wrapped(frm);
		},

		refresh(frm) {
			patch_set_query(frm);
			ensure_queries_wrapped(frm);
		},

		stock_entry_type(frm) {
			ensure_queries_wrapped(frm);
		},

		company(frm) {
			ensure_queries_wrapped(frm);
		},
	});
})();
