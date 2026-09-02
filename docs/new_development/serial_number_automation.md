# Serial Number Automation

## Purpose

This module creates and reconciles custom branch/batch serial records for approved Valve Sales Orders.

Primary implementation:

- `generate_item/generate_item/doctype/serial_number/`
- `generate_item/generate_item/doctype/serial_number_configuration/`
- `generate_item/generate_item/doctype/serial_number_configuration_branches/`
- `generate_item/public/js/sales_order.js`
- Sales Order and Stock Entry hooks in `generate_item/hooks.py`

The custom `Serial Number` DocType is separate from standard ERPNext Serial No behavior.

## Manual generation

The submitted Sales Order **Serial Number** action calls `create_serial_numbers_for_sales_order()`.

Eligibility requires:

- submitted and open Sales Order;
- Branch;
- active, non-delivered/non-cancelled rows;
- custom batch;
- Item Generator product attribute identifying the Item as Valve.

## Naming structure

Serials use:

```text
<branch-prefix><two-digit-fiscal-year><letter><four-digit-sequence>
```

Each letter supports 0001–9999, with 26 letter buckets. Counters are stored per Branch in `Serial Number Configuration Branches`.

## Quantity reconciliation

Manual generation handles:

| Existing live serials | Result |
| --- | --- |
| Zero | Generate full required quantity. |
| Equal to quantity | Skip. |
| Less than quantity | Generate the difference. |
| Greater than quantity | Cancel eligible excess serials. |

Excess cancellation is newest-first and never cancels a serial linked to a Stock Entry. A shortfall is reported when insufficient unallocated serials are available.

## Scheduler

The `daily_long` job processes eligible approved Sales Orders.

```text
pending sales quantity = SO quantity - delivered quantity
required serials = max(0, pending sales quantity - batch quantity)
difference = required serials - live unallocated serials
```

- Positive difference generates serials.
- Negative difference cancels eligible excess serials.
- Zero requires no action.

## Bulk behavior

- SQL insert chunks contain up to 10,000 rows.
- Commits occur every 25,000 generated rows.
- Realtime progress events are published to the requesting user.
- Reserved counters are restored when generation fails.

## Cancellation integration

- A cancelled Sales Order line cancels live batch serials.
- Before Sales Order cancellation, linked submitted OMRs are cancelled.
- Sales Order cancellation cancels matching batch/branch serials.
- Stock Entry cancellation clears its reference only from explicitly listed serials.

## Engineering tracking

The Serial Number record also stores manufacturing type, API monogram, MDS, GAD, ITP/QAP, pattern, engineering release, delay, and other design-status values used by Serial Number Register and Daily Review Sales Order.

