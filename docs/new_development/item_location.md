# Item Location

## Purpose

Item Location stores a physical or operational location for an Item within a Branch and related warehouses.

Primary implementation:

- `generate_item/generate_item/doctype/item_location/`
- `generate_item/generate_item/report/stock_balance_with_location/`
- `generate_item/generate_item/report/stock_ledger_with_location/`

## Data model

- Branch;
- Item and Item name;
- location text;
- Warehouse 1;
- Warehouse 2;
- description;
- generated unique link/key.

Validation prevents conflicting location identity through the `unique_link` model.

## Report integration

The custom Stock Balance and Stock Ledger reports call `get_item_location(item_code, warehouse)` and enrich inventory output with the maintained location.

## Administration

Locations should be maintained consistently for the Branch/Item/warehouse combination used by inventory reports. Warehouse renaming or branch reassignment should include Item Location review.

