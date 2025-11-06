import frappe
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
                
                # 2. Map branch_abbr from sales order
                if bom.sales_order and not getattr(bom, 'branch_abbr', None):
                    try:
                        branch = frappe.get_cached_value("Sales Order", bom.sales_order, "branch")
                        if branch:
                            bom.branch = branch
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
    
    def _map_drawing_fields_to_bom_items(self, bom, bom_creator_item_ref):
        """
        Map drawing fields from BOM Creator items to BOM items.
        Returns True if any updates were made.
        """
        updated = False
        
        try:
            # Build a map of item_code to BOM Creator item row
            bom_creator_item_map = {}
            for item in self.items:
                if item.item_code:
                    bom_creator_item_map[item.item_code] = item
            
            # Process each BOM item
            for bom_item in bom.items:
                item_code = bom_item.item_code
                
                # Get corresponding BOM Creator item
                bom_creator_item = bom_creator_item_map.get(item_code)
                
                if bom_creator_item:
                    # Map custom_drawing_no to BOM item
                    if hasattr(bom_creator_item, 'custom_drawing_no') and bom_creator_item.custom_drawing_no:
                        if not bom_item.custom_drawing_no:
                            bom_item.custom_drawing_no = bom_creator_item.custom_drawing_no
                            updated = True
                    
                    if hasattr(bom_creator_item, 'custom_drawing_rev_no') and bom_creator_item.custom_drawing_rev_no:
                        if not bom_item.custom_drawing_rev_no:
                            bom_item.custom_drawing_rev_no = bom_creator_item.custom_drawing_rev_no
                            updated = True
                    
                    # Check if this item is expandable (is_expandable marked)
                    is_expandable = getattr(bom_creator_item, 'is_expandable', False)
                    
                    if is_expandable:
                        # Map custom_drawing and custom_drawing_rev_no to custom_ga_drawing_no and custom_ga_drawing_rev_no
                        if hasattr(bom_creator_item, 'custom_drawing') and bom_creator_item.custom_drawing:
                            if not bom_item.custom_ga_drawing_no:
                                bom_item.custom_ga_drawing_no = bom_creator_item.custom_drawing
                                updated = True
                        
                        if hasattr(bom_creator_item, 'custom_drawing_rev_no') and bom_creator_item.custom_drawing_rev_no:
                            if not bom_item.custom_ga_drawing_rev_no:
                                bom_item.custom_ga_drawing_rev_no = bom_creator_item.custom_drawing_rev_no
                                updated = True
                    
                    # Also map other drawing-related fields if they exist
                    drawing_fields_map = {
                        'custom_pattern_drawing_no': 'custom_pattern_drawing_no',
                        'custom_pattern_drawing_rev_no': 'custom_pattern_drawing_rev_no',
                        'custom_purchase_specification_no': 'custom_purchase_specification_no',
                        'custom_purchase_specification_rev_no': 'custom_purchase_specification_rev_no',
                    }
                    
                    for source_field, target_field in drawing_fields_map.items():
                        if hasattr(bom_creator_item, source_field) and getattr(bom_creator_item, source_field):
                            if not getattr(bom_item, target_field, None):
                                setattr(bom_item, target_field, getattr(bom_creator_item, source_field))
                                updated = True
        
        except Exception as e:
            frappe.log_error(
                "BOM Creator - Drawing Fields Mapping Failed",
                f"BOM: {bom.name}\n\n{frappe.get_traceback()}"
            )
        
        return updated
