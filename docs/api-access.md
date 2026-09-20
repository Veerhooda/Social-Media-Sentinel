# X API Access

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
