import unittest
from resource_agent.agent.react_agent import ReactAgent


class OverBudgetLLM:
    def generate(self, **kwargs):
        return {
            "content": {
                "thought": "Need the profile first",
                "progress_assessment": "progress",
                "status": "continue",
                "action": "personal_profile_tool",
                "action_input": {"query": "profile"},
                "reason": "Need user context",
            },
            "cost": 0.25,
        }


class RepeatReplanLLM:
    def __init__(self):
        self.calls = 0

    def generate(self, **kwargs):
        self.calls += 1

        if self.calls == 1:
            return {
                "content": {
                    "thought": "Try JavaScript first",
                    "progress_assessment": "progress",
                    "status": "continue",
                    "action": "code_execution_tool",
                    "action_input": {
                        "code": "console.log('hello')",
                        "language": "javascript",
                        "timeout": 2,
                    },
                    "reason": "Initial attempt",
                },
                "cost": 0.01,
            }

        return {
            "content": {
                "thought": "Replan by retrying the same thing",
                "progress_assessment": "no_progress",
                "status": "replan",
                "action": "code_execution_tool",
                "action_input": {
                    "code": "console.log('hello')",
                    "language": "javascript",
                    "timeout": 2,
                },
                "reason": "Retry the same failed attempt",
            },
            "cost": 0.01,
        }


class SuccessfulReplanLLM:
    def __init__(self):
        self.calls = 0

    def generate(self, **kwargs):
        self.calls += 1

        if self.calls == 1:
            return {
                "content": {
                    "thought": "Try executing sample code quickly",
                    "progress_assessment": "progress",
                    "status": "continue",
                    "action": "code_execution_tool",
                    "action_input": {
                        "code": "console.log('hello')",
                        "language": "javascript",
                        "timeout": 2,
                    },
                    "reason": "Initial attempt to run code",
                },
                "cost": 0.01,
            }

        if self.calls == 2:
            return {
                "content": {
                    "thought": "That failed because only Python is supported. Replan with Python.",
                    "progress_assessment": "no_progress",
                    "status": "replan",
                    "action": "code_execution_tool",
                    "action_input": {
                        "code": "print('hello')",
                        "language": "python",
                        "timeout": 2,
                    },
                    "reason": "Previous attempt used an unsupported language.",
                },
                "cost": 0.01,
            }

        return {
            "content": {
                "thought": "The corrected execution succeeded",
                "progress_assessment": "enough_information",
                "status": "final_answer",
                "action": None,
                "action_input": {},
                "reason": "Successful replanning demo complete",
                "final_answer": "Replanning succeeded after switching from JavaScript to Python.",
            },
            "cost": 0.01,
        }


class MidTaskBudgetLLM:
    def __init__(self):
        self.calls = 0

    def generate(self, **kwargs):
        self.calls += 1

        if self.calls == 1:
            return {
                "content": {
                    "thought": "Fetch the user profile first.",
                    "progress_assessment": "no_progress",
                    "status": "continue",
                    "action": "personal_profile_tool",
                    "action_input": {"query": "profile"},
                    "reason": "Need profile context before answering.",
                },
                "cost": 0.01,
            }

        return {
            "content": {
                "thought": "I have enough context to answer now.",
                "progress_assessment": "enough_information",
                "status": "final_answer",
                "action": None,
                "action_input": {},
                "reason": "Ready to answer.",
                "final_answer": "This answer should never be recorded because the second call exceeds budget.",
            },
            "cost": 0.01,
        }


class CustomProfileLLM:
    def __init__(self):
        self.calls = 0

    def generate(self, **kwargs):
        self.calls += 1

        if self.calls == 1:
            return {
                "content": {
                    "thought": "Fetch the profile name first.",
                    "progress_assessment": "progress",
                    "status": "continue",
                    "action": "personal_profile_tool",
                    "action_input": {"query": "profile", "section": "name"},
                    "reason": "Need the hosted profile data.",
                },
                "cost": 0.01,
            }

        return {
            "content": {
                "thought": "The profile was loaded.",
                "progress_assessment": "enough_information",
                "status": "final_answer",
                "action": None,
                "action_input": {},
                "reason": "Done.",
                "final_answer": "Profile loaded.",
            },
            "cost": 0.01,
        }


