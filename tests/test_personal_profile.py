import unittest

from resource_agent.tools.personal_profile import PersonalProfileTool


class PersonalProfileToolTests(unittest.TestCase):
    def test_section_filtering_returns_only_requested_section(self):
        tool = PersonalProfileTool()

        result = tool.run({"query": "skills", "section": "skills"})

        self.assertTrue(result.success)
        self.assertIsNone(result.error_message)
        self.assertEqual(result.data["query"], "skills")
        self.assertEqual(result.data["section"], "skills")
        self.assertIn("profile", result.data)
        self.assertEqual(set(result.data["profile"].keys()), {"skills"})
        self.assertIn("programming", result.data["profile"]["skills"])


if __name__ == "__main__":
    unittest.main()