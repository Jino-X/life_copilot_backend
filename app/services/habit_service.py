"""Habit service for habit tracking."""
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.habit import Habit, HabitCompletion


class HabitService:
    """Service for habit-related operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, habit_id: int, user_id: int) -> Optional[Habit]:
        """Get habit by ID for a specific user."""
        result = await self.db.execute(
            select(Habit)
            .options(selectinload(Habit.completions))
            .where(and_(Habit.id == habit_id, Habit.user_id == user_id))
        )
        return result.scalar_one_or_none()
    
    async def get_all(
        self,
        user_id: int,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Habit]:
        """Get all habits for a user."""
        query = select(Habit).where(Habit.user_id == user_id)
        
        if active_only:
            query = query.where(Habit.is_active == True)
        
        query = query.order_by(Habit.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_with_today_status(self, user_id: int) -> list[dict]:
        """Get all habits with today's completion status."""
        habits = await self.get_all(user_id)
        today = date.today()
        
        result = []
        for habit in habits:
            completion = await self.get_completion(habit.id, today)
            result.append({
                "habit": habit,
                "completed_today": completion is not None,
                "today_count": completion.count if completion else 0,
            })
        
        return result
    
    async def create(
        self,
        user_id: int,
        name: str,
        description: Optional[str] = None,
        icon: Optional[str] = None,
        color: Optional[str] = None,
        frequency: str = "daily",
        target_count: int = 1,
    ) -> Habit:
        """Create a new habit."""
        habit = Habit(
            user_id=user_id,
            name=name,
            description=description,
            icon=icon,
            color=color,
            frequency=frequency,
            target_count=target_count,
        )
        
        self.db.add(habit)
        await self.db.flush()
        await self.db.refresh(habit)
        return habit
    
    async def update(
        self,
        habit: Habit,
        name: Optional[str] = None,
        description: Optional[str] = None,
        icon: Optional[str] = None,
        color: Optional[str] = None,
        frequency: Optional[str] = None,
        target_count: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> Habit:
        """Update a habit."""
        if name is not None:
            habit.name = name
        if description is not None:
            habit.description = description
        if icon is not None:
            habit.icon = icon
        if color is not None:
            habit.color = color
        if frequency is not None:
            habit.frequency = frequency
        if target_count is not None:
            habit.target_count = target_count
        if is_active is not None:
            habit.is_active = is_active
        
        await self.db.flush()
        await self.db.refresh(habit)
        return habit
    
    async def delete(self, habit: Habit) -> None:
        """Delete a habit."""
        await self.db.delete(habit)
        await self.db.flush()
    
    async def get_completion(
        self,
        habit_id: int,
        completion_date: date,
    ) -> Optional[HabitCompletion]:
        """Get completion for a specific date."""
        result = await self.db.execute(
            select(HabitCompletion).where(
                and_(
                    HabitCompletion.habit_id == habit_id,
                    HabitCompletion.completed_date == completion_date,
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def complete(
        self,
        habit: Habit,
        completion_date: Optional[date] = None,
        notes: Optional[str] = None,
    ) -> HabitCompletion:
        """Mark a habit as completed for a date."""
        if completion_date is None:
            completion_date = date.today()
        
        existing = await self.get_completion(habit.id, completion_date)
        
        if existing:
            existing.count += 1
            if notes:
                existing.notes = notes
            await self.db.flush()
            await self.db.refresh(existing)
            completion = existing
        else:
            completion = HabitCompletion(
                habit_id=habit.id,
                completed_date=completion_date,
                notes=notes,
            )
            self.db.add(completion)
            await self.db.flush()
            await self.db.refresh(completion)
        
        await self._update_streak(habit)
        return completion
    
    async def uncomplete(
        self,
        habit: Habit,
        completion_date: Optional[date] = None,
    ) -> None:
        """Remove completion for a date."""
        if completion_date is None:
            completion_date = date.today()
        
        existing = await self.get_completion(habit.id, completion_date)
        if existing:
            await self.db.delete(existing)
            await self.db.flush()
            await self._update_streak(habit)
    
    async def _update_streak(self, habit: Habit) -> None:
        """Update habit streak based on completions."""
        today = date.today()
        current_streak = 0
        check_date = today
        
        while True:
            completion = await self.get_completion(habit.id, check_date)
            if completion:
                current_streak += 1
                check_date -= timedelta(days=1)
            else:
                break
        
        habit.current_streak = current_streak
        if current_streak > habit.longest_streak:
            habit.longest_streak = current_streak
        
        await self.db.flush()
    
    async def get_completions_range(
        self,
        habit_id: int,
        start_date: date,
        end_date: date,
    ) -> list[HabitCompletion]:
        """Get completions for a date range."""
        result = await self.db.execute(
            select(HabitCompletion)
            .where(
                and_(
                    HabitCompletion.habit_id == habit_id,
                    HabitCompletion.completed_date >= start_date,
                    HabitCompletion.completed_date <= end_date,
                )
            )
            .order_by(HabitCompletion.completed_date)
        )
        return list(result.scalars().all())
    
    async def get_stats(self, habit: Habit, days: int = 30) -> dict:
        """Get habit statistics."""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        completions = await self.get_completions_range(habit.id, start_date, end_date)
        
        total_completions = sum(c.count for c in completions)
        completion_rate = len(completions) / days * 100 if days > 0 else 0
        
        return {
            "total_completions": total_completions,
            "completion_rate": round(completion_rate, 1),
            "current_streak": habit.current_streak,
            "longest_streak": habit.longest_streak,
            "days_tracked": days,
        }
