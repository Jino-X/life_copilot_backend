"""Notes management endpoints."""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from app.api.v1.deps import CurrentUser, DbSession
from app.api.v1.schemas import NoteCreate, NoteResponse, NoteSearchRequest, NoteUpdate
from app.services.note_service import NoteService
from app.services.vector_store import get_vector_store

router = APIRouter(prefix="/notes", tags=["Notes"])


@router.get("", response_model=list[NoteResponse])
async def get_notes(
    current_user: CurrentUser,
    db: DbSession,
    folder: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get all notes for the current user."""
    note_service = NoteService(db)
    notes = await note_service.get_all(
        user_id=current_user.id,
        folder=folder,
        search=search,
        limit=limit,
        offset=offset,
    )
    return notes


@router.get("/folders", response_model=list[str])
async def get_folders(current_user: CurrentUser, db: DbSession):
    """Get all note folders for the current user."""
    note_service = NoteService(db)
    return await note_service.get_folders(current_user.id)


@router.get("/recent", response_model=list[NoteResponse])
async def get_recent_notes(
    current_user: CurrentUser,
    db: DbSession,
    limit: int = Query(5, ge=1, le=20),
):
    """Get recent notes."""
    note_service = NoteService(db)
    return await note_service.get_recent(current_user.id, limit)


@router.get("/{note_id}", response_model=NoteResponse)
async def get_note(note_id: int, current_user: CurrentUser, db: DbSession):
    """Get a specific note."""
    note_service = NoteService(db)
    note = await note_service.get_by_id(note_id, current_user.id)
    
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )
    
    return note


@router.post("", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(data: NoteCreate, current_user: CurrentUser, db: DbSession):
    """Create a new note."""
    note_service = NoteService(db)
    
    note = await note_service.create(
        user_id=current_user.id,
        title=data.title,
        content=data.content,
        folder=data.folder,
        tags=data.tags,
    )
    
    vector_store = await get_vector_store()
    embedding_id = await vector_store.add_document(
        content=f"{note.title}\n\n{note.content}",
        user_id=current_user.id,
        doc_type="note",
        doc_id=note.id,
        metadata={"folder": data.folder, "tags": data.tags},
    )
    await note_service.update_embedding_id(note, embedding_id)
    
    return note


@router.patch("/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: int,
    data: NoteUpdate,
    current_user: CurrentUser,
    db: DbSession,
):
    """Update a note."""
    note_service = NoteService(db)
    note = await note_service.get_by_id(note_id, current_user.id)
    
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )
    
    updated_note = await note_service.update(
        note=note,
        title=data.title,
        content=data.content,
        folder=data.folder,
        tags=data.tags,
    )
    
    if data.title is not None or data.content is not None:
        vector_store = await get_vector_store()
        if note.embedding_id:
            new_embedding_id = await vector_store.update_document(
                embedding_id=note.embedding_id,
                content=f"{updated_note.title}\n\n{updated_note.content}",
                user_id=current_user.id,
                doc_type="note",
                doc_id=note.id,
                metadata={"folder": updated_note.folder, "tags": updated_note.tags},
            )
            await note_service.update_embedding_id(updated_note, new_embedding_id)
    
    return updated_note


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(note_id: int, current_user: CurrentUser, db: DbSession):
    """Delete a note."""
    note_service = NoteService(db)
    note = await note_service.get_by_id(note_id, current_user.id)
    
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )
    
    if note.embedding_id:
        vector_store = await get_vector_store()
        await vector_store.delete_document(note.embedding_id)
    
    await note_service.delete(note)


@router.post("/search", response_model=list[NoteResponse])
async def semantic_search_notes(
    data: NoteSearchRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    """Search notes using semantic search."""
    vector_store = await get_vector_store()
    
    results = await vector_store.search(
        query=data.query,
        user_id=current_user.id,
        doc_type="note",
        k=data.limit,
    )
    
    note_service = NoteService(db)
    notes = []
    
    for result in results:
        note_id = result.get("metadata", {}).get("doc_id")
        if note_id:
            note = await note_service.get_by_id(note_id, current_user.id)
            if note:
                notes.append(note)
    
    return notes
