# # Copyright (c) 2025, Finbyz and contributors
# # For license information, please see license.txt

import frappe
import time
from frappe.model.document import Document

class ItemGenerator(Document):
	def after_insert(self):
		if self.item_code:
			if not self.item_group_name:
					frappe.throw("Item Group is mandatory. Please select an Item Group.")
			# Get Item Group Defaults doc
			try:
				igd = frappe.get_doc("Item Group Defaults", self.item_group_name)
				
			except Exception as e:
				frappe.log_error(f"Item Group Defaults document not found: {e}")
				frappe.throw(f"Item Group Defaults document '{self.item_group_name}' not found. Please select a valid Item Group Defaults.")
			
			# Create new Item
			doc = frappe.new_doc("Item")
			doc.item_code = self.item_code
			
			# Use the short description (already truncated in before_validate)
			doc.item_name = self.short_description
			doc.description = self.description
			doc.gst_hsn_code = igd.hsn_code
			
			# Map fields directly
			doc.item_group = self.item_group_name
			doc.is_stock_item = igd.is_stock_item
			doc.is_fixed_asset = igd.is_fixed_asset
			doc.valuation_rate = igd.valuation_rate
			doc.standard_rate = igd.standard_rate
			doc.over_delivery_receipt_allowance = igd.over_delivery_receipt_allowance
			doc.over_billing_allowance = igd.over_billing_allowance
			doc.valuation_method = igd.valuation_method
			doc.is_purchase_item = igd.is_purchase_item
			doc.lead_time_days = igd.lead_time_days
			doc.stock_uom = igd.stock_uom
			doc.purchase_uom = igd.purchase_uom
			doc.sales_uom = igd.sales_uom
			doc.is_sales_item = igd.is_sales_item
			doc.quality_inspection_template = igd.quality_inspection_template
			doc.inspection_required_before_purchase = igd.inspection_required_before_purchase
			doc.inspection_required_before_delivery = igd.inspection_required_before_delivery
			doc.include_item_in_manufacturing = igd.include_item_in_manufacturing
			doc.is_sub_contracted_item = igd.is_sub_contracted_item
			doc.has_batch_no = igd.has_batch_no
			doc.create_new_batch = igd.create_new_batch
			doc.batch_number_series = igd.batch_number_series
			doc.has_expiry_date = igd.has_expiry_date
			doc.retain_sample = igd.retain_sample
			doc.sample_quantity = igd.sample_quantity
			doc.has_serial_no = igd.has_serial_no
			doc.serial_no_series = igd.serial_no_series

			
			# Map child tables
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
					"selling_cost_center": d.selling_cost_center,
					"income_account": d.income_account,
					"default_discount_account": d.default_discount_account,
					"default_provisional_account": d.default_provisional_account,
				})
			
			for row in igd.taxes:
				doc.append("taxes", {
					"item_tax_template": row.item_tax_template,
					"tax_category": row.tax_category,
					"valid_from": row.valid_from,
					"minimum_net_rate": row.minimum_net_rate,
					"maximum_net_rate": row.maximum_net_rate,
				})
			
			doc.save()
			
			# Update flags using db_set to avoid marking form as dirty
			self.db_set("ig_done", 1, update_modified=False)
			self.db_set("created_item", doc.name, update_modified=False)

	def after_save(self):
		if self.is_create_with_sales_order == 1 and self.is_closed != 1:
			self.db_set("is_closed", 1, update_modified=False)

	def before_validate(self):
		# Check if Selective Products document exists and has data
		try:
			selective_doc = frappe.get_doc("Selective Products", "Selective Products")
			templates_to_check = [p.product_name for p in selective_doc.products]
		except Exception as e:
			frappe.log_error(f"Selective Products document not found or error: {e}")
			# If Selective Products doesn't exist, skip the validation
			return

		if not self.template_name or self.template_name not in templates_to_check:
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
			label = getattr(self, f"attribute_{i}", "") or ""
			val = getattr(self, f"attribute_{i}_value", "") or ""
			if label.strip().upper() in [x.upper() for x in required_attributes]:
				if not val or val.strip() == "-":
					continue
				values.append(val)

		cus_description = " ".join(values)

		if cus_description:
			# Check if description exceeds 140 characters
			if len(cus_description) > 140:
				# ACTUALLY TRUNCATE IT HERE
				cus_description = cus_description[:140]
			
			# Save the (possibly truncated) description
			self.short_description = cus_description
			self.custom_conditional_description = cus_description
			self.flags.ignore_validate = True
			self.flags.ignore_validate_fields = ["short_description"]
			# Use update_modified=False to prevent form from becoming dirty
			self.db_set("short_description", cus_description, update_modified=False)
			self.db_set("custom_conditional_description", cus_description, update_modified=False)


# import frappe
# import json

# TEMPLATES_TO_CHECK = ["BLV", "BFV", "GGC","PLV"]


# # # @frappe.whitelist()
# # # def update_short_description(doc):
# # #     if isinstance(doc, str):
# # #         doc = frappe.parse_json(doc)
    
# # #     if not doc.get('template_name') or doc.get('template_name') not in TEMPLATES_TO_CHECK:
# # #         return

# # #     required_attributes = [
# # #         "Type of Product",
# # #         "Valve Type",
# # #         "Size",
# # #         "Rating",
# # #         "Ends",
# # #         "Shell MOC",
# # #         "Operator",
# # #     ]

# # #     values = []
# # #     for i in range(1, 27):
# # #         label = doc.get(f"attribute_{i}", "") or ""
# # #         val = doc.get(f"attribute_{i}_value", "") or ""
# # #         if label and label.strip().upper() in [x.upper() for x in required_attributes]:
# # #             if val:
# # #                 values.append(val)

# # #     cus_description = " ".join(values)

# # #     if cus_description:
# # #         # Update the document in database
# # #         item_generator = frappe.get_doc("Item Generator", doc.get('name'))
# # #         item_generator.short_description = cus_description     
# # #         frappe.db.commit()
        
# # #         return cus_description



# @frappe.whitelist()
# def update_short_description(docname):
#     try:
#         if not docname:
#             return {"success": False, "error": "Document name not provided"}
        
#         doc = frappe.get_doc("Item Generator", docname)
        
#         if not doc.template_name or doc.template_name not in TEMPLATES_TO_CHECK:
#             return {"success": False, "error": "Template not in required list"}
        
#         required_attributes = [
#             "Type of Product", "Valve Type", "Size", "Rating", 
#             "Ends", "Shell MOC", "Operator",
#         ]

#         values = []
#         for i in range(1, 27):
#             label = getattr(doc, f"attribute_{i}", "") or ""
#             val = getattr(doc, f"attribute_{i}_value", "") or ""
#             if label and label.strip().upper() in [x.upper() for x in required_attributes]:
#                 if val:
#                     values.append(val)

#         cus_description = " ".join(values)

#         if cus_description:
#             frappe.db.set_value(
#                 "Item Generator",
#                 docname,
#                 "short_description",
#                 cus_description,
#                 update_modified=False 
#             )
#             frappe.db.set_value(
#                 "Item Generator",
#                 docname,
#                 "custom_conditional_description",
#                 cus_description,
#                 update_modified=False 
#             )
            
#             frappe.db.commit()
            
#             return {
#                 "success": True, 
#                 "short_description": cus_description,
#                 "message": "Description updated in database"
#             }
        
#         return {"success": False, "error": "No description generated"}
        
#     except Exception as e:
#         frappe.log_error(f"Error in update_short_description: {str(e)}")
#         return {"success": False, "error": str(e)}






