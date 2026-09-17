import json
from pathlib import Path
from typing import Optional

from .interfaces import LoadedDocument


class DocumentLoader:
    """Normalize raw travel documents from text, markdown, JSON, or files."""

    def load(
        self,
        title: str,
        content: str,
        source: str,
        category: str,
        destination: Optional[str] = None,
    ) -> LoadedDocument:
        normalized = (content or "").strip()
        if not normalized:
            raise ValueError("Document content cannot be empty")
        if not title.strip():
            raise ValueError("Document title cannot be empty")
        if not source.strip():
            raise ValueError("Document source cannot be empty")

        return LoadedDocument(
            title=title.strip(),
            source=source.strip(),
            category=category.strip(),
            content=normalized,
            destination=destination.strip() if destination else None,
        )

    def load_file(self, path: str, category: str, destination: Optional[str] = None) -> LoadedDocument:
        file_path = Path(path)
        if not file_path.exists():
            raise ValueError(f"Knowledge file not found: {path}")

        raw = file_path.read_text(encoding="utf-8")
        suffix = file_path.suffix.lower()

        if suffix == ".json":
            payload = json.loads(raw)
            return self.load(
                title=payload.get("title") or file_path.stem.replace("_", " ").title(),
                content=payload.get("content") or payload.get("text") or "",
                source=payload.get("source") or str(file_path),
                category=payload.get("category") or category,
                destination=payload.get("destination") or destination,
            )

        title = file_path.stem.replace("_", " ").title()
        if suffix == ".md":
            title = self._title_from_markdown(raw) or title

        return self.load(
            title=title,
            content=raw,
            source=str(file_path),
            category=category,
            destination=destination,
        )

    def _title_from_markdown(self, content: str) -> Optional[str]:
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                return stripped[2:].strip()
        return None
