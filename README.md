# Social Sentinel

Social Sentinel is an X-first social-media analytics framework. The first vertical slice is:

```text
X recent search / filtered stream (or labeled replay)
  -> canonical Pydantic event
  -> PostgreSQL
  -> sentiment, emotion, irony, supported stance
  -> temporal aggregation
  -> interaction graph and NetworkX metrics
  -> FastAPI
```

## Local setup

Requirements: Python 3.13 and PostgreSQL 16+.

```bash
uv sync --extra dev --extra trend
cp .env.example .env
uv run alembic upgrade head
uv run python scripts/smoke_test.py
uv run pytest
uv run uvicorn app.main:app --reload
```

Transformer weights are downloaded only when explicitly enabled or when the model smoke test is run. Live X checks require `X_BEARER_TOKEN`; otherwise they are reported as skipped. Replay data is synthetic and is always labeled as replay.

See `docs/api-access.md` and `docs/limitations.md` before describing any source as live.
