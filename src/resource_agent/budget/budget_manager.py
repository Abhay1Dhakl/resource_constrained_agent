class BudgetExceededError(Exception):
    """Raised when the budget is exceeded."""
    pass

class BudgetManager:
    def __init__(self, max_calls: int = 10, max_cost: float = 0.20):
        self.max_calls = max_calls
        self.max_cost = max_cost
        self.calls_used = 0
        self.total_cost = 0.0
    
    def can_make_call(self) -> bool:
        """Check if a new API call can be made without exceeding the budget."""
        return self.calls_used < self.max_calls and self.total_cost < self.max_cost
    
    def record_llm_call(self, cost:  float):
        if self.calls_used + 1 > self.max_calls:
            raise BudgetExceededError(f"API call limit exceeded: {self.calls_used + 1} calls used, max is {self.max_calls}.")
        
        if self.total_cost + cost > self.max_cost:
            raise BudgetExceededError(f"Cost limit exceeded: total cost would be {self.total_cost + cost}, max is {self.max_cost}.")
        
        self.calls_used += 1
        self.total_cost += cost

    def summary(self) -> str:
        """Return a summary of the current budget usage."""
        return {
            "calls_used": self.calls_used,
            "total_cost": self.total_cost,
            "calls_remaining": self.max_calls - self.calls_used,
            "cost_remaining": self.max_cost - self.total_cost
        }