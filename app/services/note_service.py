"""Note service for note management."""
from typing import Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.note import Note


class NoteService:
    """Service for note-related operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, note_id: int, user_id: int) -> Optional[Note]:
        """Get note by ID for a specific user."""
        result = await self.db.execute(
            select(Note).where(and_(Note.id == note_id, Note.user_id == user_id))
        )
        return result.scalar_one_or_none()
    
    async def get_all(
        self,
        user_id: int,
        folder: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Note]:
        """Get all notes for a user with optional filters."""
        query = select(Note).where(Note.user_id == user_id)
        
        if folder:
            query = query.where(Note.folder == folder)
        
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    Note.title.ilike(search_pattern),
                    Note.content.ilike(search_pattern),
                )
            )
        
        query = query.order_by(Note.updated_at.desc())
        query = query.limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_folders(self, user_id: int) -> list[str]:
        """Get all unique folders for a user."""
        result = await self.db.execute(
            select(Note.folder)
            .where(and_(Note.user_id == user_id, Note.folder.isnot(None)))
            .distinct()
        )
        return [row[0] for row in result.all() if row[0]]
    
    async def create(
        self,
        user_id: int,
        title: str,
        content: str,
        folder: Optional[str] = None,
        tags: Optional[str] = None,
    ) -> Note:
        """Create a new note."""
        note = Note(
            user_id=user_id,
            title=title,
            content=content,
            folder=folder,
            tags=tags,
        )
        
        self.db.add(note)
        await self.db.flush()
        await self.db.refresh(note)
        return note
    
    async def update(
        self,
        note: Note,
        title: Optional[str] = None,
        content: Optional[str] = None,
        folder: Optional[str] = None,
        tags: Optional[str] = None,
    ) -> Note:
        """Update a note."""
        if title is not None:
            note.title = title
        if content is not None:
            note.content = content
        if folder is not None:
            note.folder = folder
        if tags is not None:
            note.tags = tags
        
        await self.db.flush()
        await self.db.refresh(note)
        return note
    
    async def update_embedding_id(self, note: Note, embedding_id: str) -> None:
        """Update note's embedding ID for vector search."""
        note.embedding_id = embedding_id
        await self.db.flush()
    
    async def delete(self, note: Note) -> None:
        """Delete a note."""
        await self.db.delete(note)
        await self.db.flush()
    
    async def get_recent(self, user_id: int, limit: int = 5) -> list[Note]:
        """Get recent notes for a user."""
        result = await self.db.execute(
            select(Note)
            .where(Note.user_id == user_id)
            .order_by(Note.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
