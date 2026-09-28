# Valve Testing

## Overview

The **Valve Testing** module tracks hydrostatic, pneumatic, and third-party inspection (TPI) quality testing of assembled valves. It enforces strict phase progression rules (Pre Testing, Final Testing, and TPI Testing), logs pass/fail results with specific leak defect reasons, captures testing personnel, and calculates production capacity metrics (**Inspector Inches**).

Primary source files:

- DocType definition: `generate_item/generate_item/doctype/valve_testing/valve_testing.json`
- Python controller: `generate_item/generate_item/doctype/valve_testing/valve_testing.py`
- Form script: `generate_item/generate_item/doctype/valve_testing/valve_testing.js`
- Child table DocType: `generate_item/generate_item/doctype/valve_testing_item/valve_testing_item.json`
- Phase validation & query utils: `generate_item/utils/inspector_inches.py`
- Integration tests: `generate_item/generate_item/doctype/valve_testing/test_valve_testing.py`
- Analytics report: `generate_item/generate_item/report/valve_testing_report/`

Valve Testing is a **Submittable** DocType (`is_submittable: 1`).

---

## Naming Series & Branch Routing

Document numbering is branch-dependent and incorporates the active fiscal year:

| Branch | Naming Series Pattern | Example |
| --- | --- | --- |
| Sanand | `VTES.fiscal.#####` | `VTES-2627-00001` |
| Rabale | `VTER.fiscal.#####` | `VTER-2627-00001` |
| Nandikoor | `VTEN.fiscal.#####` | `VTEN-2627-00001` |

When a user selects a Branch in a new document, the client-side `branch` trigger sets `naming_series` automatically.

### Series Rollback on Deletion

Standard Frappe naming series counters do not decrement when records are deleted. To prevent permanent gaps in audited inspection series, `ValveTesting.on_trash` executes `revert_series_on_trash(self)`:
- Populates naming variables (`fiscal`, `fiscal_year`) using `posting_date`.
- If the deleted document was the latest sequence number in `tabSeries`, the counter in `tabSeries` is decremented by 1.
- If an earlier document is deleted, the counter remains unchanged to avoid collisions.

---

## Testing Phases & Eligibility Architecture

Valve Testing supports three distinct testing stages defined in the mandatory `testing_phase` field:

```
[ Assembled Valve ]
        │
        ├──► (Optional) Pre Testing ──────► (If Not Accepted: Repair & Re-test)
        │                                  (If Accepted: Locks Pre-Testing)
        ▼
   Final Testing ────────────────────────► (If Not Accepted: Repair & Re-test)
        │                                  (If Accepted: Locks Final Testing)
        ▼ (Prerequisite: Must be Accepted in Final Testing)
   TPI Testing (Third Party Inspection) ──► (If Not Accepted: Re-inspect)
                                           (If Accepted: Completed)
```

The eligibility of a valve serial number for a given phase is determined by `validate_serial_for_testing_phase()` and `get_valve_testing_serial_query()` in `inspector_inches.py`:

### 1. Stock Entry Link Restriction
If a serial number has already been allocated to a completed manufacturing or transfer Stock Entry (`Serial Number.stock_entry` is populated), it **cannot be tested** in Valve Testing. The system rejects the serial with an error:
> *"Serial Number {0} is already linked to Stock Entry {1} and cannot be used in Valve Testing."*

### 2. Pre Testing
- **Purpose**: Preliminary in-process pressure check to detect casting porosity or seat leaks before final machining/coating.
- **Rules**:
  - Eligible if the serial number has **not previously been Accepted** in Pre Testing.
  - If a valve fails (`Not Accepted`), it can be repaired and re-tested in Pre Testing as many times as necessary.
  - Once marked `Accepted` in a submitted Pre Testing document, it cannot be tested in Pre Testing again.

### 3. Final Testing
- **Purpose**: Official factory hydrostatic shell and seat leakage testing in accordance with API / ASME / BS standards.
- **Rules**:
  - Pre Testing is **not a mandatory prerequisite** for Final Testing. Any assembled valve can proceed directly to Final Testing.
  - Eligible as long as the serial has **not previously been Accepted** in Final Testing.
  - If a valve is `Not Accepted`, it can be repaired and re-tested in Final Testing.
  - Once marked `Accepted` in a submitted Final Testing document, it cannot be tested in Final Testing again.

