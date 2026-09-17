from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from ..core.database import get_db
from ..core.dependencies import get_current_user
from ..models.user import User
from ..schemas.knowledge import (
    KnowledgeDocumentCreate,
    KnowledgeDocumentListItem,
    KnowledgeDocumentResponse,
    KnowledgeErrorResponse,
    KnowledgeSearchHit,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)
from ..services.knowledge import KnowledgeService
from ..ai.rag.embeddings import EmbeddingError
from ..ai.rag.retriever import RetrievalError
from ..ai.rag.vector_store import VectorStoreError

router = APIRouter(prefix="/knowledge", tags=["Knowledge Base"])


def _map_provider_error(exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=str(exc),
    )


@router.post(
    "/documents",
    response_model=KnowledgeDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": KnowledgeErrorResponse, "description": "Invalid document payload"},
        401: {"model": KnowledgeErrorResponse, "description": "Missing or invalid token"},
        503: {"model": KnowledgeErrorResponse, "description": "Embedding or vector store unavailable"},
    },
    summary="Ingest a travel knowledge document",
)
def ingest_document(
    document: KnowledgeDocumentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = KnowledgeService(db)
    try:
        return service.ingest_document(document)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except (EmbeddingError, VectorStoreError) as exc:
        raise _map_provider_error(exc)


@router.get(
    "/documents",
    response_model=List[KnowledgeDocumentListItem],
    responses={401: {"model": KnowledgeErrorResponse, "description": "Missing or invalid token"}},
    summary="List knowledge-base documents",
)
def list_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    destination: Optional[str] = Query(None, description="Filter by destination"),
    category: Optional[str] = Query(None, pattern="^(guide|tip|hidden_gem|faq|notes)$"),
):
    service = KnowledgeService(db)
    return service.list_documents(
        skip=skip,
        limit=limit,
        destination=destination,
        category=category,
    )


@router.get(
    "/documents/{document_id}",
    response_model=KnowledgeDocumentListItem,
    responses={
        401: {"model": KnowledgeErrorResponse, "description": "Missing or invalid token"},
        404: {"model": KnowledgeErrorResponse, "description": "Document not found"},
    },
    summary="Get knowledge-base document metadata",
)
def get_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = KnowledgeService(db)
    document = service.get_document(document_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


@router.post(
    "/documents/{document_id}/reindex",
    response_model=KnowledgeDocumentResponse,
    responses={
        401: {"model": KnowledgeErrorResponse, "description": "Missing or invalid token"},
        404: {"model": KnowledgeErrorResponse, "description": "Document not found"},
        503: {"model": KnowledgeErrorResponse, "description": "Embedding or vector store unavailable"},
    },
    summary="Re-index an existing document from stored source content",
)
def reindex_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = KnowledgeService(db)
    try:
        result = service.reindex_document(document_id)
    except (EmbeddingError, VectorStoreError) as exc:
        raise _map_provider_error(exc)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return result


@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"model": KnowledgeErrorResponse, "description": "Missing or invalid token"},
        404: {"model": KnowledgeErrorResponse, "description": "Document not found"},
        503: {"model": KnowledgeErrorResponse, "description": "Vector store unavailable"},
    },
    summary="Delete a knowledge-base document and its vectors",
)
def delete_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = KnowledgeService(db)
    try:
        deleted = service.delete_document(document_id)
    except VectorStoreError as exc:
        raise _map_provider_error(exc)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")


@router.post(
    "/search",
    response_model=KnowledgeSearchResponse,
    responses={
        400: {"model": KnowledgeErrorResponse, "description": "Invalid search request"},
        401: {"model": KnowledgeErrorResponse, "description": "Missing or invalid token"},
        503: {"model": KnowledgeErrorResponse, "description": "Retrieval backend unavailable"},
    },
    summary="Semantically search the travel knowledge base",
)
def search_knowledge(
    request: KnowledgeSearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = KnowledgeService(db)
    try:
        results = service.search(
            query=request.query,
            destination=request.destination,
            top_k=request.top_k,
        )
    except RetrievalError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))

    return {
        "query": request.query,
        "results": [
            KnowledgeSearchHit(
                document_id=item.document_id,
                title=item.title,
                source=item.source,
                category=item.category,
                destination=item.destination,
                chunk_index=item.chunk_index,
                text=item.text,
                score=item.score,
            )
            for item in results
        ],
        "message": "Knowledge search completed",
    }
