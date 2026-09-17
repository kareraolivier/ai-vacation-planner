from uuid import uuid4

import pytest

from app.ai.rag.embeddings import HashEmbeddingProvider
from app.ai.rag.interfaces import EmbeddedChunk
from app.ai.rag.vector_store import InMemoryVectorStore, VectorStoreError, get_vector_store


def _chunk(text, index, document_id, destination="Paris"):
    return EmbeddedChunk(
        text=text,
        index=index,
        vector=HashEmbeddingProvider(dimensions=32).embed_query(text),
        document_id=document_id,
        title="Paris Guide",
        source="paris.md",
        category="guide",
        destination=destination,
    )


def test_memory_store_returns_closest_chunk():
    store = InMemoryVectorStore()
    document_id = str(uuid4())
    store.upsert([
        _chunk("Louvre is best on rainy days", 0, document_id),
        _chunk("Tokyo convenience stores are excellent", 1, str(uuid4()), destination="Tokyo"),
    ])
    query = HashEmbeddingProvider(dimensions=32).embed_query("Louvre rainy days")
    results = store.search(query, top_k=1)

    assert results
    assert "Louvre" in results[0].text


def test_memory_store_reindex_replaces_document_chunks():
    store = InMemoryVectorStore()
    document_id = str(uuid4())
    store.upsert([_chunk("old hidden gem text", 0, document_id)])
    store.delete_by_document_id(document_id)
    store.upsert([_chunk("new canal saint-martin picnic tip", 0, document_id)])

    query = HashEmbeddingProvider(dimensions=32).embed_query("canal picnic")
    results = store.search(query, top_k=3)
    assert all("old hidden gem" not in item.text for item in results)
    assert any("canal" in item.text for item in results)


def test_memory_store_destination_filter():
    store = InMemoryVectorStore()
    store.upsert([
        _chunk("Paris bakery walk", 0, str(uuid4()), destination="Paris"),
        _chunk("Tokyo bakery walk", 0, str(uuid4()), destination="Tokyo"),
    ])
    query = HashEmbeddingProvider(dimensions=32).embed_query("bakery walk")
    results = store.search(query, top_k=5, destination="Tokyo")
    assert results
    assert all(item.destination == "Tokyo" for item in results)


def test_vector_store_factory_uses_memory_in_tests():
    store = get_vector_store()
    assert isinstance(store, InMemoryVectorStore)


def test_qdrant_error_is_wrapped(monkeypatch):
    from app.ai.rag.vector_store import QdrantVectorStore

    class Boom:
        def __init__(self, *args, **kwargs):
            pass

        def collection_exists(self, name):
            raise RuntimeError("connection refused")

    monkeypatch.setattr("qdrant_client.QdrantClient", Boom)
    with pytest.raises(VectorStoreError):
        QdrantVectorStore(url="http://localhost:6333", collection="test", dimensions=8)
