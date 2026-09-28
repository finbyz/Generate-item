# Valve Painting

## Overview

The **Valve Painting** module manages the painting, coating, and surface finishing operations for manufactured valves. It implements a closed-loop, two-stage custody workflow (**Received** and **Finished**) to ensure that only valves physically received into the paint shop can be completed, preventing inventory discrepancies and untracked processing.

Primary source files:

- DocType definition: `generate_item/generate_item/doctype/valve_painting/valve_painting.json`
- Python controller: `generate_item/generate_item/doctype/valve_painting/valve_painting.py`
- Form script: `generate_item/generate_item/doctype/valve_painting/valve_painting.js`
- Child table DocType: `generate_item/generate_item/doctype/valve_painting_item/valve_painting_item.json`
- Inspector inches utility: `generate_item/utils/inspector_inches.py`
- Integration tests: `generate_item/generate_item/doctype/valve_painting/test_valve_painting.py`

Valve Painting is a **Submittable** DocType (`is_submittable: 1`).

---

## Naming Series & Branch Routing

Document numbering is branch-dependent and incorporates the active fiscal year:

| Branch | Naming Series Pattern | Example |
| --- | --- | --- |
| Sanand | `VPAS.fiscal.#####` | `VPAS-2627-00001` |
| Rabale | `VPAR.fiscal.#####` | `VPAR-2627-00001` |
| Nandikoor | `VPAN.fiscal.#####` | `VPAN-2627-00001` |

When a user selects a Branch in a new document, the client-side `branch` trigger sets `naming_series` automatically.

### Series Rollback on Deletion

Standard Frappe naming series counters do not decrement when records are deleted. To prevent gaps in official production records, `ValvePainting.on_trash` executes `revert_series_on_trash(self)`:
- Populates naming variables (`fiscal`, `fiscal_year`) using `posting_date`.
- If the deleted document was the latest sequence number in `tabSeries`, the counter in `tabSeries` is decremented by 1.
- If an earlier document is deleted, the counter remains unchanged to avoid collisions.

---

## The Two-Stage Painting Workflow

Valve painting is divided into two distinct process stages governed by the mandatory header field `type`:

```
[ Tested Valve ]
       │
       ▼
┌──────────────────────────────────────────────┐
│ Stage 1: Valve Painting (Type = Received)   │
│  • Valves received into Paint Shop custody   │
│  • Pulled from Serial Register               │
│  • Submitted docstatus = 1                   │
└──────────────────────┬───────────────────────┘
                       │
                       │ Surface Blast / Primer / Top Coat / Drying
                       ▼
┌──────────────────────────────────────────────┐
│ Stage 2: Valve Painting (Type = Finished)   │
│  • Painting & coating inspection completed   │
│  • Must reference submitted 'Received' docs  │
│  • Closes paint shop custody                 │
└──────────────────────────────────────────────┘
```

### Stage 1: Type = "Received"
- **Purpose**: Records that valves have arrived at the painting department (either transferred from in-house testing or returned from outside machining/subcontracting).
- **Data Source**: Items are fetched directly from the general `Serial Number` register using `get_serial_register_items`.
- **Submission**: Once submitted (`docstatus = 1`), these serial numbers become eligible for processing in Stage 2.

### Stage 2: Type = "Finished"
- **Purpose**: Confirms completion of surface cleaning, masking, primer application, intermediate/finish coats, and dry-film thickness (DFT) inspection.
- **Data Source**: Serials **CANNOT** be pulled from the open serial register. They can **ONLY** be retrieved from valves previously logged in a submitted `Valve Painting (Type = Received)` document for that branch (`get_received_painting_items`).
- **Strict Validation Rules**:
  1. **Document-level Uniqueness**: No duplicate serial numbers can exist within the same document.
  2. **Must be Previously Received**: Every serial number must exist in a submitted `Valve Painting` record with `type = 'Received'` matching the document's branch:
     > *"The following Serial Numbers were not found in any submitted Valve Painting (Type = Received) for branch {branch}: {serial_numbers}"*
  3. **No Double-Finishing**: The serial number must not already be present in another `Finished` Valve Painting document (whether draft `0` or submitted `1`):
     > *"The following Serial Numbers are already processed in another Finished Valve Painting document: {serial_number} (already in {docname})"*

---

## Document Fields & Validation Rules

### Header Fields

