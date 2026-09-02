# Functional Design Document (FDD)
# Manufacturing KPI Dashboard — Revision Control Analytics
## Steelstrong · Frappe / ERPNext Custom Page

---

| Field            | Value                                             |
|------------------|---------------------------------------------------|
| Document Type    | Functional Design Document (FDD)                  |
| Module           | Manufacturing — Revision Control                  |
| Page Name        | Manufacturing KPI Dashboard (`manufacturing-kpi-da`) |
| Backend File     | `manufacturing_kpi_da.py`                         |
| Frontend File    | `manufacturing_kpi_da.js`                         |
| Document Version | 1.0                                               |
| Prepared For     | Functional Consultants · Business Analysts · QA Engineers · Project Managers · Developers |
| Date             | August 2026                                       |

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Document Purpose and Scope](#document-purpose-and-scope)
3. [Business Context](#business-context)
4. [Key Terminology / Glossary](#key-terminology--glossary)
5. [Data Flow](#data-flow)
6. [DocTypes Involved](#doctypes-involved)
7. [Main API Entry Point](#main-api-entry-point)
8. [Helper Functions](#helper-functions)
9. [Dashboard Sections — Feature-by-Feature](#dashboard-sections--feature-by-feature)
    - 9.1 Branch-Wise Changes
    - 9.2 Order Change Intensity (Buckets)
    - 9.3 Batch Traceability Count
    - 9.4 Top Revision Creators (Leaderboard)
    - 9.5 Fewest Revision Creators
    - 9.6 Sales Order Health Scores
    - 9.7 Milestone Achievements
    - 9.8 30-Day Revision Trend
    - 9.9 Top Changed Items
    - 9.10 Revision Velocity
    - 9.11 Batch Change Intensity (Buckets)
10. [Dashboard KPI Summary Table](#dashboard-kpi-summary-table)
11. [Business Rules](#business-rules)
12. [Calculation Logic Reference](#calculation-logic-reference)
13. [Limitations and Assumptions](#limitations-and-assumptions)

---

## 1. Executive Summary

The **Manufacturing KPI Dashboard** is a real-time analytics page built inside Frappe/ERPNext for the Steelstrong manufacturing environment. Its sole purpose is to give management, production supervisors, and business analysts a single-screen view of how frequently Sales Orders are being revised through the **Order Modification Request (OMR)** process.

Every time a production order's item, quantity, rate, or line status needs to change after a Sales Order is confirmed, an **Order Modification Request** is raised and submitted. Over time, the frequency, pattern, and ownership of these modification requests reveal the health of the manufacturing planning process.

The dashboard answers ten critical business questions:

| # | Question | Dashboard Section |
|---|---|---|
| 1 | Which branch raises the most modifications? | Branch-Wise Changes |
| 2 | How many Sales Orders have been revised once, twice, three times, or more? | Order Change Intensity |
| 3 | How many unique item-batch combinations have been touched across all modifications? | Batch Traceability Count |
| 4 | Who creates the most modification requests? | Revision Leaderboard – High |
| 5 | Who creates the fewest modification requests? | Revision Leaderboard – Low |
| 6 | Which Sales Orders are "unhealthy" (heavily revised)? | Health Scores |
| 7 | Has the team hit any process milestones? | Milestone Achievements |
| 8 | Is the rate of modification increasing or decreasing over the last 30 days? | 30-Day Trend |
| 9 | Which items are being changed the most across all OMRs? | Top Changed Items |
| 10 | How fast does the team respond to changes, and when are they most active? | Revision Velocity |

Only **submitted (docstatus = 1)** Order Modification Requests are counted, ensuring that only formally approved changes are measured.

---

## 2. Document Purpose and Scope

### Purpose

This document describes the **business functionality** implemented in the Manufacturing KPI Dashboard backend (`manufacturing_kpi_da.py`). It is intended to be used as a reference by:

- **Functional Consultants** customising or extending the dashboard
- **Business Analysts** validating that KPIs reflect the correct business logic
- **QA Engineers** writing test cases for the dashboard data
- **Project Managers** presenting dashboard capabilities to stakeholders
- **Developers** maintaining or enhancing the codebase

### Scope

This document covers:
- All ten KPI functions exposed by the backend
- All helper/utility functions
- Every business rule and calculation formula
- Data sources, inputs, and outputs for each function
- Edge cases and limitations

### Out of Scope
- Frontend rendering logic (JavaScript/CSS)
- ERPNext standard DocType configuration
- User permission setup

---

## 3. Business Context

In a make-to-order manufacturing environment like Steelstrong, a **Sales Order** is the starting point for production planning. Once a Sales Order is confirmed and enters production, any change to quantities, materials, rates, or line items must pass through a formal revision process — the **Order Modification Request (OMR)**.

An OMR records:
- Which Sales Order is being revised
- Which items are being changed (`Sales Order Item For OMR` child table)
- Which branch raised the request
- Who raised the request (owner/creator)
- What fields were changed (via `rev_*` revision fields)

The accumulation of OMR data over time is a **leading indicator of planning quality**. A healthy manufacturing process will show:
- Few OMRs per Sales Order
- OMRs concentrated on early-stage orders
- Short lag between order creation and first revision (changes caught early)
- Consistent, declining trend in modification frequency

The dashboard translates raw OMR data into actionable management intelligence.

---

## 4. Key Terminology / Glossary

| Term | Definition |
|------|------------|
| **OMR** | Order Modification Request — the formal document used to record a change to a Sales Order after confirmation |
| **Submitted OMR** | An OMR with `docstatus = 1`, meaning it has been reviewed and approved |
| **rev_* fields** | Fields prefixed with `rev_` in the `Sales Order Item For OMR` child table; they store the revised values for item code, description, quantity, rate, and line status |
| **Row Changed** | A child row in an OMR is considered "changed" if at least one `rev_*` field contains a non-null, non-empty, non-zero value |
| **Item + Batch Combination** | A unique pairing of an item code and a batch number within a single OMR, used for traceability counting |
| **Health Score** | A calculated 0–100 index for a Sales Order, reflecting how many revisions it has undergone relative to its age |
| **Revision Velocity** | The rate at which OMRs are being created, expressed as average revisions per day |
| **Branch** | A physical warehouse or operational location linked to an OMR |
| **Leaderboard** | A ranked list of users ordered by their OMR creation count |

---

## 5. Data Flow

```
Sales Order (SO)
        │
        │  [Sales Order is confirmed and enters production]
        │
        ▼
Order Modification Request (OMR)
  ├── branch
  ├── sales_order  ──────────────────────────────► Sales Order (reference)
  ├── owner (creator)
  ├── docstatus (1 = Submitted)
  └── [child table] Sales Order Item For OMR
            ├── item
            ├── batch_no
            ├── rev_item
            ├── rev_description
            ├── rev_line_status
            ├── rev_qty
            └── rev_rate
                    │
                    ▼
        Dashboard KPI Calculation
        ┌──────────────────────────────────────────┐
        │  get_dashboard_data()                     │
        │   ├── get_branch_wise_changes()            │
        │   ├── get_order_change_buckets()           │
        │   ├── get_batch_change_count()             │
        │   ├── get_top_creators()  [high/low]       │
        │   ├── get_order_health_scores()            │
        │   ├── get_milestone_achievements()         │
        │   ├── get_30_day_trends()                  │
        │   ├── get_top_changed_items()              │
        │   └── get_revision_velocity()              │
        └──────────────────────────────────────────┘
                    │
                    ▼
        Dashboard UI (manufacturing_kpi_da.js)
        ┌───────────────────────────────────────────┐
        │  Section 01 · Branch Distribution          │
        │  Section 02 · Order Change Intensity        │
        │  Section 03 · Batch Traceability            │
        │  Section 04 · Revision Leaderboard          │
        │  Section 05 · Real-Time Insights            │
        │    ├── Milestones                           │
        │    ├── 30-Day Sparkline Trend               │
        │    ├── Revision Velocity                    │
        │    ├── Sales Order Health Scores            │
        │    └── Most Revised Items                   │
        └───────────────────────────────────────────┘
```

---

## 6. DocTypes Involved

| DocType | Role in Dashboard | Key Fields Used |
|---------|-------------------|-----------------|
| **Order Modification Request** | Primary data source for all KPIs | `name`, `branch`, `sales_order`, `owner`, `creation`, `modified`, `docstatus` |
| **Sales Order Item For OMR** | Child table of OMR; provides item-level revision detail | `parent`, `item`, `batch_no`, `rev_item`, `rev_description`, `rev_line_status`, `rev_qty`, `rev_rate` |
| **Sales Order** | Referenced to compute order age (days since creation) | `name`, `creation` |
| **User** | Lookup to convert system `owner` (email) to display name | `name`, `full_name` |
| **Item** | Lookup to convert item codes to display names and UOM | `name`, `item_name`, `stock_uom` |

> **Important:** Only **`docstatus = 1`** (Submitted) OMRs are included in all KPI calculations. Draft or cancelled OMRs are excluded from every metric.

---

## 7. Main API Entry Point

### `get_dashboard_data()`

---

**Business Purpose**

This is the single API endpoint called by the dashboard UI on page load and on every manual refresh. It orchestrates all ten KPI functions and bundles their results into one JSON response.

**Data Source**
Delegates to individual KPI functions — see Section 9.

**Functional Logic**

1. Sets a base filter: `{ "docstatus": 1 }` — only submitted OMRs are evaluated.
2. Calls each of the ten KPI functions, passing this filter as a parameter.
3. Appends a `generated_at` timestamp (current server time) to the response.
4. Returns a single dictionary containing all KPI data.

**Input**
None (called without parameters from the UI).

**Output**

```
{
  "branch_wise":       [...],
  "order_change":      {...},
  "batch_change":      {"total": N},
  "top_creators_high": [...],
  "top_creators_low":  [...],
  "health_scores":     [...],
  "milestones":        [...],
  "trends":            {...},
  "top_items":         [...],
  "velocity":          {...},
  "generated_at":      "2026-08-03 07:56:00"
}
```

**Business Rules**
- All KPIs are always scoped to submitted OMRs only.
- All KPIs are calculated at the time of the API call (real-time, not cached).

---

## 8. Helper Functions

### 8.1 `_row_is_changed(row)`

---

**Business Purpose**

Determines whether a single child row in an OMR actually contains a meaningful revision. Not all rows in `Sales Order Item For OMR` may carry changes — some rows may be informational stubs. This function acts as the gatekeeper to ensure only genuinely revised rows are counted in item-level metrics.

**Functional Logic**

The function checks all `rev_*` fields (e.g., `rev_item`, `rev_description`, `rev_line_status`, `rev_qty`, `rev_rate`) on a given row. If **any one of them** contains a value that is:
- Not `None`
- Not an empty string `""`
- Not numeric zero (`0` or `0.0`)
- Not a string containing only whitespace

…then the row is considered **changed** and returns `True`. If all `rev_*` fields are empty/zero/null, the row is considered **unchanged** and returns `False`.

**Business Rule Applied**

> A row counts as a revision only if at least one change field has been filled in.

**Example**

| rev_item | rev_qty | rev_rate | rev_description | Is Changed? |
|----------|---------|----------|-----------------|-------------|
| ITEM-002 | *(empty)* | *(empty)* | *(empty)* | ✅ Yes |
| *(empty)* | 0 | 0.0 | *(empty)* | ❌ No |
| *(empty)* | 50 | *(empty)* | *(empty)* | ✅ Yes |
| *(empty)* | *(empty)* | *(empty)* | *(empty)* | ❌ No |

---

### 8.2 `get_average_revision_velocity(filters)`

---

**Business Purpose**

Calculates how many hours, on average, pass between the creation of a Sales Order and the submission of its **first** Order Modification Request. This measures how quickly the business identifies and formally records that a change is needed after an order is placed.

**Data Source**
- `tabSales Order` — `creation` date
- `tabOrder Modification Request` — `creation` date, grouped by `sales_order`

**Functional Logic**

1. Joins `Sales Order` and `Order Modification Request` tables.
2. For each Sales Order that has at least one submitted OMR, finds the **minimum OMR creation date** (i.e., the date the first revision was raised).
3. Calculates the difference in hours between the Sales Order creation and the first OMR creation.
4. Excludes cases where the difference is zero or negative (invalid data).
5. Returns the average across all qualifying Sales Orders.

**Formula**

```
Average Velocity (hours) =
    SUM( First_OMR_Creation – SO_Creation ) in hours
    ─────────────────────────────────────────────────
           COUNT( qualifying Sales Orders )
```

**Input**
- Base filters (docstatus = 1)

**Output**
- A single float number representing average hours, or `None` if no data exists.

**Edge Cases**
- Returns `None` if no Sales Orders have any submitted OMRs.
- Rows where either the SO creation or OMR creation timestamp is missing are skipped.
- Zero or negative hour differences (OMR created before or at the same instant as SO) are excluded.
- Capped at 100 Sales Orders per query to maintain performance.

---

### 8.3 `get_branch_counts_for_period(start_date, end_date, base_filters)`

---

**Business Purpose**

A utility function that counts submitted OMRs per branch for a specific date range. Used internally by the milestone achievement logic to compare branch activity across time periods.

**Functional Logic**

1. Applies the base filters plus a `creation BETWEEN start_date AND end_date` constraint.
2. Groups results by `branch`.
3. Returns a dictionary mapping each branch name to its count.

**Output**
```
{ "Sanand": 12, "Rabale": 8, "Not Set": 3 }
```

---

## 9. Dashboard Sections — Feature-by-Feature

---

### 9.1 Branch-Wise Changes

---

**KPI Name:** Branch Distribution of Order Modification Requests

**Business Purpose**

Shows how many submitted Order Modification Requests originated from each branch. Management uses this view to identify which operational locations generate the most revision activity, which may indicate planning issues, design changes, or execution challenges specific to that site.

**Data Source**
- `Order Modification Request` (submitted only)
- Fields: `branch`, `COUNT(name)`

**Functional Logic**

1. Fetches all submitted OMRs.
2. Groups them by the `branch` field.
3. Counts the number of OMRs per branch.
4. Orders branches in descending order of count (highest first).
5. Replaces blank/null branch values with the label "Not Set".

**Formula**

```
Branch Count = COUNT(submitted OMRs) GROUP BY branch ORDER BY count DESC
```

**Input**
- `{ "docstatus": 1 }`

**Output**

| branch | count |
|--------|-------|
| Sanand | 45 |
| Rabale | 28 |
| Not Set | 5 |

**Example**

> Sanand branch has 45 submitted OMRs, Rabale has 28. This indicates Sanand generates nearly twice the revision activity and may warrant a planning review.

**Business Value**

- Identifies branches with the highest revision burden.
- Supports resource allocation decisions (more planning staff where most revisions occur).
- Highlights branches with no revisions (potentially healthy, or potentially not using the system).

**Business Rules**
- Only `docstatus = 1` records are counted.
- Null or empty branch values are grouped under "Not Set".
- No upper limit on number of branches displayed.

---

### 9.2 Order Change Intensity (Buckets)

---

**KPI Name:** Order Change Bucketing by Revision Frequency

**Business Purpose**

Answers the question: "For each Sales Order that has been revised, how many times has it been revised?" Orders are placed into four severity buckets based on their cumulative OMR count. This helps management understand not just how many orders were changed, but how severely they were changed.

**Data Source**
- `Order Modification Request` (submitted only)
- Fields: `sales_order`, `COUNT(name) as count`

**Functional Logic**

1. Groups submitted OMRs by `sales_order`.
2. Counts how many OMRs exist per Sales Order.
3. Assigns each Sales Order to one of four buckets:

| Bucket | Condition | Label |
|--------|-----------|-------|
| `"1"` | Exactly 1 OMR | 1 Item Changed |
| `"2"` | Exactly 2 OMRs | 2 Items Changed |
| `"3"` | Exactly 3 OMRs | 3 Items Changed |
| `"3+"` | 4 or more OMRs | 3+ Items Changed |

4. Returns the count of Sales Orders in each bucket.

**Formula**

```
Bucket["1"]  = COUNT(sales_orders WHERE COUNT(OMR) = 1)
Bucket["2"]  = COUNT(sales_orders WHERE COUNT(OMR) = 2)
Bucket["3"]  = COUNT(sales_orders WHERE COUNT(OMR) = 3)
Bucket["3+"] = COUNT(sales_orders WHERE COUNT(OMR) >= 4)
```

**Output**

```json
{
    "1": {
        "total": 30,
        "branches": {
            "Sanand": 15,
            "Rabale": 10,
            "Nandikoor": 5
        }
    },
    "2": {
        "total": 12,
        "branches": {
            "Sanand": 8,
            "Rabale": 4
        }
    },
    "3": {
        "total": 5,
        "branches": {
            "Sanand": 5
        }
    },
    "3+": {
        "total": 3,
        "branches": {
            "Rabale": 3
        }
    },
    "_drill": {
        "1": ["SO-001", "SO-002", ...],
        ...
    }
}
```

**Example**

> Of 50 revised Sales Orders: 30 were changed only once (well handled), 12 twice, 5 three times, and 3 were revised 4 or more times. The 3 orders in the "3+" bucket require immediate management attention.

**Business Value**

- Quickly identifies "problem orders" that are being repeatedly revised.
- A high count in the "3+" bucket signals systemic planning failures or design instability.
- A high count in the "1" bucket suggests the revision process is being used efficiently (catching changes early and once).

**Business Rules**
- Only submitted OMRs are counted.
- One Sales Order can appear in only one bucket, based on its total OMR count.
- All four buckets always render on the dashboard, even if a bucket count is zero.

---

### 9.3 Batch Traceability Count

---

**KPI Name:** Unique Item + Batch Combinations Changed Per OMR

**Business Purpose**

Provides a traceability metric by counting how many unique Item + Batch number combinations have been touched across all submitted OMRs.

In a manufacturing context, batch numbers are critical for traceability — knowing which physical batch of raw material was involved in a change is essential for quality audits and regulatory compliance. This KPI ensures management knows how broad the batch-level impact of all revisions is.

**Data Source**
- `Order Modification Request` (submitted) — to get the list of applicable OMRs
- `Sales Order Item For OMR` — to get item and batch details

**Functional Logic**

1. Retrieves all submitted OMR names.
2. Fetches all child rows from `Sales Order Item For OMR` that belong to these OMRs.
3. Filters rows to only those that:
   - Have a non-empty `batch_no`
   - Are considered changed per `_row_is_changed()`
4. Creates a set of unique tuples: `(OMR name, item code, batch number)`.
5. Returns the count of unique tuples in this set.

> **Key Rule:** The same Item + Batch within the **same OMR** is counted only **once**, even if multiple child rows reference it. However, the same Item + Batch in a **different OMR** is counted **again**.

**Formula**

```
Batch Change Count = COUNT(DISTINCT {OMR_name, item, batch_no})
                     WHERE batch_no IS NOT NULL
                     AND row is changed
```

**Output**

```json
{ "total": 87 }
```

**Example**

> OMR-001 changed ITEM-A in Batch-100 across 3 rows → counted **once** for OMR-001.
> OMR-002 also changed ITEM-A in Batch-100 → counted **again** for OMR-002.
> Total: 2 entries for ITEM-A / Batch-100 across two OMRs.

**Business Value**

- Supports batch-level impact analysis for quality management.
- High batch change counts may indicate recurring raw material substitution issues.
- Useful during internal audits to quantify the scope of production-level changes.

**Business Rules**
- Only rows with a non-empty `batch_no` are counted.
- Only changed rows (per `_row_is_changed()`) are counted.
- Uniqueness is enforced at the `(OMR, item, batch)` level — not globally across all OMRs.

---

### 9.4 Top Revision Creators (Most Revisions)

---

**KPI Name:** Users with Highest OMR Creation Count

**Business Purpose**

Identifies which system users have submitted the most Order Modification Requests. In a manufacturing organisation, a high revision count for a specific user may indicate:
- A power user managing complex accounts
- An operator with a territory that has high change frequency
- Potential training needs if one person is raising many unnecessary revisions

**Data Source**
- `Order Modification Request` — `owner`, `COUNT(name)`
- `User` — `full_name` (for display)

**Functional Logic**

1. Groups submitted OMRs by `owner` (the user who created the record).
2. Counts OMRs per owner.
3. Sorts in **descending** order of count.
4. Returns the top **10** users.
5. Looks up the `full_name` of each owner from the `User` DocType for display.
6. Falls back to the email/username if the full name is not available.

**Formula**

```
Top Creators = SELECT owner, COUNT(name) as count
               FROM OMR
               WHERE docstatus = 1
               GROUP BY owner
               ORDER BY count DESC
               LIMIT 10
```

**Output**

| owner (email) | full_name | count |
|---------------|-----------|-------|
| john@steel.com | John Mehta | 32 |
| priya@steel.com | Priya Shah | 28 |

**Business Rules**
- Top 10 users are returned; the UI shows 5 and exposes the rest via a "View More" button.
- If a User record does not have a `full_name`, the raw owner email/ID is used as the display value.

---

### 9.5 Fewest Revision Creators

---

**KPI Name:** Users with Lowest OMR Creation Count

**Business Purpose**

Identifies users who submit the fewest OMRs. These users may represent locations or accounts with the most stable, well-planned production orders — or they may indicate under-reporting.

**Data Source**
Same as Section 9.4.

**Functional Logic**

Identical to Section 9.4, except the ORDER BY is **ascending** (lowest count first).

**Formula**

```
SELECT owner, COUNT(name) as count
FROM OMR
WHERE docstatus = 1
GROUP BY owner
ORDER BY count ASC
LIMIT 10
```

**Business Rules**
- Same as Top Creators.
- Ascending sort returns users with the fewest modifications first.

---

### 9.6 Sales Order Health Scores

---

**KPI Name:** Order Health Index (0–100)

**Business Purpose**

Assigns a numerical health score between 0 and 100 to each Sales Order that has been revised, indicating how "healthy" the order's revision history is. A score of 100 means the order is in excellent shape (few revisions, old enough to have settled). A score near 0 means the order has been heavily revised and may be at risk.

**Data Source**
- `Order Modification Request` — per Sales Order group
- `Sales Order Item For OMR` — for changed item count
- `Order Modification Request` — for `creation` (order age) and `modified`

**Functional Logic**

1. Retrieves the top 10 Sales Orders (by OMR count, descending) that have at least one submitted OMR.
2. For each Sales Order:
   a. Counts all submitted OMRs (`omr_count`).
   b. Retrieves all changed child rows across all those OMRs to compute `changed_items`.
   c. Calculates `age_days` = difference in days between the OMR's `creation` and today.
   d. Computes a health score using penalty/bonus components (see formula).
3. Assigns a **status** label and **emoji** based on the final score.
4. Returns the list sorted by ascending health score (least healthy first, so management focuses on the worst first).

**Formula (complete mathematical breakdown)**

```
revision_penalty = MIN(omr_count × 15, 50)
items_penalty    = MIN(changed_items × 2, 30)
age_bonus        = MIN((age_days ÷ 30) × 5, 20)

health_score     = MAX(0, 100 - revision_penalty - items_penalty + age_bonus)
```

**Component Breakdown**

| Component | Formula | Maximum Impact | Direction |
|-----------|---------|----------------|-----------|
| Revision Penalty | `OMR count × 15` | −50 points (capped) | Negative |
| Items Penalty | `Changed items × 2` | −30 points (capped) | Negative |
| Age Bonus | `(Age in days ÷ 30) × 5` | +20 points (capped) | Positive |
| Base Score | 100 | — | Starting value |
| Floor | MAX(0, result) | Cannot go below 0 | — |

**Status Classification**

| Score Range | Status | Emoji |
|-------------|--------|-------|
| 80–100 | Excellent | 🟢 |
| 60–79 | Good | 🟡 |
| 40–59 | Fair | 🟠 |
| 0–39 | Poor | 🔴 |

**Worked Example**

> Sales Order SO-2025-0042:
> - `omr_count` = 4 → revision_penalty = MIN(4 × 15, 50) = **50**
> - `changed_items` = 8 → items_penalty = MIN(8 × 2, 30) = **16**
> - `age_days` = 90 → age_bonus = MIN((90 ÷ 30) × 5, 20) = MIN(15, 20) = **15**
> - `health_score` = MAX(0, 100 − 50 − 16 + 15) = **49** → Status: **Fair 🟠**

**Output**

| Sales Order | Health Score | Status | OMR Count | Changed Items | Age (days) |
|-------------|-------------|--------|-----------|---------------|------------|
| SO-2025-0042 | 49 | Fair 🟠 | 4 | 8 | 90 |
| SO-2025-0018 | 20 | Poor 🔴 | 6 | 12 | 45 |

**Business Value**

- Enables managers to immediately spot the worst-performing Sales Orders.
- Age bonus ensures long-standing, stable orders are not penalised for historical revisions.
- The capped penalties prevent a single heavily-revised order from dominating all scoring.

**Business Rules**
- Only the top 10 most-revised Sales Orders are scored (for performance).
- Health score is always between 0 and 100 (floored at 0).
- Result is sorted ascending — lowest scores (worst health) appear first in the UI.

---

### 9.7 Milestone Achievements

---

**KPI Name:** Process Milestone Badges

**Business Purpose**

Celebrates process adoption and usage milestones to gamify engagement with the revision control system. Milestones appear as achievement cards on the dashboard, providing positive reinforcement when the team crosses key usage thresholds.

**Data Source**
- `Order Modification Request` — counts and date filters
- Helper: `get_average_revision_velocity()` — for speed-based milestones

**Functional Logic**

The function evaluates up to **5 potential milestones** and returns the **first 3** that are earned:

#### Milestone 1 — Process Active / Getting Started

| Condition | Badge |
|-----------|-------|
| Total submitted OMRs ≥ 10 | 🏆 "Process Active" — `{N} modifications processed` |
| Total submitted OMRs ≥ 5 (but < 10) | 🎯 "Getting Started" — `{N} modifications logged` |

#### Milestone 2 — Active Tracking

| Condition | Badge |
|-----------|-------|
| Submitted OMRs created in the last 7 days > 0 | 📊 "Active Tracking" — `{N} revisions in last 7 days` |

#### Milestone 3 — Branch Coverage

| Condition | Badge |
|-----------|-------|
| Distinct branches with OMRs ≥ 3 | 🌐 "Multi-Branch Coverage" — `{N} branches using revision system` |
| Distinct branches with OMRs ≥ 1 (but < 3) | 📍 "Branch Active" — `{N} branch submitting revisions` |

#### Milestone 4 — Response Speed

| Condition | Badge |
|-----------|-------|
| Average revision velocity < 24 hours | ⚡ "Lightning Fast Response" — `Average revision in {X.X} hours` |
| Average revision velocity < 48 hours (but ≥ 24) | 🚀 "Quick Response Time" — `Average revision in {X.X} hours` |
| Average revision velocity ≥ 48 hours or no data | *(No badge awarded)* |

#### Milestone 5 — Leading Branch

| Condition | Badge |
|-----------|-------|
| The top branch has ≥ 3 OMRs | 👑 "Leading Branch" — `{Branch} leads with {N} revisions` |

**Output (up to 3 milestones)**

```json
[
  { "type": "achievement", "icon": "🏆", "title": "Process Active",
    "message": "108 modifications processed",
    "detail": "Your revision control system is tracking changes effectively" },
  { "type": "activity", "icon": "📊", "title": "Active Tracking",
    "message": "4 revisions in last 7 days",
    "detail": "Team is actively using the revision system" },
  { "type": "coverage", "icon": "🌐", "title": "Multi-Branch Coverage",
    "message": "3 branches using revision system",
    "detail": "Revision control adopted across multiple locations" }
]
```

**Business Rules**
- Only the first 3 earned milestones are displayed (`milestones[:3]`).
- Milestones evaluate in the fixed order: volume → recent activity → branch coverage → speed → leading branch.
- "Process Active" and "Getting Started" are mutually exclusive (only one can be earned).
- Speed milestones require `get_average_revision_velocity()` to return a value (not `None`).

---

### 9.8 Revision Trend & Period-wise Changes

---

**KPI Name:** Daily Revision Count — 30-Day Sparkline & Period-wise Breakdown

**Business Purpose**

Plots the day-by-day count of submitted OMRs over the last 30 days as a sparkline chart. Provides management with a visual trend to determine whether revision activity is increasing (a concern) or decreasing (a positive sign of improving planning).
Additionally, it breaks down the changes into a period-wise list (Monthly, Weekly, or Daily) based on the selected date filter, allowing users to see the exact distribution of changes over time.

**Data Source**
- `Order Modification Request` — `creation` date, `docstatus = 1`
- Direct SQL query for performance

**Functional Logic**

1. Calculates the start date as 30 days before the current server time.
2. Queries the count of submitted OMRs grouped by calendar date within this 30-day window.
3. Fills in **zero** for any date that had no OMRs (to produce a complete, gapless 31-day series).
4. Computes trend direction by comparing the first 15 days to the last 15+ days:
5. Dynamically groups the daily data into Monthly, Weekly, or Daily buckets based on the active date preset:
   - **Yearly Presets** ("This Year", "Last Year"): Groups data by Month (January–December).
   - **Monthly Presets** ("This Month", "Last Month"): Groups data by Week (Week 1–5).
   - **Weekly/Daily Presets** ("This Week", "Last Week", "Today", "Custom"): Displays data by Day (Day 1–7).

**Trend Direction Calculation**

```
first_half  = SUM of counts for days 1–15
second_half = SUM of counts for days 16–31

change_pct = ((second_half − first_half) ÷ first_half) × 100
```

| `change_pct` | Trend Direction | Emoji |
|--------------|-----------------|-------|
| < −10% | Down (improving) | 📉 |
| > +10% | Up (worsening) | 📈 |
| Between −10% and +10% | Stable | 📊 |

**Special Cases for `change_pct`**

| Condition | Result |
|-----------|--------|
| `first_half = 0` and `second_half = 0` | `change_pct = 0` |
| `first_half = 0` and `second_half > 0` | `change_pct = 100` (new activity) |

**Output**

```json
{
  "daily_data": [
    { "date": "2026-07-04", "count": 0, "label": "04 Jul" },
    { "date": "2026-07-05", "count": 3, "label": "05 Jul" },
    ...
  ],
  "trend_direction": "down",
  "trend_emoji": "📉",
  "change_percentage": -18.5,
  "total_this_month": 42
}
```

**Business Value**

- A declining trend indicates the team is improving its planning accuracy.
- A rising trend signals a need to investigate planning or design change drivers.
- The sparkline gives a visual impression without requiring users to read raw numbers.

**Business Rules**
- Always returns 31 data points (today + 30 previous days), regardless of actual OMR activity.
- Days with no OMRs are represented as zero — they are not omitted from the series.
- Trend direction requires at least 14 data points to be meaningful; otherwise defaults to "stable".

---

### 9.9 Top Changed Items

---

**KPI Name:** Most Frequently Revised Items

**Business Purpose**

Identifies which inventory items appear most often in submitted OMR revision rows. Frequently revised items may indicate:
- Design instability for that item
- Supply chain issues (substitutions)
- Quoting problems (incorrect rates at order time)

**Data Source**
- `Order Modification Request` (submitted) — for OMR names
- `Sales Order Item For OMR` — for item codes and `rev_*` fields
- `Item` — for display names and UOM

**Functional Logic**

1. Retrieves all submitted OMR names.
2. Fetches all child rows from `Sales Order Item For OMR` belonging to these OMRs.
3. For each changed row (per `_row_is_changed()`):
   - If `item` is populated, uses it as the item code.
   - If `item` is empty, falls back to `rev_item` (the replacement item code).
   - If both are empty, the row is skipped.
4. Counts how many changed rows reference each unique item code.
5. Looks up the `item_name` and `stock_uom` from the `Item` master for display.
6. Sorts by count descending, returns the top 10.
7. Calculates a `percentage` for each item relative to the most-revised item (for bar chart rendering).

**Formula**

```
Item Change Count  = COUNT(changed rows WHERE item_code = X)
Percentage         = (Item Count ÷ Max Item Count) × 100   [rounded to nearest integer]
```

**Output**

| item_code | item_name | count | percentage |
|-----------|-----------|-------|------------|
| ITEM-0023 | MS Flat Bar 40×5 | 18 | 100% |
| ITEM-0110 | HR Coil 2mm | 12 | 67% |
| ITEM-0045 | GI Sheet 1.2mm | 9 | 50% |

**Business Value**

- Highlights chronic problem items that need design review or supplier improvement.
- Supports procurement decisions (if an item is repeatedly substituted, consider a strategic stockpile or alternative sourcing).
- Enables targeted training: if certain item codes are always being revised, there may be a knowledge gap in the quoting or planning team.

**Business Rules**
- Only changed rows (per `_row_is_changed()`) are counted.
- `rev_item` is used as a fallback when `item` is null (to capture item-substitution revisions).
- Item lookup is batched in groups of 100 for performance.
- Returns a maximum of 10 items.
- The item with the highest count always shows 100%; all others are relative.

---

### 9.10 Revision Velocity

---

**KPI Name:** Revision Velocity Metrics

**Business Purpose**

Provides a set of operational rhythmics around how the revision system is being used over the last 30 days: how often revisions occur per day, which day of the week is most active, and what hour of the day sees the most revisions. This helps operations managers understand team work patterns and plan capacity.

**Data Source**
- `Order Modification Request` — `creation` datetime, `docstatus = 1`
- Direct SQL queries for day-of-week and hour-of-day aggregation

**Functional Logic**

1. **Average Revisions per Day:**
   - Counts total submitted OMRs created in the last 30 days.
   - Divides by 30 to get a daily average.

2. **Most Active Day of Week:**
   - Groups OMRs by day name (Monday–Sunday) over the last 30 days.
   - Returns the day with the highest count.

3. **Peak Hour:**
   - Groups OMRs by hour of day (0–23) over the last 30 days.
   - Returns the hour with the highest count, formatted as `HH:00`.

4. **Insight Text:**
   Assembles a natural-language summary: `"Peak activity on {Day}s around {Hour}"`

**Formulas**

```
Avg Per Day         = COUNT(submitted OMRs in last 30 days) ÷ 30
Most Active Day     = day_name WHERE COUNT(OMRs) is maximum (last 30 days)
Peak Hour           = HOUR(creation) WHERE COUNT(OMRs) is maximum (last 30 days)
```

**Output**

```json
{
  "avg_per_day": 1.4,
  "total_last_30_days": 42,
  "most_active_day": "Tuesday",
  "peak_hour": "10:00",
  "insight": "Peak activity on Tuesdays around 10:00"
}
```

**Business Value**

- Average per day tells management whether the revision workload is manageable.
- Most active day reveals planning meeting effects (e.g., if revisions spike after Monday planning calls).
- Peak hour helps IT and system administrators schedule maintenance windows when the system is least active.

**Business Rules**
- "Last 30 days" is computed from the current server timestamp at the moment of API call.
- If no OMRs exist in the last 30 days, `avg_per_day` will be `0`, and `most_active_day` / `peak_hour` will return `"N/A"`.
- The `avg_per_day` is always divided by a fixed denominator of 30, regardless of how many calendar days have actually elapsed since the system was deployed.

---

### 9.11 Batch Change Intensity (Buckets)

---

**KPI Name:** Batch Change Bucketing by Revision Frequency

**Business Purpose**

Similar to Order Change Intensity, this KPI buckets unique Item + Batch combinations based on how many times they have been revised across different OMRs. It helps identify specific batches that are undergoing repeated modifications, which could indicate quality issues or instability in raw material allocation.

**Data Source**
- `Order Modification Request` (submitted only)
- `Sales Order Item For OMR` — `item`, `batch_no`

**Functional Logic**

1. Retrieves all submitted OMRs and their child rows.
2. Filters for rows with a valid `batch_no` that are considered changed.
3. Groups the unique `(item, batch_no)` combinations and counts how many distinct OMRs they appear in.
4. Assigns each combination to one of four buckets (1, 2, 3, 3+).
5. Provides a branch-wise breakdown for each bucket based on the branch of the first OMR in the set.

**Output**

```json
{
    "1": {
        "total": 45,
        "branches": {
            "Sanand": 20,
            "Rabale": 15,
            "Nandikoor": 10
        }
    },
    "2": {
        "total": 12,
        "branches": {
            "Sanand": 8,
            "Rabale": 4
        }
    },
    "3": {
        "total": 5,
        "branches": {
            "Sanand": 5
        }
    },
    "3+": {
        "total": 2,
        "branches": {
            "Rabale": 2
        }
    },
    "_drill": {
        "1": ["OMR-001", "OMR-002", ...],
        ...
    }
}
```

**Business Value**

- Highlights specific batches that are problematic and require investigation.
- The branch-wise breakdown helps pinpoint if a specific location is struggling with certain batches.

---

## 10. Dashboard KPI Summary Table

| # | KPI Name | Purpose | Formula | Data Source | Output Format |
|---|----------|---------|---------|-------------|--------------|
| 1 | Branch Distribution | Count OMRs per branch | `COUNT(OMR) GROUP BY branch` | Order Modification Request | List: Branch, Count |
| 2 | Order Change Intensity | Bucket SOs by revision frequency | `COUNT(OMR) GROUP BY SO → bucket by count` | Order Modification Request | 4 Bucketed Counts |
| 3 | Batch Traceability | Count unique Item+Batch pairs changed | `COUNT(DISTINCT {OMR, item, batch})` WHERE changed | Sales Order Item For OMR | Single integer |
| 4 | Top Creators | Top 10 users by OMR creation count | `COUNT(OMR) GROUP BY owner ORDER BY count DESC LIMIT 10` | OMR + User | List: Name, Count |
| 5 | Fewest Creators | Bottom 10 users by OMR count | Same as above, `ORDER BY count ASC` | OMR + User | List: Name, Count |
| 6 | Health Score | 0–100 index per Sales Order | `100 − MIN(OMR×15,50) − MIN(items×2,30) + MIN(age÷30×5,20)` | OMR + Sales Order Item For OMR | List: SO, Score, Status |
| 7 | Milestones | Achievement badges based on thresholds | Conditional evaluation of 5 milestone criteria | OMR | Up to 3 milestone objects |
| 8 | 30-Day Trend | Daily OMR counts + trend direction | Daily SQL aggregation + half-period comparison | OMR | Sparkline data + direction |
| 9 | Top Changed Items | Most revised items across all OMRs | `COUNT(changed rows) GROUP BY item_code ORDER BY count DESC LIMIT 10` | Sales Order Item For OMR + Item | List: Item, Count, % |
| 10 | Revision Velocity | Activity rate, peak day/hour | `COUNT ÷ 30`; `GROUP BY DAYNAME`; `GROUP BY HOUR` | OMR | Velocity metrics object |

---

## 11. Business Rules

The following business rules are implemented in the backend code:

| # | Rule | Where Applied |
|---|------|--------------|
| BR-01 | Only submitted (`docstatus = 1`) OMRs are counted in every KPI | All functions |
| BR-02 | A child row is "changed" only if at least one `rev_*` field has a non-null, non-empty, non-zero value | `_row_is_changed()` |
| BR-03 | Batch traceability uniqueness is at the `(OMR, item, batch)` level — the same item+batch counted once per OMR | `get_batch_change_count()` |
| BR-04 | Null or empty `branch` values are displayed as "Not Set" | `get_branch_wise_changes()` |
| BR-05 | Health score is capped at a minimum of 0 and a maximum of 100 | `get_order_health_scores()` |
| BR-06 | Revision penalty is capped at 50 points (max 3–4 OMRs fully saturates this) | `get_order_health_scores()` |
| BR-07 | Items changed penalty is capped at 30 points | `get_order_health_scores()` |
| BR-08 | Age bonus is capped at 20 points (~4 months to reach maximum) | `get_order_health_scores()` |
| BR-09 | Health scores are returned sorted ascending (worst first) | `get_order_health_scores()` |
| BR-10 | Only the first 3 earned milestones are returned | `get_milestone_achievements()` |
| BR-11 | Milestones evaluate in a fixed priority order | `get_milestone_achievements()` |
| BR-12 | Speed milestone is only awarded if `avg_velocity < 48 hours` | `get_milestone_achievements()` |
| BR-13 | 30-day trend fills zero for days without OMRs | `get_30_day_trends()` |
| BR-14 | Trend classification requires ≥ 14 data points | `get_30_day_trends()` |
| BR-15 | Top items fall back to `rev_item` when `item` is null | `get_top_changed_items()` |
| BR-16 | Item master lookup is batched in groups of 100 | `get_top_changed_items()` |
| BR-17 | Velocity "last 30 days" always divides by exactly 30 | `get_revision_velocity()` |
| BR-18 | Leaderboard users fall back to email/username if full_name is missing | `get_top_creators()` |
| BR-19 | All data is real-time — no caching or pre-aggregation | `get_dashboard_data()` |
| BR-20 | Health score calculation analyses top 10 SOs by OMR count | `get_order_health_scores()` |

---

## 12. Calculation Logic Reference

### Health Score Formula

```
revision_penalty = MIN(omr_count × 15,  50)
items_penalty    = MIN(changed_items × 2, 30)
age_bonus        = MIN(floor(age_days ÷ 30) × 5, 20)

health_score = MAX(0, 100 − revision_penalty − items_penalty + age_bonus)
```

**Saturation Points**

| Component | Saturates when... |
|-----------|-------------------|
| Revision Penalty (−50) | OMR count ≥ 4 (4 × 15 = 60 → capped at 50) |
| Items Penalty (−30) | Changed items ≥ 15 (15 × 2 = 30) |
| Age Bonus (+20) | Order age ≥ 120 days (4 months) |

---

### Trend Change Percentage

```
change_pct = ((second_half − first_half) ÷ first_half) × 100

Where:
  first_half  = SUM(daily counts, days 1–15)
  second_half = SUM(daily counts, days 16–31)

If first_half = 0 and second_half = 0 → change_pct = 0
If first_half = 0 and second_half > 0 → change_pct = 100
```

---

### Average Revision Velocity

```
avg_velocity (hours) = SUM( first_OMR_creation − SO_creation ) ÷ COUNT(qualifying SOs)
```

---

### Item Percentage (for bar chart)

```
max_count = MAX(count_per_item)
percentage = ROUND( (item_count ÷ max_count) × 100 )
```

---

### Revision Velocity Average

```
avg_per_day = COUNT(OMRs with creation >= (now − 30 days)) ÷ 30
```

---

## 13. Limitations and Assumptions

### Limitations

| # | Limitation | Impact |
|---|-----------|--------|
| L-01 | Health score analysis is limited to the **top 10 SOs** by OMR count | SOs with fewer revisions but still in poor health are not surfaced |
| L-02 | `get_average_revision_velocity()` is capped at **100 Sales Orders** per query | Average may not reflect the full dataset in large deployments |
| L-03 | The trend split uses a **fixed 15/15 day partition** — not a dynamic midpoint | If data is unevenly distributed (e.g., all in the last 3 days), the comparison may be misleading |
| L-04 | All KPIs are computed **at query time** with no caching | On databases with very large OMR volumes, the API call may be slow |
| L-05 | `velocity.avg_per_day` always divides by **30**, even if the system has been live for fewer than 30 days | Understates the true daily average for early adopters |
| L-06 | Top Changed Items item master lookup is done in **memory batches of 100** | Items not found in the `Item` DocType fall back to the description stored in the OMR |
| L-07 | Milestone speed badge requires completed `SO creation → OMR creation` pairs | New implementations with partial data may not earn this badge |
| L-08 | The dashboard has **no date range filter** — it always reads all-time submitted OMRs plus a 30-day window for trend/velocity | Historical analysis for a specific period requires a code change |

### Assumptions

| # | Assumption |
|---|------------|
| A-01 | An OMR with `docstatus = 1` is a formally approved, valid modification. Cancelled OMRs (`docstatus = 2`) are not revisions. |
| A-02 | The `branch` field on an OMR correctly reflects the originating location. |
| A-03 | The `owner` field on an OMR is the person who **raised** the modification, not necessarily who approved it. |
| A-04 | `rev_*` fields being empty/null/zero is sufficient evidence that no change was made in that field for that row. |
| A-05 | A Sales Order's `creation` date in the OMR table (used for age calculation) refers to the OMR's creation, not the Sales Order's own creation date — health score `age_days` is therefore the OMR's age, not the Sales Order's age. |
| A-06 | The system clock on the Frappe/ERPNext server is correct and synchronised. |
| A-07 | Item codes stored in `Sales Order Item For OMR.item` match primary keys in the `Item` DocType. |
| A-08 | The `batch_no` field in `Sales Order Item For OMR` refers to a valid batch number; no batch master validation is performed by this dashboard. |

---

*End of Functional Design Document*

*Prepared by: AI Technical Documentation Assistant*
*Review Status: Draft — Pending Functional Consultant Review*
*Document Path: `apps/generate_item/docs/pages_and_dashboards/manufacturing_kpi_dashboard_fdd.md`*
