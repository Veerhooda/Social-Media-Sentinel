# Graph Analytics

Graphs are derived only from normalized collected events. Mention links require
verified platform user IDs; textual `@names` remain event content but do not
create account nodes without a resolvable identity.

## Edge extraction

| Interaction | Source | Target | Default weight |
|---|---|---|---:|
| reply | replying author | parent author | 0.8 |
| mention | mentioning author | mentioned user | 0.5 |
| repost | reposting author | original author | 1.0 |
| quote | quoting author | quoted author | 1.0 |

The defaults are configurable engineering weights, not empirically established influence probabilities. Multiple persisted relationships between the same ordered pair are aggregated into one weighted NetworkX edge while retaining interaction-type metadata.

## Metrics

The service calculates:

- in/out degree centrality
- betweenness centrality
- closeness centrality
- PageRank
- HITS hub/authority scores
- Louvain communities on the undirected projection

Results describe structural interaction patterns in collected data. They are not causal claims about real-world influence.

No follower network is claimed or constructed because follower-edge availability has not been verified for the configured X access.

## Visual exploration

The React interaction map uses Sigma.js (WebGL) and Graphology. ForceAtlas2
positions only backend-returned accounts and relationships; its coordinates
are deterministic for the same API response. The default connected-core view
keeps up to 90 accounts with observed edges readable. “All loaded” shows all
accounts returned by the recent-edge API request, not the full database.
Directional arrows are drawn from source to target. Click or use the
keyboard-accessible PageRank ranking to select an account; its incoming and
outgoing stored relationships appear beside the map. Pan, zoom, and reset are
available. The ranking and relationship detail remain usable when WebGL is
unavailable. Community colors and node sizes are descriptive, not evidence of
causal influence.

Stored public author profiles are joined to the sampled map by platform and
platform user ID, after confirming the author has a non-replay event. When an
X profile has a stored HTTPS avatar URL, Sigma displays the public image in
its node; the account list and selected-account panel show the same image,
name, username, and a public profile link. Image loading depends on the
source host permitting cross-origin requests. A failed image falls back to a
colored node or initial. Accounts known only because someone mentioned or
replied to them stay explicitly `referenced only`; no identity or photo is
invented. No profile-image bytes are persisted.

The map's colors encode structural Louvain communities. They do not encode
age, geography, language, or professional interest. The audience coverage
strip reports total mapped nodes, stored public profiles, referenced-only
nodes, stored avatar URLs, and existing demographic records for the loaded
500-edge sample. The default view draws up to 90 connected accounts; "All
loaded" shows all nodes in that sample. These values can be smaller than the
all-time network summary at the top of the page.


## Temporal snapshots

`GET /api/network/temporal` splits stored edges into trailing fixed windows
(`15m`, `1h`, `6h`, `24h`) anchored at the latest stored source timestamp.
Chronology uses `created_at` source time; `collected_at` is preserved for
ingestion diagnostics only. Influence deltas (`pagerank increased`,
`betweenness decreased`) are reported only for nodes measured in at least
two windows. Single-measurement nodes never produce emerging-influencer
claims.

## Communities

`GET /api/network/communities` profiles each Louvain community with size,
interaction volume, dominant interaction types, and activity span.
Community identifiers are snapshot-local and are not tracked across
windows.
The dashboard requests `limit=500` for the same recent-edge sample shown in
the map. Clicking a community isolates its accounts and internal links. The endpoint omits
the limit by default for callers that need the full stored graph.

Each node is counted exactly once in its assigned community, including when
an interaction connects different communities. Interaction volume counts
edges incident to the community; a cross-community edge therefore contributes
to both communities' activity without duplicating either endpoint's membership.
Community audience summaries join existing aggregate language, country, and
interest-sector estimates only for mapped nodes that have stored profiles.
Each dimension reports known/unknown coverage. A category distribution is
shown only when at least three members share that category. Smaller category
counts are withheld and reported as suppressed; a dimension with no visible
category reports `INSUFFICIENT_DATA`. These are descriptive estimates of observed
participants, not labels for every account or a map of platform followers.

## Observed cascades

`GET /api/network/cascades` and `GET /api/network/cascades/{cascade_id}`
reconstruct cascades from stored `parent_platform_post_id` chains grouped
under `thread_root_id`. Reported metrics: depth, width, event count,
duration, participants, communities, interaction types, sentiment/emotion
composition from persisted NLP, and a chronological propagation path.
Missing parents are never inferred; such cascades are marked `partially
observable` and only the observed subset is returned. Topic-specific
cascade analysis is explicitly unavailable because per-event topic
assignments are not persisted.

## Terminology

Observed interaction network, structural influence, observed propagation,
temporal graph snapshot, interaction centrality, insufficient relationship
data. No causal influence is claimed. NDLib diffusion simulation is not
integrated; if added later it must stay clearly separated as simulated
versus observed.
