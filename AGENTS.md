# AGENTS.md
# AI-Driven Social Media Analytics Framework

This file defines the operating rules for coding agents working on this repository.
It is an execution and engineering policy document, not a replacement for `SPECS.md`.

---

## 1. SOURCE OF TRUTH

Use the project documents in this order:

1. `SPECS.md` - technical specification and architecture contract
2. `AGENTS.md` - agent behavior, workflow, quality, and repository rules
3. `builder_prompt.md` - initial implementation sequence and bootstrap instructions
4. Existing code and tests - current implementation reality
5. Agent assumptions - last resort only, and never silently

When documents conflict, prefer the more authoritative source above and document the conflict rather than silently choosing an interpretation.

A working implementation always takes precedence over an outdated assumption in prose, but update the relevant documentation after changing behavior.

---

## 2. MISSION

Build a working, testable AI-driven social-media analytics framework that covers:

- multi-platform event ingestion;
- chronological storage and timeline management;
- sentiment, emotion, irony/sarcasm, and stance analysis;
- aggregate demographic inference;
- temporal topic and trend detection;
- network topology, influence, communities, and diffusion;
- FastAPI access;
- React dashboard visualization.

The goal is a credible implementation, not a collection of demos glued together with hope and duct tape.

---

## 3. CORE ENGINEERING PRIORITIES

Use this priority order:

```text
Correctness
    >
Verified end-to-end behavior
    >
Problem-statement coverage
    >
Reliability
    >
Maintainability
    >
Performance
    >
Visual polish
```

Do not sacrifice correctness to make a demo look impressive.

Do not build infrastructure merely because it sounds sophisticated.

Avoid adding Kafka, Redis, Kubernetes, Celery, or other infrastructure unless the existing architecture demonstrably requires it.

---

## 4. GENERAL AGENT RULES

### 4.1 Inspect before changing

Before modifying a module:

1. inspect the repository structure;
2. read the relevant source files;
3. inspect related tests;
4. locate the existing interface or data flow;
5. make the smallest change that solves the problem.

Do not rewrite working code without a concrete reason.

### 4.2 Verify, do not invent

Never fabricate:

- API capabilities;
- platform permissions;
- model labels;
- benchmark results;
- test output;
- repository functionality;
- live social-media data;
- credentials;
- performance numbers.

When uncertain, inspect source, package metadata, official documentation, or execute a focused test.

### 4.3 Current APIs matter

Platform APIs and package interfaces can change.

For current API behavior, verify against official documentation before implementing a new integration or changing authentication, endpoints, permissions, or request formats.

Do not encode stale pricing or access-tier assumptions into application logic.

### 4.4 Fail explicitly

A failed dependency, API request, model load, or integration must not be silently converted into fake success.

Use clear statuses such as:

```text
PASS
FAIL
SKIPPED
UNAVAILABLE
```

with enough context to diagnose the issue.

---

## 5. RUNTIME AND STACK

### Primary runtime

Target:

```text
Python 3.13
```

Do not downgrade the entire project to accommodate a legacy dependency.

For old components, isolate them behind an optional boundary or separate environment.

### Primary stack

```text
Python 3.13
Pydantic
PostgreSQL
FastAPI
Uvicorn
React
NetworkX
Transformers / PyTorch
BERTrend
```

Platform adapters:

```text
X          -> Tweepy / current X API
Telegram   -> Telethon
YouTube    -> google-api-python-client
Meta       -> current Graph API adapter
Reddit     -> optional ScrapiReddit/OAuth-compatible adapter
```

Analytics:

```text
Sentiment  -> CardiffNLP social-text checkpoints
Emotion    -> SamLowe/roberta-base-go_emotions
Irony      -> CardiffNLP irony checkpoint
Stance     -> fixed-target CardiffNLP models where supported + separate general-target path
Trends     -> BERTrend
Graphs     -> NetworkX
Diffusion  -> optional NDLib
```

Demographics must remain privacy-conscious and aggregate. Legacy M3Inference may be isolated if retained.

---

## 6. ARCHITECTURE RULES

Keep these boundaries intact:

```text
Platform adapters
        ↓
Canonical event model
        ↓
Validation / normalization
        ↓
PostgreSQL
        ↓
NLP / demographics / trends / graph analytics
        ↓
FastAPI
        ↓
React
```

