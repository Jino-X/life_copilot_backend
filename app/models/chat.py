"""Chat history models."""
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class MessageRole(str, Enum):
    """Chat message role."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatSession(Base):
    """Chat session model for grouping messages."""
    
    __tablename__ = "chat_sessions"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    
    title: Mapped[str] = mapped_column(String(255), default="New Chat")
    
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
    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at"
    )
    
    def __repr__(self) -> str:
        # Use __dict__ to avoid triggering lazy loads when detached
        id_val = self.__dict__.get('id', 'N/A')
        title = self.__dict__.get('title', 'N/A')
        return f"<ChatSession(id={id_val}, title={title})>"


class ChatMessage(Base):
    """Chat message model for storing conversation history."""
    
    __tablename__ = "chat_messages"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    session_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # For tracking which agent handled the message
    agent_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Tool calls and results
    tool_calls: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    tool_results: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    
    # Metadata
    tokens_used: Mapped[Optional[int]] = mapped_column(nullable=True)
    model_used: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="chat_messages")
    session: Mapped[Optional["ChatSession"]] = relationship("ChatSession", back_populates="messages")
    
    def __repr__(self) -> str:
        # Use __dict__ to avoid triggering lazy loads when detached
        id_val = self.__dict__.get('id', 'N/A')
        role = self.__dict__.get('role', 'N/A')
        return f"<ChatMessage(id={id_val}, role={role})>"
