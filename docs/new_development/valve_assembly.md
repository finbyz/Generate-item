# Valve Assembly

## Overview

The **Valve Assembly** module tracks the physical assembly of valves on the shop floor. It links custom serial numbers to their sales orders, batches, item specifications, and assembly operators while automatically calculating production capacity metrics (**Inspector Inches**).

Primary source files:

- DocType definition: `generate_item/generate_item/doctype/valve_assembly/valve_assembly.json`
- Python controller: `generate_item/generate_item/doctype/valve_assembly/valve_assembly.py`
- Form script: `generate_item/generate_item/doctype/valve_assembly/valve_assembly.js`
- Child table DocType: `generate_item/generate_item/doctype/assembly_item_serial_no/assembly_item_serial_no.json`
- Inspector inches utility: `generate_item/utils/inspector_inches.py`
- Integration tests: `generate_item/generate_item/doctype/valve_assembly/test_valve_assembly.py`
- Analytics report: `generate_item/generate_item/report/valve_assembly_report/`

Valve Assembly is a **Submittable** DocType (`is_submittable: 1`).

---

## Naming Series & Branch Routing

Document numbering is branch-dependent and incorporates the active fiscal year:

| Branch | Naming Series Pattern | Example |
| --- | --- | --- |
| Sanand | `VASS.fiscal.#####` | `VASS-2627-00001` |
| Rabale | `VASR.fiscal.#####` | `VASR-2627-00001` |
| Nandikoor | `VASN.fiscal.#####` | `VASN-2627-00001` |

When a user selects a Branch in a new document, the client-side `branch` trigger sets `naming_series` automatically.

### Series Rollback on Deletion

Standard Frappe naming series counters do not decrement when records are deleted. To prevent permanent gaps in audited production series, `ValveAssembly.on_trash` executes `revert_series_on_trash(self)`:
- Populates naming variables (`fiscal`, `fiscal_year`) using `posting_date`.
- If the deleted document was the latest sequence number in `tabSeries`, the counter in `tabSeries` is decremented by 1.
- If an earlier document is deleted, the counter remains unchanged to avoid collisions.

---

## Document Fields & Validation Rules

### Header Fields

| Field Name | Type | Options / Rules | Description |
| --- | --- | --- | --- |
| `posting_date` | Date | Default: Today. Read-only unless `allow_back_date` is active. | Date of the assembly operation. Cascades to line items. |
| `allow_back_date` | Check | Default: 0 | Checkbox enabling back-dated assembly entry. |
| `branch` | Link | `Branch` (Mandatory) | Manufacturing plant/location. Determines naming series and filters operators. |
| `naming_series` | Select | `VASS.fiscal.#####`, `VASR.fiscal.#####`, `VASN.fiscal.#####` | Read-only sequence series. |
| `item_serial_number`| Table | `Assembly Item Serial No` | Table containing the valve serial numbers assembled. |
| `amended_from` | Link | `Valve Assembly` | Standard submittable amendment reference. |

### Validation Rules

1. **Mandatory Table Check**:
   The document must contain at least one line item in `item_serial_number` before saving or submitting.
2. **Posting Date Constraints**:
   - **Future dates are forbidden**: Throws `Invalid Date` error if `posting_date > Today`.
   - **Past dates require authorization**: If `posting_date < Today` and `allow_back_date` is not checked, the system throws `Back-Dating Not Allowed`.
   - When `allow_back_date` is unchecked, `posting_date` automatically resets to `Today` and becomes read-only.
   - Modifying `posting_date` updates the `date` field across all child rows in `item_serial_number`.
3. **Child Row Date Constraints**:
   Each line item's `date` must not be in the future and cannot be in the past unless `allow_back_date` is enabled.
4. **Duplicate Prevention**:
   The client dialog and import routines block duplicate serial numbers from being added to the same document.

---

## Child Table: Assembly Item Serial No

Each row in `item_serial_number` stores the assembled valve's serial number, item specification attributes, operator, and computed Inspector Inches.

### Fields

