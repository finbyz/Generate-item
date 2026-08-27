"""
Monthly Sales Performance Dashboard email - Multi-Dashboard, Multi-Group Version.

Registered in hooks.py under scheduler_events["monthly"]. Computes a
calendar-month date range, builds a dashboard URL for EACH dashboard in
DASHBOARD_ROUTES, and sends a SEPARATE HTML email (one per dashboard) via
frappe.sendmail() to the members of THAT dashboard's own Email Group
(Setup > Email > Email Group) — each dashboard has its own recipient list.
"""

import frappe
from frappe.utils import (
    add_months,
    get_first_day,
    get_last_day,
    getdate,
    get_url,
    now_datetime,
    today,
)

# ---------------------------------------------------------------------
# Configuration — adjust these to match your setup
# ---------------------------------------------------------------------
# List of dashboards to include — one email will be sent PER entry, to
# the members of that entry's own "recipient_group" Email Group.
DASHBOARD_ROUTES = [
    {
        "route": "sales-performance-da",
        "label": "Sales Performance",
        "description": "Monthly sales metrics and KPIs",
        "recipient_group": "Sales Performance Dashboard Recipients",
    },
    {
        "route": "director-dashboard",
        "label": "Director Dashboard",
        "description": "Executive overview of sales performance, key metrics, trends, and business KPIs",
        "recipient_group": "Director Dashboard Recipients",
    },
    {
        "route": "sales-team-kpi-dashb",
        "label": "Sales Team KPI Dashboard",
        "description": "sales performance, key metrics, trends, and business KPIs",
        "recipient_group": "Sales Team KPI Dashboard Recipients",
    },

    # Add more dashboards as needed — each needs its own "recipient_group"
]

# 0  -> report covers the month the scheduler runs in (only correct if
#       the cron fires ON/AFTER that month's last day)
# -1 -> report covers the month BEFORE the run date (recommended — lets
#       you trigger on the 1st of the month with a guaranteed-complete
#       previous month's data)
MONTH_OFFSET = 0


BRANCH_FILTER = None  # e.g., "Main Branch" or None
# ---------------------------------------------------------------------


def get_month_date_range(reference_date=None, month_offset=MONTH_OFFSET):
    """Return (from_date, to_date) for a calendar month, relative to reference_date.

    get_last_day resolves month length via Python's calendar module, so
    28/29-day February and 30- vs 31-day months need no special case.

    Examples with month_offset=-1 ("previous complete month"):
        ref=2026-09-01 -> (2026-08-01, 2026-08-31)
        ref=2026-02-01 -> (2026-01-01, 2026-01-31)
        ref=2024-03-01 -> (2024-02-01, 2024-02-29)   # leap year
        ref=2027-01-01 -> (2026-12-01, 2026-12-31)   # year rollover

    Examples with month_offset=0 ("month containing reference_date"):
        ref=2026-08-05 -> (2026-08-01, 2026-08-31)
        ref=2026-09-20 -> (2026-09-01, 2026-09-30)
    """
    ref = getdate(reference_date or today())
    anchor = add_months(ref, month_offset) if month_offset else ref
    return get_first_day(anchor), get_last_day(anchor)


def build_dashboard_url(from_date, to_date, dashboard_route, branch=None):
    """Dashboard link with date filters as query params. Uses /desk/ —
    confirmed as the correct v16 Desk route prefix."""
    url = f"{get_url()}/desk/{dashboard_route}?from_date={from_date}&to_date={to_date}"
    if branch:
        url += f"&branch={frappe.utils.quote(branch)}"
    return url


def get_recipients(email_group):
    """Fetch recipient emails from the given Email Group (Setup > Email
    > Email Group), instead of a hardcoded list.

    Only active (non-unsubscribed) members are returned. If the Email Group
    itself doesn't exist yet, this returns an empty list (and the caller
    logs + skips that dashboard's send) rather than raising, so a
    missing/renamed group fails soft instead of breaking the scheduler.
    """
    if not email_group:
        frappe.logger("monthly_dashboard_email").warning(
            "No recipient_group configured for a dashboard entry; skipping."
        )
        return []

    if not frappe.db.exists("Email Group", email_group):
        frappe.logger("monthly_dashboard_email").warning(
            f"Email Group '{email_group}' does not exist. "
            f"Create it under Setup > Email > Email Group and add members."
        )
        return []

    return frappe.get_all(
        "Email Group Member",
        filters={"email_group": email_group, "unsubscribed": 0},
        pluck="email",
    )


