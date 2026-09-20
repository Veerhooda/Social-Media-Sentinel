# Social Sentinel — UI/UX Design Specification

## 1. Document Purpose

This document defines the complete visual, interaction, information-architecture, and screen-level design for **Social Sentinel**, the AI-driven Social Media Analytics and Intelligence platform.

It is the design source of truth for Stitch, Figma, frontend engineers, and coding agents.

The design must preserve the visual character established by the current prototype while replacing all social-media-management concepts with analytics and intelligence workflows.

---

## 2. Product Definition

### Product
**Social Sentinel**

### Product type
Real-time social-media intelligence and analytics platform.

### Core job
Continuously collect public social activity, normalize it, analyze it with NLP and demographic inference, detect emerging topics, model interactions and influence networks, and present the resulting intelligence chronologically.

### Platforms
Core:
- X / Twitter
- Telegram

Supported / desirable:
- YouTube
- Instagram
- Facebook

Optional:
- Reddit

### Core analytical capabilities
- Continuous event collection
- Historical timeline management
- Sentiment analysis
- Nuanced emotion inference
- Sarcasm / irony detection
- Stance analysis
- Aggregate demographic profiling
- Trend and topic detection
- Topic evolution
- Network topology
- Influence analysis
- Community detection
- Temporal propagation / cascade analysis
- Data-source health monitoring

---

## 3. Design North Star

The product should communicate one coherent idea:

> **Something is happening across public social platforms, and Social Sentinel helps an analyst understand what is happening, when it changed, how people reacted, what topics are emerging, who is influential, and how information spreads.**

The interface should feel like a professional intelligence/observability product rather than a social-media management tool.

### The five-second test
A user should immediately understand:
1. Data is arriving now.
2. The system is analyzing it.
3. Sentiment, emotions, trends, demographics, and networks are available.
4. The user can drill from a high-level signal into underlying events.

---

## 4. Reference-Image Strategy

The provided reference dashboard is a **visual reference only**.

Preserve its:
- Desktop SaaS structure
- Left navigation
- Thin divider lines
- White cards
- Pale gray canvas
- Orange primary accent
- Compact top utility bar
- Rounded cards
- Subtle shadows
- Dense analytics composition
- Clean typography
- Chart-heavy layout

Do **not** copy its product semantics.

Do not include:
- Follower-growth management
- Publishing schedules
- Content publishing
- Social inbox workflows
- Boosted posts
- Caption-generation tools
- Creator-management workflows
- Follower vanity metrics as the central product model

The current Stitch prototype already uses a 260px-class sidebar, a 64px top bar, white cards, a pale-gray page canvas, Plus Jakarta Sans, and subtle borders/shadows. These are intentional visual anchors to retain. The current design system also specifies 12–16px card radii and a 20px grid gutter. [Source prototype: current generated implementation]

---

## 5. Target Screen

### Primary design target
**1440 × 900 desktop**

### Layout behavior
- Desktop-first.
- Minimum useful desktop width: 1180px.
- At 1440px, use the full analytics composition.
- At narrower widths, collapse low-priority modules before making charts unusably small.
- Mobile is not the primary presentation target for the hackathon demo.

### Global shell
```text
┌────────────────────────────────────────────────────────────────────┐
│ Sidebar │ Top Utility Bar                                          │
│         ├───────────────────────────────────────────────────────────┤
│         │ Main Analytics Workspace                                 │
│         │                                                           │
│         │ cards / charts / intelligence modules                    │
│         │                                                           │
└────────────────────────────────────────────────────────────────────┘
```

---

## 6. Information Architecture

### Sidebar

#### MAIN
- Overview
- Live Feed
- Sentiment & Emotion
- Trends & Topics
- Demographics
- Network Analysis
- Timeline

#### DATA
- Data Sources
- Collection Status

#### SYSTEM
- Settings
- Documentation

The active item uses the orange accent with a subtle warm background and/or a narrow orange edge indicator.

### Do not include
- Publishing Schedules
- Inbox
- My Publishing
- Boosted Posts
- Caption Jam
- Subscriptions as a primary navigation concept

---

## 7. Visual Design System

