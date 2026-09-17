import hashlib
import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ..core.config import settings
from ..repositories.knowledge import KnowledgeRepository
from ..schemas.knowledge import KnowledgeDocumentCreate
from ..ai.rag.chunker import TextChunker
from ..ai.rag.embeddings import EmbeddingProvider, get_embedding_provider
from ..ai.rag.interfaces import EmbeddedChunk, LoadedDocument, RetrievedChunk, VectorStore
from ..ai.rag.loader import DocumentLoader
from ..ai.rag.retriever import RetrievalError, SemanticRetriever
from ..ai.rag.vector_store import VectorStoreError, get_vector_store

logger = logging.getLogger(__name__)


def hash_content(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class KnowledgeService:
    def __init__(
        self,
        db: Session,
        loader: Optional[DocumentLoader] = None,
        chunker: Optional[TextChunker] = None,
        embeddings: Optional[EmbeddingProvider] = None,
        vector_store: Optional[VectorStore] = None,
        retriever: Optional[SemanticRetriever] = None,
    ):
        self.repo = KnowledgeRepository(db)
        self.loader = loader or DocumentLoader()
        self.chunker = chunker or TextChunker()
        self._embeddings = embeddings
        self._vector_store = vector_store
        self._retriever = retriever

    @property
    def embeddings(self) -> EmbeddingProvider:
        if self._embeddings is None:
            self._embeddings = get_embedding_provider()
        return self._embeddings

    @property
    def vector_store(self) -> VectorStore:
        if self._vector_store is None:
            self._vector_store = get_vector_store()
        return self._vector_store

    @property
    def retriever(self) -> SemanticRetriever:
        if self._retriever is None:
            self._retriever = SemanticRetriever(self.embeddings, self.vector_store)
        return self._retriever

    def ingest_document(self, data: KnowledgeDocumentCreate) -> dict:
        loaded = self.loader.load(
            title=data.title,
            content=data.content,
            source=data.source,
            category=data.category,
            destination=data.destination.title() if data.destination else None,
        )
        content_hash = hash_content(loaded.content)
        existing = self.repo.get_by_source(loaded.source)

        if existing and existing.content_hash == content_hash:
            return self._to_response(existing, "Document already indexed")

        if existing:
            self._index_document(existing.id, loaded)
            updated = self.repo.update(
                existing.id,
                title=loaded.title,
                category=loaded.category,
                destination=loaded.destination,
                content=loaded.content,
                content_hash=content_hash,
                chunk_count=self._last_chunk_count,
            )
            return self._to_response(updated, "Document re-indexed successfully")

        document = self.repo.create(
            title=loaded.title,
            source=loaded.source,
            category=loaded.category,
            destination=loaded.destination,
            content=loaded.content,
            content_hash=content_hash,
            chunk_count=0,
        )
        try:
            self._index_document(document.id, loaded)
            document = self.repo.update(document.id, chunk_count=self._last_chunk_count)
        except Exception:
            self.repo.delete(document.id)
            raise

        return self._to_response(document, "Document ingested successfully")

    def reindex_document(self, document_id: UUID) -> Optional[dict]:
        document = self.repo.get(document_id)
        if not document:
            return None

        loaded = self.loader.load(
            title=document.title,
            content=document.content,
            source=document.source,
            category=document.category,
            destination=document.destination,
        )
        self._index_document(document.id, loaded)
        updated = self.repo.update(
            document.id,
            content_hash=hash_content(loaded.content),
            chunk_count=self._last_chunk_count,
        )
        return self._to_response(updated, "Document re-indexed successfully")

    def list_documents(
        self,
        skip: int = 0,
        limit: int = 100,
        destination: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List:
        return self.repo.list_documents(
            skip=skip,
            limit=limit,
            destination=destination.title() if destination else None,
            category=category,
        )

    def get_document(self, document_id: UUID):
        return self.repo.get(document_id)

    def delete_document(self, document_id: UUID) -> bool:
        document = self.repo.get(document_id)
        if not document:
            return False
        try:
            self.vector_store.delete_by_document_id(str(document.id))
        except VectorStoreError as exc:
            logger.warning("Failed to delete vectors for %s: %s", document_id, exc)
            raise
        return self.repo.delete(document_id)

    def search(
        self,
        query: str,
        destination: Optional[str] = None,
        top_k: Optional[int] = None,
    ) -> List[RetrievedChunk]:
        try:
            return self.retriever.retrieve(
                query=query,
                top_k=top_k or settings.RAG_TOP_K,
                destination=destination.title() if destination else None,
            )
        except RetrievalError:
            raise

    def retrieve_context(
        self,
        query: str,
        destination: Optional[str] = None,
        top_k: Optional[int] = None,
    ) -> str:
        chunks = self.search(query=query, destination=destination, top_k=top_k)
        return self.retriever.format_context(chunks)

    def _index_document(self, document_id: UUID, loaded: LoadedDocument) -> None:
        chunks = self.chunker.split(loaded)
        vectors = self.embeddings.embed_documents([chunk.text for chunk in chunks])
        if len(vectors) != len(chunks):
            raise VectorStoreError("Embedding provider returned an unexpected vector count")

        self.vector_store.delete_by_document_id(str(document_id))
        embedded = [
            EmbeddedChunk(
                text=chunk.text,
                index=chunk.index,
                vector=vectors[index],
                document_id=str(document_id),
                title=loaded.title,
                source=loaded.source,
                category=loaded.category,
                destination=loaded.destination,
                metadata=chunk.metadata,
            )
            for index, chunk in enumerate(chunks)
        ]
        self.vector_store.upsert(embedded)
        self._last_chunk_count = len(embedded)

    def _to_response(self, document, message: str) -> dict:
        return {
            "id": document.id,
            "title": document.title,
            "source": document.source,
            "category": document.category,
            "destination": document.destination,
            "content_hash": document.content_hash,
            "chunk_count": document.chunk_count,
            "created_at": document.created_at,
            "updated_at": document.updated_at,
            "message": message,
        }
