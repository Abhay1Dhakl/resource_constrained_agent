class MockLLMClient:
    """A mock LLM client for testing purposes."""

    def __init__(self, mock_cost_per_call: float = 0.02):
        self.mock_cost_per_call = mock_cost_per_call
    
    def generate(self, task: str) -> dict:
        return {
            "content" : {
                "thought": "The user is asking for a simple calculator",
                "action": "calculator",
                "action_input": "2 + 2"
            },
            "cost": self.mock_cost_per_call,
            "input_tokens": 100,
            "output_tokens": 50,
        }