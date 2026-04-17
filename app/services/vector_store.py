"""Vector store service for semantic search and memory."""
import os
from typing import Optional
import uuid

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class VectorStoreService:
    """Service for vector storage and semantic search."""
    
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_EMBEDDING_MODEL,
        )
        self._store: Optional[FAISS] = None
        self._index_path = settings.FAISS_INDEX_PATH
    
    async def initialize(self) -> None:
        """Initialize or load the vector store."""
        if os.path.exists(f"{self._index_path}/index.faiss"):
            try:
                self._store = FAISS.load_local(
                    self._index_path,
                    self.embeddings,
                    allow_dangerous_deserialization=True,
                )
                logger.info("Loaded existing FAISS index")
            except Exception as e:
                logger.error(f"Failed to load FAISS index: {e}")
                self._store = None
        else:
            logger.info("No existing FAISS index found, will create on first add")
    
    async def add_document(
        self,
        content: str,
        user_id: int,
        doc_type: str,
        doc_id: int,
        metadata: Optional[dict] = None,
    ) -> str:
        """Add a document to the vector store."""
        embedding_id = str(uuid.uuid4())
        
        doc_metadata = {
            "user_id": user_id,
            "doc_type": doc_type,
            "doc_id": doc_id,
            "embedding_id": embedding_id,
            **(metadata or {}),
        }
        
        document = Document(
            page_content=content,
            metadata=doc_metadata,
        )
        
        if self._store is None:
            self._store = FAISS.from_documents([document], self.embeddings)
        else:
            self._store.add_documents([document])
        
        await self._save()
        return embedding_id
    
    async def search(
        self,
        query: str,
        user_id: int,
        doc_type: Optional[str] = None,
        k: int = 5,
    ) -> list[dict]:
        """Search for similar documents."""
        if self._store is None:
            return []
        
        results = self._store.similarity_search_with_score(query, k=k * 2)
        
        filtered_results = []
        for doc, score in results:
            if doc.metadata.get("user_id") != user_id:
                continue
            if doc_type and doc.metadata.get("doc_type") != doc_type:
                continue
            
            filtered_results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": float(score),
            })
            
            if len(filtered_results) >= k:
                break
        
        return filtered_results
    
    async def delete_document(self, embedding_id: str) -> bool:
        """Delete a document from the vector store."""
        if self._store is None:
            return False
        
        try:
            ids_to_delete = []
            for doc_id, doc in self._store.docstore._dict.items():
                if doc.metadata.get("embedding_id") == embedding_id:
                    ids_to_delete.append(doc_id)
            
            if ids_to_delete:
                self._store.delete(ids_to_delete)
                await self._save()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            return False
    
    async def update_document(
        self,
        embedding_id: str,
        content: str,
        user_id: int,
        doc_type: str,
        doc_id: int,
        metadata: Optional[dict] = None,
    ) -> str:
        """Update a document in the vector store."""
        await self.delete_document(embedding_id)
        return await self.add_document(content, user_id, doc_type, doc_id, metadata)
    
    async def get_user_memories(
        self,
        user_id: int,
        limit: int = 10,
    ) -> list[dict]:
        """Get recent memories for a user."""
        if self._store is None:
            return []
        
        memories = []
        for doc_id, doc in self._store.docstore._dict.items():
            if doc.metadata.get("user_id") == user_id:
                memories.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                })
                if len(memories) >= limit:
                    break
        
        return memories
    
    async def _save(self) -> None:
        """Save the vector store to disk."""
        if self._store is not None:
            os.makedirs(self._index_path, exist_ok=True)
            self._store.save_local(self._index_path)


_vector_store: Optional[VectorStoreService] = None


async def get_vector_store() -> VectorStoreService:
    """Get vector store service instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStoreService()
        await _vector_store.initialize()
    return _vector_store
