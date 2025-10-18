# import frappe
# from erpnext.manufacturing.doctype.bom_creator.bom_creator import BOMCreator as CoreBOMCreator


# class BOMCreator(CoreBOMCreator):
#     def on_submit(self):
#         """Run BOM creation synchronously so custom field injection happens during submit."""
#         try:
#             # mirror core pre-submit behavior if any, then run create_boms directly
#             self.create_boms()
#         except Exception:
#             frappe.log_error(
#                 "Custom BOMCreator.on_submit failed",
#                 f"BOM Creator: {self.name}\n\n{frappe.get_traceback(with_context=True)}",
#             )
#             raise

#     def create_boms(self):
#         """Override to make grouping robust if keys are missing.

#         - Ensure reference IDs are set
#         - Lazily create missing (fg_item, fg_reference_id) groups before appending
#         - Preserve core processing order
#         """
#         from collections import OrderedDict

#         # Ensure FG reference ids are available as in core before_save
#         try:
#             self.set_reference_id()
#         except Exception:
#             frappe.log_error(
#                 "BOMCreator.set_reference_id failed",
#                 f"BOM Creator: {self.name}\n\n{frappe.get_traceback(with_context=True)}",
#             )

#         self.db_set("status", "In Progress")
#         production_item_wise_rm = OrderedDict({})
#         production_item_wise_rm.setdefault(
#             (self.item_code, self.name), frappe._dict({"items": [], "bom_no": "", "fg_item_data": self})
#         )

#         for row in self.items:
#             if row.is_expandable:
#                 if (row.item_code, row.name) not in production_item_wise_rm:
#                     production_item_wise_rm.setdefault(
#                         (row.item_code, row.name),
#                         frappe._dict({"items": [], "bom_no": "", "fg_item_data": row}),
#                     )

#             key = (row.fg_item, row.fg_reference_id)
#             if key not in production_item_wise_rm:
#                 # Try to resolve the parent row referenced by fg_reference_id
#                 fg_item_data = self
#                 if row.fg_reference_id:
#                     parent_row = None
#                     try:
#                         for _r in self.items:
#                             if getattr(_r, "name", None) == row.fg_reference_id:
#                                 parent_row = _r
#                                 break
#                     except Exception:
#                         parent_row = None
#                     if parent_row:
#                         fg_item_data = parent_row
#                 production_item_wise_rm.setdefault(
#                     key, frappe._dict({"items": [], "bom_no": "", "fg_item_data": fg_item_data})
#                 )

#             production_item_wise_rm[key]["items"].append(row)

#         reverse_tree = OrderedDict(reversed(list(production_item_wise_rm.items())))

#         try:
#             for d in reverse_tree:
#                 fg_item_data = production_item_wise_rm.get(d).fg_item_data
#                 self.create_bom(fg_item_data, production_item_wise_rm)

#             frappe.msgprint("BOMs created successfully")
#         except Exception:
#             traceback = frappe.get_traceback(with_context=True)
#             self.db_set({"status": "Failed", "error_log": traceback})
#             frappe.msgprint("BOMs creation failed")

#     def create_bom(self, row, production_item_wise_rm):
#         """Override to inject custom field mapping to BOM before save/submit."""
#         # Note: This may run in background in core; in our sync override it runs inline
#         frappe.log_error("Custom BOMCreator.create_bom", f"Creating BOM for {row.item_code} from {self.name}")
#         # First, call core logic up to constructing the BOM doc
#         bom_creator_item = row.name if row.name != self.name else ""
#         if frappe.db.exists(
#             "BOM",
#             {
#                 "bom_creator": self.name,
#                 "item": row.item_code,
#                 "bom_creator_item": bom_creator_item,
#                 "docstatus": 1,
#             },
#         ):
#             return

#         bom = frappe.new_doc("BOM")
#         bom.update(
#             {
#                 "item": row.item_code,
#                 "bom_type": "Production",
#                 "quantity": row.qty,
#                 "bom_creator": self.name,
#                 "bom_creator_item": bom_creator_item,
                
#             }
#         )

