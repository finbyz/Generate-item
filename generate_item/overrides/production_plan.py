from erpnext.manufacturing.doctype.production_plan.production_plan import ProductionPlan as _ProductionPlan
import frappe
from frappe import _
# from frappe.utils import flt
from frappe.utils import flt, nowdate, add_days, cint, comma_and, get_link_to_form
import json

class ProductionPlan(_ProductionPlan):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Run cleanup only for saved documents with po_items
        if self.name and self.docstatus < 2 and hasattr(self, 'po_items') and self.po_items:
            try:
                cleanup_all_orphaned_references(self)
            except Exception as e:
                frappe.log_error("Production Plan Init Cleanup", f"Cleanup error in __init__: {str(e)}")

    def validate(self):
        """Override validate to ensure no invalid production_plan_item references"""
        super().validate()
        if hasattr(self, 'sub_assembly_items') and self.sub_assembly_items:
            try:
                invalid_references = []
                valid_ppi_names = {po_item.name for po_item in self.po_items if getattr(po_item, "name", None)}
                for sub_item in self.sub_assembly_items:
                    ppi_name = getattr(sub_item, "production_plan_item", None)
                    if ppi_name and (not frappe.db.exists("Production Plan Item", ppi_name) or ppi_name not in valid_ppi_names):
                        invalid_references.append(ppi_name)
                if invalid_references:
                    frappe.throw(
                        _("Invalid Production Plan Item references found in sub_assembly_items: {0}").format(", ".join(invalid_references)),
                        title=_("Invalid References")
                    )
                cleanup_all_orphaned_references(self)
            except Exception as e:
                frappe.log_error("Production Plan Validation", f"Validation error in Production Plan: {str(e)}")
                frappe.throw(_("Error validating Production Plan due to invalid references: {0}").format(str(e)))

    @frappe.whitelist()
    def make_work_order(self):
        from erpnext.manufacturing.doctype.work_order.work_order import get_default_warehouse
        doc = frappe.get_all("Work Order", filters={"production_plan": self.name}, fields=["name"])
        if doc:
            frappe.throw("Work Order already exists")
        wo_list, po_list = [], []
        subcontracted_po = {}
        default_warehouses = get_default_warehouse()

        # Run cleanup before creating work orders
        if hasattr(self, 'po_items') and self.po_items:
            try:
                cleanup_all_orphaned_references(self)
            except Exception as e:
                frappe.log_error("Work Order Cleanup", f"Cleanup error in make_work_order: {str(e)}")

        self.make_work_order_for_finished_goods(wo_list, default_warehouses)
        self.make_work_order_for_subassembly_items(wo_list, subcontracted_po, default_warehouses)
        self.make_subcontracted_purchase_order(subcontracted_po, po_list)
        self.show_list_created_message("Work Order", wo_list)
        self.show_list_created_message("Purchase Order", po_list)

        if not wo_list:
            frappe.msgprint(_("No Work Orders were created"))

    @frappe.whitelist()
    def get_sub_assembly_items(self, manufacturing_type=None):
        """Override to ensure sub_assembly_items inherit custom fields from po_items"""
        super().get_sub_assembly_items(manufacturing_type)
        self._populate_subassembly_items_from_po_items()

        bom_list = []
        
        # Get BOMs from main production items
        for item in self.po_items:
            if item.bom_no and item.bom_no not in bom_list:
                bom_list.append(item.bom_no)
        

        if self.name and self.docstatus < 2 and hasattr(self, 'po_items') and self.po_items:
            try:
                cleanup_all_orphaned_references(self)
            except Exception as e:
                frappe.log_error("Subassembly Cleanup", f"Cleanup error in get_sub_assembly_items: {str(e)}")

    @frappe.whitelist()
    def get_items(self):
        """Populate branch on po_items immediately after fetching items so it shows in grid"""
        super().get_items()
        try:
            # Recalculate pending/planned qty on po_items based on existing Production Plans
            self._recalculate_pending_qty_on_po_items()
            
            # Ensure po_items BOM only from same Sales Order as the row
            self._enforce_bom_matches_sales_order_on_po_items()

            if not getattr(self, "po_items", None):
                return
            soi_names = [d.sales_order_item for d in self.po_items if getattr(d, "sales_order_item", None)]
            if not soi_names:
                return
            soi_rows = frappe.get_all(
                "Sales Order Item",
                filters={"name": ("in", soi_names)},
                fields=["name", "branch"],
            )
            soi_branch_map = {row["name"]: row.get("branch") for row in soi_rows}
            for d in self.po_items:
                if hasattr(d, "branch") and getattr(d, "sales_order_item", None):
                    if not getattr(d, "branch", None):
                        d.branch = soi_branch_map.get(d.sales_order_item)
                        
        except Exception as e:
            frappe.log_error("Production Plan Branch Populate Error", f"Error populating branch on po_items: {str(e)}")

    def _recalculate_pending_qty_on_po_items(self):
        """Set `pending_qty` and `planned_qty` on `po_items` by subtracting quantities
        already planned in other Production Plans for the same Sales Order Item line.

        Logic mirrors the earlier custom SO item computation:
        remaining_qty = (SO qty in stock UOM) - SUM(planned_qty from other plans for same SO line)
        """
        try:
            if not getattr(self, "po_items", None):
                return

            # Collect SOI names and conversion factors if available
            soi_names = [d.sales_order_item for d in self.po_items if getattr(d, "sales_order_item", None)]
            if not soi_names:
                return

            # Fetch required fields from Sales Order Item to compute base qty and conversion
            soi_rows = frappe.get_all(
                "Sales Order Item",
                filters={"name": ("in", soi_names)},
                fields=["name", "parent", "item_code", "qty", "conversion_factor"],
            )
            soi_by_name = {r["name"]: r for r in soi_rows}

            kept_rows = []
            for d in self.po_items:
                soi_name = getattr(d, "sales_order_item", None)
                if not soi_name:
                    continue
                soi = soi_by_name.get(soi_name)
                if not soi:
                    continue

                # Base qty is Sales Order qty converted to stock UOM
                original_pending_qty = flt(soi.get("qty") or 0)
                stock_pending_qty = original_pending_qty * flt(soi.get("conversion_factor") or 1)

                try:
                    previous_planned_qty = frappe.db.sql(
                        """
                        SELECT SUM(ppi.planned_qty) as total_planned
                        FROM `tabProduction Plan Item` ppi
                        INNER JOIN `tabProduction Plan` pp ON ppi.parent = pp.name
                        INNER JOIN `tabProduction Plan Sales Order` pps ON pp.name = pps.parent
                        WHERE pps.sales_order = %s
                        AND ppi.item_code = %s
                        AND ppi.sales_order_item = %s
                        AND pp.docstatus IN (0, 1)
                        AND pp.name != %s
                        """,
                        (soi.get("parent"), soi.get("item_code"), soi_name, self.name or ""),
                        as_dict=True,
                    )
                    total_planned = flt(previous_planned_qty[0].total_planned) if previous_planned_qty else 0
                except Exception:
                    total_planned = 0

                remaining_qty = stock_pending_qty - total_planned
                if remaining_qty < 0:
                    remaining_qty = 0

                # Update fields on po_item row if present
                if hasattr(d, "pending_qty"):
                    d.pending_qty = remaining_qty
                if hasattr(d, "planned_qty"):
                    d.planned_qty = remaining_qty
                if hasattr(d, "planned_qty"):
                    d.actual_qty = remaining_qty

                # Keep only items with remaining qty > 0
                if remaining_qty > 0:
                    kept_rows.append(d)

            # Replace table with only rows having pending qty
            self.po_items = kept_rows
        except Exception as e:
            frappe.log_error("Production Plan Pending Qty Error", f"Error recalculating pending qty on po_items: {str(e)}")

    def _enforce_bom_matches_sales_order_on_po_items(self):
        """For each po_items row, only keep or set BOMs that belong to the same Sales Order.

        Rules:
        - If `bom_no` is set but its BOM.sales_order != row.sales_order, clear `bom_no`.
        - If `bom_no` is not set, try selecting a BOM where:
            BOM.item == row.item_code AND BOM.sales_order == row.sales_order AND BOM.is_active == 1
          Prefer a BOM that also matches the row's custom batch ref (custom_batch_no/custom_batch_ref/batch_no) if present.
        """
        try:
            if not getattr(self, "po_items", None):
                return

            for d in self.po_items:
                row_so = getattr(d, "sales_order", None)
                row_item = getattr(d, "item_code", None)
                row_bom = getattr(d, "bom_no", None)
                row_batch = (
                    getattr(d, "custom_batch_no", None)
                    or getattr(d, "custom_batch_ref", None)
                    or getattr(d, "batch_no", None)
                )

                # Skip rows without essential context
                if not row_item or not row_so:
                    continue

                # If bom_no set, validate that it belongs to the same SO
                if row_bom:
                    try:
                        bom_so = frappe.db.get_value("BOM", row_bom, "sales_order")
                        if bom_so and bom_so != row_so:
                            d.bom_no = None
                    except Exception:
                        # If BOM not found or error, clear it
                        d.bom_no = None

                # If bom_no still empty, try to fetch a matching BOM
                if not getattr(d, "bom_no", None):
                    bom_filters = {
                        "item": row_item,
                        "sales_order": row_so,
                        "is_active": 1,
                    }
                    order_by = "modified desc"
                    # If batch context exists, try batch-specific first
                    candidate = None
                    if row_batch:
                        try:
                            candidate = frappe.get_all(
                                "BOM",
                                filters={**bom_filters, "custom_batch_no": row_batch},
                                fields=["name"],
                                order_by=order_by,
                                limit=1,
                            )
                        except Exception:
                            candidate = None
                    if not candidate:
                        try:
                            candidate = frappe.get_all(
                                "BOM",
                                filters=bom_filters,
                                fields=["name"],
                                order_by=order_by,
                                limit=1,
                            )
                        except Exception:
                            candidate = None
                    if candidate:
                        d.bom_no = candidate[0]["name"]
        except Exception as e:
            frappe.log_error("Production Plan BOM Enforcement Error", f"Error enforcing BOM by Sales Order on po_items: {str(e)}")
            

    def _populate_subassembly_items_from_po_items(self):
        """Populate subassembly items with custom fields from their parent po_items"""
        try:
            po_item_by_item_code = {po_item.item_code: po_item for po_item in self.po_items if getattr(po_item, "item_code", None)}
            po_item_by_rowname = {po_item.name: po_item for po_item in self.po_items if getattr(po_item, "name", None)}

            for sub_item in self.sub_assembly_items:
                parent_po_item = None
                ppi_name = getattr(sub_item, "production_plan_item", None)
                sub_item_name = getattr(sub_item, "name", "Unknown")

                # Log the reference being checked
                frappe.log_error(
                    "Subassembly Reference Check",
                    f"Checking sub_assembly_item {sub_item_name} with production_plan_item: {ppi_name}"
                )

                if ppi_name and ppi_name in po_item_by_rowname:
                    parent_po_item = po_item_by_rowname.get(ppi_name)
                if not parent_po_item:
                    parent_code = getattr(sub_item, "parent_item_code", None) or getattr(sub_item, "production_item", None)
                    if parent_code:
                        parent_po_item = po_item_by_item_code.get(parent_code)
                
                if parent_po_item:
                    parent_batch = (
                        getattr(parent_po_item, "custom_batch_no", None)
                    )
                    if parent_batch:
                        for field in ["custom_batch_no"]:
                            if hasattr(sub_item, field):
                                setattr(sub_item, field, parent_batch)
                        if hasattr(sub_item, "type_of_manufacturing"):
                            sub_item.type_of_manufacturing = "In House"
                    if hasattr(parent_po_item, "branch") and getattr(parent_po_item, "branch", None):
                        sub_item.branch = parent_po_item.branch
                        if hasattr(sub_item, "branch"):
                            sub_item.branch = parent_po_item.branch
                    for field in ["sales_order", "sales_order_item"]:
                        if hasattr(parent_po_item, field) and getattr(parent_po_item, field, None):
                            setattr(sub_item, field, getattr(parent_po_item, field))
                    
                    # Inherit BOM from parent production plan item
                    if hasattr(parent_po_item, "bom_no") and getattr(parent_po_item, "bom_no", None):
                        if hasattr(sub_item, "bom_no"):
                            sub_item.bom_no = parent_po_item.bom_no
                            frappe.log_error(
                                "Subassembly BOM Inheritance",
                                f"Subassembly item {sub_item_name} inherited BOM {parent_po_item.bom_no} from parent production plan item {ppi_name}"
                            )
                            
                            # Get drawing numbers from BOM Item for this sub-assembly item
                            drawing_data = self._get_drawing_numbers_from_bom_item(
                                parent_po_item.bom_no, 
                                getattr(sub_item, "production_item", None)
                            )
                            if drawing_data:
                                for field, value in drawing_data.items():
                                    if hasattr(sub_item, field) and value:
                                        setattr(sub_item, field, value)
                                        frappe.log_error(
                                            "Subassembly Drawing Data",
                                            f"Subassembly item {sub_item_name} got {field}={value} from BOM Item"
                                        )
                else:
                    frappe.log_error(
                        "Subassembly Parent Not Found",
                        f"No parent po_item found for sub_assembly_item {sub_item_name} with production_plan_item: {ppi_name}"
                    )
        except Exception as e:
            frappe.log_error("Subassembly Item Population Error", f"Error populating subassembly items from po_items: {str(e)}")

    def _get_drawing_numbers_from_bom_item(self, bom_no, item_code):
        """Helper function to get drawing numbers from BOM Item for a specific item_code
        
        Args:
            bom_no (str): BOM number to search in
            item_code (str): Item code to find in BOM Item table
            
        Returns:
            dict: Dictionary containing drawing field names and values
        """
        try:
            if not bom_no or not item_code:
                return {}
                
            # Get BOM Item details for the specific item_code in the given BOM
            bom_item = frappe.get_all(
                "BOM Item",
                filters={
                    "parent": bom_no,
                    "item_code": item_code
                },
                fields=[
                    "custom_drawing_no",
                    "custom_drawing_rev_no",
                    
                ],
                limit=1
            )
            
            if bom_item:
                drawing_data = {}
                item_data = bom_item[0]
                
                # Map the fields to their values, only including non-empty values
                field_mapping = {
                    "custom_drawing_no": item_data.get("custom_drawing_no"),
                    "custom_drawing_rev_no": item_data.get("custom_drawing_rev_no"),
                   
                }
                
                # Only include fields that have values
                for field, value in field_mapping.items():
                    if value:
                        drawing_data[field] = value
                
                frappe.log_error(
                    "BOM Item Drawing Data Retrieved",
                    f"Retrieved drawing data for item {item_code} from BOM {bom_no}: {drawing_data}"
                )
                
                return drawing_data
            else:
                frappe.log_error(
                    "BOM Item Not Found",
                    f"No BOM Item found for item_code {item_code} in BOM {bom_no}"
                )
                return {}
                
        except Exception as e:
            frappe.log_error(
                "BOM Item Drawing Data Error", 
                f"Error getting drawing data for item {item_code} from BOM {bom_no}: {str(e)}"
            )
            return {}

    def make_work_order_for_subassembly_items(self, wo_list, subcontracted_po, default_warehouses):
        """Override to ensure sub_assembly_items get correct values from Sales Order Items"""
        for row in self.sub_assembly_items:
            sub_item_name = getattr(row, "name", "Unknown")
            self._populate_subassembly_item_from_sales_order(row)
            
            if row.type_of_manufacturing == "Subcontract":
                subcontracted_po.setdefault(row.supplier, []).append(row)
                continue

            if row.type_of_manufacturing == "Material Request":
                continue

            work_order_data = {
                "wip_warehouse": default_warehouses.get("wip_warehouse"),
                "fg_warehouse": default_warehouses.get("fg_warehouse"),
                "company": self.get("company"),
            }

            if flt(row.qty) <= flt(row.ordered_qty):
                continue

            # Populate work_order_data with custom fields from sub_assembly_item
            row_batch = (
                getattr(row, "custom_batch_no", None) or
                getattr(row, "custom_batch_ref", None) or
                getattr(row, "batch_no", None)
            )
            if row_batch:
                work_order_data["custom_batch_no"] = row_batch
            if hasattr(row, "branch") and row.branch:
                work_order_data["branch"] = row.branch
            if hasattr(row, "sales_order") and row.sales_order:
                work_order_data["sales_order"] = row.sales_order
            if hasattr(row, "sales_order_item") and row.sales_order_item:
                work_order_data["sales_order_item"] = row.sales_order_item

            # Fallback to parent po_item if any fields are missing
            if (
                not all(work_order_data.get(field) for field in ["custom_batch_no", "branch"])
                and hasattr(self, "po_items") and self.po_items
            ):
                po_item_by_rowname = {getattr(d, "name", None): d for d in self.po_items if getattr(d, "name", None)}
                po_item_by_item_code = {getattr(d, "item_code", None): d for d in self.po_items if getattr(d, "item_code", None)}
                parent_po_item = None
                ppi_name = getattr(row, "production_plan_item", None)
                if ppi_name and ppi_name in po_item_by_rowname:
                    parent_po_item = po_item_by_rowname.get(ppi_name)
                if not parent_po_item:
                    parent_code = getattr(row, "parent_item_code", None) or getattr(row, "production_item", None)
                    if parent_code:
                        parent_po_item = po_item_by_item_code.get(parent_code)
                
                if parent_po_item:
                    if not work_order_data.get("custom_batch_no"):
                        parent_batch = (
                            getattr(parent_po_item, "custom_batch_no", None)
                     
                        )
                        if parent_batch:
                            work_order_data["custom_batch_no"] = parent_batch
                    for field in ["branch", "sales_order", "sales_order_item"]:
                        if not work_order_data.get(field) and hasattr(parent_po_item, field) and getattr(parent_po_item, field, None):
                            work_order_data[field] = getattr(parent_po_item, field)
                else:
                    frappe.log_error(
                        "Work Order Parent Not Found",
                        f"No parent po_item found for sub_assembly_item {sub_item_name} with production_plan_item: {ppi_name}, "
                        f"production_item: {getattr(row, 'production_item', None)}, parent_item_code: {getattr(row, 'parent_item_code', None)}",
                    )

            # Log if critical fields are still missing
            if not work_order_data.get("custom_batch_no") or not work_order_data.get("branch"):
                frappe.log_error(
                    "Work Order Data Missing Fields",
                    f"Missing fields in work_order_data for sub_assembly_item {sub_item_name}: "
                    f"custom_batch_no={work_order_data.get('custom_batch_no')}, branch={work_order_data.get('branch')}"
                )

            # Clear invalid production_plan_item reference
            try:
                if getattr(row, "production_plan_item", None):
                    if not frappe.db.exists("Production Plan Item", row.production_plan_item):
                        frappe.log_error(
                            "Orphaned Production Plan Item Reference",
                            f"Orphaned Production Plan Item reference found in sub_assembly_item {sub_item_name}: {row.production_plan_item}. Clearing reference."
                        )
                        row.production_plan_item = None
                        if row.get("name"):
                            frappe.db.set_value(row.doctype, row.name, "production_plan_item", None)
                            frappe.db.commit()
            except Exception as e:
                frappe.log_error("Production Plan Item Check Error", f"Error checking Production Plan Item existence for {sub_item_name}: {str(e)}")
                row.production_plan_item = None

            self.safe_prepare_data_for_sub_assembly_items(row, work_order_data)

            if work_order_data.get("qty") <= 0:
                continue

            work_order = self.create_work_order(work_order_data)
            if work_order:
                # Ensure custom fields are actually set on the created Work Order
                try:
                    wo_doc = frappe.get_doc("Work Order", work_order)
                    updates = {}
                    # Branch
                    if work_order_data.get("branch") and hasattr(wo_doc, "branch") and not getattr(wo_doc, "branch", None):
                        updates["branch"] = work_order_data.get("branch")
                    # Batch: prefer custom_batch_no; fallback to batch_no field if present
                    custom_batch = work_order_data.get("custom_batch_no")
                    if custom_batch:
                        if hasattr(wo_doc, "custom_batch_no") and not getattr(wo_doc, "custom_batch_no", None):
                            updates["custom_batch_no"] = custom_batch
                        elif hasattr(wo_doc, "batch_no") and not getattr(wo_doc, "batch_no", None):
                            updates["batch_no"] = custom_batch
                    if updates:
                        wo_doc.db_set(updates, update_modified=False)

                    # Also backfill required_items child rows, if custom fields exist
                    try:
                        branch_value = work_order_data.get("branch")
                        for req in getattr(wo_doc, "required_items", []) or []:
                            child_updates = {}
                            if branch_value and hasattr(req, "branch") and not getattr(req, "branch", None):
                                child_updates["branch"] = branch_value
                            if custom_batch:
                                if hasattr(req, "custom_batch_no") and not getattr(req, "custom_batch_no", None):
                                    child_updates["custom_batch_no"] = custom_batch
                                elif hasattr(req, "batch_no") and not getattr(req, "batch_no", None):
                                    child_updates["batch_no"] = custom_batch
                            if child_updates:
                                req.db_set(child_updates, update_modified=False)
                    except Exception as ce:
                        frappe.log_error(
                            "Work Order Required Items Backfill Error",
                            f"Unable to backfill required_items for Work Order {work_order}: {str(ce)}"
                        )
                except Exception as e:
                    frappe.log_error("Work Order Backfill Error", f"Unable to backfill branch/batch on Work Order {work_order}: {str(e)}")
                wo_list.append(work_order)

    def safe_prepare_data_for_sub_assembly_items(self, row, work_order_data):
        try:
            sub_item_name = getattr(row, "name", "Unknown")
            production_plan_item = None
            if getattr(row, "production_plan_item", None):
                production_plan_item = safe_get_production_plan_item(row.production_plan_item, context=f"safe_prepare_data_for_sub_assembly_items ({sub_item_name})")
                if not production_plan_item:
                    row.production_plan_item = None
                    if row.get("name"):
                        frappe.db.set_value(row.doctype, row.name, "production_plan_item", None)
                        frappe.db.commit()
            
            if not production_plan_item and hasattr(row, 'production_item'):
                for po_item in self.po_items:
                    if getattr(po_item, 'item_code') == getattr(row, 'production_item'):
                        production_plan_item = po_item
                        break
            
            # Get BOM from subassembly item, fallback to parent production plan item
            bom_no = getattr(row, "bom_no", None)
            if not bom_no and production_plan_item:
                bom_no = getattr(production_plan_item, "bom_no", None)
                if bom_no:
                    frappe.log_error(
                        "Subassembly Work Order BOM",
                        f"Subassembly work order for {sub_item_name} using BOM {bom_no} from parent production plan item"
                    )
            
            work_order_data.update({
                "production_item": getattr(row, "production_item", None),
                "qty": flt(row.qty) - flt(row.ordered_qty),
                "description": getattr(row, "description", ""),
                "bom_no": bom_no,
                "stock_uom": getattr(row, "stock_uom", None),
                "production_plan": self.name,
                "production_plan_sub_assembly_item": getattr(row, "name", None),
            })
            
            if production_plan_item:
                work_order_data.update({
                    "sales_order": getattr(production_plan_item, "sales_order", None),
                    "sales_order_item": getattr(production_plan_item, "sales_order_item", None),
                    "project": getattr(production_plan_item, "project", None),
                    "production_plan_item": getattr(production_plan_item, "name", None),
                })
            
            if not work_order_data.get("wip_warehouse"):
                work_order_data["wip_warehouse"] = getattr(row, "wip_warehouse", None)
            if not work_order_data.get("fg_warehouse"):
                work_order_data["fg_warehouse"] = getattr(row, "fg_warehouse", None)
                
        except Exception as e:
            frappe.log_error("Safe Prepare Data Error", f"Error in safe_prepare_data_for_sub_assembly_items for {sub_item_name}: {str(e)}")
            # Get BOM from subassembly item as fallback
            bom_no = getattr(row, "bom_no", None)
            work_order_data.update({
                "production_item": getattr(row, "production_item", None),
                "qty": flt(row.qty) - flt(row.ordered_qty),
                "description": getattr(row, "description", ""),
                "bom_no": bom_no,
                "stock_uom": getattr(row, "stock_uom", None),
                "production_plan": self.name,
                "production_plan_sub_assembly_item": getattr(row, "name", None),
            })
            
            
    

    def _populate_subassembly_item_from_sales_order(self, row):
        try:
            sub_item_name = getattr(row, "name", "Unknown")
            production_plan_item = None
            ppi_name = getattr(row, "production_plan_item", None)
            if ppi_name:
                production_plan_item = safe_get_production_plan_item(ppi_name, context=f"populate_subassembly_item_from_sales_order ({sub_item_name})")
                if not production_plan_item:
                    frappe.log_error(
                        "Missing Production Plan Item",
                        f"Production Plan Item {ppi_name} not found for sub_assembly_item {sub_item_name}. Clearing reference."
                    )
                    row.production_plan_item = None
                    if row.get("name"):
                        frappe.db.set_value(row.doctype, row.name, "production_plan_item", None)
                        frappe.db.commit()

            if not production_plan_item and hasattr(row, 'production_item') and row.production_item:
                pp_items = frappe.get_all(
                    "Production Plan Item",
                    filters={"parent": self.name, "item_code": row.production_item},
                    fields=["name", "sales_order", "sales_order_item"],
                    limit=1
                )
                if pp_items:
                    production_plan_item = frappe.get_doc("Production Plan Item", pp_items[0].name)

            if not production_plan_item:
                frappe.log_error(
                    "Production Plan Item Not Found",
                    f"No Production Plan Item found for sub_assembly_item {sub_item_name} with production_item: {getattr(row, 'production_item', None)}"
                )
                return

            sales_order = getattr(production_plan_item, "sales_order", None)
            sales_order_item = getattr(production_plan_item, "sales_order_item", None)
            item_code = getattr(production_plan_item, "item_code", None)

            if not sales_order:
                return

            soi_filters = {"parent": sales_order}
            if sales_order_item:
                soi_filters["name"] = sales_order_item
            elif item_code:
                soi_filters["item_code"] = item_code

            soi = frappe.get_all(
                "Sales Order Item",
                filters=soi_filters,
                fields=["name", "custom_batch_no", "bom_no", "idx", "branch"],
                order_by="idx asc",
                limit=1,
            )

            if not soi:
                return

            soi = soi[0]

            if hasattr(row, 'custom_batch_no'):
                row.custom_batch_no = soi.get("custom_batch_no") or None
            if hasattr(row, 'branch'):
                row.branch = soi.get("branch") or None

        except Exception as e:
            frappe.log_error("Subassembly Item Population Error", f"Error populating subassembly item {sub_item_name} from sales order: {str(e)}")
    
    def get_items_for_material_requests(self, warehouses=None):
        """Override the original method to include custom_drawing_no from sub-assembly BOM"""
        items = super().get_items_for_material_requests(warehouses)
        
        # Get all BOMs used in this production plan
        bom_list = self.get_all_boms_in_production_plan()
        
        # Add custom_drawing_no to each item from sub-assembly BOM
        for item in items:
            custom_drawing_no = self.get_custom_drawing_no_from_bom_list(item.get('item_code'), bom_list)
            if custom_drawing_no:
                item['custom_drawing_no'] = custom_drawing_no
        
        return items



    
    
    def get_all_boms_in_production_plan(self):
        """Get all BOMs used in both main items and sub-assembly items"""
        bom_list = []
        
        # Get BOMs from main production items
        for item in self.po_items:
            if item.bom_no and item.bom_no not in bom_list:
                bom_list.append(item.bom_no)
        
        # Get BOMs from sub-assembly items
        for sub_item in self.sub_assembly_items:
            if sub_item.bom_no and sub_item.bom_no not in bom_list:
                bom_list.append(sub_item.bom_no)
                
        return bom_list
    
    def get_custom_drawing_no_from_bom_list(self, item_code, bom_list):
        """Get custom_drawing_no from any BOM in the production plan"""
        if not item_code or not bom_list:
            return None
            
        # Search for custom_drawing_no in all BOMs used in this production plan
        custom_drawing_no = frappe.db.sql("""
            SELECT bi.custom_drawing_no
            FROM `tabBOM Item` bi
            WHERE bi.item_code = %s 
            AND bi.parent IN ({bom_list})
            AND bi.custom_drawing_no IS NOT NULL
            AND bi.custom_drawing_no != ''
            LIMIT 1
        """.format(bom_list=','.join(['%s'] * len(bom_list))), 
        [item_code] + bom_list, as_dict=True)
        
        if custom_drawing_no:
            return custom_drawing_no[0].custom_drawing_no
            
        return None
    
    @frappe.whitelist()
    def make_material_request(self):
        """Create Material Requests with custom fields from assembly BOM items.
        
        Flow:
        1. For each raw material in mr_items, find which assembly BOM contains it
        2. Copy custom fields from that BOM item to the Material Request item
        3. Group MRs by Sales Order, MR Type, and Customer
        """
        from frappe import _, msgprint
        from frappe.utils import add_days, nowdate, cint, comma_and, get_link_to_form
        
        material_request_list = []
        material_request_map = {}

        for item in self.mr_items:
            if not getattr(item, "item_code", None):
                continue
                
            item_doc = frappe.get_cached_doc("Item", item.item_code)
            material_request_type = item.material_request_type or item_doc.default_material_request_type

            # Get customer from Sales Order if available
            customer = ""
            if getattr(item, "sales_order", None):
                try:
                    customer = frappe.db.get_value("Sales Order", item.sales_order, "customer") or ""
                except Exception:
                    customer = ""
            if not customer:
                customer = getattr(item_doc, "customer", "") or ""

            # Group by Sales Order:MR Type:Customer
            key = f"{item.sales_order}:{material_request_type}:{customer}"
            schedule_date = item.schedule_date or add_days(nowdate(), cint(getattr(item_doc, "lead_time_days", 0)))

            if key not in material_request_map:
                mr = frappe.new_doc("Material Request")
                mr.update({
                    "transaction_date": nowdate(),
                    "status": "Draft",
                    "company": self.company,
                    "material_request_type": material_request_type,
                    "customer": customer,
                })
                material_request_map[key] = mr
                material_request_list.append(mr)
            else:
                mr = material_request_map[key]

            # Prepare base MR item data
            mr_item_data = {
                "item_code": item.item_code,
                "from_warehouse": item.from_warehouse if material_request_type == "Material Transfer" else None,
                "qty": item.quantity,
                "schedule_date": schedule_date,
                "warehouse": item.warehouse,
                "sales_order": item.sales_order,
                "production_plan": self.name,
                "material_request_plan_item": item.name,
                "project": frappe.db.get_value("Sales Order", item.sales_order, "project") if item.sales_order else None,
            }

            # Find BOM and get custom fields for this MR item
            bom_no, custom_fields = self._get_bom_custom_fields_for_mr_item(item.item_code)
            
            if bom_no:
                mr_item_data["bom_no"] = bom_no
                frappe.log_error(
                    "MR Item BOM Set",
                    f"MR Item {item.item_code} got BOM: {bom_no}"
                )
                
            # Log what we found before appending
            frappe.log_error(
                "MR Item Before Append",
                f"Item {item.item_code}: BOM={bom_no}, Custom Fields={custom_fields}"
            )
                
            # Add custom fields to mr_item_data dictionary
            if custom_fields:
                for field_name, field_value in custom_fields.items():
                    if field_value:  # Only set non-empty values
                        mr_item_data[field_name] = field_value

            # Append the item - this returns the row object
            mr_item_row = mr.append("items", mr_item_data)
            
            # CRITICAL: Also set custom fields directly on the appended row object
            # This ensures they're set even if mr_item_data didn't work
            if bom_no and hasattr(mr_item_row, 'bom_no'):
                mr_item_row.bom_no = bom_no
                
            if custom_fields:
                for field_name, field_value in custom_fields.items():
                    if field_value and hasattr(mr_item_row, field_name):
                        setattr(mr_item_row, field_name, field_value)
                        frappe.log_error(
                            "MR Item Row Field Set",
                            f"Set {field_name}={field_value} on MR item row for {item.item_code}"
                        )

        # Save and submit Material Requests
        for material_request in material_request_list:
            material_request.flags.ignore_permissions = 1
            material_request.run_method("set_missing_values")
            
            # Log MR items before save to verify fields are set
            for idx, mr_item in enumerate(material_request.items):
                frappe.log_error(
                    "MR Item Before Save",
                    f"Item {idx}: {mr_item.item_code}, BOM: {getattr(mr_item, 'bom_no', 'NOT SET')}, "
                    f"Drawing: {getattr(mr_item, 'custom_drawing_no', 'NOT SET')}, "
                    f"Pattern: {getattr(mr_item, 'custom_pattern_drawing_no', 'NOT SET')}"
                )
            
            material_request.save()
            
            # After save, verify and update if needed
            for mr_item in material_request.items:
                if getattr(mr_item, 'item_code', None):
                    # Re-fetch custom fields for this item
                    bom_no, custom_fields = self._get_bom_custom_fields_for_mr_item(mr_item.item_code)
                    
                    # Check if fields need to be set via db_set
                    needs_update = False
                    updates = {}
                    
                    if bom_no and not getattr(mr_item, 'bom_no', None):
                        updates['bom_no'] = bom_no
                        needs_update = True
                    
                    if custom_fields:
                        for field_name, field_value in custom_fields.items():
                            if field_value and not getattr(mr_item, field_name, None):
                                updates[field_name] = field_value
                                needs_update = True
                    
                    if needs_update:
                        frappe.log_error(
                            "MR Item Post-Save Update",
                            f"Updating MR item {mr_item.name} with: {updates}"
                        )
                        mr_item.db_set(updates, update_modified=False)
            
            if self.get("submit_material_request"):
                material_request.submit()

        frappe.flags.mute_messages = False
        
        if material_request_list:
            links = [get_link_to_form("Material Request", m.name) for m in material_request_list]
            msgprint(_("{0} created").format(comma_and(links)))
        else:
            msgprint(_("No material request created"))

    def _get_bom_custom_fields_for_mr_item(self, item_code):
        """Get BOM and custom fields for a specific MR item using the working pattern from work_order.py.
        
        Returns: (bom_no, custom_fields_dict)
        """
        # Get all assembly BOMs (from po_items and sub_assembly_items)
        assembly_boms = set()
        
        # Add BOMs from po_items (main assembly items)
        for po_item in self.po_items:
            if hasattr(po_item, 'bom_no') and po_item.bom_no:
                assembly_boms.add(po_item.bom_no)
        
        # Add BOMs from sub_assembly_items
        for sub_assy in self.sub_assembly_items:
            if hasattr(sub_assy, 'bom_no') and sub_assy.bom_no:
                assembly_boms.add(sub_assy.bom_no)
        
        frappe.log_error(
            "BOM Search Start",
            f"Searching for item {item_code} in BOMs: {list(assembly_boms)}"
        )
        
        # Check each BOM to find the item and get its custom fields
        for bom_no in assembly_boms:
            try:
                # Get BOM document to access items table
                bom_doc = frappe.get_doc("BOM", bom_no)
                
                # Create mapping of item_code to bom_item (same pattern as work_order.py)
                bom_items_map = {d.item_code: d for d in (bom_doc.items or []) if getattr(d, 'item_code', None)}
                
                frappe.log_error(
                    "BOM Items Map",
                    f"BOM {bom_no} has items: {list(bom_items_map.keys())}"
                )
                
                # Find the item in BOM items map
                bom_item = bom_items_map.get(item_code)
                if bom_item:
                    custom_fields = {}
                    
                    # Get custom fields using getattr (same pattern as work_order.py)
                    custom_fields['custom_drawing_no'] = getattr(bom_item, 'custom_drawing_no', None)
                    custom_fields['custom_drawing_rev_no'] = getattr(bom_item, 'custom_drawing_rev_no', None)
                    custom_fields['custom_pattern_drawing_no'] = getattr(bom_item, 'custom_pattern_drawing_no', None)
                    custom_fields['custom_pattern_drawing_rev_no'] = getattr(bom_item, 'custom_pattern_drawing_rev_no', None)
                    custom_fields['custom_purchase_specification_no'] = getattr(bom_item, 'custom_purchase_specification_no', None)
                    custom_fields['custom_purchase_specification_rev_no'] = getattr(bom_item, 'custom_purchase_specification_rev_no', None)
                    
                    # Filter out None values
                    custom_fields = {k: v for k, v in custom_fields.items() if v is not None}
                    
                    # Log the BOM item details for debugging
                    frappe.log_error(
                        "BOM Item Found",
                        f"BOM {bom_no}, Item {item_code}: "
                        f"drawing_no={getattr(bom_item, 'custom_drawing_no', 'None')}, "
                        f"pattern_no={getattr(bom_item, 'custom_pattern_drawing_no', 'None')}, "
                        f"All fields: {custom_fields}"
                    )
                    
                    # Return BOM and custom fields (even if empty)
                    return bom_no, custom_fields
                        
            except Exception as e:
                frappe.log_error(
                    "BOM Item Check Error",
                    f"Error checking item {item_code} in BOM {bom_no}: {str(e)}"
                )
                continue
        
        # No BOM found for this item
        frappe.log_error(
            "BOM Not Found",
            f"Item {item_code} not found in any assembly BOM. Searched BOMs: {list(assembly_boms)}"
        )
        return None, {}

