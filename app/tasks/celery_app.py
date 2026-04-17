"""Celery application configuration."""
from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "life_copilot",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.email_tasks",
        "app.tasks.reminder_tasks",
        "app.tasks.sync_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
    task_soft_time_limit=240,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)

celery_app.conf.beat_schedule = {
    "sync-emails-every-15-minutes": {
        "task": "app.tasks.email_tasks.sync_all_emails",
        "schedule": 900.0,
    },
    "sync-calendars-every-30-minutes": {
        "task": "app.tasks.sync_tasks.sync_all_calendars",
        "schedule": 1800.0,
    },
    "send-daily-summaries": {
        "task": "app.tasks.reminder_tasks.send_daily_summaries",
        "schedule": {
            "hour": 7,
            "minute": 0,
        },
    },
    "check-reminders-every-5-minutes": {
        "task": "app.tasks.reminder_tasks.check_task_reminders",
        "schedule": 300.0,
    },
}