### Platform isolation

Platform-specific API objects must not leak throughout the application.

Each adapter should translate external payloads into canonical internal events.

### Analytics isolation

NLP, demographics, trend analysis, and graph analytics should expose application-level interfaces instead of making the rest of the system depend directly on model-specific code.

### Persistence isolation

Keep SQL and database-specific persistence in repository/data-access modules.

Do not scatter raw SQL across business logic.

---

## 7. DATA MODEL RULES

The canonical event schema defined by `SPECS.md` is mandatory unless an explicit documented change is made.

Core fields include:

```text
event_id
platform
platform_post_id
parent_platform_post_id
thread_root_id
interaction_type
created_at
collected_at
author
content
relationships
metrics
source_metadata
```

Rules:

- timestamps must be timezone-aware;
- normalize timestamps to UTC internally;
- preserve original source timestamps when useful;
- preserve parent-child relationships where the source provides them;
- make ingestion idempotent;
- reject malformed events;
- route irrecoverable malformed input to a dead-letter path where configured.

Do not silently discard useful source metadata during normalization.

---

## 8. PLATFORM RULES

### X

Use the current supported X API through Tweepy.

Support stream and polling/search modes where the account's permissions allow them.

Never assume an endpoint is available just because the platform displays the information publicly.

### Telegram

Use Telethon.

Support historical retrieval and live channel/message events where authorized.

Handle `FloodWaitError`, reconnects, and duplicate delivery.

Do not monitor private conversations.

Never commit Telegram session files.

### YouTube

Use the official YouTube Data API.

Use polling for comments.

Do not describe polling as a native push stream.

Deduplicate by platform comment identifier.

### Meta

Use a current-version Graph API adapter.

The older Sage Meta project is reference material only.

Do not build around a stale hardcoded Graph API version.

Use only capabilities granted to the authenticated account and permissions.

Do not perform unauthorized public-profile scraping.

### Reddit

Reddit is optional.

Keep the adapter interface compatible with an OAuth-based implementation even if the initial implementation uses public endpoints.

Treat public scraping as potentially rate-limited and non-guaranteed.

---

## 9. NLP RULES

### Sentiment

Return at least:

```text
positive
negative
neutral
confidence
```

### Emotion

Use GoEmotions where appropriate.

The PS term `anxiety` is represented using the `nervousness` label mapping:

```text
nervousness -> anxiety
```

Do not claim `anxiety` is a native GoEmotions label.

### Irony / sarcasm

Use the verified CardiffNLP irony checkpoint where applicable.

Do not assume irony detection equals sarcasm detection in every context. Document any label mapping used by the application.

### Stance

Do not confuse sentiment with stance.

CardiffNLP's stance models are fixed-target models. They cannot be treated as a universal arbitrary-topic stance classifier.

For an emerging topic from BERTrend:

- use a separately validated general-target/NLI approach; or
- mark stance as unsupported when no validated target-specific model exists.

Never pass arbitrary topics into a fixed-target model and claim valid general stance inference.

### Model interfaces

Prefer modern direct checkpoint loading through the current Transformers interface when an older wrapper is incompatible.

Each model service must expose a stable application-level output schema.

---

## 10. DEMOGRAPHIC INFERENCE RULES

Demographic outputs are estimates, not ground truth.

Allowed aggregate dimensions:

- age bracket;
- geographic distribution;
- language;
- professional/occupation sector.

Rules:

- prefer public profile indicators;
- preserve uncertainty/confidence;
- avoid precise residential inference;
- avoid presenting inferred personal attributes as confirmed facts;
- aggregate dashboard reporting by default;
- do not persist raw face crops;
- if profile images are processed, prefer ephemeral processing;
- document model limitations and coverage.

Do not use demographic inference to make unsupported claims about individual users.

---

## 11. TREND RULES

Trend processing must preserve time.

At minimum, support:

- topic discovery;
- rising topics;
- trend velocity;
- ranking;
- temporal evolution;
- weak/strong signals where supported.

Use BERTrend in an isolated service/module boundary.

Do not invent real-time behavior when the implementation is actually batch or micro-batch.

Default refresh targets are implementation settings, not platform guarantees.

---

## 12. GRAPH RULES

Build graphs from normalized events, not raw platform-specific objects.

Configurable default edge weights from `SPECS.md` include:

```text
repost/forward  -> 1.0
quote           -> 1.0
mention         -> 0.5
reply           -> 0.8
```

These are engineering defaults, not empirical claims about influence.

Implement as supported by the available data:

- degree centrality;
- betweenness centrality;
- closeness centrality;
- PageRank;
- HITS;
- community detection;
- temporal diffusion/cascade views.

Do not call centrality a causal measure of real-world influence.

Optional NDLib and cascade-influence functionality must remain isolated from the core graph path.

---

## 13. DATABASE RULES

Core tables are defined by `SPECS.md`.

Use:

- migrations;
- foreign keys;
- uniqueness constraints;
- useful indexes;
- JSONB only where appropriate;
- idempotent writes.

Do not modify production schema manually without updating migrations.

Database writes must have deterministic conflict behavior.

A duplicate event must not create a second logical event.

---

## 14. ERROR HANDLING

External systems need bounded retries with:

- exponential backoff;
- jitter;
- timeouts;
- rate-limit handling;
- structured errors.

Handle, where applicable:

```text
429
401
403
5xx
FloodWaitError
model-load failures
CUDA OOM
invalid payloads
database connection failures
serialization conflicts
```

One malformed event must not crash an entire collector.

---

## 15. OBSERVABILITY

Use structured logging.

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

Track at least:

```text
events received
events normalized
events stored
NLP processed
NLP failures
graph updates
trend updates
API errors
```

Logs must help an engineer diagnose failure without reading application source line-by-line.

---

## 16. TESTING REQUIREMENTS

Tests are part of implementation, not cleanup work.

### Unit tests

Cover:

- Pydantic schemas;
- normalization;
- timestamps;
- repositories;
- graph edge extraction;
- NLP output parsing;
- demographic uncertainty;
- trend aggregation.

### Integration tests

At minimum verify:

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
temporal analytics
    ↓
API
```

### Model smoke tests

Every integrated model must have a deterministic smoke test proving:

- it loads;
- inference executes;
- expected labels are present;
- output matches the internal schema.

### External API tests

Use recorded fixtures or mocks for normal CI.

Do not require live credentials for basic test execution.

---

## 17. REPLAY / DEMO MODE

Replay mode is mandatory because platform access may be restricted, unavailable, expensive, or unreliable during a demo.

Replay data must be clearly marked.

Never represent replay data as live data.

The analytics pipeline must work on normalized replay events without requiring an external platform.

Store sample/replay fixtures under the project data directories, not in secrets or ad hoc temporary files.

---

## 18. SECURITY AND SECRETS

Never commit:

```text
.env
Telegram session files
API tokens
OAuth secrets
real credentials
private user data
production database dumps
unnecessary model binaries
```

`.env.example` must contain placeholders only.

Be conservative with raw social-media content and personal data.

---

## 19. PRIVACY AND DATA GOVERNANCE

Implement privacy by design.

The dashboard should prefer aggregate/cohort-level demographic views.

Support deletion/retention controls for stored data.

Separate replay/test data from real collected data.

Do not imply legal compliance merely because a system has a privacy section. Applicable platform terms and law must be reviewed separately.

---

## 20. PERFORMANCE RULES

Initial engineering targets from `SPECS.md` include:

```text
event normalization: <100 ms/event excluding network
Telegram ingestion: near-real-time
YouTube polling: configurable 10–60 seconds
graph refresh: <=5 minutes
trend refresh: <=15 minutes
common API queries: <1 second
```

These are targets to measure, not facts to assume.

Do not prematurely optimize.

Measure before making performance claims.

---

## 21. DOCUMENTATION RULES

Keep these documents current:

```text
docs/architecture.md
docs/dependencies.md
docs/api-access.md
docs/data-model.md
docs/nlp.md
docs/demographics.md
docs/graph.md
docs/trends.md
docs/demo.md
docs/limitations.md
```

When behavior changes, update the relevant document in the same work item whenever practical.

Do not leave known incompatibilities undocumented.

---

## 22. GIT RULES

Use small logical commits.

Prefer commit messages such as:

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

Do not combine unrelated refactors with feature work unless necessary.

Do not commit generated secrets, caches, local databases, or personal data.

---

## 23. CHANGE MANAGEMENT

When a requirement or architecture decision needs to change:

1. identify what is changing;
2. identify why;
3. verify the new behavior/source;
4. update code;
5. update tests;
6. update the relevant documentation;
7. record compatibility/limitations;
8. report the change clearly.

Never silently replace a component because it is inconvenient.

A temporary workaround must be labeled as temporary.

---

## 24. HANDLING BLOCKERS

When blocked:

```text
1. reproduce the blocker;
2. determine whether it is code, dependency, credentials, API access, or environment;
3. isolate the affected component;
4. continue unaffected work;
5. leave a documented reproduction and workaround if available.
```

Do not spend the whole implementation stuck behind one unavailable API when the rest of the architecture can be built and tested with fixtures.

Do not replace external access with fake success.

---

## 25. WORK SESSION PROTOCOL

At the beginning of each work session:

1. read `SPECS.md` sections relevant to the task;
2. read this file;
3. inspect the current repository state;
4. inspect existing tests before writing implementation;
5. identify the smallest next task;
6. implement it;
7. run focused tests;
8. run broader tests when appropriate;
9. update docs;
10. report exact results.

At the end of a meaningful work item, provide:

```text
IMPLEMENTED
-----------
What changed.