#         # Copy all standard BOM fields from parent
#         from erpnext.manufacturing.doctype.bom_creator.bom_creator import BOM_FIELDS, BOM_ITEM_FIELDS
#         for field in BOM_FIELDS:
#             if self.get(field):
#                 bom.set(field, self.get(field))

#         # Inject custom fields from BOM Creator header and matching item BEFORE adding children
#         try:
#             # Set BOM Creator header fields first
#             has_batch = bool(getattr(self, "custom_batch_no", None))
#             has_sales_order = bool(getattr(self, "sales_order", None))

#             if has_batch:
#                 # Batch-mode: set batch, clear sales order to avoid validation conflict
#                 bom.custom_batch_no = self.custom_batch_no
#                 bom.sales_order = None
#                 frappe.log_error(
#                     "BOM Creator Header Batch",
#                     f"Set BOM {bom.item} custom_batch_no from BOM Creator header: {self.custom_batch_no} and cleared sales_order to avoid conflict"
#                 )
#             elif has_sales_order:
#                 # Sales-order-mode: set SO, leave batch empty
#                 bom.sales_order = self.sales_order

#             # Prefer matching item by item_code for drawing fields
#             source_item = None
#             if getattr(bom, "item", None) and getattr(self, "items", None):
#                 for it in self.items:
#                     if getattr(it, "item_code", None) == bom.item:
#                         source_item = it
#                         break
#                 if not source_item and len(self.items) > 0:
#                     source_item = self.items[0]

#             if source_item:
#                 frappe.log_error(
#                     "Custom BOMCreator.create_bom fields",
#                     f"BOM {bom.item}: drawing={source_item.get('custom_drawing_no')}, pattern={source_item.get('custom_pattern_drawing_no')}, purchase_spec={source_item.get('custom_purchase_specification_no')}"
#                 )
                
#                 # Only set drawing fields from source_item, NOT custom_batch_no
#                 # custom_batch_no should come from BOM Creator header, not from items
#                 bom.custom_drawing_no = source_item.get("custom_drawing_no")
#                 bom.custom_drawing_rev_no = source_item.get("custom_drawing_rev_no")
#                 bom.custom_pattern_drawing_no = source_item.get("custom_pattern_drawing_no")
#                 bom.custom_pattern_drawing_rev_no = source_item.get("custom_pattern_drawing_rev_no")
#                 bom.custom_purchase_specification_no = source_item.get("custom_purchase_specification_no")
#                 bom.custom_purchase_specification_rev_no = source_item.get("custom_purchase_specification_rev_no")
#         except Exception:
#             # Non-blocking: if mapping fails, continue with core flow
#             frappe.log_error(
#                 "Custom field injection failed",
#                 f"BOM Creator: {self.name}, Item: {row.item_code}\n\n{frappe.get_traceback(with_context=True)}",
#             )

#         # Add child items as per core logic
#         key = (row.item_code, row.name)
#         for item in production_item_wise_rm[key]["items"]:
#             bom_no = ""
#             item.do_not_explode = 1
#             if (item.item_code, item.name) in production_item_wise_rm:
#                 bom_no = production_item_wise_rm.get((item.item_code, item.name)).bom_no
#                 item.do_not_explode = 0

#             item_args = {}
#             for field in BOM_ITEM_FIELDS:
#                 item_args[field] = item.get(field)

#             # If a linked BOM is present and has conflicting fields, resolve based on current BOM mode
#             if bom_no:
#                 try:
#                     linked = frappe.get_doc("BOM", bom_no)
#                     if getattr(linked, "custom_batch_no", None) and getattr(linked, "sales_order", None):
#                         is_batch_mode = bool(getattr(bom, "custom_batch_no", None))
#                         is_so_mode = bool(getattr(bom, "sales_order", None)) and not is_batch_mode
#                         if is_batch_mode:
#                             linked.db_set("sales_order", None)
#                         elif is_so_mode:
#                             linked.db_set("custom_batch_no", None)
#                         else:
#                             # Unknown mode; avoid validation by unlinking for now
#                             bom_no = ""
#                 except Exception:
#                     # If fetch fails, unlink to avoid validation failure
#                     bom_no = ""

#             item_args.update(
#                 {
#                     "bom_no": bom_no,
#                     "allow_scrap_items": 1,
#                     "include_item_in_manufacturing": 1,
#                 }
#             )

