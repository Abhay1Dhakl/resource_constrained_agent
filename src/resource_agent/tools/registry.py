from resource_agent.tools.personal_profile import PersonalProfileTool
from resource_agent.tools.code_execution import CodeExecutionTool
from resource_agent.tools.web_search import WebSearchTool

class ToolRegistry:
    def __init__(self):
        """Create and register the default tool instances for the agent."""
        personal_profile = PersonalProfileTool()
        web_search = WebSearchTool()
        code_execution = CodeExecutionTool()

        self.tools = {
            personal_profile.name: personal_profile,
            web_search.name: web_search,
            code_execution.name: code_execution,
        }

    def get_tool(self, tool_name: str):
        """Return a tool instance by name.

        Args:
            tool_name: Registry key for the requested tool.

        Returns:
            object | None: Matching tool instance when registered.
        """
        return self.tools.get(tool_name)

    def list_tools(self):
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
