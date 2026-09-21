# Social Sentinel

AI-driven social-media analytics over a unified, timestamped event timeline.
Collects public X and Telegram activity into canonical PostgreSQL events, then
derives sentiment, emotion, irony, supported stance, BERTrend topics, network
topology, and aggregate demographics behind a FastAPI + React dashboard.

## Problem-statement coverage

The framework addresses five components:

A. Continuous collection and timeline — X Recent Search / Filtered Stream and
Telegram public history / live listener, normalized into one chronological store.
B. Multi-dimensional sentiment — positive/neutral/negative, fine-grained
emotion (GoEmotions, with `nervousness` mapped to the product term anxiety),
irony, and fixed-target stance, all with confidence and temporal aggregation.
C. Demographic profiling — aggregate geography, language, and professional
interests with unknown handling. Age is deliberately UNAVAILABLE (see below).
D. Trend and topic detection — BERTrend discovery, velocity, cross-window
evolution, and honest insufficient-data states.
E. Link analysis — interaction graph with degree, betweenness, closeness,
PageRank, HITS, Louvain communities, temporal snapshots, observed cascades,
and propagation paths. Structural metrics only; no causal claims, no follower
graph.

## What is implemented

X ingestion, Telegram ingestion, canonical events, PostgreSQL timeline,
sentiment, emotion, irony, supported stance, temporal analytics, BERTrend,
continuous scheduler jobs, NetworkX analysis, communities, observed cascades,
aggregate demographics, FastAPI, React dashboard, replay mode, health/job status.

## Deliberately unavailable

- Age inference: the corpus carries no validated age evidence, so the API and
dashboard report UNAVAILABLE instead of fabricated brackets.
- Arbitrary-target stance: fixed-target models are never misused as general
stance engines.
- YouTube and Reddit: COMING SOON. Meta/Instagram/Facebook: PLANNED, inactive.
- Per-event topic labels, follower graphs, diffusion simulation: not present.

## Architecture

```text
X ───────────┐
Telegram ────┤
             ▼
      Platform Adapters
             ▼
       Canonical Events
             ▼
         PostgreSQL
             ▼
 ┌───────────┼────────────┐
 ▼           ▼            ▼
 NLP      BERTrend       Graph
 │           │            │
 │      Topic Evolution   │
 │                        │
 └───────────┼────────────┘
             ▼
        FastAPI API
             ▼
        React Dashboard
```

Data flow: collection → normalization → persistence → NLP → trends →
graph → aggregation → API → UI. Analytics modules sit behind
application-level interfaces; SQL stays in repositories; platform objects
never leak past adapters. Full detail: `docs/architecture.md`. Requirement
mapping: `docs/ps-coverage.md`.

## Stack

Python 3.13, Pydantic, PostgreSQL 16, FastAPI, Uvicorn, React + Vite,
NetworkX, Transformers/PyTorch (CardiffNLP sentiment/irony, GoEmotions),
BERTrend/BERTopic, Tweepy (X), Telethon (Telegram), Alembic, Vitest.

## Install

```bash
uv sync --extra dev --extra trend
cp .env.example .env
cd frontend && npm install && cd ..
```

## Configure

`.env` holds placeholders only and is never committed. Live X collection needs
`X_BEARER_TOKEN`; live Telegram needs `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`,
and an authorized `TELEGRAM_SESSION_STRING`. With credentials absent, live
commands report SKIPPED. The standard demo needs no credentials at all.

## Start PostgreSQL

Use a local PostgreSQL 16+ instance and point `DATABASE_URL` at it, e.g.
`postgresql+psycopg://social_analytics:change-me@localhost:5432/social_analytics`.

## Run migrations

```bash
uv run alembic upgrade head
```

Schema-only; stored data is untouched. `uv run alembic check` must report no drift.

## Start the backend

```bash
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Health: `http://127.0.0.1:8000/api/health`. The scheduler is off unless
`SCHEDULER_ENABLED=true`, and exactly one process may own it.

## Start the frontend

```bash
cd frontend && npm run dev -- --host 127.0.0.1 --port 5173
```

Open `http://127.0.0.1:5173`. Verify with `npm run build`, `npm test`, `npm run lint`.

## Local demo

One command, read-only, no credentials, no downloads, no collection:

```bash
./scripts/demo.sh
```

It validates the environment (`scripts/demo_check.py`: database, schema,
stored rows, migrations, backend import, frontend build), applies migrations,
starts FastAPI with the scheduler disabled, and starts Vite. Follow the judge
runbook in `docs/demo.md`. Demo data states: REAL DATA (stored non-replay),
REPLAY (labeled synthetic), UNAVAILABLE, COMING SOON.

## Replay mode

Synthetic X-shaped events live in `data/replay/x_synthetic.jsonl`, always
labeled `replay`. Load them without touching live platforms:

```bash
uv run python scripts/run_replay.py
```

Replay output must never be described as live platform data.

## Live ingestion (separate from the demo)

```bash
uv run python scripts/run_x_search.py
uv run python scripts/run_telegram_history.py public_channel --max-messages 20
```

Bounded, credential-gated, and SKIPPED without configuration. Private
Telegram conversations are out of scope.

## Known limitations

Rising/cooling evidence is thin (one matched topic); several cascades are
partially observable; geography is 75% unknown; profession sectors are
heuristic interest signals; the scheduler is process-local without soak
testing. Full list: `docs/limitations.md`. See `docs/api-access.md` before
describing any source as live.
