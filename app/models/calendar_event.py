"""Calendar event model."""
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class CalendarEvent(Base):
    """Calendar event model for Google Calendar integration."""
    
    __tablename__ = "calendar_events"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    
    # Google Calendar ID
    google_event_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    google_calendar_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    is_all_day: Mapped[bool] = mapped_column(Boolean, default=False)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    recurrence_rule: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Meeting details
    meeting_link: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    attendees: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default="confirmed")
    
    # Sync tracking
    synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="calendar_events")
    
    def __repr__(self) -> str:
        id_val = self.__dict__.get('id', 'N/A')
        title = self.__dict__.get('title', 'N/A')[:30] if self.__dict__.get('title') else 'N/A'
        return f"<CalendarEvent(id={id_val}, title={title})>"
