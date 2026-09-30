# Social Sentinel — Product UI Design Specification

Status: approved design direction for the next frontend implementation pass. This document replaces the earlier white-and-orange dashboard direction. It is a design contract and implementation plan, not a claim that the current React app already matches it.

The public `/` route is a distinct editorial hero page inspired by Dialedweb's floating glass navigation, oversized centered type, grid-lined near-black canvas and staggered showcase. Its rose section is sticky and scroll-driven: the bloom enters, enlarges, and fades in as the section advances, then reverses when scrolling upward. Reduced-motion mode keeps a static visible bloom. The page uses original Social Sentinel copy and illustrative product previews; the rose photograph is separately licensed and attributed. The API-backed overview lives at `/dashboard`. The landing page must never imply that its illustrative charts are live measurements; its primary and final calls to action both enter the working dashboard.

## 1. Intent and source of truth

The user-supplied `Crypto Dashboard.png` is the visual reference. Follow its design language closely: an almost-black page, a quiet left rail, a generous charcoal workspace, black inset cards, a warm yellow focal color, rounded geometry, and high-contrast analytical charts. Translate the composition into Social Sentinel's purpose. Do not copy crypto metrics, labels, logos, avatars, wallet actions, or decorative fake data.

For technical capability and truthful claims, consult `SPECS.md` and `docs/limitations.md`. Existing API responses and tests determine what can be displayed today. A design mockup may show an intended future state, but the working app must label unavailable or insufficient evidence explicitly.

The implementation target is a fluent analyst workspace: one dominant analytical question per screen, a short path from signal to evidence, and no ornamental controls that do nothing.

## 2. Reference-to-product translation

| Reference element | Social Sentinel equivalent | Behavior |
|---|---|---|
| Black outer canvas and left rail | Persistent navigation shell | Left rail stays visually quiet; active route gets a charcoal capsule and yellow icon. |
| Large yellow “Dashboard” title | Current analytical page title | Use the route's real title, e.g. “Overview” or “Interaction map.” |
| Wide charcoal balance container | Overview intelligence stage | Holds one primary, API-backed corpus number and its context; no currency formatting. |
| Four compact coin cards with sparklines | Four analytical signal tiles | Use stored events, analyzed sentiment, persisted topics, and observed interactions. A sparkline appears only if a comparable series exists. |
| Yellow “My Portfolio” column | Source/coverage rail | X, Telegram, YouTube and replay/unknown coverage, with real stored counts and collector state kept separate. |
| Large black chart area | Primary chronological analysis | Source-time event volume or sentiment, with actual backend windows and keyboard-accessible time presets. |
| Search, mail, bell, avatar | Corpus search and actual system state | Search must query stored data. Do not add inbox, notifications, or profile controls without a working endpoint. |
| Colored gain/loss arrows | Measured change/status | Only for a valid prior comparison; otherwise show “Insufficient history.” Never infer growth from a single window. |

The reference's visual rhythm matters more than literal pixel copying: a restrained frame, one clear dominant surface, a compact upper band, and a deliberate split between a narrow evidence list and a wide chart.

## 3. Non-negotiable visual foundations

### Palette

Use the following tokens as the initial implementation targets. Check their contrast in context and adjust foreground shades if necessary without changing the dark/yellow character.

| Token | Value | Use |
|---|---|---|
| `canvas` | `#090A0B` | Body, sidebar, top-level gutters |
| `stage` | `#1D1F21` | Large rounded overview container and secondary stage surfaces |
| `surface` | `#101112` | Chart panels, signal tiles, drawers |
| `surface-raised` | `#252628` | Active navigation, hover, menus |
| `border` | `#343638` | Dividers and control outlines, never a white grid |
| `text` | `#F5F5F2` | Primary text and values |
| `text-secondary` | `#B4B6B7` | Descriptions and secondary labels |
| `text-muted` | `#909294` | Axis ticks and nonessential metadata; increase contrast for small text |
| `accent` | `#F6DE62` | Brand, active controls, primary series, focal list |
| `accent-ink` | `#151514` | Text/icons on yellow surfaces |
| `positive` | `#27CDB8` | Valid positive movement or healthy state |
| `negative` | `#FF7A35` | Valid negative movement or warning |
| `critical` | `#F36A72` | Failures |
| `series-blue` | `#4D83F5` | Secondary data series |
| `series-purple` | `#A884D8` | Tertiary data series |

Yellow is the focal brand accent, not the universal data color. Positive, neutral, negative, emotions, communities, and operational health must retain labeled semantic distinctions. Avoid neon gradients, glow, glassmorphism, and AI-themed decoration.

### Typography