@frappe.whitelist()
def get_items_for_material_requests_patched(doc, warehouses=None, get_parent_warehouse_data=None):
    """Hooks-based override: enrich MR plan rows with bom_no and custom_drawing_no.

    This is referenced in hooks.py override_whitelisted_methods so it persists across restarts.
    """
    # Import core only here to avoid circulars at app import time
    from erpnext.manufacturing.doctype.production_plan.production_plan import (
        get_items_for_material_requests as core_get_items_for_mr,
    )

    if isinstance(doc, str):
        doc = frappe._dict(json.loads(doc))

    items = core_get_items_for_mr(doc, warehouses=warehouses, get_parent_warehouse_data=get_parent_warehouse_data)

    # Build ordered BOM list: sub-assembly first, then main items
    ordered_boms, seen = [], set()
    for sub in (doc.get("sub_assembly_items") or []):
        b = sub.get("bom_no")
        if b and b not in seen:
            seen.add(b); ordered_boms.append(b)
    for po in (doc.get("po_items") or doc.get("items") or []):
        b = po.get("bom_no")
        if b and b not in seen:
            seen.add(b); ordered_boms.append(b)

    if not ordered_boms:
        return items

    for row in items or []:
        item_code = row.get("item_code")
        if not item_code:
            continue

        bom_for_item = None
        for bom_no in ordered_boms:
            try:
                if frappe.db.exists("BOM Item", {"parent": bom_no, "item_code": item_code}):
                    bom_for_item = bom_no
                    break
            except Exception:
                continue

        if bom_for_item and not row.get("bom_no"):
            row["bom_no"] = bom_for_item

        try:
            drawing = frappe.db.get_value(
                "BOM Item",
                {"parent": (row.get("bom_no") or bom_for_item), "item_code": item_code},
                "custom_drawing_no",
            )
            if drawing:
                row["custom_drawing_no"] = drawing
        except Exception:
            pass

    return items

