from erpnext.manufacturing.doctype.production_plan.production_plan import ProductionPlan as _ProductionPlan
import frappe
from erpnext.manufacturing.doctype.work_order.work_order import get_item_details
from erpnext.manufacturing.doctype.bom.bom import get_children as get_bom_children
from frappe import _
from frappe.query_builder.functions import IfNull, Sum
from pypika.terms import ExistsCriterion
from frappe.utils import (
	add_days,
	ceil,
	cint,
	comma_and,
	flt,
	get_link_to_form,
	getdate,
	now_datetime,
	nowdate,
)
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

    @frappe.whitelist()
    def get_open_sales_orders(self):
        """Override to add branch filtering and populate branch in sales_orders table"""
        # Call parent method first to get open sales orders
        super().get_open_sales_orders()

        try:
            # Branch set on Production Plan acts as filter
            plan_branch = getattr(self, "branch", None)

            # Populate branch on each row and filter
            if hasattr(self, "sales_orders") and self.sales_orders:
                filtered_rows = []

                for row in list(self.sales_orders):
                    sales_order_name = getattr(row, "sales_order", None)
                    if not sales_order_name:
                        continue

                    try:
                        row_branch = frappe.db.get_value("Sales Order", sales_order_name, "branch")

                        if hasattr(row, "branch"):
                            row.branch = row_branch

                        if plan_branch:
                            if row_branch == plan_branch:
                                filtered_rows.append(row)
                        else:
                            filtered_rows.append(row)

                    except Exception as e:
                        # On lookup error, keep row only when no plan_branch filter
                        if not plan_branch:
                            filtered_rows.append(row)

                self.sales_orders = filtered_rows

        except Exception as e:
            frappe.log_error(
                "Production Plan get_open_sales_orders Error",
                f"Error applying branch filter: {str(e)}"
            )

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
                
    def get_so_items(self):
        valid_items = []
        # Check for empty table or empty rows
        if not self.get("sales_orders") or not self.get_so_mr_list("sales_order", "sales_orders"):
            frappe.throw(_("Please fill the Sales Orders table"), title=_("Sales Orders Required"))
        so_list = self.get_so_mr_list("sales_order", "sales_orders")
        bom = frappe.qb.DocType("BOM")
        so_item = frappe.qb.DocType("Sales Order Item")
        items_subquery = frappe.qb.from_(bom).select(bom.name, bom.custom_batch_no).where(bom.is_active == 1)
        items_query = (
            frappe.qb.from_(so_item)
            .select(
                so_item.parent,
                so_item.item_code,
                so_item.warehouse,
                so_item.qty,
                so_item.work_order_qty,
                so_item.delivered_qty,
                so_item.conversion_factor,
                so_item.description,
                so_item.name,
                so_item.bom_no,  # Ignored below—kept for query compatibility
                so_item.custom_batch_no,
            )
            .distinct()
            .where(
                (so_item.parent.isin(so_list))
                & (so_item.docstatus == 1)
                & (so_item.qty > so_item.work_order_qty)
            )
        )
        if self.item_code and frappe.db.exists("Item", self.item_code):
            items_query = items_query.where(so_item.item_code == self.item_code)
            
            # FIX: Build the condition properly with correct operator precedence
            bom_condition = bom.item == so_item.item_code
            
            # Add batch matching condition if applicable
            batch_condition = (bom.custom_batch_no == so_item.custom_batch_no)
            
            # Get the BOM item condition if it exists
            try:
                bom_item_cond = self.get_bom_item_condition()
                if bom_item_cond is not None:
                    # Combine: (batch_match AND bom_item_cond) OR item_match
                    items_subquery = items_subquery.where(
                        ((batch_condition & bom_item_cond) | bom_condition)
                    )
                else:
                    # Combine: batch_match OR item_match
                    items_subquery = items_subquery.where(
                        (batch_condition | bom_condition)
                    )
            except Exception:
                # Fallback: just use item match
                items_subquery = items_subquery.where(bom_condition)
        
        items_query = items_query.where(ExistsCriterion(items_subquery))
        items = items_query.run(as_dict=True)
        
        # NEW: Direct BOM lookup using item, sales_order, and batch (ignore so_item.bom_no entirely)
        for item in items:
            # Calc pending_qty first (as it's used for conditional lookup)
            item.pending_qty = (
                flt(item.qty) - max(item.work_order_qty, item.delivered_qty, 0)
            ) * item.conversion_factor
            
            if item.pending_qty > 0:
                # Direct query to BOM doctype with exact references
                bom_name = frappe.get_value(
                    "BOM",
                    {
                        "item": item.item_code,
                        "sales_order": item.parent,  # Sales Order reference
                        "custom_batch_no": item.custom_batch_no,  # Batch reference
                        "is_active": 1,
                        "docstatus": 1  # Remove if BOMs are draft (docstatus=0)
                    },
                    "name"
                )
                if not bom_name:
                    continue
                item['bom_no'] = bom_name
                valid_items.append(item)
                
        
        # Existing packed items logic (unchanged, but add similar BOM resolution if needed)
        pi = frappe.qb.DocType("Packed Item")
        packed_items_query = (
            frappe.qb.from_(so_item)
            .from_(pi)
            .select(
                pi.parent,
                pi.item_code,
                pi.warehouse.as_("warehouse"),
                (((so_item.qty - so_item.work_order_qty) * pi.qty) / so_item.qty).as_("pending_qty"),
                pi.parent_item,
                pi.description,
                so_item.name,
                so_item.custom_batch_no,
            )
            .distinct()
            .where(
                (so_item.parent == pi.parent)
                & (so_item.docstatus == 1)
                & (pi.parent_item == so_item.item_code)
                & (so_item.parent.isin(so_list))
                & (so_item.qty > so_item.work_order_qty)
                & (
                    ExistsCriterion(
                        frappe.qb.from_(bom)
                        .select(bom.name)
                        .where((bom.item == pi.item_code) & (bom.is_active == 1))
                    )
                )
            )
        )
        if self.item_code:
            packed_items_query = packed_items_query.where(so_item.item_code == self.item_code)
        packed_items = packed_items_query.run(as_dict=True)
        
        # NEW: Direct BOM lookup for packed_items (mirroring above)
        valid_packed_items = []
        for packed_item in packed_items:
            if packed_item.get('pending_qty', 0) > 0:
                bom_name = frappe.get_value(
                    "BOM",
                    {
                        "item": packed_item.item_code,  # Use packed item's code
                        "sales_order": packed_item.parent,  # Sales Order
                        "custom_batch_no": packed_item.custom_batch_no,  # Batch from SO item
                        "is_active": 1,
                        "docstatus": 1
                    },
                    "name"
                )

                if not bom_name:
                    continue


                if bom_name:
                    packed_item['bom_no'] = bom_name
                    valid_packed_items.append(packed_item)
                else:
                    packed_item['bom_no'] = ""
                    frappe.msgprint(
                        _("No active BOM found for Packed Item '{0}' in Sales Order '{1}' (Batch: '{2}'). Added without BOM.")
                        .format(packed_item.item_code, packed_item.parent, packed_item.custom_batch_no or "N/A")
                    )
        
        self.add_items(valid_items + valid_packed_items)
        self.calculate_total_planned_qty()                        
        
    def add_items(self, items):
        refs = {}
        for data in items:
            if not data.pending_qty:
                continue
            item_details = get_item_details(data.item_code, throw=False)
            
            # UPDATED: Use pre-resolved bom_no from get_so_items (no fallback or SO item check)
            bom_no = data.get('bom_no') or ""  # Direct from data—empty if no BOM found
            
            if self.combine_items:
                if bom_no in refs:
                    refs[bom_no]["so_details"].append(
                        {"sales_order": data.parent, "sales_order_item": data.name, "qty": data.pending_qty}
                    )
                    refs[bom_no]["qty"] += data.pending_qty
                    continue
                else:
                    refs[bom_no] = {
                        "qty": data.pending_qty,
                        "po_item_ref": data.name,
                        "so_details": [],
                    }
                    refs[bom_no]["so_details"].append(
                        {"sales_order": data.parent, "sales_order_item": data.name, "qty": data.pending_qty}
                    )
            
            # Append to po_items using the resolved bom_no
            pi = self.append(
                "po_items",
                {
                    "warehouse": data.warehouse,
                    "item_code": data.item_code,
                    "description": data.description or item_details.description,
                    "stock_uom": item_details and item_details.stock_uom or "",
                    "bom_no": bom_no,  # Now directly from lookup
                    "planned_qty": data.pending_qty,
                    "pending_qty": data.pending_qty,
                    "planned_start_date": now_datetime(),
                    "product_bundle_item": data.parent_item,
                },
            )
            pi._set_defaults()
            if self.get_items_from == "Sales Order":
                pi.sales_order = data.parent
                pi.sales_order_item = data.name
                pi.description = data.description
                pi.custom_batch_no = data.get("custom_batch_no")
            elif self.get_items_from == "Material Request":
                pi.material_request = data.parent
                pi.material_request_item = data.name
                pi.description = data.description
        
        if refs:
            for po_item in self.po_items:
                po_item.planned_qty = refs[po_item.bom_no]["qty"]
                po_item.pending_qty = refs[po_item.bom_no]["qty"]
                po_item.sales_order = ""
            self.add_pp_ref(refs)

    def get_mr_items(self):
        # Check for empty table or empty rows
        if not self.get("material_requests") or not self.get_so_mr_list(
            "material_request", "material_requests"
        ):
            frappe.throw(_("Please fill the Material Requests table"), title=_("Material Requests Required"))

        mr_list = self.get_so_mr_list("material_request", "material_requests")

        bom = frappe.qb.DocType("BOM")
        mr_item = frappe.qb.DocType("Material Request Item")

        items_query = (
            frappe.qb.from_(mr_item)
            .select(
                mr_item.parent,
                mr_item.name,
                mr_item.item_code,
                mr_item.warehouse,
                mr_item.description,
                mr_item.bom_no,
                ((mr_item.qty - mr_item.ordered_qty) * mr_item.conversion_factor).as_("pending_qty"),
            )
            .distinct()
            .where(
                (mr_item.parent.isin(mr_list))
                & (mr_item.docstatus == 1)
                & (mr_item.qty > mr_item.ordered_qty)
                & (
                    ExistsCriterion(
                        frappe.qb.from_(bom)
                        .select(bom.name)
                        .where((bom.item == mr_item.item_code) & (bom.is_active == 1))
                    )
                )
            )
        )

        if self.item_code:
            items_query = items_query.where(mr_item.item_code == self.item_code)

        items = items_query.run(as_dict=True)

        self.add_items(items)
        self.calculate_total_planned_qty()


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

    def make_work_order_for_finished_goods(self, wo_list, default_warehouses):
        """Override to add naming series for finished goods work orders"""
        
        # Get naming series mapping
        series_mapping = self._get_naming_series_mapping()
        work_order_naming_series = series_mapping.get('work_order_fg', 'WOFS.YY.####')
        
        frappe.log_error(
            "Work Order Naming Series - Finished Goods",
            f"Using naming_series={work_order_naming_series} for finished goods work orders"
        )
        
        # --- Start Re-implementation of Core Logic ---
        # We re-implement this to inject naming series BEFORE creation
        
        items_data = self.get_production_items()

        # Helper to match core logic
        def set_default_warehouses_local(row, default_warehouses):
            for field in ["wip_warehouse", "fg_warehouse"]:
                if not row.get(field):
                    row[field] = default_warehouses.get(field)

        for _key, item in items_data.items():
            if self.sub_assembly_items:
                item["use_multi_level_bom"] = 0

            set_default_warehouses_local(item, default_warehouses)
            
            # --- Custom Logic Injection ---
            
            # 1. Set Naming Series
            item["naming_series"] = work_order_naming_series
            
            # 2. Set Branch (try to get from po_items if not on header)
            branch_value = getattr(self, "branch", None)
            if not branch_value and getattr(self, "po_items", None):
                try:
                    # Try to find matching po_item for this item
                    po_item_match = next((pi for pi in self.po_items if pi.item_code == item.get("production_item") and pi.warehouse == item.get("fg_warehouse")), None)
                    if po_item_match and getattr(po_item_match, "branch", None):
                         branch_value = po_item_match.branch
                    
                    if not branch_value:
                         # Fallback to any branch found
                         branch_value = next((pi.branch for pi in self.po_items if getattr(pi, "branch", None)), None)
                except Exception:
                    branch_value = None
            
            if branch_value:
                item["branch"] = branch_value
                
            # 3. Set Custom Batch No
            # The item dict here is constructed from po_items in get_production_items
            # Check if custom_batch_no is available on the po_item source
            # We can try to look it up again from po_items if missing
            if not item.get("custom_batch_no"):
                 # Find original po_item
                 po_item_ref = item.get("production_plan_item")
                 if po_item_ref:
                     po_source = next((pi for pi in self.po_items if pi.name == po_item_ref), None)
                     if po_source:
                         if getattr(po_source, "custom_batch_no", None):
                             item["custom_batch_no"] = po_source.custom_batch_no
                         if getattr(po_source, "branch", None) and not item.get("branch"):
                             item["branch"] = po_source.branch

            # 4. Set GA Drawing fields (if available on po_item)
            # Similar lookup
            if not item.get("custom_ga_drawing_no") or not item.get("custom_ga_drawing_rev_no"):
                po_item_ref = item.get("production_plan_item")
                if po_item_ref:
                    po_source = next((pi for pi in self.po_items if pi.name == po_item_ref), None)
                    if po_source:
                         if getattr(po_source, "custom_drawing_no", None):
                             item["custom_ga_drawing_no"] = po_source.custom_drawing_no
                         if getattr(po_source, "custom_drawing_rev_no", None):
                             item["custom_ga_drawing_rev_no"] = po_source.custom_drawing_rev_no

            # --- End Custom Logic Injection ---

            work_order = self.create_work_order(item)
            if work_order:
                wo_list.append(work_order)
                
                # Double check naming series on created doc
                try:
                    wo_doc = frappe.get_doc("Work Order", work_order)
                    if wo_doc.naming_series != work_order_naming_series:
                         # This shouldn't happen now, but as a safety net
                         wo_doc.db_set("naming_series", work_order_naming_series, update_modified=False)
                         frappe.log_error("Work Order Naming Series Logic Failed", f"Had to force update naming series for {work_order}")
                         
                    # Backfill required_items child table fields
                    updates_needed = False
                    for req in wo_doc.required_items:
                        req_updates = {}
                        if item.get("branch") and not req.branch:
                            req_updates["branch"] = item["branch"]
                        if item.get("custom_batch_no") and not req.custom_batch_no:
                            req_updates["custom_batch_no"] = item["custom_batch_no"]
                        
                        if req_updates:
                            req.db_set(req_updates, update_modified=False)

                except Exception as e:
                     frappe.log_error("Work Order Post-Create Check Error", str(e))      


    @frappe.whitelist()
    def get_sub_assembly_items(self, manufacturing_type=None):
        "Fetch sub assembly items and optionally combine them."
        self.sub_assembly_items = []
        sub_assembly_items_store = []  # temporary store to process all subassembly items
        bin_details = frappe._dict()

        for row in self.po_items:
            if self.skip_available_sub_assembly_item and not self.sub_assembly_warehouse:
                frappe.throw(_("Row #{0}: Please select the Sub Assembly Warehouse").format(row.idx))

            if not row.item_code:
                frappe.throw(_("Row #{0}: Please select Item Code in Assembly Items").format(row.idx))

            if not row.bom_no:
                frappe.throw(_("Row #{0}: Please select the BOM No in Assembly Items").format(row.idx))

            bom_data = []

            get_sub_assembly_items(
                [item.production_item for item in sub_assembly_items_store],
                bin_details,
                row.bom_no,
                bom_data,
                row.planned_qty,
                self.company,
                warehouse=self.sub_assembly_warehouse,
                skip_available_sub_assembly_item=self.skip_available_sub_assembly_item,
            )
            self.set_sub_assembly_items_based_on_level(row, bom_data, manufacturing_type)
            sub_assembly_items_store.extend(bom_data)

        if not sub_assembly_items_store and self.skip_available_sub_assembly_item:
            message = (
                _(
                    "As there are sufficient Sub Assembly Items, Work Order is not required for Warehouse {0}."
                ).format(self.sub_assembly_warehouse)
                + "<br><br>"
            )
            message += _(
                "If you still want to proceed, please disable 'Skip Available Sub Assembly Items' checkbox."
            )

            frappe.msgprint(message, title=_("Note"))

        if self.combine_sub_items:
            # Combine subassembly items
            sub_assembly_items_store = self.combine_subassembly_items(sub_assembly_items_store)

        for idx, row in enumerate(sub_assembly_items_store):
            row.idx = idx + 1
            self.append("sub_assembly_items", row)

        self.set_default_supplier_for_subcontracting_order()
        self._populate_subassembly_items_from_po_items()
        

        if self.name and self.docstatus < 2 and hasattr(self, 'po_items') and self.po_items:
            try:
                cleanup_all_orphaned_references(self)
            except Exception as e:
                frappe.log_error("Subassembly Cleanup", f"Cleanup error in get_sub_assembly_items: {str(e)}")

    @frappe.whitelist()
    def get_items(self):
        """Populate branch on po_items immediately after fetching items so it shows in grid"""
        self.set("po_items", [])
        if self.get_items_from == "Sales Order":
            self.get_so_items()
        elif self.get_items_from == "Material Request":
            self.get_mr_items()
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

    def set_pending_qty_in_row_without_reference(self):
            "Set Pending Qty in independent rows (not from SO or MR)."
            if self.docstatus > 0:  # set only to initialise value before submit
                return

            for item in self.po_items:
                if not item.get("sales_order") or not item.get("material_request"):
                    item.pending_qty = item.planned_qty
                    item.actual_qty = item.pending_qty

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
                row_batch = getattr(d, "custom_batch_no", None)

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
                        "custom_batch_no":row_batch,
                        "is_active":1, 
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
                    
                    # Set sub-assembly BOM based on parent BOM's BOM Item child reference
                    if hasattr(parent_po_item, "bom_no") and getattr(parent_po_item, "bom_no", None):
                        child_bom = self._get_child_bom_for_item(
                            parent_po_item.bom_no,
                            getattr(sub_item, "production_item", None),
                        )
                        if child_bom and hasattr(sub_item, "bom_no"):
                            sub_item.bom_no = child_bom
                            frappe.log_error(
                                "Subassembly BOM From Parent BOM Item",
                                f"Subassembly item {sub_item_name} set BOM {child_bom} from parent BOM {parent_po_item.bom_no} BOM Item"
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
                     "custom_drawing_no", "custom_drawing_rev_no", 
                    "custom_purchase_specification_no", "custom_purchase_specification_rev_no",
                    "custom_pattern_drawing_no", "custom_pattern_drawing_rev_no",
                    
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
                    "custom_purchase_specification_no": item_data.get("custom_purchase_specification_no"),
                    "custom_purchase_specification_rev_no": item_data.get("custom_purchase_specification_rev_no"),
                    "custom_pattern_drawing_no": item_data.get("custom_pattern_drawing_no"),
                    "custom_pattern_drawing_rev_no": item_data.get("custom_pattern_drawing_rev_no"),
                    
                   
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

    def _get_child_bom_for_item(self, parent_bom_no: str, child_item_code: str) -> str | None:
        """Return the child BOM linked on a BOM Item row inside parent_bom_no for child_item_code.
        Looks up `tabBOM Item.bom_no` for this item. Returns None if not present.
        """
        try:
            if not parent_bom_no or not child_item_code:
                return None
            child_bom = frappe.db.get_value(
                "BOM Item",
                {"parent": parent_bom_no, "item_code": child_item_code},
                "bom_no",
            )
            return child_bom or None
        except Exception as e:
            frappe.log_error(
                "Get Child BOM Error",
                f"Error reading child BOM for item {child_item_code} in parent BOM {parent_bom_no}: {str(e)}",
            )
            return None

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
                getattr(row, "custom_batch_no", None) 
               
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
                            or getattr(parent_po_item, "batch_no", None)
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

            # Set naming series for work order based on item type
            series_mapping = self._get_naming_series_mapping()
            
            # This function exclusively handles sub-assembly rows, so always use the
            # sub-assembly naming series. Relying on production_plan_item presence
            # was causing false negatives and finished-good series to be used.
            work_order_naming_series = series_mapping.get('work_order_subassembly', 'WOAS.YY.####')
            frappe.log_error(
                "Work Order Naming Series - Sub Assembly",
                f"Setting naming_series={work_order_naming_series} for sub-assembly item {getattr(row, 'production_item', 'Unknown')}"
            )
            
            # Add naming series to work order data
            work_order_data["naming_series"] = work_order_naming_series
            # Also carry GA drawing fields from sub_assembly row to WO parent
            try:
                if getattr(row, 'custom_drawing_no', None):
                    work_order_data['custom_ga_drawing_no'] = row.custom_drawing_no
                if getattr(row, 'custom_drawing_rev_no', None):
                    work_order_data['custom_ga_drawing_rev_no'] = row.custom_drawing_rev_no
            except Exception:
                pass
            
            work_order = self.create_work_order(work_order_data)
            if work_order:
                # Ensure custom fields are actually set on the created Work Order
                try:
                    wo_doc = frappe.get_doc("Work Order", work_order)
                    updates = {}
                    # Branch
                    if work_order_data.get("branch") and hasattr(wo_doc, "branch") and not getattr(wo_doc, "branch", None):
                        updates["branch"] = work_order_data.get("branch")
                    # Sales Order
                    if work_order_data.get("sales_order") and hasattr(wo_doc, "sales_order") and not getattr(wo_doc, "sales_order", None):
                        updates["sales_order"] = work_order_data.get("sales_order")
                    # Sales Order Item
                    if work_order_data.get("sales_order_item") and hasattr(wo_doc, "sales_order_item") and not getattr(wo_doc, "sales_order_item", None):
                        updates["sales_order_item"] = work_order_data.get("sales_order_item")
                    # GA Drawing fields (from sub-assembly row)
                    if work_order_data.get("custom_ga_drawing_no") and hasattr(wo_doc, "custom_ga_drawing_no") and not getattr(wo_doc, "custom_ga_drawing_no", None):
                        updates["custom_ga_drawing_no"] = work_order_data.get("custom_ga_drawing_no")
                    if work_order_data.get("custom_ga_drawing_rev_no") and hasattr(wo_doc, "custom_ga_drawing_rev_no") and not getattr(wo_doc, "custom_ga_drawing_rev_no", None):
                        updates["custom_ga_drawing_rev_no"] = work_order_data.get("custom_ga_drawing_rev_no")

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
                        sales_order_value = work_order_data.get("sales_order")
                        for req in getattr(wo_doc, "required_items", []) or []:
                            child_updates = {}
                            if branch_value and hasattr(req, "branch") and not getattr(req, "branch", None):
                                child_updates["branch"] = branch_value
                            if sales_order_value and hasattr(req, "sales_order") and not getattr(req, "sales_order", None):
                                child_updates["sales_order"] = sales_order_value
                            if custom_batch:
                                if hasattr(req, "custom_batch_no") and not getattr(req, "custom_batch_no", None):
                                    child_updates["custom_batch_no"] = custom_batch
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
        """Override the original method to include custom fields from sub-assembly BOM"""
        items = super().get_items_for_material_requests(warehouses)
        
        # Get all BOMs used in this production plan
        bom_list = self.get_all_boms_in_production_plan()
        
        # Add custom fields to each item from sub-assembly BOM
        for item in items:
            item_code = item.get('item_code')
            
            # Get all custom field values from BOM
            custom_data = self.get_custom_fields_from_bom_list(item_code, bom_list)
            
            if custom_data:
                # Add all 6 custom fields to the item
                item['custom_drawing_no'] = custom_data.get('custom_drawing_no')
                item['custom_drawing_rev_no'] = custom_data.get('custom_drawing_rev_no')
                item['custom_purchase_specification_no'] = custom_data.get('custom_purchase_specification_no')
                item['custom_purchase_specification_rev_no'] = custom_data.get('custom_purchase_specification_rev_no')
                item['custom_pattern_drawing_no'] = custom_data.get('custom_pattern_drawing_no')
                item['custom_pattern_drawing_rev_no'] = custom_data.get('custom_pattern_drawing_rev_no')
        
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
    
    def get_custom_fields_from_bom_list(self, item_code, bom_list):
        """Get all custom fields from any BOM in the production plan"""
        if not item_code or not bom_list:
            return None
            
        # Search for all custom fields in all BOMs used in this production plan
        custom_fields = frappe.db.sql("""
            SELECT 
                bi.custom_drawing_no,
                bi.custom_drawing_rev_no,
                bi.custom_purchase_specification_no,
                bi.custom_purchase_specification_rev_no,
                bi.custom_pattern_drawing_no,
                bi.custom_pattern_drawing_rev_no
            FROM `tabBOM Item` bi
            WHERE bi.item_code = %s 
            AND bi.parent IN ({bom_list})
            AND (
                bi.custom_drawing_no IS NOT NULL AND bi.custom_drawing_no != '' OR
                bi.custom_drawing_rev_no IS NOT NULL AND bi.custom_drawing_rev_no != '' OR
                bi.custom_purchase_specification_no IS NOT NULL AND bi.custom_purchase_specification_no != '' OR
                bi.custom_purchase_specification_rev_no IS NOT NULL AND bi.custom_purchase_specification_rev_no != '' OR
                bi.custom_pattern_drawing_no IS NOT NULL AND bi.custom_pattern_drawing_no != '' OR
                bi.custom_pattern_drawing_rev_no IS NOT NULL AND bi.custom_pattern_drawing_rev_no != ''
            )
            LIMIT 1
        """.format(bom_list=','.join(['%s'] * len(bom_list))), 
        [item_code] + bom_list, as_dict=True)
        
        if custom_fields:
            return custom_fields[0]
            
        return None


    @frappe.whitelist()
    def make_material_request(self):
        """Create Material Requests with custom fields from assembly BOM items.
        
        Flow:
        1. For each raw material in mr_items, find which assembly BOM contains it
        2. Copy custom fields from that BOM item to the Material Request item
        3. Group MRs by Sales Order, MR Type, and Customer
        4. Check for existing material requests with same sales order (total existing for cap, unlinked for adjustment)
        5. Reduce making qty in production plan based on unlinked (advance) and cap at total remaining
        6. Optionally link unlinked (advance) MR items to this production plan
        """
        from frappe import _, msgprint
        from frappe.utils import add_days, nowdate, cint, comma_and, get_link_to_form
        
        material_request_list = []
        material_request_map = {}
        notifications = []

        for item in self.mr_items:
            if not getattr(item, "item_code", None):
                continue
                
            item_doc = frappe.get_cached_doc("Item", item.item_code)
            material_request_type = item.material_request_type or item_doc.default_material_request_type

            # Calculate schedule_date early
            schedule_date = item.schedule_date or add_days(nowdate(), cint(getattr(item_doc, "lead_time_days", 0)))

            # Get custom_batch_no from production plan po_items
            custom_batch_no = None
            if hasattr(self, 'po_items') and self.po_items:
                for po_item in self.po_items:
                    if hasattr(po_item, 'custom_batch_no') and po_item.custom_batch_no:
                        custom_batch_no = po_item.custom_batch_no
                        break

            branch_value = getattr(self, "branch", None)
            if hasattr(self, 'po_items') and self.po_items:
                for po_item in self.po_items:
                    if hasattr(po_item, 'branch') and po_item.branch:
                        branch = po_item.branch
                        break

            # Adjustment logic if sales_order present
            plan_qty = flt(item.quantity)
            if getattr(item, "sales_order", None):
                so = item.sales_order
                so_qty = 0
                if getattr(item, "sales_order_item", None):
                    so_qty = frappe.db.get_value("Sales Order Item", item.sales_order_item, "qty") or 0
                else:
                    try:
                        so_qty = frappe.db.get_value(
                            "Sales Order Item",
                            {"parent": so, "item_code": item.item_code},
                            "qty"
                        ) or 0
                    except Exception:
                        so_qty = 0

                # Get unlinked qty (production_plan IS NULL) - for adjustment
                if custom_batch_no:
                    unlinked_qty = flt(frappe.db.sql("""
                        SELECT IFNULL(SUM(mri.qty), 0)
                        FROM `tabMaterial Request Item` mri
                        LEFT JOIN `tabMaterial Request` mr ON mr.name = mri.parent
                        WHERE mri.item_code = %s
                          AND mri.production_plan IS NULL
                          AND mr.docstatus != 2
                          AND (
                            mri.custom_batch_no = %s OR mr.linked_batch = %s
                          )
                    """, (item.item_code, custom_batch_no, custom_batch_no))[0][0])
                else:
                    unlinked_qty = flt(frappe.db.sql("""
                        SELECT IFNULL(SUM(qty), 0)
                        FROM `tabMaterial Request Item` mri
                        LEFT JOIN `tabMaterial Request` mr ON mr.name = mri.parent
                        WHERE mri.sales_order = %s AND mri.item_code = %s 
                        AND mri.production_plan IS NULL
                        AND mr.docstatus != 2
                    """, (so, item.item_code))[0][0])

                # Get total existing qty - for cap
                if custom_batch_no:
                    total_existing_qty = flt(frappe.db.sql("""
                        SELECT IFNULL(SUM(mri.qty), 0)
                        FROM `tabMaterial Request Item` mri
                        LEFT JOIN `tabMaterial Request` mr ON mr.name = mri.parent
                        WHERE mri.item_code = %s
                        AND mr.docstatus != 2
                          AND (
                            mri.custom_batch_no = %s OR mr.linked_batch = %s
                          )
                    """, (item.item_code, custom_batch_no, custom_batch_no))[0][0])
                else:
                    total_existing_qty = flt(frappe.db.sql("""
                    SELECT IFNULL(SUM(qty), 0)
                    FROM `tabMaterial Request Item` mri
                    LEFT JOIN `tabMaterial Request` mr ON mr.name = mri.parent
                    WHERE mri.sales_order = %s AND mri.item_code = %s
                      AND mr.docstatus != 2
                """, (so, item.item_code))[0][0])

                # Calculate how much of plan_qty can be covered by unlinked MRs
                coverage_from_unlinked = min(plan_qty, unlinked_qty)
                # New MR qty = plan qty minus what unlinked MRs will cover
                # Don't cap by SO qty here because plan_qty is already the correct requirement
                item.quantity = max(0, plan_qty - coverage_from_unlinked)

                frappe.log_error(
                    "MR Qty per Split/Advance Logic",
                    f"Item: {item.item_code} | Plan qty: {plan_qty} | Unlinked MR qty: {unlinked_qty} | Coverage from unlinked: {coverage_from_unlinked} | New MR qty needed: {item.quantity}"
                )
                if item.quantity <= 0:
                    frappe.log_error(
                        "MR Item Skipped",
                        f"Skipping {item.item_code}: Plan qty {plan_qty} fully covered by unlinked MR qty {unlinked_qty}"
                    )
                    notifications.append(_(f"{item.item_code}: plan qty {plan_qty} fully covered by existing unlinked MRs ({unlinked_qty}), skipping new MR."))
                    continue

                # Try to link unlinked MR items to this plan (for tracking)
                if coverage_from_unlinked > 0:
                    if custom_batch_no:
                        unlinked_items = frappe.db.sql("""
                            SELECT mri.name, mri.parent, mri.qty, mri.warehouse, mri.bom_no,
                                mri.custom_drawing_no, mri.custom_pattern_drawing_no, mri.from_warehouse
                            FROM `tabMaterial Request Item` mri
                            LEFT JOIN `tabMaterial Request` mr ON mr.name = mri.parent
                            WHERE mri.item_code = %s AND mri.production_plan IS NULL
                            AND mr.docstatus != 2
                              AND (mri.custom_batch_no = %s OR mr.linked_batch = %s)
                            ORDER BY mri.creation ASC
                        """, (item.item_code, custom_batch_no, custom_batch_no), as_dict=True)
                    else:
                        unlinked_items = frappe.db.sql("""
                            SELECT mri.name, mri.parent, mri.qty, mri.warehouse, mri.bom_no,
                                mri.custom_drawing_no, mri.custom_pattern_drawing_no, mri.from_warehouse
                            FROM `tabMaterial Request Item` mri
                            LEFT JOIN `tabMaterial Request` mr ON mr.name = mri.parent
                            WHERE mri.sales_order = %s AND mri.item_code = %s AND mri.production_plan IS NULL
                            AND mr.docstatus != 2
                            ORDER BY mri.creation ASC
                        """, (so, item.item_code), as_dict=True)

                    remaining_to_link = coverage_from_unlinked
                    for ui in unlinked_items:
                        if remaining_to_link <= 0:
                            break
                        mr_name = ui['parent']
                        mr = frappe.get_doc("Material Request", mr_name)
                        if mr.docstatus in (1, 2):
                            continue  # Skip submitted MRs

                        ui_qty = ui['qty']
                        alloc_qty = min(remaining_to_link, ui_qty)

                        if alloc_qty == ui_qty:
                            # Full allocation: link the item
                            update_fields = {
                                "production_plan": self.name,
                                "material_request_plan_item": item.name
                            }
                            if custom_batch_no and not ui.get('custom_batch_no'):
                                update_fields['custom_batch_no'] = custom_batch_no
                            frappe.db.set_value("Material Request Item", ui['name'], update_fields)
                            if custom_batch_no and not mr.linked_batch:
                                frappe.db.set_value("Material Request", mr_name, "linked_batch", custom_batch_no)
                            frappe.log_error("MR Item Linked", f"Linked full item {ui['name']} to plan {self.name}")
                            remaining_to_link -= alloc_qty
                        else:
                            # Partial allocation: split by appending new linked item and reducing original
                            bom_no, custom_fields = self._get_bom_custom_fields_for_mr_item(item.item_code)
                            new_mr_item_data = {
                                "item_code": item.item_code,
                                "qty": alloc_qty,
                                "schedule_date": schedule_date,
                                "warehouse": ui['warehouse'],
                                "from_warehouse": ui['from_warehouse'] if material_request_type == "Material Transfer" else None,
                                "sales_order": so,
                                "production_plan": self.name,
                                "material_request_plan_item": item.name,
                                "project": frappe.db.get_value("Sales Order", so, "project") if so else None,
                                "custom_batch_no": custom_batch_no,
                            }
                            if bom_no:
                                new_mr_item_data["bom_no"] = bom_no
                            # Custom fields from BOM, override with UI if present
                            for field, value in custom_fields.items():
                                if value:
                                    new_mr_item_data[field] = value
                            if ui.get('custom_drawing_no'):
                                new_mr_item_data["custom_drawing_no"] = ui['custom_drawing_no']
                            if ui.get('custom_pattern_drawing_no'):
                                new_mr_item_data["custom_pattern_drawing_no"] = ui['custom_pattern_drawing_no']

                            # Append new item
                            new_row = mr.append("items", new_mr_item_data)
                            # Reduce original item qty
                            new_ui_qty = ui_qty - alloc_qty
                            frappe.db.set_value("Material Request Item", ui['name'], "qty", new_ui_qty)
                            if new_ui_qty == 0:
                                frappe.db.delete("Material Request Item", ui['name'])
                            # Set linked_batch if needed
                            if custom_batch_no and not mr.linked_batch:
                                mr.linked_batch = custom_batch_no
                            # Save MR
                            mr.flags.ignore_permissions = 1
                            mr.run_method("set_missing_values")
                            mr.save()
                            frappe.log_error("MR Item Partial Linked", f"Partial linked {alloc_qty} for item {item.item_code} in MR {mr_name}")
                            remaining_to_link -= alloc_qty
            else:
                # No sales_order: reduce by existing MR qty for same item+batch (advance MR concept)
                if custom_batch_no:
                    total_existing_qty_by_batch = flt(frappe.db.sql("""
                        SELECT IFNULL(SUM(mri.qty), 0)
                        FROM `tabMaterial Request Item` mri
                        LEFT JOIN `tabMaterial Request` mr ON mr.name = mri.parent
                        WHERE mri.item_code = %s
                        AND mr.docstatus != 2
                          AND (mri.custom_batch_no = %s OR mr.linked_batch = %s)
                    """, (item.item_code, custom_batch_no, custom_batch_no))[0][0])
                # else:
                #     total_existing_qty_by_batch = flt(frappe.db.sql("""
                #     SELECT IFNULL(SUM(qty), 0)
                #     FROM `tabMaterial Request Item` mri
                #     LEFT JOIN `tabMaterial Request` mr ON mr.name = mri.parent
                #     WHERE mri.item_code = %s
                #       AND mr.docstatus != 2
                # """, (item.item_code,))[0][0])

                item.quantity = max(0, plan_qty - total_existing_qty_by_batch)
                if item.quantity <= 0:
                    notifications.append(_(f"{item.item_code}: already requested {total_existing_qty_by_batch} for batch {custom_batch_no or '-'}; remaining is 0, skipping."))
                    continue

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

            if key not in material_request_map:
                mr = frappe.new_doc("Material Request")
                
                # Get naming series mapping
                series_mapping = self._get_naming_series_mapping()
                
                # Determine the appropriate naming series based on material request type
                if material_request_type == "Purchase":
                    naming_series = series_mapping.get('material_request_purchase', 'PMRS.YY.####')
                elif material_request_type == "Material Transfer":
                    naming_series = series_mapping.get('material_request_transfer', 'PTRS.YY.####')
                else:
                    naming_series = series_mapping.get('material_request_purchase', 'PMRS.YY.####')
                
                # Resolve branch from Production Plan
                branch_value = getattr(self, 'branch', None)
                if not branch_value and getattr(self, 'po_items', None):
                    try:
                        branch_value = next((pi.branch for pi in self.po_items if getattr(pi, 'branch', None)), None)
                    except Exception:
                        branch_value = None
                
                header_fields = {
                    "transaction_date": nowdate(),
                    "status": "Draft",
                    "company": self.company,
                    "material_request_type": material_request_type,
                    "customer": customer,
                    "naming_series": naming_series,
                }
                # Set branch on MR parent if field exists and value is present
                try:
                    if branch_value and hasattr(mr, 'branch'):
                        header_fields["branch"] = branch_value
                except Exception:
                    pass
                mr.update(header_fields)
                
                # Set linked_batch if custom_batch_no is available
                if custom_batch_no:
                    mr.linked_batch = custom_batch_no
                    frappe.log_error(
                        "Material Request Linked Batch Set",
                        f"Setting linked_batch={custom_batch_no} for Material Request"
                    )
                
                frappe.log_error(
                    "Material Request Naming Series Set",
                    f"Setting naming_series={naming_series} for Material Request type {material_request_type}"
                )
                
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
            
            # Set custom_batch_no on MR item if available
            if custom_batch_no:
                mr_item_data["custom_batch_no"] = custom_batch_no

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

        # Show summary notifications for removed/zero quantity lines
        if notifications:
            msgprint("<br>".join(notifications))

        # Save and submit Material Requests
        for material_request in material_request_list:
            # material_request.flags.ignore_permissions = 1
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
            
            # Show additional info about quantity adjustments if any
            if any(getattr(item, "sales_order", None) for item in self.mr_items):
                msgprint(_("Note: Quantities have been adjusted to account for existing Material Requests (advance/unlinked) for the Sales Order(s)."))
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

    def _get_naming_series_mapping(self):
        """Get naming series mapping based on production plan naming series
        
        Returns:
            dict: Mapping of document types to naming series
        """
        try:
            # Get the production plan naming series
            pp_series = getattr(self, 'naming_series', None) or ''

            # Determine prefix based on Branch first, then Naming Series
            branch = getattr(self, 'branch', None)

            # If branch is not set on header, try to get from items
            if not branch and getattr(self, 'po_items', None):
                 branch = next((pi.branch for pi in self.po_items if getattr(pi, 'branch', None)), None)

            prefix = None

            if branch:
                if "Rabale" in branch:
                    prefix = 'PPOR'
                elif "Sanand" in branch:
                    prefix = 'PPOS'
                elif "Nandikoor" in branch:
                    prefix = 'PPON'
            
            if not prefix:
                # Fallback to naming series if branch not found
                if 'PPOR' in pp_series:
                    prefix = 'PPOR'
                elif 'PPON' in pp_series:
                    prefix = 'PPON'
                elif 'PPOS' in pp_series:
                    prefix = 'PPOS'
            
            # Define naming series mappings
            series_mapping = {
                'PPOS': {
                    'material_request_purchase': 'PMRS.YY.####',
                    'material_request_transfer': 'PTRS.YY.####',
                    'work_order_fg': 'WOFS.YY.####',
                    'work_order_subassembly': 'WOAS.YY.####'
                },
                'PPOR': {
                    'material_request_purchase': 'PMRR.YY.####',
                    'material_request_transfer': 'PTRR.YY.####',
                    'work_order_fg': 'WOFR.YY.####',
                    'work_order_subassembly': 'WOAR.YY.####'
                },
                'PPON': {
                    'material_request_purchase': 'PMRN.YY.####',
                    'material_request_transfer': 'PTRN.YY.####',
                    'work_order_fg': 'WOFN.YY.####',
                    'work_order_subassembly': 'WOAN.YY.####'
                }
            }
            
            frappe.log_error(
                "Naming Series Mapping",
                f"Branch: {branch}, Production Plan series: {pp_series}, Prefix: {prefix}, Mapping: {series_mapping.get(prefix, {})}"
            )
            
            return series_mapping.get(prefix, {})
            
        except Exception as e:
            frappe.log_error(
                "Naming Series Mapping Error",
                f"Error getting naming series mapping: {str(e)}"
            )
            # Return default mapping
            return {
                'material_request_purchase': 'PMRS.YY.####',
                'material_request_transfer': 'PTRS.YY.####',
                'work_order_fg': 'WOFS.YY.####',
                'work_order_subassembly': 'WOAS.YY.####'
            }

    def _get_existing_material_request_qty(self, sales_order, item_code, custom_batch_no):
        """Get existing material request quantity for the same item_code and custom_batch_no
        regardless of whether the MR came from Sales Order or Production Plan
        
        Args:
            sales_order (str): Sales Order name (for logging purposes)
            item_code (str): Item code
            custom_batch_no (str): Custom batch number from production plan
            
        Returns:
            float: Total existing quantity in material requests
        """
        try:
            # Query to find existing material requests with same item_code and custom_batch_no
            # Check both MR items with custom_batch_no and MR header with linked_batch
            existing_mr_data = frappe.db.sql("""
                SELECT 
                    SUM(mri.qty) as total_qty
                FROM `tabMaterial Request Item` mri
                INNER JOIN `tabMaterial Request` mr ON mri.parent = mr.name
                WHERE mr.docstatus IN (0, 1)
                AND mri.item_code = %s
                AND (
                    mri.custom_batch_no = %s 
                    OR mr.linked_batch = %s
                )
                AND mr.name != %s
            """, (item_code, custom_batch_no, custom_batch_no, self.name or ""), as_dict=True)
            
            total_qty = flt(existing_mr_data[0].total_qty) if existing_mr_data else 0
            
            frappe.log_error(
                "Existing Material Request Check",
                f"Item: {item_code}, Batch: {custom_batch_no}, "
                f"Existing MR Qty: {total_qty} (checked both MR items and MR header)"
            )
            
            return total_qty
            
        except Exception as e:
            frappe.log_error(
                "Material Request Qty Check Error",
                f"Error checking existing material request qty for Item {item_code}, "
                f"Batch {custom_batch_no}: {str(e)}"
            )
            return 0


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
                [
                    "custom_drawing_no",
                    "custom_drawing_rev_no",
                    "custom_pattern_drawing_no",
                    "custom_pattern_drawing_rev_no",
                    "custom_purchase_specification_no",
                    "custom_purchase_specification_rev_no"
                ],
                as_dict=True
            )

            if drawing:
                row["custom_drawing_no"] = drawing.custom_drawing_no
                row["custom_drawing_rev_no"] = drawing.custom_drawing_rev_no
                row["custom_pattern_drawing_no"] = drawing.custom_pattern_drawing_no
                row["custom_pattern_drawing_rev_no"] = drawing.custom_pattern_drawing_rev_no
                row["custom_purchase_specification_no"] = drawing.custom_purchase_specification_no
                row["custom_purchase_specification_rev_no"] = drawing.custom_purchase_specification_rev_no

            # drawing = frappe.db.get_value(
            #     "BOM Item",
            #     {"parent": (row.get("bom_no") or bom_for_item), "item_code": item_code},
            #     "custom_drawing_no",
            # )
            # if drawing:
            #     row["custom_drawing_no"] = drawing
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
                        [
                            "custom_drawing_no",
                            "custom_drawing_rev_no",
                            "custom_pattern_drawing_no",
                            "custom_pattern_drawing_rev_no",
                            "custom_purchase_specification_no",
                            "custom_purchase_specification_rev_no"
                        ],
                        as_dict=True
                    )

                    if drawing:
                        row["custom_drawing_no"] = drawing.custom_drawing_no
                        row["custom_drawing_rev_no"] = drawing.custom_drawing_rev_no
                        row["custom_pattern_drawing_no"] = drawing.custom_pattern_drawing_no
                        row["custom_pattern_drawing_rev_no"] = drawing.custom_pattern_drawing_rev_no
                        row["custom_purchase_specification_no"] = drawing.custom_purchase_specification_no
                        row["custom_purchase_specification_rev_no"] = drawing.custom_purchase_specification_rev_no
                except Exception:
                    pass
        except Exception as e:
            frappe.log_error("Patched Get MR Items Error", f"Enrichment failed: {str(e)}")
        return items

    if callable(_core_get_mr_items):
        core_pp.get_items_for_material_requests = patched_get_items_for_material_requests
