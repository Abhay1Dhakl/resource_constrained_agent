from typing import Any, Dict

from resource_agent.budget.budget_manager import BudgetManager, BudgetExceededError
from resource_agent.tools.registry import ToolRegistry
from resource_agent.llm.mock_client import MockLLMClient
from resource_agent.agent.state import AgentState


class ReactAgent:
    """
    A simple resource-constrained ReAct agent.

    Flow:
    1. Receive user task
    2. Ask LLM which tool to use
    3. Check budget
    4. Execute selected tool
    5. Store observation
    6. Build final answer
    """

    def __init__(self):
        self.llm = MockLLMClient()
        self.budget = BudgetManager(max_calls=10, max_cost=0.20)
        self.tools = ToolRegistry()

    def run(self, task: str) -> AgentState:
        state = AgentState(task=task)

        try:
            # 1. Check budget before LLM call
            if not self.budget.can_make_call():
                state.status = "stopped"
                state.stop_reason = "Budget exhausted before execution"
                state.final_answer = (
                    "Sorry, the agent stopped before starting because "
                    "the budget was already exhausted."
                )
                return state

            # 2. Ask LLM for next action
            llm_response = self.llm.generate(task)

            # 3. Record LLM cost
            self.budget.record_llm_call(llm_response["cost"])

            decision = llm_response["content"]

            action = decision.get("action")
            action_input = decision.get("action_input", {})

            state.steps_completed.append("LLM generated an action decision.")
            state.steps_completed.append(f"Selected tool: {action}")

            # 4. Validate action
            if not action:
                state.status = "failed"
                state.stop_reason = "LLM did not return an action."
                state.final_answer = "The agent failed because no tool action was selected."
                return state

            tool = self.tools.get_tool(action)

            if tool is None:
                state.status = "failed"
                state.stop_reason = f"Unknown tool requested: {action}"
                state.final_answer = (
                    f"The agent failed because the requested tool "
                    f"'{action}' is not available."
                )
                return state

            # 5. Execute selected tool
            tool_result = tool.run(action_input)

            normalized_result = self._normalize_tool_result(tool_result)

            state.steps_completed.append(f"Executed tool: {action}")
            state.steps_completed.append(f"Tool input: {action_input}")
            state.tool_results.append(normalized_result)

            # 6. Build final answer
            state.final_answer = self._build_final_answer(
                tool_name=action,
                tool_result=normalized_result,
            )

            state.status = "completed"
            state.stop_reason = "Task completed within budget."

            return state

        except BudgetExceededError as error:
            state.status = "stopped"
            state.stop_reason = "Budget exceeded during execution"
            state.final_answer = (
                f"Sorry, the agent stopped because the budget was exceeded: {str(error)}"
            )
            return state

        except Exception as error:
            state.status = "failed"
            state.stop_reason = "Unexpected runtime error"
            state.final_answer = f"The agent failed due to an unexpected error: {str(error)}"
            return state

    def _normalize_tool_result(self, tool_result: Any) -> Dict[str, Any]:
        """
        Converts tool output into a normal dictionary.

        Supports:
        - plain dict
        - Pydantic model with model_dump()
        """

        if hasattr(tool_result, "model_dump"):
            normalized = tool_result.model_dump()
            if normalized.get("error_message") and "error" not in normalized:
                normalized["error"] = normalized["error_message"]
            return normalized

        if isinstance(tool_result, dict):
            if tool_result.get("error_message") and "error" not in tool_result:
                return {**tool_result, "error": tool_result["error_message"]}
            return tool_result

        return {
            "success": False,
            "error": "Tool returned unsupported result format.",
            "raw_result": str(tool_result),
        }

    def _build_final_answer(self, tool_name: str, tool_result: Dict[str, Any]) -> str:
        """
        Builds a generic final answer for any tool.

        Later, you can replace this with an LLM-based final response generator.
        """

        if not tool_result.get("success"):
            return (
                f"The tool '{tool_name}' failed with error: "
                f"{tool_result.get('error', 'Unknown error')}"
            )

        data = tool_result.get("data", {})

        if tool_name == "calculator":
            return f"The result of the calculation is: {data.get('result')}"

        if tool_name == "personal_profile":
            profile = data.get("profile", {})
            target_role = profile.get("target_role", "your target role")
            skills = profile.get("skills", {})
            projects = profile.get("projects", [])
            weak_areas = profile.get("weak_areas", [])

            return (
                f"Based on your personal profile, you are preparing for the "
                f"{target_role} role.\n\n"
                f"Your key skill areas are: {skills}.\n\n"
                f"Your main projects are: {projects}.\n\n"
                f"Your weak areas to improve are: {weak_areas}."
            )

        if tool_name == "web_search":
            answer = data.get("answer")
            sources = data.get("sources", [])

            source_lines = []

            for index, source in enumerate(sources, start=1):
                source_lines.append(
                    f"{index}. {source.get('title')}\n"
                    f"URL: {source.get('url')}\n"
                    f"Summary: {source.get('content')}"
                )

            return (
                "Web search completed.\n\n"
                f"Search answer:\n{answer if answer else 'No direct answer returned.'}\n\n"
                "Sources:\n"
                + "\n\n".join(source_lines)
            )

        if tool_name == "code_execution":
            stdout = data.get("stdout", "")
            stderr = data.get("stderr", "")
            return (
                "Code execution completed.\n\n"
                f"Output:\n{stdout}\n\n"
                f"Errors:\n{stderr if stderr else 'No errors.'}"
            )

        return f"Tool '{tool_name}' executed successfully. Result:\n\n{data}"

    def budget_summary(self) -> dict:
        return self.budget.summary()
