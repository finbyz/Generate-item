# Financial Dashboard — Functional Team User & Testing Guide

**Module**: Financial Dashboard (`financial-dashboard`)  
**App**: `generate_item`  
**Compatibility**: Frappe v16 + ERPNext v16  
**Target Audience**: Functional Consultants, QA Engineers, Finance Team, Business Analysts  
**Desk Route**: `/app/financial-dashboard`  

---

## 1. Executive Summary & Objective

The **Financial Dashboard** is an executive-grade analytics page designed for CFOs, Financial Controllers, and Operations Leaders. It consolidates real-time data from core ERPNext sub-ledgers (General Ledger, Sales Orders, Sales Invoices, Purchase Invoices, Work Orders, Delivery Notes, Accounts Receivable, and Accounts Payable) into a unified, interactive cockpit without requiring external BI tools.

### Key Capabilities
- **Real-Time Ledger Integration**: Synchronized directly with live `GL Entry` and ERPNext transactions.
- **7 Core Financial & Operational Modules**: Revenue & Operating Margins, Multi-Unit Sales, Multi-Unit Purchases, Monthly Order Booking, Backlog Pipeline, AR Ageing (DSO), and AP Ageing (DPO).
- **Executive KPI Strip**: Summary tiles with Year-over-Year (YoY) variances and run-rates.
- **Interactive Drill-Downs**: Direct 1-click navigation from any dashboard card to underlying ERPNext reports and document lists.
- **Dynamic Granularity**: Switch views between Annual, Quarterly, and Monthly intervals across configurable dimensions (Cost Center, Branch, Company).

---

## 2. Dashboard Architecture & How It Works

### 2.1 System Data Flow

```
[ User Browser / Frappe Desk: /app/financial-dashboard ]
                    │
                    ▼
[ Frontend Controller: financial_dashboard.js ]
  • Local Chart.js Rendering Engine
  • Granularity & Dimension Toggles
  • Drill-Down Routing to ERPNext Reports
                    │
                    ▼  (Frappe Whitelisted RPC)
[ Backend Analytics Engine: financial_dashboard.py ]
  • Query Builder & Ledger Aggregations
  • Due-Date Ageing Engine (AR/AP Reports)
  • Company & Document Permission Boundaries
                    │
                    ▼
[ ERPNext Core Ledgers & Tables ]
  • GL Entry & Account (Income / Expense)
  • Sales Order & Sales Invoice
  • Purchase Invoice
  • Work Order, Delivery Note, Quality Inspection
  • Accounts Receivable & Accounts Payable Ledger Summary
```

### 2.2 Backend Endpoints

* **`get_overview`** (`financial_dashboard.py`):  
  Fetches KPI strip metrics, Monthly Revenue & Margin (Item 1), Orders Booked (Item 4), Pending Backlog (Item 5), AR Ageing (Item 6), and AP Ageing (Item 7).
* **`get_unit_series`** (`financial_dashboard.py`):  
  Fetches multi-unit time series for Sales (Item 2) and Purchases (Item 3) across selected grains (Years, Quarters, Months) and dimensions (Cost Center, Branch, Company).

### 2.3 Security & Permissions
- Access requires read permissions on **`GL Entry`** and the target **`Company`**.
- Accessible to standard roles: `Accounts Manager`, `Accounts User`, `System Manager`, `Sales Manager`.
- Multi-company access is strictly enforced: users only see records for companies authorized in their Frappe User Permissions.

---

## 3. Detailed Module Specifications & Formulas

### 3.1 KPI Summary Strip

| KPI Metric | Source & Exact Calculation | Business Meaning |
|---|---|---|
| **Net Revenue** | `Sum(Credit - Debit)` on `GL Entry` where `Account.root_type = 'Income'` and `is_cancelled = 0` | Total recognized operational income in the selected Fiscal Year. |
| **Operating Margin %** | `((Income - Expense) / Income) * 100`<br>where `Expense = Sum(Debit - Credit)` for `Account.root_type = 'Expense'` | Operational profitability before non-operating items. |
| **Orders Booked** | `Count(name)` & `Sum(base_net_total)` of `Sales Order`<br>where `docstatus = 1` and `status != 'Cancelled'` | Commercial order volume contracted during the fiscal year. |
| **Book-to-Bill Ratio** | `Total Booked Sales Orders Value / Total Net Sales Invoices Value` | Ratio > 1.0 indicates growing pipeline; < 1.0 indicates backlog depletion. |
| **Pending Backlog** | `Sum(base_grand_total * ((100 - per_delivered) / 100))` for open submitted Sales Orders | Unfulfilled commercial commitment value awaiting delivery or billing. |
| **% on SLA** | `(Pending Orders with Delivery Date >= Today / Total Pending Orders) * 100` | On-time delivery schedule compliance percentage. |

