"""Email service for Gmail integration."""
import base64
from datetime import datetime, timezone
from email.mime.text import MIMEText
from typing import Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.email import Email
from app.models.user import User


class EmailService:
    """Service for email-related operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, email_id: int, user_id: int) -> Optional[Email]:
        """Get email by ID for a specific user."""
        result = await self.db.execute(
            select(Email).where(
                and_(Email.id == email_id, Email.user_id == user_id)
            )
        )
        return result.scalar_one_or_none()
    
    async def get_all(
        self,
        user_id: int,
        category: Optional[str] = None,
        is_read: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Email]:
        """Get emails for a user with optional filters."""
        query = select(Email).where(Email.user_id == user_id)
        
        if category:
            query = query.where(Email.category == category)
        if is_read is not None:
            query = query.where(Email.is_read == is_read)
        
        query = query.order_by(Email.received_at.desc())
        query = query.limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_unread_count(self, user_id: int) -> int:
        """Get count of unread emails."""
        from sqlalchemy import func
        result = await self.db.execute(
            select(func.count(Email.id)).where(
                and_(Email.user_id == user_id, Email.is_read == False)
            )
        )
        return result.scalar() or 0
    
    async def create(
        self,
        user_id: int,
        gmail_id: str,
        subject: str,
        sender: str,
        received_at: datetime,
        thread_id: Optional[str] = None,
        recipients: Optional[str] = None,
        snippet: Optional[str] = None,
        is_read: bool = False,
    ) -> Email:
        """Create a new email record."""
        email = Email(
            user_id=user_id,
            gmail_id=gmail_id,
            thread_id=thread_id,
            subject=subject,
            sender=sender,
            recipients=recipients,
            snippet=snippet,
            received_at=received_at,
            is_read=is_read,
        )
        
        self.db.add(email)
        await self.db.flush()
        await self.db.refresh(email)
        return email
    
    async def update_ai_analysis(
        self,
        email: Email,
        summary: Optional[str] = None,
        suggested_reply: Optional[str] = None,
        category: Optional[str] = None,
        priority_score: Optional[int] = None,
    ) -> Email:
        """Update email with AI analysis results."""
        if summary is not None:
            email.summary = summary
        if suggested_reply is not None:
            email.suggested_reply = suggested_reply
        if category is not None:
            email.category = category
        if priority_score is not None:
            email.priority_score = priority_score
        
        await self.db.flush()
        await self.db.refresh(email)
        return email
    
    async def mark_as_read(self, email: Email) -> None:
        """Mark email as read."""
        email.is_read = True
        await self.db.flush()
    
    async def toggle_star(self, email: Email) -> Email:
        """Toggle email star status."""
        email.is_starred = not email.is_starred
        await self.db.flush()
        await self.db.refresh(email)
        return email
    
    async def archive(self, email: Email) -> None:
        """Archive an email."""
        email.is_archived = True
        await self.db.flush()
    
    def _get_gmail_service(self, user: User):
        """Get Gmail API service."""
        if not user.google_access_token:
            raise ValueError("User has no Google credentials")
        
        credentials = Credentials(
            token=user.google_access_token,
            refresh_token=user.google_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
        )
        
        return build("gmail", "v1", credentials=credentials)
    
    async def sync_from_gmail(
        self,
        user: User,
        max_results: int = 20,
    ) -> list[Email]:
        """Sync recent emails from Gmail."""
        service = self._get_gmail_service(user)
        
        results = service.users().messages().list(
            userId="me",
            maxResults=max_results,
            labelIds=["INBOX"],
        ).execute()
        
        messages = results.get("messages", [])
        synced_emails = []
        
        for msg in messages:
            existing = await self._get_by_gmail_id(user.id, msg["id"])
            if existing:
                synced_emails.append(existing)
                continue
            
            msg_data = service.users().messages().get(
                userId="me",
                id=msg["id"],
                format="metadata",
                metadataHeaders=["From", "To", "Subject", "Date"],
            ).execute()
            
            headers = {h["name"]: h["value"] for h in msg_data.get("payload", {}).get("headers", [])}
            
            received_at = datetime.now(timezone.utc)
            if "Date" in headers:
                try:
                    from email.utils import parsedate_to_datetime
                    received_at = parsedate_to_datetime(headers["Date"])
                except Exception:
                    pass
            
            email = await self.create(
                user_id=user.id,
                gmail_id=msg["id"],
                thread_id=msg_data.get("threadId"),
                subject=headers.get("Subject", "(No Subject)"),
                sender=headers.get("From", "Unknown"),
                recipients=headers.get("To"),
                snippet=msg_data.get("snippet"),
                received_at=received_at,
                is_read="UNREAD" not in msg_data.get("labelIds", []),
            )
            synced_emails.append(email)
        
        return synced_emails
    
    async def _get_by_gmail_id(
        self,
        user_id: int,
        gmail_id: str,
    ) -> Optional[Email]:
        """Get email by Gmail message ID."""
        result = await self.db.execute(
            select(Email).where(
                and_(Email.user_id == user_id, Email.gmail_id == gmail_id)
            )
        )
        return result.scalar_one_or_none()
    
    async def get_email_content(self, user: User, gmail_id: str) -> str:
        """Get full email content from Gmail."""
        service = self._get_gmail_service(user)
        
        msg = service.users().messages().get(
            userId="me",
            id=gmail_id,
            format="full",
        ).execute()
        
        payload = msg.get("payload", {})
        
        def get_body(payload):
            if "body" in payload and payload["body"].get("data"):
                return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
            
            if "parts" in payload:
                for part in payload["parts"]:
                    if part.get("mimeType") == "text/plain":
                        if part.get("body", {}).get("data"):
                            return base64.urlsafe_b64decode(
                                part["body"]["data"]
                            ).decode("utf-8")
                    elif "parts" in part:
                        result = get_body(part)
                        if result:
                            return result
            
            return ""
        
        return get_body(payload)
    
    async def send_reply(
        self,
        user: User,
        gmail_id: str,
        reply_text: str,
    ) -> dict:
        """Send a reply to an email."""
        service = self._get_gmail_service(user)
        
        original = service.users().messages().get(
            userId="me",
            id=gmail_id,
            format="metadata",
            metadataHeaders=["From", "Subject", "Message-ID"],
        ).execute()
        
        headers = {h["name"]: h["value"] for h in original.get("payload", {}).get("headers", [])}
        
        message = MIMEText(reply_text)
        message["to"] = headers.get("From", "")
        message["subject"] = f"Re: {headers.get('Subject', '')}"
        message["In-Reply-To"] = headers.get("Message-ID", "")
        message["References"] = headers.get("Message-ID", "")
        
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        
        sent = service.users().messages().send(
            userId="me",
            body={
                "raw": raw,
                "threadId": original.get("threadId"),
            },
        ).execute()
        
        return sent
