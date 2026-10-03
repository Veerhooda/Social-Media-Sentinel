# PS Coverage Mapping

Requirement → implementation → API → UI → status → limitation.

Statuses: COMPLETE, PARTIAL, UNAVAILABLE, NOT IMPLEMENTED.

## A. Continuous Data Collection & Timeline

| PS requirement | Implementation | API | UI | Status | Limitation |
|---|---|---|---|---|---|
| X ingestion (essential) | `app/platforms/x` search + stream, normalization, dedup | `/api/health`, `/api/events` | Overview, Data Sources | COMPLETE | Live re-verification needs billing/credits |
| Telegram ingestion (essential) | `app/platforms/telegram` history + live listener | `/api/health`, `/api/events?platform=telegram` | Overview, Data Sources | COMPLETE | Public channels only; live arrival unverified in short window |
| Historical storage | PostgreSQL canonical events, idempotent writes | `/api/events`, `/api/events/{id}` | Live Feed, Timeline | COMPLETE | — |
| Chronology | `created_at` source time + `collected_at`, UTC | All temporal endpoints | Timeline, Trends | COMPLETE | — |
| Relationships | Parent/thread references persisted | `/api/network/*` | Network Analysis | COMPLETE | Some parents never collected |
| Continuous operation | In-process scheduler, 4 jobs, checkpoints | `/api/system/jobs` | Collection Status | PARTIAL | Process-local, no soak test, one owner process |
| Instagram/Facebook | None | None | PLANNED badge | NOT IMPLEMENTED | Needs accounts/permissions |
| YouTube comments | Bounded Data API adapter, local fixture integration | `/api/events?platform=youtube` | Live Feed, Data Sources | PARTIAL | Live API unverified; polling must be invoked explicitly |
| Reddit | None | None | COMING SOON badge | NOT IMPLEMENTED | Needs API setup |

## B. Multi-Dimensional Sentiment Inference

| PS requirement | Implementation | API | UI | Status | Limitation |
|---|---|---|---|---|---|
| Positive/neutral/negative | CardiffNLP social-text checkpoint | `/api/analytics/sentiment` | Sentiment & Emotion | COMPLETE | No domain accuracy eval |
| Fine-grained emotion | GoEmotions multi-label | `/api/analytics/emotions` | Sentiment & Emotion | COMPLETE | Short-post approximation |
| Anxiety | `nervousness` → anxiety terminology mapping | Same as emotion | Sentiment & Emotion | COMPLETE | Mapping, not a native label |
| Excitement | GoEmotions signal | Same as emotion | Sentiment & Emotion | COMPLETE | — |
| Sarcasm/irony | CardiffNLP irony checkpoint | Enriched events | Sentiment & Emotion | COMPLETE | Irony is not universal sarcasm |
| Supportive/against stance | Fixed-target TweetNLP models | Enriched events | Sentiment & Emotion | COMPLETE | Supported targets only |
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
| Topic discovery | BERTrend isolated service | `/api/analytics/topics` | Trends & Topics | COMPLETE | — |
| Ranking | Volume/growth/velocity ordering | `/api/analytics/trends` | Trends & Topics | COMPLETE | — |
| Rising trends | Velocity across matched windows | Same | Trends, Topic detail | PARTIAL | One matched topic only |
| Velocity | Change per hour on matched measurements | Same | Topic detail | PARTIAL | Needs 2 measurements |
| Acceleration | Second-order change | Same | Topic detail | PARTIAL | Needs 3 measurements |
| Chronology/evolution | Windowed measurements, evolution endpoint | `/api/analytics/topics/{id}/evolution` | TopicEvolutionChart | COMPLETE | — |
| Weak/strong signals | BERTrend status semantics | Same | Trends & Topics | COMPLETE | Threshold unevaluated at scale |

"Real-time" is micro-batch (15-minute trend cadence), never claimed as true streaming.

## E. Link Analysis & Network Topology

| PS requirement | Implementation | API | UI | Status | Limitation |
|---|---|---|---|---|---|
| Graph construction | Event-derived edges, configured weights | `/api/network/graph` | Network Analysis | COMPLETE | — |
| Degree/betweenness/closeness | NetworkX metrics | `/api/network/summary`, `/influence` | Network Analysis | COMPLETE | Structural, not causal |
| PageRank, HITS | NetworkX, convergence-guarded | Same | Network Analysis | COMPLETE | — |
| Communities | Louvain + correct unique-node membership, profile coverage, aggregate cohort evidence | `/api/network/communities` | Network Analysis | PARTIAL | Snapshot-local identities; sparse stored profiles and minimum evidence per category |
| Temporal network | Fixed windows on source time + deltas | `/api/network/temporal` | Network window selector | COMPLETE | — |
| Propagation/cascades | Parent-chain reconstruction | `/api/network/cascades*` | Cascade panel + path | COMPLETE | 17 observed; some partial |
| Sentiment on propagation | Persisted NLP attached per step | Cascade detail | Propagation path | COMPLETE | Empty where no NLP |
| Follower graph | None | None | Never claimed | NOT IMPLEMENTED | No verified edge source |
| Diffusion simulation | None | None | Never shown | NOT IMPLEMENTED | Optional per SPECS |