---

### 3.2 Item 1: Revenue vs Operating Margin (Monthly View)
- **Chart Type**: Dual-Axis Combination Chart.
  - **Left Y-Axis (Bars)**: Net Revenue (Monthly Income).
  - **Right Y-Axis (Line)**: Operating Margin Percentage.
- **Controls**:
  - `Full Year (12M)`: Displays all 12 fiscal months.
  - `H1 (First Half)`: Months 1 to 6.
  - `H2 (Second Half)`: Months 7 to 12.
- **Insight Badges**: Automatically computes **Peak Revenue Month**, **Best Margin Month**, **Average Monthly Run-Rate**, and **Margin Spread**.

---

### 3.3 Item 2: Sales from Each Unit
- **Source**: `Sales Invoice Item` joined to `Sales Invoice` (`docstatus = 1`, net of credit notes).
- **Dimensions**: `Cost Center` (Default), `Branch`, `Company`.
- **Granularities**:
  - `Years`: 3-Year rolling trend (Selected FY + 2 preceding FYs).
  - `Quarters`: Q1, Q2, Q3, Q4 of selected FY.
  - `Months`: 12-Month breakdown.
- **Display**: Top 4 revenue-generating units displayed individually; remaining units aggregated into `Other Units`.

---

### 3.4 Item 3: Purchases from Each Unit
- **Source**: `Purchase Invoice Item` joined to `Purchase Invoice` (`docstatus = 1`, net of debit notes).
- **Controls**:
  - Time Grain: `Years` / `Quarters` / `Months`.
  - Visual Layout Toggle: `Stacked Bar` vs `Grouped Bar`.
- **Display**: Top 4 procurement cost units + `Other Units`.

---

### 3.5 Item 4: No. of Orders Booked (Monthly View)
- **Source**: Submitted `Sales Order` grouped by `MONTH(transaction_date)`.
- **Visuals**:
  - Monthly bar volumes.
  - Quota / Benchmark Target line (budgeted quota or average monthly mean).
  - Attainment % badge showing percentage of annual target achieved.

---

### 3.6 Item 5: Pending Orders Status Lifecycle Pipeline
Classifies active unfulfilled `Sales Order` records into 5 operational stages:

| Stage | Color | Logic / ERPNext Linked State |
|---|---|---|
| **Payment Hold** | Red | SO status is `On Hold` or has an open `Payment Request`. |
| **In Transit** | Indigo | Linked to submitted `Delivery Note` not yet closed/cancelled. |
| **QA Inspection** | Blue | Linked to draft/in-progress `Quality Inspection`. |
| **Production** | Amber | Linked to active `Work Order` (`Not Started` or `In Process`). |
| **Open** | Emerald | Unscheduled open orders without active manufacturing or delivery links. |

---

### 3.7 Item 6: Accounts Receivable (AR) Ageing & DSO
- **Engine**: Live execution of standard ERPNext report `erpnext.accounts.report.accounts_receivable` based on **Due Date**.
- **Ageing Buckets**: `< 30 Days (Current)`, `31 - 60 Days`, `61 - 90 Days`, `> 90 Days (Overdue)`.
- **Days Sales Outstanding (DSO)** Formula:
  ```
  DSO = (Total AR Outstanding / YTD Net Revenue) * Days Elapsed in Period
  ```

---

### 3.8 Item 7: Accounts Payable (AP) Ageing & DPO
- **Engine**: Live execution of standard ERPNext report `erpnext.accounts.report.accounts_payable` based on **Due Date**.
- **Ageing Buckets**: `< 30 Days`, `31 - 60 Days`, `61 - 90 Days`, `> 90 Days (Critical)`.
- **Days Payable Outstanding (DPO)** Formula:
  ```
  DPO = (Total AP Outstanding / YTD Net Purchases) * Days Elapsed in Period
  ```

---

## 4. Functional Testing Matrix

