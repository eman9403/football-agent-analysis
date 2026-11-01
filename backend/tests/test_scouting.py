import unittest
from decimal import Decimal

from pydantic import ValidationError

import backend.scouting as scouting


def aggregate(**overrides):
    values = {
        "player_id": 1,
        "player_name": "Sample Player",
        "country_name": None,
        "appearances": 10,
        "minutes_played": 900,
        "team_names": ("Sample FC",),
        "role_minutes": {
            "central_midfield": 600,
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


class ScoutingTests(unittest.TestCase):
    def test_progressive_action_requires_ten_forward_units_and_known_coordinates(self):
        self.assertTrue(scouting.is_progressive(30, 40))
        self.assertFalse(scouting.is_progressive(30, 39))
        self.assertFalse(scouting.is_progressive(30, 10))
        self.assertFalse(scouting.is_progressive(None, 40))
        self.assertFalse(scouting.is_progressive(30, None))
        self.assertTrue(scouting.is_progressive(Decimal("30"), 40.0))

    def test_role_share_and_minimum_minutes_are_inclusive(self):
        filters = scouting.ScoutingFilters(min_minutes=450, min_role_share_pct=50)
        results = scouting.build_player_results(
            [
                aggregate(player_id=1, minutes_played=450, role_minutes={"central_midfield": 225}),
                aggregate(player_id=2, minutes_played=449, role_minutes={"central_midfield": 449}),
                aggregate(player_id=3, minutes_played=450, role_minutes={"central_midfield": 224}),
                aggregate(player_id=4, minutes_played=600, role_minutes={"central_midfield": 420}),
                aggregate(player_id=5, minutes_played=450, role_minutes={"central_midfield": 224.999}),
            ],
            filters,
        )

        self.assertEqual([player.player_id for player in results], [1, 4])
        self.assertEqual(results[0].role_share_pct, 50.0)
        self.assertEqual(results[1].role_share_pct, 70.0)
        self.assertEqual(scouting.CENTRAL_MIDFIELD_POSITION_IDS, frozenset({9, 10, 11, 13, 14, 15}))

    def test_per90_and_completion_metrics_use_season_minutes(self):
        response = scouting.build_scouting_response(
            [aggregate()],
            scouting.ScoutingFilters(profile="ball_progressing_midfielder"),
        )
        metrics = response.results[0].metrics

        self.assertEqual(metrics["overall_pass_completion_pct"], 75.0)
        self.assertEqual(metrics["progressive_pass_completion_pct"], 60.0)
        self.assertEqual(metrics["progressive_passes_attempted_per90"], 1.0)
        self.assertEqual(metrics["progressive_passes_completed_per90"], 0.6)
        self.assertEqual(metrics["progressive_carries_per90"], 0.5)
        self.assertIsNone(scouting._per90(0, 0))

    def test_filters_reject_unknown_profiles_metrics_and_ranges(self):
        with self.assertRaises(ValidationError):
            scouting.ScoutingFilters(profile="all_players")
        with self.assertRaises(ValidationError):
            scouting.ScoutingFilters(
                profile="forward_finisher",
                sort_by="progressive_passes_completed_per90",
            )
        with self.assertRaises(ValidationError):
            scouting.ScoutingFilters(min_minutes=-1)
        with self.assertRaises(ValidationError):
            scouting.ScoutingFilters(min_role_share_pct=101)
        with self.assertRaises(ValidationError):
            scouting.ScoutingFilters(limit=0)

    def test_sort_is_stable_and_missing_values_sort_last(self):
        base = aggregate()
        players = [
            scouting._build_scouting_player(
                aggregate(player_id=8, player_name="Beta"), scouting.PROFILE_SPECS["ball_progressing_midfielder"]
            ),
            scouting._build_scouting_player(
                aggregate(player_id=4, player_name="Alpha"), scouting.PROFILE_SPECS["ball_progressing_midfielder"]
            ),
            scouting._build_scouting_player(
                aggregate(player_id=3, player_name="Alpha"), scouting.PROFILE_SPECS["ball_progressing_midfielder"]
            ),
        ]
        filters = scouting.ScoutingFilters(sort_by="progressive_passes_completed_per90")
        self.assertEqual([player.player_id for player in scouting.sort_players(players, filters)], [3, 4, 8])

        nullable = scouting._build_scouting_player(
            aggregate(
                player_id=1,
                player_name="No attempts",
                metric_counts={**base.metric_counts, "progressive_passes_attempted": 0},
            ),
            scouting.PROFILE_SPECS["ball_progressing_midfielder"],
        )
        attempted = scouting._build_scouting_player(
            aggregate(
                player_id=2,
                player_name="Attempted",
                metric_counts={
                    **base.metric_counts,
                    "progressive_passes_attempted": 1,
                    "progressive_passes_completed": 0,
                },
            ),
            scouting.PROFILE_SPECS["ball_progressing_midfielder"],
        )
        ascending = filters.model_copy(
            update={"sort_by": "progressive_pass_completion_pct", "sort_direction": "asc"}
        )
        self.assertEqual([player.player_id for player in scouting.sort_players([nullable, attempted], ascending)], [2, 1])

    def test_empty_search_and_profile_catalog_have_stable_shapes(self):
        response = scouting.build_scouting_response([], scouting.ScoutingFilters())
        self.assertEqual(response.result_count, 0)
        self.assertEqual(response.results, [])
        self.assertEqual(response.profile_key, "ball_progressing_midfielder")
        self.assertEqual(response.scope.season_name, "2015/16")
        self.assertTrue(response.metric_definitions)
        self.assertEqual(len(scouting.list_scouting_profiles()), 4)


if __name__ == "__main__":
    unittest.main()
