"""Chat service for managing chat sessions and messages."""
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.chat import ChatMessage, ChatSession, MessageRole


class ChatService:
    """Service for chat-related operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_session(
        self,
        session_id: int,
        user_id: int,
    ) -> Optional[ChatSession]:
        """Get chat session by ID."""
        result = await self.db.execute(
            select(ChatSession)
            .options(selectinload(ChatSession.messages))
            .where(
                and_(
                    ChatSession.id == session_id,
                    ChatSession.user_id == user_id,
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_sessions(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ChatSession]:
        """Get all chat sessions for a user."""
        result = await self.db.execute(
            select(ChatSession)
            .options(selectinload(ChatSession.messages))
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
    
    async def create_session(
        self,
        user_id: int,
        title: str = "New Chat",
    ) -> ChatSession:
        """Create a new chat session."""
        session = ChatSession(
            user_id=user_id,
            title=title,
        )
        
        self.db.add(session)
        await self.db.flush()
        await self.db.refresh(session)
        return session
    
    async def update_session_title(
        self,
        session: ChatSession,
        title: str,
    ) -> ChatSession:
        """Update chat session title."""
        session.title = title
        await self.db.flush()
        await self.db.refresh(session)
        return session
    
    async def delete_session(self, session: ChatSession) -> None:
        """Delete a chat session and all its messages."""
        await self.db.delete(session)
        await self.db.flush()
    
    async def get_messages(
        self,
        session_id: int,
        user_id: int,
        limit: int = 100,
    ) -> list[ChatMessage]:
        """Get messages for a chat session."""
        result = await self.db.execute(
            select(ChatMessage)
            .where(
                and_(
                    ChatMessage.session_id == session_id,
                    ChatMessage.user_id == user_id,
                )
            )
            .order_by(ChatMessage.created_at)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_recent_messages(
        self,
        user_id: int,
        session_id: Optional[int] = None,
        limit: int = 10,
    ) -> list[ChatMessage]:
        """Get recent messages for context."""
        query = select(ChatMessage).where(ChatMessage.user_id == user_id)
        
        if session_id:
            query = query.where(ChatMessage.session_id == session_id)
        
        query = query.order_by(ChatMessage.created_at.desc()).limit(limit)
        
        result = await self.db.execute(query)
        messages = list(result.scalars().all())
        return list(reversed(messages))
    
    async def add_message(
        self,
        user_id: int,
        role: str,
        content: str,
        session_id: Optional[int] = None,
        agent_type: Optional[str] = None,
        tool_calls: Optional[str] = None,
        tool_results: Optional[str] = None,
        tokens_used: Optional[int] = None,
        model_used: Optional[str] = None,
    ) -> ChatMessage:
        """Add a message to chat history."""
        message = ChatMessage(
            user_id=user_id,
            session_id=session_id,
            role=role,
            content=content,
            agent_type=agent_type,
            tool_calls=tool_calls,
            tool_results=tool_results,
            tokens_used=tokens_used,
            model_used=model_used,
        )
        
        self.db.add(message)
        await self.db.flush()
        await self.db.refresh(message)
        
        if session_id:
            session = await self.get_session(session_id, user_id)
            if session:
                session.updated_at = message.created_at
                await self.db.flush()
        
        return message
    
    async def add_user_message(
        self,
        user_id: int,
        content: str,
        session_id: Optional[int] = None,
    ) -> ChatMessage:
        """Add a user message."""
        return await self.add_message(
            user_id=user_id,
            role=MessageRole.USER.value,
            content=content,
            session_id=session_id,
        )
    
    async def add_assistant_message(
        self,
        user_id: int,
        content: str,
        session_id: Optional[int] = None,
        agent_type: Optional[str] = None,
        tool_calls: Optional[str] = None,
        tool_results: Optional[str] = None,
        tokens_used: Optional[int] = None,
        model_used: Optional[str] = None,
    ) -> ChatMessage:
        """Add an assistant message."""
        return await self.add_message(
            user_id=user_id,
            role=MessageRole.ASSISTANT.value,
            content=content,
            session_id=session_id,
            agent_type=agent_type,
            tool_calls=tool_calls,
            tool_results=tool_results,
            tokens_used=tokens_used,
            model_used=model_used,
        )
    
    async def generate_session_title(
        self,
        session: ChatSession,
        first_message: str,
    ) -> str:
        """Generate a title for the session based on first message."""
        title = first_message[:50]
        if len(first_message) > 50:
            title += "..."
        
        session.title = title
        await self.db.flush()
        return title
