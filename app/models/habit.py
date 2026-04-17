"""Habit tracking models."""
from datetime import datetime, timezone, date
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class HabitFrequency(str, Enum):
    """Habit frequency options."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class Habit(Base):
    """Habit model for tracking recurring habits."""
    
    __tablename__ = "habits"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    frequency: Mapped[str] = mapped_column(String(20), default=HabitFrequency.DAILY.value)
    target_count: Mapped[int] = mapped_column(Integer, default=1)
    
    # Streak tracking
    current_streak: Mapped[int] = mapped_column(Integer, default=0)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
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
    user: Mapped["User"] = relationship("User", back_populates="habits")
    completions: Mapped[list["HabitCompletion"]] = relationship(
        "HabitCompletion",
        back_populates="habit",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        id_val = self.__dict__.get('id', 'N/A')
        name = self.__dict__.get('name', 'N/A')
        return f"<Habit(id={id_val}, name={name})>"


class HabitCompletion(Base):
    """Model for tracking habit completions."""
    
    __tablename__ = "habit_completions"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    habit_id: Mapped[int] = mapped_column(ForeignKey("habits.id", ondelete="CASCADE"), index=True)
    
    completed_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    count: Mapped[int] = mapped_column(Integer, default=1)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    
    # Relationships
    habit: Mapped["Habit"] = relationship("Habit", back_populates="completions")
    
    def __repr__(self) -> str:
        id_val = self.__dict__.get('id', 'N/A')
        habit_id = self.__dict__.get('habit_id', 'N/A')
        date = self.__dict__.get('completed_date', 'N/A')
        return f"<HabitCompletion(id={id_val}, habit_id={habit_id}, date={date})>"
