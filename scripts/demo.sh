#!/usr/bin/env bash
# Social Sentinel local demo (read-only).
# Uses the existing local PostgreSQL corpus. Never contacts X or Telegram,
# never downloads models, never runs collection. Scheduler stays disabled.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== Social Sentinel demo =="
command -v uv >/dev/null || { echo "FAIL: uv is required"; exit 1; }
command -v npm >/dev/null || { echo "FAIL: npm is required"; exit 1; }

echo "-- validating demo environment"
SCHEDULER_ENABLED=false uv run python scripts/demo_check.py

echo "-- applying migrations (schema only, data untouched)"
uv run alembic upgrade head >/dev/null
echo "migrations current"

export SCHEDULER_ENABLED=false
echo "-- starting FastAPI (scheduler disabled, read-only demo)"
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 &
API_PID=$!
trap 'kill $API_PID 2>/dev/null || true' EXIT
sleep 4
curl -sf http://127.0.0.1:8000/api/health >/dev/null
echo "backend: http://127.0.0.1:8000/api/health"

echo "-- starting frontend"
cd frontend
if [ ! -d node_modules ]; then npm install; fi
npm run dev -- --host 127.0.0.1 --port 5173 &
UI_PID=$!
trap 'kill $API_PID $UI_PID 2>/dev/null || true' EXIT
wait $UI_PID
