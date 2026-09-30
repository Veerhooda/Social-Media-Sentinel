# Architecture

## Verified platform milestones

The implementation priority was changed on 2026-09-20 from the older Telegram-first plan to this X-first vertical slice:

```text
X recent search / filtered stream
  -> X mapper
  -> canonical event validation
  -> PostgreSQL
  -> NLP
  -> one-hour/daily temporal analytics
  -> interaction-edge persistence
  -> NetworkX metrics
  -> FastAPI
```

The second platform milestone adds Telegram without changing that downstream path:

```text
Telethon public history / NewMessage
  -> Telegram mapper
  -> the same CanonicalEvent/PostgreSQL/NLP/temporal/BERTrend/NetworkX/FastAPI path
```

The same downstream path accepts clearly labeled canonical replay events and
YouTube comments from the polling adapter. Meta and Reddit remain unimplemented.
The aggregate demographic service provides language, geography and professional
interest estimates; age remains unavailable. BERTrend and React are shared
services without platform-specific Telegram or YouTube logic.

## Boundaries

- `app/platforms/x`: all Tweepy and X-response knowledge.
- `app/platforms/telegram`: all Telethon connection, history, live-update, and mapping knowledge.
- `app/platforms/youtube`: all YouTube Data API usage, bounded pagination, reply completion, and mapping knowledge.
- `app/models`: platform-independent canonical contracts.
- `app/db`: SQLAlchemy models, PostgreSQL connection, repositories.
- `app/nlp`: direct Transformers checkpoint loading and stable result contracts.
- `app/analytics`: source-time temporal aggregation and lightweight hashtag trends.
- `app/trends`: platform-independent micro-batching, BERTrend adaptation, topic persistence, and evolution queries.
- `app/graph`: event relationship extraction and NetworkX algorithms.
- `app/pipeline`: shared live/replay orchestration.
- `app/api`: typed FastAPI responses.

No platform response object passes beyond its mapper. No frontend talks directly to X or Telegram.

BERTrend reads canonical text and source timestamps from PostgreSQL. It has no
dependency on Tweepy, Telethon, or either platform adapter. Telegram acceptance is
verified through this same document/repository/service boundary; insufficient
source-time windows remain an explicit outcome.

## Continuous scheduler

`app/scheduler` is a lightweight standard-library thread scheduler owned by FastAPI lifespan. It coordinates existing services without containing their business logic:

```text
SchedulerService
  ├─ x_recent_search  -> XAdapter -> canonical event repository
  ├─ nlp_processing   -> NLPService -> nlp_analysis
  ├─ trend_analysis   -> TrendService -> topics/measurements
  └─ graph_refresh    -> GraphBuilder -> graph_edges
```

PostgreSQL checkpoints preserve the X `since_id` cursor and the latest event included in a successful trend refresh. `social_events.graph_processed_at` marks graph work even when an event produces no edge. Missing `nlp_analysis` rows identify pending NLP work.

Per-job locks prevent overlap. One job failure is recorded without stopping other jobs. FastAPI shutdown stops dispatch and waits for active jobs. `/api/system/jobs` reports last/next run, last and cumulative counts, duration, failure, and overlap skips. Runtime status resets on restart; analytical progress is durable.

## React client

`frontend/` is a TypeScript React/Vite application with a centralized typed API layer and TanStack Query cache. Recharts renders persisted temporal/topic data. Sigma.js renders the interaction map from backend nodes and edges, with a deterministic Graphology/ForceAtlas2 layout, pan/zoom, keyboard-selectable ranked accounts, and explicit connected-core versus all-loaded views. This is a recent-edge sample, not a claim about the complete follower network.

The active UI follows `design.md`'s dark/yellow reference language. The
overview's charcoal stage contains API-backed corpus totals, source coverage,
four analytical signals and a source-time sentiment chart. Other routes use
the same shell, controls and dark analytical surfaces; no crypto-specific
concepts or fabricated profile/notification controls were introduced.
The public `/` route is a separate landing page inspired by Dialed's page
composition (floating navigation, centered editorial hero, staggered
showcase and scroll-driven floral reveal). A passive scroll listener updates
the rose reveal within a sticky section; reverse scrolling reverses it and
reduced-motion users see a static bloom. Its previews are explicitly
illustrative; it makes no live-data claims. `/dashboard` remains the
API-backed overview behind the existing app shell, and all other analytical
routes retain their URLs.

The client never creates analytical labels or random graph data. It displays explicit live, replay, mixed, insufficient, loading, empty, error, and unavailable states.
The health contract provides one aggregated platform summary, avoiding separate
count/timestamp requests for X and Telegram. Live Feed platform selection is sent
to the canonical repository query rather than filtering only the currently loaded
page. Text, author/hashtag, NLP, and interaction filters also run in PostgreSQL
before pagination, with a matching total count. The frontend uses a short
search debounce and announces result updates to assistive technology.

## Honest operating modes

- **Live X:** requires a valid bearer token and account access to the requested endpoint.
- **Live Telegram:** requires all three MTProto settings plus an already authorized session and explicit public-channel targets.
- **Replay:** uses synthetic canonical events with `source_metadata.replay=true`.
- **Mixed:** the selected response contains more than one real/replay source mode.
- **Idle:** API is available but no stream is active.

## System diagrams

High-level architecture (only components that exist):

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

Data flow:

```text
Collection
→ normalization
→ persistence
→ NLP
→ trends
→ graph
→ aggregation
→ API
→ UI
```

Continuous analytics (single scheduler-owning process, opt-in only):

```text
X
→ scheduler
→ processing
→ updated analytics
→ dashboard
```

Replay fixtures enter through the same canonical-event boundary and are
labeled `replay` end to end. No Kafka, Redis, Celery, or Kubernetes is used.
