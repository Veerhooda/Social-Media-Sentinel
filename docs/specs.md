> **Status (October 2026): frozen pre-build specification, dated 2026-09-20.**
> It is preserved as the historical build contract (problem statement, repository
> investigations, architecture decisions, acceptance criteria). It does not describe
> everything added since — Audience Lab, collection sources, the UI overhaul. For the
> system as it ships, start at `README.md` and the live references in `docs/`
> (`docs/architecture.md`, `docs/ps-coverage.md`).

# SPECS.md
# AI-Driven Social Media Analytics Framework

**Project status:** Pre-build technical specification  
**Specification date:** 2026-09-20  
**Target:** Hackathon / pilot implementation with a credible path to a broader multi-platform analytics system

---

## 0. Document Purpose

This document is the build contract for the AI-driven Social Media Analytics Framework described by the Problem Statement (PS).

It consolidates the repository investigations, corrective audits, architecture decisions, API constraints, model findings, dependency findings, data schemas, custom implementation requirements, privacy considerations, and remaining uncertainties discovered during project preparation.

This document is intentionally more conservative than a typical project README:

- A feature is considered implemented only when source code or an official API/library path has been verified.
- README claims alone are not sufficient evidence.
- Static datasets, mock implementations, abandoned examples, and unavailable repositories are not treated as production capabilities.
- Platform restrictions are treated as architectural constraints, not as implementation details to be ignored.
- Where a component still requires validation, the specification says so explicitly.

---

# 1. Problem Statement

The system shall provide an AI-driven social-media analytics framework capable of collecting and analyzing social-media information across multiple platforms and revealing:

1. **How people feel** through sentiment, emotion, irony/sarcasm, and stance analysis.
2. **Who the audience is at an aggregate level** through demographic inference.
3. **What topics are emerging** through temporal topic/trend analysis.
4. **How users interact** through graph topology and community analysis.
5. **How information, sentiment, and trends propagate over time** through cascade and diffusion analysis.

The PS has five major components.

## A. Continuous Data Collection & Timeline Management

Required:
- X / Twitter
- Telegram

Desirable:
- Instagram
- Facebook

Appreciable:
- Reddit OR YouTube comments

The system must:
- collect posts/messages/comments/interactions where platform access permits;
- preserve source timestamps;
- preserve parent-child relationships where available;
- retain historical events;
- normalize all platforms into a common schema;
- support chronological analysis.

## B. Multi-Dimensional Sentiment Inference

The system shall support:
- positive / negative / neutral sentiment;
- emotion classification;
- anxiety-like state;
- excitement;
- sarcasm / irony;
- support vs against / stance;
- confidence scores;
- temporal changes in sentiment/emotion.

Important interpretation:
- "Anxiety" is represented by the GoEmotions `nervousness` label and is mapped to the PS terminology.
- General stance must not be confused with ordinary sentiment.
- Arbitrary-topic stance is not fully provided by TweetNLP's fixed-target stance models and therefore needs a separate general NLI/stance solution or custom model.

## C. Automated Demographic Profiling

Aggregate/anonymized demographic signals:
- age bracket;
- geographic distribution;
- language;
- professional interests / occupation sector.

Possible inputs:
- public profile metadata;
- public bio text;
- public usernames/display names;
- public location strings;
- public profile images where allowed and appropriate.

The dashboard shall emphasize aggregate distributions and uncertainty instead of presenting inferred personal attributes as factual ground truth.

## D. Real-Time Trend & Topic Detection

The system shall support:
- topic discovery;
- emerging topic detection;
- rising discussions;
- trend velocity;
- ranking;
- chronological evolution;
- weak/strong signal analysis where useful.

## E. Link Analysis & Network Topology

The system shall support, subject to platform data availability:
- replies;
- mentions;
- reposts/retweets;
- quotes;
- comment parent-child links;
- forwards;
- follower relationships where an API actually exposes them.

Required graph analytics:
- graph construction;
- degree centrality;
- betweenness centrality;
- closeness centrality;
- PageRank;
- HITS;
- community detection;
- temporal diffusion / cascades;
- influence estimation.

---

# 2. Design Principles

## 2.1 Source-code verification

Every external component must have a concrete implementation path.

Do not rely on:
- repository descriptions;
- stars;
- screenshots;
- notebook prose;
- TODOs;
- mock responses;
- synthetic graph generation;
- static data alone.

## 2.2 API reality first

The system shall never assume that public data on a platform is automatically programmatically accessible.

For every platform:
- authentication requirements;
- permissions;
- rate limits;
- historical access;
- live access;
- account restrictions;
- commercial limits;
- API version compatibility

must be explicitly documented.

## 2.3 One normalized internal data model

Platform-specific events must be normalized before entering shared analytics.

## 2.4 Analytics is modular

Ingestion, NLP, demographics, trends, graph analytics, and presentation shall be independently replaceable.

## 2.5 Privacy by design

The framework shall avoid unnecessary persistence of highly sensitive inferred data and shall prefer aggregate reporting.

## 2.6 Graceful degradation

If a platform is unavailable or expensive:
- other live sources continue;
- replay data may be used for the demonstration;
- analytics should work against stored normalized events regardless of their origin.

---

# 3. Verified Technology / Repository Inventory

## 3.1 Core components

| Component | Repository / Library | Role | Current decision |
|---|---|---|---|
| X client | `tweepy/tweepy` | X API client and streaming/retrieval primitives | Use |
| Telegram | `LonamiWebs/Telethon` | MTProto historical + live ingestion | Use |
| Sentiment / social NLP | `cardiffnlp/tweetnlp` models/checkpoints | Social-text sentiment and irony; fixed-target stance models | Use model/checkpoint layer; avoid hard dependency on old wrapper where possible |
| Fine-grained emotion | `SamLowe/roberta-base-go_emotions` | Multi-label emotion classification | Use |
| Trends/topics | `rte-france/BERTrend` | Temporal topic modeling and weak/strong signal analysis | Use, isolated in modern Python environment |
| Graph analytics | `networkx/networkx` | Graph construction primitives and required graph algorithms | Use |
| Demographic inference | `euagendas/m3inference` | Age/gender/org prediction from profile signals | Research/optional; isolate or replace |
| Meta integration | `sageteamorg/python-sage-meta` | Existing Instagram/Facebook Graph wrapper | Reference only; write current-version adapter |
| Reddit | `vewaxio/ScrapiReddit` | Reddit post/comment ingestion | Optional |
| YouTube | `google-api-python-client` | Official YouTube Data API v3 comment ingestion | Use as primary appreciable platform |
| Diffusion | `GiulioRossetti/ndlib` | Diffusion simulations | Optional |
| Cascade influence | `computationalmedia/cascade-influence` | Retrospective cascade influence | Optional/research |
| Language ID | fastText / `facebookresearch/fastText` model | Language identification | Use model, preferably through a maintained runtime |
| Geography | GeoNames/geocoding utilities | Location normalization | Use |
| Professional interests | General NLI model | Bio sector classification | Custom service |

