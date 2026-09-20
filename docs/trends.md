# Trends

## Architecture

BERTrend 0.4.18 runs behind the platform-independent `app/trends` service boundary:

```text
canonical PostgreSQL events
  -> non-empty text extraction
  -> source-time 15-minute micro-batches
  -> Sentence Transformer embeddings
  -> BERTrend / BERTopic
  -> one-to-one semantic centroid topic matching
  -> topics + trend_measurements
  -> FastAPI
```

Replay rows are excluded by default. A caller can select any platform or all canonical platforms; no X-specific object enters the trend engine.

## Minimum data and statuses

The default minimum is 10 documents in one micro-batch.

- `PASS`: BERTrend produced one or more non-outlier topics.
- `INSUFFICIENT_DATA`: documents exist but no batch reaches the minimum, all documents are outliers, or fewer than two comparable topic windows exist for evolution.
- `SKIPPED`: no canonical text matches the requested range.
- `FAIL`: model loading or inference failed.

Topic discovery and temporal evolution have separate statuses. A first observation is `emerging`; it is not called `rising` until a later comparable window has positive growth.

Cross-window matching uses normalized document-embedding centroids from the configured Sentence Transformer. Candidate pairs must meet the configurable `0.70` cosine threshold and are greedily assigned one-to-one by strongest evidence, preventing one earlier topic from continuing as multiple later topics. Keyword overlap remains only a persistence fallback.

## Measurements

For a topic with a previous measurement:

```text
growth = (current_count - previous_count) / max(previous_count, 1)
velocity = document_count_change / elapsed_hours_between_measurement_windows
acceleration = velocity_change / elapsed_hours_between_measurement_windows
```

Statuses are `emerging`, `rising`, `explosive`, `sustained`, or `cooling`. Measurement sentiment is calculated only from persisted NLP labels assigned to that topic's documents.

## Fallback

The original hashtag-frequency endpoint remains available only when no BERTrend measurements are persisted. Its response is explicitly marked `fallback=true` and `status=SKIPPED`; it is never presented as BERTrend output.

## Real X cross-window verification — 2026-09-20

- Window 1: 24 real events at `15:00–15:15 UTC` source time.
- Window 2: 20 real events at `15:45–16:00 UTC` source time.
- Query family: `(OpenAI OR ChatGPT) lang:en -is:retweet`; narrowed to `ChatGPT lang:en -is:retweet` for comparable live/backfilled samples.
- BERTrend window topics: 13.
- Semantic cross-window matches: 1 at cosine `0.726` (`0.70` threshold).
- Persisted topics: 12.
- Persisted measurements: 13.
- Multi-point topics: 1.
- Matched volume: `8 -> 3`.
- Growth: `-0.625`.
- Velocity: `-6.6667 documents/hour`, using the actual 45-minute source-time interval.
- Status: `cooling`.
- Acceleration: unavailable with only two measurements.
- Rerun result: topic IDs, 12-topic count, and 13-measurement count remained stable.

This proves temporal mechanics only. It is not a claim that the observed topic trend is meaningful or statistically significant.

No topic result was fabricated or derived from the hashtag fallback.
