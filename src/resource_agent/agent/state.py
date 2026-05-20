from dataclasses import dataclass, field
from typing import Any

@dataclass
class AgentState:
    task: str
    status: str = "running"

    steps_completed: list[str] = field(default_factory=list)
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    replanning_events: list[str] = field(default_factory=list)

    final_answer: str = ""
    stop_reason: str = ""