| ID | Test Scenario | Pre-requisites | Expected Result | Status |
|---|---|---|---|:---:|
| **TC-01** | Page Load & Access Control | User with `Accounts Manager` | Page loads without error; KPI strip and all 7 charts render. | [ ] |
| **TC-02** | Security & Restricted User | User without `GL Entry` read | Access blocked with `PermissionError`. | [ ] |
| **TC-03** | Fiscal Year Switching | Multiple FYs configured | Data, labels, and YoY variance badges update immediately. | [ ] |
| **TC-04** | Net Revenue & Margin Match P&L | GL Entries exist in FY | Revenue & Margin match Profit and Loss Statement. | [ ] |
| **TC-05** | Orders Booked Match SO List | Submitted Sales Orders exist | Count and Base Net Total match Sales Order List summary. | [ ] |
| **TC-06** | Sales by Unit Match Sales Register | Submitted Sales Invoices exist | Sum of all units in Item 2 matches Sales Register Net Total. | [ ] |
| **TC-07** | Purchases Match Purchase Register | Submitted Purchase Invoices exist | Sum of all units in Item 3 matches Purchase Register Net Total. | [ ] |
| **TC-08** | AR Ageing & DSO Match AR Report | Open customer invoices exist | Bucket amounts and Total AR match Accounts Receivable Report. | [ ] |
| **TC-09** | AP Ageing & DPO Match AP Report | Open supplier invoices exist | Bucket amounts and Total AP match Accounts Payable Report. | [ ] |
| **TC-10** | Item 1 Period Filter (Full/H1/H2) | 12 months of GL data | H1 displays months 1-6; H2 displays months 7-12; stats recalculate. | [ ] |
| **TC-11** | Unit Dimension Switching | Invoices tagged with Branch & Cost Center | Item 2 & 3 re-aggregate correctly under new dimension. | [ ] |
| **TC-12** | Pending Stage Transitions | Test Sales Order record | Linking WO shifts to Production; DN shifts to In Transit. | [ ] |
| **TC-13** | 1-Click Drill-Down Navigation | Click on KPI cards/charts | System redirects to correct report with pre-filled filters. | [ ] |
| **TC-14** | Live Sync & Refresh Action | Add a new GL Entry / SO | Refresh button updates totals without browser reload. | [ ] |

---

## 5. Step-by-Step Test Procedures

### Procedure 1: Reconciling Revenue & Margin with Profit & Loss (TC-04)
1. Open `/app/financial-dashboard`.
2. Note the **Company**, **Fiscal Year**, **Net Revenue**, and **Operating Margin %**.
3. Open a new tab and go to **Profit and Loss Statement** (`/app/query-report/Profit and Loss Statement`).
4. Set identical filters:
   - **Company**: Selected Company
   - **Fiscal Year**: Selected Fiscal Year
   - **Periodicity**: Monthly
5. **Validation Checks**:
   - Total **Income** on P&L must equal Dashboard **Net Revenue**.
   - `((Total Income - Total Expense) / Total Income) * 100` on P&L must equal Dashboard **Operating Margin %**.
   - Monthly income bars in Item 1 must match monthly income columns in the P&L table.

---

### Procedure 2: Reconciling Accounts Receivable & DSO (TC-08)
1. On `/app/financial-dashboard`, navigate to **Item 6: Accounts Receivable Ageing**.
2. Note the **Total Outstanding**, **DSO (Days)**, and bucket amounts (`< 30d`, `31-60d`, `61-90d`, `> 90d`).
3. Open **Accounts Receivable** report (`/app/query-report/Accounts Receivable`).
4. Set filters:
   - **Company**: Selected Company
   - **Ageing Based On**: `Due Date`
   - **Report Date**: Today (or FY End Date if testing a past FY)
   - **Ranges**: `30`, `60`, `90`, `120`
5. **Validation Checks**:
   - Total Outstanding in AR Report must match Dashboard AR Total.
   - Range 1 (`0-30`), Range 2 (`31-60`), Range 3 (`61-90`), and Range 4+5 (`91+`) must match dashboard buckets.

---

### Procedure 3: Reconciling Accounts Payable & DPO (TC-09)
1. On `/app/financial-dashboard`, navigate to **Item 7: Accounts Payable Ageing**.
2. Note the **Total Outstanding**, **DPO (Days)**, and bucket amounts.
3. Open **Accounts Payable** report (`/app/query-report/Accounts Payable`).
4. Set filters matching Due Date ageing.
5. **Validation Checks**:
   - Outstanding balances across all 4 buckets match the dashboard AP table and donut chart.

