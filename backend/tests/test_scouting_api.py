import unittest
from unittest.mock import patch

from fastapi import HTTPException
import psycopg

import backend.main as main
from backend.scouting import ScoutingFilters


class ScoutingApiTests(unittest.TestCase):
    def test_openapi_exposes_the_typed_scouting_endpoint(self):
        schema = main.app.openapi()
        self.assertIn("/api/scouting/players", schema["paths"])
        operation = schema["paths"]["/api/scouting/players"]["get"]
        self.assertEqual(operation["responses"]["200"]["description"], "Successful Response")

    def test_database_connection_failure_returns_503_without_candidates(self):
        endpoint = getattr(main, "get_scouting_players", None)
        self.assertIsNotNone(endpoint, "the scouting endpoint handler is not implemented")
        with patch("backend.main.psycopg.connect", side_effect=psycopg.OperationalError("offline")):
            with self.assertRaises(HTTPException) as raised:
                endpoint(ScoutingFilters())

        self.assertEqual(raised.exception.status_code, 503)
        self.assertIn("PostgreSQL", raised.exception.detail)


if __name__ == "__main__":
    unittest.main()
