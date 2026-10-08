# Sales Performance Dashboard — Functional Documentation

## 1. Executive Overview

The **Sales Performance Dashboard** provides real-time visibility into sales pipelines, approval lifecycles, order execution efficiency, on-time delivery (OTD) adherence, revenue achievements, and operational bottlenecks across company branches.

---

## 2. Dashboard Filters

The toolbar allows filtering data dynamically across three primary dimensions:

| Filter Name | Available Options | Default Value | Functional Scope & Behavior |
| :--- | :--- | :--- | :--- |
| **View Type** | `Sales`, `Purchase` | `Sales` | Controls dashboard domain context (Sales analytics). |
| **Branch** | `All Branches`, `Sanand`, `Nandikoor`, `Rabale` | `All Branches` | Slices data by the manufacturing plant or business branch. When `All Branches` is selected, all company records are combined. |
| **Period / Date Range** | `Today`, `This Week`, `Last Week`, `This Month`, `Last Month`, `This Quarter`, `Last Quarter`, `This Year`, `Last Year`, `Custom` | `This Quarter` | Sets the date window (`From Date` to `To Date`). In `Custom` mode, users select exact start and end dates. |

---

## 3. Metric-by-Metric Functional Breakdown

---

### Section 1: Orders & Pipeline Analysis

#### 1. Orders by Status
* **Goal:** Visualizes how sales orders created in the selected date range are distributed across their lifecycle stages.
* **DocType Source:** `Sales Order`
* **Filters Applied:**
  * **Date Range:** `Sales Order.transaction_date` within the selected period.
  * **Branch:** `Sales Order.branch` matches the selected branch (if filtered).
  * **Document Status:** Excludes cancelled and closed orders (`docstatus < 2` and `status NOT IN ('Closed', 'Cancelled')`).
* **Categorization Conditions:**
  * **Pending Approval:** Unsubmitted orders with workflow state set to `Approval Pending` or `Checking Pending`.
  * **Draft:** Unsubmitted orders in initial `Draft` stage.
  * **Approved:** Submitted & active orders (`docstatus = 1`).
* **Output Display:**
  * Total order count per status.
  * Total grand total value per status (formatted in ₹ Lakhs).

---

#### 2. Order Approval Delay
* **Goal:** Highlights the aging backlog of sales orders currently awaiting approval or checking.
* **DocType Source:** `Sales Order`
* **Filters Applied:**
  * **Document Status:** Unsubmitted orders (`docstatus = 0`).
  * **Workflow State:** `Approval Pending` or `Checking Pending`.
  * **Date Range:** `Sales Order.transaction_date` within the selected period (when date filter is active).
  * **Branch:** Matches selected branch.
* **Delay Calculation:**
  $$\text{Delay (Days)} = \text{Current Date (Today)} - \text{Sales Order Transaction Date}$$
* **Aging Buckets:**
  * `0 to 7 Days`
  * `8 to 15 Days`
  * `16 to 30 Days`
  * `31 to 45 Days`
  * `46 to 60 Days`
  * `> 60 Days`
* **Output Display:** Bar chart showing order count and monetary value (in ₹ Lakhs) across each delay bracket.

---

### Section 2: On-Time Delivery (OTD) Performance

---

#### 3. Delivery OTD (On-Time Delivery)
* **Goal:** Measures how reliably deliveries are fulfilled on or before the committed scheduled delivery date.
* **DocType Source:** `Delivery Note`, `Delivery Note Item`, `Sales Order`
* **Filters Applied:**
  * **Date Range:** `Delivery Note.posting_date` within the selected period.
  * **Branch:** `Delivery Note.branch` matches selected branch.
  * **Status:** Submitted and non-cancelled delivery notes (`docstatus = 1` and `status NOT IN ('Cancelled', 'Closed')`).
  * **Linkage:** Only includes line items linked to a valid Sales Order with an established delivery schedule.
* **Evaluation Condition:**
  * **On-Time:** `Actual Delivery Date (DN Posting Date)` $\le$ `Scheduled Delivery Date (SO Delivery Date)`
  * **Delayed:** `Actual Delivery Date (DN Posting Date)` $>$ `Scheduled Delivery Date (SO Delivery Date)`
* **Output Display:** Donut chart with percentage breakdown, item count, and delivery value in ₹ Lakhs.

---

#### 4. Order Entry OTD
* **Goal:** Measures speed of booking an order in the system after receiving the customer's purchase order.
* **DocType Source:** `Sales Order`
* **Filters Applied:**
  * **Date Range:** `Sales Order.transaction_date` within the selected period.
  * **Branch:** Matches selected branch.
  * **Status:** Submitted, active orders (`docstatus = 1` and `status NOT IN ('Closed', 'Cancelled')`).
  * **Data Integrity:** Requires `Customer PO Date (po_date)` to be present.
* **Evaluation Condition (3-Day SLA):**
  * **On-Time:** `Sales Order Date` $-$ `Customer PO Date` $\le$ **3 Days**
  * **Delayed:** `Sales Order Date` $-$ `Customer PO Date` $>$ **3 Days**
