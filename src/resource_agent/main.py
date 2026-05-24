from resource_agent.agent.react_agent import ReactAgent
from resource_agent.evaluation.tasks import EVALUATION_TASKS


def print_agent_result(scenario_name: str, state, budget_summary):
    """Print a readable trace and summary for a completed scenario run.

    Args:
        scenario_name: Name of the scenario being executed.
        state: Final agent state produced by the scenario run.
        budget_summary: Snapshot of the final budget usage.
    """
    print("\n" + "=" * 80)
    print("AGENT RUN RESULT")
    print("=" * 80)
    print(f"\nScenario: {scenario_name}")

    print(f"\nTask:\n{state.task}")

    print(f"\nStatus: {state.status}")
    print(f"Stop Reason: {state.stop_reason}")

    print("\n" + "-" * 80)
    print("REACT TRACE")
    print("-" * 80)

    if not state.steps:
        print("No steps were executed.")
    else:
        for step in state.steps:
            print(f"\nStep {step.step_number}")

            if step.thought:
                print(f"Thought: {step.thought}")

            if step.action:
                print(f"Action: {step.action}")

            if step.action_input:
                print(f"Action Input: {step.action_input}")

            if step.observation:
                print(f"Observation: {step.observation}")

    print("\n" + "-" * 80)
    print("FINAL ANSWER")
    print("-" * 80)

    print(state.final_answer)
    print("\n" + "-" * 80)
    print("BUDGET SUMMARY")
    print("-" * 80)
    print(budget_summary)

    print("\n" + "=" * 80)


def run_scenario(
    scenario_name: str,
    task: str,
    max_steps: int,
    max_calls: int,
    max_cost: float,
):
    """Run one evaluation scenario and print the resulting agent trace.

    Args:
        scenario_name: Name used to label the scenario output.
        task: User task prompt passed to the agent.
        max_steps: Maximum number of planner-tool steps allowed.
        max_calls: Maximum number of LLM calls allowed.
        max_cost: Maximum total LLM cost allowed.
    """
    agent = ReactAgent(max_steps=max_steps, max_calls=max_calls, max_cost=max_cost)
    state = agent.run(task)
    print_agent_result(scenario_name, state, agent.budget_summary())


def main():
    """Run all built-in evaluation scenarios from the command line."""
    for evaluation_task in EVALUATION_TASKS:
        run_scenario(
            scenario_name=evaluation_task.task_id,
            task=evaluation_task.prompt,
            max_steps=6,
            max_calls=10,
            max_cost=0.20,
        )

if __name__ == "__main__":
    main()
