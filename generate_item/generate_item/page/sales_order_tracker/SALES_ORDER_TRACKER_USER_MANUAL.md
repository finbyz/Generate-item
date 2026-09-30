# Sales Order Tracker Dashboard — User & Client Guide

The **Sales Order Tracker Dashboard** is a centralized, end-to-end operational visibility tool designed for manufacturing, project management, supply chain, and finance teams. It delivers 360-degree traceability across the complete order fulfillment cycle—from Quotation to Delivery and Payment reconciliation.

---

## 1. Overview & Key Capabilities

* **Sales Order & Batch-Centric Traceability**: Track your orders at either the granular **Batch Level** (manufacturing lot / item line) or high-level **Sales Order Level**.
* **End-to-End Document Chain**: Seamlessly connects all 16 ERPNext document types in the order lifecycle:
  $$\text{Quotation} \rightarrow \text{Sales Order} \rightarrow \text{BOM} \rightarrow \text{Production Plan} \rightarrow \text{Material Request} \rightarrow \text{Purchase Order} \rightarrow \text{Receipt / Invoice} \rightarrow \text{Delivery Note} \rightarrow \text{Sales Invoice} \rightarrow \text{Payment Entry}$$
* **Live Status & Smart Stage Detection**: Instantly see which active stage an order or batch is currently at (e.g., *Production Plan*, *Material Request*, *Purchase Order*, *Purchase Receipt*, *Delivery Note*, or *Completed*).
* **Automated Priority Calculation**: Automatically classifies orders as *Critical*, *High*, *Normal*, or *Low* based on real-time delivery dates and downstream stage completion.
* **Interactive Quick Preview & Multi-Doc Browsing**: Click any document pill or card to inspect live values, line items, amounts, suppliers, and statuses without navigating away from the dashboard.

---

## 2. Accessing & Navigating the Dashboard

### Access Path
Navigate via the ERPNext desk sidebar or search bar:
> **Desk Search** $\rightarrow$ Type `Sales Order Tracker` $\rightarrow$ Open **Sales Order Tracker** (Route: `/app/sales-order-tracker`)

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│  Sales Order Tracker Dashboard                                             [🌙 Theme]  │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  [📅 Date Range]  [🏷️ Status: Open Orders]  [🏢 Branch]  [👥 Customer]     [🔍 Search] │
│  [📋 Sales Order] [📦 Batch No]             [⚙️ Item Code] [🏢 Company]    [🔄 Reset]  │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  [🔘 Batch Wise View]   [⚪ Sales Order Wise View]       [📥 Export]  [Page 1 of 12]   │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Dashboard Filters
| Filter | Options / Types | Description & Default Behavior |
| :--- | :--- | :--- |
| **Date Range** | `Monthly (Last 30 Days)`, `Quarterly (Last 3 Months)`, `This Financial Year`, `Previous Financial Year`, `Weekly (Last 7 Days)`, `All Time`, `Custom Range` | Automatically filters by Sales Order Transaction Date. Default: *Monthly (Last 30 Days)*. |
| **Status** | `Open Orders (Default)`, `On Hold`, `To Deliver and Bill`, `To Bill`, `To Deliver`, `Completed`, `Closed`, `All` | Excludes completed and closed orders by default for operational focus. |
| **Branch** | Link: `Branch` | Filters orders and linked manufacturing documents by Branch / Plant location (e.g. *Sanand*). |
| **Customer** | Link: `Customer` | Select a specific customer account with instant autocomplete lookup. |
| **Sales Order** | Link: `Sales Order` | Direct search for a specific Sales Order number (e.g. `SODS25229`). |
| **Batch No** | Text / Autocomplete | Direct search for an item batch number (e.g. `SODS25229-013`). |
| **Item Code** | Link: `Item` | Filter by Finished Good (FG) item code. |
| **Company** | Link: `Company` | Pre-filled with user's default company. |

---

## 3. View Modes: Batch Wise vs. Sales Order Wise

You can switch between two views using the view toggle:

### A. Batch Wise View (Recommended for Plant & Production Operations)
* Breaks down each Sales Order into its individual item lines and manufacturing batches.
* Displays batch numbers, Finished Good descriptions, ordered vs. delivered quantities, line amounts, promised delivery dates, and batch-specific BOM and procurement trails.

### B. Sales Order Wise View (Recommended for Sales, Commercial & Finance Teams)
* Aggregates item lines into a single master row per Sales Order.
* Displays total order quantity, total order value, combined document counts, and nested item line expandable drawers.

---

## 4. Table Columns & Indicators

