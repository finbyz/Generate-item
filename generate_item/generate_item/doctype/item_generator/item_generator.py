# Copyright (c) 2025, Finbyz and contributors
# For license information, please see license.txt

import frappe
import time
from frappe.model.document import Document


class ItemGenerator(Document):
	def after_insert(self):
		if self.item_code:
			# Get Item Group Defaults doc
			igd = frappe.get_doc("Item Group Defaults", self.item_group_name)

			# Create new Item
			doc = frappe.new_doc("Item")
			doc.item_code = self.item_code
			doc.item_name = self.short_description
			doc.description = self.description
			doc.gst_hsn_code = igd.hsn_code
			# Map fields directly
			doc.item_group = igd.item_group
			doc.is_stock_item = igd.is_stock_item
			doc.is_fixed_asset = igd.is_fixed_asset
			doc.valuation_rate = igd.valuation_rate
			doc.standard_rate = igd.standard_rate
			doc.over_delivery_receipt_allowance = igd.over_delivery_receipt_allowance
			doc.over_billing_allowance = igd.over_billing_allowance
			doc.valuation_method = igd.valuation_method
			doc.is_purchase_item = igd.is_purchase_item
			doc.lead_time_days = igd.lead_time_days
			doc.purchase_uom = igd.purchase_uom
			doc.sales_uom = igd.sales_uom
			doc.is_sales_item = igd.is_sales_item
			doc.quality_inspection_template = igd.quality_inspection_template
			doc.inspection_required_before_purchase = igd.inspection_required_before_purchase
			doc.inspection_required_before_delivery = igd.inspection_required_before_delivery
			doc.include_item_in_manufacturing = igd.include_item_in_manufacturing
			doc.is_sub_contracted_item = igd.is_sub_contracted_item

			for uom in igd.uoms:
				doc.append("uoms", {
					"uom": uom.uom,
					"conversion_factor": uom.conversion_factor,
				})
			for d in igd.item_defaults:
				doc.append("item_defaults", {
					"company": d.company,
					"default_warehouse": d.default_warehouse,
					"default_price_list": d.default_price_list,
					"buying_cost_center": d.buying_cost_center,
					"default_supplier": d.default_supplier,
					"selling_cost_center":d.selling_cost_center,
					"income_account": d.income_account,
					"default_discount_account": d.default_discount_account,
					"income_account":d.income_account,
					"default_provisional_account":d.default_provisional_account,
				})
			for row in igd.taxes:
				doc.append("taxes", {
					"item_tax_template": row.item_tax_template,
					"tax_category": row.tax_category,
					"valid_from": row.valid_from,
     				"minimum_net_rate":row.minimum_net_rate,
					"maximum_net_rate": row.maximum_net_rate,
				})
			doc.save()
			self.ig_done = 1
			self.created_item = doc.name		
			self.save()
			frappe.msgprint(f"Item is created : {doc.name}")

	#     # Templates that require short_description logic
	# TEMPLATES_TO_CHECK = ["BLV", "BFV", "GGC"]

	# def before_save(self):
	# 	if not self.template_name or self.template_name not in getattr(self, "TEMPLATES_TO_CHECK", []):
	# 		return

	# 	required_attributes = [
	# 		"Type of Product",
	# 		"Valve Type",
	# 		"Size",
	# 		"Rating",
	# 		"Ends",
	# 		"Shell MOC",
	# 		"Operator",
	# 	]

	# 	values = []
	# 	for i in range(1, 27):
	# 		label = getattr(self, f"attribute_{i}", "") or ""
	# 		val = getattr(self, f"attribute_{i}_value", "") or ""
	# 		if label.strip().upper() in [x.upper() for x in required_attributes]:
	# 			if val:
	# 				values.append(val)

	# 	cus_description = " ".join(values)

	# 	if cus_description:
	# 		self.short_description = cus_description
	# 		self.flags.ignore_validate = True
	# 		self.flags.ignore_validate_fields = ['short_description']
	# 		self.db_set("short_description", cus_description, commit=True)
	# 		frappe.msgprint(f"Description (server override): {cus_description}")
	# 		frappe.msgprint(f"Short Description (server override): {self.short_description}")

import frappe
import json

TEMPLATES_TO_CHECK = ["BLV", "BFV", "GGC"]

@frappe.whitelist()
def update_short_description(doc):
    if isinstance(doc, str):
        doc = frappe.parse_json(doc)
    
    if not doc.get('template_name') or doc.get('template_name') not in TEMPLATES_TO_CHECK:
        return

    required_attributes = [
        "Type of Product",
        "Valve Type",
        "Size",
        "Rating",
        "Ends",
        "Shell MOC",
        "Operator",
    ]

    values = []
    for i in range(1, 27):
        label = doc.get(f"attribute_{i}", "") or ""
        val = doc.get(f"attribute_{i}_value", "") or ""
        if label and label.strip().upper() in [x.upper() for x in required_attributes]:
            if val:
                values.append(val)

    cus_description = " ".join(values)

    if cus_description:
        # Update the document in database
        item_generator = frappe.get_doc("Item Generator", doc.get('name'))
        item_generator.short_description = cus_description     
        frappe.db.commit()
        
        return cus_description


import frappe

TEMPLATES_TO_CHECK = ["BLV", "BFV", "GGC"]

@frappe.whitelist()
def update_short_description(docname):
    try:
        if not docname:
            return {"success": False, "error": "Document name not provided"}
        
        doc = frappe.get_doc("Item Generator", docname)
        
        if not doc.template_name or doc.template_name not in TEMPLATES_TO_CHECK:
            return {"success": False, "error": "Template not in required list"}
        
        required_attributes = [
            "Type of Product", "Valve Type", "Size", "Rating", 
            "Ends", "Shell MOC", "Operator",
        ]

        values = []
        for i in range(1, 27):
            label = getattr(doc, f"attribute_{i}", "") or ""
            val = getattr(doc, f"attribute_{i}_value", "") or ""
            if label and label.strip().upper() in [x.upper() for x in required_attributes]:
                if val:
                    values.append(val)

        cus_description = " ".join(values)

        if cus_description:
            frappe.db.set_value(
                "Item Generator",
                docname,
                "short_description",
                cus_description,
                update_modified=False 
            )
            frappe.db.set_value(
                "Item Generator",
                docname,
                "custom_conditional_description",
                cus_description,
                update_modified=False 
            )
            
            frappe.db.commit()
            
            return {
                "success": True, 
                "short_description": cus_description,
                "message": "Description updated in database"
            }
        
        return {"success": False, "error": "No description generated"}
        
    except Exception as e:
        frappe.log_error(f"Error in update_short_description: {str(e)}")
        return {"success": False, "error": str(e)}