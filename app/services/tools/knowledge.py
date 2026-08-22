from typing import Optional

from pydantic import BaseModel, Field

from ..knowledge import KnowledgeService
from ..rag.retriever import RetrievalError
from .base import AgentTool, ToolResult


class KnowledgeToolInput(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000, description="What travel knowledge to retrieve")
    destination: Optional[str] = Field(None, max_length=100, description="Optional destination filter")
    top_k: int = Field(5, ge=1, le=20, description="Number of knowledge chunks to retrieve")


class KnowledgeTool(AgentTool):
    name = "search_travel_knowledge"
    description = (
        "Search the travel knowledge base for guides, local tips, hidden gems, FAQs, and destination notes. "
        "Use for destination advice that should be grounded in stored travel content."
    )
    args_schema = KnowledgeToolInput

    def __init__(self, knowledge_service: KnowledgeService):
        self.knowledge_service = knowledge_service

    def execute(self, params: KnowledgeToolInput) -> ToolResult:
        try:
            chunks = self.knowledge_service.search(
                query=params.query,
                destination=params.destination,
                top_k=params.top_k,
            )
        except RetrievalError as exc:
            return ToolResult(success=False, error=str(exc))

        return ToolResult(
            success=True,
            data={
                "results": [
                    {
                        "title": chunk.title,
                        "category": chunk.category,
                        "destination": chunk.destination,
                        "text": chunk.text,
                        "score": chunk.score,
                    }
                    for chunk in chunks
                ]
            },
        )
