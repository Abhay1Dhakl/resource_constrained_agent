from resource_agent.budget.budget_manager import BudgetManager, BudgetExceededError
from resource_agent.tools.calculator import CalculatorTool
from resource_agent.llm.mock_client import MockLLMClient
from resource_agent.agent.state import AgentState

class ReactAgent:
    """A simple REACT agent that uses a mock LLM and a calculator tool to perform tasks."""

    def __init__(self):
        self.llm = MockLLMClient()
        self.budget = BudgetManager(max_calls=10, max_cost=0.20)

        self.tools = {
            "calculator": CalculatorTool(),
        }

    
    def run(self, task: str) -> AgentState:
        state = AgentState(task=task)

        try:
            if not self.budget.can_make_call():
                state.status = "stopped"
                state.stop_reason = "Budget exited befote execution"
                state.final_answer = "Sorry...the agent stopped before starting because the budget was already exhausted"

            llm_response = self.llm.generate(task)
            self.budget.record_llm_call(llm_response["cost"])
            decision = llm_response["content"]
            action = decision["action"]
            action_input = decision["action_input"]

            if action not in self.tools:
                state.status = "failed",
                state.stop_reason = f"Unknown tool was requested: {action}"
                state.final_answer = f"The agent failed because the requested tool {action} is not available"
                return state
        
            tool = self.tools[action]
            tool_result = tool.run(action_input)

            state.steps_completed.append(f"LLm selected tool: {action}")
            state.steps_completed.append(f"Executed tool with input '{action_input}'")
            state.tool_results.append(tool_result)

            return state
        
        except BudgetExceededError as error:
            state.status = "stopped"
            state.stop_reason = "Budget exceeded during execution"
            state.final_answer = f"Sorry...the agent stopped because the budget was exceeded: {str(error)}"
            return state
        
    def _build_final_answer(self, tool_result: dict) -> str:
        if tool_result["success"]:
            return f"The result of the calculation is: {tool_result['result']}"
        else:
            return f"The calculation failed with error: {tool_result['error']}"
        
    def budget_summary(self) -> dict:
        return self.budget.summary()