# Custom DocType Inventory

## Primary business and configuration DocTypes

| DocType | Type | Purpose |
| --- | --- | --- |
| Order Modification Request | Submittable | Sales Order/BOM header and item revision request. |
| Bom Modification Request | Submittable | Controlled BOM component revision. |
| Purchase Order Modification Request | Submittable | Controlled PO header/item revision. |
| Modification Task | Submittable | Role/branch-routed change action. |
| Serial Number | Submittable | Batch/branch serial and engineering-status record. |
| Serial Number Configuration | Single | Fiscal year and Branch counters. |
| Item Generator | Process/master | Attribute-driven Item generation. |
| Item Generator Template | Master | Ordered attributes and Item Group defaults. |
| Custom Item Attribute | Master | Attribute codes and descriptions. |
| Item Group Defaults | Master | Defaults copied into generated Items. |
| Gate Pass Outward | Submittable | Material/component outward movement. |
| Gate Pass Inward | Submittable | Return/receipt against outward movement. |
| Gatepass Component | Submittable master | Asset-linked serviceable component. |
| CRM Notes | Submittable | Sales Order/customer CRM note. |
| Item Location | Master | Branch/Item warehouse location. |
| Customer Supplier Workflow Settings | Single | Branch approval rules. |
| Scenario Workflow Settings | Single | Stock Entry and MR submit roles. |
| Selective Products | Single | Products using selective description rules. |

## Supporting child DocTypes

| Child DocType | Parent/use |
| --- | --- |
| Commercial Detail | OMR commercial change table. |
| Commercial Details | Additional OMR commercial change table. |
| Order Modification Request Detail | OMR/BMR component detail. |
| Order Modification Request Detail History | OMR original/revised history. |
| Sales Order Item For OMR | Sales Order-specific OMR changes. |
| Purchase Order Modification Request Detail | PMR Item changes. |
| Purchase Order Modification Request Detail History | PMR original/revised history. |
| Link Document | OMR/BMR linked documents. |
| Template Attribute Table | Item Generator Template attributes. |
| Custom Item Attribute Value | Attribute values/codes/descriptions. |
| Product Details | Selective Products rows. |
| Serial Number Configuration Branches | Branch serial counters. |
| Gate Pass Outward Item | Component outward rows. |
| Gate Pass Outward Detail | Stock Item outward rows. |
| Gate Pass Inward Item | Component inward rows. |
| Gate Pass Inward Detail | Stock Item inward rows. |
| Gate Pass History | Component Gate Pass history. |
| Quality Inspection Heat No | Heat/certificate rows. |
| Stock Entry Scenario Role | Scenario submit roles. |
| Material Request Approval Rule | MR creator/approver role map. |
| Customer Approval Rule | Branch Customer approval roles. |
| Supplier Approval Rule | Branch Supplier approval roles. |

The app contains 40 DocType JSON definitions in total, including parent, child, Single, and master definitions.

## Source location

```text
generate_item/generate_item/doctype/<scrubbed_doctype_name>/
```

Full DocTypes normally contain JSON, Python, JavaScript when needed, `__init__.py`, and sometimes tests. Child DocTypes generally contain JSON and a minimal Python controller.

