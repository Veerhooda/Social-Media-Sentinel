# BUILDER PROMPT
# AI-Driven Social Media Analytics Framework

You are the primary software-engineering agent responsible for building this project.

Before writing application code, read `SPECS.md` completely and treat it as the project's current technical specification.

Your job is to TURN THE SPECIFICATION INTO A WORKING REPOSITORY, not to produce another architecture essay.

---

# 0. OPERATING MODE

Work as a senior implementation engineer.

Rules:

1. Read `SPECS.md` first.
2. Do not ignore, silently change, or contradict the specification.
3. If the specification contains a known uncertainty, verify it before implementing.
4. Prefer simple, working solutions over unnecessary infrastructure.
5. Do not add Kafka, Redis, Kubernetes, microservices, or other infrastructure merely because it sounds impressive.
6. Build in small verified increments.
7. Run tests after meaningful changes.
8. Never claim something works unless you actually tested it or clearly mark it as untested.
9. Never fake platform data, API responses, model outputs, or test results.
10. Never commit credentials, access tokens, Telegram sessions, or real social-media data.
11. Keep platform-specific code behind clean adapters.
12. Preserve a replay/demo mode so the project remains testable without every external API being available.
13. Do not replace a verified component with a random alternative without documenting the reason.
14. When a dependency or platform API has changed, update the implementation to the current supported interface and document the change.
15. If a blocker is encountered, isolate it and continue building everything that is not blocked.

The priority order is:

```text
Correctness
    >
Working end-to-end path
    >
PS coverage
    >
Reliability
    >
Performance
    >
Visual polish
```

---

# 1. PROJECT OBJECTIVE

Build an AI-driven Social Media Analytics Framework covering:

A. Continuous Data Collection & Timeline Management
B. Multi-Dimensional Sentiment Inference
C. Automated Demographic Profiling
D. Real-Time Trend & Topic Detection
E. Link Analysis & Network Topology

The system should ultimately support:

```text
PLATFORM INGESTION
        ↓
EVENT NORMALIZATION
        ↓
POSTGRESQL TIMELINE
        ↓
┌─────────────┬──────────────┬──────────────┐
│ NLP         │ DEMOGRAPHICS │ TRENDS       │
└─────────────┴──────────────┴──────────────┘
        ↓
NETWORK / DIFFUSION / INFLUENCE
        ↓
FASTAPI
        ↓
REACT DASHBOARD
```

---

# 2. IMPORTANT ARCHITECTURAL DECISIONS

## Runtime

Use modern Python.

Target:

```text
Python 3.13
```

Do NOT force legacy M3Inference into the main runtime.

## Main components

### Platform ingestion

- X: `tweepy`
- Telegram: `Telethon`
- YouTube: `google-api-python-client`
- Instagram/Facebook: current Meta Graph API adapter
- Reddit: optional adapter using `ScrapiReddit` initially or OAuth/PRAW where appropriate

### NLP

Use CardiffNLP social-media transformer checkpoints where appropriate.

Primary tasks:

```text
Sentiment
Irony
Stance (only for supported/fixed targets)
```

Use:

```text
SamLowe/roberta-base-go_emotions
```

for fine-grained emotion.

Map:

```text
nervousness -> anxiety
```

Do not claim that anxiety is a native GoEmotions class.

### Trends

Use:

```text
rte-france/BERTrend
```

with micro-batched social-media text.

### Graph

Use:

```text
networkx
```

for:

- degree centrality
- betweenness centrality
- closeness centrality
- PageRank
- HITS
- Louvain communities

### Diffusion

Optional:

```text
GiulioRossetti/ndlib
```

### Empirical cascade influence

Optional:

```text
computationalmedia/cascade-influence
```

### Demographics

Potential:

```text
M3Inference
```

but treat it as an isolated/optional legacy component.

Use current text/location/language tools where they provide a cleaner implementation.

### Storage

```text
PostgreSQL
```

### Backend

```text
FastAPI + Uvicorn
```

### Frontend

