# Social Sentinel — UI Design System

Status: **implemented** (October 2026 overhaul). This file describes the interface as it ships and the rules
any new screen must follow. It replaces the earlier "crypto dashboard reference" direction (rounded charcoal
stage, blue/purple series, editorial landing page with a scroll-driven rose image), which was removed.

## 1. Principles

1. **Every number comes from the API.** No placeholder metrics, sample charts, or hard-coded option lists.
   Filter values come from the data (platforms from `/api/health`, emotions from the model output, interaction
   types from the backend schema). If something is missing, say so in plain words ("No credentials",
   "Not enough evidence yet", "First seen").
2. **No AI decoration.** No "AI-powered" copy, sparkle icons, glowing gradients, glassmorphism, pill/capsule
   badges or gradient text. Model names appear only where they are provenance (event drawer, Sentiment footer).
3. **One question per screen.** Each page title answers what it measures; the first block is the answer.
4. **Calm surfaces, data in colour.** Chrome is graphite and neutral. Colour is spent on data and status.
5. **Controls work or are hidden.** No dead buttons, no `window.confirm`, no "coming soon".

Inspiration (studied, not copied): Vercel and Linear dashboards (density, quiet chrome, dot status),
Grafana and Plausible (honest charts, range toggles, compact stat rows), the AdminLTE dashboard roundup
(adminlte.io/blog/dashboard-examples) and impeccable.style's list of AI-slop UI tells (purple/blue gradients,
capsule badges everywhere, oversized hero copy, emoji/sparkle decoration) which this system avoids on purpose.

## 2. Tokens (`frontend/src/styles/tokens.css`)

No blue or violet hue appears anywhere in the palette.

| Token | Value | Use |
|---|---|---|
| `--bg` / `--bg-rail` | `#0c0d0f` / `#0f1013` | Page and navigation rail |
| `--surface` / `-2` / `-3` | `#15171a` / `#1b1d21` / `#23262b` | Panels; hover/inputs; active row |
| `--line` / `--line-strong` | `#24272c` / `#31353b` | Dividers, control borders |
| `--text` / `-2` / `-3` | `#ecedee` / `#a9aeb5` / `#7c838c` | Primary, secondary, tertiary text |
| `--accent` | `#e9c46a` (gold) | Brand mark, active nav, primary button, focus ring, primary series |
| `--pos` `--neu` `--neg` `--sar` | `#3fb98a` `#8a9199` `#e5594f` `#ef8a3b` | Positive, neutral, negative, sarcastic/irony |
| `--ok` `--warn` `--err` | green / amber `#e2a33a` / red | Operational status |
| `--c1`…`--c8` | gold, green, orange, sand, teal `#5fb3a7`, rose, olive, grey | Categorical series (communities, emotions, platforms) |

Charts read the same values from `src/charts/theme.ts` (`COLORS`, `CATEGORICAL`, `SENTIMENT_COLORS`); never
inline hex in components.

**Type:** system UI stack (`-apple-system`, Segoe UI, Roboto…) at 14px base; tabular numerals for all figures;
`ui-monospace` for IDs. Page title 22px/600, panel title 14px/600, stat value 26px/600. No web fonts.

**Geometry:** radii 4 / 6 / 8px (controls / inputs / panels). Rail 224px, top bar 56px, 24px gutter.
Panels are flat with a 1px border; no shadows except the drawer.

**Logo — "Lookout":** an eye whose outline ends in a speech-bubble tail ("watching the conversation"), solid gold
on graphite, no gradients. `public/logo.svg` is the bare mark (sidebar, landing), `public/favicon.svg` the mark on a
dark tile (browser tab), `public/apple-touch-icon.png` the 180px tile. Minimum size 16px; keep clear space of at
least a quarter of the mark's width; never recolour it outside gold-on-dark or dark-on-gold.

## 3. Components (`frontend/src/components`)

| Component | Contract |
|---|---|
| `Panel` | Title, optional description, actions, footer; `flush` for tables. |
| `PageHeader` | Title, one-line description, right-aligned actions. |
| `Stats` / `Stat` / `Delta` | Row of figures with label, animated value, meta line, optional delta (`+2.1 pp`) that is shown only when a previous comparable window exists. `null` renders "–". |
| `Status` | Coloured dot + text ("Collecting", "Skipped", "Failed"). Replaces all capsule badges. Pulses only when the tone is a running state. |
| `Segmented` | Mutually exclusive options (time range, count/share). Every option must change the data. |
| `LoadingState` / `EmptyState` / `ErrorState` / `Notice` | Skeleton, empty explanation, API error with message, inline warning/error. |
| `Bars` / `StackBar` | Labelled horizontal distributions; values below 1% print "<1%". |
| `Platform` | Lucide icon + name for X, Telegram, YouTube. |
| Charts | `VolumeChart` (stacked sentiment, count or share), `SignalChart`, `TopicEvolutionChart`, `ActivityHeatmap`, shared `ChartTooltip`. |

Tables are always wrapped in `.table-wrap` (horizontal scroll inside the panel, never the page).

## 4. Information architecture

Rail groups (labels are the page titles):

- **Analyze** — Overview `/dashboard`, Conversations `/live-feed`, Sentiment `/sentiment`, Topics `/trends`,
  Interaction map `/network`, Timeline `/timeline`
- **Audience** — Demographics `/demographics`, Audience Lab `/audience-lab`
- **Collection** — Sources `/data-sources`, Jobs `/collection-status`

Top bar: corpus search (⌘K focuses it; Enter opens Conversations with the query) and one status line computed
from `/api/health` + `/api/system/jobs`: "Collecting · last event 3m ago", "Collection paused", "API offline" or
"N jobs failing". `/` is a short landing page with live totals and a real 30-day chart.

Drill-down: Overview conversation row → `/live-feed?event=<id>` (drawer opens via
`GET /api/events/{id}/enriched`, works for any event age); topic → `/trends/:id`; account → Interaction map.

## 5. Motion

- Page content fades/rises in with a short stagger (`--t`, 220ms, `--ease`).
- Numbers tween with `AnimatedNumber` (rAF); bars grow from zero; charts use Recharts' entry animation.
- New rows in Conversations flash once; the drawer slides in from the right.
- Loading uses a shimmer skeleton, never a spinner over a blank page. Background polling never blanks content.
- `prefers-reduced-motion` sets all durations to 0.

## 6. Writing

Short, specific and factual. Say what the number is and where it came from ("446 stored · 4 replay kept separate").
No marketing tone, exclamation marks, emoji or "Powered by AI". Explain gaps with the real reason
("X_BEARER_TOKEN is not set in .env", "no validated age model is configured").

## 7. Responsive and accessibility

- ≥1280px full layout; ≤1024px two-column stats; <768px rail becomes a drawer, panels stack.
- No page-level horizontal overflow at 375px (checked per route); wide tables scroll inside their panel.
- Visible gold focus ring, labels on every input, icon buttons have `aria-label`, drawer traps focus,
  closes on Escape and restores focus. Switches use `role="switch"` + `aria-checked`.

## 8. Verification

`verify_prototype.command` (repo root) runs migrations, Ruff, pytest, ESLint, Vitest, `tsc -b && vite build`
and `scripts/verify_live.py` (every dashboard endpoint, stored counts, freshness per platform, job status)
and writes `verify_prototype.log`. Page tests stub the API through `src/test/fetch.ts` so they assert
behaviour against API shapes, not fixed copy.
