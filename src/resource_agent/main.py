from resource_agent.agent.react_agent import ReactAgent


def print_agent_result(state):
    print("\n" + "=" * 80)
    print("AGENT RUN RESULT")
    print("=" * 80)

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

    print("\n" + "=" * 80)


def main():
    agent = ReactAgent(max_steps=5)

    task = (
        "Prepare me for a Cedar Gate AI Engineer interview based on my profile. "
        "Also search recent company information and give me one Python coding question to practice."
    )

    state = agent.run(task)

    print_agent_result(state)


if __name__ == "__main__":
    main()