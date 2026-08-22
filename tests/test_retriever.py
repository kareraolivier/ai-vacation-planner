from uuid import uuid4

import pytest

from app.schemas.knowledge import KnowledgeDocumentCreate
from app.services.knowledge import KnowledgeService
from app.ai.rag.embeddings import EmbeddingError, HashEmbeddingProvider
from app.ai.rag.retriever import RetrievalError, SemanticRetriever
from app.ai.rag.vector_store import InMemoryVectorStore


def test_retriever_returns_relevant_chunk():
    store = InMemoryVectorStore()
    embeddings = HashEmbeddingProvider(dimensions=32)
    retriever = SemanticRetriever(embeddings, store)
    from app.ai.rag.interfaces import EmbeddedChunk

    document_id = str(uuid4())
    store.upsert([
        EmbeddedChunk(
            text="Visit Musee d'Orsay when it rains in Paris",
            index=0,
            vector=embeddings.embed_query("Visit Musee d'Orsay when it rains in Paris"),
            document_id=document_id,
            title="Paris Guide",
            source="paris.md",
            category="guide",
            destination="Paris",
        )
    ])
    results = retriever.retrieve("rainy museum Paris", top_k=1)
    assert results
    assert "Orsay" in results[0].text


def test_retriever_wraps_embedding_failures():
    class BrokenEmbeddings(HashEmbeddingProvider):
        def embed_query(self, text):
            raise EmbeddingError("upstream embedding outage")

    retriever = SemanticRetriever(BrokenEmbeddings(dimensions=8), InMemoryVectorStore())
    with pytest.raises(RetrievalError, match="upstream embedding outage"):
        retriever.retrieve("Paris", top_k=3)


def test_retriever_rejects_empty_query():
    retriever = SemanticRetriever(HashEmbeddingProvider(dimensions=8), InMemoryVectorStore())
    with pytest.raises(RetrievalError):
        retriever.retrieve("   ", top_k=3)


def test_knowledge_ingest_and_search_roundtrip(db_session):
    embeddings = HashEmbeddingProvider(dimensions=32)
    store = InMemoryVectorStore()
    service = KnowledgeService(
        db_session,
        embeddings=embeddings,
        vector_store=store,
        retriever=SemanticRetriever(embeddings, store),
    )
    created = service.ingest_document(
        KnowledgeDocumentCreate(
            title="Paris Guide",
            source="seed://paris",
            category="guide",
            destination="Paris",
            content="The covered passages are the best rainy-day walk in Paris. Try Galerie Vivienne.",
        )
    )
    assert created["chunk_count"] >= 1

    skipped = service.ingest_document(
        KnowledgeDocumentCreate(
            title="Paris Guide",
            source="seed://paris",
            category="guide",
            destination="Paris",
            content="The covered passages are the best rainy-day walk in Paris. Try Galerie Vivienne.",
        )
    )
    assert skipped["message"] == "Document already indexed"

    updated = service.ingest_document(
        KnowledgeDocumentCreate(
            title="Paris Guide",
            source="seed://paris",
            category="guide",
            destination="Paris",
            content="Canal Saint-Martin is a quieter evening picnic spot than the Notre-Dame riverfront.",
        )
    )
    assert updated["message"] == "Document re-indexed successfully"

    hits = service.search("Canal picnic Paris", destination="Paris", top_k=3)
    assert hits
    assert any("Canal" in hit.text for hit in hits)
