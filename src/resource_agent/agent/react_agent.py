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


                tool_result = self._run_tool(
                    tool_name=action,
                    tool_input=action_input,
                )

                normalized_result = self._normalize_tool_result(
                    tool_name=action,
                    result=tool_result,
                )

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

    def _run_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Any:
        """Run a named tool through the registry abstraction.

        Args:
            tool_name: Registry name of the tool to execute.
            tool_input: Structured payload passed to the tool.

        Returns:
            Any: Raw tool response before normalization.
        """

        if hasattr(self.tools, "run_tool"):
            return self.tools.run_tool(tool_name, tool_input)

        if hasattr(self.tools, "get_tool"):
            tool = self.tools.get_tool(tool_name)

            if tool is None:
                return {
                    "success": False,
                    "tool_name": tool_name,
                    "data": {},
                    "error": f"Tool '{tool_name}' not found",
                }

            return tool.run(tool_input)

        return {
            "success": False,
            "tool_name": tool_name,
            "data": {},
            "error": "ToolRegistry does not support run_tool or get_tool",
        }

    def _normalize_tool_result(
        self,
        tool_name: str,
        result: Any,
    ) -> Dict[str, Any]:
        """Convert a raw tool result into the agent observation format.

        Args:
            tool_name: Tool name to use when the result omits one.
            result: Raw value returned by the tool implementation.

        Returns:
            Dict[str, Any]: Normalized observation payload for agent state.
        """
        def to_observation(payload: Dict[str, Any]) -> Dict[str,Any]:
            """Map a raw tool payload into the standard observation schema.

            Args:
                payload: Raw dictionary returned by a tool implementation.

            Returns:
                Dict[str, Any]: Observation dictionary stored in agent state.
            """
            error = payload.get("error")
            if error is None:
                error = payload.get("error_message")
            return {
                "success": payload.get("success", False),
                "tool_name": payload.get("tool_name", tool_name),
                "data": payload.get("data", {}),
                "error": error,
            }
        if result is None:
            return {
                "success": False,
                "tool_name": tool_name,
                "data": {},
                "error": "Tool returned None",
            }

        if isinstance(result, dict):
            return to_observation(result)

        if hasattr(result, "model_dump"):
            dumped = result.model_dump()
            return to_observation(dumped)

        if hasattr(result, "dict"):
            dumped = result.dict()
            return to_observation(dumped)

        return {
            "success": False,
            "tool_name": tool_name,
            "data": {},
            "error": f"Unsupported tool result type: {type(result)}",
        }

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
    
