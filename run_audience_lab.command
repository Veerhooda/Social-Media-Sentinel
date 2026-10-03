#!/usr/bin/env bash
# Starts Social Sentinel (API with auto-reload + dashboard). SCHEDULER_ENABLED in .env controls live collection.
cd "$(dirname "$0")" || exit 1
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
LOG=run_audience_lab.log
exec > >(tee "$LOG") 2>&1
echo "== Audience Lab launcher $(date) =="

if command -v pg_isready >/dev/null && ! pg_isready -q -h localhost; then
  echo "-- PostgreSQL not running, trying brew services"
  brew services start postgresql@16 2>/dev/null || brew services start postgresql 2>/dev/null
  sleep 3
fi
pg_isready -h localhost || echo "WARN: PostgreSQL does not look reachable"

echo "-- freeing ports 8000/5173"
lsof -ti tcp:8000 | xargs kill 2>/dev/null; lsof -ti tcp:5173 | xargs kill 2>/dev/null; sleep 1

echo "-- database migrations"
uv run alembic upgrade head || { echo "FAIL: migrations"; read -r; exit 1; }

echo "-- Muse Spark live check"
uv run python scripts/audience_lab_live_check.py

echo "-- starting API on :8000"
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --reload-dir app > api.log 2>&1 &
API_PID=$!
for i in $(seq 1 30); do curl -sf http://127.0.0.1:8000/api/audience-lab/status >/dev/null && break; sleep 1; done
curl -s http://127.0.0.1:8000/api/audience-lab/status; echo

echo "-- starting dashboard on :5173"
cd frontend
[ -d node_modules ] || npm ci
npm run dev -- --host 127.0.0.1 --port 5173 > ../ui.log 2>&1 &
UI_PID=$!
cd ..
for i in $(seq 1 30); do curl -sf http://127.0.0.1:5173 >/dev/null && break; sleep 1; done
open "http://127.0.0.1:5173/dashboard"
echo "== RUNNING: API pid $API_PID, UI pid $UI_PID. Close this window to stop. =="
trap 'kill $API_PID $UI_PID 2>/dev/null' EXIT
wait