---

### Procedure 4: Testing Pending Orders Pipeline Stages (TC-12)
1. Create a new **Sales Order** (Net Total = ₹100,000) and Submit.
   - *Expected*: Dashboard Backlog count increases by 1; stage is **Open**.
2. Create and Submit a **Work Order** against this Sales Order (Status: `Not Started` or `In Process`).
   - *Expected*: Refresh dashboard -> Stage shifts from **Open** to **Production**.
3. Complete Work Order and create a draft **Quality Inspection** against this Sales Order.
   - *Expected*: Refresh dashboard -> Stage shifts to **QA Inspection**.
4. Create and Submit a **Delivery Note** against this Sales Order.
   - *Expected*: Refresh dashboard -> Stage shifts to **In Transit**.
5. Set Sales Order status to **On Hold**.
   - *Expected*: Refresh dashboard -> Stage shifts to **Payment Hold**.

---

### Procedure 5: Testing Drill-Down Links (TC-13)
1. Click **Revenue KPI Card** -> Opens `Profit and Loss Statement` with pre-filled Company and Fiscal Year.
2. Click **Orders Booked KPI Card** -> Opens `/app/sales-order` filtered by `docstatus = 1` and `transaction_date` within FY.
3. Click **AR Ageing Card** -> Opens `Accounts Receivable` report.
4. Click **AP Ageing Card** -> Opens `Accounts Payable` report.

---

## 6. Edge Cases & Boundary Handling

| Scenario | Condition | Expected System Behavior |
|---|---|---|
| **Zero Income / New Company** | No GL Entries in Fiscal Year | Revenue displays `₹0.00`, Margin displays `0.0%` (no division-by-zero error). |
| **Zero Receivables** | All customer invoices fully paid | DSO displays `0 Days`, bucket breakdown displays `100% Current` (`₹0.00`). |
| **Sales Returns (Credit Notes)** | Return Sales Invoice with `is_return = 1` | Correctly deducted from Net Revenue and Unit Sales (no double counting). |
| **Purchase Returns (Debit Notes)** | Return Purchase Invoice with `is_return = 1` | Correctly deducted from Purchases by Unit and DPO calculations. |
| **Multi-Currency Transactions** | Invoices in foreign currency (USD/EUR) | Aggregates base ledger amount (`base_net_amount`) in Company Base Currency. |
| **Unassigned Dimensions** | Invoices without Cost Center or Branch | Grouped gracefully under `'Unassigned'` or `'General'` without SQL null errors. |

---

## 7. Troubleshooting & FAQ for Functional Consultants

**Q1: Why does Net Revenue on the dashboard differ from the Sales Register?**  
- *Answer*: The Sales Register only captures `Sales Invoice` documents. Dashboard Net Revenue is computed from all Income ledger accounts in `GL Entry`, which also includes Journal Entries and other direct operational credits. For Sales Invoices specifically, compare with **Item 2 (Sales from Each Unit)**.

**Q2: Why does DSO show 0 days?**  
- *Answer*: DSO requires non-zero YTD Net Revenue. If no revenue is recognized yet in the fiscal period, DSO safely defaults to 0 to prevent division-by-zero errors.

**Q3: How do I change the default dimension from Cost Center to Branch?**  
- *Answer*: Use the dimension dropdown at the top of Item 2 / Item 3, or select the preferred Unit Dimension from the global filter control.

**Q4: Are canceled or draft documents included?**  
- *Answer*: No. All dashboard queries enforce `docstatus = 1` (Submitted) and exclude `is_cancelled = 1` records.

---

## 8. Sign-off & Verification Template

| Validation Item | Tested By | Date Tested | Status (Pass / Fail) | Notes / Remarks |
|---|---|---|:---:|---|
| Net Revenue & Margin Match P&L | | | [ ] | |
| Sales by Unit Match Sales Register | | | [ ] | |
| Purchases by Unit Match Purchase Register | | | [ ] | |
| Orders Booked Matches SO List | | | [ ] | |
| Backlog Pipeline Matches Pending SOs | | | [ ] | |
| AR Ageing & DSO Match AR Report | | | [ ] | |
| AP Ageing & DPO Match AP Report | | | [ ] | |
| Drill-Down Links Verified | | | [ ] | |
| Permission Restrictions Verified | | | [ ] | |
