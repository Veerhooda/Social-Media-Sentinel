# Known Limitations

## Live access

- Live Recent Search and a short Filtered Stream run passed on 2026-09-20 after credits were activated. X billing/credit availability remains an external operational dependency.
- X endpoint availability, quotas, rules, and pricing depend on the current developer account/product.
- No other platform is implemented in this milestone.

## Analytics

- Real sentiment, emotion, and irony checkpoint smoke tests pass, but no domain accuracy evaluation has been performed.
- Irony is not identical to sarcasm in every context.
- Fixed-target stance is not arbitrary-target stance. General-target stance remains explicitly unsupported.
- Temporal analytics support rolling one-hour windows with 15-minute steps and daily summaries.
- BERTrend topic discovery and one real cross-window cooling classification are verified. Only one topic matched across the two windows; the other 11 persisted topics still have insufficient temporal evidence.
- Cross-window identity uses one-to-one Sentence Transformer centroid similarity at a configurable `0.70` threshold, with keyword overlap only as a persistence fallback. This threshold needs evaluation on a larger chronological corpus.
- Acceleration remains unavailable for the real matched topic because it has only two measurements; three are required.
- The embedding model is downloaded to the user's model cache, not committed to Git. First-run model download and CPU inference can be comparatively slow.
- NetworkX is in-memory and intended for bounded/rolling graph windows.
- No follower graph or causal influence is claimed.

## Persistence and operations

- PostgreSQL 16.14 is verified locally. Deployment configuration, backups, retention automation, and production hardening remain outside this milestone.
- The migration includes foundation tables for later demographics/topics, but those services are not implemented.
- The process uses synchronous SQLAlchemy and in-process orchestration; no durable queue is present.
- The filtered-stream runner has adapter-level callbacks/reconnect reporting but has not been live soak-tested.
- The successful stream check was deliberately short and bounded; it is not a long-duration reliability or reconnect soak test.
- The automated suite reports one upstream deprecation warning from Starlette's test client using the deprecated AnyIO `BlockingPortal` alias; application tests still pass.

## Replay

Replay records are synthetic, contain no real users or private data, and are marked with `source_metadata.replay=true`. Replay output must never be described as live X data.

## User interface

The React dashboard is intentionally not started. This milestone stops at the typed FastAPI layer.
