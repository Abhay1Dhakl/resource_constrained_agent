import unittest

from resource_agent.tools.base import ToolResult
from resource_agent.tools.calculator import CalculatorTool


class CalculatorToolTests(unittest.TestCase):
    def test_valid_expression_returns_tool_result(self):
        tool = CalculatorTool()

        result = tool.run({"expression": "1 + 2 * 3"})

        self.assertIsInstance(result, ToolResult)
        self.assertTrue(result.success)
        self.assertEqual(result.tool_name, tool.name)
        self.assertEqual(result.data["expression"], "1 + 2 * 3")
        self.assertEqual(result.data["result"], 7)
        self.assertIsNone(result.error_message)

    def test_missing_expression_returns_validation_error(self):
        tool = CalculatorTool()

        result = tool.run({})

        self.assertFalse(result.success)
        self.assertEqual(result.tool_name, tool.name)
        self.assertEqual(result.error_message, "No arithmetic expression provided.")


if __name__ == "__main__":
    unittest.main()
