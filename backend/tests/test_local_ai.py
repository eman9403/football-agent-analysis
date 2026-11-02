import unittest
from unittest.mock import Mock, patch

from langchain_core.exceptions import OutputParserException
from pydantic import ValidationError

from backend.scouting import ScoutingFilters
from backend.local_ai import (
    FilterInterpretation,
    InvalidModelOutput,
    OllamaStatus,
    interpret_question,
    resolve_interpretation,
)


class LocalAiTests(unittest.TestCase):
    def test_supported_filter_is_typed_and_keeps_existing_thresholds(self):
        active = ScoutingFilters(min_minutes=720, min_role_share_pct=65)
        proposal = FilterInterpretation(
            decision="apply",
            message="Review this player shortlist.",
            profile="chance_creating_attacker",
            sort_by="shot_assists_per90",
            sort_direction="desc",
            min_minutes=900,
            min_role_share_pct=None,
        )

        result = resolve_interpretation(proposal, active)

        self.assertEqual(result.status, "ready")
        self.assertEqual(result.proposed_filters.profile, "chance_creating_attacker")
        self.assertEqual(result.proposed_filters.sort_by, "shot_assists_per90")
        self.assertEqual(result.proposed_filters.min_minutes, 900)
        self.assertEqual(result.proposed_filters.min_role_share_pct, 65)

    def test_ambiguous_and_unsupported_requests_never_propose_filters(self):
        active = ScoutingFilters()
        for decision in ("clarify", "unsupported"):
            with self.subTest(decision=decision):
                result = resolve_interpretation(
                    FilterInterpretation(decision=decision, message="Please narrow this request."),
                    active,
                )
                self.assertEqual(result.status, decision)
                self.assertIsNone(result.proposed_filters)

    def test_profile_incompatible_metric_is_rejected_before_database_search(self):
        with self.assertRaises(ValidationError):
            resolve_interpretation(
                FilterInterpretation(
                    decision="apply",
                    profile="forward_finisher",
                    sort_by="progressive_passes_completed_per90",
                ),
                ScoutingFilters(),
            )

    def test_invalid_model_output_gets_one_repair_attempt_then_fails_closed(self):
        calls = []

        def invoke(payload):
            calls.append(payload)
            return {"decision": "apply", "profile": "invented_profile", "message": "go"}

        with self.assertRaises(InvalidModelOutput):
            interpret_question("find players", ScoutingFilters(), invoker=invoke)

        self.assertEqual(len(calls), 2)
        self.assertTrue(calls[1].get("repair_feedback"))

    def test_repair_can_correct_a_profile_metric_mismatch(self):
        outputs = iter(
            [
                {
                    "decision": "apply",
                    "profile": "forward_finisher",
                    "sort_by": "progressive_passes_completed_per90",
                    "message": "I found forwards.",
                },
                {
                    "decision": "apply",
                    "profile": "forward_finisher",
                    "sort_by": "expected_goals_per90",
                    "message": "Rank forwards by source xG per 90.",
                },
            ]
        )

        result = interpret_question("rank forwards by xG per 90", ScoutingFilters(), invoker=lambda _: next(outputs))

        self.assertEqual(result.status, "ready")
        self.assertEqual(result.proposed_filters.sort_by, "expected_goals_per90")

    def test_langchain_parse_failure_is_repaired_once_instead_of_reported_as_outage(self):
        chain = Mock()
        chain.invoke.side_effect = [
            OutputParserException("model output was not valid JSON"),
            FilterInterpretation(
                decision="apply",
                message="Sort the selected forwards by expected goals per 90.",
                profile="forward_finisher",
                sort_by="expected_goals_per90",
                sort_direction="desc",
            ),
        ]
        with patch("backend.local_ai._make_filter_chain", return_value=chain):
            result = interpret_question("rank forwards by xG per 90", ScoutingFilters())

        self.assertEqual(result.status, "ready")
        self.assertEqual(chain.invoke.call_count, 2)
        self.assertTrue(chain.invoke.call_args_list[1].args[0]["repair_feedback"])

    def test_ollama_status_shape_distinguishes_missing_runtime_from_missing_model(self):
        with patch("backend.local_ai._read_ollama_tags", return_value=None):
            runtime_missing = OllamaStatus.inspect("qwen3.5:4b")
        with patch("backend.local_ai._read_ollama_tags", return_value=[]):
            model_missing = OllamaStatus.inspect("qwen3.5:4b")

        self.assertEqual(runtime_missing.state, "runtime_missing")
        self.assertEqual(model_missing.state, "model_missing")

    def test_non_loopback_ollama_endpoint_is_rejected_without_network_access(self):
        result = OllamaStatus.inspect("qwen3.5:4b", "https://remote.example.com")
        self.assertEqual(result.state, "remote_disallowed")
        self.assertIn("loopback", result.detail)


if __name__ == "__main__":
    unittest.main()
