#!/usr/bin/env python3
"""Ingest bundled travel guides into the knowledge base.

Usage, from the project root:

    python scripts/seed_knowledge.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.database import SessionLocal, engine, Base
from app.models.knowledge import KnowledgeDocument  # noqa: F401
from app.schemas.knowledge import KnowledgeDocumentCreate
from app.services.knowledge import KnowledgeService
from app.ai.rag.loader import DocumentLoader

KNOWLEDGE_DIR = ROOT / "data" / "knowledge"

SEED_FILES = [
    ("paris.md", "guide", "Paris"),
    ("tokyo.md", "guide", "Tokyo"),
    ("barcelona.md", "guide", "Barcelona"),
]


def main() -> None:
    Base.metadata.create_all(bind=engine)
    loader = DocumentLoader()
    db = SessionLocal()
    try:
        service = KnowledgeService(db)
        for filename, category, destination in SEED_FILES:
            path = KNOWLEDGE_DIR / filename
            loaded = loader.load_file(str(path), category=category, destination=destination)
            result = service.ingest_document(
                KnowledgeDocumentCreate(
                    title=loaded.title,
                    source=loaded.source,
                    category=loaded.category,
                    destination=loaded.destination,
                    content=loaded.content,
                )
            )
            print(f"{result['message']}: {result['title']} ({result['chunk_count']} chunks)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
