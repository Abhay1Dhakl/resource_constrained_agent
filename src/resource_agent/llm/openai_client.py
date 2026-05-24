import os
import json
from typing import Any, Dict, List, Optional

from resource_agent.config import load_env_file
from resource_agent.llm.schemas import AgentDecision

FALLBACK_ESTIMATED_COST = 0.002

MODEL_PRICING_PER_MILLION = {
    "gpt-5.4-mini": {
        "input_per_million": 0.375,
        "output_per_million": 2.25,
    },
}

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
        """Initialize the OpenAI-backed planner client.

        Args:
            model: Optional model name override for planner calls.
            reasoning_effort: Optional reasoning effort override for Responses
                API requests.
            api_key: Optional API key override used for authentication.

        Raises:
            ValueError: Raised when required credentials or pricing settings are
                invalid.
            ImportError: Raised when the OpenAI SDK is not installed.
        """
        load_env_file()

        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
        self.reasoning_effort = reasoning_effort or os.getenv(
            "OPENAI_REASONING_EFFORT",
            "low",
        )

        self.input_cost_per_million = self._read_float_env(
            "OPENAI_INPUT_COST_PER_MILLION"
        )
        self.output_cost_per_million = self._read_float_env(
            "OPENAI_OUTPUT_COST_PER_MILLION"
        )

        if (self.input_cost_per_million is None) != (
            self.output_cost_per_million is None
        ):
            raise ValueError(
                "Set both OPENAI_INPUT_COST_PER_MILLION and "
                "OPENAI_OUTPUT_COST_PER_MILLION together."
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
        """Return the next structured planning decision from the model.

        Args:
            task: User task the planner is trying to solve.
            scratchpad: Serialized history of prior steps and observations.
            budget_summary: Current budget usage snapshot for the run.
            tools: Tool metadata exposed to the planner.

        Returns:
            Dict[str, Any]: Parsed planner decision plus cost and usage metadata.

        Raises:
            ValueError: Raised when the API response does not include a parsed
                planner decision.
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
        """Build the planner system instructions including available tools.

        Args:
            tools: Tool metadata available to the planner.

        Returns:
            str: Instruction string sent to the model.
        """
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
            "2. If the user explicitly asks to execute code or use a specific available tool, prefer honoring that request instead of answering from prior knowledge alone.\n"
            "3. If the last step was useful, set status='continue' and choose the next tool action.\n"
            "4. If the last step failed but is recoverable, set status='replan' with a revised action_input.\n"
            "5. If enough information is already available, set status='final_answer' and provide final_answer.\n"
            "6. If the task is blocked or continuing would waste budget, set status='stop'.\n"
            "7. Keep action_input small and specific.\n"
            "8. If status is 'final_answer' or 'stop', action must be null.\n"
            "9. If status is 'continue' or 'replan', action must be a tool name and action_input must be an object.\n"
            "10. If a user explicitly requires tool-based execution and the tool fails because the capability is unsupported, do not provide the requested execution result from general knowledge; explain the failure and stop or replan safely.\n"
            "11. Be conservative with tool usage because the run has a strict call and cost budget."
        )

    def _build_user_input(
        self,
        task: str,
        scratchpad: str,
        budget_summary: Dict[str, Any],
    ) -> str:
        """Build the user input payload for the planner call.

        Args:
            task: User task being solved.
            scratchpad: Serialized trace of previous agent steps.
            budget_summary: Current budget usage snapshot.

        Returns:
            str: Combined task and runtime context for the planner.
        """
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
        """Convert a validated planner decision model into a plain dict.

        Args:
            payload: Structured planner response validated by Pydantic.

        Returns:
            Dict[str, Any]: Plain dictionary consumed by the agent loop.
        """
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
        """Extract token usage details from an OpenAI response object.

        Args:
            response: Raw response returned by the OpenAI SDK.

        Returns:
            Dict[str, Any]: Usage payload when available, otherwise an empty
                dictionary.
        """
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
        """Estimate the planner call cost from token usage and pricing data.

        Args:
            response: Raw response returned by the OpenAI SDK.

        Returns:
            float: Estimated cost for the planner call.
        """
        usage = self._extract_usage(response)
        if not usage:
            return FALLBACK_ESTIMATED_COST

        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)

        pricing = self._resolve_pricing()
        if pricing is None:
            return FALLBACK_ESTIMATED_COST

        input_rate = pricing["input_per_million"] / 1_000_000
        output_rate = pricing["output_per_million"] / 1_000_000

        return round(
            (input_tokens * input_rate) + (output_tokens * output_rate),
            6,
        )
    
    def _read_float_env(self, key: str) -> Optional[float]:
        """Read an environment variable as a float when it is set.

        Args:
            key: Environment variable name to parse.

        Returns:
            Optional[float]: Parsed float value or `None` when unset.

        Raises:
            ValueError: Raised when the environment value cannot be parsed as a
                float.
        """
        value = os.getenv(key)

        if value is None or value == "":
            return None

        try:
            return float(value)
        except ValueError as exc:
            raise ValueError(f"{key} must be a float if set.") from exc


    def _resolve_pricing(self) -> Optional[Dict[str, float]]:
        """Resolve the pricing configuration for the current model.

        Returns:
            Optional[Dict[str, float]]: Input and output token pricing when
                available.
        """
        if (
            self.input_cost_per_million is not None
            and self.output_cost_per_million is not None
        ):
            return {
                "input_per_million": self.input_cost_per_million,
                "output_per_million": self.output_cost_per_million,
            }

        return MODEL_PRICING_PER_MILLION.get(self.model)
