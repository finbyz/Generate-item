# Purchase User Dashboard — Data Filtering & Testing Reference

This document details the exact filtering mechanisms, database queries, and testing steps implemented in [purchase_user.py](file:///home/frappe/benches/steelstrong-v16-bench/apps/generate_item/generate_item/generate_item/page/purchase_user/purchase_user.py) and [purchase_user.js](file:///home/frappe/benches/steelstrong-v16-bench/apps/generate_item/generate_item/generate_item/page/purchase_user/purchase_user.js).

---

## 1. Global Filter Bar & Permission Logic

```text
┌─────────────────┐   ┌──────────────────────┐   ┌────────────────────────┐
│  BRANCH FILTER  │   │  CREATED BY (USER)   │   │  DATE RANGE / PERIOD   │
└────────┬────────┘   └──────────┬───────────┘   └───────────┬────────────┘
         │                       │                           │
         ▼                       ▼                           ▼
[tabBranch Perms]      [tabUser Permission BFS]    [transaction_date / posting_date]
```

| Filter | Code Identifier | Target DB Column | How It Filters |
| :--- | :--- | :--- | :--- |
| **Branch** | `this.filters.branch` | `doc.branch` | Matches the selected plant (e.g. `Sanand`, `Nandikoor`, `Rabale`). Users without unrestricted access only see their permitted branches. |
| **Created By** | `this.filters.user` | `doc.owner` | Filters records by document creator. Restricted to logged-in user and direct/indirect subordinates in the User Permission hierarchy. |
| **Period** | `this.filters.from_date`<br>`this.filters.to_date` | `transaction_date`<br>or `posting_date` | • `Material Request` & `Purchase Order`: `transaction_date BETWEEN from_date AND to_date`<br>• `Purchase Receipt` & `Purchase Invoice`: `posting_date BETWEEN from_date AND to_date` |

---

## 2. Child-Table Foreign Key Linkage (Source of Truth)

Calculations rely strictly on ERPNext's native child-table row IDs (`name`) and reference fields:

```text
tabMaterial Request Item (name: "mri_01")
        │
        ▼ Purchase Order Item.material_request_item = "mri_01"
tabPurchase Order Item (name: "poi_01")
        │
        ▼ Purchase Receipt Item.purchase_order_item = "poi_01"
tabPurchase Receipt Item (name: "pri_01")
        │
        ▼ Purchase Invoice Item.pr_detail = "pri_01"
tabPurchase Invoice Item (name: "pii_01")
```

---

## 3. Stage-by-Stage Filtering Logic (`purchase_user.py`)

### Card 1 · MR Pending (`id: "po_pending"`)
* **Parent Doctype**: `Material Request` (`docstatus = 1`, `material_request_type = 'Purchase'`, `status NOT IN ('Stopped', 'Cancelled')`).
* **Child Table**: `Material Request Item` where `(qty - COALESCE(ordered_qty, 0)) > 0`.
* **Metric Calculation**:
  * **Document Count**: `COUNT(DISTINCT mr.name)`
  * **Line Items Pending**: `COUNT(mri.name)`
  * **Total Quantity**: `SUM(mri.qty - mri.ordered_qty)`
* **Special Rule**: **Branch filter applies, User filter is BYPASSED**. Pending Material Requests represent plant-wide requirements rather than individual buyer tasks.

---

### Card 2 · PO Converted (`id: "mr_completed"`)
* **Linkage**: `tabPurchase Order Item.material_request_item = tabMaterial Request Item.name`.
* **Parent Doctype**: `Purchase Order` (`docstatus = 1`, date in period, matches user & branch).
* **Child Table**: `Material Request Item` linked to submitted Purchase Order Items.
* **Metric Calculation**:
  * **Document Count**: `COUNT(DISTINCT mr.name)` (Unique Material Requests converted to PO).
  * **Line Items Converted**: `COUNT(DISTINCT mri.name)` (Unique MR Item row IDs converted).
  * **Total Quantity**: `SUM(poi.qty)`

---

### Card 3 · PR Pending (`id: "pr_pending"`)
* **Parent Doctype**: `Purchase Order` (`docstatus = 1`, `status NOT IN ('Closed', 'Cancelled', 'Delivered', 'Completed')`).
* **Child Table**: `Purchase Order Item` where `(qty - COALESCE(received_qty, 0)) > 0`.
* **Metric Calculation**:
  * **Document Count**: `COUNT(DISTINCT po.name)`
  * **Line Items Pending**: `COUNT(poi.name)`
  * **Total Quantity**: `SUM(poi.qty - poi.received_qty)`

---

### Card 4 · PI Pending (`id: "pi_pending"`)
* **Parent Doctype**: `Purchase Receipt` (`docstatus = 1`, `is_return = 0`, `status IN ('Partly Billed', 'To Bill', 'Partially Billed')`).
* **Child Table**: `Purchase Receipt Item` where `(amount - COALESCE(billed_amt, 0)) > 0`.
* **Metric Calculation**:
  * **Document Count**: `COUNT(DISTINCT pr.name)`
  * **Line Items Pending**: `COUNT(pri.name)`
  * **Total Amount**: `SUM(pri.amount - pri.billed_amt)`

---

### Card 5 · Total PI Completed (`id: "pi_completed"`)
* **Parent Doctype**: `Purchase Invoice` (`docstatus = 1`, `is_return = 0`, `posting_date` in period).
* **Child Table**: `Purchase Invoice Item`.
* **Metric Calculation**:
  * **Document Count**: `COUNT(DISTINCT pi.name)`
  * **Line Items Completed**: `COUNT(pii.name)`
  * **Total Amount**: `SUM(pii.amount)`

---

### PO Value & Delivery Cards (`_get_po_metrics`, returned as `po_metrics`)

**Layout**: all 8 number cards share one grid (`.pud-kpi-grid-4`), 4 cards per row. Row 1: MR Pending, PO Converted, PR Pending, PI Pending. Row 2: Total PI Completed, On Time Delivery, Total PO Value (Net), Average PO Value. The grid drops to 2 per row below 1100px and 1 per row below 480px. On the 3 PO cards the value font scales with screen width, and the small badge (e.g. `NET VALUE`) moves under the value when there is not enough room, so long amounts do not overflow the card.

The 3 PO cards all use submitted Purchase Orders (`docstatus = 1`) with `transaction_date` in the selected period, and apply both the Branch and Created By filters. Each card also shows the change against the previous period (`po_metrics.previous`).

| Card | Value | Calculation |
| :--- | :--- | :--- |
| **On Time Delivery** | `on_time_pct` | `on_time_count / due_count * 100`, shown with `on_time_count / due_count` and `late_count`. The change is shown in percentage points (pts). |
| **Total PO Value (Net)** | `total_net_value` | `SUM(po.base_net_total)`, the net total in company currency, before taxes. |
| **Average PO Value** | `avg_po_value` | `total_net_value / po_count` (0 when there are no POs). |

**On Time Delivery rules:**
* **Due PO** (`due_count`): `po.per_received >= 100` OR `po.schedule_date < today`. POs with status `Closed` or `On Hold`, or with no `schedule_date`, are left out.
* **On time PO** (`on_time_count`): a due PO with `per_received >= 100` whose **last** submitted Purchase Receipt (`MAX(pr.posting_date)` over `Purchase Receipt Item.purchase_order`) is on or before `po.schedule_date` (Required By).
* **Late / Not Received** (`late_count`): `due_count - on_time_count`. This covers POs received after the Required By date and POs past that date that are not yet fully received.
* Card colour: green at 90% or above, amber at 70% to 89%, red below 70%.

---

### Section 01 · Purchase Order Workflow Status (`_get_po_workflow_status`, returned as `po_workflow_status`)

* **Doctype**: `Purchase Order` with `docstatus < 2`, so drafts awaiting approval are included and cancelled POs are not. Date (`transaction_date`), Branch and Created By filters apply.
* **Grouping**: `po.workflow_state` (falls back to `po.status` if the field does not exist). Empty values are shown as `Not Set`.
* **Per status**: `count` (number of POs) and `net_value` (`SUM(po.base_net_total)`), sorted by count, highest first.
* **Display**: a list (status, PO count, share of total, net value, with a total row) next to a **horizontal** bar chart of PO count per status. The chart is plain HTML/CSS (`.pud-hbar-row`), not `frappe.Chart`, with bar widths relative to the largest status and a 0 / half / max scale underneath. Clicking a bar works like clicking a list row.

---

### Section 04 · Supplier-wise Purchase Orders (`_get_po_supplier_orders`, returned as `po_supplier_orders`)

Shown next to **Most Purchase Orders** in the Leaderboard section. It replaces the old **Fewest Purchase Orders** list, which was removed.

* **Backend**: returns one row per submitted Purchase Order (`docstatus = 1`) with `name`, `date`, `supplier`, `supplier_name`, `owner`, `net_value` (`base_net_total`), `status` and `workflow_state`. Period, Branch and Created By filters apply. Capped at the latest 3,000 POs; `truncated = true` shows a note on the card.
* **Grouping (in the page)**: `get_supplier_groups()` groups the rows by supplier, with PO count and total net value, sorted by count then value.
* **Drill-down levels**:
  1. Click a creator in **Most Purchase Orders**: the supplier card shows only that creator's POs and the creator row is highlighted. Click the same creator again, or **All Creators**, to go back to all creators.
  2. Click a supplier: it expands to show its POs (up to 25: PO link, date, creator, workflow status, net value).
  3. **Open in List View** under a supplier: opens the Purchase Order list filtered by that supplier, the selected creator (if any), Period and Branch.
* **Other**: supplier search (more than 5 suppliers), View More / View Less, and **CSV** export of the supplier totals.

> The **Material Request Trend (Item-wise)** section and its backend function `_get_mr_trends` were removed on 23 Nov 2026. `get_dashboard` no longer returns a `trends` key.

---

## 4. UI Actions & Drill-Down Routing (`purchase_user.js`)

1. **Card Click (Modal Popup)**:
   * Opens `#pud-modal` displaying parent documents (`it.ao`), dates (`it.date`), creators (`it.who`), and branches (`it.branch`).
   * Expanding a document reveals the table of child items (`it.doc_items`) with item codes, names, pending quantities, schedule dates, and amounts.
2. **List View Button ([↗ List])**:
   * Directly routes to ERPNext standard List View with pre-populated filters matching the active card stage, branch, and date range.
3. **PO Value & Delivery Cards ([↗ List])**:
   * Open the Purchase Order List View with `docstatus = 1` plus the dashboard's active filters: `transaction_date` (Period), `branch` (Branch) and `owner IN (...)` (Created By). The filters are built by `po_list_filters()`, which follows the same rules as `open_list_view()` for the stage cards. These cards have no modal popup.
4. **Section 01 (PO Workflow Status)**:
   * Clicking a status row or its bar in the horizontal chart opens the Purchase Order List View filtered by that `workflow_state`, `docstatus != 2`, and the same Period, Branch and Created By filters.
5. **Section 02 (Document Intensity)**:
   * Groups documents into `1 Item`, `2 Items`, `3 Items`, and `3+ Items` buckets with branch distribution. Clicking any bucket opens the matching document modal.
6. **Section 03 (Item-wise Summary Table)**:
   * Aggregates line items by `(item_code, stage_id)`. Includes live multi-column search and **Export CSV** download.
7. **Section 04 (Leaderboard)**:
   * **Most Purchase Orders** ranks creators by PO count and grand total. Clicking a creator drills the Supplier-wise card down to that creator. The small ↗ button on each row opens that creator's Purchase Orders in List View.
   * **Supplier-wise Purchase Orders**: see the Section 04 description above. The **Fewest Purchase Orders** list was removed.

---

## 5. How to Test & Verify

### Verification via Python Bench Console:
```bash
bench --site steelstrong.finbyz.com console
```
```python
import frappe
from generate_item.generate_item.page.purchase_user.purchase_user import get_dashboard

# Test for today's date
data = get_dashboard(from_date="2026-09-30", to_date="2026-09-30")

for card in data["cards"]:
    print(f"[{card['title']}] Count: {card['count']} Docs, {card['line_item_count']} Line Items | Modal Items: {len(card.get('items', []))}")

# PO value & delivery cards
m = data["po_metrics"]
print(f"On Time: {m['on_time_pct']}% ({m['on_time_count']}/{m['due_count']}) | Net Value: {m['total_net_value']} | Avg PO: {m['avg_po_value']}")

# Workflow status list
for row in data["po_workflow_status"]:
    print(f"{row['workflow_state']}: {row['count']} POs, {row['net_value']}")
```

### Verification via SQL (On Time Delivery):
```sql
SELECT
    po.name, po.schedule_date, po.per_received, pr_last.last_date,
    (po.per_received >= 100 AND pr_last.last_date <= po.schedule_date) AS on_time
FROM `tabPurchase Order` po
LEFT JOIN (
    SELECT pri.purchase_order, MAX(pr.posting_date) AS last_date
    FROM `tabPurchase Receipt Item` pri
    INNER JOIN `tabPurchase Receipt` pr ON pr.name = pri.parent AND pr.docstatus = 1
    WHERE COALESCE(pri.purchase_order, '') != ''
    GROUP BY pri.purchase_order
) pr_last ON pr_last.purchase_order = po.name
WHERE po.docstatus = 1
  AND po.status NOT IN ('Closed', 'On Hold')
  AND po.schedule_date IS NOT NULL
  AND (po.per_received >= 100 OR po.schedule_date < CURDATE())
  AND po.transaction_date BETWEEN '2026-08-23' AND '2026-11-23';
```

### Verification via SQL (Card 1 Example):
```sql
SELECT 
    mr.name AS mr_id,
    mri.item_code,
    mri.qty,
    mri.ordered_qty,
    (mri.qty - COALESCE(mri.ordered_qty, 0)) AS pending_qty
FROM `tabMaterial Request` mr
INNER JOIN `tabMaterial Request Item` mri ON mr.name = mri.parent AND mri.parenttype = 'Material Request'
WHERE mr.docstatus = 1 
  AND mr.material_request_type = 'Purchase'
  AND mr.status NOT IN ('Stopped', 'Cancelled')
  AND (mri.qty - COALESCE(mri.ordered_qty, 0)) > 0
  AND mr.transaction_date = '2026-09-30';
```

---

## 6. `get_dashboard` Response Keys

| Key | Used by |
| :--- | :--- |
| `cards` | The 5 stage cards, Sections 02 and 03, and the item modals |
| `item_summary`, `total_distinct_items` | Section 03 item table and the header summary |
| `po_metrics` | On Time Delivery, Total PO Value (Net) and Average PO Value cards |
| `po_workflow_status` | Section 01 workflow status list and chart |
| `po_leaderboard` | Section 04 Most Purchase Orders list |
| `po_supplier_orders` | Section 04 Supplier-wise Purchase Orders drill-down |
| `active_filters`, `branch_permissions` | Filter bar state and branch access |

---

## 7. Change Log

| Date | Change |
| :--- | :--- |
| 23 Nov 2026 | Added On Time Delivery, Total PO Value (Net) and Average PO Value cards. Added Section 01 Purchase Order Workflow Status (list and bar chart). Removed the Material Request Trend (Item-wise) section and `_get_mr_trends`. |
| 23 Nov 2026 | All 8 number cards shown in one grid, 4 per row (`.pud-kpi-grid-4`). |
| 23 Nov 2026 | List buttons on the 3 PO cards and Workflow Status rows now pass Branch and Created By filters, not only Period (`po_list_filters()`). |
| 23 Nov 2026 | Fixed long amounts (e.g. ₹1,70,60,704) pushing the `NET VALUE` badge outside the card: value font scales and the badge wraps below. |
| 23 Nov 2026 | Workflow Status chart changed from vertical bars (`frappe.Chart`) to horizontal bars. |
| 23 Nov 2026 | Removed the Fewest Purchase Orders list. Added Supplier-wise Purchase Orders with drill-down (creator → supplier → POs → List View), backed by `_get_po_supplier_orders`. Creator rows now drill down; the ↗ button opens the List View. |