#             # Map custom fields from BOM Creator Item -> BOM Item child row (if present on target doctype)
#             for cf in (
#                 "custom_drawing_no",
#                 "custom_drawing_rev_no",
#                 "custom_pattern_drawing_no",
#                 "custom_pattern_drawing_rev_no",
#                 "custom_purchase_specification_no",
#                 "custom_purchase_specification_rev_no",
#             ):
#                 try:
#                     cf_val = item.get(cf)
#                 except Exception:
#                     cf_val = getattr(item, cf, None)
#                 if cf_val is not None:
#                     item_args[cf] = cf_val
            
#             # For custom_batch_no, only set in batch-mode to avoid conflicts with sales-order-mode
#             if bool(getattr(self, "custom_batch_no", None)) and not bool(getattr(self, "sales_order", None)):
#                 item_args["custom_batch_no"] = self.custom_batch_no
#                 frappe.log_error(
#                     "BOM Item Batch Set",
#                     f"Set BOM Item {item.get('item_code')} custom_batch_no from BOM Creator header: {self.custom_batch_no}"
#                 )

#             bom.append("items", item_args)

#         # Resolve conflicts on any linked child BOMs before saving this BOM
#         try:
#             is_batch_mode = bool(getattr(bom, "custom_batch_no", None))
#             is_so_mode = bool(getattr(bom, "sales_order", None)) and not is_batch_mode
#             for bi in bom.items or []:
#                 if not getattr(bi, "bom_no", None):
#                     # Also check the default BOM of the item if no explicit bom_no is set
#                     try:
#                         default_bom = frappe.get_cached_value("Item", bi.item_code, "default_bom")
#                     except Exception:
#                         default_bom = None
#                     if default_bom:
#                         try:
#                             linked = frappe.get_doc("BOM", default_bom)
#                             if getattr(linked, "custom_batch_no", None) and getattr(linked, "sales_order", None):
#                                 if is_batch_mode:
#                                     linked.db_set("sales_order", None)
#                                 elif is_so_mode:
#                                     linked.db_set("custom_batch_no", None)
#                         except Exception:
#                             pass
#                     continue
#                 try:
#                     linked = frappe.get_doc("BOM", bi.bom_no)
#                 except Exception:
#                     continue
#                 if getattr(linked, "custom_batch_no", None) and getattr(linked, "sales_order", None):
#                     if is_batch_mode:
#                         linked.db_set("sales_order", None)
#                     elif is_so_mode:
#                         linked.db_set("custom_batch_no", None)
#         except Exception:
#             frappe.log_error(
#                 "Child BOM conflict resolution failed",
#                 f"BOM: {getattr(bom, 'name', '')}\n\n{frappe.get_traceback(with_context=True)}",
#             )

#         # Save and submit
#         bom.save(ignore_permissions=True)
#         bom.submit()

#         production_item_wise_rm[(row.item_code, row.name)].bom_no = bom.name


import frappe
from erpnext.manufacturing.doctype.bom_creator.bom_creator import BOMCreator as CoreBOMCreator
from collections import OrderedDict


