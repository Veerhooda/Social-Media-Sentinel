# Social Sentinel

Social Sentinel is a canonical multi-platform social-media analytics framework. X
is the first verified real platform; Telegram is the second integrated adapter.
Both use the same downstream slice:

```text
X recent search / filtered stream, Telegram public history/live, or labeled replay
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

After canonical events are stored, run the isolated trend service with:

```bash
uv run python scripts/run_trends.py --platform x --allow-model-download
```

The first run downloads the configured Sentence Transformer model. Later runs use the local model cache. Topic discovery and temporal evolution status are reported separately so a single populated window is never described as a rising trend.

## Telegram

Configure `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, and an authorized
`TELEGRAM_SESSION_STRING` in `.env`. Never commit the session. Bounded public-channel
history and a short controlled live run are available with:

```bash
uv run python scripts/run_telegram_history.py public_channel --max-messages 20
uv run python scripts/run_telegram_stream.py --channel public_channel --duration-seconds 30
```

Private conversations are out of scope. When the three settings are absent, these
commands report `SKIPPED` without fabricating events.

## Continuous analytics

Enable the lightweight in-process scheduler for a single Uvicorn worker:

```bash
SCHEDULER_ENABLED=true uv run uvicorn app.main:app
```

The scheduler starts and stops with FastAPI lifespan and runs four isolated jobs:

- bounded X Recent Search collection;
- NLP for events without an `nlp_analysis` row;
- graph extraction for events without a graph-processing marker;
- BERTrend only when newly collected canonical events exist.

Intervals and batch behavior are configured with:

```dotenv
X_SEARCH_INTERVAL_SECONDS=60
NLP_PROCESSING_INTERVAL_SECONDS=30
TREND_INTERVAL_SECONDS=900
GRAPH_INTERVAL_SECONDS=300
SCHEDULER_TICK_SECONDS=1
ANALYTICS_JOB_BATCH_SIZE=100
ANALYTICS_INCLUDE_REPLAY=false
```

Inspect `/api/system/jobs` and `/api/health`. A bounded local verification can be run with:

```bash
uv run python scripts/run_scheduler.py --duration-seconds 25
```

Use one scheduler-owning process. Multiple scheduler-enabled Uvicorn workers would each dispatch jobs.

## React dashboard

The dashboard is a TypeScript/Vite client of FastAPI. Start the backend, then:

```bash
cd frontend
npm install
npm run dev
```

Vite serves `http://127.0.0.1:5173` and proxies `/api` to FastAPI on port 8000. Use `npm run build`, `npm run test`, and `npm run lint` for verification. Centralized query caching polls live events every 5 seconds, system health/jobs every 10 seconds, and broader analytics every 30 seconds.

Transformer weights are downloaded only when explicitly enabled or when the model smoke test is run. Live X checks require `X_BEARER_TOKEN`; live Telegram checks require all three Telegram settings and an authorized public-channel session. Missing credentials are reported as skipped. Replay data is synthetic and is always labeled as replay.

See `docs/api-access.md` and `docs/limitations.md` before describing any source as live.
