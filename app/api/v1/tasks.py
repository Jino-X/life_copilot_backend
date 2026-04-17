"""Task management endpoints."""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from app.api.v1.deps import CurrentUser, DbSession
from app.api.v1.schemas import (
    TaskBreakdownRequest,
    TaskCreate,
    TaskResponse,
    TaskUpdate,
)
from app.agents.planner import PlannerAgent
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get("", response_model=list[TaskResponse])
async def get_tasks(
    current_user: CurrentUser,
    db: DbSession,
    status: Optional[str] = Query(None, pattern="^(todo|in_progress|completed|cancelled)$"),
    priority: Optional[str] = Query(None, pattern="^(low|medium|high|urgent)$"),
    include_subtasks: bool = Query(False),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get all tasks for the current user."""
    task_service = TaskService(db)
    tasks = await task_service.get_all(
        user_id=current_user.id,
        status=status,
        priority=priority,
        include_subtasks=include_subtasks,
        limit=limit,
        offset=offset,
    )
    return tasks


@router.get("/due-today", response_model=list[TaskResponse])
async def get_tasks_due_today(current_user: CurrentUser, db: DbSession):
    """Get tasks due today."""
    task_service = TaskService(db)
    return await task_service.get_due_today(current_user.id)


@router.get("/overdue", response_model=list[TaskResponse])
async def get_overdue_tasks(current_user: CurrentUser, db: DbSession):
    """Get overdue tasks."""
    task_service = TaskService(db)
    return await task_service.get_overdue(current_user.id)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int, current_user: CurrentUser, db: DbSession):
    """Get a specific task."""
    task_service = TaskService(db)
    task = await task_service.get_by_id(task_id, current_user.id)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    
    return task


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(data: TaskCreate, current_user: CurrentUser, db: DbSession):
    """Create a new task."""
    task_service = TaskService(db)
    
    if data.parent_id:
        parent = await task_service.get_by_id(data.parent_id, current_user.id)
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent task not found",
            )
    
    task = await task_service.create(
        user_id=current_user.id,
        title=data.title,
        description=data.description,
        priority=data.priority,
        due_date=data.due_date,
        parent_id=data.parent_id,
        tags=data.tags,
    )
    
    return task


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    data: TaskUpdate,
    current_user: CurrentUser,
    db: DbSession,
):
    """Update a task."""
    task_service = TaskService(db)
    task = await task_service.get_by_id(task_id, current_user.id)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    
    updated_task = await task_service.update(
        task=task,
        title=data.title,
        description=data.description,
        priority=data.priority,
        status=data.status,
        due_date=data.due_date,
        tags=data.tags,
    )
    
    return updated_task


@router.post("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(task_id: int, current_user: CurrentUser, db: DbSession):
    """Mark a task as completed."""
    task_service = TaskService(db)
    task = await task_service.get_by_id(task_id, current_user.id)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    
    return await task_service.complete(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: int, current_user: CurrentUser, db: DbSession):
    """Delete a task."""
    task_service = TaskService(db)
    task = await task_service.get_by_id(task_id, current_user.id)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    
    await task_service.delete(task)


@router.post("/{task_id}/breakdown", response_model=list[TaskResponse])
async def breakdown_task(
    task_id: int,
    current_user: CurrentUser,
    db: DbSession,
    description: Optional[str] = None,
):
    """Break down a task into subtasks using AI."""
    task_service = TaskService(db)
    task = await task_service.get_by_id(task_id, current_user.id)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    
    planner = PlannerAgent()
    subtask_titles = await planner.suggest_task_breakdown(
        task_title=task.title,
        task_description=description or task.description,
    )
    
    if not subtask_titles:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not generate subtasks for this task",
        )
    
    subtasks = await task_service.create_subtasks(task, subtask_titles)
    return subtasks
