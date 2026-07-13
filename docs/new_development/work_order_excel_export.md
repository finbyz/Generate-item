# Work Order Excel Export

## Purpose

The Work Order list provides an Excel export containing manufacturing and stock availability information for selected Work Orders.

Primary implementation:

- `generate_item/public/js/work_order_list.js`
- `generate_item/utils/work_order.py`

## User workflow

1. Open the Work Order list.
2. Select one or more Work Orders.
3. Click **Export to Excel**.
4. The client calls `generate_item.utils.work_order.export_work_orders`.
5. The generated Frappe File URL is opened in the browser.

## Export columns

- Work Order number and Branch;
- finished Item and BOM;
- batch;
- required Item and description;
- issued, current, on-hand, and balance quantities;
- UOM;
- source and target warehouses;
- bin number column;
- drawing number and revision.

Branch on-hand quantity is summed across all warehouses belonging to the Work Order Branch. Current quantity is calculated across the required Item source warehouse and Work Order finished-goods warehouse.

## Output

The server uses `openpyxl`, styles the header and cells, saves `Work_Order_Export.xlsx` as a Frappe File, and returns the file URL.

Additional exports exist in Work Order Shortage Report, Item-wise Batch Summary, and Gate Pass Register, but those are documented with their reports.