### 7.1 Color philosophy

The product uses a neutral canvas, white analytical surfaces, warm orange as the primary brand accent, and restrained semantic colors.

### Core colors

| Token | Value | Usage |
|---|---|---|
| Canvas | `#F5F6F8` | Global background |
| Surface | `#FFFFFF` | Cards, panels, top bar, sidebar |
| Subtle Surface | `#F1F3F6` | Inputs, inactive chart regions, muted chips |
| Border | `#EAECEF` | Card and structural borders |
| Text Primary | `#111827` | Titles, metrics, strong labels |
| Text Secondary | `#64748B` | Supporting text |
| Text Muted | `#94A3B8` | Axes, timestamps, inactive labels |
| Brand Orange | `#FF7A00` | Primary accent, active state, important signals |
| Brand Orange Hover | `#E66E00` | Interactive hover |
| Orange Soft | `#FFF7ED` | Active/background accent |
| Blue | `#2563EB` | Secondary data series, growth |
| Pink/Red | `#E11D48` | Negative/Instagram-like series |
| Pink | `#EC4899` | Secondary emotion/data series |
| Emerald | `#10B981` | Positive/success/live status |
| Error | `#BA1A1A` | Errors and critical failures |

### Semantic analytics colors

Use consistent semantic mapping throughout the application:

- Positive / supportive → emerald
- Negative / against → red/pink
- Neutral → gray/slate
- Excitement → orange
- Anxiety / nervousness → amber/orange-red
- Anger → red
- Joy → yellow/orange
- Fear → purple
- Sadness → blue
- Sarcasm / irony → pink/magenta
- Live/healthy → emerald
- Warning/degraded → orange
- Error/offline → red

Do not use color alone as the only way to communicate meaning. Pair color with labels, icons, or values.

---

## 8. Typography

### Font
**Plus Jakarta Sans**

### Primary hierarchy

| Role | Size | Weight | Line height |
|---|---:|---:|---:|
| Page title | 22–28px | 600–700 | 30–36px |
| Section title | 16–18px | 600–700 | 24–26px |
| Metric | 24–28px | 700 | 32–36px |
| Body | 13–15px | 400–500 | 20–22px |
| Label | 11–12px | 500–600 | 14–16px |
| Micro | 10–11px | 500 | 14px |

Keep headings dark and supporting text muted.

Avoid giant hero typography. This is an analytical workspace, not a marketing landing page.

---

## 9. Spacing and Geometry

### Grid
- 12-column grid.
- 20px standard gutter.
- Main workspace horizontal padding: 24–32px depending on viewport.
- Card internal padding: 20–24px.

### Radii
- Major cards: 14–16px.
- Small controls: 8–12px.
- Pills/badges: fully rounded.
- Heatmap cells: 4–6px.
- Avatars: 50%.

### Borders
Use 1px low-contrast borders rather than heavy outlines.

### Shadows
Default cards should use nearly invisible elevation:

```css
box-shadow:
  0 1px 3px rgba(15, 23, 42, 0.03),
  0 1px 2px rgba(15, 23, 42, 0.02);
```

Hover:

```css
box-shadow:
  0 4px 12px rgba(15, 23, 42, 0.05),
  0 1px 3px rgba(15, 23, 42, 0.03);
```

Do not make every card visibly float.

---

## 10. Iconography

Use a consistent outline icon system.

Preferred characteristics:
- 16–20px icons
- 1.5–2px stroke
- muted gray by default
- orange when active
- semantic status icons when required

Avoid mixing many unrelated icon styles.

Platform icons may retain recognizable platform identity where useful.

---

## 11. Global Top Bar

Height: approximately 64–68px.

### Left side
- Optional context/navigation icon
- Global search

### Search
Placeholder:
**Search posts, topics, users...**

Search targets:
- posts
- users/channels
- topics
- platforms
- event IDs

### Right side
- Live ingestion status
- Notification/alerts
- Theme control if implemented
- Current user/profile

### Live indicator
Example:
```text
● STREAM LIVE   14,840 evt/s
```

The number is placeholder data only. Production implementation must use actual backend metrics.