Use a neutral geometric sans-serif with local/system fallback. Do not require Google Fonts for the interface to render. At the 1440px design target: page title 38–44px, stage total 48–60px, section titles 20–24px, tile metrics 24–32px, body 14–16px, labels and axes at least 12px when space allows. Use tabular numerals for counts, ratios, timestamps, and chart labels. Keep line lengths and label density controlled; the reference is spacious, not miniature.

### Geometry and space

- Desktop left rail: roughly 248–264px. The main top bar is 68–80px high.
- Main page content starts within a 32–40px gutter. Maximum content width is about 1600px.
- The principal charcoal stage has a large 32–40px radius; inset cards use 24–32px. Controls use 10–16px. These radii create the reference's soft block silhouette.
- Use a 16–20px analytical grid gap, 24–32px card padding, and broad 32–48px separation between major content bands.
- Dividers are thin and subdued. Flat dark surfaces and contrast do the work; avoid card shadows as the primary separator.
- Source-specific logos may retain recognizable forms, but sit inside a coherent icon treatment. Do not copy coin marks.

### Project icon

Retain the Social Sentinel pulse/node mark in `frontend/public/favicon.svg` as the starting brand asset. Rework its color treatment to yellow on near-black, preserving its recognizable form. Use the same SVG in the sidebar and favicon; do not use a generic crypto “C,” profile illustration, or robot/brain icon. Verify its legibility at 16, 32, and 40px.

## 4. Navigation and global shell

Desktop rail: icon and wordmark at top, routes in a clear vertical sequence, a subdued system-status link near the bottom. Actual routes: Overview, Conversation feed, Sentiment & emotion, Trends & topics, Interaction map, Demographics, Timeline, Data sources, Collection status. Do not display nonfunctional Account, Wallet, News, Settings, Log out, Inbox, or Alerts items from the reference.

Active route: raised charcoal capsule with yellow icon and white text. Inactive route: medium gray icon/text that brightens on hover. Focus-visible uses a high-contrast yellow outline, not hover alone.

Top bar: current page title in yellow, broad dark search field, and a compact right-aligned database/collector status. The global search routes to the corpus-backed conversation feed with the query preserved. It must not promise topic/user search beyond the supported fields. Do not show fabricated messages, notifications, or an invented user avatar.

Page title appears once. Avoid a redundant large in-page heading immediately below an identical top-bar title. On analytical pages, use a concise subtitle for scope and provenance, followed by the first data block.

## 5. Overview composition

Target: 1440×900 desktop with no horizontal scroll. The first viewport should answer what corpus exists, what changed, and where to investigate.

```text
black rail │ yellow route title       corpus search            system state
           │
           │ ╭──────────────────── CHARCOAL INTELLIGENCE STAGE ────────────────────╮
           │ │ corpus total + source-time scope     measured short-period changes │
           │ │                                                                       │
           │ │ four black analytical signal tiles                                  │
           │ │                                                                       │
           │ │ ╭ yellow source/coverage rail ╮ ╭ black chronological chart ─────╮ │
           │ │ │ X / Telegram / YouTube       │ │ measured series and time tabs  │ │
           │ │ │ real rows, replay, unknown   │ │ honest empty/insufficient data │ │
           │ │ ╰───────────────────────────────╯ ╰─────────────────────────────────╯ │
           │ ╰───────────────────────────────────────────────────────────────────────╯
           │
           │ topic evidence / recent conversations / network preview below
```

The hero total is **stored canonical events**, split into real and replay where present. Its nearby comparisons may be volume or positive-share change only when the API has comparable source-time windows. Do not render static “today / seven days / thirty days” percentage placeholders. If those intervals have no evidence, show a neutral “No comparison” label.

Four signal tiles, in order:

1. **Collection** — real stored event count, with a volume sparkline only when real time-series points exist.
2. **Sentiment** — proportions or valid positive-share shift, with a clear event sample and model coverage.
3. **Topics** — persisted BERTrend topic count; the latest topic's measured status only when valid.
4. **Interactions** — observed graph edges with a small relationship-type breakdown. Never label this a follower graph.

The yellow side rail is a visual focal point, but its content is an honest source/coverage index. Each row includes platform, real stored count, last source-time or collection time if present, and collector configuration/running status separately. Yellow backgrounds use dark text and dividers. Missing YouTube rows must not become “live” merely because an API key is configured.

The large black chart defaults to source-time event volume if a suitable endpoint/series is available; otherwise use the currently implemented sentiment time series. The chart heading names the actual measure. Add mutually exclusive 1H / 6H / 24H / 7D controls only where each selection genuinely changes the plotted data. Tooltip: UTC/local timestamp, sample/event count, plotted values and status. Axis labels must be legible against black. For zero or one point, do not draw a fictitious trend line.

