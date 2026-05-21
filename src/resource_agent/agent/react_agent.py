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

    def __init__(self, max_steps: int = 5):
        self.llm = MockLLMClient()
        self.budget = BudgetManager(max_calls=10, max_cost=0.20)
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
                    state.mark_failed(
                        f"Tool '{action}' failed: {normalized_result.get('error')}"
                    )
                    return state

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

        if result is None:
            return {
                "success": False,
                "tool_name": tool_name,
                "data": {},
                "error": "Tool returned None",
            }

        if isinstance(result, dict):
            return {
                "success": result.get("success", False),
                "tool_name": result.get("tool_name", tool_name),
                "data": result.get("data", {}),
                "error": result.get("error"),
            }

        if hasattr(result, "model_dump"):
            dumped = result.model_dump()
            return {
                "success": dumped.get("success", False),
                "tool_name": dumped.get("tool_name", tool_name),
                "data": dumped.get("data", {}),
                "error": dumped.get("error"),
            }

        if hasattr(result, "dict"):
            dumped = result.dict()
            return {
                "success": dumped.get("success", False),
                "tool_name": dumped.get("tool_name", tool_name),
                "data": dumped.get("data", {}),
                "error": dumped.get("error"),
            }

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