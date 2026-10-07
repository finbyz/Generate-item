# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import json
from io import BytesIO
import frappe
from frappe import _
from frappe.utils import flt, cint, cstr


def is_common_warehouse(wh_info):
	"""
	Determines if a warehouse is classified as a Common Warehouse based on:
	1. Explicit custom fields (e.g. is_common, is_common_warehouse, common_warehouse)
	2. Warehouse Type containing 'common' or 'central'
	3. Naming convention: 'common' in warehouse name / warehouse_name (case-insensitive)
	4. Absence of a specific branch when branch custom field exists
	"""
	if not wh_info:
		return False

	# 1. Custom checkbox fields
	for field in ("is_common", "is_common_warehouse", "common_warehouse", "is_central"):
		if wh_info.get(field):
			return True

	# 2. Warehouse Type
	wh_type = (wh_info.get("warehouse_type") or "").strip().lower()
	if "common" in wh_type or "central" in wh_type:
		return True

	# 3. Naming convention in name or warehouse_name
	name = (wh_info.get("name") or "").strip().lower()
	wh_name = (wh_info.get("warehouse_name") or "").strip().lower()
	if "common" in name or "common" in wh_name:
		return True

	return False


def get_descendant_warehouses(warehouse):
	"""
	Returns a list of leaf warehouse names (is_group = 0) under the given warehouse.
	If warehouse is a leaf warehouse, returns [warehouse].
	If warehouse is a group warehouse, returns all leaf descendant warehouses using nested set hierarchy.
	"""
	if not warehouse:
		return []

	wh_doc = frappe.db.get_value("Warehouse", warehouse, ["is_group", "lft", "rgt"], as_dict=True)
	if not wh_doc:
		return [warehouse]

	if not wh_doc.get("is_group"):
		return [warehouse]

	lft = wh_doc.get("lft")
	rgt = wh_doc.get("rgt")

	if lft and rgt and lft < rgt:
		descendants = frappe.db.sql_list(
			"""
			SELECT name
			FROM `tabWarehouse`
			WHERE lft >= %(lft)s AND rgt <= %(rgt)s AND is_group = 0
			ORDER BY warehouse_name ASC
			""",
			{"lft": lft, "rgt": rgt},
		)
		if descendants:
			return descendants

	# Fallback if nested set is not populated: check parent_warehouse recursively
	child_whs = frappe.db.sql_list(
		"""
		SELECT name
		FROM `tabWarehouse`
		WHERE parent_warehouse = %(parent)s AND is_group = 0
		ORDER BY warehouse_name ASC
		""",
		{"parent": warehouse},
	)
	return child_whs or [warehouse]


def get_attribute_values(possible_attr_names, pattern_set_field=None):
	"""
	Fetches values from Custom Item Attribute Value child table (Item Generator logic)
	for given possible parent attribute names, and merges with distinct values from Pattern Set doctype.
	"""
	options = []
	seen = set()

	# 1. Fetch from Custom Item Attribute Value (Item Generator logic)
	try:
		if frappe.db.table_exists("Custom Item Attribute"):
			existing_parents = frappe.db.sql_list(
				"""
				SELECT name
				FROM `tabCustom Item Attribute`
				WHERE name IN %(names)s
				""",
				{"names": tuple(possible_attr_names)},
			)
			if not existing_parents:
				# Fallback to suffix / pattern match
				like_conditions = " OR ".join(["name LIKE %s" for _ in possible_attr_names])
				like_params = [f"%{name.split('-')[-1]}%" for name in possible_attr_names]
				existing_parents = frappe.db.sql_list(
					f"SELECT name FROM `tabCustom Item Attribute` WHERE {like_conditions}",
					tuple(like_params),
				)

			if existing_parents and frappe.db.table_exists("Custom Item Attribute Value"):
				rows = frappe.db.sql(
					"""
					SELECT DISTINCT item_long_description
					FROM `tabCustom Item Attribute Value`
					WHERE parent IN %(parents)s AND disabled = 0 AND IFNULL(item_long_description, '') != ''
					ORDER BY idx ASC, name ASC
					""",
					{"parents": tuple(existing_parents)},
					as_dict=True,
				)
				for r in rows:
					val = (r.item_long_description or "").strip()
					if val and val != "-" and val not in seen:
						seen.add(val)
						options.append(val)
	except Exception:
		pass

	# 2. Merge with distinct values in Pattern Set table if field provided
	if pattern_set_field and frappe.db.table_exists("Pattern Set"):
		try:
			ps_vals = frappe.db.sql_list(
				f"""
				SELECT DISTINCT `{pattern_set_field}`
				FROM `tabPattern Set`
				WHERE IFNULL(`{pattern_set_field}`, '') != '' AND docstatus != 2
				ORDER BY `{pattern_set_field}` ASC
				"""
			)
			for val in ps_vals:
				val_str = str(val).strip()
				if val_str and val_str not in seen:
					seen.add(val_str)
					options.append(val_str)
		except Exception:
			pass

	return options


