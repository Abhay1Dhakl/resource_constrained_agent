from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AgentStep:
    """
    Stoers one ReAct step:
    Thought -> Action -> Observation
    """
    step_number: int
    thought: Optional[str] = None
    action: Optional[str] = None
    action_input: Optional[Dict[str, Any]] = None
    observation: Optional[Dict[str, Any]] = None


@dataclass
class AgentState:
    """
    Stores the state of the agent during execution."""
    task: str
    status: str = "running"

    steps: List[AgentStep] = field(default_factory=list)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    replanning_events: List[str] = field(default_factory=list)

    final_answer: Optional[str] = None
    stop_reason: Optional[str]  = None

    def add_step(self, thought: str, action: str, action_input: Dict[str, Any], observation: Dict[str, Any]) -> None:
        step_number = len(self.steps) + 1
        step = AgentStep(
            step_number=step_number,
            thought=thought,
            action=action,
            action_input=action_input,
            observation=observation,
        )
        self.steps.append(step)
    
    def get_scratchpad(self) -> str:
        """"
        COnverts previous steps into text so the LLM can see what already happeded
        """
        if not self.steps:
            return "No steps completed yet."
        
        scratchpad_parts = []
        for step in self.steps:
            scratchpad_parts.append(f"Step {step.step_number}:\n")

            if step.thought:
                scratchpad_parts.append(f"Thought: {step.thought}\n")

            if step.action:
                scratchpad_parts.append(f"Action: {step.action}\n")
            
            if step.action_input:
                scratchpad_parts.append(f"Action Input: {step.action_input}\n")
            
            if step.observation:
                scratchpad_parts.append(f"Observation: {step.observation}\n")
            
            scratchpad_parts.append("\n")

        return "".join(scratchpad_parts)
    
    def mark_completed(self, final_answer: str) -> None:
        self.status = "completed"
        self.final_answer = final_answer
        self.stop_reason = "Task completed successfully."
    
    def mark_failed(self, reason: str) -> None:
        self.status = "failed"
        self.final_answer = f"The agent failed because: {reason}"
        self.stop_reason = reason
    
    def mark_stopped(self, reason: str) -> None:
        self.status = "stopped"
        self.final_answer = f"The agent stopped because: {reason}"
        self.stop_reason = reason