Use a small pulsing dot only if the application is truly live. Do not simulate live behavior when using replay data without labeling it as replay/demo mode.

---

# 12. Overview Dashboard

## Purpose
Answer the question:

> **What is happening across the monitored social ecosystem right now?**

The Overview page is the primary hackathon-demo screen.

---

## 12.1 Header

Title:
**Overview**

Subtitle:
**Real-time intelligence from conversations, sentiment, trends and social networks.**

Right controls:
- Time range: 1H / 6H / 24H / 7D / Custom
- Refresh
- Optional platform filter

---

## 12.2 KPI Row

Five compact cards.

### Card 1
**Live Events**

Example:
`12,842`
`+18.4%`

### Card 2
**Active Users**

Example:
`4,721`
`+7.8%`

### Card 3
**Trending Topics**

Example:
`38`
`+12 new`

### Card 4
**Sentiment Shift**

Example:
`+8.2%`
`vs previous window`

### Card 5
**Network Activity**

Example:
`8.4K`
`interactions`

These are analytical metrics. Do not use followers/posts as the primary KPI model.

---

## 12.3 Sentiment Over Time

### Layout
8-column card in the first analytical row.

### Title
**Sentiment Over Time**

### Subtitle
**How public conversation sentiment has changed across the selected period.**

### Chart
Multi-series line chart:
- Positive
- Neutral
- Negative

### Controls
- 1H
- 6H
- 24H
- 7D

### Interactions
Hover should display:
- timestamp
- event count
- positive %
- neutral %
- negative %

Optional event markers can highlight major topic spikes.

---

## 12.4 Emotion Distribution

### Layout
4-column card beside Sentiment Over Time.

### Title
**Emotion Distribution**

### Suggested visualization
Horizontal bars are preferred over a crowded donut because there are many emotion classes.

### Categories
- Excitement
- Supportive
- Anxiety
- Anger
- Joy
- Fear
- Sadness
- Sarcasm / Irony

### Interaction
Clicking an emotion filters or drills into relevant events/posts.

---

## 12.5 Conversation Activity Heatmap

### Title
**Conversation Activity**

### Purpose
Show when conversation volume and/or analytical activity spikes.

### Layout
8-column card.

### Visualization
Day × hour heatmap.

Horizontal:
- 12–3am
- 3–6am
- 6–9am
- 9am–12pm
- 12–3pm
- 3–6pm
- 6–9pm
- 9pm–12am

Vertical:
- Mon–Sun

### Color scale
Low → moderate → high → peak using restrained orange intensity.

### Tooltip
- day/time
- events
- unique users
- dominant sentiment
- dominant topic

This replaces the reference application's publishing engagement heatmap.

---

## 12.6 Live Activity

### Title
**Live Activity**

### Purpose
Show meaningful system-detected events, not social-media-manager notifications.

### Example events
- Topic spike detected
- Sentiment shifted negative
- Emotion spike detected
- New community detected
- High-influence node became active
- Cross-platform activity increased
- Sarcasm anomaly detected

### Activity row
Each row includes:
- timestamp
- platform/source
- event icon
- concise event description
- severity/state badge

Example:
```text
13:42:18   X
Topic spike detected
"Autonomous AI Agents"
+184% volume
```

---

## 12.7 Rising Topics & Trend Velocity

### Title
**Rising Topics & Trend Velocity**

### Subtitle
**Emerging themes and their rate of change.**

### Table columns
- Topic / Entity
- Growth
- Volume
- Sentiment
- Status

### Example
```text
Autonomous AI Agents     ↑248%   42.8K   +68% Pos   Explosive
Quantum Cryptography     ↑142%   28.1K   +44% Pos   High
Energy Grid Resilience    ↑96%   19.4K   -22% Neg   Moderate
Open Weights LLM 2.0      ↑74%   31.6K   +82% Pos   Sustained
```

Placeholder data only.

### Status vocabulary
- Emerging
- Rising
- High
- Explosive
- Sustained
- Cooling

Avoid subjective labels that imply political judgments. Status must describe measurable trend behavior.

### Interactions
- Click topic → Topic detail.
- Hover growth → show baseline and current window.
- Click sentiment → filter topic events.

