"""Lightweight local demo validation.

Read-only with respect to the stored corpus. It never contacts X or
Telegram, never downloads models, and never runs BERTrend. Exit 0 when
the demo can start, 1 otherwise. Prints PASS / FAIL / WARNING lines.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

results: list[tuple[str, str, str]] = []


def report(name: str, status: str, detail: str = "") -> None:
    results.append((name, status, detail))
    print(f"{status:7} {name}" + (f" — {detail}" if detail else ""))


def main() -> int:
    # 1. Environment: demo must not auto-start ingestion.
    scheduler = os.getenv("SCHEDULER_ENABLED", "false").lower()
    if scheduler in ("1", "true", "yes", "on"):
        report("demo-mode", "FAIL", "SCHEDULER_ENABLED must be false for the read-only demo")
    else:
        report("demo-mode", "PASS", "scheduler disabled; no ingestion will start")

    # 2. PostgreSQL reachable + expected tables + stored data.
    try:
        from sqlalchemy import func, inspect, select

        from app.db.models import SocialEvent
        from app.db.session import SessionLocal

        with SessionLocal() as session:
            tables = set(inspect(session.bind).get_table_names())
        expected = {
            "social_users", "social_events", "nlp_analysis", "user_demographics",
            "graph_edges", "topics", "trend_measurements", "analytics_checkpoints",
        }
        missing = sorted(expected - tables)
        if missing:
            report("database-schema", "FAIL", f"missing tables: {', '.join(missing)}")
        else:
            report("database-schema", "PASS", "all expected tables present")
        with SessionLocal() as session:
            total = session.scalar(select(func.count()).select_from(SocialEvent)) or 0
        if total == 0:
            report("demo-data", "WARNING", "no stored events; load replay data (see docs/demo.md)")
        else:
            report("demo-data", "PASS", f"{total} stored events available")
    except Exception as exc:
        report("database", "FAIL", f"PostgreSQL unreachable: {exc}")

    # 3. Check the applied revision without running autogenerate.
    try:
        from alembic.config import Config
        from alembic.runtime.migration import MigrationContext
        from alembic.script import ScriptDirectory

        from app.db.session import engine

        config = Config(str(ROOT / "alembic.ini"))
        head = ScriptDirectory.from_config(config).get_current_head()
        with engine.connect() as connection:
            revision = MigrationContext.configure(connection).get_current_revision()
        if revision == head:
            report("migrations", "PASS", f"database at revision {head}")
        else:
            report("migrations", "FAIL", f"database revision {revision}; expected {head}")
    except Exception as exc:
        report("migrations", "FAIL", str(exc))

    # 4. FastAPI app imports without contacting platforms or models.
    try:
        from app.main import create_app  # noqa: F401

        report("backend-import", "PASS", "FastAPI app imports cleanly")
    except Exception as exc:
        report("backend-import", "FAIL", str(exc))

    # 5. Frontend build output present for the demo.
    dist = ROOT / "frontend" / "dist" / "index.html"
    if dist.exists():
        report("frontend-build", "PASS", "frontend/dist/index.html present")
    else:
        report("frontend-build", "WARNING", "run `npm run build` in frontend/ first")

    # 6. No live credentials required (informational only; never printed).
    creds = sum(
        1 for key in ("X_BEARER_TOKEN", "TELEGRAM_SESSION_STRING") if os.getenv(key)
    )
    report(
        "credentials",
        "PASS" if creds == 0 else "WARNING",
        "no live credentials in environment" if creds == 0 else "live credentials present; demo stays read-only",
    )

    failed = sum(1 for _, status, _ in results if status == "FAIL")
    print(f"demo_check: {len(results) - failed}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
