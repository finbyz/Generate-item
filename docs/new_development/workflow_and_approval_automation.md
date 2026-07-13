# Workflow and Approval Automation

## Overview

Generate Item ships two Frappe Workflow fixtures and two settings-driven approval systems.

## Exported Frappe Workflows

### BOM Modification

Status: active.

```text
Draft --Approve / Design User--> Approved (docstatus 1)
```

### PO Modification Request

Status: shipped inactive.

```text
Draft
  --Submit for Checking / Purchase User--> Checking Pending
  --Submit for Approval / PO Checking--> Approval Pending
  --Approve / PO Approval--> Approved
```

It also contains rejection-to-Draft and Approved-to-Cancelled transitions.

## Scenario Workflow Settings

Primary implementation:

- `generate_item/generate_item/doctype/scenario_workflow_settings/`
- `generate_item/utils/scenario_workflow.py`
- `generate_item/public/js/scenario_workflow.js`

This Single DocType controls who may submit:

- any Stock Entry;
- Production Plan MR Material Transfer;
- Work Order Material Transfer for Manufacture;
- Work Order Manufacture;
- manually created Purchase Material Requests.

`Stock Entry Scenario Role` maps scenarios to roles. `Material Request Approval Rule` maps creator roles to approver roles.

Server validation is authoritative. The shared client script also hides Submit for an ineligible user. Production Plan-generated Purchase MRs are excluded from the manual MR rule.

An optional System Manager bypass is available.

## Customer/Supplier approval

Primary implementation:

- `generate_item/generate_item/doctype/customer_supplier_workflow_settings/`
- `generate_item/utils/customer_supplier_workflow.py`
- `generate_item/public/js/customer_supplier_workflow.js`

Customer and Supplier approvals can be enabled independently. Each Branch rule identifies:

- creator role;
- L1 approver role;
- final approver role.

State sequence:

```text
Draft -> Pending L1 Approval -> Pending Final Approval -> Approved
```

Behavior:

- Branch is mandatory while enabled;
- new records start disabled;
- only configured roles can advance the status;
- non-approved records remain disabled;
- Approved enables the master;
- direct approval-status editing is reverted;
- settings ensure required custom fields exist;
- existing active records are initialized as Approved;
- controlled System Manager or configured-role bypass is supported.

## Scope clarification

The scenario controls are code-based authorization, not standard Frappe Workflow definitions. No general artifacts named Manufacturing Workflow, Purchase Workflow, Stock Entry Workflow, or Material Request Workflow are shipped beyond the specific mechanisms described above.

