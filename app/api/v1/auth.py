"""Authentication endpoints."""
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from google_auth_oauthlib.flow import Flow

from app.api.v1.deps import CurrentUser, DbSession
from app.api.v1.schemas import (
    TokenRefresh,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
)
from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_token,
)
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["Authentication"])

GOOGLE_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, db: DbSession):
    """Register a new user."""
    user_service = UserService(db)
    
    existing = await user_service.get_by_email(data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    user = await user_service.create(
        email=data.email,
        full_name=data.full_name,
        password=data.password,
    )
    
    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, db: DbSession):
    """Login with email and password."""
    user_service = UserService(db)
    
    user = await user_service.authenticate(data.email, data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    
    await user_service.update_last_login(user)
    
    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(data: TokenRefresh, db: DbSession):
    """Refresh access token."""
    payload = verify_token(data.refresh_token, token_type="refresh")
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    
    user_id = payload.get("sub")
    user_service = UserService(db)
    user = await user_service.get_by_id(int(user_id))
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    
    access_token = create_access_token(subject=user.id)
    new_refresh_token = create_refresh_token(subject=user.id)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: CurrentUser):
    """Get current user information."""
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    data: UserUpdate,
    current_user: CurrentUser,
    db: DbSession,
):
    """Update current user information."""
    user_service = UserService(db)
    
    updated_user = await user_service.update_profile(
        user=current_user,
        full_name=data.full_name,
        avatar_url=data.avatar_url,
        timezone=data.timezone,
        preferences=data.preferences,
    )
    
    return updated_user


@router.get("/google")
async def google_auth(request: Request):
    """Initiate Google OAuth flow."""
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
            }
        },
        scopes=GOOGLE_SCOPES,
    )
    flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
    
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    
    return {"authorization_url": authorization_url}


@router.get("/google/callback")
async def google_callback(code: str, db: DbSession):
    """Handle Google OAuth callback."""
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
            }
        },
        scopes=GOOGLE_SCOPES,
    )
    flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
    
    flow.fetch_token(code=code)
    credentials = flow.credentials
    
    id_info = id_token.verify_oauth2_token(
        credentials.id_token,
        google_requests.Request(),
        settings.GOOGLE_CLIENT_ID,
    )
    
    google_id = id_info.get("sub")
    email = id_info.get("email")
    name = id_info.get("name", email.split("@")[0])
    picture = id_info.get("picture")
    
    user_service = UserService(db)
    
    user = await user_service.get_by_google_id(google_id)
    
    if not user:
        user = await user_service.get_by_email(email)
        if user:
            user.google_id = google_id
        else:
            user = await user_service.create(
                email=email,
                full_name=name,
                google_id=google_id,
                avatar_url=picture,
            )
    
    await user_service.update_google_tokens(
        user=user,
        access_token=credentials.token,
        refresh_token=credentials.refresh_token,
        expiry=credentials.expiry.replace(tzinfo=timezone.utc) if credentials.expiry else datetime.now(timezone.utc),
    )
    
    await user_service.update_last_login(user)
    
    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)
    
    frontend_url = settings.CORS_ORIGINS[0] if settings.CORS_ORIGINS else "http://localhost:3000"
    redirect_url = f"{frontend_url}/auth/callback?access_token={access_token}&refresh_token={refresh_token}"
    
    return RedirectResponse(url=redirect_url)