class ReactAgentSmokeTests(unittest.TestCase):
    def test_budget_overrun_stops_cleanly(self):
        agent = ReactAgent(
            max_steps=2,
            max_calls=10,
            max_cost=0.20,
            llm=OverBudgetLLM(),
        )

        state = agent.run("test task")

        self.assertEqual(state.status, "stopped")
        self.assertIn("Cost limit exceeded", state.stop_reason)
        self.assertEqual(len(state.steps), 0)
        self.assertIn("The agent stopped because:", state.final_answer)

    def test_mid_task_budget_stop_preserves_partial_progress(self):
        agent = ReactAgent(
            max_steps=3,
            max_calls=10,
            max_cost=0.015,
            llm=MidTaskBudgetLLM(),
        )

        state = agent.run("mid-task budget test")

        self.assertEqual(state.status, "stopped")
        self.assertIn("Cost limit exceeded", state.stop_reason)
        self.assertEqual(len(state.steps), 1)
        self.assertEqual(state.steps[0].action, "personal_profile_tool")
        self.assertTrue(state.steps[0].observation["success"])
        self.assertIn("The agent stopped because:", state.final_answer)

    def test_repeated_replan_is_blocked(self):
        agent = ReactAgent(
            max_steps=4,
            max_calls=10,
            max_cost=0.20,
            llm=RepeatReplanLLM(),
        )

        state = agent.run("repeat replan test")

        self.assertEqual(state.status, "stopped")
        self.assertEqual(
            state.stop_reason,
            "Repeated replanning attempt was blocked to prevent a loop.",
        )
        self.assertEqual(len(state.steps), 2)
        self.assertEqual(len(state.replanning_events), 1)

        first_step = state.steps[0]
        second_step = state.steps[1]

        self.assertEqual(first_step.action, "code_execution_tool")
        self.assertFalse(first_step.observation["success"])
        self.assertIn("Unsupported language", first_step.observation["error"])

        self.assertEqual(second_step.progress_assessment, "blocked")
        self.assertFalse(second_step.observation["success"])
        self.assertIn(
            "Blocked repeated replanning attempt",
            second_step.observation["error"],
        )

    def test_successful_replan_is_recorded(self):
        agent = ReactAgent(
            max_steps=5,
            max_calls=10,
            max_cost=0.20,
            llm=SuccessfulReplanLLM(),
        )

        state = agent.run("successful replanning demo")

        self.assertEqual(state.status, "completed")
        self.assertEqual(
            state.final_answer,
            "Replanning succeeded after switching from JavaScript to Python.",
        )
        self.assertEqual(len(state.replanning_events), 1)

        replanning_event = state.replanning_events[0]
        self.assertEqual(replanning_event["step_number"], 2)
        self.assertEqual(replanning_event["failed_action"], "code_execution_tool")
        self.assertEqual(replanning_event["next_action"], "code_execution_tool")
        self.assertTrue(replanning_event["successful"])

        self.assertEqual(len(state.steps), 3)
        self.assertFalse(state.steps[0].observation["success"])
        self.assertTrue(state.steps[1].observation["success"])
        self.assertEqual(state.steps[2].observation["tool_name"], "final_answer")

    def test_agent_uses_custom_profile_data(self):
        agent = ReactAgent(
            max_steps=3,
            max_calls=10,
            max_cost=0.20,
            llm=CustomProfileLLM(),
            profile_data={"name": "Hosted Demo User"},
        )

        state = agent.run("custom profile test")

        self.assertEqual(state.status, "completed")
        self.assertEqual(
            state.steps[0].observation["data"]["profile"]["name"],
            "Hosted Demo User",
        )


if __name__ == "__main__":
    unittest.main()
