# Financial Dashboard (Frappe v16 + ERPNext v16)

A production-ready, executive-grade Financial Dashboard implemented as a custom Frappe Page within the custom Frappe app (`generate_item`), wired to live ERPNext ledger and operational data.

---

## 1. Installation & Setup

### Environment Requirements
- **Frappe Framework**: `version-16` (v16.24.0+)
- **ERPNext**: `version-16` (v16.25.0+)
- **Python**: `3.14+`
- **Node.js**: `24+`

### Setup Commands
```bash
# 1. Build assets (vendors Chart.js locally without CDN dependencies)
bench build --app generate_item

# 2. Run migrations to sync Page, Roles, and Settings DocType
bench --site [site-name] migrate

# 3. Clear cache
bench --site [site-name] clear-cache
```

---

## 2. Page & File Architecture

```
generate_item/
├── generate_item/
│   ├── page/financial_dashboard/
│   │   ├── financial_dashboard.json        # Page definition, title & roles
│   │   ├── financial_dashboard.py          # Page backend API bridge
│   │   ├── financial_dashboard.js          # Controller class (FinancialDashboard)
│   │   └── financial_dashboard.css         # Scoped styles under .fd-root
│   └── doctype/financial_dashboard_settings/ # Single DocType for targets & dimension
├── api/
│   └── financial_dashboard.py              # Whitelisted backend endpoints & queries
├── public/js/vendor/
│   └── chart.umd.min.js                    # Vendored Chart.js (Strictly offline/local)
├── tests/
│   └── test_financial_dashboard.py         # IntegrationTestCase test suite
└── FINANCIAL_DASHBOARD_README.md           # This documentation
```

- **Page Route**: `/app/financial-dashboard`
- **Access Roles**: `Accounts Manager`, `Accounts User`, `System Manager`, `Sales Manager`.

---

## 3. Data Mapping & Metric Definitions

| Dashboard Element | Source & Query Logic | Definition / Formula |
|---|---|---|
| **KPI: Total Net Revenue** | `GL Entry` joined to `Account` where `Account.root_type = 'Income'`, `is_cancelled = 0`, `company = ...` | $\text{Revenue} = \sum(\text{credit} - \text{debit})$ for the selected Fiscal Year period. |
| **KPI: Operating Margin** | `GL Entry` joined to `Account` for Income and Expense accounts | $\text{Operating Margin} = \frac{\text{Income} - \text{Expenses}}{\text{Income}} \times 100$. |
| **KPI: Orders Booked** | `Sales Order` where `docstatus = 1`, `status != 'Cancelled'`, `company = ...` | Count and `base_net_total` value of booked Sales Orders. |
| **KPI: Book-to-Bill** | `Sales Order` booked value $\div$ `Sales Invoice` net value | $\text{Book-to-Bill} = \frac{\sum \text{Sales Orders}}{\sum \text{Sales Invoices}}$. |
| **KPI: Pending Backlog** | `Sales Order` where `status in ('To Deliver and Bill', 'To Deliver', 'To Bill', 'On Hold')` and `per_delivered < 100` | $\text{Backlog Value} = \sum\left(\text{base\_grand\_total} \times \frac{100 - \text{per\_delivered}}{100}\right)$. |
| **KPI: % on SLA** | Share of pending Sales Orders where `delivery_date >= today - grace_days` | $\text{SLA} = \frac{\text{On-time Pending SOs}}{\text{Total Pending SOs}} \times 100$. |
| **Item 1: Revenue vs Op. Margin** | Monthly GL Entry aggregation across 12 months with Full Year / H1 / H2 filters | Dual-axis combo chart: Left bars = Net Revenue; Right line = Operating Margin %. |
| **Item 2: Sales by Unit** | `Sales Invoice Item` joined to `Sales Invoice` (`docstatus = 1`, returns handled) | Multi-grain series (Years / Quarters / Months) by Cost Center / Branch / Company. |
| **Item 3: Purchases by Unit** | `Purchase Invoice Item` joined to `Purchase Invoice` (`docstatus = 1`, returns handled) | Multi-grain series (Years / Quarters / Months) with Stacked / Grouped toggle. |
| **Item 4: Orders Booked Monthly** | `Sales Order` grouped by `MONTH(transaction_date)` | Monthly actuals vs target quota line + monthly mean + attainment %. |
| **Item 5: Pending Orders Lifecycle** | Stage classification function | - **Production**: Open linked `Work Order`<br>- **QA Inspection**: Open linked `Quality Inspection`<br>- **In Transit**: Open linked `Delivery Note`<br>- **Payment Hold**: Status 'On Hold' / open `Payment Request`<br>- **Open**: Unscheduled. |
| **Item 6: AR Ageing & DSO** | `erpnext.accounts.report.accounts_receivable.execute` with `ageing_based_on = 'Due Date'` | Dynamic bucket aggregation (<30d, 31-60d, 61-90d, >90d) + $\text{DSO} = \frac{\text{AR Outstanding}}{\text{YTD Net Revenue}} \times \text{Days}$. |
| **Item 7: AP Ageing & DPO** | `erpnext.accounts.report.accounts_payable.execute` with `ageing_based_on = 'Due Date'` | Dynamic bucket aggregation + $\text{DPO} = \frac{\text{AP Outstanding}}{\text{YTD Purchases}} \times \text{Days}$. |

---

## 4. Key Assumptions & Deviations

1. **Prototype Units $\to$ ERPNext Cost Centers / Branches**:
   - The prototype's generic Units ("Alpha", "Beta", "Gamma", "Delta") are mapped directly to the organization's **Cost Centers** (default), **Branches**, or **Companies**.
2. **Currency & Locale**:
   - Replaced hardcoded `$` symbols with dynamic multi-currency formatting (`format_currency` / compact notation using Company's `default_currency`).
3. **Fiscal Year Alignment**:
   - Replaced fixed 2024/2025/2026 buttons with dynamic `Fiscal Year` link filter and automatic previous year detection for YoY deltas.
4. **Vendored Chart.js**:
   - Chart.js is bundled locally in `generate_item/public/js/vendor/chart.umd.min.js` to eliminate CDN dependencies and comply with strict enterprise CSP policies.

---

## 5. Verification Checklist Against ERPNext Standard Reports

- [x] **Revenue & Margin**: Open **Profit and Loss Statement** (`/app/query-report/Profit and Loss Statement`) for the selected company and fiscal year $\to$ confirm total Income, total Expense, and Net Profit match Item 1 and KPI strip.
- [x] **Sales Invoices & Registers**: Open **Sales Register** (`/app/query-report/Sales Register`) $\to$ confirm net sales match Item 2.
- [x] **Purchase Invoices & Registers**: Open **Purchase Register** (`/app/query-report/Purchase Register`) $\to$ confirm net purchases match Item 3.
- [x] **Sales Orders**: Open **Sales Order List** (`/app/sales-order`) $\to$ confirm count and booked value match Item 4.
- [x] **Accounts Receivable**: Open **Accounts Receivable** (`/app/query-report/Accounts Receivable`) $\to$ confirm bucket totals and total outstanding match Item 6.
- [x] **Accounts Payable**: Open **Accounts Payable** (`/app/query-report/Accounts Payable`) $\to$ confirm bucket totals and total outstanding match Item 7.
