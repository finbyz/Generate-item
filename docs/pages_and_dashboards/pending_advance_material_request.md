# Pending Advance Material Request Page Report

## Overview

**Pending Advance Material Request** is a custom Frappe Desk Page for reviewing submitted Advance Material Request item rows and linking each row to a Production Plan with the same Batch Number. It is not a standard Query Report: JavaScript renders the table and calls whitelisted Python APIs.

| Property | Value |
| --- | --- |
| Route | `/app/pending-advance-mate` |
| Page name | `pending-advance-mate` |
| Module | Generate Item |
| Source folder | `generate_item/generate_item/page/pending_advance_mate/` |

The page lists both linked and unlinked rows. Despite its title, "pending" is not defined as an empty `production_plan` by the current query.

## Source files

| File | Responsibility |
| --- | --- |
| `pending_advance_mate.json` | Standard Page metadata, title, route, and module. |
| `pending_advance_mate.js` | Filters, table, inline editor, staged changes, save flow, and CSV export. |
| `pending_advance_mate.py` | Data query, Production Plan search, validation, and updates. |
| `__init__.py` | Python package marker. |

## Filters, columns, and actions

Filters refresh automatically when changed.

| Filter | Type | Behavior |
| --- | --- | --- |
| Company | Company Link | Defaults to the user's Company and matches `Material Request.company`. |
| From Date | Date | Includes `transaction_date >= from_date`. |
| To Date | Date | Includes `transaction_date <= to_date`. |

The table contains Sr No, Material Request, Date, Company, Item, Item Name, Qty, Warehouse, Batch No, and Production Plan. Document fields are rendered as links where applicable. Production Plan is the only editable column.

Toolbar actions:

- **Refresh** reloads data with current filters.
- **Save Changes** saves staged rows and displays their count.
- **Export CSV** exports loaded rows, including unsaved staged Production Plan values.

## Data selection

`get_data(filters=None)` performs an inner join between `Material Request` and `Material Request Item`. It returns one record per item when:

```text
Material Request.docstatus = 1
AND Material Request.advance_mr = 1
AND optional Company/date filters match
```


## Editing and save workflow

1. The user clicks a Production Plan cell.
2. Editing is blocked if the item has no Batch Number.
3. The inline editor searches by Batch Number; typed searches are debounced by 300 ms.
4. The server returns up to 50 submitted Production Plans containing a matching Production Plan Item `custom_batch_no`.
5. The chosen value is staged in browser memory and the cell is highlighted.
6. On save, changes are grouped by parent Material Request.
7. Each group is sent sequentially to `bulk_update_production_plan`.
8. The staged state is cleared and the report refreshes.

Keyboard controls are Enter to accept, Escape to restore the editor's initial value, Up/Down to navigate results, and Tab to accept the active result.

## API reference

All methods are under:

```text
generate_item.generate_item.page.pending_advance_mate.pending_advance_mate
```

### `get_data(filters=None)`

Returns report rows. `filters` may be a JSON string or a mapping with `company`, `from_date`, and `to_date`.

### `production_plan_query(doctype, txt, searchfield, start, page_len, filters)`

Provides autocomplete results. It uses `validate_and_sanitize_search_inputs`, requires `filters.batch_no`, selects distinct submitted Production Plans with a matching item Batch Number, matches typed text against the plan name, and orders newest first.

### `bulk_update_production_plan(material_request, updates)`

Updates selected child rows for one Material Request.

```json
{
  "material_request": "MAT-MR-00001",
  "updates": [
    {
      "name": "material-request-item-row-id",
      "production_plan": "PRO-PLAN-00001"
    }
  ]
}
```

Response:

```json
{
  "status": "success",
  "updated": 1,
  "skipped": 0,
  "message": "Production Plan linked for 1 item(s)."
}
```

Empty plan values become `null` and count as skipped. The client currently stages only non-empty changes, so it does not expose unlinking.

## Validation and transaction behavior

| Rule | Enforcement |
| --- | --- |
| Parent MR must be submitted. | Server checks `docstatus == 1`. |
| Child row must belong to the supplied MR. | Server maps valid row names from that parent. |
| Plan must match the item's Batch Number. | A matching `Production Plan Item` must exist. |
| Search requires a Batch Number. | Search returns no results without one. |
| Displayed MRs must be submitted Advance MRs. | Enforced by report SQL. |

Writes use `frappe.db.set_value` on `Material Request Item.production_plan` with `update_modified=False`. Normal Frappe request transaction handling is used; there is no explicit commit.

## Security and permissions

- The three methods are whitelisted for authenticated RPC use.
- Query values are parameterized; dynamic conditions come only from predefined filter clauses.
- The search method uses Frappe's search-input validation decorator.
- Update validation checks parent status, child ownership, and Batch compatibility.
- The Page metadata has no role restrictions, so access depends on Desk/module/page configuration.
- The SQL does not explicitly apply `frappe.has_permission` or user-permission match conditions. Add explicit enforcement if Company, document, or row-level isolation is required.
- The update endpoint does not verify Production Plan `docstatus`. The UI offers submitted plans only, but a direct RPC caller is not protected by the same rule.

## Error and state handling

| Scenario | Behavior |
| --- | --- |
| No report rows | Shows `No records found`. |
| Missing Batch Number | Shows an alert and blocks editing. |
| No matching plan | Shows a no-results dropdown message. |
| No staged changes | Shows an informational alert. |
| Child belongs to another MR | Server throws an error. |
| MR is not submitted | Server rejects the update. |
| Plan Batch does not match | Server rejects the update. |
| One MR group fails | Client reports it and continues with later groups. |

After the save loop, all pending state is cleared, including failed groups. Users must re-enter failed assignments.

## CSV export

CSV is produced in the browser from the current in-memory rows. Sr No is excluded; all values are quoted and embedded quotes are escaped. The name is:

```text
pending_advance_material_request_<current-datetime>.csv
```

No fresh server query is performed during export.

## Dependencies

| DocType | Fields used |
| --- | --- |
| Material Request | `name`, `transaction_date`, `company`, `docstatus`, `advance_mr` |
| Material Request Item | `parent`, `idx`, `item_code`, `item_name`, `qty`, `warehouse`, `custom_batch_no`, `production_plan` |
| Production Plan | `name`, `creation`, `docstatus` |
| Production Plan Item | `parent`, `custom_batch_no` |

