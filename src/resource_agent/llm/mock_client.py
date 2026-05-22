from typing import Any, Dict, Optional


class MockLLMClient:
    """
    Mock LLM client for testing a multi-step ReAct agent.

    It returns structured decisions like:
    {
        "thought": "...",
        "action": "tool_name",
        "action_input": {...}
    }

    or:

    {
        "thought": "...",
        "action": "final_answer",
        "final_answer": "..."
    }
    """

    def generate(
        self,
        task: str,
        scratchpad: Optional[str] = None,
        budget_summary: Optional[Dict[str, Any]] = None,
        tools: Optional[list[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        scratchpad = scratchpad or ""

        content = self._decide_next_action(task, scratchpad)

        return {
            "content": content,
            "cost": 0.01,
        }

    def _decide_next_action(
        self,
        task: str,
        scratchpad: str,
    ) -> Dict[str, Any]:
        task_lower = task.lower()
        scratchpad_lower = scratchpad.lower()

        # --------------------------------------------------
        # Multi-step interview preparation flow
        # --------------------------------------------------
        if "interview" in task_lower or "cedar gate" in task_lower or "ai engineer" in task_lower:
            if "personal_profile" not in scratchpad_lower:
                return {
                    "thought": "I should first understand the user's profile, skills, projects, and weak areas.",
                    "action": "personal_profile",
                    "action_input": {
                        "query": "Get the user's profile, target role, skills, projects, weak areas, and interview focus."
                    },
                }

            if "web_search" not in scratchpad_lower:
                return {
                    "thought": "Now I should search for recent information about Cedar Gate and AI Engineer interview preparation.",
                    "action": "web_search",
                    "action_input": {
                        "query": "Cedar Gate Nepal AI Engineer interview preparation company overview"
                    },
                }

            if "code_execution" not in scratchpad_lower:
                return {
                    "thought": "Now I should run a small Python example related to a common coding interview pattern.",
                    "action": "code_execution",
                    "action_input": {
                        "code": (
                            "def two_sum(nums, target):\n"
                            "    seen = {}\n"
                            "    for i, num in enumerate(nums):\n"
                            "        diff = target - num\n"
                            "        if diff in seen:\n"
                            "            return [seen[diff], i]\n"
                            "        seen[num] = i\n"
                            "    return []\n\n"
                            "print(two_sum([2, 7, 11, 15], 9))"
                        )
                    },
                }

            return {
                "thought": "I have the user's profile, company information, and a coding example. I can now produce the final interview preparation answer.",
                "action": "final_answer",
                "final_answer": (
                    "Based on your profile and the available company/interview context, focus on: "
                    "Python fundamentals, OOP, ML basics, embeddings, RAG, prompt injection, SQL-agent safety, "
                    "and production-level LLM system design. Also practice coding patterns like HashMap, two pointers, "
                    "sliding window, sorting, and basic recursion. A good starter coding problem is Two Sum because it "
                    "tests HashMap lookup clearly."
                ),
            }

        # --------------------------------------------------
        # Direct personal profile query
        # --------------------------------------------------
        if "profile" in task_lower or "my skills" in task_lower or "my weak" in task_lower:
            if "personal_profile" not in scratchpad_lower:
                return {
                    "thought": "The user is asking about their own stored profile.",
                    "action": "personal_profile",
                    "action_input": {
                        "query": task
                    },
                }

            return {
                "thought": "The profile information has been retrieved. I can now answer.",
                "action": "final_answer",
                "final_answer": "I retrieved your profile information and used it to answer your request.",
            }

        # --------------------------------------------------
        # Direct web search query
        # --------------------------------------------------
        if "search" in task_lower or "latest" in task_lower or "recent" in task_lower:
            if "web_search" not in scratchpad_lower:
                return {
                    "thought": "The user needs recent or external information, so I should use web search.",
                    "action": "web_search",
                    "action_input": {
                        "query": task
                    },
                }

            return {
                "thought": "The web search result is available. I can now answer.",
                "action": "final_answer",
                "final_answer": "I searched the web and used the result to answer your request.",
            }

        # --------------------------------------------------
        # Direct code execution query
        # --------------------------------------------------
        if "run code" in task_lower or "execute" in task_lower or "python" in task_lower:
            if "code_execution" not in scratchpad_lower:
                return {
                    "thought": "The user wants code to be executed.",
                    "action": "code_execution",
                    "action_input": {
                        "code": "print('Hello from the code execution tool')"
                    },
                }

            return {
                "thought": "The code has been executed. I can now answer.",
                "action": "final_answer",
                "final_answer": "The code execution tool ran successfully.",
            }

        # --------------------------------------------------
        # Calculator fallback
        # --------------------------------------------------
        if any(operator in task_lower for operator in ["+", "-", "*", "/", "calculate", "sum"]):
            if "calculator" not in scratchpad_lower:
                return {
                    "thought": "The user appears to need a calculation.",
                    "action": "calculator",
                    "action_input": {
                        "expression": task
                    },
                }

            return {
                "thought": "The calculation has been completed.",
                "action": "final_answer",
                "final_answer": "The calculation tool returned a result.",
            }

        # --------------------------------------------------
        # Default final answer
        # --------------------------------------------------
        return {
            "thought": "No tool is required for this task.",
            "action": "final_answer",
            "final_answer": "I can answer this directly without using a tool.",
        }
