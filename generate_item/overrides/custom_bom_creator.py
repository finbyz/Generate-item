import time

import frappe
from frappe.exceptions import QueryDeadlockError
from erpnext.manufacturing.doctype.bom_creator.bom_creator import BOMCreator as CoreBOMCreator

class BOMCreator(CoreBOMCreator):
    def create_boms(self):
        """
        Override create_boms to inject custom fields after BOM creation.
        """
        # Call parent method to create BOMs
        super().create_boms()
        
        # After BOMs are created, update them with custom fields
        try:
            self._update_created_boms_with_custom_fields()
        except Exception as e:
            frappe.log_error(
                "BOM Creator - Custom Field Update Failed",
                f"BOM Creator: {self.name}\n\n{frappe.get_traceback()}"
            )
    
    def _update_created_boms_with_custom_fields(self):
        """
        Update all created BOMs with custom fields from BOM Creator.
        """
        # Get all BOMs created by this BOM Creator
        bom_list = frappe.get_all(
            "BOM",
            filters={"bom_creator": self.name, "docstatus": ["<", 2]},
            fields=["name", "item", "bom_creator_item"]
        )
        
        for bom_data in bom_list:
            try:
                bom = frappe.get_doc("BOM", bom_data.name)
                updated = False
                
                # 1. Map sales_order and custom_batch_no from BOM Creator to parent BOM
                if hasattr(self, 'sales_order') and self.sales_order:
                    if not bom.sales_order:
                        bom.sales_order = self.sales_order
                        updated = True
                
                if hasattr(self, 'custom_batch_no') and self.custom_batch_no:
                    if not bom.custom_batch_no:
                        bom.custom_batch_no = self.custom_batch_no
                        updated = True
                
                # 2. Map branch from sales order
                if bom.sales_order:
                    try:
                        branch = frappe.get_cached_value("Sales Order", bom.sales_order, "branch")
                        if branch:
                            # Set branch on parent BOM if not set
                            if not bom.branch:
                                bom.branch = branch
                                updated = True
                            
                            # Set branch_abbr on parent BOM if not set
                            if not getattr(bom, 'branch_abbr', None):
                                # Get branch_abbr from Branch master
                                branch_abbr = frappe.get_cached_value("Branch", branch, "abbr") or \
                                             frappe.get_cached_value("Branch", branch, "custom_abbr")
                                if branch_abbr:
                                    bom.branch_abbr = branch_abbr
                                else:
                                    # Fallback mapping
                                    branch_abbr_map = {'Rabale': 'RA', 'Nandikoor': 'NA', 'Sanand': 'SA'}
                                    bom.branch_abbr = branch_abbr_map.get(branch, None)
                                updated = True
                            
                            # Always set branch in BOM items if not already set
                            for bom_item in bom.items:
                                if not getattr(bom_item, 'branch', None):
                                    bom_item.branch = branch
                                    updated = True
                            
                    except Exception:
                        pass
                
                # 3. Map drawing fields to BOM items
                if self._map_drawing_fields_to_bom_items(bom, bom_data.bom_creator_item):
                    updated = True

                if updated:
                    bom.save(ignore_permissions=True)
                    bom.reload()
                    
            except Exception as e:
                frappe.log_error(
                    "BOM Creator - Failed to update BOM",
                    f"BOM: {bom_data.name}\n\n{frappe.get_traceback()}"
                )
    
    def create_bom(self, row, production_item_wise_rm):
        """Wrap core create_bom with retry to gracefully handle deadlocks."""
        max_retries = 2
        last_exception = None

        for attempt in range(1, max_retries + 1):
            try:
                return super().create_bom(row, production_item_wise_rm)
            except QueryDeadlockError as exc:
                frappe.db.rollback()
                last_exception = exc

                bom_creator_item = row.name if getattr(row, "name", None) != self.name else ""
                existing_bom = frappe.db.get_value(
                    "BOM",
                    {
                        "bom_creator": self.name,
                        "item": row.item_code,
                        "bom_creator_item": bom_creator_item,
                        "docstatus": 1,
                    },
                )

                if existing_bom:
                    key = (row.item_code, getattr(row, "name", None))
                    context = production_item_wise_rm.get(key)
                    if context:
                        context.bom_no = existing_bom

                    frappe.logger("generate_item").warning(
                        "Handled BOM Creator deadlock by reusing existing BOM %s for item %s (Creator %s)",
                        existing_bom,
                        row.item_code,
                        self.name,
                    )
                    return

                if attempt < max_retries:
                    time.sleep(0.5 * attempt)
                    continue

                break

        if last_exception:
            raise last_exception
    
    def _map_drawing_fields_to_bom_items(self, bom, bom_creator_item_ref):
        """
        Map drawing fields from BOM Creator items to BOM items.
        Handles both direct item_code matching and parent-child relationships.
        Returns True if any updates were made.
        """
        updated = False
        
        try:
            # Build multiple maps for flexible matching
            # 1. Map by item_code
            bom_creator_item_map = {}
            # 2. Map by name (for parent-child relationships)
            bom_creator_item_by_name = {}
            # 3. Map by fg_reference_id (links child items to parent)
            bom_creator_item_by_fg_ref = {}
            # 4. Map by idx (row index)
            bom_creator_item_by_idx = {}
            
            for item in self.items:
                if item.item_code:
                    bom_creator_item_map[item.item_code] = item
                if item.name:
                    bom_creator_item_by_name[item.name] = item
                if hasattr(item, 'fg_reference_id') and item.fg_reference_id:
                    if item.fg_reference_id not in bom_creator_item_by_fg_ref:
                        bom_creator_item_by_fg_ref[item.fg_reference_id] = []
                    bom_creator_item_by_fg_ref[item.fg_reference_id].append(item)
                if hasattr(item, 'idx') and item.idx:
                    bom_creator_item_by_idx[item.idx] = item
            
            # Helper function to find and map custom fields
            def find_and_map_custom_fields(bom_item, item_code):
                """Find BOM Creator item and map custom fields. Returns True if updated."""
                bom_creator_item = None
                item_updated = False
                
                # Strategy 1: Direct item_code match
                bom_creator_item = bom_creator_item_map.get(item_code)
                
                # Strategy 2: If not found and bom_item has fg_reference_id, try to find by fg_reference_id
                if not bom_creator_item and hasattr(bom_item, 'fg_reference_id') and bom_item.fg_reference_id:
                    fg_ref_items = bom_creator_item_by_fg_ref.get(bom_item.fg_reference_id, [])
                    # Try to find exact match by item_code in fg_ref items
                    for fg_item in fg_ref_items:
                        if fg_item.item_code == item_code:
                            bom_creator_item = fg_item
                            break
                    # If still not found, use first item with matching fg_reference_id
                    if not bom_creator_item and fg_ref_items:
                        bom_creator_item = fg_ref_items[0]
                
                # Strategy 3: If bom_item has parent_row_no, find parent and use its fields
                if not bom_creator_item and hasattr(bom_item, 'parent_row_no') and bom_item.parent_row_no:
                    try:
                        parent_idx = int(bom_item.parent_row_no)
                        parent_item = bom_creator_item_by_idx.get(parent_idx)
                        if parent_item:
                            # For child items, we might want to use parent's fields or find child-specific item
                            # First try to find child item by matching item_code in items with same fg_reference_id
                            if hasattr(parent_item, 'fg_reference_id') and parent_item.fg_reference_id:
                                fg_ref_items = bom_creator_item_by_fg_ref.get(parent_item.fg_reference_id, [])
                                for fg_item in fg_ref_items:
                                    if fg_item.item_code == item_code:
                                        bom_creator_item = fg_item
                                        break
                            # If still not found, use parent item (child inherits from parent)
                            if not bom_creator_item:
                                bom_creator_item = parent_item
                    except (ValueError, TypeError):
                        pass
                
                if bom_creator_item:
                    # Map all custom drawing fields
                    custom_fields_to_map = [
                        'custom_drawing_no',
                        'custom_drawing_rev_no',
                        'custom_pattern_drawing_no',
                        'custom_pattern_drawing_rev_no',
                        'custom_purchase_specification_no',
                        'custom_purchase_specification_rev_no',
                    ]
                    
                    for field_name in custom_fields_to_map:
                        if hasattr(bom_creator_item, field_name) and getattr(bom_creator_item, field_name):
                            if not getattr(bom_item, field_name, None):
                                setattr(bom_item, field_name, getattr(bom_creator_item, field_name))
                                item_updated = True
                    
                    # # Check if this item is expandable (is_expandable marked)
                    # is_expandable = getattr(bom_creator_item, 'is_expandable', False)
                    
                    # if is_expandable:
                    #     # Map custom_drawing and custom_drawing_rev_no to custom_ga_drawing_no and custom_ga_drawing_rev_no
                    #     if hasattr(bom_creator_item, 'custom_drawing') and bom_creator_item.custom_drawing:
                    #         if not getattr(bom_item, 'custom_ga_drawing_no', None):
                    #             bom_item.custom_ga_drawing_no = bom_creator_item.custom_drawing
                    #             item_updated = True
                        
                    #     if hasattr(bom_creator_item, 'custom_drawing_rev_no') and bom_creator_item.custom_drawing_rev_no:
                    #         if not getattr(bom_item, 'custom_ga_drawing_rev_no', None):
                    #             bom_item.custom_ga_drawing_rev_no = bom_creator_item.custom_drawing_rev_no
                    #             item_updated = True
                
                return item_updated
            
            # Process each BOM item
            for bom_item in bom.items:
                item_code = bom_item.item_code
                if item_code:
                    if find_and_map_custom_fields(bom_item, item_code):
                        updated = True
            
            # Also process exploded_items if they exist (for multi-level BOMs)
            if hasattr(bom, 'exploded_items') and bom.exploded_items:
                for exploded_item in bom.exploded_items:
                    item_code = exploded_item.item_code
                    if item_code:
                        if find_and_map_custom_fields(exploded_item, item_code):
                            updated = True
        
        except Exception as e:
            frappe.log_error(
                "BOM Creator - Drawing Fields Mapping Failed",
                f"BOM: {bom.name}\n\n{frappe.get_traceback()}"
            )
        
        return updated
    
    @frappe.whitelist()
    def verify_custom_fields_mapping(self):
        """
        Verify that custom fields from BOM Creator items are correctly mapped to created BOMs.
        Returns a report of missing or incorrect mappings.
        """
        verification_report = {
            "bom_creator": self.name,
            "total_boms": 0,
            "verified_boms": [],
            "issues": []
        }
        
        try:
            # Get all BOMs created by this BOM Creator
            bom_list = frappe.get_all(
                "BOM",
                filters={"bom_creator": self.name, "docstatus": ["<", 2]},
                fields=["name", "item", "bom_creator_item"]
            )
            
            verification_report["total_boms"] = len(bom_list)
            
            # Build maps from BOM Creator items
            bom_creator_item_map = {}
            bom_creator_item_by_fg_ref = {}
            bom_creator_item_by_idx = {}
            
            for item in self.items:
                if item.item_code:
                    bom_creator_item_map[item.item_code] = item
                if hasattr(item, 'fg_reference_id') and item.fg_reference_id:
                    if item.fg_reference_id not in bom_creator_item_by_fg_ref:
                        bom_creator_item_by_fg_ref[item.fg_reference_id] = []
                    bom_creator_item_by_fg_ref[item.fg_reference_id].append(item)
                if hasattr(item, 'idx') and item.idx:
                    bom_creator_item_by_idx[item.idx] = item
            
            # Verify each BOM
            for bom_data in bom_list:
                try:
                    bom = frappe.get_doc("BOM", bom_data.name)
                    bom_verification = {
                        "bom_name": bom.name,
                        "bom_item": bom.item,
                        "total_items": len(bom.items),
                        "verified_items": 0,
                        "missing_fields": []
                    }
                    
                    # Verify each BOM item
                    for bom_item in bom.items:
                        item_code = bom_item.item_code
                        bom_creator_item = bom_creator_item_map.get(item_code)
                        
                        # Try alternative matching strategies
                        if not bom_creator_item:
                            if hasattr(bom_item, 'fg_reference_id') and bom_item.fg_reference_id:
                                fg_ref_items = bom_creator_item_by_fg_ref.get(bom_item.fg_reference_id, [])
                                for fg_item in fg_ref_items:
                                    if fg_item.item_code == item_code:
                                        bom_creator_item = fg_item
                                        break
                        
                        if bom_creator_item:
                            bom_verification["verified_items"] += 1
                            
                            # Check each custom field
                            custom_fields = [
                                'custom_drawing_no',
                                'custom_drawing_rev_no',
                                'custom_pattern_drawing_no',
                                'custom_pattern_drawing_rev_no',
                                'custom_purchase_specification_no',
                                'custom_purchase_specification_rev_no',
                            ]
                            
                            for field_name in custom_fields:
                                creator_value = getattr(bom_creator_item, field_name, None)
                                bom_value = getattr(bom_item, field_name, None)
                                
                                if creator_value and not bom_value:
                                    bom_verification["missing_fields"].append({
                                        "item_code": item_code,
                                        "field": field_name,
                                        "expected": creator_value,
                                        "actual": bom_value or "None"
                                    })
                        else:
                            bom_verification["missing_fields"].append({
                                "item_code": item_code,
                                "field": "bom_creator_item_match",
                                "expected": "Found in BOM Creator",
                                "actual": "Not found"
                            })
                    
                    verification_report["verified_boms"].append(bom_verification)
                    
                    if bom_verification["missing_fields"]:
                        verification_report["issues"].append({
                            "bom": bom.name,
                            "issues": bom_verification["missing_fields"]
                        })
                        
                except Exception as e:
                    verification_report["issues"].append({
                        "bom": bom_data.name,
                        "error": str(e)
                    })
            
        except Exception as e:
            frappe.log_error(
                "BOM Creator - Verification Failed",
                f"BOM Creator: {self.name}\n\n{frappe.get_traceback()}"
            )
            verification_report["error"] = str(e)
        
        return verification_report
