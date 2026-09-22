# Purchase User Dashboard — Functional User Guide & Documentation

## 1. Overview
The **Purchase User Dashboard** provides real-time operational visibility and executive insights across the end-to-end procurement cycle in ERPNext. It tracks and measures Material Requests (MR), Purchase Orders (PO), Purchase Receipts (PR), and Purchase Invoices (PI), enabling purchase managers and officers to identify bottlenecks, optimize item fulfillment, and track team output.

---

## 2. Dashboard Layout & Navigation

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│  HEADER: Title & Operational Summary                                                  │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  FILTER TOOLBAR: Branch · User · Date Range Preset · Date Picker · Today · Reset · Ref │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  TOP KPI CARDS: MR Pending · MR Completed · PR Pending · PI Pending · PI Completed    │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  SECTION 01: Material Request Trend (Item-wise Line Chart / Area Chart)               │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  SECTION 02: Document Intensity (Document-wise Batching Analysis)                     │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  SECTION 03: Item Intensity (Item-wise Batching & Searchable Table with CSV Export)   │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  SECTION 04: Creator Leaderboards (Most Purchase Orders & Fewest Purchase Orders)     │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Global Filters & Toolbar

| Control | Description | Functional Behavior |
| :--- | :--- | :--- |
| **Branch Filter** | Multi-branch dropdown | Filters all metrics, charts, tables, and leaderboards by the selected operating branch or plant. |
| **User / Owner Filter** | User search dropdown | Filters dashboard metrics by the creator (`owner`) of the procurement documents. |
| **Date Preset Selector** | Quick range dropdown | Select from predefined periods: `Today`, `This Week`, `This Month`, `This Quarter`, `This Year`, `Last Month`, or `Custom`. Automatically calculates comparative previous period ranges for delta calculations. |
| **Date Range Inputs** | From Date & To Date | Custom start and end date pickers (active when `Custom` preset is selected). |
| **Today Shortcut** | Quick button | One-click shortcut to set the active filter to today's date. |
| **Reset Button** | Ghost icon button | Clears all filters back to system defaults (`All Branches`, `All Users`, `This Month`). |
| **Refresh Button** | Solid action button | Triggers background data refresh without a full page reload. |

---

## 4. Top KPI Cards (Procurement Lifecycle)

The dashboard presents 5 primary lifecycle KPI cards at the top. Each card displays the total quantity/count, percentage change compared to the previous period, and an **"Open in List View"** shortcut.

```
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   MR PENDING    │ │  MR COMPLETED   │ │   PR PENDING    │ │   PI PENDING    │ │  PI COMPLETED   │
│   (PO Pending)  │ │   (PO Ordered)  │ │   (Receipt Due) │ │  (Invoice Due)  │ │(Billed & Closed)│
│                 │ │                 │ │                 │ │                 │ │                 │
│      1,240      │ │      3,890      │ │       412       │ │       285       │ │      3,150      │
│  ▲ +12% vs last │ │  ▲ +5% vs last  │ │  ▼ -3% vs last  │ │  ▲ +8% vs last  │ │  ▲ +14% vs last │
│  [↗ List View]  │ │  [↗ List View]  │ │  [↗ List View]  │ │  [↗ List View]  │ │  [↗ List View]  │
└─────────────────┘ └─────────────────┘ └─────────────────┘ └─────────────────┘ └─────────────────┘
```

### Stage Definitions & Business Logic:

1. **MR Pending (`po_pending`)**:
   - **Definition**: Material Requests that have been submitted (`docstatus = 1`) where line items still require a Purchase Order (`qty - ordered_qty > 0`).
   - **Click Action**: Opens a drill-down modal showing all pending Material Requests and item quantities.
   - **List View Button**: Directly opens `Material Request List` filtered by `status = 'Pending'`.

2. **MR Completed (`mr_completed`)**:
   - **Definition**: Material Requests where all line items have been fully ordered (`ordered_qty >= qty`).
   - **Click Action**: Opens a modal showing completed Material Requests.
   - **List View Button**: Directly opens `Material Request List` filtered by `status = 'Ordered'`.

3. **PR Pending (`pr_pending`)**:
   - **Definition**: Purchase Orders submitted (`docstatus = 1`) that are pending goods receipt / warehouse delivery (`per_received < 100%`).
   - **Click Action**: Opens a modal showing Purchase Orders awaiting receipt.
   - **List View Button**: Directly opens `Purchase Order List` filtered by `status = 'To Receive and Bill'` / `To Receive`.

4. **PI Pending (`pi_pending`)**:
   - **Definition**: Purchase Orders or Receipts awaiting supplier invoice booking (`per_billed < 100%`).
   - **Click Action**: Opens a modal showing pending purchase invoices.
   - **List View Button**: Directly opens `Purchase Order List` filtered by `status = 'To Bill'`.

5. **PI Completed (`pi_completed`)**:
   - **Definition**: Fully completed, received, and billed procurement cycles (`per_received >= 100%` and `per_billed >= 100%`).
   - **Click Action**: Opens a modal showing completed POs.
   - **List View Button**: Directly opens `Purchase Order List` filtered by `status = 'Completed'`.

---

## 5. Section 01 · Material Request Trend (Item-wise)

