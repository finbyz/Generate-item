# Customer Complaint Management Implementation Guide

## 1. Overview
The **Customer Complaint Management** feature provides a production-ready system for logging, tracking, analyzing, and resolving customer complaints on industrial valves. It utilizes ERPNext's standard `Issue` DocType as the core entity, extending it with custom fields and an append-only `Issue Progress Update` child table, along with an interactive Script Report titled **Customer Complaint Register** with in-line editing and "New Complaint" quick actions.

---

## 2. Architecture & Modules
- **Application**: `generate_item`
- **Module**: `Generate Item`
- **Reference DocType**: `Issue` (standard ERPNext core DocType)
- **Child DocType**: `Issue Progress Update`
- **Script Report**: `Customer Complaint Register`

---

## 3. Files Created and Modified

### Created Files:
1. `apps/generate_item/generate_item/generate_item/doctype/issue_progress_update/__init__.py`: Package marker.
2. `apps/generate_item/generate_item/generate_item/doctype/issue_progress_update/issue_progress_update.py`: Document controller for progress history.
3. `apps/generate_item/generate_item/generate_item/doctype/issue_progress_update/issue_progress_update.json`: Child table schema definition.
4. `apps/generate_item/generate_item/customer_complaint/__init__.py`: Module package marker.
5. `apps/generate_item/generate_item/customer_complaint/setup.py`: Idempotent custom field installer (`create_custom_fields`).
6. `apps/generate_item/generate_item/customer_complaint/issue.py`: Issue lifecycle hooks for validation, append-only security, and auto-syncing progress history.
7. `apps/generate_item/generate_item/public/js/issue.js`: Form script for Issue with quick buttons and defaults.
8. `apps/generate_item/generate_item/generate_item/report/customer_complaint_register/customer_complaint_register.json`: Script Report metadata.
9. `apps/generate_item/generate_item/generate_item/report/customer_complaint_register/customer_complaint_register.py`: Parameterized SQL query and whitelisted batch save API.
10. `apps/generate_item/generate_item/generate_item/report/customer_complaint_register/customer_complaint_register.js`: Interactive report script with editable cells, yellow diff highlights, and New Complaint button.
11. `apps/generate_item/generate_item/tests/test_customer_complaint_register.py`: 13 integration tests covering permissions, filtering, validation, and history integrity.

### Modified Files:
1. `apps/generate_item/generate_item/hooks.py`:
   - Added `generate_item.customer_complaint.setup.setup_customer_complaint` to `after_migrate`.
   - Added `Issue` validation and before_save hooks under `doc_events`.
   - Added `Issue` client script under `doctype_js`.
2. `apps/generate_item/generate_item/fixtures/custom_field.json`: Exported custom fields for version control.

---

## 4. Field Mapping Reference (Workbook to DocType & Report)

