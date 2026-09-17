from typing import List, Optional

from .embeddings import EmbeddingError
from .interfaces import EmbeddingProvider, RetrievedChunk, VectorStore
from .vector_store import VectorStoreError


class RetrievalError(Exception):
    pass


class SemanticRetriever:
    def __init__(self, embeddings: EmbeddingProvider, vector_store: VectorStore):
        self.embeddings = embeddings
        self.vector_store = vector_store

    def retrieve(
        self,
        query: str,
        top_k: int,
        destination: Optional[str] = None,
    ) -> List[RetrievedChunk]:
        if not query or not query.strip():
            raise RetrievalError("Search query cannot be empty")

        try:
            vector = self.embeddings.embed_query(query.strip())
        except EmbeddingError as exc:
            raise RetrievalError(str(exc)) from exc

        try:
            return self.vector_store.search(vector, top_k=top_k, destination=destination)
        except VectorStoreError as exc:
            raise RetrievalError(str(exc)) from exc

    def format_context(self, chunks: List[RetrievedChunk]) -> str:
        if not chunks:
            return ""
        sections = []
        for chunk in chunks:
            header = f"[{chunk.title} | {chunk.category}"
            if chunk.destination:
                header += f" | {chunk.destination}"
            header += "]"
            sections.append(f"{header}\n{chunk.text}")
        return "\n\n".join(sections)
