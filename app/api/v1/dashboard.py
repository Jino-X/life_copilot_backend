"""Dashboard endpoints."""
from fastapi import APIRouter

from app.api.v1.deps import CurrentUser, DbSession
from app.api.v1.schemas import (
    CalendarEventResponse,
    DashboardResponse,
    HabitWithStatusResponse,
    TaskResponse,
)
from app.agents.base import AgentContext
from app.agents.orchestrator import OrchestratorAgent
from app.services.task_service import TaskService
from app.services.calendar_service import CalendarService
from app.services.habit_service import HabitService
from app.services.email_service import EmailService
from app.services.vector_store import get_vector_store

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardResponse)
async def get_dashboard(current_user: CurrentUser, db: DbSession):
    """Get dashboard data with AI-generated insights."""
    task_service = TaskService(db)
    calendar_service = CalendarService(db)
    habit_service = HabitService(db)
    email_service = EmailService(db)
    
    tasks_due_today = await task_service.get_due_today(current_user.id)
    overdue_tasks = await task_service.get_overdue(current_user.id)
    upcoming_events = await calendar_service.get_upcoming_events(current_user.id, hours=24)
    habits_data = await habit_service.get_with_today_status(current_user.id)
    unread_emails = await email_service.get_unread_count(current_user.id)
    
    habits_status = [
        HabitWithStatusResponse(
            id=h["habit"].id,
            name=h["habit"].name,
            description=h["habit"].description,
            icon=h["habit"].icon,
            color=h["habit"].color,
            frequency=h["habit"].frequency,
            target_count=h["habit"].target_count,
            current_streak=h["habit"].current_streak,
            longest_streak=h["habit"].longest_streak,
            is_active=h["habit"].is_active,
            created_at=h["habit"].created_at,
            completed_today=h["completed_today"],
            today_count=h["today_count"],
        )
        for h in habits_data
    ]
    
    return DashboardResponse(
        tasks_due_today=[TaskResponse.model_validate(t) for t in tasks_due_today],
        overdue_tasks=[TaskResponse.model_validate(t) for t in overdue_tasks],
        upcoming_events=[CalendarEventResponse.model_validate(e) for e in upcoming_events],
        habits_status=habits_status,
        unread_emails=unread_emails,
    )


@router.get("/summary")
async def get_daily_summary(current_user: CurrentUser, db: DbSession):
    """Get AI-generated daily summary."""
    task_service = TaskService(db)
    calendar_service = CalendarService(db)
    habit_service = HabitService(db)
    
    tasks = await task_service.get_all(current_user.id, limit=20)
    events = await calendar_service.get_upcoming_events(current_user.id, hours=24)
    habits_data = await habit_service.get_with_today_status(current_user.id)
    
    context = AgentContext(
        user_id=current_user.id,
        tasks=[
            {
                "id": t.id,
                "title": t.title,
                "priority": t.priority,
                "status": t.status,
                "due_date": t.due_date.isoformat() if t.due_date else None,
            }
            for t in tasks
        ],
        calendar_events=[
            {
                "id": e.id,
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
    
    vector_store = await get_vector_store()
    orchestrator = OrchestratorAgent(vector_store=vector_store)
    summary = await orchestrator.get_daily_summary(context)
    
    return summary


@router.get("/plan-my-day")
async def plan_my_day(current_user: CurrentUser, db: DbSession):
    """Get AI-generated daily plan."""
    task_service = TaskService(db)
    calendar_service = CalendarService(db)
    habit_service = HabitService(db)
    
    tasks = await task_service.get_all(current_user.id, limit=30)
    events = await calendar_service.get_today_events(current_user.id)
    habits_data = await habit_service.get_with_today_status(current_user.id)
    
    context = AgentContext(
        user_id=current_user.id,
        tasks=[
            {
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "priority": t.priority,
                "status": t.status,
                "due_date": t.due_date.isoformat() if t.due_date else None,
            }
            for t in tasks
        ],
        calendar_events=[
            {
                "id": e.id,
                "title": e.title,
                "start_time": e.start_time.isoformat(),
                "end_time": e.end_time.isoformat(),
                "location": e.location,
            }
            for e in events
        ],
        habits=[
            {
                "name": h["habit"].name,
                "current_streak": h["habit"].current_streak,
                "completed_today": h["completed_today"],
                "target_count": h["habit"].target_count,
            }
            for h in habits_data
        ],
    )
    
    vector_store = await get_vector_store()
    orchestrator = OrchestratorAgent(vector_store=vector_store)
    
    plan = await orchestrator.planner.create_daily_plan(context)
    
    return {"plan": plan}


@router.get("/insights")
async def get_insights(current_user: CurrentUser, db: DbSession):
    """Get AI-generated productivity insights."""
    task_service = TaskService(db)
    habit_service = HabitService(db)
    
    all_tasks = await task_service.get_all(current_user.id, limit=50)
    completed_tasks = [t for t in all_tasks if t.status == "completed"]
    pending_tasks = [t for t in all_tasks if t.status != "completed"]
    overdue_tasks = await task_service.get_overdue(current_user.id)
    
    habits = await habit_service.get_all(current_user.id)
    habit_stats = []
    for habit in habits:
        stats = await habit_service.get_stats(habit, days=7)
        habit_stats.append({
            "name": habit.name,
            "completion_rate": stats["completion_rate"],
            "current_streak": stats["current_streak"],
        })
    
    insights = {
        "task_completion_rate": len(completed_tasks) / len(all_tasks) * 100 if all_tasks else 0,
        "pending_tasks_count": len(pending_tasks),
        "overdue_tasks_count": len(overdue_tasks),
        "high_priority_pending": len([t for t in pending_tasks if t.priority in ["high", "urgent"]]),
        "habit_stats": habit_stats,
        "suggestions": [],
    }
    
    if len(overdue_tasks) > 3:
        insights["suggestions"].append(
            "You have several overdue tasks. Consider reviewing and reprioritizing them."
        )
    
    if insights["task_completion_rate"] < 50:
        insights["suggestions"].append(
            "Your task completion rate is below 50%. Try breaking down large tasks into smaller ones."
        )
    
    low_streak_habits = [h for h in habit_stats if h["completion_rate"] < 50]
    if low_streak_habits:
        insights["suggestions"].append(
            f"Some habits need attention: {', '.join(h['name'] for h in low_streak_habits[:3])}"
        )
    
    return insights
