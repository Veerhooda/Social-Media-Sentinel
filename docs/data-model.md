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
- `user_demographics` (aggregate signals with provenance: language/geography confidence, inference source, model versions, updated_at; age brackets persist NULL by design until a validated model exists)

YouTube comments reuse this schema unchanged (`platform=youtube`,
`platform_post_id`=comment ID, `parent_platform_post_id`=parent comment ID,
`thread_root_id`=top-level comment ID, video ID in `source_metadata`).
Reply edges target the parent author's channel ID when it is present. When
YouTube omits that ID, authors receive comment-scoped fallback IDs to avoid
merging people with the same display name; no reply edge is inferred from a
name alone. Textual @mentions do not create graph edges without verified IDs.
No migration was required.
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

Migration `0003_scheduler` adds:

- `social_events.graph_processed_at` for incremental graph processing;
- `analytics_checkpoints` for X collection cursors and trend watermarks.

Migration `0004_demographic_provenance` extends `user_demographics` with
per-dimension confidence (`language_confidence`, `geography_confidence`),
`inference_source`, `model_versions` (JSONB), and `updated_at`, plus indexes.

Migration `0006_audience_lab` creates the Audience Lab tables (see
`docs/audience-lab.md`):

- `audience_profiles` (source-agnostic profile records with a unique
  `(source, external_ref)`);
- `audience_segmentations` (background segmentation jobs with status/progress);
- `audience_segments` and `audience_segment_members` (segment membership);
- `post_simulations` (baseline reactions, analyst output, rewrite, re-test uplift).

There is no `0005`: the number was skipped, not lost. Migration
`0007_drop_draft_reviews` drops the removed Draft Review prototype tables
(`draft_reviews`, `audience_cohort_snapshots`).

Migration `0008_collection_sources` creates `collection_sources`
(`source_id`, platform, target, label, enabled, scheduling/cursor state) —
the single table behind the Sources UI and the three collection jobs.

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

## Telegram mapping

Telegram message IDs are unique only within a channel. The canonical
`platform_post_id` is therefore `<channel_id>:<message_id>`; the original channel
and message identifiers are also retained separately in `source_metadata`.

- Telegram `date` -> canonical `created_at`
- mapper observation time -> independent `collected_at`
- channel-scoped reply ID -> `parent_platform_post_id`
- discussion/reply top ID -> `thread_root_id`
- sender/channel entity -> canonical author
- text hashtags and `@username` mentions -> canonical content
- resolvable mention entity IDs -> `source_metadata.mention_ids`
- reply sender -> `relationships.parent_author_id`
- resolvable forward peer -> `relationships.forwarded_from_id`
- photos/documents -> metadata-only canonical media records (no private download URL)
- reactions/forwards/replies/views -> available canonical engagement counters

Hidden forward names are retained as source metadata but do not produce an invented
graph identity. The existing unique `(platform, platform_post_id)` constraint,
repositories, indexes, and graph tables require no Telegram-specific migration.
