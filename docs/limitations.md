# Known Limitations

## Live access

- Live Recent Search and a short Filtered Stream run passed on 2026-09-20 after credits were activated. X billing/credit availability remains an external operational dependency.
- X endpoint availability, quotas, rules, and pricing depend on the current developer account/product.
- Telegram history and live adapter paths are implemented and locally verified with
  deterministic Telethon-shaped fixtures. Authorized public-channel history passed
  with 3 real messages on 2026-09-21. A bounded 15-second live listener received no
  new update, so genuinely arriving live-event verification remains **SKIPPED**.
- Telegram collection is limited to explicitly selected public channels and public
  supergroups. Private dialogs are rejected. Associated discussion threads work
  only when the authenticated account and target visibility permit them.
- Telegram edits/deletions, participant crawling, follower/member graphs, and media
  byte downloads are not implemented. Hidden forward sources create no graph edge.
- Telegram does not provide a reliable content-language field on each message;
  canonical language remains unknown until the shared language analysis layer is added.

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
- Network cascades are observed interaction trees only: 17 reconstructed on the current corpus, largest 6 events, max depth 3, several partially observable where parents are missing from storage.
- Community identifiers are snapshot-local; cross-window community identity is not tracked.
- Per-event topic assignments are not persisted, so topic-specific cascade analysis is unavailable.
- NDLib diffusion simulation is not integrated.

## Persistence and operations

- PostgreSQL 16.14 is verified locally. Deployment configuration, backups, retention automation, and production hardening remain outside this milestone.
- Demographics: language, geography, and professional-interest aggregates are implemented; age inference is honestly UNAVAILABLE (no validated model). A 2026-09-21 feasibility spike audited the local corpus (0 explicit age cues in 225 bios, 9 weak life-stage mentions, median 1 event per user, no stored image bytes) and rejected M3Inference (image-dependent, 2019 training data, legacy stack, AGPL-3.0), the available HF text-age checkpoints (undocumented labels, negligible adoption, severe domain mismatch), face-age models (no image bytes stored), and keyword heuristics (4% coverage, stereotyping risk). The `AgeModel` interface is kept for a future validated approach; no weak classifier was implemented to make the UI green. Profession sectors are heuristic interest signals, geography is 75% unknown on the current corpus, and language is 100% English on the current corpus.
- The process uses synchronous SQLAlchemy and in-process orchestration; no durable queue is present.
- The filtered-stream runner has adapter-level callbacks/reconnect reporting but has not been live soak-tested.
- The successful stream check was deliberately short and bounded; it is not a long-duration reliability or reconnect soak test.
- Scheduler status is process-local and resets after restart; X/trend cursors and analytical completion markers are durable in PostgreSQL.
- Only one application process should own the scheduler. Multiple scheduler-enabled Uvicorn workers would duplicate dispatch, although database operations remain idempotent.
- Shutdown waits for in-flight jobs up to a timeout; this is graceful local shutdown, not distributed job recovery.
- Temporal sentiment endpoints remain query-derived from persisted NLP, so they require no separate materialization job.
- The automated suite reports one upstream deprecation warning from Starlette's test client using the deprecated AnyIO `BlockingPortal` alias; application tests still pass.

## Replay

Replay records are synthetic, contain no real users or private data, and are marked with `source_metadata.replay=true`. Replay output must never be described as live platform data.

## User interface

The canonical React dashboard is implemented. Current limitations:

- events do not persist per-event BERTrend topic assignments, so the Live Feed topic filter is explicitly unavailable;
- network visualization excludes replay and uses interaction-derived IDs, not follower relationships;
- frontend refresh uses polling rather than WebSocket/SSE;
- `LIVE DATA` denotes real, non-replay rows already stored for a platform; active
  collector state is reported separately and is not inferred from stored rows;
- npm reports two moderate development-tooling advisories; the production dependency audit reports zero vulnerabilities, and no breaking forced upgrade was applied;
- chart-library route chunks remain comparatively large;
- demographics are exposed as an aggregate-only navigation destination with unknown/insufficient-data states; the Settings UI
  remains intentionally unavailable.
