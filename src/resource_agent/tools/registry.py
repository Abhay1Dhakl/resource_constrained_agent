from typing import Any

from resource_agent.tools.personal_profile import PersonalProfileTool
from resource_agent.tools.code_execution import CodeExecutionTool
from resource_agent.tools.web_search import WebSearchTool
from resource_agent.tools.base import BaseTool, ToolResult

class ToolRegistry:
    def __init__(
        self,
        personal_profile_tool: BaseTool | None = None,
        profile_data: dict[str, Any] | None = None,
    ):
        """Create and register the default tool instances for the agent.

        Args:
            personal_profile_tool: Optional fully constructed profile tool.
            profile_data: Optional in-memory profile payload passed to the
                default profile tool.
        """
        if personal_profile_tool is not None and profile_data is not None:
            raise ValueError(
                "Pass either personal_profile_tool or profile_data, not both."
            )

        personal_profile = personal_profile_tool or PersonalProfileTool(
            profile_data=profile_data
        )
        web_search = WebSearchTool()
        code_execution = CodeExecutionTool()

        self.tools: dict[str, BaseTool] = {
            personal_profile.name: personal_profile,
            web_search.name: web_search,
            code_execution.name: code_execution,
        }

    def get_tool(self, tool_name: str) -> BaseTool | None:
        """Return a tool instance by name.

        Args:
            tool_name: Registry key for the requested tool.

        Returns:
            BaseTool | None: Matching tool instance when registered.
        """
        return self.tools.get(tool_name)

    def run_tool(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult:
        """Run a registered tool and normalize unknown-tool failures.

        Args:
            tool_name: Registry key for the requested tool.
            arguments: Structured input payload passed to the tool.

        Returns:
            ToolResult: Tool execution result or unknown-tool error.
        """
        tool = self.get_tool(tool_name)

        if tool is None:
            return ToolResult(
                success=False,
                tool_name=tool_name,
                error_message=f"Tool '{tool_name}' not found",
            )

        return tool.run(arguments)

    def list_tools(self) -> list[dict[str, str]]:
        """Return tool metadata that can be shown to the planner.

        Returns:
            list[dict[str, str]]: Tool names and descriptions for the planner.
        """
        return [
            {
                'name': tool.name,
                'description': tool.description
            }
            for tool in self.tools.values()
        ]