---

# 4. Repository Investigation History

## 4.1 Original candidate set

The first proposed list contained:

1. `uche-madu/twitter-pipeline`
2. `nemo1991/telegram-channel-monitor`
3. `sageteamorg/python-sage-meta`
4. `nawazaj/CivicShield-backend`
5. `jtonglet/Demographics-PWS`
6. `wri/demographic-identifier`
7. `rte-france/BERTrend`
8. `Zaher503/coordinated-bot-network-detection`
9. `behavioral-ds/evently`
10. `computationalmedia/cascade-influence`
11. `vewaxio/ScrapiReddit`
12. `machphy/youtube_sentiment_analysis_API`

## 4.2 Repositories rejected

### `nemo1991/telegram-channel-monitor`

Rejected after independent audit reported the repository URL as unavailable / 404.

Replacement:
- `LonamiWebs/Telethon`

### `nawazaj/CivicShield-backend`

Rejected after independent audit reported the repository as nonexistent.

This was the source of the original incorrect claim that a dedicated repository supplied sentiment + emotion + sarcasm.

Replacement:
- CardiffNLP TweetNLP models/checkpoints
- GoEmotions

### `jtonglet/Demographics-PWS`

Rejected as unavailable/private under the proposed URL.

Replacement:
- M3Inference as a research/optional component
- text/location/language inference implemented independently

### `Zaher503/coordinated-bot-network-detection`

Rejected in the corrective audit as unavailable under the proposed URL.

Replacement:
- NetworkX directly

### `behavioral-ds/evently`

Removed from the core architecture.

Reason:
- R-based research implementation;
- external solver/dependency overhead;
- not necessary for the hackathon core when custom temporal aggregation + optional NDLib/Cas.In are sufficient.

### `machphy/youtube_sentiment_analysis_API`

Removed from the core stack.

It is a working example for YouTube comment retrieval and basic three-class sentiment, but it is not a sufficient multi-dimensional NLP engine.

Replacement:
- Google YouTube API client for ingestion;
- shared NLP service for analysis.

## 4.3 Additional rejected/removed candidates

Previously inspected and removed examples include:
- `11Shraddha/SentimentAnalysis_NLP`
- `Jannah58/Social-Media-Analysis`
- `Prerna237/SocialNetworkAnalysis`
- `saad-sharif/Social-Media-Network-Analysis`
- `momo-shogun/Trends-Tracker`
- `rodekruis/social-media-listening`
- `bfelbo/DeepMoji`
- `ManasReddy-11/MULTILINGUAL-SENTIMENT-UNDERSTANDING-OF-SOCIAL-MEDIA-TEXT-STREAMS-WITH-A-TRANSFORMER`
- `Palvin21/Multi-Platform-Social-Media-Sentiment-and-Sarcasm-Analyzer`
- `vellie27/YouTube_commentStreaming_ETL`
- `senyszrm/TwitterDataCollector`
- `CreepyD246/tweepy-stream-api-v2`
- `sriniskanda/Extracts-comments-and-posts-from-facebook`
- `nikhilkumarsingh/FacebookGraphAPI-Examples`
- `lilkimchi/media-metrics-YouTube-analyzer`

Reasons included:
- static data;
- mock implementations;
- obsolete APIs;
- source implementation not verifiable;
- basic tutorial scope;
- hard-coded credentials;
- unrelated application purpose.

---

# 5. Important Corrections to Previous Audits

## 5.1 X API pricing/access

Do not encode the earlier fixed "$100 Basic / $5,000 Pro" subscription assumptions into the application.

Current X access is governed by current API product/credit/access rules and must be checked against the actual developer account before deployment.

The application shall therefore implement:
- a clean X adapter;
- read-limit accounting;
- rate-limit/backoff handling;
- a replay source that can substitute for X during development and demo.

The architecture must not depend on one assumed pricing tier.

## 5.2 BERTrend Python version

The current BERTrend repository declares:

```text
requires-python = >=3.12,<4.0
```

The earlier Python 3.10 plan was therefore incorrect.

## 5.3 NetworkX Python version

Current NetworkX also requires Python >=3.12.

The primary analytics environment shall therefore use:

```text
Python 3.13
```

unless an integration spike proves a different modern version is better.

## 5.4 TweetNLP compatibility

TweetNLP is a real social NLP implementation, but its wrapper is older and its source uses older Hugging Face arguments such as `use_auth_token`.

Preferred approach:
- use TweetNLP-derived models/checkpoints directly through current Transformers APIs where required;
- retain TweetNLP as the source/reference for task-specific social models;
- do not make the entire system dependent on an old wrapper version.

## 5.5 Stance is not arbitrary-target magic

TweetNLP contains separate models for fixed stance targets such as:
- abortion;
- atheism;
- climate;
- feminist;
- Hillary.

Therefore:

```text
BERTrend topic -> arbitrary new target -> TweetNLP stance
```

must NOT be treated as already verified.

Dynamic stance shall use:
- a general NLI/stance model;
- or a specifically validated arbitrary-target stance model;
- or a model fine-tuned by the project.

The exact final general stance model must be validated during the integration spike.

## 5.6 Meta SDK version

`sageteamorg/python-sage-meta` contains code using Graph URL `v20.0` and initializes the Facebook SDK with version `3.1`.

Because Meta API versions move forward, this repository is not the canonical Meta integration for the final system.

Decision:
- use its source as reference;
- implement a thin current Graph API adapter;
- verify current permissions/endpoints before deployment.

## 5.7 M3Inference

M3Inference is real and implements:
- age;
- gender;
- organization/person classification.

Its README states that it supports profile text/name/screen-name/image inputs and includes a text-only mode.

However:
- it is a 2019 research implementation;
- its dependency stack is old;
- its model environment requires compatibility testing;
- it should not be forced into the primary modern environment.

Decision:
- isolate it;
- or replace it with a modern text-only demographic approach;
- use it only if the integration spike demonstrates practical value.

---

# 6. High-Level Architecture

```text
                         PLATFORM SOURCES
 ┌────────────┬─────────────┬─────────────┬─────────────┐
 │ X          │ Telegram    │ YouTube     │ Meta        │
 │ Tweepy     │ Telethon    │ API Poller  │ Graph API   │
 └────────────┴─────────────┴─────────────┴─────────────┘
       │             │             │             │
       └─────────────┴─────────────┴─────────────┘
                           │
                           ▼
                 ┌──────────────────┐
                 │ Event Normalizer  │
                 │ Pydantic Models   │
                 └──────────────────┘
                           │
                           ▼
                 ┌──────────────────┐
                 │ PostgreSQL       │
                 │ Timeline Store   │
                 └──────────────────┘
                           │
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
       ┌─────────┐   ┌────────────┐  ┌────────────┐
       │ NLP     │   │ Demographic│  │ Trend      │
       │ Service │   │ Service    │  │ Service    │
       └─────────┘   └────────────┘  └────────────┘
            │              │              │
            └──────────────┼──────────────┘
                           ▼
                    ┌──────────────┐
                    │ Graph Engine │
                    │ NetworkX     │
                    └──────────────┘
                           │
                   ┌───────┴────────┐
                   ▼                ▼
              Topology          Cascades
              PageRank          NDLib/Cas.In
              HITS
              Communities
                           │
                           ▼
                    ┌──────────────┐
                    │ FastAPI API  │
                    │ WebSockets   │
                    └──────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ Dashboard    │
                    │ React /      │
                    │ Chart.js     │
                    └──────────────┘
```

