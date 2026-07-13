# Gate Pass Module

## Purpose

The Gate Pass module controls stock-item and asset-component movement out of and back into the organization, including Stock Entry and service Purchase Order integration.

Primary implementation:

- `generate_item/generate_item/doctype/gate_pass_outward/`
- `generate_item/generate_item/doctype/gate_pass_inward/`
- `generate_item/generate_item/doctype/gate_pass_history/`
- `generate_item/generate_item/doctype/gatepass_component/`
- related outward/inward child DocTypes

## Gate Pass Outward

Supports:

- Customer or Supplier party;
- stock Item or Gatepass Component movement;
- returnable/non-returnable movement;
- Repair, Job Work, Branch Transfer, Testing, Customer Complaint, Sales, and Consumption purposes;
- transport, billing, branch, warehouse, quantity, rate, and value data;
- linked Stock Entry, Gate Pass Inward, and Purchase Order.

### Outward Stock Entry

Before submission, a stock-item Gate Pass creates or updates a Stock Entry:

- returnable → Material Transfer;
- non-returnable → Material Issue.

The service validates positive quantities, warehouses, and required serial/batch values. It reuses an existing draft Stock Entry. If automatic submission fails, the draft is preserved and linked for correction and retry.

## Gate Pass return process

A submitted outward pass exposes **Gate Pass Inward** when return quantities remain.

The client:

- checks for existing draft inwards;
- calculates pending quantities;
- creates a draft inward with the correct stock/component child rows;
- links each inward row to its outward source row.

Submitting an inward:

- creates a Material Transfer Stock Entry for stock Items;
- updates received and pending outward quantities;
- prevents over-receipt;
- changes the outward status to Open or Closed.

Cancelling an inward reverses received quantities. Cancelling an outward cancels linked submitted inwards under the cancellation guard.

## Gatepass Component

`Gatepass Component` is the implemented asset-linked component master. It stores parent Asset, component identity, serial, status, location, service details, make/model, description, and Gate Pass history.

No DocType named `Asset Sub Component` exists. Purchase Order Item has a Data field `asset_subcomponent` used to carry the selected Gatepass Component identifier.

## Purchase Order from Gate Pass

For component/service flows, the outward form can:

1. fetch non-stock service Items;
2. allow the user to select services;
3. create a draft Purchase Order;
4. set Supplier and `gate_pass_outword`;
5. add service rows with quantity one and zero initial rate;
6. stamp `asset_subcomponent` from the outward component rows.

## Naming

Outward and inward forms select branch-specific naming series for stock, returnable, and non-returnable variants.