@frappe.whitelist()
def get_filter_options():
	"""
	Returns distinct available options for Type of Valve, Size, and Class
	using Item Generator (Custom Item Attribute) logic merged with Pattern Sets.
	"""
	if not frappe.has_permission("Pattern Set", "read"):
		frappe.throw(_("Not permitted to view Pattern Set data"), frappe.PermissionError)

	types_of_valve = get_attribute_values(
		["WIP-Type Of Valve", "FG-Valve Type", "Type Of Valve", "Type of Valve", "Valve Type"],
		pattern_set_field="type_of_valve",
	)
	sizes = get_attribute_values(
		["WIP-Size", "FG-Size", "Size"],
		pattern_set_field="size",
	)
	classes = get_attribute_values(
		["WIP-Class", "FG-Rating", "Class", "Rating"],
		pattern_set_field="class",
	)

	return {
		"types_of_valve": types_of_valve,
		"sizes": sizes,
		"classes": classes,
	}


@frappe.whitelist()
def get_pattern_set_component_availability(
	pattern_set=None,
	component_item=None,
	warehouse=None,
	type_of_valve=None,
	size=None,
	class_val=None,
	search_text=None,
	show_zero_stock=0,
):
	"""
	Fetches stock availability grouped by:
	Pattern Set + Warehouse -> ALL Components of that Pattern Set (with stock or 0)

	Supports filtering by:
	- pattern_set
	- component_item
	- warehouse (Group Warehouse or Leaf Warehouse)
	- type_of_valve
	- size
	- class / class_val
	- search_text
	- show_zero_stock
	"""
	if not frappe.has_permission("Pattern Set", "read"):
		frappe.throw(_("Not permitted to view Pattern Set data"), frappe.PermissionError)

	if not class_val and frappe.form_dict.get("class"):
		class_val = frappe.form_dict.get("class")

	show_zero = cint(show_zero_stock)
	search_lower = (search_text or "").strip().lower()

	# -------------------------------------------------------------
	# 1. Resolve Warehouse Hierarchy (Group Warehouse -> Leaf Children)
	# -------------------------------------------------------------
	target_warehouses = None
	if warehouse:
		target_warehouses = get_descendant_warehouses(warehouse)
		if not target_warehouses:
			return _empty_response()

	# -------------------------------------------------------------
	# 2. Filter Pattern Sets using Primary Key & Indexes
	# -------------------------------------------------------------
	ps_conditions = ["docstatus != 2", "IFNULL(disable, 0) = 0"]
	ps_params = {}

	if pattern_set:
		ps_conditions.append("name = %(pattern_set)s")
		ps_params["pattern_set"] = pattern_set

	if type_of_valve and str(type_of_valve).strip():
		ps_conditions.append("type_of_valve = %(type_of_valve)s")
		ps_params["type_of_valve"] = str(type_of_valve).strip()

	if size and str(size).strip():
		ps_conditions.append("size = %(size)s")
		ps_params["size"] = str(size).strip()

	if class_val and str(class_val).strip():
		ps_conditions.append("`class` = %(class_val)s")
		ps_params["class_val"] = str(class_val).strip()

	if component_item:
		parent_sets = frappe.db.sql_list(
			"""
			SELECT DISTINCT parent
			FROM `tabPattern Set Component`
			WHERE component_item = %(component_item)s
			""",
			{"component_item": component_item},
		)
		if not parent_sets:
			return _empty_response()

		ps_conditions.append("name IN %(parent_sets)s")
		ps_params["parent_sets"] = tuple(parent_sets)

	where_clause = " AND ".join(ps_conditions)
	pattern_sets = frappe.db.sql(
		f"""
		SELECT name, pattern_set_name, type_of_valve, size, `class`, type_of_pattern, disable
		FROM `tabPattern Set`
		WHERE {where_clause}
		ORDER BY name ASC
		""",
		ps_params,
		as_dict=True,
	)

	if not pattern_sets:
		return _empty_response()

	matched_ps_names = [ps.name for ps in pattern_sets]

	# -------------------------------------------------------------
	# 3. Batch Fetch Component Items using Child Table Parent Index
	# -------------------------------------------------------------
	components = frappe.db.sql(
		"""
		SELECT parent, component_item, component_name, qty, uom,
		       drawing_no, drawing_rev_no, pattern_drawing_no, pattern_drawing_rev_no, idx
		FROM `tabPattern Set Component`
		WHERE parent IN %(parents)s
		ORDER BY parent ASC, idx ASC
		""",
		{"parents": tuple(matched_ps_names)},
		as_dict=True,
	)

	if not components:
		return _empty_response()

	unique_item_codes = list({c.component_item for c in components if c.component_item})
	if not unique_item_codes:
		return _empty_response()

	# -------------------------------------------------------------
	# 4. Batch Fetch Bin Stock Data using (item_code, warehouse) Index
	# -------------------------------------------------------------
	if target_warehouses:
		bins = frappe.db.sql(
			"""
			SELECT item_code, warehouse, actual_qty, stock_uom
			FROM `tabBin`
			WHERE item_code IN %(items)s AND warehouse IN %(warehouses)s
			""",
			{"items": tuple(unique_item_codes), "warehouses": tuple(target_warehouses)},
			as_dict=True,
		)
	else:
		bins = frappe.db.sql(
			"""
			SELECT item_code, warehouse, actual_qty, stock_uom
			FROM `tabBin`
			WHERE item_code IN %(items)s
			""",
			{"items": tuple(unique_item_codes)},
			as_dict=True,
		)

	# -------------------------------------------------------------
	# 5. Batch Fetch Warehouse Details using Primary Key Index
	# -------------------------------------------------------------
	warehouses_in_bins = list({b.warehouse for b in bins if b.warehouse})
	if target_warehouses:
		for wh_t in target_warehouses:
			if wh_t not in warehouses_in_bins:
				warehouses_in_bins.append(wh_t)

	wh_map = {}
	if warehouses_in_bins:
		has_branch = frappe.db.has_column("Warehouse", "branch")
		branch_col = ", branch" if has_branch else ""
		wh_rows = frappe.db.sql(
			f"""
			SELECT name, warehouse_name, warehouse_type, is_group{branch_col}
			FROM `tabWarehouse`
			WHERE name IN %(warehouses)s
			""",
			{"warehouses": tuple(warehouses_in_bins)},
			as_dict=True,
		)
		wh_map = {w.name: w for w in wh_rows}

	# Map stock by (item_code, warehouse)
	item_wh_qty = {}
	item_wh_uom = {}
	for b in bins:
		qty = flt(b.actual_qty)
		key = (b.item_code, b.warehouse)
		item_wh_qty[key] = item_wh_qty.get(key, 0.0) + qty
		if b.stock_uom:
			item_wh_uom[key] = b.stock_uom

	# Group components by parent Pattern Set
	ps_components_map = {}
	for c in components:
		ps_components_map.setdefault(c.parent, []).append(c)

	# -------------------------------------------------------------
	# 6. Build Grouped Structure: Pattern Set x Warehouse
	# -------------------------------------------------------------
	hierarchy = []
	total_components_set = set()
	total_warehouses_set = set()
	components_with_stock_count = 0
	components_without_stock_count = 0
	total_stock_qty = 0.0
	total_common_stock_qty = 0.0

	for ps in pattern_sets:
		ps_comps = ps_components_map.get(ps.name, [])
		if not ps_comps:
			continue

		ps_item_codes = [c.component_item for c in ps_comps if c.component_item]

		# Determine applicable warehouses for this Pattern Set
		applicable_warehouses = []
		if target_warehouses:
			if show_zero:
				wh_with_bins = {wh for (i_code, wh) in item_wh_qty if i_code in ps_item_codes and wh in target_warehouses}
				applicable_warehouses = list(wh_with_bins) if wh_with_bins else list(target_warehouses)
			else:
				wh_with_stock = {wh for (i_code, wh), q in item_wh_qty.items() if i_code in ps_item_codes and wh in target_warehouses and q > 0}
				applicable_warehouses = list(wh_with_stock)
		else:
			warehouses_with_stock = set()
			warehouses_with_bin = set()

			for item_code in ps_item_codes:
				for (i_code, wh_name), qty in item_wh_qty.items():
					if i_code == item_code:
						warehouses_with_bin.add(wh_name)
						if qty > 0:
							warehouses_with_stock.add(wh_name)

			if show_zero:
				applicable_warehouses = list(warehouses_with_bin)
			else:
				applicable_warehouses = list(warehouses_with_stock)

		if not applicable_warehouses:
			continue

		# Sort warehouses: common warehouse first, then alphabetical by warehouse name
		def _wh_sort_key(wh_n):
			wh_info = wh_map.get(wh_n, {})
			is_comm = is_common_warehouse(wh_info)
			disp_name = wh_info.get("warehouse_name") or wh_n
			return (not is_comm, disp_name.lower())

		applicable_warehouses.sort(key=_wh_sort_key)

		# Build warehouse groups for this Pattern Set
		wh_groups = []
		for wh_name in applicable_warehouses:
			wh_info = wh_map.get(wh_name, {"name": wh_name, "warehouse_name": wh_name})
			is_common = is_common_warehouse(wh_info)
			branch = wh_info.get("branch") or ""
			disp_wh_name = wh_info.get("warehouse_name") or wh_name

			group_components = []
			group_total_qty = 0.0

			for c in ps_comps:
				item_code = c.component_item
				if not item_code:
					continue

				if component_item and item_code != component_item:
					continue

				qty = item_wh_qty.get((item_code, wh_name), 0.0)
				uom = item_wh_uom.get((item_code, wh_name)) or c.uom or ""
				has_stock = qty > 0

				total_components_set.add(item_code)
				if has_stock:
					components_with_stock_count += 1
					total_warehouses_set.add(wh_name)
				else:
					components_without_stock_count += 1

				group_total_qty += qty
				total_stock_qty += qty
				if is_common:
					total_common_stock_qty += qty

				group_components.append({
					"component_item": item_code,
					"component_name": c.component_name or item_code,
					"required_qty": flt(c.qty),
					"uom": uom,
					"drawing_no": c.drawing_no or "",
					"drawing_rev_no": c.drawing_rev_no or "",
					"pattern_drawing_no": c.pattern_drawing_no or "",
					"pattern_drawing_rev_no": c.pattern_drawing_rev_no or "",
					"warehouse": wh_name,
					"warehouse_name": disp_wh_name,
					"actual_qty": qty,
					"has_stock": has_stock,
				})

			if not group_components:
				continue

			# Calculate Pattern Set Quantity (minimum possible sets from components)
			possible_sets_list = []
			for c_item in group_components:
				r_qty = flt(c_item.get("required_qty", 0))
				a_qty = flt(c_item.get("actual_qty", 0))
				if r_qty > 0:
					possible_sets_list.append(a_qty / r_qty)

			pattern_set_qty = 0
			if possible_sets_list:
				pattern_set_qty = int(min(possible_sets_list))
				if pattern_set_qty < 0:
					pattern_set_qty = 0

			# Calculate extra_qty = max(0, available_qty - (pattern_set_qty * required_qty))
			for c_item in group_components:
				r_qty = flt(c_item.get("required_qty", 0))
				a_qty = flt(c_item.get("actual_qty", 0))
				extra_qty = max(0.0, a_qty - (pattern_set_qty * r_qty))
				c_item["extra_qty"] = extra_qty

			wh_groups.append({
				"warehouse": wh_name,
				"warehouse_name": disp_wh_name,
				"is_common": is_common,
				"branch": branch,
				"total_qty": group_total_qty,
				"pattern_set_qty": pattern_set_qty,
				"components": group_components,
			})

		if not wh_groups:
			continue

		# Apply text search filter if provided
		if search_lower:
			filtered_wh_groups = []
			ps_matches = (
				search_lower in ps.name.lower()
				or search_lower in (ps.get("pattern_set_name") or "").lower()
				or search_lower in (ps.get("type_of_valve") or "").lower()
				or search_lower in (ps.get("size") or "").lower()
				or search_lower in (ps.get("class") or "").lower()
				or search_lower in (ps.get("type_of_pattern") or "").lower()
			)

			for wh_g in wh_groups:
				wh_matches = (
					search_lower in wh_g["warehouse"].lower()
					or search_lower in wh_g["warehouse_name"].lower()
				)
				if ps_matches or wh_matches:
					filtered_wh_groups.append(wh_g)
				else:
					matched_comps = [
						comp for comp in wh_g["components"]
						if search_lower in comp["component_item"].lower()
						or search_lower in comp["component_name"].lower()
						or search_lower in comp["drawing_no"].lower()
					]
					if matched_comps:
						wh_g_copy = dict(wh_g)
						wh_g_copy["components"] = matched_comps
						filtered_wh_groups.append(wh_g_copy)

			wh_groups = filtered_wh_groups

		if not wh_groups:
			continue

		hierarchy.append({
			"pattern_set": ps.name,
			"pattern_set_name": ps.get("pattern_set_name") or ps.name,
			"type_of_valve": ps.get("type_of_valve") or "",
			"size": ps.get("size") or "",
			"class": ps.get("class") or "",
			"type_of_pattern": ps.get("type_of_pattern") or "",
			"warehouse_groups": wh_groups,
		})

	summary = {
		"total_pattern_sets": len(hierarchy),
		"total_groups": sum(len(ps["warehouse_groups"]) for ps in hierarchy),
		"total_components": len(total_components_set),
		"total_warehouses": len(total_warehouses_set),
		"components_with_stock": components_with_stock_count,
		"components_without_stock": components_without_stock_count,
		"total_stock_qty": total_stock_qty,
		"common_warehouse_stock": total_common_stock_qty,
	}

	return {
		"hierarchy": hierarchy,
		"summary": summary,
	}


