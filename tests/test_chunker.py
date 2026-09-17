import pytest

from app.ai.rag.chunker import TextChunker
from app.ai.rag.interfaces import LoadedDocument
from app.ai.rag.loader import DocumentLoader


def test_chunker_splits_long_document_with_overlap():
    content = "Paris is compact. " * 80
    document = LoadedDocument(
        title="Paris",
        source="paris.md",
        category="guide",
        content=content,
        destination="Paris",
    )
    chunks = TextChunker(chunk_size=120, chunk_overlap=30).split(document)

    assert len(chunks) > 1
    assert chunks[0].index == 0
    assert chunks[1].index == 1
    assert all(chunk.metadata["destination"] == "Paris" for chunk in chunks)


def test_chunker_rejects_invalid_overlap():
    with pytest.raises(ValueError):
        TextChunker(chunk_size=50, chunk_overlap=50)


def test_loader_rejects_empty_content():
    loader = DocumentLoader()
    with pytest.raises(ValueError):
        loader.load(title="Paris", content="   ", source="x", category="guide")