```text
React
Chart.js or another lightweight charting library
```

---

# 3. DO NOT START WITH THE DASHBOARD

The first goal is a complete backend vertical slice.

Build this first:

```text
X recent-search post / filtered-stream post
      ↓
Normalizer
      ↓
PostgreSQL
      ↓
Sentiment
      ↓
Emotion
      ↓
Irony
      ↓
Graph edge
      ↓
Temporal metric
      ↓
FastAPI response
```

Once that works, expand.

---

# 4. PHASE 0: INTEGRATION SPIKE

Before creating the full architecture, establish a reproducible development environment.

Create:

```text
pyproject.toml
.env.example
.gitignore
README.md
```

Recommended structure:

```text
social-analytics/
├── app/
├── tests/
├── scripts/
├── data/
│   ├── replay/
│   └── samples/
├── migrations/
├── frontend/
├── docs/
├── docker/
├── .env.example
├── .gitignore
├── pyproject.toml
├── README.md
└── SPECS.md
```

Do not commit real `.env`.

---

# 5. PHASE 0 SMOKE TESTS

Create a script such as:

```text
scripts/smoke_test.py
```

It must verify, as far as local dependencies allow:

1. Python version.
2. PostgreSQL connectivity.
3. Pydantic import.
4. FastAPI import.
5. Tweepy import.
6. Telethon import.
7. Transformers import.
8. PyTorch import.
9. NetworkX import.
10. BERTrend import.
11. Sentiment model loading.
12. GoEmotions model loading.
13. Irony model loading.
14. A simple NetworkX graph calculation.

For each test print:

```text
PASS
FAIL
SKIPPED
```

Do not hide failures.

For anything requiring credentials:
- verify configuration exists;
- perform the live request only when credentials are present;
- otherwise mark it `SKIPPED`.

---

# 6. DEPENDENCY STRATEGY

Avoid blindly installing the newest version of every package.

For each major dependency:

```text
package
version
Python requirement
known compatibility issue
test status
```

Maintain this information in:

```text
docs/dependencies.md
```

Important:

- BERTrend currently targets modern Python.
- NetworkX currently targets modern Python.
- TweetNLP's wrapper is older and should not become the single point of dependency failure.
- Where practical, use the verified CardiffNLP checkpoints directly with the current Transformers interface.
- M3Inference is legacy and should remain isolated if retained.

If dependency conflicts exist, prefer:

```text
main modern environment
+
optional isolated legacy environment
```

rather than downgrading the entire project.

---

# 7. CANONICAL DATA MODEL

Implement the canonical event model from `SPECS.md`.

Use Pydantic.

Create something like:

```text
app/models/events.py
```

The model must support:

- event_id
- platform
- platform_post_id
- parent_platform_post_id
- thread_root_id
- interaction_type
- created_at
- collected_at
- author
- content
- relationships
- metrics
- source_metadata

Timestamps must be timezone-aware and normalized to UTC.

Reject malformed events.

---

# 8. DATABASE IMPLEMENTATION

Create PostgreSQL migrations for:

```text
social_users
social_events
nlp_analysis
user_demographics
topics
trend_measurements
graph_edges
dead_letter_events
```

Use the schema in `SPECS.md` as the baseline.

Add:

- indexes;
- uniqueness constraints;
- foreign keys;
- JSONB where appropriate;
- idempotent insertion.

The storage layer must support:

```text
insert event
upsert user
insert NLP result
insert demographic result
insert topic
insert trend measurement
insert graph edge
```

Do not put SQL directly throughout business logic.

Use a repository/data-access layer.

---

# 9. INGESTION ARCHITECTURE

Create an adapter interface.

For example:

```python
class PlatformAdapter(Protocol):
    async def historical(...): ...
    async def listen(...): ...
```

The exact interface may be adjusted where a platform's API is fundamentally different.

Every adapter should produce canonical events.

---

# 10. TELEGRAM ADAPTER

Do not implement Telegram until the X vertical slice has passed its end-to-end acceptance test.

Use:

