# Dependencies

Verified on 2026-09-20 using CPython 3.13.11 on macOS arm64.

| Component | Installed version | Python requirement / role | Verification |
|---|---:|---|---|
| Python | 3.13.11 | Primary runtime | PASS |
| PostgreSQL | 16.14 | Timeline/persistence | PASS: connection and migration |
| Pydantic | 2.13.5 | Canonical/API schemas | PASS |
| FastAPI | 0.141.1 | HTTP API | PASS |
| Uvicorn | 0.53.0 | ASGI server | PASS |
| Tweepy | 4.17.0 | X recent search/stream | PASS: import and interface tests |
| Telethon | 1.45.0 | Telegram public history/live updates | PASS: import, mapper, history, retry, reconnect, shutdown tests; live SKIPPED |
| Transformers | 4.57.6 | Direct model loading | PASS |
| PyTorch | 2.14.0 | Model inference | PASS |
| NetworkX | 3.6.1 | Graph analytics | PASS: PageRank and test suite |
| BERTrend | 0.4.18 | Topic/trend service | PASS: real cross-window and scheduled refresh |
| SQLAlchemy | 2.0.54 | Repository/data access | PASS |
| Psycopg | 3.3.6 | PostgreSQL driver | PASS |
| Node.js | 22.22.0 | Frontend runtime/tooling | PASS |
| React | 19.3.0 | Dashboard UI | PASS: real browser verification |
| Vite | 7.3.6 | Frontend build/dev server | PASS |
| Recharts | 3.10.1 | Analytics charts | PASS |
| TanStack Query | 5.103.1 | Central query cache/polling | PASS |
| Sigma.js | 3.0.3 | WebGL interaction map | PASS: desktop/mobile browser rendering and controls |
| Graphology | 0.26.0 | Directed graph view model | PASS: deterministic graph unit tests |
| ForceAtlas2 | 0.10.1 | Deterministic graph positioning | PASS: unit and browser checks |

`uv sync --extra dev --extra trend` resolves 307 packages on Python 3.13. BERTrend has a large transitive dependency footprint; both direct and scheduled real-data analysis are verified.

The continuous scheduler uses Python's standard `threading` primitives and adds no Celery, Redis, Kafka, or scheduling dependency.

The 2026-09-23 frontend audit found **0 production-dependency vulnerabilities**
with `npm audit --omit=dev --audit-level=moderate`. The full development
dependency audit still reports 2 moderate Vitest/@vitest/mocker advisories;
the upstream fix requires a major Vitest upgrade and is not part of the UI
runtime. Do not treat this as a clean full audit.

Model smoke tests executed real inference for:

- `cardiffnlp/twitter-roberta-base-sentiment-latest`: PASS; expected labels present.
- `SamLowe/roberta-base-go_emotions`: PASS; native `nervousness` and mapped `anxiety` present.
- `cardiffnlp/twitter-roberta-base-irony`: PASS; binary irony score present.
- `cardiffnlp/twitter-roberta-base-stance-climate`: PASS; `against`/`favor`/`none` labels present.

M3Inference and other legacy demographic dependencies are intentionally absent from the modern environment.

## Verification record

- `uv run pytest -q`: **67 passed**, with one upstream Starlette/AnyIO deprecation warning.
- `uv run ruff check app scripts tests migrations`: **all checks passed**.
- `uv run alembic check`: **no new upgrade operations detected**.
- Telegram-focused unit/shared/integration tests: **18 passed**. This covers current
  Telethon object mapping, source/collection timestamps, sender/media/metrics,
  replies/forwards, malformed input, checkpoints, FloodWait, transient retry,
  reconnect, shutdown, PostgreSQL deduplication, temporal/trend acceptance, graph
  edges, API serialization, and mixed X + Telegram fixture coexistence.
- One cached-model Telegram fixture produced real Cardiff sentiment/irony and
  GoEmotions outputs without downloading or rerunning analysis over stored X data.
- Telegram authorized history verification: **PASS** with 3 real messages from an
  official public channel, 3 persisted NLP results, and 3/3 deliberate duplicates
  rejected. A single 15-second live listener connected and stopped cleanly but
  received no arriving message, so live-arrival verification remains **SKIPPED**.
- BERTrend accepted the 3 real Telegram documents and returned
  **INSUFFICIENT_DATA** because the configured minimum is 10 documents; no topic
  result was fabricated.
- PostgreSQL migration `0001_x_first`: **applied successfully**.
- Real replay run: **4 events stored, 4 NLP results produced, 4 relationship records created**; a second run reported all **4 as duplicates**.
- Required FastAPI checks: **7/7 returned HTTP 200**.
- Live X verification: **10 Recent Search events plus 4 bounded-stream events stored**, **14 real NLP results**, **15 real interaction edges**, and **10/10 deliberate duplicate reprocesses rejected**.
- BERTrend 0.4.18 cross-window verification: **44 canonical real-X documents**, **2 populated 15-minute batches**, **13 window topics**, **1 semantic cross-window match**, **12 persisted topics**, and **13 idempotent measurements**.
- Bounded scheduler verification: **25 seconds**, **10 real X events stored**, **10 NLP results added**, all **58 events graph-marked**, BERTrend refreshed through a third populated source-time window, and operational/API checks passed.
- React verification: **13 frontend tests**, TypeScript production build, ESLint, and real Playwright navigation against PostgreSQL-backed FastAPI.
