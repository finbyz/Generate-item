# Modification Task Module

## Purpose

Modification Task provides traceable, role-specific action records for manufacturing and purchasing changes.

Primary implementation:

- `generate_item/generate_item/doctype/modification_task/`
- `generate_item/generate_item/modification_task_utils/modification_task.py`
- `generate_item/generate_item/modification_task_utils/modification_task_permission.py`
- `generate_item/generate_item/modification_task_utils/modification_task_notification.py`

## Data model

`Modification Task` is submittable and contains:

- category;
- subject and generated instructions;
- reference DocType and Dynamic Link document;
- reason/remarks;
- branch;
- task status;
- assignee;
- task remarks.

## Automatic task creation

| Trigger | Category | Reference |
| --- | --- | --- |
| Item-changing OMR submitted | BOM Modification | Sales Order |
| Linked BMR submitted | Production Plan Update | Production Plan |
| Production Plan Get Update | Work Order Update | Work Order |
| Production Plan Get Update | Purchase Order Modification | Purchase Order |

Tasks are inserted and submitted with pending status. Their descriptions include affected Items, old/revised quantities or codes, source documents, and completion instructions.

## Role/category control

| Roles | Categories |
| --- | --- |
| Design User, Design Manager | BOM Modification |
| Planning User, Planning Manager | Production Plan Update, Work Order Update |
| Purchase User, Purchase Manager, Purchase Master Manager | Purchase Order Modification |
| Sales User, Sales Manager, Sales Master Manager | Sales Order Modification |

Users without a mapped role are denied. Administrator bypasses category and branch filtering.

## Branch permissions

If a user has Branch User Permission records, task list and document access are limited to matching task branches. A user without Branch User Permissions is not restricted by branch.

## Notifications

Submitting a Modification Task creates a `Notification Log` alert for enabled System Users who:

- hold a role mapped to the task category;
- pass the branch check;
- are not the task owner.

Notification content links to both the task and referenced document.

## Assignment behavior

The `assign_to` field is editable after submission, but current task-creation methods do not automatically populate it. The module provides automatic routing, visibility, and notification rather than automatic user assignment.

## Maintenance considerations

- Stage-specific creation functions do not visibly deduplicate repeated tasks.
- Branch is stamped during creation and must remain available on source documents.
- Permission and notification category maps should be updated together when adding a category.

