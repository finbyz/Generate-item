# Notifications and Workflow Email

## Notification mechanisms

Generate Item uses two separate mechanisms:

1. local Frappe bell notifications for Modification Tasks;
2. workflow email delivery owned by the external `workflow_transitions` app.

## Modification Task notifications

Primary implementation:

- `generate_item/generate_item/modification_task_utils/modification_task_notification.py`
- `generate_item/generate_item/doctype/modification_task/modification_task.py`

`ModificationTask.on_submit()` creates a `Notification Log` for eligible users.

Eligibility requires:

- an enabled System User;
- a role mapped to the task category;
- matching Branch User Permission when branch restrictions exist;
- a user different from the task owner.

Notifications include links to the Modification Task and referenced business document.

## Workflow Email ownership

`Workflow Email` is not a Generate Item DocType. Its implementation is located in:

```text
apps/workflow_transitions/workflow_transitions/workflow_transitions/doctype/workflow_email/
```

Generate Item integrates through:

```text
generate_item/generate_item/doctype/order_modification_request/order_modification_request_list.js
```

## OMR pending notification action

The OMR list action **Send Pending Notification** calls:

```text
workflow_transitions.workflow_transitions.doctype.workflow_email.workflow_email.send_pending_notification
```

For selected OMRs the external service:

1. reads distinct non-Draft workflow states from state history;
2. checks Email Queue records for each state;
3. classifies notifications as sent, in progress, failed, or pending;
4. avoids resending successful states;
5. finds active Workflow Email rules for the OMR and state;
6. evaluates optional document conditions;
7. resolves role, user/email, child-row, and approved-document-owner recipients;
8. enqueues the email.

The list view displays sent, already-sent, queued, and failed results.

## Runtime dependency

Generate Item does not list `workflow_transitions` in `required_apps`. The list action therefore assumes the other app is installed. Without it, the RPC fails.

Recommended maintenance options:

- declare the external app as required;
- hide the action when the method is unavailable;
- or provide a guarded local fallback.

