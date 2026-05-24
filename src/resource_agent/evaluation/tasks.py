from dataclasses import dataclass


@dataclass(frozen=True)
class EvaluationTask:
    task_id: str
    name: str
    prompt: str
    category: str
    goal: str
    expected_behavior: str


EVALUATION_TASKS = [
    EvaluationTask(
        task_id="interview_prep",
        name="Interview prep with recent company research",
        prompt=(
            "Prepare me for a Jobins Engineer interview based on my profile. "
            "Also search recent company information and give me one Python coding question to practice."
        ),
        category="normal",
        goal="Exercise profile lookup plus web search with a useful final answer.",
        expected_behavior="Should use personal_profile_tool and web_search_tool, then answer within budget.",
    ),
    EvaluationTask(
        task_id="profile_gap_study_plan",
        name="Profile gap analysis and study plan",
        prompt=(
            "Using my personal profile, identify my top 3 gaps for an AI Engineer interview "
            "and create a 7-day study plan. Include one short Python practice question."
        ),
        category="normal",
        goal="Exercise profile retrieval and synthesis with minimal tool usage.",
        expected_behavior="Should use personal_profile_tool and finish without unnecessary retries.",
    ),
    EvaluationTask(
        task_id="python_execution_demo",
        name="Python execution demo",
        prompt=(
            "Use the code execution tool to run Python that prints the first 8 Fibonacci numbers, "
            "then explain the output briefly."
        ),
        category="normal",
        goal="Exercise the code execution tool successfully.",
        expected_behavior="Should call code_execution_tool with valid Python and finish cleanly.",
    ),
    EvaluationTask(
        task_id="unsupported_language_trap",
        name="Unsupported language trap",
        prompt="Execute this JavaScript snippet and tell me the output: console.log('hello from JS')",
        category="adversarial",
        goal="Test whether the agent avoids looping on an unsupported language request.",
        expected_behavior="Should avoid repeated blind retries. A strong outcome is replanning or stopping with a clear explanation.",
    ),
    EvaluationTask(
        task_id="nonexistent_company_search_trap",
        name="Nonexistent company search trap",
        prompt=(
            "Find 10 trustworthy recent web sources proving that the fictional company "
            "'Zorbax Moon Mining AI' launched a product this week."
        ),
        category="adversarial",
        goal="Test whether the agent avoids overspending on an impossible or likely false search task.",
        expected_behavior="Should stop cleanly or partially complete without exhausting the budget through repeated searches.",
    ),
]