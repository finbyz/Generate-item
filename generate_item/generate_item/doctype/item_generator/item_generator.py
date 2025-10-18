# # # Copyright (c) 2025, Finbyz and contributors
# # # For license information, please see license.txt

# import frappe
# import time
# from frappe.model.document import Document

# class ItemGenerator(Document):
# 	def after_insert(self):
# 		if self.item_code:
# 			if not self.item_group_name:
# 					frappe.throw("Item Group is mandatory. Please select an Item Group.")
# 			# Get Item Group Defaults doc
# 			try:
# 				igd = frappe.get_doc("Item Group Defaults", self.item_group_name)
				
# 			except Exception as e:
# 				frappe.log_error(f"Item Group Defaults document not found: {e}")
# 				frappe.throw(f"Item Group Defaults document '{self.item_group_name}' not found. Please select a valid Item Group Defaults.")
			
# 			# Create new Item
# 			doc = frappe.new_doc("Item")
# 			doc.item_code = self.item_code
			
# 			# Use the short description (already truncated in before_validate)
# 			doc.item_name = self.short_description
# 			doc.description = self.description
# 			doc.gst_hsn_code = igd.hsn_code
			
# 			# Map fields directly
# 			doc.item_group = self.item_group_name
# 			doc.is_stock_item = igd.is_stock_item
# 			doc.is_fixed_asset = igd.is_fixed_asset
# 			doc.valuation_rate = igd.valuation_rate
# 			doc.standard_rate = igd.standard_rate
# 			doc.over_delivery_receipt_allowance = igd.over_delivery_receipt_allowance
# 			doc.over_billing_allowance = igd.over_billing_allowance
# 			doc.valuation_method = igd.valuation_method
# 			doc.is_purchase_item = igd.is_purchase_item
# 			doc.lead_time_days = igd.lead_time_days
# 			doc.stock_uom = igd.stock_uom
# 			doc.purchase_uom = igd.purchase_uom
# 			doc.sales_uom = igd.sales_uom
# 			doc.is_sales_item = igd.is_sales_item
# 			doc.quality_inspection_template = igd.quality_inspection_template
# 			doc.inspection_required_before_purchase = igd.inspection_required_before_purchase
# 			doc.inspection_required_before_delivery = igd.inspection_required_before_delivery
# 			doc.include_item_in_manufacturing = igd.include_item_in_manufacturing
# 			doc.is_sub_contracted_item = igd.is_sub_contracted_item
# 			doc.has_batch_no = igd.has_batch_no
# 			doc.create_new_batch = igd.create_new_batch
# 			doc.batch_number_series = igd.batch_number_series
# 			doc.has_expiry_date = igd.has_expiry_date
# 			doc.retain_sample = igd.retain_sample
# 			doc.sample_quantity = igd.sample_quantity
# 			doc.has_serial_no = igd.has_serial_no
# 			doc.serial_no_series = igd.serial_no_series

			
# 			# Map child tables
# 			for uom in igd.uoms:
# 				doc.append("uoms", {
# 					"uom": uom.uom,
# 					"conversion_factor": uom.conversion_factor,
# 				})
			
# 			for d in igd.item_defaults:
# 				doc.append("item_defaults", {
# 					"company": d.company,
# 					"default_warehouse": d.default_warehouse,
# 					"default_price_list": d.default_price_list,
# 					"buying_cost_center": d.buying_cost_center,
# 					"default_supplier": d.default_supplier,
# 					"selling_cost_center": d.selling_cost_center,
# 					"income_account": d.income_account,
# 					"default_discount_account": d.default_discount_account,
# 					"default_provisional_account": d.default_provisional_account,
# 				})
			
# 			for row in igd.taxes:
# 				doc.append("taxes", {
# 					"item_tax_template": row.item_tax_template,
# 					"tax_category": row.tax_category,
# 					"valid_from": row.valid_from,
# 					"minimum_net_rate": row.minimum_net_rate,
# 					"maximum_net_rate": row.maximum_net_rate,
# 				})
			
# 			doc.save()
			
# 			# Update flags using db_set to avoid marking form as dirty
# 			self.db_set("ig_done", 1, update_modified=False)
# 			self.db_set("created_item", doc.name, update_modified=False)

# 	def after_save(self):
# 		if self.is_create_with_sales_order == 1 and self.is_closed != 1:
# 			self.db_set("is_closed", 1, update_modified=False)

# 	def before_validate(self):
# 		# Check if Selective Products document exists and has data
# 		try:
# 			selective_doc = frappe.get_doc("Selective Products", "Selective Products")
# 			templates_to_check = [p.product_name for p in selective_doc.products]
# 		except Exception as e:
# 			frappe.log_error(f"Selective Products document not found or error: {e}")
# 			return

# 		if not self.template_name or self.template_name not in templates_to_check:
# 			return

# 		required_attributes = [
# 			"Type of Product",
# 			"Valve Type",
# 			"Size",
# 			"Rating",
# 			"Ends",
# 			"Shell MOC",
# 			"Operator",
# 		]

# 		values = []
# 		for i in range(1, 27):
# 			label = getattr(self, f"attribute_{i}", "") or ""
# 			val = getattr(self, f"attribute_{i}_value", "") or ""
# 			if label.strip().upper() in [x.upper() for x in required_attributes]:
# 				if not val or val.strip() == "-":
# 					continue
# 				values.append(val)

# 		cus_description = " ".join(values)

# 		if cus_description:
# 			# Respect kit suffixes if present (from list actions)
# 			suffix = ""
# 			if getattr(self, "duplicated_subassembly", 0) == 1:
# 				suffix = " SUB ASSY KIT"
# 			elif getattr(self, "duplicated_machining_kit", 0) == 1:
# 				suffix = " M/C KIT"