```
┌────────────┬─────────────┬─────────────┬──────────────┬──────────────┬──────────────┬──────────────┬───────────┐
│  Batch No  │  Item Code  │ Sales Order │  Recent Doc  │     BOM      │      PP      │      PO      │  Priority │
├────────────┼─────────────┼─────────────┼──────────────┼──────────────┼──────────────┼──────────────┼───────────┤
│ SODS25229  │ Valve GTV   │  SODS25229  │Purchase Order│   Approved   │  PPOS252185  │  SD2502361   │  NORMAL   │
│   -013     │   DN50      │             │              │  (Clickable) │  (Completed) │ (19 Orders)  │           │
└────────────┴─────────────┴─────────────┴──────────────┴──────────────┴──────────────┴──────────────┴───────────┘
```

### Column Guide

1. **Batch No**: The manufacturing batch code assigned to the line item.
2. **Item Code & Name**: Finished Good item code and descriptive item title.
3. **Sales Order**: Clickable Sales Order reference link.
4. **Customer**: Customer company name.
5. **Qty & Delivered Qty**: Ordered quantity and already dispatched quantity.
6. **Amount**: Line item selling price total.
7. **Delivery Date**: Target delivery date commitment.
8. **Branch**: Manufacturing plant or branch location.
9. **Recent Document (Smart Stage Progression)**:
   * Dynamically tracks the current active processing stage.
   * Progression path: $\text{Quotation} \rightarrow \text{Sales Order} \rightarrow \text{BOM} \rightarrow \text{Production Plan} \rightarrow \text{Material Request} \rightarrow \text{Purchase Order} \rightarrow \text{Purchase Receipt} \rightarrow \text{Delivery Note} \rightarrow \text{Sales Invoice} \rightarrow \text{Completed}$.
   * *Smart Downstream Detection*: Advances past Material Request to Purchase Order when POs are placed, avoiding false bottlenecks.
10. **Linked Document Columns**:
   * **BOM**: Displays **`Approved`** (green badge) if submitted or **`Pending`** (amber badge) if draft. Clicking opens the BOM record.
   * **PP (Production Plan)**: Shows the Production Plan reference and status (*Completed*, *In Process*, *Draft*).
   * **MR (Material Request)**: Shows raw material indents generated for this batch.
   * **PO (Purchase Order)**: Displays single PO reference or multi-order pill (e.g. `16 Purchase Orders →`).
   * **PR (Purchase Receipt)**: Goods receipt notes for incoming raw materials.
   * **PI (Purchase Invoice)**: Supplier invoices generated against purchase orders.
   * **DN (Delivery Note)**: Outbound dispatch notes for finished goods.
   * **SI (Sales Invoice)**: Customer sales invoices and billing status.
11. **Priority Badges**:
   * 🔴 **`CRITICAL`**: Order is overdue past delivery date and pending fulfillment.
   * 🟠 **`HIGH`**: Delivery date is due within the next 7 days.
   * 🔵 **`NORMAL`**: On schedule with delivery date beyond 7 days.
   * 🟢 **`LOW` / `COMPLETED`**: Order fulfilled and delivered.

---

## 5. Interactive Features & Modals

### 1. Single Document Quick Preview Modal
Click any individual document link (e.g. `SD2502361`, `PPOS252185`, `PIES2600616`):
* A modal popup displays immediate key details:
  * Document Status & Workflow State
  * Posting / Creation Date, Supplier or Customer
  * Complete Item Breakdown Table (Item Codes, Quantities, Rates, Amounts)
  * Direct action button: **`Open in New Tab`** to access the full ERPNext form.

### 2. Multi-Document Browse Modal
When multiple documents exist (e.g. `42 Purchase Invoices →` or `31 Purchase Receipts →`):
* Click the multi-document pill to open the **Linked Documents List**.
* Lists all linked records with document name, creation date, supplier/party, grand total, and status badge.
* Click any row to preview its full item breakdown.

---

## 6. Detailed 360° View

Click the arrow button (**`→`**) on any row to open the complete **Detailed View**:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│  SALES ORDER: SODS25229 · BATCH: SODS25229-013                             [← Back]    │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  [💰 Revenue: ₹3,52,800]    [📦 RM Cost: ₹3,65,747]    [📊 Estimated Margin: -3.6%]    │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  LINKED DOCUMENTS (16 Flow Cards):                                                     │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐  │
│  │ BOM       │ │ PROD PLAN │ │ MAT REQ   │ │ PO        │ │ PR        │ │ PI        │  │
│  │ Approved  │ │ PPOS252185│ │ PMRS252783│ │ SD2502361 │ │ 2 Receipts│ │ 2 Invoices│  │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘ └───────────┘ └───────────┘  │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐  │
│  │ DEL NOTE  │ │ SALES INV │ │ REC PAY   │ │ PAID PAY  │ │ STOCK REQ │ │ JOURNAL   │  │
│  │ ODNS260131│ │ INDS2600112│ │ Not Gen   │ │PEFS2600002│ │ MSES260263│ │ Not Gen   │  │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘ └───────────┘ └───────────┘  │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  ORDER ITEMS & BILL OF MATERIALS (BOM) CONSUMPTION TABLE                               │
│  - Finished Good Items, Rates & Delivered Quantities                                   │
│  - Sub-Assembly Kits & Raw Material Components Required                                │
│  - Actual Consumed Stock vs. Item Valuation Rates                                      │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Detailed View Highlights:
1. **Financial Overview KPIs**:
   * **Revenue**: Total Selling Value of the order / batch.
   * **Raw Material Cost**: Calculated component valuation rate $\times$ quantity required.
   * **Estimated Profit & Gross Margin %**: Live estimated profitability.