| Field Name | Type | Options / Rules | Description |
| --- | --- | --- | --- |
| `posting_date` | Date | Default: Today. Read-only unless `allow_back_date` is active. | Date of painting document. Cascades to line items. |
| `allow_back_date` | Check | Default: 0 | Checkbox enabling back-dated entry. |
| `branch` | Link | `Branch` (Mandatory) | Manufacturing plant/location. Determines naming series. |
| `type` | Select | `Received`, `Finished` (Mandatory) | Painting stage. |
| `naming_series` | Select | `VPAS.fiscal.#####`, `VPAR.fiscal.#####`, `VPAN.fiscal.#####` | Sequence series. |
| `item_serial_number`| Table | `Valve Painting Item` | Table containing serial numbers being painted. |
| `amended_from` | Link | `Valve Painting` | Standard amendment reference. |

### Validation Rules

1. **Mandatory Header Fields**: `posting_date`, `branch`, and `type` cannot be blank.
2. **Mandatory Table Check**: Must have at least one line item in `item_serial_number`.
3. **Date Validations**:
   - `posting_date` cannot be a future date.
   - `posting_date` cannot be a past date unless `allow_back_date` is checked.
   - Line-item `date` values cannot be future dates, nor past dates without `allow_back_date`.
4. **Duplicate Prevention**:
   Both client-side `validate(frm)` and server-side `validate_finished_serial_numbers()` enforce serial number uniqueness.

---

## Child Table: Valve Painting Item

Each row in `item_serial_number` represents an individual valve in the paint process.

### Fields

| Field Name | Type | Details / Options | Description |
| --- | --- | --- | --- |
| `serial_number` | Link (`Serial Number`) | Filtered by painting stage | Serial number of the valve. |
| `item_code` | Link (`Item`) | Read-only from Batch | Valve item master code. |
| `description` | Small Text | Read-only | Item description. |
| `batch_no` | Link (`Batch`) | Read-only | Production batch. |
| `sales_order` | Link (`Sales Order`) | Read-only | Sales Order. |
| `date` | Date | Defaults to `posting_date` | Date of painting operation. |
| `tested_by` | Link (`General Employee`)| Label: **Painted By** | Painter or technician who painted the valve. |
| `size` | Data | Fetched from Item Generator | Valve nominal size. |
| `class` | Data | Fetched from Item Generator | Valve pressure rating. |
| `type` | Data | Fetched from Item Generator (`Valve Type`) | Valve type (Gate, Globe, Check, Ball). |
| `end_connection` | Data | Fetched from Item Generator | End connection type. |
| `shell_moc` | Data | Fetched from Item Generator | Shell material. |
| `operation` | Data | Fetched from Item Generator | Operator type. |
| `inch_factor` | Data | Read-only | Rating factor from `Custom Item Attribute` "FG-Rating". |
| `value` | Data | Hidden, read-only | Size factor from `Custom Item Attribute` "FG-Size". |
| `inches` | Data | Read-only | Computed Inspector Inches (`inch_factor * value`). |
| `test_ok` | Select | `Not Accepted`, `Accepted` | Coating inspection result. |
| `leak_reason` | Select | Visible if `test_ok == "Not Accepted"` | Quality failure cause. |
| `remark` | Small Text | Optional | Paint shade, RAL code, or technician remarks. |

---

## Dynamic Serial Acquisition & Form Filtering

The UI adapts dynamically depending on whether `type` is set to `Received` or `Finished`:

### Link Field Queries (`serial_number`)
- **When Type = "Received"**:
  Displays active, submitted serial numbers from `tabSerial Number` matching the document branch (`docstatus = 1, branch = frm.doc.branch`).
- **When Type = "Finished"**:
  Invokes `received_serial_number_query`. This query joins `tabValve Painting Item` with submitted `Valve Painting (Type = Received)` records, excluding any serial numbers already present in a draft or submitted `Finished` document.

### Dialog Search ("Get Item from Serial Register")
When the user clicks **Get Item from Serial Register**:

| Condition | API Called | Items Returned |
| --- | --- | --- |
| `type == "Received"` | `get_serial_register_items` | Active serial numbers from `Serial Number` DocType for this branch/sales order/batch. |
| `type == "Finished"` | `get_received_painting_items` | Only serial numbers that exist in a submitted `Received` painting document and are not yet in any `Finished` document. |

When items are selected and added to the child table:
1. Item specifications are parsed from the corresponding `Item Generator` record.
2. `get_inspector_inches(size, rating)` calculates `inch_factor`, `value`, and `inches`.
3. Server-side `calculate_doc_inspector_inches(self)` ensures every row's inches are committed to the database.

---

## Painter Linking: General Employee

The `tested_by` field (labeled **Painted By** in the UI) links to `General Employee`:
- Filters active records (`enabled = 1`).
- Scoped to the current document's `branch`.
- Restricted to department **"Valve painting"** using `general_employee_by_department_query`.
