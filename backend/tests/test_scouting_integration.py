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
        fetch = getattr(scouting, "fetch_player_aggregates", None)
        self.assertIsNotNone(fetch, "the PostgreSQL scouting query is not implemented")
        return fetch(self.connection)

    def test_progressive_counts_match_source_event_payloads(self):
        aggregates = self.aggregates()
        aggregate = next(
            row for row in aggregates
            if row.progressive_passes_attempted or row.progressive_carries
        )
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT e.event_type, e.location_x, e.pass_completed, e.source_payload
                FROM statsbomb_events AS e
                JOIN statsbomb_matches AS m ON m.match_id = e.match_id
                WHERE m.competition_id = %s AND m.season_id = %s
                  AND e.player_id = %s AND e.event_type IN ('Pass', 'Carry')
                """,
                (scouting.COMPETITION_ID, scouting.SEASON_ID, aggregate.player_id),
            )
            event_rows = cursor.fetchall()

        passes_attempted = 0
        passes_completed = 0
        progressive_passes_attempted = 0
        progressive_passes_completed = 0
        progressive_carries = 0
        for event_type, start_x, pass_completed, payload in event_rows:
            if event_type == "Pass":
                passes_attempted += 1
                passes_completed += pass_completed is True
                pass_data = payload.get("pass") or {}
                end_location = pass_data.get("end_location") or []
                end_x = end_location[0] if end_location else None
                if scouting.is_progressive(start_x, end_x):
                    progressive_passes_attempted += 1
                    progressive_passes_completed += pass_completed is True
            elif event_type == "Carry":
                carry_data = payload.get("carry") or {}
                end_location = carry_data.get("end_location") or []
                end_x = end_location[0] if end_location else None
                progressive_carries += scouting.is_progressive(start_x, end_x)

        self.assertEqual(aggregate.passes_attempted, passes_attempted)
        self.assertEqual(aggregate.passes_completed, passes_completed)
        self.assertEqual(aggregate.progressive_passes_attempted, progressive_passes_attempted)
        self.assertEqual(aggregate.progressive_passes_completed, progressive_passes_completed)
        self.assertEqual(aggregate.progressive_carries, progressive_carries)

    def test_five_saved_scenarios_return_repeatable_eligible_results(self):
        aggregates = self.aggregates()
        scenarios_path = Path(__file__).with_name("scouting_scenarios.json")
        scenarios = json.loads(scenarios_path.read_text())
        self.assertEqual(len(scenarios), 5)

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
                    self.assertGreaterEqual(player.central_midfield_share_pct, filters.min_central_share_pct)
                metric_values = [getattr(player, filters.sort_by) for player in first.results]
                values = [value for value in metric_values if value is not None]
                if filters.sort_direction == "desc":
                    self.assertEqual(values, sorted(values, reverse=True))
                else:
                    self.assertEqual(values, sorted(values))

    def test_extreme_minimum_minutes_returns_an_empty_response(self):
        aggregates = self.aggregates()
        filters = scouting.ScoutingFilters(min_minutes=25000)
        response = scouting.build_scouting_response(aggregates, filters)
        self.assertEqual(response.results, [])
        self.assertEqual(response.result_count, 0)


if __name__ == "__main__":
    unittest.main()