---

## 12.8 Influence Network Snapshot

### Title
**Influence Network**

### Subtitle
**Multi-cluster viral propagation topology.**

### Visualization
Interactive graph containing:
- nodes
- edges
- communities
- high-influence nodes

### Visual encoding
- Node size → influence score or degree/PageRank.
- Node ring → community.
- Edge thickness → interaction weight.
- Highlighted node → selected/high-influence node.

### Summary metrics
- Total Nodes
- Connections
- Communities
- Top Influence Node

### Interactions
- Pan
- Zoom
- Hover node
- Select node
- Toggle metric overlay

Avoid overwhelming the Overview with thousands of visible labels. Label only the most relevant nodes.

---

## 12.9 Demographic Snapshot

### Title
**Audience Demographics**

Use only aggregate/anonymized presentation.

### Age
- 18 or under
- 19–29
- 30–39
- 40+

### Geography
Aggregate regional distribution.

### Language
- English
- Hindi
- Marathi
- Other

### Professional interests
Example sectors:
- Technology
- Education
- Finance
- Healthcare
- Other

Do not display individual inferred demographic identities.
Do not display exact private residence information.

---

## 12.10 Monitored Ingestion Pipelines

### Title
**Monitored Ingestion Pipelines**

### Sources
- X / Twitter
- Telegram
- YouTube
- Instagram
- Facebook
- Reddit

### Each source card shows
- source name
- current status
- events/day or recent event volume
- ingestion latency
- last event timestamp
- small sparkline if available

### Status
- Live
- Polling
- Degraded
- Paused
- Offline
- Replay

A source marked live must correspond to an actual active ingestion mode.

---

# 13. Live Feed

## Purpose
Expose the normalized event stream.

### Layout
Dense table/list view.

### Columns
- Time
- Platform
- Author/channel
- Content
- Interaction type
- Sentiment
- Emotion
- Topic
- Engagement/metrics

### Filters
- Platform
- Time range
- Sentiment
- Emotion
- Topic
- Interaction type

### Event row example
```text
13:42:18 | X | @user_482 | "..." | repost | Positive | Excitement | AI Healthcare
```

### UX
- Infinite or cursor pagination.
- Live insertion indicator.
- Pause live updates.
- Replay mode clearly labeled.
- Click row to open detail drawer.

---

# 14. Event Detail Drawer

When an event is selected, open a right-side drawer.

### Header
- Platform
- timestamp
- event type
- source ID

### Content
- text
- hashtags
- mentions
- media indicator

### NLP panel
- sentiment + confidence
- emotions + confidence
- irony/sarcasm + confidence
- stance + confidence
- language
- topic

### Network panel
- author
- parent/quoted/forwarded account where available
- interaction relationship

### Metadata
- collected_at
- processing status
- model/version identifiers where appropriate

Do not expose raw secrets, API tokens, internal infrastructure information, or unnecessary personal information.

---

# 15. Sentiment & Emotion Screen

## Purpose
Deep analytical view of how people are reacting.

### Header
**Sentiment & Emotion**

### Primary visual
Large sentiment timeline.

### Secondary modules
- emotion distribution
- emotion over time
- sarcasm / irony rate
- stance distribution
- sentiment by platform
- sentiment by topic

### Suggested layout
```text
┌─────────────────────────────────────────────┐
│ Sentiment Over Time                         │
├──────────────────────┬──────────────────────┤
│ Emotion Distribution  │ Emotion Over Time    │
├──────────────────────┼──────────────────────┤
│ Stance               │ Sarcasm / Irony      │
├──────────────────────┴──────────────────────┤
│ Sentiment by Platform / Topic               │
└─────────────────────────────────────────────┘
```

### Cross-filtering
Selecting a topic or emotion updates the other analytical modules.

---

# 16. Trends & Topics Screen

## Purpose
Understand what topics are emerging, growing, fading, and evolving.

### Main modules
- Rising topics
- Trend velocity
- Topic volume over time
- Topic evolution graph
- Topic-to-sentiment relationship
- Platform distribution
- Trend event markers

