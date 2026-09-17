from typing import List, Optional
from sqlalchemy.orm import Session
from .base import BaseRepository
from ..models.knowledge import KnowledgeDocument
from uuid import UUID


class KnowledgeRepository(BaseRepository[KnowledgeDocument]):
    def __init__(self, db: Session):
        super().__init__(KnowledgeDocument, db)

    def get_by_source(self, source: str) -> Optional[KnowledgeDocument]:
        return self.get_by(source=source)

    def list_documents(
        self,
        skip: int = 0,
        limit: int = 100,
        destination: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[KnowledgeDocument]:
        query = self.db.query(KnowledgeDocument)
        if destination:
            query = query.filter(KnowledgeDocument.destination == destination)
        if category:
            query = query.filter(KnowledgeDocument.category == category)
        return query.offset(skip).limit(limit).all()

    def delete_document(self, document_id: UUID) -> bool:
        return self.delete(document_id)
