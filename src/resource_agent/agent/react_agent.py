import json
from typing import Any, Dict
from resource_agent.agent.state import AgentState
from resource_agent.budget.budget_manager import BudgetExceededError, BudgetManager
from resource_agent.llm import build_llm_client
from resource_agent.tools.registry import ToolRegistry


class ReactAgent:
    """
    Multi-step ReAct agent.

    Flow:
    User task
        -> LLM decides next action
        -> Agent checks budget
        -> ToolRegistry runs tool
        -> Observation is stored in AgentState
        -> LLM sees scratchpad
        -> Repeat until final_answer
    """

    def __init__(
        self,
        max_steps: int = 5,
        max_calls: int = 10,
        max_cost: float = 0.20,
        llm=None,
    ):
        """Initialize the agent runtime and supporting components.

        Args:
            max_steps: Maximum planner-tool iterations allowed in one run.
            max_calls: Maximum number of LLM calls permitted by budget.
            max_cost: Maximum cumulative LLM spend permitted by budget.
            llm: Optional injected LLM client used for testing or customization.
        """
        self.llm = llm or build_llm_client()
        self.budget = BudgetManager(max_calls=max_calls, max_cost=max_cost)
        self.tools = ToolRegistry()
        self.max_steps = max_steps

    def run(self, task: str) -> AgentState:
        """Run the ReAct loop until completion, stop, or failure.

        Args:
            task: User task the planner should solve.

        Returns:
            AgentState: Final state containing the full execution trace.
        """
        state = AgentState(task=task)
        try:
            for _ in range(self.max_steps):
                if not self.budget.can_make_call():
                    state.mark_stopped("Budget exhausted before LLM call")
                    return state

                scratchpad = state.get_scratchpad()
                llm_response = self.llm.generate(
                    task=task,
                    scratchpad=scratchpad,
                    budget_summary=self.budget.summary(),
                    tools=self.tools.list_tools(),
                )

                try:
                    self.budget.record_llm_call(llm_response.get("cost", 0.0))
                except BudgetExceededError as ex:
                    state.mark_stopped(str(ex))
                    return state
                
                decision = llm_response.get("content", {})

                thought = decision.get("thought")
                action = decision.get("action")
                action_input = decision.get("action_input") or {}
                status = decision.get("status")
                reason = decision.get("reason", "")
                progress_assessment = decision.get("progress_assessment")

                if status == "final_answer":
                    final_answer = (
                        decision.get("final_answer")
                        or reason
                        or "No final answer provided."
                    )
                    state.add_step(
                        thought=thought,
                        action=action,
                        action_input=action_input,
                        observation={
                            "success": True,
                            "tool_name": "final_answer",
                            "data": {
                                "answer": final_answer,
                            },
                            "error": None,
                        },
                        progress_assessment=progress_assessment,
                    )
                    state.mark_completed(final_answer)
                    return state
                
                if status == "stop":
                    stop_message = (
                        decision.get("final_answer")
                        or reason
                        or "Planner chose to stop"
                    )
                    state.add_step(
                            thought=thought,
                            action=None,
                            action_input=action_input,
                            observation={
                                "success": True,
                                "tool_name": "planner_stop",
                                "data": {
                                    "reason": stop_message,
                                },
                                "error": None,
                            },
                            progress_assessment=progress_assessment,
                        )
                    state.mark_stopped(stop_message)
                    return state

                if status not in {"continue", "replan"}:
                    state.mark_failed(f"Invalid status from LLM: {status}")
                    return state
                if not action:
                    state.mark_failed("Planner did not return an action")
                    return state
                
                action_signature = self._action_signature(action, action_input)

                if status == "replan" and state.has_failed_attempt(action_signature):
                    blocked_observation = {
                        "success": False,
                        "tool_name": action,
                        "data": {},
                        "error": (
                            "Blocked repeated replanning attempt: the same action and "
                            "action_input already failed earlier."
                        ),
                    }

                    state.add_step(
                        thought=thought,
                        action=action,
                        action_input=action_input,
                        observation=blocked_observation,
                        progress_assessment="blocked",
                    )

                    state.add_replanning_event(
                        step_number=state.steps[-1].step_number,
                        action=action,
                        reason=reason or "Planner repeated an earlier failed attempt.",
                        next_action=action,
                        successful=False,
                    )

                    state.mark_stopped("Repeated replanning attempt was blocked to prevent a loop.")
                    return state


                tool_result = self.tools.run_tool(action, action_input)
                normalized_result = tool_result.to_observation()

                if not normalized_result.get("success", False):
                    state.remember_failed_action(action_signature)

                state.add_step(
                    thought=thought,
                    action=action,
                    action_input=action_input,
                    observation=normalized_result,
                    progress_assessment=progress_assessment,
                )

                if status == "replan":
                    previous_action = action
                    if len(state.steps) > 1 and state.steps[-2].action:
                        previous_action = state.steps[-2].action

                    state.add_replanning_event(
                        step_number=state.steps[-1].step_number,
                        action=previous_action,
                        reason=reason or normalized_result.get("error") or "Planner revised approach",
                        next_action=action,
                        successful=normalized_result.get("success", False),
                    )

            state.mark_stopped(
                f"Maximum step limit reached: {self.max_steps}"
            )
            return state

        except Exception as e:
            state.mark_failed(str(e))
            return state

    def _action_signature(self, action: str, action_input: Dict[str, Any]) -> str:
        """Build a stable signature for detecting repeated failed actions.

        Args:
            action: Tool name chosen by the planner.
            action_input: Structured payload passed to the tool.

        Returns:
            str: Deterministic signature of the action and input payload.
        """
        return f"{action}:{json.dumps(action_input or {}, sort_keys=True, ensure_ascii=True)}"

    def budget_summary(self) -> Dict[str, Any]:
        """Return the current budget summary for reporting."""
        return self.budget.summary()
    
