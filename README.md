# Social Sentinel

AI-driven social-media analytics over a unified, timestamped event timeline.
Public X, Telegram, and YouTube activity is collected into canonical
PostgreSQL events, analyzed (sentiment, emotion, irony, stance, BERTrend
topics, network topology, aggregate demographics), and served through a
FastAPI backend to a React dashboard. An Audience Lab pre-flights draft
posts against AI agents that each represent one audience segment.

- [Features](#features)
- [Architecture](#architecture)
- [Quickstart](#quickstart)
- [Configuration](#configuration)
- [Verification](#verification)
- [Project structure](#project-structure)
- [Documentation](#documentation)

## Features

**Collect**

- X Recent Search + Filtered Stream (Tweepy), Telegram public history +
  live listener (Telethon), YouTube comment polling (Data API v3).
- Collection targets (X queries, Telegram channels, YouTube videos) are
  managed in the Sources UI and stored in `collection_sources` — nothing is
  hard-coded.
- An 8-job in-process scheduler runs collection, NLP, trends, demographics,
  audience sync, and graph refresh on separate cadences (`SCHEDULER_ENABLED=true`,
  one owning process). Every job can also be triggered once via
  `POST /api/system/jobs/{name}/run` or the Jobs page.

**Analyze**

- Sentiment (positive/neutral/negative), GoEmotions multi-label emotion with
  a `nervousness` → anxiety mapping, irony, and fixed-target stance — all
  with confidence, persisted per event, aggregated over rolling windows.
- BERTrend topic discovery with velocity, cross-window evolution, and honest
  `INSUFFICIENT_DATA` states instead of fabricated virality.
- Interaction graph (replies, mentions, reposts, quotes): degree/betweenness/
  closeness, PageRank, HITS, Louvain communities, temporal snapshots, and
  observed (never inferred) propagation cascades.
- Aggregate-only demographics (language, geography, professional interests)
  with unknown cohorts always shown. Age is UNAVAILABLE by design — the
  corpus carries no validated age evidence.

**Simulate**

- Audience Lab (`/audience-lab`): builds audience segments from collected
  profiles, reacts to a draft post with one agent per segment, has an analyst
  agent rewrite it, and re-tests to measure uplift. Requires a Meta Model
  API key; without one the Lab says so instead of faking results.

**Operate honestly**

- Every number on screen comes from the API or shows an explicit empty /
  insufficient / unavailable state. Replay fixtures are always badged
  REPLAY. Live commands print SKIPPED when credentials are absent.

## Architecture

```text
                    ┌─ Sources UI (/data-sources) ─ collection_sources ─┐
                    │                                                   │
X ──────────┐       │                                                   │
Telegram ───┼─► Platform Adapters ─► Canonical Events ─► PostgreSQL ◄───┘
YouTube ────┘ (polling)                       │              ▲
                                              ▼              │
                                   ┌─────────────────────┐   │  8-job scheduler
                                   │ NLP · BERTrend      │───┘  (collection, NLP,
                                   │ Graph · Demographics│      trends, demographics,
                                   └─────────────────────┘      audience sync, graph)
                                              │
                        audience_profiles ────┼──► Audience Lab ─► Meta Model API
                        (segments, simulations)│      (opt-in, key required)
                                              ▼
                                         FastAPI (/api/*)
                                              ▼
                              React (landing + dashboard routes)
```

Collection → normalization → persistence → analysis → API → UI. Analytics
modules sit behind application-level interfaces; SQL stays in repositories;
platform objects never leak past adapters. Full detail:
`docs/architecture.md`; requirement mapping: `docs/ps-coverage.md`.

## Quickstart

```bash
# 1. Backend dependencies and env
uv sync --extra dev --extra trend
cp .env.example .env

# 2. PostgreSQL 16+ (example DSN for DATABASE_URL in .env)
# postgresql+psycopg://social_analytics:change-me@localhost:5432/social_analytics

# 3. Schema (stored data is untouched; `alembic check` must report no drift)
uv run alembic upgrade head

# 4. Backend (scheduler off unless SCHEDULER_ENABLED=true)
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
# health: http://127.0.0.1:8000/api/health

# 5. Frontend
cd frontend && npm install && npm run dev -- --host 127.0.0.1 --port 5173
# open http://127.0.0.1:5173 → "Open dashboard" or "Test a post"
```

**Read-only local demo** (no credentials, no downloads, no collection):

```bash
./scripts/demo.sh
```

It validates the environment, starts the API with the scheduler disabled,
and starts Vite. Judge runbook: `docs/demo.md`. Synthetic fixtures (always
labeled replay) can be loaded with `uv run python scripts/run_replay.py`.

## Configuration

`.env` holds placeholders only and is never committed.

| Need | Setting |
|---|---|
| PostgreSQL | `DATABASE_URL` |
| X collection | `X_BEARER_TOKEN` (+ `X_QUERY` or Sources UI) |
| Telegram collection | `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_SESSION_STRING` |
| YouTube polling | `YOUTUBE_API_KEY` |
| Continuous collection | `SCHEDULER_ENABLED=true` (exactly one process) |
| Audience Lab | `META_MODEL_API_KEY` (+ `AUDIENCE_LAB_MODEL`) |

Without credentials, live paths report SKIPPED — never fake success.

## Verification

```bash
uv run ruff check app tests scripts migrations
uv run pytest -q
cd frontend && npm run lint && npm test && npm run build
```

Live smoke test against a running API: `uv run python scripts/verify_live.py`.
Model/key check for the Lab: `uv run python scripts/audience_lab_live_check.py`.

## Project structure

```text
app/            FastAPI service (platforms, nlp, trends, graph, demographics,
                audience_lab, sources, scheduler, analytics, api, db, pipeline)
frontend/       React + Vite dashboard (pages, components, charts, api layer)
migrations/     Alembic revisions (schema only)
scripts/        Bounded operational commands (demo, replay, collectors, checks)
tests/          Unit + integration suites (PostgreSQL-backed)
data/replay/    Labeled synthetic fixtures for the credential-free demo
docs/           Live references + index (specs.md is the frozen pre-build contract)
```

## Documentation

Full index: `docs/README.md`. Honest limits: `docs/limitations.md`.
Platform access notes: `docs/api-access.md`. Deliberately out of scope:
Reddit/Meta collectors (roadmap, no UI badges), per-event topic labels,
follower graphs, diffusion simulation, age inference.
