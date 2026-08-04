import frappe
from frappe import _

@frappe.whitelist()
def get_dashboard_data(branch=None, from_date=None, to_date=None):
    """
    Fetch live manufacturing data from ERPNext doctypes.
    Filters by branch if provided (Sanand / Vadodara / All).
    """
    data = {
        "boms": [],
        "production_plans": [],
        "work_orders": [],
        "material_requests": []
    }

    # ---------- BOM ----------
    bom_filters = {"docstatus": ["<", 2]}
    if branch and branch != "All":
        bom_filters["branch"] = branch
    if from_date and to_date:
        bom_filters["creation"] = ["between", [from_date, to_date]]

    boms = frappe.get_all(
        "BOM",
        filters=bom_filters,
        fields=[
            "name", "item_name", "item as item_code", "branch",
            "is_active", "is_default", "docstatus", "total_cost",
            "modified as last_updated"
        ],
        limit=100,
        order_by="modified desc"
    )

    for bom in boms:
        # Count components from BOM Item child table
        comp_count = frappe.db.count("BOM Item", {"parent": bom.name, "parenttype": "BOM"})
        bom["components"] = comp_count or 1
        # Version from naming (last segment after last hyphen)
        parts = (bom.name or "").rsplit("-", 1)
        bom["version"] = parts[-1] if len(parts) > 1 else "001"
        # Status logic
        if bom.docstatus == 0 and not bom.is_active:
            bom["status"] = "Draft"
        elif bom.docstatus == 0 and bom.is_active:
            bom["status"] = "Active"
        elif bom.docstatus == 1 and not bom.is_active:
            bom["status"] = "Inactive"
        elif bom.docstatus == 1 and bom.is_active:
            bom["status"] = "Active"
        else:
            bom["status"] = "Review"
        data["boms"].append(bom)

    # ---------- Production Plan ----------
    pp_filters = {"docstatus": ["<", 2]}
    if branch and branch != "All":
        pp_filters["branch"] = branch
    if from_date and to_date:
        pp_filters["posting_date"] = ["between", [from_date, to_date]]

    production_plans = frappe.get_all(
        "Production Plan",
        filters=pp_filters,
        fields=[
            "name", "status", "branch", "posting_date",
            "total_planned_qty", "total_produced_qty", "docstatus"
        ],
        limit=100,
        order_by="modified desc"
    )

    for pp in production_plans:
        pp["actual"] = flt(pp.get("total_produced_qty", 0))
        pp["target"] = flt(pp.get("total_planned_qty", 1)) or 1
        pp["progress"] = min(100, round((pp["actual"] / pp["target"]) * 100, 1))
        # Try to get product name from first PO item
        po_items = frappe.get_all(
            "Production Plan Item",
            filters={"parent": pp.name},
            fields=["item_code"],
            limit=1
        )
        if po_items:
            item_code = po_items[0].item_code
            item_name = frappe.db.get_value("Item", item_code, "item_name") or item_code
            pp["product"] = item_name
            pp["product_code"] = item_code
        else:
            pp["product"] = pp.name
            pp["product_code"] = ""
        # Shift is not standard on Production Plan; default to 1st
        pp["shift"] = "1st"
        data["production_plans"].append(pp)

    # ---------- Work Order ----------
    wo_filters = {"docstatus": ["<", 2]}
    if branch and branch != "All":
        wo_filters["branch"] = branch
    if from_date and to_date:
        wo_filters["planned_start_date"] = ["between", [from_date, to_date]]

    work_orders = frappe.get_all(
        "Work Order",
        filters=wo_filters,
        fields=[
            "name", "production_item", "item_name", "qty", "produced_qty",
            "status", "branch", "planned_start_date", "sales_order", "bom_no"
        ],
        limit=100,
        order_by="modified desc"
    )

    for wo in work_orders:
        wo["product"] = wo.item_name or wo.production_item or wo.name
        wo["due_date"] = wo.planned_start_date
        # Priority heuristic
        if wo.status in ["Overdue", "Stopped"]:
            wo["priority"] = "High"
        elif wo.status in ["In Process", "Not Started"]:
            wo["priority"] = "Medium"
        else:
            wo["priority"] = "Low"
        data["work_orders"].append(wo)

    # ---------- Material Request ----------
    mr_filters = {"docstatus": ["<", 2]}
    if branch and branch != "All":
        mr_filters["branch"] = branch
    if from_date and to_date:
        mr_filters["transaction_date"] = ["between", [from_date, to_date]]

    material_requests = frappe.get_all(
        "Material Request",
        filters=mr_filters,
        fields=[
            "name", "title", "material_request_type", "status", "branch",
            "transaction_date", "per_ordered", "per_received"
        ],
        limit=100,
        order_by="modified desc"
    )

    for mr in material_requests:
        # Get first item details for display
        mr_items = frappe.get_all(
            "Material Request Item",
            filters={"parent": mr.name},
            fields=["item_name", "qty", "stock_uom", "warehouse"],
            limit=1
        )
        if mr_items:
            mr["material"] = mr_items[0].item_name or mr.title or mr.name
            mr["qty"] = "{} {}".format(mr_items[0].qty or 1, mr_items[0].stock_uom or "Nos")
            mr["department"] = (mr_items[0].warehouse or "").replace(" - SVIPL", "").replace("Sanand ", "").replace("Vadodara ", "")
        else:
            mr["material"] = mr.title or mr.name
            mr["qty"] = "1 Nos"
            mr["department"] = "Stores"
        mr["date"] = mr.transaction_date
        data["material_requests"].append(mr)

    return data


def flt(val, default=0):
    """Safe float cast."""
    try:
        return float(val or default)
    except (ValueError, TypeError):
        return float(default)

@frappe.whitelist()
def get_branches():
    branches = frappe.get_all("Branch", fields=["name"])
    return [b.name for b in branches]