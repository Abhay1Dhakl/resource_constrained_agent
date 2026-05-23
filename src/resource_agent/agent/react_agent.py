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
        self.llm = llm or build_llm_client()
        self.budget = BudgetManager(max_calls=max_calls, max_cost=max_cost)
        self.tools = ToolRegistry()
        self.max_steps = max_steps

    def run(self, task: str) -> AgentState:
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
                    state.mark_stopped(stop_message)
                    return state

                if status not in {"continue", "replan"}:
                    state.mark_failed(f"Invalid status from LLM: {status}")
                    return state
                if not action:
                    state.mark_failed("Planner did not return an action")
                    return state


                tool_result = self._run_tool(
                    tool_name=action,
                    tool_input=action_input,
                )

                normalized_result = self._normalize_tool_result(
                    tool_name=action,
                    result=tool_result,
                )

                state.add_step(
                    thought=thought,
                    action=action,
                    action_input=action_input,
                    observation=normalized_result,
                    progress_assessment=progress_assessment,
                )

                if status == "replan" and not normalized_result.get("success", False):
                    state.add_replanning_event(
                        step_number=state.steps[-1].step_number,
                        action=action,
                        reason=reason or normalized_result.get("error") or "Tool failed",
                        next_action=action,
                    )

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

    def budget_summary(self) -> Dict[str, Any]:
        return self.budget.summary()
    
