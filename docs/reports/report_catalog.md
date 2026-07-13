# Report Catalog

## Overview

Generate Item contains 25 Script Reports. Each report has its own folder under:

```text
generate_item/generate_item/report/<report_name>/
```

The folder normally contains Python execution logic, JavaScript filters/actions, JSON metadata, and `__init__.py`.

## Manufacturing and planning reports

### Work Order Shortage Report

Reference: Work Order.

Combines Work Order requirements, allocations, and stock to show shortage quantities. It provides status, age, and quantity charts, report summaries, and **Export to Excel**.

### Batch Wise Report

Reference: Sales Order.

Shows Sales Order and batch-level status information with transaction/date filters.

### Item-wise Batch Summary

Reference: Sales Order.

Builds simplified or original hierarchical views of Item, batch, and related manufacturing/order data. It adds a standard report export action.

### Bom Explorer SSV

Reference: BOM.

Recursively explodes child BOMs and returns an indented component tree with quantities.

### Stock Production Plan Projected Qty

Reference: Item.

Extends stock projection with Production Plan request quantities by Item and Warehouse.

### Tagging Sheet

Reference: Purchase Order.

Reports PO Item, batch, drawing, revision, and purchase-specification information used for tagging.

### OMR Item Change

Reference: Order Modification Request.

Shows OMR item changes and bulk approval details for change-review users.

## Sales reports

### Daily Review Sales Order

Reference: Sales Order.

Provides Sales Order/serial engineering release and delay review, including week buckets and a dashboard header. Whitelisted update APIs support controlled batch, serial, and reference-based updates.

### Sales Order Register Final

Reference: Sales Order.

Consolidated final register containing order, customer, address, item, invoice, and Item Generator attribute data.

### Sales Order Register Marketing

Reference: Sales Order.

Marketing view including customer/order details, delivered/invoiced quantities, Item Generator attributes, and workflow approval details.

### Sales Order Register Marketing Steelstrong

Reference: Sales Order.

SteelStrong-specific marketing register variant with additional organization-specific output.

### Sales Order Register Technical

Reference: Sales Order.

Technical register containing order/item technical values, delivery/invoice status, Item Generator attributes, and approval data.

### Sales Order Register Planning

Reference: Sales Order.

Planning-focused register with a broad planning column set and delivery/invoice/approval calculations.

The requested “Daily Review Sales Order Register” does not exist under that exact name; the implemented report is `Daily Review Sales Order`.

## Purchase reports

### Requested Items To Be Ordered

Reference: Material Request.

Shows outstanding Material Request items, applies Branch permissions, retrieves purchase history, groups by Supplier, and can create Purchase Orders using selected series, Branch, and order type.

### Requested Items To Be Received

Reference: Purchase Order.

Shows outstanding PO Items, purchase history, and Supplier grouping. It can create Purchase Receipts for selected rows and Branch/series.

### Request to Receipt

Reference: Material Request.

Builds a hierarchical Material Request → Purchase Order → Purchase Receipt tree and calculates quantities/status across the chain.

### Purchase Order Analysis

Reference: Purchase Order.

Analyzes pending and completed PO quantities/amounts and prepares report chart data.

### Purchase Order Analysis SteelStrong

Reference: Purchase Order.

SteelStrong-specific Purchase Order analysis variant with additional receipt/amount calculations.

### Vendor Item List

Reference: Item.

Lists vendor/supplier Item information and includes a custom HTML report template.

## Inventory reports

### Stock Balance With Location

Reference: Stock Ledger Entry.

Extends ERPNext Stock Balance logic and adds Item Location information.

### Stock ledger with Location

Reference: Stock Ledger Entry.

Extends Stock Ledger with Item Location while retaining serial/batch bundle and inventory-dimension processing.

### Serial Number Register

Reference: custom Serial Number.

Reports engineering and manufacturing status by serial/batch. It provides APIs for per-row updates and batch bulk updates.

## Gate Pass report

### Gate Pass Register

Reference: Gate Pass Outward.

Combines outward and inward stock/component rows with party/component details, pending/received quantities, summaries, and charts. It adds **Export Party Summary (CSV)**.

## Quality reports

### Incoming Inspection

Reference: Purchase Receipt.

Shows incoming Purchase Receipt and Quality Inspection data. A controlled update method edits MTC and related inspection values.

### RT Inward Register

Reference: Quality Inspection.

Reports RT/heat-number inward data and provides an update method for heat-number usage.

## Report permissions

Report roles are defined in each report JSON. They span relevant Sales, Planning, Manufacturing, Design, Purchase, Stock, Quality, Accounts, Delivery, Supplier, Dashboard, and System Manager roles.

Developers adding a report must update JSON roles as well as server-side permission or Branch filters where sensitive data is involved.

## Report files

| Report folder | Report name |
| --- | --- |
| `batch_wise_report` | Batch Wise Report |
| `bom_explorer_ssv` | Bom Explorer SSV |
| `daily_review_sales_order` | Daily Review Sales Order |
| `gate_pass_register` | Gate Pass Register |
| `incoming_inspection` | Incoming Inspection |
| `item_wise_batch_summary` | Item-wise Batch Summary |
| `omr_item_change` | OMR Item Change |
| `purchase_order_analysis` | Purchase Order Analysis |
| `purchase_order_analysis_steelstrong` | Purchase Order Analysis SteelStrong |
| `request_to_receipt` | Request to Receipt |
| `requested_items_to_be_ordered` | Requested Items To Be Ordered |
| `requested_items_to_be_received` | Requested Items To Be Received |
| `rt_inward_register` | RT Inward Register |
| `sales_order_register_final` | Sales Order Register Final |
| `sales_order_register_marketing` | Sales Order Register Marketing |
| `sales_order_register_marketing_steelstrong` | Sales Order Register Marketing Steelstrong |
| `sales_order_register_planning` | Sales Order Register Planning |
| `sales_order_register_technical` | Sales Order Register Technical |
| `serial_number_register` | Serial Number Register |
| `stock_balance_with_location` | Stock Balance With Location |
| `stock_ledger_with_location` | Stock ledger with Location |
| `stock_production_plan_projected_qty` | Stock Production Plan Projected Qty |
| `tagging_sheet` | Tagging Sheet |
| `vendor_item_list` | Vendor Item List |
| `work_order_shortage_report` | Work Order Shortage Report |

