import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql

from data.import_statsbomb import (
    download_selection,
    import_match,
    load_selection,
    normalize_appearances,
    normalize_event,
    parse_game_clock,
)


class NormalizationTests(unittest.TestCase):
    def test_parse_game_clock_returns_elapsed_seconds(self):
        self.assertEqual(parse_game_clock("90:12"), 5412)

    def test_parse_game_clock_rejects_malformed_values(self):
        with self.assertRaises(ValueError):
            parse_game_clock("90")

    def test_appearances_sum_position_intervals_and_ignore_unused_players(self):
        lineups = [
            {
                "team_id": 10,
                "team_name": "North FC",
                "lineup": [
                    {
                        "player_id": 101,
                        "player_name": "Starter",
                        "player_nickname": None,
                        "positions": [
                            {
                                "position_id": 1,
                                "position": "Goalkeeper",
                                "from": "00:00",
                                "to": "45:00",
                                "start_reason": "Starting XI",
                            },
                            {
                                "position_id": 2,
                                "position": "Center Back",
                                "from": "45:00",
                                "to": None,
                                "start_reason": "Tactical Shift",
                            },
                        ],
                    },
                    {
                        "player_id": 102,
                        "player_name": "Substitute",
                        "player_nickname": None,
                        "positions": [
                            {
                                "position_id": 9,
                                "position": "Midfielder",
                                "from": "60:00",
                                "to": None,
                                "start_reason": "Substitution - On",
                            }
                        ],
                    },
                    {"player_id": 103, "player_name": "Unused", "positions": []},
                ],
            }
        ]

        appearances = normalize_appearances(lineups, match_end_seconds=90 * 60)

        self.assertEqual(len(appearances), 2)
        self.assertEqual(appearances[0]["minutes_played"], 90.0)
        self.assertTrue(appearances[0]["started"])
        self.assertEqual(appearances[0]["position_name"], "Goalkeeper")
        self.assertEqual(appearances[1]["minutes_played"], 30.0)
        self.assertFalse(appearances[1]["started"])

    def test_event_preserves_source_ids_and_nullable_values(self):
        source = {
            "id": "35df4e8a-3e9a-4911-b5c6-b507d5c85b68",
            "index": 12,
            "period": 1,
            "minute": 5,
            "second": 7,
            "type": {"id": 30, "name": "Pass"},
            "player": {"id": 101, "name": "Starter"},
            "team": {"id": 10, "name": "North FC"},
            "location": [60.0, 40.0],
            "pass": {"outcome": {"id": 9, "name": "Incomplete"}},
        }

        event = normalize_event(source, match_id=500)

        self.assertEqual(event["event_id"], source["id"])
        self.assertEqual(event["player_id"], 101)
        self.assertEqual(event["team_id"], 10)
        self.assertEqual(event["pass_outcome"], "Incomplete")
        self.assertIsNone(event["shot_outcome"])
        self.assertEqual(event["source_payload"], source)

    def test_zero_length_position_interval_remains_an_appearance(self):
        lineups = [
            {
                "team_id": 10,
                "team_name": "North FC",
                "lineup": [
                    {
                        "player_id": 102,
                        "player_name": "Late Substitute",
                        "positions": [
                            {
                                "position_id": 9,
                                "position": "Midfielder",
                                "from": "90:00",
                                "to": "90:00",
                                "start_reason": "Substitution - On",
                            }
                        ],
                    }
                ],
            }
        ]

        appearance = normalize_appearances(lineups, match_end_seconds=90 * 60)[0]

        self.assertEqual(appearance["minutes_played"], 0.0)
        self.assertEqual(appearance["position_name"], "Midfielder")

    def test_checked_in_selection_pins_the_documented_sample(self):
        selection = load_selection()

        self.assertEqual(selection["competition_id"], 2)
        self.assertEqual(selection["season_id"], 27)
        self.assertEqual(selection["expected_match_count"], 380)
        self.assertEqual(len(selection["source_commit"]), 40)


class DatabaseImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.connection = psycopg.connect(
            os.getenv("TEST_DATABASE_URL", "dbname=football_scouting")
        )
        cls.schema_name = "sb_test_" + uuid4().hex
        cls.connection.execute(
            sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(cls.schema_name))
        )
        cls.connection.execute(
            sql.SQL("SET search_path TO {}").format(sql.Identifier(cls.schema_name))
        )
        schema = Path(__file__).resolve().parents[1] / "schema.sql"
        cls.connection.execute(schema.read_text())

    @classmethod
    def tearDownClass(cls):
        cls.connection.execute(
            sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(cls.schema_name))
        )
        cls.connection.close()

    def test_match_import_is_idempotent_and_metrics_use_minutes(self):
        selection = {
            "source_repository": "https://github.com/hudl/open-data",
            "competition_id": 2,
            "season_id": 27,
            "competition_name": "Premier League",
            "season_name": "2015/2016",
            "source_commit": "a" * 40,
        }
        match = {
            "match_id": 500,
            "match_date": "2016-01-01",
            "home_team": {"home_team_id": 10, "home_team_name": "North FC"},
            "away_team": {"away_team_id": 20, "away_team_name": "South FC"},
            "home_score": 1,
            "away_score": 0,
        }
        lineups = [
            {
                "team_id": 10,
                "team_name": "North FC",
                "lineup": [
                    {
                        "player_id": 101,
                        "player_name": "Starter",
                        "player_nickname": None,
                        "positions": [
                            {
                                "position_id": 23,
                                "position": "Center Forward",
                                "from": "00:00",
                                "to": None,
                                "start_reason": "Starting XI",
                            }
                        ],
                    },
                    {
                        "player_id": 102,
                        "player_name": "Late Substitute",
                        "player_nickname": None,
                        "positions": [
                            {
                                "position_id": 9,
                                "position": "Midfielder",
                                "from": "90:00",
                                "to": "90:00",
                                "start_reason": "Substitution - On",
                            }
                        ],
                    },
                ],
            }
        ]
        events = [
            {
                "id": "00000000-0000-0000-0000-000000000001",
                "index": 1,
                "period": 1,
                "minute": 1,
                "second": 0,
                "type": {"name": "Pass"},
                "team": {"id": 10, "name": "North FC"},
                "player": {"id": 101, "name": "Starter"},
                "pass": {},
            },
            {
                "id": "00000000-0000-0000-0000-000000000002",
                "index": 2,
                "period": 1,
                "minute": 2,
                "second": 0,
                "type": {"name": "Pass"},
                "team": {"id": 10, "name": "North FC"},
                "player": {"id": 101, "name": "Starter"},
                "pass": {"outcome": {"name": "Incomplete"}},
            },
            {
                "id": "00000000-0000-0000-0000-000000000003",
                "index": 3,
                "period": 2,
                "minute": 75,
                "second": 0,
                "type": {"name": "Shot"},
                "team": {"id": 10, "name": "North FC"},
                "player": {"id": 101, "name": "Starter"},
                "shot": {"outcome": {"name": "Goal"}},
            },
            {
                "id": "00000000-0000-0000-0000-000000000004",
                "index": 4,
                "period": 2,
                "minute": 90,
                "second": 0,
                "type": {"name": "Half End"},
            },
        ]

        for _ in range(2):
            import_match(self.connection, selection, match, lineups, events)

        counts = self.connection.execute(
            "SELECT (SELECT count(*) FROM statsbomb_matches), "
            "(SELECT count(*) FROM statsbomb_appearances), "
            "(SELECT count(*) FROM statsbomb_events)"
        ).fetchone()
        metrics = self.connection.execute(
            "SELECT appearances, minutes_played, passes_attempted, passes_completed, "
            "shots, goals, passes_completed_per90 "
            "FROM statsbomb_player_season_metrics WHERE player_id = 101"
        ).fetchone()

        self.assertEqual(counts, (1, 2, 4))
        self.assertEqual(metrics[:6], (1, 90, 2, 1, 1, 1))
        self.assertEqual(float(metrics[6]), 1.0)
        zero_minute_metrics = self.connection.execute(
            "SELECT minutes_played, passes_completed_per90 "
            "FROM statsbomb_player_season_metrics WHERE player_id = 102"
        ).fetchone()
        self.assertEqual(zero_minute_metrics, (0, None))


class DownloadTests(unittest.TestCase):
    def test_download_writes_manifest_and_repairs_a_modified_file(self):
        payloads = {
            "/rev/data/competitions.json": json.dumps(
                [{"competition_id": 2, "season_id": 27}]
            ).encode(),
            "/rev/data/matches/2/27.json": json.dumps(
                [{"match_id": 500, "match_status": "available"}]
            ).encode(),
            "/rev/data/events/500.json": b"[]",
            "/rev/data/lineups/500.json": json.dumps(
                [{"team_id": 10, "team_name": "North FC", "lineup": []}]
            ).encode(),
        }

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                payload = payloads.get(self.path)
                if payload is None:
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *_args):
                pass

        with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            selection = {
                "source_repository": "https://github.com/hudl/open-data",
                "source_commit": "rev",
                "competition_id": 2,
                "season_id": 27,
                "competition_name": "Premier League",
                "season_name": "2015/2016",
                "expected_match_count": 1,
            }
            base_url = f"http://127.0.0.1:{server.server_port}/rev"

            try:
                with tempfile.TemporaryDirectory() as raw_root:
                    manifest = download_selection(
                        selection, Path(raw_root), raw_base_url=base_url
                    )
                    raw_file = (
                        Path(raw_root)
                        / "statsbomb"
                        / "rev"
                        / "data"
                        / "events"
                        / "500.json"
                    )
                    original_hash = json.loads(manifest.read_text())["files"][
                        "data/events/500.json"
                    ]["sha256"]
                    raw_file.write_text("corrupted")
                    repaired_manifest = download_selection(
                        selection, Path(raw_root), raw_base_url=base_url
                    )

                    self.assertEqual(json.loads(raw_file.read_text()), [])
                    self.assertEqual(
                        json.loads(repaired_manifest.read_text())["files"][
                            "data/events/500.json"
                        ]["sha256"],
                        original_hash,
                    )
            finally:
                server.shutdown()
                thread.join()


if __name__ == "__main__":
    unittest.main()
