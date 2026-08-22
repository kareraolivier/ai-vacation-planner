from typing import List, Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter

from ...core.config import settings
from .interfaces import LoadedDocument, TextChunk


class TextChunker:
    """Split travel documents into overlapping chunks for embedding."""

    def __init__(self, chunk_size: Optional[int] = None, chunk_overlap: Optional[int] = None):
        self.chunk_size = chunk_size or settings.RAG_CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.RAG_CHUNK_OVERLAP
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")

        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def split(self, document: LoadedDocument) -> List[TextChunk]:
        parts = [part.strip() for part in self._splitter.split_text(document.content) if part.strip()]
        if not parts:
            raise ValueError("Document produced no chunks")

        return [
            TextChunk(
                text=part,
                index=index,
                metadata={
                    "title": document.title,
                    "source": document.source,
                    "category": document.category,
                    "destination": document.destination,
                },
            )
            for index, part in enumerate(parts)
        ]
