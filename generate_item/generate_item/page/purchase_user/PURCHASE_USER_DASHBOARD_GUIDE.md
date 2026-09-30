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

## 4. UI Actions & Drill-Down Routing (`purchase_user.js`)

1. **Card Click (Modal Popup)**:
   * Opens `#pud-modal` displaying parent documents (`it.ao`), dates (`it.date`), creators (`it.who`), and branches (`it.branch`).
   * Expanding a document reveals the table of child items (`it.doc_items`) with item codes, names, pending quantities, schedule dates, and amounts.
2. **List View Button ([↗ List])**:
   * Directly routes to ERPNext standard List View with pre-populated filters matching the active card stage, branch, and date range.
3. **Section 02 (Document Intensity)**:
   * Groups documents into `1 Item`, `2 Items`, `3 Items`, and `3+ Items` buckets with branch distribution. Clicking any bucket opens the matching document modal.
4. **Section 03 (Item-wise Summary Table)**:
   * Aggregates line items by `(item_code, stage_id)`. Includes live multi-column search and **Export CSV** download.
5. **Section 04 (Leaderboards)**:
   * Ranks buyers by PO count and grand total. Clicking any buyer opens their Purchase Orders in ERPNext List View.

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