---

# 7. Service Boundaries

## 7.1 Ingestion service

Responsibilities:
- connect to platform APIs;
- retrieve historical data;
- receive live data where available;
- attach `collected_at`;
- perform minimal source validation;
- push normalized candidates into the event queue.

## 7.2 Normalization service

Responsibilities:
- convert platform-specific objects into the canonical event model;
- normalize timestamps to UTC;
- normalize interaction types;
- extract mentions;
- resolve parent identifiers;
- preserve raw source payload where retention policy permits.

## 7.3 Storage service

Responsibilities:
- persist users;
- persist events;
- persist interactions;
- persist inference results;
- persist topic/trend results;
- support time-window queries;
- guarantee idempotency.

## 7.4 NLP service

Responsibilities:
- sentiment;
- emotion;
- irony/sarcasm;
- stance;
- confidence;
- model version tracking.

## 7.5 Demographic service

Responsibilities:
- age brackets;
- language;
- geography;
- professional-interest sector;
- uncertainty;
- aggregation.

## 7.6 Trend service

Responsibilities:
- topic extraction;
- temporal grouping;
- emerging-signal detection;
- velocity;
- trend ranking.

## 7.7 Graph service

Responsibilities:
- construct graph edges;
- maintain time-windowed graph;
- calculate centrality;
- PageRank;
- HITS;
- communities;
- optionally diffusion/influence.

## 7.8 API/dashboard service

Responsibilities:
- expose current metrics;
- serve historical charts;
- stream selected real-time updates;
- never expose raw secrets;
- enforce aggregate demographic display.

---

# 8. Platform Integration Specification

## 8.1 X / Twitter

### Library
`tweepy/tweepy`

### Required capabilities
- recent search;
- user lookup;
- filtered stream when the account has access;
- tweet metadata;
- timestamps;
- mentions;
- referenced/reposted/quoted relationships where returned by the API.

### Authentication
Credentials depend on the current X API product.

Configuration must support:
- bearer token;
- additional app/user credentials if the selected endpoint requires them.

### Data collection modes

```text
Mode A: filtered stream
Mode B: search/polling
Mode C: replay
```

The replay mode must always exist so development and demos do not depend on uninterrupted commercial API access.

### Failure behavior
- respect API response status;
- read retry/backoff information;
- maintain pagination/cursor state;
- deduplicate events.

### Important limitation
Follower graph and arbitrary social relationships must not be assumed to be available at the scale required by the PS. The graph engine shall primarily use observable interaction edges when follower data is unavailable.

---

## 8.2 Telegram

### Library
`LonamiWebs/Telethon`

### Verified capabilities
- historical channel message retrieval with `iter_messages`;
- live updates through event handlers;
- timestamps;
- replies;
- forwards;
- channel metadata.

### Credentials
Requires:
- `api_id`;
- `api_hash`;
- authorized Telegram user/session.

Telegram officially requires developers to obtain their own API ID/hash for MTProto applications.

### Target scope
Initial implementation:
- public channels;
- public supergroups where permitted;
- discussion threads associated with target channels.

Do not monitor private conversations.

### Flood control
Catch:

```python
telethon.errors.FloodWaitError
```

and sleep for the server-specified period.

---

## 8.3 Instagram

### Integration
Current Meta Graph API adapter.

### Scope
Only data actually available to the authenticated Business/Creator/Page context.

Potential:
- media;
- comments;
- replies;
- metrics;
- timestamps.

### Important limitation
The PS must not be interpreted as authorization to scrape arbitrary personal Instagram profiles.

### Strategy
- implement a current-version direct API adapter;
- treat Sage Meta as reference code only;
- support polling/webhooks where officially available.

---

## 8.4 Facebook

### Integration
Current Meta Graph API adapter.

### Scope
Primarily owned/managed Pages and permitted resources.

Potential:
- page posts;
- comments;
- reactions/engagement where endpoint permissions permit;
- timestamps;
- webhooks.

### Important limitation
No architectural assumption may be made that arbitrary public Facebook feeds are accessible through the Graph API.

---

## 8.5 Reddit

### Recommended role
Optional secondary ingestion source.

### Existing code
`vewaxio/ScrapiReddit`

### Capabilities
- listings;
- nested comments;
- parent-child relationships;
- timestamps;
- JSON/CSV output.

### Production decision
For reliable high-volume use, prefer authenticated official/OAuth access where available instead of depending solely on unauthenticated public endpoints.

### Development strategy
- use ScrapiReddit for small-scale tests;
- provide an adapter boundary so the backend can later switch to OAuth/PRAW.

---

## 8.6 YouTube

### Library
`google-api-python-client`

### Endpoint
`commentThreads.list`

### Capabilities
- comment threads;
- top-level comments;
- replies where returned;
- timestamps;
- video/channel association.

For complete reply retrieval, use `comments.list` when the thread response does not contain all replies.

### Quota
The current YouTube Data API documentation states:
- default quota: 10,000 units/day for most endpoints;
- `commentThreads.list`: 1 quota unit/call;
- `comments.list`: 1 quota unit/call.

### Live strategy
YouTube comments are not treated as a true push stream.

Use:
- polling;
- configurable interval;
- deduplication by comment ID;
- backoff.

---

# 9. Canonical Event Model

Every platform-specific event must normalize into the following shape.

```json
{
  "event_id": "uuid",
  "platform": "telegram",
  "platform_post_id": "1049281",
  "parent_platform_post_id": "1049250",
  "thread_root_id": "1049000",
  "interaction_type": "reply",

  "created_at": "2026-09-20T09:30:00Z",
  "collected_at": "2026-09-20T09:30:04Z",

  "author": {
    "platform_user_id": "tg_992811",
    "username": "tech_analyst",
    "display_name": "Tech Analyst",
    "bio": "Covering AI infrastructure and distributed systems.",
    "location_raw": "San Francisco, CA",
    "avatar_url": null,
    "followers_count": 1420,
    "following_count": 310,
    "is_verified": false
  },

  "content": {
    "text": "The latest benchmark results are astonishing!",
    "language": "en",
    "hashtags": ["AI", "Hardware"],
    "mentions": ["user_123"],
    "media_urls": []
  },

  "relationships": {
    "parent_author_id": null,
    "repost_of_author_id": null,
    "quote_of_event_id": null,
    "forwarded_from_id": null
  },

  "metrics": {
    "likes": 45,
    "shares": 12,
    "comments": 4,
    "views": 1280
  },

  "source_metadata": {
    "channel_id": "channel_123",
    "video_id": null,
    "raw_event_type": "telegram_message"
  }
}
```

