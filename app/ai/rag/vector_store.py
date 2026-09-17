import math
import uuid
from typing import List, Optional

from ...core.config import settings
from .interfaces import EmbeddedChunk, RetrievedChunk, VectorStore


class VectorStoreError(Exception):
    pass


def _cosine_similarity(left: List[float], right: List[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def _point_id(document_id: str, chunk_index: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{document_id}:{chunk_index}"))


def _to_retrieved(payload: dict, score: float) -> RetrievedChunk:
    return RetrievedChunk(
        document_id=uuid.UUID(str(payload["document_id"])),
        title=payload.get("title", ""),
        source=payload.get("source", ""),
        category=payload.get("category", ""),
        destination=payload.get("destination"),
        chunk_index=int(payload.get("chunk_index", 0)),
        text=payload.get("text", ""),
        score=float(score),
    )


class InMemoryVectorStore(VectorStore):
    """In-process cosine search used by tests and local development."""

    def __init__(self):
        self._points = {}

    def upsert(self, chunks: List[EmbeddedChunk]) -> None:
        for chunk in chunks:
            self._points[_point_id(chunk.document_id, chunk.index)] = {
                "vector": chunk.vector,
                "payload": {
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.index,
                    "text": chunk.text,
                    "title": chunk.title,
                    "source": chunk.source,
                    "category": chunk.category,
                    "destination": chunk.destination,
                },
            }

    def delete_by_document_id(self, document_id: str) -> None:
        to_delete = [
            key
            for key, point in self._points.items()
            if point["payload"]["document_id"] == document_id
        ]
        for key in to_delete:
            del self._points[key]

    def search(
        self,
        query_vector: List[float],
        top_k: int,
        destination: Optional[str] = None,
    ) -> List[RetrievedChunk]:
        scored = []
        for point in self._points.values():
            payload = point["payload"]
            if destination and (payload.get("destination") or "").lower() != destination.lower():
                continue
            score = _cosine_similarity(query_vector, point["vector"])
            scored.append(_to_retrieved(payload, score))
        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:top_k]


class QdrantVectorStore(VectorStore):
    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        collection: Optional[str] = None,
        dimensions: Optional[int] = None,
        timeout: Optional[float] = None,
    ):
        from qdrant_client import QdrantClient

        self._collection = collection or settings.QDRANT_COLLECTION
        self._dimensions = dimensions or settings.EMBEDDING_DIMENSIONS
        self._client = QdrantClient(
            url=url or settings.QDRANT_URL,
            api_key=api_key or settings.QDRANT_API_KEY or None,
            timeout=timeout or settings.QDRANT_TIMEOUT,
        )
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        from qdrant_client.models import Distance, VectorParams

        try:
            exists = self._client.collection_exists(self._collection)
        except Exception as exc:
            raise VectorStoreError(f"Unable to reach Qdrant: {exc}") from exc

        if not exists:
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(size=self._dimensions, distance=Distance.COSINE),
            )

    def upsert(self, chunks: List[EmbeddedChunk]) -> None:
        from qdrant_client.models import PointStruct

        if not chunks:
            return

        points = [
            PointStruct(
                id=_point_id(chunk.document_id, chunk.index),
                vector=chunk.vector,
                payload={
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.index,
                    "text": chunk.text,
                    "title": chunk.title,
                    "source": chunk.source,
                    "category": chunk.category,
                    "destination": chunk.destination,
                },
            )
            for chunk in chunks
        ]
        try:
            self._client.upsert(collection_name=self._collection, points=points)
        except Exception as exc:
            raise VectorStoreError(f"Failed to upsert vectors: {exc}") from exc

    def delete_by_document_id(self, document_id: str) -> None:
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        try:
            self._client.delete(
                collection_name=self._collection,
                points_selector=Filter(
                    must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
                ),
            )
        except Exception as exc:
            raise VectorStoreError(f"Failed to delete document vectors: {exc}") from exc

    def search(
        self,
        query_vector: List[float],
        top_k: int,
        destination: Optional[str] = None,
    ) -> List[RetrievedChunk]:
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        query_filter = None
        if destination:
            query_filter = Filter(
                must=[FieldCondition(key="destination", match=MatchValue(value=destination))]
            )

        try:
            if hasattr(self._client, "query_points"):
                response = self._client.query_points(
                    collection_name=self._collection,
                    query=query_vector,
                    limit=top_k,
                    query_filter=query_filter,
                    with_payload=True,
                )
                points = response.points
            else:
                points = self._client.search(
                    collection_name=self._collection,
                    query_vector=query_vector,
                    limit=top_k,
                    query_filter=query_filter,
                    with_payload=True,
                )
        except Exception as exc:
            raise VectorStoreError(f"Vector search failed: {exc}") from exc

        results = []
        for point in points:
            payload = point.payload or {}
            results.append(_to_retrieved(payload, getattr(point, "score", 0.0)))
        return results


_MEMORY_STORE = InMemoryVectorStore()


def get_vector_store() -> VectorStore:
    provider = (settings.VECTOR_STORE_PROVIDER or "qdrant").lower()
    if provider == "qdrant":
        return QdrantVectorStore()
    if provider in {"memory", "inmemory", "test"}:
        return _MEMORY_STORE
    raise VectorStoreError(f"Unsupported vector store provider: {settings.VECTOR_STORE_PROVIDER}")
