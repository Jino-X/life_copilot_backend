"""API v1 router."""
from fastapi import APIRouter

from app.api.v1 import auth, tasks, notes, habits, calendar, emails, chat, dashboard

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(dashboard.router)
api_router.include_router(tasks.router)
api_router.include_router(notes.router)
api_router.include_router(habits.router)
api_router.include_router(calendar.router)
api_router.include_router(emails.router)
api_router.include_router(chat.router)