def _empty_response():
	return {
		"hierarchy": [],
		"summary": {
			"total_pattern_sets": 0,
			"total_groups": 0,
			"total_components": 0,
			"total_warehouses": 0,
			"components_with_stock": 0,
			"components_without_stock": 0,
			"total_stock_qty": 0.0,
			"common_warehouse_stock": 0.0,
		},
	}


@frappe.whitelist()
def export_availability_excel(
	pattern_set=None,
	component_item=None,
	warehouse=None,
	type_of_valve=None,
	size=None,
	class_val=None,
	search_text=None,
	show_zero_stock=0,
):
	"""
	Generates and returns an Excel workbook (.xlsx) download of the grouped stock availability.
	Format matches the exact requested columns:
	Col A: Pattern Set
	Col B: Warehouse
	Col C: QTY
	"""
	if not class_val and frappe.form_dict.get("class"):
		class_val = frappe.form_dict.get("class")

	data = get_pattern_set_component_availability(
		pattern_set=pattern_set,
		component_item=component_item,
		warehouse=warehouse,
		type_of_valve=type_of_valve,
		size=size,
		class_val=class_val,
		search_text=search_text,
		show_zero_stock=show_zero_stock,
	)

	hierarchy = data.get("hierarchy") or []

	from openpyxl import Workbook
	from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
	from openpyxl.utils import get_column_letter

	wb = Workbook()
	ws = wb.active
	ws.title = "Pattern Set Stock"
	ws.views.sheetView[0].showGridLines = True

	# Headers: Pattern Set, Warehouse, QTY, Extra Qty
	headers = [
		"Pattern Set",
		"Warehouse",
		"QTY",
		"Extra Qty",
	]

	header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
	header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
	thin_border = Border(
		left=Side(style="thin", color="E2E8F0"),
		right=Side(style="thin", color="E2E8F0"),
		top=Side(style="thin", color="E2E8F0"),
		bottom=Side(style="thin", color="E2E8F0"),
	)

	ws.append(headers)
	for col_idx in range(1, len(headers) + 1):
		cell = ws.cell(row=1, column=col_idx)
		cell.fill = header_fill
		cell.font = header_font
		cell.alignment = Alignment(horizontal="left" if col_idx <= 2 else "right", vertical="center")
		cell.border = thin_border
	ws.row_dimensions[1].height = 24

	group_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
	group_font = Font(name="Segoe UI", size=10, bold=True, color="0F172A")
	item_font = Font(name="Segoe UI", size=10, color="334155")
	qty_font = Font(name="Segoe UI", size=10, bold=True, color="0F172A")
	zero_qty_font = Font(name="Segoe UI", size=10, color="64748B")

	row_idx = 2
	for ps in hierarchy:
		ps_title = ps.get("pattern_set_name") or ps.get("pattern_set")

		for wh_group in ps.get("warehouse_groups", []):
			wh_display = wh_group.get("warehouse_name") or wh_group.get("warehouse")
			ps_qty = wh_group.get("pattern_set_qty", 0)
			ps_qty_text = f"Pattern Set Qty: {ps_qty}"

			# Group Header Row: Pattern Set | Warehouse | Pattern Set Qty | (blank Extra Qty)
			ws.append([
				ps_title,
				wh_display,
				ps_qty_text,
				"",
			])
			for c_i in range(1, 5):
				c = ws.cell(row=row_idx, column=c_i)
				c.fill = group_fill
				c.font = group_font
				c.border = thin_border
				c.alignment = Alignment(horizontal="left" if c_i <= 2 else "right", vertical="center")
			ws.row_dimensions[row_idx].height = 20
			row_idx += 1

			# Component Detail Rows under this Pattern Set + Warehouse group
			for comp in wh_group.get("components", []):
				comp_display = f"    {comp['component_item']}"
				if comp.get("component_name") and comp["component_name"] != comp["component_item"]:
					comp_display += f" ({comp['component_name']})"

				qty_val = comp["actual_qty"]
				extra_qty_val = comp.get("extra_qty", 0.0)

				ws.append([
					comp_display,
					wh_display,
					qty_val,
					extra_qty_val,
				])

				c1 = ws.cell(row=row_idx, column=1)
				c1.font = item_font
				c1.border = thin_border
				c1.alignment = Alignment(horizontal="left", vertical="center")

				c2 = ws.cell(row=row_idx, column=2)
				c2.font = item_font
				c2.border = thin_border
				c2.alignment = Alignment(horizontal="left", vertical="center")

				c3 = ws.cell(row=row_idx, column=3)
				c3.font = qty_font if qty_val > 0 else zero_qty_font
				c3.border = thin_border
				c3.alignment = Alignment(horizontal="right", vertical="center")
				c3.number_format = "#,##0.##"

				c4 = ws.cell(row=row_idx, column=4)
				c4.font = qty_font if extra_qty_val > 0 else zero_qty_font
				c4.border = thin_border
				c4.alignment = Alignment(horizontal="right", vertical="center")
				c4.number_format = "#,##0.##"

				ws.row_dimensions[row_idx].height = 18
				row_idx += 1

	# Auto-fit columns
	for col in ws.columns:
		max_len = max(len(str(cell.value or "")) for cell in col)
		col_letter = get_column_letter(col[0].column)
		ws.column_dimensions[col_letter].width = max(max_len + 4, 16)

	output = BytesIO()
	wb.save(output)
	output.seek(0)

	frappe.response["filename"] = "Pattern_Set_Component_Warehouse_Availability.xlsx"
	frappe.response["filecontent"] = output.getvalue()
	frappe.response["type"] = "binary"
