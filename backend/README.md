# Backend

This folder will hold the FastAPI service, PostgreSQL access, and local-model adapter. FastAPI validates typed filters and builds deterministic queries; LangChain talks to Ollama for question interpretation and report drafting. Keep model prompts and parsing separate from metric calculations.

Sprint 0 exposes `GET /api/health`. It runs `SELECT 1` against the local `football_scouting` database and reports whether FastAPI and PostgreSQL are connected. When PostgreSQL is unavailable, the route returns HTTP 503 and a short status body. Later sprints add ingestion-facing data access, search, and evaluation-backed AI routes. Keep tests beside the related Python modules.

Start the full local stack with `./infra/dev.sh` from the repository root. `requirements.txt` pins the API's direct dependencies; the script creates a local `.venv` on first run. The backend accepts `DATABASE_URL` if a non-default PostgreSQL connection is needed.