### Topic detail
Each topic should display:
- current volume
- baseline volume
- growth rate
- first detected time
- current sentiment
- dominant emotions
- participating platforms
- associated communities

### Topic evolution
Use a flow/sankey-like or node-link visualization only where it improves clarity. Keep it lightweight.

---

# 17. Demographics Screen

## Purpose
Present aggregate audience characteristics.

### Modules
- Age distribution
- Language distribution
- Geographic distribution
- Professional-interest sectors
- Demographics by platform
- Demographics by topic
- Demographics by sentiment

### Privacy presentation
Use labels such as:
**Aggregated from public profile indicators and behavioral signals**

Never imply certainty when a characteristic is inferred.

Use:
- percentages
- confidence/coverage indicators
- "unknown" bucket
- minimum cohort thresholds if implemented

---

# 18. Network Analysis Screen

## Purpose
Understand information flow, influence, topology, and communities.

### Main layout
Left/center:
- large interactive graph

Right:
- network metrics
- selected node details

Bottom:
- community table
- influence ranking

### Metrics
- Nodes
- Edges
- Density
- Communities
- Average degree
- PageRank / influence
- Betweenness
- Clustering coefficient where appropriate

### Filters
- Platform
- interaction type
- time range
- minimum degree
- community

### Edge semantics
Display relationship types through legend or filtering:
- reply
- mention
- repost
- quote
- forward

Weights must be described as configured analytical weights, not literal probabilities of influence.

---

# 19. Timeline Screen

## Purpose
Explain how the information ecosystem evolved.

### Primary visualization
Horizontal chronological timeline.

### Event lanes
- volume
- sentiment
- emotion
- topics
- network activity

### Major-event markers
When a large change occurs, show a marker such as:
```text
14:15
Topic spike
Sentiment shift
Community propagation
```

### Interaction
Selecting a time region filters all analytics to that interval.

This screen should make chronological emergence one of the clearest features of the product.

---

# 20. Data Sources Screen

## Purpose
Show source coverage and ingestion configuration.

### Each source row/card
- platform
- connection mode
- status
- last successful collection
- recent event rate
- latency
- errors
- current mode

### Modes
Examples:
- stream
- polling
- replay
- disabled

### Source-specific detail
Show only relevant information.

For example:
X:
- stream status
- polling fallback

Telegram:
- authorized session status
- channels monitored

YouTube:
- polling interval
- quota-aware state

Meta:
- API version
- permissions/status

Reddit:
- optional adapter state

Do not expose API keys.

---

# 21. Collection Status Screen

## Purpose
Operational monitoring for the ingestion pipeline.

### KPIs
- events/sec
- events/min
- events/day
- processing latency
- queue depth
- failed events
- dead-letter events

### Charts
- ingestion throughput over time
- latency over time
- errors over time

### Operational status
Use clear statuses:
- Healthy
- Degraded
- Offline

Do not make the dashboard falsely appear healthy if the backend is not actually connected.

---

# 22. Settings

Sections:
- General
- Appearance
- Time range defaults
- Data retention/configuration
- Source configuration
- Analytics configuration
- Privacy controls

Sensitive credentials must never be entered into visible mock UI intended for screenshots.

---

# 23. Notifications / Alerts

Alerts should correspond to analytical events, not generic application notifications.

### Examples
- Topic spike crossed configured threshold
- Sentiment changed materially
- Collection source degraded
- High-volume anomaly detected
- Community growth anomaly
- Processing backlog increased

Each alert should contain:
- severity
- time
- source
- event
- concise explanation

---

# 24. Filters and Global Controls

### Time presets
- 1H
- 6H
- 24H
- 7D
- 30D where data volume permits
- Custom

### Platform chips
- X
- Telegram
- YouTube
- Instagram
- Facebook
- Reddit

### Optional global topic filter
Search/select topic.

### Filter behavior
Filters should update all compatible visualizations on the current screen and clearly display the active filter state.

Avoid hidden filter state.

---

# 25. Chart Standards

## Line charts
Use when showing:
- sentiment over time
- event volume
- emotion over time
- trend velocity

Rules:
- light horizontal grid lines
- muted axes
- clear legend
- no excessive point markers
- tooltips on hover