```text
Telethon
```

Support:

### Historical
- channel history;
- timestamps;
- sender;
- replies;
- forwards where available.

### Live
Use Telethon's live event mechanism.

### Requirements
Credentials:

```text
TELEGRAM_API_ID
TELEGRAM_API_HASH
TELEGRAM_SESSION_STRING
```

Do not store the Telegram session in Git.

Implement:

- reconnect handling;
- FloodWait handling;
- duplicate prevention;
- cursor/checkpointing where practical.

Do not monitor private conversations.

---

# 11. X ADAPTER

Implement X behind an adapter.

Use Tweepy/current X API access.

Support where access permits:

- recent posts;
- user metadata;
- mentions;
- replies;
- repost/quote relationships;
- timestamps.

Implement both:

```text
stream mode
poll/search mode
```

with replay fallback.

Do not hard-code assumptions about X pricing or access tiers.

At runtime, detect API errors and surface them clearly.

---

# 12. YOUTUBE ADAPTER

Use the official Google API client.

Primary endpoint:

```text
commentThreads.list
```

Use:

```text
comments.list
```

when complete reply retrieval is necessary.

Implement:

```text
poll
→ deduplicate comment IDs
→ normalize
→ enqueue
```

Do not call polling a push stream.

---

# 13. META ADAPTER

Do not depend on the old Sage Meta wrapper as the final integration.

Create a thin current-version Graph API adapter.

Structure:

```text
app/ingestion/meta/
├── client.py
├── instagram.py
├── facebook.py
├── auth.py
└── models.py
```

Use only capabilities available to the authenticated account and permissions.

Support:

- Page/media retrieval;
- comments;
- replies where available;
- timestamps;
- metrics where available.

Do not attempt unauthorized public-profile scraping.

---

# 14. REDDIT ADAPTER

Keep Reddit optional.

Initial implementation may use:

```text
vewaxio/ScrapiReddit
```

behind an adapter.

The adapter must support:

- posts;
- comments;
- parent IDs;
- timestamps.

Keep the interface compatible with a future OAuth/PRAW implementation.

---

# 15. NORMALIZATION PIPELINE

Implement:

```text
platform payload
      ↓
adapter-specific parser
      ↓
canonical Pydantic event
      ↓
validation
      ↓
PostgreSQL
```

Create:

```text
app/normalization/
├── base.py
├── twitter.py
├── telegram.py
├── youtube.py
├── reddit.py
├── instagram.py
└── facebook.py
```

Do not leak platform-specific structures into downstream analytics.

---

# 16. NLP SERVICE

Create:

```text
app/nlp/
├── service.py
├── sentiment.py
├── emotion.py
├── irony.py
├── stance.py
├── preprocessing.py
└── schemas.py
```

Input:

```python
NormalizedEvent
```

Output:

```text
NLPResult
```

The output should contain:

```json
{
  "sentiment": {
    "label": "...",
    "scores": {}
  },
  "emotions": {},
  "sarcasm": {
    "is_sarcastic": false,
    "score": 0.0
  },
  "stance": {
    "target": null,
    "label": null,
    "score": null
  }
}
```

Record model versions.

Use batched inference.

Use `torch.no_grad()`.

---

# 17. SENTIMENT

Use:

```text
cardiffnlp/twitter-roberta-base-sentiment-latest
```

Outputs:

```text
positive
neutral
negative
```

Preserve the full probability distribution.

Do not infer sentiment from emotion labels.

---

# 18. EMOTION

Use:

```text
SamLowe/roberta-base-go_emotions
```

Store multi-label scores.

Important mappings:

```text
nervousness -> anxiety
excitement -> excitement
```

Store the original model label if useful, so transformations remain auditable.

Do not reduce the model to one arbitrary emotion unless a UI view specifically needs a primary emotion.

---

# 19. IRONY / SARCASM

Use:

```text
cardiffnlp/twitter-roberta-base-irony
```

Output:

```text
irony probability
non-irony probability
```

Define a configurable threshold.

Do not call the classifier infallible.