- **Purpose**: Displays the daily or weekly progression of procurement requirements over the selected timeframe.
- **Visuals**: Interactive dual-series area chart:
  - 🔵 **Total Items Requested**: Line item volume raised in Material Requests.
  - 🟢 **Items Ordered / Fulfilled**: Line item volume converted into Purchase Orders.
- **Interactivity**: Hover over data points to inspect date-wise counts, rates of fulfillment, and comparative volume.

---

## 6. Section 02 · Document Intensity (Document-wise)

- **Purpose**: Analyzes document complexity by grouping procurement transactions by the number of line items per document.
- **Stage Pills**: Filter between `All Stages`, `MR Pending`, `MR Ordered`, `PR Pending`, `PI Pending`, and `PI Completed`.
- **4 Complexity Buckets**:
  1. **Single Item (1 Item)**: Fast-track, single-line purchases.
  2. **2 Items**: Dual-item procurement.
  3. **3 Items**: Medium-sized purchase documents.
  4. **4+ Items (Heavy)**: Complex, high-density multi-line orders requiring extra attention.
- **Branch Breakdown**: Each card displays a mini bar graph and branch-specific item counts (e.g. *Plant 1, Plant 2, Corporate*).
- **Drill-Down**: Clicking any intensity card opens a modal listing all matching documents with clickable links.

---

## 7. Section 03 · Item Intensity & Live Searchable Table

### A. Item Intensity Buckets
Categorizes individual line items based on how many separate procurement documents they appear in during the selected period:
- **Single Doc (1)**: Items appearing in only 1 purchase document.
- **2 Docs**: Moderately requested items.
- **3 Docs**: Frequently requisitioned items.
- **4+ Docs (High Frequency)**: High-demand items requiring consolidated bulk purchasing agreements.

### B. Searchable Item Table
A real-time, interactive table embedded directly below the intensity cards:
- **Instant Search**: Type item code, item name, or linked document number to instantly filter line items.
- **Stage Tabs**: Quick buttons with live count pills (`All Items`, `MR Pending`, `MR Ordered`, `PR Pending`, `PI Pending`, `PI Completed`).
- **Columns Displayed**:
  - `Item Code` (Clickable link to Item master)
  - `Item Name` & `Supplier`
  - `Stage Badge`
  - `Pending Qty` with colored alert tags (amber if pending, green if 0)
  - `Total Qty` & `UOM`
  - `Est. Amount` (Formatted in `₹` INR currency)
  - `Branch / Warehouse`
  - `Linked Documents` (Clickable chips routing directly to source Material Request or Purchase Order forms)
- **CSV Export**: Click the **"Export CSV"** button to download all filtered line items into an Excel-ready `.csv` file.

---

## 8. Section 04 · Creator Leaderboard (Purchase Orders)

Provides performance visibility into user workload and procurement throughput.

```
┌──────────────────────────────────────┐  ┌──────────────────────────────────────┐
│  🏆 MOST PURCHASE ORDERS             │  │  📉 FEWEST PURCHASE ORDERS           │
│  Top creators by submitted PO count  │  │  Creators with lower PO volume       │
├──────────────────────────────────────┤  ├──────────────────────────────────────┤
│  🔍 Search creator...                │  │  🔍 Search creator...                │
│                                      │  │                                      │
│  🥇 [JD] John Doe       42 POs · ₹12L│  │  1.  [AS] Alice Smith   2 POs · ₹45K │
│  🥈 [RK] Rahul Kumar    35 POs · ₹8.5L│ │  2.  [VK] Vikas K       3 POs · ₹80K │
│  🥉 [PS] Priya Sharma   28 POs · ₹6.1L│ │  3.  [NB] Neha B        4 POs · ₹1.1L│
│  4.  [AM] Amit Mehta    19 POs · ₹4.2L│ │  4.  [RP] Ravi Patel    5 POs · ₹1.8L│
│  5.  [SK] Suresh K      14 POs · ₹2.9L│ │  5.  [MK] Manoj K       6 POs · ₹2.2L│
│                                      │  │                                      │
│  [ ▼ View More ]                     │  │  [ ▼ View More ]                     │
└──────────────────────────────────────┘  └──────────────────────────────────────┘
```

### Key Leaderboard Features:
1. **Most Purchase Orders (Left Card)**:
   - Ranks users in descending order of submitted Purchase Orders (`docstatus = 1`).
   - Highlights top 3 performers with gold (🥇), silver (🥈), and bronze (🥉) medals.
2. **Fewest Purchase Orders (Right Card)**:
   - Ranks users in ascending order to identify team members who may have capacity or require re-allocation.
3. **Metrics per User**:
   - Initials Avatar with distinctive color palette.
   - Total submitted PO count (`X POs`).
   - Total currency value badge (`₹ Amount`).
   - Proportional visual progress bar.
4. **Interactive Controls**:
   - **In-card Search**: Live filter creators by typing their name or email.
   - **View More Toggle**: Defaults to top 5 users; click `View More` to expand the full list of contributors.
   - **Open in List View on Click**: Clicking any creator row immediately opens the **Purchase Order List View** filtered by that creator (`owner = user`), submitted status (`docstatus = 1`), and active dashboard date/branch filters.
   - **Header List View Button**: Click the `List View` button in the card header to view all Purchase Orders in the period.
   - **Export CSV**: Export creator breakdown data to CSV with one click.

---

