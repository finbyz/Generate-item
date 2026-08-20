# ERPNext Customizations

## Purpose

This document catalogs confirmed changes to standard ERPNext DocTypes and transaction behavior. New Generate Item DocTypes are documented separately under `docs/new_development`.

## Controller overrides

Registered through `override_doctype_class` in `generate_item/hooks.py`.

| Standard DocType | Override | Main changes |
| --- | --- | --- |
| BOM | `overrides.custombom.CustomBOM` | Branch/Item naming, draft child-BOM allowance while saving, submitted child-BOM enforcement, custom explosion. |
| BOM Creator | `overrides.custom_bom_creator.BOMCreator` | Drawing/custom field mapping, BOM enrichment, deadlock retry, mapping verification. |
| Production Plan | `overrides.production_plan.ProductionPlan` | Branch/SO filters, pending quantities, BOM enforcement, sub-assembly fields, WO/MR creation and series. |
| Work Order | `overrides.customWorkorder.WorkOrder` | Permits valid sub-assembly Work Orders through Sales Order validation. |
| Sales Order | `overrides.custom_sales_order.CustomSalesOrder` | Unlinks Batch and Sales Order Item references before deletion. |
| Purchase Order | `overrides.purchase_order.CustomPurchaseOrder` | Custom receiving-percentage behavior. |
| Purchase Receipt | `overrides.purchase_receipt.CustomPurchaseReceipt` | Stock-UOM quantity handling and custom validation. |

## Standard DocType event customizations

### Sales Order

- duplicate draft prevention;
- Branch and extensive commercial/technical fields;
- free-item and warranty logic;
- Item Generator, BOM, Batch, Serial Number, and CRM actions;
- batch creation/update and mismatch correction;
- custom Update Items persistence;
- serial and linked OMR cancellation behavior.

### BOM and BOM Creator

- custom `BOM-<branch>-<item>` naming with a unique suffix;
- Branch and Branch abbreviation;
- Sales Order and batch linkage;
- available/valid batch validation;
- drawing and purchase-specification propagation;
- draft child BOM support while designing;
- submitted child BOM enforcement during final submit;
- custom BOM Creator mapping.

### Production Plan and Work Order

- Branch and batch propagation;
- branch-filtered Sales Orders and warehouses;
- naming series by Branch/plan series;
- custom pending quantities;
- BOM, drawing, and Sales Order consistency;
- sub-assembly Work Order creation;
- grouped Material Requests;
- manufacturing change synchronization;
- Work Order required-item availability and Excel export.

### Material Request

- duplicate draft prevention;
- BOM, batch, drawing, Branch, Production Plan, Sales Order, and Work Order fields;
- custom pending quantity when creating Purchase Orders;
- manual Purchase MR creator/approver controls;
- production-plan Material Transfer role controls.

### Purchase Order

- duplicate draft prevention;
- Branch/batch/Production Plan enrichment;
- Material Request remaining quantity including draft POs;
- custom line update and branch series/defaults;
- Gate Pass and asset sub-component fields;
- Purchase Order Modification Request integration;
- subcontracting mappings.

### Purchase Receipt

- Purchase Order mapping with custom batch;
- branch series and warehouse selection;
- append-from-PO line-wise behavior;
- pending quantity calculation;
- duplicate/return validation;
- stock-UOM received quantity synchronization;
- custom Quality Inspection generation.

### Purchase Invoice

- Branch and custom drawing/batch fields;
- duplicate draft validation by supplier/item/quantity/batch/source links.

### Delivery Note

- dispatchable Sales Order selection;
- requirement that linked Work Orders are complete where applicable;
- batch assignment from Sales Order;
- stock/batch availability validation;
- draft Delivery Note quantity exclusion;
- actual-charge remaining amount calculation;
- PO line propagation;
- free-item validation;
- duplicate draft protection.

### Sales Invoice

- dispatchable Sales Order action;
- draft Sales Invoice quantity exclusion;
- remaining actual taxes from Delivery Note or Sales Order;
- duplicate draft protection;
- free-item removal/remarks;
- warranty and serial updates.

### Stock Entry

- Branch, batch, Production Plan, drawing, and source-document fields;
- Work Order and subcontracting field propagation;
- scenario-based Submit control;
- custom serial cleanup on cancellation.

### Subcontracting Order and Receipt

- PO, MR, Production Plan, batch, branch, drawing, and specification propagation;
- supplied-item database updates;
- custom Subcontracting Receipt mapping;
- custom raw-material Stock Entry mapping;
- receipt-side supplied custom fields and validation.

### Quality Inspection

- Branch and branch series;
- drawing/specification data;
- heat numbers;
- inspector and accepted quantity;
- MTC/PMI/RT-related metadata;
- custom creation from Purchase Receipt.

### Customer and Supplier

- Branch field;
- standard validations;
- optional branch-specific creator/L1/final approval;
- disabled until Approved.

## Whitelisted method overrides

| Standard behavior | Custom behavior |
| --- | --- |
| Material Request → Purchase Order | Counts Draft and submitted PO quantity before mapping remaining quantity. |
| Purchase Order → Purchase Receipt | Copies PO Item custom batch into PR Item batch. |
| Sales Order → Delivery Note | Excludes quantity already present in Draft Delivery Notes. |
| Delivery Note → Sales Invoice | Excludes quantity already present in Draft Sales Invoices. |
| Production Plan MR items | Adds BOM and drawing fields. |
| Child quantity/rate update | Supports controlled submitted changes and subcontracting rules. |
| Quality Inspection creation | Maps custom inspection fields. |
| PO → Subcontracting Order | Maps custom production context. |
| Subcontracting Order → Receipt | Maps custom production context. |
| Subcontracting RM Stock Entry | Maps supplied-item custom fields. |

## Branch and warehouse customization

Branch is mandatory on BOM, Production Plan, Material Request, Sales Order, Quality Inspection, Subcontracting Receipt, Payment Entry, Delivery Note, Purchase Invoice, and Purchase Receipt Item.

Branch is also propagated to Work Order, Batch, Warehouse, transaction item rows, planning rows, and sub-assembly rows.

Warehouse classifications:

- `store_warehouse`;
- `raw_material_warehouse`;
- `gatepass_warehouse`.

They support branch-aware warehouse selection in production, purchase, and Gate Pass flows.

Some fallback mappings explicitly reference Sanand, Nandikoor, and Rabale. New Branch implementation must review those mappings and naming series.

## Fixtures

The app exports 399 Custom Fields and 127 Property Setters. The largest customization surfaces are Sales Order, Sales Order Item, Quality Inspection, Purchase Receipt Item, Purchase Order/Item, Production Plan, Work Order Item, BOM/BOM Item, and Material Request planning rows.

## Print-format scope

No Generate Item Print Format definitions or Print Format fixtures were found. The app contains print-related fields, letter-head selections, layout Property Setters, and transaction format values, but app-owned transaction Print Formats are outside the verified repository scope.

No dedicated Credit Note or Debit Note controller/client/DocType implementation was found.

