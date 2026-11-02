import json
import unittest
from pathlib import Path


class SprintFourEvalSuiteTests(unittest.TestCase):
    def test_fixed_suite_covers_supported_ambiguous_and_unsupported_requests(self):
        suite_path = Path(__file__).resolve().parents[2] / "evals" / "sprint-4-local-ai.json"
        suite = json.loads(suite_path.read_text())
        decisions = {case["expected_decision"] for case in suite["filter_cases"]}

        self.assertEqual(decisions, {"apply", "clarify", "unsupported"})
        self.assertGreaterEqual(len(suite["filter_cases"]), 10)
        self.assertFalse(suite["report_contract"]["player_specific_results_in_source"])

    def test_every_expected_filter_uses_a_supported_profile(self):
        suite_path = Path(__file__).resolve().parents[2] / "evals" / "sprint-4-local-ai.json"
        suite = json.loads(suite_path.read_text())
        allowed_profiles = {
            "ball_progressing_midfielder",
            "chance_creating_attacker",
            "forward_finisher",
            "ball_winning_midfielder",
        }

        for case in suite["filter_cases"]:
            with self.subTest(case=case["id"]):
                if case["expected_decision"] == "apply":
                    self.assertIn(case["expected_filters"]["profile"], allowed_profiles)


if __name__ == "__main__":
    unittest.main()
