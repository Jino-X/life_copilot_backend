"""Habit tracking endpoints."""
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from app.api.v1.deps import CurrentUser, DbSession
from app.api.v1.schemas import (
    HabitCompleteRequest,
    HabitCreate,
    HabitResponse,
    HabitUpdate,
    HabitWithStatusResponse,
)
from app.services.habit_service import HabitService

router = APIRouter(prefix="/habits", tags=["Habits"])


@router.get("", response_model=list[HabitWithStatusResponse])
async def get_habits(
    current_user: CurrentUser,
    db: DbSession,
    active_only: bool = Query(True),
):
    """Get all habits with today's completion status."""
    habit_service = HabitService(db)
    habits_with_status = await habit_service.get_with_today_status(current_user.id)
    
    result = []
    for item in habits_with_status:
        habit = item["habit"]
        result.append(HabitWithStatusResponse(
            id=habit.id,
            name=habit.name,
            description=habit.description,
            icon=habit.icon,
            color=habit.color,
            frequency=habit.frequency,
            target_count=habit.target_count,
            current_streak=habit.current_streak,
            longest_streak=habit.longest_streak,
            is_active=habit.is_active,
            created_at=habit.created_at,
            completed_today=item["completed_today"],
            today_count=item["today_count"],
        ))
    
    return result


@router.get("/{habit_id}", response_model=HabitResponse)
async def get_habit(habit_id: int, current_user: CurrentUser, db: DbSession):
    """Get a specific habit."""
    habit_service = HabitService(db)
    habit = await habit_service.get_by_id(habit_id, current_user.id)
    
    if not habit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Habit not found",
        )
    
    return habit


@router.get("/{habit_id}/stats")
async def get_habit_stats(
    habit_id: int,
    current_user: CurrentUser,
    db: DbSession,
    days: int = Query(30, ge=7, le=365),
):
    """Get statistics for a habit."""
    habit_service = HabitService(db)
    habit = await habit_service.get_by_id(habit_id, current_user.id)
    
    if not habit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Habit not found",
        )
    
    return await habit_service.get_stats(habit, days)


@router.get("/{habit_id}/completions")
async def get_habit_completions(
    habit_id: int,
    current_user: CurrentUser,
    db: DbSession,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
    """Get completions for a habit within a date range."""
    habit_service = HabitService(db)
    habit = await habit_service.get_by_id(habit_id, current_user.id)
    
    if not habit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Habit not found",
        )
    
    if not start_date:
        start_date = date.today() - timedelta(days=30)
    if not end_date:
        end_date = date.today()
    
    completions = await habit_service.get_completions_range(
        habit_id=habit.id,
        start_date=start_date,
        end_date=end_date,
    )
    
    return [
        {
            "date": c.completed_date.isoformat(),
            "count": c.count,
            "notes": c.notes,
        }
        for c in completions
    ]


@router.post("", response_model=HabitResponse, status_code=status.HTTP_201_CREATED)
async def create_habit(data: HabitCreate, current_user: CurrentUser, db: DbSession):
    """Create a new habit."""
    habit_service = HabitService(db)
    
    habit = await habit_service.create(
        user_id=current_user.id,
        name=data.name,
        description=data.description,
        icon=data.icon,
        color=data.color,
        frequency=data.frequency,
        target_count=data.target_count,
    )
    
    return habit


@router.patch("/{habit_id}", response_model=HabitResponse)
async def update_habit(
    habit_id: int,
    data: HabitUpdate,
    current_user: CurrentUser,
    db: DbSession,
):
    """Update a habit."""
    habit_service = HabitService(db)
    habit = await habit_service.get_by_id(habit_id, current_user.id)
    
    if not habit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Habit not found",
        )
    
    updated_habit = await habit_service.update(
        habit=habit,
        name=data.name,
        description=data.description,
        icon=data.icon,
        color=data.color,
        frequency=data.frequency,
        target_count=data.target_count,
        is_active=data.is_active,
    )
    
    return updated_habit


@router.post("/{habit_id}/complete")
async def complete_habit(
    habit_id: int,
    data: HabitCompleteRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    """Mark a habit as completed."""
    habit_service = HabitService(db)
    habit = await habit_service.get_by_id(habit_id, current_user.id)
    
    if not habit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Habit not found",
        )
    
    completion = await habit_service.complete(
        habit=habit,
        completion_date=data.date,
        notes=data.notes,
    )
    
    return {
        "message": "Habit completed",
        "date": completion.completed_date.isoformat(),
        "count": completion.count,
        "current_streak": habit.current_streak,
    }


@router.post("/{habit_id}/uncomplete")
async def uncomplete_habit(
    habit_id: int,
    current_user: CurrentUser,
    db: DbSession,
    completion_date: Optional[date] = Query(None),
):
    """Remove completion for a habit."""
    habit_service = HabitService(db)
    habit = await habit_service.get_by_id(habit_id, current_user.id)
    
    if not habit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Habit not found",
        )
    
    await habit_service.uncomplete(habit, completion_date)
    
    return {"message": "Completion removed"}


@router.delete("/{habit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_habit(habit_id: int, current_user: CurrentUser, db: DbSession):
    """Delete a habit."""
    habit_service = HabitService(db)
    habit = await habit_service.get_by_id(habit_id, current_user.id)
    
    if not habit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Habit not found",
        )
    
    await habit_service.delete(habit)
