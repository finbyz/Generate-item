# Report Email Master DocType

A unified configuration for Report / Page email distributions and recipient groups in Frappe Framework.

---

## 1. DocType Architecture

### 1.1 Parent DocType: `Report Email Master`
- **DocType**: Root-level, non-submittable master.
- **Naming**: Set by user (`prompt`).
- **Type Field**: `Master` or `Group`.

#### Type = Master (Email Distribution Configuration)
- **Source**: Select (`Report`, `Page`).
- **Report Name**: Link to `Report` (conditional & mandatory when `Source = Report`).
- **Page Name**: Link to `Page` (conditional & mandatory when `Source = Page`).
- **Email Group**: Child Table (`Report Email Group`).
  - Holds links to Group-type `Report Email Master` documents.
  - Automatically calculates and stores recipient `count`.

#### Type = Group (Recipient Group Configuration)
- **Group Name**: Link to `Report Email Master` (optional nested / parent group, restricted to `Type = Group` with circular-reference validation).
- **Receipts**: Child Table (`Email Group User`).
  - `user`: Link to `User` (filtered to enabled users only).
- **CC**: Child Table (`Report Email CC`).
  - `cc_user`: Link to `User` (filtered to enabled users only).

---

## 2. Child DocTypes

### 2.1 `Report Email Group` (`istable = 1`)
Child table for Master configurations:
- `group_name`: Link to `Report Email Master` (filtered strictly to `Type = Group`).
- `count`: Int (calculated number of unique recipients in the referenced group).

### 2.2 `Email Group User` (`istable = 1`)
Child table for Group recipients:
- `user`: Link to `User`.

### 2.3 `Report Email CC` (`istable = 1`)
Child table for Group CC recipients:
- `cc_user`: Link to `User`.

---

## 3. Server-Side Validations (`report_email_master.py`)

1. **Master Configuration Rules**:
   - Clears group-specific fields (`group_name`, `receipts`, `cc`).
   - Enforces that `Source` is selected (`Report` or `Page`).
   - If `Source == Report`, `report_name` is mandatory and `page_name` is cleared.
   - If `Source == Page`, `page_name` is mandatory and `report_name` is cleared.
   - Enforces at least 1 `email_group` row.
   - Validates that each linked group has `Type == Group` and is not the master document itself.
   - Prevents duplicate groups in `email_group`.
   - Automatically maintains `row.count`.

2. **Group Configuration Rules**:
   - Clears master-specific fields (`source`, `report_name`, `page_name`, `email_group`).
   - Enforces at least 1 row in `receipts` table.
   - Validates that each user in `receipts` exists and is enabled (`enabled == 1`).
   - Prevents duplicate users in `receipts`.
   - If `group_name` is provided:
     - Prevents self-reference (`group_name == doc.name`).
     - Verifies `group_name` has `Type == Group`.
     - Detects and prevents circular ancestor chains.
   - Validates that each user in `cc` exists and is enabled (`enabled == 1`).
   - Prevents duplicate users in `cc`.

---

## 4. Recipient Resolution Helper (`get_resolved_recipients`)

Whitelisted API:
```python
generate_item.generate_item.doctype.report_email_master.report_email_master.get_resolved_recipients(report_email_master)
```

- **For Group**:
  - Resolves email addresses from `receipts` (`user`) into `To`.
  - Resolves email addresses from `cc` (`cc_user`) into `CC`.
  - Recursively resolves parent `group_name` if linked.
- **For Master**:
  - Traverses all linked groups in `email_group`.
  - Aggregates all `To` and `CC` recipients.
- **Deduplication Rules**:
  - `To` list is de-duplicated.
  - `CC` list is de-duplicated and excludes any address already present in `To`.
  - Skips disabled users, empty, or invalid email addresses.
  - Returns structured `{"to": [...], "cc": [...]}`.

---

## 5. Client Scripts (`report_email_master.js`)

- Dynamic field visibility toggling based on `type` and `source`.
- Immediately clears inactive fields when `type` or `source` changes.
- Link query filtering:
  - `email_group.group_name`: restricted to `Type == 'Group'`.
  - `group_name`: restricted to `Type == 'Group'` and excludes current document.
  - `receipts.user`: restricted to `enabled == 1`.
  - `cc.cc_user`: restricted to `enabled == 1`.
- Automatically calls `get_group_recipient_count` when `group_name` is chosen in `email_group`.
