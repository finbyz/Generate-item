# Quality Inspection and Heat Number Development

## Purpose

This functionality extends ERPNext Quality Inspection with branch, drawing/specification, heat-number, MTC, PMI, and incoming-inspection controls.

Primary implementation:

- `generate_item/generate_item/doctype/quality_inspection_heat_no/`
- `generate_item/utils/quality_inspection.py`
- `generate_item/utils/heat_no_generator.py`
- `generate_item/public/js/quality_inspection.js`

## Quality Inspection enhancements

- branch-specific naming-series selection;
- Purchase Receipt/reference resolution;
- BOM and Item custom field lookup;
- drawing, drawing revision, pattern drawing, and purchase-specification propagation;
- inspected-by population;
- received, accepted, rejected, and sample quantity handling;
- validation that heat-number quantity does not exceed permitted quantity;
- accepted quantity updates on submit;
- MTC, PMI, NCR, RT, and other inspection metadata through Custom Fields.

## Heat Number child table

`Quality Inspection Heat No` stores:

- heat number;
- quantity;
- test certificate number.

The client can generate a range using start, end, and series values. Server validation checks the resulting quantities.

## Reports

- `Incoming Inspection` exposes receipt/inspection data and controlled inspection-row updates.
- `RT Inward Register` reports heat/RT information and provides a used-status update API.

## Integration

Purchase Receipt mapping and custom Quality Inspection creation are registered through document hooks and an overridden ERPNext inspection-creation method.

