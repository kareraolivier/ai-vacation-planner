from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


class KnowledgeDocumentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Human-readable document title")
    source: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Stable identifier used for upserts and re-indexing (file path, URL, or slug)",
    )
    category: str = Field(
        ...,
        pattern="^(guide|tip|hidden_gem|faq|notes)$",
        description="Document type: guide, tip, hidden_gem, faq, or notes",
    )
    destination: Optional[str] = Field(
        None,
        max_length=100,
        description="Optional destination this document is about",
    )
    content: str = Field(..., min_length=1, description="Full document text to chunk and embed")


class KnowledgeDocumentResponse(BaseModel):
    id: UUID
    title: str
    source: str
    category: str
    destination: Optional[str] = None
    content_hash: str
    chunk_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    message: str

    class Config:
        from_attributes = True


class KnowledgeDocumentListItem(BaseModel):
    id: UUID
    title: str
    source: str
    category: str
    destination: Optional[str] = None
    content_hash: str
    chunk_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000, description="Natural-language search query")
    destination: Optional[str] = Field(None, max_length=100, description="Optional destination filter")
    top_k: Optional[int] = Field(None, ge=1, le=20, description="Number of chunks to return")


class KnowledgeSearchHit(BaseModel):
    document_id: UUID
    title: str
    source: str
    category: str
    destination: Optional[str] = None
    chunk_index: int
    text: str
    score: float


class KnowledgeSearchResponse(BaseModel):
    query: str
    results: List[KnowledgeSearchHit]
    message: str


class KnowledgeErrorResponse(BaseModel):
    detail: str
