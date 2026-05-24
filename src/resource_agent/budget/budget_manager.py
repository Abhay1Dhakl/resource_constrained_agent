class BudgetExceededError(Exception):
    """Raised when the budget is exceeded."""
    pass

class BudgetManager:
    """Tracks the hard assignment budget for LLM usage only.

    - calls_used counts LLM calls
    - total_cost tracks LLM cost
    - tool invocations do not count toward the 10-call limit"""
    
    def __init__(self, max_calls: int = 10, max_cost: float = 0.20):
        """Initialize the LLM budget tracker.

        Args:
            max_calls: Maximum number of LLM calls allowed for a run.
            max_cost: Maximum cumulative LLM cost allowed for a run.
        """
        self.max_calls = max_calls
        self.max_cost = max_cost
        self.calls_used = 0
        self.total_cost = 0.0
    
    def can_make_call(self) -> bool:
        """Check whether another LLM call fits within the current budget.

        Returns:
            bool: `True` when the next call would stay within limits.
        """
        return self.calls_used < self.max_calls and self.total_cost < self.max_cost
    
    def record_llm_call(self, cost:  float):
        """Record a completed LLM call and enforce the configured budget.

        Args:
            cost: Estimated cost of the completed LLM call.

        Raises:
            BudgetExceededError: Raised when adding the call would exceed the
                call or cost budget.
        """
        if self.calls_used + 1 > self.max_calls:
            raise BudgetExceededError(f"API call limit exceeded: {self.calls_used + 1} calls used, max is {self.max_calls}.")
        
        if self.total_cost + cost > self.max_cost:
            raise BudgetExceededError(f"Cost limit exceeded: total cost would be {self.total_cost + cost}, max is {self.max_cost}.")
        
        self.calls_used += 1
        self.total_cost += cost

    def summary(self) -> dict[str, int | float]:
        """Return a snapshot of current budget usage and remaining limits.

        Returns:
            dict: Current call usage, total cost, and remaining budget values.
        """
        return {
            "calls_used": self.calls_used,
            "total_cost": self.total_cost,
            "calls_remaining": self.max_calls - self.calls_used,
            "cost_remaining": self.max_cost - self.total_cost
        }
