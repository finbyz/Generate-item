# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import nowdate, nowtime
from generate_item.mould_set_management.doctype.component_transfer.component_transfer import (
	get_mould_set_components,
)
from generate_item.mould_set_management.report.pattern_set_stock_status.pattern_set_stock_status import (
	execute as run_stock_status_report,
)


def run_verification():
	print("--- STARTING PATTERN SET MANAGEMENT VERIFICATION ---")

	# 1. Check or pick items and company
	company = frappe.db.get_single_value("Global Defaults", "default_company")
	if not company:
		company = frappe.get_all("Company", limit=1, pluck="name")[0]

	warehouses = frappe.get_all(
		"Warehouse",
		filters={"is_group": 0, "company": company},
		limit=2,
		pluck="name",
	)
	if len(warehouses) < 2:
		warehouses = frappe.get_all("Warehouse", filters={"is_group": 0}, limit=2, pluck="name")

	from_warehouse = warehouses[0]
	to_warehouse = warehouses[1]
	print(f"Company: {company}, From WH: {from_warehouse}, To WH: {to_warehouse}")

	# Get items for pattern set parent and components
	items = frappe.get_all(
		"Item",
		filters={"is_stock_item": 1, "has_variants": 0, "disabled": 0},
		limit=3,
		pluck="name",
	)
	assert len(items) >= 2, "Need at least 2 stock items for testing"

	parent_item = items[0]
	comp_item_1 = items[1]
	comp_item_2 = items[2] if len(items) > 2 else items[1]

	# Ensure components have drawings on Item master to test sync
	frappe.db.set_value("Item", comp_item_1, {
		"custom_drawing_no": "DRG-001",
		"custom_drawing_rev_no": "R1",
		"custom_pattern_drawing_no": "PAT-001",
		"custom_pattern_drawing_rev_no": "PR1",
	})
	frappe.db.commit()

	# 2. Test Pattern Set Creation and Validation
	test_ps_name = f"TEST-PS-{frappe.generate_hash(length=5)}"
	ps = frappe.new_doc("Pattern Set")
	ps.pattern_set_name = test_ps_name
	ps.item = parent_item
	ps.append("items", {
		"component_item": comp_item_1,
		"qty": 2,
	})
	if comp_item_2 != comp_item_1:
		ps.append("items", {
			"component_item": comp_item_2,
			"qty": 1,
		})
	ps.insert(ignore_permissions=True)
	ps.submit()
	print(f"Created and Submitted Pattern Set: {ps.name} for Item: {parent_item}")

	# Verify drawings were auto-synced from Item
	reloaded_ps = frappe.get_doc("Pattern Set", ps.name)
	assert reloaded_ps.items[0].drawing_no == "DRG-001", "Drawing No sync failed"
	assert reloaded_ps.items[0].drawing_rev_no == "R1", "Drawing Rev No sync failed"
	print("Pattern Set drawing synchronization verified successfully!")

	# 3. Test Auto-fetch function
	fetch_result = get_mould_set_components(
		mould_set_item=parent_item,
		transfer_type="All Components (Complete Set)",
		set_qty=3.0,
		from_warehouse=from_warehouse,
		to_warehouse=to_warehouse,
	)
	assert fetch_result["mould_set"] == ps.name, "Auto-fetch returned wrong pattern set"
	assert len(fetch_result["items"]) == len(reloaded_ps.items), "Auto-fetch returned wrong number of items"
	assert fetch_result["items"][0]["qty"] == 6.0, f"Expected 2*3=6, got {fetch_result['items'][0]['qty']}"
	print("Auto-fetch components API verified successfully!")

	# Ensure stock is available at from_warehouse for components
	receipt = frappe.new_doc("Stock Entry")
	receipt.purpose = "Material Receipt"
	receipt.stock_entry_type = "Material Receipt"
	receipt.company = company
	receipt.to_warehouse = from_warehouse
	branches = frappe.get_all("Branch", limit=1, pluck="name")
	receipt.branch = branches[0] if branches else None
	for item_data in fetch_result["items"]:
		receipt.append("items", {
			"item_code": item_data["component_item"],
			"qty": 10.0,
			"t_warehouse": from_warehouse,
			"basic_rate": 10.0,
			"allow_zero_valuation_rate": 1,
		})
	receipt.set_stock_entry_type()
	receipt.insert(ignore_permissions=True)
	receipt.submit()

	# 4. Test Component Transfer Document & Stock Entry Creation
	ct = frappe.new_doc("Component Transfer")
	ct.company = company
	branches = frappe.get_all("Branch", limit=1, pluck="name")
	ct.branch = branches[0] if branches else None
	ct.posting_date = nowdate()
	ct.posting_time = nowtime()
	ct.mould_set_item = parent_item
	ct.mould_set = ps.name
	ct.transfer_type = "All Components (Complete Set)"
	ct.set_qty = 1.0
	ct.from_warehouse = from_warehouse
	ct.to_warehouse = to_warehouse

	# Auto populate items
	for item_data in fetch_result["items"]:
		ct.append("items", {
			"component_item": item_data["component_item"],
			"component_name": item_data["component_name"],
			"qty": item_data["qty"] / 3.0,  # 1 set
			"uom": item_data["uom"],
			"source_warehouse": from_warehouse,
			"target_warehouse": to_warehouse,
			"drawing_no": item_data["drawing_no"],
			"drawing_rev_no": item_data["drawing_rev_no"],
			"pattern_drawing_no": item_data["pattern_drawing_no"],
			"pattern_drawing_rev_no": item_data["pattern_drawing_rev_no"],
		})

	ct.insert(ignore_permissions=True)
	print(f"Created Component Transfer: {ct.name}")

	# Submit Component Transfer -> Should create and submit Stock Entry
	ct.submit()
	print(f"Submitted Component Transfer: {ct.name}")

	# Reload to check stock_entry link
	ct.reload()
	stock_entry_name = ct.stock_entry
	assert stock_entry_name, "Stock Entry was NOT linked to Component Transfer!"
	print(f"Stock Entry {stock_entry_name} created and linked successfully!")

	# Verify Stock Entry details
	se = frappe.get_doc("Stock Entry", stock_entry_name)
	assert se.docstatus == 1, "Created Stock Entry is not submitted!"
	assert se.purpose == "Material Transfer", f"Expected Material Transfer, got {se.purpose}"
	assert se.from_warehouse == from_warehouse, "From warehouse mismatch"
	assert se.to_warehouse == to_warehouse, "To warehouse mismatch"
	assert len(se.items) == len(ct.items), "Stock Entry items count mismatch"
	print("Stock Entry (Material Transfer) contents verified successfully!")

	# 5. Test Cancellation
	ct.cancel()
	se.reload()
	assert se.docstatus == 2, f"Stock Entry was expected to be cancelled, but docstatus is {se.docstatus}"
	print("Component Transfer cancellation successfully cancelled linked Stock Entry!")

	# 6. Test Pattern Set Stock Status Report
	cols, data = run_stock_status_report({
		"company": company,
		"mould_set_item": parent_item,
		"warehouse": from_warehouse,
	})
	print(f"Pattern Set Stock Status Report returned {len(data)} rows for warehouse {from_warehouse}")
	assert len(cols) > 0, "Report columns missing"

	# 7. Test Purchase Order Enhancement (Pattern Set Info & Stock Calculation)
	from generate_item.mould_set_management.po_enhancement import (
		get_mould_sets_for_items,
		calculate_mould_sets_stock,
		get_po_mould_set_info,
		on_po_validate_or_save,
	)

	po_mould_sets = get_mould_sets_for_items([parent_item])
	assert ps.name in po_mould_sets, f"PO item matching failed: {po_mould_sets}"

	po_info = get_po_mould_set_info(
		supplier_warehouse=from_warehouse,
		items=[{"item_code": parent_item}],
	)
	assert "html" in po_info, "Pattern Set HTML missing in PO info"
	assert "total_complete_sets" in po_info, "total_complete_sets missing in PO info"
	assert "total_loose_components" in po_info, "total_loose_components missing in PO info"
	print(
		f"PO Pattern Set Info verified: Complete Sets = {po_info['total_complete_sets']}, "
		f"Loose = {po_info['total_loose_components']}"
	)

	# Test on_po_validate_or_save with mock PO
	class MockPO:
		name = "TEST-PO-VERIFY"
		supplier = "Test Supplier"
		supplier_warehouse = from_warehouse
		mould_set_info = ""
		items = []

	mock_po = MockPO()
	class MockPOItem:
		item_code = parent_item
		fg_item = None
	mock_po.items = [MockPOItem()]

	on_po_validate_or_save(mock_po)
	assert mock_po.mould_set_info, "mould_set_info was not populated on PO"
	assert "PATTERN SET STOCK INFORMATION" in mock_po.mould_set_info, "HTML header missing"
	print("Purchase Order save hook (on_po_validate_or_save) verified successfully!")

	# Cleanup test records
	ct.delete()
	ps.cancel()
	ps.delete()
	receipt.cancel()
	receipt.delete()

	print("--- ALL VERIFICATION TESTS PASSED SUCCESSFULLY! ---")
