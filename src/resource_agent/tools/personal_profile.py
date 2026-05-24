import json
from typing import Dict, Any
from pathlib import Path
from resource_agent.tools.base import BaseTool, ToolResult
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from resource_agent.config import project_root

TIMEOUT_SECONDS = 3

ALLOWED_SECTIONS = {
    "name",
    "target_role",
    "target_companies",
    "skills",
    "projects",
    "weak_areas",
    "interview_focus",
}

class PersonalProfileTool(BaseTool):
    name = "personal_profile_tool"
    description = ("This tool retrieves the user's personal profile, skills, projects, weak areas,"
                   "target role, and interview preparation focus")
    
    def __init__(self, profile_path: str = "data/personal_profile.json"):
        path = Path(profile_path)

        if path.is_absolute():
            self.profile_path = path
        else:
            self.profile_path = project_root() / path

    def run(self, arguments: Dict[str, Any]) -> ToolResult:
        try:
            if not self.profile_path.exists():
                return ToolResult(
                    success = False,
                    tool_name = self.name,
                    error_message = f"Profile file not found: {self.profile_path}",
                )
            
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self._load_profile)
                profile = future.result(timeout=TIMEOUT_SECONDS)

            query = arguments.get("query", "")

            section = arguments.get("section")

            if section is not None and section not in ALLOWED_SECTIONS:
                return ToolResult(
                    success=False,
                    tool_name=self.name,
                    error_message=f"section must be one of: {sorted(ALLOWED_SECTIONS)}.",
                )

            selected_data = profile if section is None else {section: profile.get(section)}

            return ToolResult(
                success = True,
                tool_name=self.name,
                data={
                    "query": query,
                    "profile": profile,
                    "profile": selected_data,
                }
            )

        except TimeoutError:
            return ToolResult(
                success = False,
                tool_name = self.name,
                error_message = f"Profile loading timed out after {TIMEOUT_SECONDS} seconds",
            )
        except Exception as exc:
            return ToolResult(
                success= False,
                tool_name= self.name,
                error_message=str(exc)
            )

    def _load_profile(self) -> Dict[str, Any]:
        with self.profile_path.open("r", encoding="utf-8") as file:
            return json.load(file)