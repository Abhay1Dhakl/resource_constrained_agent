import unittest

from resource_agent.tools.base import ToolResult
from resource_agent.tools.registry import ToolRegistry


class ToolRegistryTests(unittest.TestCase):
    def test_run_tool_executes_registered_tool(self):
        registry = ToolRegistry()

        result = registry.run_tool("personal_profile_tool", {"section": "skills"})

        self.assertIsInstance(result, ToolResult)
        self.assertTrue(result.success)
        self.assertEqual(result.tool_name, "personal_profile_tool")
        self.assertEqual(result.data["section"], "skills")
        self.assertIn("skills", result.data["profile"])

    def test_run_tool_returns_error_for_unknown_tool(self):
        registry = ToolRegistry()

        result = registry.run_tool("missing_tool", {})

        self.assertFalse(result.success)
        self.assertEqual(result.tool_name, "missing_tool")
        self.assertEqual(result.error_message, "Tool 'missing_tool' not found")

    def test_registry_uses_profile_override(self):
        registry = ToolRegistry(
            profile_data={"skills": {"programming": ["Rust"]}},
        )

        result = registry.run_tool("personal_profile_tool", {"section": "skills"})

        self.assertTrue(result.success)
        self.assertEqual(
            result.data["profile"]["skills"]["programming"],
            ["Rust"],
        )


if __name__ == "__main__":
    unittest.main()
