from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel

class ToolResult(BaseModel):
    success: bool
    tool_name: str
    data: Dict[str, Any] = {}
    error_message: Optional[str] = None


class BaseTool(ABC):
    name: str
    description: str

    @abstractmethod
    def run(self, arguments: Dict[str, Any]) -> ToolResult:
        pass