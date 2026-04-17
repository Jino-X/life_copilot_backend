"""Task service for task management."""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.task import Task, TaskStatus


class TaskService:
    """Service for task-related operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, task_id: int, user_id: int) -> Optional[Task]:
        """Get task by ID for a specific user."""
        result = await self.db.execute(
            select(Task)
            .options(selectinload(Task.subtasks))
            .where(and_(Task.id == task_id, Task.user_id == user_id))
        )
        return result.scalar_one_or_none()
    
    async def get_all(
        self,
        user_id: int,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        include_subtasks: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Task]:
        """Get all tasks for a user with optional filters."""
        query = select(Task).options(selectinload(Task.subtasks)).where(
            and_(Task.user_id == user_id, Task.parent_id.is_(None))
        )
        
        if status:
            query = query.where(Task.status == status)
        if priority:
            query = query.where(Task.priority == priority)
        
        query = query.order_by(Task.order, Task.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_due_today(self, user_id: int) -> list[Task]:
        """Get tasks due today."""
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        today_end = today_start.replace(hour=23, minute=59, second=59)
        
        result = await self.db.execute(
            select(Task)
            .options(selectinload(Task.subtasks))
            .where(
                and_(
                    Task.user_id == user_id,
                    Task.due_date >= today_start,
                    Task.due_date <= today_end,
                    Task.status != TaskStatus.COMPLETED.value,
                )
            )
            .order_by(Task.due_date)
        )
        return list(result.scalars().all())
    
    async def get_overdue(self, user_id: int) -> list[Task]:
        """Get overdue tasks."""
        now = datetime.now(timezone.utc)
        
        result = await self.db.execute(
            select(Task)
            .options(selectinload(Task.subtasks))
            .where(
                and_(
                    Task.user_id == user_id,
                    Task.due_date < now,
                    Task.status != TaskStatus.COMPLETED.value,
                )
            )
            .order_by(Task.due_date)
        )
        return list(result.scalars().all())
    
    async def create(
        self,
        user_id: int,
        title: str,
        description: Optional[str] = None,
        priority: str = "medium",
        due_date: Optional[datetime] = None,
        parent_id: Optional[int] = None,
        tags: Optional[str] = None,
        ai_generated: bool = False,
    ) -> Task:
        """Create a new task."""
        task = Task(
            user_id=user_id,
            title=title,
            description=description,
            priority=priority,
            due_date=due_date,
            parent_id=parent_id,
            tags=tags,
            ai_generated=ai_generated,
        )
        
        self.db.add(task)
        await self.db.flush()
        await self.db.refresh(task, attribute_names=['subtasks'])
        return task
    
    async def create_subtasks(
        self,
        parent_task: Task,
        subtask_titles: list[str],
    ) -> list[Task]:
        """Create multiple subtasks for a parent task."""
        subtasks = []
        for i, title in enumerate(subtask_titles):
            subtask = Task(
                user_id=parent_task.user_id,
                title=title,
                parent_id=parent_task.id,
                priority=parent_task.priority,
                order=i,
                ai_generated=True,
            )
            self.db.add(subtask)
            subtasks.append(subtask)
        
        await self.db.flush()
        for subtask in subtasks:
            await self.db.refresh(subtask)
        return subtasks
    
    async def update(
        self,
        task: Task,
        title: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[str] = None,
        status: Optional[str] = None,
        due_date: Optional[datetime] = None,
        tags: Optional[str] = None,
    ) -> Task:
        """Update a task."""
        if title is not None:
            task.title = title
        if description is not None:
            task.description = description
        if priority is not None:
            task.priority = priority
        if status is not None:
            task.status = status
            if status == TaskStatus.COMPLETED.value:
                task.completed_at = datetime.now(timezone.utc)
        if due_date is not None:
            task.due_date = due_date
        if tags is not None:
            task.tags = tags
        
        await self.db.flush()
        await self.db.refresh(task, attribute_names=['subtasks'])
        return task
    
    async def complete(self, task: Task) -> Task:
        """Mark a task as completed."""
        task.status = TaskStatus.COMPLETED.value
        task.completed_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(task, attribute_names=['subtasks'])
        return task
    
    async def delete(self, task: Task) -> None:
        """Delete a task."""
        await self.db.delete(task)
        await self.db.flush()
    
    async def reorder(self, task: Task, new_order: int) -> None:
        """Reorder a task."""
        task.order = new_order
        await self.db.flush()
