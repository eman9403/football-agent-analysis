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
        self.assertIn("/api/scouting/profiles", schema["paths"])
        self.assertIn("/api/ai/status", schema["paths"])
        self.assertIn("/api/ai/interpret", schema["paths"])
        self.assertIn("/api/reports/player", schema["paths"])
        operation = schema["paths"]["/api/scouting/players"]["get"]
        self.assertEqual(operation["responses"]["200"]["description"], "Successful Response")

    def test_profile_catalog_is_available_without_a_database_connection(self):
        profiles = main.get_scouting_profiles()
        self.assertEqual(len(profiles), 4)
        self.assertEqual(profiles[0].profile_key, "ball_progressing_midfielder")

    def test_local_ai_status_is_readable_without_database_access(self):
        from backend.local_ai import OllamaStatus

        with patch.object(
            main.OllamaStatus,
            "inspect",
            return_value=OllamaStatus(
                state="runtime_missing",
                model="qwen3.5:4b",
                base_url="http://127.0.0.1:11434",
                detail="Ollama is not responding.",
            ),
        ):
            result = main.get_local_ai_status()

        self.assertEqual(result.state, "runtime_missing")

    def test_database_connection_failure_returns_503_without_candidates(self):
        endpoint = getattr(main, "get_scouting_players", None)
        self.assertIsNotNone(endpoint, "the scouting endpoint handler is not implemented")
        with patch("backend.main.psycopg.connect", side_effect=psycopg.OperationalError("offline")):
            with self.assertRaises(HTTPException) as raised:
                endpoint(ScoutingFilters())

        self.assertEqual(raised.exception.status_code, 503)
        self.assertIn("PostgreSQL", raised.exception.detail)

    def test_natural_language_route_explains_when_optional_local_model_is_missing(self):
        from backend.local_ai import OllamaStatus

        request = main.InterpretQuestionRequest(question="Find forwards")
        missing = OllamaStatus(
            state="model_missing",
            model="qwen3.5:4b",
            base_url="http://127.0.0.1:11434",
            detail="Download the selected local model first.",
        )
        with patch.object(main.OllamaStatus, "inspect", return_value=missing):
            with self.assertRaises(HTTPException) as raised:
                main.interpret_scouting_question(request)

        self.assertEqual(raised.exception.status_code, 503)
        self.assertIn("Download", raised.exception.detail)


if __name__ == "__main__":
    unittest.main()
