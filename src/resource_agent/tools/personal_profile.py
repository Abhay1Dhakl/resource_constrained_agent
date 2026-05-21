import json
from typing import Dict, Any
from pathlib import Path
from resource_agent.tools.base import BaseTool, ToolResult

class PersonalProfileTool(BaseTool):
    name = "personal_profile_tool"
    description = ("This tool retrieves the user's personal profile, skills, projects, weak areas,"
                   "target role, and interview preparation focus")
    
    def __init__(self, profile_path: str = "data/personal_profile.json"):
        self.profile_path = Path(profile_path)
    
    def run(self, arguments: Dict[str, Any]) -> ToolResult:
        try:
            if not self.profile_path.exists():
                return ToolResult(
                    success = False,
                    tool_name = self.name,
                    error_message = f"Profile file not found: {self.profile_path}",
                )
            
            with open(self.profile_path, "r", encoding="utf-8") as file:
                profile = json.load(file)

            query = arguments.get("query", "")

            return ToolResult(
                success = True,
                tool_name=self.name,
                data={
                    "query": query,
                    "profile": profile
                }
            )

        except Exception as exc:
            return ToolResult(
                success= False,
                tool_name= self.name,
                error_message=str(exc)
            )
