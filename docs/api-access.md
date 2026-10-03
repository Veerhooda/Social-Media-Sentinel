# Platform API Access

## Telegram / Telethon

Telegram is isolated under `app/platforms/telegram` and uses Telethon 1.45.0 with an
in-memory `StringSession`. The adapter exposes:

- `TelegramAdapter.historical(...)` for bounded public-channel/supergroup history;
- `TelegramAdapter.stream(...)` for new-message events with bounded reconnects and
  graceful shutdown;
- `TelegramAdapter.health_check(...)` for configuration or an explicitly requested
  live authorization check.

Configuration is loaded only from environment settings:

```dotenv
TELEGRAM_API_ID=
TELEGRAM_API_HASH=
TELEGRAM_SESSION_STRING=
```

Obtain the API ID/hash from Telegram and create the authorized session outside this
repository. Do not paste credentials into chat, print a session string, or commit a
`.session`/`.session-journal` file.

History accepts a channel, a `1..1000` message bound, optional timezone-aware
start/end times, and a channel-scoped last-message checkpoint. Live collection
requires an explicit channel list and uses Telethon's `NewMessage` handler. Targets
must resolve to a public broadcast channel or public supergroup with a username;
private user dialogs are rejected.

`FloodWaitError` waits for Telegram's server-specified duration before a bounded
retry. Transport/server failures use bounded exponential backoff. Telethon-specific
objects stop at the mapper boundary. Repository uniqueness on
`(platform, platform_post_id)` remains the final duplicate-delivery guard.

Local deterministic mapper/history/stream tests: PASS. On 2026-09-21 an authorized
session completed a bounded pull from Telegram's official public channel: 3 messages
were fetched, normalized, stored, and analyzed. A single 15-second `NewMessage`
listener connected and stopped cleanly but received no arriving update; therefore
live-arrival verification remains **SKIPPED**, not reported as success.

Useful bounded commands (they print `SKIPPED` when credentials are absent):

```bash
uv run python scripts/run_telegram_history.py public_channel --max-messages 20
uv run python scripts/run_telegram_stream.py --channel public_channel --duration-seconds 30
```

References:

- <https://docs.telethon.dev/en/stable/basic/signing-in.html>
- <https://docs.telethon.dev/en/stable/modules/client.html#telethon.client.messages.MessageMethods.iter_messages>
- <https://docs.telethon.dev/en/stable/modules/events.html#telethon.events.newmessage.NewMessage>
- <https://core.telegram.org/api/obtaining_api_id>

## X / Tweepy

## Implemented interfaces

The X adapter uses Tweepy 4.17.0 and keeps API calls inside `app/platforms/x`.

- Recent Search: `XAdapter.search_recent(...)`
- Filtered Stream: `XAdapter.stream(...)`
- Configuration/live-access check: `XAdapter.health_check(...)`

Recent Search is the deterministic first ingestion path. It follows `meta.next_token`, preserves source `created_at`, sets collection time independently, and requests the fields/expansions needed for authors, public metrics, entities, media, and referenced posts.

Filtered Stream manages only rules tagged with the `social-sentinel:` prefix, leaves unrelated account rules intact, and maps Tweepy stream responses through the same canonical mapper.

## Configuration

```dotenv
X_BEARER_TOKEN=
X_CLIENT_ID=
X_CLIENT_SECRET=
X_QUERY=
X_MAX_RESULTS=100
X_STREAM_ENABLED=false
X_SEARCH_INTERVAL_SECONDS=60
```

No topic is hard-coded. `X_QUERY` or a method argument supplies the query.

## Access status

- Adapter implementation: PASS.
- Synthetic response mapping/pagination/error tests: PASS.
- Live recent-search request: PASS; 10 real posts completed the pipeline.
- Live filtered stream: PASS; a bounded run processed 4 arriving events and removed its rule.

### Live verification attempt: 2026-09-20

The first attempt using the bounded query `(OpenAI OR ChatGPT) lang:en -is:retweet` returned `HTTP 402 Payment Required: credits depleted`. After credits were added, the same query returned 10 real posts. All 10 completed persistence and real NLP inference; reprocessing the identical in-memory batch produced 10 duplicates. The bounded filtered-stream test subsequently processed 4 arriving events, disconnected, and removed only its `social-sentinel:` rule. X briefly returned `503 ProvisioningSubscription` while the new subscription was being provisioned; a later bounded retry connected successfully.

Missing credentials never produce fake events or fake success.

## Failure behavior

- `401`/`403`: explicit authentication/access failure; no infinite retry.
- `429`: bounded retry using `retry-after` or rate-limit reset information, capped per attempt.
- `5xx`, connection error, timeout: bounded exponential backoff with jitter.
- Pagination state is read from X response metadata.
- Persistence deduplicates on `(platform, platform_post_id)`.
- A malformed post is logged/reported through the mapper error hook while valid posts in the same response continue.

