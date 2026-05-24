from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AgentStep:
    """Store one ReAct step in the agent execution trace.

    Args:
        step_number: Sequential index of the step in the run.
        thought: Planner reasoning captured before the tool action.
        action: Tool chosen by the planner for this step, if any.
        action_input: Structured input passed to the selected tool.
        observation: Normalized result returned by the tool execution.
        progress_assessment: Planner self-assessment of whether the step made
            progress.
    """
    step_number: int
    thought: Optional[str] = None
    action: Optional[str] = None
    action_input: Optional[Dict[str, Any]] = None
    observation: Optional[Dict[str, Any]] = None
    progress_assessment: Optional[str] = None


@dataclass
class AgentState:
    """Store the mutable state of an agent run from start to finish."""
    task: str
    status: str = "running"
    steps: List[AgentStep] = field(default_factory=list)
    replanning_events: List[Dict[str, Any]] = field(default_factory=list)
    failed_actions_signature: set[str] = field(default_factory=set)
    final_answer: Optional[str] = None
    stop_reason: Optional[str]  = None

    def add_step(
                self,
                thought: Optional[str],
                action: Optional[str],
                action_input: Optional[Dict[str, Any]],
                observation: Dict[str, Any],
                progress_assessment: Optional[str] = None,
            ) -> None:
        """Append a completed planner step to the execution trace.

        Args:
            thought: Planner reasoning for the step.
            action: Tool action chosen for the step.
            action_input: Input payload used for the selected tool.
            observation: Normalized tool result recorded for the step.
            progress_assessment: Planner self-assessment for the step.
        """
        step_number = len(self.steps) + 1
        step = AgentStep(
            step_number=step_number,
            thought=thought,
            action=action,
            action_input=action_input,
            observation=observation,
            progress_assessment=progress_assessment,
        )
        self.steps.append(step)
    
    def get_scratchpad(self) -> str:
        """Convert prior steps into planner-readable scratchpad text.

        Returns:
            str: Serialized execution trace used as LLM context.
        """
        if not self.steps:
            return "No steps completed yet."
        
        scratchpad_parts = []
        for step in self.steps:
            scratchpad_parts.append(f"Step {step.step_number}:\n")

            if step.thought:
                scratchpad_parts.append(f"Thought: {step.thought}\n")

            if step.progress_assessment:
                scratchpad_parts.append(f"Progress Assessment: {step.progress_assessment}\n" )

            if step.action:
                scratchpad_parts.append(f"Action: {step.action}\n")
            
            if step.action_input:
                scratchpad_parts.append(f"Action Input: {step.action_input}\n")
            
            if step.observation:
                scratchpad_parts.append(f"Observation: {step.observation}\n")
            
            scratchpad_parts.append("\n")

        return "".join(scratchpad_parts)
    
    def mark_completed(self, final_answer: str) -> None:
        """Mark the run as completed with a final answer.

        Args:
            final_answer: Final response produced by the agent.
        """
        self.status = "completed"
        self.final_answer = final_answer
        self.stop_reason = "Task completed successfully."
    
    def mark_failed(self, reason: str) -> None:
        """Mark the run as failed and store the failure reason.

        Args:
            reason: Failure message describing why the run ended.
        """
        self.status = "failed"
        self.final_answer = f"The agent failed because: {reason}"
        self.stop_reason = reason
    
    def mark_stopped(self, reason: str) -> None:
        """Mark the run as stopped without reaching a final answer.

        Args:
            reason: Message explaining why execution stopped.
        """
        self.status = "stopped"
        self.final_answer = f"The agent stopped because: {reason}"
        self.stop_reason = reason
    
    def add_replanning_event(self, step_number: int, action: str, reason: str, next_action: Optional[str], successful: bool) -> None:
        """Record a replanning event for later analysis.

        Args:
            step_number: Step number at which replanning occurred.
            action: Action that prompted or represented the replan.
            reason: Explanation for the replanning event.
            next_action: Revised action selected after replanning, if any.
            successful: Whether the replanned action succeeded.
        """
        self.replanning_events.append(
            {
                "step_number": step_number,
                "failed_action": action,
                "reason": reason,
                "next_action": next_action,
                "successful": successful,
            }
        )
    
    def remember_failed_action(self, action_signature: str) -> None:
        """Record an action signature that already failed.

        Args:
            action_signature: Stable representation of a failed action attempt.
        """
        self.failed_actions_signature.add(action_signature)
    
    def has_failed_attempt(self, action_signature: str) -> bool:
        """Return whether the same action signature has failed before.

        Args:
            action_signature: Stable representation of an action attempt.

        Returns:
            bool: `True` when the action previously failed.
        """
        return action_signature in self.failed_actions_signature
