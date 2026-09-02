# Hooks, APIs, Fixtures, and Schedulers

## Runtime registration

Runtime integration is defined in `generate_item/hooks.py`.

## Client scripts

Form scripts are registered for Item, Sales Order, BOM, BOM Creator, Material Request, Purchase Order, Purchase Receipt, Purchase Invoice, Production Plan, Work Order, Stock Entry, Subcontracting Order, Delivery Note, Sales Invoice, Quality Inspection, Customer, and Supplier.

List scripts are registered for Item Generator and Work Order. OMR includes a DocType-local list script.

## Controller overrides

- BOM
- BOM Creator
- Production Plan
- Work Order
- Sales Order
- Purchase Order
- Purchase Receipt

See [ERPNext Customizations](../customizations/erpnext_customizations.md).

## Important public method groups

| Domain | Methods/purpose |
| --- | --- |
| Production change | Production Plan Get Update, pending MR lookup, shortage MR creation, single/bulk WO update. |
| Serial | Sales Order serial generation and report bulk updates. |
| Gate Pass | Stock Entry lifecycle and draft inward coverage query. |
| Purchase | Pending MR/PO quantities, direct PO/PR creation, subcontracting mapping. |
| Sales | Dispatchable SO queries, remaining taxes, mapped DN/SI creation. |
| Approvals | Scenario Submit control and Customer/Supplier status actions. |
| Dashboards | Director and Sales Performance APIs. |
| Export | Work Order Excel generation. |

## Whitelisted ERPNext overrides

- Material Request → Purchase Order;
- Purchase Order → Purchase Receipt;
- Sales Order → Delivery Note;
- Delivery Note → Sales Invoice;
- Production Plan Material Request calculation;
- Accounts child quantity/rate update;
- Quality Inspection creation;
- Purchase Order → Subcontracting Order;
- Subcontracting Order → Subcontracting Receipt;
- Subcontracting raw-material Stock Entry.

## Scheduler

| Schedule | Method | Purpose |
| --- | --- | --- |
| `daily_long` | `process_sales_orders_for_serial_creation` | Reconciles Sales Order serial requirements. |
| `0 */4 * * *` | `sync_exchange_rates` | Synchronizes Currency Exchange every four hours. |

## Fixtures

- 399 Generate Item Custom Fields;
- 127 Generate Item Property Setters;
- active BOM Modification workflow;
- inactive PO Modification Request workflow.

## External dependencies

- Frappe and ERPNext;
- `workflow_transitions` for OMR pending Workflow Email;
- `openpyxl` for Work Order Excel;
- external MoneyConvert API for exchange rates;
- India Compliance metadata used by some transaction fields.

`workflow_transitions` is used at runtime but is not declared in `required_apps`.

