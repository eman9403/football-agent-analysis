# Backend

This folder holds the FastAPI service, PostgreSQL access, and optional local-model adapter. FastAPI validates typed filters and builds deterministic queries; LangChain talks to Ollama for question interpretation and evidence selection. Keep model prompts and parsing separate from metric calculations.

`GET /api/health` runs `SELECT 1` against the local `football_scouting` database and reports whether FastAPI and PostgreSQL are connected. `GET /api/ai/status` checks whether the configured Ollama model is available. `POST /api/ai/interpret` returns a filter proposal that the scout reviews before applying. `POST /api/reports/player` builds a role-matched evidence dossier; when Ollama is absent, it uses deterministic metric selection and still returns a usable dossier. Keep tests beside the related Python modules.

Start the full local stack with `./infra/dev.sh` from the repository root. The script creates `backend/.venv` when needed and installs the pinned direct dependencies from `requirements.txt`. The backend accepts `DATABASE_URL` if a non-default PostgreSQL connection is needed. Optional Ollama configuration is documented in `docs/local-ai.md`.
