"""Email management endpoints."""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from app.api.v1.deps import CurrentUser, DbSession
from app.api.v1.schemas import (
    EmailReplyGenerateRequest,
    EmailReplyRequest,
    EmailResponse,
)
from app.agents.email_agent import EmailAgent
from app.services.email_service import EmailService

router = APIRouter(prefix="/emails", tags=["Emails"])


@router.get("", response_model=list[EmailResponse])
async def get_emails(
    current_user: CurrentUser,
    db: DbSession,
    category: Optional[str] = Query(None),
    is_read: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Get emails for the current user."""
    email_service = EmailService(db)
    emails = await email_service.get_all(
        user_id=current_user.id,
        category=category,
        is_read=is_read,
        limit=limit,
        offset=offset,
    )
    return emails


@router.get("/unread-count")
async def get_unread_count(current_user: CurrentUser, db: DbSession):
    """Get count of unread emails."""
    email_service = EmailService(db)
    count = await email_service.get_unread_count(current_user.id)
    return {"unread_count": count}


@router.get("/{email_id}", response_model=EmailResponse)
async def get_email(email_id: int, current_user: CurrentUser, db: DbSession):
    """Get a specific email."""
    email_service = EmailService(db)
    email = await email_service.get_by_id(email_id, current_user.id)
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found",
        )
    
    return email


@router.get("/{email_id}/content")
async def get_email_content(
    email_id: int,
    current_user: CurrentUser,
    db: DbSession,
):
    """Get full email content from Gmail."""
    if not current_user.google_access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gmail not connected",
        )
    
    email_service = EmailService(db)
    email = await email_service.get_by_id(email_id, current_user.id)
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found",
        )
    
    try:
        content = await email_service.get_email_content(current_user, email.gmail_id)
        return {"content": content}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch email content: {str(e)}",
        )


@router.post("/{email_id}/read")
async def mark_as_read(email_id: int, current_user: CurrentUser, db: DbSession):
    """Mark an email as read."""
    email_service = EmailService(db)
    email = await email_service.get_by_id(email_id, current_user.id)
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found",
        )
    
    await email_service.mark_as_read(email)
    return {"message": "Email marked as read"}


@router.post("/{email_id}/star")
async def toggle_star(email_id: int, current_user: CurrentUser, db: DbSession):
    """Toggle email star status."""
    email_service = EmailService(db)
    email = await email_service.get_by_id(email_id, current_user.id)
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found",
        )
    
    updated_email = await email_service.toggle_star(email)
    return {"is_starred": updated_email.is_starred}


@router.post("/{email_id}/archive")
async def archive_email(email_id: int, current_user: CurrentUser, db: DbSession):
    """Archive an email."""
    email_service = EmailService(db)
    email = await email_service.get_by_id(email_id, current_user.id)
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found",
        )
    
    await email_service.archive(email)
    return {"message": "Email archived"}


@router.post("/sync")
async def sync_emails(current_user: CurrentUser, db: DbSession):
    """Sync emails from Gmail."""
    if not current_user.google_access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gmail not connected. Please connect via Google OAuth.",
        )
    
    email_service = EmailService(db)
    
    try:
        synced_emails = await email_service.sync_from_gmail(current_user)
        
        email_agent = EmailAgent()
        for email in synced_emails[:10]:
            if not email.summary:
                try:
                    content = await email_service.get_email_content(
                        current_user, email.gmail_id
                    )
                    analysis = await email_agent.analyze_email(
                        subject=email.subject,
                        sender=email.sender,
                        content=content,
                    )
                    await email_service.update_ai_analysis(
                        email=email,
                        summary=analysis.get("summary"),
                        category=analysis.get("category"),
                        priority_score=analysis.get("priority_score"),
                    )
                except Exception:
                    pass
        
        return {
            "message": f"Synced {len(synced_emails)} emails",
            "emails_count": len(synced_emails),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync emails: {str(e)}",
        )


@router.post("/{email_id}/analyze")
async def analyze_email(email_id: int, current_user: CurrentUser, db: DbSession):
    """Analyze an email using AI."""
    if not current_user.google_access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gmail not connected",
        )
    
    email_service = EmailService(db)
    email = await email_service.get_by_id(email_id, current_user.id)
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found",
        )
    
    try:
        content = await email_service.get_email_content(current_user, email.gmail_id)
        
        email_agent = EmailAgent()
        analysis = await email_agent.analyze_email(
            subject=email.subject,
            sender=email.sender,
            content=content,
        )
        
        await email_service.update_ai_analysis(
            email=email,
            summary=analysis.get("summary"),
            category=analysis.get("category"),
            priority_score=analysis.get("priority_score"),
        )
        
        return analysis
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze email: {str(e)}",
        )


@router.post("/{email_id}/generate-reply")
async def generate_reply(
    email_id: int,
    data: EmailReplyGenerateRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    """Generate a reply for an email using AI."""
    if not current_user.google_access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gmail not connected",
        )
    
    email_service = EmailService(db)
    email = await email_service.get_by_id(email_id, current_user.id)
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found",
        )
    
    try:
        content = await email_service.get_email_content(current_user, email.gmail_id)
        
        email_agent = EmailAgent()
        reply = await email_agent.generate_reply(
            subject=email.subject,
            sender=email.sender,
            content=content,
            tone=data.tone,
            key_points=data.key_points,
            user_name=current_user.full_name,
        )
        
        await email_service.update_ai_analysis(email=email, suggested_reply=reply)
        
        return {"suggested_reply": reply}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate reply: {str(e)}",
        )


@router.post("/{email_id}/send-reply")
async def send_reply(
    email_id: int,
    data: EmailReplyRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    """Send a reply to an email."""
    if not current_user.google_access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gmail not connected",
        )
    
    email_service = EmailService(db)
    email = await email_service.get_by_id(email_id, current_user.id)
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found",
        )
    
    try:
        result = await email_service.send_reply(
            user=current_user,
            gmail_id=email.gmail_id,
            reply_text=data.reply_text,
        )
        return {"message": "Reply sent", "message_id": result.get("id")}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send reply: {str(e)}",
        )
