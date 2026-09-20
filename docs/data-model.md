# Canonical Data Model

`CanonicalEvent` is platform-independent and rejects extra or malformed fields.

Required event identity and chronology:

- `event_id` UUID
- `platform`
- `platform_post_id`
- `parent_platform_post_id`
- `thread_root_id`
- `interaction_type`
- timezone-aware `created_at`
- timezone-aware `collected_at`

Nested records contain author metadata, text/language/hashtags/mentions/media, relationships, engagement metrics, and source metadata. Both timestamps are normalized to UTC. Source time is never replaced with collection time.

## PostgreSQL

Migration `0001_x_first` creates:

- `social_users`
- `social_events`
- `nlp_analysis`
- `user_demographics` (schema foundation only)
- `topics`
- `trend_measurements`
- `graph_edges`
- `dead_letter_events`

Migration `0002_bertrend` extends topic persistence with:

- stable, unique `topics.topic_key` values;
- the producing model identifier;
- idempotent `(topic_id, window_start, window_end)` measurements;
- growth, velocity, acceleration, and signal status;
- measurement-level sentiment distributions;
- the analysis engine/version.

The event repository upserts users and performs deterministic event insertion with a unique `(platform, platform_post_id)` constraint. Chronological queries sort by `created_at`.

Indexes cover platform/source time, author, creation time, collection time, parent lookup, hashtag GIN queries, graph endpoints/time, and trend windows.

## X mapping

- X post ID -> `platform_post_id`
- X `created_at` -> canonical `created_at`
- mapper observation time -> `collected_at`
- `conversation_id` -> `thread_root_id`
- referenced reply/repost/quote -> canonical relationship fields
- entities -> hashtags and mentions
- media expansion -> canonical media records
- public metrics -> canonical engagement metrics

Useful source identifiers and collection mode are retained in `source_metadata`; credentials and secrets are never stored.