def safe_get_production_plan_item(production_plan_item_name, context=""):
    try:
        if not production_plan_item_name:
            return None
        if not frappe.db.exists("Production Plan Item", production_plan_item_name):
            frappe.log_error(
                "Missing Production Plan Item",
                f"Production Plan Item {production_plan_item_name} not found in context: {context}"
            )
            return None
        return frappe.get_doc("Production Plan Item", production_plan_item_name)
    except frappe.DoesNotExistError:
        frappe.log_error(
            "Production Plan Item Does Not Exist",
            f"Production Plan Item {production_plan_item_name} does not exist in context: {context}"
        )
        return None
    except Exception as e:
        frappe.log_error(
            "Production Plan Item Fetch Error",
            f"Error fetching Production Plan Item {production_plan_item_name} in context {context}: {str(e)}"
        )
        return None

def cleanup_all_orphaned_references(production_plan):
    try:
        valid_ppi_names = {getattr(po, 'name', None) for po in production_plan.po_items if getattr(po, 'name', None)}
        
        if hasattr(production_plan, 'sub_assembly_items') and production_plan.sub_assembly_items:
            for sub_item in production_plan.sub_assembly_items:
                sub_item_name = getattr(sub_item, "name", "Unknown")
                ppi_name = getattr(sub_item, "production_plan_item", None)
                if ppi_name and (not frappe.db.exists("Production Plan Item", ppi_name) or ppi_name not in valid_ppi_names):
                   
                    sub_item.production_plan_item = None
                    if sub_item.get("name"):
                        frappe.db.set_value(sub_item.doctype, sub_item.name, "production_plan_item", None)
                        frappe.db.commit()
        
        if hasattr(production_plan, 'mr_items') and production_plan.mr_items:
            for mr_item in production_plan.mr_items:
                mr_item_name = getattr(mr_item, "name", "Unknown")
                ppi_name = getattr(mr_item, "production_plan_item", None)
                if ppi_name and not frappe.db.exists("Production Plan Item", ppi_name):
                    frappe.log_error(
                        "Cleanup Orphaned MR Item",
                        f"Clearing orphaned Production Plan Item reference {ppi_name} in mr_item {mr_item_name}"
                    )
                    mr_item.production_plan_item = None
                    if mr_item.get("name"):
                        frappe.db.set_value(mr_item.doctype, mr_item.name, "production_plan_item", None)
                        frappe.db.commit()
        
        frappe.log_error("Production Plan Cleanup", "Completed comprehensive cleanup of orphaned references")
        
    except Exception as e:
        frappe.log_error("Production Plan Cleanup Error", f"Error in comprehensive cleanup: {str(e)}")

