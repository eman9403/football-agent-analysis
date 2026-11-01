import unittest

from pydantic import ValidationError

import backend.scouting as scouting


PROFILE_KEYS = (
    "ball_progressing_midfielder",
    "chance_creating_attacker",
    "forward_finisher",
    "ball_winning_midfielder",
)


def aggregate(**overrides):
    values = {
        "player_id": 1,
        "player_name": "Sample Player",
        "country_name": None,
        "appearances": 10,
        "minutes_played": 900,
        "team_names": ("Sample FC",),
        "role_minutes": {
            "central_midfield": 700,
            "chance_creator": 600,
            "forward": 600,
        },
        "metric_counts": {
            "passes_attempted": 20,
            "passes_completed": 15,
            "progressive_passes_attempted": 10,
            "progressive_passes_completed": 6,
            "progressive_carries": 5,
            "shot_assists": 4,
            "goal_assists": 2,
            "completed_box_passes": 9,
            "shots": 10,
            "goals": 3,
            "expected_goals": 2.5,
            "pressures": 20,
            "ball_recoveries": 12,
            "interceptions": 5,
            "positive_interceptions": 3,
            "tackle_duels": 8,
            "positive_tackle_duels": 4,
        },
    }
    values.update(overrides)
    return scouting.PlayerSeasonAggregate(**values)


class MultiProfileScoutingTests(unittest.TestCase):
    def test_profile_catalog_exposes_four_separate_role_lenses(self):
        profiles = scouting.list_scouting_profiles()
        self.assertEqual([profile.profile_key for profile in profiles], list(PROFILE_KEYS))
        self.assertEqual(
            [profile.role_group for profile in profiles],
            ["central_midfield", "chance_creator", "forward", "central_midfield"],
        )

    def test_each_profile_has_its_own_default_sort_and_metric_contract(self):
        expected = {
            "ball_progressing_midfielder": (
                "progressive_passes_completed_per90",
                {
                    "progressive_passes_attempted_per90",
                    "progressive_passes_completed_per90",
                    "progressive_pass_completion_pct",
                    "progressive_carries_per90",
                    "overall_pass_completion_pct",
                },
            ),
            "chance_creating_attacker": (
                "shot_assists_per90",
                {
                    "shot_assists_per90",
                    "goal_assists_per90",
                    "completed_box_passes_per90",
                    "progressive_carries_per90",
                },
            ),
            "forward_finisher": (
                "expected_goals_per90",
                {"shots_per90", "expected_goals_per90", "goals_per90", "expected_goals_per_shot"},
            ),
            "ball_winning_midfielder": (
                "interceptions_per90",
                {
                    "pressures_per90",
                    "ball_recoveries_per90",
                    "interceptions_per90",
                    "interception_positive_outcome_pct",
                    "tackle_duels_per90",
                    "tackle_positive_outcome_pct",
                },
            ),
        }
        for profile_key, (default_sort, metric_keys) in expected.items():
            with self.subTest(profile=profile_key):
                filters = scouting.ScoutingFilters(profile=profile_key)
                response = scouting.build_scouting_response([aggregate()], filters)
                self.assertEqual(filters.sort_by, default_sort)
                self.assertEqual(response.profile_key, profile_key)
                self.assertEqual({metric.key for metric in response.metric_definitions}, metric_keys)
                self.assertEqual(set(response.results[0].metrics), metric_keys)

    def test_profile_specific_metrics_use_their_documented_denominators(self):
        fixtures = {
            "ball_progressing_midfielder": {
                "progressive_passes_attempted_per90": 1.0,
                "progressive_passes_completed_per90": 0.6,
                "progressive_pass_completion_pct": 60.0,
                "progressive_carries_per90": 0.5,
                "overall_pass_completion_pct": 75.0,
            },
            "chance_creating_attacker": {
                "shot_assists_per90": 0.4,
                "goal_assists_per90": 0.2,
                "completed_box_passes_per90": 0.9,
                "progressive_carries_per90": 0.5,
            },
            "forward_finisher": {
                "shots_per90": 1.0,
                "expected_goals_per90": 0.25,
                "goals_per90": 0.3,
                "expected_goals_per_shot": 0.25,
            },
            "ball_winning_midfielder": {
                "pressures_per90": 2.0,
                "ball_recoveries_per90": 1.2,
                "interceptions_per90": 0.5,
                "interception_positive_outcome_pct": 60.0,
                "tackle_duels_per90": 0.8,
                "tackle_positive_outcome_pct": 50.0,
            },
        }
        for profile_key, expected in fixtures.items():
            with self.subTest(profile=profile_key):
                response = scouting.build_scouting_response(
                    [aggregate()], scouting.ScoutingFilters(profile=profile_key)
                )
                self.assertEqual(response.results[0].metrics, expected)

    def test_role_share_uses_the_selected_profile_role_pool(self):
        player = aggregate(
            role_minutes={
                "central_midfield": 400,
                "chance_creator": 600,
                "forward": 200,
            }
        )
        creator = scouting.build_scouting_response(
            [player], scouting.ScoutingFilters(profile="chance_creating_attacker")
        )
        midfielder = scouting.build_scouting_response(
            [player], scouting.ScoutingFilters(profile="ball_progressing_midfielder")
        )

        self.assertEqual(creator.results[0].role_share_pct, 66.6667)
        self.assertEqual(creator.results[0].role_minutes, 600)
        self.assertEqual(midfielder.results, [])

    def test_each_profile_rejects_metrics_from_other_profiles(self):
        with self.assertRaises(ValidationError):
            scouting.ScoutingFilters(
                profile="forward_finisher",
                sort_by="progressive_passes_completed_per90",
            )
        with self.assertRaises(ValidationError):
            scouting.ScoutingFilters(profile="not_a_profile")

    def test_missing_denominators_remain_null_and_sort_last(self):
        no_shots = aggregate(
            player_id=2,
            player_name="No shots",
            metric_counts={**aggregate().metric_counts, "shots": 0, "expected_goals": 0, "goals": 0},
        )
        filters = scouting.ScoutingFilters(
            profile="forward_finisher",
            sort_by="expected_goals_per_shot",
        )
        response = scouting.build_scouting_response([no_shots, aggregate()], filters)

        self.assertEqual(response.results[0].player_id, 1)
        self.assertEqual(response.results[1].player_id, 2)
        self.assertIsNone(response.results[1].metrics["expected_goals_per_shot"])


if __name__ == "__main__":
    unittest.main()