2. **Linked Document Catalog (16 Flow Cards)**:
   * Real-time cards for all upstream and downstream records.
   * Supplier Payments (**Payment Paid / PPD**) and Customer Collections (**Payment Received / PREC**) are automatically tracked.
3. **BOM & Material Consumption Table**:
   * Lists the Finished Good and all sub-assembly components, kits, and raw materials needed.
   * Displays quantities needed, valuation rates, and consumption entries.

---

## 7. Document Traceability Reference Table

| Key | Stage Label | DocType | Traceability Link Logic |
| :--- | :--- | :--- | :--- |
| `quote` | Quotation | `Quotation` | `Sales Order Item.prevdoc_docname` or `Sales Order.quotation_no` |
| `so` | Sales Order | `Sales Order` | Primary anchor document |
| `bom` | BOM | `BOM` | Finished Good item match + Batch link + Default BOM fallback |
| `pp` | Production Plan | `Production Plan` | `Production Plan Item.sales_order` / `custom_batch_no` / `sales_order_item` |
| `mr` | Material Request | `Material Request` | `Material Request Item.production_plan` or `Production Plan Material Request` |
| `po` | Purchase Order | `Purchase Order` | `Purchase Order Item.material_request` or `Purchase Order Item.sales_order` |
| `pr` | Purchase Receipt | `Purchase Receipt` | Linked Purchase Orders $\rightarrow$ `Purchase Receipt Item.purchase_order` |
| `pi` | Purchase Invoice | `Purchase Invoice` | Linked Purchase Orders $\rightarrow$ `Purchase Invoice Item.purchase_order` |
| `sr` | Stock Requisition | `Stock Entry` | Stock transfers and requisitions linked to the batch |
| `pe_out`| Payment Paid (PPD)| `Payment Entry` | Payments referencing linked Purchase Invoices or Purchase Orders (`payment_type = 'Pay'`) |
| `dn` | Delivery Note | `Delivery Note` | `Delivery Note Item.against_sales_order` / `so_detail` / `batch_no` |
| `si` | Sales Invoice | `Sales Invoice` | `Sales Invoice Item.sales_order` / `so_detail` / `batch_no` |
| `pe_in` | Payment Received | `Payment Entry` | Payments referencing linked Sales Invoices or Sales Orders (`payment_type = 'Receive'`) |
| `je` | Journal Entry | `Journal Entry` | `Journal Entry Account.reference_name` linked to Sales Order |

---

## 8. Role Permissions & Security

Access to the **Detailed View** and financial gross margins can be restricted:
1. Go to **Selling Settings** in ERPNext.
2. Configure: **`Role Allowed to Detail View Sales Order Tracker`**.
3. Set the designated role (e.g. *Sales Manager*, *Accounts Manager*, or leave empty for *System Manager / Administrator* only).
4. Users without the configured role can browse the Status Overview list but cannot access detailed financial margins.

---

## 9. Frequently Asked Questions (FAQ)

**Q: Why does a batch row show "Approved" for BOM instead of a BOM number?**  
A: To keep the dashboard clean and actionable, the BOM column confirms whether an authorized Finished Good BOM exists and is approved. Clicking the badge opens the exact BOM record.

**Q: Why do cancelled documents not show up in the counts?**  
A: Cancelled documents (`docstatus = 2`) are filtered out automatically so counts and status indicators only reflect active, valid transactions.

**Q: Why does the Recent Document stage jump to Purchase Order if Material Request is still open?**  
A: The tracker uses smart downstream progression. If a Purchase Order has already been placed against the Material Request, the active operational stage advances to Purchase Order.

**Q: How do supplier payments appear under Payment Paid?**  
A: When a Payment Entry of type *Pay* is submitted against any Purchase Invoice or Purchase Order associated with the order's procurement, it automatically links and appears in the Payment Paid card.
