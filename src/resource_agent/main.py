from resource_agent.agent.react_agent import ReactAgent


DEFAULT_TASK = (
    "Prepare me for a Cedar Gate AI Engineer interview based on my profile. "
    "Also search recent company information and give me one Python coding question to practice."
)


def print_agent_result(scenario_name: str, state, budget_summary):
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
    agent = ReactAgent(max_steps=max_steps, max_calls=max_calls, max_cost=max_cost)
    state = agent.run(task)
    print_agent_result(scenario_name, state, agent.budget_summary())


def main():
    run_scenario(
        scenario_name="normal_budget",
        task=DEFAULT_TASK,
        max_steps=5,
        max_calls=10,
        max_cost=0.20,
    )
    run_scenario(
        scenario_name="tight_call_budget",
        task=DEFAULT_TASK,
        max_steps=10,
        max_calls=2,
        max_cost=0.20,
    )
    run_scenario(
        scenario_name="tight_cost_budget",
        task=DEFAULT_TASK,
        max_steps=10,
        max_calls=10,
        max_cost=0.02,
    )


if __name__ == "__main__":
    main()
