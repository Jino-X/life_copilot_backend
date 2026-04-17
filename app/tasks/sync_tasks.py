"""Sync-related Celery tasks."""
import asyncio

from app.tasks.celery_app import celery_app
from app.core.database import get_db_context
from app.core.logging import get_logger
from app.services.calendar_service import CalendarService
from app.services.user_service import UserService

logger = get_logger(__name__)


def run_async(coro):
    """Run async function in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=3)
def sync_user_calendar(self, user_id: int):
    """Sync calendar for a specific user."""
    async def _sync():
        async with get_db_context() as db:
            user_service = UserService(db)
            user = await user_service.get_by_id(user_id)
            
            if not user or not user.google_access_token:
                logger.info(f"User {user_id} has no Google credentials, skipping calendar sync")
                return {"status": "skipped", "reason": "no_credentials"}
            
            calendar_service = CalendarService(db)
            
            try:
                synced_events = await calendar_service.sync_from_google(user, days_ahead=30)
                logger.info(f"Synced {len(synced_events)} calendar events for user {user_id}")
                
                return {
                    "status": "success",
                    "events_synced": len(synced_events),
                }
            except Exception as e:
                logger.error(f"Failed to sync calendar for user {user_id}: {e}")
                raise self.retry(exc=e, countdown=60)
    
    return run_async(_sync())


@celery_app.task
def sync_all_calendars():
    """Sync calendars for all users with Google credentials."""
    async def _sync_all():
        from sqlalchemy import select
        from app.models.user import User
        
        async with get_db_context() as db:
            result = await db.execute(
                select(User.id).where(User.google_access_token.isnot(None))
            )
            user_ids = [row[0] for row in result.all()]
        
        for user_id in user_ids:
            sync_user_calendar.delay(user_id)
        
        return {"users_queued": len(user_ids)}
    
    return run_async(_sync_all())


@celery_app.task(bind=True, max_retries=3)
def full_user_sync(self, user_id: int):
    """Perform full sync for a user (calendar + emails)."""
    from app.tasks.email_tasks import sync_user_emails
    
    sync_user_calendar.delay(user_id)
    sync_user_emails.delay(user_id)
    
    return {
        "status": "queued",
        "user_id": user_id,
        "tasks": ["calendar_sync", "email_sync"],
    }


@celery_app.task
def cleanup_old_data():
    """Clean up old synced data."""
    async def _cleanup():
        from datetime import datetime, timedelta, timezone
        from sqlalchemy import delete
        from app.models.calendar_event import CalendarEvent
        from app.models.email import Email
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=90)
        
        async with get_db_context() as db:
            events_deleted = await db.execute(
                delete(CalendarEvent).where(CalendarEvent.end_time < cutoff_date)
            )
            
            emails_deleted = await db.execute(
                delete(Email).where(Email.received_at < cutoff_date)
            )
            
            return {
                "events_deleted": events_deleted.rowcount,
                "emails_deleted": emails_deleted.rowcount,
            }
    
    return run_async(_cleanup())