| Field Name | Type | Source / Calculation | Description |
| --- | --- | --- | --- |
| `serial_number` | Link (`Serial Number`) | Mandatory, read-only | Custom serial number of the valve. |
| `item_code` | Link (`Item`) | Read-only from Batch | Valve item master code. |
| `description` | Small Text | Read-only | Item description from Item / Item Generator. |
| `batch_no` | Link (`Batch`) | Read-only | Production batch linked to the serial number. |
| `sales_order` | Link (`Sales Order`) | Read-only | Sales Order referenced by the batch. |
| `date` | Date | Defaults to `posting_date` | Specific date of assembly for this valve. |
| `assembled_by` | Link (`General Employee`)| Filtered query | Technician or group who assembled the valve. |
| `size` | Data | Fetched from Item Generator | Valve nominal diameter (e.g., `2"`, `4"`). |
| `class` | Data | Fetched from Item Generator | Valve pressure rating (e.g., `150#`, `300#`). |
| `end_connection` | Data | Fetched from Item Generator | End connection type (e.g., `FLANGED RF`). |
| `shell_moc` | Data | Fetched from Item Generator | Shell material of construction (e.g., `WCB`, `CF8M`). |
| `wedge_plug_ball_disc_moc` | Data | Fetched from Item Generator | Trim closure element material. |
| `facing` | Data | Fetched from Item Generator | Seat / Ball facing specifications. |
| `seat_ringguide_moc` | Data | Fetched from Item Generator | Seat ring material of construction. |
| `stem_moc` | Data | Fetched from Item Generator | Stem material of construction. |
| `gasket` | Data | Fetched from Item Generator | Body/bonnet gasket material. |
| `gland_packing__oring_moc` | Data | Fetched from Item Generator | Gland packing and O-ring materials. |
| `fasteners` | Data | Fetched from Item Generator | Bolting / fastener grade. |
| `operation` | Data | Fetched from Item Generator | Operator type (Lever, Gear, Actuator). |
| `inch_factor` | Data | Read-only | Multiplier from `Custom Item Attribute` "FG-Rating". |
| `value` | Data | Hidden, read-only | Value from `Custom Item Attribute` "FG-Size". |
| `inches` | Data | Read-only | Computed Inspector Inches (`inch_factor * value`). |
| `remark` | Small Text | User entry | Line-level technician remarks. |
| `status` | Data | Optional | Status descriptor. |

---

## Serial Acquisition: "Get Item from Serial Register"

In draft state (`docstatus === 0`), users click **Get Item from Serial Register** on the form toolbar to launch an interactive multi-selection dialog.

### Search Filters
- **Sales Order**: Lists submitted Sales Orders (`docstatus = 1`) filtered by the document's `branch`.
- **Batch Number**: Lists Batches linked to the selected Sales Order (`reference_name = sales_order`).
- **Serial Number**: Lists active, submitted `Serial Number` records filtered by `branch` and `batch`.

### Eligibility & Exclusion Logic
The backend API `generate_item.doctype.valve_assembly.valve_assembly.get_serial_register_items`:
1. Queries `tabSerial Number` records matching `docstatus = 1` and `branch`.
2. **Excludes previously assembled valves**: Queries child table `Assembly Item Serial No` where `docstatus = 1` and `parenttype = 'Valve Assembly'`. Any serial number that has already been assembled in a submitted document is filtered out. A valve serial number can only be assembled once.
3. Automatically maps `item_code` and `sales_order` from the associated `tabBatch` record.
4. Retrieves `description` from `tabItem` or `tabItem Generator`.

### Attribute & Inspector Inches Hydration
When selected rows are added to the form:
1. The script fetches the `Item Generator` document matching `row.item_code`.
2. Attributes 1 through 28 are parsed and mapped to the child table:
   - `Size` -> `size`
   - `Rating` -> `class`
   - `Ends` -> `end_connection`
   - `Shell MOC` -> `shell_moc`
   - `Ball MOC` -> `wedge_plug_ball_disc_moc`
   - `Ball Facing` -> `facing`
   - `Seat Ring(Guide) MOC` -> `seat_ringguide_moc`
   - `Stem MOC` -> `stem_moc`
   - `Gasket` -> `gasket`
   - `Gland Packing + O'Ring MOC` -> `gland_packing__oring_moc`
   - `Fasteners` -> `fasteners`
   - `Operator` -> `operation`
3. Calls `generate_item.utils.inspector_inches.get_inspector_inches(size, rating)` to populate `inch_factor`, `value`, and `inches`.
4. As a safety net, `ValveAssembly.before_save` executes `calculate_doc_inspector_inches(self)` on the server to verify that every row has populated Inspector Inches.

---

## Operator Linking: General Employee

The `assembled_by` field links to `General Employee`:
- Filters only active employee records (`enabled = 1`).
- Scoped to the current document's `branch`.
- Restricted to department **"Valve assembly"** using `general_employee_by_department_query`.

---

## Reporting & Analytics

The **Valve Assembly Report** (`valve_assembly_report`) provides comprehensive visibility into assembly operations:

- **Filters**: Date Range (`posting_date`), Assembly Date (`item_serial_number.date`), Branch, Sales Order, Batch No, Valve Serial No, Item Code, Assembled By, User.
- **Columns**: Valve Assembly link, Posting Date, Assembly Date, Branch, Created By User, Serial Number, Item Code, Item Name, Sales Order, Batch No, Assembled By, Size, Class, End Connection, Shell MOC, Stem MOC, Inch Factor, Inches, Status, Remark.
- **Summary Cards**:
  - Total Valves Assembled
  - Total Inspector Inches Assembled
  - Unique Items
  - Unique Batches
- **Charts**: Assembly count and total inches broken down by Branch or Assembled By.
