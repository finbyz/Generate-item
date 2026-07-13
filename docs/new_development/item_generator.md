# Item Generator

## Purpose

Item Generator creates structured Item codes and descriptions from configurable product attributes and copies transaction-ready defaults into the new Item master.

Primary implementation:

- `generate_item/generate_item/doctype/item_generator/`
- `generate_item/generate_item/doctype/item_generator_template/`
- `generate_item/generate_item/doctype/custom_item_attribute/`
- `generate_item/generate_item/doctype/custom_item_attribute_value/`
- `generate_item/generate_item/doctype/template_attribute_table/`
- `generate_item/generate_item/doctype/item_group_defaults/`
- `generate_item/generate_item/doctype/selective_products/`
- `generate_item/public/js/item_generator_list.js`

## Configuration model

| DocType | Responsibility |
| --- | --- |
| Item Generator Template | Selects and orders attributes for a product template. |
| Custom Item Attribute | Stores code length, product/component context, and allowed values. |
| Custom Item Attribute Value | Maps long description, short description, and code. |
| Item Group Defaults | Stores Item defaults, UOMs, accounts, tax, quality, inventory, sales, purchase, batch, and serial settings. |
| Selective Products | Lists templates receiving selective short-description rules. |

## Generation workflow

1. User selects an Item Generator Template.
2. Client loads up to 28 configured attribute fields.
3. Attribute values build the Item descriptor, Item code, long description, and short description.
4. Saving the new Item Generator inserts an Item.
5. Item Group Defaults are copied to the Item master.
6. The generator stores `created_item` and `ig_done`.

## Item defaults copied

- Item Group and HSN;
- stock, sales, purchase, asset, and subcontracting flags;
- valuation and standard rates;
- stock/purchase/sales UOMs and conversion rows;
- Item Defaults accounts, warehouses, supplier, and price list;
- Item Tax rows;
- quality inspection settings;
- batch and serial settings;
- manufacturing inclusion.

## Transaction integration

Item Generator can be opened from:

- Sales Order Item;
- Order Modification Request revised Item;
- Item form;
- Item Generator list tools.

Sales Order and OMR integrations store a return context in browser session storage, verify Item creation, route back to the source form, and apply the new Item to the correct row.

## Security and lifecycle

- New records can be saved by permitted users.
- Saved records are locked for non-System Managers.
- Sales Order-created generators support Save and Close.
- `update_item_master()` updates Item name and description from the generator.

## Maintenance considerations

- Attribute order and code length affect generated codes and must be governed as master data.
- Browser session storage keys are part of transaction return routing.
- Item creation depends on a matching Item Group Defaults record.

