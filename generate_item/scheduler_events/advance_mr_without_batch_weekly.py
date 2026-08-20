# Weekly Scheduled Script for Advance MR without Batch Report

import frappe


# ------------------------------------------------------------------
# Name of the Email Group (Setup > Email > Email Group) that holds the
# recipient list for this report. Manage members from the UI — no code
# change or deploy needed when recipients change.
# ------------------------------------------------------------------
RECIPIENT_EMAIL_GROUP = "Advance MR Without Batch Alert"


def get_recipients():
    """Fetch recipient emails from the configured Email Group (Setup > Email
    > Email Group), instead of a hardcoded address.

    Only active (non-unsubscribed) members are returned. If the Email Group
    itself doesn't exist yet, this returns an empty list (and the caller
    logs + skips the send) rather than raising, so a missing/renamed group
    fails soft instead of breaking the scheduler.
    """
    if not frappe.db.exists("Email Group", RECIPIENT_EMAIL_GROUP):
        frappe.logger().warning(
            f"Email Group '{RECIPIENT_EMAIL_GROUP}' does not exist. "
            f"Create it under Setup > Email > Email Group and add members."
        )
        return []

    return frappe.get_all(
        "Email Group Member",
        filters={"email_group": RECIPIENT_EMAIL_GROUP, "unsubscribed": 0},
        pluck="email",
    )


def process_advance_mr_without_batch():
    """
    Weekly scheduled job to find Advance MRs with items missing batch numbers
    and send ONE consolidated email to the members of RECIPIENT_EMAIL_GROUP.
    """

    # Get all Advance MRs that are not cancelled
    advance_mrs = frappe.get_all(
        "Material Request",
        filters={
            "advance_mr": 1,
            "docstatus": ["!=", 2],  # Not cancelled
            "status": ["!=", "Stopped"]
        },
        fields=["name", "owner", "creation", "transaction_date"]
    )

    all_items_without_batch = []
    total_mrs_processed = 0

    # Process each MR
    for mr in advance_mrs:
        items_without_batch = frappe.get_all(
            "Material Request Item",
            filters={
                "parent": mr.name,
                "custom_batch_no": ["in", ["", None]]
            },
            fields=["item_code", "item_name", "parent", "qty"]
        )

        if not items_without_batch:
            continue

        for item in items_without_batch:
            all_items_without_batch.append({
                "mr_name": mr.name,
                "transaction_date": mr.transaction_date,
                "item_code": item.item_code,
                "item_name": item.item_name,
                "qty": item.qty,
            })

        total_mrs_processed += 1

    if not all_items_without_batch:
        frappe.logger().info(
            "No Advance MR items without batch numbers found. No email sent."
        )
        return

    recipients = get_recipients()

    if not recipients:
        frappe.logger().warning(
            f"No recipients found in Email Group '{RECIPIENT_EMAIL_GROUP}'; "
            f"skipping send even though {len(all_items_without_batch)} items "
            f"without batch were found."
        )
        return

    try:
        send_notification_email(
            recipients=recipients,
            items_data=all_items_without_batch
        )

        frappe.logger().info(
            f"Consolidated email sent to {', '.join(recipients)} "
            f"({len(all_items_without_batch)} items from {total_mrs_processed} MRs)"
        )
    except Exception as e:

        frappe.log_error(
            message=f"Failed to send email to {', '.join(recipients)}: {str(e)}",
            title="Advance MR Weekly Report Error"
        )


def send_notification_email(recipients, items_data):
    """
    Send ONE formatted consolidated email with a table of items missing batch numbers.
    Columns: Sr No, Material Request Name, Transaction Date, Item Code, Qty

    recipients: list of email addresses (from the Email Group).
    """

    # Build table rows
    table_rows = ""
    for idx, item in enumerate(items_data, start=1):
        row_style = (
            'style="background-color: #ffffff;"'
            if idx % 2 == 0
            else 'style="background-color: #f9f9f9;"'
        )
        table_rows += f"""
        <tr {row_style}>
            <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{idx}</td>
            <td style="padding: 8px; border: 1px solid #ddd;">{item['mr_name']}</td>
            <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{item['transaction_date']}</td>
            <td style="padding: 8px; border: 1px solid #ddd; font-family: monospace;">{item['item_code']}</td>
            <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{item['qty']}</td>
        </tr>"""

    total_items = len(items_data)
    unique_mrs = len(set(item['mr_name'] for item in items_data))

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; }}
            .container {{ max-width: 900px; margin: 0 auto; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white; padding: 20px; border-radius: 10px 10px 0 0;">
                <h2 style="margin: 0;color: #000000">🔔 Weekly Report: Advance Material Request Items Without Batch Numbers</h2>
                <p style="color: #000000;margin: 5px 0 0 0; opacity: 0.9;">
                    Generated: {frappe.utils.now_datetime().strftime('%B %d, %Y at %I:%M %p')}
                </p>
            </div>

            <div style="padding: 20px; background-color: #ffffff;
                        border: 1px solid #dee2e6; border-top: none;">
                <p>This is the weekly consolidated report of Advance Material Request items
                that are <strong style="color: #dc3545;">missing batch numbers</strong>.</p>

                <div style="background-color: #fff3cd; border: 1px solid #ffc107;
                            padding: 12px; border-radius: 5px; margin: 15px 0;">
                    <strong>📊 Summary:</strong><br>
                    • Total Material Request requiring attention: <strong>{unique_mrs}</strong><br>
                    • Total items without batch: <strong>{total_items}</strong>
                </div>

                <table style="width: 100%; border-collapse: collapse; margin-top: 20px;
                              box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <thead>
                        <tr style="background-color: #007bff; color: white;">
                            <th style="padding: 12px; border: 1px solid #0056b3;
                                       text-align: center; width: 8%;">Sr No</th>
                            <th style="padding: 12px; border: 1px solid #0056b3;
                                       text-align: left; width: 27%;">Material Request Name</th>
                            <th style="padding: 12px; border: 1px solid #0056b3;
                                       text-align: center; width: 20%;">Transaction Date</th>
                            <th style="padding: 12px; border: 1px solid #0056b3;
                                       text-align: left; width: 27%;">Item Code</th>
                            <th style="padding: 12px; border: 1px solid #0056b3;
                                       text-align: center; width: 18%;">Qty</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows}
                    </tbody>
                </table>
            </div>

            <div style="padding: 15px; background-color: #f8f9fa;
                        border-radius: 0 0 10px 10px; text-align: center;
                        border: 1px solid #dee2e6; border-top: none;">
                <p style="margin: 0; color: #6c757d; font-size: 12px;">
                    This is an automated consolidated weekly report.<br>
                    For any queries, please contact the system administrator.
                </p>
            </div>
        </div>
    </body>
    </html>
    """

    frappe.sendmail(
        recipients=recipients,
        subject=(
            f"Weekly Report: Advance Material Request Items Without Batch - "
            f"{frappe.utils.now_datetime().strftime('%Y-%m-%d')}"
        ),
        message=html_content,
        delayed=False,
        reference_doctype="Material Request",
        reference_name=None
    )