# Purchase Order Modification

## Purpose

Purchase Order Modification Request provides controlled revision of submitted Purchase Order commercial and item data while preserving an original/revised history.

Primary implementation:

- `generate_item/generate_item/doctype/purchase_order_modification_request/`
- `generate_item/generate_item/doctype/purchase_order_modification_request_detail/`
- `generate_item/generate_item/doctype/purchase_order_modification_request_detail_history/`

## Request types

### Order Change

Supported header changes include:

- incoterm;
- payment terms template and payment schedule;
- Terms and Conditions;
- insurance;
- mode of dispatch;
- freight charges;
- PO remarks;
- same-item grouping.

Only genuinely changed fields are written to history and applied to the Purchase Order.

### Order Item Change

Supported item changes include:

- quantity and rate;
- Item replacement;
- line addition and deletion;
- required and expected delivery dates;
- UOM, stock UOM, stock quantity, and conversion factor;
- price-list rate;
- target warehouse and Item Tax Template;
- line status and free-item flag;
- Item name and description.

## Material Request synchronization

Quantity changes reconcile linked Material Request quantities and links. When a quantity increase must be split, the implementation creates/links new PO rows and preserves the originating MR relationship.

Deleted PO lines have their Material Request links cleared. New lines receive branch context.

## Revision and history

The request records original and revised values in `Purchase Order Modification Request Detail History`. It also stamps the Purchase Order revision metadata and recalculates order quantities.

## Workflow

The exported `PO Modification Request` workflow defines:

```text
Draft
  -> Checking Pending
  -> Approval Pending
  -> Approved/submitted
```

It includes rejection-to-Draft and Approved-to-Cancelled paths. The fixture is shipped with `is_active = 0`, so site administrators must activate it before it governs requests.

## Main controller methods

| Method | Responsibility |
| --- | --- |
| `update_purchase_order_commercial_details()` | Applies changed header fields. |
| `_sync_payment_schedule_to_po()` | Rebuilds PO payment rows. |
| `update_purchase_order_values()` | Applies item additions, updates, and deletions. |
| `_compute_delta_and_update_mrs()` | Calculates quantity deltas and MR changes. |
| `_link_new_po_lines_to_mrs()` | Restores MR links on generated PO rows. |
| `_apply_item_replacements()` | Updates Item code/name/description. |
| `create_history_records()` | Stores original and revised values. |