Below the stage, use a calmer three-part evidence layer: latest persisted topic measurements, recently collected event excerpts, and a small network preview with a clear “Open map” action. This layer can scroll; the overview's first screen must not become a wall of equal-weight cards.

## 6. Secondary screens

### Conversation feed and event details

Use the same dark shell. Desktop: a black inset result list with legible columns. Mobile: stacked event cards, never a horizontally scrolled 800px table. Keep a visible total, active filters, clear-filter action, page position, and explicit search loading state. Search, platform, sentiment, emotion, and interaction filters must operate in PostgreSQL before pagination; debounce text input without clearing focus on background refetch. The event drawer uses a dark surface, 16px body text, visible model labels/confidence, Escape-to-close, focus return, and a source link only when a valid source ID exists. Do not show a topic filter until per-event topic assignments exist.

### Sentiment and emotion

One dominant timeline with labeled positive, neutral, and negative series. A yellow accent may frame the module, but it must not recolor negative sentiment yellow. Place fine-grained emotion bars and selected-source-time signal summaries below. Label `nervousness → anxiety` as a product terminology mapping, not a native model label. General arbitrary-target stance stays unavailable unless validated.

### Trends and topic detail

Lead with persisted topics and chronological measurements. Use a readable ranked list plus one large black evolution chart for the selected topic. Volume, growth, velocity, and acceleration show units, source-time window, and insufficient-history states. A first observation is never styled as a rising trend. Retain the fallback frequency mode only when visibly labeled as such.

### Interaction map

Keep the Sigma.js/Graphology implementation and API-derived edges. Give the map a larger dark viewport with yellow selection focus, restrained community colors, pan/zoom/reset, and a readable ranking/relationship panel. The default connected-core view may reduce visual clutter, but its node/edge count must clearly state it is a subset of the loaded graph. Keyboard selection from the ranking is mandatory. Do not imply follower-network or causal influence.

### Demographics

Aggregate-only distributions on dark surfaces. The yellow accent may highlight the selected dimension, never an individual inferred identity. Keep unknown/insufficient buckets, sample size, coverage and confidence when available. Age/geography/profession estimates are not facts.

### Timeline, data sources, collection status

Timeline: source-time chronology with compact labeled lanes, not decorative animations. Data sources: platform rows with honest stored counts and configuration state. Collection status: job status, last run, duration and failures from backend data. These pages should use the shared dark/yellow primitives rather than unique visual themes.

## 7. Interaction behavior

- Every visible control has a working action. Hide unavailable controls rather than decorating a dead button.
- Search and filters show an explicit updating state. Background polling must not blank the page, interrupt typing, reset scroll or discard the user's selection.
- Drill-down is predictable: overview signal → evidence list or analytical screen → source event/topic/node. Preserve URL query parameters where practical.
- Tooltips never contain information that is unavailable to keyboard users. Pair charts with a legend and concise textual summary or accessible data view.
- Motion is purposeful and brief: 150–220ms for hover, focus, menu, or chart-state transitions. Obey `prefers-reduced-motion`. Do not pulse indicators unless a collector is actually running.
- Status language distinguishes configured, running, stored real data, replay, skipped, unavailable, insufficient data, and failed. A yellow arrow is not proof of an emerging trend.

## 8. Responsive and accessible contract

At 1440px and wider, show the full rail, hero stage, four signal tiles, yellow coverage rail, and wide chart. At 1024–1439px, tighten gutters and use two signal-tile columns if the text would otherwise wrap badly. At 768–1023px, stack the yellow rail above or beside the chart as space permits. Below 768px, use an accessible navigation drawer, two-column or single-column tiles, full-width chart, and stacked event cards. At 390px there must be no page-level horizontal overflow or clipped primary actions.

Target WCAG 2.2 AA where possible: text contrast at least 4.5:1 for normal text, meaningful non-text contrast at least 3:1, visible focus, keyboard operation, labels on all inputs, and touch targets at least 24×24 CSS pixels with comfortable spacing. Prefer 40–44px control height. Run checks with real content, long author IDs, unavailable states, empty data and mobile viewport—not just a polished static mock.

The chart, graph, and any color-coded status must have a text alternative. SVG/bitmap icons are decorative unless they communicate a unique action; icon-only buttons have accessible names. Do not load untrusted remote imagery for a fabricated profile.

## 9. Implementation sequence and acceptance gates

This request updates the plan/design; code implementation follows these gated steps. Preserve the current working data contracts and uncommitted work.

