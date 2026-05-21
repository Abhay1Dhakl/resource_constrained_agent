import sys
from resource_agent.agent.react_agent import ReactAgent

def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <task>")
        return 
    
    task = sys.argv[1]
    agent = ReactAgent()
    result = agent.run(task)
    print("Agent State:")
    print(f"Task: {result.task}")
    print(f"Status: {result.status}")
    print(f"Steps Completed: {result.steps_completed}")
    print(f"Tool Results: {result.tool_results}")
    print(f"Final Answer: {result.final_answer}")
    print(f"Stop Reason: {result.stop_reason}")
    print(f"Budget Summary: {agent.budget_summary()}")


if __name__ == "__main__":
    main()