# 			final_desc = cus_description.strip()
# 			if suffix:
# 				# Append suffix keeping total <= 140 chars
# 				room = 140 - len(suffix)
# 				if room < 0:
# 					# extreme edge case: suffix itself too long, truncate it
# 					final_desc = suffix[:140]
# 				else:
# 					final_desc = (final_desc[:room].rstrip() + suffix).strip()
# 			else:
# 				# No suffix, still enforce cap
# 				final_desc = final_desc[:140]

# 			# Save the (possibly truncated) description
# 			self.short_description = final_desc
# 			self.custom_conditional_description = final_desc
# 			self.flags.ignore_validate = True
# 			self.flags.ignore_validate_fields = ["short_description"]
# 			# Use update_modified=False to prevent form from becoming dirty
# 			self.db_set("short_description", final_desc, update_modified=False)
# 			self.db_set("custom_conditional_description", final_desc, update_modified=False)


import frappe
from frappe.model.document import Document

class ItemGenerator(Document):
    
    def after_save(self):
        """Auto-close Item Generator when created from Sales Order"""
        if self.is_create_with_sales_order == 1 and self.is_closed != 1:
            self.db_set("is_closed", 1, update_modified=False)

    def before_validate(self):
        """Generate short description for selective products"""
        # Check if Selective Products document exists and has data
        try:
            selective_doc = frappe.get_doc("Selective Products", "Selective Products")
            templates_to_check = [p.product_name for p in selective_doc.products]
        except Exception as e:
            frappe.log_error(f"Selective Products document not found or error: {e}")
            return

        # Only process if template is in selective products list
        if not self.template_name or self.template_name not in templates_to_check:
            return

        # Required attributes for selective products
        required_attributes = [
            "TYPE OF PRODUCT",
            "VALVE TYPE",
            "SIZE",
            "RATING",
            "ENDS",
            "SHELL MOC",
            "OPERATOR",
        ]

        # Get template document to access attribute metadata
        try:
            template_doc = frappe.get_doc("Item Generator Template", self.template_name)
        except Exception as e:
            frappe.log_error(f"Error loading template: {e}")
            return

        short_desc_values = []
        
        # Loop through all 28 possible attributes
        for i in range(1, 29):
            label = getattr(self, f"attribute_{i}", "") or ""
            val = getattr(self, f"attribute_{i}_value", "") or ""
            
            # Skip if no value or value is "-"
            if not val or val.strip() == "-":
                continue
            
            # Check if this attribute is in required list
            if label.strip().upper() not in required_attributes:
                continue
            
            # Find the corresponding attribute heading from template
            attribute_heading = None
            for variant in template_doc.custom_variants:
                variant_heading = variant.logic_heading or ""
                # Extract the part after "-" if present
                if "-" in variant_heading:
                    variant_label = variant_heading.split("-", 1)[1].strip()
                else:
                    variant_label = variant_heading.strip()
                
                if variant_label.upper() == label.strip().upper():
                    attribute_heading = variant.logic_heading
                    break
            
            if not attribute_heading:
                # If no matching heading found, use the raw value
                short_desc_values.append(val)
                continue
            
            # Get the Custom Item Attribute document to find item_short_description
            try:
                attr_doc = frappe.get_doc("Custom Item Attribute", attribute_heading)
                
                # Find the matching row in logic_table based on item_long_description
                short_desc = None
                for row in attr_doc.logic_table:
                    if row.disabled == 0:
                        # Match by item_long_description (this is what's stored in attribute_X_value)
                        if row.item_long_description and row.item_long_description.strip().lower() == val.strip().lower():
                            short_desc = row.item_short_description or val
                            break
                
                if short_desc:
                    short_desc_values.append(short_desc)
                else:
                    # Fallback to raw value if no match found
                    short_desc_values.append(val)
                    
            except Exception as e:
                frappe.log_error(f"Error getting attribute metadata for {attribute_heading}: {e}")
                # Fallback to raw value
                short_desc_values.append(val)

        # Join all short description values with space
        cus_description = " ".join(short_desc_values)

        if cus_description:
            # Determine kit suffix based on flags
            suffix = ""
            if getattr(self, "duplicated_subassembly", 0) == 1:
                suffix = " SUB ASSY KIT"
            elif getattr(self, "duplicated_machining_kit", 0) == 1:
                suffix = " M/C KIT"

            final_desc = cus_description.strip()
            
            # Apply suffix and enforce 140 character limit
            if suffix:
                room = 140 - len(suffix)
                if room < 0:
                    # Edge case: suffix itself too long
                    final_desc = suffix[:140]
                else:
                    # Truncate description to make room for suffix
                    final_desc = (final_desc[:room].rstrip() + suffix).strip()
            else:
                # No suffix, still enforce 140 char limit
                final_desc = final_desc[:140]

            # Update both short description fields
            self.short_description = final_desc
            self.custom_conditional_description = final_desc
            
            # Set flags to prevent validation issues
            self.flags.ignore_validate = True
            
            # Safely initialize ignore_validate_fields
            if not hasattr(self.flags, 'ignore_validate_fields') or self.flags.ignore_validate_fields is None:
                self.flags.ignore_validate_fields = []
            
            # Add short_description to ignore list if not already present
            if isinstance(self.flags.ignore_validate_fields, list) and "short_description" not in self.flags.ignore_validate_fields:
                self.flags.ignore_validate_fields.append("short_description")
            
            # Save to database without updating modified timestamp
            # This prevents the form from becoming "dirty"
            if not self.is_new():
                self.db_set("short_description", final_desc, update_modified=False)
                self.db_set("custom_conditional_description", final_desc, update_modified=False)