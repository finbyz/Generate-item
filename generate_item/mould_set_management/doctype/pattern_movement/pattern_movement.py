# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, get_link_to_form
from erpnext.stock.utils import get_stock_balance


class PatternMovement(Document):
	def validate(self):
		self.validate_purpose_and_suppliers()
		self.validate_warehouses()
		self.validate_items()

	def validate_purpose_and_suppliers(self):
		if self.purpose == "Company to Supplier":
			if not self.to_supplier:
				frappe.throw(_("To Supplier is mandatory when Purpose is Company to Supplier."))
		elif self.purpose == "Supplier to Supplier":
			if not self.from_supplier:
				frappe.throw(_("From Supplier is mandatory when Purpose is Supplier to Supplier."))
			if not self.to_supplier:
				frappe.throw(_("To Supplier is mandatory when Purpose is Supplier to Supplier."))
			if self.from_supplier == self.to_supplier:
				frappe.throw(_("From Supplier and To Supplier cannot be the same."))

	def validate_warehouses(self):
		if not self.from_warehouse:
			frappe.throw(_("From Warehouse is required."))
		if not self.to_warehouse:
			frappe.throw(_("To Warehouse is required."))
		if self.from_warehouse == self.to_warehouse:
			frappe.throw(_("From Warehouse and To Warehouse cannot be the same."))

	def validate_items(self):
		if not self.items:
			frappe.throw(_("No items to transfer. Please select Pattern Set components."))

		for row in self.items:
			if not row.component_item:
				frappe.throw(_("Row #{0}: Component Item is required.").format(row.idx))

			if flt(row.qty) <= 0:
				frappe.throw(
					_("Row #{0}: Transfer Qty must be greater than 0 for Component {1}.").format(
						row.idx, row.component_item
					)
				)

			if not row.source_warehouse:
				row.source_warehouse = self.from_warehouse
			if not row.target_warehouse:
				row.target_warehouse = self.to_warehouse

			# Fetch current available stock at source warehouse
			row.available_qty_at_source = get_stock_balance(
				row.component_item, row.source_warehouse
			)

			# Validate Serial No and Batch No requirements
			item_details = frappe.db.get_value(
				"Item",
				row.component_item,
				["has_serial_no", "has_batch_no"],
				as_dict=True,
			) or {}

			if item_details.get("has_batch_no") and not row.batch_no:
				frappe.throw(
					_("Row #{0}: Batch No is mandatory for Item {1}.").format(
						row.idx, frappe.bold(row.component_item)
					)
				)

			if item_details.get("has_serial_no"):
				if not row.serial_no:
					frappe.throw(
						_("Row #{0}: Serial No is mandatory for Item {1}.").format(
							row.idx, frappe.bold(row.component_item)
						)
					)
				from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
				sn_list = get_serial_nos(row.serial_no)
				if len(sn_list) != int(flt(row.qty)):
					frappe.throw(
						_("Row #{0}: {1} Serial No(s) required for Item {2}, but {3} provided.").format(
							row.idx, int(flt(row.qty)), frappe.bold(row.component_item), len(sn_list)
						)
					)

	def on_submit(self):
		self.create_stock_entry()

	def create_stock_entry(self):
		"""
		Automatically creates and submits a Stock Entry (Material Transfer) in the backend.
		"""
		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.purpose = "Material Transfer"
		stock_entry.stock_entry_type = "Material Transfer"
		stock_entry.company = self.company
		stock_entry.from_warehouse = self.from_warehouse
		stock_entry.to_warehouse = self.to_warehouse
		stock_entry.branch = self.branch
		stock_entry.posting_date = self.posting_date
		stock_entry.posting_time = self.posting_time
		stock_entry.remarks = (
			f"Material Transfer for Pattern Set {self.mould_set} via Pattern Movement {self.name}"
		)

		for item in self.items:
			stock_uom = frappe.db.get_value("Item", item.component_item, "stock_uom") or item.uom
			item_row = {
				"item_code": item.component_item,
				"qty": flt(item.qty),
				"uom": item.uom or stock_uom,
				"stock_uom": stock_uom,
				"conversion_factor": 1.0,
				"s_warehouse": item.source_warehouse or self.from_warehouse,
				"t_warehouse": item.target_warehouse or self.to_warehouse,
				"allow_zero_valuation_rate": 1,
			}

			if item.serial_no or item.batch_no:
				item_row["serial_no"] = item.serial_no.strip() if item.serial_no else ""
				item_row["batch_no"] = item.batch_no or ""
				item_row["use_serial_batch_fields"] = 1

			stock_entry.append("items", item_row)

		stock_entry.set_stock_entry_type()
		stock_entry.insert(ignore_permissions=True)
		stock_entry.submit()

		self.db_set("stock_entry", stock_entry.name)

		frappe.msgprint(
			_("Stock Entry {0} created and submitted successfully.").format(
				get_link_to_form("Stock Entry", stock_entry.name)
			),
			alert=True,
		)

	def on_cancel(self):
		self.cancel_stock_entry()

	def cancel_stock_entry(self):
		if self.stock_entry:
			if frappe.db.exists("Stock Entry", self.stock_entry):
				se = frappe.get_doc("Stock Entry", self.stock_entry)
				if se.docstatus == 1:
					se.cancel()
					frappe.msgprint(
						_("Linked Stock Entry {0} has been cancelled.").format(
							get_link_to_form("Stock Entry", se.name)
						),
						alert=True,
					)