except Exception as e:
    frappe.log_error("Production Plan MR Patch Error", f"Unable to patch: {str(e)}")

@frappe.whitelist()
def get_bin_details(row, company, for_warehouse=None, all_warehouse=False):
	if isinstance(row, str):
		row = frappe._dict(json.loads(row))

	bin = frappe.qb.DocType("Bin")
	wh = frappe.qb.DocType("Warehouse")

	subquery = frappe.qb.from_(wh).select(wh.name).where(wh.company == company)

	warehouse = ""
	if not all_warehouse:
		warehouse = for_warehouse or row.get("source_warehouse") or row.get("default_warehouse")

	if warehouse:
		lft, rgt = frappe.db.get_value("Warehouse", warehouse, ["lft", "rgt"])
		subquery = subquery.where((wh.lft >= lft) & (wh.rgt <= rgt) & (wh.name == bin.warehouse))

	query = (
		frappe.qb.from_(bin)
		.select(
			bin.warehouse,
			IfNull(Sum(bin.projected_qty), 0).as_("projected_qty"),
			IfNull(Sum(bin.actual_qty), 0).as_("actual_qty"),
			IfNull(Sum(bin.ordered_qty), 0).as_("ordered_qty"),
			IfNull(Sum(bin.reserved_qty_for_production), 0).as_("reserved_qty_for_production"),
			IfNull(Sum(bin.planned_qty), 0).as_("planned_qty"),
		)
		.where((bin.item_code == row["item_code"]) & (bin.warehouse.isin(subquery)))
		.groupby(bin.item_code, bin.warehouse)
	)

	return query.run(as_dict=True)


