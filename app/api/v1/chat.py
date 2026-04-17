"""Chat endpoints with streaming support."""
import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.api.v1.deps import CurrentUser, DbSession
from app.api.v1.schemas import (
    ChatMessageCreate,
    ChatMessageResponse,
    ChatSessionResponse,
)
from app.agents.base import AgentContext
from app.agents.orchestrator import OrchestratorAgent
from app.services.chat_service import ChatService
from app.services.task_service import TaskService
from app.services.calendar_service import CalendarService
from app.services.habit_service import HabitService
from app.services.vector_store import get_vector_store

router = APIRouter(prefix="/chat", tags=["Chat"])


async def build_agent_context(
    user_id: int,
    db,
) -> AgentContext:
    """Build context for the AI agent."""
    task_service = TaskService(db)
    calendar_service = CalendarService(db)
    habit_service = HabitService(db)
    
    tasks = await task_service.get_all(user_id, limit=20)
    events = await calendar_service.get_upcoming_events(user_id, hours=48)
    habits_data = await habit_service.get_with_today_status(user_id)
    
    return AgentContext(
        user_id=user_id,
        tasks=[
            {
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "priority": t.priority,
                "status": t.status,
                "due_date": t.due_date.isoformat() if t.due_date else None,
            }
            for t in tasks
        ],
        calendar_events=[
            {
                "id": e.id,
                "title": e.title,
                "start_time": e.start_time.isoformat(),
                "end_time": e.end_time.isoformat(),
                "location": e.location,
            }
            for e in events
        ],
        habits=[
            {
                "id": h["habit"].id,
                "name": h["habit"].name,
                "current_streak": h["habit"].current_streak,
                "completed_today": h["completed_today"],
                "target_count": h["habit"].target_count,
            }
            for h in habits_data
        ],
    )


@router.get("/sessions", response_model=list[ChatSessionResponse])
async def get_sessions(
    current_user: CurrentUser,
    db: DbSession,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Get all chat sessions for the current user."""
    chat_service = ChatService(db)
    sessions = await chat_service.get_sessions(
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )
    return sessions


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_session(
    session_id: int,
    current_user: CurrentUser,
    db: DbSession,
):
    """Get a specific chat session with messages."""
    chat_service = ChatService(db)
    session = await chat_service.get_session(session_id, current_user.id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    
    return session


@router.post("/sessions", response_model=ChatSessionResponse)
async def create_session(
    current_user: CurrentUser,
    db: DbSession,
    title: str = "New Chat",
):
    """Create a new chat session."""
    chat_service = ChatService(db)
    session = await chat_service.create_session(
        user_id=current_user.id,
        title=title,
    )
    return session


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: int,
    current_user: CurrentUser,
    db: DbSession,
):
    """Delete a chat session."""
    chat_service = ChatService(db)
    session = await chat_service.get_session(session_id, current_user.id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    
    await chat_service.delete_session(session)


@router.post("", response_model=ChatMessageResponse)
async def send_message(
    data: ChatMessageCreate,
    current_user: CurrentUser,
    db: DbSession,
):
    """Send a message and get AI response (non-streaming)."""
    chat_service = ChatService(db)
    
    if data.session_id:
        session = await chat_service.get_session(data.session_id, current_user.id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )
    else:
        session = await chat_service.create_session(current_user.id)
        data.session_id = session.id
    
    await chat_service.add_user_message(
        user_id=current_user.id,
        content=data.content,
        session_id=data.session_id,
    )
    
    context = await build_agent_context(current_user.id, db)
    
    recent_messages = await chat_service.get_recent_messages(
        user_id=current_user.id,
        session_id=data.session_id,
        limit=10,
    )
    chat_history = [
        {"role": m.role, "content": m.content}
        for m in recent_messages[:-1]
    ]
    
    vector_store = await get_vector_store()
    orchestrator = OrchestratorAgent(vector_store=vector_store)
    
    response = await orchestrator.process_message(
        message=data.content,
        user_id=current_user.id,
        context=context,
        chat_history=chat_history,
    )
    
    assistant_message = await chat_service.add_assistant_message(
        user_id=current_user.id,
        content=response,
        session_id=data.session_id,
        agent_type="orchestrator",
    )
    
    if len(recent_messages) <= 1:
        await chat_service.generate_session_title(session, data.content)
    
    return assistant_message


@router.post("/stream")
async def stream_message(
    data: ChatMessageCreate,
    current_user: CurrentUser,
    db: DbSession,
):
    """Send a message and stream AI response."""
    chat_service = ChatService(db)
    
    if data.session_id:
        session = await chat_service.get_session(data.session_id, current_user.id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )
    else:
        session = await chat_service.create_session(current_user.id)
        data.session_id = session.id
    
    await chat_service.add_user_message(
        user_id=current_user.id,
        content=data.content,
        session_id=data.session_id,
    )
    
    context = await build_agent_context(current_user.id, db)
    
    recent_messages = await chat_service.get_recent_messages(
        user_id=current_user.id,
        session_id=data.session_id,
        limit=10,
    )
    chat_history = [
        {"role": m.role, "content": m.content}
        for m in recent_messages[:-1]
    ]
    
    vector_store = await get_vector_store()
    orchestrator = OrchestratorAgent(vector_store=vector_store)
    
    async def generate():
        full_response = ""
        
        yield f"data: {json.dumps({'type': 'start', 'session_id': data.session_id})}\n\n"
        
        async for chunk in orchestrator.stream_message(
            message=data.content,
            user_id=current_user.id,
            context=context,
            chat_history=chat_history,
        ):
            full_response += chunk
            yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
        
        assistant_message = await chat_service.add_assistant_message(
            user_id=current_user.id,
            content=full_response,
            session_id=data.session_id,
            agent_type="orchestrator",
        )
        
        if len(recent_messages) <= 1:
            await chat_service.generate_session_title(session, data.content)
        
        yield f"data: {json.dumps({'type': 'end', 'message_id': assistant_message.id})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get("/messages", response_model=list[ChatMessageResponse])
async def get_messages(
    current_user: CurrentUser,
    db: DbSession,
    session_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    """Get chat messages."""
    chat_service = ChatService(db)
    
    if session_id:
        messages = await chat_service.get_messages(
            session_id=session_id,
            user_id=current_user.id,
            limit=limit,
        )
    else:
        messages = await chat_service.get_recent_messages(
            user_id=current_user.id,
            limit=limit,
        )
    
    return messages