## 9.1 Timestamp rules

Store:
- `created_at`: source-origin timestamp;
- `collected_at`: system collection timestamp.

Always convert to UTC.

Never replace an event's original timestamp with ingestion time.

---

# 10. PostgreSQL Data Model

## 10.1 `social_users`

```sql
CREATE TABLE social_users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform VARCHAR(32) NOT NULL,
    platform_user_id VARCHAR(128) NOT NULL,
    username VARCHAR(128),
    display_name VARCHAR(256),
    bio TEXT,
    location_raw VARCHAR(256),
    followers_count BIGINT DEFAULT 0,
    following_count BIGINT DEFAULT 0,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(platform, platform_user_id)
);
```

## 10.2 `social_events`

```sql
CREATE TABLE social_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform VARCHAR(32) NOT NULL,
    platform_post_id VARCHAR(128) NOT NULL,
    parent_event_id UUID REFERENCES social_events(event_id),
    author_id UUID NOT NULL REFERENCES social_users(user_id),

    interaction_type VARCHAR(32) NOT NULL,

    created_at TIMESTAMPTZ NOT NULL,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    content_text TEXT,
    language_code VARCHAR(16),

    metrics_likes BIGINT DEFAULT 0,
    metrics_shares BIGINT DEFAULT 0,
    metrics_comments BIGINT DEFAULT 0,
    metrics_views BIGINT DEFAULT 0,

    raw_payload JSONB,

    UNIQUE(platform, platform_post_id)
);

CREATE INDEX idx_events_created_at
ON social_events(created_at DESC);

CREATE INDEX idx_events_platform_created
ON social_events(platform, created_at DESC);

CREATE INDEX idx_events_author
ON social_events(author_id);

CREATE INDEX idx_events_parent
ON social_events(parent_event_id);
```

## 10.3 `nlp_analysis`

```sql
CREATE TABLE nlp_analysis (
    analysis_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL REFERENCES social_events(event_id) ON DELETE CASCADE,

    sentiment_label VARCHAR(16) NOT NULL,
    sentiment_score DOUBLE PRECISION NOT NULL,

    is_sarcastic BOOLEAN,
    sarcasm_score DOUBLE PRECISION,

    primary_emotion VARCHAR(64),
    emotion_scores JSONB NOT NULL DEFAULT '{}'::jsonb,

    stance_target VARCHAR(256),
    stance_label VARCHAR(32),
    stance_score DOUBLE PRECISION,

    model_versions JSONB NOT NULL DEFAULT '{}'::jsonb,

    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(event_id)
);
```

## 10.4 `user_demographics`

```sql
CREATE TABLE user_demographics (
    demographic_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES social_users(user_id) ON DELETE CASCADE,

    age_bracket VARCHAR(16),
    age_confidence DOUBLE PRECISION,

    inferred_country VARCHAR(8),
    inferred_region VARCHAR(128),

    primary_language VARCHAR(16),

    professional_sector VARCHAR(128),
    profession_confidence DOUBLE PRECISION,

    gender VARCHAR(32),
    gender_confidence DOUBLE PRECISION,

    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(user_id)
);
```

Gender is auxiliary and shall not be represented as definitive personal truth.

## 10.5 `topics`

