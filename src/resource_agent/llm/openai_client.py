import os
import json
from typing import Any, Dict, List, Optional

from resource_agent.config import load_env_file
from resource_agent.llm.schemas import AgentDecision


class OpenAILLMClient:
    """
    OpenAI-backed planner for the agent loop.

    This client does one job: given the task, prior steps, tool list, and
    remaining budget, return the next structured control decision.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        reasoning_effort: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> None:
        load_env_file()

        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
        self.reasoning_effort = reasoning_effort or os.getenv(
            "OPENAI_REASONING_EFFORT",
            "low",
        )

        if not self.api_key:
            raise ValueError(
                "OPENAI_API_KEY is not set. Add it to your environment or .env file."
            )

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError(
                "The 'openai' package is not installed. Run 'pip install -r requirements.txt'."
            ) from exc

        self.client = OpenAI(api_key=self.api_key)

    def generate(
        self,
        task: str,
        scratchpad: Optional[str] = None,
        budget_summary: Optional[Dict[str, Any]] = None,
        tools: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Return a structured planning decision.

        The model is asked to:
        - assess whether the latest step made progress
        - decide whether to continue, replan, stop, or finalize
        - choose one of the available tools when another tool step is needed
        """

        scratchpad = scratchpad or "No steps completed yet."
        budget_summary = budget_summary or {}
        tools = tools or []

        instructions = self._build_instructions(tools=tools)
        user_input = self._build_user_input(
            task=task,
            scratchpad=scratchpad,
            budget_summary=budget_summary,
        )

        response = self.client.responses.parse(
            model=self.model,
            instructions=instructions,
            input=user_input,
            reasoning={"effort": self.reasoning_effort},
            text_format=AgentDecision,
        )

        parsed = response.output_parsed
        if parsed is None:
            raise ValueError("OpenAI returned no parsed planner decision.")

        return {
            "content": self._normalize_decision(parsed),
            "cost": self._estimate_cost(response),
            "raw_usage": self._extract_usage(response),
            "model": self.model,
        }

    def _build_instructions(self, tools: List[Dict[str, str]]) -> str:
        tool_lines = []
        for tool in tools:
            tool_lines.append(f"- {tool['name']}: {tool['description']}")

        available_tools = "\n".join(tool_lines) if tool_lines else "- No tools provided"

        return (
            "You are a budget-constrained ReAct planning agent.\n"
            "Your job is to inspect the task, prior steps, and latest observation, then produce the next control decision.\n"
            "You must explicitly reflect after every observation.\n"
            "Available tools:\n"
            f"{available_tools}\n\n"
            "Rules:\n"
            "1. Only choose an action from the available tools.\n"
            "2. If the last step was useful, set status='continue' and choose the next tool action.\n"
            "3. If the last step failed but is recoverable, set status='replan' with a revised action_input.\n"
            "4. If enough information is already available, set status='final_answer' and provide final_answer.\n"
            "5. If the task is blocked or continuing would waste budget, set status='stop'.\n"
            "6. Keep action_input small and specific.\n"
            "7. If status is 'final_answer' or 'stop', action must be null.\n"
            "8. If status is 'continue' or 'replan', action must be a tool name and action_input must be an object.\n"
            "9. Be conservative with tool usage because the run has a strict call and cost budget."
        )

    def _build_user_input(
        self,
        task: str,
        scratchpad: str,
        budget_summary: Dict[str, Any],
    ) -> str:
        return (
            "Task:\n"
            f"{task}\n\n"
            "Current scratchpad:\n"
            f"{scratchpad}\n\n"
            "Budget summary:\n"
            f"{json.dumps(budget_summary, indent=2, sort_keys=True)}\n\n"
            "Return only the structured decision."
        )

    def _normalize_decision(self, payload: AgentDecision) -> Dict[str, Any]:
        return {
            "thought": payload.thought,
            "progress_assessment": payload.progress_assessment,
            "reason": payload.reason,
            "status": payload.status,
            "action": payload.action,
            "action_input": (
                payload.action_input.model_dump(exclude_none=True)
                if payload.action_input is not None
                else {}
            ),
            "final_answer": payload.final_answer,
        }

    def _extract_usage(self, response: Any) -> Dict[str, Any]:
        usage = getattr(response, "usage", None)
        if usage is None:
            return {}

        if hasattr(usage, "to_dict"):
            return usage.to_dict()

        if hasattr(usage, "model_dump"):
            return usage.model_dump()

        if isinstance(usage, dict):
            return usage

        return {}

    def _estimate_cost(self, response: Any) -> float:
        """
        Keep a simple, explicit estimate for the assignment budget loop.

        We use the currently documented short-context pricing for gpt-5.4-mini:
        input $0.375 / 1M tokens, output $2.25 / 1M tokens.
        If usage is unavailable, fall back to a tiny non-zero cost so the budget
        system still behaves deterministically during development.
        """

        usage = self._extract_usage(response)
        if not usage:
            return 0.002

        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)

        if self.model == "gpt-5.4-mini":
            input_rate = 0.375 / 1_000_000
            output_rate = 2.25 / 1_000_000
            return round((input_tokens * input_rate) + (output_tokens * output_rate), 6)

        # Safe fallback for now. We will make this model-aware in a later pass.
        return 0.005