@frappe.whitelist()
def get_mould_set_components(
	mould_set=None,
	mould_set_item=None,
	transfer_type="All Components (Complete Set)",
	component=None,
	set_qty=1.0,
	from_warehouse=None,
	to_warehouse=None,
):
	"""
	Auto-fetches all components linked to the selected Pattern Set.
	"""
	if not mould_set and mould_set_item:
		mould_set = frappe.db.get_value(
			"Pattern Set",
			{"item": mould_set_item, "disable": 0, "docstatus": ["!=", 2]},
			"name",
		)

	if not mould_set or not frappe.db.exists("Pattern Set", mould_set):
		return {"mould_set": None, "items": []}

	mould_set_doc = frappe.get_doc("Pattern Set", mould_set)
	set_multiplier = flt(set_qty) if flt(set_qty) > 0 else 1.0

	items_to_transfer = []
	for c in mould_set_doc.items:
		if transfer_type == "Specific Component" and component and c.component_item != component:
			continue

		source_wh = from_warehouse
		avail_qty = get_stock_balance(c.component_item, source_wh) if source_wh else 0.0

		items_to_transfer.append(
			{
				"component_item": c.component_item,
				"component_name": c.component_name
				or frappe.db.get_value("Item", c.component_item, "item_name"),
				"qty": flt(c.qty) * set_multiplier,
				"uom": c.uom or frappe.db.get_value("Item", c.component_item, "stock_uom"),
				"source_warehouse": source_wh,
				"target_warehouse": to_warehouse,
				"available_qty_at_source": avail_qty,
				"drawing_no": c.drawing_no,
				"drawing_rev_no": c.drawing_rev_no,
				"pattern_drawing_no": c.pattern_drawing_no,
				"pattern_drawing_rev_no": c.pattern_drawing_rev_no,
			}
		)

	return {"mould_set": mould_set_doc.name, "items": items_to_transfer}


@frappe.whitelist()
def component_item_query(doctype, txt, searchfield, start, page_len, filters):
	"""
	Filter component field to only show items that are components of the selected pattern set.
	"""
	mould_set = filters.get("mould_set") if filters else None
	if not mould_set:
		return []

	search_cond = ""
	if txt:
		search_cond = "AND (i.name LIKE %(txt)s OR i.item_name LIKE %(txt)s)"

	return frappe.db.sql(
		f"""
		SELECT DISTINCT msc.component_item, i.item_name
		FROM `tabPattern Set Component` msc
		INNER JOIN `tabItem` i ON i.name = msc.component_item
		WHERE msc.parent = %(mould_set)s
		{search_cond}
		ORDER BY msc.idx ASC
		LIMIT %(start)s, %(page_len)s
		""",
		{"mould_set": mould_set, "txt": f"%{txt}%", "start": start, "page_len": page_len},
		as_list=1,
	)


@frappe.whitelist()
def mould_set_item_query(doctype, txt, searchfield, start, page_len, filters):
	"""
	Filter for mould_set_item field to only show items that have an active Pattern Set.
	"""
	search_cond = ""
	if txt:
		search_cond = "AND (i.name LIKE %(txt)s OR i.item_name LIKE %(txt)s)"

	return frappe.db.sql(
		f"""
		SELECT DISTINCT i.name, i.item_name
		FROM `tabItem` i
		INNER JOIN `tabPattern Set` ms ON ms.name = i.name OR ms.item = i.name
		WHERE ms.docstatus != 2 AND ifnull(ms.disable, 0) = 0
		{search_cond}
		ORDER BY i.name ASC
		LIMIT %(start)s, %(page_len)s
		""",
		{"txt": f"%{txt}%", "start": start, "page_len": page_len},
		as_list=1,
	)
