#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
PNPM_BIN="${PNPM_BIN:-pnpm}"
POSTGRES_BIN_DIR="${POSTGRES_BIN_DIR:-/Applications/Postgres.app/Contents/Versions/latest/bin}"
API_PORT="${API_PORT:-8000}"
UI_PORT="${UI_PORT:-5173}"
export SCOUTING_API_PROXY_URL="${SCOUTING_API_PROXY_URL:-http://127.0.0.1:$API_PORT}"

if [[ -d "$POSTGRES_BIN_DIR" ]]; then
  export PATH="$POSTGRES_BIN_DIR:$PATH"
fi

for command_name in node pg_isready psql createdb; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "Missing $command_name. See the local setup instructions in README.md." >&2
    exit 1
  fi
done

if ! command -v "$PNPM_BIN" >/dev/null 2>&1; then
  echo "Missing pnpm. See the local setup instructions in README.md." >&2
  exit 1
fi

if ! "$PYTHON_BIN" -c 'import sys; sys.exit(sys.version_info < (3, 12))'; then
  echo "Python 3.12 or newer is required. Set PYTHON_BIN if needed." >&2
  exit 1
fi

if ! pg_isready -q; then
  echo "PostgreSQL is not running. Start and initialize Postgres.app, then retry." >&2
  exit 1
fi

if ! psql -d postgres -Atqc "SELECT 1 FROM pg_database WHERE datname = 'football_scouting'" | grep -qx 1; then
  createdb football_scouting
fi

if [[ ! -x "$PROJECT_DIR/backend/.venv/bin/python" ]]; then
  "$PYTHON_BIN" -m venv "$PROJECT_DIR/backend/.venv"
fi

"$PROJECT_DIR/backend/.venv/bin/python" -m pip install -r "$PROJECT_DIR/backend/requirements.txt"

if [[ ! -d "$PROJECT_DIR/frontend/node_modules" ]]; then
  (cd "$PROJECT_DIR/frontend" && "$PNPM_BIN" install --frozen-lockfile)
fi

(cd "$PROJECT_DIR" && "$PROJECT_DIR/backend/.venv/bin/python" -m uvicorn backend.main:app --reload --host 127.0.0.1 --port "$API_PORT") &
API_PID=$!
(cd "$PROJECT_DIR/frontend" && "$PNPM_BIN" dev --host 127.0.0.1 --port "$UI_PORT" --strictPort) &
UI_PID=$!

cleanup() {
  kill "$API_PID" "$UI_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Workbench: http://127.0.0.1:$UI_PORT"
echo "API health: http://127.0.0.1:$API_PORT/api/health"
echo "Press Ctrl+C to stop both development servers."

while kill -0 "$API_PID" 2>/dev/null && kill -0 "$UI_PID" 2>/dev/null; do
  sleep 1
done
wait "$API_PID" "$UI_PID" || true
exit 1