---

# 20. STANCE

Implement TWO modes.

## Fixed-target mode

Use TweetNLP stance checkpoints for supported targets.

## General-target mode

Do NOT assume TweetNLP can accept arbitrary emerging topics.

Implement a separate general NLI/stance adapter.

The interface should look like:

```python
class StanceAnalyzer:
    def analyze(self, text: str, target: str) -> StanceResult:
        ...
```

The actual model checkpoint must be validated during the integration spike.

---

# 21. TEMPORAL ANALYTICS

Create:

```text
app/analytics/
├── temporal.py
├── sentiment_timeseries.py
├── emotion_timeseries.py
└── aggregation.py
```

Use initial windows:

```text
rolling window = 1 hour
step = 15 minutes
daily summary = 24 hours
```

Calculate:

- post count;
- positive ratio;
- neutral ratio;
- negative ratio;
- anxiety average;
- excitement average;
- emotion distributions;
- sarcasm rate;
- stance distribution.

Never derive time-series metrics from current timestamps when source `created_at` is available.

---

# 22. TREND ENGINE

Use:

```text
rte-france/BERTrend
```

Create:

```text
app/trends/
├── service.py
├── batching.py
├── persistence.py
└── schemas.py
```

Input:

```text
text + timestamp
```

Schedule:

```text
every 15 minutes initially
```

or trigger when sufficient documents are available.

Persist:

- topic;
- keywords;
- document count;
- velocity;
- acceleration;
- status;
- observation window.

Do not run BERTrend on every individual post.

---

# 23. GRAPH ENGINE

Create:

```text
app/graph/
├── builder.py
├── metrics.py
├── communities.py
├── temporal.py
└── schemas.py
```

Build a directed weighted graph.

Example:

```text
reposter → original author
mentioner → mentioned user
replier → parent author
commenter → parent commenter
```

The graph builder is OUR code.

NetworkX provides the algorithms, not platform-specific extraction.

---

# 24. GRAPH METRICS

Implement:

```python
nx.in_degree_centrality(G)
nx.out_degree_centrality(G)
nx.betweenness_centrality(G)
nx.closeness_centrality(G)
nx.pagerank(G)
nx.hits(G)
nx.community.louvain_communities(...)
```

Store results separately from raw edges.

Use configurable time windows.

For very large graphs:
- use rolling windows;
- approximate betweenness;
- avoid loading the entire historical graph unnecessarily.

Do not invent a synthetic social network in production.

---

# 25. CASCADE / DIFFUSION

These are optional until the core pipeline is working.

## NDLib

Use for controlled propagation simulations.

## Cas.In

Use only for historical cascade influence.

Create adapters that transform internal events into the required cascade format.

Do not present Cas.In as a live streaming influence engine.

---

# 26. DEMOGRAPHIC ENGINE

Create:

```text
app/demographics/
├── service.py
├── age.py
├── language.py
├── geography.py
├── profession.py
└── schemas.py
```

## Age

Potentially use M3Inference.

But first test whether it is operationally usable.

Do not block the whole project on it.

## Language

Use a current language-ID runtime/model compatible with the selected environment.

## Geography

Normalize self-reported public location strings.

Do not infer exact residence.

## Professional interest

Implement a configurable zero-shot classifier over a controlled taxonomy.

Initial sectors:

```text
Technology / Software
Finance / Banking
Healthcare / Medicine
Education / Research
Arts / Entertainment
Sales / Marketing
Trades / Labor
Student / Academic
```

Store:
- label;
- confidence;
- model version.

---

# 27. DEMOGRAPHIC PRIVACY

Demographics are for aggregate audience analysis.

Do not display:

```text
User X is 27 years old and works in finance.
```

Prefer:

```text
19–29 = 42%
30–39 = 23%
Unknown = 35%
```

For profile-image inference:
- process bytes ephemerally;
- do not persist face crops;
- do not persist unnecessary image data.

Always support:

```text
UNKNOWN
```

and confidence.

---

# 28. REPLAY ENGINE