class BOMCreator(CoreBOMCreator):
    def on_submit(self):
        """Run BOM creation synchronously so custom field injection happens during submit."""
        try:
            self.create_boms()
        except Exception:
            frappe.log_error(
                "Custom BOMCreator.on_submit failed",
                f"BOM Creator: {self.name}\n\n{frappe.get_traceback(with_context=True)}",
            )
            raise

    def create_boms(self):
        """
        Override to fix ERPNext bug (GitHub issue #43948) and inject custom fields.
        
        Standard ERPNext has a KeyError bug where it assumes parent keys exist before
        appending items. This override fixes that while preserving exact standard logic.
        """
        # Ensure FG reference ids are set
        try:
            self.set_reference_id()
        except Exception:
            frappe.log_error(
                "BOMCreator.set_reference_id failed",
                f"BOM Creator: {self.name}\n\n{frappe.get_traceback(with_context=True)}",
            )

        self.db_set("status", "In Progress")
        production_item_wise_rm = OrderedDict()

        # Initialize root production item (FG item from BOM Creator header)
        production_item_wise_rm[(self.item_code, self.name)] = frappe._dict({
            "items": [],
            "bom_no": "",
            "fg_item_data": self
        })

        # Process all items in the BOM Creator items table
        for row in self.items:
            # If item is expandable (will be a sub-assembly), initialize its group
            if row.is_expandable:
                production_item_wise_rm[(row.item_code, row.name)] = frappe._dict({
                    "items": [],
                    "bom_no": "",
                    "fg_item_data": row
                })

            # FIX for ERPNext bug: Ensure parent key exists BEFORE appending
            # This prevents KeyError: (fg_item, fg_reference_id)
            parent_key = (row.fg_item, row.fg_reference_id)
            
            if parent_key not in production_item_wise_rm:
                # Find the parent row data
                fg_item_data = self  # Default to BOM Creator itself
                
                # If fg_reference_id points to a specific item row, find it
                if row.fg_reference_id and row.fg_reference_id != self.name:
                    for parent_row in self.items:
                        if getattr(parent_row, "name", None) == row.fg_reference_id:
                            fg_item_data = parent_row
                            break
                
                # Initialize the missing parent group
                production_item_wise_rm[parent_key] = frappe._dict({
                    "items": [],
                    "bom_no": "",
                    "fg_item_data": fg_item_data
                })

            # Add this item to its parent's items list
            production_item_wise_rm[parent_key]["items"].append(row)

        # Process in reverse order (leaf nodes first) for bottom-up BOM creation
        reverse_tree = OrderedDict(reversed(list(production_item_wise_rm.items())))

        try:
            for group_key, group_data in reverse_tree.items():
                fg_item_data = group_data.fg_item_data
                # Create BOM with the exact group_key used for grouping
                self.create_bom(fg_item_data, production_item_wise_rm, group_key)

            self.db_set("status", "Completed")
            frappe.msgprint("BOMs created successfully")
        except Exception:
            traceback = frappe.get_traceback(with_context=True)
            self.db_set({"status": "Failed", "error_log": traceback})
            frappe.log_error("BOM Creation Failed", traceback)
            frappe.msgprint("BOMs creation failed")

    def create_bom(self, row, production_item_wise_rm, group_key):
        """Override to inject custom fields while preserving standard BOM creation logic."""
        
        # Determine bom_creator_item reference
        bom_creator_item = row.name if row.name != self.name else ""
        
        # Check if BOM already exists (skip if submitted BOM exists)
        if frappe.db.exists(
            "BOM",
            {
                "bom_creator": self.name,
                "item": row.item_code,
                "bom_creator_item": bom_creator_item,
                "docstatus": 1,
            },
        ):
            frappe.log_error(
                "BOM Already Exists",
                f"Submitted BOM already exists for {row.item_code}, skipping creation"
            )
            return

        # Get items for this BOM from the production dict
        items_list = production_item_wise_rm.get(group_key, {}).get("items", [])
        
        # Check if we have any items
        if not items_list:
            # For expandable items (sub-assemblies), this might be valid if they only have sub-BOMs
            if not getattr(row, "is_expandable", False):
                frappe.log_error(
                    "BOM Creator - No Raw Materials",
                    f"Cannot create BOM for {row.item_code} - no raw materials found for group_key: {group_key}"
                )
                return

        # Create new BOM document
        bom = frappe.new_doc("BOM")
        bom.update({
            "item": row.item_code,
            "quantity": row.qty,
            "bom_creator": self.name,
            "bom_creator_item": bom_creator_item,
        })

        # Copy standard BOM fields from BOM Creator header
        from erpnext.manufacturing.doctype.bom_creator.bom_creator import BOM_FIELDS, BOM_ITEM_FIELDS
        
        for field in BOM_FIELDS:
            if self.get(field):
                bom.set(field, self.get(field))

        # CUSTOM: Inject custom fields to BOM header
        try:
            self._inject_custom_fields_to_bom(bom, row)
        except Exception:
            frappe.log_error(
                "Custom field injection failed",
                f"BOM Creator: {self.name}, Item: {row.item_code}\n\n{frappe.get_traceback(with_context=True)}",
            )

        # Add child items to BOM
        for item in items_list:
            # Check if item is a sub-assembly with its own BOM
            bom_no = ""
            item.do_not_explode = 1
            
            sub_key = (item.item_code, item.name)
            if sub_key in production_item_wise_rm:
                bom_no = production_item_wise_rm[sub_key].get("bom_no", "")
                if bom_no:
                    item.do_not_explode = 0

            # Build item arguments from standard BOM_ITEM_FIELDS
            item_args = {}
            for field in BOM_ITEM_FIELDS:
                item_args[field] = item.get(field)

            # CUSTOM: Resolve conflicts in linked BOM if needed
            if bom_no:
                bom_no = self._resolve_linked_bom_conflicts(bom, bom_no)

            # Set additional standard item properties
            item_args.update({
                "bom_no": bom_no,
                "allow_scrap_items": 1,
                "include_item_in_manufacturing": 1,
            })

            # CUSTOM: Map custom fields from BOM Creator Item to BOM Item
            self._inject_custom_fields_to_bom_item(item, item_args, bom)
            
            # Add item to BOM
            bom.append("items", item_args)

        # CUSTOM: Resolve conflicts on all linked child BOMs before saving
        self._resolve_child_bom_conflicts(bom)

        # Validate that BOM has items before saving
        if not bom.items or len(bom.items) == 0:
            # Only log error if this was not an expandable item
            if not getattr(row, "is_expandable", False):
                frappe.log_error(
                    "BOM Creator - No Items Added",
                    f"BOM for {row.item_code} has no items after processing. Cannot save BOM without raw materials."
                )
            return

        # Save and submit BOM
        try:
            bom.save(ignore_permissions=True)
            bom.submit()
            
            # Store BOM number back in production dict for parent references
            production_item_wise_rm[group_key].bom_no = bom.name
            
            frappe.log_error(
                "BOM Created Successfully",
                f"Created BOM {bom.name} for item {row.item_code}"
            )
            
        except Exception:
            frappe.log_error(
                "BOM Save/Submit Failed",
                f"Item: {row.item_code}\nError: {frappe.get_traceback(with_context=True)}",
            )
            raise

    def _inject_custom_fields_to_bom(self, bom, row):
        """Inject custom fields from BOM Creator to BOM header."""
        # Handle batch vs sales order mode (mutually exclusive)
        has_batch = bool(getattr(self, "custom_batch_no", None))
        has_sales_order = bool(getattr(self, "sales_order", None))

        if has_batch:
            # Batch-mode: set batch, clear sales order to avoid validation conflict
            bom.custom_batch_no = self.custom_batch_no
            bom.sales_order = None
        elif has_sales_order:
            # Sales-order-mode: set SO, leave batch empty
            bom.sales_order = self.sales_order
            bom.custom_batch_no = None

        # Map drawing specification fields from matching item
        source_item = None
        if getattr(bom, "item", None) and getattr(self, "items", None):
            # Find exact match by item_code
            for it in self.items:
                if getattr(it, "item_code", None) == bom.item:
                    source_item = it
                    break
        
        # Fallback to current row if it matches
        if not source_item and getattr(row, "item_code", None) == getattr(bom, "item", None):
            source_item = row

        if source_item:
            # Map all drawing-related custom fields
            drawing_fields = [
                "custom_drawing_no",
                "custom_drawing_rev_no",
                "custom_pattern_drawing_no",
                "custom_pattern_drawing_rev_no",
                "custom_purchase_specification_no",
                "custom_purchase_specification_rev_no",
            ]
            
            for field in drawing_fields:
                value = source_item.get(field)
                if value:
                    bom.set(field, value)

    def _inject_custom_fields_to_bom_item(self, item, item_args, parent_bom):
        """Inject custom fields from BOM Creator Item to BOM Item child row."""
        # Map drawing specification fields
        custom_fields = [
            "custom_drawing_no",
            "custom_drawing_rev_no",
            "custom_pattern_drawing_no",
            "custom_pattern_drawing_rev_no",
            "custom_purchase_specification_no",
            "custom_purchase_specification_rev_no",
        ]
        
        for cf in custom_fields:
            try:
                cf_val = item.get(cf)
            except Exception:
                cf_val = getattr(item, cf, None)
            if cf_val:
                item_args[cf] = cf_val
        
        # Set batch number only in batch mode (not in sales order mode)
        is_batch_mode = bool(getattr(self, "custom_batch_no", None))
        is_so_mode = bool(getattr(self, "sales_order", None))
        
        if is_batch_mode and not is_so_mode:
            item_args["custom_batch_no"] = self.custom_batch_no

    def _resolve_linked_bom_conflicts(self, parent_bom, bom_no):
        """
        Resolve conflicts when linked BOM has both batch and sales order.
        Returns the bom_no if resolved, empty string if should unlink.
        """
        if not bom_no:
            return ""
            
        try:
            linked_bom = frappe.get_doc("BOM", bom_no)
            
            # Check if linked BOM has conflicting fields (both batch and SO)
            has_both = (
                getattr(linked_bom, "custom_batch_no", None) and 
                getattr(linked_bom, "sales_order", None)
            )
            
            if not has_both:
                return bom_no
            
            # Resolve based on parent BOM's mode
            parent_has_batch = bool(getattr(parent_bom, "custom_batch_no", None))
            parent_has_so = bool(getattr(parent_bom, "sales_order", None))
            
            if parent_has_batch and not parent_has_so:
                # Batch mode: clear sales order from linked BOM
                linked_bom.db_set("sales_order", None, update_modified=False)
                frappe.db.commit()
            elif parent_has_so and not parent_has_batch:
                # Sales order mode: clear batch from linked BOM
                linked_bom.db_set("custom_batch_no", None, update_modified=False)
                frappe.db.commit()
            else:
                # Unclear mode: unlink to avoid validation errors
                return ""
                
        except Exception:
            # If resolution fails, unlink to avoid validation errors
            frappe.log_error(
                "Linked BOM conflict resolution failed",
                f"BOM: {bom_no}\n\n{frappe.get_traceback(with_context=True)}",
            )
            return ""
        
        return bom_no

    def _resolve_child_bom_conflicts(self, bom):
        """
        Resolve conflicts on all linked child BOMs before saving parent.
        Prevents validation errors when child BOMs have conflicting batch/SO fields.
        """
        try:
            parent_has_batch = bool(getattr(bom, "custom_batch_no", None))
            parent_has_so = bool(getattr(bom, "sales_order", None))
            
            # Determine parent mode
            if parent_has_batch and not parent_has_so:
                mode = "batch"
            elif parent_has_so and not parent_has_batch:
                mode = "sales_order"
            else:
                mode = "unclear"
            
            for bom_item in bom.items or []:
                linked_bom_no = getattr(bom_item, "bom_no", None)
                
                # Also check item's default BOM if no explicit link
                if not linked_bom_no:
                    try:
                        linked_bom_no = frappe.get_cached_value(
                            "Item", 
                            bom_item.item_code, 
                            "default_bom"
                        )
                    except Exception:
                        continue
                
                if not linked_bom_no:
                    continue
                
                try:
                    linked_bom = frappe.get_doc("BOM", linked_bom_no)
                    
                    # Check for conflict (both batch and SO present)
                    has_both = (
                        getattr(linked_bom, "custom_batch_no", None) and 
                        getattr(linked_bom, "sales_order", None)
                    )
                    
                    if not has_both:
                        continue
                    
                    # Resolve based on parent mode
                    if mode == "batch":
                        linked_bom.db_set("sales_order", None, update_modified=False)
                        frappe.db.commit()
                    elif mode == "sales_order":
                        linked_bom.db_set("custom_batch_no", None, update_modified=False)
                        frappe.db.commit()
                    
                except Exception:
                    # Non-blocking: log and continue
                    frappe.log_error(
                        "Child BOM conflict resolution failed",
                        f"Child BOM: {linked_bom_no}\n\n{frappe.get_traceback(with_context=True)}",
                    )
                    
        except Exception:
            frappe.log_error(
                "Child BOM conflict resolution failed",
                f"Parent BOM: {getattr(bom, 'name', 'unsaved')}\n\n{frappe.get_traceback(with_context=True)}",
            )