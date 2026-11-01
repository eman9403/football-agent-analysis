import unittest
from decimal import Decimal

from pydantic import ValidationError

import backend.scouting as scouting


class ScoutingTests(unittest.TestCase):
    def require(self, name):
        value = getattr(scouting, name, None)
        self.assertIsNotNone(value, f"backend.scouting.{name} is not implemented")
        return value

    def aggregate(self, **overrides):
        values = {
            "player_id": 1,
            "player_name": "Sample Player",
            "country_name": None,
            "appearances": 10,
            "minutes_played": 900,
            "central_midfield_minutes": 600,
            "team_names": ("Sample FC",),
            "passes_attempted": 20,
            "passes_completed": 15,
            "progressive_passes_attempted": 10,
            "progressive_passes_completed": 6,
            "progressive_carries": 5,
        }
        values.update(overrides)
        return self.require("PlayerSeasonAggregate")(**values)

    def test_progressive_action_requires_ten_forward_units_and_known_coordinates(self):
        is_progressive = self.require("is_progressive")
        self.assertTrue(is_progressive(30, 40))
        self.assertFalse(is_progressive(30, 39))
        self.assertFalse(is_progressive(30, 10))
        self.assertFalse(is_progressive(None, 40))
        self.assertFalse(is_progressive(30, None))
        self.assertTrue(is_progressive(Decimal("30"), 40.0))

    def test_role_share_and_minimum_minutes_are_inclusive_and_use_total_minutes(self):
        filters = self.require("ScoutingFilters")(
            min_minutes=450,
            min_central_share_pct=50,
            sort_by="progressive_passes_attempted_per90",
        )
        player_results = self.require("build_player_results")(
            [
                self.aggregate(player_id=1, player_name="Alpha", minutes_played=450, central_midfield_minutes=225),
                self.aggregate(player_id=2, player_name="Too Few Minutes", minutes_played=449, central_midfield_minutes=449),
                self.aggregate(player_id=3, player_name="Too Little Role", minutes_played=450, central_midfield_minutes=224),
                self.aggregate(player_id=4, player_name="Bravo", minutes_played=600, central_midfield_minutes=420),
                self.aggregate(player_id=5, player_name="Just Below Role", minutes_played=450, central_midfield_minutes=224.9999),
                self.aggregate(player_id=6, player_name="Just Below Minutes", minutes_played=449.999, central_midfield_minutes=449.999),
            ],
            filters,
        )

        self.assertEqual([player.player_id for player in player_results], [1, 4])
        self.assertEqual(player_results[0].central_midfield_share_pct, 50.0)
        self.assertEqual(player_results[1].central_midfield_share_pct, 70.0)
        self.assertEqual(self.require("CENTRAL_MIDFIELD_POSITION_IDS"), frozenset({9, 10, 11, 13, 14, 15}))

    def test_completed_passes_follow_statsbomb_outcome_and_rates_use_season_minutes(self):
        result = self.require("build_scouting_player")(self.aggregate())

        self.assertEqual(result.overall_pass_completion_pct, 75.0)
        self.assertEqual(result.progressive_pass_completion_pct, 60.0)
        self.assertEqual(result.progressive_passes_attempted_per90, 1.0)
        self.assertEqual(result.progressive_passes_completed_per90, 0.6)
        self.assertEqual(result.progressive_carries_per90, 0.5)
        self.assertIsNone(self.require("build_scouting_player")(
            self.aggregate(passes_attempted=0, passes_completed=0,
                           progressive_passes_attempted=0, progressive_passes_completed=0)
        ).overall_pass_completion_pct)
        self.assertIsNone(self.require("build_scouting_player")(
            self.aggregate(minutes_played=0, central_midfield_minutes=0)
        ).progressive_passes_attempted_per90)

    def test_filters_reject_unknown_profile_sort_and_out_of_range_values(self):
        filters = self.require("ScoutingFilters")
        with self.assertRaises(ValidationError):
            filters(profile="all_players")
        with self.assertRaises(ValidationError):
            filters(sort_by="player_id; DROP TABLE statsbomb_players")
        with self.assertRaises(ValidationError):
            filters(min_minutes=-1)
        with self.assertRaises(ValidationError):
            filters(min_central_share_pct=101)
        with self.assertRaises(ValidationError):
            filters(limit=0)

    def test_sort_is_allowlisted_and_ties_have_a_stable_order(self):
        filters = self.require("ScoutingFilters")(
            sort_by="progressive_passes_completed_per90", sort_direction="desc"
        )
        players = self.require("build_player_results")(
            [
                self.aggregate(player_id=8, player_name="Beta", progressive_passes_completed=5),
                self.aggregate(player_id=4, player_name="Alpha", progressive_passes_completed=5),
                self.aggregate(player_id=3, player_name="Alpha", progressive_passes_completed=5),
            ],
            filters,
        )
        self.assertEqual([player.player_id for player in players], [3, 4, 8])

        nullable_players = self.require("build_player_results")(
            [
                self.aggregate(player_id=1, player_name="No Attempts", progressive_passes_attempted=0,
                               progressive_passes_completed=0),
                self.aggregate(player_id=2, player_name="Attempted", progressive_passes_attempted=1,
                               progressive_passes_completed=0),
            ],
            filters.model_copy(update={"sort_by": "progressive_pass_completion_pct", "sort_direction": "asc"}),
        )
        self.assertEqual([player.player_id for player in nullable_players], [2, 1])

    def test_empty_search_returns_a_valid_empty_response(self):
        filters = self.require("ScoutingFilters")()
        response = self.require("build_scouting_response")([], filters)

        self.assertEqual(response.result_count, 0)
        self.assertEqual(response.results, [])
        self.assertEqual(response.profile_key, "ball_progressing_midfielder")
        self.assertEqual(response.scope.season_name, "2015/16")
        self.assertTrue(response.metric_definitions)


if __name__ == "__main__":
    unittest.main()
