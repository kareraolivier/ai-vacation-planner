import hashlib
import math
from typing import List, Optional

from ...core.config import settings
from .interfaces import EmbeddingProvider


class EmbeddingError(Exception):
    pass


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        dimensions: Optional[int] = None,
        base_url: Optional[str] = None,
    ):
        key = api_key or settings.EMBEDDING_API_KEY or settings.LLM_API_KEY
        if not key:
            raise EmbeddingError("Embedding API key is not configured")

        from langchain_openai import OpenAIEmbeddings

        self._dimensions = dimensions or settings.EMBEDDING_DIMENSIONS
        kwargs = {
            "api_key": key,
            "model": model or settings.EMBEDDING_MODEL,
        }
        url = base_url or settings.LLM_BASE_URL
        if url:
            kwargs["base_url"] = url
        if self._dimensions:
            kwargs["dimensions"] = self._dimensions
        self._client = OpenAIEmbeddings(**kwargs)

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        try:
            return self._client.embed_documents(texts)
        except Exception as exc:
            raise EmbeddingError(f"Failed to embed documents: {exc}") from exc

    def embed_query(self, text: str) -> List[float]:
        try:
            return self._client.embed_query(text)
        except Exception as exc:
            raise EmbeddingError(f"Failed to embed query: {exc}") from exc


class HashEmbeddingProvider(EmbeddingProvider):
    """Deterministic bag-of-words embeddings for tests and offline development."""

    def __init__(self, dimensions: Optional[int] = None):
        self._dimensions = dimensions or settings.EMBEDDING_DIMENSIONS

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> List[float]:
        vector = [0.0] * self._dimensions
        tokens = [token for token in text.lower().split() if token]
        if not tokens:
            return vector

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self._dimensions
            vector[index] += 1.0

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]


def get_embedding_provider() -> EmbeddingProvider:
    provider = (settings.EMBEDDING_PROVIDER or "openai").lower()
    if provider == "openai":
        return OpenAIEmbeddingProvider()
    if provider in {"hash", "memory", "test"}:
        return HashEmbeddingProvider()
    raise EmbeddingError(f"Unsupported embedding provider: {settings.EMBEDDING_PROVIDER}")
