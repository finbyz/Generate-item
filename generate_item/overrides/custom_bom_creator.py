import frappe
from erpnext.manufacturing.doctype.bom_creator.bom_creator import BOMCreator as CoreBOMCreator
from generate_item.utils.bom_naming import set_bom_naming_series, get_custom_bom_name, get_available_bom_name
from frappe.utils import get_link_to_form

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
        # Track successfully created BOM names for user message with links
        self._created_boms = []
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
            # Build a message with links to the created BOM(s)
            links = []
            for bom_name in getattr(self, "_created_boms", []) or []:
                try:
                    links.append(get_link_to_form("BOM", bom_name))
                except Exception:
                    pass
            if links:
                message = "Created BOM(s): " + ", ".join(links)
                frappe.msgprint(message, title="BOMs Created", indicator="green")
            else:
                frappe.msgprint("BOMs created successfully", title="BOMs Created", indicator="green")
        except Exception:
            traceback = frappe.get_traceback(with_context=True)
            self.db_set({"status": "Failed", "error_log": traceback})
            frappe.log_error("BOM Creation Failed", traceback)
            frappe.msgprint("BOMs creation failed")

    def create_bom(self, row, production_item_wise_rm, group_key):
        """Override to inject custom fields while preserving standard BOM creation logic."""
        
        # CRITICAL: Use group_key to get the correct item_code, not row.item_code
        # group_key is (item_code, reference_id) tuple from how we built production_item_wise_rm
        correct_item_code = group_key[0]
        correct_reference_id = group_key[1]
        
        # Determine bom_creator_item reference
        bom_creator_item = correct_reference_id if correct_reference_id != self.name else ""
        
        # Check if BOM already exists (skip if submitted BOM exists)
        # existing_bom = frappe.db.exists(
        #     "BOM",
        #     {
        #         "bom_creator": self.name,
        #         "item": correct_item_code,
        #         "bom_creator_item": bom_creator_item,
        #         "docstatus": 1,
        #     },
        # )
        bom_creator_item_value = bom_creator_item or None

        existing_bom = frappe.db.get_value(
            "BOM",
            {
                "bom_creator": self.name,
                "item": correct_item_code,
                "bom_creator_item": ["in", [bom_creator_item_value, "", None]],
                "docstatus": 1,
            },
            "name",
        )
        
        if existing_bom:
            # BOM already exists, just store its name and skip creation
            production_item_wise_rm[group_key].bom_no = existing_bom
            frappe.log_error(
                "BOM Already Exists",
                f"Submitted BOM {existing_bom} already exists for {correct_item_code}, skipping creation"
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
                    f"Cannot create BOM for {correct_item_code} - no raw materials found for group_key: {group_key}"
                )
                return

        # Create new BOM document
        bom = frappe.new_doc("BOM")
        bom.update({
            "item": correct_item_code,
            "quantity": row.qty,
            "bom_creator": self.name,
            "bom_creator_item": bom_creator_item,
            "custom_is_sub_assembly": bool(getattr(row, "is_expandable", False)),
        })

        # CUSTOM: Pass branch information to BOM for custom naming
        if hasattr(self, 'branch') and self.branch:
            bom.branch = self.branch
        # If branch not set on BOM Creator, try to derive it from linked Sales Order
        if not getattr(bom, 'branch', None):
            try:
                so_name = getattr(self, 'sales_order', None)
                if so_name:
                    so_branch = frappe.get_cached_value("Sales Order", so_name, "branch")
                    if so_branch:
                        bom.branch = so_branch
            except Exception:
                pass
        if hasattr(self, 'branch_abbr') and self.branch_abbr:
            bom.branch_abbr = self.branch_abbr
        # If branch_abbr still missing, derive from Branch master (abbr/custom_abbr) or fallback map
        if not getattr(bom, 'branch_abbr', None) and getattr(bom, 'branch', None):
            try:
                abbr = None
                try:
                    abbr = frappe.get_cached_value("Branch", bom.branch, "abbr")
                except Exception:
                    abbr = None
                if not abbr:
                    try:
                        abbr = frappe.get_cached_value("Branch", bom.branch, "custom_abbr")
                    except Exception:
                        abbr = None
                if not abbr:
                    branch_abbr_map = { 'Rabale': 'RA', 'Nandikoor': 'NA', 'Sanand': 'SA' }
                    abbr = branch_abbr_map.get(bom.branch, None)
                if abbr:
                    bom.branch_abbr = abbr
            except Exception:
                pass

        # Ensure custom naming series is applied so duplicates get suffixed automatically
        try:
            set_bom_naming_series(bom)
        except Exception:
            frappe.log_error(
                "BOM Naming Series Setup Failed",
                f"BOM Creator: {self.name}, Item: {correct_item_code}\n\n{frappe.get_traceback(with_context=True)}",
            )

        # Copy standard BOM fields from BOM Creator header
        from erpnext.manufacturing.doctype.bom_creator.bom_creator import BOM_FIELDS, BOM_ITEM_FIELDS
        
        for field in BOM_FIELDS:
            if self.get(field):
                bom.set(field, self.get(field))

        # CUSTOM: Inject custom fields to BOM header
        try:
            self._inject_custom_fields_to_bom(bom, row, correct_item_code)
        except Exception:
            frappe.log_error(
                "Custom field injection failed",
                f"BOM Creator: {self.name}, Item: {correct_item_code}\n\n{frappe.get_traceback(with_context=True)}",
            )

        # Add child items to BOM
        for item in items_list:
            # Check if item is a sub-assembly with its own BOM
            bom_no = ""
            item.do_not_explode = 0 # change Always need 0
            
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
                    f"BOM for {correct_item_code} has no items after processing. Cannot save BOM without raw materials."
                )
            return

        # Save and submit BOM
        try:
            bom.save(ignore_permissions=True)
            bom.submit()
            # Track created BOM for user message and parent references
            production_item_wise_rm[group_key].bom_no = bom.name
            self._created_boms.append(bom.name)
            frappe.log_error(
                "BOM Created Successfully",
                f"Created BOM {bom.name} for item {correct_item_code} (group_key: {group_key})"
            )
        except Exception as e:
            # Duplicate-safe fallback: if name conflict, add incremental suffix and retry once
            try:
                from frappe.exceptions import DuplicateEntryError, UniqueValidationError
            except Exception:
                DuplicateEntryError = Exception
                UniqueValidationError = Exception


    def _inject_custom_fields_to_bom(self, bom, row, correct_item_code):
        """Inject custom fields from BOM Creator to BOM header."""
        # Handle batch vs sales order mode (mutually exclusive)
        has_batch = bool(getattr(self, "custom_batch_no", None))
        has_sales_order = bool(getattr(self, "sales_order", None))

        if has_batch:
            # Batch-mode: set batch, clear sales order to avoid validation conflict
            bom.custom_batch_no = self.custom_batch_no
            bom.sales_order  = self.sales_order
        elif has_sales_order:
            # Sales-order-mode: set SO, leave batch empty
            bom.sales_order = self.sales_order
            bom.custom_batch_no =None

        # CUSTOM: Map drawing specification fields from matching item
        source_item = None
        if getattr(bom, "item", None) and getattr(self, "items", None):
            # Find exact match by item_code using the CORRECT item code from group_key
            for it in self.items:
                if getattr(it, "item_code", None) == correct_item_code:
                    source_item = it
                    break
        
        # Fallback to current row if it matches the correct item code
        if not source_item and getattr(row, "item_code", None) == correct_item_code:
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