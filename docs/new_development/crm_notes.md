# CRM Notes

## Purpose

CRM Notes provides a submitted record for Sales Order-related customer follow-up and commercial notes.

Primary implementation:

- `generate_item/generate_item/doctype/crm_notes/`
- `generate_item/utils/sales_order.py`
- `generate_item/public/js/sales_order.js`

## Data captured

- naming series;
- Sales Order and order date;
- Branch;
- delivery date;
- Customer;
- customer Purchase Order number and date;
- order amount and currency;
- rich-text CRM notes.

## Sales Order integration

Sales Order adds **Add To CRM**, which calls `create_crm_note_from_sales_order()`. The server builds a CRM Notes record from the Sales Order context and returns it for user access.

## Permissions

CRM Notes is submittable and its JSON metadata defines its own role permissions. It is a Generate Item DocType, not an ERPNext CRM Note override.

