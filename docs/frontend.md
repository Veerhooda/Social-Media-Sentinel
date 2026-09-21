# React Dashboard

The dashboard follows `design.md` and is a real client of FastAPI.

## Stack

- React + TypeScript + Vite
- React Router
- TanStack Query
- Recharts
- Lucide icons
- Vitest + Testing Library

## Pages

- Overview
- Live Feed and event detail drawer
- Sentiment & Emotion
- Trends & Topics and topic evolution
- Network Analysis
- Timeline
- Data Sources
- Collection Status
- honest unavailable Settings state

## Data policy

No analytical value is hard-coded. Cards and charts use API data or show
unavailable/insufficient states. Real, replay, and mixed data are labeled. X and
Telegram use platform-filtered canonical events. YouTube and Reddit are shown as
`COMING SOON`; inactive Meta platforms show a planned state without fake counts,
latency, or timestamps. Topic status, velocity, growth, and acceleration are
displayed exactly as returned by FastAPI.

The polished shell uses restrained surfaces, larger analytical typography, a
single current-state strip, and direct operational copy. The platform filter is
server-backed so older Telegram events are not hidden by an X-heavy first page.

## Refresh policy

- live feed: 5 seconds;
- scheduler and health: 10 seconds;
- broader analytics: 30 seconds.

TanStack Query deduplicates requests shared by the top bar and pages.
