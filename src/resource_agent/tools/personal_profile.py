from copy import deepcopy
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
    
    def __init__(
        self,
        profile_path: str = "data/personal_profile.json",
        profile_data: Dict[str, Any] | None = None,
    ):
        """Configure the profile lookup tool.

        Args:
            profile_path: Absolute or project-relative path to the profile JSON
                file.
            profile_data: Optional in-memory profile payload that overrides the
                file-based profile. Useful for hosted or per-session demos.
        """
        path = Path(profile_path)
        self.profile_data = profile_data

        if path.is_absolute():
            self.profile_path = path
        else:
            self.profile_path = project_root() / path

    def run(self, arguments: Dict[str, Any]) -> ToolResult:
        """Load the profile data and optionally filter to one section.

        Args:
            arguments: Tool payload that may include `query` and `section`.

        Returns:
            ToolResult: Profile lookup result or validation error details.
        """
        try:
            if self.profile_data is None and not self.profile_path.exists():
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
                    "section": section,
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
        """Read the profile JSON file from disk.

        Returns:
            Dict[str, Any]: Parsed profile payload.
        """
        if self.profile_data is not None:
            if not isinstance(self.profile_data, dict):
                raise ValueError("Profile data must be a JSON object at the top level.")
            return deepcopy(self.profile_data)

        with self.profile_path.open("r", encoding="utf-8") as file:
            return json.load(file)
