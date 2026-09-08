import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, ValidationError

from ..providers.base import ProviderError

logger = logging.getLogger(__name__)


class ToolResult(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None


class AgentTool(ABC):
    name: str
    description: str
    args_schema: Type[BaseModel]

    @abstractmethod
    def execute(self, params: BaseModel) -> ToolResult:
        raise NotImplementedError

    def run(self, **kwargs) -> str:
        try:
            params = self.args_schema(**kwargs)
            result = self.execute(params)
        except ValidationError as exc:
            result = ToolResult(success=False, error=f"Invalid tool input: {exc}")
        except ProviderError as exc:
            logger.warning("Provider failure in tool %s: %s", self.name, exc)
            result = ToolResult(success=False, error=str(exc))
        except Exception as exc:
            logger.exception("Unexpected failure in tool %s", self.name)
            result = ToolResult(success=False, error=f"Tool '{self.name}' failed: {exc}")
        return result.model_dump_json()

    def as_langchain_tool(self) -> StructuredTool:
        return StructuredTool.from_function(
            name=self.name,
            description=self.description,
            func=self.run,
            args_schema=self.args_schema,
        )
