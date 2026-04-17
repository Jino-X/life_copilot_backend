"""Reminder-related Celery tasks."""
import asyncio
from datetime import datetime, timedelta, timezone

from app.tasks.celery_app import celery_app
from app.core.database import get_db_context
from app.core.logging import get_logger
from app.services.task_service import TaskService
from app.services.habit_service import HabitService
from app.services.calendar_service import CalendarService
from app.services.user_service import UserService
from app.agents.reminder import ReminderAgent
from app.agents.base import AgentContext

logger = get_logger(__name__)


def run_async(coro):
    """Run async function in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task
def check_task_reminders():
    """Check for tasks that need reminders."""
    async def _check():
        from sqlalchemy import select, and_
        from app.models.task import Task
        from app.models.user import User
        
        now = datetime.now(timezone.utc)
        reminder_window = now + timedelta(minutes=15)
        
        async with get_db_context() as db:
            result = await db.execute(
                select(Task).where(
                    and_(
                        Task.reminder_at.isnot(None),
                        Task.reminder_at <= reminder_window,
                        Task.reminder_at > now - timedelta(minutes=5),
                        Task.status != "completed",
                    )
                )
            )
            tasks = result.scalars().all()
            
            reminders_sent = 0
            for task in tasks:
                send_task_reminder.delay(task.user_id, task.id)
                reminders_sent += 1
            
            return {"reminders_queued": reminders_sent}
    
    return run_async(_check())


@celery_app.task(bind=True, max_retries=2)
def send_task_reminder(self, user_id: int, task_id: int):
    """Send a reminder for a specific task."""
    async def _send():
        async with get_db_context() as db:
            task_service = TaskService(db)
            task = await task_service.get_by_id(task_id, user_id)
            
            if not task or task.status == "completed":
                return {"status": "skipped", "reason": "task_completed_or_not_found"}
            
            reminder_agent = ReminderAgent()
            
            urgency = "normal"
            if task.due_date:
                hours_until_due = (task.due_date - datetime.now(timezone.utc)).total_seconds() / 3600
                if hours_until_due < 1:
                    urgency = "urgent"
                elif hours_until_due < 4:
                    urgency = "high"
            
            reminder_message = await reminder_agent.generate_reminder(
                task={
                    "title": task.title,
                    "description": task.description,
                    "due_date": task.due_date.isoformat() if task.due_date else None,
                    "priority": task.priority,
                },
                urgency_level=urgency,
            )
            
            logger.info(f"Task reminder for user {user_id}: {reminder_message}")
            
            return {
                "status": "success",
                "task_id": task_id,
                "urgency": urgency,
                "message": reminder_message,
            }
    
    return run_async(_send())


@celery_app.task
def send_daily_summaries():
    """Send daily summary to all active users."""
    async def _send_all():
        from sqlalchemy import select
        from app.models.user import User
        
        async with get_db_context() as db:
            result = await db.execute(
                select(User.id).where(User.is_active == True)
            )
            user_ids = [row[0] for row in result.all()]
        
        for user_id in user_ids:
            generate_daily_summary.delay(user_id)
        
        return {"users_queued": len(user_ids)}
    
    return run_async(_send_all())


@celery_app.task(bind=True, max_retries=2)
def generate_daily_summary(self, user_id: int):
    """Generate and send daily summary for a user."""
    async def _generate():
        async with get_db_context() as db:
            user_service = UserService(db)
            user = await user_service.get_by_id(user_id)
            
            if not user:
                return {"status": "error", "reason": "user_not_found"}
            
            task_service = TaskService(db)
            calendar_service = CalendarService(db)
            habit_service = HabitService(db)
            
            tasks = await task_service.get_all(user_id, limit=20)
            events = await calendar_service.get_today_events(user_id)
            habits_data = await habit_service.get_with_today_status(user_id)
            overdue = await task_service.get_overdue(user_id)
            
            context = AgentContext(
                user_id=user_id,
                tasks=[
                    {
                        "title": t.title,
                        "priority": t.priority,
                        "status": t.status,
                        "due_date": t.due_date.isoformat() if t.due_date else None,
                    }
                    for t in tasks
                ],
                calendar_events=[
                    {
                        "title": e.title,
                        "start_time": e.start_time.isoformat(),
                        "end_time": e.end_time.isoformat(),
                    }
                    for e in events
                ],
                habits=[
                    {
                        "name": h["habit"].name,
                        "current_streak": h["habit"].current_streak,
                        "completed_today": h["completed_today"],
                    }
                    for h in habits_data
                ],
            )
            
            reminder_agent = ReminderAgent()
            nudge = await reminder_agent.generate_daily_nudge(
                context=context,
                time_of_day="morning",
            )
            
            logger.info(f"Daily summary for user {user_id}: {nudge}")
            
            return {
                "status": "success",
                "user_id": user_id,
                "tasks_count": len(tasks),
                "events_count": len(events),
                "overdue_count": len(overdue),
                "nudge": nudge,
            }
    
    return run_async(_generate())


@celery_app.task
def send_habit_reminders():
    """Send habit reminders to users."""
    async def _send():
        from sqlalchemy import select
        from app.models.habit import Habit
        
        async with get_db_context() as db:
            result = await db.execute(
                select(Habit).where(Habit.is_active == True)
            )
            habits = result.scalars().all()
            
            habit_service = HabitService(db)
            reminder_agent = ReminderAgent()
            
            reminders_sent = 0
            for habit in habits:
                completion = await habit_service.get_completion(
                    habit.id,
                    datetime.now(timezone.utc).date(),
                )
                
                if not completion:
                    reminder = await reminder_agent.generate_habit_reminder(
                        habit={
                            "name": habit.name,
                            "current_streak": habit.current_streak,
                            "target_count": habit.target_count,
                            "frequency": habit.frequency,
                        },
                        time_remaining="evening",
                    )
                    
                    logger.info(f"Habit reminder for {habit.name}: {reminder}")
                    reminders_sent += 1
            
            return {"reminders_sent": reminders_sent}
    
    return run_async(_send())


@celery_app.task(bind=True, max_retries=2)
def analyze_overdue_tasks(self, user_id: int):
    """Analyze overdue tasks and generate suggestions."""
    async def _analyze():
        async with get_db_context() as db:
            task_service = TaskService(db)
            overdue_tasks = await task_service.get_overdue(user_id)
            
            if not overdue_tasks:
                return {"status": "success", "message": "No overdue tasks"}
            
            reminder_agent = ReminderAgent()
            analysis = await reminder_agent.analyze_overdue_tasks([
                {
                    "title": t.title,
                    "due_date": t.due_date.isoformat() if t.due_date else None,
                    "priority": t.priority,
                }
                for t in overdue_tasks
            ])
            
            return {
                "status": "success",
                "overdue_count": len(overdue_tasks),
                "analysis": analysis,
            }
    
    return run_async(_analyze())
