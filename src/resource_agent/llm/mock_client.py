class MockLLMClient:
    def generate(self, task: str) -> dict:
        task_lower = task.lower()

        if "run code" in task_lower or "execute code" in task_lower or "python" in task_lower:
            return {
                "cost": 0.01,
                "content": {
                    "action": "code_execution",
                    "action_input": {
                        "language": "python",
                        "code": """
def two_sum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        diff = target - num
        if diff in seen:
            return [seen[diff], i]
        seen[num] = i
    return []

print(two_sum([2, 7, 11, 15], 9))
"""
                    }
                }
            }

        if "profile" in task_lower or "interview" in task_lower or "prepare me" in task_lower:
            return {
                "cost": 0.01,
                "content": {
                    "action": "personal_profile",
                    "action_input": {
                        "query": task
                    }
                }
            }

        return {
            "cost": 0.01,
            "content": {
                "action": "calculator",
                "action_input": {
                    "expression": "2 + 2"
                }
            }
        }