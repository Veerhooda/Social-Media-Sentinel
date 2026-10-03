#!/usr/bin/env bash
# Full prototype check: migrations, backend tests, frontend lint/tests/build, live API smoke test.
# Writes everything to verify_prototype.log. Start run_audience_lab.command first for the live check.
cd "$(dirname "$0")" || exit 1
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
LOG=verify_prototype.log
exec > >(tee "$LOG") 2>&1
echo "== Social Sentinel verification $(date) =="
FAILED=()
step() { local name=$1; shift; echo; echo "-- $name"; if "$@"; then echo "OK: $name"; else echo "FAIL: $name"; FAILED+=("$name"); fi; }

step "database migrations" uv run alembic upgrade head
step "backend lint" uv run ruff check app tests scripts
step "backend tests" uv run pytest -q
cd frontend || exit 1
[ -d node_modules ] || npm ci
step "frontend lint" npm run lint
step "frontend tests" npm test
step "frontend typecheck + build" npm run build
cd ..
if curl -sf http://127.0.0.1:8000/api/health >/dev/null; then
  step "live API smoke test" uv run python scripts/verify_live.py
else
  echo; echo "-- live API smoke test skipped: API not running on :8000 (start run_audience_lab.command)"
fi
echo
if [ ${#FAILED[@]} -eq 0 ]; then echo "== ALL CHECKS PASSED =="; else echo "== FAILED: ${FAILED[*]} =="; fi
echo "Log saved to $(pwd)/$LOG. Press Enter to close."; read -r
