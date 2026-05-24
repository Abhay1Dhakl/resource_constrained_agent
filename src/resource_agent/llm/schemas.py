from typing import Literal, Optional

from pydantic import BaseModel


class ActionInput(BaseModel):
    query: Optional[str] = None
    topic: Optional[str] = None
    max_results: Optional[int] = None
    code: Optional[str] = None
    language: Optional[str] = None
    timeout: Optional[int] = None
    section: Optional[str] = None


class AgentDecision(BaseModel):
    thought: str
    progress_assessment: Literal[
        "progress",
        "partial_progress",
        "no_progress",
        "blocked",
        "enough_information",
    ]
    reason: str
    status: Literal["continue", "replan", "final_answer", "stop"]
    action: Optional[str] = None
    action_input: Optional[ActionInput] = None
    final_answer: Optional[str] = None
