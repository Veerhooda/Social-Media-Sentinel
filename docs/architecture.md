# Architecture

## First product milestone

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

The same downstream path accepts clearly labeled canonical replay events. Telegram, YouTube, Meta, Reddit, demographics, the BERTrend service integration, and React are not implemented in this milestone.

## Boundaries

- `app/platforms/x`: all Tweepy and X-response knowledge.
- `app/models`: platform-independent canonical contracts.
- `app/db`: SQLAlchemy models, PostgreSQL connection, repositories.
- `app/nlp`: direct Transformers checkpoint loading and stable result contracts.
- `app/analytics`: source-time temporal aggregation and lightweight hashtag trends.
- `app/trends`: platform-independent micro-batching, BERTrend adaptation, topic persistence, and evolution queries.
- `app/graph`: event relationship extraction and NetworkX algorithms.
- `app/pipeline`: shared live/replay orchestration.
- `app/api`: typed FastAPI responses.

No platform response object passes beyond the X mapper. No frontend talks directly to X.

BERTrend reads canonical text and source timestamps from PostgreSQL. It has no dependency on Tweepy or the X adapter, so future canonical Telegram, YouTube, Meta, or Reddit events can use the same service.

## Honest operating modes

- **Live X:** requires a valid bearer token and account access to the requested endpoint.
- **Replay:** uses synthetic canonical events with `source_metadata.replay=true`.
- **Mixed:** the selected response contains both real X and replay events.
- **Idle:** API is available but no stream is active.
