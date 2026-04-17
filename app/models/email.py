"""Email metadata model."""
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class EmailCategory(str, Enum):
    """Email category options."""
    IMPORTANT = "important"
    FOLLOW_UP = "follow_up"
    NEWSLETTER = "newsletter"
    SPAM = "spam"
    PERSONAL = "personal"
    WORK = "work"
    OTHER = "other"


class Email(Base):
    """Email metadata model for Gmail integration."""
    
    __tablename__ = "emails"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    
    # Gmail IDs
    gmail_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    thread_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Email details
    subject: Mapped[str] = mapped_column(String(1000), nullable=False)
    sender: Mapped[str] = mapped_column(String(500), nullable=False)
    recipients: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # AI-generated
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    suggested_reply: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(20), default=EmailCategory.OTHER.value)
    priority_score: Mapped[Optional[int]] = mapped_column(nullable=True)
    
    # Status
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    is_starred: Mapped[bool] = mapped_column(Boolean, default=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Timestamps
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    
    def __repr__(self) -> str:
        id_val = self.__dict__.get('id', 'N/A')
        subject = self.__dict__.get('subject', 'N/A')[:30] if self.__dict__.get('subject') else 'N/A'
        return f"<Email(id={id_val}, subject={subject})>"
