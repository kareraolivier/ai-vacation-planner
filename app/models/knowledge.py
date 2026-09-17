import uuid
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from ..core.database import Base
from ..core.types import GUID


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    title = Column(String(255), nullable=False)
    source = Column(String(500), nullable=False, unique=True, index=True)
    category = Column(String(50), nullable=False, index=True)
    destination = Column(String(100), nullable=True, index=True)
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False, index=True)
    chunk_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
