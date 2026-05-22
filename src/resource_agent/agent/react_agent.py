from typing import Any, Dict

from resource_agent.agent.state import AgentState
from resource_agent.budget.budget_manager import BudgetManager
from resource_agent.llm.mock_client import MockLLMClient
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
    ):
        self.llm = MockLLMClient()
        self.budget = BudgetManager(max_calls=max_calls, max_cost=max_cost)
        self.tools = ToolRegistry()
        self.max_steps = max_steps

    def run(self, task: str) -> AgentState:
        state = AgentState(task=task)
        pending_replan: Dict[str, Any] | None = None
        failure_counts: Dict[str, int] = {}
        try:
            for _ in range(self.max_steps):
                if not self.budget.can_make_call():
                    state.mark_stopped("Budget exhausted before LLM call")
                    return state

                if pending_replan is not None:
                    decision = pending_replan
                    pending_replan = None
                else:
                    scratchpad = state.get_scratchpad()
                    llm_response = self.llm.generate(
                        task=task,
                        scratchpad=scratchpad,
                    )

                    self.budget.record_llm_call(llm_response.get("cost", 0.0))
                    decision = llm_response.get("content", {})

                thought = decision.get("thought")
                action = decision.get("action")
                action_input = decision.get("action_input", {})

                if not action:
                    state.mark_failed("LLM did not return an action")
                    return state

                if action == "final_answer":
                    final_answer = decision.get("final_answer", "No final answer provided.")
                    state.add_step(
                        thought=thought,
                        action=action,
                        action_input=None,
                        observation={
                            "success": True,
                            "tool_name": "final_answer",
                            "data": {
                                "answer": final_answer,
                            },
                            "error": None,
                        },
                    )
                    state.mark_completed(final_answer)
                    return state

                if not self.budget.can_make_call():
                    state.mark_stopped("Budget exhausted before tool call")
                    return state

                tool_result = self._run_tool(
                    tool_name=action,
                    tool_input=action_input,
                )

                normalized_result = self._normalize_tool_result(
                    tool_name=action,
                    result=tool_result,
                )

                self._record_tool_cost_if_supported()

                state.add_step(
                    thought=thought,
                    action=action,
                    action_input=action_input,
                    observation=normalized_result,
                )

                if not normalized_result.get("success", False):
                    error_text = normalized_result.get("error") or "Unknown error"
                    state.mark_failed(
                        f"Tool '{action}' failed: {error_text}"
                    )
                    return state

                ## Revise this properly later
                reflection = self._reflect_on_progress(action, action_input, normalized_result)

                if reflection["progress"]:
                    continue

                reason = reflection["reason"]
                signature = f"{action}|{reason}"
                failure_counts[signature] = failure_counts.get(signature, 0) + 1

                replan = reflection.get("replan")
                state.add_replanning_event(
                    step_number=len(state.steps),
                    action=action,
                    reason=reason,
                    next_action=replan["action"] if replan else None,
                )

                if replan and failure_counts[signature] == 1:
                    pending_replan = replan
                    continue

            state.mark_stopped(
                f"Maximum step limit reached: {self.max_steps}"
            )
            return state

        except Exception as e:
            state.mark_failed(str(e))
            return state

    def _run_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Any:
        """
        Runs a tool through ToolRegistry.

        Supports both:
        - registry.run_tool(name, input)
        - registry.get_tool(name).run(input)
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
        """
        Converts tool result into a normal dictionary.

        This supports:
        - plain dict
        - Pydantic model with model_dump()
        - older Pydantic model with dict()
        """
        def to_observation(payload: Dict[str, Any]) -> Dict[str,Any]:
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

    def _record_tool_cost_if_supported(self) -> None:
        """
        Records a tool call if BudgetManager supports it.

        This keeps the agent compatible with your current BudgetManager
        even if it only has record_llm_call().
        """

        if hasattr(self.budget, "record_tool_call"):
            self.budget.record_tool_call()

    def budget_summary(self) -> Dict[str, Any]:
        return self.budget.summary()
    

    def _reflect_on_progress(self, action: str, action_input: Dict[str, Any], obs: Dict[str, Any],) -> Dict[str, Any]:
        if obs.get("success"):
            return {
                "progress": True,
                "reason": f"{action} succeeded",
                "replan": None,
            }

        error_text = obs.get("error") or "unknown tool failure"

        if action == "web_search" and "Invalid topic" in error_text:
            fixed_input = dict(action_input or {})
            fixed_input["topic"] = "general"
            return {
                "progress": False,
                "reason": error_text,
                "replan": {
                    "thought": "Web search failed due to invalid topic. Retry with topic='general'.",
                    "action": "web_search",
                    "action_input": fixed_input,
                },
            }

        return {
            "progress": False,
            "reason": error_text,
            "replan": None,
        }
