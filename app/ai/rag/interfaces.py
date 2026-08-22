from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from uuid import UUID


@dataclass
class LoadedDocument:
    title: str
    source: str
    category: str
    content: str
    destination: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TextChunk:
    text: str
    index: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EmbeddedChunk:
    text: str
    index: int
    vector: List[float]
    document_id: str
    title: str
    source: str
    category: str
    destination: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievedChunk:
    document_id: UUID
    title: str
    source: str
    category: str
    destination: Optional[str]
    chunk_index: int
    text: str
    score: float


class EmbeddingProvider(ABC):
    @property
    @abstractmethod
    def dimensions(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError

    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        raise NotImplementedError


class VectorStore(ABC):
    @abstractmethod
    def upsert(self, chunks: List[EmbeddedChunk]) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete_by_document_id(self, document_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def search(
        self,
        query_vector: List[float],
        top_k: int,
        destination: Optional[str] = None,
    ) -> List[RetrievedChunk]:
        raise NotImplementedError