1. **Inventory and baseline** — capture current 1440px, 1024px, 768px and 390px screens; record route, network, console and overflow issues. Audit the existing component/API contracts and data availability.
2. **Tokens and shell** — implement the dark/yellow palette, typography, spacing, brand icon variant, sidebar, top search, focus/hover states and mobile navigation. Gate: all routes remain reachable and search still works.
3. **Overview stage** — build the hero, four real signal tiles, yellow coverage rail, and large black chart using existing typed API data. Gate: no placeholder metric or unsupported comparison; all time presets change actual data or show insufficiency.
4. **Evidence layer** — topic list, recent events and network preview as reusable modules. Gate: click-through reaches the right detail page and source/replay provenance is visible.
5. **Secondary screen migration** — feed/drawer; sentiment; trends/topic detail; interaction map; demographics; timeline; sources/status. Gate each route with unit/component checks and one real-browser interaction.
6. **Responsive and accessibility audit** — desktop/mobile screenshots, keyboard traversal, focus traps/return, no horizontal overflow, contrast checks, reduced-motion behavior, tooltip equivalents.
7. **Regression and release check** — `npm run build`, frontend tests, lint, backend tests where API contracts changed, Ruff, Alembic check and browser console/network inspection. Document any blocked or unverified functionality precisely.

Do not rewrite X/Telegram/YouTube ingestion or analytics solely to fit this design. Add a backend endpoint only when a visualized analytical need cannot be met truthfully with existing contracts; test and document that contract.

## 10. Repository migration map

The current React app uses a light teal/white theme. This document deliberately supersedes that visual direction; do not preserve its colors merely because they are already in `tokens.css`. Keep its working routes, typed API client, tests and verified interactions.

| Area | Existing implementation | Intended change |
|---|---|---|
| Foundations | `frontend/src/styles/tokens.css`, `global.css` | Replace light tokens and old overrides with one coherent dark token layer; remove obsolete CSS after each route is migrated. |
| Brand | `frontend/public/favicon.svg`, `frontend/index.html`, `Sidebar.tsx` | Yellow/black pulse mark, matching theme color, same mark in rail and browser tab. |
| Shell | `AppShell.tsx`, `Sidebar.tsx`, `TopBar.tsx` | Black rail, yellow page title, dark search, honest system status and responsive drawer. |
| Overview | `OverviewPage.tsx`, `MetricCard.tsx`, `Panel.tsx`, chart components | Reference-like stage, four tiles, yellow coverage column, black chronological chart and deliberate evidence modules. |
| Feed | `LiveFeedPage.tsx`, `useApiQueries.ts`, typed event API | Dark desktop result list and mobile cards; retain PostgreSQL-backed filters, count, pagination and accessible drawer. |
| Network | `NetworkPage.tsx`, `NetworkGraph.tsx`, `utils/network.ts` | Dark map viewport, subdued communities, yellow selection, visible sample scope and keyboard-accessible ranking. |
| Other analysis | Sentiment, Trends, Topic Detail, Demographics, Timeline pages | Reuse shared surfaces, controls, chart colors, status/empty/loading patterns; no page-specific parallel design system. |
| Operations | Data Sources, Collection Status pages | Dark/yellow visual system with semantic PASS/FAIL/SKIPPED/UNAVAILABLE distinctions. |

### Acceptance matrix

| Gate | Evidence required |
|---|---|
| Reference fidelity | Side-by-side desktop screenshots show the same major hierarchy, dark surfaces, yellow focus and rounded block rhythm, with social-analytics content instead of crypto content. |
| Product correctness | Every number and time comparison traces to a documented API field or calculation; unavailable metrics are omitted or labeled. |
| Navigation | Every visible route and top-bar action works with mouse and keyboard; no dead reference-image ornaments. |
| Search/feed | Search finds events beyond the first page; count and pagination remain accurate under combined filters. |
| Charts/network | Time controls change actual source-time data; graph edges come from stored relationships; exact values have text access. |
| Responsive | No page-level horizontal overflow at 390, 768, 1024 or 1440px; primary controls and data remain legible. |
| Quality | Build, lint, relevant frontend/backend tests, browser console, reduced-motion and focus checks pass. Document any remaining exception. |

## 11. Definition of done

This redesign is done only when the running app—not just a mockup—uses the reference's dark/yellow design family consistently across the active routes, works at the target breakpoints, has a legible and functional overview, preserves real-data provenance, passes automated checks, and survives keyboard/mobile browser verification. Any screen not migrated must be labeled as pending in the implementation report. “Looks similar” without working filters, credible numbers, and accessible navigation is not done.