### 4. TPI Testing (Third Party Inspection)
- **Purpose**: Witnessed inspection conducted by customer-appointed inspection agencies (e.g., Lloyd's, BV, DNV, TUV, Engineers India Limited).
- **Rules**:
  - **Strict Prerequisite**: The serial number **MUST have been marked `Accepted` in a submitted Final Testing document**.
  - If the valve has not passed Final Testing, the system rejects it:
    > *"Serial Number {0} has not been Accepted in Final Testing. Only Serial Numbers that have passed Final Testing are eligible for TPI Testing."*
  - Cannot be re-tested in TPI if it was already marked `Accepted` in a prior submitted TPI document.

### Phase Eligibility Summary Table

| Serial Number Status | Pre Testing Eligible? | Final Testing Eligible? | TPI Testing Eligible? |
| --- | :---: | :---: | :---: |
| Not yet tested | **Yes** | **Yes** | No (requires Final test pass) |
| Pre Testing: Not Accepted | **Yes** (re-test) | **Yes** | No |
| Pre Testing: Accepted | No (already passed) | **Yes** | No (requires Final test pass) |
| Final Testing: Not Accepted | No | **Yes** (re-test) | No |
| Final Testing: Accepted | No | No (already passed) | **Yes** |
| TPI Testing: Not Accepted | No | No | **Yes** (re-inspect) |
| TPI Testing: Accepted | No | No | No (already passed) |
| Linked to Stock Entry | **No** | **No** | **No** |

---

## Document Fields & Validation Rules

### Header Fields

| Field Name | Type | Options / Rules | Description |
| --- | --- | --- | --- |
| `posting_date` | Date | Default: Today. Read-only unless `allow_back_date` is active. | Date of testing document. Cascades to line items. |
| `allow_back_date` | Check | Default: 0 | Checkbox enabling back-dated test entry. |
| `branch` | Link | `Branch` (Mandatory) | Manufacturing plant/location. Determines naming series. |
| `testing_phase` | Select | `Pre Testing`, `Final Testing`, `TPI Testing` (Mandatory) | The inspection stage being executed. |
| `naming_series` | Select | `VTES.fiscal.#####`, `VTER.fiscal.#####`, `VTEN.fiscal.#####` | Sequence series. |
| `item_serial_number`| Table | `Valve Testing Item` | Table containing tested valve serial numbers and results. |
| `amended_from` | Link | `Valve Testing` | Standard amendment reference. |

### Validation Rules

1. **Mandatory Table Check**: Must have at least one line item in `item_serial_number`.
2. **Mandatory Testing Phase**: `testing_phase` cannot be blank.
3. **Date Validations**:
   - `posting_date` cannot be in the future.
   - `posting_date` cannot be in the past unless `allow_back_date` is checked.
   - Child line `date` values cannot be in the future, nor in the past unless `allow_back_date` is active.
4. **Serial Phase Eligibility Check**:
   During `validate()`, every row's `serial_number` is verified against `validate_serial_for_testing_phase(serial_number, testing_phase)`. If any serial is ineligible, a descriptive error message halts document save.
5. **Testing Phase Change Warning**:
   If `testing_phase` is changed on an existing draft document with line items, a client warning alerts the user to verify item validity.

---

## Child Table: Valve Testing Item

Each row in `item_serial_number` captures a tested valve, technical specifications, test results, defect details, and inspector inches.

### Fields

| Field Name | Type | Details / Options | Description |
| --- | --- | --- | --- |
| `serial_number` | Link (`Serial Number`) | Filtered by phase eligibility | Serial number of the valve being tested. |
| `item_code` | Link (`Item`) | Read-only from Batch | Valve item master code. |
| `description` | Small Text | Read-only | Item description. |
| `batch_no` | Link (`Batch`) | Read-only | Production batch. |
| `sales_order` | Link (`Sales Order`) | Read-only | Linked Sales Order. |
| `date` | Date | Defaults to `posting_date` | Specific date of test execution. |
| `tested_by` | Link (`General Employee`)| Filtered query | Inspector/technician who conducted the test. |
| `test_ok` | Select | `Not Accepted`, `Accepted` | Quality outcome. |
| `leak_reason` | Select | Mandatory if `test_ok == "Not Accepted"` | Specific leak/failure mode. |
| `size` | Data | Fetched from Item Generator | Valve nominal size. |
| `class` | Data | Fetched from Item Generator | Valve pressure rating. |
| `type` | Data | Fetched from Item Generator (`Valve Type`) | Valve type (Gate, Globe, Check, Ball). |
| `end_connection` | Data | Fetched from Item Generator | End connection type. |
| `shell_moc` | Data | Fetched from Item Generator | Shell material. |
| `operation` | Data | Fetched from Item Generator | Operator type. |
| `inch_factor` | Data | Read-only | Rating factor from `Custom Item Attribute` "FG-Rating". |
| `value` | Data | Hidden, read-only | Size factor from `Custom Item Attribute` "FG-Size". |
| `inches` | Data | Read-only | Computed Inspector Inches (`inch_factor * value`). |
| `remark` | Small Text | Optional | Test observations or inspector notes. |

### Quality Outcome & Defect Categorization

When a valve fails testing (`test_ok` set to `Not Accepted`), the field `leak_reason` becomes **visible and strictly mandatory**. The supported standardized defect categories are:

| Leak Reason | Description / Typical Root Cause |
| --- | --- |
| `Air Seat Leak` | Seat seal failure under low-pressure air testing. |
| `Hydro Seat Leak` | High-pressure hydrostatic seat leakage past closure element. |
| `Body Casting Leak` | Through-wall porosity, shrinkage, or crack in valve shell casting. |
| `Seatring Casting Leak` | Defect/porosity in pressed or welded seat ring casting. |
| `Bonnet Casting Leak` | Porosity or flaw in valve bonnet / cover casting. |
| `Wedge Casting Leak` | Porosity or shrinkage in gate valve wedge casting. |
| `Joint Leak` | Leakage at body-to-bonnet gasket bolted joint. |
| `Back Seat Leak` | Leakage past stem backseat bushing during packing isolation test. |
| `Welding Leak` | Leakage in seat ring weld overlay, butt weld, or seal weld. |
| `Bore Casting Leak` | Defect located in the internal valve flow passage/bore. |

---

## Serial Acquisition: "Get Item from Serial Register"

In draft state (`docstatus === 0`), users click **Get Item from Serial Register**.

1. **Prerequisite**: User must select `testing_phase` on the form before opening the dialog. If blank, an error modal prompts selection.
2. **Search Criteria**: Filter by Sales Order, Batch Number, and Serial Number.
3. **Backend Query Filtering**:
   - `get_serial_register_items(doctype="Valve Testing", testing_phase=...)` only returns serial numbers that meet the eligibility criteria for the selected phase.
   - Serials already linked to a `Stock Entry` are excluded.
   - Serials already Accepted in the selected phase (or lacking Final pass for TPI) are omitted.
4. **Child Row Population**:
   - Selected serials are added without duplicates.
   - Fetches valve attributes from `Item Generator`.
   - Computes Inspector Inches using `get_inspector_inches(size, rating)`.
   - Server-side `before_save` validates and populates any missing inches via `calculate_doc_inspector_inches(self)`.

---

## Inspector Linking: General Employee

The `tested_by` field links to `General Employee`:
- Filters only active employee records (`enabled = 1`).
- Scoped to current document `branch`.
- Restricted to department **"Valve testing"** using `general_employee_by_department_query`.

---

## Reporting & Analytics

The **Valve Testing Report** (`valve_testing_report`) provides comprehensive QA analytics:

- **Filters**: Date Range (`posting_date`), Test Date, Branch, Testing Phase (`Pre Testing`, `Final Testing`, `TPI Testing`), Test OK (`Accepted`, `Not Accepted`), Sales Order, Batch No, Valve Serial No, Item Code, Tested By, User.
- **Columns**: Valve Testing link, Posting Date, Test Date, Branch, Testing Phase, User, Tested By, Serial Number, Item Code, Item Name, Sales Order, Batch No, Test OK, Leak Reason, Size, Class, Valve Type, End Connection, Shell MOC, Stem MOC, Inch Factor, Inches, Remark.
- **Summary Cards**:
  - Total Valves Tested
  - Total Accepted
  - Total Not Accepted / Rejected
  - Acceptance Rate (%)
  - Total Inspector Inches Tested
  - Pre Testing Count / Final Testing Count / TPI Testing Count
- **Charts**: Test volume by phase, pass/fail ratios, and Pareto distribution of `leak_reason` defect causes.
