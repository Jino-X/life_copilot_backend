"""Calendar management endpoints."""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from app.api.v1.deps import CurrentUser, DbSession
from app.api.v1.schemas import (
    CalendarEventCreate,
    CalendarEventResponse,
    CalendarEventUpdate,
    FreeSlotsRequest,
)
from app.services.calendar_service import CalendarService

router = APIRouter(prefix="/calendar", tags=["Calendar"])


@router.get("", response_model=list[CalendarEventResponse])
async def get_events(
    current_user: CurrentUser,
    db: DbSession,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(100, ge=1, le=500),
):
    """Get calendar events within a date range."""
    calendar_service = CalendarService(db)
    
    if not start_date:
        start_date = datetime.now(timezone.utc)
    if not end_date:
        end_date = start_date + timedelta(days=30)
    
    events = await calendar_service.get_events(
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    
    return events


@router.get("/today", response_model=list[CalendarEventResponse])
async def get_today_events(current_user: CurrentUser, db: DbSession):
    """Get today's calendar events."""
    calendar_service = CalendarService(db)
    return await calendar_service.get_today_events(current_user.id)


@router.get("/upcoming", response_model=list[CalendarEventResponse])
async def get_upcoming_events(
    current_user: CurrentUser,
    db: DbSession,
    hours: int = Query(24, ge=1, le=168),
):
    """Get upcoming events within specified hours."""
    calendar_service = CalendarService(db)
    return await calendar_service.get_upcoming_events(current_user.id, hours)


@router.get("/{event_id}", response_model=CalendarEventResponse)
async def get_event(event_id: int, current_user: CurrentUser, db: DbSession):
    """Get a specific calendar event."""
    calendar_service = CalendarService(db)
    event = await calendar_service.get_by_id(event_id, current_user.id)
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    
    return event


@router.post("", response_model=CalendarEventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    data: CalendarEventCreate,
    current_user: CurrentUser,
    db: DbSession,
):
    """Create a new calendar event."""
    if data.end_time <= data.start_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End time must be after start time",
        )
    
    calendar_service = CalendarService(db)
    
    event = await calendar_service.create(
        user_id=current_user.id,
        title=data.title,
        start_time=data.start_time,
        end_time=data.end_time,
        description=data.description,
        location=data.location,
        is_all_day=data.is_all_day,
    )
    
    return event


@router.patch("/{event_id}", response_model=CalendarEventResponse)
async def update_event(
    event_id: int,
    data: CalendarEventUpdate,
    current_user: CurrentUser,
    db: DbSession,
):
    """Update a calendar event."""
    calendar_service = CalendarService(db)
    event = await calendar_service.get_by_id(event_id, current_user.id)
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    
    if data.start_time and data.end_time and data.end_time <= data.start_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End time must be after start time",
        )
    
    updated_event = await calendar_service.update(
        event=event,
        title=data.title,
        start_time=data.start_time,
        end_time=data.end_time,
        description=data.description,
        location=data.location,
    )
    
    return updated_event


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(event_id: int, current_user: CurrentUser, db: DbSession):
    """Delete a calendar event."""
    calendar_service = CalendarService(db)
    event = await calendar_service.get_by_id(event_id, current_user.id)
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    
    await calendar_service.delete(event)


@router.post("/sync")
async def sync_google_calendar(current_user: CurrentUser, db: DbSession):
    """Sync events from Google Calendar."""
    if not current_user.google_access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google Calendar not connected. Please connect via Google OAuth.",
        )
    
    calendar_service = CalendarService(db)
    
    try:
        synced_events = await calendar_service.sync_from_google(current_user)
        return {
            "message": f"Synced {len(synced_events)} events from Google Calendar",
            "events_count": len(synced_events),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync calendar: {str(e)}",
        )


@router.post("/free-slots")
async def find_free_slots(
    data: FreeSlotsRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    """Find free time slots for scheduling."""
    calendar_service = CalendarService(db)
    
    free_slots = await calendar_service.find_free_slots(
        user_id=current_user.id,
        duration_minutes=data.duration_minutes,
        start_date=data.start_date,
        end_date=data.end_date,
        working_hours=data.working_hours,
    )
    
    return {"free_slots": free_slots}
