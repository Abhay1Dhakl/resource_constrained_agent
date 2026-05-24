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

    def test_in_memory_profile_override_is_used(self):
        tool = PersonalProfileTool(
            profile_path="data/does_not_matter.json",
            profile_data={
                "name": "Hosted Demo User",
                "skills": {"programming": ["Python", "Go"]},
            },
        )

        result = tool.run({"query": "skills", "section": "skills"})

        self.assertTrue(result.success)
        self.assertEqual(
            result.data["profile"]["skills"]["programming"],
            ["Python", "Go"],
        )


if __name__ == "__main__":
    unittest.main()
