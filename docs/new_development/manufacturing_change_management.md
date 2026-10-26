# Manufacturing Change Management

## Purpose

This module propagates approved Sales Order item and quantity changes through BOMs, Production Plans, Material Requests, Work Orders, Purchase Orders, and operational Modification Tasks.

```text
Sales Order
  -> Order Modification Request
  -> BOM Modification Request when BOM/design work is needed
  -> Production Plan Get Update
  -> incremental Material Request
  -> Work Order synchronization
```

## Order Modification Request

Primary implementation:

- `generate_item/generate_item/doctype/order_modification_request/`
- `generate_item/generate_item/doctype/order_modification_request_detail/`
- `generate_item/generate_item/doctype/order_modification_request_detail_history/`
- `generate_item/generate_item/doctype/sales_order_item_for_omr/`

`Order Modification Request` is a submittable DocType supporting `Order Change` and `Order Item Change`.

It manages:

- original and revised item, quantity, rate, delivery, status, address, tag, free-item, drawing, and specification values;
- Sales Order commercial-header changes;
- original/revised line and commercial history;
- Sales Order revision stamping;
- batch creation and batch-item updates;
- revised Item creation through Item Generator;
- BMR creation or reuse for affected item/BOM changes;
- affected Production Plan flagging through `sales_order_modification`;
- creation of BOM Modification Tasks.

On submit, an Order Item Change updates the Sales Order values, revision, and batches before evaluating whether a BMR is required.

## BOM Modification Request

Primary implementation:

- `generate_item/generate_item/doctype/bom_modification_request/`

The BMR copies current BOM component context and supports revised components, quantities, drawings, specifications, child BOMs, and deletion.

On submit it:

1. applies component changes;
2. propagates changed `custom_drawing_no` values to safely matched draft and
   submitted Production Plan, Work Order, Material Request, Purchase Order, and
   Purchase Receipt child rows;
3. excludes cancelled documents and reports ambiguous records without changing
   them;
4. updates BOM item revision data;
5. synchronizes batch and Sales Order context;
6. handles removed sub-assembly references;
7. flags linked Production Plans through `bom_modification` for item or
   quantity changes only;
8. creates Production Plan Update tasks for those manufacturing changes.

Drawing propagation follows BOM component identity plus transaction-row links;
it does not use item code alone. When repeated components or BOM-derived planning rows cannot be disambiguated,
downstream rows are left unchanged and reported. Drawing-only changes do not
invoke the Production Plan or Work Order quantity synchronization flow.
Propagation changes only the child-row drawing field; it does not rerun
submitted-document lifecycle hooks.

The shipped active `BOM Modification` workflow is:

```text
Draft --Approve (Design User)--> Approved/submitted
```

## Production Plan update

Primary implementation:

- `generate_item/public/js/production_plan.js`
- `generate_item/utils/production_plan.py`
- `generate_item/overrides/production_plan.py`

The **Get Update** action:

- blocks when an active linked Work Order is Started, In Process, or Completed;
- captures original assembly, sub-assembly, and raw-material rows once;
- updates increased Sales Order planned quantities;
- regenerates BOM-derived sub-assemblies and Material Request planning rows;
- uses the branch store warehouse when configured;
- clears modification flags;
- marks linked Work Orders as requiring an update;
- creates downstream Work Order and Purchase Order tasks.

Original tracking tables:

| Live table | Tracking table |
| --- | --- |
| `po_items` | `tracking_assembly_items` |
| `sub_assembly_items` | `tracking_sub_assembly_items` |
| `mr_items` | `tracking_raw_materials` |

The hidden `original_data` flag prevents later refreshes from replacing the first baseline.

## Incremental Material Request

The custom action requests only the remaining shortage:

```text
pending quantity = required quantity - non-cancelled requested quantity
```

Rows are matched using item code, warehouse, and Sales Order. The server recalculates shortages inside a cache lock and calls standard Production Plan MR creation using only pending rows.

## Work Order synchronization

Primary implementation:

- `generate_item/public/js/work_order.js`
- `generate_item/utils/work_order.py`

The Production Plan can update all linked non-cancelled Work Orders, and a flagged Work Order can update itself using **Get Update**.

The update:

- synchronizes the finished Item from the BOM;
- updates raw-material quantities, rates, and amounts;
- adds new components;
- removes obsolete components only when nothing was transferred or consumed;
- preserves used obsolete components with a warning;
- uses per-Work-Order savepoints during bulk processing;
- clears `modification_status` after success.

Work Order operations are not synchronized by the current implementation.

## Detailed reference

See [Production Plan Modification Workflow](../production_plan_modification_workflow.md) for button visibility, server endpoints, state fields, task propagation, concurrency behavior, and developer tests.
