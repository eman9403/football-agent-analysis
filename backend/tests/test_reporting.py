import unittest

from pydantic import ValidationError

from backend.reporting import (
    DraftSelection,
    build_report_evidence,
    resolve_report_selection,
)
from backend.scouting import PlayerSeasonAggregate, ScoutingFilters


def aggregate(player_id, player_name, progressive_completed, **overrides):
    values = {
        "player_id": player_id,
        "player_name": player_name,
        "country_name": None,
        "appearances": 20,
        "minutes_played": 1800,
        "team_names": ("Example FC",),
        "role_minutes": {"central_midfield": 1500, "chance_creator": 1000, "forward": 200},
        "metric_counts": {
            "passes_attempted": 200,
            "passes_completed": 160,
            "progressive_passes_attempted": 50,
            "progressive_passes_completed": progressive_completed,
            "progressive_carries": 20,
            "shot_assists": 10,
            "goal_assists": 2,
            "completed_box_passes": 14,
            "shots": 8,
            "goals": 2,
            "expected_goals": 1.5,
            "pressures": 90,
            "ball_recoveries": 24,
            "interceptions": 12,
            "positive_interceptions": 8,
            "tackle_duels": 20,
            "positive_tackle_duels": 12,
        },
    }
    values.update(overrides)
    return PlayerSeasonAggregate(**values)


class ReportingTests(unittest.TestCase):
    def test_report_evidence_is_built_from_profile_metrics_and_eligible_peers(self):
        filters = ScoutingFilters(min_minutes=450, min_role_share_pct=50)
        aggregates = [
            aggregate(1, "Sample One", 20),
            aggregate(2, "Sample Two", 30),
            aggregate(3, "Sample Three", 40),
        ]

        evidence = build_report_evidence(aggregates, filters, player_id=3)

        metric = next(item for item in evidence.metrics if item.metric_key == "progressive_passes_completed_per90")
        self.assertEqual(evidence.player.player_id, 3)
        self.assertEqual(evidence.peer_count, 3)
        self.assertEqual(metric.player_value, 2.0)
        self.assertAlmostEqual(metric.peer_median, 1.5)
        self.assertEqual(metric.unit, "completed passes per 90 minutes")
        self.assertEqual(metric.source_commit, evidence.scope.source_commit)

    def test_player_outside_selected_profile_or_thresholds_cannot_get_dossier(self):
        filters = ScoutingFilters(profile="forward_finisher", min_minutes=450)
        players = [aggregate(9, "Not A Forward", 30)]
        with self.assertRaises(LookupError):
            build_report_evidence(players, filters, player_id=9)

    def test_model_selection_cannot_reference_metrics_outside_evidence(self):
        selection = DraftSelection(highlights=["progressive_passes_completed_per90"], watchpoints=[])
        evidence = build_report_evidence(
            [aggregate(1, "Sample One", 20), aggregate(2, "Sample Two", 40)],
            ScoutingFilters(),
            player_id=2,
        )
        report = resolve_report_selection(evidence, selection, selected_by="ollama")

        self.assertTrue(report.claims)
        self.assertEqual(report.claims[0].metric_key, "progressive_passes_completed_per90")
        self.assertEqual(report.claims[0].source_commit, evidence.scope.source_commit)
        self.assertIn("2.00 completed passes per 90 minutes", report.claims[0].statement)
        self.assertIn("eligible central-midfield players", report.claims[0].statement)
        self.assertIn("peer median", report.claims[0].statement)

    def test_model_cannot_label_a_below_median_metric_as_a_strength(self):
        evidence = build_report_evidence(
            [aggregate(1, "Sample One", 20), aggregate(2, "Sample Two", 40)],
            ScoutingFilters(),
            player_id=1,
        )
        with self.assertRaises(ValueError):
            resolve_report_selection(
                evidence,
                DraftSelection(highlights=["progressive_passes_completed_per90"], watchpoints=[]),
                selected_by="ollama",
            )

    def test_unknown_or_duplicate_metric_keys_are_rejected_by_schema(self):
        with self.assertRaises(ValidationError):
            DraftSelection(highlights=["current_market_value"], watchpoints=[])
        with self.assertRaises(ValidationError):
            DraftSelection(
                highlights=["progressive_passes_completed_per90", "progressive_passes_completed_per90"],
                watchpoints=[],
            )


if __name__ == "__main__":
    unittest.main()