Build a replay mechanism early.

Structure:

```text
data/replay/
```

Create records for:

- X;
- Telegram;
- Instagram;
- Facebook;
- Reddit;
- YouTube.

Replay events must have realistic:
- timestamps;
- replies;
- mentions;
- reposts;
- nested comments;
- multiple users;
- topic changes.

The replay engine must emit the exact same canonical event format as live collectors.

This is essential for deterministic development and demos.

---

# 29. API

Create FastAPI endpoints.

Minimum:

```text
GET /health
GET /events
GET /events/{id}
GET /sentiment/timeline
GET /emotions/timeline
GET /trends
GET /trends/{id}
GET /network/top
GET /network/communities
GET /demographics
WS  /ws/events
```

Return Pydantic response models.

Do not expose raw credentials or unnecessary raw personal data.

---

# 30. DASHBOARD

Only after backend functionality exists.

Create:

```text
frontend/
```

Minimum screens:

### Overview

- event volume;
- current sentiment;
- current trending topics;
- active users.

### Sentiment

- positive/neutral/negative timeline;
- anxiety;
- excitement;
- sarcasm;
- stance.

### Trends

- emerging topics;
- velocity;
- acceleration;
- keywords.

### Network

- graph;
- PageRank;
- HITS;
- centrality;
- communities.

### Audience

- age;
- geography;
- language;
- professional sectors.

Demographic view must be aggregate.

---

# 31. FRONTEND DATA RULE

The frontend must consume the FastAPI API.

Do not make the frontend directly call platform APIs.

Architecture:

```text
Platform
 ↓
Backend
 ↓
Database / Analytics
 ↓
FastAPI
 ↓
React
```

---

# 32. ERROR HANDLING

Every external integration needs bounded retries.

Implement:
- exponential backoff;
- jitter;
- rate-limit handling;
- timeout;
- structured errors.

Platform-specific:

### Telegram
Catch:

```python
FloodWaitError
```

### HTTP APIs
Handle:
- 429;
- 401;
- 403;
- 5xx.

### Model inference
Handle:
- missing model;
- tokenizer failure;
- CUDA OOM;
- invalid input.

### Database
Handle:
- connection failure;
- serialization issues;
- duplicate keys.

Bad events go to:

```text
dead_letter_events
```

Do not crash the entire collector because one event is malformed.

---

# 33. OBSERVABILITY

Add structured logs.

Minimum fields:

```text
timestamp
service
platform
event_id
operation
duration_ms
status
error
```

Counters:
- events received;
- events normalized;
- events stored;
- NLP processed;
- NLP failures;
- graph updates;
- trend updates;
- API errors.

---

# 34. TESTING STRATEGY

Testing is mandatory.

## Unit tests

Test:
- schemas;
- validators;
- normalizers;
- timestamp handling;
- graph edge extraction;
- SQL repositories;
- NLP result parsing;
- demographic uncertainty;
- trend aggregation.

## Integration tests

At minimum:

```text
fixture event
 ↓
normalizer
 ↓
database
 ↓
NLP
 ↓
graph
 ↓
analytics
```

## Platform tests

Use recorded/mock payloads.

Do not require external credentials for unit tests.

## Model smoke tests

Each model must have a deterministic smoke test that verifies:
- load;
- inference;
- expected label set;
- output format.

---

# 35. ACCEPTANCE TEST

Create a single end-to-end acceptance test.

Input:

```text
one realistic social event
```

Expected:

```text
event normalized
↓
stored
↓
NLP result generated
↓
graph edge generated if applicable
↓
temporal aggregate updated
↓
API exposes resulting data
```

Then repeat with:
- reply;
- mention;
- repost;
- multiple users.

---

# 36. DEMO ACCEPTANCE PATH

The first hackathon demo should demonstrate:

```text
1. Live X event when access permits, otherwise clearly labeled X replay
        ↓
2. Event appears in database
        ↓
3. Sentiment + emotion + irony analysis
        ↓
4. Stance analysis where target is available
        ↓
5. Graph edge created
        ↓
6. Network metrics updated
        ↓
7. Trend engine updates
        ↓
8. Dashboard updates
```