## Bar charts
Use for:
- demographic distributions
- emotion distribution
- platform comparisons

## Heatmaps
Use for:
- hourly activity
- temporal concentration

## Network graphs
Use for:
- influence
- communities
- propagation

## Tables
Use when exact values matter more than visual shape.

---

# 26. Empty States

Every major screen needs an honest empty state.

Examples:

### No data
**No events in this window**

### Waiting for source
**Waiting for new events from Telegram**

### Feature unavailable
**Demographic inference is unavailable for the selected cohort**

### Replay mode
**Viewing replayed historical data**

Never fill an unavailable module with fake metrics without labeling them as demo data.

---

# 27. Loading States

Use skeleton placeholders matching the final card geometry.

Avoid full-screen spinners for simple widgets.

Charts should display:
- skeleton grid
- muted placeholder line/shape
- loading label only when necessary

---

# 28. Error States

Errors should be specific.

Bad:
**Something went wrong**

Better:
**X stream disconnected**
**Last successful event: 13:42:11**
**Retrying connection...**

For model failures:
**Emotion analysis unavailable for 23 events**
**Events retained; analysis will retry.**

---

# 29. Live / Replay UX

The application must visually distinguish:

### LIVE
```text
● LIVE
Receiving events now
```

### REPLAY
```text
◷ REPLAY
Historical dataset
```

### PAUSED
```text
Ⅱ PAUSED
Live updates paused
```

Never label replayed data as live.

---

# 30. Micro-interactions

Use subtle motion only.

### Allowed
- sidebar active transition
- card hover elevation
- dropdown opening
- tooltip fade/slide
- live event insertion
- graph zoom
- filter transitions

### Avoid
- large page animations
- constant chart bouncing
- decorative particle systems
- fake AI typing animations
- excessive neon effects

Animations should communicate state, not decoration.

---

# 31. Accessibility

Requirements:
- keyboard-focusable controls
- visible focus state
- sufficient text contrast
- charts with text/tooltip equivalents
- do not rely solely on color
- semantic buttons and links
- readable font sizes

---

# 32. Responsive Behavior

Desktop is primary.

### 1440px+
Use the full 12-column dashboard.

### 1180–1439px
Reduce card gutters and padding slightly.

### 900–1179px
Collapse some 8/4 layouts into stacked sections.

### Below 900px
Use a simplified navigation/drawer if responsive support is required.

Do not force dense network graphs or large data tables into tiny columns.

---

# 33. Dashboard Component Library

Create reusable components before building all pages.

### Shell
- AppShell
- Sidebar
- TopBar
- PageHeader

### Navigation
- NavSection
- NavItem
- ActiveIndicator

### Cards
- MetricCard
- AnalyticsCard
- StatusCard
- SourceCard

### Controls
- TimeRangePicker
- PlatformFilter
- Dropdown
- SearchInput
- FilterChip

### Analytics
- SentimentChart
- EmotionBars
- TrendTable
- ActivityHeatmap
- InfluenceGraph
- TimelineChart
- DistributionBars

### Operational
- LiveStatus
- SourceHealthBadge
- AlertRow
- ActivityRow

### Data
- EventTable
- EventDetailDrawer
- UserSummary
- TopicSummary

---

# 34. Overview Component Placement

At 1440px, the preferred vertical structure is:

```text
Top Bar
  ↓
Page Header
  ↓
5 KPI Cards
  ↓
Sentiment Over Time       | Emotion Distribution
  ↓
Conversation Activity     | Live Activity
  ↓
Rising Topics             | Influence Network
  ↓
Monitored Ingestion Pipelines
```

Demographic summary may occupy a side slot on the Overview if space allows, but the Overview should never become too vertically fragmented.

---

# 35. Design Hierarchy

Priority order for screen real estate:

1. Live/current state
2. Sentiment and emotional change
3. Emerging topics
4. Network/influence
5. Timeline
6. Aggregate demographics
7. Source health

The most important information should have the largest visual area.

---

# 36. Trust and Data Honesty

The UI is an analytical system, so visual honesty is more important than visual spectacle.