# Ensure the standard button path enriches MR items with BOM and drawing
try:
    import erpnext.manufacturing.doctype.production_plan.production_plan as core_pp

    _core_get_mr_items = getattr(core_pp, "get_items_for_material_requests", None)

    def _pp_ordered_boms(doc):
        ordered, seen = [], set()
        for sub in (doc.get("sub_assembly_items") or []):
            b = sub.get("bom_no")
            if b and b not in seen:
                seen.add(b); ordered.append(b)
        for po in (doc.get("po_items") or doc.get("items") or []):
            b = po.get("bom_no")
            if b and b not in seen:
                seen.add(b); ordered.append(b)
        return ordered

    @frappe.whitelist()
    def patched_get_items_for_material_requests(doc, warehouses=None, get_parent_warehouse_data=None):
        # doc may be JSON string
        if isinstance(doc, str):
            import json as _json
            doc = frappe._dict(_json.loads(doc))

        items = _core_get_mr_items(doc, warehouses=warehouses, get_parent_warehouse_data=get_parent_warehouse_data)
        try:
            ordered_boms = _pp_ordered_boms(doc)
            if not ordered_boms:
                return items
            for row in items or []:
                item_code = row.get("item_code")
                if not item_code:
                    continue
                # Resolve BOM from sub-assembly first
                bom_for_item = None
                for bom_no in ordered_boms:
                    try:
                        if frappe.db.exists("BOM Item", {"parent": bom_no, "item_code": item_code}):
                            bom_for_item = bom_no
                            break
                    except Exception:
                        continue
                if bom_for_item and not row.get("bom_no"):
                    row["bom_no"] = bom_for_item
                # Set drawing from BOM Item if present
                try:
                    drawing = frappe.db.get_value(
                        "BOM Item",
                        {"parent": (row.get("bom_no") or bom_for_item), "item_code": item_code},
                        "custom_drawing_no",
                    )
                    if drawing:
                        row["custom_drawing_no"] = drawing
                except Exception:
                    pass
        except Exception as e:
            frappe.log_error("Patched Get MR Items Error", f"Enrichment failed: {str(e)}")
        return items

    if callable(_core_get_mr_items):
        core_pp.get_items_for_material_requests = patched_get_items_for_material_requests
except Exception as e:
    frappe.log_error("Production Plan MR Patch Error", f"Unable to patch: {str(e)}")