```sql
CREATE TABLE topics (
    topic_id BIGSERIAL PRIMARY KEY,
    name VARCHAR(256) NOT NULL,
    keywords TEXT[] NOT NULL DEFAULT '{}',
    first_seen_at TIMESTAMPTZ,
    last_seen_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

## 10.6 `trend_measurements`

```sql
CREATE TABLE trend_measurements (
    measurement_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic_id BIGINT NOT NULL REFERENCES topics(topic_id),

    window_start TIMESTAMPTZ NOT NULL,
    window_end TIMESTAMPTZ NOT NULL,

    document_count INTEGER NOT NULL,
    velocity_score DOUBLE PRECISION,
    acceleration_score DOUBLE PRECISION,

    status VARCHAR(32),

    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_trend_time
ON trend_measurements(window_start, window_end);
```

## 10.7 `graph_edges`

```sql
CREATE TABLE graph_edges (
    edge_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    source_user_id UUID NOT NULL REFERENCES social_users(user_id),
    target_user_id UUID NOT NULL REFERENCES social_users(user_id),

    interaction_type VARCHAR(32) NOT NULL,

    event_id UUID REFERENCES social_events(event_id),

    weight DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    occurred_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_graph_source
ON graph_edges(source_user_id);

CREATE INDEX idx_graph_target
ON graph_edges(target_user_id);

CREATE INDEX idx_graph_occurred
ON graph_edges(occurred_at DESC);
```

## 10.8 Optional `dead_letter_events`

```sql
CREATE TABLE dead_letter_events (
    dead_letter_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform VARCHAR(32),
    error_type VARCHAR(128),
    error_message TEXT,
    raw_payload JSONB,
    failed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

# 11. NLP Specification

## 11.1 Sentiment

Primary model:

```text
cardiffnlp/twitter-roberta-base-sentiment-latest
```

Outputs:
- positive;
- neutral;
- negative.

Store:
- selected label;
- full probability distribution;
- model version.

## 11.2 Emotion

Primary checkpoint:

```text
SamLowe/roberta-base-go_emotions
```

The current Hugging Face model card identifies it as a GoEmotions model trained for multi-label emotion classification.

Important labels include:
- excitement;
- nervousness;
- fear;
- anger;
- joy;
- sadness;
- surprise;
- and other GoEmotions categories.

Mapping:

```text
nervousness -> anxiety
```

This is a terminology mapping, not a claim that the model contains a native `anxiety` class.

## 11.3 Sarcasm / irony

Primary model:

```text
cardiffnlp/twitter-roberta-base-irony
```

Binary output:
- irony;
- non-irony.

Store:
- boolean;
- confidence.

Do not present irony probability as perfect sarcasm understanding.

## 11.4 Stance

### Fixed supported targets

TweetNLP provides fixed-target stance models for specific TweetEval topics.

These can be used where the monitored topic matches a supported target.

### Arbitrary target

For arbitrary emerging topics:
- use a general NLI/stance model;
- pair input text with a target hypothesis;
- validate performance on the application's target domain.

Candidate model family discovered during planning:
- DeBERTa-v3 NLI models.

Exact checkpoint is a build-time validation decision.

## 11.5 Unified NLP output

Example:

```json
{
  "sentiment": {
    "label": "negative",
    "scores": {
      "negative": 0.88,
      "neutral": 0.09,
      "positive": 0.03
    }
  },

  "emotions": {
    "anxiety": 0.74,
    "excitement": 0.02,
    "fear": 0.62,
    "anger": 0.41
  },

  "sarcasm": {
    "is_sarcastic": true,
    "score": 0.81
  },

  "stance": {
    "target": "Target Topic",
    "label": "against",
    "score": 0.79
  }
}
```

## 11.6 Inference batching

Use batches rather than one model invocation per event.

Initial target:
- batch size 8-32 depending on hardware;
- `torch.no_grad()`;
- bounded queues.

GPU inference is preferred for sustained throughput but must not be a hard requirement for correctness.

---

# 12. Temporal Sentiment & Emotion Analytics

Individual models are stateless.

The temporal layer is custom.

## 12.1 Primary windows

### Fine window
- 1-hour rolling view;
- 15-minute step.

Used for:
- sentiment;
- emotions;
- sarcasm;
- stance.

### Daily view
- 24-hour aggregation.

Used for:
- demographic shifts;
- cross-platform comparison;
- long-range trends.

## 12.2 Metrics

For each window:
- event count;
- positive ratio;
- neutral ratio;
- negative ratio;
- average anxiety score;
- average excitement score;
- emotion distribution;
- sarcasm rate;
- stance distribution;
- change vs previous window.

Example:

```text
11:00
negative = 0.31
anxiety = 0.22
sarcasm = 0.08

12:00
negative = 0.48
anxiety = 0.41
sarcasm = 0.14
```

The dashboard shall be able to display this as a time series.

---

# 13. Trend / Topic Specification

## Engine

`rte-france/BERTrend`

Current repository status:
- Python >= 3.12;
- transformer/BERTopic-based;
- temporal topic analysis;
- emerging weak/strong signal analysis.

## Input

BERTrend requires text + timestamp-oriented document data.

Normalized pipeline:

```text
events
 -> select text
 -> group into time window
 -> construct BERTrend input
 -> topic model
 -> temporal comparison
 -> velocity
 -> ranking
```

## Initial scheduling target

Run:
- every 15 minutes;
- or when the buffered document count exceeds a configured threshold.

This is a practical micro-batch interpretation of a "real-time" trend system.

## Trend metrics

Store:
- topic name;
- keywords;
- document count;
- velocity;
- acceleration;
- status;
- observation window.

---

# 14. Graph Specification

## 14.1 Graph model

Use a directed weighted graph.

Node:
```text
user
```

Edge:
```text
source user -> target user
```

## 14.2 Edge semantics

| Interaction | Source | Target | Default weight |
|---|---|---|---:|
| X repost/retweet | reposter | original author | 1.0 |
| X quote | quoting user | quoted author | 1.0 |
| X mention | mentioning user | mentioned user | 0.5 |
| X reply | replying user | parent author | 0.8 |
| Telegram forward | forwarding source | origin source | 1.0 |
| Telegram reply | replying user | parent author | 0.8 |
| Reddit reply | commenter | parent commenter | 0.8 |
| YouTube reply | replier | parent commenter | 0.8 |

Weights are configuration defaults, not empirical truths. They exist to distinguish interaction strength in the prototype.

## 14.3 Algorithms

NetworkX shall provide:

```python
nx.in_degree_centrality(G)
nx.out_degree_centrality(G)
nx.betweenness_centrality(G)
nx.closeness_centrality(G)
nx.pagerank(G)
nx.hits(G)
nx.community.louvain_communities(G.to_undirected())
```

## 14.4 KOL interpretation

Do not identify a node as influential using one metric only.

Dashboard may show:
- PageRank;
- authority;
- hub score;
- betweenness;
- degree.

The term "high-influence" should be based on documented metrics, not hidden scoring.

---

# 15. Diffusion & Cascade Analysis

## 15.1 NDLib

Optional forward simulation engine.

Use for:
- Independent Cascade simulation;
- Threshold/opinion dynamics;
- hypothetical propagation experiments.

NDLib is not a live empirical influence estimator.

## 15.2 Cas.In

`computationalmedia/cascade-influence`

Use for:
- retrospective cascade influence;
- timestamped cascade sequences;
- user influence estimation.

Expected input:
```text
time
magnitude
user_id
```

The project must construct such cascade sequences from normalized social events.

Cas.In is therefore:
- a research/analysis component;
- not an ingestion system;
- not a live streaming system.

---

# 16. Demographic Specification

## 16.1 Age

Preferred output:
- <=18;
- 19-29;
- 30-39;
- >=40.

Candidate:
`euagendas/m3inference`

M3 is a research model and must be isolated or replaced if compatibility/testing is poor.

## 16.2 Language

Use a maintained language-identification runtime/model.

The discovered fastText `lid.176` model provides broad language identification.

Store:
```text
language_code
language_confidence
```

Special handling:
- 1-2 word inputs;
- emoji-only inputs;
- URLs;
- mentions.

## 16.3 Geography

Input:
```text
location_raw
```

Pipeline:
1. exact country match;
2. city/region match;
3. GeoNames lookup;
4. cached normalized result;
5. UNKNOWN.

Never infer a precise home address from public text.

## 16.4 Professional interests

No verified repository was found that completely solves the PS's professional-interest requirement.

Implement a custom zero-shot classifier over a controlled taxonomy.

Initial sectors:
- Technology / Software;
- Finance / Banking;
- Healthcare / Medicine;
- Education / Research;
- Arts / Entertainment;
- Sales / Marketing;
- Trades / Labor;
- Student / Academic.

Store:
- sector;
- confidence;
- model version.

## 16.5 Aggregate-only dashboard

Dashboard examples:

```text
Age
19-29: 42%
30-39: 23%
>=40: 12%
Unknown: 23%
```

Do not display:

```text
User 123 is 27 years old and works in Finance.
```

---

# 17. Privacy & Data Governance

## 17.1 Principles

The framework must:
- collect only data needed for the stated analytics;
- preserve source policy constraints;
- minimize retention of unnecessary personal data;
- display demographic information in aggregate form;
- track inference confidence.

## 17.2 Profile images

If profile-image inference is enabled:
- process images ephemerally;
- do not persist raw face crops;
- do not put raw profile images into the database;
- delete temporary bytes after inference.

## 17.3 Inference uncertainty

Every demographic prediction should allow:
```text
prediction
confidence
unknown
```

The model output must not be represented as verified identity information.

## 17.4 Sensitive categories

The system shall not attempt to infer or expose:
- exact residential addresses;
- salary;
- security clearance;
- similar highly sensitive attributes.

---

# 18. Real-Time Architecture

Initial hackathon architecture:

```text
Platform listeners/pollers
        |
        v
asyncio.Queue
        |
        v
Normalization worker
        |
        +-------> PostgreSQL
        |
        +-------> NLP worker
        |
        +-------> Demographic worker
        |
        +-------> Graph edge writer
        |
        +-------> Trend buffer
```

Periodic workers:

```text
Graph runner: every 5 minutes
Trend runner: every 15 minutes
Temporal aggregation: continuous query / scheduled
```

Dashboard:

```text
FastAPI
   |
   +-- REST
   |
   +-- WebSocket
            |
            v
       React dashboard
```

## 18.1 Queue choice

Start with:
```text
asyncio.Queue
```

Do not introduce Kafka merely for appearance.

Move to Redis/Kafka only if:
- multiple workers are required;
- events need durable queueing;
- process isolation makes it necessary.

---

# 19. Configuration

Example `.env`:

```dotenv
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/social_analytics

# Telegram
TELEGRAM_API_ID=
TELEGRAM_API_HASH=
TELEGRAM_SESSION_STRING=

# X
X_BEARER_TOKEN=
X_CLIENT_ID=
X_CLIENT_SECRET=

# YouTube
YOUTUBE_API_KEY=

# Meta
META_APP_ID=
META_APP_SECRET=
META_ACCESS_TOKEN=

# Application
APP_ENV=development
API_HOST=0.0.0.0
API_PORT=8000

# Analytics
NLP_BATCH_SIZE=16
GRAPH_INTERVAL_SECONDS=300
TREND_INTERVAL_SECONDS=900
SENTIMENT_WINDOW_MINUTES=60
```

Never commit `.env`.

Never place real keys in documentation.

---

# 20. Dependency / Runtime Strategy

## Primary environment

```text
Python 3.13
```

Reason:
- current BERTrend requires Python >=3.12;
- current NetworkX requires Python >=3.12;
- current Tweepy supports modern Python versions.

## Recommended structure

```text
analytics-app: Python 3.13
    Tweepy
    Telethon
    Transformers
    PyTorch
    NetworkX
    FastAPI
    PostgreSQL client
    language ID runtime

trend-service: Python 3.13
    BERTrend
    BERTopic
    sentence-transformers
    PyTorch

legacy-demographics-service: isolated only if M3Inference is retained
    M3Inference
    compatible legacy runtime
```

### Why isolation matters

M3Inference is old and its environment is not a safe dependency anchor for the rest of the project.

The final project must not make the modern pipeline depend on one old research package.

---

# 21. Model Asset Strategy

Required model assets may include:

```text
cardiffnlp/twitter-roberta-base-sentiment-latest
cardiffnlp/twitter-roberta-base-irony
SamLowe/roberta-base-go_emotions
```

Model artifacts should be:
- downloaded during controlled setup;
- cached;
- version recorded;
- not blindly committed to Git;
- validated before inference.

The current GoEmotions Hugging Face model has a safetensors artifact and an ONNX variant. The ONNX variant may be considered later if inference footprint becomes a bottleneck.

---

# 22. Failure & Recovery

## API 429

- respect server retry timing;
- exponential backoff;
- jitter;
- pause the affected collector only.

## Telegram FloodWaitError

- sleep for the server-specified duration;
- preserve progress cursor.

## Authentication failure

- do not spin indefinitely;
- place collector into degraded state;
- notify operator.

## Network failure

- reconnect;
- resume from persisted cursor/timestamp where possible.

## Malformed event

- Pydantic validation;
- write to `dead_letter_events`;
- continue processing.

## NLP OOM

- lower batch size;
- retry on CPU if supported;
- mark failure if still unsuccessful.

## Duplicate event

Use:

```text
UNIQUE(platform, platform_post_id)
```

and idempotent writes.

---

# 23. Observability

Every major service shall expose basic counters:

## Ingestion
- events received;
- events normalized;
- events rejected;
- last successful collection time.

## NLP
- events analyzed;
- average inference latency;
- model failures;
- queue length.

## Trends
- documents processed;
- latest trend run;
- latest topic count.

## Graph
- active nodes;
- active edges;
- latest computation time;
- latest PageRank update.

## System
- DB connectivity;
- queue depth;
- API error count.

---

# 24. Testing Requirements

## 24.1 Unit tests

Test:
- each platform normalizer;
- timestamp conversion;
- parent relationship extraction;
- mention extraction;
- graph edge creation;
- SQL upserts;
- NLP result parsing;
- demographic uncertainty;
- trend-window calculations.

## 24.2 Integration tests

Minimum:

```text
sample Telegram event
 -> normalization
 -> PostgreSQL
 -> NLP
 -> graph edge
 -> trend buffer
```

## 24.3 Model smoke tests

For every model:
- load checkpoint;
- run one known string;
- inspect output labels;
- verify probability structure.

## 24.4 Platform adapter tests

Use mocked API payloads for:
- X;
- Telegram;
- Meta;
- Reddit;
- YouTube.

Live credentials should not be required for unit tests.

## 24.5 End-to-end acceptance test

One event shall be able to travel:

```text
source
 -> normalized event
 -> DB
 -> NLP
 -> graph
 -> dashboard metric
```

---

# 25. Hackathon Demo Strategy

Because some platform APIs are access-controlled, the demo shall be hybrid.

## Live sources

First milestone:
- X recent search;
- X filtered stream where the configured account has access.

## Replay sources

Use pre-collected or synthetic records for:
- X when live access is unavailable;
- Instagram;
- Facebook;
- optionally Reddit.

Replay events must preserve:
- realistic timestamps;
- replies;
- mentions;
- reposts;
- nested comments;
- multiple interacting users.

The replay engine is a demo/testing mechanism, not a substitute for claiming that unavailable APIs are live.

## Demonstration sequence

### Stage 1
Collect a real X post, or inject a clearly labeled synthetic X replay event when credentials/access are unavailable.

### Stage 2
The event is persisted.

### Stage 3
NLP analyzes:
- sentiment;
- emotion;
- irony;
- stance.

### Stage 4
The event generates graph edges.

### Stage 5
The trend engine incorporates the text into its temporal window.

### Stage 6
Dashboard updates:
- event count;
- sentiment;
- emotion;
- trend;
- graph;
- demographic aggregate.

### Stage 7
Show historical timeline:
- sentiment spike;
- emotion change;
- emerging topic;
- community/influence information.

---

# 26. Dashboard Functional Specification

## Page 1: Overview

Show:
- total events;
- events/minute;
- active users;
- top topics;
- overall sentiment.

## Page 2: Sentiment & Emotion

Charts:
- positive/neutral/negative over time;
- anxiety over time;
- excitement over time;
- emotion distribution;
- sarcasm rate;
- stance distribution.

## Page 3: Trends

Show:
- emerging topics;
- velocity;
- acceleration;
- keyword lists;
- topic timeline.

## Page 4: Network

Show:
- interactive graph;
- top PageRank nodes;
- top HITS authorities;
- top hubs;
- betweenness bridges;
- Louvain communities.

## Page 5: Audience

Show aggregate:
- age;
- geography;
- language;
- professional sector.

Always include:
- unknown cohort;
- sample size;
- confidence/coverage indicators.

---

# 27. PS Coverage Matrix

| PS | Implementation path | Status |
|---|---|---|
| X ingestion | Tweepy + current API access | Conditional on account/access |
| Telegram ingestion | Telethon | Ready |
| Instagram | Current Meta adapter | Requires account/permissions |
| Facebook | Current Meta adapter | Requires Page permissions |
| Reddit | ScrapiReddit / OAuth | Optional |
| YouTube comments | Google API | Ready with polling |
| Timeline | PostgreSQL | Custom |
| Sentiment | Cardiff model | Ready |
| Emotions | GoEmotions | Ready |
| Anxiety | `nervousness` mapping | Ready |
| Excitement | GoEmotions | Ready |
| Sarcasm/irony | Cardiff irony model | Ready |
| Fixed-target stance | TweetNLP | Ready for supported targets |
| Arbitrary-target stance | General NLI / custom | Requires validation |
| Temporal sentiment | PostgreSQL aggregation | Custom |
| Age | M3Inference or replacement | Conditional |
| Geography | GeoNames/geocoder | Custom + library |
| Language | fastText | Ready after runtime validation |
| Profession | Zero-shot classifier | Custom |
| Topic detection | BERTrend/BERTopic | Ready with adaptation |
| Emerging trends | BERTrend | Ready with adaptation |
| Trend velocity | BERTrend/custom metrics | Ready with adaptation |
| Graph construction | Custom event parser + NetworkX | Custom |
| Degree | NetworkX | Ready |
| Betweenness | NetworkX | Ready |
| Closeness | NetworkX | Ready |
| PageRank | NetworkX | Ready |
| HITS | NetworkX | Ready |
| Communities | NetworkX Louvain | Ready |
| Diffusion simulation | NDLib | Optional |
| Cascade influence | Cas.In | Optional/research |
| Aggregate dashboard | FastAPI + React | Custom |

---

# 28. What Must Be Written by the Team

This project is not just a repository assembly exercise.

The following are custom project components.

## Critical

1. Unified event normalizer.
2. Platform-specific adapters.
3. PostgreSQL persistence layer.
4. NLP orchestration wrapper.
5. Temporal sentiment/emotion aggregation.
6. Dynamic/general-target stance integration.
7. Graph edge extraction.
8. Network analysis runner.
9. Trend scheduling/micro-batching.
10. API/dashboard bridge.

## Important

11. Replay engine.
12. Geographic normalization.
13. Professional-interest classifier.
14. Secret management.
15. Monitoring/health endpoints.
16. Error recovery/checkpointing.

## Optional

17. M3 vision demographic service.
18. NDLib propagation simulation.
19. Cas.In influence analysis.
20. Reddit integration.
21. Meta webhook integrations.

---

# 29. Build Phases

**Priority decision (2026-09-20):** X is the first real platform milestone. This supersedes the older Telegram-first ordering while keeping the platform-independent architecture intact.

## Phase 0: Integration Spike

Before building the full application:

- create Python 3.13 environment;
- install/test current dependencies;
- load sentiment model;
- load irony model;
- load GoEmotions;
- load NetworkX;
- load BERTrend;
- initialize the Tweepy client;
- test PostgreSQL.

This phase exists to catch dependency reality before application scaffolding.

## Phase 1: Canonical data layer

Build:
- Pydantic event model;
- PostgreSQL tables;
- ingestion queue;
- normalization.

## Phase 2: PostgreSQL persistence

Build migrations and repositories for canonical events, users, NLP analysis, graph edges, and chronological/idempotent queries.

## Phase 3: X adapter

Implement:

```text
X recent search / filtered stream
 -> normalization
 -> canonical event
```

Recent search is implemented and verified first; filtered stream is the live path where account access permits it.

## Phase 4: X persistence connection

Implement and verify:

```text
X post
 -> canonical event
 -> PostgreSQL
 -> repository retrieval
```

## Phase 5: NLP

Implement:
- sentiment;
- emotions;
- irony;
- supported fixed-target stance;
- explicit unsupported state for unvalidated arbitrary targets.

## Phase 6: Temporal analytics

Implement rolling one-hour/15-minute-step and daily aggregates from source `created_at`.

## Phase 7: Graph analytics

Implement:
- event -> edge extraction;
- NetworkX;
- centrality;
- PageRank;
- HITS;
- Louvain.

## Phase 8: FastAPI

Expose typed health, event, temporal, trend-summary, and network endpoints.

The first complete working path is:

```text
X/replay event
 -> normalization
 -> PostgreSQL
 -> NLP
 -> temporal aggregation
 -> graph
 -> FastAPI
```

## Phase 9: Future adapter preparation

Prepare boundaries for Telegram, YouTube, Meta, and Reddit. Do not implement those platforms or the React dashboard until the X-backed milestone is verified.

---

# 30. Build-Readiness Gate

Before full implementation:

- [ ] Python 3.13 environment created
- [ ] Dependency resolution completed
- [ ] Sentiment model loads
- [ ] GoEmotions model loads
- [ ] Irony model loads
- [ ] Stance approach selected and tested
- [ ] BERTrend loads
- [ ] NetworkX loads
- [ ] Telethon initializes
- [ ] YouTube API credentials tested
- [ ] X credentials/access verified
- [ ] Meta account/permissions verified if Meta is included in live demo
- [ ] PostgreSQL running
- [ ] Canonical schema frozen
- [ ] Normalization contract frozen
- [ ] Graph edge semantics frozen
- [ ] Temporal windows frozen
- [ ] Privacy rules frozen
- [ ] `.env` and secret handling configured
- [ ] Replay data generated
- [ ] End-to-end sample event passes through the system

---

# 31. Acceptance Criteria

The implementation is considered successful when:

## A. Ingestion

At least one live-capable platform and one additional source can feed the normalized pipeline.

## B. Timeline

Events are stored with:
- original timestamp;
- collection timestamp;
- parent relationship where available.

## C. NLP

A single event produces:
- sentiment;
- emotion;
- irony;
- stance when target configuration permits.

## D. Temporal analysis

The system can show sentiment/emotion changes across multiple time windows.

## E. Trends

The system can display an emerging/rising topic with temporal evidence.

## F. Network

The system can construct a graph and calculate:
- PageRank;
- HITS;
- centrality;
- communities.

## G. Demographics

The system can display at least:
- age bracket;
- language;
- geography;
- professional sector

at aggregate level, with UNKNOWN handling.

## H. Dashboard

An evaluator can see the complete chain from incoming event to analytics.

---

# 32. Non-Goals

The hackathon version will NOT attempt to guarantee:

- unrestricted access to every user's data on every platform;
- arbitrary scraping of private accounts;
- exact age;
- exact residential location;
- perfect sarcasm detection;
- perfect stance detection for every possible topic;
- universal demographic accuracy;
- massive-scale graph processing beyond the chosen infrastructure;
- inference of every possible social relation;
- legally unrestricted redistribution of all collected platform content.

The system shall state these limitations instead of hiding them.

---

# 33. Known Risks

## Risk 1: X access

API access, read volume, pricing, and available endpoints can change.

Mitigation:
- abstract X adapter;
- replay mode;
- monitor API usage.

## Risk 2: Meta restrictions

Instagram/Facebook access is constrained by ownership, permissions, and account type.

Mitigation:
- current Graph API adapter;
- owned test assets;
- replay data.

## Risk 3: Legacy demographics

M3Inference is old.

Mitigation:
- isolate;
- test;
- replace if necessary.

## Risk 4: TweetNLP wrapper age

The social models are valuable but the wrapper has older Transformers assumptions.

Mitigation:
- load checkpoints through current APIs where appropriate.

## Risk 5: Dynamic stance

TweetNLP fixed-target models do not automatically prove arbitrary-topic stance.

Mitigation:
- separate general stance/NLI component.

## Risk 6: BERTrend computational cost

Transformer-based topic modeling can be expensive.

Mitigation:
- micro-batching;
- configurable intervals;
- GPU or remote embedding service when available.

## Risk 7: Network scaling

NetworkX is in-memory.

Mitigation:
- rolling graph windows;
- sampled betweenness;
- archive old edges in PostgreSQL;
- upgrade to a distributed graph system only if genuinely needed.

---

# 34. Recommended Minimal Stack

## Essential

1. `tweepy/tweepy`
2. `LonamiWebs/Telethon`
3. CardiffNLP social transformer checkpoints
4. `SamLowe/roberta-base-go_emotions`
5. `rte-france/BERTrend`
6. `networkx/networkx`
7. PostgreSQL
8. FastAPI
9. React/Chart.js

## Optional platform integrations

10. Current Meta Graph API adapter
11. YouTube Data API
12. Reddit adapter

## Optional research components

13. `GiulioRossetti/ndlib`
14. `computationalmedia/cascade-influence`
15. M3Inference

---

# 35. Recommended Repository / Library Philosophy

The final implementation should not be forced to contain a GitHub repository for every PS bullet.

For mature infrastructure, a standard library is often preferable to a third-party demo repository.

Examples:
- NetworkX instead of an abandoned social-graph repository;
- official Google client instead of a student YouTube Flask wrapper;
- direct current Meta API instead of an outdated SDK wrapper;
- current Hugging Face model loading instead of a fragile NLP wrapper.

The objective is a defensible engineering system, not a collection of repository links.

---

# 36. Current Final Architecture Decision

```text
                ┌─────────────────────────┐
                │     PLATFORM LAYER      │
                ├─────────────────────────┤
                │ X / Tweepy               │
                │ Telegram / Telethon      │
                │ YouTube / Google API     │
                │ Meta / Current Graph API │
                │ Reddit / optional        │
                └────────────┬────────────┘
                             │
                             ▼
                ┌─────────────────────────┐
                │  EVENT NORMALIZATION    │
                │ Pydantic canonical model│
                └────────────┬────────────┘
                             │
                             ▼
                ┌─────────────────────────┐
                │       PostgreSQL        │
                │ Timeline + raw events   │
                └───────┬─────┬─────┬─────┘
                        │     │     │
               ┌────────┘     │     └─────────┐
               ▼              ▼               ▼
        ┌────────────┐ ┌────────────┐  ┌────────────┐
        │ NLP        │ │ Demographic│  │ BERTrend   │
        │ Sentiment  │ │ Age        │  │ Topics     │
        │ Emotion    │ │ Language   │  │ Trends     │
        │ Irony      │ │ Geography  │  │ Velocity   │
        │ Stance     │ │ Profession │  │ Emergence  │
        └─────┬──────┘ └─────┬──────┘  └─────┬──────┘
              │               │               │
              └───────────────┼───────────────┘
                              ▼
                   ┌────────────────────┐
                   │     NetworkX       │
                   │ Graph construction │
                   │ PageRank / HITS    │
                   │ Centrality         │
                   │ Communities        │
                   └─────────┬──────────┘
                             │
                  ┌──────────┴──────────┐
                  ▼                     ▼
             NDLib (opt.)          Cas.In (opt.)
             Diffusion             Influence
                  │                     │
                  └──────────┬──────────┘
                             ▼
                  ┌────────────────────┐
                  │   FastAPI API      │
                  │ REST + WebSocket   │
                  └─────────┬──────────┘
                            ▼
                  ┌────────────────────┐
                  │ React Dashboard    │
                  │ Timeline           │
                  │ Sentiment          │
                  │ Emotion            │
                  │ Trends             │
                  │ Demographics       │
                  │ Network            │
                  └────────────────────┘
```

---

# 37. Final Project Position

The system is **technically implementable**, but not every platform can promise unrestricted live collection.

The strongest implementation strategy is therefore:

```text
LIVE CAPABLE CORE
Telegram + X (when account access permits)
        +
YouTube polling
        +
Meta owned-page integration
        +
Replay fallback
```

with:

```text
Shared Analytics
NLP + Demographics + Trends + Graph
```

The most important engineering distinction is:

> **External components provide specialized capabilities. The team owns the integration layer.**

No external repository currently provides the entire PS as a turnkey application.

---

# 38. External References

## GitHub / implementation references

- TweetNLP: https://github.com/cardiffnlp/tweetnlp
- TweetEval: https://github.com/cardiffnlp/tweeteval
- Telethon: https://github.com/LonamiWebs/Telethon
- Tweepy: https://github.com/tweepy/tweepy
- BERTrend: https://github.com/rte-france/BERTrend
- NetworkX: https://github.com/networkx/networkx
- M3Inference: https://github.com/euagendas/m3inference
- Sage Meta: https://github.com/sageteamorg/python-sage-meta
- ScrapiReddit: https://github.com/vewaxio/ScrapiReddit
- NDLib: https://github.com/GiulioRossetti/ndlib
- Cascade Influence: https://github.com/computationalmedia/cascade-influence
- fastText: https://github.com/facebookresearch/fastText

## Model

- GoEmotions checkpoint: https://huggingface.co/SamLowe/roberta-base-go_emotions

## Official platform documentation

- Telegram API ID: https://core.telegram.org/api/obtaining_api_id
- YouTube API overview: https://developers.google.com/youtube/v3/getting-started
- YouTube comment threads: https://developers.google.com/youtube/v3/docs/commentThreads/list
- YouTube comments: https://developers.google.com/youtube/v3/docs/comments/list

For X and Meta, consult the current official developer documentation at build time because platform access policies, API versions, pricing, permissions, and quotas can change.

---

# 39. Build Rule

**Do not begin full application implementation until the Phase 0 integration spike passes.**

The first executable milestone is:

```text
ONE REAL EVENT
    ↓
NORMALIZE
    ↓
STORE
    ↓
NLP
    ↓
GRAPH EDGE
    ↓
TEMPORAL METRIC
    ↓
DASHBOARD
```

Once that path works, expand horizontally to the remaining platforms and analytics modules.