### Requirements
- Distinguish measured values from inferred values.
- Show unknown/insufficient-data states.
- Avoid false precision.
- Label demo/replay data.
- Use aggregate demographic displays.
- Show confidence where model uncertainty materially matters.
- Do not imply causal relationships when the backend only measures correlation or interaction.

Example:

Bad:
**Topic caused sentiment to drop 18%**

Better:
**Sentiment declined 18% during the topic spike**

---

# 37. Demo Data Guidelines

Stitch/mockup data can be realistic and visually varied.

Suggested placeholder values should:
- have believable magnitudes
- show changes over time
- include positive and negative movement
- include several platforms
- include multiple topics
- include network communities

Avoid using the exact same numbers repeatedly across screens.

All demo data should be clearly replaceable with API-backed values.

---

# 38. Important Product Language

Preferred terms:
- Event
- Conversation
- Public activity
- Topic
- Trend
- Sentiment
- Emotion
- Influence
- Community
- Network
- Propagation
- Source
- Pipeline
- Collection
- Timeline
- Aggregate

Avoid:
- Follower growth
- Creator performance
- Publishing schedule
- Boosted post
- Caption
- Social inbox
- Marketing campaign metrics

---

# 39. Platform Terminology

Use:
- **X** as the primary current name, optionally showing `(Twitter)` in secondary technical contexts.
- **Telegram**
- **YouTube**
- **Instagram**
- **Facebook**
- **Reddit**

Platform branding should be recognizable but visually subordinate to the analytical information.

---

# 40. Design for Technical Demonstration

The UI should make it easy to demonstrate the underlying engineering.

A good demo flow:

```text
Overview
  ↓
Live Feed
  ↓
click a post/event
  ↓
Event Detail
  ↓
Sentiment & Emotion
  ↓
click emerging topic
  ↓
Trends & Topics
  ↓
Network Analysis
  ↓
Timeline
  ↓
Data Sources
```

The audience should be able to see that the dashboard is not a collection of independent mock charts.

---

# 41. Hackathon Demo Story

The recommended demonstration narrative is:

### Step 1 — Data arrives
Show the Live status and monitored pipelines.

### Step 2 — Activity spikes
Show Conversation Activity / volume change.

### Step 3 — Trend detected
Open Rising Topics.

### Step 4 — Human reaction changes
Open Sentiment & Emotion.

### Step 5 — Emotion becomes nuanced
Show excitement, anxiety, sarcasm/irony, and stance.

### Step 6 — Information spreads
Open Influence Network.

### Step 7 — Different communities react
Show network communities and aggregate demographics.

### Step 8 — Explain the evolution
Open Timeline.

This creates a direct visual mapping from data ingestion to intelligence.

---

# 42. Figma / Stitch Page List

Create the following pages/frames:

```text
00 — Design System
01 — Overview
02 — Live Feed
03 — Event Detail Drawer
04 — Sentiment & Emotion
05 — Trends & Topics
06 — Topic Detail
07 — Demographics
08 — Network Analysis
09 — Timeline
10 — Data Sources
11 — Collection Status
12 — Alerts / Notifications
13 — Settings
14 — System Architecture
15 — Data Flow
```

---

# 43. Design System Page Requirements

The Design System frame should contain:

### Foundations
- colors
- typography
- spacing
- radii
- shadows
- icon sizing

### Components
- buttons
- dropdowns
- chips
- metric cards
- analytics cards
- status badges
- tables
- activity rows
- tooltips
- tabs

### Data visualization examples
- line chart
- bar chart
- heatmap
- network graph
- timeline

---

# 44. System Architecture Visual

Create a separate clean architecture diagram:

```text
X ───────────────┐
Telegram ────────┤
YouTube ─────────┤
Meta ────────────┤
Reddit ──────────┘
        │
        ▼
Event Normalizer
        │
        ▼
PostgreSQL
        │
   ┌────┼─────────────┐
   ▼    ▼             ▼
  NLP  BERTrend   Demographics
   │    │             │
   └────┼─────────────┘
        ▼
    NetworkX
        │
        ▼
      FastAPI
        │
        ▼
 React Dashboard
```

