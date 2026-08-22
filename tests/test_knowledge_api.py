from uuid import uuid4

from app.controllers import knowledge as knowledge_controller
from app.schemas.knowledge import KnowledgeDocumentCreate


class FakeKnowledgeService:
    def __init__(self, db=None):
        self.db = db

    def ingest_document(self, document: KnowledgeDocumentCreate):
        return {
            "id": uuid4(),
            "title": document.title,
            "source": document.source,
            "category": document.category,
            "destination": document.destination,
            "content_hash": "abc",
            "chunk_count": 2,
            "created_at": "2026-08-22T00:00:00",
            "updated_at": None,
            "message": "Document ingested successfully",
        }

    def search(self, query, destination=None, top_k=None):
        from app.ai.rag.interfaces import RetrievedChunk

        return [
            RetrievedChunk(
                document_id=uuid4(),
                title="Paris Guide",
                source="paris.md",
                category="guide",
                destination="Paris",
                chunk_index=0,
                text="Covered passages are ideal in the rain.",
                score=0.88,
            )
        ]


def test_knowledge_ingest_validation_error(auth_client):
    response = auth_client.post("/knowledge/documents", json={
        "title": "Paris",
        "source": "paris",
        "category": "not-a-category",
        "content": "hello",
    })
    assert response.status_code == 422


def test_knowledge_ingest_and_search_success(auth_client, monkeypatch):
    monkeypatch.setattr(knowledge_controller, "KnowledgeService", FakeKnowledgeService)

    ingest = auth_client.post("/knowledge/documents", json={
        "title": "Paris Guide",
        "source": "seed://paris",
        "category": "guide",
        "destination": "Paris",
        "content": "A short guide",
    })
    assert ingest.status_code == 201
    assert ingest.json()["message"] == "Document ingested successfully"

    search = auth_client.post("/knowledge/search", json={"query": "rainy Paris", "destination": "Paris"})
    assert search.status_code == 200
    assert search.json()["results"][0]["category"] == "guide"


def test_knowledge_search_requires_auth(client):
    response = client.post("/knowledge/search", json={"query": "Paris"})
    assert response.status_code in {401, 403}
