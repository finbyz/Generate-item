import frappe
from frappe.utils import now_datetime


def log(message, title="Report Email Scheduler"):
    frappe.log_error(
        message=message,
        title=title
    )


def process_scheduled_reports():

    now = now_datetime()

    # log(
    #     f"Scheduler started\n"
    #     f"Current Time: {now}"
    # )

    schedules = frappe.get_all(
        "Report Email Scheduled",
        filters={
            "enable": 1,
            "next_execution": ["<=", now],
        },
        fields=[
            "name",
            "report",
            "frequency",
            "next_execution",
        ],
    )

    # log(
    #     f"Due schedules found: {len(schedules)}"
    # )

    for schedule in schedules:

        # log(
        #     f"Queueing schedule\n"
        #     f"Name: {schedule.name}\n"
        #     f"Report: {schedule.report}\n"
        #     f"Frequency: {schedule.frequency}\n"
        #     f"Next Execution: {schedule.next_execution}"
        # )

        try:

            frappe.enqueue(
                "ibtevolve.doc_events.repot_email_schedule.execute_scheduled_report",
                queue="long",
                schedule_name=schedule.name,
            )

            # log(
            #     f"Successfully queued:\n"
            #     f"{schedule.name}"
            # )

        except Exception:

            frappe.log_error(
                message=frappe.get_traceback(),
                title=f"Failed to Queue: {schedule.name}"
            )


def execute_scheduled_report(schedule_name):

    # log(
    #     f"Execution started\n"
    #     f"Schedule: {schedule_name}"
    # )

    try:

        doc = frappe.get_doc(
            "Report Email Scheduled",
            schedule_name
        )

        # log(
        #     f"Schedule loaded\n"
        #     f"Name: {doc.name}\n"
        #     f"Report: {doc.report}\n"
        #     f"enable: {doc.enable}\n"
        #     f"Next Execution: {doc.next_execution}"
        # )

        if not doc.enable:

            # log(
            #     f"Schedule is disabled\n"
            #     f"Schedule: {schedule_name}"
            # )

            return

        # log(
        #     f"Calling send_scheduled_report()\n"
        #     f"Schedule: {schedule_name}"
        # )

        doc.send_scheduled_report()

        # log(
        #     f"Execution completed successfully\n"
        #     f"Schedule: {schedule_name}"
        # )

    except Exception:

        frappe.log_error(
            message=frappe.get_traceback(),
            title=f"Scheduled Report Failed: {schedule_name}"
        )

        raise