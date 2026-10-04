# PS Coverage Mapping

Requirement → implementation → API → UI → status → limitation.

Statuses: COMPLETE, PARTIAL, UNAVAILABLE, NOT IMPLEMENTED.

UI names below are the exact rail labels: Overview, Conversations, Sentiment,
Topics, Interaction map, Timeline, Demographics, Audience Lab, Sources, Jobs.

## A. Continuous Data Collection & Timeline

| PS requirement | Implementation | API | UI | Status | Limitation |
|---|---|---|---|---|---|
| X ingestion (essential) | `app/platforms/x` search + stream, normalization, dedup | `/api/health`, `/api/events` | Overview, Sources | COMPLETE | Live re-verification needs billing/credits |
| Telegram ingestion (essential) | `app/platforms/telegram` history + live listener | `/api/health`, `/api/events?platform=telegram` | Overview, Sources | COMPLETE | Public channels only; live arrival unverified in short window |
| Historical storage | PostgreSQL canonical events, idempotent writes | `/api/events`, `/api/events/{id}` | Conversations, Timeline | COMPLETE | — |
| Chronology | `created_at` source time + `collected_at`, UTC | All temporal endpoints | Timeline, Topics | COMPLETE | — |
| Relationships | Parent/thread references persisted | `/api/network/*` | Interaction map | COMPLETE | Some parents never collected |
| Continuous operation | In-process scheduler, 8 jobs (3 collection, NLP, trends, demographics, audience sync, graph), checkpoints | `/api/system/jobs` | Jobs | PARTIAL | Process-local, no soak test, one owner process |
| Instagram/Facebook | None | None | None (roadmap) | NOT IMPLEMENTED | Needs accounts/permissions |
| YouTube comments | Bounded Data API adapter, scheduler polling job, shared EventPipeline | `/api/events?platform=youtube` | Conversations, Sources | PARTIAL | Adapter verified against a public video; collection is credential-gated |
| Reddit | None | None | None (roadmap) | NOT IMPLEMENTED | Needs API setup |

## B. Multi-Dimensional Sentiment Inference

| PS requirement | Implementation | API | UI | Status | Limitation |
|---|---|---|---|---|---|
| Positive/neutral/negative | CardiffNLP social-text checkpoint | `/api/analytics/sentiment` | Sentiment | COMPLETE | No domain accuracy eval |
| Fine-grained emotion | GoEmotions multi-label | `/api/analytics/emotions` | Sentiment | COMPLETE | Short-post approximation |
| Anxiety | `nervousness` → anxiety terminology mapping | Same as emotion | Sentiment | COMPLETE | Mapping, not a native label |
| Excitement | GoEmotions signal | Same as emotion | Sentiment | COMPLETE | — |
| Sarcasm/irony | CardiffNLP irony checkpoint | Enriched events | Sentiment | COMPLETE | Irony is not universal sarcasm |
| Supportive/against stance | Fixed-target TweetNLP models | Enriched events | Sentiment | COMPLETE | Supported targets only |
| Arbitrary-topic stance | None | Explicit unsupported state | Unavailable notice | UNAVAILABLE | By design, never faked |
| Temporal fluctuation | Rolling 1h + daily aggregation | Same as above | Overview, Sentiment | COMPLETE | — |

## C. Automated Demographic Profiling

| PS requirement | Implementation | API | UI | Status | Limitation |
|---|---|---|---|---|---|
| Age brackets | None (spike rejected all candidates) | `UNAVAILABLE` aggregate | Unavailable notice | UNAVAILABLE | No validated evidence; deliberate |
| Geographic distribution | Location normalization → country buckets | `/api/analytics/demographics*` | Demographics | COMPLETE | 75% unknown on corpus |
| Language | Platform codes + text identification | Same | Demographics | COMPLETE | Short-post approximation |
| Professional interests | Sector classifier over controlled taxonomy | Same | Demographics | COMPLETE | Interest signals, not verified jobs |
| Privacy | Aggregate-only, confidence, unknown cohorts | No per-user endpoint | No profile cards | COMPLETE | — |

## D. Real-Time Trend & Topic Detection

| PS requirement | Implementation | API | UI | Status | Limitation |
|---|---|---|---|---|---|
| Topic discovery | BERTrend isolated service | `/api/analytics/topics` | Topics | COMPLETE | — |
| Ranking | Volume/growth/velocity ordering | `/api/analytics/trends` | Topics | COMPLETE | — |
| Rising trends | Velocity across matched windows | Same | Topics, topic detail | PARTIAL | One matched topic only |
| Velocity | Change per hour on matched measurements | Same | Topic detail | PARTIAL | Needs 2 measurements |
| Acceleration | Second-order change | Same | Topic detail | PARTIAL | Needs 3 measurements |
| Chronology/evolution | Windowed measurements, evolution endpoint | `/api/analytics/topics/{id}/evolution` | TopicEvolutionChart | COMPLETE | — |
| Weak/strong signals | BERTrend status semantics | Same | Topics | COMPLETE | Threshold unevaluated at scale |

"Real-time" is micro-batch (15-minute trend cadence), never claimed as true streaming.

## E. Link Analysis & Network Topology

| PS requirement | Implementation | API | UI | Status | Limitation |
|---|---|---|---|---|---|
| Graph construction | Event-derived edges, configured weights | `/api/network/graph` | Interaction map | COMPLETE | — |
| Degree/betweenness/closeness | NetworkX metrics | `/api/network/summary`, `/influence` | Interaction map | COMPLETE | Structural, not causal |
| PageRank, HITS | NetworkX, convergence-guarded | Same | Interaction map | COMPLETE | — |
| Communities | Louvain + correct unique-node membership, profile coverage, aggregate cohort evidence | `/api/network/communities` | Interaction map | PARTIAL | Snapshot-local identities; sparse stored profiles and minimum evidence per category |
| Temporal network | Fixed windows on source time + deltas | `/api/network/temporal` | Interaction map window selector | COMPLETE | — |
| Propagation/cascades | Parent-chain reconstruction | `/api/network/cascades*` | Cascade panel + path | COMPLETE | 17 observed; some partial |
| Sentiment on propagation | Persisted NLP attached per step | Cascade detail | Propagation path | COMPLETE | Empty where no NLP |
| Follower graph | None | None | Never claimed | NOT IMPLEMENTED | No verified edge source |
| Diffusion simulation | None | None | Never shown | NOT IMPLEMENTED | Optional per docs/specs.md |
