"""Calendar service for Google Calendar integration."""
import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.calendar_event import CalendarEvent
from app.models.user import User


class CalendarService:
    """Service for calendar-related operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, event_id: int, user_id: int) -> Optional[CalendarEvent]:
        """Get calendar event by ID for a specific user."""
        result = await self.db.execute(
            select(CalendarEvent).where(
                and_(CalendarEvent.id == event_id, CalendarEvent.user_id == user_id)
            )
        )
        return result.scalar_one_or_none()
    
    async def get_events(
        self,
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[CalendarEvent]:
        """Get calendar events for a user within a date range."""
        query = select(CalendarEvent).where(CalendarEvent.user_id == user_id)
        
        if start_date:
            query = query.where(CalendarEvent.start_time >= start_date)
        if end_date:
            query = query.where(CalendarEvent.start_time <= end_date)
        
        query = query.order_by(CalendarEvent.start_time).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_today_events(self, user_id: int) -> list[CalendarEvent]:
        """Get today's events for a user."""
        now = datetime.now(timezone.utc)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        
        return await self.get_events(user_id, start_of_day, end_of_day)
    
    async def get_upcoming_events(
        self,
        user_id: int,
        hours: int = 24,
    ) -> list[CalendarEvent]:
        """Get upcoming events within specified hours."""
        now = datetime.now(timezone.utc)
        end_time = now + timedelta(hours=hours)
        
        return await self.get_events(user_id, now, end_time)
    
    async def create(
        self,
        user_id: int,
        title: str,
        start_time: datetime,
        end_time: datetime,
        description: Optional[str] = None,
        location: Optional[str] = None,
        is_all_day: bool = False,
        google_event_id: Optional[str] = None,
        google_calendar_id: Optional[str] = None,
    ) -> CalendarEvent:
        """Create a new calendar event."""
        event = CalendarEvent(
            user_id=user_id,
            title=title,
            start_time=start_time,
            end_time=end_time,
            description=description,
            location=location,
            is_all_day=is_all_day,
            google_event_id=google_event_id,
            google_calendar_id=google_calendar_id,
        )
        
        self.db.add(event)
        await self.db.flush()
        await self.db.refresh(event)
        return event
    
    async def update(
        self,
        event: CalendarEvent,
        title: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
    ) -> CalendarEvent:
        """Update a calendar event."""
        if title is not None:
            event.title = title
        if start_time is not None:
            event.start_time = start_time
        if end_time is not None:
            event.end_time = end_time
        if description is not None:
            event.description = description
        if location is not None:
            event.location = location
        
        await self.db.flush()
        await self.db.refresh(event)
        return event
    
    async def delete(self, event: CalendarEvent) -> None:
        """Delete a calendar event."""
        await self.db.delete(event)
        await self.db.flush()
    
    def _get_google_service(self, user: User):
        """Get Google Calendar API service."""
        if not user.google_access_token:
            raise ValueError("User has no Google credentials")
        
        credentials = Credentials(
            token=user.google_access_token,
            refresh_token=user.google_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
        )
        
        return build("calendar", "v3", credentials=credentials)
    
    async def sync_from_google(
        self,
        user: User,
        days_ahead: int = 30,
    ) -> list[CalendarEvent]:
        """Sync events from Google Calendar."""
        service = self._get_google_service(user)
        
        now = datetime.now(timezone.utc)
        time_min = now.isoformat()
        time_max = (now + timedelta(days=days_ahead)).isoformat()
        
        events_result = service.events().list(
            calendarId="primary",
            timeMin=time_min,
            timeMax=time_max,
            maxResults=100,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        
        google_events = events_result.get("items", [])
        synced_events = []
        
        for g_event in google_events:
            start = g_event.get("start", {})
            end = g_event.get("end", {})
            
            is_all_day = "date" in start
            
            if is_all_day:
                start_time = datetime.fromisoformat(start["date"])
                end_time = datetime.fromisoformat(end["date"])
            else:
                start_time = datetime.fromisoformat(
                    start.get("dateTime", "").replace("Z", "+00:00")
                )
                end_time = datetime.fromisoformat(
                    end.get("dateTime", "").replace("Z", "+00:00")
                )
            
            existing = await self._get_by_google_id(user.id, g_event["id"])
            
            if existing:
                existing.title = g_event.get("summary", "No Title")
                existing.description = g_event.get("description")
                existing.location = g_event.get("location")
                existing.start_time = start_time
                existing.end_time = end_time
                existing.is_all_day = is_all_day
                existing.meeting_link = g_event.get("hangoutLink")
                existing.attendees = json.dumps(g_event.get("attendees", []))
                existing.synced_at = datetime.now(timezone.utc)
                synced_events.append(existing)
            else:
                event = await self.create(
                    user_id=user.id,
                    title=g_event.get("summary", "No Title"),
                    start_time=start_time,
                    end_time=end_time,
                    description=g_event.get("description"),
                    location=g_event.get("location"),
                    is_all_day=is_all_day,
                    google_event_id=g_event["id"],
                    google_calendar_id="primary",
                )
                event.meeting_link = g_event.get("hangoutLink")
                event.attendees = json.dumps(g_event.get("attendees", []))
                event.synced_at = datetime.now(timezone.utc)
                synced_events.append(event)
        
        await self.db.flush()
        return synced_events
    
    async def _get_by_google_id(
        self,
        user_id: int,
        google_event_id: str,
    ) -> Optional[CalendarEvent]:
        """Get event by Google Calendar event ID."""
        result = await self.db.execute(
            select(CalendarEvent).where(
                and_(
                    CalendarEvent.user_id == user_id,
                    CalendarEvent.google_event_id == google_event_id,
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def find_free_slots(
        self,
        user_id: int,
        duration_minutes: int,
        start_date: datetime,
        end_date: datetime,
        working_hours: tuple[int, int] = (9, 17),
    ) -> list[dict]:
        """Find free time slots for scheduling."""
        events = await self.get_events(user_id, start_date, end_date)
        
        free_slots = []
        current_date = start_date.date()
        end_date_only = end_date.date()
        
        while current_date <= end_date_only:
            day_start = datetime.combine(
                current_date,
                datetime.min.time().replace(hour=working_hours[0]),
                tzinfo=timezone.utc,
            )
            day_end = datetime.combine(
                current_date,
                datetime.min.time().replace(hour=working_hours[1]),
                tzinfo=timezone.utc,
            )
            
            day_events = [
                e for e in events
                if e.start_time.date() == current_date
            ]
            day_events.sort(key=lambda x: x.start_time)
            
            slot_start = day_start
            for event in day_events:
                if event.start_time > slot_start:
                    slot_duration = (event.start_time - slot_start).total_seconds() / 60
                    if slot_duration >= duration_minutes:
                        free_slots.append({
                            "start": slot_start.isoformat(),
                            "end": event.start_time.isoformat(),
                            "duration_minutes": int(slot_duration),
                        })
                slot_start = max(slot_start, event.end_time)
            
            if slot_start < day_end:
                slot_duration = (day_end - slot_start).total_seconds() / 60
                if slot_duration >= duration_minutes:
                    free_slots.append({
                        "start": slot_start.isoformat(),
                        "end": day_end.isoformat(),
                        "duration_minutes": int(slot_duration),
                    })
            
            current_date += timedelta(days=1)
        
        return free_slots
