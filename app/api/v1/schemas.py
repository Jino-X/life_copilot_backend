"""Pydantic schemas for API request/response validation."""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# Auth Schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=1, max_length=255)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    avatar_url: Optional[str] = None
    timezone: str
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    timezone: Optional[str] = None
    preferences: Optional[str] = None


# Task Schemas
class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    priority: str = Field(default="medium", pattern="^(low|medium|high|urgent)$")
    due_date: Optional[datetime] = None
    tags: Optional[str] = None
    parent_id: Optional[int] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    priority: Optional[str] = Field(None, pattern="^(low|medium|high|urgent)$")
    status: Optional[str] = Field(None, pattern="^(todo|in_progress|completed|cancelled)$")
    due_date: Optional[datetime] = None
    tags: Optional[str] = None


class TaskResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    priority: str
    status: str
    due_date: Optional[datetime]
    tags: Optional[str]
    ai_generated: bool
    parent_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    subtasks: list["TaskResponse"] = []

    class Config:
        from_attributes = True


class TaskBreakdownRequest(BaseModel):
    task_id: int
    description: Optional[str] = None


# Note Schemas
class NoteCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    content: str
    folder: Optional[str] = None
    tags: Optional[str] = None


class NoteUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    content: Optional[str] = None
    folder: Optional[str] = None
    tags: Optional[str] = None


class NoteResponse(BaseModel):
    id: int
    title: str
    content: str
    folder: Optional[str]
    tags: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NoteSearchRequest(BaseModel):
    query: str
    limit: int = Field(default=10, ge=1, le=50)


# Habit Schemas
class HabitCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    frequency: str = Field(default="daily", pattern="^(daily|weekly|monthly)$")
    target_count: int = Field(default=1, ge=1)


class HabitUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    frequency: Optional[str] = Field(None, pattern="^(daily|weekly|monthly)$")
    target_count: Optional[int] = Field(None, ge=1)
    is_active: Optional[bool] = None


class HabitResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    icon: Optional[str]
    color: Optional[str]
    frequency: str
    target_count: int
    current_streak: int
    longest_streak: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class HabitWithStatusResponse(HabitResponse):
    completed_today: bool
    today_count: int


class HabitCompleteRequest(BaseModel):
    date: Optional[date] = None
    notes: Optional[str] = None


# Calendar Schemas
class CalendarEventCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    location: Optional[str] = None
    start_time: datetime
    end_time: datetime
    is_all_day: bool = False


class CalendarEventUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    location: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class CalendarEventResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    location: Optional[str]
    start_time: datetime
    end_time: datetime
    is_all_day: bool
    is_recurring: bool
    meeting_link: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class FreeSlotsRequest(BaseModel):
    duration_minutes: int = Field(..., ge=15, le=480)
    start_date: datetime
    end_date: datetime
    working_hours: tuple[int, int] = (9, 17)


# Email Schemas
class EmailResponse(BaseModel):
    id: int
    gmail_id: str
    subject: str
    sender: str
    snippet: Optional[str]
    summary: Optional[str]
    suggested_reply: Optional[str]
    category: str
    priority_score: Optional[int]
    is_read: bool
    is_starred: bool
    received_at: datetime

    class Config:
        from_attributes = True


class EmailReplyRequest(BaseModel):
    email_id: int
    reply_text: str


class EmailReplyGenerateRequest(BaseModel):
    email_id: int
    tone: str = Field(default="professional", pattern="^(professional|casual|formal|friendly)$")
    key_points: Optional[list[str]] = None


# Chat Schemas
class ChatMessageCreate(BaseModel):
    content: str = Field(..., min_length=1)
    session_id: Optional[int] = None


class ChatMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    agent_type: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ChatSessionResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[ChatMessageResponse] = []

    class Config:
        from_attributes = True


# Dashboard Schemas
class DashboardResponse(BaseModel):
    tasks_due_today: list[TaskResponse]
    overdue_tasks: list[TaskResponse]
    upcoming_events: list[CalendarEventResponse]
    habits_status: list[HabitWithStatusResponse]
    unread_emails: int
    daily_summary: Optional[str] = None
    ai_suggestions: list[str] = []


# Update forward references
TaskResponse.model_rebuild()