FILES
-----
Files created/modified.

TESTS
-----
Commands executed and actual results.

PS COVERAGE
-----------
Which requirement this advances.

KNOWN ISSUES
------------
Anything not verified or still blocked.

NEXT STEP
---------
One concrete next implementation step.
```

Never report a test as passing unless it was actually executed.

---

## 26. IMPLEMENTATION ORDER

The initial platform priority was changed on 2026-09-20. Follow:

```text
PHASE 0   Environment + smoke tests
PHASE 1   Canonical event schemas
PHASE 2   PostgreSQL + migrations
PHASE 3   X recent-search adapter
PHASE 4   X filtered-stream adapter
PHASE 5   X normalization + persistence
PHASE 6   NLP service
PHASE 7   Temporal analytics
PHASE 8   Graph analytics
PHASE 9   Replay engine
PHASE 10  FastAPI
PHASE 11  X/replay end-to-end testing
PHASE 12  BERTrend integration
PHASE 13  Future adapter preparation
PHASE 14  Telegram adapter
PHASE 15  YouTube adapter
PHASE 16  Meta adapter
PHASE 17  Reddit adapter
PHASE 18  Demographics
PHASE 19  React dashboard
PHASE 20  Demo hardening
```

Do not jump to the dashboard before the backend pipeline works.

Humans already have enough dashboards displaying broken databases with confidence.

---

## 27. DEFINITION OF DONE

A feature is DONE only when all applicable conditions are true:

1. implementation exists;
2. upstream/downstream integration works;
3. tests exist;
4. tests have been executed;
5. output is observable;
6. limitations are documented;
7. external dependencies are identified;
8. no secret or private data was introduced.

"Installed" is not the same as "implemented".

"Implemented" is not the same as "verified".

"Verified" is not the same as "production-ready".

Use those terms precisely.

---

## 28. FIRST-TASK GUARDRAIL

When the repository is being initialized, the first agent task is limited to:

```text
Read SPECS.md
Inspect repository
Create project structure
Create pyproject.toml
Create .gitignore
Create .env.example
Create migration skeleton
Create canonical Pydantic event model
Create smoke-test script
Run smoke tests
Fix local dependency/import problems
Report exact results
```

Do not begin by implementing all platforms.

Do not begin by building the dashboard.

Do not add speculative infrastructure.

After the bootstrap milestone passes, proceed to the X vertical slice. Do not begin Telegram or the dashboard first.

---

## 29. FINAL SYSTEM CHECK

Before calling the project demo-ready, verify that the repository can demonstrate:

```text
social event arrives
        ↓
normalized event
        ↓
chronological persistence
        ↓
sentiment analysis
        ↓
emotion analysis
        ↓
irony/sarcasm analysis
        ↓
stance where supported
        ↓
aggregate audience signals
        ↓
emerging topic/trend detection
        ↓
graph update
        ↓
centrality / PageRank / HITS / communities
        ↓
temporal propagation analysis
        ↓
FastAPI response
        ↓
React dashboard
```

Where live platform access is unavailable, use clearly labeled replay data.

The agent must never hide a limitation that changes what the evaluator is actually seeing.
