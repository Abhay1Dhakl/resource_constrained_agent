from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class ToolResult(BaseModel):
    success: bool
    tool_name: str
    data: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None

    def to_observation(self) -> Dict[str, Any]:
        """Convert the tool result into the agent observation schema.

        Returns:
            Dict[str, Any]: Observation payload stored in agent state.
        """
        return {
            "success": self.success,
            "tool_name": self.tool_name,
            "data": self.data,
            "error": self.error_message,
        }


class BaseTool(ABC):
    name: str
    description: str

    @abstractmethod
    def run(self, arguments: Dict[str, Any]) -> ToolResult:
        """Execute the tool with the provided arguments.

        Args:
            arguments: Structured input payload for the tool.

        Returns:
            ToolResult: Normalized tool execution result.
        """
        pass
