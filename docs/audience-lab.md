# Audience Lab

Pre-flight a post against AI agents that each represent one audience segment.
Module: `app/audience_lab/` · API: `/api/audience-lab/*` · UI: `/audience-lab` · migrations `0006_audience_lab`, `0007_drop_draft_reviews`.

## Pipeline (every judgement is made by Muse Spark)

```
audience_profiles ──► 1. Discovery agent   picks N segments (within min/max) from a random sample of profile cards
   (any source)       2. Assignment agent  places every profile (parallel batches) → audience_segment_members
                      3. Persona agent     writes one role-play agent per segment from that segment's members
post (+image) ─────► 4. Segment agents    react in parallel: positive/neutral/negative/sarcastic mix, interested %,
                                           engage %, share %, who inside the segment is interested, sample comments
                      5. Analyst agent     verdict, insights, risks, interested-audience profile, recommendations,
                                           rewritten post (or "no change needed")
                      6. Re-test           the same segment agents score the rewrite → simulated uplift
```

Code only does arithmetic: size-weighted averages of what agents report, the
interested-audience mix (segment share × interested %), and before/after
deltas. There are no hard-coded segments, labels, thresholds or uplift numbers.

## Why uplift is measured, not asked

Asking a model "how much better would this do?" produces an uncalibrated
number. Instead the rewrite is re-scored by the same agents under the same
conditions; the uplift is the difference (percentage points and relative %).
It is a *simulated* uplift. Calibrate it later by comparing simulations with
real post outcomes.

## Growing the audience database

`audience_profiles` is source-agnostic: `source`, `external_ref` (unique per
source), free-form `attributes`/`behaviour` JSON, `sample_texts`, and
`weight` (how many real people a record represents, e.g. a survey cell).

* `POST /api/audience-lab/profiles/sync`: upsert one profile per collected
  social account (profile fields, inferred demographics, NLP sentiment/irony/
  emotion mix, hashtags, recent posts). Replay data is excluded.
* `POST /api/audience-lab/profiles/import` with `{"profiles": [...]}`: add
  CRM exports, survey panels or hand-written personas. Re-importing the same
  `(source, external_ref)` updates the record.

Rebuild segments after adding data; old segmentations and simulations stay
immutable for comparison.

## API

| Method | Path | Notes |
|---|---|---|
| GET | `/status` | model, key configured?, profile counts, latest segmentation |
| POST | `/profiles/sync` · `/profiles/import` | upsert profiles |
| GET | `/profiles?source=&limit=&offset=` | browse |
| POST | `/segmentations` `{focus?, min_segments?, max_segments?, sources?}` | 202, background job |
| GET | `/segmentations`, `/segmentations/{id}` | poll `status`/`progress` |
| POST | `/simulations` `{text, platform, image_data_url?, media_description?, auto_improve, segmentation_id?}` | 202, background job |
| GET | `/simulations`, `/simulations/{id}` | poll; `baseline`, `analysis`, `improved_post`, `improved`, `uplift` |
| POST | `/segmentations/{id}/cancel`, `/simulations/{id}/cancel` | stops new model calls; in-flight calls finish |

Statuses: `QUEUED → RUNNING → COMPLETED | PARTIAL (some agents failed) | FAILED | CANCELLED`.

## Watching a job

`progress` on every segmentation/simulation is refreshed every ~2 s while it runs:
`stage`, `step/steps`, `done/total`, `started_at`, `last_activity_at`, `elapsed_seconds`,
`calls` (`in_flight`, `finished`, `failed`, `retries`), `tokens` (prompt / completion / reasoning)
and `events` (last 40 log lines, e.g. "Batch 3/7 (40 profiles) finished in 52s"). The UI shows these
live, keeps the log after completion, and offers Cancel. Every model call is also logged by the API
(`Muse Spark <call> ok in Ns usage=…`).

A job owned by a server process that has since restarted is marked `FAILED` the next time it is read;
a job with no activity for longer than `timeout × (retries + 1) + 2 min` is failed the same way.

## Speed

Profile placement is the bulk step (profiles ÷ `AUDIENCE_LAB_ASSIGN_BATCH` calls, run
`AUDIENCE_LAB_MAX_PARALLEL_AGENTS` at a time) and uses `AUDIENCE_LAB_FAST_REASONING_EFFORT` (default
`low`); judgement calls use `AUDIENCE_LAB_REASONING_EFFORT` (provider default when empty). If the API
rejects `reasoning_effort`, the call is retried without it.

## Platforms

The audience currently comes from the implemented collectors: X, Telegram and YouTube. The post
composer offers the platforms present in `audience_profiles`; importing profiles from another
platform adds it automatically.

## Configuration (`.env`)

```
META_MODEL_API_KEY=...                  # or MUSE_SPARK_API_KEY; the generic MODEL_API_KEY is ignored on purpose
META_MODEL_BASE_URL=https://api.meta.ai/v1
AUDIENCE_LAB_MODEL=muse-spark-1.3-contributor
AUDIENCE_LAB_REASONING_EFFORT=          # minimal|low|medium|high|xhigh, empty = default
AUDIENCE_LAB_FAST_REASONING_EFFORT=low  # used for bulk profile placement
AUDIENCE_LAB_TIMEOUT_SECONDS=300
AUDIENCE_LAB_MAX_PARALLEL_AGENTS=8
AUDIENCE_LAB_ASSIGN_BATCH=40
AUDIENCE_LAB_MIN_SEGMENTS=3
AUDIENCE_LAB_MAX_SEGMENTS=8
```

Requests use Chat Completions with `response_format: json_schema` (strict).
If the endpoint rejects schema mode, the client falls back to `json_object`
with the schema in the prompt. Invalid output gets one repair round, then the
call fails explicitly.

## Limits

* Agents simulate reactions; they are not measured engagement.
* Segment quality depends on profile evidence. Personas report
  `evidence_strength`, and agents report `confidence`.
* Jobs run in-process; a restart fails in-flight jobs (start them again).
* The earlier Draft Review prototype (`app/audience`, `/draft-review`) was removed; migration
  `0007_drop_draft_reviews` drops its leftover tables.
* `scripts/audience_lab_live_check.py` verifies the key and model with one call.