## References verified reachable on 2026-09-20

- <https://docs.x.com/x-api/posts/search/integrate/build-a-query>
- <https://docs.x.com/x-api/posts/filtered-stream/integrate/build-a-rule>
- <https://docs.tweepy.org/en/stable/client.html#tweepy.Client.search_recent_tweets>
- <https://docs.tweepy.org/en/stable/streamingclient.html#tweepy.StreamingClient.filter>

API product access and limits depend on the actual X developer account and current X policy; the application does not encode a pricing tier.

## Dashboard contracts

The React client additionally consumes:

- `GET /api/health` — component health plus per-platform real/replay counts and
  latest source/collection timestamps;
- `GET /api/events/enriched` — paginated canonical events with optional persisted NLP. Optional `q` (literal case-insensitive text, author or hashtag substring, maximum 200 characters), `platform`, `sentiment`, `emotion`, and `interaction` filters apply in PostgreSQL before pagination; `total` is the filtered count;
- `GET /api/events/{event_id}/enriched` — one event with its NLP result (deep links from other pages);
- `GET /api/network/graph` — real, non-replay interaction nodes and edges;
- `GET /api/system/jobs` — scheduler/job observability; `POST /api/system/jobs/{name}/run` runs one job now
  (works when the scheduler is disabled);
- `GET /api/sources` — per-platform credential state, poll interval and configured sources with last-run
  results; `POST /api/sources` `{platform, target, label?}` adds one (YouTube URLs/IDs, Telegram `@handle` or
  `t.me` links are normalised), `PATCH /api/sources/{id}` `{enabled?, label?}`, `DELETE /api/sources/{id}`.
  Sources listed in `.env` (`TELEGRAM_CHANNELS`, `YOUTUBE_VIDEO_IDS`) are seeded on first use;
- existing health, temporal, trend, topic, and summary endpoints.

Event endpoints support bounded pagination. Dashboard network endpoints exclude replay edges by default.
`/api/events`, `/api/events/live`, temporal analytics, and network endpoints accept
the same canonical platform values, including `telegram`.

## YouTube / Data API v3

YouTube is isolated under `app/platforms/youtube` and uses
`google-api-python-client` with an API key. The adapter exposes:

- `YouTubeAdapter.collect(...)` for bounded comment retrieval;
- `YouTubeAdapter.poll_once(...)` for a single scheduler-friendly pass
  (disabled by default; never runs in demo mode);
- `YouTubeAdapter.health_check(...)` for configuration or an explicitly
  requested live check.

Configuration is loaded only from environment settings:

```dotenv
YOUTUBE_API_KEY=
YOUTUBE_VIDEO_ID=
YOUTUBE_MAX_RESULTS=50
YOUTUBE_MAX_PAGES=2
YOUTUBE_MAX_API_CALLS=10
YOUTUBE_POLL_INTERVAL_SECONDS=60
```

Primary endpoint is `commentThreads.list` (1 quota unit per call);
`comments.list` (1 unit per call) completes reply lists only when a thread's
`totalReplyCount` exceeds the inline replies. Pagination uses `pageToken`
with bounded page, result, and total API-call counts per pass; this command
does not crawl channels.
Quota exhaustion is classified as `YouTubeQuotaError`; other 403 access
failures remain explicit `YouTubeAPIError` results. Neither is hot-retried;
comments-disabled videos return
an honest empty result. Google API objects stop at the mapper boundary.
Malformed comments are rejected individually. If reply completion is
truncated after five pages, the result records an incomplete thread. A
request-budget pause returns a checkpoint with the thread/reply position for
explicit resumption; `exhausted=false` distinguishes a paused pass from an
exhausted response (both may have a null page token). No background retry or
polling is started.
Repository uniqueness on `(platform, platform_post_id)` is the final
deduplication guard.

YouTube comments are polling-based, never a true push stream, and the UI
labels them AVAILABLE / polling rather than live. Local deterministic
mapper/pagination/error tests use fixtures only. On 2026-09-23, a bounded
live API check against a public test video returned three comments using one
API call; canonical IDs, source timestamps, separate collection timestamps,
author IDs, and two reply relationships were validated in memory. This was
an adapter check, not a PostgreSQL/NLP/API end-to-end verification, and no
test-video comments were stored. A project video ID is still required for
the explicit ingestion command.

The adapter reports fetched events and hands them to an explicit callback;
the shared `EventPipeline` owns PostgreSQL, NLP and graph writes. The bounded
`scripts/run_youtube_comments.py` command uses this shared pipeline when an
API key and video ID are explicitly supplied. No YouTube polling job is
registered in the scheduler.