* **Output Display:** Donut chart with on-time percentage, order count, and value in ₹ Lakhs.

---

#### 5. Order Approval OTD
* **Goal:** Evaluates internal turnaround time taken by managers to approve and submit sales orders.
* **DocType Source:** `Sales Order`
* **Filters Applied:**
  * **Date Range:** `Sales Order.transaction_date` within the selected period.
  * **Branch:** Matches selected branch.
  * **Status:** Submitted, active orders (`docstatus = 1` and `status NOT IN ('Closed', 'Cancelled')`).
* **Evaluation Condition (5-Day SLA):**
  * **On-Time:** `Approval Date` $-$ `Sales Order Date` $\le$ **5 Days**
  * **Delayed:** `Approval Date` $-$ `Sales Order Date` $>$ **5 Days**
* **Output Display:** Donut chart with on-time compliance rate, order count, and value in ₹ Lakhs.

---

### Section 3: Financial & Operational Metrics

---

#### 6. Order Booking Value
* **Goal:** Tracks new booking revenue generated in the current financial year and current calendar month.
* **DocType Source:** `Sales Order`
* **Filters Applied:**
  * **Status:** Submitted and active (`docstatus = 1` and `status NOT IN ('Closed', 'Cancelled')`).
  * **Branch:** Matches selected branch.
* **Time Windows Evaluated:**
  * **Current Financial Year (FY):** Orders where `transaction_date` falls between the active Fiscal Year start date (e.g. April 1) and end date (e.g. March 31).
  * **Current Month:** Orders where `transaction_date` belongs to the current calendar month and year.
* **Output Display:**
  * Values in **₹ Lakhs**
  * Converted values in **USD ($)** using active exchange rates from `Currency Exchange`.

---

#### 7. Invoicing Value (Sales Revenue)
* **Goal:** Quantifies actual billed revenue for the current fiscal year and current month.
* **DocType Source:** `Sales Invoice`
* **Filters Applied:**
  * **Status:** Submitted invoices (`docstatus = 1`).
  * **Branch:** Matches selected branch.
* **Time Windows Evaluated:**
  * **Current Financial Year (FY):** Invoices with `posting_date` within the current fiscal year.
  * **Current Month:** Invoices with `posting_date` in the current month.
* **Output Display:**
  * Billed totals in **₹ Lakhs**
  * Billed totals in **USD ($)**.

---

#### 8. Outstanding vs Collection
* **Goal:** Compares newly generated unpaid customer dues against payments collected during the current month.
* **DocType Source:** `Sales Invoice` (for Outstanding) and `Payment Entry` (for Collections).
* **Filters Applied:**
  * **Branch:** Applied to both invoices and payment entries.
  * **Outstanding Revenue:** Sum of `outstanding_amount` from submitted `Sales Invoice` documents posted in the current month.
  * **Collections Received:** Sum of `paid_amount` from submitted `Payment Entry` documents where `payment_type = 'Receive'` posted in the current month.
* **Output Display:** Comparative card showing Outstanding vs Collected amounts in ₹ Lakhs.

---

#### 9. BOM Release Pending (Bill of Materials Delay)
* **Goal:** Identifies production-readiness bottlenecks where booked sales orders cannot proceed to manufacturing because the engineering BOM is missing or not submitted.
* **DocType Source:** `Sales Order`, `Sales Order Item`, `BOM`
* **Filters Applied:**
  * **Sales Order Status:** Submitted, active orders (`docstatus = 1` and not cancelled/closed).
  * **Branch:** Matches selected branch.
  * **Pending BOM Criteria:** Line items where:
    * No BOM is linked (`bom_no` is blank/null), OR
    * The linked `BOM` is in draft/unsubmitted state (`BOM.docstatus != 1`).
* **Delay Calculation:**
  $$\text{Delay (Days)} = \text{Current Date (Today)} - \text{Sales Order Creation Date}$$
* **Aging Buckets:** Grouped into `0-7`, `8-15`, `16-30`, `31-45`, `46-60`, and `>60` days.
* **Output Display:** Bar chart displaying unreleased item counts and monetary value in ₹ Lakhs.

---

## 4. Summary of Filter Impact Across Metrics

| Metric / Chart Name | Branch Filter | Period / Date Filter | Current Month / FY Rule |
| :--- | :---: | :---: | :---: |
| **Orders by Status** | Applied | Applied (`transaction_date`) | Range-bound |
| **Order Approval Delay** | Applied | Applied (`transaction_date`) | Open Backlog |
| **Delivery OTD** | Applied | Applied (`posting_date`) | Range-bound |
| **Order Entry OTD** | Applied | Applied (`transaction_date`) | Range-bound |
| **Order Approval OTD** | Applied | Applied (`transaction_date`) | Range-bound |
| **Order Booking Value** | Applied | System-defined | FY & Current Month |
| **Invoicing Value** | Applied | System-defined | FY & Current Month |
| **Outstanding vs Collection** | Applied | System-defined | Current Month |
| **BOM Release Pending** | Applied | Open Backlog | Open Backlog |
