# Generate Item Technical Documentation

## Documentation index

This is the entry point for the Generate Item developer documentation. The documentation is separated by functional module so each area can be maintained independently.

The content is code-verified from `apps/generate_item`. Features owned by another app, inactive metadata, partial implementations, and unsupported claims are identified explicitly.

## New development

| Functionality | Documentation |
| --- | --- |
| OMR, BMR, Production Plan, incremental MR, and Work Order propagation | [Manufacturing Change Management](new_development/manufacturing_change_management.md) |
| Detailed Production Plan implementation | [Production Plan Modification Workflow](production_plan_modification_workflow.md) |
| Modification Task creation, permissions, and notifications | [Modification Task Module](new_development/modification_task.md) |
| Purchase Order Modification Request | [Purchase Order Modification](new_development/purchase_order_modification.md) |
| Manual and scheduled serial generation | [Serial Number Automation](new_development/serial_number_automation.md) |
| Attribute-based Item creation | [Item Generator](new_development/item_generator.md) |
| Gate Pass Outward, Inward, components, Stock Entry, and PO | [Gate Pass Module](new_development/gate_pass.md) |
| Modification alerts and external Workflow Email | [Notifications and Workflow Email](new_development/notifications_and_workflow_email.md) |
| Frappe workflows and settings-driven approvals | [Workflow and Approval Automation](new_development/workflow_and_approval_automation.md) |
| Sales Order CRM follow-up | [CRM Notes](new_development/crm_notes.md) |
| Quality Inspection and heat numbers | [Quality and Heat Number](new_development/quality_and_heat_number.md) |
| Branch/Item physical location | [Item Location](new_development/item_location.md) |
| Scheduled Currency Exchange integration | [Currency Exchange Synchronization](new_development/currency_exchange_sync.md) |
| Selected Work Order spreadsheet output | [Work Order Excel Export](new_development/work_order_excel_export.md) |

## ERPNext customizations

[ERPNext Customizations](customizations/erpnext_customizations.md) covers controller overrides, document hooks, mapping overrides, Branch/warehouse logic, Custom Fields, Property Setters, duplicate prevention, and print-format scope.

## Reports

[Report Catalog](reports/report_catalog.md) documents all 25 Script Reports, grouped into manufacturing/planning, sales, purchase, inventory, Gate Pass, and quality.

## Pages and dashboards

[Pages and Dashboards](pages_and_dashboards/dashboard_catalog.md) documents Director Dashboard and Sales Performance Dashboard, including routes, metrics, filters, and APIs.

## Technical reference

| Reference | Documentation |
| --- | --- |
| Custom parent, master, Single, and child DocTypes | [Custom DocType Inventory](reference/doctype_inventory.md) |
| Hooks, APIs, fixtures, overrides, and scheduler | [Hooks, APIs, Fixtures, and Schedulers](reference/hooks_apis_and_schedulers.md) |
| Confirmed, partial, external, inactive, and missing scope | [Implementation Status and Audit Notes](reference/implementation_status.md) |

## Repository overview

| Artifact | Count |
| --- | ---: |
| Files under the app package | 521 |
| Python files | 200 |
| JavaScript files | 66 |
| JSON files | 71 |
| DocType JSON definitions | 40 |
| Script Reports | 25 |
| Desk Pages | 2 |
| Exported Custom Fields | 399 |
| Exported Property Setters | 127 |

## Source layout

```text
generate_item/
├── api/                       Whitelisted lookup APIs
├── fixtures/                  Custom Fields, Property Setters, Workflows
├── generate_item/doctype/     Custom DocTypes
├── generate_item/report/      Script Reports
├── generate_item/page/        Desk Pages
├── generate_item/modification_task_utils/
├── overrides/                 Standard controller subclasses
├── public/js/                 Standard form/list scripts
├── utils/                     Hooks and business services
└── hooks.py                   Runtime integration map
```

## Documentation maintenance

When changing a feature:

1. update its functional document;
2. update the relevant reference catalog if the data model, hook, report, page, or status changes;
3. keep this index path stable;
4. rebuild assets after JavaScript changes;
5. migrate after DocType or fixture changes;
6. add behavioral tests for critical change-management, serial, Gate Pass, and approval behavior.