The diagram should visually match the dashboard design system.

---

# 45. Data Flow Visual

Separate diagram:

```text
Post / Message / Comment
          ↓
      Collection
          ↓
      Normalization
          ↓
        Storage
          ↓
 ┌────────┼───────────┐
 ▼        ▼           ▼
NLP     Trends      Graph
 ▼        ▼           ▼
Sentiment Topic     Influence
Emotion   Evolution  Community
Stance    Velocity   Propagation
          │
          ▼
      Aggregation
          │
          ▼
       Dashboard
```

---

# 46. AI / Analytics Presentation Rules

Do not make AI visible through arbitrary glowing brains, robot icons, or decorative neural networks.

Instead, communicate intelligence through:
- confidence badges
- detected anomalies
- topic evolution
- relationships
- model-derived labels
- timeline changes
- analytical explanations

The product should look technically sophisticated because the **information design is sophisticated**, not because it uses futuristic decoration.

---

# 47. Implementation Rules for Frontend Agents

Before implementing:
1. Read `SPECS.md`.
2. Read `AGENTS.md`.
3. Read this `design.md`.
4. Inspect the approved Stitch/Figma design.

The agent must treat this file as the visual source of truth.

### Preserve
- component hierarchy
- spacing system
- color tokens
- typography
- visual density
- interaction states

### Do not invent
- new navigation concepts
- unrelated product features
- fake social-management modules
- unsupported analytics metrics

### Data binding
Every dashboard metric must have an obvious future backend data source.

---

# 48. Frontend Implementation Priorities

Build in this order:

1. App shell
2. Sidebar
3. Top bar
4. Design tokens
5. Overview layout
6. Metric cards
7. Sentiment chart
8. Emotion distribution
9. Trend table
10. Live activity
11. Conversation heatmap
12. Network graph
13. Ingestion pipeline cards
14. Live Feed
15. Detail drawer
16. Remaining analytical pages
17. Responsive behavior
18. Accessibility and polish

Do not spend the majority of implementation time on decorative details before the core analytics screens function.

---

# 49. Backend-to-UI Contract Expectations

The UI should expect structured analytical data rather than embedding business logic into components.

Examples:

### KPI
```json
{
  "label": "Live Events",
  "value": 12842,
  "change": 18.4,
  "period": "24h"
}
```

### Sentiment point
```json
{
  "timestamp": "2026-09-20T13:00:00Z",
  "positive": 0.47,
  "neutral": 0.28,
  "negative": 0.25,
  "volume": 842
}
```

### Trend
```json
{
  "topic": "Autonomous AI Agents",
  "growth": 2.48,
  "volume": 42800,
  "sentiment": 0.68,
  "status": "explosive"
}
```

### Network node
```json
{
  "id": "user_472",
  "community": 3,
  "influence": 0.82,
  "degree": 421
}
```

These examples are interface contracts, not mandatory database schemas.

---

# 50. Definition of Done — Design

The design is ready for implementation when:

- Overview clearly represents the Social Sentinel product.
- No creator/social-media-manager workflows remain.
- Sidebar exactly matches the intelligence information architecture.
- All five core analytical capabilities have visible UI representation.
- Live data collection is visually represented honestly.
- Sentiment and emotion are separate but connected concepts.
- Trends have growth/velocity and chronological context.
- Demographics are aggregate and privacy-conscious.
- Network analysis visibly supports nodes, edges, communities, and influence.
- Timeline explains change through time.
- Data source health is visible.
- Empty/loading/error/replay states exist.
- Components are reusable.
- Design tokens are documented.
- The 1440px Overview looks cohesive without scrolling horizontally.
- A judge can understand the product within approximately 10 seconds.

---

# 51. Final Visual Target

The finished product should look like a mature B2B analytics application:

**Clean enough for a SaaS product.**

**Dense enough for an analyst.**

**Technical enough for a hackathon.**

**Simple enough for a judge to understand immediately.**

The reference image provides the visual grammar. This document defines the product language.

The final UI should therefore feel like the same design family as the reference while being unmistakably a **real-time AI-driven social intelligence platform** rather than a social-media management dashboard.
