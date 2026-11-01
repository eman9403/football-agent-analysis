import json
import os
import unittest
from pathlib import Path

import psycopg

import backend.scouting as scouting


RUN_POSTGRES_TESTS = os.environ.get("RUN_SCOUTING_POSTGRES_TESTS") == "1"


@unittest.skipUnless(RUN_POSTGRES_TESTS, "set RUN_SCOUTING_POSTGRES_TESTS=1 to use local PostgreSQL")
class ScoutingPostgresIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.connection = psycopg.connect(
            os.environ.get("DATABASE_URL", "dbname=football_scouting"), connect_timeout=3
        )

    @classmethod
    def tearDownClass(cls):
        cls.connection.close()

    def aggregates(self):
        return scouting.fetch_player_aggregates(self.connection)

    def test_aggregated_event_counts_match_source_payloads(self):
        aggregates = self.aggregates()
        aggregate = next(
            row for row in aggregates
            if any(value for value in row.metric_counts.values())
        )
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT e.event_type, e.location_x, e.pass_completed, e.shot_outcome,
                       e.source_payload
                FROM statsbomb_events AS e
                JOIN statsbomb_matches AS m ON m.match_id = e.match_id
                WHERE m.competition_id = %s AND m.season_id = %s
                  AND e.player_id = %s
                """,
                (scouting.COMPETITION_ID, scouting.SEASON_ID, aggregate.player_id),
            )
            event_rows = cursor.fetchall()

        counts = {key: 0 for key in scouting.METRIC_COUNT_KEYS}
        for event_type, start_x, pass_completed, shot_outcome, payload in event_rows:
            if event_type == "Pass":
                counts["passes_attempted"] += 1
                counts["passes_completed"] += pass_completed is True
                pass_data = payload.get("pass") or {}
                end_location = pass_data.get("end_location") or []
                end_x = end_location[0] if end_location else None
                end_y = end_location[1] if len(end_location) > 1 else None
                if scouting.is_progressive(start_x, end_x):
                    counts["progressive_passes_attempted"] += 1
                    counts["progressive_passes_completed"] += pass_completed is True
                counts["shot_assists"] += pass_data.get("shot_assist") is True
                counts["goal_assists"] += pass_data.get("goal_assist") is True
                counts["completed_box_passes"] += (
                    pass_completed is True
                    and end_x is not None
                    and end_y is not None
                    and end_x >= 102
                    and 18 <= end_y <= 62
                )
            elif event_type == "Carry":
                carry_data = payload.get("carry") or {}
                end_location = carry_data.get("end_location") or []
                end_x = end_location[0] if end_location else None
                counts["progressive_carries"] += scouting.is_progressive(start_x, end_x)
            elif event_type == "Shot":
                counts["shots"] += 1
                counts["goals"] += shot_outcome == "Goal"
                counts["expected_goals"] += (payload.get("shot") or {}).get("statsbomb_xg") or 0
            elif event_type == "Pressure":
                counts["pressures"] += 1
            elif event_type == "Ball Recovery":
                counts["ball_recoveries"] += 1
            elif event_type == "Interception":
                counts["interceptions"] += 1
                outcome = ((payload.get("interception") or {}).get("outcome") or {}).get("name")
                counts["positive_interceptions"] += outcome in scouting.POSITIVE_OUTCOMES
            elif event_type == "Duel":
                duel = payload.get("duel") or {}
                if (duel.get("type") or {}).get("name") == "Tackle":
                    counts["tackle_duels"] += 1
                    outcome = (duel.get("outcome") or {}).get("name")
                    counts["positive_tackle_duels"] += outcome in scouting.POSITIVE_OUTCOMES

        for key, expected in counts.items():
            with self.subTest(metric=key):
                self.assertAlmostEqual(aggregate.metric_counts[key], expected)

    def test_saved_scenarios_return_repeatable_eligible_results(self):
        aggregates = self.aggregates()
        scenarios_path = Path(__file__).with_name("scouting_scenarios.json")
        scenarios = json.loads(scenarios_path.read_text())
        self.assertEqual({scenario["filters"].get("profile", "ball_progressing_midfielder") for scenario in scenarios}, set(scouting.PROFILE_ORDER))

        for scenario in scenarios:
            with self.subTest(scenario=scenario["name"]):
                filters = scouting.ScoutingFilters(**scenario["filters"])
                first = scouting.build_scouting_response(aggregates, filters)
                second = scouting.build_scouting_response(aggregates, filters)
                first_ids = [player.player_id for player in first.results]
                second_ids = [player.player_id for player in second.results]
                self.assertEqual(first_ids, second_ids)
                self.assertEqual(first.result_count, second.result_count)
                self.assertLessEqual(len(first.results), filters.limit)
                for player in first.results:
                    self.assertGreaterEqual(player.minutes_played, filters.min_minutes)
                    self.assertGreaterEqual(player.role_share_pct, filters.min_role_share_pct)
                values = [player.metrics[filters.sort_by] for player in first.results]
                values = [value for value in values if value is not None]
                ordered = sorted(values, reverse=filters.sort_direction == "desc")
                self.assertEqual(values, ordered)

    def test_extreme_minimum_minutes_returns_an_empty_response(self):
        response = scouting.build_scouting_response(
            self.aggregates(), scouting.ScoutingFilters(min_minutes=25000)
        )
        self.assertEqual(response.results, [])
        self.assertEqual(response.result_count, 0)


if __name__ == "__main__":
    unittest.main()
