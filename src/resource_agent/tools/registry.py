from resource_agent.tools.personal_profile import PersonalProfile

class ToolRegistry:
    def __init__(self):
        self.tools = {
            'personal_profile': PersonalProfile(),
            # 'web_search': WebSearch(),
            # 'code_execution': CodeExecution(),
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