def get_sub_assembly_items(
	sub_assembly_items,
	bin_details,
	bom_no,
	bom_data,
	to_produce_qty,
	company,
	warehouse=None,
	indent=0,
	skip_available_sub_assembly_item=False,
):
	data = get_bom_children(parent=bom_no)
	for d in data:
		if d.expandable:
			parent_item_code = frappe.get_cached_value("BOM", bom_no, "item")
			stock_qty = (d.stock_qty / d.parent_bom_qty) * flt(to_produce_qty)

			if skip_available_sub_assembly_item and d.item_code not in sub_assembly_items:
				bin_details.setdefault(d.item_code, get_bin_details(d, company, for_warehouse=warehouse))

				for _bin_dict in bin_details[d.item_code]:
					if _bin_dict.projected_qty > 0:
						if _bin_dict.projected_qty >= stock_qty:
							_bin_dict.projected_qty -= stock_qty
							stock_qty = 0
							continue
						else:
							stock_qty = stock_qty - _bin_dict.projected_qty
							sub_assembly_items.append(d.item_code)
			elif warehouse:
				bin_details.setdefault(d.item_code, get_bin_details(d, company, for_warehouse=warehouse))

			if stock_qty > 0:
				bom_data.append(
					frappe._dict(
						{
							"actual_qty": bin_details[d.item_code][0].get("actual_qty", 0)
							if bin_details.get(d.item_code)
							else 0,
							"parent_item_code": parent_item_code,
							"description": d.description,
							"production_item": d.item_code,
							"item_name": d.item_name,
							"stock_uom": d.stock_uom,
							"uom": d.stock_uom,
							"bom_no": d.value,
							"is_sub_contracted_item": d.is_sub_contracted_item,
							"bom_level": indent,
							"indent": indent,
							"stock_qty": stock_qty,
						}
					)
				)

				if d.value:
					get_sub_assembly_items(
						sub_assembly_items,
						bin_details,
						d.value,
						bom_data,
						stock_qty,
						company,
						warehouse,
						indent=indent + 1,
						skip_available_sub_assembly_item=skip_available_sub_assembly_item,
					)