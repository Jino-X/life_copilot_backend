"""User service for authentication and user management."""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, verify_password
from app.models.user import User


class UserService:
    """Service for user-related operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()
    
    async def get_by_google_id(self, google_id: str) -> Optional[User]:
        """Get user by Google ID."""
        result = await self.db.execute(select(User).where(User.google_id == google_id))
        return result.scalar_one_or_none()
    
    async def create(
        self,
        email: str,
        full_name: str,
        password: Optional[str] = None,
        google_id: Optional[str] = None,
        avatar_url: Optional[str] = None,
    ) -> User:
        """Create a new user."""
        hashed_password = get_password_hash(password) if password else None
        
        user = User(
            email=email,
            full_name=full_name,
            hashed_password=hashed_password,
            google_id=google_id,
            avatar_url=avatar_url,
            is_verified=google_id is not None,
        )
        
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user
    
    async def authenticate(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password."""
        user = await self.get_by_email(email)
        if not user or not user.hashed_password:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user
    
    async def update_last_login(self, user: User) -> None:
        """Update user's last login timestamp."""
        user.last_login = datetime.now(timezone.utc)
        await self.db.flush()
    
    async def update_google_tokens(
        self,
        user: User,
        access_token: str,
        refresh_token: Optional[str],
        expiry: datetime,
    ) -> None:
        """Update user's Google OAuth tokens."""
        user.google_access_token = access_token
        if refresh_token:
            user.google_refresh_token = refresh_token
        user.google_token_expiry = expiry
        await self.db.flush()
    
    async def update_profile(
        self,
        user: User,
        full_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
        timezone: Optional[str] = None,
        preferences: Optional[str] = None,
    ) -> User:
        """Update user profile."""
        if full_name is not None:
            user.full_name = full_name
        if avatar_url is not None:
            user.avatar_url = avatar_url
        if timezone is not None:
            user.timezone = timezone
        if preferences is not None:
            user.preferences = preferences
        
        await self.db.flush()
        await self.db.refresh(user)
        return user
    
    async def change_password(self, user: User, new_password: str) -> None:
        """Change user's password."""
        user.hashed_password = get_password_hash(new_password)
        await self.db.flush()
    
    async def deactivate(self, user: User) -> None:
        """Deactivate a user account."""
        user.is_active = False
        await self.db.flush()
