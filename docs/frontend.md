# React Dashboard

The dashboard follows `docs/design-system.md` (tokens, components, motion, writing rules) and is a real client of FastAPI.

## Stack

- React 19 + TypeScript + Vite
- React Router (lazy-loaded routes)
- TanStack Query
- Recharts, Sigma.js + Graphology (interaction map)
- Lucide icons
- Vitest + Testing Library (`src/test/fetch.ts` stubs the API by route)

## Pages

| Route | Page |
|---|---|
| `/` | Landing: live totals and 30-day volume |
| `/dashboard` | Overview: totals, sentiment volume, sources, latest conversations, topics, emotions, activity heatmap, central accounts |
| `/live-feed` | Conversations: server-side search and filters, event drawer, `?event=<id>` deep link |
| `/sentiment` | Sentiment share, emotions, anxiety/excitement/irony signals |
| `/trends`, `/trends/:id` | Topics (BERTrend) and topic evolution |
| `/network` | Interaction map, communities, centrality, snapshots, cascades |
| `/timeline` | Day-grouped chronology with lane filter |
| `/demographics` | Aggregate demographic estimates with coverage |
| `/audience-lab` | Audience segments and AI-agent post testing (see `docs/audience-lab.md`) |
| `/data-sources` | Sources per platform: add, enable/disable, remove, collect now |
| `/collection-status` | Jobs: status, timings, run now |

## Data policy

No analytical value or option list is hard-coded. Stats and charts use API data or show an explicit
empty/insufficient state. Real and replay data are kept separate. Topic status, velocity, growth and
acceleration are shown exactly as returned; a topic seen in one window is "First seen", not "rising".
A change (delta) is shown only when a previous comparable window exists.

## Refresh policy

- conversations: 5 seconds;
- scheduler, jobs, sources and health: 10 seconds;
- broader analytics: 30 seconds.

TanStack Query deduplicates requests shared by the top bar and pages. Running a job or editing a source
invalidates jobs, sources, health, events, analytics and network queries.
