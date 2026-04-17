"""Email-related Celery tasks."""
import asyncio
from typing import Optional

from app.tasks.celery_app import celery_app
from app.core.database import get_db_context
from app.core.logging import get_logger
from app.services.email_service import EmailService
from app.services.user_service import UserService
from app.agents.email_agent import EmailAgent

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
def sync_user_emails(self, user_id: int):
    """Sync emails for a specific user."""
    async def _sync():
        async with get_db_context() as db:
            user_service = UserService(db)
            user = await user_service.get_by_id(user_id)
            
            if not user or not user.google_access_token:
                logger.info(f"User {user_id} has no Google credentials, skipping email sync")
                return {"status": "skipped", "reason": "no_credentials"}
            
            email_service = EmailService(db)
            
            try:
                synced_emails = await email_service.sync_from_gmail(user, max_results=20)
                logger.info(f"Synced {len(synced_emails)} emails for user {user_id}")
                
                return {
                    "status": "success",
                    "emails_synced": len(synced_emails),
                }
            except Exception as e:
                logger.error(f"Failed to sync emails for user {user_id}: {e}")
                raise self.retry(exc=e, countdown=60)
    
    return run_async(_sync())


@celery_app.task(bind=True, max_retries=3)
def analyze_user_emails(self, user_id: int, email_ids: Optional[list[int]] = None):
    """Analyze emails for a user using AI."""
    async def _analyze():
        async with get_db_context() as db:
            user_service = UserService(db)
            user = await user_service.get_by_id(user_id)
            
            if not user or not user.google_access_token:
                return {"status": "skipped", "reason": "no_credentials"}
            
            email_service = EmailService(db)
            email_agent = EmailAgent()
            
            if email_ids:
                emails = []
                for eid in email_ids:
                    email = await email_service.get_by_id(eid, user_id)
                    if email:
                        emails.append(email)
            else:
                emails = await email_service.get_all(user_id, limit=10)
                emails = [e for e in emails if not e.summary]
            
            analyzed_count = 0
            for email in emails:
                try:
                    content = await email_service.get_email_content(user, email.gmail_id)
                    analysis = await email_agent.analyze_email(
                        subject=email.subject,
                        sender=email.sender,
                        content=content,
                    )
                    
                    await email_service.update_ai_analysis(
                        email=email,
                        summary=analysis.get("summary"),
                        category=analysis.get("category"),
                        priority_score=analysis.get("priority_score"),
                    )
                    analyzed_count += 1
                except Exception as e:
                    logger.error(f"Failed to analyze email {email.id}: {e}")
            
            return {
                "status": "success",
                "emails_analyzed": analyzed_count,
            }
    
    return run_async(_analyze())


@celery_app.task
def sync_all_emails():
    """Sync emails for all users with Google credentials."""
    async def _sync_all():
        from sqlalchemy import select
        from app.models.user import User
        
        async with get_db_context() as db:
            result = await db.execute(
                select(User.id).where(User.google_access_token.isnot(None))
            )
            user_ids = [row[0] for row in result.all()]
        
        for user_id in user_ids:
            sync_user_emails.delay(user_id)
        
        return {"users_queued": len(user_ids)}
    
    return run_async(_sync_all())


@celery_app.task(bind=True, max_retries=3)
def generate_email_reply(self, user_id: int, email_id: int, tone: str = "professional"):
    """Generate AI reply for an email."""
    async def _generate():
        async with get_db_context() as db:
            user_service = UserService(db)
            user = await user_service.get_by_id(user_id)
            
            if not user or not user.google_access_token:
                return {"status": "error", "reason": "no_credentials"}
            
            email_service = EmailService(db)
            email = await email_service.get_by_id(email_id, user_id)
            
            if not email:
                return {"status": "error", "reason": "email_not_found"}
            
            try:
                content = await email_service.get_email_content(user, email.gmail_id)
                
                email_agent = EmailAgent()
                reply = await email_agent.generate_reply(
                    subject=email.subject,
                    sender=email.sender,
                    content=content,
                    tone=tone,
                    user_name=user.full_name,
                )
                
                await email_service.update_ai_analysis(
                    email=email,
                    suggested_reply=reply,
                )
                
                return {
                    "status": "success",
                    "email_id": email_id,
                    "reply_generated": True,
                }
            except Exception as e:
                logger.error(f"Failed to generate reply for email {email_id}: {e}")
                raise self.retry(exc=e, countdown=30)
    
    return run_async(_generate())