Use replay for platforms whose live access is unavailable.

Never pretend replay data is live data.

---

# 37. IMPLEMENTATION ORDER

The initial platform priority changed on 2026-09-20. Follow this order:

```text
PHASE 0
Environment + dependency smoke tests

PHASE 1
Pydantic event schemas

PHASE 2
PostgreSQL + migrations

PHASE 3
X recent-search adapter

PHASE 4
X filtered-stream adapter

PHASE 5
X normalizer + persistence

PHASE 6
NLP service

PHASE 7
Temporal analytics

PHASE 8
Graph builder + NetworkX metrics

PHASE 9
Replay engine

PHASE 10
FastAPI API

PHASE 11
X/replay end-to-end tests

PHASE 12
BERTrend integration

PHASE 13
Future adapter preparation

PHASE 14
Telegram adapter

PHASE 15
YouTube adapter

PHASE 16
Meta adapter

PHASE 17
Reddit adapter

PHASE 18
Demographics

PHASE 19
React dashboard

PHASE 20
Demo hardening
```

Do not jump to Phase 15 because building dashboards is more visually satisfying than writing database migrations. The database does not care about our feelings.

---

# 38. GIT / REPOSITORY RULES

Use logical commits.

Suggested milestones:

```text
chore: initialize project
feat: add canonical event schema
feat: add postgres persistence
feat: add telegram ingestion
feat: add nlp pipeline
feat: add temporal analytics
feat: add graph analytics
feat: add trend engine
feat: add x adapter
feat: add youtube adapter
feat: add meta adapter
feat: add demographics
feat: add replay engine
feat: add api
feat: add dashboard
test: add end-to-end pipeline
```

Never commit:
- `.env`;
- Telegram `.session`;
- API tokens;
- real API credentials;
- private user data;
- database dumps;
- unnecessary model binaries.

---

# 39. SECURITY BASELINE

Create `.gitignore` entries for:

```text
.env
*.session
*.db
*.sqlite
*.sqlite3
*.sql
*.dump
__pycache__/
.venv/
.env.*
*.pt
*.pth
*.bin
```

Be careful with model files:
- some can be downloaded during setup;
- others may be suitable for local caching;
- never commit enormous artifacts without a deliberate decision.

---

# 40. CONFIGURATION

Create:

```text
.env.example
```

with placeholders only:

```dotenv
DATABASE_URL=

TELEGRAM_API_ID=
TELEGRAM_API_HASH=
TELEGRAM_SESSION_STRING=

X_BEARER_TOKEN=
X_CLIENT_ID=
X_CLIENT_SECRET=

YOUTUBE_API_KEY=

META_APP_ID=
META_APP_SECRET=
META_ACCESS_TOKEN=

APP_ENV=development
API_HOST=0.0.0.0
API_PORT=8000

NLP_BATCH_SIZE=16
GRAPH_INTERVAL_SECONDS=300
TREND_INTERVAL_SECONDS=900
SENTIMENT_WINDOW_MINUTES=60
```

Never place realistic-looking fake credentials in production configuration examples.

---

# 41. DOCUMENTATION TO MAINTAIN

Create:

```text
docs/
├── architecture.md
├── dependencies.md
├── api-access.md
├── data-model.md
├── nlp.md
├── demographics.md
├── graph.md
├── trends.md
├── demo.md
└── limitations.md
```

Update documentation when implementation changes.

---

# 42. PLATFORM LIMITATIONS DOCUMENT

Explicitly document:

### X
Access depends on current API product/account and usage limits.

### Telegram
MTProto credentials and authorized user session are required.

### Meta
Instagram/Facebook access depends on account ownership, permissions, and current Graph API capabilities.

### Reddit
Unofficial public scraping may be rate-limited; keep an OAuth path available.

### YouTube
Comments are obtained through API polling, not treated as a native push stream.

---

