import frappe
from frappe.model.document import Document


class ItemGenerator(Document):
    def before_validate(self):
        """Generate short description for selective products"""
        try:
            selective_doc = frappe.get_doc("Selective Products", "Selective Products")
            templates_to_check = [p.product_name for p in selective_doc.products]
        except Exception as e:
            frappe.log_error(f"Selective Products document not found or error: {e}")
            return

        # Only process if template is in selective products list
        if not self.template_name or self.template_name not in templates_to_check:
            return

        required_attributes = [
            "TYPE OF PRODUCT",
            "VALVE TYPE",
            "SIZE",
            "RATING",
            "ENDS",
            "SHELL MOC",
            "OPERATOR",
        ]

        try:
            template_doc = frappe.get_doc("Item Generator Template", self.template_name)
        except Exception as e:
            frappe.log_error(f"Error loading template: {e}")
            return

        short_desc_values = []

        for i in range(1, 29):
            label = getattr(self, f"attribute_{i}", "") or ""
            val = getattr(self, f"attribute_{i}_value", "") or ""

            if not val or val.strip() == "-":
                continue
            if label.strip().upper() not in required_attributes:
                continue

            # Find attribute heading from template
            attribute_heading = None
            for variant in template_doc.custom_variants:
                variant_heading = variant.logic_heading or ""
                variant_label = variant_heading.split("-", 1)[1].strip() if "-" in variant_heading else variant_heading.strip()

                if variant_label.upper() == label.strip().upper():
                    attribute_heading = variant.logic_heading
                    break

            if not attribute_heading:
                short_desc_values.append(val)
                continue

            # Get Custom Item Attribute document for short description
            try:
                attr_doc = frappe.get_doc("Custom Item Attribute", attribute_heading)
                short_desc = None

                for row in attr_doc.logic_table:
                    if row.disabled == 0 and row.item_long_description and row.item_long_description.strip().lower() == val.strip().lower():
                        short_desc = row.item_short_description or val
                        break

                short_desc_values.append(short_desc or val)

            except Exception as e:
                frappe.log_error(f"Error getting attribute metadata for {attribute_heading}: {e}")
                short_desc_values.append(val)

        cus_description = " ".join(short_desc_values)

        if cus_description:
            suffix = ""
            if getattr(self, "duplicated_subassembly", 0) == 1:
                suffix = " SUB ASSY KIT"
            elif getattr(self, "duplicated_machining_kit", 0) == 1:
                suffix = " M/C KIT"

            final_desc = cus_description.strip()
            if suffix:
                room = 140 - len(suffix)
                final_desc = (final_desc[:room].rstrip() + suffix).strip()
            else:
                final_desc = final_desc[:140]

            self.short_description = final_desc
            self.custom_conditional_description = final_desc

            # Prevent validation issues
            self.flags.ignore_validate = True
            if not hasattr(self.flags, "ignore_validate_fields") or self.flags.ignore_validate_fields is None:
                self.flags.ignore_validate_fields = []
            if "short_description" not in self.flags.ignore_validate_fields:
                self.flags.ignore_validate_fields.append("short_description")

            if not self.is_new():
                self.db_set("short_description", final_desc, update_modified=False)
                self.db_set("custom_conditional_description", final_desc, update_modified=False)


    def after_insert(self):
        """Automatically create Item after Item Generator is inserted"""
        if not self.item_code:
            return

        if not self.item_group_name:
            frappe.throw("Item Group is mandatory. Please select an Item Group.")

        try:
            igd = frappe.get_doc("Item Group Defaults", self.item_group_name)
        except Exception as e:
            frappe.log_error(f"Item Group Defaults document not found: {e}")
            frappe.throw(
                f"Item Group Defaults document '{self.item_group_name}' not found. Please select a valid Item Group Defaults."
            )

        # Create new Item
        doc = frappe.new_doc("Item")
        doc.item_code = self.item_code
        doc.item_name = self.short_description
        doc.description = self.description
        doc.gst_hsn_code = igd.hsn_code
        doc.created_by_ig = 1

        # Map fields directly
        field_list = [
            "item_group", "is_stock_item", "is_fixed_asset", "valuation_rate", "standard_rate",
            "over_delivery_receipt_allowance", "over_billing_allowance", "valuation_method",
            "is_purchase_item", "lead_time_days", "stock_uom", "purchase_uom", "sales_uom",
            "is_sales_item", "quality_inspection_template", "inspection_required_before_purchase",
            "inspection_required_before_delivery", "include_item_in_manufacturing", "is_sub_contracted_item",
            "has_batch_no", "create_new_batch", "batch_number_series", "has_expiry_date", "retain_sample",
            "sample_quantity", "has_serial_no", "serial_no_series"
        ]
        for field in field_list:
            setattr(doc, field, getattr(igd, field, None))

        # Map child tables
        for uom in igd.uoms:
            doc.append("uoms", {"uom": uom.uom, "conversion_factor": uom.conversion_factor})

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

        # Update flags without marking form dirty
        self.db_set("ig_done", 1, update_modified=False)
        self.db_set("created_item", doc.name, update_modified=False)

    def after_save(self):
        """Auto-close Item Generator when created from Sales Order"""
        if self.is_create_with_sales_order == 1 and self.is_closed != 1:
            self.db_set("is_closed", 1, update_modified=False)
