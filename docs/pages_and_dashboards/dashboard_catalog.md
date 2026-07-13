# Pages and Dashboards

## Overview

Generate Item contains two custom Desk Pages under:

```text
generate_item/generate_item/page/
```

Each page has JSON metadata, a JavaScript UI, and a Python backend.

## Director Dashboard

Route:

```text
director-dashboard
```

Primary files:

- `generate_item/generate_item/page/director_dashboard/director_dashboard.json`
- `director_dashboard.js`
- `director_dashboard.py`

### Purpose

Displays pending purchase-cycle documents and outstanding line counts grouped by age.

### Metrics

- pending Purchase Material Requests;
- pending Purchase Orders;
- pending Purchase Receipts;
- pending Purchase Invoices.

Each metric supports:

- document-wise counts;
- line-wise truly outstanding counts;
- Branch filter;
- date range filter;
- age buckets: 0–7, 8–14, 15–21, 22–28, and 28+ days.

### APIs

| Method | Result |
| --- | --- |
| `get_dashboard_data()` | Document-wise pending buckets. |
| `get_item_wise_data()` | Outstanding line-wise buckets. |

The backend excludes terminal statuses and uses remaining quantity conditions for line-level cards.

## Sales Performance Dashboard

Route:

```text
sales-performance-da
```

Primary files:

- `generate_item/generate_item/page/sales_performance_da/sales_performance_da.json`
- `sales_performance_da.js`
- `sales_performance_da.py`

### Purpose

Provides executive Sales Order, billing, collection, engineering-release, and on-time-delivery performance metrics.

### Metrics

- Draft, Booked, and Approved Sales Orders;
- approval delay buckets;
- fiscal-year and current-month order booking value;
- invoicing value;
- outstanding versus collection;
- BOM release pending;
- delivery OTD;
- order-entry OTD;
- order-approval OTD.

Values are presented in lakhs where implemented. The dashboard supports date and Branch filtering for relevant metrics.

### Main API

`get_dashboard_data(from_date, to_date, branch)` aggregates all cards and charts.

### Naming clarification

The implemented page title is `Sales Performance Dashboard`. There is no separate page named exactly `Sales Dashboard`.

## Adding a dashboard

Create a Page folder containing:

- page JSON metadata;
- client JavaScript;
- whitelisted Python data methods;
- Branch/date permission filtering as required.

Avoid exposing unrestricted SQL-backed metrics to users who should not see cross-branch data.