# 43. PERFORMANCE TARGETS

Initial hackathon targets:

```text
event normalization: <100 ms/event excluding network
NLP batch inference: configurable
Telegram ingestion latency: near-real-time
YouTube polling: configurable 10–60 seconds
graph refresh: <=5 minutes
trend refresh: <=15 minutes
API response: <1 second for common dashboard queries
```

These are engineering targets, not guaranteed platform-level SLAs.

Measure actual values.

---

# 44. DATA RETENTION

Implement enough retention control to allow:

- event deletion;
- raw payload removal;
- demographic result removal;
- replay/test data separation.

Do not retain data forever just because PostgreSQL politely offers to do so.

---

# 45. WHAT COUNTS AS DONE

A feature is DONE only when:

1. Code exists.
2. It is connected to the correct upstream/downstream component.
3. It has tests.
4. It has been executed successfully.
5. Its output is observable.
6. Any external dependency/caveat is documented.

A repository being installed does not mean a PS feature is DONE.

---

# 46. AGENT WORKING STYLE

At the start of every work session:

1. Read the current project state.
2. Read relevant sections of `SPECS.md`.
3. Inspect existing code before adding new code.
4. Identify the smallest next implementation unit.
5. Implement it.
6. Run tests.
7. Fix failures.
8. Update documentation.
9. Report exactly what changed and what remains.

Do not rewrite working modules unnecessarily.

Do not perform large speculative refactors.

---

# 47. DECISION RULES FOR UNCERTAINTY

When you find uncertainty:

### If it is an API issue
Check current official documentation.

### If it is a repository/library issue
Inspect actual source and package metadata.

### If it is a model issue
Verify:
- checkpoint;
- labels;
- input requirements;
- inference path.

### If it is a dependency issue
Test the import/runtime compatibility.

### If it cannot be resolved quickly
Isolate the component and continue with the rest of the system.

Never silently invent an answer.

---

# 48. FIRST TASK

Do NOT start by writing the full application.

Your FIRST TASK is:

```text
1. Read SPECS.md.
2. Inspect the empty/current repository.
3. Create the initial project structure.
4. Create pyproject.toml.
5. Create .gitignore.
6. Create .env.example.
7. Create the first database migration skeleton.
8. Create the canonical Pydantic event model.
9. Create the dependency/model smoke-test script.
10. Run the smoke test.
11. Fix all local dependency/import errors.
12. Report the exact results.
```

Do not implement the dashboard yet.

Do not implement every platform yet.

Do not add unnecessary infrastructure.

The first milestone is:

```text
PROJECT BOOTS
+
DEPENDENCIES RESOLVE
+
EVENT MODEL VALIDATES
+
DATABASE CAN CONNECT
```

Then proceed to the X vertical slice.

---

# 49. REQUIRED FINAL RESPONSE AFTER EACH IMPLEMENTATION STEP

After completing each meaningful step, report:

```text
IMPLEMENTED
-----------
What changed.

FILES
-----
Files created/modified.

TESTS
-----
Commands executed and results.

PS COVERAGE
-----------
Which PS requirement this advances.

KNOWN ISSUES
------------
Anything not verified.

NEXT STEP
---------
The single next implementation task.
```

Be factual.

Do not say "fully complete" unless the corresponding acceptance test actually passed.

---

# 50. FINAL SUCCESS CONDITION

The project is successful when the evaluator can see:

```text
Social event arrives
        ↓
Stored chronologically
        ↓
Sentiment inferred
        ↓
Emotion inferred
        ↓
Irony/sarcasm inferred
        ↓
Stance inferred where supported
        ↓
Audience demographics aggregated
        ↓
Emerging topics detected
        ↓
Network graph updated
        ↓
Centrality / PageRank / HITS / communities calculated
        ↓
Temporal propagation analyzed
        ↓
Dashboard displays the results
```

with real API data where available and clearly labeled replay data where access restrictions prevent live collection.

Build the system incrementally, verify every important claim, and leave the codebase in a state another engineer can understand and run.
