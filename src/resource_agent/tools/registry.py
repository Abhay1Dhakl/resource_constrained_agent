from resource_agent.tools.personal_profile import PersonalProfileTool
from resource_agent.tools.code_execution import CodeExecutionTool
from resource_agent.tools.web_search import WebSearchTool

class ToolRegistry:
    def __init__(self):
        personal_profile = PersonalProfileTool()
        web_search = WebSearchTool()
        code_execution = CodeExecutionTool()

        self.tools = {
            personal_profile.name: personal_profile,
            web_search.name: web_search,
            code_execution.name: code_execution,
        }

    def get_tool(self, tool_name: str):
        return self.tools.get(tool_name)

    def list_tools(self):
        return [
            {
                'name': tool.name,
                'description': tool.description
            }
            for tool in self.tools.values()
        ]