| Workbook Column Header | Issue Fieldname | Field Type | Report Column | Target / Role |
| :--- | :--- | :--- | :--- | :--- |
| **Sl. No. / CCR-XX** | `custom_complaint_ref_no` | Data | CCR / Ref No | Complaint identifier |
| **Status** | `custom_complaint_status` | Select (`Open`, `Action in Progress`, `Close`) | Complaint Status | Current lifecycle state |
| **Standard Status** | `status` | Select (Standard) | Issue Status | Standard ERPNext status |
| **Priority** | `priority` | Link (`Priority`) | Priority | Severity |
| **Reg. Dt** | `custom_complaint_reg_date` | Date | Reg. Dt | Complaint registration date |
| **Customer Name** | `customer` | Link (`Customer`) | Customer | Customer entity |
| **Subject** | `subject` | Data | Subject | Complaint title/summary |
| **SO/Number** | `custom_sales_order` / `custom_so_number` | Link (`Sales Order`) / Data | Sales Order / SO Number | Linked order and free text |
| **FS/Number** | `custom_fs_number` | Data | FS / Number | Field service / FS number |
| **Project** | `custom_project_name` / `project` | Data / Link (`Project`) | Project | Project identifier |
| **Site** | `custom_site` | Data | Site | Installation/Refinery site |
| **Valve** | `custom_valve` | Data | Valve | Valve description |
| **Type** | `custom_valve_type` | Data | Type | Valve type (e.g. LCV, GTV, etc.) |
| **Size** | `custom_valve_size` | Data | Size | Valve size (e.g. 2", 48, etc.) |
| **Class** | `custom_valve_class` | Data | Class | Rating (e.g. 150#, 300, etc.) |
| **MOC** | `custom_moc` | Data | MOC | Material of Construction |
| **Valve Serial Nos.** | `custom_valve_serial_no` | Small Text | Valve Serial Nos. | Single or multiple serial numbers |
| **Qty** | `custom_qty` | Data | Qty | Quantity (numeric or text) |
| **Actuator Make** | `custom_actuator_make` | Data | Actuator Make | e.g. Rotork, Valmet, Auma |
| **Resp. Dept** | `custom_responsible_department` | Data | Resp. Dept | Responsible department |
| **Nature of complaint** | `custom_nature_of_complaint` | Small Text | Nature of Complaint | Defect description |
| **Action Date** | `custom_action_date` | Date | Action Date | Target/completion date |
| **Action decided / Remark**| `custom_action_remarks` | Small Text | Action / Remark | Immediate action |
| **Final Status / Closure** | `custom_final_action_remarks` | Small Text | Final Status / Remark | Resolution / outcome |
| **Progress Updated By** | `custom_progress_updated_by` | Data | Progress Updated By | Reviewer initials |
| **Action By** | `custom_action_taken_by` | Data | Action By | Action taker |
| **SSV Visiting Engineer**| `custom_ssv_visiting_engineer` | Data | SSV Visiting Engineer | Field engineer |
| **SSV Visiting Schedule**| `custom_visit_schedule_date` | Date | Visit Schedule Date | Visit date |
| **Visit Notes** | `custom_visit_schedule_notes` | Small Text | Visit Schedule / Notes | Field notes |
| **Photo evidence** | `custom_photo_evidence` | Attach Image | Evidence Image | Attached photo |
| **MOM** | `custom_mom_attachment` | Attach | MOM File | Minutes of meeting PDF |
| **History Log** | `custom_progress_history` | Table (`Issue Progress Update`)| Details in DocType | Append-only history trail |

---

## 5. Child Table: Issue Progress Update
Each progress entry captures:
- `posting_datetime`: Timestamp of the update (read-only/auto-populated)
- `complaint_status`: Status at time of update (`Open`, `Action in Progress`, `Close`)
- `action_by`: Individual who took or planned the action
- `responsible_department`: Department taking responsibility
- `action_remarks`: Remarks on the action taken
- `progress_update`: Full update narrative
- `ssv_visiting_engineer`: Visiting engineer
- `visit_schedule_date`: Target visit date
- `visit_schedule_notes`: Visit coordination notes
- `attachment`: Photo or document evidence
- `mom_attachment`: Minutes of meeting attachment
- `updated_by`: User session that committed the change

### Append-Only & Synchronization Rules:
1. Historical rows cannot be deleted or have their timestamps altered.
2. When progress-related fields on `Issue` change (e.g. status, remarks, schedule), the controller automatically appends a new progress history record if a new one was not already manually added.
3. Editing non-progress fields (like Subject or Customer) does not create extraneous history rows.

---

## 6. Editable Cells & Save Changes Allowlist
In the Script Report, users can click to edit the following approved fields:
- `custom_complaint_status` (Dropdown: `Open`, `Action in Progress`, `Close`)
- `custom_responsible_department`
- `custom_site`
- `custom_action_date` (Date picker)
- `custom_action_remarks`
- `custom_visit_schedule_date` (Date picker)
- `custom_final_action_remarks`
- `custom_ssv_visiting_engineer`

Unsaved changes are highlighted with a distinct yellow background (`#fff3a3`). Clicking **Save Changes** calls the server-side whitelisted API `save_complaint_register_changes`, which:
- Checks document existence and verifies user write permissions.
- Strictly allows only whitelisted fields.
- Validates field types and allowed select options.
- Executes `doc.save()` ensuring lifecycle events and audit trail are preserved.
- Returns row-level status and refreshes the report table.

---

## 7. How to Use

### Creating a Complaint:
1. Open the Desk, navigate to **Support > Issue** or click **New Complaint** from the **Customer Complaint Register** report.
2. Select the **Customer**, **Sales Order**, and fill in the Valve details (Size, Class, Type, Serial Nos.).
3. Set the **Complaint Status** (default is `Open`).
4. Enter the **Nature of Complaint** and initial action.
5. Save the Issue. The initial progress history row is created automatically.

### Adding Progress Updates:
- From the Issue form: Click the **Add Progress Update** button in the header, fill in the dialog fields, and submit.
- Or edit allowed fields directly within the **Customer Complaint Register** grid and click **Save Changes**.

### Viewing the Register:
- Search for **Customer Complaint Register** in the search bar or go to `/app/query-report/Customer Complaint Register`.
- Use filters for Date Range, Customer, Complaint Status, Standard Issue Status, Valve Size/Class, Site, or Responsible Department.
