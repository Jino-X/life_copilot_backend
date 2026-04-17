"""Celery tasks module."""
from app.tasks.celery_app import celery_app
from app.tasks.email_tasks import sync_user_emails, analyze_user_emails, sync_all_emails
from app.tasks.reminder_tasks import (
    check_task_reminders,
    send_task_reminder,
    send_daily_summaries,
    generate_daily_summary,
)
from app.tasks.sync_tasks import sync_user_calendar, sync_all_calendars, full_user_sync

__all__ = [
    "celery_app",
    "sync_user_emails",
    "analyze_user_emails",
    "sync_all_emails",
    "check_task_reminders",
    "send_task_reminder",
    "send_daily_summaries",
    "generate_daily_summary",
    "sync_user_calendar",
    "sync_all_calendars",
    "full_user_sync",
]