def get_email_html_template():
    """Return the HTML email template as a string.

    Built around a SINGLE dashboard per email (one card, one button).
    """
    return """
<!DOCTYPE html>
<html>
<head>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            background: #1a5276;
            color: white;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 20px;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 24px;
        }
        .header h2 {
            margin: 5px 0 0 0;
            font-weight: normal;
            font-size: 18px;
            opacity: 0.9;
        }
        .dashboard-card {
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 5px;
            padding: 25px;
            text-align: center;
            margin: 20px 0;
        }
        .dashboard-card h3 {
            margin: 0 0 5px 0;
            color: #1a5276;
            font-size: 20px;
        }
        .dashboard-card p {
            color: #6c757d;
            font-size: 14px;
            margin: 5px 0 15px 0;
        }
        .btn {
            display: inline-block;
            padding: 10px 25px;
            background: #1a5276;
            color: white !important;
            text-decoration: none;
            border-radius: 3px;
            font-weight: bold;
            transition: background 0.2s;
        }
        .btn:hover {
            background: #154360;
        }
        .footer {
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #dee2e6;
            font-size: 12px;
            color: #6c757d;
            text-align: center;
        }
        .period-info {
            background: #eaf2f8;
            padding: 10px;
            border-radius: 3px;
            margin: 15px 0;
            text-align: center;
        }
        .period-info strong {
            color: #1a5276;
        }
        .generated-on {
            font-size: 12px;
            color: #6c757d;
            margin-top: 10px;
        }
        .greeting {
            margin: 20px 0 10px 0;
            font-size: 16px;
        }
        .dashboard-icon {
            font-size: 36px;
            margin-bottom: 10px;
        }
        @media (max-width: 600px) {
            .header h1 {
                font-size: 20px;
            }
            .header h2 {
                font-size: 16px;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ company_name }}</h1>
        <h2>{{ dashboard.label }}</h2>
        <h2 style="font-size: 16px; margin-top: 5px;">{{ month_label }}</h2>
    </div>

    <div class="period-info">
        <strong>Reporting Period:</strong> {{ from_date }} to {{ to_date }}
    </div>

    <p class="greeting">Dear Team,</p>
    <p>Your {{ dashboard.label }} report is ready. Click the button below to view it:</p>

    <div class="dashboard-card">
        <div class="dashboard-icon">📊</div>
        <h3>{{ dashboard.label }}</h3>
        {% if dashboard.description %}
        <p>{{ dashboard.description }}</p>
        {% endif %}
        <a href="{{ dashboard.url }}" class="btn" target="_blank">View Dashboard</a>
    </div>

    <p style="margin-top: 20px; font-size: 14px; color: #555;">
        If you have any questions about this report, please contact your manager
    </p>

    <div class="footer">
        <p>This is an automated email generated on {{ generated_on }}.</p>
        <p>Please do not reply to this email.</p>
        <p style="margin-top: 5px; font-size: 11px; color: #999;">
            &copy; {{ now_datetime().year }} {{ company_name }}. All rights reserved.
        </p>
    </div>
</body>
</html>
    """


def _send_single_dashboard_email(dashboard, from_date, to_date, recipients, company_name, jinja_env, html_template):
    """Build and queue one email for a single dashboard entry, to that
    dashboard's own recipient group."""
    dashboard_url = build_dashboard_url(
        from_date,
        to_date,
        dashboard["route"],
        BRANCH_FILTER
    )

    dashboard_ctx = {
        "label": dashboard["label"],
        "description": dashboard.get("description", ""),
        "url": dashboard_url,
        "route": dashboard["route"],
    }

    template = jinja_env.from_string(html_template)
    message = template.render({
        "month_label": from_date.strftime("%B %Y"),
        "from_date": frappe.utils.formatdate(from_date),
        "to_date": frappe.utils.formatdate(to_date),
        "dashboard": dashboard_ctx,
        "generated_on": frappe.utils.format_datetime(now_datetime(), "dd-MM-yyyy HH:mm"),
        "company_name": company_name,
        "now_datetime": now_datetime,
    })

    frappe.sendmail(
        recipients=recipients,
        subject=f"{dashboard['label']} – {from_date.strftime('%B %Y')}",
        message=message,
        delayed=True,  # goes through the Email Queue, retried on transient SMTP errors
    )


def send_monthly_dashboard_email():
    """Scheduler entry point for monthly task. Sends ONE separate email PER
    dashboard in DASHBOARD_ROUTES, each to its OWN Email Group's members
    (via dashboard['recipient_group']). Wrapped end-to-end in try/except so
    a failure is logged to Error Log instead of silently killing the
    scheduler tick."""
    try:
        from_date, to_date = get_month_date_range()

        if not DASHBOARD_ROUTES:
            frappe.logger("monthly_dashboard_email").warning(
                "No dashboards configured in DASHBOARD_ROUTES; skipping send."
            )
            return

        company_name = frappe.defaults.get_global_default("company")

        from jinja2 import Environment, BaseLoader
        jinja_env = Environment(loader=BaseLoader())
        html_template = get_email_html_template()

        sent_labels = []
        skipped_labels = []
        failed_labels = []

        for dashboard in DASHBOARD_ROUTES:
            label = dashboard.get("label", dashboard.get("route"))
            group = dashboard.get("recipient_group")

            recipients = get_recipients(group)
            if not recipients:
                frappe.logger("monthly_dashboard_email").warning(
                    f"No recipients found for dashboard '{label}' "
                    f"(group '{group}'); skipping this dashboard's email."
                )
                skipped_labels.append(label)
                continue

            try:
                _send_single_dashboard_email(
                    dashboard, from_date, to_date, recipients,
                    company_name, jinja_env, html_template
                )
                sent_labels.append(f"{label} ({len(recipients)} recipients)")
            except Exception as inner_e:
                # One dashboard failing shouldn't stop the rest from sending
                failed_labels.append(label)
                frappe.log_error(
                    frappe.get_traceback(),
                    f"Monthly Dashboard Email Failed ({label})"
                )
                frappe.logger("monthly_dashboard_email").error(
                    f"Failed to send email for dashboard '{label}': {str(inner_e)}"
                )

        frappe.logger("monthly_dashboard_email").info(
            f"Monthly dashboard emails processed for period {from_date} to {to_date}. "
            f"Sent: {', '.join(sent_labels) if sent_labels else 'none'}. "
            f"Skipped (no recipients): {', '.join(skipped_labels) if skipped_labels else 'none'}. "
            f"Failed: {', '.join(failed_labels) if failed_labels else 'none'}."
        )

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Monthly Dashboard Email Failed")
        frappe.logger("monthly_dashboard_email").error(
            f"Failed to send monthly dashboard email: {str(e)}"
        )